"""
Synthetic Data Generator

Generates realistic synthetic USER, USER_PROFILE, and ITINERARY_RATING rows
for training the K-Means model and seeding the feedback loop.

METHODOLOGY NOTE (for your Chapter 3 / Chapter 5 report):
  - Attraction data is REAL (sourced from OpenTripMap API via fetch_attractions.py)
  - User onboarding responses are SYNTHETICALLY GENERATED using known distributions
    that reflect plausible travel preference patterns
  - Itinerary ratings are generated with a similarity-based rule:
    higher cosine similarity between persona and attraction category → higher
    probability of a high rating, plus Gaussian noise. This is the standard
    academic approach when real user interaction data is unavailable.
  - All synthetic data is clearly labelled as such in the database (no deception).

Run this script ONCE before starting the Flask server:
    python scripts/generate_synthetic_data.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import numpy as np
import bcrypt

from app import create_app
from app.models.db import db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.itinerary import Itinerary
from app.models.itinerary_item import ItineraryItem
from app.models.itinerary_rating import ItineraryRating
from app.models.attraction import Attraction
from app.modules.profiling import encode_user, train_model, BUDGET_OPTIONS, WEATHER_OPTIONS, INTEREST_OPTIONS

random.seed(42)
np.random.seed(42)

N_USERS = 500     # synthetic users to generate
N_CLUSTERS = 6    # K-Means clusters — match PERSONA_LABELS in profiling.py


def random_interests(n_min=1, n_max=3) -> list:
    return random.sample(INTEREST_OPTIONS, k=random.randint(n_min, n_max))


def generate_users():
    """Returns list of (budget_type, weather_pref, interests) tuples."""
    # Use weighted sampling so personas are not uniformly distributed
    budget_weights = [0.4, 0.35, 0.25]   # budget > mid-range > luxury
    weather_weights = [0.45, 0.2, 0.35]  # warm > cold > moderate

    users = []
    for _ in range(N_USERS):
        budget = random.choices(BUDGET_OPTIONS, weights=budget_weights)[0]
        weather = random.choices(WEATHER_OPTIONS, weights=weather_weights)[0]
        interests = random_interests()
        users.append((budget, weather, interests))
    return users


def seed_users_and_train(app):
    """Insert synthetic users + profiles into DB, train K-Means model."""
    with app.app_context():
        # Skip if already seeded
        if User.query.filter(User.email.like("synthetic_%")).count() >= N_USERS:
            print("Synthetic users already seeded. Skipping.")
            return

        print(f"Generating {N_USERS} synthetic users...")
        user_data = generate_users()
        pw_hash = bcrypt.hashpw(b"synthetic_password", bcrypt.gensalt()).decode()
        feature_vectors = []

        for idx, (budget, weather, interests) in enumerate(user_data):
            email = f"synthetic_{idx:04d}@travelplanner.test"
            if User.query.filter_by(email=email).first():
                continue

            user = User(full_name=f"Synthetic User {idx}", email=email, password_hash=pw_hash)
            db.session.add(user)
            db.session.flush()

            profile = UserProfile(
                user_id=user.user_id,
                budget_type=budget,
                weather_pref=weather,
                interests=",".join(interests),
                persona_label=None,  # set after training
            )
            db.session.add(profile)

            vec = encode_user(budget, weather, interests)
            feature_vectors.append(vec.flatten())

        db.session.commit()
        print("Users inserted. Training K-Means model...")

        model = train_model(feature_vectors, n_clusters=N_CLUSTERS)
        print(f"K-Means trained with {N_CLUSTERS} clusters. Model saved.")

        # Back-fill persona labels for synthetic users
        from app.modules.profiling import load_model, PERSONA_LABELS, normalize
        km = load_model()
        synthetic_profiles = (
            UserProfile.query
            .join(User, UserProfile.user_id == User.user_id)
            .filter(User.email.like("synthetic_%"))
            .all()
        )
        for profile in synthetic_profiles:
            vec = encode_user(profile.budget_type, profile.weather_pref, profile.interests_list())
            cluster = int(km.predict(normalize(vec))[0])
            profile.persona_label = PERSONA_LABELS.get(cluster, f"Type {cluster}")

        db.session.commit()
        print("Persona labels assigned to all synthetic users.")


def seed_ratings(app):
    """
    Creates synthetic itineraries + ratings for synthetic users.
    Uses similarity-based rule: rating ~ round(3 + 2 * sim_score + noise)
    """
    with app.app_context():
        attractions = Attraction.query.all()
        if not attractions:
            print("No attractions in DB yet. Run the Flask server once to auto-fetch, then re-run this script.")
            return

        synthetic_users = (
            User.query
            .filter(User.email.like("synthetic_%"))
            .all()
        )
        if not synthetic_users:
            print("No synthetic users found. Run seed_users_and_train first.")
            return

        if ItineraryRating.query.count() > 0:
            print("Ratings already seeded. Skipping.")
            return

        from app.modules.recommendation import encode_attraction
        from app.modules.profiling import encode_user
        from sklearn.metrics.pairwise import cosine_similarity
        from sklearn.preprocessing import normalize

        print(f"Generating synthetic ratings for {len(synthetic_users)} users...")
        att_dicts = [a.to_dict() for a in attractions]

        for user in synthetic_users:
            profile = user.profile
            if not profile:
                continue

            user_vec = normalize(encode_user(
                profile.budget_type, profile.weather_pref, profile.interests_list()
            ))

            # Each synthetic user "visits" 3–8 random attractions
            sample_atts = random.sample(att_dicts, k=min(random.randint(3, 8), len(att_dicts)))
            att_ids = [a["attraction_id"] for a in sample_atts]

            itin = Itinerary(
                user_id=user.user_id,
                destination=sample_atts[0]["city"],
                travel_days=max(1, len(sample_atts) // 3),
            )
            db.session.add(itin)
            db.session.flush()

            for order, att in enumerate(sample_atts, start=1):
                item = ItineraryItem(
                    itinerary_id=itin.itinerary_id,
                    attraction_id=att["attraction_id"],
                    day_number=1,
                    visit_order=order,
                )
                db.session.add(item)

            # Similarity-based rating with noise
            att_vecs = normalize(np.vstack([encode_attraction(a) for a in sample_atts]))
            sims = cosine_similarity(user_vec, att_vecs)[0]
            avg_sim = float(np.mean(sims))
            raw_score = 3 + 2 * avg_sim + np.random.normal(0, 0.4)
            rating_score = int(np.clip(round(raw_score), 1, 5))

            rating = ItineraryRating(
                itinerary_id=itin.itinerary_id,
                user_id=user.user_id,
                rating_score=rating_score,
                feedback_text=None,
            )
            db.session.add(rating)

        db.session.commit()
        print(f"Synthetic ratings seeded for {len(synthetic_users)} users.")


if __name__ == "__main__":
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()

    seed_users_and_train(flask_app)
    seed_ratings(flask_app)
    print("\nDone. You can now start the Flask server: python app.py")
