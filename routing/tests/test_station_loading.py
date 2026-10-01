import csv
import tempfile
import unittest
from pathlib import Path

from routing.services.stations import load_stations


class LoadStationsTests(unittest.TestCase):
    def write_csv(self, rows):
        d = tempfile.mkdtemp()
        path = Path(d) / "s.csv"
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["opis_truckstop_id", "truckstop_name", "address", "city",
                                              "state", "rack_id", "retail_price", "latitude", "longitude"])
            w.writeheader()
            w.writerows(rows)
        return path

    def row(self, sid, state, price, lat="39.0", lon="-86.0"):
        return {"opis_truckstop_id": sid, "truckstop_name": "N" + sid, "address": "", "city": "C",
                "state": state, "rack_id": "1", "retail_price": price, "latitude": lat, "longitude": lon}

    def test_canadian_rows_are_dropped(self):
        path = self.write_csv([self.row("1", "IN", "3.1"), self.row("2", "ON", "3.0"), self.row("3", "AB", "2.9")])
        self.assertEqual([s["id"] for s in load_stations(path)], ["1"])

    def test_duplicate_ids_keep_lowest_price(self):
        path = self.write_csv([self.row("1", "TX", "3.5"), self.row("1", "TX", "3.2"), self.row("1", "TX", "3.4")])
        stations = load_stations(path)
        self.assertEqual(len(stations), 1)
        self.assertAlmostEqual(stations[0]["price_per_gallon"], 3.2)


if __name__ == "__main__":
    unittest.main()
