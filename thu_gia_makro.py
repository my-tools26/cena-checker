# -*- coding: utf-8 -*-
"""Thu thap gia + ten + EAN toan bo sortiment.makro.cz (API cong khai, khong can dang nhap).

Chay:  python thu_gia_makro.py
Ket qua -> makro_full_prices.json  (gia THUONG cua Makro, khong chi khuyen mai).

Luu y:
- API tra gia NET (bez DPH, xem price-config: primaryPriceType=net).
  Gia s DPH tinh theo co "food": 12% thuc pham, 21% con lai.
- Phan trang search bi chan o ~10k ket qua -> phai quet theo danh muc
  (filter=category:<duong-dan>), danh muc nao qua lon thi xuong cap con.

TOI UU (28/09/2026, khong doi hanh vi/gia tri):
- Da kiem chung API tim kiem KHONG ho tro sort theo ngay tao -> khong the bo
  qua trang cu mot cach an toan cho buoc THU THAP GIA (van phai quet HET moi
  danh muc moi lan, de gia luon dung cho TAT CA mat hang, khong chi hang moi).
- NHUNG buoc lay TEN + EAN (goi API betty-variants theo lo 40 id) la phan
  NANG NHAT (hang tram request) va KHONG doi theo thoi gian cho 1 variantId
  co san -> CACHE ten/EAN vao makro_variant_cache.json, lan sau chi goi API
  cho variantId MOI (chua co trong cache), tai su dung ten/EAN da biet cho
  variantId cu -> giam manh so request ma khong lam gia cu di.
- --full: xoa cache, tra lai TEN/EAN cho TAT CA (nen ~1-2 thang/lan phong khi
  Makro doi ten/EAN 1 san pham da co).
"""
from safeio import atomic_open  # ghi file an toan (tmp roi doi ten)
import json
import os
import re
import time

import requests

VARIANT_CACHE = None  # nap 1 lan trong main()

BASE = "https://sortiment.makro.cz"
STORE = "00006"  # makro Praha - Stodulky
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "makro_full_prices.json")
CACHE_FILE = os.path.join(HERE, "makro_variant_cache.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0",
     "Accept": "application/json", "CallTreeId": "cena-checker"}
RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)
MAX_SEARCH = 3000  # search co filter danh muc bi chan o 3000 ket qua (do duoc 10.7.2026)


def load_variant_cache():
    """variantId -> {name, ean, food}. Ton tai qua nhieu lan chay -> khoi phai
    goi lai API ten/EAN cho variantId da biet."""
    try:
        return json.load(open(CACHE_FILE, encoding="utf-8"))
    except Exception:
        return {}


def save_variant_cache(cache):
    json.dump(cache, atomic_open(CACHE_FILE), ensure_ascii=False)


def get(url, params, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=H, timeout=45)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 400:
                return None
        except Exception as e:
            print(f"  loi {e}, cho 10s")
        time.sleep(10)
    return None


def search(cat_path, rows, page):
    p = {"storeId": STORE, "language": "cs-CZ", "country": "CZ",
         "query": "*", "rows": rows, "page": page}
    if cat_path:
        p["filter"] = f"category:{cat_path}"
    return get(f"{BASE}/searchdiscover/articlesearch/search", p)


def cat_tree():
    """Danh sach danh muc de quet. Search co filter danh muc bi chan o 3000 ket qua,
    nen phai dung danh muc cap 3 (moi cai nho); cap 2 chi khi khong co cap con."""
    d = get(f"{BASE}/searchdiscover/navigationmenu/menu_structure/"
            f"country/CZ/locale/cs-CZ/store/{STORE}", {})
    cats = []

    def walk(nodes, depth):
        for n in nodes:
            rel = n.get("relativeURL", "")
            kids = [c for c in (n.get("children") or [])
                    if c.get("relativeURL", "").startswith("/category/")]
            if rel.startswith("/category/"):
                if depth >= 3 or not kids:
                    cats.append(rel[len("/category/"):])
                    continue
            if n.get("children"):
                walk(n["children"], depth + 1)

    walk(d["shop"], 0)
    return cats


