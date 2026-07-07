# -*- coding: utf-8 -*-
"""Thu thap EAN + ten mat hang tu e-shop Tamda Express (tamdaexpress.eu).

Chay:  python thu_gtin_tamda.py
Duyet 11 danh muc, moi trang san pham doc EAN trong bang thong so.
Ket qua gop dan vao ean_db.json (source=tamda). Chay lai an toan - bo qua URL da xu ly
(luu trong tamda_urls_done.txt).
"""
import http.client
import json
import os
import re
import time

import requests

# tamdaexpress.eu gui >100 header (Set-Cookie...) -> nang gioi han cua http.client
http.client._MAXHEADERS = 1000

BASE = "https://tamdaexpress.eu"
CATS = ["thuc-pham", "gia-vi", "nuoc", "che-cafe", "banh-keo", "drogerie",
        "do-gia-dung", "tre-em", "cho-meo", "do-choi", "qua-tang"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0",
           "Accept-Language": "cs,vi;q=0.8"}
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ean_db.json")
DONE = os.path.join(HERE, "tamda_urls_done.txt")

RE_PROD = re.compile(r'<span class="product-title"><a\s+href="(https://tamdaexpress\.eu/[^"]+\.html)"\s+title="([^"]*)"')
RE_PAGE = re.compile(r'-page-(\d+)\.html')
RE_EAN = re.compile(r'EAN</span></div>\s*(?:<!--[^>]*-->)?\s*<div class="ty-product-feature__value">(\d{8,14})</div>', re.S)
RE_EAN2 = re.compile(r'<em>EAN</em></span><span><em>(\d{8,14})</em>')


def load_db():
    with open(DB, encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    tmp = DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DB)


def get(url):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=45)
            if r.status_code == 200:
                return r.text
            print(f"  {url} -> HTTP {r.status_code}")
            return None
        except Exception as e:
            print(f"  loi {url}: {e}, cho 15s")
            time.sleep(15)
    return None


def main():
    db = load_db()
    done = set()
    if os.path.exists(DONE):
        with open(DONE, encoding="utf-8") as f:
            done = {l.strip() for l in f if l.strip()}

    # 1) Gom URL san pham tu tat ca danh muc
    products = {}
    for cat in CATS:
        page, maxpage = 1, 1
        while page <= maxpage:
            url = f"{BASE}/{cat}.html" if page == 1 else f"{BASE}/{cat}-page-{page}.html"
            h = get(url)
            if not h:
                break
            for purl, title in RE_PROD.findall(h):
                products[purl] = title
            pages = [int(x) for x in RE_PAGE.findall(h)]
            maxpage = max(pages) if pages else 1
            print(f"[{cat}] trang {page}/{maxpage} - tong URL: {len(products)}")
            page += 1
            time.sleep(0.5)

    todo = [(u, t) for u, t in products.items() if u not in done]
    print(f"Tong {len(products)} san pham, can cao {len(todo)} (da xong {len(products)-len(todo)})")

    # 2) Doc EAN tung trang san pham (song song 8 luong)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from threading import Lock
    lock = Lock()
    new = 0
    i = 0

    def worker(url, title):
        h = get(url)
        return url, title, (RE_EAN.findall(h) + RE_EAN2.findall(h)) if h else []

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(worker, u, t) for u, t in todo]
        for fut in as_completed(futs):
            url, title, eans = fut.result()
            with lock:
                for e in set(eans):
                    if e not in db["items"]:
                        db["items"][e] = {"name": title, "source": "tamda"}
                        new += 1
                done.add(url)
                i += 1
                if i % 100 == 0 or i == len(todo):
                    save_db(db)
                    with open(DONE, "w", encoding="utf-8") as f:
                        f.write("\n".join(sorted(done)))
                    print(f"tien do {i}/{len(todo)} - db {len(db['items'])} GTIN (+{new})")

    save_db(db)
    with open(DONE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(done)))
    print(f"XONG tamda: db co {len(db['items'])} GTIN, them moi {new}")


if __name__ == "__main__":
    main()
