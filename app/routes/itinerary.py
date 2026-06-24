"""
Itinerary route — POST /api/itinerary/generate

Body: { user_id, destination, attraction_ids (list), travel_days }

Runs Module 4 (Haversine + nearest-neighbour) and persists the result
as ITINERARIES + ITINERARY_ITEMS rows.
"""

from flask import Blueprint, request, jsonify
from app.models.db import db
from app.models.user import User
from app.models.attraction import Attraction
from app.models.itinerary import Itinerary
from app.models.itinerary_item import ItineraryItem
from app.modules.distance import build_itinerary_items

itinerary_bp = Blueprint("itinerary", __name__)


@itinerary_bp.route("/generate", methods=["POST"])
def generate_itinerary():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    destination = data.get("destination", "").strip()
    attraction_ids = data.get("attraction_ids", [])
    travel_days = data.get("travel_days", 1)

    if not user_id or not destination or not attraction_ids or not travel_days:
        return jsonify({
            "error": "user_id, destination, attraction_ids, and travel_days are required."
        }), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    attractions = Attraction.query.filter(Attraction.attraction_id.in_(attraction_ids)).all()
    if not attractions:
        return jsonify({"error": "No matching attractions found."}), 404

    attraction_dicts = [a.to_dict() for a in attractions]

    # Build optimised items using Module 4
    items_data = build_itinerary_items(attraction_dicts, travel_days)

    # Persist itinerary
    itinerary = Itinerary(
        user_id=user_id,
        destination=destination,
        travel_days=travel_days,
    )
    db.session.add(itinerary)
    db.session.flush()  # get itinerary_id before committing

    for item in items_data:
        row = ItineraryItem(
            itinerary_id=itinerary.itinerary_id,
            attraction_id=item["attraction_id"],
            day_number=item["day_number"],
            visit_order=item["visit_order"],
            start_time=item["start_time"],
            end_time=item["end_time"],
        )
        db.session.add(row)

    db.session.commit()

    # Return full itinerary with attraction names for readability
    att_map = {a.attraction_id: a.to_dict() for a in attractions}
    result_items = []
    for item in itinerary.items:
        d = item.to_dict()
        d["attraction"] = att_map.get(item.attraction_id, {})
        result_items.append(d)

    return jsonify({
        "itinerary_id": itinerary.itinerary_id,
        "destination": destination,
        "travel_days": travel_days,
        "items": result_items,
    }), 201


@itinerary_bp.route("/<int:itinerary_id>", methods=["GET"])
def get_itinerary(itinerary_id):
    """GET /api/itinerary/<id> — fetch a saved itinerary with all items."""
    itinerary = Itinerary.query.get(itinerary_id)
    if not itinerary:
        return jsonify({"error": "Itinerary not found."}), 404

    att_ids = [item.attraction_id for item in itinerary.items]
    attractions = Attraction.query.filter(Attraction.attraction_id.in_(att_ids)).all()
    att_map = {a.attraction_id: a.to_dict() for a in attractions}

    result_items = []
    for item in sorted(itinerary.items, key=lambda x: (x.day_number, x.visit_order)):
        d = item.to_dict()
        d["attraction"] = att_map.get(item.attraction_id, {})
        result_items.append(d)

    return jsonify({
        "itinerary_id": itinerary.itinerary_id,
        "destination": itinerary.destination,
        "travel_days": itinerary.travel_days,
        "total_budget": itinerary.total_budget,
        "actual_cost": itinerary.actual_cost,
        "created_at": itinerary.created_at.isoformat() if itinerary.created_at else None,
        "items": result_items,
    }), 200


@itinerary_bp.route("/<int:itinerary_id>/rate", methods=["POST"])
def rate_itinerary(itinerary_id):
    """POST /api/itinerary/<id>/rate — user rates a completed itinerary."""
    from app.models.itinerary_rating import ItineraryRating

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    rating_score = data.get("rating_score")
    feedback_text = data.get("feedback_text", "")

    if not user_id or rating_score is None:
        return jsonify({"error": "user_id and rating_score are required."}), 400

    if not (1 <= int(rating_score) <= 5):
        return jsonify({"error": "rating_score must be between 1 and 5."}), 400

    itinerary = Itinerary.query.get(itinerary_id)
    if not itinerary:
        return jsonify({"error": "Itinerary not found."}), 404

    rating = ItineraryRating(
        itinerary_id=itinerary_id,
        user_id=user_id,
        rating_score=int(rating_score),
        feedback_text=feedback_text or None,
    )
    db.session.add(rating)
    db.session.commit()

    return jsonify({"message": "Rating saved.", "rating_id": rating.rating_id}), 201
