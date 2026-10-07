"""Write one JSON file per region plus manifest.json for the front end.

Usage: python tools/split_regions.py <out_dir> <combined.json> [<combined.json> ...]

Each combined file has the shape {"states": {CODE: [row, ...]}} (as produced by
build_data.py / build_us.py / verify_census.py). Later files win on duplicate codes.
Rows are [street, city, ...]; city (index 1) is used for the city count.
"""
import json
import sys
from pathlib import Path


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    regions = {}
    for path in sys.argv[2:]:
        regions.update(json.load(open(path, encoding="utf8"))["states"])
    manifest = {"regions": {}, "cities": {}}
    for code in sorted(regions):
        rows = regions[code]
        (out / f"{code}.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
        manifest["regions"][code] = len(rows)
        manifest["cities"][code] = len({r[1] for r in rows})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(f"{len(regions)} regions, {sum(manifest['regions'].values())} rows -> {out}")


if __name__ == "__main__":
    main()
