"""Collect addresses from BBBike city extracts of OpenStreetMap (.osm.pbf).

Usage: python tools/build_pbf.py <raw_dir> <country> [<country> ...]
Downloads https://download.bbbike.org/osm/bbbike/<City>/<City>.osm.pbf into <raw_dir>/cache
and writes <raw_dir>/intl_<country>_pbf.json with the same row layout as build_osm.py:
[housenumber, street, postcode, city, suburb, state]. Used where the Overpass API is too slow.
Address data © OpenStreetMap contributors, ODbL.
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import osmium

TARGET = 3000
# country: {slug: (BBBike name, default city, state)}
EXTRACTS = {
    "gb": {
        "london": ("London", "London", "England"),
        "manchester": ("Manchester", "Manchester", "England"),
        "birmingham": ("Birmingham", "Birmingham", "England"),
        "edinburgh": ("Edinburgh", "Edinburgh", "Scotland"),
        "glasgow": ("Glasgow", "Glasgow", "Scotland"),
    },
    "tr": {"istanbul": ("Istanbul", "İstanbul", "İstanbul")},
}
POSTCODE = {"gb": r"[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}", "tr": r"\d{5}"}

# Extracts are rectangles that spill into neighbouring towns; keep only postcode districts
# whose post town is the city itself (e.g. Edinburgh = EH1-EH17, not KY11 in Fife).
GB_CORE = {
    "London": lambda a, n: a in {"E", "EC", "N", "NW", "SE", "SW", "W", "WC"},
    "Manchester": lambda a, n: a == "M" and 1 <= n <= 23,
    "Birmingham": lambda a, n: a == "B" and 1 <= n <= 48,
    "Edinburgh": lambda a, n: a == "EH" and 1 <= n <= 17,
    "Glasgow": lambda a, n: a == "G" and 1 <= n <= 53,
}


def fetch(cache, name):
    path = cache / f"bbbike_{name}.osm.pbf"
    if path.exists():
        return path
    part = path.with_suffix(".part")
    url = f"https://download.bbbike.org/osm/bbbike/{name}/{name}.osm.pbf"
    for attempt in range(10):
        if subprocess.run(["curl", "-sL", "-C", "-", "--retry", "5", "--max-time", "3600", "-o", str(part), url]).returncode == 0:
            part.rename(path)
            return path
        print(f"  resume {attempt + 1} {name}", flush=True)
    raise RuntimeError(f"could not download {name}")


class Collector(osmium.SimpleHandler):
    def __init__(self, cc, city, state, rng):
        super().__init__()
        self.cc, self.city, self.state, self.rng = cc, city, state, rng
        self.pool, self.seen, self.keys = [], 0, set()

    def take(self, tags):
        num, street = tags.get("addr:housenumber", "").strip(), tags.get("addr:street", "").strip()
        pc = tags.get("addr:postcode", "").strip().upper()
        if not num or not street or not re.fullmatch(r"\d{1,5}[A-Za-z]?(/\d+)?(-\d+)?", num) or len(street) < 3:
            return
        if not re.fullmatch(POSTCODE[self.cc], pc):
            return
        city = tags.get("addr:city", "").strip() or self.city
        if self.cc == "gb":
            m = re.match(r"([A-Z]{1,2})(\d+)", pc)
            if city != self.city or not GB_CORE[self.city](m.group(1), int(m.group(2))):
                return
            if " " not in pc:
                pc = f"{pc[:-3]} {pc[-3:]}"
        key = (num, street, city)
        if key in self.keys:
            return
        self.keys.add(key)
        suburb = (tags.get("addr:suburb") or tags.get("addr:district") or tags.get("addr:neighbourhood") or "").strip()
        row = [num, street, pc, city, suburb, self.state]
        self.seen += 1
        if len(self.pool) < TARGET:
            self.pool.append(row)
        else:
            j = self.rng.randrange(self.seen)
            if j < TARGET:
                self.pool[j] = row

    def node(self, n):
        if "addr:housenumber" in n.tags:
            self.take(n.tags)

    def way(self, w):
        if "addr:housenumber" in w.tags:
            self.take(w.tags)


def build(cc, raw):
    cache = raw / "cache"
    cache.mkdir(exist_ok=True)
    rng = random.Random(f"pbf-{cc}")
    result = {"states": {}}
    for slug, (name, city, state) in EXTRACTS[cc].items():
        path = fetch(cache, name)
        h = Collector(cc, city, state, rng)
        h.apply_file(str(path))
        result["states"][slug] = h.pool
        print(f"{cc} {slug}: {h.seen} usable, kept {len(h.pool)}", flush=True)
    (raw / f"intl_{cc}_pbf.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")


if __name__ == "__main__":
    raw_dir = Path(sys.argv[1])
    for c in sys.argv[2:]:
        build(c, raw_dir)
