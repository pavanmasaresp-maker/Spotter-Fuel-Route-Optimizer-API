"""Turn "City, ST" (or "lat,lon") into coordinates. Nominatim (free), cached in memory + DB."""
import re

import requests
from django.conf import settings
from django.core.cache import cache

from routing.models import GeocodeCache
from .errors import PlanError
from .throttle import Throttle

# Nominatim public usage policy: at most 1 request per second
_THROTTLE = Throttle(1.1)

LATLON = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")
# contiguous USA bounding box
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 24.0, 50.0, -125.5, -66.0


def _check_us(lat, lon, label):
    if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
        raise PlanError(f"{label} must be inside the contiguous USA.", 422)


def geocode_location(query, stats, label="location"):
    m = LATLON.match(query)
    if m:  # explicit coordinates: no external call at all
        lat, lon = float(m.group(1)), float(m.group(2))
        _check_us(lat, lon, label)
        return {"latitude": lat, "longitude": lon, "display_name": f"{lat:.5f}, {lon:.5f}"}

    key = "geocode:" + query.casefold()
    hit = cache.get(key)
    if hit:
        return hit
    row = GeocodeCache.objects.filter(query__iexact=query).first()
    if row:
        result = {"latitude": row.latitude, "longitude": row.longitude, "display_name": row.display_name}
        cache.set(key, result, settings.GEOCODE_CACHE_TTL)
        return result

    try:
        _THROTTLE.wait()
        stats["external_calls"] += 1
        r = requests.get(
            settings.NOMINATIM_URL + "/search",
            params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "us"},
            headers={"User-Agent": settings.GEOCODER_USER_AGENT}, timeout=8)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise PlanError("Geocoding service unavailable.", 502) from exc
    if not data:
        raise PlanError(f"Could not find {label} \u0027{query}\u0027 in the USA.", 422)

    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    _check_us(lat, lon, label)
    result = {"latitude": lat, "longitude": lon, "display_name": data[0].get("display_name", query)}
    GeocodeCache.objects.update_or_create(query=query, defaults={
        "latitude": lat, "longitude": lon, "display_name": result["display_name"][:500]})
    cache.set(key, result, settings.GEOCODE_CACHE_TTL)
    return result
