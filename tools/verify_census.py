"""Keep only addresses the US Census geocoder matches exactly; take its ZIP.

Usage: python tools/verify_census.py public/data/addresses.json
Rewrites the file in place.
"""
import csv
import io
import json
import re
import sys
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BATCH = 2500


def format_city(name):
    """MCMINNVILLE -> McMinnville, MC LEOD -> McLeod."""
    city = re.sub(r"\bMC ", "MC", name.upper()).title()
    return re.sub(r"\bMc([a-z])", lambda m: "Mc" + m.group(1).upper(), city)


def geocode(rows):
    """rows: list of (id, street, city, state, zip) -> {id: (matched_zip, matched_city)}"""
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"benchmark\"\r\n\r\nPublic_AR_Current\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"addressFile\"; filename=\"a.csv\"\r\n"
        f"Content-Type: text/csv\r\n\r\n{buf.getvalue()}\r\n--{boundary}--\r\n"
    ).encode("utf8")
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            text = urllib.request.urlopen(req, timeout=900).read().decode("utf8", "replace")
            break
        except Exception as e:  # the service is flaky under load
            print("  retry", attempt + 1, e)
            time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError("Census batch geocoder failed")
    out = {}
    for rec in csv.reader(io.StringIO(text)):
        if len(rec) >= 5 and rec[2] == "Match" and rec[3] == "Exact":
            parts = [p.strip() for p in rec[4].split(",")]
            if len(parts) >= 4 and parts[-1].isdigit():
                out[rec[0]] = (parts[-1], format_city(parts[-3]))
    return out


def main():
    path = sys.argv[1]
    data = json.load(open(path, encoding="utf8"))
    jobs, rows = [], []
    for st, recs in data["states"].items():
        for i, r in enumerate(recs):
            rows.append((f"{st}:{i}", r[0], r[1], st, r[2]))
    for i in range(0, len(rows), BATCH):
        jobs.append(rows[i:i + BATCH])
    matched = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for n, res in enumerate(ex.map(geocode, jobs), 1):
            matched.update(res)
            print(f"batch {n}/{len(jobs)} done, matched so far {len(matched)}")
    for st, recs in data["states"].items():
        kept = []
        for i, r in enumerate(recs):
            m = matched.get(f"{st}:{i}")
            if m:
                zip_code, city = m
                kept.append([r[0], city, zip_code, r[3]])
        print(f"{st}: {len(kept)}/{len(recs)} verified")
        data["states"][st] = kept
    data["verified"] = "US Census Geocoder (Public_AR_Current), exact matches only"
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
