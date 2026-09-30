import math
import random
import unittest

from routing.services.geo import haversine_miles, route_positions
from routing.services.stations import StationIndex


def straight_route(lon1, lat1, lon2, lat2, n):
    return [[lon1 + (lon2 - lon1) * i / (n - 1), lat1 + (lat2 - lat1) * i / (n - 1)] for i in range(n)]


class StationIndexTests(unittest.TestCase):
    def setUp(self):
        self.coords = straight_route(-80.0, 40.0, -90.0, 40.0, 2000)
        self.total = route_positions(self.coords)[-1]

    def station(self, sid, lon, lat, price=3.0):
        return {"id": sid, "name": sid, "address": "", "city": "", "state": "", "lat": lat, "lon": lon,
                "price_per_gallon": price}

    def test_finds_only_stations_inside_corridor_with_correct_position(self):
        near = self.station("near", -85.0, 40.05)          # ~3.5 mi off the route
        far = self.station("far", -85.0, 40.5)             # ~34 mi off the route
        behind = self.station("behind", -70.0, 40.0)       # beyond the start
        found = StationIndex([near, far, behind]).along_route(self.coords, self.total, 15)
        self.assertEqual([s["id"] for s in found], ["near"])
        expected = haversine_miles(-80.0, 40.0, -85.0, 40.0)
        self.assertAlmostEqual(found[0]["route_miles"], expected, delta=2.0)
        self.assertLess(found[0]["offset_miles"], 5)

    def test_sorted_by_route_position(self):
        st = [self.station("b", -88.0, 40.0), self.station("a", -82.0, 40.0)]
        found = StationIndex(st).along_route(self.coords, self.total, 15)
        self.assertEqual([s["id"] for s in found], ["a", "b"])

    def test_cross_country_speed(self):
        import time
        rnd = random.Random(3)
        coords = straight_route(-74.0, 40.7, -118.2, 34.0, 20000)
        total = route_positions(coords)[-1]
        stations = [self.station(str(i), rnd.uniform(-124, -70), rnd.uniform(26, 48)) for i in range(6700)]
        t = time.perf_counter()
        found = StationIndex(stations).along_route(coords, total, 15)
        elapsed = time.perf_counter() - t
        print(f"\n  cross-country: {len(found)} candidates in {elapsed * 1000:.0f} ms")
        self.assertLess(elapsed, 1.0)
        self.assertGreater(len(found), 0)


if __name__ == "__main__":
    unittest.main()
