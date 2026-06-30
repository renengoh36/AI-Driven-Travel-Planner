"""
Unit Tests — Module 4 (distance.py) and Module 5 (chatbot.py)

Test design technique: Equivalence Partitioning (EP) + Boundary Value Analysis (BVA)

Test groups:
    TC01–TC05  haversine()
    TC06–TC09  nearest_neighbour_route()
    TC10–TC12  assign_time_slots()
    TC13–TC16  chatbot NLP functions (tokenise, extract_*)
"""

import math
import sys
import os
import unittest
import datetime

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.distance import (
    haversine,
    nearest_neighbour_route,
    assign_time_slots,
    EARTH_RADIUS_KM,
    VISIT_DURATION_MINUTES,
    DAY_START_HOUR,
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_attraction(aid, lat, lon, name="Place"):
    return {"attraction_id": aid, "name": name, "latitude": lat, "longitude": lon}


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
        """EP: one attraction on day 1 → start 09:00, end 10:30."""
        att  = [_make_attraction(1, 3.1, 101.7)]
        items = assign_time_slots(att, day_number=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["start_time"], datetime.time(DAY_START_HOUR, 0),
                         msg="First attraction must start at 09:00")
        end_hour     = DAY_START_HOUR + VISIT_DURATION_MINUTES // 60
        end_min      = VISIT_DURATION_MINUTES % 60
        expected_end = datetime.time(end_hour, end_min)
        self.assertEqual(items[0]["end_time"], expected_end,
                         msg="End time must be start + 90 min")

    def test_TC11_three_attractions_sequential_times(self):
        """EP: 3 attractions → times chained consecutively."""
        atts  = [_make_attraction(i, 3.0 + i * 0.01, 101.0) for i in range(3)]
        items = assign_time_slots(atts, day_number=1)
        self.assertEqual(len(items), 3)
        # Second attraction starts where first ends
        self.assertEqual(items[1]["start_time"], items[0]["end_time"],
                         msg="Second attraction must start exactly when first ends")
        self.assertEqual(items[2]["start_time"], items[1]["end_time"],
                         msg="Third attraction must start exactly when second ends")

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

if __name__ == "__main__":
    unittest.main(verbosity=2)
