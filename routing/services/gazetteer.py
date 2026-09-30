"""City-centroid lookup from the free GeoNames US gazetteer (no Django imports).

The supplied fuel CSV has highway-exit addresses ("I-44, EXIT 283 & US-69"), which street
geocoders such as the Census geocoder cannot match. City + state centroids are accurate
to a few miles, which is enough for a 15-mile route corridor.
"""
import re
import unicodedata

_ABBR = [(r"\bSAINT\b", "ST"), (r"\bSTE\b", "ST"), (r"\bMOUNT\b", "MT"),
         (r"\bFORT\b", "FT"), (r"\bPOINT\b", "PT")]


def norm_city(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[.'`]", "", s)
    s = re.sub(r"[-/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for pattern, repl in _ABBR:
        s = re.sub(pattern, repl, s)
    return s


def parse_gazetteer(lines, wanted):
    """lines: GeoNames tab-separated rows. wanted: set of (norm_city, STATE).

    Returns {(norm_city, STATE): (lat, lon, population)}, keeping the most populous match.
    """
    out = {}
    for line in lines:
        p = line.rstrip("\n").split("\t")
        if len(p) < 15 or p[6] != "P" or p[8] != "US":
            continue
        state = p[10]
        try:
            pop = int(p[14] or 0)
            lat, lon = float(p[4]), float(p[5])
        except ValueError:
            continue
        for name in (p[1], p[2]):
            key = (norm_city(name), state)
            if key in wanted:
                cur = out.get(key)
                if cur is None or pop > cur[2]:
                    out[key] = (lat, lon, pop)
    return out
