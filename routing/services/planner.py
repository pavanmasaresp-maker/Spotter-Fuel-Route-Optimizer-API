import time

from django.conf import settings

from .errors import PlanError
from .geocoding import geocode_location
from .optimizer import InfeasibleRoute, optimize_fuel_stops
from .routing import get_route
from .stations import get_index, has_enriched_data

METERS_PER_MILE = 1609.344


def plan_trip(start_query, finish_query):
    t0 = time.perf_counter()
    stats = {"external_calls": 0}

    if not has_enriched_data():
        raise PlanError("Fuel data has no coordinates yet. Run: python manage.py enrich_fuel_stations", 503)

    start = geocode_location(start_query, stats, "start")
    finish = geocode_location(finish_query, stats, "finish")
    route = get_route(start, finish, stats)

    miles = route["distance_meters"] / METERS_PER_MILE
    candidates = get_index().along_route(route["geometry"]["coordinates"], miles,
                                         settings.STATION_CORRIDOR_MILES)
    try:
        plan = optimize_fuel_stops(miles, candidates, settings.MAX_RANGE_MILES, settings.MPG)
    except InfeasibleRoute as exc:
        raise PlanError(str(exc), 422) from exc

    return {
        "assumptions": {
            "max_range_miles": settings.MAX_RANGE_MILES,
            "mpg": settings.MPG,
            "starting_tank": "full (not charged to the trip)",
            "station_corridor_miles": settings.STATION_CORRIDOR_MILES,
            "station_location": "city centroid (supplied CSV has no coordinates)",
        },
        "start": start,
        "finish": finish,
        "route": {
            "distance_miles": round(miles, 2),
            "duration_minutes": round(route["duration_seconds"] / 60, 1),
            "geojson": route["geometry"],
        },
        "fuel": {
            "stations_considered": len(candidates),
            "stops": plan["stops"],
            "total_cost": plan["total_cost"],
            "fuel_consumed_gallons": plan["fuel_consumed_gallons"],
            "fuel_purchased_gallons": plan["fuel_purchased_gallons"],
            "ending_fuel_gallons": plan["ending_fuel_gallons"],
        },
        "performance": {
            "external_api_calls": stats["external_calls"],
            "processing_ms": round((time.perf_counter() - t0) * 1000, 1),
        },
    }
