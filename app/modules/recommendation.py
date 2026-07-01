
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize, MinMaxScaler

from .profiling import (
    encode_user,
    BUDGET_OPTIONS,
    WEATHER_OPTIONS,
    INTEREST_OPTIONS,
)

# Budget tier ordering used to encode attraction entry cost
BUDGET_TIER_MAP = {
    "budget": [1, 0, 0],
    "mid-range": [0, 1, 0],
    "luxury": [0, 0, 1],
}

CATEGORIES = INTEREST_OPTIONS  # same list: nature/food/history/shopping/adventure/relaxation


def encode_attraction(attraction: dict) -> np.ndarray:
    """
    Encodes an attraction dict into the same vector space as the user vector.

    Attraction dict keys expected: category, entry_cost, popularity_score
    """
    # Budget tier from entry_cost (same thresholds as user budget_type expectations)
    cost = attraction.get("entry_cost") or 0
    if cost == 0:
        budget_tier = "budget"
    elif cost <= 10:
        budget_tier = "mid-range"
    else:
        budget_tier = "luxury"

    vec = []
    # Budget tier (3 dims, mirrors user encoding)
    vec += BUDGET_TIER_MAP.get(budget_tier, [0, 1, 0])
    # Weather pref: attractions don't have a weather attribute, so leave neutral (all 0s)
    vec += [0, 0, 0]
    # Category (6 dims)
    category = (attraction.get("category") or "").lower()
    vec += [1 if category == c else 0 for c in CATEGORIES]

    return np.array(vec, dtype=float).reshape(1, -1)


def get_feedback_score(attraction_id: int, persona_label: str, db_session) -> float:
    """
    Returns average itinerary rating from users who share the same persona_label
    AND whose itinerary included this attraction.
    Returns 0.5 (neutral) when there are no feedback records yet.
    """
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
        return 0.5  # cold-start neutral

    scores = [r.rating_score for r in rows]
    # Normalise 1-5 scale to 0-1
    return (sum(scores) / len(scores) - 1) / 4


def recommend_attractions(
    user_profile: dict,
    attractions: list,
    db_session,
    budget_limit: float = None,
    top_n: int = 20,
) -> list:
    """
    Returns top_n ranked attractions for a user.

    user_profile dict keys: budget_type, weather_pref, interests (list), persona_label
    attractions: list of attraction dicts (from Attraction.to_dict())
    """
    if not attractions:
        return []

    # Encode user
    user_vec = encode_user(
        user_profile["budget_type"],
        user_profile["weather_pref"],
        user_profile["interests"],
    )
    user_vec_norm = normalize(user_vec)

    # Filter by budget if provided
    if budget_limit is not None:
        attractions = [a for a in attractions if (a.get("entry_cost") or 0) <= budget_limit]

    if not attractions:
        return []

    # Encode all attractions
    att_vecs = np.vstack([encode_attraction(a) for a in attractions])
    att_vecs_norm = normalize(att_vecs)

    # Cosine similarity (user vs every attraction)
    sim_scores = cosine_similarity(user_vec_norm, att_vecs_norm)[0]  # shape (n_attractions,)

    # Feedback scores
    persona = user_profile.get("persona_label", "")
    feedback_scores = np.array([
        get_feedback_score(a["attraction_id"], persona, db_session)
        for a in attractions
    ])

    # ==========================================================
    # Algorithm 2: Hybrid Recommendation
    # ==========================================================

    hybrid_scores = (
        0.7 * sim_scores
        + 0.3 * feedback_scores
    )

    # ==========================================================
    # Algorithm 3: Multi-Criteria Ranking
    # ==========================================================

    ratings = np.array(
        [a.get("rating") or 0 for a in attractions]
    ).reshape(-1, 1)

    pops = np.array(
        [a.get("popularity_score") or 0 for a in attractions]
    ).reshape(-1, 1)

    hybrid_norm = MinMaxScaler().fit_transform(
        hybrid_scores.reshape(-1, 1)
    ).flatten()

    ratings_norm = (
        MinMaxScaler().fit_transform(ratings).flatten()
        if ratings.max() > 0
        else ratings.flatten()
    )

    pops_norm = (
        MinMaxScaler().fit_transform(pops).flatten()
        if pops.max() > 0
        else pops.flatten()
    )

    final_scores = (
        0.5 * hybrid_norm
        + 0.2 * ratings_norm
        + 0.1 * pops_norm
        + 0.2 * feedback_scores
    )

    # Sort descending
    ranked_indices = np.argsort(final_scores)[::-1][:top_n]

    result = []
    for idx in ranked_indices:
        rec = dict(attractions[idx])
        rec["recommendation_score"] = round(float(final_scores[idx]), 4)
        rec["similarity_score"] = round(float(sim_scores[idx]), 4)
        rec["feedback_score"] = round(float(feedback_scores[idx]), 4)
        result.append(rec)

    return result
