/* Cena Checker - ban WEB TINH (GitHub Pages).
   Toan bo chay trong trinh duyet: doc du lieu tu docs/data/*.json.
   - Quet ma vach: chi tai 1 manh EAN nho (~20KB) -> rat nhanh
   - Tim theo ten: tai catalog (1.9MB nen) mot lan roi cache
*/
'use strict';

var SHOP = ['Tamda Foods', 'Makro', 'Bidfood', 'dathang.cz',
            'Linsan24h', 'Bombacena', 'PTT Global', 'JIP', 'JUNIORpapír'];
var SHOP_SLUG = ['tamda', 'makro', 'bidfood', 'dathang', 'linsan',
                 'bombacena', 'ptt', 'jip', 'juniorpapir'];
var WHOLESALE_FILTERS = [['tamda', '🅣 Tamda'], ['makro', 'Ⓜ Makro'],
  ['jip', '🄹 JIP'], ['bidfood', '🅑 Bidfood'], ['dathang', '🅳 dathang'],
  ['linsan', '🅻 Linsan'], ['bombacena', '🅱 Bombacena'], ['ptt', '🅟 PTT Global'],
  ['juniorpapir', '🅹 JUNIORpapír']];
/* Loc ban buon hien tren trang Akce (co JIP vi JIP co deal akce tu kupi) */
var AKCE_WS_FILTERS = [['makro', 'Ⓜ Makro'], ['jip', '🄹 JIP'], ['tamda', '🅣 Tamda'],
  ['bidfood', '🅑 Bidfood'], ['ptt', '🅟 PTT Global'], ['dathang', '🅳 dathang'],
  ['linsan', '🅻 Linsan'], ['bombacena', '🅱 Bombacena'], ['juniorpapir', '🅹 JUNIORpapír']];
var RETAIL_FILTERS = ['Lidl', 'Kaufland', 'Billa', 'Penny', 'Tesco', 'Albert',
  'Globus', 'COOP', 'Hruška', 'Flop', 'Ratio', 'Košík'];
/* So nut ban le hien san; con lai an sau nut "…" (muc 6) */
var RETAIL_SHOWN = 6;
/* Dong nghia tim kiem: 1 tu Viet -> nhieu tu Sec (OR). VD banh mi -> rohlik + chleb */
var SEARCH_SYNONYMS = {
  'banh mi': ['rohlik', 'chleb'], 'banh my': ['rohlik', 'chleb'],
  'rohlik': ['rohlik', 'chleb'],
  'dua': ['ananas', 'meloun', 'kokos', 'dua'],
  'thanh long': ['pitahaya', 'draci ovoce']
};
var TILES = [['🍎', 'Rau quả', 'ovoce'], ['🥩', 'Thịt cá', 'maso'],
  ['🥛', 'Sữa trứng', 'mleko'], ['🍞', 'Bánh mì', 'pecivo'],
  ['🍫', 'Bánh kẹo', 'sladkosti'], ['🍺', 'Bia', 'pivo'],
  ['🥤', 'Đồ uống', 'napoje'], ['☕', 'Cà phê & trà', 'kava'],
  ['🧴', 'Drogerie', 'drogerie'], ['🐶', 'Thú cưng', 'mazlicci']];
var CAT_WORDS = {
  ovoce: ['ovoce', 'ovocn', 'zelenina', 'jablk', 'banan', 'banán', 'hrozn', 'meloun',
    'ananas', 'pomeranc', 'pomeranč', 'mandarink', 'broskv', 'svestk', 'tresn',
    'jahod', 'boruvk', 'malin', 'hrusk', 'avokad', 'kokos', 'mango', 'kiwi',
    'limetk', 'citron', 'ostruzin', 'brusink', 'merunk', 'meruňk', 'fik', 'datle',
    'granatov', 'kaki', 'pitahaya', 'papaj', 'papáj', 'marakuja',
    'rajcat', 'brambor', 'cibul', 'mrkev', 'okurk', 'paprik', 'zeli', 'salat',
    'spenat', 'houb', 'kvetak', 'brokolic', 'kukuric', 'dyne', 'cuket', 'lilek',
    'redkev', 'repa', 'celer', 'porek', 'chrest', 'tofu', 'klicky', 'bylink',
    'koriandr', 'bazalk', 'kopr', 'cesnek', 'zazvor', 'chilli'],
  maso: ['maso', 'kureci', 'veprov', 'hovezi', 'ryba', 'losos', 'sunka', 'parky', 'krevet'],
  mleko: ['mleko', 'jogurt', 'syr', 'maslo', 'vejce', 'smetana', 'tvaroh', 'eidam'],
  pecivo: ['chleb', 'rohlik', 'pecivo', 'toast', 'croissant', 'bageta'],
  sladkosti: ['cokolad', 'bonbon', 'susenk', 'oplatk', 'chipsy', 'sladk', 'dort'],
  pivo: ['pivo', 'lezak', 'plzen', 'gambrinus', 'kozel', 'radegast', 'staropramen', 'birell'],
  napoje: ['voda', 'limonad', 'dzus', 'napoj', 'cola', 'kofola', 'sirup', 'mineraln'],
  kava: ['kava', 'caj', 'espresso', 'nescafe', 'cappuccino', 'jacobs', 'tchibo'],
  drogerie: ['praci', 'sampon', 'mydlo', 'zubni', 'toaletni', 'ubrousky', 'cistic', 'gel'],
  mazlicci: ['psy', 'kocky', 'granule', 'kapsick', 'stelivo', 'pamlsk']
};

var DATA = { dict: null, catalog: null, retail: null, meta: null, shards: null };
var $ = function (s) { return document.querySelector(s); };

/* ---------- tien ich ---------- */
var _rng = (function (s) {
  return function () {
    s |= 0; s = s + 0x6D2B79F5 | 0;
    var t = Math.imul(s ^ s >>> 15, 1 | s);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
})(Date.now());
function stripAccents(s) {
  return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
  });
}
/* Chong CACHE: gan dau thoi diem build vao moi file du lieu. Khong co no,
   trinh duyet giu ban cu -> cap nhat gia xong ma may nguoi dung van thay so cu. */
function getJSON(url) {
  var u = url;
  if (u.indexOf('data/') === 0 && u.indexOf('?') < 0 && DATA.cb) u += '?v=' + DATA.cb;
  return fetch(u).then(function (r) {
    if (!r.ok) throw new Error(r.status);
    return r.json();
  });
}

/* ---------- tu dien Viet -> Sec (ghep cum dai nhat) ---------- */
function viTranslate(q) {
  var d = DATA.dict;
  if (!d) return q;
  if (d[q]) return d[q];
  var w = q.split(/\s+/), out = [], i = 0, changed = false;
  while (i < w.length) {
    var hit = false;
    for (var k = Math.min(4, w.length - i); k > 0; k--) {
      var phrase = w.slice(i, i + k).join(' ');
      if (d[phrase]) { out.push(d[phrase]); i += k; changed = hit = true; break; }
    }
    if (!hit) { out.push(w[i]); i++; }
  }
  return changed ? out.join(' ') : q;
}

/* ---------- ma vach: bien the theo chuan GS1 ---------- */
function gtinCheck(d) {
  var s = 0, r = d.split('').reverse();
  for (var i = 0; i < r.length; i++) s += (+r[i]) * (i % 2 === 0 ? 3 : 1);
  return String((10 - s % 10) % 10);
}
function eanVariants(code) {
  var out = [code], b;
  if (code.length === 12) { out.push(code + gtinCheck(code)); out.push('0' + code); }
  if (code.length === 14) {
    if (code[0] === '0') out.push(code.slice(1));
    b = code.slice(1, 13); out.push(b + gtinCheck(b));
  }
  if (code.length === 13) {
    if (code[0] === '0') out.push(code.slice(1));
    b = code.slice(0, 12);
    for (var i = 1; i <= 8; i++) out.push(i + b + gtinCheck(i + b));
  }
  return out;
}

