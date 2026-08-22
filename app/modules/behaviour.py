import json
from app.modules.profiling import INTEREST_OPTIONS

# Event weights: search=0.5, add=1.0, generate=0.8, rating adjusted below
_BASE_WEIGHT = {
    "search":             0.5,
    "attraction_add":     1.0,
    "itinerary_generate": 0.8,
    "rating":             1.5,
}

# Logs user interactions and assigns behaviour weights for dynamic preference learning.
def log_event(user_id, event_type, db_session, category=None,
              destination=None, attraction_id=None, rating_score=None):
    from app.models.user_behaviour import UserBehaviour

    weight = _BASE_WEIGHT.get(event_type, 1.0)
    if event_type == "rating" and rating_score is not None:
        weight = 1.5 if rating_score >= 4 else (0.5 if rating_score == 3 else -0.5)

    db_session.add(UserBehaviour(
        user_id=user_id,
        event_type=event_type,
        category=category if category in INTEREST_OPTIONS else None,
        destination=destination,
        attraction_id=attraction_id,
        event_weight=weight,
    ))
    db_session.commit()

# Calculates normalised preference weights from the user's recorded behaviour.
def compute_behaviour_weights(user_id, db_session):
    from app.models.user_behaviour import UserBehaviour

    logs = (
        db_session.query(UserBehaviour)
        .filter(UserBehaviour.user_id == user_id, UserBehaviour.category.isnot(None))
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

# Updates the user's dynamic interests based on accumulated behaviour weights.
def update_user_dynamic_interests(user_id, db_session):
    from app.models.user_profile import UserProfile

    weights = compute_behaviour_weights(user_id, db_session)
    profile = db_session.query(UserProfile).filter_by(user_id=user_id).first()
    if profile and weights:
        profile.dynamic_interests = json.dumps(weights)
        db_session.commit()
    return weights

 # Retrieves the user's stored dynamic interest weights from the profile.
def get_behaviour_weights(user_id, db_session):
    from app.models.user_profile import UserProfile

    profile = db_session.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile or not profile.dynamic_interests:
        return {}
    try:
        return json.loads(profile.dynamic_interests)
    except (json.JSONDecodeError, TypeError):
        return {}