def get_subcats(cat_path):
    """Lay danh muc con cua cat_path tu menu API."""
    d = get(f"{BASE}/searchdiscover/navigationmenu/menu_structure/"
            f"country/CZ/locale/cs-CZ/store/{STORE}", {})
    if not d:
        return []
    subs = []

    def walk(nodes, parent_match):
        for n in nodes:
            rel = n.get("relativeURL", "")
            is_match = rel == f"/category/{cat_path}"
            kids = n.get("children") or []
            if parent_match and rel.startswith("/category/"):
                subs.append(rel[len("/category/"):])
            elif is_match and kids:
                walk(kids, True)
            elif kids:
                walk(kids, False)

    walk(d.get("shop", []), False)
    return subs


def collect_category(cat_path, prices, depth=0):
    """Quet 1 danh muc; neu >MAX_SEARCH ket qua thi tu dong chia nho theo cap con."""
    d = search(cat_path, 1, 1)
    total = (d or {}).get("amount", 0)
    if not total:
        return
    if total > MAX_SEARCH and depth < 3:
        subs = get_subcats(cat_path)
        if subs:
            print(f"  ! {cat_path}: {total} > {MAX_SEARCH}, chia thanh {len(subs)} danh muc con")
            for sc in subs:
                collect_category(sc, prices, depth + 1)
            return
        print(f"  ! {cat_path}: {total} > {MAX_SEARCH}, khong co danh muc con - lay {MAX_SEARCH} dau")
    pages = min((total + 499) // 500, MAX_SEARCH // 500)
    got = 0
    # so trang biet truoc -> tai SONG SONG (fastfetch), gop theo dung thu tu
    from fastfetch import map_parallel
    for d in map_parallel(lambda pg: search(cat_path, 500, pg), range(1, pages + 1)):
        if not d:
            break
        for rid in d.get("resultIds", []):
            info = d["results"].get(rid, {})
            if rid not in prices and info.get("price"):
                prices[rid] = info["price"]
                got += 1
    print(f"[{cat_path}] {total} sp, +{got} moi, tong {len(prices)}")


def main():
    import sys
    full = "--full" in sys.argv
    cats = cat_tree()
    print(f"{len(cats)} danh muc cap 2")
    prices = {}  # variantId -> gia net (LUON quet HET moi lan, de gia moi cho TAT CA)
    for c in cats:
        collect_category(c, prices)
    # quet them query=* khong filter de vot 9000 sp dau (phong khi menu thieu)
    collect_category("", prices)
    ids = list(prices)
    print(f"Tong {len(ids)} variant")

    # TOI UU: ten/EAN cua variantId DA BIET tu lan truoc khong doi -> tai su
    # dung tu cache, chi goi API cho variantId MOI -> giam manh so request.
    cache = {} if full else load_variant_cache()
    new_ids = [vid for vid in ids if vid not in cache]
    print(f"  {len(ids) - len(new_ids)} variant da co ten/EAN trong cache, "
          f"chi tra {len(new_ids)} variant moi...")

    from fastfetch import map_parallel
    chunks = [new_ids[i:i + 40] for i in range(0, len(new_ids), 40)]
    details = map_parallel(lambda ch: get(
        f"{BASE}/evaluate.article.v1/betty-variants",
        {"storeIds": STORE, "country": "CZ", "locale": "cs-CZ", "ids": ",".join(ch)}), chunks)
    for i, d in zip(range(0, len(new_ids), 40), details):
        if not d:
            continue
        for art in d.get("result", {}).values():
            food = art.get("food", True)
            for v in art.get("variants", {}).values():
                vid = v.get("bettyVariantId", {}).get("bettyVariantId", "")
                name = (v.get("description") or "").strip()
                if not name or vid not in prices:
                    continue
                ean = ""
                for b in v.get("bundles", {}).values():
                    for g in (b.get("gtins") or []):
                        e = re.sub(r"\D", "", str(g.get("number", g) if isinstance(g, dict) else g))
                        if len(e) in (8, 12, 13, 14):
                            ean = e.lstrip("0") if len(e) == 14 else e
                            break
                    if not ean:
                        for g in (b.get("eanNumber") or []):
                            e = re.sub(r"\D", "", str(g.get("number", "") if isinstance(g, dict) else g))
                            if len(e) in (8, 12, 13):
                                ean = e
                                break
                    if ean:
                        break
                cache[vid] = {"name": name, "ean": ean, "food": food}
        if (i // 40) % 25 == 0:
            print(f"  chi tiet moi {i}/{len(new_ids)}")

    save_variant_cache(cache)

    # GIA THAT (11/10/2026): API cong khai chi tra "shelfPrice" (gia ke) — KHAC gia
    # khach dang nhap thay tren Makro (vd soda Dr.Oetker: ke 12,20 / thuc 11,42
    # bez DPH; thue 21% chu khong phai 12%). Lay netPrice + vatPercent that bang
    # phien DANG NHAP (Chrome rieng, giu phien); khong lay duoc -> dung gia ke cu.
    real = login_prices(ids)

    items = []
    seen_names = set()
    for vid in ids:
        info = cache.get(vid)
        net = prices.get(vid)
        if not info or not net:
            continue
        name, ean, food = info["name"], info["ean"], info.get("food", True)
        vat = 1.12 if food else 1.21
        if vid in real:
            net, vat = real[vid][0], 1 + real[vid][1]
        m = RE_AMOUNT.search(name)
        key = name + "|" + ean
        if key in seen_names:
            continue
        seen_names.add(key)
        items.append({"name": name, "price": round(net * vat, 2),
                      "price_net": net, "ean": ean,
                      "amount": f"{m.group(1)} {m.group(2).lower()}" if m else "",
                      "unit": ""})

    with atomic_open(OUT) as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "makro_full",
                   "store": STORE,
                   "vat_note": "price = s DPH; net + DPH that tu phien dang nhap (neu co)",
                   "login_prices": len(real), "items": items}, f, ensure_ascii=False)
    print(f"XONG makro: {len(items)} mat hang (gia that dang nhap: {len(real)}) "
          f"-> makro_full_prices.json")


