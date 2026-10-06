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
    json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)


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

    items = []
    seen_names = set()
    for vid in ids:
        info = cache.get(vid)
        net = prices.get(vid)
        if not info or not net:
            continue
        name, ean, food = info["name"], info["ean"], info.get("food", True)
        vat = 1.12 if food else 1.21
        m = RE_AMOUNT.search(name)
        key = name + "|" + ean
        if key in seen_names:
            continue
        seen_names.add(key)
        items.append({"name": name, "price": round(net * vat, 1),
                      "price_net": net, "ean": ean,
                      "amount": f"{m.group(1)} {m.group(2).lower()}" if m else "",
                      "unit": ""})

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "makro_full",
                   "store": STORE, "vat_note": "price = s DPH (12% food/21% non-food tinh tu gia net)",
                   "items": items}, f, ensure_ascii=False)
    print(f"XONG makro: {len(items)} mat hang -> makro_full_prices.json")


if __name__ == "__main__":
    main()
