from .db import db
import datetime as dt


class ItineraryItem(db.Model):
    __tablename__ = "itinerary_items"

    item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    itinerary_id = db.Column(db.Integer, db.ForeignKey("itineraries.itinerary_id"), nullable=False)
    attraction_id = db.Column(db.Integer, db.ForeignKey("attractions.attraction_id"), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    visit_order = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "itinerary_id": self.itinerary_id,
            "attraction_id": self.attraction_id,
            "day_number": self.day_number,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "visit_order": self.visit_order,
        }
