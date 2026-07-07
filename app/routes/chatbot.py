"""
Chatbot route — POST /api/chat

Accepts a JSON body:
    { "user_id": int (optional), "message": str }

Returns:
    { "reply": str, "intent": str, "entities": dict, "updates_applied": bool }

Uses Groq (Llama 3) for AI responses. The rule-based NLP module runs in the
background to extract entities and update the user's profile (budget,
interests, weather preference).
"""

from flask import Blueprint, request, jsonify, current_app

from app.models.db import db
from app.models.user_profile import UserProfile
from app.modules.chatbot import process_message, BUDGET_OPTIONS, WEATHER_OPTIONS, INTEREST_OPTIONS
from app.modules.profiling import assign_persona

chatbot_bp = Blueprint("chatbot", __name__)


def _build_ai_reply(message: str, context: dict, profile) -> str | None:
    """Call Groq API (Llama 3) and return a travel-assistant reply."""
    from groq import Groq
    import os

    api_key = current_app.config.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    ctx_parts = []
    if context.get("budget_type"):
        ctx_parts.append(f"Budget: {context['budget_type']}")
    if context.get("weather_pref"):
        ctx_parts.append(f"Weather preference: {context['weather_pref']}")
    if context.get("interests"):
        ctx_parts.append(f"Interests: {', '.join(context['interests'])}")
    if profile and getattr(profile, "persona_label", None):
        ctx_parts.append(f"Travel persona: {profile.persona_label}")

    user_ctx = "\n".join(ctx_parts) if ctx_parts else "No profile set yet."

    system_prompt = (
        "You are Pengo, a friendly AI travel assistant for the Pengo Travel Planner app. "
        "You help users plan trips, suggest attractions, answer any travel questions, and refine travel preferences.\n\n"
        f"Current user profile:\n{user_ctx}\n\n"
        "Guidelines:\n"
        "- Be helpful, friendly, and concise (2-4 sentences usually)\n"
        "- Answer any travel question: destinations, food, culture, packing, weather, budgets, itineraries\n"
        "- If asked about specific places, suggest real well-known spots\n"
        "- For non-travel questions, politely redirect to travel topics\n"
        "- Do not use markdown bold (**text**), use plain text\n"
        "- Respond in the same language the user uses"
    )

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": message},
            ],
            max_tokens=512,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        current_app.logger.error(f"Groq API error: {type(e).__name__}: {e}")
        return None


@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    """POST /api/chat"""
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

    # Run rule-based NLP to extract entities and detect profile updates
    result = process_message(message, context)

    # Call Groq AI for the main reply
    ai_reply = _build_ai_reply(message, context, profile)
    if ai_reply:
        result["reply"] = ai_reply

    # Persist any preference updates extracted by the rule-based system
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
                pass

            db.session.commit()
            updates_applied = True

    return jsonify({
        "reply":           result["reply"],
        "intent":          result["intent"],
        "entities":        result["entities"],
        "updates_applied": updates_applied,
    }), 200
