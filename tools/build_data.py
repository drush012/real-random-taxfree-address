"""Build data/addresses.json from OpenAddresses state extracts.

Usage: python tools/build_data.py <raw_dir> <out_file>

raw_dir must contain:
  ak.geojson.gz, de_nc.geojson.gz, de_kent.geojson.gz, de_sussex.geojson.gz,
  mt.geojson.gz, nh.geojson.gz, or.geojson.gz   (OpenAddresses batch output)
  zcta/cb_2020_us_zcta520_500k.shp              (Census ZCTA boundaries)
  geonames/US.txt                               (GeoNames US postal codes)
"""
import gzip
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import shapefile
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

PER_STATE = 5000
POOL = 60000  # random candidates per state before ZIP assignment / stratification
SEED = 20261007

STATES = {
    "AK": {"files": ["ak"], "zip_prefix": ("995", "996", "997", "998", "999")},
    "DE": {"files": ["de_nc", "de_kent", "de_sussex"], "zip_prefix": ("197", "198", "199")},
    "MT": {"files": ["mt"], "zip_prefix": ("590", "591", "592", "593", "594", "595", "596", "597", "598", "599")},
    "NH": {"files": ["nh"], "zip_prefix": ("030", "031", "032", "033", "034", "035", "036", "037", "038")},
    "OR": {"files": ["or"], "zip_prefix": ("970", "971", "972", "973", "974", "975", "976", "977", "978", "979")},
}

SUFFIX = {
    "AVENUE": "Ave", "AVE": "Ave", "AV": "Ave", "STREET": "St", "ST": "St", "ROAD": "Rd", "RD": "Rd",
    "DRIVE": "Dr", "DR": "Dr", "LANE": "Ln", "LN": "Ln", "COURT": "Ct", "CT": "Ct",
    "CIRCLE": "Cir", "CIR": "Cir", "BOULEVARD": "Blvd", "BLVD": "Blvd", "PLACE": "Pl", "PL": "Pl",
    "TERRACE": "Ter", "TER": "Ter", "HIGHWAY": "Hwy", "HWY": "Hwy", "PARKWAY": "Pkwy", "PKWY": "Pkwy",
    "WAY": "Way", "TRAIL": "Trl", "TRL": "Trl", "LOOP": "Loop", "SQUARE": "Sq", "SQ": "Sq",
    "POINT": "Pt", "PT": "Pt", "CROSSING": "Xing", "RIDGE": "Rdg", "HEIGHTS": "Hts",
    "HW": "Hwy", "RN": "Run", "ALLEY": "Aly",
}
DIRECTION = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
    "N": "N", "S": "S", "E": "E", "W": "W", "NE": "NE", "NW": "NW", "SE": "SE", "SW": "SW",
}
KEEP_UPPER = {"US", "SR", "FM", "II", "III", "IV"}


def title_word(w):
    u = w.upper()
    if u in KEEP_UPPER:
        return u
    if re.fullmatch(r"\d+(ST|ND|RD|TH)", u):
        return u[:-2] + u[-2:].lower()
    if u.startswith("MC") and len(u) > 2:
        return "Mc" + u[2:].capitalize()
    if "'" in u:
        return "'".join(p.capitalize() for p in u.split("'"))
    return u.capitalize()


def format_street(number, street):
    number = number.lstrip("0") or number  # some sources pad house numbers ("0491")
    words = street.replace(".", "").split()
    if not words:
        return None
    up = [w.upper() for w in words]
    out = []
    for i, u in enumerate(up):
        last = i == len(up) - 1
        first = i == 0
        if (first or last) and u in DIRECTION and len(up) > 1:
            out.append(DIRECTION[u])
        elif last and u in SUFFIX and len(up) > 1:
            out.append(SUFFIX[u])
        elif i == len(up) - 2 and u in SUFFIX and up[-1] in DIRECTION and len(up) > 2:
            out.append(SUFFIX[u])
        else:
            out.append(title_word(words[i]))
    return f"{number} {' '.join(out)}"


def valid_number(n):
    return bool(n) and re.fullmatch(r"\d{1,6}[A-Z]?", n.strip().upper()) is not None and n.strip() != "0"


def load_geonames(path):
    zips = {}
    with open(path, encoding="utf8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            zips[p[1]] = {"city": p[2], "state": p[4], "county": p[5]}
    return zips


def load_zcta(path, prefixes):
    r = shapefile.Reader(path)
    fields = [f[0] for f in r.fields[1:]]
    zi = fields.index("ZCTA5CE20")
    geoms, codes = [], []
    for sr in r.iterShapeRecords():
        z = sr.record[zi]
        if z.startswith(prefixes):
            geoms.append(shape(sr.shape.__geo_interface__))
            codes.append(z)
    return STRtree(geoms), geoms, codes


def candidates(raw, files, rng):
    """Reservoir-sample POOL usable records across the state's files."""
    pool, seen = [], 0
    for name in files:
        with gzip.open(raw / f"{name}.geojson.gz", "rt", encoding="utf8") as f:
            for line in f:
                d = json.loads(line)
                p = d.get("properties") or {}
                g = d.get("geometry") or {}
                if (p.get("unit") or "").strip():
                    continue
                if not valid_number(p.get("number") or "") or not (p.get("street") or "").strip():
                    continue
                if g.get("type") != "Point":
                    continue
                rec = (p["number"].strip().upper(), p["street"].strip(), (p.get("postcode") or "").strip()[:5],
                       (p.get("city") or "").strip(), tuple(g["coordinates"]))
                seen += 1
                if len(pool) < POOL:
                    pool.append(rec)
                else:
                    j = rng.randrange(seen)
                    if j < POOL:
                        pool[j] = rec
    return pool, seen


def main():
    raw, out = Path(sys.argv[1]), Path(sys.argv[2])
    rng = random.Random(SEED)
    gn = load_geonames(raw / "geonames" / "US.txt")
    result = {"source": "OpenAddresses (openaddresses.io); ZIP/city: US Census ZCTA 2020, GeoNames (CC BY 4.0)",
              "fields": ["street", "city", "zip", "county"], "states": {}}

    for code, cfg in STATES.items():
        pool, usable = candidates(raw, cfg["files"], rng)
        tree, geoms, zcodes = load_zcta(raw / "zcta" / "cb_2020_us_zcta520_500k.shp", cfg["zip_prefix"])
        by_zip = defaultdict(list)
        dedupe = set()
        for number, street, postcode, src_city, (lon, lat) in pool:
            z = postcode if re.fullmatch(r"\d{5}", postcode or "") and postcode.startswith(cfg["zip_prefix"]) else None
            if z is None:
                pt = Point(lon, lat)
                for idx in tree.query(pt):
                    if geoms[idx].contains(pt):
                        z = zcodes[idx]
                        break
            if z is None or z not in gn or gn[z]["state"] != code:
                continue
            s = format_street(number, street)
            if not s or s in dedupe:
                continue
            dedupe.add(s)
            by_zip[z].append([s, gn[z]["city"], z, gn[z]["county"]])

        # Round-robin across ZIPs so every area is represented.
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
        result["states"][code] = picked
        cities = len({r[1] for r in picked})
        print(f"{code}: usable={usable} picked={len(picked)} zips={len({r[2] for r in picked})} cities={cities}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
