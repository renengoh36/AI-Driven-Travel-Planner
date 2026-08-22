from datetime import datetime
from .db import db

# Stores user feedback linking an attraction to a generated itinerary.
class AttractionFeedback(db.Model):
    __tablename__ = "attraction_feedback"

    feedback_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    itinerary_id  = db.Column(db.Integer, db.ForeignKey("itineraries.itinerary_id"), nullable=False)
    attraction_id = db.Column(db.Integer, db.ForeignKey("attractions.attraction_id"), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "feedback_id":   self.feedback_id,
            "user_id":       self.user_id,
            "itinerary_id":  self.itinerary_id,
            "attraction_id": self.attraction_id,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }
