"""
User Profiling Module — Module 1 (Chapter 4, Algorithm 1)

Assigns a travel persona to a new user using K-Means clustering on
their onboarding responses (budget_type, weather_pref, interests).

Encoding scheme matches the feature vector used in recommendation.py
so that user vectors and attraction vectors live in the same space.
"""

import os
import pickle
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

# ----------------------------------------------------------------------
# Onboarding vocabulary (fixed sets so one-hot encoding is consistent)
# ----------------------------------------------------------------------
BUDGET_OPTIONS = ["budget", "mid-range", "luxury"]
WEATHER_OPTIONS = ["warm", "cold", "moderate"]
INTEREST_OPTIONS = ["nature", "food", "history", "shopping", "adventure", "relaxation"]

# Cluster ID -> human-readable persona label.
# Adjust these labels after inspecting real cluster centroids.
PERSONA_LABELS = {
    0: "Budget Nature Explorer",
    1: "Luxury Culture Enthusiast",
    2: "Adventure Seeker",
    3: "Relaxation & Foodie",
    4: "History & Heritage Buff",
    5: "Urban Shopping Explorer",
}

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "kmeans_model.pkl")


def encode_user(budget_type: str, weather_pref: str, interests: list) -> np.ndarray:
    """
    One-hot encodes a user's onboarding answers into a fixed-length vector.
    Returns shape (1, len(BUDGET_OPTIONS) + len(WEATHER_OPTIONS) + len(INTEREST_OPTIONS)).
    """
    vec = []
    # Budget
    vec += [1 if budget_type == b else 0 for b in BUDGET_OPTIONS]
    # Weather
    vec += [1 if weather_pref == w else 0 for w in WEATHER_OPTIONS]
    # Interests (multi-select: a user can have multiple)
    vec += [1 if i in interests else 0 for i in INTEREST_OPTIONS]
    return np.array(vec, dtype=float).reshape(1, -1)


def train_model(training_data: list, n_clusters: int = 6, random_state: int = 42) -> KMeans:
    """
    Trains a K-Means model on a list of encoded user vectors (numpy arrays).
    Call this from the synthetic data generator to build the initial model.
    Saves the fitted model to MODEL_PATH.
    """
    X = np.vstack(training_data)
    X = normalize(X)

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    model.fit(X)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    return model


def load_model() -> KMeans:
    """Loads the saved K-Means model from disk."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"K-Means model not found at {MODEL_PATH}. "
            "Run scripts/generate_synthetic_data.py first to train it."
        )
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def assign_persona(budget_type: str, weather_pref: str, interests: list) -> str:
    """
    Main entry point: given a user's onboarding answers, returns their
    persona label (e.g. "Budget Nature Explorer").
    """
    model = load_model()
    vec = encode_user(budget_type, weather_pref, interests)
    vec_norm = normalize(vec)
    cluster_id = int(model.predict(vec_norm)[0])
    return PERSONA_LABELS.get(cluster_id, f"Traveller Type {cluster_id}")