/* ---------- tai du lieu ---------- */
function loadDict() {
  if (DATA.dict) return Promise.resolve(DATA.dict);
  return getJSON('data/dict.json').then(function (d) { return (DATA.dict = d); })
    .catch(function () { return (DATA.dict = {}); });
}
function loadShardIndex() {
  if (DATA.shards) return Promise.resolve(DATA.shards);
  // shards.json: ten KHONG co gach duoi (Jekyll cua GitHub Pages bo qua file "_*")
  return getJSON('data/ean/shards.json').then(function (a) {
    return (DATA.shards = new Set(a));
  }).catch(function () {
    return getJSON('data/ean/_index.json').then(function (a) {   // ban cu
      return (DATA.shards = new Set(a));
    }).catch(function () { return (DATA.shards = new Set()); });
  });
}
/* Tra ma vach: tai TUNG manh mot, thay la dung ngay (tiet kiem 3G).
   Ma goc thu truoc, cac bien the (ma bich GTIN-14) chi thu khi khong thay. */
function eanLookup(code) {
  return loadShardIndex().then(function (idx) {
    var codes = eanVariants(code), i = 0;
    function shardOf(c) {
      for (var L = 8; L >= 3; L--) { var p = c.slice(0, L); if (idx.has(p)) return p; }
      return null;
    }
    function next() {
      if (i >= codes.length) return null;
      var c = codes[i++], p = shardOf(c);
      if (!p) return next();
      return getJSON('data/ean/' + p + '.json').catch(function () { return {}; })
        .then(function (m) { return m[c] ? { code: c, rec: m[c] } : next(); });
    }
    return next();
  });
}
/* Gom TAT CA kho co CUNG ma vach (ke ca ma thung GTIN-14) vao 1 ban ghi -> kho
   dat hon nam o cot #2/#3 cung mot dong, khong bi bo sot nhu khi dung eanLookup
   (ham do thay manh dau tien la dung). Moi kho giu gia re nhat. */
function eanLookupAll(code) {
  return loadShardIndex().then(function (idx) {
    var codes = eanVariants(code);
    function shardOf(c) {
      for (var L = 8; L >= 3; L--) { var p = c.slice(0, L); if (idx.has(p)) return p; }
      return null;
    }
    var need = {};                       // manh -> danh sach ma can tra
    codes.forEach(function (c) {
      var p = shardOf(c); if (p) (need[p] = need[p] || []).push(c);
    });
    var prefixes = Object.keys(need);
    if (!prefixes.length) return null;
    return Promise.all(prefixes.map(function (p) {
      return getJSON('data/ean/' + p + '.json').catch(function () { return {}; })
        .then(function (m) { return { p: p, m: m }; });
    })).then(function (parts) {
      var name = '', byShop = {}, hitCode = null, byName = false, exact = false;
      parts.forEach(function (part) {
        need[part.p].forEach(function (c) {
          var rec = part.m[c];
          if (!rec) return;
          if (!hitCode) hitCode = c;
          if (!name && rec[0]) name = rec[0];
          if (rec[2] === 1) byName = true; else if (rec[1] && rec[1].length) exact = true;
          (rec[1] || []).forEach(function (o) {
            var ex = byShop[o[0]];
            if (!ex || o[1] < ex[1]) byShop[o[0]] = o;
          });
        });
      });
      if (!hitCode) return null;
      var offers = Object.keys(byShop).map(function (k) { return byShop[k]; });
      // nameMatched = gia suy theo ten (build-time), khong phai trung ma vach that
      return { code: hitCode, rec: [name, offers], nameMatched: byName && !exact };
    });
  });
}
function loadCatalog(onProgress) {
  if (DATA.catalog) return Promise.resolve(DATA.catalog);
  if (onProgress) onProgress();
  return getJSON('data/catalog.json').then(function (c) { return (DATA.catalog = c); });
}
/* Deal het akce > 1 ngay -> loai bo (data cu, khong show nua) */
function isExpiredDeal(valid) {
  if (!valid) return false;
  var m = valid.match(/(\d{1,2})\.\s*(\d{1,2})\./g);
  if (!m || !m.length) return false;
  var last = /(\d{1,2})\.\s*(\d{1,2})\./.exec(m[m.length - 1]);
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var end = new Date(today.getFullYear(), +last[2] - 1, +last[1]);
  return (today - end) / 86400000 > 1;
}
function loadRetail() {
  if (DATA.retail !== null && DATA.retail !== undefined) return Promise.resolve(DATA.retail);
  return getJSON('data/retail.json').then(function (d) {
    // Loc bo deal het han >1 ngay ngay khi load; item con >=1 deal thi giu
    var items = (d.items || []).map(function (p) {
      var deals = p[2].filter(function (dd) { return !isExpiredDeal(dd[4]); });
      return deals.length ? [p[0], p[1], deals] : null;
    }).filter(Boolean);
    d.items = items;
    return (DATA.retail = d);
  }).catch(function () { return (DATA.retail = { items: [] }); });
}

/* ---------- bo loc kho (nho localStorage) ---------- */
function offSet(key) {
  try { return new Set(JSON.parse(localStorage.getItem(key) || '[]')); }
  catch (e) { return new Set(); }
}
function filterBar(list, key, attr, collapseAfter) {
  var off = offSet(key);
  function btn(x) {
    var slug = Array.isArray(x) ? x[0] : x, lbl = Array.isArray(x) ? x[1] : x;
    return '<button class="stp' + (off.has(slug) ? ' off' : '') + '" ' + attr +
      '="' + esc(slug) + '">' + esc(lbl) + '</button>';
  }
  // Muc 6: chi hien "collapseAfter" nut dau, con lai an sau nut "…"
  if (collapseAfter && list.length > collapseAfter) {
    return '<div class="sfgroup"><div class="sfrow">' +
      list.slice(0, collapseAfter).map(btn).join('') +
      '<button type="button" class="stp morebtn">…</button>' +
      '<span class="moreshops" style="display:none">' +
      list.slice(collapseAfter).map(btn).join('') + '</span></div></div>';
  }
  var half = Math.floor(list.length / 2);
  return '<div class="sfgroup"><div class="sfrow">' + list.slice(0, half).map(btn).join('') +
    '</div><div class="sfrow">' + list.slice(half).map(btn).join('') + '</div></div>';
}
function wireFilters(key, attr, rerender) {
  document.querySelectorAll('[' + attr + ']').forEach(function (b) {
    b.addEventListener('click', function () {
      var off = offSet(key), k = b.getAttribute(attr);
      if (off.has(k)) off.delete(k); else off.add(k);
      localStorage.setItem(key, JSON.stringify([].concat(Array.from(off))));
      rerender();
    });
  });
  // nut "…" mo rong cac cua hang con lai (khong gan lai neu da gan)
  document.querySelectorAll('.morebtn').forEach(function (b) {
    if (b.dataset.w) return; b.dataset.w = '1';
    b.addEventListener('click', function (e) {
      e.preventDefault();
      var s = b.parentNode.querySelector('.moreshops');
      if (!s) return;
      var open = s.style.display !== 'none';
      s.style.display = open ? 'none' : 'contents';
      b.textContent = open ? '…' : '✕';
    });
  });
}

