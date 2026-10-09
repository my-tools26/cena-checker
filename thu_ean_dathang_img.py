# -*- coding: utf-8 -*-
"""Tim EAN cho mon dathang KHONG tu khai "EAN kod" tren trang, tu 2 nguon CHINH XAC
(khong doan theo ten):
  1. SKU dathang chinh la ma vach (8/12/13 so, dung so kiem tra)  -> src "SKU"
  2. Doc ma vach trong ANH san pham (zxing-cpp)                    -> src "IMG"
Nghien cuu 10/2026: 5150/6938 mon khong co EAN tren trang; SKU dang ma vach ~22 mon,
anh chup ma vach ~1.3% (phan lon anh chi chup mat truoc) -> ~65 mon.

Chay:  python thu_ean_dathang_img.py        (can: pip install --user zxing-cpp)
Ket qua -> dathang_img_ean.json {slug: {name, ean, src}}  (match_dathang.py --apply nap vao)
Chay lai: chi xu ly mon CHUA co trong file (nhanh).
"""
import io
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://www.dathang.cz/wp-json/wc/store/v1/products"
OUT = os.path.join(HERE, "dathang_img_ean.json")
PAGE = os.path.join(HERE, "dathang_page_ean.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CenaChecker/1.0"}


def ean_ok(s):
    """So kiem tra GS1 cho EAN-8/UPC-A/EAN-13."""
    if not re.fullmatch(r"\d{8}|\d{12}|\d{13}", s or ""):
        return False
    d = [int(c) for c in s]
    body, chk = d[:-1], d[-1]
    tot = sum(x * (3 if i % 2 == 0 else 1) for i, x in enumerate(reversed(body)))
    return (10 - tot % 10) % 10 == chk


def all_products(sess):
    out, pg = [], 1
    while True:
        r = sess.get(API, params={"per_page": 100, "page": pg}, timeout=45)
        if r.status_code != 200 or not r.json():
            return out
        out += r.json()
        pg += 1


def from_images(sess, p):
    import zxingcpp
    from PIL import Image
    for im in p.get("images") or []:
        try:
            b = sess.get(im["src"], timeout=30).content
            img = Image.open(io.BytesIO(b)).convert("RGB")
            for res in zxingcpp.read_barcodes(img):
                if ean_ok(res.text):
                    return res.text
        except Exception:
            pass
    return None


def main():
    sess = requests.Session()
    sess.headers.update(H)
    done = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    page = set(json.load(open(PAGE, encoding="utf-8"))) if os.path.exists(PAGE) else set()
    prods = [p for p in all_products(sess) if p["slug"] not in page]
    todo = [p for p in prods if p["slug"] not in done]
    print(f"{len(prods)} mon khong co EAN tren trang; can xu ly {len(todo)}")

    def job(p):
        sku = re.sub(r"-\d+$", "", (p.get("sku") or "").strip())
        if ean_ok(sku):
            return p, sku, "SKU"
        e = from_images(sess, p)
        return p, e, "IMG" if e else None

    n = 0
    with ThreadPoolExecutor(8) as ex:
        for p, e, src in ex.map(job, todo):
            # ghi ca mon KHONG tim thay (ean "") de lan sau bo qua
            done[p["slug"]] = {"name": p["name"], "ean": e or "", "src": src or ""}
            n += 1 if e else 0
    json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    tot = sum(1 for v in done.values() if v["ean"])
    print(f"XONG: lan nay +{n}, tong {tot} mon co EAN (SKU/anh) -> {OUT}")


if __name__ == "__main__":
    main()
