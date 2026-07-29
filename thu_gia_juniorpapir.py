# -*- coding: utf-8 -*-
"""Thu thap gia B2B toan bo juniorpapir.cz (can dang nhap; dung cookie phien
luu trong juniorpapir_cookie.json).

Chay:  python thu_gia_juniorpapir.py
Ket qua -> juniorpapir_prices.json

Cach lay cookie: dang nhap juniorpapir.cz trong Chrome, mo DevTools (F12) ->
tab Network -> F5 reload -> bam vao request dau tien -> Headers -> Request
Headers -> copy gia tri sau "cookie:" -> dua cho Claude de tach 2 cookie
".BSCTOK2" va ".BSSTOK2".

Cau truc: moi trang danh muc goc (c-so) nhung <script type='application/
ld+json'> chua ItemList day du (ten, gia B2B, EAN gtin8, url) cho CA CAY
danh muc con - khong can quet rieng tung danh muc con.
Phan trang: ?f=N (N = 0,30,60,... buoc 30). Trang cuoi < 30 san pham.
"""
import json
import os
import re
import time

import requests

BASE = "https://www.juniorpapir.cz"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "juniorpapir_prices.json")
COOKIE_FILE = os.path.join(HERE, "juniorpapir_cookie.json")
HEADERS = {
    "Accept": "text/html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0",
}

CATEGORIES_FALLBACK = [
    "akcie-zlavy-a-novinky-v-ponuke-juniorpapier-c2664",
    "skolske-tasky-a-batohy-pre-skolakov-a-studentov-c2229",
    "skolske-potreby-a-pomocky-pre-ziakov-a-studentov-c1214",
    "pisacie-potreby-farbicky-a-korektory-c1209",
    "papier-zosity-a-papierove-potreby-pre-skoly-aj-kancelarie-c1151",
    "kancelarske-potreby-pre-firmy-skoly-aj-domacnosti-c1187",
    "kancelarska-technika-a-prislusenstvo-c1202",
    "gastro-potreby-a-party-vyzdoba-c1224",
    "drogeria-hygienicke-potreby-a-obalovy-material-c1233",
    "spolocenske-hry-a-hracky-pre-deti-c1242",
    "darcekove-doplnky-a-dekoracie-c2228",
    "sezonny-sortiment-vianoce-velka-noc-halloween-a-dekoracie-c1261",
]


def discover_categories(session):
    """Doc menu trang chu de tim danh muc co dang *-cNNNN, fallback neu that bai."""
    try:
        r = session.get(f"{BASE}/", headers=HEADERS, timeout=45)
        r.raise_for_status()
        slugs = []
        seen = set()
        for m in re.finditer(r'href="/([a-z0-9-]+-c\d+)/"', r.text):
            slug = m.group(1)
            if slug not in seen:
                seen.add(slug)
                slugs.append(slug)
        if len(slugs) >= 8:
            print(f"Auto-discover: {len(slugs)} danh muc tu menu")
            return slugs
    except Exception as e:
        print(f"Loi discover: {e}")
    print(f"Dung fallback {len(CATEGORIES_FALLBACK)} danh muc")
    return CATEGORIES_FALLBACK

PAGE_SIZE = 30
MAX_PAGES = 200  # phanh an toan (~6000 sp/danh muc)
RE_LDJSON = re.compile(r"<script type='application/ld\+json'>(.*?)</script>", re.S)
RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)
MIN_ITEMS = 500


def parse_itemlist(html_text):
    for sc in RE_LDJSON.findall(html_text):
        try:
            d = json.loads(sc.strip())
        except Exception:
            continue
        if d.get("@type") == "ItemList":
            return d.get("itemListElement", [])
    return []


def check_login(session):
    r = session.get(f"{BASE}/", headers=HEADERS, timeout=45)
    r.raise_for_status()
    return "UserPanelView" in r.text and "settings" in r.text


def crawl_category(session, slug):
    items, offset = [], 0
    for _ in range(MAX_PAGES):
        url = f"{BASE}/{slug}/" + (f"?f={offset}" if offset else "")
        for attempt in range(4):
            try:
                r = session.get(url, headers=HEADERS, timeout=45)
                r.raise_for_status()
                break
            except Exception as e:
                print(f"  {slug} f={offset} loi ({e}), cho 10s")
                time.sleep(10)
        else:
            break
        elems = parse_itemlist(r.text)
        if not elems:
            break
        for el in elems:
            it = el.get("item", {})
            offer = it.get("offers", {}) or {}
            name = (it.get("name") or "").strip()
            price = offer.get("price")
            if not name or not price:
                continue
            ean = it.get("gtin8") or it.get("gtin13") or it.get("gtin") or ""
            items.append({"name": name, "price": float(price), "ean": str(ean),
                          "sku": it.get("sku", "")})
        if len(elems) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.3)
    return items


def main():
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    session = requests.Session()
    session.cookies.update(cookies)

    if not check_login(session):
        print("LOI: cookie juniorpapir het han (khong thay dau hieu dang nhap). "
              "Lay cookie moi tu Chrome da dang nhap (F12 > Network > request "
              "dau tien > Request Headers > Cookie), roi chay lai.")
        raise SystemExit(2)

    categories = discover_categories(session)
    seen = {}
    for slug in categories:
        prods = crawl_category(session, slug)
        new = 0
        for p in prods:
            key = p["ean"] or p["sku"] or p["name"]
            if key not in seen:
                seen[key] = p
                new += 1
        print(f"[juniorpapir] {slug}: {len(prods)} sp ({new} moi) - tong {len(seen)}")
        time.sleep(1)

    items = []
    for p in seen.values():
        m = RE_AMOUNT.search(p["name"])
        items.append({"name": p["name"], "price": round(p["price"], 2),
                      "ean": p["ean"],
                      "amount": f"{m.group(1)} {m.group(2).lower()}" if m else "",
                      "unit": ""})

    if len(items) < MIN_ITEMS:
        print(f"LOI: chi lay duoc {len(items)} mat hang (< {MIN_ITEMS}), "
              f"nghi ngo cookie het han. KHONG ghi de du lieu cu.")
        raise SystemExit(2)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "items": items},
                  f, ensure_ascii=False, indent=1)
    print(f"XONG juniorpapir: {len(items)} mat hang -> juniorpapir_prices.json")


if __name__ == "__main__":
    main()
