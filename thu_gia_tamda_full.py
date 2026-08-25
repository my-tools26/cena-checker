# -*- coding: utf-8 -*-
"""Cao gia catalog Tamda Express (tamdaexpress.eu) - CAN DANG NHAP B2B.

Gia bi an sau dang nhap ("Dang nhap de xem gia") nen script mo mot cua so Chrome
that (khong headless), ban tu dang nhap 1 lan, roi script duyet danh muc doc
ten/gia/EAN -> tamda_full_prices.json.

MAC DINH = INCREMENTAL (chi them mat hang MOI):
  - Nap data cu tamda_full_prices.json, GIU nguyen.
  - Duyet danh muc voi sort MOI-NHAT-TRUOC; khi gap 3 trang lien tiep khong co
    hang moi -> dung (khoi cao het). Bo search sweep. -> nhanh hon nhieu.
  - Dung cho lich hang tuan (khi to roi het han thi hang moi tu vao).

  python thu_gia_tamda_full.py

CAO LAI TOAN BO (bo data cu + quet het moi trang + search sweep) - nen ~1 thang/lan
de bat het hang o sub-category sau:

  python thu_gia_tamda_full.py --full
"""
import json
import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

# Mac dinh CHAY INCREMENTAL: giu data cu, chi them mat hang MOI (sort moi-nhat
# truoc + dung som khi gap toan hang da biet, bo search sweep). Chay lai TOAN BO
# (bo data cu + quet het + search sweep) bang co --full (nen chay ~1 thang/lan).
FULL = "--full" in sys.argv
# So trang lien tiep KHONG co san pham moi -> coi nhu da toi vung da cao, dung
STOP_AFTER_ALLKNOWN = 3

BASE = "https://tamdaexpress.eu"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tamda_full_prices.json")

# Danh muc fallback neu tu dong kham pha that bai
CATS_FALLBACK = [
    "gastro", "do-uong-gastro", "drogerie", "banh-keo", "nuoc", "che-cafe",
    "gia-vi", "tre-em", "cho-meo", "do-choi", "do-gia-dung", "qua-tang",
    "hang-thoi-vu", "thuoc-la", "thuc-pham",
]

MAX_PAGES_PER_CAT = 120
EMPTY_PAGES_TO_STOP = 2


def wait_login(driver):
    print("Mo tamdaexpress.eu - hay dang nhap tai khoan B2B trong cua so Chrome vua mo...")
    driver.get(f"{BASE}/banh-keo.html")
    while True:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body_text = ""
        if "Đăng nhập để xem giá" not in body_text:
            print("Da phat hien dang nhap. Bat dau cao...")
            return
        time.sleep(2)


def parse_price(text):
    digits = re.sub(r"[^0-9]", "", text or "")
    if not digits:
        return None
    if len(digits) <= 2:
        return int(digits) / 100
    return int(digits[:-2]) + int(digits[-2:]) / 100


def extract_items(driver):
    try:
        grid = driver.find_element(By.CSS_SELECTOR, ".cat-view-grid")
    except Exception:
        return []
    cards = grid.find_elements(By.CSS_SELECTOR, ".product-item.ut2-gl__item")
    out = []
    for card in cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, ".product-title").text.strip()
        except Exception:
            continue
        try:
            price_txt = card.find_element(By.CSS_SELECTOR, ".ty-price").text
        except Exception:
            continue
        price = parse_price(price_txt)
        if price is None or not name:
            continue
        ean = None
        for feat in card.find_elements(By.CSS_SELECTOR, ".ut2-gl__feature"):
            m = re.search(r"EAN\s*(\d{8,14})", feat.text or "")
            if m:
                ean = m.group(1)
                break
        out.append({"name": name, "price": price, "ean": ean, "amount": "", "unit": ""})
    return out


def merge_items(collector, items):
    new = 0
    for it in items:
        key = it["ean"] or it["name"]
        if key not in collector:
            collector[key] = it
            new += 1
    return new


def discover_categories(driver):
    """Doc menu chinh de tim tat ca danh muc (ke ca sub-category)."""
    driver.get(BASE)
    time.sleep(2)
    slugs = set()
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        for a in links:
            href = a.get_attribute("href") or ""
            if href.startswith(BASE + "/") and href.endswith(".html"):
                slug = href[len(BASE) + 1:-5]  # bo ".html"
                if slug and "/" not in slug and not slug.startswith("search") \
                        and slug not in ("index", "profiles", "orders", "wishlist"):
                    slugs.add(slug)
    except Exception as e:
        print(f"Loi kham pha danh muc: {e}")
    if len(slugs) >= 10:
        print(f"Tu dong tim thay {len(slugs)} danh muc tu menu")
        return sorted(slugs)
    print(f"Chi tim thay {len(slugs)} danh muc, dung fallback")
    return CATS_FALLBACK


