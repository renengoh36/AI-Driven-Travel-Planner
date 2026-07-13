import os
import pickle
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

# ── Onboarding vocabulary  ──
BUDGET_OPTIONS  = ["budget", "mid-range", "luxury"]
WEATHER_OPTIONS = ["warm", "cold", "moderate"]
INTEREST_OPTIONS = ["nature", "food", "history", "shopping", "adventure", "relaxation"]

PERSONA_LABELS = {
    0: "Budget Nature Explorer",
    1: "Luxury Culture Enthusiast",
    2: "Adventure Seeker",
    3: "Relaxation & Foodie",
    4: "History & Heritage Buff",
    5: "Urban Shopping Explorer",
}

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "kmeans_model.pkl")


def encode_user(budget_type, weather_pref, interests, behaviour_weights=None):
    # 12-dim vector: [budget(3), weather(3), interests(6)]
    vec = [1.0 if budget_type == b else 0.0 for b in BUDGET_OPTIONS]
    vec += [1.0 if weather_pref == w else 0.0 for w in WEATHER_OPTIONS]
    for cat in INTEREST_OPTIONS:
        base = 1.0 if cat in interests else 0.0
        if behaviour_weights:
            base = min(1.0, base + 0.5 * behaviour_weights.get(cat, 0.0))
        vec.append(base)
    return np.array(vec, dtype=float).reshape(1, -1)


def train_model(training_data, n_clusters=6, random_state=42):
    X = normalize(np.vstack(training_data))
    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    model.fit(X)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    return model


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"K-Means model not found at {MODEL_PATH}.")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def assign_persona(budget_type, weather_pref, interests):
    model = load_model()
    vec = normalize(encode_user(budget_type, weather_pref, interests))
    cluster_id = int(model.predict(vec)[0])
    return PERSONA_LABELS.get(cluster_id, f"Traveller Type {cluster_id}")
