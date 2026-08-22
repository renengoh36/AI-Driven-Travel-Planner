import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

 # Builds a user-attraction rating matrix from itinerary feedback data.
def build_user_item_matrix(db_session):
    from app.models.itinerary_rating import ItineraryRating
    from app.models.itinerary_item import ItineraryItem

    ratings = db_session.query(ItineraryRating).all()
    if not ratings:
        return None, {}, {}

    itin_meta = {r.itinerary_id: (r.user_id, r.rating_score) for r in ratings}
    items = (
        db_session.query(ItineraryItem)
        .filter(ItineraryItem.itinerary_id.in_(list(itin_meta.keys())))
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
        if not meta:
            continue
        uid, score = meta
        u = user_index.get(uid)
        a = att_index.get(item.attraction_id)
        if u is not None and a is not None:
            implicit = (score - 1) / 4.0  # map 1-5 → 0.0-1.0
            matrix[u, a] = max(matrix[u, a], implicit)

    return matrix, user_index, att_index

# Calculates attraction scores based on ratings from similar users.
def get_collaborative_scores(target_user_id, attraction_ids, db_session, k=10):
    neutral = {aid: 0.5 for aid in attraction_ids}

    matrix, user_index, att_index = build_user_item_matrix(db_session)
    if matrix is None:
        return neutral

    target_row = user_index.get(target_user_id)
    if target_row is None:
        return neutral

    sims = sk_cosine(matrix)[target_row].copy()
    sims[target_row] = 0.0

    top_k_idx  = np.argsort(sims)[::-1][:k]
    top_k_sims = sims[top_k_idx]
    valid = top_k_sims > 0.0
    if not valid.any():
        return neutral

    top_k_idx  = top_k_idx[valid]
    top_k_sims = top_k_sims[valid]

    result = {}
    for aid in attraction_ids:
        a_idx = att_index.get(aid)
        if a_idx is None:
            result[aid] = 0.5
            continue
        peer_scores = matrix[top_k_idx, a_idx]
        rated = peer_scores > 0.0
        if not rated.any():
            result[aid] = 0.5
            continue
        result[aid] = round(
            float(np.dot(top_k_sims[rated], peer_scores[rated])) / float(top_k_sims[rated].sum()),
            4
        )

    return result
