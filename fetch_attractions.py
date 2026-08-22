import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()


GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NEARBY_URL  = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

# Search these types separately so we get diverse category coverage.
# Google only accepts one `type` per Nearby Search call.
SEARCH_TYPES = [
    "tourist_attraction",
    "museum",
    "park",
    "restaurant",
    "shopping_mall",
    "amusement_park",
    "spa",
    "art_gallery",
    "zoo",
    "aquarium",
    "night_club",
    "movie_theater",
    "casino",
    "bowling_alley",
    "campground",
    "hindu_temple",
    "market",
]

# Priority order: first match in a place's types list wins.
TYPE_TO_CATEGORY = [
    ("museum",           "history"),
    ("art_gallery",      "history"),
    ("church",           "history"),
    ("mosque",           "history"),
    ("hindu_temple",     "history"),
    ("synagogue",        "history"),
    ("place_of_worship", "history"),
    ("cemetery",         "history"),
    ("city_hall",        "history"),
    ("courthouse",       "history"),
    ("zoo",              "nature"),
    ("aquarium",         "nature"),
    ("park",             "nature"),
    ("natural_feature",  "nature"),
    ("campground",       "nature"),
    ("restaurant",       "food"),
    ("cafe",             "food"),
    ("bakery",           "food"),
    ("bar",              "food"),
    ("food",             "food"),
    ("shopping_mall",    "shopping"),
    ("store",            "shopping"),
    ("market",           "shopping"),
    ("amusement_park",   "adventure"),
    ("stadium",          "adventure"),
    ("bowling_alley",    "adventure"),
    ("night_club",       "adventure"),
    ("movie_theater",    "adventure"),
    ("casino",           "adventure"),
    ("spa",              "relaxation"),
    ("beauty_salon",     "relaxation"),
    ("tourist_attraction","history"),   # fallback for generic landmarks
]

# Google price_level (0–4) → estimated entry cost in USD.
# Real relative indicator, not exact pricing.
PRICE_LEVEL_TO_COST = {0: 0.0, 1: 5.0, 2: 15.0, 3: 30.0, 4: 50.0}

# Types we never want in ATTRACTIONS (noise).
EXCLUDED_TYPES = {
    "lodging", "hotel", "motel",
    "hospital", "doctor", "dentist", "pharmacy",
    "school", "university", "library",
    "bank", "atm", "finance",
    "gas_station", "car_repair", "car_wash",
    "police", "fire_station", "post_office",
    "real_estate_agency", "insurance_agency",
    "laundry", "electrician", "plumber",
    "moving_company", "storage",
}



# Converts a city name into coordinates and canonical location information.
def geocode_city(city_name: str) -> dict:
    """City name → lat, lon, city (canonical), country via Google Geocoding."""
    resp = requests.get(
        GEOCODE_URL,
        params={"address": city_name, "key": GOOGLE_API_KEY, "language": "en"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"City '{city_name}' not found by Google Geocoding.")

    result = data["results"][0]
    loc = result["geometry"]["location"]

    # Extract city and country from address_components
    city = city_name
    country = ""
    for comp in result.get("address_components", []):
        types = comp.get("types", [])
        if "locality" in types or "administrative_area_level_1" in types:
            city = comp["long_name"]
        if "country" in types:
            country = comp["long_name"]

    return {"city": city, "country": country, "lat": loc["lat"], "lon": loc["lng"]}


 # Retrieves nearby places of a specified type from the Google Places API.
def nearby_search(lat: float, lon: float, place_type: str, radius_m: int = 15000) -> list:
    params = {
        "location": f"{lat},{lon}",
        "radius": radius_m,
        "type": place_type,
        "key": GOOGLE_API_KEY,
        "language": "en",
    }
    resp = requests.get(NEARBY_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Google Places API error for type '{place_type}': {status}")

    return data.get("results", [])

# Maps Google place types to the system's predefined attraction categories.
def map_google_types_to_category(types: list) -> str | None:
    type_set = set(types)
    if type_set & EXCLUDED_TYPES:
        return None
    for gtype, category in TYPE_TO_CATEGORY:
        if gtype in type_set:
            return category
    return None


 # Converts the Google review count into a popularity score from 1 to 4.
def popularity_from_ratings_count(count: int) -> int:
    """Maps raw Google review count to a 1–4 popularity_score."""
    if count >= 2000:
        return 4
    if count >= 500:
        return 3
    if count >= 100:
        return 2
    return 1

# Converts Google's price level into an estimated attraction entry cost.
def cost_from_price_level(price_level):
    if price_level is None:
        return None
    return PRICE_LEVEL_TO_COST.get(int(price_level), 5.0)


# ----------------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------------
# Fetches, categorises, and prepares attraction data for database storage.
def build_attraction_records(
    city_name: str,
    radius_m: int = 25000,
    lat: float | None = None,
    lon: float | None = None,
    country: str | None = None,
) -> list:
    if lat is None or lon is None:
        geo = geocode_city(city_name)
        lat, lon, country = geo["lat"], geo["lon"], country or geo["country"]
    else:
        country = country or ""

    seen_ids = set()
    records = []
    skipped = 0

    for place_type in SEARCH_TYPES:
        try:
            places = nearby_search(lat, lon, place_type, radius_m)
        except RuntimeError as e:
            print(f"  Warning: {e}")
            continue

        for place in places:
            place_id = place.get("place_id")
            if not place_id or place_id in seen_ids:
                continue
            seen_ids.add(place_id)

            name = place.get("name", "").strip()
            if not name:
                skipped += 1
                continue

            google_types = place.get("types", [])
            category = map_google_types_to_category(google_types)
            if category is None:
                skipped += 1
                continue

            # Real data from Google
            rating = place.get("rating")                        # float 1.0–5.0, may be None
            ratings_count = place.get("user_ratings_total", 0)  # int, real review count
            price_level = place.get("price_level")              # 0–4, may be None

            photos = place.get("photos", [])
            photo_reference = photos[0].get("photo_reference") if photos else None

            loc = place.get("geometry", {}).get("location", {})
            lat = loc.get("lat")
            lng = loc.get("lng")
            if lat is None or lng is None:
                skipped += 1
                continue

            records.append({
                "name": name,
                "city": city_name,
                "country": country,
                "category": category,
                "rating": round(float(rating), 1) if rating is not None else None,
                "entry_cost": cost_from_price_level(price_level),
                "popularity_score": popularity_from_ratings_count(ratings_count),
                "latitude": lat,
                "longitude": lng,
                "photo_reference": photo_reference,
            })

        time.sleep(0.1)  # be polite to the API between type searches

    if skipped:
        print(f"  ({skipped} records skipped for {city_name})")

    return records


if __name__ == "__main__":
    if not GOOGLE_API_KEY:
        print("ERROR: Set the GOOGLE_API_KEY environment variable first.")
        print("  Windows PowerShell: $env:GOOGLE_API_KEY='your_key_here'")
        print("  Or add GOOGLE_API_KEY=your_key to your .env file")
        exit(1)

    test_cities = ["Paris", "Tokyo", "Cape Town"]
    for city in test_cities:
        print(f"\n=== {city} ===")
        try:
            results = build_attraction_records(city)
            print(f"Fetched {len(results)} usable attractions.")
            for r in results[:5]:
                print(
                    f"  - {r['name']} | {r['category']} | "
                    f"rating={r['rating']} | cost=${r['entry_cost']} | "
                    f"pop={r['popularity_score']}"
                )
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(1)
