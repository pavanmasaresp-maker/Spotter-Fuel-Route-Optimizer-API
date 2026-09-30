"""Adds latitude/longitude to the supplied fuel price CSV (run once, commit the output).

Method: geocode each unique (city, state) to its centroid using the free GeoNames US
gazetteer (one download, no rate limit). Anything unmatched falls back to Nominatim
(1 request/second, capped by --nominatim-limit).
"""
import csv
import io
import time
import zipfile

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from routing.services.gazetteer import norm_city, parse_gazetteer
from routing.services.stations import DATA_DIR, ENRICHED

GEONAMES_URL = "https://download.geonames.org/export/dump/US.zip"
SOURCE = DATA_DIR / "fuel_prices.csv"
CACHE_DIR = DATA_DIR / "cache"


def _norm_row(row):
    return {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items() if k}


class Command(BaseCommand):
    help = "Geocode fuel stations by city centroid and write data/fuel_prices_enriched.csv"

    def add_arguments(self, parser):
        parser.add_argument("--gazetteer", help="Path to an already-downloaded GeoNames US.zip")
        parser.add_argument("--nominatim-limit", type=int, default=400,
                            help="Max fallback lookups for cities missing from GeoNames")

    def handle(self, *args, **opts):
        with SOURCE.open(encoding="utf-8-sig", newline="") as f:
            rows = [_norm_row(r) for r in csv.DictReader(f)]

        # one row per truck stop, lowest price wins
        best = {}
        for r in rows:
            try:
                price = float(r["retail_price"])
            except (KeyError, ValueError):
                continue
            sid = r["opis_truckstop_id"]
            if sid not in best or price < float(best[sid]["retail_price"]):
                best[sid] = r
        stations = list(best.values())
        wanted = {(norm_city(r["city"]), r["state"].upper()) for r in stations}
        self.stdout.write(f"{len(stations)} stations, {len(wanted)} unique city/state pairs")

        zip_path = opts["gazetteer"] or self._download()
        with zipfile.ZipFile(zip_path) as z, z.open("US.txt") as raw:
            found = parse_gazetteer(io.TextIOWrapper(raw, encoding="utf-8"), wanted)
        self.stdout.write(f"GeoNames matched {len(found)}/{len(wanted)} cities")

        missing = sorted(wanted - set(found))
        used = 0
        for city, state in missing[: opts["nominatim_limit"]]:
            hit = self._nominatim(city, state)
            used += 1
            if hit:
                found[(city, state)] = (hit[0], hit[1], 0)
            time.sleep(1.1)  # Nominatim usage policy: max 1 request/second
        if used:
            self.stdout.write(f"Nominatim fallback: {used} lookups, matched {len(found)}/{len(wanted)} total")

        fields = ["opis_truckstop_id", "truckstop_name", "address", "city", "state",
                  "rack_id", "retail_price", "latitude", "longitude"]
        kept = 0
        with ENRICHED.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in stations:
                hit = found.get((norm_city(r["city"]), r["state"].upper()))
                if not hit:
                    continue
                w.writerow({**{k: r.get(k, "") for k in fields[:7]},
                            "latitude": round(hit[0], 5), "longitude": round(hit[1], 5)})
                kept += 1
        if not kept:
            raise CommandError("No stations could be geocoded.")
        self.stdout.write(self.style.SUCCESS(f"Wrote {kept}/{len(stations)} stations -> {ENRICHED}"))

    def _download(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / "US.zip"
        if path.exists():
            return path
        self.stdout.write("Downloading GeoNames US gazetteer (one time)...")
        try:
            with requests.get(GEONAMES_URL, stream=True, timeout=120) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        except requests.RequestException as exc:
            path.unlink(missing_ok=True)
            raise CommandError(f"Could not download GeoNames data: {exc}") from exc
        return path

    def _nominatim(self, city, state):
        try:
            r = requests.get(
                settings.NOMINATIM_URL + "/search",
                params={"city": city.title(), "state": state, "country": "USA", "format": "jsonv2", "limit": 1},
                headers={"User-Agent": settings.GEOCODER_USER_AGENT}, timeout=10)
            r.raise_for_status()
            data = r.json()
            return (float(data[0]["lat"]), float(data[0]["lon"])) if data else None
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return None
