from flask import Blueprint, request, jsonify, current_app, Response, abort
import requests as http_requests
import os
import sys
import unicodedata
from app.models.db import db
from sqlalchemy import or_ as sql_or
from app.models.user import User
from app.models.attraction import Attraction
from app.modules.recommendation import recommend_attractions
from app.modules.behaviour import get_behaviour_weights, log_event

# fetch_attractions.py lives at the project root (two levels up from app/routes/,
# not three — the old sys.path.insert here pointed one level above the project
# itself and only worked by accident because `python app.py` already puts the
# project root on sys.path).
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    import fetch_attractions as _fetch_mod
    _HAS_FETCH = True
except ImportError:
    _HAS_FETCH = False

rec_bp = Blueprint("recommendations", __name__)


def _fold(s):
    """Diacritic/case-insensitive fold so 'Istanbul' and 'İstanbul' compare equal —
    catches spelling variants a plain SQL ILIKE can miss depending on DB collation."""
    decomposed = unicodedata.normalize("NFKD", (s or "").strip().casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _query_by_destination(destination):
    resolved = _COUNTRY_ALIASES.get(destination.lower(), destination)
    rows = Attraction.query.filter(
        sql_or(
            Attraction.city.ilike(f"%{destination}%"),
            Attraction.country.ilike(f"%{resolved}%"),
        )
    ).all()
    if rows:
        return rows

    # Fallback: fold every distinct city/country in the DB and compare that way.
    target = _fold(destination)
    if not target:
        return []
    distinct_cities    = {c for (c,) in db.session.query(Attraction.city).distinct()}
    distinct_countries = {c for (c,) in db.session.query(Attraction.country).distinct()}
    city_matches    = [c for c in distinct_cities if target in _fold(c)]
    country_matches = [c for c in distinct_countries if target in _fold(c)]
    if not city_matches and not country_matches:
        return []
    return Attraction.query.filter(
        sql_or(
            Attraction.city.in_(city_matches),
            Attraction.country.in_(country_matches),
        )
    ).all()


def _cache_attractions_for_city(city):
    """Live-fetch a city from Google Places when it isn't already seeded.
    Restored from git history (deleted in a prior commit without updating the
    caller) — see fetch_attractions.py for the Google Places pipeline itself."""
    if not _HAS_FETCH:
        return 0
    api_key = current_app.config.get("GOOGLE_API_KEY", "")
    if not api_key:
        return 0

    os.environ["GOOGLE_API_KEY"] = api_key
    _fetch_mod.GOOGLE_API_KEY = api_key

    records = _fetch_mod.build_attraction_records(city_name=city, radius_m=25000)
    new_count = 0
    for r in records:
        photo_ref = r.get("photo_reference")
        if photo_ref and len(photo_ref) > 2000:
            photo_ref = photo_ref[:2000]

        exists = Attraction.query.filter_by(name=r["name"], city=r["city"]).first()
        if not exists:
            db.session.add(Attraction(
                name=r["name"], city=r["city"], country=r["country"],
                category=r["category"], rating=r["rating"],
                entry_cost=r["entry_cost"], popularity_score=r["popularity_score"],
                latitude=r["latitude"], longitude=r["longitude"],
                photo_reference=photo_ref,
            ))
            new_count += 1
        elif exists.photo_reference is None and photo_ref:
            exists.photo_reference = photo_ref
            new_count += 1

    if new_count:
        db.session.commit()
    return new_count


@rec_bp.route("/recommendations", methods=["POST"])
def get_recommendations():
    data        = request.get_json(silent=True) or {}
    user_id     = data.get("user_id")
    destination = data.get("destination", "").strip()
    budget      = data.get("budget")

    if not user_id or not destination:
        return jsonify({"error": "user_id and destination are required."}), 400

    user = User.query.get(user_id)
    if not user or not user.profile:
        return jsonify({"error": "User profile not found. Complete onboarding first."}), 404

    attractions_db = _query_by_destination(destination)

    # Deduplicate by name+city
    seen, unique_db = set(), []
    for a in attractions_db:
        key = (a.name.strip().lower(), (a.city or "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique_db.append(a)
    attractions_db = unique_db

    if not attractions_db:
        try:
            added = _cache_attractions_for_city(destination)
            if added == 0:
                return jsonify({"error": f"No attractions found for '{destination}'."}), 404
            attractions_db = _query_by_destination(destination)
        except Exception as e:
            return jsonify({"error": f"Could not fetch attractions: {str(e)}"}), 500

    try:
        log_event(user_id=int(user_id), event_type="search",
                  db_session=db.session, destination=destination)
    except Exception:
        pass

    user_profile = user.profile.to_dict()
    user_profile["user_id"] = int(user_id)
    attractions = [a.to_dict() for a in attractions_db if a.photo_reference or a.photo_url]
    bw = get_behaviour_weights(int(user_id), db.session)

    # top_n was 30 — since scoring already runs over the whole destination pool
    # regardless of top_n (the cut only affects the returned slice, not the cost),
    # a narrow cut meant a user's off-interest categories (e.g. Shopping for
    # someone who never picked it) could have zero representation in the results
    # even when the destination has plenty — the category filter then looked
    # broken. Raised so filters have the real destination inventory to work with.
    ranked = recommend_attractions(
        user_profile=user_profile, attractions=attractions,
        db_session=db.session, budget_limit=budget,
        top_n=150, behaviour_weights=bw or None, use_cf=True,
    )
    return jsonify({"destination": destination, "recommendations": ranked}), 200


@rec_bp.route("/photo", methods=["GET"])
def proxy_photo():
    ref = request.args.get("ref", "").strip()
    w   = request.args.get("w", "600")
    if not ref:
        abort(400)

    api_key = current_app.config.get("GOOGLE_API_KEY", "")
    if not api_key:
        abort(500)

    google_url = (
        f"https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={w}&photo_reference={ref}&key={api_key}"
    )
    try:
        # allow_redirects=True — Google's legacy Photo endpoint almost always
        # responds with a redirect to its CDN rather than the image directly,
        # so following it here (not just relaying the redirect to the browser)
        # is required to actually get bytes worth caching.
        resp = http_requests.get(google_url, timeout=8, allow_redirects=True)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            _cache_photo_locally(ref, resp.content, content_type)
            return Response(resp.content, content_type=content_type)
        abort(404)
    except Exception:
        abort(502)


def _cache_photo_locally(ref, content, content_type):
    """Every photo that's ever successfully shown gets permanently saved and the
    owning attraction's photo_reference swapped for the local file — so coverage
    grows on its own as real traffic hits it, instead of needing every possible
    city pre-cached (photo_reference tokens are known to expire; a local copy
    never does). Best-effort: any failure here must never break the photo response."""
    try:
        attraction = Attraction.query.filter_by(photo_reference=ref).first()
        if not attraction:
            return  # already cleared by a previous cache, or not in DB at all
        ext = ".png" if "png" in content_type else ".jpg"
        static_dir = os.path.join(current_app.root_path, "static", "images", "attraction_photos")
        os.makedirs(static_dir, exist_ok=True)
        filename = f"{attraction.attraction_id}{ext}"
        with open(os.path.join(static_dir, filename), "wb") as f:
            f.write(content)
        attraction.photo_url = f"/static/images/attraction_photos/{filename}"
        attraction.photo_reference = None
        db.session.commit()
    except Exception:
        db.session.rollback()


_COUNTRY_ALIASES = {
    "turkiye": "Turkey", "türkiye": "Turkey",
    "uae": "United Arab Emirates", "emirates": "United Arab Emirates",
    "usa": "United States", "us": "United States", "america": "United States",
    "uk": "United Kingdom", "britain": "United Kingdom", "england": "United Kingdom",
    "korea": "South Korea",
}

# The seeded `city` column mixes real cities with regions/provinces and, in some
# rows, the country name reused as the city — neither belongs in a city picker.
_NON_CITY_LABELS = {
    "catalonia", "maharashtra", "lazio", "california", "tuscany", "victoria",
    "new south wales", "ile-de-france", "england",
    "spain", "thailand", "taiwan", "vietnam", "greece", "turkey",
    "united kingdom", "germany", "new zealand", "australia", "indonesia",
}


def _clean_cities(rows):
    """De-junk and de-duplicate (city, country) rows for display: drop region/
    country-as-city labels, merge spelling variants like 'İstanbul'/'Istanbul'
    (keeping whichever spelling is most common), keep the first country seen
    per city."""
    counts, spelling_counts, country_for = {}, {}, {}
    for city, country in rows:
        if not city:
            continue
        key = _fold(city)
        # city == country is normally a "no real city seeded" artifact, except
        # for genuine city-state countries where that equality is just correct.
        is_city_state = key in {"singapore"}
        if key in _NON_CITY_LABELS or (not is_city_state and key == _fold(country or "")):
            continue
        counts[key] = counts.get(key, 0) + 1
        spelling_counts.setdefault(key, {}).setdefault(city.strip(), 0)
        spelling_counts[key][city.strip()] += 1
        country_for.setdefault(key, country)

    ordered = sorted(counts, key=lambda k: -counts[k])
    out = []
    for key in ordered:
        canonical = max(spelling_counts[key], key=spelling_counts[key].get)
        out.append({"city": canonical, "country": country_for[key]})
    return out


@rec_bp.route("/cities", methods=["GET"])
def get_cities():
    country = request.args.get("country", "").strip()
    if country:
        resolved = _COUNTRY_ALIASES.get(country.lower(), country)
        rows = (
            db.session.query(Attraction.city, Attraction.country)
            .filter(Attraction.country.ilike(f"%{resolved}%"))
            .distinct().order_by(Attraction.city).all()
        )
    else:
        rows = (
            db.session.query(Attraction.city, Attraction.country)
            .distinct().order_by(Attraction.country, Attraction.city).all()
        )
    cities = sorted(_clean_cities(rows), key=lambda c: c["city"])
    return jsonify({"cities": cities}), 200


@rec_bp.route("/recommendations/persona", methods=["GET"])
def persona_recommendations():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user_id"}), 400

    user = User.query.get(user_id)
    if not user or not user.profile:
        return jsonify({"error": "User profile not found. Complete onboarding first."}), 404

    attractions_db = Attraction.query.all()
    if not attractions_db:
        return jsonify({"recommendations": []}), 200

    user_profile = user.profile.to_dict()
    user_profile["user_id"] = user_id
    attractions = [a.to_dict() for a in attractions_db if a.photo_reference or a.photo_url]
    bw = get_behaviour_weights(user_id, db.session)

    ranked = recommend_attractions(
        user_profile=user_profile, attractions=attractions,
        db_session=db.session, top_n=40,
        behaviour_weights=bw or None, use_cf=True,
    )
    return jsonify({"recommendations": ranked}), 200
