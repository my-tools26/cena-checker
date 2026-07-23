# -*- coding: utf-8 -*-
"""Thu thap gia + ten + ma PTT + EAN toan bo pttglobal.eu (can dang nhap moi
thay gia; dung cookie phien PHPSESSID luu trong pttglobal_cookie.json,
KHONG commit file cookie len git - xem .gitignore).

Chay:  python thu_gia_pttglobal.py
Ket qua -> pttglobal_prices.json.

Cau truc 1 san pham (.s31-article-box):
  - ten: attribute alt cua <img>
  - ma PTT: span.code1
  - EAN: span.code2
  - gia s DPH: .s31-article-price
  - gia bez DPH (net): .s31-article-price-DPH

Cac danh muc cap 1 hien thi TOAN BO san pham cua ca cay danh muc con, phan
trang bang ?page=N (moi trang 48 san pham) - khong can cao rieng tung danh
muc con.
"""
import html
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.pttglobal.eu"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pttglobal_prices.json")
COOKIE_FILE = os.path.join(HERE, "pttglobal_cookie.json")
HEADERS = {"Accept": "text/html",
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0"}

CATEGORIES = [
    "sezonni", "drogerie", "domaci-potreby", "skolni-a-kancelarske-potreby",
    "svicky", "hracky", "automoto", "cestovni-potreby",
]
MAX_PAGES = 400  # phanh an toan

RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)
RE_PRICE = re.compile(r"([\d\s,.]+)\s*Kč", re.I)


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s or "")).strip()


def parse_price(text):
    m = RE_PRICE.search(text or "")
    if not m:
        return None
    num = m.group(1).replace(" ", "").replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None


def parse_products(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    out = []
    for box in soup.select(".s31-article-box"):
        img = box.select_one("img")
        name = clean(img.get("alt")) if img else ""
        code1 = box.select_one("span.code1")
        code2 = box.select_one("span.code2")
        code = clean(code1.get_text()) if code1 else ""
        ean = clean(code2.get_text()) if code2 else ""
        price_el = box.select_one(".s31-article-price")
        price_dph_el = box.select_one(".s31-article-price-DPH")
        price = parse_price(price_el.get_text()) if price_el else None
        price_net = parse_price(price_dph_el.get_text()) if price_dph_el else None
        if not name or not price:
            continue
        out.append({"name": name, "code": code, "ean": ean,
                    "price": price, "price_net": price_net})
    return out


def crawl_category(session, slug):
    page = 1
    results = []
    while page <= MAX_PAGES:
        for attempt in range(4):
            try:
                r = session.get(f"{BASE}/{slug}/", params={"page": page},
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
        print(f"  {slug} trang {page}: +{len(prods)}")
        page += 1
        time.sleep(0.4)
    return results


MIN_ITEMS = 5000  # duoi nguong nay coi nhu that bai (cookie het han) -> KHONG ghi de


def check_login(session):
    """Kiem tra cookie con hieu luc: trang drogerie phai co it nhat 1 gia.
    Chua dang nhap thi 'Cena za 1 kus' trong -> parse_products tra rong."""
    try:
        r = session.get(f"{BASE}/drogerie/", params={"page": 1},
                        headers=HEADERS, timeout=45)
        r.raise_for_status()
    except Exception as e:
        print(f"LOI: khong tai duoc trang kiem tra ({e})")
        return False
    return bool(parse_products(r.text))


def main():
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    session = requests.Session()
    session.cookies.update(cookies)

    if not check_login(session):
        print("LOI: cookie PTT Global het han (khong thay gia). "
              "Lay PHPSESSID moi tu Chrome da dang nhap, ghi vao "
              "pttglobal_cookie.json roi chay lai. KHONG ghi de du lieu cu.")
        raise SystemExit(2)

    seen = {}
    for slug in CATEGORIES:
        prods = crawl_category(session, slug)
        new = 0
        for p in prods:
            key = p["ean"] or p["code"] or p["name"]
            if key not in seen:
                seen[key] = p
                new += 1
        print(f"[pttglobal] {slug} - {len(prods)} mat hang ({new} moi) - tong {len(seen)}")

    items = []
    for p in seen.values():
        m = RE_AMOUNT.search(p["name"])
        amount = f"{m.group(1)} {m.group(2).lower()}" if m else ""
        items.append({"name": p["name"], "code": p["code"], "ean": p["ean"],
                       "price": round(p["price"], 2),
                       "price_net": round(p["price_net"], 2) if p["price_net"] else None,
                       "amount": amount, "unit": ""})

    if len(items) < MIN_ITEMS:
        print(f"LOI: chi lay duoc {len(items)} mat hang (< {MIN_ITEMS}), nghi ngo "
              f"cookie het han hoac site loi. KHONG ghi de du lieu cu.")
        raise SystemExit(2)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "pttglobal",
                   "vat_note": "price = s DPH, price_net = bez DPH",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"XONG pttglobal: {len(items)} mat hang -> pttglobal_prices.json")


if __name__ == "__main__":
    main()
