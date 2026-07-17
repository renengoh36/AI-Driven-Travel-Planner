from flask import Blueprint, request, jsonify
from app.models.db import db
from app.models.wishlist import Wishlist
from app.models.attraction import Attraction

wishlist_bp = Blueprint("wishlist", __name__)


@wishlist_bp.route("/wishlist", methods=["GET"])
def get_wishlist():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    items = (
        Wishlist.query
        .filter_by(user_id=int(user_id))
        .order_by(Wishlist.added_at.desc())
        .all()
    )
    result = []
    for item in items:
        att = db.session.get(Attraction, item.attraction_id)
        if att:
            d = att.to_dict()
            d["wishlist_id"] = item.wishlist_id
            d["added_at"]    = item.added_at.isoformat() if item.added_at else None
            result.append(d)

    return jsonify({"wishlist": result}), 200


@wishlist_bp.route("/wishlist/ids", methods=["GET"])
def get_wishlist_ids():
    """Lightweight endpoint — returns only the attraction_id list for a user."""
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"ids": []}), 200

    ids = [
        w.attraction_id
        for w in Wishlist.query.filter_by(user_id=int(user_id)).all()
    ]
    return jsonify({"ids": ids}), 200


@wishlist_bp.route("/wishlist", methods=["POST"])
def add_to_wishlist():
    data = request.get_json(silent=True) or {}
    user_id      = data.get("user_id")
    attraction_id = data.get("attraction_id")

    if not user_id or not attraction_id:
        return jsonify({"error": "user_id and attraction_id required"}), 400

    existing = Wishlist.query.filter_by(
        user_id=int(user_id), attraction_id=int(attraction_id)
    ).first()
    if existing:
        return jsonify({"message": "Already in wishlist", "wishlist_id": existing.wishlist_id}), 200

    item = Wishlist(user_id=int(user_id), attraction_id=int(attraction_id))
    db.session.add(item)
    db.session.commit()
    return jsonify({"message": "Added to wishlist", "wishlist_id": item.wishlist_id}), 201


@wishlist_bp.route("/wishlist/<int:attraction_id>", methods=["DELETE"])
def remove_from_wishlist(attraction_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    item = Wishlist.query.filter_by(
        user_id=int(user_id), attraction_id=attraction_id
    ).first()
    if not item:
        return jsonify({"error": "Not in wishlist"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Removed from wishlist"}), 200
