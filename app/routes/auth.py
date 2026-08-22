import bcrypt
from flask import Blueprint, request, jsonify
from app.models.db import db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.modules.profiling import assign_persona, INTEREST_OPTIONS, BUDGET_OPTIONS, WEATHER_OPTIONS

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
  # Registers a new user account and securely stores the hashed password.
def register():
    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name", "").strip()
    email     = data.get("email", "").strip().lower()
    password  = data.get("password", "")

    if not full_name or not email or not password:
        return jsonify({"error": "full_name, email, and password are required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(full_name=full_name, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    return jsonify({"user_id": user.user_id, "message": "Registration successful."}), 201


@auth_bp.route("/login", methods=["POST"])
# Verifies user credentials and returns the user's profile information.
def login():
    data     = request.get_json(silent=True) or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({"error": "Invalid email or password."}), 401

    profile = user.profile
    return jsonify({
        "user_id":       user.user_id,
        "full_name":     user.full_name,
        "has_profile":   profile is not None,
        "persona_label": profile.persona_label if profile else None,
        "budget_type":   profile.budget_type if profile else None,
    }), 200


@auth_bp.route("/onboarding", methods=["POST"])
 # Validates onboarding preferences, assigns a persona, and saves the user profile.
def onboarding():
    data         = request.get_json(silent=True) or {}
    user_id      = data.get("user_id")
    budget_type  = str(data.get("budget_type", "")).strip().lower()
    weather_pref = str(data.get("weather_pref", "")).strip().lower()
    interests    = data.get("interests", [])

    if not user_id:
        return jsonify({"error": "user_id is required."}), 400
    if budget_type not in BUDGET_OPTIONS:
        return jsonify({"error": f"budget_type must be one of {BUDGET_OPTIONS}"}), 400
    if weather_pref not in WEATHER_OPTIONS:
        return jsonify({"error": f"weather_pref must be one of {WEATHER_OPTIONS}"}), 400
    if not isinstance(interests, list) or not interests:
        return jsonify({"error": "interests must be a non-empty list."}), 400

    interests = [str(i).strip().lower() for i in interests if str(i).strip()]
    invalid   = [i for i in interests if i not in INTEREST_OPTIONS]
    if invalid:
        return jsonify({"error": f"Invalid interests: {invalid}"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    try:
        persona = assign_persona(budget_type, weather_pref, interests)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile:
        profile.budget_type  = budget_type
        profile.weather_pref = weather_pref
        profile.interests    = ",".join(interests)
        profile.persona_label = persona
    else:
        profile = UserProfile(
            user_id=user_id, budget_type=budget_type,
            weather_pref=weather_pref, interests=",".join(interests),
            persona_label=persona,
        )
        db.session.add(profile)

    db.session.commit()
    return jsonify({"persona_label": persona, "profile": profile.to_dict()}), 200


@auth_bp.route("/<int:user_id>/profile", methods=["GET"])
 # Retrieves the user's stored profile information.
def get_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404
    return jsonify({"profile": profile.to_dict()}), 200


@auth_bp.route("/<int:user_id>/preferences", methods=["PATCH"])
# Updates user preferences and recalculates the assigned traveller persona.
def update_preferences(user_id):
    data = request.get_json(silent=True) or {}
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"error": "Profile not found. Complete onboarding first."}), 404

    changed = False

    if "budget_type" in data:
        budget_type = str(data["budget_type"]).strip().lower()
        if budget_type == "mid":
            budget_type = "mid-range"
        if budget_type not in BUDGET_OPTIONS:
            return jsonify({"error": f"budget_type must be one of {BUDGET_OPTIONS}"}), 400
        profile.budget_type = budget_type
        changed = True

    if "weather_pref" in data:
        weather_pref = str(data["weather_pref"]).strip().lower()
        if weather_pref not in WEATHER_OPTIONS:
            return jsonify({"error": f"weather_pref must be one of {WEATHER_OPTIONS}"}), 400
        profile.weather_pref = weather_pref
        changed = True

    if "interests" in data:
        interests = data["interests"]
        if not isinstance(interests, list) or not interests:
            return jsonify({"error": "interests must be a non-empty list."}), 400
        interests = [str(i).strip().lower() for i in interests if str(i).strip()]
        invalid   = [i for i in interests if i not in INTEREST_OPTIONS]
        if invalid:
            return jsonify({"error": f"Invalid interests: {invalid}"}), 400
        profile.interests = ",".join(dict.fromkeys(interests))
        changed = True

    if "add_interest" in data and data["add_interest"] in INTEREST_OPTIONS:
        current = [i for i in profile.interests.split(",") if i] if profile.interests else []
        if data["add_interest"] not in current:
            current.append(data["add_interest"])
            profile.interests = ",".join(current)
            changed = True

    if "remove_interest" in data and profile.interests:
        current = [i for i in profile.interests.split(",") if i != data["remove_interest"]]
        if current:
            profile.interests = ",".join(current)
            changed = True

    if changed:
        try:
            profile.persona_label = assign_persona(
                profile.budget_type, profile.weather_pref, profile.interests_list()
            )
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 500

    db.session.commit()
    return jsonify({"message": "Preferences updated.", "profile": profile.to_dict()}), 200
