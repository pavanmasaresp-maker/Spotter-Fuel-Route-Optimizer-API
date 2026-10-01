# Spotter Fuel Route API (Django 6.1)

Give a start and finish inside the USA. The API returns the driving route (GeoJSON),
the cheapest fuel stops along it (500-mile range, 10 mpg) and the total fuel cost.

## Quick start (GitHub Codespaces or local, Python 3.12+)

```bash
pip install -r requirements.txt
cp .env.example .env            # set GEOCODER_USER_AGENT to include your email
python manage.py migrate
python manage.py enrich_fuel_stations   # one time: adds lat/lon, writes data/fuel_prices_enriched.csv
python manage.py test
python manage.py runserver 0.0.0.0:8000
```

Commit `data/fuel_prices_enriched.csv` so reviewers do not have to run the enrich step.
In Codespaces, open the forwarded port 8000 URL (set it to Public for Postman).

## Endpoints

| Method | URL | Notes |
| --- | --- | --- |
| POST | `/api/route/` | body `{"start": "New York, NY", "finish": "Los Angeles, CA"}` |
| GET | `/api/route/?start=...&finish=...` | same thing, handy in a browser |
| GET | `/api/map/` | Leaflet map page: draws the route and the fuel stops |
| GET | `/api/health/` | liveness |

`start` / `finish` can also be `"lat,lon"` (skips the geocoding call).
Import `postman/Spotter-Fuel-Route.postman_collection.json` into Postman.

Response (trimmed):

```json
{
  "route": {"distance_miles": 2790.1, "duration_minutes": 2520.3, "geojson": {"type": "LineString", "coordinates": [...]}},
  "fuel": {
    "stops": [{"station_name": "...", "city": "...", "state": "..", "latitude": 0, "longitude": 0,
               "route_miles": 402.5, "price_per_gallon": 3.189, "fuel_gallons": 41.2, "cost": 131.39}],
    "total_cost": 842.17, "fuel_consumed_gallons": 279.0
  },
  "performance": {"external_api_calls": 3, "processing_ms": 42.1}
}
```

## How it works

1. **Geocode** start and finish with Nominatim (free). Skipped for `lat,lon` input and for repeats (cache).
2. **Route** with the free OSRM server: a single call, cached in memory and in SQLite.
3. **Stations near the route**: the CSV is loaded once per process; a grid index over the route
   finds stations within `STATION_CORRIDOR_MILES` (default 30) in milliseconds.
4. **Optimise** (`routing/services/optimizer.py`): classic gas-station greedy, exact for continuous fuel:
   buy just enough to reach the first cheaper station in range; otherwise fill up and drive to the cheapest
   station in range; buy only what is needed to finish. Tests compare it against a brute-force DP.

External calls per new request: 1 route + up to 2 geocodes (= 3); repeat requests make 0.

## Assumptions and limits (worth saying in the Loom)

- The vehicle starts with a full 500-mile tank that is **not charged** to the trip, so trips under
  500 miles cost $0. Only fuel bought at stops is counted.
- The supplied CSV has no coordinates and its addresses are highway exits, so stations are placed at their
  **city centroid** (GeoNames). Accuracy is a few miles; the detour off the highway is not priced in.
- Duplicate rows for the same truck stop keep the lowest price.
- OSRM and Nominatim public servers are fair-use demo services. For production, self-host or use a paid plan.
- Contiguous USA only.

## Loom outline (5 min)

1. (0:30) Problem + stack: Django, OSRM, Nominatim, CSV.
2. (1:30) Postman: NYC to Chicago, then NYC to LA. Show stops, `total_cost`, `external_api_calls`, `processing_ms`. Repeat the call to show the cache.
3. (0:45) Open `/api/map/` and show the route with stops.
4. (1:45) Code: `planner.py` flow, `stations.py` grid index, `optimizer.py` greedy + brute-force test.
5. (0:30) Assumptions above.

## Known limitations and production notes

- **Corridor (30 miles):** station coordinates are city centroids, so a station can sit several miles from
  its real exit. A 30-mile corridor avoids false "no station in range" results; the cost is that a chosen
  station may be a short detour off the highway (detour fuel is not priced in).
- **Starting fuel:** the assignment does not give it. A full 50-gallon tank is assumed and not charged,
  so `total_cost` is the cost of fuel bought at stops, not the whole trip's historical fuel spend.
- **Duplicate prices:** the CSV has no timestamps, so for repeated truck-stop IDs the lowest price is used.
- **Distance along route:** station position uses geographic projection onto the OSRM polyline, scaled to
  OSRM's road distance. It is an approximation, not turn-by-turn network distance.
- **Public services:** OSRM and Nominatim demo servers are fair-use. Results are cached; production should
  self-host or use a paid plan.
- **Production hardening (not needed for the assessment):** PostgreSQL + Redis (shared cache across
  workers), authentication and rate limiting on the API.
- **US-only data:** the supplied CSV also lists Canadian truck stops (ON, AB, BC, ...). They are dropped
  when loading and when enriching, because the route is limited to the contiguous USA.
- **Nominatim rate limit:** calls to the public geocoder are spaced at least 1.1 seconds apart (policy: 1 request/second),
  so a cold request with two geocodes takes about a second longer. Cached or `lat,lon` requests are not delayed.
- **GET vs POST:** `POST /api/route/` is the main endpoint. `GET` exists for browser testing and the map page.
