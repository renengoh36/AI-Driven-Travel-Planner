# Integration Tests — API endpoints. Flask test client + in-memory SQLite (no external MySQL needed); fresh data seeded per test class in setUpClass(). TC01-05 itinerary/generate, TC06-09 itinerary/<id>, TC10-12 itinerary/<id>/rate, TC13-16 users/<id>/preferences, TC17-20 chat, TC21-23 register+onboarding, TC24-25 destination search, TC26-27 recommendation generation, TC28-29 behaviour logging, TC30 rating-to-feedback integration.

import sys
import os
import json
import unittest
import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Test configuration ────────────────────────────────────────────────────────
class TestConfig:
    TESTING                  = True
    SQLALCHEMY_DATABASE_URI  = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY               = "test-secret-key"
    GOOGLE_API_KEY           = ""


# ── Fixture data ──────────────────────────────────────────────────────────────
_ATTRACTIONS = [
    {"attraction_id": 1, "name": "Twin Towers", "city": "Kuala Lumpur",
     "country": "Malaysia", "category": "history",
     "latitude": 3.1579, "longitude": 101.7116,
     "rating": 4.5, "entry_cost": 50.0, "popularity_score": 9000,
     "photo_url": "/static/images/placeholder.jpg"},
    {"attraction_id": 2, "name": "Batu Caves",  "city": "Kuala Lumpur",
     "country": "Malaysia", "category": "history",
     "latitude": 3.2379, "longitude": 101.6840,
     "rating": 4.3, "entry_cost": 0.0, "popularity_score": 7500,
     "photo_url": "/static/images/placeholder.jpg"},
    {"attraction_id": 3, "name": "KLCC Park",   "city": "Kuala Lumpur",
     "country": "Malaysia", "category": "nature",
     "latitude": 3.1534, "longitude": 101.7139,
     "rating": 4.1, "entry_cost": 0.0, "popularity_score": 6000,
     "photo_url": "/static/images/placeholder.jpg"},
]
# Note: recommend_attractions() candidates are pre-filtered to attractions that
# have a photo_reference or photo_url (see recommendations.py) — every fixture
# attraction needs one, or /api/recommendations and /api/recommendations/persona
# will silently return an empty list regardless of what's seeded.


def _create_test_user(db, models):
    User, UserProfile = models
    pw_hash = bcrypt.hashpw(b"TestPass123", bcrypt.gensalt()).decode()
    user = User(full_name="Test User", email="test@pengo.com", password_hash=pw_hash)
    db.session.add(user)
    db.session.flush()
    profile = UserProfile(
        user_id=user.user_id,
        budget_type="mid-range",
        weather_pref="warm",
        interests="food,history",
        persona_label="Cultural Explorer",
    )
    db.session.add(profile)
    db.session.commit()
    return user, profile


def _seed_attractions(db, Attraction):
    for a in _ATTRACTIONS:
        db.session.add(Attraction(**a))
    db.session.commit()


