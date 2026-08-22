# -*- coding: utf-8 -*-
"""Cao 'EAN kod:' tu TUNG trang san pham dathang.cz (API khong tra ma nay,
chi co trong HTML). Day la ma dathang TU KHAI -> chinh xac nhat, uu tien hon
khop-theo-ten.

Chay:  python thu_ean_dathang_page.py
Ket qua -> dathang_page_ean.json {slug: {"name":..., "ean":..., "price":...}}
+ in so hang co EAN / tong.
"""
import json
import os
import re
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://www.dathang.cz/wp-json/wc/store/v1/products"
SHOP = "https://www.dathang.cz/shop/"
OUT = os.path.join(HERE, "dathang_page_ean.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0"}
RE_EAN = re.compile(r"EAN\s*k[oó]d:\s*(\d{8,14})", re.I)


def all_products(sess):
    prods, page = [], 1
    while True:
        r = sess.get(API, params={"per_page": 100, "page": page}, timeout=45)
        if r.status_code == 400:
            break
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        for p in data:
            prods.append({"slug": p.get("slug"), "name": p.get("name"),
                          "price": (p.get("prices") or {}).get("price")})
        page += 1
        time.sleep(0.2)
    return prods


def main():
    sess = requests.Session()
    sess.headers.update(UA)
    print("[1/2] Liet ke san pham ...")
    prods = all_products(sess)
    print(f"      {len(prods)} san pham")

    print("[2/2] Cao 'EAN kod' tung trang (co the vai chuc phut) ...")
    out = {}
    has = 0
    for i, p in enumerate(prods, 1):
        slug = p["slug"]
        if not slug:
            continue
        for attempt in range(3):
            try:
                r = sess.get(SHOP + slug + "/", timeout=30)
                break
            except Exception:
                time.sleep(5)
        else:
            continue
        m = RE_EAN.search(r.text)
        if m:
            out[slug] = {"name": p["name"], "ean": m.group(1), "price": p["price"]}
            has += 1
        if i % 250 == 0:
            print(f"      ...{i}/{len(prods)}  co EAN: {has}")
            json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(0.1)

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"XONG. Co 'EAN kod': {has}/{len(prods)} san pham -> dathang_page_ean.json")


if __name__ == "__main__":
    main()
