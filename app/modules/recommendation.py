import math
from collections import defaultdict

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize, MinMaxScaler
from .profiling import INTEREST_OPTIONS
from .collaborative import get_collaborative_scores

BUDGET_TIER_ORDER = ["budget", "mid-range", "luxury"]

# Determines the budget tier based on the attraction's entry cost.
def cost_tier(entry_cost):
    cost = entry_cost or 0
    if cost == 0:
        return "budget"
    elif cost <= 10:
        return "mid-range"
    return "luxury"

 # Encodes an attraction's category into a feature vector.
def encode_attraction(attraction):
    category = (attraction.get("category") or "").lower()
    vec = [1.0 if category == c else 0.0 for c in INTEREST_OPTIONS]
    return np.array(vec, dtype=float).reshape(1, -1)

# Calculates the attraction's compatibility with the user's budget preference.
def budget_fit(attraction_tier, user_budget_type):
    if user_budget_type not in BUDGET_TIER_ORDER or attraction_tier not in BUDGET_TIER_ORDER:
        return 1.0
    dist = abs(BUDGET_TIER_ORDER.index(attraction_tier) - BUDGET_TIER_ORDER.index(user_budget_type))
    return {0: 1.0, 1: 0.7, 2: 0.4}[dist]

# Calculates average feedback scores for attractions from users with the same persona.
def get_feedback_scores_batch(attraction_ids, persona_label, db_session):
    from app.models import ItineraryRating, ItineraryItem, UserProfile

    rows = (
        db_session.query(ItineraryItem.attraction_id, ItineraryRating.rating_score)
        .join(ItineraryRating, ItineraryRating.itinerary_id == ItineraryItem.itinerary_id)
        .join(UserProfile, ItineraryRating.user_id == UserProfile.user_id)
        .filter(
            ItineraryItem.attraction_id.in_(attraction_ids),
            UserProfile.persona_label == persona_label,
        )
        .all()
    )
    scores_by_attraction = defaultdict(list)
    for attraction_id, rating_score in rows:
        scores_by_attraction[attraction_id].append(rating_score)

    result = {}
    for attraction_id in attraction_ids:
        scores = scores_by_attraction.get(attraction_id)
        result[attraction_id] = 0.5 if not scores else (sum(scores) / len(scores) - 1) / 4
    return result

# Retrieves the feedback score for a single attraction and persona.
def get_feedback_score(attraction_id, persona_label, db_session):
    return get_feedback_scores_batch([attraction_id], persona_label, db_session)[attraction_id]

# Limits category dominance to maintain diversity in the top recommendations.
def _diversify_top_n(ranked_indices, attractions, top_n, max_share=0.4):
    cap = max(1, math.ceil(top_n * max_share))
    counts = defaultdict(int)
    selected, leftover = [], []
    for idx in ranked_indices:
        category = attractions[idx].get("category")
        if counts[category] < cap:
            selected.append(idx)
            counts[category] += 1
        else:
            leftover.append(idx)
        if len(selected) == top_n:
            break
    if len(selected) < top_n:
        selected.extend(leftover[: top_n - len(selected)])
    return selected

