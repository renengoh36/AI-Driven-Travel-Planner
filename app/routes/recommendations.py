from flask import Blueprint, request, jsonify, current_app, Response, abort
from app.models.db import db
from sqlalchemy import or_ as sql_or
from app.models.user import User
from app.models.attraction import Attraction
from app.modules.recommendation import recommend_attractions

import os
import fetch_attractions

rec_bp = Blueprint("recommendations", __name__)


def _query_by_destination(destination: str):
    """Search attractions by city name OR country name (case-insensitive)."""
    return Attraction.query.filter(
        sql_or(
            Attraction.city.ilike(f"%{destination}%"),
            Attraction.country.ilike(f"%{destination}%"),
        )
    ).all()


def _cache_attractions_for_city(city: str) -> int:
    api_key = current_app.config.get("GOOGLE_API_KEY", "")
    if not api_key:
        return 0

    os.environ["GOOGLE_API_KEY"] = api_key
    fetch_attractions.GOOGLE_API_KEY = api_key

    records = fetch_attractions.build_attraction_records(city_name=city, radius_m=25000)
    new_count = 0
    for r in records:
        # Truncate photo_reference as a safety net (DB column is now TEXT, but just in case)
        photo_ref = r.get("photo_reference")
        if photo_ref and len(photo_ref) > 2000:
            photo_ref = photo_ref[:2000]

        exists = Attraction.query.filter_by(name=r["name"], city=r["city"]).first()
        if not exists:
            att = Attraction(
                name=r["name"],
                city=r["city"],
                country=r["country"],
                category=r["category"],
                rating=r["rating"],
                entry_cost=r["entry_cost"],
                popularity_score=r["popularity_score"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                photo_reference=photo_ref,
            )
            db.session.add(att)
            new_count += 1
        elif exists.photo_reference is None and photo_ref:
            # Back-fill photo reference for records saved before the column fix
            exists.photo_reference = photo_ref
            new_count += 1

    if new_count:
        db.session.commit()
    return new_count


@rec_bp.route("/recommendations", methods=["POST"])
def get_recommendations():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    destination = data.get("destination", "").strip()
    budget = data.get("budget")

    if not user_id or not destination:
        return jsonify({"error": "user_id and destination are required."}), 400

    user = db.session.get(User, user_id)
    if not user or not user.profile:
        return jsonify({"error": "User profile not found. Complete onboarding first."}), 404

    attractions_db = _query_by_destination(destination)

    if not attractions_db:
        try:
            added = _cache_attractions_for_city(destination)
            if added == 0:
                return jsonify({"error": f"No attractions found for '{destination}'. Try a specific city name (e.g. 'Berlin' instead of 'Germany')."}), 404
            attractions_db = _query_by_destination(destination)
        except Exception as e:
            return jsonify({"error": f"Could not fetch attractions: {str(e)}"}), 500

    user_profile = user.profile.to_dict()
    attractions = [a.to_dict() for a in attractions_db]

    ranked = recommend_attractions(
        user_profile=user_profile,
        attractions=attractions,
        db_session=db.session,
        budget_limit=budget,
        top_n=30,
    )

    return jsonify({"destination": destination, "recommendations": ranked}), 200


@rec_bp.route("/cities", methods=["GET"])
def get_cities():
    """Return distinct (city, country) pairs available in the DB, optionally filtered by country."""
    country = request.args.get("country", "").strip()
    if country:
        rows = (
            db.session.query(Attraction.city, Attraction.country)
            .filter(Attraction.country.ilike(f"%{country}%"))
            .distinct()
            .order_by(Attraction.city)
            .all()
        )
    else:
        rows = (
            db.session.query(Attraction.city, Attraction.country)
            .distinct()
            .order_by(Attraction.country, Attraction.city)
            .all()
        )
    cities = [{"city": r[0], "country": r[1]} for r in rows]
    return jsonify({"cities": cities}), 200


@rec_bp.route("/recommendations/persona", methods=["GET"])
def persona_recommendations():
    """Return top attractions from all cities ranked by the user's persona (no city filter)."""
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user_id"}), 400

    user = db.session.get(User, user_id)
    if not user or not user.profile:
        return jsonify({"error": "User profile not found. Complete onboarding first."}), 404

    attractions_db = Attraction.query.all()
    if not attractions_db:
        return jsonify({"recommendations": []}), 200

    user_profile = user.profile.to_dict()
    attractions = [a.to_dict() for a in attractions_db]

    ranked = recommend_attractions(
        user_profile=user_profile,
        attractions=attractions,
        db_session=db.session,
        top_n=24,
    )
    return jsonify({"recommendations": ranked}), 200


@rec_bp.route("/photo")
def get_photo():
    """Server-side proxy for Google Places photos — keeps API key off the client."""
    ref = request.args.get("ref", "").strip()
    width = request.args.get("w", "800")
    if not ref:
        abort(404)

    api_key = current_app.config.get("GOOGLE_API_KEY", "")
    if not api_key:
        abort(503)

    url = (
        f"https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={width}&photoreference={ref}&key={api_key}"
    )
    try:
        import requests as req_lib
        resp = req_lib.get(url, timeout=10)
        return Response(
            resp.content,
            content_type=resp.headers.get("content-type", "image/jpeg"),
        )
    except Exception:
        abort(504)
