"""
refresh_photos.py
Re-fetches Google Places data for all cities that have attractions with
NULL photo_reference, updating existing rows in-place.

Run from project root:
    python refresh_photos.py
"""

import time
from app import create_app
from app.models.db import db
from app.models.attraction import Attraction
from app.routes.recommendations import _cache_attractions_for_city
from sqlalchemy import text

flask_app = create_app()

# Cities to skip — these are country/region names stored wrongly as city,
# geocoding them will give wrong results
SKIP = {"Greece", "United Kingdom", "Indonesia", "Australia", "Thailand",
        "Spain", "New Zealand", "Vietnam", "Taiwan", "Turkey", "England"}

with flask_app.app_context():
    # Get all distinct cities that have at least one attraction with no photo
    rows = db.session.execute(text("""
        SELECT DISTINCT city
        FROM attractions
        WHERE (photo_reference IS NULL OR photo_reference = '')
          AND (photo_url IS NULL OR photo_url = '')
        ORDER BY city
    """)).fetchall()

    cities = [r[0] for r in rows if r[0] and r[0] not in SKIP]
    print(f"\nFound {len(cities)} cities needing photo refresh:\n{cities}\n")

    for city in cities:
        print(f"  Refreshing: {city} ...", end=" ", flush=True)
        try:
            updated = _cache_attractions_for_city(city)
            print(f"{updated} updated")
        except Exception as e:
            print(f"FAILED — {e}")
        time.sleep(0.5)   # be polite to Google API

    print("\nDone. Restart Flask to see updated photos.")
