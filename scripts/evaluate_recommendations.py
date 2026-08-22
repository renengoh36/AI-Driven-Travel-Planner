import argparse
import csv
import os
import random
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:  # Windows consoles default to cp1252, which chokes on city names like "İzmir"
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from app import create_app
from app.models.db import db
from app.models.attraction import Attraction
from app.modules.recommendation import recommend_attractions
from app.modules.profiling import INTEREST_OPTIONS, BUDGET_OPTIONS, WEATHER_OPTIONS, assign_persona
from app.routes.recommendations import _query_by_destination

BUDGET_RANK = {b: i for i, b in enumerate(BUDGET_OPTIONS)}  # budget=0, mid-range=1, luxury=2

# The seeded `city` column mixes real cities with regions/provinces and, in some rows,
# the country name reused as the city — neither is something a real user would type.
# Excluded here so the evaluator only tests genuine, searchable destinations.
NON_CITY_LABELS = {
    "catalonia", "maharashtra", "lazio", "california", "tuscany", "victoria",
    "new south wales", "ile-de-france", "île-de-france", "england",
    "spain", "thailand", "taiwan", "vietnam", "greece", "turkey",
    "united kingdom", "germany", "new zealand", "australia", "indonesia",
}

# Determines the budget tier corresponding to an attraction's entry cost.
def cost_tier(cost):
    """Mirrors encode_attraction()'s tiering in app/modules/recommendation.py."""
    cost = cost or 0
    if cost == 0:
        return "budget"
    if cost <= 10:
        return "mid-range"
    return "luxury"

 # Checks whether an attraction matches the user's interest and budget criteria.
def is_relevant(attraction, profile):
    category_ok = (attraction.get("category") or "").lower() in profile["interests"]
    budget_ok = BUDGET_RANK[cost_tier(attraction.get("entry_cost"))] <= BUDGET_RANK[profile["budget_type"]]
    return category_ok and budget_ok


 # Generates synthetic user profiles for recommendation evaluation.
def build_test_profiles(n, seed=42):
    rng = random.Random(seed)
    profiles = []
    for i in range(n):
        interests = rng.sample(INTEREST_OPTIONS, k=rng.randint(1, 3))
        budget_type = rng.choice(BUDGET_OPTIONS)
        weather_pref = rng.choice(WEATHER_OPTIONS)
        persona = assign_persona(budget_type, weather_pref, interests)
        profiles.append({
            "label": f"U{i + 1:02d}",
            "interests": interests,
            "budget_type": budget_type,
            "weather_pref": weather_pref,
            "persona_label": persona,
            "user_id": None,
        })
    return profiles


