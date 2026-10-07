"""Build per-region address rows for non-US countries from OpenAddresses.

Usage: python tools/build_intl.py <raw_dir> <country> [<country> ...]
Writes <raw_dir>/intl_<country>.json in the {"states": {REGION: [row, ...]}} shape
that split_regions.py turns into public/data/<country>/.

raw_dir must contain (only for the countries you build):
  geonames_DE/DE.txt            GeoNames postal codes (Germany)
  tw_county_en.xml              Chunghwa Post County_h_10906.xml (TW postcodes + English names)
Row layouts are documented next to each handler and mirrored in public/assets/countries.js.
"""
import gzip
import json
import random
import re
import subprocess
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

TARGET = 3000          # rows kept per region
POOL = 9000            # reservoir per region per source
API = "https://batch.openaddresses.io/api/data?source={}/"
DL = "https://v2.openaddresses.io/batch-prod/job/{}/source.geojson.gz"


def sources(cc):
    cached = CACHE.parent / f"{cc}_sources.json"
    if cached.exists():
        data = json.load(open(cached))
    else:
        for attempt in range(5):
            try:
                data = json.load(urllib.request.urlopen(API.format(cc), timeout=120))
                break
            except Exception as e:  # flaky connection; try again
                print(f"  source list retry {attempt + 1}: {e}", flush=True)
        else:
            raise RuntimeError(f"could not list sources for {cc}")
        json.dump(data, open(cached, "w"))
    return [s for s in data if s["layer"] == "addresses" and s.get("size") and s["source"].startswith(cc + "/")]


def job_of(cc, source):
    """Newest job id for an exact source path."""
    return max(s["job"] for s in sources(cc) if s["source"] == source)


CACHE = None  # set in __main__ to <raw_dir>/cache


def fetch(job):
    """Download a job's output once, resuming after dropped connections; returns the local path."""
    path = CACHE / f"{job}.geojson.gz"
    if path.exists():
        return path
    tmp = path.with_suffix(".part")
    for attempt in range(8):
        r = subprocess.run(["curl", "-sL", "-C", "-", "--retry", "5", "--max-time", "3600", "-o", str(tmp), DL.format(job)])
        if r.returncode == 0:
            try:
                with gzip.open(tmp) as g:
                    while g.read(1 << 24):
                        pass
                tmp.rename(path)
                return path
            except (EOFError, OSError):
                pass  # incomplete; resume
        print(f"  resume {attempt + 1} job {job}", flush=True)
    raise RuntimeError(f"could not download job {job}")


def stream(job):
    """Yield (properties, lon, lat) for every point record of an OpenAddresses job."""
    with gzip.open(fetch(job), "rb") as gz:
        for raw in gz:
            d = json.loads(raw)
            g = d.get("geometry") or {}
            if g.get("type") != "Point":
                continue
            lon, lat = g["coordinates"][:2]
            yield d.get("properties") or {}, lon, lat


def sample_job(job, handler, rng):
    """Reservoir-sample handler output per region for one job; retries truncated downloads."""
    for attempt in range(3):
        pools, seen = defaultdict(list), defaultdict(int)
        try:
            for p, lon, lat in stream(job):
                out = handler(p, lon, lat)
                if not out:
                    continue
                region, key, row = out
                seen[region] += 1
                pool = pools[region]
                if len(pool) < POOL:
                    pool.append((key, row))
                else:
                    j = rng.randrange(seen[region])
                    if j < POOL:
                        pool[j] = (key, row)
            return pools
        except (EOFError, OSError) as e:
            print(f"  retry {attempt + 1} job {job}: {e}", flush=True)
    raise RuntimeError(f"job {job} kept failing")


def stratify(items, rng, target=TARGET):
    """items: [(key, row)]; dedupe rows, then round-robin across keys (postcode/district)."""
    by_key, seen = defaultdict(list), set()
    for key, row in items:
        sig = json.dumps(row, ensure_ascii=False)
        if sig in seen:
            continue
        seen.add(sig)
        by_key[key].append(row)
    for v in by_key.values():
        rng.shuffle(v)
    keys = list(by_key)
    rng.shuffle(keys)
    picked, i = [], 0
    while len(picked) < target and any(by_key[k] for k in keys):
        k = keys[i % len(keys)]
        if by_key[k]:
            picked.append(by_key[k].pop())
        i += 1
    rng.shuffle(picked)
    return picked


