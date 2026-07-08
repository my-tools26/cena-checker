# -*- coding: utf-8 -*-
"""Thu thap gia + ten mat hang tu dathang.cz (WooCommerce Store API cong khai).
Chay:  python thu_gia_dathang.py
Ket qua -> dathang_prices.json (nguon shop Viet, gia thuong khong chi khuyen mai).
"""
import html
import json
import os
import re
import time

import requests

API = "https://www.dathang.cz/wp-json/wc/store/v1/products"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dathang_prices.json")
HEADERS = {"Accept": "application/json",
           "User-Agent": "Mozilla/5.0 CenaChecker/1.0"}

# don vi tu ten: bat so luong de tinh gia/don vi sau nay
RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s or "")).strip()


def main():
    items = []
    page = 1
    while True:
        for attempt in range(4):
            try:
                r = requests.get(API, params={"per_page": 100, "page": page},
                                 headers=HEADERS, timeout=45)
                if r.status_code == 400:  # het trang
                    r = None
                    break
                r.raise_for_status()
                break
            except Exception as e:
                print(f"  trang {page} loi ({e}), cho 15s")
                time.sleep(15)
        else:
            r = None
        if r is None:
            break
        data = r.json()
        if not data:
            break
        for p in data:
            name = clean(p.get("name"))
            prices = p.get("prices") or {}
            raw = prices.get("price")
            minor = prices.get("currency_minor_unit", 2)
            if not name or raw in (None, "", "0"):
                continue
            try:
                price = int(raw) / (10 ** int(minor))
            except (ValueError, TypeError):
                continue
            if price <= 0:
                continue
            m = RE_AMOUNT.search(name)
            amount = f"{m.group(1)} {m.group(2).lower()}" if m else ""
            items.append({"name": name, "price": round(price, 2),
                          "amount": amount, "unit": ""})
        print(f"[dathang] trang {page} - tong {len(items)} mat hang")
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.5)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "dathang",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"XONG dathang: {len(items)} mat hang -> dathang_prices.json")


if __name__ == "__main__":
    main()
