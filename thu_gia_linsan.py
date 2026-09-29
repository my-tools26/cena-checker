# -*- coding: utf-8 -*-
"""Thu thap gia + ten mat hang tu linsan24h.cz (potraviny.linsan24h.cz).
API noi bo cua site (api.potraviny.linsan24h.cz/api/products/getProducts) tra ve
gia that (PriceValue) va ma vach that (Sku) du giao dien web hien "Dang nhap de
xem gia" cho khach chua dang nhap - khong can dang nhap, khong can cookie.
Chay:  python thu_gia_linsan.py
Ket qua -> linsan_prices.json.

Luu y (28/09/2026): API nay KHONG ho tro sort theo ngay tao (da kiem chung cac
tham so OrderBy/Sort deu bi bo qua hoac loi 400) -> KHONG THE bo qua trang cu
mot cach an toan (co nguy co sot hang moi nam giua danh sach). Van quet HET
moi trang moi lan (~16 trang, da nhanh <1 phut), nhung MERGE vao data cu thay
vi ghi de tu dau -> khong mat du lieu neu crawl loi giua chung, hang MOI van
duoc them, gia hang cu duoc cap nhat.
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


def load_existing():
    if not os.path.exists(OUT):
        return {}
    try:
        d = json.load(open(OUT, encoding="utf-8"))
    except Exception as e:
        print(f"LOI NGHIEM TRONG: file cu {OUT} ton tai nhung doc/parse that "
              f"bai ({e}). DUNG lai de tranh ghi de mat du lieu cu.")
        raise SystemExit(2)
    out = {}
    for it in d.get("items", []):
        # hang cu (truoc khi co sku_key) van co ean == sku -> khop dung khoa moi
        key = it.get("sku_key") or it.get("ean") or it.get("name")
        if key:
            out[key] = it
    return out


def main():
    merged = load_existing()
    before = len(merged)
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
            sku = clean(p.get("Sku"))
            # sku_key: dinh danh THAT cua site (moi khi co), tranh gop nham cac
            # san pham KHAC NHAU dung chung ten hien thi (~25 cap da thay trong
            # data that 28/09/2026). Field noi bo, khong dung o app.
            item = {"name": name, "price": round(float(price), 2),
                     "amount": amount, "unit": "", "sku_key": sku or None}
            if not item["sku_key"]:
                del item["sku_key"]
            if sku.isdigit() and len(sku) in (8, 12, 13, 14):
                item["ean"] = sku
            key = item.get("sku_key") or name
            # bo ban cu khoa theo TEN (chua co sku_key) de khong nhan doi
            old = merged.get(name)
            if key != name and old is not None and not old.get("sku_key"):
                del merged[name]
            # ghi de ca item -> ten/dung tich luon theo du lieu MOI NHAT tren kho
            merged[key] = item
        print(f"[linsan] trang {page} - da doc {fetched}/{total} mat hang, tong {len(merged)}")
        if len(products) < LIMIT or fetched >= total:
            break
        page += 1
        time.sleep(0.5)

    items = list(merged.values())
    if before and len(items) < before * 0.5:
        print(f"LOI: sau khi cao con {len(items)} < 50% data cu {before}, KHONG ghi de.")
        raise SystemExit(2)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "linsan",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"(+{len(items) - before} moi so voi lan truoc)")
    print(f"XONG linsan: {len(items)} mat hang -> linsan_prices.json")


if __name__ == "__main__":
    main()
