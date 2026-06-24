"""
Collaborative Filtering Module — Algorithm 4 (Chapter 4)

Implements user-user collaborative filtering on top of the existing
itinerary_ratings + itinerary_items data.

Since the system collects itinerary-level ratings (1–5) rather than
per-attraction ratings, we derive implicit attraction-level scores by
propagating each itinerary's rating to all attractions it contained:

    implicit_score(user, attraction) = (itinerary_rating − 1) / 4   ∈ [0, 1]

If a user rated the same attraction across multiple itineraries, we keep
the maximum implicit score (most favourable signal).

User-user cosine similarity is then computed on this sparse matrix.
For a target user, the top-K most similar peers vote on each attraction:

    CF_score(attraction) =
        Σ [ sim(target, peer_i) × score(peer_i, attraction) ]
        ─────────────────────────────────────────────────────
                 Σ [ sim(target, peer_i) ]        (peers who rated it)

Attractions unseen by all peers default to 0.5 (neutral / cold-start).

This score is combined with the content-based hybrid in Algorithm 4:

    final_score = 0.40 × CB_hybrid
               + 0.25 × CF_score
               + 0.20 × rating_norm
               + 0.10 × popularity_norm
               + 0.05 × feedback_norm
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine


def build_user_item_matrix(db_session):
    """
    Constructs the user × attraction implicit-rating matrix.

    Returns
    -------
    matrix           : np.ndarray shape (n_users, n_attractions)
    user_index       : dict  {user_id  → row index}
    attraction_index : dict  {attraction_id → col index}

    Returns (None, {}, {}) when no ratings data exists yet.
    """
    from app.models.itinerary_rating import ItineraryRating
    from app.models.itinerary_item import ItineraryItem
    from app.models.itinerary import Itinerary

    ratings = db_session.query(ItineraryRating).all()
    if not ratings:
        return None, {}, {}

    # itinerary_id → (user_id, rating_score)
    itin_meta = {r.itinerary_id: (r.user_id, r.rating_score) for r in ratings}

    rated_ids = list(itin_meta.keys())
    items = (
        db_session.query(ItineraryItem)
        .filter(ItineraryItem.itinerary_id.in_(rated_ids))
        .all()
    )
    if not items:
        return None, {}, {}

    user_ids = sorted({uid for uid, _ in itin_meta.values()})
    att_ids  = sorted({i.attraction_id for i in items})

    user_index = {uid: idx for idx, uid in enumerate(user_ids)}
    att_index  = {aid: idx for idx, aid in enumerate(att_ids)}

    matrix = np.zeros((len(user_ids), len(att_ids)), dtype=np.float32)

    for item in items:
        meta = itin_meta.get(item.itinerary_id)
        if meta is None:
            continue
        uid, score = meta
        u_idx = user_index.get(uid)
        a_idx = att_index.get(item.attraction_id)
        if u_idx is None or a_idx is None:
            continue
        implicit = (score - 1) / 4.0           # map 1-5 → 0.0-1.0
        matrix[u_idx, a_idx] = max(matrix[u_idx, a_idx], implicit)

    return matrix, user_index, att_index


def get_collaborative_scores(
    target_user_id: int,
    attraction_ids: list,
    db_session,
    k: int = 10,
) -> dict:
    """
    Returns collaborative filtering scores for a list of attraction IDs.

    Parameters
    ----------
    target_user_id : ID of the user receiving recommendations
    attraction_ids : list of attraction IDs to score
    db_session     : SQLAlchemy session
    k              : number of nearest peers to consider

    Returns
    -------
    dict {attraction_id: cf_score}   values in [0, 1]
    0.5 is the neutral / cold-start default.
    """
    neutral = {aid: 0.5 for aid in attraction_ids}

    matrix, user_index, att_index = build_user_item_matrix(db_session)
    if matrix is None:
        return neutral

    target_row = user_index.get(target_user_id)
    if target_row is None:
        # User has no ratings yet → pure cold start → neutral
        return neutral

    # ── User-user cosine similarity ──────────────────────────────────────
    # Shape: (n_users, n_users)
    sim_matrix = sk_cosine(matrix)
    sims = sim_matrix[target_row].copy()
    sims[target_row] = 0.0          # exclude self

    # Top-K peers with positive similarity
    top_k_idx  = np.argsort(sims)[::-1][:k]
    top_k_sims = sims[top_k_idx]
    valid       = top_k_sims > 0.0
    if not valid.any():
        return neutral

    top_k_idx  = top_k_idx[valid]
    top_k_sims = top_k_sims[valid]

    # ── Weighted average for each attraction ─────────────────────────────
    result = {}
    for aid in attraction_ids:
        a_idx = att_index.get(aid)
        if a_idx is None:
            result[aid] = 0.5       # Never seen by any rated user
            continue

        peer_scores = matrix[top_k_idx, a_idx]
        rated_mask  = peer_scores > 0.0
        if not rated_mask.any():
            result[aid] = 0.5       # No peer has encountered this attraction
            continue

        w_sum   = float(np.dot(top_k_sims[rated_mask], peer_scores[rated_mask]))
        sim_sum = float(top_k_sims[rated_mask].sum())
        result[aid] = round(w_sum / sim_sum, 4)

    return result
