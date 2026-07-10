# -*- coding: utf-8 -*-
"""Thu thap gia + ten + EAN toan bo sortiment.makro.cz (API cong khai, khong can dang nhap).

Chay:  python thu_gia_makro.py
Ket qua -> makro_full_prices.json  (gia THUONG cua Makro, khong chi khuyen mai).

Luu y:
- API tra gia NET (bez DPH, xem price-config: primaryPriceType=net).
  Gia s DPH tinh theo co "food": 12% thuc pham, 21% con lai.
- Phan trang search bi chan o ~10k ket qua -> phai quet theo danh muc
  (filter=category:<duong-dan>), danh muc nao qua lon thi xuong cap con.
"""
import json
import os
import re
import time

import requests

BASE = "https://sortiment.makro.cz"
STORE = "00006"  # makro Praha - Stodulky
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "makro_full_prices.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0",
     "Accept": "application/json", "CallTreeId": "cena-checker"}
RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)
MAX_SEARCH = 3000  # search co filter danh muc bi chan o 3000 ket qua (do duoc 10.7.2026)


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


def collect_category(cat_path, prices, depth=0):
    """Quet 1 danh muc; neu >MAX_SEARCH ket qua thi chia nho theo cap con (them 1 tu vao path)."""
    d = search(cat_path, 1, 1)
    total = (d or {}).get("amount", 0)
    if not total:
        return
    if total > MAX_SEARCH:
        print(f"  ! {cat_path}: {total} > {MAX_SEARCH}, chi lay duoc 1 phan")
    pages = min((total + 499) // 500, MAX_SEARCH // 500)
    got = 0
    for pg in range(1, pages + 1):
        d = search(cat_path, 500, pg)
        if not d:
            break
        for rid in d.get("resultIds", []):
            info = d["results"].get(rid, {})
            if rid not in prices and info.get("price"):
                prices[rid] = info["price"]
                got += 1
        time.sleep(0.3)
    print(f"[{cat_path}] {total} sp, +{got} moi, tong {len(prices)}")


def main():
    cats = cat_tree()
    print(f"{len(cats)} danh muc cap 2")
    prices = {}  # variantId -> gia net
    for c in cats:
        collect_category(c, prices)
    # quet them query=* khong filter de vot 9000 sp dau (phong khi menu thieu)
    collect_category("", prices)
    ids = list(prices)
    print(f"Tong {len(ids)} variant, bat dau lay ten/EAN...")

    items = []
    seen_names = set()
    for i in range(0, len(ids), 40):
        chunk = ids[i:i + 40]
        d = get(f"{BASE}/evaluate.article.v1/betty-variants",
                {"storeIds": STORE, "country": "CZ", "locale": "cs-CZ",
                 "ids": ",".join(chunk)})
        if not d:
            continue
        for art in d.get("result", {}).values():
            food = art.get("food", True)
            for v in art.get("variants", {}).values():
                vid = v.get("bettyVariantId", {}).get("bettyVariantId", "")
                name = (v.get("description") or "").strip()
                net = prices.get(vid)
                if not name or not net:
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
        if (i // 40) % 25 == 0:
            print(f"  chi tiet {i}/{len(ids)} -> {len(items)} items")
        time.sleep(0.25)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "makro_full",
                   "store": STORE, "vat_note": "price = s DPH (12% food/21% non-food tinh tu gia net)",
                   "items": items}, f, ensure_ascii=False)
    print(f"XONG makro: {len(items)} mat hang -> makro_full_prices.json")


if __name__ == "__main__":
    main()
