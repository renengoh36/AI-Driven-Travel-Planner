from datetime import datetime
from .db import db


class Itinerary(db.Model):
    __tablename__ = "itineraries"

    itinerary_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    destination = db.Column(db.String(150), nullable=False)
    travel_days = db.Column(db.Integer, nullable=False)
    total_budget = db.Column(db.Float, nullable=True)
    actual_cost = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("ItineraryItem", backref="itinerary", cascade="all, delete-orphan",
                            order_by="(ItineraryItem.day_number, ItineraryItem.visit_order)")
    ratings = db.relationship("ItineraryRating", backref="itinerary", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "itinerary_id": self.itinerary_id,
            "user_id": self.user_id,
            "destination": self.destination,
            "travel_days": self.travel_days,
            "total_budget": self.total_budget,
            "actual_cost": self.actual_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
