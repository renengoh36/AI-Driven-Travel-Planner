from .db import db

# Stores attraction information, including location, category, ratings, cost, popularity, and photos.
class Attraction(db.Model):
    __tablename__ = "attractions"

    attraction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)    # nature / food / history / shopping / adventure / relaxation
    rating = db.Column(db.Float, nullable=True)             # Google Places rating (1.0–5.0)
    entry_cost = db.Column(db.Float, nullable=True)         # Estimated from Google price_level
    popularity_score = db.Column(db.Integer, nullable=True) # Derived from Google user_ratings_total
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    photo_reference = db.Column(db.Text, nullable=True)
    photo_url = db.Column(db.String(500), nullable=True)  # manually assigned fallback image URL

    itinerary_items = db.relationship("ItineraryItem", backref="attraction")

    def to_dict(self):
        return {
            "attraction_id": self.attraction_id,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "category": self.category,
            "rating": self.rating,
            "entry_cost": self.entry_cost,
            "popularity_score": self.popularity_score,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "photo_reference": self.photo_reference,
            "photo_url": self.photo_url,
        }
