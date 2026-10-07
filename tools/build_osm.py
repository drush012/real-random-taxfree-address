"""Collect real addresses for main cities from OpenStreetMap (Overpass API).

Usage: python tools/build_osm.py <raw_dir> <country> [<country> ...]
Writes <raw_dir>/intl_<country>.json ({"states": {city_slug: [row, ...]}}).
Row: [housenumber, street, postcode, city, suburb, state]

Each city's bounding box is split into a GRID x GRID grid and queried tile by tile so the
sample is spread across the city instead of clustering in one neighbourhood.
Address data © OpenStreetMap contributors, ODbL.
"""
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
TILES = 40      # random small tiles per city
PER_TILE = 150
TARGET = 3000

# slug: (default city name, state/region, (south, west, north, east))
CITIES = {
    "gb": {
        "london": ("London", "England", (51.38, -0.30, 51.62, 0.10)),
        "manchester": ("Manchester", "England", (53.40, -2.32, 53.53, -2.15)),
        "birmingham": ("Birmingham", "England", (52.40, -2.03, 52.56, -1.73)),
        "edinburgh": ("Edinburgh", "Scotland", (55.89, -3.33, 55.99, -3.08)),
        "glasgow": ("Glasgow", "Scotland", (55.82, -4.38, 55.90, -4.15)),
    },
    "in": {
        "mumbai": ("Mumbai", "Maharashtra", (18.90, 72.80, 19.25, 72.98)),
        "delhi": ("New Delhi", "Delhi", (28.50, 77.05, 28.75, 77.30)),
        "bengaluru": ("Bengaluru", "Karnataka", (12.85, 77.48, 13.08, 77.72)),
        "chennai": ("Chennai", "Tamil Nadu", (12.95, 80.18, 13.15, 80.30)),
        "hyderabad": ("Hyderabad", "Telangana", (17.32, 78.35, 17.50, 78.55)),
        "kolkata": ("Kolkata", "West Bengal", (22.48, 88.30, 22.62, 88.42)),
    },
    "ng": {
        "lagos": ("Lagos", "Lagos", (6.42, 3.30, 6.65, 3.55)),
        "abuja": ("Abuja", "FCT", (8.95, 7.35, 9.12, 7.55)),
        "ibadan": ("Ibadan", "Oyo", (7.33, 3.85, 7.45, 3.98)),
        "port-harcourt": ("Port Harcourt", "Rivers", (4.76, 6.95, 4.88, 7.08)),
    },
    "ph": {
        "metro-manila": ("Manila", "Metro Manila", (14.50, 120.97, 14.68, 121.10)),
        "cebu": ("Cebu City", "Cebu", (10.28, 123.85, 10.36, 123.93)),
        "davao": ("Davao City", "Davao del Sur", (7.03, 125.55, 7.12, 125.65)),
    },
    "tr": {  # İstanbul comes from the BBBike extract (build_pbf.py)
        "ankara": ("Ankara", "Ankara", (39.85, 32.70, 40.00, 32.95)),
        "izmir": ("İzmir", "İzmir", (38.38, 27.05, 38.48, 27.20)),
    },
}

POSTCODE = {
    "gb": r"[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}",
    "in": r"\d{6}",
    "ng": r"\d{6}",
    "ph": r"\d{4}",
    "tr": r"\d{5}",
}
NEED_POSTCODE = {"gb", "in", "tr", "ph"}  # Nigerian addresses rarely carry one


def overpass(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(3):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"User-Agent": "taxfree-address-builder"}), timeout=90) as r:
                body = r.read()
            if not body.lstrip().startswith(b"{"):  # Overpass reports overload as an HTML page with status 200
                raise ValueError("non-JSON response")
            return json.loads(body)["elements"]
        except Exception as e:
            print(f"    overpass retry {attempt + 1}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    return []


def tiles(bbox, n, rng, size=0.012):
    """n random ~1 km tiles inside bbox; small tiles keep each Overpass query cheap."""
    s, w, nth, e = bbox
    for _ in range(n):
        lat = s + rng.random() * max(nth - s - size, 0)
        lon = w + rng.random() * max(e - w - size, 0)
        yield (lat, lon, lat + size, lon + size)


def build(cc, raw):
    rng = random.Random(f"osm-{cc}")
    result = {"states": {}}
    for slug, (city, state, bbox) in CITIES[cc].items():
        rows, seen = [], set()
        pc_filter = '["addr:postcode"]' if cc in NEED_POSTCODE else ""
        for t in tiles(bbox, TILES, rng):
            if len(rows) >= TARGET:
                break
            # Small tiles and a server-side postcode filter keep each query well under Overpass' limits.
            q = (f'[out:json][timeout:90];nw["addr:housenumber"]["addr:street"]{pc_filter}'
                 f'({t[0]:.4f},{t[1]:.4f},{t[2]:.4f},{t[3]:.4f});out tags {PER_TILE};')
            for el in overpass(q):
                tg = el.get("tags", {})
                num, street = tg.get("addr:housenumber", "").strip(), tg.get("addr:street", "").strip()
                pc = tg.get("addr:postcode", "").strip().upper()
                if not re.fullmatch(r"\d{1,5}[A-Za-z]?(/\d+)?(-\d+)?", num) or len(street) < 3:
                    continue
                if pc and not re.fullmatch(POSTCODE[cc], pc):
                    pc = ""
                if cc in NEED_POSTCODE and not pc:
                    continue
                row = [num, street, pc, tg.get("addr:city", "").strip() or city,
                       (tg.get("addr:suburb") or tg.get("addr:district") or tg.get("addr:neighbourhood") or "").strip(), state]
                key = (num, street, row[3])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
            time.sleep(1)
        rng.shuffle(rows)
        result["states"][slug] = rows[:TARGET]
        print(f"{cc} {slug}: {len(rows)} found, kept {len(result['states'][slug])}", flush=True)
    result["states"] = {k: v for k, v in result["states"].items() if len(v) >= 100}
    (raw / f"intl_{cc}.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")


if __name__ == "__main__":
    raw_dir = Path(sys.argv[1])
    for c in sys.argv[2:]:
        build(c, raw_dir)
