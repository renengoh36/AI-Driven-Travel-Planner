import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from app import create_app
from app.models.db import db
from app.models.attraction import Attraction
from fetch_attractions import build_attraction_records

app = create_app()

# =========================
# DESTINATIONS TO LOAD
# =========================

CITIES = [
    "Kuala Lumpur",
    "Penang",
    "Singapore",
    "Tokyo",
    "Seoul",
    "Paris"
]


def attraction_exists(name, city):
    return Attraction.query.filter_by(
        name=name,
        city=city
    ).first() is not None


with app.app_context():
    db.create_all()

    grand_total_fetched = 0
    grand_total_inserted = 0
    grand_total_duplicates = 0

    print("\n======================================")
    print(" GOOGLE PLACES DATA IMPORT")
    print("======================================")

    for city in CITIES:

        print(f"\n📍 Processing: {city}")

        try:

            records = build_attraction_records(
                city_name=city,
                radius_m=25000
            )

            fetched_count = len(records)
            inserted_count = 0
            duplicate_count = 0

            grand_total_fetched += fetched_count

            print(f"   Fetched: {fetched_count}")

            for record in records:

                if attraction_exists(
                    record["name"],
                    record["city"]
                ):
                    duplicate_count += 1
                    continue

                attraction = Attraction(
                    name=record["name"],
                    city=record["city"],
                    country=record["country"],
                    category=record["category"],
                    rating=record["rating"],
                    entry_cost=record["entry_cost"],
                    popularity_score=record["popularity_score"],
                    latitude=record["latitude"],
                    longitude=record["longitude"],
                    photo_reference=record.get("photo_reference")
                )

                db.session.add(attraction)
                inserted_count += 1

            db.session.commit()

            grand_total_inserted += inserted_count
            grand_total_duplicates += duplicate_count

            print(f"   Inserted: {inserted_count}")
            print(f"   Duplicates Skipped: {duplicate_count}")

        except Exception as e:

            db.session.rollback()

            print(f"   ERROR: {e}")

    print("\n======================================")
    print(" IMPORT SUMMARY")
    print("======================================")

    print(f"Total Fetched:      {grand_total_fetched}")
    print(f"Total Inserted:     {grand_total_inserted}")
    print(f"Duplicates Skipped: {grand_total_duplicates}")

    total_db_records = Attraction.query.count()

    print(f"\nAttractions In Database: {total_db_records}")
    print("======================================")
