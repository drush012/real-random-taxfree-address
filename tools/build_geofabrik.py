"""Collect city addresses from Geofabrik country extracts of OpenStreetMap.

Usage: python tools/build_geofabrik.py <raw_dir> <country> [<country> ...]
Writes <raw_dir>/intl_<country>_gf.json with build_osm.py's row layout:
[housenumber, street, postcode, city, suburb, state]. Cities and bounding boxes come
from build_osm.CITIES; an address is kept when its point (or a way's first node) is inside one.
Address data © OpenStreetMap contributors, ODbL.
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import osmium

from build_osm import CITIES, NEED_POSTCODE, POSTCODE

TARGET = 3000
EXTRACTS = {
    "ph": ["asia/philippines"],
    "ng": ["africa/nigeria"],
    "tr": ["europe/turkey"],
    "in": ["asia/india/western-zone", "asia/india/northern-zone", "asia/india/southern-zone", "asia/india/eastern-zone"],
}


def fetch(cache, region):
    path = cache / ("gf_" + region.replace("/", "_") + ".osm.pbf")
    if path.exists():
        return path
    part = path.with_suffix(".part")
    url = f"https://download.geofabrik.de/{region}-latest.osm.pbf"
    for attempt in range(20):
        if subprocess.run(["curl", "-sL", "-C", "-", "--retry", "5", "--max-time", "7200", "-o", str(part), url]).returncode == 0:
            part.rename(path)
            return path
        print(f"  resume {attempt + 1} {region}", flush=True)
    raise RuntimeError(f"could not download {region}")


class Collector(osmium.SimpleHandler):
    def __init__(self, cc, rng):
        super().__init__()
        self.cc, self.rng = cc, rng
        self.cities = CITIES[cc]
        self.pools = {slug: [] for slug in self.cities}
        self.seen = {slug: 0 for slug in self.cities}
        self.keys = set()

    def city_at(self, lat, lon):
        for slug, (_, _, (s, w, n, e)) in self.cities.items():
            if s <= lat <= n and w <= lon <= e:
                return slug
        return None

    def take(self, tags, loc):
        if not loc.valid():
            return
        slug = self.city_at(loc.lat, loc.lon)
        if not slug:
            return
        num, street = tags.get("addr:housenumber", "").strip(), tags.get("addr:street", "").strip()
        pc = tags.get("addr:postcode", "").strip().upper()
        if not re.fullmatch(r"\d{1,5}[A-Za-z]?(/\d+)?(-\d+)?", num) or len(street) < 3:
            return
        if pc and not re.fullmatch(POSTCODE[self.cc], pc):
            pc = ""
        if self.cc in NEED_POSTCODE and not pc:
            return
        city_default, state, _ = self.cities[slug]
        city = tags.get("addr:city", "").strip() or city_default
        key = (num, street, city)
        if key in self.keys:
            return
        self.keys.add(key)
        suburb = (tags.get("addr:suburb") or tags.get("addr:district") or tags.get("addr:neighbourhood") or "").strip()
        row = [num, street, pc, city, suburb, state]
        self.seen[slug] += 1
        pool = self.pools[slug]
        if len(pool) < TARGET:
            pool.append(row)
        else:
            j = self.rng.randrange(self.seen[slug])
            if j < TARGET:
                pool[j] = row

    def node(self, n):
        if "addr:housenumber" in n.tags:
            self.take(n.tags, n.location)

    def way(self, w):
        if "addr:housenumber" in w.tags and len(w.nodes):
            self.take(w.tags, w.nodes[0].location)


def build(cc, raw):
    cache = raw / "cache"
    cache.mkdir(exist_ok=True)
    h = Collector(cc, random.Random(f"gf-{cc}"))
    for region in EXTRACTS[cc]:
        path = fetch(cache, region)
        print(f"{cc}: reading {path.name}", flush=True)
        h.apply_file(str(path), locations=True, idx="flex_mem")
    result = {"states": {slug: rows for slug, rows in h.pools.items() if len(rows) >= 100}}
    for slug in h.pools:
        print(f"{cc} {slug}: {h.seen[slug]} usable, kept {len(h.pools[slug])}", flush=True)
    (raw / f"intl_{cc}_gf.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")


if __name__ == "__main__":
    raw_dir = Path(sys.argv[1])
    for c in sys.argv[2:]:
        build(c, raw_dir)