# Generates and ranks personalised attraction recommendations using hybrid scoring.
def recommend_attractions(
    user_profile,
    attractions,
    db_session,
    budget_limit=None,
    top_n=20,
    behaviour_weights=None,
    use_cf=True,
):
    if not attractions:
        return []

    # Interest-only vector — budget_type is handled separately by budget_fit()
    # below, not folded into this dot product (see encode_attraction() docstring).
    selected_interests = set(user_profile["interests"])
    user_vec = np.array(
        [1.0 if c in selected_interests else 0.0 for c in INTEREST_OPTIONS],
        dtype=float,
    ).reshape(1, -1)
    if behaviour_weights:
        for i, c in enumerate(INTEREST_OPTIONS):
            user_vec[0, i] = min(1.0, user_vec[0, i] + 0.5 * behaviour_weights.get(c, 0.0))
    user_vec_norm = normalize(user_vec)

    # Remove disliked attractions
    if user_profile.get("user_id"):
        from app.models.attraction_feedback import AttractionFeedback
        disliked_ids = {
            f.attraction_id
            for f in db_session.query(AttractionFeedback)
            .filter_by(user_id=int(user_profile["user_id"]))
            .all()
        }
        if disliked_ids:
            attractions = [a for a in attractions if a["attraction_id"] not in disliked_ids]

    if budget_limit is not None:
        attractions = [a for a in attractions if (a.get("entry_cost") or 0) <= budget_limit]
    if not attractions:
        return []

    att_vecs_norm = normalize(np.vstack([encode_attraction(a) for a in attractions]))

    # Algorithm 2: CB_hybrid = 0.7 × cosine_similarity + 0.3 × feedback_score
    # cosine_similarity is now interest-vs-category only; budget_fit scales it
    # afterward as a [0.4, 1.0] multiplier rather than sharing the dot product,
    # so a budget mismatch discounts a match instead of erasing it.
    sim_scores = cosine_similarity(user_vec_norm, att_vecs_norm)[0]
    user_budget_type = user_profile.get("budget_type")
    budget_fit_arr = np.array([
        budget_fit(cost_tier(a.get("entry_cost")), user_budget_type) for a in attractions
    ])
    sim_scores = sim_scores * budget_fit_arr
    persona = user_profile.get("persona_label", "")
    feedback_lookup = get_feedback_scores_batch(
        [a["attraction_id"] for a in attractions], persona, db_session
    )
    feedback_scores = np.array([feedback_lookup[a["attraction_id"]] for a in attractions])
    hybrid_scores = 0.7 * sim_scores + 0.3 * feedback_scores

    def safe_norm(arr):
        col = arr.reshape(-1, 1)
        if col.max() - col.min() < 1e-9:
            return np.zeros(len(arr))
        return MinMaxScaler().fit_transform(col).flatten()

    hybrid_norm  = safe_norm(hybrid_scores)
    ratings_norm = safe_norm(np.array([a.get("rating") or 0 for a in attractions]))
    pops_norm    = safe_norm(np.array([a.get("popularity_score") or 0 for a in attractions]))

    # Algorithm 4: final = 0.40×CB + 0.25×CF + 0.20×rating + 0.15×popularity
    user_id = user_profile.get("user_id")
    cf_raw = get_collaborative_scores(user_id, [a["attraction_id"] for a in attractions], db_session) \
        if use_cf and user_id else {}
    cf_arr  = np.array([cf_raw.get(a["attraction_id"], 0.5) for a in attractions])
    cf_norm = safe_norm(cf_arr)

    # When CF is flat (cold-start — no rating history yet), skip it and redistribute
    # its 0.25 weight to CB and rating so the top match can score higher (≥85%)
    if cf_norm.sum() < 1e-9:
        final_scores = 0.55 * hybrid_norm + 0.28 * ratings_norm + 0.17 * pops_norm
    else:
        final_scores = 0.40 * hybrid_norm + 0.25 * cf_norm + 0.20 * ratings_norm + 0.15 * pops_norm

    '''Full score-descending order first, then cap any single category's share
    of the returned top_n (see _diversify_top_n) so results stay a mix of
    the user's selected interests instead of collapsing to whichever
    category happens to have the most budget-tier-matching supply.'''
    full_ranking = np.argsort(final_scores)[::-1]
    ranked_indices = _diversify_top_n(full_ranking, attractions, top_n)

    result = []
    for idx in ranked_indices:
        rec = dict(attractions[idx])
        rec["recommendation_score"] = round(float(final_scores[idx]), 4)
        rec["similarity_score"]     = round(float(sim_scores[idx]), 4)
        rec["cf_score"]             = round(float(cf_arr[idx]), 4)
        rec["feedback_score"]       = round(float(feedback_scores[idx]), 4)
        result.append(rec)

    return result