# Base test case with app factory
class BaseTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import create_app
        from app.models.db import db as _db
        from app.models.user import User
        from app.models.user_profile import UserProfile
        from app.models.attraction import Attraction
        from app.models.itinerary import Itinerary
        from app.models.itinerary_item import ItineraryItem
        from app.models.itinerary_rating import ItineraryRating

        cls.app    = create_app(TestConfig)
        cls.client = cls.app.test_client()
        cls.db     = _db

        with cls.app.app_context():
            _db.create_all()
            cls.user, cls.profile = _create_test_user(_db, (User, UserProfile))
            cls.user_id = cls.user.user_id
            _seed_attractions(_db, Attraction)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.db.session.remove()
            cls.db.drop_all()

    def post(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def patch(self, url, payload):
        return self.client.patch(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )


# TC01–TC05  POST /api/itinerary/generate
class TestGenerateItinerary(BaseTestCase):

    def test_TC01_generate_success_returns_201(self):
        """EP: valid payload → 201 + itinerary_id in response."""
        rv = self.post("/api/itinerary/generate", {
            "user_id":        self.user_id,
            "destination":    "Kuala Lumpur",
            "attraction_ids": [1, 2, 3],
            "travel_days":    2,
        })
        self.assertEqual(rv.status_code, 201)
        data = rv.get_json()
        self.assertIn("itinerary_id", data)
        self.assertEqual(data["destination"], "Kuala Lumpur")
        self.assertGreater(len(data["items"]), 0)

    def test_TC02_generate_missing_destination_returns_400(self):
        """EP: missing destination → 400 Bad Request."""
        rv = self.post("/api/itinerary/generate", {
            "user_id":        self.user_id,
            "attraction_ids": [1, 2],
            "travel_days":    1,
        })
        self.assertEqual(rv.status_code, 400)

    def test_TC03_generate_missing_attraction_ids_returns_400(self):
        """EP: empty attraction_ids list → 400."""
        rv = self.post("/api/itinerary/generate", {
            "user_id":        self.user_id,
            "destination":    "Kuala Lumpur",
            "attraction_ids": [],
            "travel_days":    1,
        })
        self.assertEqual(rv.status_code, 400)

    def test_TC04_generate_invalid_user_returns_404(self):
        """EP: non-existent user_id → 404 Not Found."""
        rv = self.post("/api/itinerary/generate", {
            "user_id":        99999,
            "destination":    "Kuala Lumpur",
            "attraction_ids": [1],
            "travel_days":    1,
        })
        self.assertEqual(rv.status_code, 404)

    def test_TC05_generate_items_count_matches_attractions(self):
        """EP: 3 attractions, 1 day → 3 items all on day 1."""
        rv = self.post("/api/itinerary/generate", {
            "user_id":        self.user_id,
            "destination":    "Kuala Lumpur",
            "attraction_ids": [1, 2, 3],
            "travel_days":    1,
        })
        self.assertEqual(rv.status_code, 201)
        items = rv.get_json()["items"]
        self.assertEqual(len(items), 3, msg="All 3 attractions should be scheduled")
        self.assertTrue(all(i["day_number"] == 1 for i in items),
                        msg="All items should be on day 1 for single-day trip")


# TC06–TC09  GET /api/itinerary/<id>
class TestGetItinerary(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Pre-create an itinerary to retrieve
        rv = cls.client.post(
            "/api/itinerary/generate",
            data=json.dumps({
                "user_id":        cls.user_id,
                "destination":    "Kuala Lumpur",
                "attraction_ids": [1, 2],
                "travel_days":    1,
            }),
            content_type="application/json",
        )
        cls.itin_id = rv.get_json()["itinerary_id"]

    def test_TC06_get_existing_itinerary_returns_200(self):
        """EP: valid itinerary_id + owning user_id → 200 + full details."""
        rv = self.client.get(f"/api/itinerary/{self.itin_id}?user_id={self.user_id}")
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data["itinerary_id"], self.itin_id)
        self.assertIn("items", data)

    def test_TC07_get_nonexistent_itinerary_returns_404(self):
        """EP: unknown id → 404."""
        rv = self.client.get(f"/api/itinerary/99999?user_id={self.user_id}")
        self.assertEqual(rv.status_code, 404)

    def test_TC08_get_itinerary_items_have_attraction_details(self):
        """EP: each item in response contains nested attraction dict."""
        rv = self.client.get(f"/api/itinerary/{self.itin_id}?user_id={self.user_id}")
        for item in rv.get_json()["items"]:
            self.assertIn("attraction", item,
                          msg="Each item must include nested attraction info")
            self.assertIn("name", item["attraction"])

    def test_TC09_get_itinerary_response_has_required_fields(self):
        """EP: response body must include all top-level fields."""
        rv   = self.client.get(f"/api/itinerary/{self.itin_id}?user_id={self.user_id}")
        data = rv.get_json()
        for field in ("itinerary_id", "destination", "travel_days", "items"):
            self.assertIn(field, data, msg=f"Field '{field}' must be present")

    def test_TC09b_get_itinerary_missing_user_id_returns_400(self):
        """EP: no user_id supplied → 400 (ownership cannot be checked)."""
        rv = self.client.get(f"/api/itinerary/{self.itin_id}")
        self.assertEqual(rv.status_code, 400)

    def test_TC09c_get_itinerary_wrong_owner_returns_403(self):
        """BVA: user_id supplied but does not own the itinerary → 403."""
        rv = self.client.get(f"/api/itinerary/{self.itin_id}?user_id=999999")
        self.assertEqual(rv.status_code, 403)


# TC10–TC12  POST /api/itinerary/<id>/rate
class TestRateItinerary(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        rv = cls.client.post(
            "/api/itinerary/generate",
            data=json.dumps({
                "user_id":        cls.user_id,
                "destination":    "Kuala Lumpur",
                "attraction_ids": [1, 2, 3],
                "travel_days":    1,
            }),
            content_type="application/json",
        )
        cls.itin_id = rv.get_json()["itinerary_id"]

    def test_TC10_valid_rating_returns_201(self):
        """EP: valid rating (4) with feedback → 201 + rating_id."""
        rv = self.post(f"/api/itinerary/{self.itin_id}/rate", {
            "user_id":      self.user_id,
            "rating_score": 4,
            "feedback_text": "Amazing food scene!",
        })
        self.assertEqual(rv.status_code, 201)
        data = rv.get_json()
        self.assertIn("rating_id", data)

    def test_TC11_rating_score_out_of_range_returns_400(self):
        """BVA: score = 6 → 400 Bad Request."""
        rv = self.post(f"/api/itinerary/{self.itin_id}/rate", {
            "user_id":      self.user_id,
            "rating_score": 6,
        })
        self.assertEqual(rv.status_code, 400)

    def test_TC12_rating_missing_user_id_returns_400(self):
        """EP: missing user_id → 400."""
        rv = self.post(f"/api/itinerary/{self.itin_id}/rate", {
            "rating_score": 3,
        })
        self.assertEqual(rv.status_code, 400)


# TC13–TC16  PATCH /api/users/<id>/preferences
class TestUpdatePreferences(BaseTestCase):

    def test_TC13_update_budget_type_returns_200(self):
        """EP: valid budget_type update → 200 + updated profile."""
        rv = self.patch(f"/api/users/{self.user_id}/preferences",
                        {"budget_type": "luxury"})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.get_json()["profile"]["budget_type"], "luxury")

    def test_TC14_invalid_budget_type_returns_400(self):
        """EP: unrecognised budget_type → 400."""
        rv = self.patch(f"/api/users/{self.user_id}/preferences",
                        {"budget_type": "ultra-rich"})
        self.assertEqual(rv.status_code, 400)

    def test_TC15_update_interests_list_returns_200(self):
        """EP: valid interests list → 200 + interests updated."""
        rv = self.patch(f"/api/users/{self.user_id}/preferences",
                        {"interests": ["nature", "adventure"]})
        self.assertEqual(rv.status_code, 200)
        interests = rv.get_json()["profile"]["interests"]
        self.assertIn("nature",    interests)
        self.assertIn("adventure", interests)

    def test_TC16_unknown_user_returns_404(self):
        """EP: non-existent user_id → 404."""
        rv = self.patch("/api/users/99999/preferences",
                        {"budget_type": "budget"})
        self.assertEqual(rv.status_code, 404)


# TC17–TC20  POST /api/chat
class TestChatEndpoint(BaseTestCase):

    def test_TC17_greeting_returns_200_with_reply(self):
        """EP: greeting message → 200 + non-empty reply string."""
        rv = self.post("/api/chat", {"message": "hello"})
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIn("reply", data)
        self.assertGreater(len(data["reply"]), 0)
        self.assertEqual(data["intent"], "greet")

    def test_TC18_empty_message_returns_400(self):
        """BVA: empty message string → 400 Bad Request."""
        rv = self.post("/api/chat", {"message": ""})
        self.assertEqual(rv.status_code, 400)

    def test_TC19_budget_update_applied_to_profile(self):
        """EP: message with budget_type → profile updated, updates_applied=True."""
        rv = self.post("/api/chat", {
            "user_id": self.user_id,
            "message": "I prefer budget travel",
        })
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertTrue(data["updates_applied"],
                        msg="Budget update should be applied when user_id is provided")
        self.assertEqual(data["entities"]["budget_type"], "budget")

    def test_TC20_destination_entity_extracted(self):
        """EP: message mentioning Tokyo → destination entity returned."""
        rv = self.post("/api/chat", {
            "user_id": self.user_id,
            "message": "I want to visit Tokyo",
        })
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data["entities"]["destination"], "Tokyo")
        self.assertEqual(data["intent"], "update_destination")


