# -*- coding: utf-8 -*-
"""Thu thap gia + ten mat hang tu bombacena.eu.
Trang web chi hien gia cho khach da dang nhap ("Prihlaste se pro zobrazeni
ceny"), nhung HTML cong khai van chua thuoc tinh data-price that trong khoi
.in-cart-info-price cua moi san pham (ro ri gia qua HTML, khong can dang nhap,
khong can cookie). Cao qua tung danh muc lon + phan trang ?p=N.

Bo sung EAN (ma vach): trang chi tiet moi san pham co dong "EAN: <so>" va
"EAN baleni: <so>" - cung cong khai, khong can dang nhap. Vi co ~40k mat hang,
ta cao EAN DAN DAN: chi ghe trang chi tiet cua item CHUA co EAN (chua nam trong
bombacena_ean.json), moi lan chay gioi han BOMBACENA_EAN_LIMIT item de tranh
nang / chan IP. EAN da lay duoc cache lai vinh vien -> khong bao gio cao lai.
Chay:  python thu_gia_bombacena.py
Ket qua -> bombacena_prices.json (+ cache bombacena_ean.json).
"""
import html
import json
import os
import re
import time
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE = "https://www.bombacena.eu"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "bombacena_prices.json")
EAN_CACHE = os.path.join(HERE, "bombacena_ean.json")
HEADERS = {"Accept": "text/html", "User-Agent": "Mozilla/5.0 CenaChecker/1.0"}

# So item toi da ghe trang chi tiet de lay EAN moi lan chay (item chua co EAN).
# Chinh qua bien moi truong BOMBACENA_EAN_LIMIT. Dat 0 de tat viec cao EAN.
EAN_LIMIT = int(os.environ.get("BOMBACENA_EAN_LIMIT", "1200"))
EAN_SLEEP = 0.25  # nghi giua moi lan ghe trang chi tiet (lich su)

# 14 danh muc lon o menu chinh - di het se phu toan bo catalog (danh muc con
# nam trong cac danh muc lon nay, khong can cao rieng).
CATEGORIES_FALLBACK = [
    "vyprodej", "nealko", "alko", "tabak", "cukrovinky", "trvanlive",
    "podpultovky", "pet-food", "drogerie", "domacnost-a-zahrada", "pecivo",
    "ovoce-a-zelenina", "chlazene-mlecne-a-uzeniny", "mrazene",
]


def discover_categories(session):
    """Doc menu trang chu de tim tat ca danh muc, fallback neu that bai."""
    try:
        r = session.get(f"{BASE}/cs", headers=HEADERS, timeout=45)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        slugs = []
        seen = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            m = re.match(r"/cs/([a-z0-9-]+)/?$", href)
            if m and m.group(1) not in seen and m.group(1) not in (
                    "prihlaseni", "registrace", "kosik", "kontakt"):
                seen.add(m.group(1))
                slugs.append(m.group(1))
        if len(slugs) >= 10:
            print(f"Auto-discover: {len(slugs)} danh muc tu menu")
            return slugs
    except Exception as e:
        print(f"Loi discover: {e}")
    print(f"Dung fallback {len(CATEGORIES_FALLBACK)} danh muc")
    return CATEGORIES_FALLBACK
MAX_PAGES = 60  # phanh an toan, thuc te khong danh muc nao dai nhu vay

RE_AMOUNT = re.compile(r"(\d+[,.]?\d*)\s*(kg|g|ml|l|ks)\b", re.I)
# Bat "EAN: 123...", "EAN kus: 123...", "EAN baleni: 123..." (dau tuy chon)
RE_EAN = re.compile(r"(EAN(?:\s*(?:balen\w*|kus))?)\s*:?\s*([0-9]{8,14})", re.I)


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s or "")).strip()


def slug_of(href):
    """Lay ma san pham (tham so ?url=<slug>) tu href chi tiet lam khoa on dinh."""
    if not href:
        return None
    q = parse_qs(urlparse(href).query)
    return (q.get("url") or [None])[0] or href


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


def load_ean_cache():
    try:
        with open(EAN_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_ean_cache(cache):
    with open(EAN_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


def fetch_ean(session, href):
    """Ghe trang chi tiet, tra {'ean':..,'ean_bal':..,'fetched':True} hoac None."""
    url = href if href.startswith("http") else BASE + href
    for attempt in range(3):
        try:
            r = session.get(url, headers=HEADERS, timeout=45)
            r.raise_for_status()
            break
        except Exception:
            time.sleep(5)
    else:
        return None  # that bai -> khong cache, thu lai lan sau
    text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    ean = ean_bal = None
    for label, num in RE_EAN.findall(text):
        if "balen" in label.lower():
            ean_bal = num
        else:
            ean = num
    return {"ean": ean, "ean_bal": ean_bal, "fetched": True}


def enrich_ean(session, seen, cache):
    """Bo sung EAN dan dan cho item chua co trong cache (gioi han EAN_LIMIT)."""
    if EAN_LIMIT <= 0:
        print("Bo qua cao EAN (BOMBACENA_EAN_LIMIT=0)")
        return
    # BO TRUNG slug: 1 san pham co the nam o nhieu danh muc (href khac, slug giong)
    # -> chi ghe trang chi tiet 1 lan cho moi slug chua co trong cache.
    uniq = {}
    for v in seen.values():
        s = slug_of(v["href"])
        if s and s not in cache and s not in uniq:
            uniq[s] = v["href"]
    todo = list(uniq.items())
    print(f"EAN: {len(cache)} da co, {len(todo)} slug chua co - lan nay cao toi da {EAN_LIMIT}")
    fetched = 0
    for slug, href in todo:
        if fetched >= EAN_LIMIT:
            break
        info = fetch_ean(session, href)
        if info is None:
            continue  # loi mang -> de lan sau
        cache[slug] = info
        fetched += 1
        if fetched % 100 == 0:
            print(f"  ...da lay EAN {fetched}/{min(EAN_LIMIT, len(todo))}")
            save_ean_cache(cache)  # luu dan de khong mat tien do
        time.sleep(EAN_SLEEP)
    save_ean_cache(cache)
    print(f"EAN: lay them {fetched} item lan nay, tong cache {len(cache)}")


def main():
    session = requests.Session()
    categories = discover_categories(session)
    seen = {}
    for slug in categories:
        prods = crawl_category(session, slug)
        new = 0
        for href, name, price in prods:
            key = href or name
            if key not in seen:
                seen[key] = {"name": name, "price": price, "href": href}
                new += 1
        print(f"[bombacena] {slug} - {len(prods)} mat hang ({new} moi) - tong {len(seen)}")

    cache = load_ean_cache()
    enrich_ean(session, seen, cache)

    items = []
    n_ean = 0
    for v in seen.values():
        name, price, href = v["name"], v["price"], v["href"]
        m = RE_AMOUNT.search(name)
        amount = f"{m.group(1)} {m.group(2).lower()}" if m else ""
        item = {"name": name, "price": round(price, 2),
                "amount": amount, "unit": ""}
        c = cache.get(slug_of(href), {})
        if c.get("ean"):
            item["ean"] = c["ean"]
            n_ean += 1
        if c.get("ean_bal"):
            item["ean_bal"] = c["ean_bal"]
        items.append(item)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "bombacena",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"XONG bombacena: {len(items)} mat hang ({n_ean} co EAN) -> bombacena_prices.json")


if __name__ == "__main__":
    main()