/* ---------- hien thi ---------- */
function shopBadge(name) {
  var s = stripAccents(name), bg = '#F1EFE8', fg = '#444441';
  var C = [['lidl', '#FFF3C4', '#7A5C00'], ['kaufland', '#D4E8F0', '#2A4F6B'],
    ['billa', '#FFF0C8', '#6B5000'], ['penny', '#E0F0E0', '#2B5C2B'],
    ['tesco', '#DCEBFF', '#0A3D7A'], ['albert', '#DFF5DF', '#1F5C1F'],
    ['globus', '#FAEEDA', '#633806'], ['tamda', '#FFE3CC', '#8A4B00'],
    ['makro', '#DCE9F8', '#123C6B'], ['jip', '#E8E0F8', '#4A2F7A'],
    ['bidfood', '#D8F3E8', '#0B5C43'], ['dathang', '#D8EEF8', '#1A4A6B'],
    ['linsan', '#E6E1FF', '#3A2F7A'], ['bombacena', '#FFE9D6', '#7A4300'],
    ['ptt', '#E3F0FF', '#1A4E8A'], ['kosik', '#E8F0D8', '#3F5C0B'],
    ['hruska', '#FFE7D6', '#7A3E00'], ['coop', '#DDEEFF', '#0A3D7A'],
    ['junior', '#EAE6DC', '#4A4335']];
  for (var i = 0; i < C.length; i++)
    if (s.indexOf(C[i][0]) >= 0) { bg = C[i][1]; fg = C[i][2]; break; }
  return "<span class='sbadge' style='background:" + bg + ";color:" + fg + "'>" +
    esc(name) + '</span>';
}
/* Icon theo tu khoa trong ten (giong ICON_RULES ben Python) */
var ICON_RULES = [
  ['banan', '🍌'], ['jablk', '🍎'], ['pomeranc', '🍊'], ['citron', '🍋'],
  ['meloun', '🍉'], ['jahod', '🍓'], ['hrozn', '🍇'], ['broskv', '🍑'],
  ['merunk', '🍑'], ['tresn', '🍒'], ['visn', '🍒'], ['svestk', '🟣'],
  ['mandarin', '🍊'], ['kiwi', '🥝'], ['ananas', '🍍'], ['mango', '🥭'],
  ['hrusk', '🍐'], ['boruvk', '🔵'], ['malin', '🍓'], ['avokad', '🥑'],
  ['rajc', '🍅'], ['brambor', '🥔'], ['mrkev', '🥕'], ['cibul', '🧅'],
  ['cesnek', '🧄'], ['okurk', '🥒'], ['salat', '🥬'], ['paprik', '🌶️'],
  ['kukuric', '🌽'], ['mleko', '🥛'], ['jogurt', '🥛'], ['smetana', '🥛'],
  ['maslo', '🧈'], ['syr', '🧀'], ['eidam', '🧀'], ['mozzarel', '🧀'],
  ['vejce', '🥚'], ['vajec', '🥚'], ['kurec', '🍗'], ['kure', '🍗'],
  ['veprov', '🥩'], ['hovez', '🥩'], ['sunka', '🥓'], ['slanin', '🥓'],
  ['salam', '🥓'], ['klobas', '🌭'], ['parky', '🌭'], ['ryb', '🐟'],
  ['losos', '🐟'], ['tunak', '🐟'], ['krevet', '🦐'], ['chleb', '🍞'],
  ['rohlik', '🥖'], ['bageta', '🥖'], ['croissant', '🥐'], ['kobliha', '🍩'],
  ['kolac', '🍰'], ['dort', '🍰'], ['cokolad', '🍫'], ['bonbon', '🍬'],
  ['zele', '🍬'], ['lizatk', '🍭'], ['susenk', '🍪'], ['oplatk', '🍪'],
  ['tycink', '🍫'], ['chips', '🍟'], ['krekry', '🍘'], ['zmrzlin', '🍦'],
  ['nanuk', '🍦'], ['pivo', '🍺'], ['lezak', '🍺'], ['radler', '🍺'],
  ['vino', '🍷'], ['kava', '☕'], ['caj', '🍵'], ['dzus', '🧃'],
  ['limonad', '🥤'], ['cola', '🥤'], ['miner', '💧'], ['voda', '💧'],
  ['energ', '⚡'], ['ryze', '🍚'], ['testovin', '🍝'], ['spaget', '🍝'],
  ['mouka', '🌾'], ['cukr', '🍬'], ['olej', '🌻'], ['kecup', '🍅'],
  ['majonez', '🥫'], ['konzerv', '🥫'], ['polevk', '🍲'], ['pizza', '🍕'],
  ['toaletni', '🧻'], ['papir', '🧻'], ['praci', '🧺'], ['gel', '🧴'],
  ['sampon', '🧴'], ['sprchov', '🧴'], ['mydlo', '🧼'], ['zubni', '🦷'],
  ['plenky', '👶'], ['cistic', '🧽'], ['wc', '🚽'], ['osvezovac', '🌸'],
  ['deodorant', '🧴'], ['kremy', '🧴'], ['ubrousk', '🧻'], ['pes', '🐶'],
  ['psy', '🐶'], ['granule', '🐶'], ['kocic', '🐱']
];
function iconFor(name) {
  var n = stripAccents(name);
  for (var i = 0; i < ICON_RULES.length; i++)
    if (n.indexOf(ICON_RULES[i][0]) >= 0) return ICON_RULES[i][1] + ' ';
  return '🛒 ';
}

/* Deal sap het han (hom nay/ngay mai) -> nhan ⏰ (giong deal_expiring ben Python) */
function expShort(valid) {
  var v = stripAccents(valid || '');
  if (v.indexOf('dnes konci') >= 0) return 'hôm nay';
  if (v.indexOf('zitra konci') >= 0) return 'ngày mai';
  var m = (valid || '').match(/(\d{1,2})\.\s*(\d{1,2})\./g);
  if (!m || !m.length) return null;
  var last = /(\d{1,2})\.\s*(\d{1,2})\./.exec(m[m.length - 1]);
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var end = new Date(today.getFullYear(), +last[2] - 1, +last[1]);
  var diff = Math.round((end - today) / 86400000);
  if (diff === 0) return 'hôm nay';
  if (diff === 1) return 'ngày mai';
  return null;   // con han dai -> khong canh bao
}

function unitPrice(amount, price, pack) {
  var m = /(\d+[.,]?\d*)\s*(kg|g|l|ml|ks)\b/i.exec((amount || '').replace(',', '.'));
  if (!m) return '';
  var v = parseFloat(m[1]), u = m[2].toLowerCase();
  if (!v) return '';
  var per = price / Math.max(pack || 1, 1);
  if (u === 'kg') { return (per / v).toFixed(2) + ' Kč/kg'; }
  if (u === 'g') { return (per / v * 1000).toFixed(2) + ' Kč/kg'; }
  if (u === 'l') { return (per / v).toFixed(2) + ' Kč/lít'; }
  if (u === 'ml') { return (per / v * 1000).toFixed(2) + ' Kč/lít'; }
  if (u === 'ks') { return (per / v).toFixed(2) + ' Kč/ks'; }
  return '';
}
/* 1 hang bang: ten + toi da 3 o gia re nhat */
function rowHTML(name, amount, offers) {
  offers = offers.slice().sort(function (a, b) { return a.price - b.price; });
  // Dam bao deal SAP HET akce co mat trong 3 cot hien thi (giong ben Python):
  // cot 1 van la re nhat, deal sap het chen vao cot cuoi neu chua co
  var shown = offers.slice(0, 3);
  if (shown.length === 3 && !shown.some(function (o) { return o.valid && expShort(o.valid); })) {
    var ed = offers.find(function (o) { return o.valid && expShort(o.valid); });
    if (ed) {
      shown = shown.slice(0, 2).concat([ed])
        .sort(function (a, b) { return a.price - b.price; });
    }
  }
  offers = shown;
  var tds = '';
  for (var i = 0; i < 3; i++) {
    var o = offers[i];
    if (!o) { tds += "<td class='a'>—</td>"; continue; }
    var per = o.unit || unitPrice(o.amount || amount, o.price, o.pack);
    var ks = (o.pack > 1) ? "<span class='a'> · " + (o.price / o.pack).toFixed(2) + ' Kč/ks</span>' : '';
    var dph = o.wholesale ? " <span class='a' style='font-weight:normal;font-size:.75em'>vč. DPH</span>" : '';
    var netLine = (o.wholesale && o.net) ? "<span class='a'>" + o.net.toFixed(2) + ' Kč bez DPH</span>' : '';
    var pct = o.pct ? " <span class='pctb'>" + esc(o.pct) + '</span>' : '';
    var d = o.valid ? expShort(o.valid) : null;
    var exp = d ? " <span class='expb'>⏰ " + esc(d) + '</span>' : '';
    tds += "<td" + (i === 0 ? " class='w'" : '') + " data-shop='" + esc(o.slug || '') + "'>" +
      shopBadge(o.shop) + exp + "<span class='mxp'>" + o.price.toFixed(2) + ' Kč' + dph + pct +
      '</span>' + netLine + (per ? "<span class='a'>" + esc(per) + '</span>' : '') + ks + '</td>';
  }
  return '<tr><td>' + iconFor(name) + '<b>' + esc(name) + '</b>' +
    (amount ? " <span class='a'>" + esc(amount) + '</span>' : '') + '</td>' + tds + '</tr>';
}
function tableHTML(rows) {
  return "<div class='mxwrap'><table class='mx'><tr><th style='width:26%'>Mặt hàng</th>" +
    "<th style='background:var(--acc-bg);color:var(--acc-strong)'>✅ Rẻ nhất</th>" +
    '<th>#2</th><th>#3</th></tr>' + rows.join('') + '</table></div>';
}
function tilesHTML() {
  return '<div class="tiles">' + TILES.map(function (t) {
    return '<a class="tile" href="#/cat/' + t[2] + '"><span class="em">' + t[0] + '</span>' + t[1] + '</a>';
  }).join('') + '</div>';
}