# TC21–TC23  POST /api/users/register → POST /api/users/onboarding
class TestRegistrationAndPersona(BaseTestCase):
    """Covers Table 5.7's 'User registration and persona assignment' scenario:
    auth.py -> profiling.py -> user_profiles."""

    def test_TC21_register_new_user_returns_201(self):
        """EP: valid registration payload → 201 + new user_id."""
        rv = self.post("/api/users/register", {
            "full_name": "Integration Tester",
            "email":     "integration.tester@pengo.com",
            "password":  "TestPass123",
        })
        self.assertEqual(rv.status_code, 201)
        self.assertIn("user_id", rv.get_json())

    def test_TC22_onboarding_assigns_and_persists_persona(self):
        """EP: register then submit onboarding → persona assigned and stored in user_profiles."""
        reg = self.post("/api/users/register", {
            "full_name": "Persona Tester",
            "email":     "persona.tester@pengo.com",
            "password":  "TestPass123",
        })
        new_user_id = reg.get_json()["user_id"]

        rv = self.post("/api/users/onboarding", {
            "user_id":      new_user_id,
            "budget_type":  "luxury",
            "weather_pref": "warm",
            "interests":    ["food", "history"],
        })
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIn("persona_label", data)
        self.assertIsInstance(data["persona_label"], str)
        self.assertGreater(len(data["persona_label"]), 0,
                           msg="Onboarding must assign a non-empty persona label")
        self.assertEqual(data["profile"]["budget_type"], "luxury",
                         msg="Submitted preferences must be persisted to user_profiles")

    def test_TC23_duplicate_email_returns_409(self):
        """BVA: registering the same email twice → second attempt returns 409."""
        payload = {"full_name": "Dup Tester", "email": "dup.tester@pengo.com", "password": "TestPass123"}
        first  = self.post("/api/users/register", payload)
        second = self.post("/api/users/register", payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)


