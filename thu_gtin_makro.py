# -*- coding: utf-8 -*-
"""Thu thap GTIN + ten mat hang tu API cong khai cua Makro (sortiment.makro.cz).

Chay:  python thu_gtin_makro.py [category]
Mac dinh category = potraviny. Ket qua gop dan vao ean_db.json (source=makro).
Co the chay lai bat ky luc nao - chi them ma moi, an toan khi ngat giua chung.
"""
import json
import os
import sys
import time

import requests

BASE = "https://sortiment.makro.cz"
STORE = "00006"
HEADERS = {"Accept": "application/json",
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0"}
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ean_db.json")


def load_db():
    if os.path.exists(DB):
        with open(DB, encoding="utf-8") as f:
            return json.load(f)
    return {"_note": "Database ma vach rieng", "items": {}}


def save_db(db):
    tmp = DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DB)


def search_page(cat, page, rows=1000):
    r = requests.get(
        f"{BASE}/searchdiscover/articlesearch/search",
        params={"storeId": STORE, "language": "cs-CZ", "country": "CZ",
                "query": "*", "rows": rows, "page": page,
                "filter": f"category:{cat}"},
        headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()


def betty(ids):
    r = requests.get(
        f"{BASE}/evaluate.article.v1/betty-articles",
        params={"ids": ",".join(ids), "country": "CZ", "locale": "cs-CZ",
                "storeIds": STORE, "details": "true"},
        headers=HEADERS, timeout=60)
    r.raise_for_status()
    j = r.json()
    if "errorCode" in j:
        raise RuntimeError(j.get("errorMessage"))
    out = {}
    for a in j.get("result", {}).values():
        for v in (a.get("variants") or {}).values():
            name = v.get("description")
            for b in (v.get("bundles") or {}).values():
                for g in (b.get("gtins") or []):
                    n = g.get("number")
                    if n and name:
                        out[n] = name
    return out


def category_tree(root):
    """Lay cay danh muc; tra ve list (path, amount) sao cho moi path <= 3000 mat hang
    (API chan offset > 3000)."""
    r = requests.get(
        f"{BASE}/searchdiscover/articlesearch/search",
        params={"storeId": STORE, "language": "cs-CZ", "country": "CZ",
                "query": "*", "rows": 1, "page": 1,
                "filter": f"category:{root}", "facets": "true"},
        headers=HEADERS, timeout=60)
    tree = r.json().get("categorytree") or {}

    out = []

    def walk(node):
        path, amt = node.get("urlCategoryPath"), node.get("amounts") or 0
        kids = list((node.get("children") or {}).values())
        if amt <= 3000 or not kids:
            if path and amt:
                out.append((path, amt))
            return
        for k in kids:
            walk(k)

    for top in (tree.get("children") or {}).values():
        walk(top)
    return out


def crawl_category(cat, db, known_arts, stats):
    page = 1
    while True:
        try:
            j = search_page(cat, page)
        except Exception as e:
            print(f"[{cat}] trang {page}: loi search ({e}), cho 30s")
            time.sleep(30)
            continue
        ids = j.get("resultIds") or []
        if not ids:
            break
        arts = []
        for i in ids:
            a = i[:-4]
            if a not in known_arts:
                known_arts.add(a)
                arts.append(a)
        print(f"[{cat}] trang {page}/{j.get('totalPages')} - {len(arts)} mat hang moi")
        for k in range(0, len(arts), 40):
            chunk = arts[k:k + 40]
            for attempt in range(3):
                try:
                    got = betty(chunk)
                    new = {g: n for g, n in got.items() if g not in db["items"]}
                    for g, n in new.items():
                        db["items"][g] = {"name": n, "source": "makro"}
                    stats["new"] += len(new)
                    break
                except Exception as e:
                    print(f"  batch loi ({e}), cho 20s...")
                    time.sleep(20)
            save_db(db)
            time.sleep(1.5)
        if not j.get("nextPage") or page >= (j.get("totalPages") or 1) or page * 1000 >= 3000:
            break
        page += 1


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "potraviny"
    db = load_db()
    known_arts = set()
    stats = {"new": 0}
    cats = category_tree(root)
    print(f"{len(cats)} danh muc con cua '{root}': tong ~{sum(a for _, a in cats)} mat hang")
    for i, (cat, amt) in enumerate(cats, 1):
        print(f"=== [{i}/{len(cats)}] {cat} ({amt}) ===")
        crawl_category(cat, db, known_arts, stats)
        print(f"  => db: {len(db['items'])} GTIN (+{stats['new']} phien nay)")
    print(f"XONG {root}: db co {len(db['items'])} GTIN, them moi {stats['new']}")


if __name__ == "__main__":
    main()
