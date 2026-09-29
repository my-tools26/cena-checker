# -*- coding: utf-8 -*-
"""Thu thap gia + ten mat hang tu dathang.cz (WooCommerce Store API cong khai).

MAC DINH = INCREMENTAL (chi them mat hang MOI):
  - Da kiem chung (28/09/2026): thu tu mac dinh cua API nay CHINH LA moi-nhat-
    truoc (id giam dan = ngay tao giam dan) -> an toan de dung SOM.
  - Nap data cu, giu nguyen; duyet tu trang 1, khi gap 3 trang lien tiep 0 san
    pham moi thi dung (khong can quet het ~70 trang nhu truoc).
  - Gia CUA HANG DA BIET van duoc cap nhat trong vung vua quet qua (khong chi
    them moi) - chi hang nam sau diem dung la giu gia cu.

  python thu_gia_dathang.py

CAO LAI TOAN BO (bo qua data cu, quet het moi trang) - nen ~1 thang/lan de
lam moi gia CA cac hang cu nam sau diem dung incremental:

  python thu_gia_dathang.py --full
"""
import html
import json
import os
import re
import sys
import time

import requests

API = "https://www.dathang.cz/wp-json/wc/store/v1/products"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dathang_prices.json")
HEADERS = {"Accept": "application/json",
           "User-Agent": "Mozilla/5.0 CenaChecker/1.0"}

FULL = "--full" in sys.argv
STOP_AFTER_ALLKNOWN = 3

# don vi tu ten: bat so luong de tinh gia/don vi sau nay
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
    # khoa = id san pham cua site (on dinh khi kho DOI TEN); hang cu chua co id
    # -> tam khoa theo ten, se duoc gan id o lan cao ke tiep
    return {(str(it["id"]) if it.get("id") else it["name"]): it
            for it in d.get("items", []) if it.get("id") or it.get("name")}


def main():
    print(f"Che do: {'TOAN BO (--full)' if FULL else 'INCREMENTAL (chi hang moi)'}")
    merged = {} if FULL else load_existing()
    before = len(merged)

    page = 1
    allknown_streak = 0
    while True:
        params = {"per_page": 100, "page": page}
        if not FULL:
            params["orderby"] = "date"
            params["order"] = "desc"
        for attempt in range(4):
            try:
                r = requests.get(API, params=params, headers=HEADERS, timeout=45)
                if r.status_code == 400:  # het trang
                    r = None
                    break
                r.raise_for_status()
                break
            except Exception as e:
                print(f"  trang {page} loi ({e}), cho 15s")
                time.sleep(15)
        else:
            r = None
        if r is None:
            break
        data = r.json()
        if not data:
            break
        new_this_page = 0
        for p in data:
            name = clean(p.get("name"))
            prices = p.get("prices") or {}
            raw = prices.get("price")
            minor = prices.get("currency_minor_unit", 2)
            if not name or raw in (None, "", "0"):
                continue
            try:
                price = int(raw) / (10 ** int(minor))
            except (ValueError, TypeError):
                continue
            if price <= 0:
                continue
            m = RE_AMOUNT.search(name)
            amount = f"{m.group(1)} {m.group(2).lower()}" if m else ""
            item = {"name": name, "price": round(price, 2),
                    "amount": amount, "unit": ""}
            pid = p.get("id")
            key = str(pid) if pid else name
            if pid:
                item["id"] = pid
            old = merged.get(key)
            if old is None and key != name and name in merged                     and not merged[name].get("id"):
                old = merged.pop(name)  # hang cu khoa theo ten -> chuyen sang id, khong nhan doi
            if old is None:
                new_this_page += 1
            elif old.get("ean"):
                item["ean"] = old["ean"]  # giu EAN da gan boi match_dathang.py
            # ghi de -> ten/gia/dung tich luon theo du lieu MOI NHAT tren kho
            merged[key] = item
        print(f"[dathang] trang {page} - +{new_this_page} moi (tong {len(merged)})")
        if not FULL:
            allknown_streak = allknown_streak + 1 if new_this_page == 0 else 0
            if allknown_streak >= STOP_AFTER_ALLKNOWN:
                print(f"  {STOP_AFTER_ALLKNOWN} trang lien tiep khong co hang moi -> dung (incremental)")
                break
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.5)

    items = list(merged.values())
    if not FULL and before and len(items) < before * 0.5:
        print(f"LOI: sau khi cao con {len(items)} < 50% data cu {before}, KHONG ghi de.")
        raise SystemExit(2)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "shop": "dathang",
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"XONG dathang: {len(items)} mat hang (+{len(items) - before} moi) -> dathang_prices.json")


if __name__ == "__main__":
    main()