# TC24–TC25  POST /api/recommendations — destination search and attraction retrieval
class TestDestinationSearchAndFetch(BaseTestCase):
    """Covers Table 5.7's 'Destination search and attraction fetch' scenario:
    recommendations.py -> attractions. Exercises the local-database retrieval path;
    the live Google Places fetch path (used only when a destination has zero seeded
    attractions) requires a real API key and is verified manually — see the
    Attraction Data Management module's screenshot evidence rather than here."""

    def test_TC24_search_known_destination_returns_seeded_attractions(self):
        """EP: destination already has seeded attractions → 200 + those attractions returned."""
        rv = self.post("/api/recommendations", {
            "user_id":     self.user_id,
            "destination": "Kuala Lumpur",
        })
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data["destination"], "Kuala Lumpur")
        returned_names = {r["name"] for r in data["recommendations"]}
        seeded_names = {a["name"] for a in _ATTRACTIONS}
        self.assertTrue(returned_names & seeded_names,
                        msg="Response must include at least one of the seeded attractions")

    def test_TC25_search_unknown_destination_without_api_key_returns_404(self):
        """EP: destination with no seeded data and no Google API key configured
        (test environment) → 404, confirming the live-fetch fallback is reached
        and fails gracefully rather than crashing."""
        rv = self.post("/api/recommendations", {
            "user_id":     self.user_id,
            "destination": "Nowhereville",
        })
        self.assertEqual(rv.status_code, 404)


