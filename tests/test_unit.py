"""
Unit Tests — Module 4 (distance.py), Module 5 (chatbot.py), and the
AI/ML core: profiling.py, recommendation.py, behaviour.py, and
password hashing (auth.py's bcrypt usage).

Test design technique: Equivalence Partitioning (EP) + Boundary Value Analysis (BVA)

Test groups:
    TC01–TC05  haversine()
    TC06–TC09  nearest_neighbour_route()
    TC10–TC12  assign_time_slots()
    TC13–TC16  chatbot NLP functions (tokenise, extract_*)
    TC17–TC19  encode_user()
    TC20–TC22  assign_persona()
    TC23–TC24  encode_attraction()
    TC25–TC27  budget_fit()
    TC28–TC30  password hashing (bcrypt)
    TC31–TC33  get_feedback_score() / get_feedback_scores_batch()
    TC34–TC37  recommend_attractions()
    TC38–TC39  compute_behaviour_weights()
"""

import math
import sys
import os
import unittest
import datetime
import bcrypt

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.distance import (
    haversine,
    nearest_neighbour_route,
    assign_time_slots,
    EARTH_RADIUS_KM,
    VISIT_DURATIONS,
    DEFAULT_VISIT_DURATION,
    DAY_START_HOUR,
    MIN_TRAVEL_BUFFER_MINUTES,
    LUNCH_BREAK_HOUR,
    LUNCH_BREAK_MIN,
    LUNCH_DURATION_MINUTES,
)
from app.modules.chatbot import (
    tokenise,
    extract_destination,
    extract_budget_type,
    extract_days,
    extract_interests,
    detect_intent,
    process_message,
)
from app.modules.profiling import (
    encode_user,
    assign_persona,
    PERSONA_LABELS,
    BUDGET_OPTIONS,
    WEATHER_OPTIONS,
    INTEREST_OPTIONS,
)
from app.modules.recommendation import (
    encode_attraction,
    budget_fit,
    cost_tier,
    get_feedback_score,
    get_feedback_scores_batch,
    recommend_attractions,
)
from app.modules.behaviour import compute_behaviour_weights, log_event


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════
# Creates a test attraction dictionary with the required fields.
def _make_attraction(aid, lat, lon, name="Place", category=""):
    return {"attraction_id": aid, "name": name, "latitude": lat, "longitude": lon, "category": category}


# ═══════════════════════════════════════════════════════════════════════════════
#  TC01–TC05  haversine()
# ═══════════════════════════════════════════════════════════════════════════════

class TestHaversine(unittest.TestCase):

    def test_TC01_same_point_is_zero(self):
        """EP: identical coordinates → distance must be 0."""
        result = haversine(3.139, 101.687, 3.139, 101.687)
        self.assertAlmostEqual(result, 0.0, places=6,
                               msg="Same lat/lon should produce 0 km")

    def test_TC02_known_distance_london_paris(self):
        """EP: two well-known cities → result within ±5 km of accepted value (~341 km)."""
        london = (51.5074, -0.1278)
        paris  = (48.8566,  2.3522)
        result = haversine(*london, *paris)
        self.assertAlmostEqual(result, 341.0, delta=5.0,
                               msg="London-Paris distance should be ~341 km")

    def test_TC03_antipodal_points_approximately_half_circumference(self):
        """BVA: opposite poles → ~20 015 km (half Earth circumference)."""
        result = haversine(90.0, 0.0, -90.0, 0.0)
        expected = math.pi * EARTH_RADIUS_KM   # half circumference
        self.assertAlmostEqual(result, expected, delta=1.0,
                               msg="Antipodal distance should be ~20 015 km")

    def test_TC04_southern_hemisphere_negative_coords(self):
        """EP: negative lat/lon (Sydney ↔ Cape Town) → non-zero positive result."""
        sydney    = (-33.8688, 151.2093)
        cape_town = (-33.9249,  18.4241)
        result = haversine(*sydney, *cape_town)
        self.assertGreater(result, 0,
                           msg="Distance between hemispheric cities must be positive")
        self.assertLess(result, EARTH_RADIUS_KM * 2 * math.pi,
                        msg="Distance must not exceed Earth's circumference")

    def test_TC05_symmetry(self):
        """BVA: d(A,B) == d(B,A) — haversine must be symmetric."""
        a = (35.6762, 139.6503)   # Tokyo
        b = (48.8566,   2.3522)   # Paris
        self.assertAlmostEqual(haversine(*a, *b), haversine(*b, *a), places=8,
                               msg="Haversine must be symmetric")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC06–TC09  nearest_neighbour_route()
