/* MAC address generator (/mac/) and vendor lookup (/mac-lookup/).
 * Vendor data: /data/oui.json = { "F0D1A9": ["Apple, Inc.", "US"], ... } built from the IEEE MA-L registry. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const has = (id) => !!document.getElementById(id);
  const rand = (n) => {
    const a = new Uint32Array(1);
    crypto.getRandomValues(a);
    return a[0] % n;
  };
  const hex2 = (n) => n.toString(16).padStart(2, "0").toUpperCase();

  // Label -> regular expression over the IEEE organization name.
  const VENDORS = [
    ["Apple", /^Apple, Inc/i], ["Samsung 三星", /^Samsung Electronics/i], ["Huawei 华为", /^HUAWEI TECHNOLOGIES|^Huawei Device/i],
    ["Xiaomi 小米", /^Xiaomi Communications/i], ["OPPO", /^GUANGDONG OPPO/i], ["vivo", /^vivo Mobile/i],
    ["Intel", /^Intel Corporate/i], ["Cisco", /^Cisco Systems/i], ["TP-Link", /^TP-LINK/i], ["Dell", /^Dell Inc/i],
    ["HP / HPE", /^Hewlett Packard/i], ["Lenovo 联想", /^LCFC|^Lenovo/i], ["ASUS 华硕", /^ASUSTek/i],
    ["Google", /^Google, Inc/i], ["Amazon", /^Amazon Technologies/i], ["Microsoft", /^Microsoft/i],
    ["Sony", /^Sony/i], ["Espressif (ESP32)", /^Espressif/i], ["Raspberry Pi", /^Raspberry Pi/i], ["Realtek", /^Realtek/i],
  ];

  const COUNTRY = {
    US: "美国", CN: "中国", KR: "韩国", TW: "台湾", JP: "日本", DE: "德国", GB: "英国", MY: "马来西亚", CA: "加拿大",
    FR: "法国", HK: "香港", IN: "印度", IT: "意大利", NL: "荷兰", SE: "瑞典", CH: "瑞士", IL: "以色列", SG: "新加坡",
    FI: "芬兰", AU: "澳大利亚", ES: "西班牙", DK: "丹麦", NO: "挪威", AT: "奥地利", BE: "比利时", VN: "越南", TH: "泰国",
  };

  let oui = null;
  let byVendor = {};
  let generated = [];

  async function load() {
    const res = await fetch("/data/oui.json");
    if (!res.ok) throw new Error(res.status);
    oui = await res.json();
    const prefixes = Object.keys(oui);
    for (const [label, re] of VENDORS) byVendor[label] = prefixes.filter((p) => re.test(oui[p][0]));
    byVendor.__any = prefixes;
    $("stats").textContent = `IEEE 厂商库 ${prefixes.length.toLocaleString()} 个前缀`;
  }

  function format(bytes, sep, lower) {
    const h = bytes.map(hex2);
    let s = sep === "." ? [h[0] + h[1], h[2] + h[3], h[4] + h[5]].join(".") : h.join(sep);
    return lower ? s.toLowerCase() : s;
  }

  let toastTimer;
  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 1300);
  }

  async function copy(text, el) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
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

  /* ---------- generator ---------- */

  function generate() {
    const vendor = $("vendor").value;
    const n = Math.max(1, Math.min(100, parseInt($("count").value, 10) || 1));
    $("count").value = n;
    const sep = $("format").value;
    const lower = $("lower").checked;
    generated = [];
    for (let i = 0; i < n; i++) {
      let bytes, owner;
      if (vendor === "__local") {
        // Locally administered unicast: second-lowest bit of the first byte set, lowest bit clear.
        bytes = [(rand(256) & 0xfc) | 0x02, rand(256), rand(256), rand(256), rand(256), rand(256)];
        owner = "本地管理地址（随机）";
      } else {
        const pool = byVendor[vendor];
        const p = pool[rand(pool.length)];
        bytes = [parseInt(p.slice(0, 2), 16), parseInt(p.slice(2, 4), 16), parseInt(p.slice(4, 6), 16), rand(256), rand(256), rand(256)];
        owner = oui[p][0];
      }
      generated.push({ mac: format(bytes, sep, lower), owner });
    }
    const list = $("list");
    list.textContent = "";
    generated.forEach((g, i) => {
      const row = document.createElement("div");
      row.className = "row";
      row.tabIndex = 0;
      row.setAttribute("role", "button");
      row.dataset.i = i;
      const k = document.createElement("span");
      k.className = "k";
      k.textContent = g.owner;
      const v = document.createElement("span");
      v.className = "v mono";
      v.textContent = g.mac;
      const ic = document.createElement("span");
      ic.className = "ic";
      ic.innerHTML = '<svg width="18" height="18" aria-hidden="true"><use href="#i-copy"/></svg>';
      row.append(k, v, ic);
      list.append(row);
    });
  }

  function initGenerator() {
    const sel = $("vendor");
    const add = (value, text) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = text;
      sel.append(o);
    };
    add("__local", "随机（本地管理地址）");
    add("__any", "随机真实厂商");
    for (const [label] of VENDORS) if (byVendor[label].length) add(label, `${label}（${byVendor[label].length} 个前缀）`);
    sel.value = "Apple";
    for (const id of ["vendor", "format", "lower"]) $(id).addEventListener("change", generate);
    $("generate").addEventListener("click", generate);
    const pick = (e) => {
      const row = e.target.closest(".row");
      if (row) copy(generated[row.dataset.i].mac, row);
    };
    $("list").addEventListener("click", pick);
    $("list").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(e); } });
    $("copyAll").addEventListener("click", () => generated.length && copy(generated.map((g) => g.mac).join("\n")));
    $("generate").disabled = false;
    generate();
  }

  /* ---------- lookup ---------- */

  function lookup() {
    const body = $("resultBody");
    body.textContent = "";
    const lines = $("input").value.split(/\n+/).map((s) => s.trim()).filter(Boolean).slice(0, 200);
    for (const line of lines) {
      const hex = line.replace(/[^0-9a-fA-F]/g, "").toUpperCase();
      const tr = document.createElement("tr");
      const cells = [];
      if (hex.length < 6) {
        cells.push(line, "格式不正确", "", "");
      } else {
        const first = parseInt(hex.slice(0, 2), 16);
        const local = (first & 2) !== 0;
        const multicast = (first & 1) !== 0;
        const hit = oui[hex.slice(0, 6)];
        const pretty = hex.length >= 12 ? hex.slice(0, 12).match(/../g).join(":") : hex.match(/../g).join(":");
        const vendor = hit ? hit[0] : local ? "本地管理地址（随机 MAC，无厂商）" : "未在 IEEE 注册表中找到";
        cells.push(pretty, vendor, hit ? (COUNTRY[hit[1]] ? `${COUNTRY[hit[1]]} (${hit[1]})` : hit[1]) : "",
          `${multicast ? "组播" : "单播"} · ${local ? "本地管理" : "全球唯一"}`);
      }
      cells.forEach((c, i) => {
        const td = document.createElement("td");
        td.textContent = c;
        if (i === 0) td.className = "num mono";
        tr.append(td);
      });
      body.append(tr);
    }
    $("resultEmpty").hidden = lines.length > 0;
  }

  function initLookup() {
    $("lookup").addEventListener("click", lookup);
    $("input").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) lookup(); });
    $("lookup").disabled = false;
    const q = new URLSearchParams(location.search).get("mac");
    if (q) {
      $("input").value = q;
      lookup();
    }
  }

  load().then(() => {
    if (has("vendor")) initGenerator();
    if (has("lookup")) initLookup();
  }).catch((err) => {
    $("stats").textContent = "厂商库加载失败，请刷新重试";
    console.error(err);
  });
})();