PRICE_JS = r"""
const ids = arguments[0], store = arguments[1], done = arguments[arguments.length - 1];
async function one(chunk) {
  try {
    const u = '/evaluate.article.v1/betty-variants?storeIds=' + store +
              '&country=CZ&locale=cs-CZ&ids=' + chunk.join(',');
    const d = await fetch(u, {credentials: 'include'}).then(r => r.json());
    const out = {};
    for (const art of Object.values(d.result || {}))
      for (const v of Object.values(art.variants || {})) {
        const vid = (v.bettyVariantId || {}).bettyVariantId;
        let best = null;
        for (const b of Object.values(v.bundles || {}))
          for (const st of Object.values((b.stores || {})))
            for (const dm of Object.values(st.possibleDeliveryModes || {}))
              for (const ft of Object.values(dm.possibleFulfillmentTypes || {})) {
                const s = ft.sellingPriceInfo;
                if (s && s.netPrice && s.vatPercent != null && !best) best = [s.netPrice, s.vatPercent];
              }
        if (vid && best) out[vid] = best;
      }
    return out;
  } catch (e) { return {}; }
}
const chunks = []; for (let i = 0; i < ids.length; i += 40) chunks.push(ids.slice(i, i + 40));
Promise.all(chunks.map(one)).then(rs => done(Object.assign({}, ...rs)));
"""


def login_prices(ids, wait_login=300):
    """{variantId: [netPrice, vatPercent]} lay trong phien DANG NHAP Makro.
    Chrome rieng .chrome-cookie-profiles/makro giu phien (+ luu mat khau) -> lan
    sau tu chay. Chua dang nhap -> cho toi da 5 phut (KHONG tu go mat khau)."""
    try:
        from selenium import webdriver
    except Exception:
        return {}
    o = webdriver.ChromeOptions()
    o.add_argument("--user-data-dir=" + os.path.join(HERE, ".chrome-cookie-profiles", "makro"))
    o.add_experimental_option("prefs", {"credentials_enable_service": True,
                                        "profile.password_manager_enabled": True})
    d = webdriver.Chrome(options=o)
    try:
        d.get(f"{BASE}/shop/search?q=soda")
        d.set_script_timeout(180)
        probe = ids[:40]
        waited = 0
        while not d.execute_async_script(PRICE_JS, probe, STORE):
            if waited == 0:
                print("Makro: CHUA DANG NHAP - hay dang nhap trong cua so Chrome vua mo (cho 5 phut)...")
            if waited >= wait_login:
                print("Makro: khong dang nhap -> dung gia ke cong khai (CO THE LECH gia that)")
                return {}
            time.sleep(5); waited += 5
        real = {}
        for i in range(0, len(ids), 40 * 8):          # 8 request song song moi luot
            real.update(d.execute_async_script(PRICE_JS, ids[i:i + 320], STORE))
            if (i // 320) % 20 == 0:
                print(f"  gia that {len(real)}/{len(ids)}")
        print(f"Makro: gia that cho {len(real)}/{len(ids)} variant")
        return real
    finally:
        d.quit()


if __name__ == "__main__":
    main()
