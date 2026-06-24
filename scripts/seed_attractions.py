"""
scripts/seed_attractions.py

Pre-populates the ATTRACTIONS table for the 6 featured destination cities so that
the app works immediately after setup — without needing to search each city first.

Two modes:
  1. REAL mode  — GOOGLE_API_KEY is set in .env → fetches live data from Google Places
  2. DEMO mode  — no API key              → inserts synthetic placeholder attractions
                                            so the UI is fully testable offline

Run this BEFORE generate_synthetic_data.py:
    python scripts/seed_attractions.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.db import db
from app.models.attraction import Attraction

FEATURED_CITIES = [
    ("Tokyo",        "Japan"),
    ("Paris",        "France"),
    ("Kuala Lumpur", "Malaysia"),
    ("Bali",         "Indonesia"),
    ("New York",     "United States"),
    ("Rome",         "Italy"),
    ("Bangkok",      "Thailand"),
    ("London",       "United Kingdom"),
    ("Osaka",        "Japan"),
    ("Sydney",       "Australia"),
]

# ── Synthetic fallback attractions (used when no API key is available) ──────
SYNTHETIC_ATTRACTIONS = [
    # Tokyo
    ("Tokyo Tower",            "Tokyo", "Japan",         "history",     4.5, 10.0,  3,  35.6586, 139.7454),
    ("Shinjuku Gyoen",         "Tokyo", "Japan",         "nature",      4.6,  5.0,  3,  35.6851, 139.7100),
    ("Senso-ji Temple",        "Tokyo", "Japan",         "history",     4.7,  0.0,  4,  35.7148, 139.7967),
    ("Tsukiji Fish Market",    "Tokyo", "Japan",         "food",        4.3,  0.0,  3,  35.6654, 139.7707),
    ("Akihabara District",     "Tokyo", "Japan",         "shopping",    4.4,  0.0,  3,  35.7023, 139.7745),
    ("teamLab Borderless",     "Tokyo", "Japan",         "adventure",   4.6, 32.0,  4,  35.6248, 139.7830),
    ("Harajuku Takeshita St",  "Tokyo", "Japan",         "shopping",    4.1,  0.0,  3,  35.6702, 139.7026),
    ("Ueno Park",              "Tokyo", "Japan",         "nature",      4.4,  0.0,  3,  35.7148, 139.7737),
    # Paris
    ("Eiffel Tower",           "Paris", "France",        "history",     4.7, 26.0,  4,  48.8584,   2.2945),
    ("Louvre Museum",          "Paris", "France",        "history",     4.7, 17.0,  4,  48.8606,   2.3376),
    ("Notre-Dame Cathedral",   "Paris", "France",        "history",     4.7,  0.0,  4,  48.8530,   2.3499),
    ("Montmartre",             "Paris", "France",        "history",     4.5,  0.0,  3,  48.8867,   2.3431),
    ("Musée d'Orsay",          "Paris", "France",        "history",     4.8, 16.0,  4,  48.8600,   2.3266),
    ("Champs-Élysées",         "Paris", "France",        "shopping",    4.4,  0.0,  3,  48.8698,   2.3079),
    ("Seine River Cruise",     "Paris", "France",        "relaxation",  4.5, 15.0,  3,  48.8588,   2.3470),
    ("Palace of Versailles",   "Paris", "France",        "history",     4.6, 20.0,  4,  48.8049,   2.1204),
    # Kuala Lumpur
    ("Petronas Twin Towers",   "Kuala Lumpur", "Malaysia", "history",   4.6, 22.0,  4,   3.1579, 101.7119),
    ("Batu Caves",             "Kuala Lumpur", "Malaysia", "history",   4.6,  0.0,  4,   3.2379, 101.6840),
    ("Bukit Bintang",          "Kuala Lumpur", "Malaysia", "shopping",  4.3,  0.0,  3,   3.1466, 101.7138),
    ("KL Bird Park",           "Kuala Lumpur", "Malaysia", "nature",    4.5, 25.0,  3,   3.1420, 101.6866),
    ("Central Market KL",      "Kuala Lumpur", "Malaysia", "shopping",  4.1,  0.0,  2,   3.1450, 101.6954),
    ("Jalan Alor Night Market","Kuala Lumpur", "Malaysia", "food",      4.4,  0.0,  2,   3.1467, 101.7073),
    ("KLCC Park",              "Kuala Lumpur", "Malaysia", "nature",    4.5,  0.0,  3,   3.1567, 101.7121),
    ("Merdeka Square",         "Kuala Lumpur", "Malaysia", "history",   4.4,  0.0,  2,   3.1486, 101.6943),
    # Bali
    ("Tanah Lot Temple",       "Bali", "Indonesia",      "history",     4.6, 10.0,  4,  -8.6215, 115.0865),
    ("Ubud Monkey Forest",     "Bali", "Indonesia",      "nature",      4.5, 10.0,  3,  -8.5189, 115.2626),
    ("Tegallalang Rice Terrace","Bali","Indonesia",      "nature",      4.5,  0.0,  3,  -8.4320, 115.2784),
    ("Seminyak Beach",         "Bali", "Indonesia",      "relaxation",  4.4,  0.0,  3,  -8.6920, 115.1641),
    ("Uluwatu Temple",         "Bali", "Indonesia",      "history",     4.6,  5.0,  3,  -8.8291, 115.0849),
    ("Kuta Beach",             "Bali", "Indonesia",      "relaxation",  4.2,  0.0,  3,  -8.7188, 115.1686),
    ("Tirta Empul",            "Bali", "Indonesia",      "history",     4.7,  5.0,  3,  -8.4153, 115.3147),
    ("Nusa Penida",            "Bali", "Indonesia",      "adventure",   4.7, 15.0,  3,  -8.7277, 115.5444),
    # New York
    ("Central Park",           "New York", "United States", "nature",   4.8,  0.0,  4,  40.7851,  -73.9683),
    ("Times Square",           "New York", "United States", "shopping", 4.3,  0.0,  4,  40.7580,  -73.9855),
    ("Metropolitan Museum",    "New York", "United States", "history",  4.8, 25.0,  4,  40.7794,  -73.9632),
    ("Brooklyn Bridge",        "New York", "United States", "history",  4.8,  0.0,  4,  40.7061,  -73.9969),
    ("High Line Park",         "New York", "United States", "nature",   4.6,  0.0,  3,  40.7479,  -74.0048),
    ("Chelsea Market",         "New York", "United States", "food",     4.5,  0.0,  3,  40.7424,  -74.0059),
    ("Empire State Building",  "New York", "United States", "history",  4.7, 42.0,  4,  40.7484,  -73.9857),
    ("Statue of Liberty",      "New York", "United States", "history",  4.7, 24.0,  4,  40.6892,  -74.0445),
    # Bangkok
    ("Grand Palace",           "Bangkok", "Thailand",     "history",    4.5, 15.0,  4,  13.7500, 100.4913),
    ("Wat Pho Temple",         "Bangkok", "Thailand",     "history",    4.5,  4.0,  4,  13.7466, 100.4930),
    ("Chatuchak Market",       "Bangkok", "Thailand",     "shopping",   4.3,  0.0,  4,  13.7999, 100.5501),
    ("Lumphini Park",          "Bangkok", "Thailand",     "nature",     4.4,  0.0,  3,  13.7301, 100.5413),
    ("Khao San Road",          "Bangkok", "Thailand",     "food",       4.0,  0.0,  3,  13.7587, 100.4971),
    ("Asiatique Waterfront",   "Bangkok", "Thailand",     "shopping",   4.3,  0.0,  3,  13.7040, 100.5049),
    ("Wat Arun",               "Bangkok", "Thailand",     "history",    4.5,  2.0,  4,  13.7436, 100.4883),
    ("Sukhumvit Night Market", "Bangkok", "Thailand",     "food",       4.2,  0.0,  3,  13.7310, 100.5693),
    # London
    ("Tower of London",        "London", "United Kingdom","history",    4.7, 35.0,  4,  51.5081,  -0.0759),
    ("British Museum",         "London", "United Kingdom","history",    4.7,  0.0,  4,  51.5194,  -0.1269),
    ("Buckingham Palace",      "London", "United Kingdom","history",    4.6,  0.0,  4,  51.5014,  -0.1419),
    ("Hyde Park",              "London", "United Kingdom","nature",     4.7,  0.0,  4,  51.5073,  -0.1657),
    ("Tate Modern",            "London", "United Kingdom","history",    4.6,  0.0,  3,  51.5076,  -0.0994),
    ("Camden Market",          "London", "United Kingdom","shopping",   4.3,  0.0,  3,  51.5418,  -0.1477),
    ("Borough Market",         "London", "United Kingdom","food",       4.6,  0.0,  4,  51.5055,  -0.0910),
    ("Greenwich Park",         "London", "United Kingdom","nature",     4.6,  0.0,  3,  51.4777,  -0.0001),
    # Osaka
    ("Osaka Castle",           "Osaka", "Japan",          "history",    4.5,  6.0,  4,  34.6873, 135.5262),
    ("Dotonbori",              "Osaka", "Japan",          "food",       4.4,  0.0,  4,  34.6687, 135.5006),
    ("Shinsekai",              "Osaka", "Japan",          "food",       4.2,  0.0,  3,  34.6524, 135.5063),
    ("Namba Kuromon Market",   "Osaka", "Japan",          "food",       4.3,  0.0,  3,  34.6637, 135.5030),
    ("Universal Studios Japan","Osaka", "Japan",          "adventure",  4.5, 75.0,  4,  34.6654, 135.4323),
    ("Shinsaibashi",           "Osaka", "Japan",          "shopping",   4.3,  0.0,  3,  34.6731, 135.5001),
    ("Sumiyoshi Taisha",       "Osaka", "Japan",          "history",    4.5,  0.0,  3,  34.6142, 135.4929),
    ("Tempozan Ferris Wheel",  "Osaka", "Japan",          "adventure",  4.1, 13.0,  3,  34.6553, 135.4279),
    # Sydney
    ("Sydney Opera House",     "Sydney", "Australia",     "history",    4.7, 40.0,  4, -33.8568, 151.2153),
    ("Bondi Beach",            "Sydney", "Australia",     "relaxation", 4.6,  0.0,  4, -33.8915, 151.2767),
    ("Taronga Zoo",            "Sydney", "Australia",     "nature",     4.7, 50.0,  4, -33.8432, 151.2415),
    ("The Rocks",              "Sydney", "Australia",     "history",    4.4,  0.0,  3, -33.8599, 151.2090),
    ("Darling Harbour",        "Sydney", "Australia",     "food",       4.3,  0.0,  3, -33.8733, 151.1983),
    ("Blue Mountains",         "Sydney", "Australia",     "nature",     4.8, 12.0,  4, -33.7036, 150.3124),
    ("Manly Beach",            "Sydney", "Australia",     "relaxation", 4.6,  0.0,  3, -33.7969, 151.2876),
    ("Royal Botanic Garden",   "Sydney", "Australia",     "nature",     4.7,  0.0,  3, -33.8642, 151.2166),
    # Rome
    ("Colosseum",              "Rome", "Italy",           "history",    4.7, 16.0,  4,  41.8902,  12.4922),
    ("Vatican Museums",        "Rome", "Italy",           "history",    4.7, 17.0,  4,  41.9065,  12.4536),
    ("Trevi Fountain",         "Rome", "Italy",           "history",    4.7,  0.0,  4,  41.9009,  12.4833),
    ("Pantheon",               "Rome", "Italy",           "history",    4.8,  5.0,  4,  41.8986,  12.4769),
    ("Borghese Gallery",       "Rome", "Italy",           "history",    4.8, 15.0,  4,  41.9141,  12.4924),
    ("Trastevere Quarter",     "Rome", "Italy",           "food",       4.5,  0.0,  3,  41.8896,  12.4690),
    ("Campo de' Fiori",        "Rome", "Italy",           "food",       4.4,  0.0,  3,  41.8956,  12.4722),
    ("Villa Borghese",         "Rome", "Italy",           "nature",     4.6,  0.0,  3,  41.9141,  12.4924),
]


def seed_from_api(app):
    """Fetch live attractions from Google Places for all 6 featured cities."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return False

    os.environ["GOOGLE_API_KEY"] = api_key
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from fetch_attractions import build_attraction_records

    with app.app_context():
        total = 0
        for city, country in FEATURED_CITIES:
            existing = Attraction.query.filter(Attraction.city.ilike(f"%{city}%")).count()
            if existing >= 5:
                print(f"  {city}: {existing} attractions already in DB. Skipping.")
                continue

            print(f"  Fetching {city} from Google Places...", end=" ", flush=True)
            try:
                records = build_attraction_records(city_name=city)
                added = 0
                for r in records:
                    if not Attraction.query.filter_by(name=r["name"], city=r["city"]).first():
                        att = Attraction(
                            name=r["name"], city=r["city"], country=r["country"],
                            category=r["category"], rating=r["rating"],
                            entry_cost=r["entry_cost"], popularity_score=r["popularity_score"],
                            latitude=r["latitude"], longitude=r["longitude"],
                            photo_reference=r.get("photo_reference"),
                        )
                        db.session.add(att)
                        added += 1
                db.session.commit()
                print(f"{added} added.")
                total += added
            except Exception as e:
                print(f"Failed ({e})")
        print(f"\nGoogle Places seed complete. {total} new attractions added.")
    return True


def seed_synthetic(app):
    """Insert hardcoded synthetic attractions (no API key needed)."""
    with app.app_context():
        existing = Attraction.query.count()
        if existing >= len(SYNTHETIC_ATTRACTIONS):
            print(f"  Synthetic attractions already in DB ({existing} rows). Skipping.")
            return

        added = 0
        for row in SYNTHETIC_ATTRACTIONS:
            name, city, country, category, rating, cost, pop, lat, lng = row
            if not Attraction.query.filter_by(name=name, city=city).first():
                att = Attraction(
                    name=name, city=city, country=country,
                    category=category, rating=rating,
                    entry_cost=cost, popularity_score=pop,
                    latitude=lat, longitude=lng,
                    photo_reference=None,
                )
                db.session.add(att)
                added += 1

        db.session.commit()
        print(f"  Synthetic attractions added: {added}")


if __name__ == "__main__":
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key and api_key != "your_google_api_key_here":
        print("Google API key found. Fetching real attraction data...")
        seed_from_api(flask_app)
    else:
        print("No Google API key — inserting synthetic placeholder attractions...")
        seed_synthetic(flask_app)

    print("\nDone. Next: python scripts/generate_synthetic_data.py")
