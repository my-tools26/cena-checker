# -*- coding: utf-8 -*-
"""Thu thap gia + ten mat hang tu bombacena.eu.
Trang web chi hien gia cho khach da dang nhap ("Prihlaste se pro zobrazeni
ceny"), nhung HTML cong khai van chua thuoc tinh data-price that trong khoi
.in-cart-info-price cua moi san pham (ro ri gia qua HTML, khong can dang nhap,
khong can cookie). Cao qua tung danh muc lon + phan trang ?p=N.
Chay:  python thu_gia_bombacena.py
Ket qua -> bombacena_prices.json.
"""
import html
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.bombacena.eu"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "bombacena_prices.json")
HEADERS = {"Accept": "text/html", "User-Agent": "Mozilla/5.0 CenaChecker/1.0"}

# 14 danh muc lon o menu chinh - di het se phu toan bo catalog (danh muc con
# nam trong cac danh muc lon nay, khong can cao rieng).
CATEGORIES = [
    "vyprodej", "nealko", "alko", "tabak", "cukrovinky", "trvanlive",
    "podpultovky", "pet-food", "drogerie", "domacnost-a-zahrada", "pecivo",
    "ovoce-a-zelenina", "chlazene-mlecne-a-uzeniny", "mrazene",
]
MAX_PAGES = 60  # phanh an toan, thuc te khong danh muc nao dai nhu vay

RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s or "")).strip()


def parse_products(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    out = []
    for p in soup.select(".product"):
        name_el = p.select_one("h3.name a")
        if not name_el:
            continue
        href = name_el.get("href") or ""
        name = clean(name_el.get_text())
        price_el = p.select_one(".in-cart-info-price")
        raw_price = price_el.get("data-price") if price_el else None
        try:
            price = float(raw_price) if raw_price not in (None, "") else None
        except ValueError:
            price = None
        if not name or not price or price <= 0:
            continue
        out.append((href, name, price))
    return out


def crawl_category(session, slug):
    page = 1
    results = []
    while page <= MAX_PAGES:
        for attempt in range(4):
            try:
                r = session.get(f"{BASE}/cs/{slug}", params={"p": page},
                                 headers=HEADERS, timeout=45)
                r.raise_for_status()
                break
            except Exception as e:
                print(f"  {slug} trang {page} loi ({e}), cho 10s")
                time.sleep(10)
        else:
            break
        prods = parse_products(r.text)
        if not prods:
            break
        results.extend(prods)
        page += 1
        time.sleep(0.4)
    return results


def main():
    session = requests.Session()
    seen = {}
    for slug in CATEGORIES:
        prods = crawl_category(session, slug)
        new = 0
        for href, name, price in prods:
            key = href or name
            if key not in seen:
                seen[key] = (name, price)
                new += 1
        print(f"[bombacena] {slug} - {len(prods)} mat hang ({new} moi) - tong {len(seen)}")

    items = []
    for name, price in seen.values():
        m = RE_AMOUNT.search(name)
        amount = f"{m.group(1)} {m.group(2).lower()}" if m else ""
        items.append({"name": name, "price": round(price, 2),
                      "amount": amount, "unit": ""})

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "bombacena",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"XONG bombacena: {len(items)} mat hang -> bombacena_prices.json")


if __name__ == "__main__":
    main()