def run(cc, jobs, handler, raw):
    rng = random.Random(f"intl-{cc}")
    merged = defaultdict(list)
    for job in jobs:
        for region, pool in sample_job(job, handler, rng).items():
            merged[region].extend(pool)
    result = {"states": {}}
    for region in sorted(merged):
        rows = stratify(merged[region], rng)
        if len(rows) >= 50:
            result["states"][region] = rows
        print(f"{cc} {region}: pool={len(merged[region])} kept={len(rows)}", flush=True)
    out = raw / f"intl_{cc}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(f"{cc}: wrote {out} regions={len(result['states'])} rows={sum(map(len, result['states'].values()))}", flush=True)


# ---------------------------------------------------------------- helpers

def nfkc(s):
    return unicodedata.normalize("NFKC", s or "").strip()


SMALL = {"of", "and", "the", "de", "du", "des", "la", "le", "les", "et", "d'", "l'"}


def title(s):
    words = nfkc(s).lower().split()
    out = []
    for i, w in enumerate(words):
        if i and w in SMALL:
            out.append(w)
        elif re.fullmatch(r"\d+(st|nd|rd|th|e|er)", w):
            out.append(w)
        elif w.startswith("mc") and len(w) > 2:
            out.append("Mc" + w[2:].capitalize())
        else:
            out.append("-".join(x[:1].upper() + x[1:] for x in w.split("-")))
    return " ".join(out)


def num_ok(n):
    return bool(re.fullmatch(r"\d{1,5}[A-Za-z]?(-\d{1,4}[A-Za-z]?)?", n or ""))


# ---------------------------------------------------------------- Hong Kong
# Region = district slug. Row: [number, street_en, street_zh, area_en, area_zh]
# The en and zh files are the same rows in the same order; they are zipped together.

def build_hk(raw):
    srcs = {s["source"]: s["job"] for s in sources("hk")}
    def load(src):
        return [(p, lon, lat) for p, lon, lat in stream(srcs[src])]
    en, zh = load("hk/countrywide-en"), load("hk/countrywide-zh")
    assert len(en) == len(zh), (len(en), len(zh))
    rng = random.Random("intl-hk")
    merged, names = defaultdict(list), {}
    for (pe, *_), (pz, *_) in zip(en, zh):
        if pe.get("number") != pz.get("number") or not num_ok(pe.get("number")) or not pe.get("street") or not pz.get("street"):
            continue
        d_en = title(pe["district"]).replace(" District", "")
        slug = re.sub(r"[^a-z]+", "-", d_en.lower()).strip("-")
        names[slug] = {"en": d_en, "zh": nfkc(pz["district"]), "area_en": {"HK": "Hong Kong Island", "KLN": "Kowloon", "NT": "New Territories"}.get(pe["region"], pe["region"]), "area_zh": nfkc(pz["region"])}
        row = [pe["number"], title(pe["street"]), nfkc(pz["street"]), title(pe.get("city") or ""), nfkc(pz.get("city") or "")]
        merged[slug].append((row[1], row))
    result = {"states": {}, "regions": names}
    for slug in sorted(merged):
        result["states"][slug] = stratify(merged[slug], rng)
        print(f"hk {slug} {names[slug]['zh']}: {len(result['states'][slug])}", flush=True)
    (raw / "intl_hk.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")


# ---------------------------------------------------------------- Singapore
# Region "SG". Row: [number, street, building, postcode]

def build_sg(raw):
    def h(p, lon, lat):
        pc, num, street = p.get("postcode") or "", p.get("number") or "", p.get("street") or ""
        if not re.fullmatch(r"\d{6}", pc) or not num_ok(num) or not street:
            return None
        bld = title(p.get("unit") or "")
        if re.search(r"temporary|site office|\bnil\b|^-$", bld, re.I):
            bld = ""
        return "SG", pc[:2], [num, title(street), bld.split(",")[0].strip(), pc]
    run("sg", [s["job"] for s in sources("sg")], h, raw)


