/* Per-country configuration for the address engine (assets/app.js).
 *
 * Each country declares:
 *   dataDir    folder under /data holding manifest.json and one <REGION>.json per region
 *   regions    { CODE: { name, zh, ... } } in display order
 *   names      name pools used for random people
 *   phone(region, row)            random phone number string
 *   address(row, region, code)    turns a data row into display fields (must set fullAddress)
 *   fields     [key, label] rows shown in the result grid, in order
 *   wide       keys that take a full row
 *   ssn        whether the SSN switch applies
 *   maps(rec)  query string for the map link
 */
(function () {
  "use strict";

  const rand = (n) => window.RNG.rand(n);
  const between = (lo, hi) => window.RNG.between(lo, hi);
  const pick = (arr) => window.RNG.pick(arr);

  const US_STATES = {
    AL: ["Alabama", "阿拉巴马州", [205, 251, 256, 334, 659, 938]],
    AK: ["Alaska", "阿拉斯加州", [907]],
    AZ: ["Arizona", "亚利桑那州", [480, 520, 602, 623, 928]],
    AR: ["Arkansas", "阿肯色州", [479, 501, 870]],
    CA: ["California", "加利福尼亚州", [209, 213, 310, 323, 408, 415, 510, 530, 559, 562, 619, 626, 650, 657, 661, 707, 714, 760, 805, 818, 831, 858, 909, 916, 925, 949, 951]],
    CO: ["Colorado", "科罗拉多州", [303, 719, 720, 970]],
    CT: ["Connecticut", "康涅狄格州", [203, 475, 860, 959]],
    DE: ["Delaware", "特拉华州", [302]],
    DC: ["District of Columbia", "华盛顿特区", [202]],
    FL: ["Florida", "佛罗里达州", [239, 305, 321, 352, 386, 407, 561, 727, 754, 772, 786, 813, 850, 863, 904, 941, 954]],
    GA: ["Georgia", "佐治亚州", [229, 404, 470, 478, 678, 706, 762, 770, 912]],
    HI: ["Hawaii", "夏威夷州", [808]],
    ID: ["Idaho", "爱达荷州", [208, 986]],
    IL: ["Illinois", "伊利诺伊州", [217, 224, 309, 312, 331, 618, 630, 708, 773, 779, 815, 847, 872]],
    IN: ["Indiana", "印第安纳州", [219, 260, 317, 463, 574, 765, 812, 930]],
    IA: ["Iowa", "艾奥瓦州", [319, 515, 563, 641, 712]],
    KS: ["Kansas", "堪萨斯州", [316, 620, 785, 913]],
    KY: ["Kentucky", "肯塔基州", [270, 364, 502, 606, 859]],
    LA: ["Louisiana", "路易斯安那州", [225, 318, 337, 504, 985]],
    ME: ["Maine", "缅因州", [207]],
    MD: ["Maryland", "马里兰州", [240, 301, 410, 443, 667]],
    MA: ["Massachusetts", "马萨诸塞州", [339, 351, 413, 508, 617, 774, 781, 857, 978]],
    MI: ["Michigan", "密歇根州", [231, 248, 269, 313, 517, 586, 616, 734, 810, 906, 947, 989]],
    MN: ["Minnesota", "明尼苏达州", [218, 320, 507, 612, 651, 763, 952]],
    MS: ["Mississippi", "密西西比州", [228, 601, 662, 769]],
    MO: ["Missouri", "密苏里州", [314, 417, 573, 636, 660, 816]],
    MT: ["Montana", "蒙大拿州", [406]],
    NE: ["Nebraska", "内布拉斯加州", [308, 402, 531]],
    NV: ["Nevada", "内华达州", [702, 725, 775]],
    NH: ["New Hampshire", "新罕布什尔州", [603]],
    NJ: ["New Jersey", "新泽西州", [201, 551, 609, 640, 732, 848, 856, 862, 908, 973]],
    NM: ["New Mexico", "新墨西哥州", [505, 575]],
    NY: ["New York", "纽约州", [212, 315, 332, 347, 516, 518, 585, 607, 631, 646, 680, 716, 718, 838, 845, 914, 917, 929, 934]],
    NC: ["North Carolina", "北卡罗来纳州", [252, 336, 704, 743, 828, 910, 919, 980, 984]],
    ND: ["North Dakota", "北达科他州", [701]],
    OH: ["Ohio", "俄亥俄州", [216, 220, 234, 330, 380, 419, 440, 513, 567, 614, 740, 937]],
    OK: ["Oklahoma", "俄克拉何马州", [405, 539, 580, 918]],
    OR: ["Oregon", "俄勒冈州", [458, 503, 541, 971]],
    PA: ["Pennsylvania", "宾夕法尼亚州", [215, 223, 267, 272, 412, 445, 484, 570, 610, 717, 724, 814, 878]],
    RI: ["Rhode Island", "罗得岛州", [401]],
    SC: ["South Carolina", "南卡罗来纳州", [803, 839, 843, 854, 864]],
    SD: ["South Dakota", "南达科他州", [605]],
    TN: ["Tennessee", "田纳西州", [423, 615, 629, 731, 865, 901, 931]],
    TX: ["Texas", "得克萨斯州", [210, 214, 254, 281, 325, 346, 361, 409, 430, 432, 469, 512, 682, 713, 726, 737, 806, 817, 830, 832, 903, 915, 936, 940, 956, 972, 979]],
    UT: ["Utah", "犹他州", [385, 435, 801]],
    VT: ["Vermont", "佛蒙特州", [802]],
    VA: ["Virginia", "弗吉尼亚州", [276, 434, 540, 571, 703, 757, 804]],
    WA: ["Washington", "华盛顿州", [206, 253, 360, 425, 509, 564]],
    WV: ["West Virginia", "西弗吉尼亚州", [304, 681]],
    WI: ["Wisconsin", "威斯康星州", [262, 414, 534, 608, 715, 920]],
    WY: ["Wyoming", "怀俄明州", [307]],
  };

  function nanp(area) {
    let exchange;
    do { exchange = between(200, 999); } while (exchange % 100 === 11 || exchange === 555);
    return `(${area}) ${exchange}-${String(between(0, 9999)).padStart(4, "0")}`;
  }

  const N = window.NAMES;
  const digits = (n) => Array.from({ length: n }, () => between(0, 9)).join("");

  /* Countries built from OpenStreetMap share one row layout:
   * [housenumber, street, postcode, city, suburb, state]. `format` builds the one-line address. */
  function osmCountry({ dataDir, regions, names, mail, phone, format, line = (a) => `${a.number} ${a.street}`, labels = {} }) {
    return {
      dataDir,
      regionWord: "城市",
      regions,
      names,
      mail,
      phone,
      address(row) {
        const [number, street, postcode, city, suburb, state] = row;
        const a = { number, street, postcode, city, suburb, state };
        return { street: line(a), suburb, city, state, zip: postcode, fullAddress: format(a) };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["gender", "性别 / Gender"], ["phone", "电话 / Phone"],
        ["street", labels.street || "街道门牌 / Street"],
        ["suburb", labels.suburb || "区 / District"], ["city", "城市 / City"],
        ["state", labels.state || "州/省 / State"], ["zip", labels.zip || "邮编 / Postal Code"],
        ["email", "电子邮件 / Email"],
        ["fullAddress", "完整地址 / Full Address"],
      ],
      wide: ["street", "email", "fullAddress"],
      maps: (rec) => rec.fullAddress,
    };
  }

  window.COUNTRIES = {
    us: {
      dataDir: "us",
      regions: Object.fromEntries(Object.entries(US_STATES).map(([code, [name, zh, area]]) => [code, { name, zh, area }])),
      names: { male: N.enMale, female: N.enFemale, last: N.enLast },
      mail: ["gmail.com", "gmail.com", "gmail.com", "outlook.com", "yahoo.com", "icloud.com", "hotmail.com"],
      phone(region, row) {
        // Oregon: 503/971 cover Portland, Salem and the north coast (ZIP 970-972); 541/458 the rest.
        if (region.code === "OR") return nanp(pick(row[2] < "973" ? [503, 971] : [541, 458]));
        return nanp(pick(region.area));
      },
      address(row, region) {
        const [street, city, zip, county] = row;
        return {
          street, city, zip, county,
          stateCode: region.code,
          stateFull: `${region.name} (${region.code})`,
          fullAddress: `${street}, ${city}, ${region.code} ${zip}`,
        };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["gender", "性别 / Gender"], ["phone", "电话 / Phone"],
        ["street", "街道地址 / Street Address"],
        ["city", "城市 / City"], ["county", "县 / County"],
        ["stateFull", "州 / State"], ["zip", "邮编 / ZIP Code"],
        ["email", "电子邮件 / Email"],
        ["fullAddress", "完整地址 / Full Address"],
      ],
      wide: ["street", "email", "fullAddress"],
      csv: ["street", "city", "stateCode", "zip", "county"],
      ssn: true,
      maps: (rec) => rec.fullAddress,
    },

    // Row: [number, street_en, street_zh, sub_area_en, sub_area_zh]. Hong Kong has no postcodes.
    hk: {
      dataDir: "hk",
      regionWord: "地区",
      regions: {
        "central-western": { name: "Central & Western", zh: "中西區", area: ["Hong Kong Island", "香港"] },
        "wan-chai": { name: "Wan Chai", zh: "灣仔區", area: ["Hong Kong Island", "香港"] },
        "eastern": { name: "Eastern", zh: "東區", area: ["Hong Kong Island", "香港"] },
        "southern": { name: "Southern", zh: "南區", area: ["Hong Kong Island", "香港"] },
        "yau-tsim-mong": { name: "Yau Tsim Mong", zh: "油尖旺區", area: ["Kowloon", "九龍"] },
        "sham-shui-po": { name: "Sham Shui Po", zh: "深水埗區", area: ["Kowloon", "九龍"] },
        "kowloon-city": { name: "Kowloon City", zh: "九龍城區", area: ["Kowloon", "九龍"] },
        "wong-tai-sin": { name: "Wong Tai Sin", zh: "黃大仙區", area: ["Kowloon", "九龍"] },
        "kwun-tong": { name: "Kwun Tong", zh: "觀塘區", area: ["Kowloon", "九龍"] },
        "kwai-tsing": { name: "Kwai Tsing", zh: "葵青區", area: ["New Territories", "新界"] },
        "tsuen-wan": { name: "Tsuen Wan", zh: "荃灣區", area: ["New Territories", "新界"] },
        "tuen-mun": { name: "Tuen Mun", zh: "屯門區", area: ["New Territories", "新界"] },
        "yuen-long": { name: "Yuen Long", zh: "元朗區", area: ["New Territories", "新界"] },
        "north": { name: "North", zh: "北區", area: ["New Territories", "新界"] },
        "tai-po": { name: "Tai Po", zh: "大埔區", area: ["New Territories", "新界"] },
        "sha-tin": { name: "Sha Tin", zh: "沙田區", area: ["New Territories", "新界"] },
        "sai-kung": { name: "Sai Kung", zh: "西貢區", area: ["New Territories", "新界"] },
        "islands": { name: "Islands", zh: "離島區", area: ["New Territories", "新界"] },
      },
      names: { male: N.hkMale, female: N.hkFemale, last: N.hkLast },
      localName: (last, first) => last + first,
      mail: ["gmail.com", "gmail.com", "yahoo.com.hk", "outlook.com", "hotmail.com", "icloud.com", "netvigator.com"],
      phone() {
        // Mobile numbers start with 5, 6 or 9 (999 is the emergency number, so skip that prefix).
        let n;
        do { n = String(pick([5, 6, 9])) + String(between(0, 9999999)).padStart(7, "0"); } while (n.startsWith("999"));
        return `+852 ${n.slice(0, 4)} ${n.slice(4)}`;
      },
      address(row, region) {
        const [number, streetEn, streetZh, subEn, subZh] = row;
        const floor = between(1, 30);
        const flat = "ABCDEFGH"[rand(8)];
        const [areaEn, areaZh] = region.area;
        const street = `${number} ${streetEn}`;
        return {
          flat: `Flat ${flat}, ${floor}/F`,
          street,
          district: `${region.name} District`,
          region: areaEn,
          fullAddress: [`Flat ${flat}, ${floor}/F`, street, subEn, `${region.name} District`, areaEn].filter(Boolean).join(", "),
          localAddress: `${areaZh}${region.zh}${subZh || ""}${streetZh}${number}號${floor}樓${flat}室`,
          mapQuery: `${street}, ${subEn ? subEn + ", " : ""}${region.name}, Hong Kong`,
        };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["localName", "中文姓名 / Chinese Name"], ["gender", "性别 / Gender"],
        ["phone", "电话 / Phone"], ["flat", "楼层单位 / Flat & Floor"],
        ["street", "街道门牌 / Street"],
        ["district", "地区 / District"], ["region", "区域 / Region"],
        ["email", "电子邮件 / Email"],
        ["localAddress", "中文地址 / Chinese Address"],
        ["fullAddress", "英文地址 / Full Address"],
      ],
      wide: ["street", "email", "localAddress", "fullAddress"],
      maps: (rec) => rec.mapQuery,
    },

    // Row: [district, street, number, floor, zip3, district_en]. English district names are Chunghwa Post's official ones.
    tw: {
      dataDir: "tw",
      regionWord: "城市",
      regions: {
        tpe: { name: "Taipei City", zh: "臺北市" },
        nwt: { name: "New Taipei City", zh: "新北市" },
        tao: { name: "Taoyuan City", zh: "桃園市" },
        txg: { name: "Taichung City", zh: "臺中市" },
        tnn: { name: "Tainan City", zh: "臺南市" },
        khh: { name: "Kaohsiung City", zh: "高雄市" },
      },
      names: { male: N.twMale, female: N.twFemale, last: N.twLast },
      localName: (last, first) => last + first,
      mail: ["gmail.com", "gmail.com", "yahoo.com.tw", "hotmail.com", "outlook.com", "icloud.com", "msa.hinet.net"],
      phone: () => `09${between(10, 89)}-${String(between(0, 999)).padStart(3, "0")}-${String(between(0, 999)).padStart(3, "0")}`,
      address(row, region) {
        const [district, street, number, floor, zip, districtEn] = row;
        const line = `${street}${number}${floor}`;
        return {
          zip,
          city: region.zh,
          district,
          street: line,
          fullAddress: `${zip}${region.zh}${district}${line}`,
          districtEn: `${districtEn} ${zip}, Taiwan (R.O.C.)`,
        };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["localName", "中文姓名 / Chinese Name"], ["gender", "性别 / Gender"],
        ["phone", "电话 / Phone"], ["zip", "邮递区号 / Postal Code"],
        ["city", "县市 / City"], ["district", "乡镇市区 / District"],
        ["street", "街道门牌 / Street"],
        ["email", "电子邮件 / Email"],
        ["fullAddress", "完整地址 / Full Address"],
        ["districtEn", "英文区域 / District (EN)"],
      ],
      wide: ["street", "email", "fullAddress", "districtEn"],
      maps: (rec) => rec.fullAddress,
    },

    // Row: [gu, dong, road, number, postcode]
    kr: {
      dataDir: "kr",
      regionWord: "城市",
      regions: {
        seoul: { name: "Seoul", zh: "首尔", ko: "서울특별시" },
        busan: { name: "Busan", zh: "釜山", ko: "부산광역시" },
        incheon: { name: "Incheon", zh: "仁川", ko: "인천광역시" },
        daegu: { name: "Daegu", zh: "大邱", ko: "대구광역시" },
      },
      names: { male: N.krMale, female: N.krFemale, last: N.krLast },
      localName: (last, first) => last + first,
      mail: ["gmail.com", "gmail.com", "naver.com", "naver.com", "daum.net", "kakao.com", "hanmail.net"],
      phone: () => `010-${String(between(2000, 9999))}-${String(between(0, 9999)).padStart(4, "0")}`,
      address(row, region) {
        const [gu, dong, road, number, postcode] = row;
        return {
          zip: postcode,
          city: region.ko,
          district: gu,
          dong,
          street: `${road} ${number}`,
          fullAddress: `${region.ko} ${gu} ${road} ${number}${dong ? ` (${dong})` : ""}`,
        };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["localName", "韩文姓名 / Korean Name"], ["gender", "性别 / Gender"],
        ["phone", "电话 / Phone"], ["zip", "邮编 / Postal Code"],
        ["city", "市/道 / City"], ["district", "区/郡 / District"],
        ["street", "道路名地址 / Road Address"], ["dong", "洞 / Dong"],
        ["email", "电子邮件 / Email"],
        ["fullAddress", "完整地址 / Full Address"],
      ],
      wide: ["email", "fullAddress"],
      maps: (rec) => rec.fullAddress,
    },

    // Row: [city, town, chome, number, postcode, city_romaji, town_romaji]. Postcodes and romaji are Japan Post's.
    jp: {
      dataDir: "jp",
      regionWord: "都道府县",
      regions: {
        tokyo: { name: "Tokyo", zh: "东京都", ja: "東京都" },
        osaka: { name: "Osaka", zh: "大阪府", ja: "大阪府" },
        kanagawa: { name: "Kanagawa", zh: "神奈川县", ja: "神奈川県" },
        kyoto: { name: "Kyoto", zh: "京都府", ja: "京都府" },
        fukuoka: { name: "Fukuoka", zh: "福冈县", ja: "福岡県" },
        hokkaido: { name: "Hokkaido", zh: "北海道", ja: "北海道" },
      },
      names: { male: N.jpMale, female: N.jpFemale, last: N.jpLast },
      localName: (last, first) => `${last} ${first}`,
      mail: ["gmail.com", "gmail.com", "yahoo.co.jp", "yahoo.co.jp", "docomo.ne.jp", "icloud.com", "outlook.jp"],
      phone: () => `0${pick([9, 8, 7])}0-${String(between(1000, 9999))}-${String(between(0, 9999)).padStart(4, "0")}`,
      address(row, region) {
        const [city, town, chome, number, postcode, cityEn, townEn] = row;
        const townFull = `${town}${chome ? `${chome}丁目` : ""}`;
        return {
          zip: postcode,
          state: region.ja,
          city,
          town: townFull,
          street: number,
          localAddress: `〒${postcode} ${region.ja}${city}${townFull}${number}`,
          fullAddress: `${number} ${townEn}${chome ? ` ${chome}-chome` : ""}, ${cityEn}, ${region.name} ${postcode}`,
        };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["localName", "日文姓名 / Japanese Name"], ["gender", "性别 / Gender"],
        ["phone", "电话 / Phone"], ["zip", "邮编 / Postal Code"],
        ["state", "都道府县 / Prefecture"], ["city", "市区町村 / City"],
        ["town", "町域 / Town"], ["street", "番地 / Block No."],
        ["email", "电子邮件 / Email"],
        ["localAddress", "日文地址 / Japanese Address"],
        ["fullAddress", "英文地址 / Full Address"],
      ],
      wide: ["email", "localAddress", "fullAddress"],
      maps: (rec) => rec.localAddress.replace(/^〒\S+ /, ""),
    },

    // Row: [street, house_number, plz, city]
    de: {
      dataDir: "de",
      regionWord: "城市",
      regions: {
        berlin: { name: "Berlin", zh: "柏林", land: "Berlin" },
        hamburg: { name: "Hamburg", zh: "汉堡", land: "Hamburg" },
        koeln: { name: "Köln", zh: "科隆", land: "Nordrhein-Westfalen" },
        frankfurt: { name: "Frankfurt am Main", zh: "法兰克福", land: "Hessen" },
        bremen: { name: "Bremen", zh: "不来梅", land: "Bremen" },
      },
      names: { male: N.deMale, female: N.deFemale, last: N.deLast },
      mail: ["gmail.com", "web.de", "gmx.de", "gmx.de", "t-online.de", "outlook.de", "yahoo.de"],
      phone: () => `+49 ${pick([151, 152, 157, 159, 160, 162, 163, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179])} ${String(between(1000000, 99999999))}`,
      address(row, region) {
        const [street, number, plz, city] = row;
        return {
          street: `${street} ${number}`,
          zip: plz,
          city,
          state: region.land,
          fullAddress: `${street} ${number}, ${plz} ${city}`,
        };
      },
      fields: [
        ["firstName", "名 / Vorname"], ["lastName", "姓 / Nachname"],
        ["gender", "性别 / Gender"], ["phone", "电话 / Telefon"],
        ["street", "街道门牌 / Straße & Hausnummer"],
        ["zip", "邮编 / PLZ"], ["city", "城市 / Ort"],
        ["state", "联邦州 / Bundesland"], ["email", "电子邮件 / E-Mail"],
        ["fullAddress", "完整地址 / Full Address"],
      ],
      wide: ["street", "email", "fullAddress"],
      maps: (rec) => rec.fullAddress,
    },

    // Row: [street, suburb, postcode, state]
    au: {
      dataDir: "au",
      regionWord: "城市",
      regions: {
        sydney: { name: "Sydney", zh: "悉尼" },
        melbourne: { name: "Melbourne", zh: "墨尔本" },
        brisbane: { name: "Brisbane", zh: "布里斯班" },
        "gold-coast": { name: "Gold Coast", zh: "黄金海岸" },
        canberra: { name: "Canberra", zh: "堪培拉" },
      },
      names: { male: N.enMale, female: N.enFemale, last: N.enLast },
      mail: ["gmail.com", "gmail.com", "outlook.com", "bigpond.com", "yahoo.com.au", "icloud.com", "hotmail.com"],
      phone: () => `04${between(0, 99).toString().padStart(2, "0")} ${String(between(0, 999)).padStart(3, "0")} ${String(between(0, 999)).padStart(3, "0")}`,
      address(row) {
        const [street, suburb, postcode, state] = row;
        return {
          street, city: suburb, stateCode: state, zip: postcode,
          fullAddress: `${street}, ${suburb} ${state} ${postcode}`,
        };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["gender", "性别 / Gender"], ["phone", "电话 / Phone"],
        ["street", "街道地址 / Street Address"],
        ["city", "区 / Suburb"], ["stateCode", "州 / State"],
        ["zip", "邮编 / Postcode"], ["email", "电子邮件 / Email"],
        ["fullAddress", "完整地址 / Full Address"],
      ],
      wide: ["street", "email", "fullAddress"],
      maps: (rec) => rec.fullAddress,
    },

    gb: osmCountry({
      dataDir: "gb",
      regions: {
        london: { name: "London", zh: "伦敦" }, manchester: { name: "Manchester", zh: "曼彻斯特" },
        birmingham: { name: "Birmingham", zh: "伯明翰" }, edinburgh: { name: "Edinburgh", zh: "爱丁堡" },
        glasgow: { name: "Glasgow", zh: "格拉斯哥" },
      },
      names: { male: N.ukMale, female: N.ukFemale, last: N.ukLast },
      mail: ["gmail.com", "gmail.com", "outlook.com", "hotmail.co.uk", "yahoo.co.uk", "icloud.com", "btinternet.com"],
      phone: () => `07${pick([4, 5, 7, 8, 9])}${digits(2)} ${digits(6)}`,
      format: (a) => `${a.number} ${a.street}, ${a.city} ${a.postcode}`,
      labels: { state: "地区 / Country", zip: "邮编 / Postcode" },
    }),

    tr: osmCountry({
      dataDir: "tr",
      regions: {
        istanbul: { name: "İstanbul", zh: "伊斯坦布尔" }, ankara: { name: "Ankara", zh: "安卡拉" }, izmir: { name: "İzmir", zh: "伊兹密尔" },
      },
      names: { male: N.trMale, female: N.trFemale, last: N.trLast },
      mail: ["gmail.com", "gmail.com", "hotmail.com", "outlook.com", "yandex.com", "yahoo.com", "icloud.com"],
      phone: () => `+90 5${pick([0, 3, 4, 5])}${digits(1)} ${digits(3)} ${digits(2)} ${digits(2)}`,
      line: (a) => `${a.street} No:${a.number}`,
      format: (a) => `${a.street} No:${a.number}, ${a.postcode} ${a.suburb ? `${a.suburb}/` : ""}${a.city}`,
      labels: { street: "街道门牌 / Cadde-Sokak No", suburb: "区 / İlçe-Mahalle", state: "省 / İl", zip: "邮编 / Posta Kodu" },
    }),

    in: osmCountry({
      dataDir: "in",
      regions: {
        mumbai: { name: "Mumbai", zh: "孟买" }, delhi: { name: "Delhi", zh: "新德里" }, bengaluru: { name: "Bengaluru", zh: "班加罗尔" },
        chennai: { name: "Chennai", zh: "金奈" }, hyderabad: { name: "Hyderabad", zh: "海得拉巴" }, kolkata: { name: "Kolkata", zh: "加尔各答" },
      },
      names: { male: N.inMale, female: N.inFemale, last: N.inLast },
      mail: ["gmail.com", "gmail.com", "gmail.com", "yahoo.co.in", "outlook.com", "rediffmail.com", "hotmail.com"],
      phone: () => `+91 ${pick([6, 7, 8, 9])}${digits(4)} ${digits(5)}`,
      line: (a) => `${a.number}, ${a.street}`,
      format: (a) => `${a.number}, ${a.street}, ${a.suburb ? `${a.suburb}, ` : ""}${a.city}, ${a.state} ${a.postcode}`,
      labels: { suburb: "区域 / Locality", zip: "邮编 / PIN Code" },
    }),

    ph: osmCountry({
      dataDir: "ph",
      regions: {
        "metro-manila": { name: "Metro Manila", zh: "马尼拉大都会" }, cebu: { name: "Cebu City", zh: "宿务" }, davao: { name: "Davao City", zh: "达沃" },
      },
      names: { male: N.phMale, female: N.phFemale, last: N.phLast },
      mail: ["gmail.com", "gmail.com", "yahoo.com", "yahoo.com.ph", "outlook.com", "hotmail.com", "icloud.com"],
      phone: () => `+63 9${digits(2)} ${digits(3)} ${digits(4)}`,
      format: (a) => `${a.number} ${a.street}, ${a.suburb ? `${a.suburb}, ` : ""}${a.city}, ${a.state} ${a.postcode}`,
      labels: { suburb: "区/巴朗盖 / Barangay", state: "省/大区 / Province" },
    }),

    ng: osmCountry({
      dataDir: "ng",
      regions: {
        lagos: { name: "Lagos", zh: "拉各斯" }, abuja: { name: "Abuja", zh: "阿布贾" },
        ibadan: { name: "Ibadan", zh: "伊巴丹" }, "port-harcourt": { name: "Port Harcourt", zh: "哈科特港" },
      },
      names: { male: N.ngMale, female: N.ngFemale, last: N.ngLast },
      mail: ["gmail.com", "gmail.com", "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"],
      phone: () => `+234 ${pick(["803", "806", "813", "816", "703", "706", "810", "814", "903", "906", "805", "807", "815", "905", "802", "808", "812", "701", "708", "902"])} ${digits(3)} ${digits(4)}`,
      format: (a) => `${a.number} ${a.street}, ${a.suburb ? `${a.suburb}, ` : ""}${a.city}, ${a.state === "FCT" ? "FCT" : `${a.state} State`}${a.postcode ? ` ${a.postcode}` : ""}`,
      labels: { suburb: "区域 / Area", state: "州 / State" },
    }),

    // Row: [number, street, building, postcode]
    sg: {
      dataDir: "sg",
      regionWord: "地区",
      regions: { SG: { name: "Singapore", zh: "新加坡" } },
      names: { male: N.sgMale, female: N.sgFemale, last: N.sgLast },
      localName: (last, first) => last + first,
      mail: ["gmail.com", "gmail.com", "yahoo.com.sg", "outlook.com", "hotmail.com", "icloud.com", "singnet.com.sg"],
      phone: () => `+65 ${pick([8, 9])}${String(between(0, 999)).padStart(3, "0")} ${String(between(0, 9999)).padStart(4, "0")}`,
      address(row) {
        const [number, street, building, postcode] = row;
        const line1 = `${number} ${street}`;
        return {
          street: line1,
          building,
          zip: postcode,
          fullAddress: [line1, building, `Singapore ${postcode}`].filter(Boolean).join(", "),
        };
      },
      fields: [
        ["firstName", "名 / First Name"], ["lastName", "姓 / Last Name"],
        ["localName", "中文姓名 / Chinese Name"], ["gender", "性别 / Gender"],
        ["phone", "电话 / Phone"], ["zip", "邮编 / Postal Code"],
        ["street", "街道门牌 / Street"], ["building", "建筑名 / Building"],
        ["email", "电子邮件 / Email"],
        ["fullAddress", "完整地址 / Full Address"],
      ],
      wide: ["street", "email", "fullAddress"],
      maps: (rec) => rec.fullAddress,
    },
  };
})();
