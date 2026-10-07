"""Generate every page under public/ from one template.

Usage: python tools/build_pages.py

Edit PAGES / NAV below, then re-run. Pages whose `ready` is False are left out of
the navigation and not written, so half-finished countries never show a broken link.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "public"
SITE = "https://haike.eu.cc"  # public domain, used for sitemap.xml

OA = '<a href="https://openaddresses.io" target="_blank" rel="noopener">OpenAddresses</a>'
GEONAMES = '<a href="https://www.geonames.org" target="_blank" rel="noopener">GeoNames</a>（CC BY 4.0）'
US_SOURCES = f"地址数据来自 {OA}（各州及地方政府公开地址数据），经美国人口普查局 Geocoder 逐条核验；邮编边界来自人口普查局 ZCTA，邮编与城市对照来自 {GEONAMES}。"
US_DISCLAIMER = ("地址是真实存在的门牌，但姓名、电话、邮箱、生日均为随机生成，与该地址的住户无关。"
                 "SSN 的中间两位固定为社会保障局从未签发过的 00，不对应任何真人；信用卡号是支付平台公开的测试卡号，无法完成真实扣款。"
                 "仅用于开发测试和表单格式验证，请勿用于收件、实名或任何欺诈用途。")

INTL_DISCLAIMER = ("地址是真实存在的门牌，但姓名、电话、邮箱、生日以及楼层单位均为随机生成，与该地址的住户无关。"
                   "信用卡号是支付平台公开的测试卡号，无法完成真实扣款。仅用于开发测试和表单格式验证，请勿用于收件、实名或任何欺诈用途。")

READY_OSM = {"tr", "gb"}  # OSM-based pages whose data is in public/data

OSM_SOURCES = ('地址数据 © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> 贡献者，'
               '以 ODbL 协议发布。社区标注的地址覆盖程度因城市而异。')

TAXFREE = ["AK", "DE", "MT", "NH", "OR"]

PAGES = [
    {
        "key": "taxfree", "path": "", "ready": True, "country": "us", "regions": TAXFREE,
        "title": "免税州地址生成器 - 美国免税州真实地址、邮编、电话",
        "h1": ("免费", "美国免税州", "地址生成器"),
        "desc": "街道、门牌、城市和邮编取自阿拉斯加、特拉华、蒙大拿、新罕布什尔、俄勒冈五州政府公开地址数据，逐条经美国人口普查局核验；姓名、电话等随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "地址经官方核验"],
        "regionLabel": "选择免税州", "randomLabel": "随机免税州", "button": "生成免税州地址",
        "ssn": True, "sources": US_SOURCES, "disclaimer": US_DISCLAIMER,
    },
    {
        "key": "us", "path": "us/", "ready": True, "country": "us", "regions": None,
        "title": "美国地址生成器 - 50 州真实地址、邮编、电话",
        "h1": ("免费", "美国", "随机地址生成器"),
        "desc": "覆盖美国 50 个州和华盛顿特区。街道、门牌、城市和邮编取自各州政府公开地址数据，逐条经美国人口普查局核验；姓名、电话等随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "50 州全覆盖"],
        "regionLabel": "选择州", "randomLabel": "随机州", "button": "生成美国地址",
        "ssn": True, "sources": US_SOURCES, "disclaimer": US_DISCLAIMER,
    },
    {
        "key": "hk", "path": "hk/", "ready": True, "country": "hk", "regions": None,
        "title": "香港地址生成器 - 香港真实街道地址、中英文地址、电话",
        "h1": ("免费", "香港随机地址", "生成器"),
        "desc": "街道和门牌取自香港特区政府地址查询服务（ALS）公开数据，覆盖全港 18 区，同时给出中英文地址；楼层、单位、姓名和电话随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "中英文地址"],
        "regionLabel": "选择地区", "randomLabel": "随机地区", "button": "生成香港地址",
        "sources": f"地址数据来自香港特区政府地址查询服务 <a href=\"https://www.als.gov.hk\" target=\"_blank\" rel=\"noopener\">ALS</a>，经 {OA} 整理。",
        "disclaimer": INTL_DISCLAIMER,
    },
    {
        "key": "tw", "path": "tw/", "ready": True, "country": "tw", "regions": None,
        "title": "台湾地址生成器 - 台湾真实地址、邮递区号、电话",
        "h1": ("免费", "台湾随机地址", "生成器"),
        "desc": "覆盖台北、新北、桃园、台中、台南、高雄六都。街道门牌取自各市政府公开门牌数据，3 码邮递区号与英文区名来自中华邮政官方对照表；姓名和电话随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "官方邮递区号"],
        "regionLabel": "选择城市", "randomLabel": "随机城市", "button": "生成台湾地址",
        "sources": f"门牌数据来自各市政府公开资料，经 {OA} 整理；邮递区号与英文区名来自<a href=\"https://www.post.gov.tw\" target=\"_blank\" rel=\"noopener\">中华邮政</a>。",
        "disclaimer": INTL_DISCLAIMER,
    },
    {
        "key": "jp", "path": "jp/", "ready": True, "country": "jp", "regions": None,
        "title": "日本地址生成器 - 日本真实地址、邮编、日英文地址",
        "h1": ("免费", "日本随机地址", "生成器"),
        "desc": "覆盖东京、大阪、神奈川、京都、福冈、北海道。町域和街区号取自日本国土交通省位置参照信息公开数据，邮编与罗马字来自日本邮政官方邮编表，同时给出日文和英文地址；姓名和电话随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "日英文地址"],
        "regionLabel": "选择都道府县", "randomLabel": "随机地区", "button": "生成日本地址",
        "sources": f"地址数据来自日本国土交通省<a href=\"https://nlftp.mlit.go.jp/isj/index.html\" target=\"_blank\" rel=\"noopener\">位置参照情報</a>，经 {OA} 整理；邮编与罗马字来自<a href=\"https://www.post.japanpost.jp/zipcode/download.html\" target=\"_blank\" rel=\"noopener\">日本邮政</a>。",
        "disclaimer": INTL_DISCLAIMER,
    },
    {
        "key": "kr", "path": "kr/", "ready": True, "country": "kr", "regions": None,
        "title": "韩国地址生成器 - 韩国真实道路名地址、邮编、电话",
        "h1": ("免费", "韩国随机地址", "生成器"),
        "desc": "覆盖首尔、釜山、仁川、大邱。道路名地址和 5 位邮编取自韩国行政安全部道路名地址公开数据（2017 年版）；姓名和电话随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "官方邮编"],
        "regionLabel": "选择城市", "randomLabel": "随机城市", "button": "生成韩国地址",
        "sources": f"地址数据来自韩国行政安全部<a href=\"https://www.juso.go.kr\" target=\"_blank\" rel=\"noopener\">道路名地址</a>公开数据（2017 年版），经 {OA} 整理。",
        "disclaimer": INTL_DISCLAIMER,
    },
    {
        "key": "de", "path": "de/", "ready": True, "country": "de", "regions": None,
        "title": "德国地址生成器 - 德国真实地址、邮编、电话",
        "h1": ("免费", "德国随机地址", "生成器"),
        "desc": "覆盖柏林、汉堡、科隆、法兰克福、不来梅。街道、门牌和邮编取自各州及城市政府公开地址数据；姓名和电话随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "官方邮编"],
        "regionLabel": "选择城市", "randomLabel": "随机城市", "button": "生成德国地址",
        "sources": f"地址数据来自德国各州及城市政府公开地址数据，经 {OA} 整理。",
        "disclaimer": INTL_DISCLAIMER,
    },
    {
        "key": "au", "path": "au/", "ready": True, "country": "au", "regions": None,
        "title": "澳大利亚地址生成器 - 澳洲真实地址、邮编、电话",
        "h1": ("免费", "澳大利亚随机地址", "生成器"),
        "desc": "覆盖悉尼、墨尔本、布里斯班、黄金海岸、堪培拉。街道、门牌和邮编取自澳大利亚地方政府公开地址数据；姓名和电话随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "官方地址"],
        "regionLabel": "选择城市", "randomLabel": "随机城市", "button": "生成澳洲地址",
        "sources": f"地址数据来自澳大利亚各州及地方政府公开地址数据，经 {OA} 整理；部分邮编由 {GEONAMES} 补全。",
        "disclaimer": INTL_DISCLAIMER,
    },
    *[
        {
            "key": key, "path": f"{key}/", "ready": key in READY_OSM, "country": key, "regions": None,
            "title": f"{zh}地址生成器 - {zh}真实街道地址、邮编、电话",
            "h1": ("免费", f"{zh}随机地址", "生成器"),
            "desc": f"覆盖{cities}。街道、门牌和邮编取自 OpenStreetMap 社区标注的真实地址；姓名和电话随机生成，仅供测试。",
            "badges": ["免费可用", "无需注册", "真实街道"],
            "regionLabel": "选择城市", "randomLabel": "随机城市", "button": f"生成{zh}地址",
            "sources": OSM_SOURCES, "disclaimer": INTL_DISCLAIMER,
        }
        for key, zh, cities in [
            ("gb", "英国", "伦敦、曼彻斯特、伯明翰、爱丁堡、格拉斯哥"),
            ("in", "印度", "孟买、新德里、班加罗尔、金奈、海得拉巴、加尔各答"),
            ("ng", "尼日利亚", "拉各斯、阿布贾、伊巴丹、哈科特港"),
            ("ph", "菲律宾", "马尼拉大都会、宿务、达沃"),
            ("tr", "土耳其", "伊斯坦布尔"),
        ]
    ],
    {
        "key": "sg", "path": "sg/", "ready": True, "country": "sg", "regions": None,
        "title": "新加坡地址生成器 - 新加坡真实地址、邮编、电话",
        "h1": ("免费", "新加坡随机地址", "生成器"),
        "desc": "街道、门牌、建筑名和 6 位邮编取自新加坡土地管理局 OneMap 公开数据；姓名和电话随机生成，仅供测试。",
        "badges": ["免费可用", "无需注册", "官方邮编"],
        "regionLabel": "选择地区", "randomLabel": "新加坡全岛", "button": "生成新加坡地址",
        "sources": f"地址数据来自新加坡土地管理局 <a href=\"https://www.onemap.gov.sg\" target=\"_blank\" rel=\"noopener\">OneMap</a>，经 {OA} 整理。",
        "disclaimer": INTL_DISCLAIMER,
    },
]

# (key, label, href) — order is the order shown. The first four sit in the bar, the rest under "更多地址".
NAV = [
    ("us", "美国地址", "/us/"),
    ("taxfree", "美国免税州地址", "/"),
    ("hk", "香港地址", "/hk/"),
    ("gb", "英国地址", "/gb/"),
    ("de", "德国地址", "/de/"),
    ("sg", "新加坡地址", "/sg/"),
    ("jp", "日本地址", "/jp/"),
    ("ca", "加拿大地址", "/ca/"),
    ("in", "印度地址", "/in/"),
    ("tw", "台湾地址", "/tw/"),
    ("mac", "MAC地址生成", "/mac/"),
    ("mac-lookup", "MAC地址查询", "/mac-lookup/"),
    ("ng", "尼日利亚地址", "/ng/"),
    ("ph", "菲律宾地址", "/ph/"),
    ("tr", "土耳其地址", "/tr/"),
    ("kr", "韩国地址", "/kr/"),
    ("au", "澳大利亚地址", "/au/"),
]
PRIMARY = 4


def ready_keys():
    keys = {p["key"] for p in PAGES if p["ready"]}
    keys |= {p["key"] for p in EXTRA_READY}
    return keys


EXTRA_READY = []  # non-generator pages (e.g. MAC tools) registered here when they exist


def nav_html(active):
    items = [n for n in NAV if n[0] in ready_keys()]
    main, more = items[:PRIMARY], items[PRIMARY:]
    out = []
    for key, label, href in main:
        cls = ' class="active"' if key == active else ""
        out.append(f'<a{cls} href="{href}">{label}</a>')
    if more:
        open_cls = " active" if any(k == active for k, _, _ in more) else ""
        links = "".join(
            f'<a{" class=\"active\"" if k == active else ""} href="{h}">{l}</a>' for k, l, h in more)
        out.append(f'<details class="more{open_cls}"><summary>更多地址</summary><div class="menu">{links}</div></details>')
    return "\n      ".join(out)


def page_html(p):
    a, b, c = p["h1"]
    badges = "".join(f'<li><svg width="18" height="18"><use href="#i-check"/></svg>{html.escape(x)}</li>' for x in p["badges"])
    ssn = '<label class="switch"><input type="checkbox" id="withSsn"><span class="track"></span>SSN</label>' if p.get("ssn") else ""
    page_cfg = {"country": p["country"], "regions": p["regions"], "randomLabel": p["randomLabel"]}
    return TEMPLATE.replace("{{title}}", html.escape(p["title"])) \
        .replace("{{description}}", html.escape(p["desc"])) \
        .replace("{{nav}}", nav_html(p["key"])) \
        .replace("{{h1}}", f'{html.escape(a)}<span class="hl">{html.escape(b)}</span>{html.escape(c)}') \
        .replace("{{desc}}", html.escape(p["desc"])) \
        .replace("{{badges}}", badges) \
        .replace("{{regionLabel}}", html.escape(p["regionLabel"])) \
        .replace("{{ssnSwitch}}", ssn) \
        .replace("{{button}}", html.escape(p["button"])) \
        .replace("{{sources}}", p["sources"]) \
        .replace("{{disclaimer}}", html.escape(p["disclaimer"])) \
        .replace("{{page}}", json.dumps(page_cfg, ensure_ascii=False))


IEEE = '<a href="https://standards.ieee.org/products-programs/regauth/" target="_blank" rel="noopener">IEEE 注册管理机构</a>'
MAC_BADGES = "".join(f'<li><svg width="18" height="18"><use href="#i-check"/></svg>{x}</li>' for x in ["免费可用", "无需注册", "IEEE 官方数据"])

TOOL_PAGES = [
    {
        "key": "mac", "path": "mac/",
        "title": "MAC 地址生成器 - 按厂商生成随机 MAC 地址",
        "desc": "按厂商（Apple、三星、华为、小米、Intel 等）生成随机 MAC 地址，或生成本地管理的随机地址，支持多种格式和批量生成。",
        "main": f"""
  <section class="card">
    <div class="hero">
      <div class="hero-text">
        <h1>免费<span class="hl">MAC 地址</span>生成器</h1>
        <p class="desc">按厂商生成随机 MAC 地址，前缀取自 IEEE 官方 OUI 注册表；也可以生成本地管理地址（与手机"随机 MAC"相同的类型）。支持多种格式，一次最多 100 个。</p>
        <ul class="badges">{MAC_BADGES}</ul>
        <p class="stats" id="stats" aria-live="polite">加载厂商库…</p>
      </div>
      <div class="hero-form">
        <label class="lbl" for="vendor">厂商</label>
        <div class="select"><select id="vendor"></select></div>
        <label class="lbl" for="format">格式</label>
        <div class="select"><select id="format">
          <option value=":">AA:BB:CC:DD:EE:FF</option>
          <option value="-">AA-BB-CC-DD-EE-FF</option>
          <option value=".">AABB.CCDD.EEFF（Cisco）</option>
          <option value="">AABBCCDDEEFF</option>
        </select></div>
        <div class="inline-fields">
          <label class="lbl-inline">数量 <input type="number" id="count" min="1" max="100" value="10" class="num-input"></label>
          <label class="switch"><input type="checkbox" id="lower"><span class="track"></span>小写</label>
        </div>
        <button type="button" class="btn-primary" id="generate" disabled><svg width="20" height="20"><use href="#i-refresh"/></svg>生成 MAC 地址</button>
      </div>
    </div>
    <div class="results">
      <div class="results-head">
        <h2>生成结果</h2>
        <div class="actions"><button type="button" class="btn-cyan" id="copyAll"><svg width="16" height="16"><use href="#i-copyall"/></svg>复制全部</button></div>
      </div>
      <div class="grid" id="list"></div>
      <p class="note">点击任意一行即可复制。本地管理地址的第一个字节第 2 位为 1，不属于任何厂商。</p>
    </div>
  </section>""",
        "sources": f"厂商前缀来自 {IEEE} 公开的 OUI（MA-L）注册表。",
    },
    {
        "key": "mac-lookup", "path": "mac-lookup/",
        "title": "MAC 地址查询 - 查询 MAC 地址所属厂商",
        "desc": "输入 MAC 地址，查询所属厂商、注册国家和地址类型（单播/组播、全球/本地管理），支持批量查询。",
        "main": f"""
  <section class="card">
    <div class="hero">
      <div class="hero-text">
        <h1><span class="hl">MAC 地址</span>厂商查询</h1>
        <p class="desc">根据 IEEE 官方 OUI 注册表查询 MAC 地址的生产厂商和注册国家，并判断是单播还是组播、全球唯一还是本地管理（随机）地址。查询完全在浏览器内完成。</p>
        <ul class="badges">{MAC_BADGES}</ul>
        <p class="stats" id="stats" aria-live="polite">加载厂商库…</p>
      </div>
      <div class="hero-form">
        <label class="lbl" for="input">MAC 地址（每行一个，支持任意分隔符）</label>
        <textarea id="input" class="textarea" rows="6" placeholder="F0:D1:A9:12:34:56&#10;00-1A-2B-3C-4D-5E&#10;001a.2b3c.4d5e"></textarea>
        <button type="button" class="btn-primary" id="lookup" disabled><svg width="20" height="20"><use href="#i-refresh"/></svg>查询厂商</button>
      </div>
    </div>
    <div class="results">
      <div class="results-head"><h2>查询结果</h2></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>MAC 地址</th><th>厂商</th><th>国家/地区</th><th>类型</th></tr></thead>
          <tbody id="resultBody"></tbody>
        </table>
        <p class="empty" id="resultEmpty">输入 MAC 地址后点击查询。</p>
      </div>
    </div>
  </section>""",
        "sources": f"厂商数据来自 {IEEE} 公开的 OUI（MA-L）注册表。仅覆盖 24 位 OUI 前缀；MA-M、MA-S 小块分配会显示为其上级前缀的登记者。",
    },
]
EXTRA_READY.extend(TOOL_PAGES)


def tool_html(t):
    head = TEMPLATE.split('<main class="wrap">')[0]
    head = head.replace("{{title}}", html.escape(t["title"])).replace("{{description}}", html.escape(t["desc"])) \
        .replace("{{nav}}", nav_html(t["key"]))
    head = head.split('    <a class="saved-link"')[0] + "  </div>\n</header>\n"
    return (head + '\n<main class="wrap">' + t["main"] +
            f'\n  <footer>\n    <p>{t["sources"]}</p>\n  </footer>\n</main>\n'
            '<div class="toast" id="toast" role="status"></div>\n'
            '<script src="/assets/mac.js"></script>\n</body>\n</html>\n')


def versioned(page):
    """Append ?v=<content hash> to /assets/ links so browsers fetch new code after each deploy."""
    import hashlib
    import re
    def stamp(m):
        f = ROOT / m.group(1).lstrip("/")
        return f'{m.group(1)}?v={hashlib.sha1(f.read_bytes()).hexdigest()[:8]}"'
    return re.sub(r'(/assets/[\w.-]+)"', stamp, page)


def main():
    for p in PAGES:
        if not p["ready"]:
            continue
        out = ROOT / p["path"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(versioned(page_html(p)), encoding="utf8")
        print("wrote", out.relative_to(ROOT))
    for t in TOOL_PAGES:
        out = ROOT / t["path"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(versioned(tool_html(t)), encoding="utf8")
        print("wrote", out.relative_to(ROOT))
    paths = [p["path"] for p in PAGES if p["ready"]] + [t["path"] for t in TOOL_PAGES]
    urls = "".join(f"  <url><loc>{SITE}/{p}</loc></url>\n" for p in paths)
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n',
        encoding="utf8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf8")
    print("wrote sitemap.xml, robots.txt")


TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}}</title>
<meta name="description" content="{{description}}">
<meta name="theme-color" content="#0f172a">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%233b82f6'/><path d='M16 6a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.6a2.6 2.6 0 1 1 0-5.2 2.6 2.6 0 0 1 0 5.2z' fill='white'/></svg>">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="i-copy" viewBox="0 0 24 24"><path fill="currentColor" d="M16 1H6a2 2 0 0 0-2 2v12h2V3h10V1zm3 4H10a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H10V7h9v14z"/></symbol>
  <symbol id="i-check" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="M7.5 12.5l3 3 6-6.5" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></symbol>
  <symbol id="i-refresh" viewBox="0 0 24 24"><path fill="currentColor" d="M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></symbol>
  <symbol id="i-copyall" viewBox="0 0 24 24"><path fill="currentColor" d="M19 3h-4.18A3 3 0 0 0 12 1a3 3 0 0 0-2.82 2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm-7 0a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></symbol>
  <symbol id="i-save" viewBox="0 0 24 24"><path fill="currentColor" d="M17 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7l-4-4zm-5 16a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm3-10H5V5h10v4z"/></symbol>
  <symbol id="i-pin" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></symbol>
  <symbol id="i-bookmark" viewBox="0 0 24 24"><path fill="currentColor" d="M17 3H7a2 2 0 0 0-2 2v16l7-3 7 3V5a2 2 0 0 0-2-2zm0 15-5-2.18L7 18V5h10v13z"/></symbol>
</svg>

<header class="nav">
  <div class="nav-inner">
    <a class="brand" href="/">
      <span class="logo"><svg width="18" height="18"><use href="#i-pin"/></svg></span>
      <span>随机地址</span>
    </a>
    <nav class="links" aria-label="主导航">
      {{nav}}
    </nav>
    <a class="saved-link" href="#saved"><svg width="16" height="16"><use href="#i-bookmark"/></svg><span class="saved-text">已保存地址</span> <span class="badge" id="navCount">0</span></a>
  </div>
</header>

<main class="wrap">
  <section class="card">
    <div class="hero">
      <div class="hero-text">
        <h1>{{h1}}</h1>
        <p class="desc">{{desc}}</p>
        <ul class="badges">{{badges}}</ul>
        <p class="stats" id="stats" aria-live="polite">加载地址库…</p>
      </div>

      <div class="hero-form">
        <label class="lbl" for="regionSelect">{{regionLabel}}</label>
        <div class="select"><select id="regionSelect"></select></div>
        <div class="switches">
          <label class="switch"><input type="checkbox" id="withIdentity" checked><span class="track"></span>生日和职业</label>
          {{ssnSwitch}}
          <label class="switch"><input type="checkbox" id="withCard"><span class="track"></span>信用卡</label>
        </div>
        <button type="button" class="btn-primary" id="generate" disabled>
          <svg width="20" height="20"><use href="#i-refresh"/></svg>{{button}}
        </button>
      </div>
    </div>

    <div class="results" id="result" aria-live="polite">
      <div class="results-head">
        <h2>生成结果</h2>
        <div class="actions">
          <button type="button" class="btn-cyan" id="copyAll"><svg width="16" height="16"><use href="#i-copyall"/></svg>复制全部</button>
          <button type="button" class="btn-green" id="save"><svg width="16" height="16"><use href="#i-save"/></svg>保存</button>
        </div>
      </div>
      <div class="grid" id="grid"></div>
    </div>
  </section>

  <section class="card saved" id="saved">
    <div class="results-head">
      <h2>已保存的地址 <span class="badge" id="savedCount">0</span></h2>
      <div class="actions">
        <button type="button" class="btn-ghost" id="exportCsv">导出 CSV</button>
        <button type="button" class="btn-ghost" id="exportJson">导出 JSON</button>
        <button type="button" class="btn-red" id="clearAll">全部删除</button>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>姓名</th><th>地址</th><th>电话</th><th></th></tr></thead>
        <tbody id="savedBody"></tbody>
      </table>
      <p class="empty" id="savedEmpty">暂无保存的地址。保存的记录只存在这个浏览器里，各页面共用。</p>
    </div>
  </section>

  <footer>
    <p>{{sources}}</p>
    <p>{{disclaimer}}</p>
  </footer>
</main>
<div class="toast" id="toast" role="status"></div>
<script>window.PAGE = {{page}};</script>
<script src="/assets/names.js"></script>
<script src="/assets/countries.js"></script>
<script src="/assets/app.js"></script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
