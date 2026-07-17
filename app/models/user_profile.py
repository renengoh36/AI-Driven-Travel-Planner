from datetime import datetime
from .db import db


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    profile_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, unique=True)
    persona_label = db.Column(db.String(100), nullable=True)
    budget_type = db.Column(db.String(50), nullable=False)      
    weather_pref = db.Column(db.String(50), nullable=False)     
    interests = db.Column(db.Text, nullable=False)              
    dynamic_interests = db.Column(db.Text, nullable=True)       
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def interests_list(self) -> list:
        return [i.strip() for i in self.interests.split(",") if i.strip()]

    def to_dict(self):
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "persona_label": self.persona_label,
            "budget_type": self.budget_type,
            "weather_pref": self.weather_pref,
            "interests": self.interests_list(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
