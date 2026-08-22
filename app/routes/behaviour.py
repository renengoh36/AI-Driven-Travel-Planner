from flask import Blueprint, request, jsonify
from app.models.db import db
from app.modules.behaviour import log_event, update_user_dynamic_interests

beh_bp = Blueprint("behaviour", __name__)

_VALID_EVENTS = {"search", "attraction_add", "itinerary_generate", "rating"}


@beh_bp.route("/behaviour/log", methods=["POST"])
# Logs a user behaviour event and updates dynamic interests after a rating.
def log_behaviour():
    data       = request.get_json(silent=True) or {}
    user_id    = data.get("user_id")
    event_type = data.get("event_type", "").strip()

    if not user_id or not event_type:
        return jsonify({"error": "user_id and event_type are required"}), 400

    if event_type not in _VALID_EVENTS:
        return jsonify({"error": f"event_type must be one of {sorted(_VALID_EVENTS)}"}), 400

    log_event(
        user_id=int(user_id),
        event_type=event_type,
        db_session=db.session,
        category=data.get("category"),
        destination=data.get("destination"),
        attraction_id=data.get("attraction_id"),
        rating_score=data.get("rating_score"),
    )

    # Re-profile immediately after a rating (highest-signal event)
    if event_type == "rating":
        update_user_dynamic_interests(int(user_id), db.session)

    return jsonify({"status": "logged"}), 200