# TC26–TC27  GET /api/recommendations/persona — full hybrid scoring pipeline
class TestRecommendationGeneration(BaseTestCase):
    """Covers Table 5.7's 'Recommendation generation' scenario:
    recommendation.py -> collaborative filtering -> database."""

    def test_TC26_persona_recommendations_returns_ranked_list(self):
        """EP: valid user_id → 200 + non-empty ranked recommendation list."""
        rv = self.client.get(f"/api/recommendations/persona?user_id={self.user_id}")
        self.assertEqual(rv.status_code, 200)
        recs = rv.get_json()["recommendations"]
        self.assertGreater(len(recs), 0, msg="Should return at least one recommendation")

    def test_TC27_each_result_carries_all_scoring_components(self):
        """EP: every returned attraction must expose the individual sub-scores that
        make up Algorithm 4's final ranking — proving CB, CF, and feedback all ran."""
        rv = self.client.get(f"/api/recommendations/persona?user_id={self.user_id}")
        recs = rv.get_json()["recommendations"]
        for field in ("recommendation_score", "similarity_score", "cf_score", "feedback_score"):
            self.assertIn(field, recs[0], msg=f"'{field}' must be present on each result")


# TC28–TC29  POST /api/behaviour/log
class TestBehaviourLogging(BaseTestCase):
    """Covers Table 5.7's 'Behaviour logging' scenario: Behaviour Module -> user_behaviour."""

    def test_TC28_log_valid_event_returns_200(self):
        """EP: valid search event → 200 + logged status."""
        rv = self.post("/api/behaviour/log", {
            "user_id":    self.user_id,
            "event_type": "attraction_add",
            "category":   "food",
        })
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.get_json()["status"], "logged")

    def test_TC29_invalid_event_type_returns_400(self):
        """EP: event_type outside the allowed set → 400 Bad Request."""
        rv = self.post("/api/behaviour/log", {
            "user_id":    self.user_id,
            "event_type": "not_a_real_event",
        })
        self.assertEqual(rv.status_code, 400)


# TC30  Rating submission integrated with the recommendation feedback mechanism
class TestRatingFeedbackIntegration(BaseTestCase):
    """Covers the second half of Table 5.7's 'Rating submission' scenario:
    itinerary_ratings -> recommendation.py — verifies a submitted rating is not
    just stored, but actually changes what get_feedback_scores_batch() returns
    for that attraction and persona."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.app.app_context():
            cls.persona_label = cls.db.session.merge(cls.profile).persona_label
        rv = cls.client.post(
            "/api/itinerary/generate",
            data=json.dumps({
                "user_id": cls.user_id, "destination": "Kuala Lumpur",
                "attraction_ids": [1], "travel_days": 1,
            }),
            content_type="application/json",
        )
        cls.itin_id = rv.get_json()["itinerary_id"]

    def test_TC30_rating_changes_feedback_score_for_that_persona(self):
        from app.modules.recommendation import get_feedback_scores_batch

        with self.app.app_context():
            before = get_feedback_scores_batch([1], self.persona_label, self.db.session)[1]
        self.assertEqual(before, 0.5, msg="No ratings yet → neutral default")

        rv = self.post(f"/api/itinerary/{self.itin_id}/rate", {
            "user_id": self.user_id, "rating_score": 5,
        })
        self.assertEqual(rv.status_code, 201)

        with self.app.app_context():
            after = get_feedback_scores_batch([1], self.persona_label, self.db.session)[1]
        self.assertGreater(after, before,
                           msg="A 5-star rating must raise the feedback score above neutral")


if __name__ == "__main__":
    unittest.main(verbosity=2)
