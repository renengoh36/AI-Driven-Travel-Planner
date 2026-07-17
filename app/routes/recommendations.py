from flask import Blueprint, request, jsonify, current_app, Response, abort, redirect
import requests as http_requests
import os
import sys
from app.models.db import db
from sqlalchemy import or_ as sql_or
from app.models.user import User
from app.models.attraction import Attraction
from app.modules.recommendation import recommend_attractions
from app.modules.behaviour import get_behaviour_weights, log_event

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import fetch_attractions

rec_bp = Blueprint("recommendations", __name__)


def _query_by_destination(destination):
    resolved = _COUNTRY_ALIASES.get(destination.lower(), destination)
    return Attraction.query.filter(
        sql_or(
            Attraction.city.ilike(f"%{destination}%"),
            Attraction.country.ilike(f"%{resolved}%"),
        )
    ).all()


def _cache_attractions_for_city(city):
    api_key = current_app.config.get("GOOGLE_API_KEY", "")
    if not api_key:
        return 0

    os.environ["GOOGLE_API_KEY"] = api_key
    fetch_attractions.GOOGLE_API_KEY = api_key

    records = fetch_attractions.build_attraction_records(city_name=city, radius_m=25000)
    new_count = 0
    for r in records:
        photo_ref = r.get("photo_reference")
        if photo_ref and len(photo_ref) > 2000:
            photo_ref = photo_ref[:2000]

        exists = Attraction.query.filter_by(name=r["name"], city=r["city"]).first()
        if not exists:
            db.session.add(Attraction(
                name=r["name"], city=r["city"], country=r["country"],
                category=r["category"], rating=r["rating"],
                entry_cost=r["entry_cost"], popularity_score=r["popularity_score"],
                latitude=r["latitude"], longitude=r["longitude"],
                photo_reference=photo_ref,
            ))
            new_count += 1
        elif exists.photo_reference is None and photo_ref:
            exists.photo_reference = photo_ref
            new_count += 1

    if new_count:
        db.session.commit()
    return new_count


@rec_bp.route("/recommendations", methods=["POST"])
def get_recommendations():
    data        = request.get_json(silent=True) or {}
    user_id     = data.get("user_id")
    destination = data.get("destination", "").strip()
    budget      = data.get("budget")

    if not user_id or not destination:
        return jsonify({"error": "user_id and destination are required."}), 400

    user = User.query.get(user_id)
    if not user or not user.profile:
        return jsonify({"error": "User profile not found. Complete onboarding first."}), 404

    attractions_db = _query_by_destination(destination)

    # Deduplicate by name+city
    seen, unique_db = set(), []
    for a in attractions_db:
        key = (a.name.strip().lower(), (a.city or "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique_db.append(a)
    attractions_db = unique_db

    if not attractions_db:
        try:
            added = _cache_attractions_for_city(destination)
            if added == 0:
                return jsonify({"error": f"No attractions found for '{destination}'."}), 404
            attractions_db = _query_by_destination(destination)
        except Exception as e:
            return jsonify({"error": f"Could not fetch attractions: {str(e)}"}), 500

    try:
        log_event(user_id=int(user_id), event_type="search",
                  db_session=db.session, destination=destination)
    except Exception:
        pass

    user_profile = user.profile.to_dict()
    user_profile["user_id"] = int(user_id)
    attractions = [a.to_dict() for a in attractions_db if a.photo_reference or a.photo_url]
    bw = get_behaviour_weights(int(user_id), db.session)

    ranked = recommend_attractions(
        user_profile=user_profile, attractions=attractions,
        db_session=db.session, budget_limit=budget,
        top_n=30, behaviour_weights=bw or None, use_cf=True,
    )
    return jsonify({"destination": destination, "recommendations": ranked}), 200


@rec_bp.route("/photo", methods=["GET"])
def proxy_photo():
    ref = request.args.get("ref", "").strip()
    w   = request.args.get("w", "600")
    if not ref:
        abort(400)

    api_key = current_app.config.get("GOOGLE_API_KEY", "")
    if not api_key:
        abort(500)

    google_url = (
        f"https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={w}&photo_reference={ref}&key={api_key}"
    )
    try:
        resp = http_requests.get(google_url, timeout=8, allow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308):
            return redirect(resp.headers["Location"])
        if resp.status_code == 200:
            return Response(resp.content, content_type=resp.headers.get("Content-Type", "image/jpeg"))
        abort(404)
    except Exception:
        abort(502)


_COUNTRY_ALIASES = {
    "turkey": "Türkiye", "turkiye": "Türkiye",
    "uae": "United Arab Emirates", "emirates": "United Arab Emirates",
    "usa": "United States", "us": "United States", "america": "United States",
    "uk": "United Kingdom", "britain": "United Kingdom", "england": "United Kingdom",
    "korea": "South Korea",
}

@rec_bp.route("/cities", methods=["GET"])
def get_cities():
    country = request.args.get("country", "").strip()
    if country:
        resolved = _COUNTRY_ALIASES.get(country.lower(), country)
        rows = (
            db.session.query(Attraction.city, Attraction.country)
            .filter(Attraction.country.ilike(f"%{resolved}%"))
            .distinct().order_by(Attraction.city).all()
        )
    else:
        rows = (
            db.session.query(Attraction.city, Attraction.country)
            .distinct().order_by(Attraction.country, Attraction.city).all()
        )
    return jsonify({"cities": [{"city": r[0], "country": r[1]} for r in rows]}), 200


@rec_bp.route("/recommendations/persona", methods=["GET"])
def persona_recommendations():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user_id"}), 400

    user = User.query.get(user_id)
    if not user or not user.profile:
        return jsonify({"error": "User profile not found. Complete onboarding first."}), 404

    attractions_db = Attraction.query.all()
    if not attractions_db:
        return jsonify({"recommendations": []}), 200

    user_profile = user.profile.to_dict()
    user_profile["user_id"] = user_id
    attractions = [a.to_dict() for a in attractions_db if a.photo_reference or a.photo_url]
    bw = get_behaviour_weights(user_id, db.session)

    ranked = recommend_attractions(
        user_profile=user_profile, attractions=attractions,
        db_session=db.session, top_n=24,
        behaviour_weights=bw or None, use_cf=True,
    )
    return jsonify({"recommendations": ranked}), 200
