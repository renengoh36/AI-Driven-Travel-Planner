"""Quick smoke test for the core algorithm modules (no DB required)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.distance import haversine, nearest_neighbour_route, build_itinerary_items
from app.modules.profiling import encode_user, BUDGET_OPTIONS, INTEREST_OPTIONS

# --- Haversine ---
d = haversine(48.8566, 2.3522, 51.5074, -0.1278)
assert 338 < d < 345, f"Unexpected Paris->London distance: {d}"
print(f"PASS  haversine: Paris->London = {d:.1f} km")

# --- Nearest-neighbour route ---
atts = [
    {"attraction_id": 1, "name": "A", "latitude": 48.85, "longitude": 2.35, "entry_cost": 0, "category": "nature", "rating": 4.0, "popularity_score": 2},
    {"attraction_id": 2, "name": "B", "latitude": 48.87, "longitude": 2.33, "entry_cost": 5, "category": "food",   "rating": 4.2, "popularity_score": 3},
    {"attraction_id": 3, "name": "C", "latitude": 48.86, "longitude": 2.34, "entry_cost": 8, "category": "history","rating": 4.5, "popularity_score": 4},
    {"attraction_id": 4, "name": "D", "latitude": 48.84, "longitude": 2.36, "entry_cost": 0, "category": "nature", "rating": 3.8, "popularity_score": 1},
]
route = nearest_neighbour_route(atts)
print(f"PASS  nearest_neighbour: {[a['name'] for a in route]}")

items = build_itinerary_items(atts, travel_days=2)
assert len(items) == 4, f"Expected 4 items, got {len(items)}"
days = sorted(set(i["day_number"] for i in items))
assert days == [1, 2], f"Expected days [1,2], got {days}"
for item in items:
    print(f"      Day {item['day_number']} #{item['visit_order']}  att_id={item['attraction_id']}  {item['start_time']} -> {item['end_time']}")
print("PASS  build_itinerary_items")

# --- User encoding ---
vec = encode_user("budget", "warm", ["nature", "food"])
assert vec.shape == (1, 12), f"Unexpected vector shape: {vec.shape}"
print(f"PASS  encode_user: shape={vec.shape}  values={vec.flatten().tolist()}")

print("\nAll smoke tests passed.")
