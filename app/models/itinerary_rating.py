from datetime import datetime
from .db import db


class ItineraryRating(db.Model):
    __tablename__ = "itinerary_ratings"

    rating_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    itinerary_id = db.Column(db.Integer, db.ForeignKey("itineraries.itinerary_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    rating_score = db.Column(db.Integer, nullable=False)    # 1–5: user's satisfaction with the itinerary
    feedback_text = db.Column(db.Text, nullable=True)
    rated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "rating_id": self.rating_id,
            "itinerary_id": self.itinerary_id,
            "user_id": self.user_id,
            "rating_score": self.rating_score,
            "feedback_text": self.feedback_text,
            "rated_at": self.rated_at.isoformat() if self.rated_at else None,
        }
