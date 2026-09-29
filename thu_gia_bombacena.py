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
import sys
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


# Mac dinh INCREMENTAL: chi cao danh muc "hang moi + khuyen mai" (nhanh ~2-4 phut),
# giu data cu + cap nhat gia + them hang moi. Chay TOAN BO (tat ca danh muc + fetch
# EAN) bang --full (~30-40 phut, nen ~1 thang/lan de refresh het gia + lay EAN moi).
FULL = "--full" in sys.argv
INCR_CATS = ["akce", "novinky", "vyprodej"]   # hang moi + deal (noi gia hay doi)


def _is_incr(href):
    return any((href or "").startswith(f"/cs/{c}?") for c in INCR_CATS)


def load_existing():
    """Nap bombacena_prices.json cu -> {name: item} (giu ean/ean_bal), de incremental.
    QUAN TRONG: neu FILE TON TAI nhung doc loi (JSON hong, khoa boi tien trinh
    khac...) thi PHAI DUNG hang, KHONG duoc tra ve {} roi de main() tuong nham
    la 'chua co data cu' -> bo qua an toan giam manh -> ghi de mat sach du lieu
    cu (loi thuc te 18/09/2026: mat 28k/39971 mat hang vi loi nay)."""
    if not os.path.exists(OUT):
        return {}
    try:
        old = json.load(open(OUT, encoding="utf-8"))
        # KHOA la href/slug (dinh danh THAT), KHONG PHAI name: nhieu san pham
        # KHAC NHAU (mui huong/mau khac) dung chung 1 ten hien thi rut gon (vd
        # "Bartek 115g Svíčka ve skle..." lap toi 104 lan trong data that,
        # thang 39971 dong con 11815 ten neu gop theo ten -> gop NHAM mat
        # ~28000 san pham khac nhau. Loi thuc te 18-28/09/2026, da phuc hoi tu
        # git va sua lai key o day.
        # Khoa = SLUG (?url=...), KHONG phai href: cung 1 san pham nam o nhieu
        # danh muc (/cs/akce?url=X, /cs/novinky?url=X...) -> khoa href lam NHAN
        # DOI 3-4 lan (40276 dong nhung chi 13108 san pham that, 29/09/2026).
        # Khi trung slug: uu tien ban o danh muc incremental (duoc cao lai
        # thuong xuyen nhat = gia/ten moi nhat).
        out = {}
        for it in old.get("items", []):
            key = slug_of(it.get("href")) or it.get("name")
            if not key:
                continue
            if key in out and not _is_incr(it.get("href")):
                continue
            out[key] = it
        return out
    except Exception as e:
        print(f"LOI NGHIEM TRONG: file cu {OUT} ton tai nhung doc/parse that bai "
              f"({e}). DUNG lai de tranh ghi de mat du lieu cu.")
        raise SystemExit(2)


def main():
    session = requests.Session()
    categories = discover_categories(session) if FULL else INCR_CATS
    print(f"Che do: {'TOAN BO (--full)' if FULL else 'INCREMENTAL (hang moi + akce)'}")

    seen = {}
    for slug in categories:
        prods = crawl_category(session, slug)
        new = 0
        for href, name, price in prods:
            key = slug_of(href) or name
            if key not in seen:
                seen[key] = {"name": name, "price": price, "href": href}
                new += 1
        print(f"[bombacena] {slug} - {len(prods)} mat hang ({new} moi) - tong {len(seen)}")

    cache = load_ean_cache()
    enrich_ean(session, seen, cache)   # incremental: chi it hang moi chua co EAN -> nhanh

    # san pham vua cao -> {href-hoac-ten: item}. GIU href trong item de lan
    # sau (kha incremental) khop DUNG san pham, khong gop nham theo ten chung.
    crawled = {}
    for key, v in seen.items():
        name, price, href = v["name"], v["price"], v["href"]
        m = RE_AMOUNT.search(name)
        amount = f"{m.group(1)} {m.group(2).lower()}" if m else ""
        item = {"name": name, "price": round(price, 2), "amount": amount,
                "unit": "", "href": href}
        c = cache.get(slug_of(href), {})
        if c.get("ean"):
            item["ean"] = c["ean"]
        if c.get("ean_bal"):
            item["ean_bal"] = c["ean_bal"]
        crawled[key] = item

    if FULL:
        items = list(crawled.values())
    else:
        # INCREMENTAL: giu data cu, cap nhat GIA + them hang MOI (khop theo href)
        merged = load_existing()
        before = len(merged)
        added = updated = 0
        for key, it in crawled.items():
            if key in merged:
                old = merged[key]
                if old.get("price") != it["price"]:
                    updated += 1
                # lay ten/gia/dung tich MOI NHAT tren kho; giu EAN cu neu lan nay thieu
                for f in ("ean", "ean_bal"):
                    if old.get(f) and not it.get(f):
                        it[f] = old[f]
                merged[key] = it
            else:
                merged[key] = it; added += 1
        items = list(merged.values())
        print(f"Incremental: +{added} hang moi, cap nhat gia {updated}, tong {len(items)} (cu {before})")
        # an toan: khong duoc giam manh (neu it hon 90% data cu -> nghi loi;
        # nguong cao vi gio khop chinh xac theo href, khong con gop nham nua)
        if before and len(items) < before * 0.9:
            print("LOI: giam manh bat thuong, KHONG ghi de."); raise SystemExit(2)

    # href GIU LAI trong output (build_static/app.js chi doc field can, bo qua
    # field la) - de LAN CHAY SAU dung href lam khoa khop chinh xac, khong con
    # gop nham cac san pham khac nhau dung chung 1 ten hien thi.
    n_ean = sum(1 for it in items if it.get("ean"))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "bombacena",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"XONG bombacena: {len(items)} mat hang ({n_ean} co EAN) -> bombacena_prices.json")


if __name__ == "__main__":
    main()
