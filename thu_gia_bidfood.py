# -*- coding: utf-8 -*-
"""Thu thap gia + ten toan bo mujbidfood.cz (can dang nhap; dung cookie
phien luu trong bidfood_cookie.json).

Chay:  python thu_gia_bidfood.py
Ket qua -> bidfood_prices.json

Cach lay cookie: mo DevTools (F12) tren mujbidfood.cz da dang nhap,
tab Application > Cookies > mujbidfood.cz, copy tat ca cookie vao
bidfood_cookie.json theo format {"ten": "gia tri", ...}.
Hoac copy gia tri header Cookie tu bat ky request nao trong tab Network.
"""
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.mujbidfood.cz"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "bidfood_prices.json")
COOKIE_FILE = os.path.join(HERE, "bidfood_cookie.json")
HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0",
}

CATEGORIES = [
    "maso-drubez",
    "ryby-speciality",
    "hotova-jidla",
    "uzeniny-lahudky",
    "mlecne-chlazene",
    "pecivo-dezerty",
    "bramborove-vyrobky",
    "testoviny",
    "zelenina-ovoce-houby",
    "trvanlive-zbozi",
    "napoje-led",
    "zmrzliny",
    "nadobi-kuchynske-potreby",
    "non-food",
    "krmeni-pro-domaci-zvirata",
]

RE_PRICE = re.compile(r"([\d\s,]+)\s*Kč/(\w+)\s*bez DPH")
MIN_ITEMS = 2000


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def parse_products(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    items = []
    for card in soup.select(".product.product-card"):
        name_el = card.select_one(".name")
        name = clean(name_el.get_text()) if name_el else ""
        if not name:
            continue

        price_unit_el = card.select_one(".price-per-unit")
        price_text = clean(price_unit_el.get_text()) if price_unit_el else ""
        m = RE_PRICE.search(price_text)
        if not m:
            continue
        price_str = m.group(1).replace(" ", "").replace(",", ".")
        try:
            price = float(price_str)
        except ValueError:
            continue
        unit = m.group(2)

        unit_el = card.select_one(".unit")
        amount = clean(unit_el.get_text()) if unit_el else ""

        itemid_el = card.select_one(".itemid")
        itemid = clean(itemid_el.get_text()) if itemid_el else ""

        promo_el = card.select_one(".promo")
        pct = ""
        if promo_el:
            pct_text = clean(promo_el.get_text())
            pct_m = re.search(r"-?\d+\s*%", pct_text)
            if pct_m:
                pct = pct_m.group(0).replace(" ", "")

        items.append({
            "name": name,
            "amount": amount,
            "price": round(price, 2),
            "unit": unit,
            "code": itemid,
            "pct": pct,
        })
    return items


def check_login(session):
    try:
        r = session.get(f"{BASE}/cs/maso-drubez", headers=HEADERS, timeout=45)
        r.raise_for_status()
    except Exception as e:
        print(f"LOI: khong tai duoc trang kiem tra ({e})")
        return False
    soup = BeautifulSoup(r.text, "html.parser")
    prices = soup.select(".price-per-unit")
    for p in prices[:5]:
        if "Kč" in p.get_text():
            return True
    return False


def crawl_category(session, slug):
    url = f"{BASE}/cs/{slug}?showAll=Yes_please!"
    for attempt in range(4):
        try:
            r = session.get(url, headers=HEADERS, timeout=120)
            r.raise_for_status()
            return parse_products(r.text)
        except Exception as e:
            print(f"  {slug} loi ({e}), cho 10s...")
            time.sleep(10)
    return []


def main():
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    session = requests.Session()
    session.cookies.update(cookies)

    if not check_login(session):
        print("LOI: cookie Bidfood het han (khong thay gia). "
              "Lay cookie moi tu Chrome da dang nhap, ghi vao "
              "bidfood_cookie.json roi chay lai.")
        raise SystemExit(2)

    seen = {}
    for slug in CATEGORIES:
        prods = crawl_category(session, slug)
        new = 0
        for p in prods:
            key = p["code"] or p["name"]
            if key not in seen:
                seen[key] = p
                new += 1
        print(f"[bidfood] {slug}: {len(prods)} sp ({new} moi) - tong {len(seen)}")
        time.sleep(1)

    items = list(seen.values())

    if len(items) < MIN_ITEMS:
        print(f"LOI: chi lay duoc {len(items)} mat hang (< {MIN_ITEMS}), "
              f"nghi ngo cookie het han. KHONG ghi de du lieu cu.")
        raise SystemExit(2)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "items": items},
                  f, ensure_ascii=False, indent=1)
    print(f"XONG bidfood: {len(items)} mat hang -> bidfood_prices.json")


if __name__ == "__main__":
    main()
