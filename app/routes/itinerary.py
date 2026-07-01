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

    user = db.session.get(User, user_id)
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

    # ── Behaviour: log one itinerary_generate event per attraction category ──
    try:
        from app.modules.behaviour import log_event as _log
        att_map_tmp = {a.attraction_id: a for a in attractions}
        seen_cats = set()
        for aid in attraction_ids:
            att = att_map_tmp.get(int(aid))
            if att and att.category not in seen_cats:
                seen_cats.add(att.category)
                _log(
                    user_id=int(user_id),
                    event_type="itinerary_generate",
                    db_session=db.session,
                    category=att.category,
                    destination=destination,
                    attraction_id=att.attraction_id,
                )
    except Exception:
        pass

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


@itinerary_bp.route("/my", methods=["GET"])
def get_my_itineraries():
    """GET /api/itinerary/my?user_id=X — all itineraries for a user, newest first."""
    from app.models.itinerary_rating import ItineraryRating

    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    itineraries = (
        Itinerary.query
        .filter_by(user_id=int(user_id))
        .order_by(Itinerary.created_at.desc())
        .all()
    )

    result = []
    for itin in itineraries:
        att_ids = [item.attraction_id for item in itin.items]
        attractions = Attraction.query.filter(Attraction.attraction_id.in_(att_ids)).all()
        att_map = {a.attraction_id: a.to_dict() for a in attractions}

        # Group items by day
        days = {}
        for item in sorted(itin.items, key=lambda x: (x.day_number, x.visit_order)):
            d = item.to_dict()
            d["attraction"] = att_map.get(item.attraction_id, {})
            days.setdefault(item.day_number, []).append(d)

        # Rating (if exists)
        rating_row = ItineraryRating.query.filter_by(
            itinerary_id=itin.itinerary_id, user_id=int(user_id)
        ).first()

        result.append({
            "itinerary_id": itin.itinerary_id,
            "destination":  itin.destination,
            "travel_days":  itin.travel_days,
            "created_at":   itin.created_at.isoformat() if itin.created_at else None,
            "days":         [{"day": d, "items": items} for d, items in days.items()],
            "total_attractions": len(att_ids),
            "rating": rating_row.to_dict() if rating_row else None,
        })

    return jsonify({"itineraries": result}), 200


@itinerary_bp.route("/<int:itinerary_id>", methods=["GET"])
def get_itinerary(itinerary_id):
    """GET /api/itinerary/<id> — fetch a saved itinerary with all items."""
    itinerary = db.session.get(Itinerary, itinerary_id)
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


