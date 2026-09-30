import unittest

from routing.services.gazetteer import norm_city, parse_gazetteer


def row(name, lat, lon, cls, state, pop, country="US"):
    cols = [""] * 19
    cols[0], cols[1], cols[2] = "1", name, name
    cols[4], cols[5], cols[6], cols[7], cols[8], cols[10], cols[14] = str(lat), str(lon), cls, "PPL", country, state, str(pop)
    return "\t".join(cols) + "\n"


class GazetteerTests(unittest.TestCase):
    def test_normalisation(self):
        self.assertEqual(norm_city("  Saint  Louis "), "ST LOUIS")
        self.assertEqual(norm_city("St. Louis"), "ST LOUIS")
        self.assertEqual(norm_city("Mount Vernon"), norm_city("Mt Vernon"))
        self.assertEqual(norm_city("Effingham                               "), "EFFINGHAM")

    def test_picks_most_populous_match_and_ignores_non_places(self):
        wanted = {("SPRINGFIELD", "IL")}
        lines = [
            row("Springfield", 39.8, -89.6, "P", "IL", 114000),
            row("Springfield", 40.0, -90.0, "P", "IL", 500),
            row("Springfield", 1.0, 1.0, "H", "IL", 999999),   # not a populated place
            row("Springfield", 2.0, 2.0, "P", "MO", 999999),   # wrong state
        ]
        out = parse_gazetteer(lines, wanted)
        self.assertEqual(out[("SPRINGFIELD", "IL")][:2], (39.8, -89.6))


if __name__ == "__main__":
    unittest.main()
