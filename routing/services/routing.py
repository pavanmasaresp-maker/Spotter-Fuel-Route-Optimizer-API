"""One OSRM call per new start/finish pair; results cached in memory and in the DB."""
import hashlib

import requests
from django.conf import settings
from django.core.cache import cache

from routing.models import RouteCache
from .errors import PlanError


def get_route(start, finish, stats):
    raw = "%.4f,%.4f;%.4f,%.4f" % (start["longitude"], start["latitude"],
                                    finish["longitude"], finish["latitude"])
    key = hashlib.sha256(raw.encode()).hexdigest()
    hit = cache.get("route:" + key)
    if hit:
        return hit
    row = RouteCache.objects.filter(cache_key=key).first()
    if row:
        cache.set("route:" + key, row.payload, settings.ROUTE_CACHE_TTL)
        return row.payload

    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{raw}"
    try:
        stats["external_calls"] += 1
        r = requests.get(url, params={"overview": "full", "geometries": "geojson",
                                      "steps": "false", "alternatives": "false"}, timeout=20)
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise PlanError("Routing service unavailable.", 502) from exc
    if body.get("code") != "Ok" or not body.get("routes"):
        raise PlanError("No driving route was found between those locations.", 422)

    route = body["routes"][0]
    payload = {"distance_meters": route["distance"], "duration_seconds": route["duration"],
               "geometry": route["geometry"]}
    RouteCache.objects.update_or_create(cache_key=key, defaults={"payload": payload})
    cache.set("route:" + key, payload, settings.ROUTE_CACHE_TTL)
    return payload
