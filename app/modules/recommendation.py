import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize, MinMaxScaler

from .profiling import encode_user, INTEREST_OPTIONS
from .collaborative import get_collaborative_scores

BUDGET_TIER_MAP = {
    "budget":    [1, 0, 0],
    "mid-range": [0, 1, 0],
    "luxury":    [0, 0, 1],
}


def encode_attraction(attraction):
    cost = attraction.get("entry_cost") or 0
    if cost == 0:
        tier = "budget"
    elif cost <= 10:
        tier = "mid-range"
    else:
        tier = "luxury"
    vec = list(BUDGET_TIER_MAP.get(tier, [0, 1, 0]))
    vec += [0, 0, 0]  # no weather attribute for attractions
    category = (attraction.get("category") or "").lower()
    vec += [1 if category == c else 0 for c in INTEREST_OPTIONS]
    return np.array(vec, dtype=float).reshape(1, -1)


def get_feedback_score(attraction_id, persona_label, db_session):
    from app.models import ItineraryRating, ItineraryItem, UserProfile
    rows = (
        db_session.query(ItineraryRating.rating_score)
        .join(ItineraryItem, ItineraryRating.itinerary_id == ItineraryItem.itinerary_id)
        .join(UserProfile, ItineraryRating.user_id == UserProfile.user_id)
        .filter(
            ItineraryItem.attraction_id == attraction_id,
            UserProfile.persona_label == persona_label,
        )
        .all()
    )
    if not rows:
        return 0.5
    scores = [r.rating_score for r in rows]
    return (sum(scores) / len(scores) - 1) / 4


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

    user_vec = encode_user(
        user_profile["budget_type"],
        user_profile["weather_pref"],
        user_profile["interests"],
        behaviour_weights=behaviour_weights,
    )
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
    sim_scores = cosine_similarity(user_vec_norm, att_vecs_norm)[0]
    persona = user_profile.get("persona_label", "")
    feedback_scores = np.array([
        get_feedback_score(a["attraction_id"], persona, db_session)
        for a in attractions
    ])
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
    ranked_indices = np.argsort(final_scores)[::-1][:top_n]

    result = []
    for idx in ranked_indices:
        rec = dict(attractions[idx])
        rec["recommendation_score"] = round(float(final_scores[idx]), 4)
        rec["similarity_score"]     = round(float(sim_scores[idx]), 4)
        rec["cf_score"]             = round(float(cf_arr[idx]), 4)
        rec["feedback_score"]       = round(float(feedback_scores[idx]), 4)
        result.append(rec)

    return result