/* ---------- gom du lieu -> hang ---------- */
function catalogOffers(item) {
  return { shop: SHOP[item[3]], slug: SHOP_SLUG[item[3]], price: item[1],
           amount: item[2], pack: item[4] || 1, net: item[6] || null, wholesale: true };
}
/* Trang chu chi hien gia BAN LE: bo deal cua kho ban buon (giong WHOLESALE_KEYWORDS) */
var WHOLESALE_KW = ['jip', 'makro', 'tamda', 'bidfood'];
function retailOnly(items) {
  var out = [];
  items.forEach(function (p) {
    var deals = p[2].filter(function (d) {
      var s = stripAccents(d[0]);
      return !WHOLESALE_KW.some(function (k) { return s.indexOf(k) >= 0; });
    });
    if (deals.length) out.push([p[0], p[1], deals]);
  });
  return out;
}
/* % giam sau nhat cua mat hang (de xep thu tu nhu ben Python) */
function bestPct(p) {
  var mx = 0;
  p[2].forEach(function (d) {
    var m = /(\d+)/.exec(d[3] || ''); if (m && +m[1] > mx) mx = +m[1];
  });
  return mx;
}
function hasExpiring(p) {
  return p[2].some(function (d) { return d[4] && expShort(d[4]); });
}
/* Deal "to roi moi": ngay BAT DAU nam trong tuong lai (giong build_home_suggestions) */
function isFresh(p) {
  var today = new Date(); today.setHours(0, 0, 0, 0);
  return p[2].some(function (d) {
    var m = (d[4] || '').match(/(\d{1,2})\.\s*(\d{1,2})\./g);
    if (!m || m.length < 2) return false;
    var f = /(\d{1,2})\.\s*(\d{1,2})\./.exec(m[0]);
    var start = new Date(today.getFullYear(), +f[2] - 1, +f[1]);
    return start > today;
  });
}

/* Xao tron on dinh theo NGAY: trong ngay thu tu khong doi (phan trang on dinh),
   sang ngay moi tu doi. Dung cho trang Akce (giong ban Railway). */
