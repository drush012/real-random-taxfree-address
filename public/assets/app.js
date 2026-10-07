/* Address generator engine. Each page sets window.PAGE = { country, regions?, saveTag }.
 * Country specifics live in countries.js; random helpers and name pools in names.js. */
(() => {
  "use strict";

  const { rand, pick, between } = window.RNG;
  const PAGE = window.PAGE;
  const C = window.COUNTRIES[PAGE.country];
  let REGION_CODES = PAGE.regions || Object.keys(C.regions);  // narrowed to regions with data once the manifest loads
  const STORE_KEY = "taxfree-address:saved:v1";

  const JOBS = ["Software Developer", "Registered Nurse", "Teacher", "Accountant", "Sales Representative", "Electrician",
    "Graphic Designer", "Marketing Specialist", "Project Manager", "Pharmacist", "Mechanical Engineer", "Chef",
    "Customer Service Representative", "Data Analyst", "Dental Hygienist", "Real Estate Agent", "Physical Therapist",
    "Carpenter", "Administrative Assistant", "Financial Advisor", "Truck Driver", "Plumber", "Web Developer",
    "Human Resources Specialist", "Retail Manager", "Paralegal", "Veterinary Technician", "Photographer",
    "Civil Engineer", "Insurance Agent", "Construction Manager", "Librarian", "Medical Assistant", "Student"];

  const ID_FIELDS = [["birthday", "生日 / Date of Birth"], ["occupation", "职业 / Occupation"]];
  const SSN_FIELDS = [["ssn", "社会安全号 / SSN"]];
  const CARD_FIELDS = [
    ["cardType", "卡组织 / Card Type"], ["cardNumber", "卡号 / Card Number"],
    ["cardExpiry", "有效期 / Expiry"], ["cardCvv", "CVV"],
  ];
  const WIDE = new Set([...(C.wide || []), "ssn"]);
  // Colour group per field (see .row[data-group] in style.css); anything unlisted is an address field.
  const GROUP = {
    lastName: "name", firstName: "name", localName: "name", gender: "name",
    phone: "contact", email: "contact",
    birthday: "id", occupation: "id", ssn: "id",
    cardType: "card", cardNumber: "card", cardExpiry: "card", cardCvv: "card",
  };

  // Publicly documented test card numbers (Stripe / Braintree docs). They pass Luhn checks but never charge.
  const TEST_CARDS = [
    ["Visa", "4242424242424242"], ["Visa", "4000056655665556"], ["Visa", "4111111111111111"],
    ["Visa", "4012888888881881"], ["Mastercard", "5555555555554444"], ["Mastercard", "2223003122003222"],
    ["Mastercard", "5105105105105100"], ["Mastercard", "5200828282828210"],
    ["American Express", "378282246310005"], ["American Express", "371449635398431"],
    ["Discover", "6011111111111117"], ["Discover", "6011000990139424"],
  ];

  const $ = (id) => document.getElementById(id);
  const has = (id) => !!document.getElementById(id);

  let manifest = null;
  const cache = {};
  let region = "RANDOM";
  let current = null;
  let saved = loadSaved();

  /* ---------- random person ---------- */

  // Name pool entries are either "Latin" or ["Latin", "本地写法"].
  const latin = (n) => (Array.isArray(n) ? n[0] : n);
  const local = (n) => (Array.isArray(n) ? n[1] : "");

  function birthday() {
    const now = new Date();
    const d = new Date(now.getFullYear() - between(21, 62), rand(12), 1 + rand(28));
    return `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}/${d.getFullYear()}`;
  }

  const ascii = (s) => s.toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss").replace(/ı/g, "i")
    .normalize("NFKD").replace(/[^a-z]/g, "");

  function email(first, last) {
    const f = ascii(latin(first));
    const l = ascii(latin(last));
    const style = rand(4);
    const local = style === 0 ? `${f}.${l}${between(1, 99)}`
      : style === 1 ? `${f}${l}${between(10, 999)}`
      : style === 2 ? `${f[0]}${l}${between(10, 99)}`
      : `${f}_${l}${between(1980, 2004)}`;
    return `${local}@${pick(C.mail)}`;
  }

  // Random area (001-899, never 666) with group number 00: the SSA has never issued group 00,
  // so these look ordinary but can never be a real person's SSN.
  function sampleSsn() {
    let area;
    do { area = between(1, 899); } while (area === 666);
    return `${String(area).padStart(3, "0")}-00-${String(between(1, 9999)).padStart(4, "0")}`;
  }

  function testCard() {
    const [type, num] = pick(TEST_CARDS);
    const groups = type === "American Express" ? [4, 6, 5] : [4, 4, 4, 4];
    let i = 0;
    const number = groups.map((n) => num.slice(i, (i += n))).join(" ");
    const month = String(1 + rand(12)).padStart(2, "0");
    const year = String(new Date().getFullYear() + between(1, 5)).slice(-2);
    const cvv = type === "American Express" ? String(between(0, 9999)).padStart(4, "0") : String(between(0, 999)).padStart(3, "0");
    return { cardType: type, cardNumber: number, cardExpiry: `${month}/${year}`, cardCvv: cvv };
  }

  /* ---------- data ---------- */

  async function loadRegion(code) {
    if (!cache[code]) {
      cache[code] = fetch(`/data/${C.dataDir}/${code}.json`).then((r) => {
        if (!r.ok) throw new Error(`${code}: HTTP ${r.status}`);
        return r.json();
      });
      cache[code].catch(() => { delete cache[code]; });
    }
    return cache[code];
  }

  async function generate() {
    const code = region === "RANDOM" ? pick(REGION_CODES) : region;
    let rows;
    try {
      rows = await loadRegion(code);
    } catch (err) {
      console.error(err);
      toast("地址数据加载失败，请重试");
      return;
    }
    const reg = { code, ...C.regions[code] };
    const row = pick(rows);
    const isMale = rand(2) === 0;
    const first = pick(isMale ? C.names.male : C.names.female);
    const last = pick(C.names.last);
    const rec = {
      country: PAGE.country,
      firstName: latin(first),
      lastName: latin(last),
      gender: isMale ? "Male" : "Female",
      phone: C.phone(reg, row),
      email: email(first, last),
      ...C.address(row, reg),
    };
    if (C.localName && local(last) && local(first)) rec.localName = C.localName(local(last), local(first));
    if (has("withIdentity") && $("withIdentity").checked) {
      rec.birthday = birthday();
      rec.occupation = pick(JOBS);
    }
    if (C.ssn && has("withSsn") && $("withSsn").checked) rec.ssn = sampleSsn();
    if (has("withCard") && $("withCard").checked) Object.assign(rec, testCard());
    current = rec;
    render(rec);
  }

  /* ---------- rendering ---------- */

  function render(rec) {
    const grid = $("grid");
    grid.textContent = "";
    const fields = C.fields.concat(rec.birthday ? ID_FIELDS : [], rec.ssn ? SSN_FIELDS : [], rec.cardNumber ? CARD_FIELDS : []);
    for (const [key, label] of fields) {
      if (rec[key] == null || rec[key] === "") continue;
      const row = document.createElement("div");
      row.className = WIDE.has(key) ? "row wide" : "row";
      row.dataset.key = key;
      row.dataset.group = GROUP[key] || "address";
      row.tabIndex = 0;
      row.setAttribute("role", "button");
      row.setAttribute("aria-label", `复制${label}`);
      const k = document.createElement("span");
      k.className = "k";
      k.textContent = label;
      const v = document.createElement("span");
      v.className = "v";
      v.textContent = rec[key];
      row.append(k, v);
      if (key === "fullAddress") {
        const map = document.createElement("a");
        map.className = "map";
        map.target = "_blank";
        map.rel = "noopener";
        map.href = "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(C.maps(rec));
        map.textContent = "📍 验证地址";
        row.append(map);
      }
      const ic = document.createElement("span");
      ic.className = "ic";
      ic.innerHTML = '<svg width="18" height="18" aria-hidden="true"><use href="#i-copy"/></svg>';
      row.append(ic);
      grid.append(row);
    }
  }

  function asText(rec) {
    const labels = C.fields.concat(ID_FIELDS, SSN_FIELDS, CARD_FIELDS);
    return labels
      .filter(([key]) => rec[key] != null && rec[key] !== "")
      .map(([key, label]) => `${label.split(" / ").pop()}: ${rec[key]}`)
      .join("\n");
  }

  /* ---------- clipboard / toast ---------- */

  async function copy(text, el) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.append(ta);
      ta.select();
      try { document.execCommand("copy"); } catch { /* ignore */ }
      ta.remove();
    }
    if (el) {
      el.classList.add("copied");
      setTimeout(() => el.classList.remove("copied"), 900);
    }
    toast("已复制");
  }

  let toastTimer;
  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 1300);
  }

  /* ---------- saved list (shared by every page) ---------- */

  function loadSaved() {
    try {
      const v = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
      return Array.isArray(v) ? v : [];
    } catch {
      return [];
    }
  }

  function persist() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(saved)); } catch { /* storage unavailable */ }
    renderSaved();
  }

  function renderSaved() {
    if (has("navCount")) $("navCount").textContent = saved.length;
    if (!has("savedBody")) return;
    const body = $("savedBody");
    body.textContent = "";
    $("savedCount").textContent = saved.length;
    $("savedEmpty").hidden = saved.length > 0;
    saved.forEach((r, i) => {
      const tr = document.createElement("tr");
      const name = document.createElement("td");
      name.textContent = `${r.firstName} ${r.lastName}`;
      const addr = document.createElement("td");
      addr.className = "addr";
      addr.textContent = r.fullAddress;
      const phone = document.createElement("td");
      phone.className = "num";
      phone.textContent = r.phone;
      const act = document.createElement("td");
      const del = document.createElement("button");
      del.type = "button";
      del.className = "del";
      del.setAttribute("aria-label", "删除");
      del.textContent = "✕";
      del.addEventListener("click", () => { saved.splice(i, 1); persist(); });
      act.append(del);
      tr.append(name, addr, phone, act);
      body.append(tr);
    });
  }

  function download(name, text, type) {
    const blob = new Blob([text], { type });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  const CSV_COLS = ["country", "firstName", "lastName", "localName", "gender", "phone", "email", "street", "district", "city", "county",
    "stateCode", "state", "region", "zip", "localAddress", "birthday", "occupation", "ssn", "cardType", "cardNumber", "cardExpiry", "cardCvv", "fullAddress"];
  function toCsv(rows) {
    const cols = CSV_COLS.filter((c) => rows.some((r) => r[c] != null && r[c] !== ""));
    const esc = (v) => {
      const s = v == null ? "" : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    return "﻿" + [cols.join(",")].concat(rows.map((r) => cols.map((c) => esc(r[c])).join(","))).join("\n");
  }

  /* ---------- wiring ---------- */

  function fillRegions() {
    const sel = $("regionSelect");
    const opt = (value, text) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = text;
      sel.append(o);
    };
    opt("RANDOM", PAGE.randomLabel || "随机");
    for (const code of REGION_CODES) {
      const r = C.regions[code];
      opt(code, r.zh === r.name ? r.name : `${r.zh} (${r.name})`);
    }
  }

  function bind() {
    $("regionSelect").addEventListener("change", (e) => {
      region = e.target.value;
      generate();
    });
    $("generate").addEventListener("click", () => {
      const b = $("generate");
      b.classList.remove("spin");
      void b.offsetWidth;
      b.classList.add("spin");
      generate();
    });
    for (const id of ["withIdentity", "withSsn", "withCard"]) {
      if (has(id)) $(id).addEventListener("change", () => { if (current) generate(); });
    }
    const copyRow = (e) => {
      if (e.target.closest("a")) return;
      const row = e.target.closest(".row");
      if (row && current) copy(current[row.dataset.key], row);
    };
    $("grid").addEventListener("click", copyRow);
    $("grid").addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); copyRow(e); }
    });
    $("copyAll").addEventListener("click", () => current && copy(asText(current)));
    $("save").addEventListener("click", () => {
      if (!current) return;
      if (saved.some((r) => r.fullAddress === current.fullAddress && r.email === current.email)) return toast("已经保存过了");
      saved.unshift(current);
      persist();
      toast("已保存");
    });
    $("exportCsv").addEventListener("click", () => saved.length ? download("addresses.csv", toCsv(saved), "text/csv;charset=utf-8") : toast("没有可导出的记录"));
    $("exportJson").addEventListener("click", () => saved.length ? download("addresses.json", JSON.stringify(saved, null, 2), "application/json") : toast("没有可导出的记录"));
    $("clearAll").addEventListener("click", () => {
      if (!saved.length) return;
      if (confirm(`删除全部 ${saved.length} 条已保存的地址？`)) { saved = []; persist(); }
    });
    document.addEventListener("click", (e) => {
      for (const d of document.querySelectorAll("details.more[open]")) if (!d.contains(e.target)) d.open = false;
    });
  }

  async function init() {
    bind();
    renderSaved();
    try {
      const res = await fetch(`/data/${C.dataDir}/manifest.json`);
      if (!res.ok) throw new Error(res.status);
      manifest = await res.json();
      REGION_CODES = REGION_CODES.filter((c) => manifest.regions[c] > 0);
      fillRegions();
      const total = REGION_CODES.reduce((n, c) => n + (manifest.regions[c] || 0), 0);
      const cities = REGION_CODES.reduce((n, c) => n + (manifest.cities[c] || 0), 0);
      // Row index 1 is the city for most countries; others set regionWord and count regions instead.
      const extra = C.regionWord
        ? (REGION_CODES.length > 1 ? ` · ${REGION_CODES.length} 个${C.regionWord}` : "")
        : ` · ${cities.toLocaleString()} 个城市`;
      $("stats").textContent = `地址库 ${total.toLocaleString()} 条${extra}`;
      $("generate").disabled = false;
      await generate();
    } catch (err) {
      $("stats").textContent = "地址库加载失败，请刷新重试";
      console.error(err);
    }
  }

  init();
})();
