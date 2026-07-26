/* Cena Checker - ban WEB TINH (GitHub Pages).
   Toan bo chay trong trinh duyet: doc du lieu tu docs/data/*.json.
   - Quet ma vach: chi tai 1 manh EAN nho (~20KB) -> rat nhanh
   - Tim theo ten: tai catalog (1.9MB nen) mot lan roi cache
*/
'use strict';

var SHOP = ['Tamda Foods', 'Tamda Foods', 'Makro', 'Bidfood', 'dathang.cz',
            'Linsan24h', 'Bombacena', 'PTT Global', 'JIP'];
var SHOP_SLUG = ['tamda', 'tamda', 'makro', 'bidfood', 'dathang', 'linsan',
                 'bombacena', 'ptt', 'jip'];
var WHOLESALE_FILTERS = [['tamda', '🅣 Tamda'], ['makro', 'Ⓜ Makro'],
  ['jip', '🄹 JIP'], ['bidfood', '🅑 Bidfood'], ['dathang', '🅳 dathang'],
  ['linsan', '🅻 Linsan'], ['bombacena', '🅱 Bombacena'], ['ptt', '🅟 PTT Global']];
/* Loc ban buon hien tren trang Akce (co JIP vi JIP co deal akce tu kupi) */
var AKCE_WS_FILTERS = [['makro', 'Ⓜ Makro'], ['jip', '🄹 JIP'], ['tamda', '🅣 Tamda'],
  ['bidfood', '🅑 Bidfood'], ['dathang', '🅳 dathang'], ['linsan', '🅻 Linsan'],
  ['bombacena', '🅱 Bombacena'], ['ptt', '🅟 PTT Global']];
var RETAIL_FILTERS = ['Lidl', 'Kaufland', 'Billa', 'Penny', 'Tesco', 'Albert',
  'Globus', 'COOP', 'Hruška', 'Flop', 'Ratio', 'Košík'];
/* So nut ban le hien san; con lai an sau nut "…" (muc 6) */
var RETAIL_SHOWN = 7;
/* Dong nghia tim kiem: 1 tu Viet -> nhieu tu Sec (OR). VD banh mi -> rohlik + chleb */
var SEARCH_SYNONYMS = {
  'banh mi': ['rohlik', 'chleb'], 'banh my': ['rohlik', 'chleb'],
  'rohlik': ['rohlik', 'chleb']
};
var TILES = [['🍎', 'Rau quả', 'ovoce'], ['🥩', 'Thịt cá', 'maso'],
  ['🥛', 'Sữa trứng', 'mleko'], ['🍞', 'Bánh mì', 'pecivo'],
  ['🍫', 'Bánh kẹo', 'sladkosti'], ['🍺', 'Bia', 'pivo'],
  ['🥤', 'Đồ uống', 'napoje'], ['☕', 'Cà phê & trà', 'kava'],
  ['🧴', 'Drogerie', 'drogerie'], ['🐶', 'Thú cưng', 'mazlicci']];