function seededRand(seed) {
  return function () {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function dateSeed() {
  var d = new Date();
  return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
}
/* kupi ghi "TAMDA FOODS", to roi ghi "Tamda Foods" -> cung 1 sieu thi, hien 1 ten */
function canonShop(s) {
  return stripAccents(s).indexOf('tamda') === 0 ? 'Tamda Foods' : s;
}
function retailRows(items, offFilter) {
  return items.map(function (p) {
    var seen = {};
    var offers = p[2].filter(function (d) {
      // tach ca space va dau cham -> "Košík.cz" -> "košík" (khop nut filter "Košík")
      return !offFilter.has(stripAccents(d[0]).split(/[\s.]/)[0]);
    }).map(function (d) {
      var shop = canonShop(d[0]);
      return { shop: shop, slug: stripAccents(shop).split(/[\s.]/)[0], price: d[1],
               unit: d[2], pct: d[3], valid: d[4], wholesale: false };
    }).filter(function (o) {          // bo deal trung y het (cung kho + cung gia)
      var k = o.slug + '|' + o.price;
      if (seen[k]) return false;
      seen[k] = 1; return true;
    });
    return offers.length ? rowHTML(p[0], p[1], offers) : '';
  }).filter(Boolean);
}

/* ---------- cac trang ---------- */
function pageHome(keepOrder) {
  var el = $('#main');
  el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
    "<p class='muted'>Đang tải giá khuyến mãi…</p>";
  loadRetail().then(function (d) {
    var off = offSet('retail_off'), lower = new Set();
    off.forEach(function (x) { lower.add(stripAccents(x)); });
    // Chi shuffle khi vao trang moi (F5 hoac chuyen tab); an filter GIU nguyen thu tu.
    if (!keepOrder || !DATA.homeAll) {
      DATA.homeAll = retailOnly(d.items || []);
      for (var i = DATA.homeAll.length - 1; i > 0; i--) {
        var j = (_rng() * (i + 1)) | 0;
        var t = DATA.homeAll[i]; DATA.homeAll[i] = DATA.homeAll[j]; DATA.homeAll[j] = t;
      }
    }
    var all = DATA.homeAll;
    var pick = all.slice(0, 14);
    var rows = retailRows(pick, lower);
    el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
      "<h2 style='font-size:.95em'>💡 MUA GÌ Ở ĐÂU HÔM NAY</h2>" +
      (rows.length ? tableHTML(rows) : "<p class='muted'>Chưa có dữ liệu giá bán lẻ.</p>") +
      "<p class='muted' style='font-size:.85em'>⏰ = sắp hết akce (hôm nay/ngày mai) · " +
      '(giá/đơn vị) ghi nhỏ · cập nhật ' + esc(d.date || '') + '</p>' +
      freshHTML(all, lower) +
      "<p class='muted' style='margin-top:20px'>So sánh giá siêu thị Séc — gõ tiếng Việt " +
      "có dấu hoặc không dấu đều được.<br>Dữ liệu chỉ mang tính tham khảo · " +
      "<a href='#/gioithieu'>Giới thiệu &amp; miễn trừ trách nhiệm</a></p>";
    wireFilters('retail_off', 'data-rshop', function () { pageHome(true); });
  });
}

function pageGioithieu() {
  var el = $('#main');
  el.innerHTML =
    "<h1 style='font-size:1.4em'>ℹ️ Giới thiệu</h1>" +
    "<p><b>Cena Checker</b> là công cụ phi lợi nhuận giúp cộng đồng người Việt tại Séc " +
    "so sánh giá khuyến mãi giữa các siêu thị bán lẻ và bán buôn. Hỗ trợ tìm kiếm bằng " +
    "tiếng Việt có dấu hoặc không dấu, và quét mã vạch sản phẩm bằng camera điện thoại.</p>" +
    "<h2 style='font-size:1.1em;margin-top:20px'>📋 Nguồn dữ liệu</h2>" +
    "<p><b>Bán lẻ</b> (khuyến mãi tuần, tổng hợp từ kupi.cz): Lidl, Kaufland, Billa, " +
    "Penny Market, Tesco, Albert, Globus, COOP, Hruška, Flop, Ratio, Košík.<br>" +
    "<b>Bán buôn</b> (giá catalog B2B, cào trực tiếp từ site chính thức): Tamda Foods " +
    "(tamdafoods.eu + tamdaexpress.eu), Makro (sortiment.makro.cz), JIP (jip-eshop.cz), " +
    "Bidfood (mujbidfood.cz), dathang.cz, Linsan24h (linsan24h.cz), Bombacena " +
    "(bombacena.eu), PTT Global (pttglobal.eu), JUNIORpapír (juniorpapir.cz).</p>" +
    "<h2 style='font-size:1.1em;margin-top:20px'>⚖️ Miễn trừ trách nhiệm</h2>" +
    "<p>· Dữ liệu giá được tổng hợp <b>tự động</b> từ các nguồn công khai (tờ rơi/catalog " +
    "chính thức của các chuỗi) và <b>chỉ mang tính tham khảo</b> — giá thực tế tại cửa " +
    "hàng có thể khác do khuyến mãi thay đổi, sai sót thu thập, khác biệt giữa các chi " +
    "nhánh, hoặc hết hạn tờ rơi.<br>" +
    "· Trang này <b>không liên kết, không đại diện, không phải đại lý</b> của bất kỳ " +
    "chuỗi siêu thị nào (Kupi.cz, Tamda Foods, Makro, JIP, Bidfood, dathang, Linsan, " +
    "Bombacena, PTT Global, JUNIORpapír, Lidl, Kaufland, Billa, Penny, Tesco, Albert, " +
    "Globus, COOP, Hruška, Flop, Ratio, Košík, hay bất kỳ đơn vị nào).<br>" +
    "· Các tên gọi, thương hiệu, logo (nếu có) thuộc quyền sở hữu của chủ sở hữu tương ứng.<br>" +
    "· Chúng tôi <b>không chịu trách nhiệm</b> cho quyết định mua sắm, tổn thất tài " +
    "chính, hay bất kỳ hậu quả nào phát sinh từ việc sử dụng thông tin trên trang này. " +
    "Người dùng nên tự kiểm tra giá tại cửa hàng trước khi mua.<br>" +
    "· Giá bán buôn (Tamda Express, Makro, JIP, Bidfood, PTT Global, JUNIORpapír, dathang) " +
    "là <b>giá B2B</b> — cần tài khoản kinh doanh của các chuỗi này để mua.<br>" +
    "· Dữ liệu được cập nhật định kỳ (bán lẻ hàng ngày, bán buôn mỗi tuần). " +
    "Ngày cập nhật hiện tại xem ở phần cuối mỗi bảng.</p>" +
    "<h2 style='font-size:1.1em;margin-top:20px'>💬 Liên hệ</h2>" +
    "<p class='muted'>Góp ý / báo lỗi: liên hệ người quản trị trang qua GitHub " +
    "<a href='https://github.com/my-tools26/cena-checker'>my-tools26/cena-checker</a>.</p>" +
    "<p style='margin-top:20px'><a href='#/'>← Về Trang chủ</a></p>";
}

/* Bang "TO ROI MOI - deal sap bat dau" (giong home_suggestions_html ben Python) */
function freshHTML(all, lower) {
  var fresh = all.filter(isFresh).slice(0, 15);
  if (!fresh.length) return '';
  var rows = retailRows(fresh, lower);
  if (!rows.length) return '';
  return "<h2 style='font-size:.95em'>🆕 TỜ RƠI MỚI — deal sắp bắt đầu</h2>" +
    tableHTML(rows) +
    "<p class='muted' style='font-size:.85em'>Khuyến mãi của tờ rơi tuần mới, " +
    'chưa/vừa bắt đầu — lên kế hoạch đi chợ trước.</p>';
}

function pageAkce(keepOrder) {
  var el = $('#main');
  el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
    filterBar(AKCE_WS_FILTERS, 'retail_off', 'data-rshop') +
    "<p class='muted'>Đang tải…</p>";
  loadRetail().then(function (d) {
    var off = offSet('retail_off'), lower = new Set();
    off.forEach(function (x) { lower.add(stripAccents(x)); });
    // Chi shuffle khi vao trang moi; an filter GIU nguyen thu tu.
    if (!keepOrder || !DATA.akceAll) {
      DATA.akceAll = (d.items || []).slice();
      for (var i = DATA.akceAll.length - 1; i > 0; i--) {
        var j = (_rng() * (i + 1)) | 0, t = DATA.akceAll[i]; DATA.akceAll[i] = DATA.akceAll[j]; DATA.akceAll[j] = t;
      }
    }
    var items = DATA.akceAll;
    var rows = retailRows(items.slice(0, 60), lower);
    el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
      filterBar(AKCE_WS_FILTERS, 'retail_off', 'data-rshop') +
      "<h2 style='font-size:.95em'>🔥 AKCE ĐANG DIỄN RA — " + items.length + ' mặt hàng</h2>' +
      tableHTML(rows) +
      "<p class='muted' style='font-size:.85em'>Cập nhật " + esc(d.date || '') +
      " · Dữ liệu chỉ mang tính tham khảo · " +
      "<a href='#/gioithieu'>Giới thiệu &amp; miễn trừ trách nhiệm</a></p>";
    wireFilters('retail_off', 'data-rshop', function () { pageAkce(true); });
  });
}

/* Gom CUNG MOT MAT HANG o nhieu kho -> 1 dong 3 cot (Re nhat / #2 / #3).
   Khoa gom: MA VACH (chac chan nhat), khong co ma thi theo ten + quy cach.
   Moi kho chi giu gia re nhat. Mat hang co nhieu kho duoc xep len dau vi day
   la trang SO SANH gia - de nguyen thu tu thi cot #2/#3 trong tron. */
var bbPage = 1;
function buildBBGroups(cat) {
  if (DATA.bbGroups) return DATA.bbGroups;
  var by = new Map(), i, it, key, g, o, ex, k;
  for (i = 0; i < cat.length; i++) {
    it = cat[i];
    key = (it[5] && it[5].length >= 8) ? 'E' + it[5]
      : 'N' + stripAccents(it[0]).replace(/\s+/g, ' ').trim() +
        '|' + stripAccents(it[2] || '').replace(/\s+/g, '');
    g = by.get(key);
    o = catalogOffers(it);
    if (!g) { by.set(key, { name: it[0], amount: it[2], offers: [o] }); continue; }
    ex = null;
    for (k = 0; k < g.offers.length; k++) if (g.offers[k].slug === o.slug) { ex = g.offers[k]; break; }
    if (!ex) g.offers.push(o);
    else if (o.price < ex.price) { ex.price = o.price; ex.amount = o.amount; ex.pack = o.pack; }
  }
  var arr = [];
  by.forEach(function (v) { arr.push(v); });
  arr.sort(function (a, b) { return b.offers.length - a.offers.length; });  // sort on dinh
  DATA.bbGroups = arr;
  return arr;
}
function pageBanbuon(keepOrder) {
  var el = $('#main');
  el.innerHTML = tilesHTML() + filterBar(WHOLESALE_FILTERS, 'bb_off', 'data-bbcol') +
    "<p class='muted'>Đang tải catalog bán buôn (lần đầu ~2MB, sau đó nhanh)…</p>";
  loadCatalog().then(function (cat) {
    var off = offSet('bb_off');
    var groups = buildBBGroups(cat);
    // Chi shuffle khi vao trang moi/doi filter/doi trang; giu index shuffle tren FULL groups.
    if (!DATA.bbOrder || DATA.bbOrder.length !== groups.length) {
      DATA.bbOrder = groups.map(function (_, i) { return i; });
      for (var si = DATA.bbOrder.length - 1; si > 0; si--) {
        var sj = (_rng() * (si + 1)) | 0;
        var st = DATA.bbOrder[si]; DATA.bbOrder[si] = DATA.bbOrder[sj]; DATA.bbOrder[sj] = st;
      }
    }
    var shuffled = DATA.bbOrder.map(function (i) { return groups[i]; });
    var items = off.size ? shuffled.map(function (g) {         // bo kho bi tat
      var ofs = g.offers.filter(function (o) { return !off.has(o.slug); });
      return ofs.length ? { name: g.name, amount: g.amount, offers: ofs } : null;
    }).filter(Boolean) : shuffled;
    var PER = 30, npages = Math.max(1, Math.ceil(items.length / PER));
    if (bbPage > npages) bbPage = npages;
    var slice = items.slice((bbPage - 1) * PER, bbPage * PER);
    var rows = slice.map(function (g) {
      return rowHTML(g.name, g.amount, g.offers);
    });
    function pager() {
      var out = [], nums = new Set([1, 2, npages - 1, npages, bbPage - 1, bbPage, bbPage + 1]);
      Array.from(nums).filter(function (n) { return n >= 1 && n <= npages; })
        .sort(function (a, b) { return a - b; }).forEach(function (n, i, arr) {
          if (i && n - arr[i - 1] > 1) out.push("<span class='a'>…</span>");
          out.push(n === bbPage ? "<b style='padding:6px 10px'>" + n + '</b>' :
            "<a href='#' data-bbp='" + n + "' style='padding:6px 10px'>" + n + '</a>');
        });
      return "<p style='text-align:center'>" + out.join('') + '</p>';
    }
    el.innerHTML = tilesHTML() + filterBar(WHOLESALE_FILTERS, 'bb_off', 'data-bbcol') +
      pager() + tableHTML(rows) + pager() +
      "<p class='muted' style='font-size:.8em'>📦 " + items.length + ' mặt hàng · trang ' +
      bbPage + '/' + npages + ' · giá đã gồm DPH · cùng mặt hàng ở nhiều kho được ' +
      "gộp 1 dòng, ✅ là kho rẻ nhất · giá bán buôn cần tài khoản B2B · " +
      "<a href='#/gioithieu'>Giới thiệu &amp; miễn trừ trách nhiệm</a></p>";
    wireFilters('bb_off', 'data-bbcol', function () { bbPage = 1; pageBanbuon(true); });
    document.querySelectorAll('[data-bbp]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault(); bbPage = +a.getAttribute('data-bbp');
        pageBanbuon(true); window.scrollTo(0, 0);
      });
    });
  }).catch(function (e) {
    el.innerHTML = "<p>Không tải được dữ liệu: " + esc(e.message) + '</p>';
  });
}

