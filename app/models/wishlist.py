from datetime import datetime
from .db import db

# Stores attractions saved by users for future reference.
class Wishlist(db.Model):
    __tablename__ = "wishlists"

    wishlist_id  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    attraction_id = db.Column(db.Integer, db.ForeignKey("attractions.attraction_id"), nullable=False)
    added_at     = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "attraction_id", name="uq_wishlist_user_attraction"),
    )

    def to_dict(self):
        return {
            "wishlist_id":  self.wishlist_id,
            "user_id":      self.user_id,
            "attraction_id": self.attraction_id,
            "added_at":     self.added_at.isoformat() if self.added_at else None,
        }
