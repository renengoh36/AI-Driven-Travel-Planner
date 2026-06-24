"""
Behavioural Travel Profiling — Module 1b (Chapter 4)

Extends the static onboarding profile with signals derived from how the
user actually interacts with the system over time.

Event weight table:
    search               →  0.5  (passive intent; user looked, nothing committed)
    attraction_add       →  1.0  (explicit selection; strong preference signal)
    itinerary_generate   →  0.8  (confirmed interest; user built a trip around it)
    rating 4–5           →  1.5  (positive outcome confirmation)
    rating 3             →  0.5  (neutral)
    rating 1–2           → -0.5  (negative signal; reduce that category's weight)

Dynamic interests are stored as JSON in UserProfile.dynamic_interests:
    {"food": 0.45, "shopping": 0.30, "history": 0.15, "nature": 0.10, ...}

These are normalised category probabilities summing to 1.0. They supplement
(never replace) the static onboarding interests inside encode_user().
"""

import json
from app.modules.profiling import INTEREST_OPTIONS

# Base weight per event type
_BASE_WEIGHT = {
    "search":               0.5,
    "attraction_add":       1.0,
    "itinerary_generate":   0.8,
    "rating":               1.5,   # adjusted below for actual score
}


def log_event(
    user_id: int,
    event_type: str,
    db_session,
    category: str = None,
    destination: str = None,
    attraction_id: int = None,
    rating_score: int = None,
) -> None:
    """
    Persist a single user behaviour event.

    Parameters
    ----------
    user_id       : ID of the acting user
    event_type    : one of 'search' | 'attraction_add' | 'itinerary_generate' | 'rating'
    category      : attraction category involved (e.g. 'food', 'history')
    destination   : destination string (search events)
    attraction_id : specific attraction (attraction_add events)
    rating_score  : 1-5 (rating events only)
    """
    from app.models.user_behaviour import UserBehaviour

    weight = _BASE_WEIGHT.get(event_type, 1.0)
    if event_type == "rating" and rating_score is not None:
        if rating_score >= 4:
            weight = 1.5
        elif rating_score == 3:
            weight = 0.5
        else:
            weight = -0.5  # 1 or 2 stars → negative signal

    log = UserBehaviour(
        user_id=user_id,
        event_type=event_type,
        category=category if category in INTEREST_OPTIONS else None,
        destination=destination,
        attraction_id=attraction_id,
        event_weight=weight,
    )
    db_session.add(log)
    db_session.commit()


def compute_behaviour_weights(user_id: int, db_session) -> dict:
    """
    Aggregates all behaviour logs for a user into normalised category weights.

    Returns a dict like {"food": 0.45, "shopping": 0.30, ...}.
    Returns an empty dict when no usable behaviour is recorded yet.

    Only categories that appear in INTEREST_OPTIONS are counted.
    Negative totals are clamped to 0 before normalisation.
    """
    from app.models.user_behaviour import UserBehaviour

    logs = (
        db_session.query(UserBehaviour)
        .filter(
            UserBehaviour.user_id == user_id,
            UserBehaviour.category.isnot(None),
        )
        .all()
    )

    raw = {cat: 0.0 for cat in INTEREST_OPTIONS}
    for log in logs:
        if log.category in raw:
            raw[log.category] += log.event_weight

    clamped = {cat: max(0.0, v) for cat, v in raw.items()}
    total = sum(clamped.values())
    if total == 0:
        return {}

    return {cat: round(v / total, 4) for cat, v in clamped.items()}


def update_user_dynamic_interests(user_id: int, db_session) -> dict:
    """
    Recomputes behaviour weights and writes them to UserProfile.dynamic_interests.

    Called automatically after a 'rating' event (natural re-profiling trigger).
    The stored JSON is read by recommend_attractions() on every recommendation
    request to produce a behaviour-aware cosine similarity.
    """
    from app.models.user_profile import UserProfile

    weights = compute_behaviour_weights(user_id, db_session)
    profile = db_session.query(UserProfile).filter_by(user_id=user_id).first()
    if profile and weights:
        profile.dynamic_interests = json.dumps(weights)
        db_session.commit()
    return weights


def get_behaviour_weights(user_id: int, db_session) -> dict:
    """
    Loads the stored behaviour weights from UserProfile.dynamic_interests.
    Returns an empty dict if no behaviour data is available yet (cold-start).
    """
    from app.models.user_profile import UserProfile

    profile = db_session.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile or not profile.dynamic_interests:
        return {}
    try:
        return json.loads(profile.dynamic_interests)
    except (json.JSONDecodeError, TypeError):
        return {}
