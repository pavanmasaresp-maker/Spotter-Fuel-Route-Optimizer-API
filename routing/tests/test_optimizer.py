import random
import unittest

from routing.services.optimizer import InfeasibleRoute, optimize_fuel_stops


def st(i, pos, price):
    return {"id": i, "name": i, "address": "x", "city": "x", "state": "TX",
            "lat": 30.0, "lon": -95.0, "route_miles": pos, "price_per_gallon": price}


def brute_force(dist, stations, rng=500, mpg=10):
    """Exact DP with 1-gallon fuel steps (valid when all distances are multiples of 10 mi)."""
    cap = int(rng / mpg)
    nodes = sorted((s for s in stations if 0 < s["route_miles"] < dist), key=lambda s: s["route_miles"])
    pts = [(0, None)] + [(s["route_miles"], s["price_per_gallon"]) for s in nodes] + [(dist, None)]
    INF = float("inf")
    dp = [INF] * (cap + 1)
    dp[cap] = 0.0
    for i in range(len(pts) - 1):
        pos, price = pts[i]
        if price is not None:
            nd = dp[:]
            for f in range(cap + 1):
                if dp[f] < INF:
                    for g in range(f + 1, cap + 1):
                        nd[g] = min(nd[g], dp[f] + (g - f) * price)
            dp = nd
        need = int(round((pts[i + 1][0] - pos) / mpg))
        nd = [INF] * (cap + 1)
        for f in range(need, cap + 1):
            nd[f - need] = min(nd[f - need], dp[f])
        dp = nd
    return min(dp)


class OptimizerTests(unittest.TestCase):
    def test_short_trip_needs_no_stop(self):
        r = optimize_fuel_stops(400, [], 500, 10)
        self.assertEqual(r["stops"], [])
        self.assertEqual(r["fuel_consumed_gallons"], 40)

    def test_buys_only_to_reach_cheaper_station(self):
        r = optimize_fuel_stops(800, [st("A", 200, 4.0), st("B", 350, 2.5), st("C", 500, 3.5)], 500, 10)
        self.assertLess(r["total_cost"], 400)
        self.assertTrue(any(s["station_id"] == "B" for s in r["stops"]))

    def test_does_not_skip_cheap_intermediate_station(self):
        # Old v3 logic jumped to the farthest station (5.00/gal) and paid $199.90.
        stations = [st("cur", 10, 3.00), st("X", 100, 3.10), st("F", 490, 5.00)]
        r = optimize_fuel_stops(900, stations, 500, 10)
        self.assertAlmostEqual(r["total_cost"], brute_force(900, stations), places=1)
        self.assertLess(r["total_cost"], 190)

    def test_infeasible_gap(self):
        with self.assertRaises(InfeasibleRoute):
            optimize_fuel_stops(900, [st("A", 600, 2.5)], 500, 10)

    def test_never_buys_more_than_tank(self):
        r = optimize_fuel_stops(1500, [st(str(p), p, 3 + (p % 7) / 10) for p in range(50, 1500, 50)], 500, 10)
        self.assertLessEqual(max(s["fuel_gallons"] for s in r["stops"]), 50.0 + 1e-6)

    def test_fuel_accounting(self):
        r = optimize_fuel_stops(700, [st("A", 450, 3.0)], 500, 10)
        self.assertAlmostEqual(r["fuel_consumed_gallons"], 70.0)
        self.assertAlmostEqual(r["fuel_purchased_gallons"], 20.0)
        self.assertAlmostEqual(r["total_cost"], 60.0)
        self.assertAlmostEqual(r["ending_fuel_gallons"], 0.0)

    def test_matches_brute_force_on_random_routes(self):
        rnd = random.Random(7)
        checked = 0
        for _ in range(400):
            dist = rnd.choice([700, 900, 1200, 1500, 2000])
            pos = sorted(rnd.sample(range(10, dist - 10, 10), rnd.randint(3, 14)))
            stations = [st(f"s{i}", p, round(rnd.uniform(2.8, 4.5), 2)) for i, p in enumerate(pos)]
            try:
                got = optimize_fuel_stops(dist, stations, 500, 10)["total_cost"]
            except InfeasibleRoute:
                continue
            self.assertAlmostEqual(got, brute_force(dist, stations), delta=0.02)
            checked += 1
        self.assertGreater(checked, 100)


if __name__ == "__main__":
    unittest.main()