@itinerary_bp.route("/<int:itinerary_id>/dislike-attraction", methods=["POST"])
def dislike_attraction(itinerary_id):
    """
    POST /api/itinerary/<id>/dislike-attraction
    Body: { user_id, attraction_id }

    Records the dislike, removes the attraction from the itinerary,
    finds a same-category replacement from the same city, rebuilds the
    day schedule, and returns the updated day items.
    """
    from app.models.attraction_feedback import AttractionFeedback
    from app.modules.distance import nearest_neighbour_route, assign_time_slots

    data = request.get_json(silent=True) or {}
    user_id      = data.get("user_id")
    attraction_id = data.get("attraction_id")

    if not user_id or not attraction_id:
        return jsonify({"error": "user_id and attraction_id required"}), 400

    itinerary = db.session.get(Itinerary, itinerary_id)
    if not itinerary:
        return jsonify({"error": "Itinerary not found"}), 404

    item_to_remove = ItineraryItem.query.filter_by(
        itinerary_id=itinerary_id,
        attraction_id=int(attraction_id),
    ).first()

    if not item_to_remove:
        return jsonify({"error": "Attraction not found in this itinerary"}), 404

    day_number = item_to_remove.day_number

    # Record dislike so future recommendations exclude this attraction
    db.session.add(AttractionFeedback(
        user_id=int(user_id),
        itinerary_id=itinerary_id,
        attraction_id=int(attraction_id),
    ))

    # Remove the item from the itinerary
    db.session.delete(item_to_remove)
    db.session.flush()

    # Find a replacement: same city + same category, not already in itinerary,
    # not previously disliked by this user
    disliked_att = db.session.get(Attraction, int(attraction_id))
    replacement  = None

    if disliked_att:
        existing_ids = {item.attraction_id for item in itinerary.items}
        disliked_ids = {
            f.attraction_id
            for f in AttractionFeedback.query.filter_by(user_id=int(user_id)).all()
        }
        disliked_ids.add(int(attraction_id))
        exclude_ids = existing_ids | disliked_ids

        # Try same category first, then any category in same city
        replacement = (
            Attraction.query
            .filter_by(city=disliked_att.city, category=disliked_att.category)
            .filter(Attraction.attraction_id.notin_(exclude_ids))
            .order_by(Attraction.rating.desc())
            .first()
        ) or (
            Attraction.query
            .filter_by(city=disliked_att.city)
            .filter(Attraction.attraction_id.notin_(exclude_ids))
            .order_by(Attraction.rating.desc())
            .first()
        )

    # Rebuild the day schedule with remaining items + replacement
    day_items = (
        ItineraryItem.query
        .filter_by(itinerary_id=itinerary_id, day_number=day_number)
        .order_by(ItineraryItem.visit_order)
        .all()
    )

    day_att_dicts = []
    for item in day_items:
        att = db.session.get(Attraction, item.attraction_id)
        if att:
            day_att_dicts.append(att.to_dict())

    if replacement:
        day_att_dicts.append(replacement.to_dict())

    # Delete existing day items and reinsert rebuilt schedule
    for item in day_items:
        db.session.delete(item)
    db.session.flush()

    if day_att_dicts:
        optimised = nearest_neighbour_route(day_att_dicts)
        rebuilt   = assign_time_slots(optimised, day_number=day_number)
        for r in rebuilt:
            db.session.add(ItineraryItem(
                itinerary_id=itinerary_id,
                attraction_id=r["attraction_id"],
                day_number=day_number,
                visit_order=r["visit_order"],
                start_time=r["start_time"],
                end_time=r["end_time"],
            ))

    db.session.commit()

    # Return updated day
    updated_items = (
        ItineraryItem.query
        .filter_by(itinerary_id=itinerary_id, day_number=day_number)
        .order_by(ItineraryItem.visit_order)
        .all()
    )
    att_map = {
        a.attraction_id: a.to_dict()
        for a in Attraction.query.filter(
            Attraction.attraction_id.in_([i.attraction_id for i in updated_items])
        ).all()
    }

    result = []
    for item in updated_items:
        d = item.to_dict()
        d["attraction"] = att_map.get(item.attraction_id, {})
        result.append(d)

    return jsonify({
        "message": "Attraction removed and replaced.",
        "day": day_number,
        "replaced_with": replacement.name if replacement else None,
        "items": result,
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

    itinerary = db.session.get(Itinerary, itinerary_id)
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

    # ── Behaviour: log one rating event per attraction category in this itinerary
    # and re-profile the user so the next recommendation uses updated weights ──
    try:
        from app.modules.behaviour import log_event as _log, update_user_dynamic_interests
        items_for_rating = itinerary.items
        seen_cats = set()
        for it_item in items_for_rating:
            att = db.session.get(Attraction, it_item.attraction_id)
            if att and att.category not in seen_cats:
                seen_cats.add(att.category)
                _log(
                    user_id=int(user_id),
                    event_type="rating",
                    db_session=db.session,
                    category=att.category,
                    attraction_id=att.attraction_id,
                    rating_score=int(rating_score),
                )
        # Recompute and store dynamic interest weights after rating
        update_user_dynamic_interests(int(user_id), db.session)
    except Exception:
        pass

    return jsonify({"message": "Rating saved.", "rating_id": rating.rating_id}), 201