function pageCat(cat, keepOrder) {
  var el = $('#main'), words = CAT_WORDS[cat] || [];
  el.innerHTML = tilesHTML() + "<p class='muted'>Đang tải…</p>";
  loadRetail().then(function (d) {
    var off = offSet('retail_off'), lower = new Set();
    off.forEach(function (x) { lower.add(stripAccents(x)); });
    if (!keepOrder || !DATA.catCache || DATA.catCache.cat !== cat) {
      var items = (d.items || []).filter(function (p) {
        var n = stripAccents(p[0]);
        return words.some(function (w) { return n.indexOf(w) >= 0; });
      });
      for (var i = items.length - 1; i > 0; i--) {
        var j = (_rng() * (i + 1)) | 0, tmp = items[i]; items[i] = items[j]; items[j] = tmp;
      }
      DATA.catCache = { cat: cat, items: items };
    }
    var items = DATA.catCache.items;
    var t = TILES.filter(function (x) { return x[2] === cat; })[0] || ['', cat, cat];
    el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
      "<h2 style='font-size:.95em'>" + t[0] + ' ' + esc(t[1]) + ' — ' + items.length +
      ' mặt hàng khuyến mãi</h2>' +
      (items.length ? tableHTML(retailRows(items.slice(0, 60), lower))
        : "<p class='muted'>Tuần này không có khuyến mãi nhóm này.</p>");
    wireFilters('retail_off', 'data-rshop', function () { pageCat(cat, true); });
  });
}

/* ---------- tim kiem ---------- */
function pageSearch(query) {
  var el = $('#main'), raw = stripAccents(query.trim());
  el.innerHTML = tilesHTML() + "<p class='muted'>Đang tìm…</p>";
  var isEan = /^\d{8,14}$/.test(raw);

  loadDict().then(function () {
    var cs = viTranslate(raw);
    var head = "<h1 style='font-size:1.15em'>Kết quả: " + esc(query) + '</h1>';

    if (isEan) return searchByEan(raw, head, el);
    return searchByText(raw, cs, head, el);
  });
}

function searchByEan(code, head, el) {
  return eanLookupAll(code).then(function (hit) {
    if (!hit) {
      el.innerHTML = tilesHTML() + head +
        "<p>Không tìm thấy mã vạch <b>" + esc(code) + '</b> trong dữ liệu.</p>';
      return;
    }
    var name = hit.rec[0], offers = (hit.rec[1] || []).map(function (o) {
      return { shop: SHOP[o[0]], slug: SHOP_SLUG[o[0]], price: o[1], amount: o[2],
               pack: o[3] || 1, wholesale: true };
    });
    var html = head + "<p class='muted'>📦 Mã vạch: <b>" + esc(name) + '</b></p>';
    if (offers.length) {
      html += "<h2 style='font-size:.95em'>" + (hit.nameMatched
        ? "≈ Cùng tên & dung tích ở các kho" : "✅ Đúng mã vạch quét") + '</h2>' +
        tableHTML([rowHTML(name, offers[0].amount, offers)]) +
        (hit.nameMatched ? "<p class='muted' style='font-size:.8em'>Mã vạch này chỉ " +
          'có ở một nơi; các kho khác ghép theo tên + đúng dung tích.</p>' : '');
    } else {
      html += "<p class='muted'>Nhận diện được tên nhưng chưa có giá kho nào.</p>";
    }
    // Tim gia SIEU THI theo ten (retail.json nho ~120KB).
    // KHONG tai catalog 2MB o day - manh EAN da co du gia kho cua dung ma nay;
    // muon xem hang tuong tu thi bam nut (tai catalog khi that su can).
    var toks = stripAccents(name).split(/\s+/).filter(function (w) { return w.length >= 3; })
      .slice(0, 2).join(' ');
    el.innerHTML = tilesHTML() + html +
      "<p class='muted'>Đang tìm giá siêu thị…</p>";
    return loadRetail().then(function (rd) {
      var ret = searchRetail(rd, toks);
      var base = html +
        (ret.length ? "<h2 style='font-size:.95em'>🏪 Giá siêu thị (khuyến mãi)</h2>" +
          tableHTML(retailRows(ret.slice(0, 15), new Set())) : '');
      el.innerHTML = tilesHTML() + base +
        "<p class='muted' id='simwait'>⏳ Đang tìm cùng loại ở các kho khác…</p>";
      // TU DONG tim cung loai o kho khac: nhieu kho (Bombacena/dathang) khong ghi
      // ma vach, hoac dung ma khac (ban CZ/EU) -> quet ma chi khop 1 kho. Tim
      // theo TEN de van thay ho ban bao nhieu. Catalog duoc cache sau lan dau.
      return loadCatalog().then(function (cat) {
        var sim = searchCatalog(cat, toks).filter(function (x) { return x[0] !== name; });
        // GOP vao CUNG MOT DONG cac kho ban DUNG san pham nay nhung khong ghi ma
        // vach (Bombacena/dathang) -> kho dat hon nam o cot #2/#3.
        // "330 ml" va "0,33 l" la MOT -> quy ve cung don vi truoc khi so sanh
        function normAmt(s) {
          var m = /(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|ks)\b/i.exec(stripAccents(s || ''));
          if (!m) return '';
          var n = parseFloat(m[1].replace(',', '.')), u = m[2].toLowerCase();
          if (u === 'g') { n /= 1000; u = 'kg'; }
          if (u === 'ml') { n /= 1000; u = 'l'; }
          return (Math.round(n * 10000) / 10000) + u;
        }
        // Ma chi co TEN chua co gia (vd tu Luigi's Box) -> offers rong, lay dung
        // tich tu chinh TEN ("...45g") de van ghep duoc dung mat hang o cac kho.
        var myAmt = normAmt((offers[0] && offers[0].amount) || '') || normAmt(name);
        var myName = stripAccents(name);
        var VAR = ['zero', 'light', 'cherry', 'vanilla', 'lemon', 'lime', 'free', 'diet',
          'max', 'sprite', 'fanta', 'pomeranc', 'citron', 'jahoda', 'bez cukru'];
        var keyToks = myName.split(/[^a-z0-9]+/).filter(function (t) {
          return t.length >= 3 && !/^\d+$/.test(t);
        }).slice(0, 3);
        var merged = [], rest = [];
        sim.forEach(function (x) {
          var n = stripAccents(x[0]);
          var sameSize = myAmt && normAmt(x[2]) === myAmt;
          // du thuong hieu (tu dau) la du - ten cac kho viet rat khac nhau
          // ("Coca Cola 0,33L" vs "Coca 330ml Cerveny"); chan nham nho VAR + dung tich
          var allToks = keyToks.length && n.indexOf(keyToks[0]) >= 0;
          // Phai GIONG NHAU ca 2 chieu: quet ban Zero thi khong duoc ghep ban thuong,
          // va nguoc lai.
          var extraVariant = VAR.some(function (wv) {
            return (n.indexOf(wv) >= 0) !== (myName.indexOf(wv) >= 0);
          });
          if (sameSize && allToks && !extraVariant) merged.push(x); else rest.push(x);
        });
        if (merged.length) {
          merged.forEach(function (x) {
            var o = catalogOffers(x);
            var ex = null;
            for (var i2 = 0; i2 < offers.length; i2++) if (offers[i2].slug === o.slug) { ex = offers[i2]; break; }
            if (!ex) offers.push(o); else if (o.price < ex.price) { ex.price = o.price; ex.amount = o.amount; ex.pack = o.pack; }
          });
          html = head + "<p class='muted'>📦 Mã vạch: <b>" + esc(name) + '</b></p>' +
            "<h2 style='font-size:.95em'>✅ Sản phẩm vừa quét — giá các kho</h2>" +
            tableHTML([rowHTML(name, offers[0].amount, offers)]) +
            "<p class='muted' style='font-size:.8em'>Kho không ghi mã vạch được ghép " +
            'theo tên + đúng dung tích.</p>';
          base = html + (ret.length ? "<h2 style='font-size:.95em'>🏪 Giá siêu thị (khuyến mãi)</h2>" +
            tableHTML(retailRows(ret.slice(0, 15), new Set())) : '');
          sim = rest;
        }
        // Uu tien: CUNG dung tich -> chua het han -> re nhat
        var amt = stripAccents((offers[0] && offers[0].amount) || '').replace(/\s+/g, '');
        function sameAmt(x) { return stripAccents(x[2] || '').replace(/\s+/g, '') === amt ? 0 : 1; }
        function expired(x) { return /het han/.test(stripAccents(x[0])) ? 1 : 0; }
        sim.sort(function (a, b) {
          return sameAmt(a) - sameAmt(b) || expired(a) - expired(b) || a[1] - b[1];
        });
        el.innerHTML = tilesHTML() + base + (sim.length
          ? "<h2 style='font-size:.95em'>🏬 Cùng loại ở kho khác — " + sim.length + '</h2>' +
            tableHTML(groupRows(sim.slice(0, 30)))
          : "<p class='muted'>Không có hàng cùng loại ở kho khác.</p>");
      }).catch(function () {
        var w = document.getElementById('simwait');
        if (w) w.textContent = 'Không tải được danh mục kho.';
      });
    });
  });
}

