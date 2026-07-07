"""
Personalised Recommendation Module — Modules 2, 3 & 4 (Chapter 4)

─────────────────────────────────────────────────────────────────────────────
Algorithm 2  Content-based hybrid score (unchanged):
    hybrid_score = 0.7 × cosine_similarity + 0.3 × feedback_score

    cosine_similarity is computed between the user vector and each attraction
    vector. When behaviour_weights are available, the user vector is
    behaviour-augmented (see profiling.encode_user).

─────────────────────────────────────────────────────────────────────────────
Algorithm 3  Multi-criteria ranking (unchanged):
    rank_score = 0.5 × hybrid_norm
               + 0.2 × rating_norm
               + 0.1 × popularity_norm
               + 0.2 × feedback_norm

─────────────────────────────────────────────────────────────────────────────
Algorithm 4  Full hybrid with Collaborative Filtering (NEW):
    final_score = 0.40 × hybrid_norm          (behaviour-aware content-based)
               + 0.25 × cf_score_norm         (user-user collaborative filtering)
               + 0.20 × rating_norm           (attraction quality signal)
               + 0.15 × popularity_norm       (crowd wisdom)

    Weights sum to 1.0.
    Note: feedback is already embedded inside hybrid_norm via Algorithm 2,
    so it is not added again as a separate term.

    When CF data is unavailable (cold-start / no ratings yet), cf_score
    defaults to 0.5 (neutral) and the formula degrades gracefully to a
    content-based result.

─────────────────────────────────────────────────────────────────────────────
All sub-scores are normalised to [0, 1] before weighting.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize, MinMaxScaler

from .profiling import (
    encode_user,
    BUDGET_OPTIONS,
    WEATHER_OPTIONS,
    INTEREST_OPTIONS,
)
from .collaborative import get_collaborative_scores

BUDGET_TIER_MAP = {
    "budget":    [1, 0, 0],
    "mid-range": [0, 1, 0],
    "luxury":    [0, 0, 1],
}

CATEGORIES = INTEREST_OPTIONS


def encode_attraction(attraction: dict) -> np.ndarray:
    """
    Encodes one attraction into the same 12-dim vector space as the user.
    Attraction vectors are always binary (no behaviour augmentation needed).
    """
    cost = attraction.get("entry_cost") or 0
    if cost == 0:
        budget_tier = "budget"
    elif cost <= 10:
        budget_tier = "mid-range"
    else:
        budget_tier = "luxury"

    vec = []
    vec += BUDGET_TIER_MAP.get(budget_tier, [0, 1, 0])
    vec += [0, 0, 0]                                   # weather: attractions have no weather attr
    category = (attraction.get("category") or "").lower()
    vec += [1 if category == c else 0 for c in CATEGORIES]

    return np.array(vec, dtype=float).reshape(1, -1)


def get_feedback_score(attraction_id: int, persona_label: str, db_session) -> float:
    from app.models import ItineraryRating, ItineraryItem, UserProfile

    rows = (
        db_session.query(ItineraryRating.rating_score)
        .join(ItineraryItem, ItineraryRating.itinerary_id == ItineraryItem.itinerary_id)
        .join(UserProfile,   ItineraryRating.user_id == UserProfile.user_id)
        .filter(
            ItineraryItem.attraction_id == attraction_id,
            UserProfile.persona_label   == persona_label,
        )
        .all()
    )

    if not rows:
        return 0.5
    scores = [r.rating_score for r in rows]
    return (sum(scores) / len(scores) - 1) / 4


def recommend_attractions(
    user_profile: dict,
    attractions: list,
    db_session,
    budget_limit: float = None,
    top_n: int = 20,
    behaviour_weights: dict = None,
    use_cf: bool = True,
) -> list:
    """
    Returns top_n ranked attractions for a user.

    Parameters
    ----------
    user_profile      : dict with keys budget_type, weather_pref, interests,
                        persona_label, user_id
    attractions       : list of attraction dicts (Attraction.to_dict())
    db_session        : active SQLAlchemy session
    budget_limit      : optional maximum entry_cost filter
    top_n             : number of results to return
    behaviour_weights : optional dict from behaviour.get_behaviour_weights()
                        used to produce a behaviour-augmented user vector
    use_cf            : set False to skip CF (faster, used for cold-start users)

    Algorithm 4 is used when CF data is available; falls back to Algorithm 3
    transparently when CF cannot be computed.
    """
    if not attractions:
        return []

    # ── Behaviour-aware user encoding ────────────────────────────────────
    # behaviour_weights softens the interest dimensions based on observed
    # behaviour without altering the persona assignment (K-Means stays binary).
    user_vec      = encode_user(
        user_profile["budget_type"],
        user_profile["weather_pref"],
        user_profile["interests"],
        behaviour_weights=behaviour_weights,    # None on first visit
    )
    user_vec_norm = normalize(user_vec)

    # ── Filter attractions the user has explicitly disliked ───────────────
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

    # ── Budget filter ─────────────────────────────────────────────────────
    if budget_limit is not None:
        attractions = [a for a in attractions if (a.get("entry_cost") or 0) <= budget_limit]
    if not attractions:
        return []

    # ── Encode attractions ────────────────────────────────────────────────
    att_vecs      = np.vstack([encode_attraction(a) for a in attractions])
    att_vecs_norm = normalize(att_vecs)

    # ── Algorithm 2: Content-based hybrid ────────────────────────────────
    sim_scores = cosine_similarity(user_vec_norm, att_vecs_norm)[0]   # (n,)

    persona = user_profile.get("persona_label", "")
    feedback_scores = np.array([
        get_feedback_score(a["attraction_id"], persona, db_session)
        for a in attractions
    ])

    hybrid_scores = 0.7 * sim_scores + 0.3 * feedback_scores

    # ── Normalise sub-scores to [0, 1] ───────────────────────────────────
    def safe_norm(arr):
        col = arr.reshape(-1, 1)
        if col.max() - col.min() < 1e-9:
            return np.zeros(len(arr))
        return MinMaxScaler().fit_transform(col).flatten()

    hybrid_norm  = safe_norm(hybrid_scores)
    ratings_norm = safe_norm(np.array([a.get("rating") or 0 for a in attractions]))
    pops_norm    = safe_norm(np.array([a.get("popularity_score") or 0 for a in attractions]))

    # ── Algorithm 4: Collaborative Filtering ─────────────────────────────
    user_id    = user_profile.get("user_id")
    att_ids    = [a["attraction_id"] for a in attractions]
    cf_raw     = {}

    if use_cf and user_id:
        cf_raw = get_collaborative_scores(
            target_user_id=user_id,
            attraction_ids=att_ids,
            db_session=db_session,
        )

    cf_arr = np.array([cf_raw.get(a["attraction_id"], 0.5) for a in attractions])
    cf_norm = safe_norm(cf_arr)

    # ── Final ranking: Algorithm 4 formula ───────────────────────────────
    #
    #   final = 0.40 × CB_hybrid       (includes feedback inside Algorithm 2)
    #         + 0.25 × CF_score
    #         + 0.20 × rating
    #         + 0.15 × popularity
    #
    # Feedback is already encoded in CB_hybrid (= 0.7×sim + 0.3×feedback),
    # so it is not added again separately.
    # When CF defaults to neutral (0.5 everywhere, normalised to 0),
    # the formula degrades gracefully to a pure content-based result.
    final_scores = (
        0.40 * hybrid_norm
        + 0.25 * cf_norm
        + 0.20 * ratings_norm
        + 0.15 * pops_norm
    )

    ranked_indices = np.argsort(final_scores)[::-1][:top_n]

    result = []
    for idx in ranked_indices:
        rec = dict(attractions[idx])
        rec["recommendation_score"]  = round(float(final_scores[idx]), 4)
        rec["similarity_score"]      = round(float(sim_scores[idx]), 4)
        rec["cf_score"]              = round(float(cf_arr[idx]), 4)
        rec["feedback_score"]        = round(float(feedback_scores[idx]), 4)
        result.append(rec)

    return result