# ---------------------------------------------------------------- Japan
# Region = prefecture slug. Row: [city, town, chome, number, postcode, city_en, town_en]
# Prefecture files carry no postcodes; Japan Post's KEN_ALL_ROME gives postcode + romaji for
# (prefecture, city, town). Only towns that map to exactly one postcode are kept.

JP_PREFS = {"tokyo": "東京都", "osaka": "大阪府", "kanagawa": "神奈川県", "kyoto": "京都府", "fukuoka": "福岡県", "hokkaido": "北海道"}
KANJI_DIGITS = str.maketrans("〇一二三四五六七八九", "0123456789")


def jp_key(s):
    return nfkc(s).translate(KANJI_DIGITS).replace(" ", "").replace("　", "")


def jp_roman_city(s):
    parts = s.split()
    out = []
    for w in parts:
        if w in ("SHI", "KU", "CHO", "MACHI", "SON", "MURA", "GUN") and out:
            out[-1] += "-" + w.lower()
        else:
            out.append(w.capitalize())
    return " ".join(out)


def build_jp(raw):
    import csv
    path = next((raw / "ken_all_rome").glob("*.CSV"))
    table = defaultdict(set)
    for r in csv.reader(open(path, encoding="cp932")):
        zip7, pref, city, town, _, city_r, town_r = r[:7]
        if "以下に掲載がない場合" in town or "次に番地がくる場合" in town:
            continue
        town = re.sub(r"（.*?）|\(.*?\)", "", town)
        town_r = re.sub(r"\(.*?\)", "", town_r).strip()
        table[(pref, jp_key(city), jp_key(town))].add((zip7, jp_roman_city(city_r), town_r.title()))
    rng = random.Random("intl-jp")
    merged = defaultdict(list)
    for slug, pref in JP_PREFS.items():
        def h(p, lon, lat, pref=pref, slug=slug):
            street, number, city = nfkc(p.get("street")), nfkc(p.get("number")), nfkc(p.get("city"))
            m = re.fullmatch(r"(.+?)(\d+)丁目", street.translate(KANJI_DIGITS))
            town, chome = (m.group(1), m.group(2)) if m else (street, "")
            hit = table.get((pref, jp_key(city), jp_key(town)))
            if not hit or len(hit) != 1 or not re.fullmatch(r"\d+(-\d+){0,2}", number):
                return None
            zip7, city_en, town_en = next(iter(hit))
            return slug, zip7[:5], [city, town, chome, number, f"{zip7[:3]}-{zip7[3:]}", city_en, town_en]
        for region, pool in sample_job(job_of("jp", f"jp/{slug}"), h, rng).items():
            merged[region].extend(pool)
        print(f"jp {slug}: pool={len(merged[slug])}", flush=True)
    result = {"states": {r: stratify(v, rng) for r, v in merged.items()}}
    (raw / "intl_jp.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print("jp done", {r: len(v) for r, v in result["states"].items()}, flush=True)


# ---------------------------------------------------------------- South Korea
# Region = city slug. Row: [district (gu), dong, road, number, postcode]

KR_CITIES = {"11": "seoul", "26": "busan", "27": "daegu", "28": "incheon"}


def build_kr(raw):
    rng = random.Random("intl-kr")
    merged = defaultdict(list)
    for code, slug in KR_CITIES.items():
        def h(p, lon, lat, slug=slug):
            pc = p.get("postcode") or ""
            if not re.fullmatch(r"\d{5}", pc) or not p.get("street") or not num_ok(p.get("number")):
                return None
            return slug, pc[:3], [p.get("city") or "", p.get("district") or "", p["street"], p["number"], pc]
        for region, pool in sample_job(job_of("kr", f"kr/{code}/provincewide"), h, rng).items():
            merged[region].extend(pool)
    result = {"states": {r: stratify(v, rng) for r, v in merged.items()}}
    (raw / "intl_kr.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print("kr done", {r: len(v) for r, v in result["states"].items()}, flush=True)


# ---------------------------------------------------------------- Taiwan
# Region = OA region code (tpe, nwt, ...). Row: [district, street, number, floor, zip3]

TW_REGION = {"tpe": "臺北市", "nwt": "新北市", "tao": "桃園市", "txg": "臺中市", "tnn": "臺南市", "khh": "高雄市",
             "kee": "基隆市", "hsz": "新竹市", "hsq": "新竹縣", "mia": "苗栗縣", "cha": "彰化縣", "yun": "雲林縣",
             "cyq": "嘉義縣", "pif": "屏東縣", "ttt": "臺東縣", "hua": "花蓮縣", "pen": "澎湖縣", "kin": "金門縣"}


def build_tw(raw):
    xml = (raw / "tw_county_en.xml").read_text(encoding="utf8")
    zips = {}
    for z, name, en in re.findall(r"<欄位1>(\d+)</欄位1>\s*<欄位2>(.*?)</欄位2>\s*<欄位3>(.*?)</欄位3>", xml):
        zips[name.replace("台", "臺")] = (z, en)
    rng = random.Random("intl-tw")
    merged = defaultdict(list)
    best = {}
    for s in sources("tw"):
        code = s["source"].split("/")[1]
        if code in TW_REGION and not s["source"].endswith("-en"):
            if code not in best or s["job"] > best[code]["job"]:  # newest job per region
                best[code] = s
    for code, s in sorted(best.items()):
        county = TW_REGION[code]
        def h(p, lon, lat, county=county, code=code):
            district = nfkc(p.get("district") or "") or nfkc(p.get("city") or "")
            if not re.search(r"[區鄉鎮市]$", district):
                return None
            hit = zips.get(county + district)
            num = nfkc(p.get("number") or "")
            street = nfkc(p.get("street") or "")
            if not hit or not re.fullmatch(r"\d+(之\d+)?號", num) or not street:
                return None
            floor = nfkc(p.get("unit") or "")
            return code, hit[0], [district, street, num, floor if re.fullmatch(r"[一二三四五六七八九十]+樓(之\d+)?", floor) else "", hit[0]]
        for region, pool in sample_job(s["job"], h, rng).items():
            merged[region].extend(pool)
    result = {"states": {}, "zips": {z: en for _, (z, en) in zips.items()}}
    for region in sorted(merged):
        result["states"][region] = stratify(merged[region], rng)
        print(f"tw {region}: pool={len(merged[region])} kept={len(result['states'][region])}", flush=True)
    (raw / "intl_tw.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")


# ---------------------------------------------------------------- Germany
# Region = Land code. Row: [street, number, plz, city]
# Sources without postcodes get one only when GeoNames lists exactly one PLZ for that town in that Land.

DE_SOURCE_LAND = {"bb": "BB", "berlin": "BE", "bw": "BW", "hb": "HB", "he": "HE", "hh": "HH", "mv": "MV", "ni": "NI",
                  "nw": "NW", "rp": "RP", "sh": "SH", "sl": "SL", "sn": "SN", "st": "ST", "th": "TH"}
DE_LAND_NAME = {"BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin", "BB": "Brandenburg", "HB": "Bremen", "HH": "Hamburg",
                "HE": "Hessen", "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen", "NW": "Nordrhein-Westfalen",
                "RP": "Rheinland-Pfalz", "SL": "Saarland", "SN": "Sachsen", "ST": "Sachsen-Anhalt",
                "SH": "Schleswig-Holstein", "TH": "Thüringen"}


# Main cities only; every one of these sources ships postcodes.
DE_CITIES = {"berlin": ("de/berlin", "Berlin"), "hamburg": ("de/hh/statewide", "Hamburg"),
             "koeln": ("de/nw/city_of_cologne", "Köln"), "frankfurt": ("de/he/city_of_frankfurtammain", "Frankfurt am Main"),
             "bremen": ("de/hb/statewide", None)}


def build_de(raw):
    rng = random.Random("intl-de")
    merged = defaultdict(list)
    for slug, (src, fixed_city) in DE_CITIES.items():
        def h(p, lon, lat, slug=slug, fixed_city=fixed_city):
            street, num = nfkc(p.get("street")), nfkc(p.get("number"))
            city = fixed_city or nfkc(p.get("city"))
            pc = nfkc(p.get("postcode"))
            if not street or not city or not re.fullmatch(r"\d{5}", pc) or not re.fullmatch(r"\d{1,4}\s?[a-zA-Z]?", num):
                return None
            street = re.sub(r"(?<=[a-zäöü])str\.$", "straße", street)
            street = re.sub(r"Str\.$", "Straße", street)
            return slug, pc, [street, num.replace(" ", ""), pc, city]
        for region, pool in sample_job(job_of("de", src), h, rng).items():
            merged[region].extend(pool)
        print(f"de {slug}: pool={len(merged[slug])}", flush=True)
    result = {"states": {r: stratify(v, rng) for r, v in merged.items()}}
    (raw / "intl_de.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print("de done", {r: len(v) for r, v in result["states"].items()}, flush=True)


# ---------------------------------------------------------------- Canada
# Region = province code. Row: [street, city, postcode]

def build_ca(raw):
    sys.path.insert(0, str(Path(__file__).parent))
    from build_data import format_street
    provinces = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
    def h(p, lon, lat):
        region = (p.get("region") or "").upper()
        pc = re.sub(r"\s", "", (p.get("postcode") or "").upper())
        if region not in provinces or not re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", pc):
            return None
        if (p.get("unit") or "").strip() or not num_ok(p.get("number")) or not p.get("street") or not p.get("city"):
            return None
        street = format_street(p["number"].upper(), p["street"]) if region != "QC" else f"{p['number']} {title(p['street'])}"
        return region, pc[:3], [street, title(p["city"]), f"{pc[:3]} {pc[3:]}"]
    run("ca", [s["job"] for s in sources("ca") if s["source"] == "ca/countrywide"], h, raw)


# ---------------------------------------------------------------- Australia
# Region = city slug. Row: [street, suburb, postcode, state]
# Melbourne and Canberra files have no postcodes; GeoNames fills them when the suburb has exactly one.

AU_CITIES = {"sydney": ("au/nsw/city_of_sydney", "NSW"), "melbourne": ("au/vic/city_of_melbourne", "VIC"),
             "brisbane": ("au/qld/brisbane_city_council", "QLD"), "gold-coast": ("au/qld/city_of_gold_coast", "QLD"),
             "canberra": ("au/act/statewide", "ACT"), "adelaide": ("au/sa/city_of_adelaide", "SA")}


def build_au(raw):
    pcs = defaultdict(set)
    for line in open(raw / "geonames_AU" / "AU.txt", encoding="utf8"):
        f = line.split("\t")
        pcs[(f[4], f[2].upper())].add(f[1])
    rng = random.Random("intl-au")
    merged = defaultdict(list)
    for slug, (src, state) in AU_CITIES.items():
        def h(p, lon, lat, slug=slug, state=state):
            if (p.get("unit") or "").strip() or not num_ok(p.get("number")) or not p.get("street") or not p.get("city"):
                return None
            pc = p.get("postcode") or ""
            if not re.fullmatch(r"\d{4}", pc):
                cands = pcs.get((state, nfkc(p["city"]).upper()), ())
                if len(cands) != 1:
                    return None
                pc = next(iter(cands))
            return slug, pc, [f"{p['number']} {title(p['street'])}", title(p["city"]), pc, state]
        for region, pool in sample_job(job_of("au", src), h, rng).items():
            merged[region].extend(pool)
        print(f"au {slug}: pool={len(merged[slug])}", flush=True)
    result = {"states": {r: stratify(v, rng) for r, v in merged.items()}}
    (raw / "intl_au.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print("au done", {r: len(v) for r, v in result["states"].items()}, flush=True)


BUILDERS = {"hk": build_hk, "sg": build_sg, "jp": build_jp, "kr": build_kr, "tw": build_tw,
            "de": build_de, "ca": build_ca, "au": build_au}

if __name__ == "__main__":
    raw_dir = Path(sys.argv[1])
    CACHE = raw_dir / "cache"
    CACHE.mkdir(exist_ok=True)
    for cc in sys.argv[2:]:
        BUILDERS[cc](raw_dir)