def crawl_category(driver, cat, collector):
    empty_streak = 0
    allknown_streak = 0
    for page in range(1, MAX_PAGES_PER_CAT + 1):
        if FULL:
            # TOAN BO: phan trang SEO nhu cu, khong sort
            url = f"{BASE}/{cat}.html" if page == 1 else f"{BASE}/{cat}-page-{page}.html"
        else:
            # INCREMENTAL: sort MOI-NHAT truoc + phan trang query de sort giu nguyen
            url = f"{BASE}/{cat}.html?sort_by=timestamp&sort_order=desc&page={page}"
        try:
            driver.get(url)
        except Exception as e:
            print(f"  [{cat} p{page}] loi mo trang: {e}")
            break
        time.sleep(1.0)
        items = extract_items(driver)
        if not items:
            empty_streak += 1
            if empty_streak >= EMPTY_PAGES_TO_STOP:
                break
            continue
        empty_streak = 0
        new = merge_items(collector, items)
        print(f"  [{cat} p{page}] {len(items)} san pham, +{new} moi (tong {len(collector)})")
        # INCREMENTAL: sort moi-nhat truoc -> khi da qua vung san pham moi,
        # cac trang sau toan hang cu -> dung som (khoi cao het 120 trang).
        if not FULL:
            allknown_streak = allknown_streak + 1 if new == 0 else 0
            if allknown_streak >= STOP_AFTER_ALLKNOWN:
                print(f"  [{cat}] {STOP_AFTER_ALLKNOWN} trang lien tiep khong co "
                      f"hang moi -> dung (incremental)")
                break


def search_sweep(driver, collector):
    """Tim kiem a-z, 0-9, cac ky tu Czech de bat san pham o sub-category sau."""
    queries = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["č", "ř", "š", "ž", "ů", "ď", "ť", "ň", "á", "é", "í", "ó", "ú", "ý"]
    before = len(collector)
    for q in queries:
        page = 1
        while page <= 30:
            url = (f"{BASE}/search.html?match=all&subcats=Y&pcode_from_q=Y"
                   f"&pshort=N&pfull=N&pname=Y&pkeywords=N"
                   f"&search_performed=Y&hidden=1&q={q}")
            if page > 1:
                url += f"&page={page}"
            try:
                driver.get(url)
            except Exception:
                break
            time.sleep(1.0)
            items = extract_items(driver)
            if not items:
                break
            new = merge_items(collector, items)
            if new > 0:
                print(f"  [search '{q}' p{page}] +{new} moi (tong {len(collector)})")
            page += 1
    added = len(collector) - before
    print(f"Search sweep: +{added} san pham moi")


def load_existing():
    """Nap tamda_full_prices.json cu -> collector, de INCREMENTAL chi them hang moi."""
    if not os.path.exists(OUT):
        return {}
    try:
        data = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        return {}
    coll = {}
    for it in data.get("items", []):
        key = it.get("ean") or it.get("name")
        if key:
            coll[key] = it
    return coll


def main():
    mode = "TOAN BO (--full)" if FULL else "INCREMENTAL (chi them hang moi)"
    print(f"Che do: {mode}")
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=vi-VN")
    driver = webdriver.Chrome(options=options)

    all_items = {} if FULL else load_existing()
    before = len(all_items)
    print(f"Data cu: {before} san pham" if not FULL else "Cao lai tu dau")
    try:
        wait_login(driver)
        cats = discover_categories(driver)
        for cat in cats:
            print(f"=== [{cat}] ===")
            crawl_category(driver, cat, all_items)
        if FULL:
            print(f"\n=== SEARCH SWEEP (bat san pham sot) ===")
            search_sweep(driver, all_items)
    finally:
        driver.quit()

    added = len(all_items) - before
    # An toan: incremental KHONG duoc lam giam so luong (neu cao loi ra rong ->
    # giu data cu, khong ghi de).
    if not FULL and os.path.exists(OUT) and len(all_items) < before:
        print(f"LOI: sau khi cao con {len(all_items)} < data cu {before} - "
              f"nghi cao loi, KHONG ghi de.")
        raise SystemExit(2)

    result = {
        "date": time.strftime("%Y-%m-%d"),
        "shop": "tamda_full",
        "items": list(all_items.values()),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"XONG: {len(result['items'])} san pham (+{added} moi) -> {OUT}")


if __name__ == "__main__":
    main()
