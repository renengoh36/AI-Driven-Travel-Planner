"""
Chatbot route — POST /api/chat

Accepts a JSON body:
    { "user_id": int (optional), "message": str }

Returns:
    { "reply": str, "intent": str, "entities": dict, "updates_applied": bool }

If user_id is provided and a profile exists, any extracted preference updates
(budget_type, weather_pref, interests) are persisted to UserProfile and the
K-Means persona is recalculated.
"""

from flask import Blueprint, request, jsonify

from app.models.db import db
from app.models.user_profile import UserProfile
from app.modules.chatbot import process_message, BUDGET_OPTIONS, WEATHER_OPTIONS, INTEREST_OPTIONS
from app.modules.profiling import assign_persona

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    """POST /api/chat — process a natural-language message and return a bot reply."""
    data    = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "message is required."}), 400

    # Build context from stored profile (if logged in)
    context: dict = {}
    profile: UserProfile | None = None

    if user_id:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile:
            context = {
                "budget_type":  profile.budget_type,
                "weather_pref": profile.weather_pref,
                "interests":    profile.interests_list(),
            }

    result = process_message(message, context)

    # Persist any preference updates back to the profile
    updates_applied = False
    if profile and result.get("updates"):
        updates = result["updates"]
        changed = False

        if "budget_type" in updates and updates["budget_type"] in BUDGET_OPTIONS:
            profile.budget_type = updates["budget_type"]
            changed = True

        if "weather_pref" in updates and updates["weather_pref"] in WEATHER_OPTIONS:
            profile.weather_pref = updates["weather_pref"]
            changed = True

        if "interests" in updates:
            valid = [i for i in updates["interests"] if i in INTEREST_OPTIONS]
            if valid:
                profile.interests = ",".join(dict.fromkeys(valid))
                changed = True

        if changed:
            try:
                profile.persona_label = assign_persona(
                    profile.budget_type,
                    profile.weather_pref,
                    profile.interests_list(),
                )
            except FileNotFoundError:
                pass  # non-critical — persona model may not be loaded

            db.session.commit()
            updates_applied = True

    return jsonify({
        "reply":           result["reply"],
        "intent":          result["intent"],
        "entities":        result["entities"],
        "updates_applied": updates_applied,
    }), 200
