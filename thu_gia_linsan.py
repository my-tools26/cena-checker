# -*- coding: utf-8 -*-
"""Thu thap gia + ten mat hang tu linsan24h.cz (potraviny.linsan24h.cz).
API noi bo cua site (api.potraviny.linsan24h.cz/api/products/getProducts) tra ve
gia that (PriceValue) va ma vach that (Sku) du giao dien web hien "Dang nhap de
xem gia" cho khach chua dang nhap - khong can dang nhap, khong can cookie.
Chay:  python thu_gia_linsan.py
Ket qua -> linsan_prices.json.
"""
import html
import json
import os
import re
import time

import requests

API = "https://api.potraviny.linsan24h.cz/api/products/getProducts"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "linsan_prices.json")
HEADERS = {"Accept": "application/json", "Content-Type": "application/json",
           "User-Agent": "Mozilla/5.0 CenaChecker/1.0"}
LIMIT = 200

RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s or "")).strip()


def main():
    items = []
    fetched = 0
    total = None
    page = 1
    while True:
        for attempt in range(4):
            try:
                r = requests.post(API, json={"Limit": LIMIT, "Page": page},
                                   headers=HEADERS, timeout=45)
                r.raise_for_status()
                break
            except Exception as e:
                print(f"  trang {page} loi ({e}), cho 15s")
                time.sleep(15)
        else:
            break
        data = r.json()
        products = data.get("Products") or []
        if total is None:
            total = data.get("TotalCount", 0)
        if not products:
            break
        fetched += len(products)
        for p in products:
            name = clean(p.get("Name"))
            price_info = p.get("ProductPrice") or {}
            price = price_info.get("PriceValue")
            if not name or not price or price <= 0:
                continue
            m = RE_AMOUNT.search(name)
            amount = f"{m.group(1)} {m.group(2).lower()}" if m else ""
            item = {"name": name, "price": round(float(price), 2),
                     "amount": amount, "unit": ""}
            sku = clean(p.get("Sku"))
            if sku.isdigit() and len(sku) in (8, 12, 13, 14):
                item["ean"] = sku
            items.append(item)
        print(f"[linsan] trang {page} - da doc {fetched}/{total} mat hang, con lai {len(items)}")
        if len(products) < LIMIT or fetched >= total:
            break
        page += 1
        time.sleep(0.5)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "linsan",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"XONG linsan: {len(items)} mat hang -> linsan_prices.json")


if __name__ == "__main__":
    main()