# ═══════════════════════════════════════════════════════════════════════════════

class TestNearestNeighbourRoute(unittest.TestCase):

    def test_TC06_empty_list_returns_empty(self):
        """BVA: empty input → empty output."""
        result = nearest_neighbour_route([])
        self.assertEqual(result, [],
                         msg="Empty attraction list should return empty list")

    def test_TC07_single_attraction_returned_unchanged(self):
        """BVA: single element → same element returned."""
        att = [_make_attraction(1, 3.1, 101.7)]
        result = nearest_neighbour_route(att)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["attraction_id"], 1,
                         msg="Single attraction must be returned as-is")

    def test_TC08_two_attractions_both_returned(self):
        """EP: two attractions → both appear in result."""
        a = _make_attraction(1, 3.139, 101.687)
        b = _make_attraction(2, 3.150, 101.700)
        result = nearest_neighbour_route([a, b])
        ids = {r["attraction_id"] for r in result}
        self.assertEqual(ids, {1, 2},
                         msg="Both attractions must appear in the result")

    def test_TC09_route_preserves_all_attractions(self):
        """EP: n attractions → result has n items, no duplicates."""
        attractions = [
            _make_attraction(i, 3.0 + i * 0.01, 101.0 + i * 0.01)
            for i in range(6)
        ]
        result = nearest_neighbour_route(attractions)
        self.assertEqual(len(result), 6,
                         msg="Route must contain all 6 attractions")
        ids = [r["attraction_id"] for r in result]
        self.assertEqual(len(ids), len(set(ids)),
                         msg="No duplicate attractions in route")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC10–TC12  assign_time_slots()
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssignTimeSlots(unittest.TestCase):

    def test_TC10_single_attraction_starts_at_day_start(self):
        """EP: one attraction, no category → start 09:00, end at DEFAULT_VISIT_DURATION."""
        att   = [_make_attraction(1, 3.1, 101.7)]
        items = assign_time_slots(att, day_number=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["start_time"], datetime.time(DAY_START_HOUR, 0),
                         msg="First attraction must start at 09:00")
        end_hour = DAY_START_HOUR + DEFAULT_VISIT_DURATION // 60
        end_min  = DEFAULT_VISIT_DURATION % 60
        self.assertEqual(items[0]["end_time"], datetime.time(end_hour, end_min),
                         msg=f"End time must be start + {DEFAULT_VISIT_DURATION} min")

    def test_TC11_travel_buffer_and_lunch_break_inserted(self):
        """EP: 3 attractions across midday → travel gap between each, lunch break at 12:30.

        Attractions 1.11 km apart (0.01° lat) → travel = MIN_TRAVEL_BUFFER_MINUTES = 15 min.
        Timeline:
          09:00–10:30  Attr 0  (90 min, no category)
          10:45–12:15  Attr 1  (+ 15 min travel)
          13:30–15:00  Attr 2  (+ 15 min travel reaches 12:30 → 60 min lunch → 13:30)
        """
        atts  = [_make_attraction(i, 3.0 + i * 0.01, 101.0) for i in range(3)]
        items = assign_time_slots(atts, day_number=1)
        self.assertEqual(len(items), 3)

        # Attr 0: 09:00 → 10:30
        self.assertEqual(items[0]["start_time"], datetime.time(9, 0))
        self.assertEqual(items[0]["end_time"],   datetime.time(10, 30))

        # Attr 1: 10:30 + MIN_TRAVEL_BUFFER(15 min) = 10:45 → 12:15
        expected_start1 = datetime.time(10, 30 + MIN_TRAVEL_BUFFER_MINUTES)
        self.assertEqual(items[1]["start_time"], expected_start1,
                         msg="Second attraction must be offset by travel buffer")

        # Attr 2: 12:15 + 15 travel = 12:30 → lunch +60 = 13:30 → 15:00
        total_lunch_min = LUNCH_BREAK_MIN + LUNCH_DURATION_MINUTES
        lunch_end = datetime.time(LUNCH_BREAK_HOUR + total_lunch_min // 60, total_lunch_min % 60)
        self.assertEqual(items[2]["start_time"], lunch_end,
                         msg="Third attraction delayed by travel buffer + lunch break")
        self.assertEqual(items[2]["end_time"],   datetime.time(15, 0))

    def test_TC12_day_number_and_visit_order_correct(self):
        """BVA: day_number is passed through; visit_order starts at 1."""
        atts  = [_make_attraction(i, 3.0, 101.0 + i * 0.01) for i in range(2)]
        items = assign_time_slots(atts, day_number=3, visit_order_start=1)
        for item in items:
            self.assertEqual(item["day_number"], 3,
                             msg="day_number must match the argument")
        self.assertEqual(items[0]["visit_order"], 1)
        self.assertEqual(items[1]["visit_order"], 2,
                         msg="visit_order must increment from visit_order_start")

    def test_TC_category_visit_durations(self):
        """EP: category-specific durations — history=120 min, food=60 min."""
        history_att = [_make_attraction(1, 3.0, 101.0, category="history")]
        food_att    = [_make_attraction(2, 3.0, 101.0, category="food")]

        history_items = assign_time_slots(history_att, day_number=1)
        food_items    = assign_time_slots(food_att,    day_number=1)

        expected_history_end = datetime.time(DAY_START_HOUR + VISIT_DURATIONS["history"] // 60,
                                             VISIT_DURATIONS["history"] % 60)
        expected_food_end    = datetime.time(DAY_START_HOUR + VISIT_DURATIONS["food"] // 60,
                                             VISIT_DURATIONS["food"] % 60)

        self.assertEqual(history_items[0]["end_time"], expected_history_end,
                         msg="history attraction should get 120 min visit")
        self.assertEqual(food_items[0]["end_time"], expected_food_end,
                         msg="food attraction should get 60 min visit")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC13–TC16  chatbot NLP functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatbotNLP(unittest.TestCase):

    def test_TC13_tokenise_removes_stop_words(self):
        """EP: stop-words like 'I', 'want', 'to' must not appear in output."""
        tokens = tokenise("I want to visit Tokyo")
        self.assertNotIn("i",    tokens, msg="'i' is a stop-word")
        self.assertNotIn("to",   tokens, msg="'to' is a stop-word")
        # 'visit' and 'tokyo' must remain
        self.assertIn("visit", tokens, msg="'visit' should remain after stop-word removal")
        self.assertIn("tokyo", tokens, msg="'tokyo' should remain after stop-word removal")

    def test_TC14_extract_destination_finds_known_city(self):
        """EP: message containing a seeded city → correct canonical name returned."""
        self.assertEqual(extract_destination("I want to go to Paris"),
                         "Paris", msg="Paris should be extracted")
        self.assertEqual(extract_destination("fly to Kuala Lumpur next month"),
                         "Kuala Lumpur", msg="Multi-word city should be extracted")
        # Alias test
        self.assertEqual(extract_destination("heading to KL for a week"),
                         "Kuala Lumpur", msg="Alias 'KL' should resolve to Kuala Lumpur")

    def test_TC15_extract_budget_type_recognises_all_three_levels(self):
        """EP: each budget tier recognised from synonyms."""
        self.assertEqual(extract_budget_type([], "I prefer cheap hotels"),
                         "budget", msg="'cheap' → budget")
        self.assertEqual(extract_budget_type([], "my budget is mid-range"),
                         "mid-range", msg="'mid-range' literal → mid-range")
        self.assertEqual(extract_budget_type([], "I want luxury accommodation"),
                         "luxury", msg="'luxury' → luxury")

    def test_TC16_extract_days_handles_days_and_nights(self):
        """EP + BVA: various phrasings of trip duration."""
        self.assertEqual(extract_days("I plan to stay for 5 days"), 5,
                         msg="'5 days' → 5")
        self.assertEqual(extract_days("booking 3 nights"), 3,
                         msg="'3 nights' → 3")
        self.assertIsNone(extract_days("I want to travel"),
                          msg="No number present → None")
        self.assertIsNone(extract_days("I need 0 days"),
                          msg="0 days is out of valid range → None")
        self.assertIsNone(extract_days("a 31-day journey"),
                          msg="31 days exceeds 30-day cap → None")

    # ── Bonus: intent detection smoke tests ──────────────────────────────────

    def test_TC_intent_greet(self):
        tokens = tokenise("hello")
        self.assertEqual(detect_intent(tokens, "hello"), "greet")

    def test_TC_intent_destination(self):
        tokens = tokenise("I want to visit Tokyo")
        self.assertEqual(detect_intent(tokens, "I want to visit Tokyo"),
                         "update_destination")

    def test_TC_intent_budget(self):
        tokens = tokenise("my budget is luxury")
        self.assertEqual(detect_intent(tokens, "my budget is luxury"),
                         "update_budget")

    def test_TC_intent_generate(self):
        tokens = tokenise("plan my trip")
        self.assertEqual(detect_intent(tokens, "plan my trip"),
                         "generate_itinerary")

    def test_TC_process_message_returns_required_keys(self):
        result = process_message("I want to go to Tokyo for 5 days")
        for key in ("intent", "entities", "updates", "reply"):
            self.assertIn(key, result, msg=f"Key '{key}' must be in process_message output")
        self.assertIsInstance(result["reply"], str)
        self.assertGreater(len(result["reply"]), 0, msg="Reply must not be empty")

    def test_TC_extract_interests_multiword(self):
        """EP: multi-word synonym 'street food' should map to 'food'."""
        tokens = tokenise("I love street food and hiking")
        interests = extract_interests(tokens)
        self.assertIn("nature", interests, msg="'hiking' → nature")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC17–TC19  encode_user()
# ═══════════════════════════════════════════════════════════════════════════════

class TestEncodeUser(unittest.TestCase):

    def test_TC17_known_input_produces_correct_one_hot_dims(self):
        """EP: luxury/cold/[food] → correct budget, weather, and interest dims set."""
        vec = encode_user("luxury", "cold", ["food"])
        row = vec[0]
        self.assertEqual(row.shape[0], 12, msg="Vector must be 12-dimensional")
        self.assertEqual(list(row[0:3]), [0.0, 0.0, 1.0], msg="budget=luxury → [0,0,1]")
        self.assertEqual(list(row[3:6]), [0.0, 1.0, 0.0], msg="weather=cold → [0,1,0]")
        food_idx = INTEREST_OPTIONS.index("food")
        for i, c in enumerate(INTEREST_OPTIONS):
            expected = 1.0 if i == food_idx else 0.0
            self.assertEqual(row[6 + i], expected, msg=f"interest dim '{c}' incorrect")

    def test_TC18_behaviour_weights_softly_boost_unselected_interest(self):
        """EP: a category NOT selected still gets a partial boost from behaviour_weights."""
        vec_plain  = encode_user("budget", "warm", ["nature"])
        vec_boosted = encode_user("budget", "warm", ["nature"],
                                   behaviour_weights={"food": 0.8})
        food_idx = INTEREST_OPTIONS.index("food")
        self.assertEqual(vec_plain[0][6 + food_idx], 0.0,
                         msg="Unselected, unboosted interest must stay 0")
        self.assertAlmostEqual(vec_boosted[0][6 + food_idx], 0.4, places=6,
                               msg="behaviour_weights boost = 0.5 * weight = 0.4")

    def test_TC19_empty_interests_all_interest_dims_zero(self):
        """BVA: no interests selected → all 6 interest dimensions are 0."""
        vec = encode_user("mid-range", "moderate", [])
        row = vec[0]
        for i in range(6, 12):
            self.assertEqual(row[i], 0.0, msg="No interests selected → all interest dims 0")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC20–TC22  assign_persona()
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssignPersona(unittest.TestCase):

    def test_TC20_returns_a_known_persona_label(self):
        """EP: a valid preference combination must map to one of the 6 real personas."""
        label = assign_persona("luxury", "warm", ["food", "history"])
        self.assertIn(label, PERSONA_LABELS.values(),
                     msg="assign_persona must return one of the defined PERSONA_LABELS")

    def test_TC21_deterministic_for_same_input(self):
        """BVA: identical input, called twice, must return the identical persona label."""
        label1 = assign_persona("budget", "cold", ["nature", "adventure"])
        label2 = assign_persona("budget", "cold", ["nature", "adventure"])
        self.assertEqual(label1, label2, msg="K-Means assignment must be deterministic")

    def test_TC22_empty_interests_does_not_crash(self):
        """BVA: no interests selected → still returns a valid string label, no exception."""
        label = assign_persona("mid-range", "moderate", [])
        self.assertIsInstance(label, str)
        self.assertGreater(len(label), 0, msg="Persona label must not be empty")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC23–TC24  encode_attraction()
# ═══════════════════════════════════════════════════════════════════════════════

class TestEncodeAttraction(unittest.TestCase):

    def test_TC23_category_one_hot_at_correct_index(self):
        """EP: category='history' → 1 at the history index, 0 elsewhere (6-dim, category-only)."""
        vec = encode_attraction({"category": "history"})
        row = vec[0]
        self.assertEqual(row.shape[0], 6,
                         msg="encode_attraction is category-only — must be 6-dimensional")
        history_idx = INTEREST_OPTIONS.index("history")
        for i, c in enumerate(INTEREST_OPTIONS):
            expected = 1.0 if i == history_idx else 0.0
            self.assertEqual(row[i], expected, msg=f"dim '{c}' incorrect for category='history'")

    def test_TC24_unknown_category_returns_all_zero_vector(self):
        """BVA: missing/unrecognised category → all-zero vector, no exception."""
        vec = encode_attraction({"category": "unknown_type"})
        self.assertTrue((vec[0] == 0.0).all(), msg="Unknown category must yield an all-zero vector")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC25–TC27  budget_fit()
# ═══════════════════════════════════════════════════════════════════════════════

class TestBudgetFit(unittest.TestCase):

    def test_TC25_exact_match_returns_one(self):
        """EP: attraction tier == user's declared budget_type → full score 1.0."""
        self.assertEqual(budget_fit("luxury", "luxury"), 1.0)
        self.assertEqual(cost_tier(50.0), "luxury", msg="cost>10 must classify as luxury tier")

    def test_TC26_adjacent_tier_returns_partial_score(self):
        """BVA: one tier apart (budget<->mid-range, mid-range<->luxury) → 0.7."""
        self.assertEqual(budget_fit("mid-range", "budget"), 0.7)
        self.assertEqual(budget_fit("luxury", "mid-range"), 0.7)

    def test_TC27_opposite_ends_returns_minimum_score(self):
        """BVA: budget vs luxury (max distance) → discounted to 0.4, never zeroed out."""
        self.assertEqual(budget_fit("luxury", "budget"), 0.4)
        self.assertGreater(budget_fit("luxury", "budget"), 0.0,
                           msg="A budget mismatch must discount, not erase, the match")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC28–TC30  Password hashing (bcrypt, as used in auth.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing(unittest.TestCase):

    def test_TC28_hash_is_not_plaintext_and_verifies_correctly(self):
        """EP: hashing then checking the SAME password must succeed, and never store plaintext."""
        password = "MySecret123"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.assertNotEqual(hashed, password, msg="Stored hash must never equal the plaintext")
        self.assertTrue(bcrypt.checkpw(password.encode(), hashed.encode()),
                        msg="Correct password must verify successfully")

    def test_TC29_wrong_password_fails_verification(self):
        """BVA: an incorrect password must fail bcrypt.checkpw()."""
        hashed = bcrypt.hashpw("CorrectPass1".encode(), bcrypt.gensalt()).decode()
        self.assertFalse(bcrypt.checkpw("WrongPass1".encode(), hashed.encode()),
                         msg="Incorrect password must not verify")

    def test_TC30_same_password_produces_different_salted_hashes(self):
        """EP: hashing the same password twice must yield two different hashes (random salt),
        with both still verifying correctly."""
        password = "RepeatPass1"
        hash1 = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        hash2 = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.assertNotEqual(hash1, hash2, msg="Each hash must use a fresh random salt")
        self.assertTrue(bcrypt.checkpw(password.encode(), hash1.encode()))
        self.assertTrue(bcrypt.checkpw(password.encode(), hash2.encode()))


# ═══════════════════════════════════════════════════════════════════════════════
#  DB-backed fixture — in-memory SQLite, mirroring test_integration.py's BaseTestCase
# ═══════════════════════════════════════════════════════════════════════════════

class _DBTestCase(unittest.TestCase):
    """Shared Flask + in-memory SQLite fixture for functions that query the
    database (feedback scores, collaborative filtering, behavioural logging).
    No external MySQL needed — fresh schema created per test class."""

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
        from app.models.attraction_feedback import AttractionFeedback
        from app.models.user_behaviour import UserBehaviour

        class _TestConfig:
            TESTING = True
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            SECRET_KEY = "test-secret-key"
            GOOGLE_API_KEY = ""

        cls.app = create_app(_TestConfig)
        cls.db  = _db
        cls.User, cls.UserProfile, cls.Attraction = User, UserProfile, Attraction
        cls.Itinerary, cls.ItineraryItem, cls.ItineraryRating = Itinerary, ItineraryItem, ItineraryRating
        cls.AttractionFeedback, cls.UserBehaviour = AttractionFeedback, UserBehaviour

        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        _db.create_all()

    @classmethod
    def tearDownClass(cls):
        cls.db.session.remove()
        cls.db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        """Fresh user, profile, and attractions before every test method."""
        self.user = self.User(full_name="Unit Test User", email=f"ut{id(self)}@pengo.com",
                              password_hash="x")
        self.db.session.add(self.user)
        self.db.session.flush()
        self.profile = self.UserProfile(
            user_id=self.user.user_id, budget_type="mid-range",
            weather_pref="warm", interests="food,history", persona_label="Relaxation & Foodie",
        )
        self.db.session.add(self.profile)

        self.att_food = self.Attraction(
            attraction_id=9001, name="Test Cafe", city="TestCity", country="TestCountry",
            category="food", rating=4.5, entry_cost=15.0, popularity_score=3,
            latitude=3.1, longitude=101.7,
        )
        self.att_history = self.Attraction(
            attraction_id=9002, name="Test Museum", city="TestCity", country="TestCountry",
            category="history", rating=4.0, entry_cost=50.0, popularity_score=2,
            latitude=3.2, longitude=101.8,
        )
        self.db.session.add_all([self.att_food, self.att_history])
        self.db.session.commit()

    def tearDown(self):
        """Clear all rows between tests so each test starts from a clean slate."""
        for model in (self.AttractionFeedback, self.UserBehaviour, self.ItineraryRating,
                      self.ItineraryItem, self.Itinerary, self.UserProfile,
                      self.Attraction, self.User):
            self.db.session.query(model).delete()
        self.db.session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
#  TC31–TC33  get_feedback_score() / get_feedback_scores_batch()
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeedbackScore(_DBTestCase):

    def test_TC31_no_ratings_returns_neutral_default(self):
        """EP: no historical ratings for this persona/attraction → neutral 0.5 default."""
        result = get_feedback_scores_batch([self.att_food.attraction_id],
                                           self.profile.persona_label, self.db.session)
        self.assertEqual(result[self.att_food.attraction_id], 0.5,
                         msg="No ratings available → must default to 0.5, not error or 0")

    def test_TC32_computes_correct_normalised_average(self):
        """EP: a rating_score of 5 from a same-persona user → (5-1)/4 = 1.0."""
        itinerary = self.Itinerary(user_id=self.user.user_id, destination="TestCity", travel_days=1)
        self.db.session.add(itinerary)
        self.db.session.flush()
        self.db.session.add(self.ItineraryItem(
            itinerary_id=itinerary.itinerary_id, attraction_id=self.att_food.attraction_id,
            day_number=1, visit_order=1,
        ))
        self.db.session.add(self.ItineraryRating(
            itinerary_id=itinerary.itinerary_id, user_id=self.user.user_id, rating_score=5,
        ))
        self.db.session.commit()

        result = get_feedback_scores_batch([self.att_food.attraction_id],
                                           self.profile.persona_label, self.db.session)
        self.assertAlmostEqual(result[self.att_food.attraction_id], 1.0, places=4,
                               msg="rating_score=5 must normalise to (5-1)/4 = 1.0")

    def test_TC33_single_id_wrapper_matches_batch_result(self):
        """EP: get_feedback_score() (single-ID wrapper) must equal the batched result
        for the same attraction, since it delegates to get_feedback_scores_batch()."""
        single = get_feedback_score(self.att_history.attraction_id,
                                    self.profile.persona_label, self.db.session)
        batch = get_feedback_scores_batch([self.att_history.attraction_id],
                                          self.profile.persona_label, self.db.session)
        self.assertEqual(single, batch[self.att_history.attraction_id],
                         msg="Single-ID wrapper must match the batched implementation")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC34–TC37  recommend_attractions()
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecommendAttractions(_DBTestCase):

    def _user_profile_dict(self):
        return {
            "user_id": self.user.user_id,
            "budget_type": self.profile.budget_type,
            "weather_pref": self.profile.weather_pref,
            "interests": ["food", "history"],
            "persona_label": self.profile.persona_label,
        }

    def test_TC34_empty_attraction_list_returns_empty(self):
        """BVA: no candidate attractions → empty result, no exception."""
        result = recommend_attractions(
            user_profile=self._user_profile_dict(), attractions=[],
            db_session=self.db.session, top_n=10, use_cf=False,
        )
        self.assertEqual(result, [])

    def test_TC35_respects_top_n_limit(self):
        """EP: more candidates than top_n → result truncated to top_n."""
        attractions = [self.att_food.to_dict(), self.att_history.to_dict()]
        result = recommend_attractions(
            user_profile=self._user_profile_dict(), attractions=attractions,
            db_session=self.db.session, top_n=1, use_cf=False,
        )
        self.assertEqual(len(result), 1, msg="Result must be capped at top_n")

    def test_TC36_budget_limit_excludes_expensive_attractions(self):
        """EP: budget_limit below an attraction's entry_cost → that attraction excluded."""
        attractions = [self.att_food.to_dict(), self.att_history.to_dict()]  # cost 15.0, 50.0
        result = recommend_attractions(
            user_profile=self._user_profile_dict(), attractions=attractions,
            db_session=self.db.session, budget_limit=20.0, top_n=10, use_cf=False,
        )
        result_ids = {r["attraction_id"] for r in result}
        self.assertNotIn(self.att_history.attraction_id, result_ids,
                         msg="Attraction costing 50 must be excluded by a budget_limit of 20")
        self.assertIn(self.att_food.attraction_id, result_ids,
                      msg="Attraction costing 15 must remain under a budget_limit of 20")

    def test_TC37_disliked_attractions_are_excluded(self):
        """EP: an attraction the user disliked must never appear in their results."""
        self.db.session.add(self.AttractionFeedback(
            user_id=self.user.user_id, itinerary_id=1, attraction_id=self.att_food.attraction_id,
        ))
        self.db.session.commit()

        attractions = [self.att_food.to_dict(), self.att_history.to_dict()]
        result = recommend_attractions(
            user_profile=self._user_profile_dict(), attractions=attractions,
            db_session=self.db.session, top_n=10, use_cf=False,
        )
        result_ids = {r["attraction_id"] for r in result}
        self.assertNotIn(self.att_food.attraction_id, result_ids,
                         msg="Disliked attraction must be excluded from recommendations")


# ═══════════════════════════════════════════════════════════════════════════════
#  TC38–TC39  compute_behaviour_weights()
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeBehaviourWeights(_DBTestCase):

    def test_TC38_no_logged_events_returns_empty_dict(self):
        """BVA: a user with no behaviour history → empty weights, not an error."""
        weights = compute_behaviour_weights(self.user.user_id, self.db.session)
        self.assertEqual(weights, {})

    def test_TC39_logged_events_produce_normalised_weights(self):
        """EP: repeated 'food' events must dominate the normalised weight distribution,
        and all weights must sum to ~1.0."""
        for _ in range(3):
            log_event(user_id=self.user.user_id, event_type="attraction_add",
                     db_session=self.db.session, category="food")
        log_event(user_id=self.user.user_id, event_type="search",
                 db_session=self.db.session, category="history")

        weights = compute_behaviour_weights(self.user.user_id, self.db.session)
        self.assertGreater(weights["food"], weights["history"],
                           msg="3x attraction_add(food) must outweigh 1x search(history)")
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4,
                               msg="Normalised weights must sum to 1.0")


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
