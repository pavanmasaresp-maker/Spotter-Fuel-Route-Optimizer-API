"""Station loading + fast "which stations are near this route" lookup (no Django imports)."""
import csv
import math
from functools import lru_cache
from pathlib import Path

from .geo import point_to_segment_miles, route_positions

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
ENRICHED = DATA_DIR / "fuel_prices_enriched.csv"

US_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)


def _normalise(row):
    return {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items() if k}


def load_stations(path=ENRICHED):
    """One record per truck stop; duplicate rows keep the lowest price."""
    best = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            r = _normalise(raw)
            if r.get("state", "").upper() not in US_STATES:
                continue  # the CSV also contains Canadian stops (ON, AB, BC, ...)
            try:
                price = float(r["retail_price"])
                lat, lon = float(r["latitude"]), float(r["longitude"])
            except (KeyError, ValueError):
                continue
            sid = r.get("opis_truckstop_id") or (r.get("truckstop_name", "") + "|" + r.get("address", ""))
            if sid not in best or price < best[sid]["price_per_gallon"]:
                best[sid] = {
                    "id": sid, "name": r.get("truckstop_name"), "address": r.get("address"),
                    "city": r.get("city"), "state": r.get("state"),
                    "lat": lat, "lon": lon, "price_per_gallon": price,
                }
    return list(best.values())


class StationIndex:
    CELL = 0.5  # degrees; 3x3 cells comfortably cover a 15-25 mile corridor in the US

    def __init__(self, stations):
        self.stations = stations

    def along_route(self, coords, route_miles, corridor_miles, spacing_miles=2.0):
        """Stations within corridor_miles of the route, with miles-from-start and offset."""
        if len(coords) < 2:
            return []
        pos = route_positions(coords)
        scale = route_miles / pos[-1] if pos[-1] > 0 else 1.0  # align with the router's distance

        keep, last = [0], 0.0
        for i in range(1, len(coords) - 1):
            if pos[i] - last >= spacing_miles:
                keep.append(i)
                last = pos[i]
        keep.append(len(coords) - 1)
        pts = [coords[i] for i in keep]
        ppos = [pos[i] for i in keep]

        max_abs_lat = max(abs(pt[1]) for pt in pts)
        cell = max(self.CELL, (corridor_miles + spacing_miles) * 1.1
                   / (69.17 * max(0.2, math.cos(math.radians(max_abs_lat)))))
        grid = {}
        for k, (lon, lat) in enumerate(pts):
            grid.setdefault((math.floor(lon / cell), math.floor(lat / cell)), []).append(k)

        lats = [p[1] for p in pts]
        lons = [p[0] for p in pts]
        pad_lat = corridor_miles / 69.0 + 0.05
        pad_lon = pad_lat / max(0.2, math.cos(math.radians(max(abs(min(lats)), abs(max(lats))))))
        lat_lo, lat_hi = min(lats) - pad_lat, max(lats) + pad_lat
        lon_lo, lon_hi = min(lons) - pad_lon, max(lons) + pad_lon
        limit2 = (corridor_miles + spacing_miles) ** 2

        found = []
        for s in self.stations:
            slat, slon = s["lat"], s["lon"]
            if not (lat_lo <= slat <= lat_hi and lon_lo <= slon <= lon_hi):
                continue
            cx, cy = math.floor(slon / cell), math.floor(slat / cell)
            cosl = math.cos(math.radians(slat))
            best_k, best_d = None, float("inf")
            for gx in (cx - 1, cx, cx + 1):
                for gy in (cy - 1, cy, cy + 1):
                    for k in grid.get((gx, gy), ()):
                        dx = (pts[k][0] - slon) * cosl * 69.17
                        dy = (pts[k][1] - slat) * 69.0
                        d = dx * dx + dy * dy
                        if d < best_d:
                            best_d, best_k = d, k
            if best_k is None or best_d > limit2:
                continue
            off, along = float("inf"), None
            for a in (best_k - 1, best_k):
                if a < 0 or a + 1 >= len(pts):
                    continue
                o, t = point_to_segment_miles((slon, slat), pts[a], pts[a + 1])
                if o < off:
                    off, along = o, ppos[a] + t * (ppos[a + 1] - ppos[a])
            if along is not None and off <= corridor_miles:
                found.append({**s, "route_miles": along * scale, "offset_miles": off})
        found.sort(key=lambda x: x["route_miles"])
        return found


def has_enriched_data():
    return ENRICHED.exists()


@lru_cache(maxsize=1)
def get_index():
    """Built once per process, reused by every request."""
    return StationIndex(load_stations())
