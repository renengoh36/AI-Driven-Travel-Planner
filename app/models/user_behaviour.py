from datetime import datetime
from .db import db

# Stores user behaviour events used to refine recommendations.
class UserBehaviour(db.Model):
    __tablename__ = "user_behaviour"

    behaviour_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    event_type   = db.Column(
        db.Enum("search", "attraction_add", "itinerary_generate", "rating"),
        nullable=False,
    )
    category     = db.Column(db.String(100), nullable=True)   # attraction category implied by event
    destination  = db.Column(db.String(100), nullable=True)   # destination string (search events)
    attraction_id = db.Column(
        db.Integer,
        db.ForeignKey("attractions.attraction_id", ondelete="SET NULL"),
        nullable=True,
    )
    event_weight  = db.Column(db.Float, nullable=False, default=1.0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "behaviour_id": self.behaviour_id,
            "user_id":      self.user_id,
            "event_type":   self.event_type,
            "category":     self.category,
            "destination":  self.destination,
            "attraction_id": self.attraction_id,
            "event_weight": self.event_weight,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }
