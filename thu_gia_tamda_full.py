# -*- coding: utf-8 -*-
"""Cao gia catalog day du Tamda Express (tamdaexpress.eu) - CAN DANG NHAP B2B.

Gia bi an sau dang nhap ("Dang nhap de xem gia") nen script nay mo mot cua so
Chrome that (khong headless), ban tu dang nhap 1 lan, roi script tu dong duyet
qua tung trang so cua tat ca danh muc (URL dang <danh-muc>-page-N.html), doc
ten/gia/EAN va ghi vao tamda_full_prices.json.

Luu y: da thu chuyen sang requests (HTTP thuan, khong qua trinh duyet) de
nhanh hon nhung site khong chap nhan cookie tai su dung qua requests (van bi
coi la chua dang nhap) - nen phai dung Selenium (dieu khien that trinh duyet)
cho toan bo qua trinh, khong chi phan dang nhap.

Chay:  python thu_gia_tamda_full.py
"""
import json
import os
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

BASE = "https://tamdaexpress.eu"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tamda_full_prices.json")

CATS = [
    "gastro", "do-uong-gastro", "drogerie", "banh-keo", "nuoc", "che-cafe",
    "gia-vi", "tre-em", "cho-meo", "do-choi", "do-gia-dung", "qua-tang",
    "hang-thoi-vu", "thuoc-la",
]

MAX_PAGES_PER_CAT = 60  # an toan, tranh vong lap vo han neu site doi cau truc
EMPTY_PAGES_TO_STOP = 2  # 2 trang lien tiep khong co san pham moi -> het danh muc


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


def crawl_category(driver, cat, collector):
    empty_streak = 0
    for page in range(1, MAX_PAGES_PER_CAT + 1):
        url = f"{BASE}/{cat}.html" if page == 1 else f"{BASE}/{cat}-page-{page}.html"
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


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=vi-VN")
    driver = webdriver.Chrome(options=options)
    all_items = {}
    try:
        wait_login(driver)
        for cat in CATS:
            print(f"=== [{cat}] ===")
            crawl_category(driver, cat, all_items)
    finally:
        driver.quit()

    result = {
        "date": time.strftime("%Y-%m-%d"),
        "shop": "tamda_full",
        "items": list(all_items.values()),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"XONG: ghi {len(result['items'])} san pham vao {OUT}")


if __name__ == "__main__":
    main()
