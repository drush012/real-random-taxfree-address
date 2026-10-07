"""Build candidate addresses for every US state (+DC) straight from OpenAddresses.

Usage: python tools/build_us.py <raw_dir> <out_file> [STATE ...]

raw_dir must contain zcta/ and geonames/ (see build_data.py). Source files are
streamed from OpenAddresses and never written to disk. Output uses the same
schema as addresses.json so verify_census.py can run on it.
"""
import gzip
import json
import random
import re
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import shapefile
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

import build_intl
from build_data import format_street, load_geonames, valid_number

PER_STATE = 3200
POOL = 12000
MAX_STATEWIDE = 260e6
MAX_SOURCE = 160e6
MAX_SOURCES = 4
SKIP = {"AK", "DE", "MT", "NH", "OR"}  # already built and verified by build_data.py
API = "https://batch.openaddresses.io/api/data?source=us/"
DL = "https://v2.openaddresses.io/batch-prod/job/{}/source.geojson.gz"


FORCE_COUNTIES = {"OH"}  # their "statewide" file only covers a few counties


def choose_sources(sources, code=""):
    # OpenAddresses' "name" field is unreliable (e.g. us/il/city_of_chicago is tagged "state"), so trust the path only.
    statewide = [s for s in sources if "statewide" in s["source"] and s["size"] <= MAX_STATEWIDE and code not in FORCE_COUNTIES]
    exact = [s for s in statewide if s["source"].endswith("/statewide")]
    if exact:
        return [max(exact, key=lambda s: s["size"])]
    if statewide:  # split files such as statewide-east / statewide-west
        return statewide
    rest = sorted((s for s in sources if s["size"] <= MAX_SOURCE), key=lambda s: -s["size"])
    return rest[:MAX_SOURCES]


def stream_candidates(jobs, rng):
    for attempt in range(3):
        try:
            return _stream_candidates(jobs, rng)
        except (EOFError, OSError) as e:  # truncated transfer; start the state over
            print(f"  retry {attempt + 1} after: {e}", flush=True)
    raise RuntimeError(f"download kept failing for jobs {jobs}")


def _stream_candidates(jobs, rng):
    pool, seen = [], 0
    for job in jobs:
        with gzip.open(build_intl.fetch(job), "rb") as gz:  # cached, resumable download
            for raw in gz:
                d = json.loads(raw)
                p = d.get("properties") or {}
                g = d.get("geometry") or {}
                if (p.get("unit") or "").strip() or g.get("type") != "Point":
                    continue
                num, street = (p.get("number") or "").strip(), (p.get("street") or "").strip()
                if not valid_number(num) or not street:
                    continue
                rec = (num.upper(), street, (p.get("postcode") or "").strip()[:5], tuple(g["coordinates"]))
                seen += 1
                if len(pool) < POOL:
                    pool.append(rec)
                else:
                    j = rng.randrange(seen)
                    if j < POOL:
                        pool[j] = rec
    return pool, seen


def zcta_tree(path, prefixes):
    r = shapefile.Reader(path)
    zi = [f[0] for f in r.fields[1:]].index("ZCTA5CE20")
    geoms, codes = [], []
    for sr in r.iterShapeRecords():
        z = sr.record[zi]
        if z[:3] in prefixes:
            geoms.append(shape(sr.shape.__geo_interface__))
            codes.append(z)
    return STRtree(geoms), geoms, codes


def build_state(code, sources, raw, gn):
    rng = random.Random(f"us-{code}")
    picked_sources = choose_sources(sources, code)
    pool, usable = stream_candidates([s["job"] for s in picked_sources], rng)
    state_zips = {z for z, v in gn.items() if v["state"] == code}
    prefixes = {z[:3] for z in state_zips}
    tree, geoms, zcodes = zcta_tree(raw / "zcta" / "cb_2020_us_zcta520_500k.shp", prefixes)
    by_zip, dedupe = defaultdict(list), set()
    for number, street, postcode, (lon, lat) in pool:
        z = postcode if postcode in state_zips else None
        if z is None:
            pt = Point(lon, lat)
            for idx in tree.query(pt):
                if geoms[idx].contains(pt):
                    z = zcodes[idx]
                    break
        if z not in state_zips:
            continue
        s = format_street(number, street)
        if not s or s in dedupe:
            continue
        dedupe.add(s)
        by_zip[z].append([s, gn[z]["city"], z, gn[z]["county"]])
    for v in by_zip.values():
        rng.shuffle(v)
    zips = sorted(by_zip)
    rng.shuffle(zips)
    picked, i = [], 0
    while len(picked) < PER_STATE and any(by_zip[z] for z in zips):
        z = zips[i % len(zips)]
        if by_zip[z]:
            picked.append(by_zip[z].pop())
        i += 1
    rng.shuffle(picked)
    names = ",".join(s["source"].split("/", 2)[2] for s in picked_sources)
    print(f"{code}: sources=[{names}] usable={usable} picked={len(picked)} zips={len({r[2] for r in picked})}", flush=True)
    return code, picked


def main():
    raw, out = Path(sys.argv[1]), Path(sys.argv[2])
    build_intl.CACHE = raw / "cache"
    build_intl.CACHE.mkdir(exist_ok=True)
    only = {s.upper() for s in sys.argv[3:]}
    gn = load_geonames(raw / "geonames" / "US.txt")
    all_sources = json.load(urllib.request.urlopen(API, timeout=120))
    by_state = defaultdict(list)
    for s in all_sources:
        parts = s["source"].split("/")
        if s["layer"] == "addresses" and s.get("size") and len(parts) == 3:
            by_state[parts[1].upper()].append(s)
    codes = sorted(c for c in by_state if c != "PR" and c not in SKIP and (not only or c in only))
    result = {"states": {}}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(build_state, c, by_state[c], raw, gn) for c in codes]
        for f in futures:
            try:
                code, picked = f.result()
                result["states"][code] = picked
            except Exception as e:  # keep going; report at the end
                print("FAILED", type(e).__name__, e, flush=True)
    out.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    missing = [c for c in codes if c not in result["states"]]
    print(f"wrote {out}; missing: {missing}")


if __name__ == "__main__":
    main()
