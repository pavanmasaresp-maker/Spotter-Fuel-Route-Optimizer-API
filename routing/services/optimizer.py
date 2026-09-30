"""Exact fuel-stop optimiser for a fixed route (pure Python, no Django).

Classic gas-station greedy, which is optimal for continuous fuel:
  * at a station, if a strictly cheaper station is reachable on a full tank,
    buy only enough to reach the FIRST such station;
  * otherwise, if the finish is reachable, buy only enough to finish;
  * otherwise fill the tank and drive to the CHEAPEST station in range.
The vehicle starts with a full tank that is not charged to the trip.
"""
EPS = 1e-9


class InfeasibleRoute(ValueError):
    pass


def optimize_fuel_stops(route_miles, stations, max_range=500.0, mpg=10.0):
    capacity = max_range / mpg
    if route_miles <= 0:
        return _result([], 0.0, capacity, capacity, 0.0)

    usable = sorted((s for s in stations if 0 < s["route_miles"] < route_miles),
                    key=lambda s: s["route_miles"])
    # node 0 = START (free fuel, price 0), then stations, then FINISH
    pos = [0.0] + [s["route_miles"] for s in usable] + [route_miles]
    price = [0.0] + [s["price_per_gallon"] for s in usable] + [float("inf")]
    last = len(pos) - 1

    fuel, total, stops, i = 0.0, 0.0, [], 0
    while i < last:
        here = pos[i]
        in_range = [k for k in range(i + 1, last) if pos[k] - here <= max_range + EPS]

        cheaper = next((k for k in in_range if price[k] < price[i] - EPS), None)
        if cheaper is not None:
            target = cheaper
            buy = max(0.0, (pos[target] - here) / mpg - fuel)
        elif route_miles - here <= max_range + EPS:
            target = last
            buy = max(0.0, (route_miles - here) / mpg - fuel)
        elif in_range:
            target = min(in_range, key=lambda k: (price[k], pos[k]))
            buy = capacity - fuel
        else:
            gap = (pos[i + 1] - here) if i + 1 <= last else 0
            raise InfeasibleRoute(
                f"No fuel station within {max_range:.0f} miles after mile {here:.0f} "
                f"(next one is {gap:.0f} miles away).")

        if buy > EPS:
            if i > 0:  # START fuel is the free initial tank
                cost = buy * price[i]
                total += cost
                s = usable[i - 1]
                stops.append({
                    "station_id": s.get("id"), "station_name": s.get("name"),
                    "address": s.get("address"), "city": s.get("city"), "state": s.get("state"),
                    "latitude": s.get("lat"), "longitude": s.get("lon"),
                    "route_miles": round(here, 2),
                    "offset_miles_from_route": round(s.get("offset_miles", 0.0), 2),
                    "price_per_gallon": round(price[i], 3),
                    "fuel_gallons": round(buy, 3), "cost": round(cost, 2),
                })
            fuel += buy
        fuel -= (pos[target] - here) / mpg
        if fuel < -1e-6:
            raise InfeasibleRoute("Internal fuel accounting error.")
        fuel = max(0.0, fuel)
        i = target

    return _result(stops, total, fuel, capacity, route_miles / mpg)


def _result(stops, total, ending, initial, consumed):
    return {
        "stops": stops,
        "total_cost": round(total, 2),
        "fuel_consumed_gallons": round(consumed, 3),
        "fuel_purchased_gallons": round(sum(s["fuel_gallons"] for s in stops), 3),
        "ending_fuel_gallons": round(ending, 3),
        "initial_tank_gallons": round(initial, 3),
    }