function searchCatalog(cat, q) {
  var terms = q.split(/\s+/).filter(Boolean);
  if (!terms.length) return [];
  var out = [];
  for (var i = 0; i < cat.length && out.length < 400; i++) {
    var n = stripAccents(cat[i][0]);
    var ok = true;
    for (var j = 0; j < terms.length; j++) if (n.indexOf(terms[j]) < 0) { ok = false; break; }
    if (ok) out.push(cat[i]);
  }
  return out;
}
function searchRetail(d, q) {
  var terms = q.split(/\s+/).filter(Boolean);
  return (d.items || []).filter(function (p) {
    var n = stripAccents(p[0]);
    return terms.every(function (t) { return n.indexOf(t) >= 0; });
  });
}
/* gom cac mat hang cung ten -> 1 hang nhieu kho */
function groupRows(items) {
  var by = {};
  items.forEach(function (it) {
    var k = it[0] + '|' + it[2];
    (by[k] = by[k] || { name: it[0], amount: it[2], offers: [] }).offers.push(catalogOffers(it));
  });
  return Object.keys(by).map(function (k) {
    return rowHTML(by[k].name, by[k].amount, by[k].offers);
  });
}

/* Mo rong 1 truy van thanh nhieu tu Sec (OR) theo bang dong nghia */
function expandQueries(raw, cs) {
  var s = SEARCH_SYNONYMS[raw] || SEARCH_SYNONYMS[cs];
  return s ? s.slice() : [cs];
}
/* Gop nhieu mang ket qua, bo trung (theo tham chieu doi tuong goc) */
function uniqConcat(lists) {
  var seen = [], out = [];
  lists.forEach(function (l) {
    l.forEach(function (x) { if (seen.indexOf(x) < 0) { seen.push(x); out.push(x); } });
  });
  return out;
}

function searchByText(raw, cs, head, el) {
  el.innerHTML = tilesHTML() + head +
    "<p class='muted'>Đang tải dữ liệu giá (lần đầu ~2MB, sau đó nhanh)…</p>";
  return Promise.all([loadCatalog(), loadRetail()]).then(function (r) {
    var cat = r[0], retail = r[1];
    var qs = expandQueries(raw, cs);
    var hits = uniqConcat(qs.map(function (q) { return searchCatalog(cat, q); }));
    if (!hits.length && cs !== raw) hits = searchCatalog(cat, raw);
    var ret = uniqConcat(qs.map(function (q) { return searchRetail(retail, q); }));
    if (!ret.length && cs !== raw) ret = searchRetail(retail, raw);
    var html = head;
    if (ret.length) html += "<h2 style='font-size:.95em'>🏪 Giá siêu thị (khuyến mãi) — " +
      ret.length + '</h2>' + tableHTML(retailRows(ret.slice(0, 20), new Set()));
    if (hits.length) html += "<h2 style='font-size:.95em'>📦 Giá bán buôn — " + hits.length +
      ' mặt hàng</h2>' + tableHTML(groupRows(hits.slice(0, 40)));
    if (!ret.length && !hits.length)
      html += '<p>Không tìm thấy gì. Thử từ khác hoặc tên tiếng Séc?</p>';
    el.innerHTML = tilesHTML() + html;
  });
}

