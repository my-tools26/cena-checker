// Cao gia Makro THAT theo tai khoan DANG NHAP cua user (11/10/2026).
// Chay bang Claude in Chrome trong tab https://sortiment.makro.cz (Chrome that, da login):
//   1) javascript_tool: dan TOAN BO file nay, roi `await window.__mkStep(30000)`
//   2) goi lai `await window.__mkStep(35000)` toi khi phase === 'done' (~2-3 lan, moi lan <45s)
//   3) `window.__mkExport()` -> hien nut do "TAI makro_full_prices.json" goc tren trai;
//      CLICK CHUOT THAT vao nut (computer tool) de Chrome cho tai blob ve Downloads.
//      File co the mang ten tam *.tmp trong C:\Users\charl\Downloads -> doc noi dung,
//      kiem tra roi ghi vao cena-checker/makro_full_prices.json.
// pack = bundleSize: Makro ban theo THUNG (vd smetana 10 x 200 g), gia = ca thung (17/10/2026).
// Gia = sellingPriceInfo.netPrice + vatPercent (betty-variants, CAN dang nhap).
// API cong khai chi co shelfPrice (gia ke) -> LECH gia that (vd soda 12,20 vs 11,42).
window.__mk = window.__mk || {phase: 'cats', cats: [], ci: 0, ids: new Set(), idList: null, di: 0, items: {}};
(function () {
  const S = '00006', P = (o) => new URLSearchParams(o).toString();
  const J = (u) => fetch(u, {credentials: 'include'}).then(r => r.ok ? r.json() : null).catch(() => null);
  const search = (cat, rows, page) => {
    const o = {storeId: S, language: 'cs-CZ', country: 'CZ', query: '*', rows, page};
    if (cat) o.filter = 'category:' + cat;
    return J('/searchdiscover/articlesearch/search?' + P(o));
  };
  window.__mkStep = async function (budget) {
    const m = window.__mk, t0 = Date.now();
    if (m.phase === 'cats') {
      const d = await J('/searchdiscover/navigationmenu/menu_structure/country/CZ/locale/cs-CZ/store/' + S);
      const cats = [];
      (function walk(ns, depth) {
        for (const n of ns || []) {
          const rel = n.relativeURL || '';
          const kids = (n.children || []).filter(c => (c.relativeURL || '').startsWith('/category/'));
          if (rel.startsWith('/category/') && (depth >= 3 || !kids.length)) { cats.push(rel.slice(10)); continue; }
          if (n.children) walk(n.children, depth + 1);
        }
      })(d.shop, 0);
      cats.push(''); m.cats = cats; m.phase = 'search';
    }
    while (m.phase === 'search' && Date.now() - t0 < budget) {
      const batch = m.cats.slice(m.ci, m.ci + 6);
      if (!batch.length) { m.idList = [...m.ids]; m.phase = 'detail'; break; }
      await Promise.all(batch.map(async c => {
        const f = await search(c, 1, 1); const tot = (f || {}).amount || 0;
        const pages = Math.min(Math.ceil(tot / 500), 6);
        const rs = await Promise.all([...Array(pages).keys()].map(i => search(c, 500, i + 1)));
        rs.forEach(r => (r && r.resultIds || []).forEach(id => m.ids.add(id)));
      }));
      m.ci += 6;
    }
    while (m.phase === 'detail' && Date.now() - t0 < budget) {
      const chunks = [];
      for (let k = 0; k < 8; k++) { const c = m.idList.slice(m.di + k * 40, m.di + (k + 1) * 40); if (c.length) chunks.push(c); }
      if (!chunks.length) { m.phase = 'done'; break; }
      await Promise.all(chunks.map(async ch => {
        const d = await J('/evaluate.article.v1/betty-variants?storeIds=' + S + '&country=CZ&locale=cs-CZ&ids=' + ch.join(','));
        for (const art of Object.values((d || {}).result || {})) for (const v of Object.values(art.variants || {})) {
          const vid = (v.bettyVariantId || {}).bettyVariantId; const name = (v.description || '').trim();
          if (!vid || !name) continue;
          let ean = '', best = null, pack = 1;
          for (const b of Object.values(v.bundles || {})) {
            for (const g of (b.gtins || [])) {
              const e = String(g && g.number != null ? g.number : g).replace(/\D/g, '');
              if (!ean && [8, 12, 13, 14].includes(e.length)) ean = e.length == 14 ? e.replace(/^0+/, '') : e;
            }
            for (const st of Object.values(b.stores || {})) for (const dm of Object.values(st.possibleDeliveryModes || {}))
              for (const ft of Object.values(dm.possibleFulfillmentTypes || {})) {
                const s = ft.sellingPriceInfo;
                if (s && s.netPrice && s.vatPercent != null && !best) { best = [s.netPrice, s.vatPercent, s.listNetPrice || null]; pack = parseInt(b.bundleSize) || 1; }
              }
          }
          if (best) m.items[vid] = [name, ean, best[0], best[1], best[2], pack];
        }
      }));
      m.di += 320;
    }
    return {phase: m.phase, cats: m.cats.length, ci: m.ci, ids: m.ids.size, di: m.di, items: Object.keys(m.items).length};
  };
  window.__mkExport = function () {
    const RE = /(\d+[.,]?\d*)\s*(kg|g|ml|l|ks)\b/i, seen = new Set(), items = [];
    for (const [name, ean, net, vat, list, pack] of Object.values(window.__mk.items)) {
      const k = name + '|' + ean; if (seen.has(k)) continue; seen.add(k); const m = RE.exec(name);
      const it = {name, price: Math.round(net * (1 + vat) * 100) / 100, price_net: net, vat, list_net: list, ean,
                  amount: m ? m[1] + ' ' + m[2].toLowerCase() : '', unit: ''};
      if (pack > 1) it.pack = pack;   // gia la ca THUNG (bundleSize mon) -> web hien them Kc/ks
      items.push(it);
    }
    const blob = new Blob([JSON.stringify({date: new Date().toISOString().slice(0, 10), shop: 'makro_full', store: '00006',
      source: 'tai khoan Makro dang nhap (Claude in Chrome)', vat_note: 'price = s DPH theo vatPercent that; price_net = gia that bez DPH', items})],
      {type: 'application/json'});
    let a = document.getElementById('__mkdl');
    if (!a) { a = document.createElement('a'); a.id = '__mkdl'; a.textContent = '⬇ TẢI makro_full_prices.json';
      a.style.cssText = 'position:fixed;top:120px;left:40px;z-index:999999;background:#e00;color:#fff;padding:18px 28px;font:bold 20px sans-serif;border-radius:8px';
      document.body.appendChild(a); }
    a.href = URL.createObjectURL(blob); a.download = 'makro_full_prices.json';
    return {items: items.length};
  };
})();