# Normalises city names to merge spelling and accent variations.
def _fold_key(name):
    decomposed = unicodedata.normalize("NFKD", name.strip().casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

# Identifies valid searchable cities from the attraction database.
def pick_destinations(limit=None):
    rows = db.session.query(Attraction.city, Attraction.country).all()
    counts, spelling_counts = {}, {}
    for city, country in rows:
        if not city:
            continue
        key = _fold_key(city)
        if key in NON_CITY_LABELS or key == _fold_key(country or ""):
            continue
        counts[key] = counts.get(key, 0) + 1
        spelling_counts.setdefault(key, {}).setdefault(city.strip(), 0)
        spelling_counts[key][city.strip()] += 1

    # canonical spelling per city = whichever literal form appeared most often
    canonical = {key: max(spellings, key=spellings.get) for key, spellings in spelling_counts.items()}

    ordered = sorted(counts, key=lambda k: -counts[k])
    cities = [canonical[k] for k in ordered]
    verified = [c for c in cities if _query_by_destination(c)]
    return verified[:limit] if limit else verified


# Calculates Precision, Recall, and F1 for the recommended attractions.
def precision_recall_f1(topk, pool, profile):
    relevant_in_topk = [a for a in topk if is_relevant(a, profile)]
    precision = len(relevant_in_topk) / len(topk) if topk else 0.0

    relevant_pool = [a for a in pool if is_relevant(a, profile)]
    if not relevant_pool:
        return precision, None, None, 0

    recall = len(relevant_in_topk) / len(relevant_pool)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1, len(relevant_pool)


 # Removes duplicate attractions with the same name and city.
def _dedupe(attractions_db):
    """Same dedup POST /api/recommendations applies before ranking."""
    seen, unique = set(), []
    for a in attractions_db:
        key = (a.name.strip().lower(), (a.city or "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


 # Runs the recommendation evaluation and saves the per-profile results.
def run(k=5, n_profiles=24):
    app = create_app()
    with app.app_context():
        destinations = pick_destinations(limit=None)
        if not destinations:
            print("None of the curated destinations have seeded attractions — seed data first.")
            return

        profiles = build_test_profiles(n_profiles)
        for i, p in enumerate(profiles):
            p["destination"] = destinations[i % len(destinations)]

        rows = []
        for p in profiles:
            attractions_db = _dedupe(_query_by_destination(p["destination"]))
            pool = [a.to_dict() for a in attractions_db if a.photo_reference or a.photo_url]
            if not pool:
                continue

            ranked = recommend_attractions(
                user_profile=p, attractions=pool, db_session=db.session,
                top_n=k, use_cf=False,
            )
            precision, recall, f1, relevant_pool = precision_recall_f1(ranked, pool, p)
            rows.append({
                "user": p["label"], "destination": p["destination"], "persona": p["persona_label"],
                "interests": "+".join(p["interests"]), "budget": p["budget_type"],
                f"precision@{k}": round(precision, 4),
                f"recall@{k}": None if recall is None else round(recall, 4),
                f"f1@{k}": None if f1 is None else round(f1, 4),
                "relevant_in_pool": relevant_pool, "pool_size": len(pool),
            })

        if not rows:
            print("No attractions matched any test profile's destination — nothing to evaluate.")
            return

        scored = [r for r in rows if r[f"recall@{k}"] is not None]
        skipped = [r for r in rows if r[f"recall@{k}"] is None]

        print(f"{'User':<5}{'Destination':<14}{'Persona':<28}{'Interests':<30}{'Budget':<11}"
              f"{'P@' + str(k):<8}{'R@' + str(k):<8}{'F1@' + str(k):<8}{'Pool':<6}")
        for r in rows:
            rec = "n/a" if r[f"recall@{k}"] is None else f"{r[f'recall@{k}'] * 100:.0f}%"
            f1s = "n/a" if r[f"f1@{k}"] is None else f"{r[f'f1@{k}'] * 100:.0f}%"
            print(f"{r['user']:<5}{r['destination']:<14}{r['persona']:<28}{r['interests']:<30}{r['budget']:<11}"
                  f"{r[f'precision@{k}'] * 100:>5.0f}%  {rec:<8}{f1s:<8}{r['relevant_in_pool']:<6}")

        missing = n_profiles - len(rows)
        if missing:
            print(f"\n({missing} profile(s) skipped entirely — their destination's attraction pool "
                  f"was empty after the photo-availability filter recommend_attractions() also "
                  f"applies in production.)")

        if scored:
            avg_p = sum(r[f"precision@{k}"] for r in scored) / len(scored)
            avg_r = sum(r[f"recall@{k}"] for r in scored) / len(scored)
            avg_f1 = sum(r[f"f1@{k}"] for r in scored) / len(scored)
            print(f"\nAverage Precision@{k} = {avg_p * 100:.1f}%  (n={len(scored)})")
            print(f"Average Recall@{k}    = {avg_r * 100:.1f}%")
            print(f"Average F1@{k}        = {avg_f1 * 100:.1f}%")
        if skipped:
            print(f"\n{len(skipped)} of {len(rows)} profiles had zero relevant attractions in "
                  f"their city's pool (that interest+budget combination isn't covered by the "
                  f"dataset there) — excluded from the Recall/F1 averages above, but kept in the "
                  f"CSV for transparency.")

        out_path = os.path.join(os.path.dirname(__file__), "eval_results.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved per-profile results to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=5, help="Top-K to evaluate (default 5)")
    parser.add_argument("--profiles", type=int, default=24, help="Number of test profiles (default 24)")
    args = parser.parse_args()
    run(k=args.k, n_profiles=args.profiles)
