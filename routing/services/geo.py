import math

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return EARTH_RADIUS_MILES * 2 * math.asin(math.sqrt(a))


def point_to_segment_miles(point, a, b):
    """Distance from point to segment a-b (lon, lat pairs) and fraction t along it."""
    lon, lat = point
    lat0 = math.radians((a[1] + b[1]) / 2)
    c = math.cos(lat0)
    ax, ay, bx, by, px, py = a[0] * c, a[1], b[0] * c, b[1], lon * c, lat
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    t = 0.0 if den == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / den))
    q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    return haversine_miles(lon, lat, q[0], q[1]), t


def route_positions(coords):
    """Cumulative miles along the polyline for every vertex."""
    out = [0.0]
    for a, b in zip(coords, coords[1:]):
        out.append(out[-1] + haversine_miles(a[0], a[1], b[0], b[1]))
    return out