/* ---------- quet ma vach bang camera ---------- */
function initScanner() {
  var btn = $('#scanbtn'), box = $('#scanbox'), closeBtn = $('#scanclose');
  var torchBtn = document.getElementById('torchbtn');
  var stream = null, rafId = null, track = null, torchOn = false, zx = null;
  var FORMATS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128'];

  function stop() {
    if (rafId) { clearInterval(rafId); rafId = null; }
    if (track && torchOn) { try { track.applyConstraints({ advanced: [{ torch: false }] }); } catch (e) {} }
    torchOn = false; track = null;
    if (torchBtn) torchBtn.textContent = '🔦 Đèn';
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    box.style.display = 'none';
  }
  function found(code) { stop(); location.hash = '#/q/' + encodeURIComponent(code); }

  /* ZXing: doc duoc ma vach o MOI chieu (co xoay anh), dung cho may khong co
     BarcodeDetector (iPhone/Safari). Tai 1 lan roi cache. */
  function loadZX() {
    if (window.ZXing) return Promise.resolve();
    return new Promise(function (res, rej) {
      var s = document.createElement('script');
      s.src = 'https://unpkg.com/@zxing/library@0.21.3/umd/index.min.js';
      s.onload = res; s.onerror = rej; document.head.appendChild(s);
    });
  }
  function zxInit() {
    if (zx || !window.ZXing) return;
    var Z = window.ZXing, h = new Map();
    h.set(Z.DecodeHintType.POSSIBLE_FORMATS, [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8,
      Z.BarcodeFormat.UPC_A, Z.BarcodeFormat.UPC_E, Z.BarcodeFormat.CODE_128]);
    h.set(Z.DecodeHintType.TRY_HARDER, true);
    zx = new Z.MultiFormatReader(); zx.setHints(h);
  }
  function zxDecode(cv) {
    if (!zx || !window.ZXing) return null;
    var Z = window.ZXing;
    try {
      var src = Z.HTMLCanvasElementLuminanceSource
        ? new Z.HTMLCanvasElementLuminanceSource(cv)
        : new Z.RGBLuminanceSource(cv.getContext('2d')
            .getImageData(0, 0, cv.width, cv.height).data, cv.width, cv.height);
      return zx.decode(new Z.BinaryBitmap(new Z.HybridBinarizer(src))).getText();
    } catch (e) {
      try { zx.reset(); } catch (e2) {}
      return null;
    }
  }

  function start() {
    var v = document.createElement('video');
    v.setAttribute('playsinline', ''); v.muted = true; v.style.width = '100%';
    $('#scanview').innerHTML = ''; $('#scanview').appendChild(v);
    // canvas thuong + canvas xoay 90° (de bat ma vach NAM DOC)
    var ca = document.createElement('canvas'), cxa = ca.getContext('2d', { willReadFrequently: true });
    var cb = document.createElement('canvas'), cxb = cb.getContext('2d', { willReadFrequently: true });
    var det = null;
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment',
      width: { ideal: 1920 }, height: { ideal: 1080 } } })
      .then(function (s) {
        stream = s; v.srcObject = s; v.play();
        track = s.getVideoTracks()[0];
        // luon hien nut den; may nao khong ho tro thi bao khi bam
        if (torchBtn) torchBtn.style.display = 'inline-block';
        if ('BarcodeDetector' in window) { try { det = new BarcodeDetector({ formats: FORMATS }); } catch (e) {} }
        if (!det) loadZX().then(zxInit).catch(function () {
          alert('Không tải được bộ đọc mã vạch. Kiểm tra kết nối mạng rồi thử lại.');
        });
        var busy = false, flip = false;
        // setInterval chu KHONG requestAnimationFrame: rAF dung han khi trang
        // khong ve khung hinh (mot so may/trinh duyet) -> quet mai khong ra.
        rafId = setInterval(function loop() {
          if (busy || v.readyState < 2) return;
          var w = v.videoWidth, h = v.videoHeight;
          if (!w || !h) return;
          busy = true;
          // DUNG DO PHAN GIAI GOC. (Truoc day thu nho ve 720px "cho nhanh" -> vach
          // ma vach co lai con ~2px, ZXing khong doc noi -> quet mai khong ra.)
          ca.width = w; ca.height = h; cxa.drawImage(v, 0, 0);
          cb.width = h; cb.height = w;
          cxb.save(); cxb.translate(h / 2, w / 2); cxb.rotate(Math.PI / 2);
          cxb.drawImage(v, -w / 2, -h / 2); cxb.restore();
          if (det) {
            det.detect(ca).then(function (c) {
              if (c.length) { found(c[0].rawValue); return; }
              return det.detect(cb).then(function (c2) { if (c2.length) found(c2[0].rawValue); });
            }).catch(function () {}).then(function () { busy = false; });
          } else {
            // ZXing nang hon: moi khung chi thu 1 chieu, luan phien ngang/doc
            flip = !flip;
            var r = zxDecode(flip ? ca : cb) || zxDecode(flip ? cb : ca);
            busy = false;
            if (r) found(r);
          }
        }, 120);
      }).catch(function (e) { stop(); alert('Không mở được camera: ' + e.message); });
  }

  if (torchBtn) {
    torchBtn.addEventListener('click', function () {
      if (!track) return;
      torchOn = !torchOn;
      track.applyConstraints({ advanced: [{ torch: torchOn }] }).then(function () {
        torchBtn.textContent = torchOn ? '💡 Tắt đèn' : '🔦 Đèn';
      }).catch(function () {
        torchOn = false;
        torchBtn.textContent = '🔦 Đèn';
        alert('Máy/trình duyệt này không bật được đèn flash khi quét.');
      });
    });
  }
  btn.addEventListener('click', function () { box.style.display = 'block'; start(); });
  closeBtn.addEventListener('click', stop);
  // chi hien nut tren dien thoai
  if (!/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)) btn.style.display = 'none';
}

/* ---------- dieu huong ---------- */
function route() {
  var h = location.hash.replace(/^#/, '') || '/';
  document.querySelectorAll('[data-nav]').forEach(function (a) {
    a.classList.toggle('on', a.getAttribute('data-nav') === h);
  });
  if (h.indexOf('/q/') === 0) {
    var q = decodeURIComponent(h.slice(3));
    $('#q').value = q; pageSearch(q);
  } else if (h.indexOf('/cat/') === 0) { pageCat(h.slice(5)); }
  else if (h === '/akce') pageAkce();
  else if (h === '/banbuon') { bbPage = 1; pageBanbuon(); }
  else if (h === '/gioithieu') pageGioithieu();
  else pageHome();
  window.scrollTo(0, 0);
}

$('#searchform').addEventListener('submit', function (e) {
  e.preventDefault();
  var q = $('#q').value.trim();
  if (q) location.hash = '#/q/' + encodeURIComponent(q);
});
// Bam vao o tim kiem -> boi xanh toan bo (desktop + mobile) -> go moi de tu de len
(function () {
  var q = $('#q');
  function selAll() { try { q.select(); } catch (e) {} }
  q.addEventListener('focus', selAll);
  q.addEventListener('click', selAll);
})();
$('#themebtn').addEventListener('click', function () {
  var dark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('cctheme', dark ? 'dark' : 'light');
  this.textContent = dark ? '☀' : '🌙';
});
if (document.documentElement.classList.contains('dark')) $('#themebtn').textContent = '☀';

window.addEventListener('hashchange', route);
initScanner();
var el = document.getElementById('appver');
if (el) el.textContent = 'v1.5.8.6';

/* ---------- filter panel (focus search -> open) ---------- */
(function () {
  var KEY = 'cc_hidden_shops';
  var panel = document.getElementById('filterwrap');
  var input = document.getElementById('q');
  if (!panel || !input) return;
  function norm(s) { return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  function hidden() { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; } }
  function save(a) { localStorage.setItem(KEY, JSON.stringify(a)); }
  function apply() {
    var h = hidden();
    document.querySelectorAll('td[data-shop]').forEach(function (td) {
      var s = norm(td.getAttribute('data-shop'));
      var hide = h.some(function (k) { return s.indexOf(k) >= 0; });
      if (hide) { if (!td.dataset.orig) td.dataset.orig = td.innerHTML; td.innerHTML = "<span class='a'>ẩn</span>"; }
      else if (td.dataset.orig) { td.innerHTML = td.dataset.orig; td.removeAttribute('data-orig'); }
    });
  }
  function paint() {
    var h = hidden();
    panel.querySelectorAll('.stp').forEach(function (b) {
      b.classList.toggle('off', h.indexOf(b.getAttribute('data-k')) >= 0);
    });
  }
  panel.querySelectorAll('.stp').forEach(function (b) {
    b.addEventListener('click', function () {
      var k = b.getAttribute('data-k'); var h = hidden(); var i = h.indexOf(k);
      if (i >= 0) h.splice(i, 1); else h.push(k);
      save(h); paint(); apply();
    });
  });
  document.getElementById('stall').addEventListener('click', function () { save([]); paint(); apply(); });
  document.getElementById('stnone').addEventListener('click', function () {
    var all = []; panel.querySelectorAll('.stp').forEach(function (b) { all.push(b.getAttribute('data-k')); });
    save(all); paint(); apply();
  });
  function show() { panel.classList.add('open'); }
  function hide() { panel.classList.remove('open'); }
  input.addEventListener('focus', show);
  input.addEventListener('click', show);
  document.addEventListener('click', function (e) {
    if (!panel.contains(e.target) && e.target !== input) hide();
  });
  paint();
  window.addEventListener('load', apply);
  setTimeout(apply, 300);
})();

/* ---------- viewtabs (Tat ca / Sieu thi / Ban buon) ---------- */
(function () {
  var KEY = 'cc_view';
  var tabs = document.getElementById('viewtabs');
  var form = document.getElementById('searchform');
  if (!tabs) return;
  var saved = localStorage.getItem(KEY) || 'all';
  tabs.querySelectorAll('button').forEach(function (b) {
    if (b.getAttribute('data-v') === saved) b.classList.add('on');
    b.addEventListener('click', function () {
      var v = b.getAttribute('data-v');
      localStorage.setItem(KEY, v);
      tabs.querySelectorAll('button').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on');
      window.SCANVIEW = v;
    });
  });
})();

/* Doc meta.json (nho, luon lay ban moi) -> lay dau thoi diem build lam ma chong
   cache cho cac file du lieu lon. Xong moi tai tu dien + ve trang. */
fetch('data/meta.json?t=' + Date.now(), { cache: 'no-store' })
  .then(function (r) { return r.json(); })
  .then(function (m) { DATA.cb = (m && m.built || '').replace(/\D/g, ''); })
  .catch(function () {})
  .then(function () { return loadDict(); })
  .then(route);
