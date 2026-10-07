# 随机地址生成器

多国真实地址生成器：地址取自各国政府公开地址数据（美国全部经人口普查局核验），姓名、电话、邮箱等随机生成。另有 MAC 地址生成和查询工具。纯静态站点，所有生成都在浏览器里完成。

## 页面

| 路径 | 内容 | 数据来源 |
|---|---|---|
| `/` | 美国免税州（AK、DE、MT、NH、OR） | OpenAddresses，人口普查局核验 |
| `/us/` | 美国 50 州 + 华盛顿特区 | OpenAddresses，人口普查局核验 |
| `/hk/` | 香港 18 区，中英文地址 | 香港特区政府 ALS |
| `/tw/` | 台湾六都 | data.gov.tw 门牌，中华邮政邮递区号 |
| `/jp/` | 东京、大阪、神奈川、京都、福冈、北海道 | 国土交通省位置参照情報，日本邮政邮编 |
| `/kr/` | 首尔、釜山、仁川、大邱 | 行政安全部道路名地址（2017） |
| `/de/` | 柏林、汉堡、科隆、法兰克福、不来梅 | 各州/城市政府公开数据 |
| `/au/` | 悉尼、墨尔本、布里斯班、黄金海岸、堪培拉 | 地方政府公开数据，GeoNames 补邮编 |
| `/sg/` | 新加坡 | OneMap（新加坡土地管理局） |
| `/gb/` `/tr/` `/in/` `/ph/` `/ng/` | 主要城市 | OpenStreetMap |
| `/mac/` `/mac-lookup/` | MAC 地址生成与厂商查询 | IEEE OUI 注册表 |

## 目录

```
public/                    网站本体（部署这个目录）
  */index.html             各页面（由 tools/build_pages.py 生成，不要手改）
  assets/app.js            地址生成引擎
  assets/countries.js      各国配置：地区、电话格式、地址格式、显示字段
  assets/names.js          随机数工具和各国姓名库
  assets/mac.js            MAC 工具
  assets/style.css
  data/<国家>/<地区>.json  地址数据，manifest.json 记录各地区条数
  data/oui.json            IEEE 厂商前缀
tools/
  build_pages.py           生成所有页面和导航（改文案、加国家改这里）
  build_data.py            免税州数据
  build_us.py              美国各州数据
  verify_census.py         人口普查局批量核验
  build_intl.py            OpenAddresses 国家（HK/TW/JP/KR/DE/AU/SG）
  build_osm.py             OpenStreetMap Overpass 查询（IN/PH/NG/TR）
  build_pbf.py             BBBike 城市数据包（GB、伊斯坦布尔）
  split_regions.py         拆成按地区的 JSON 和 manifest
wrangler.jsonc             Cloudflare Workers 静态资源部署配置
```

## 本地预览

```bash
python -m http.server 8765 --directory public
```

然后打开 http://localhost:8765 。页面用了以 `/` 开头的绝对路径，所以必须以 `public` 为站点根目录。

## 部署到 Cloudflare

仓库连接到 Cloudflare Workers，部署命令保持 `npx wrangler deploy`，构建命令留空。`wrangler.jsonc` 只发布 `public/` 目录。

## 加一个国家

1. 写数据：在 `tools/` 里加一个生成器，输出 `{"states": {地区: [行, ...]}}`，再用 `split_regions.py` 写到 `public/data/<国家>/`。
2. 在 `public/assets/countries.js` 里加配置（地区、电话、`address()` 把一行数据变成显示字段、`fields`）。
3. 在 `tools/build_pages.py` 的 `PAGES` 里加页面，`ready: True`，运行 `python tools/build_pages.py`。

## 说明

- 地址是真实存在的门牌，但姓名、电话、邮箱、生日、楼层单位都是随机生成的，与住户无关。
- SSN（仅美国页面）前三位随机（001–899，不含 666），中间两位固定为 00。社会保障局从未签发过组号 00，所以不会与任何真人的 SSN 重合。
- 信用卡只用 Stripe / Braintree 文档公开的测试卡号，无法真实扣款。
- 仅用于开发测试和表单格式验证，请勿用于收件、实名或任何欺诈用途。
