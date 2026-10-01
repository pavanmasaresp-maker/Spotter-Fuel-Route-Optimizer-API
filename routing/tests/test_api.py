from unittest.mock import patch

from django.test import Client, SimpleTestCase, TestCase

from routing.services.errors import PlanError
from routing.services import planner


class ApiValidationTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_missing_finish(self):
        r = self.client.post("/api/route/", {"start": "New York, NY"}, content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_same_start_and_finish(self):
        r = self.client.post("/api/route/", {"start": "Dallas, TX", "finish": "dallas, tx"},
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_bad_json(self):
        r = self.client.post("/api/route/", "not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    @patch("routing.views.plan_trip", side_effect=PlanError("boom", 422))
    def test_plan_error_maps_to_status(self, _):
        r = self.client.get("/api/route/?start=A&finish=B")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["error"], "boom")

    def test_health_and_map(self):
        self.assertEqual(self.client.get("/api/health/").status_code, 200)
        self.assertEqual(self.client.get("/api/map/").status_code, 200)


class PlannerTests(TestCase):
    STATIONS = [
        {"id": "a", "name": "A", "address": "", "city": "X", "state": "IL", "lat": 40.0, "lon": -85.0,
         "price_per_gallon": 3.10},
        {"id": "b", "name": "B", "address": "", "city": "Y", "state": "IL", "lat": 40.0, "lon": -90.0,
         "price_per_gallon": 2.90},
        {"id": "c", "name": "C", "address": "", "city": "Z", "state": "IL", "lat": 40.0, "lon": -95.0,
         "price_per_gallon": 3.00},
    ]

    @patch("routing.services.planner.has_enriched_data", return_value=True)
    def test_full_plan_uses_one_route_call(self, _):
        from routing.services.stations import StationIndex

        coords = [[-80.0 - i * 0.05, 40.0] for i in range(0, 401)]  # ~1,050 miles west
        route = {"distance_meters": 1_690_000, "duration_seconds": 60000,
                 "geometry": {"type": "LineString", "coordinates": coords}}
        with patch("routing.services.planner.geocode_location",
                   side_effect=[{"latitude": 40.0, "longitude": -80.0, "display_name": "S"},
                                {"latitude": 40.0, "longitude": -100.0, "display_name": "F"}]), \
             patch("routing.services.planner.get_route", return_value=route), \
             patch("routing.services.planner.get_index", return_value=StationIndex(self.STATIONS)):
            result = planner.plan_trip("Start, PA", "Finish, NE")
        self.assertGreater(result["route"]["distance_miles"], 1000)
        self.assertGreaterEqual(len(result["fuel"]["stops"]), 1)
        self.assertGreater(result["fuel"]["total_cost"], 0)

    @patch("routing.services.planner.has_enriched_data", return_value=False)
    def test_requires_enriched_data(self, _):
        with self.assertRaises(PlanError) as ctx:
            planner.plan_trip("A", "B")
        self.assertEqual(ctx.exception.status, 503)
