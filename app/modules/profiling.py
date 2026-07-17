import os
import pickle
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

# ── Onboarding vocabulary  ──
BUDGET_OPTIONS  = ["budget", "mid-range", "luxury"]
WEATHER_OPTIONS = ["warm", "cold", "moderate"]
INTEREST_OPTIONS = ["nature", "food", "history", "shopping", "adventure", "relaxation"]

# Labels derived from inspecting cluster centres (budget×3 + weather×3 + interests×6)
# Cluster 0: mid-range, moderate/cold, top-interest=nature
# Cluster 1: budget,    warm,          top-interest=shopping/adventure
# Cluster 2: mid-range, warm,          top-interest=history/food
# Cluster 3: budget,    moderate,      top-interest=food
# Cluster 4: luxury/budget, cold,      top-interest=shopping
# Cluster 5: luxury,    warm,          top-interest=food/history
PERSONA_LABELS = {
    0: "Nature Explorer",
    1: "Budget Adventure Seeker",
    2: "Culture & History Explorer",
    3: "Relaxation & Foodie",
    4: "Urban Shopping Explorer",
    5: "Luxury Culture Enthusiast",
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
