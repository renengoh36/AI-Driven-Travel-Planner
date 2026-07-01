"""
User Profiling Module — Module 1 (Chapter 4, Algorithm 1)

Assigns a travel persona to a new user using K-Means clustering on
their onboarding responses (budget_type, weather_pref, interests).

encode_user() is also called during recommendation (Algorithm 2) where
an optional behaviour_weights dict can be supplied to produce a
behaviour-augmented vector for cosine similarity.

IMPORTANT: persona assignment (K-Means.predict) always uses the BINARY
vector (behaviour_weights=None) because the model was trained on binary
one-hot data. Only the recommendation cosine similarity step uses the
soft-augmented vector.
"""

import os
import pickle
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

# ── Onboarding vocabulary (fixed — changing these breaks the saved model) ──
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


def encode_user(
    budget_type: str,
    weather_pref: str,
    interests: list,
    behaviour_weights: dict = None,
) -> np.ndarray:
    """
    One-hot encodes a user's profile into the shared feature space.

    Vector layout (12 dimensions):
        [0:3]  budget tier   (budget / mid-range / luxury)
        [3:6]  weather pref  (warm / cold / moderate)
        [6:12] interest flags (nature / food / history / shopping / adventure / relaxation)

    When behaviour_weights is provided (recommendation step only):
        interest dimensions are augmented with behavioural signals:

            interest_dim[i] = min(1.0, static_flag[i] + 0.5 × behaviour_weight[i])

        Explanation:
        - A statically-selected interest stays at 1.0 (already max).
        - A category the user did NOT select at onboarding but has repeatedly
          interacted with gets partially boosted toward 1.0.
        - The 0.5 scaling factor keeps the static preference dominant.

    K-Means persona assignment must call this WITHOUT behaviour_weights so
    that the binary vector matches the model's training distribution.
    """
    vec = []
    # Budget (3 dims)
    vec += [1.0 if budget_type == b else 0.0 for b in BUDGET_OPTIONS]
    # Weather (3 dims)
    vec += [1.0 if weather_pref == w else 0.0 for w in WEATHER_OPTIONS]
    # Interests (6 dims) — optionally softened with behaviour weights
    for cat in INTEREST_OPTIONS:
        base = 1.0 if cat in interests else 0.0
        if behaviour_weights:
            bw   = behaviour_weights.get(cat, 0.0)
            base = min(1.0, base + 0.5 * bw)
        vec.append(base)

    return np.array(vec, dtype=float).reshape(1, -1)


def train_model(training_data: list, n_clusters: int = 6, random_state: int = 42) -> KMeans:
    """
    Trains a K-Means model on a list of encoded user vectors (numpy arrays).
    Saves the fitted model to MODEL_PATH.
    Always call encode_user WITHOUT behaviour_weights when building training data.
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
    Given onboarding answers, returns the persona label (e.g. 'Budget Nature Explorer').
    Always uses the BINARY vector — no behaviour augmentation.
    """
    model = load_model()
    vec   = encode_user(budget_type, weather_pref, interests)   # binary, no behaviour
    vec_norm = normalize(vec)
    cluster_id = int(model.predict(vec_norm)[0])
    return PERSONA_LABELS.get(cluster_id, f"Traveller Type {cluster_id}")
