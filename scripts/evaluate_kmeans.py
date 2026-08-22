import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.preprocessing import normalize

from app import create_app
from app.models.user_profile import UserProfile
from app.modules.profiling import encode_user, load_model, PERSONA_LABELS

# Builds a normalised feature matrix from all stored user profiles.
def build_matrix():
    profiles = UserProfile.query.all()
    vecs = [
        encode_user(p.budget_type, p.weather_pref, p.interests_list())
        for p in profiles
    ]
    return normalize(np.vstack(vecs)), profiles

 # Evaluates the deployed K-Means model and compares cluster counts from k=2 to k=10.
def run():
    app = create_app()
    with app.app_context():
        X, profiles = build_matrix()
        n = X.shape[0]
        print(f"Evaluating against {n} user profiles from the DB.\n")

        # ── 1. Validity of the CURRENTLY DEPLOYED model (k=6) ──
        model = load_model()
        labels = model.predict(X)
        k_deployed = model.n_clusters

        sil = silhouette_score(X, labels)
        dbi = davies_bouldin_score(X, labels)
        ch = calinski_harabasz_score(X, labels)

        print(f"Deployed model: k={k_deployed}")
        print(f"  Silhouette Score      = {sil:.3f}")
        print(f"  Davies-Bouldin Index  = {dbi:.3f}")
        print(f"  Calinski-Harabasz     = {ch:.1f}")

        sizes = np.bincount(labels, minlength=k_deployed)
        print("\n  Cluster sizes (balance check):")
        for cid, size in enumerate(sizes):
            label = PERSONA_LABELS.get(cid, f"Cluster {cid}")
            print(f"    {cid} ({label:<28}) n={size:<4} ({100 * size / n:.1f}%)")

        # ── 2. Sweep k=2..10 on the SAME data to justify why k=6 ──
        print(f"\nSweep k=2..10 (throwaway fits — does not touch the deployed model):")
        print(f"  {'k':<4}{'Silhouette':<14}{'Davies-Bouldin':<18}{'Inertia':<12}")
        for k in range(2, 11):
            km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
            lbl = km.labels_
            s = silhouette_score(X, lbl)
            d = davies_bouldin_score(X, lbl)
            marker = "  <- deployed" if k == k_deployed else ""
            print(f"  {k:<4}{s:<14.3f}{d:<18.3f}{km.inertia_:<12.1f}{marker}")


if __name__ == "__main__":
    run()
