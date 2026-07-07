"""
update_photos.py
Run once to fetch real Google Places photo_references for every attraction
in the database that currently has no photo.

Usage (from project root, with Flask server stopped):
    python update_photos.py
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"


def get_photo_reference(name: str, city: str) -> str | None:
    """Call Google Places 'Find Place' to get a photo_reference for name+city."""
    params = {
        "input":      f"{name} {city}",
        "inputtype":  "textquery",
        "fields":     "photos",
        "key":        GOOGLE_API_KEY,
    }
    try:
        resp = requests.get(FIND_PLACE_URL, params=params, timeout=8)
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            photos = candidates[0].get("photos", [])
            if photos:
                ref = photos[0].get("photo_reference", "")
                # DB column is TEXT — trim if somehow very long
                return ref[:2000] if ref else None
    except Exception as e:
        print(f"  ⚠  API error for '{name}': {e}")
    return None


def main():
    if not GOOGLE_API_KEY or "your_google" in GOOGLE_API_KEY:
        print("GOOGLE_API_KEY not set in .env -- aborting.")
        return

    # Import app inside main so dotenv is loaded first
    from app import create_app
    from app.models.db import db
    from app.models.attraction import Attraction

    app = create_app()
    with app.app_context():
        attractions = Attraction.query.filter(
            Attraction.photo_reference.is_(None) | (Attraction.photo_reference == "")
        ).all()

        total   = len(attractions)
        updated = 0
        failed  = 0

        print(f"\nFound {total} attractions without photos. Fetching from Google...\n")

        for i, att in enumerate(attractions, 1):
            ref = get_photo_reference(att.name, att.city or "")
            if ref:
                att.photo_reference = ref
                updated += 1
                print(f"  [{i}/{total}] OK  {att.name} ({att.city})")
            else:
                failed += 1
                print(f"  [{i}/{total}] --  {att.name} ({att.city}) - no photo found")

            # Commit every 10 rows so progress is saved even if script is interrupted
            if i % 10 == 0:
                db.session.commit()

            # Be polite to the API — 5 requests/sec max
            time.sleep(0.2)

        db.session.commit()
        print(f"\nDone -- {updated} updated, {failed} not found.\n")
        print("Restart Flask and refresh the website to see real photos.")


if __name__ == "__main__":
    main()