var CAT_WORDS = {
  ovoce: ['ovoce', 'zelenina', 'jablk', 'banan', 'rajcat', 'brambor', 'cibul', 'mrkev'],
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
function stripAccents(s) {
  return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
  });
}
function getJSON(url) {
  return fetch(url).then(function (r) {
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
  return getJSON('data/ean/_index.json').then(function (a) {
    return (DATA.shards = new Set(a));
  }).catch(function () { return (DATA.shards = new Set()); });
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
function loadCatalog(onProgress) {
  if (DATA.catalog) return Promise.resolve(DATA.catalog);
  if (onProgress) onProgress();
  return getJSON('data/catalog.json').then(function (c) { return (DATA.catalog = c); });
}
function loadRetail() {
  if (DATA.retail !== null && DATA.retail !== undefined) return Promise.resolve(DATA.retail);
  return getJSON('data/retail.json').then(function (d) { return (DATA.retail = d); })
    .catch(function () { return (DATA.retail = { items: [] }); });
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
  var C = [['lidl', '#FFF3C4', '#7A5C00'], ['kaufland', '#FFDDDD', '#8A1F1F'],
    ['billa', '#FFE0E0', '#8A1F1F'], ['penny', '#FFE3E3', '#8A1F1F'],
    ['tesco', '#DCEBFF', '#0A3D7A'], ['albert', '#DFF5DF', '#1F5C1F'],
    ['globus', '#FAEEDA', '#633806'], ['tamda', '#FFE3CC', '#8A4B00'],
    ['makro', '#DCE9F8', '#123C6B'], ['jip', '#FFE0E0', '#8A1F1F'],
    ['bidfood', '#D8F3E8', '#0B5C43'], ['dathang', '#FFE1E7', '#8A1F3F'],
    ['linsan', '#E6E1FF', '#3A2F7A'], ['bombacena', '#FFE9D6', '#7A4300'],
    ['ptt', '#E3F0FF', '#1A4E8A'], ['kosik', '#E8F0D8', '#3F5C0B'],
    ['hruska', '#FFE7D6', '#7A3E00'], ['coop', '#DDEEFF', '#0A3D7A']];
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
    var dph = o.wholesale ? " <span class='a' style='font-weight:normal;font-size:.75em'>s DPH</span>" : '';
    var pct = o.pct ? " <span class='pctb'>" + esc(o.pct) + '</span>' : '';
    var d = o.valid ? expShort(o.valid) : null;
    var exp = d ? " <span class='expb'>⏰ " + esc(d) + '</span>' : '';
    tds += "<td" + (i === 0 ? " class='w'" : '') + " data-shop='" + esc(o.slug || '') + "'>" +
      shopBadge(o.shop) + exp + "<span class='mxp'>" + o.price.toFixed(2) + ' Kč' + dph + pct +
      '</span>' + (per ? "<span class='a'>" + esc(per) + '</span>' : '') + ks + '</td>';
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
           amount: item[2], pack: item[4] || 1, wholesale: true };
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

function retailRows(items, offFilter) {
  return items.map(function (p) {
    var offers = p[2].filter(function (d) {
      return !offFilter.has(stripAccents(d[0]).split(' ')[0]);
    }).map(function (d) {
      return { shop: d[0], slug: stripAccents(d[0]).split(' ')[0], price: d[1],
               unit: d[2], pct: d[3], valid: d[4], wholesale: false };
    });
    return offers.length ? rowHTML(p[0], p[1], offers) : '';
  }).filter(Boolean);
}

/* ---------- cac trang ---------- */
function pageHome() {
  var el = $('#main');
  el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
    "<p class='muted'>Đang tải giá khuyến mãi…</p>";
  loadRetail().then(function (d) {
    var off = offSet('retail_off'), lower = new Set();
    off.forEach(function (x) { lower.add(stripAccents(x)); });
    // Giong Railway: CHI gia ban le, uu tien 8 hang sap het akce + BOC NGAU NHIEN
    // du 14 (moi F5 doi mat hang -> khong lap loai). Sap xep theo % giam sau nhat.
    var all = retailOnly(d.items || []);
    var exp = all.filter(hasExpiring).slice(0, 8);
    var rest = all.filter(function (p) { return exp.indexOf(p) < 0; });
    // shuffle Fisher-Yates
    for (var i = rest.length - 1; i > 0; i--) {
      var j = (Math.random() * (i + 1)) | 0;
      var t = rest[i]; rest[i] = rest[j]; rest[j] = t;
    }
    var pick = exp.concat(rest.slice(0, Math.max(0, 14 - exp.length)));
    pick.sort(function (a, b) { return bestPct(b) - bestPct(a); });
    var rows = retailRows(pick, lower);
    el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
      "<h2 style='font-size:.95em'>💡 MUA GÌ Ở ĐÂU HÔM NAY</h2>" +
      (rows.length ? tableHTML(rows) : "<p class='muted'>Chưa có dữ liệu giá bán lẻ.</p>") +
      "<p class='muted' style='font-size:.85em'>⏰ = sắp hết akce (hôm nay/ngày mai) · " +
      '(giá/đơn vị) ghi nhỏ · cập nhật ' + esc(d.date || '') + '</p>' +
      freshHTML(all, lower) +
      "<p class='muted' style='margin-top:20px'>So sánh giá siêu thị Séc — gõ tiếng Việt " +
      'có dấu hoặc không dấu đều được.<br>Nguồn: kupi.cz, tamdafoods.eu, makro.cz, ' +
      'mujbidfood.cz · dữ liệu chỉ mang tính tham khảo.</p>';
    wireFilters('retail_off', 'data-rshop', pageHome);
  });
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

function pageAkce() {
  var el = $('#main');
  el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
    filterBar(AKCE_WS_FILTERS, 'retail_off', 'data-rshop') +
    "<p class='muted'>Đang tải…</p>";
  loadRetail().then(function (d) {
    var off = offSet('retail_off'), lower = new Set();
    off.forEach(function (x) { lower.add(stripAccents(x)); });
    // Akce: ban le + ban buon GOP CHUNG (giong Railway), xep theo % giam sau nhat
    var items = (d.items || []).slice();
    items.sort(function (a, b) { return bestPct(b) - bestPct(a); });
    var rows = retailRows(items.slice(0, 60), lower);
    el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
      filterBar(AKCE_WS_FILTERS, 'retail_off', 'data-rshop') +
      "<h2 style='font-size:.95em'>🔥 AKCE ĐANG DIỄN RA — " + items.length + ' mặt hàng</h2>' +
      tableHTML(rows) +
      "<p class='muted' style='font-size:.85em'>Cập nhật " + esc(d.date || '') + '</p>';
    wireFilters('retail_off', 'data-rshop', pageAkce);
  });
}

var bbPage = 1;
function pageBanbuon() {
  var el = $('#main');
  el.innerHTML = tilesHTML() + filterBar(WHOLESALE_FILTERS, 'bb_off', 'data-bbcol') +
    "<p class='muted'>Đang tải catalog bán buôn (lần đầu ~2MB, sau đó nhanh)…</p>";
  loadCatalog().then(function (cat) {
    var off = offSet('bb_off');
    var items = cat.filter(function (it) { return !off.has(SHOP_SLUG[it[3]]); });
    var PER = 30, npages = Math.max(1, Math.ceil(items.length / PER));
    if (bbPage > npages) bbPage = npages;
    var slice = items.slice((bbPage - 1) * PER, bbPage * PER);
    var rows = slice.map(function (it) {
      return rowHTML(it[0], it[2], [catalogOffers(it)]);
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
      bbPage + '/' + npages + ' · giá đã gồm DPH</p>';
    wireFilters('bb_off', 'data-bbcol', function () { bbPage = 1; pageBanbuon(); });
    document.querySelectorAll('[data-bbp]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault(); bbPage = +a.getAttribute('data-bbp');
        pageBanbuon(); window.scrollTo(0, 0);
      });
    });
  }).catch(function (e) {
    el.innerHTML = "<p>Không tải được dữ liệu: " + esc(e.message) + '</p>';
  });
}

function pageCat(cat) {
  var el = $('#main'), words = CAT_WORDS[cat] || [];
  el.innerHTML = tilesHTML() + "<p class='muted'>Đang tải…</p>";
  loadRetail().then(function (d) {
    var off = offSet('retail_off'), lower = new Set();
    off.forEach(function (x) { lower.add(stripAccents(x)); });
    var items = (d.items || []).filter(function (p) {
      var n = stripAccents(p[0]);
      return words.some(function (w) { return n.indexOf(w) >= 0; });
    });
    var t = TILES.filter(function (x) { return x[2] === cat; })[0] || ['', cat, cat];
    el.innerHTML = tilesHTML() + filterBar(RETAIL_FILTERS, 'retail_off', 'data-rshop', RETAIL_SHOWN) +
      "<h2 style='font-size:.95em'>" + t[0] + ' ' + esc(t[1]) + ' — ' + items.length +
      ' mặt hàng khuyến mãi</h2>' +
      (items.length ? tableHTML(retailRows(items.slice(0, 60), lower))
        : "<p class='muted'>Tuần này không có khuyến mãi nhóm này.</p>");
    wireFilters('retail_off', 'data-rshop', function () { pageCat(cat); });
  });
}

/* ---------- tim kiem ---------- */
function pageSearch(query) {
  var el = $('#main'), raw = stripAccents(query.trim());
  el.innerHTML = tilesHTML() + "<p class='muted'>Đang tìm…</p>";
  var isEan = /^\d{8,14}$/.test(raw);

  loadDict().then(function () {
    var cs = viTranslate(raw);
    var head = "<h1 style='font-size:1.15em'>Kết quả: " + esc(query) + '</h1>' +
      (cs !== raw ? "<p class='muted'>(tự dịch sang tiếng Séc: <b>" + esc(cs) + '</b>)</p>' : '');

    if (isEan) return searchByEan(raw, head, el);
    return searchByText(raw, cs, head, el);
  });
}

function searchByEan(code, head, el) {
  return eanLookup(code).then(function (hit) {
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
      html += "<h2 style='font-size:.95em'>✅ Đúng mã vạch quét</h2>" +
        tableHTML([rowHTML(name, offers[0].amount, offers)]);
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
      el.innerHTML = tilesHTML() + html +
        (ret.length ? "<h2 style='font-size:.95em'>🏪 Giá siêu thị (khuyến mãi)</h2>" +
          tableHTML(retailRows(ret.slice(0, 15), new Set())) : '') +
        "<p style='margin-top:14px'><button id='simbtn' class='stp' " +
        "style='padding:8px 16px;font-size:.9em'>🔍 Tìm sản phẩm tương tự ở các kho</button></p>";
      var b = document.getElementById('simbtn');
      if (b) b.addEventListener('click', function () {
        b.textContent = 'Đang tải…';
        loadCatalog().then(function (cat) {
          var sim = searchCatalog(cat, toks).filter(function (x) { return x[0] !== name; });
          b.parentNode.outerHTML = sim.length
            ? "<h2 style='font-size:.95em'>🔍 Sản phẩm tương tự — " + sim.length + '</h2>' +
              tableHTML(groupRows(sim.slice(0, 30)))
            : "<p class='muted'>Không có hàng tương tự.</p>";
        });
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
  var scanner = null, stream = null, rafId = null;
  var FORMATS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128'];
  function stop() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    if (scanner) { scanner.stop().catch(function () {}); scanner = null; }
    box.style.display = 'none';
  }
  function found(code) { stop(); location.hash = '#/q/' + encodeURIComponent(code); }
  function startNative() {
    var det = new BarcodeDetector({ formats: FORMATS });
    var v = document.createElement('video');
    v.setAttribute('playsinline', ''); v.style.width = '100%';
    $('#scanview').innerHTML = ''; $('#scanview').appendChild(v);
    var cvs = document.createElement('canvas'), cx = cvs.getContext('2d');
    // Xoay khung hinh 90° -> doc duoc ma vach NAM DOC ma khong phai quay may (muc 4)
    function detectRotated() {
      var w = v.videoWidth, h = v.videoHeight;
      if (!w || !h) return Promise.resolve([]);
      cvs.width = h; cvs.height = w;
      cx.save(); cx.translate(h / 2, w / 2); cx.rotate(Math.PI / 2);
      cx.drawImage(v, -w / 2, -h / 2); cx.restore();
      return det.detect(cvs).catch(function () { return []; });
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment',
      width: { ideal: 1920 }, height: { ideal: 1080 } } })
      .then(function (s) {
        stream = s; v.srcObject = s; v.play();
        var busy = false;
        (function loop() {
          rafId = requestAnimationFrame(loop);
          if (busy || v.readyState < 2) return;
          busy = true;
          det.detect(v).then(function (codes) {
            if (codes.length) { found(codes[0].rawValue); return; }
            // chieu ngang khong thay -> thu chieu doc
            return detectRotated().then(function (c2) {
              if (c2.length) found(c2[0].rawValue);
            });
          }).catch(function () {}).then(function () { busy = false; });
        })();
      }).catch(function (e) { stop(); alert('Không mở được camera: ' + e.message); });
  }
  function startLib() {
    // khung vuong + cho phep lat -> de bat ma vach o nhieu chieu hon
    scanner = new Html5Qrcode('scanview');
    scanner.start({ facingMode: 'environment' },
      { fps: 15, qrbox: { width: 250, height: 250 }, disableFlip: false },
      function (c) { found(c); }, function () {})
      .catch(function (e) { stop(); alert('Không mở được camera: ' + e); });
  }
  btn.addEventListener('click', function () {
    box.style.display = 'block';
    function loadLib() {
      if (window.Html5Qrcode) { startLib(); return; }
      var s = document.createElement('script');
      s.src = 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
      s.onload = startLib; document.head.appendChild(s);
    }
    if ('BarcodeDetector' in window) {
      BarcodeDetector.getSupportedFormats().then(function (fs) {
        if (fs.indexOf('ean_13') >= 0) startNative(); else loadLib();
      }).catch(loadLib);
    } else loadLib();
  });
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
  else pageHome();
  window.scrollTo(0, 0);
}

$('#searchform').addEventListener('submit', function (e) {
  e.preventDefault();
  var q = $('#q').value.trim();
  if (q) location.hash = '#/q/' + encodeURIComponent(q);
});
$('#themebtn').addEventListener('click', function () {
  var dark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('cctheme', dark ? 'dark' : 'light');
  this.textContent = dark ? '☀' : '🌙';
});
if (document.documentElement.classList.contains('dark')) $('#themebtn').textContent = '☀';

window.addEventListener('hashchange', route);
initScanner();
var el = document.getElementById('appver');
if (el) el.textContent = 'v0.4';

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

loadDict().then(route);
