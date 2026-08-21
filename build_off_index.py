# -*- coding: utf-8 -*-
"""Tao nguon ung vien EAN OFFLINE tu Open Food Facts (mien phi) cho matcher
dathang - thay cho map tay.

Y tuong: dathang khong co ma vach, cac catalog Sec cua ta thieu hang ngoai
(Muller Duc...). OFF co hang trieu san pham EU co san EAN + ten + hang. Tai 1
lan bo CSV (~1.3GB nen), STREAM loc chi giu san pham co ten/hang TRUNG voi
thuong hieu dathang dang ban -> off_candidates.json (nho gon) -> nap vao
match_dathang.py nhu 1 nguon "OFF".

Chay:  python build_off_index.py
Ket qua -> off_candidates.json  {ean: {"name":..., "brand":..., "qty":...}}

Chi phi: 1 lan tai ~1.3GB. Chay lai khi muon lam moi (vd hang thang).
"""
import csv
import gzip
import io
import json
import os
import re
import sys
import unicodedata

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OFF_CSV = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
OUT = os.path.join(HERE, "off_candidates.json")
DATHANG = os.path.join(HERE, "dathang_prices.json")
UA = {"User-Agent": "CenaChecker/1.0 (quoctuan1234@gmail.com)"}

STOP = {"kart", "bal", "krt", "the", "pro", "bez", "cca", "set", "kus", "kusu",
        "and", "with", "new", "mix", "bpo", "vyr", "orig", "ltd", "part",
        "party", "limited", "edition", "sugar", "zero", "protein", "gastro"}


def strip_accents(s):
    s = (s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def toks(name):
    out = []
    s = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", strip_accents(name))
    for t in re.split(r"[^a-z0-9]+", s):
        if len(t) >= 4 and not t.isdigit() and t not in STOP:
            out.append(t)
    return out


def dathang_brand_tokens():
    """Tap token 'thuong hieu' cua dathang: token >=4 ky tu xuat hien vua du hiem
    (khong phai tu chung) -> dung de LOC OFF cho gon + dung trong tam."""
    data = json.load(open(DATHANG, encoding="utf-8"))
    items = data.get("items", data)
    from collections import Counter
    cnt = Counter()
    for it in items:
        for t in set(toks(it.get("name", ""))):
            cnt[t] += 1
    # bo token qua pho bien (tu chung) va qua hiem (loi chinh ta) -> giu "thuong hieu"
    n = len(items)
    keep = set()
    for t, c in cnt.items():
        if 2 <= c <= n * 0.03:      # xuat hien tu 2 lan den <=3% san pham
            keep.add(t)
    return keep


VALID_EAN = re.compile(r"^\d{8}$|^\d{12,13}$")


def main():
    print("[1/3] Doc thuong hieu dathang de loc ...")
    brands = dathang_brand_tokens()
    print(f"      {len(brands)} token thuong-hieu dathang lam bo loc")

    print(f"[2/3] Stream OFF CSV (~1.3GB nen) va loc ... (vai phut)")
    csv.field_size_limit(2 ** 31 - 1)   # OFF co field ingredients rat dai
    r = requests.get(OFF_CSV, headers=UA, stream=True, timeout=120)
    r.raise_for_status()
    gz = gzip.GzipFile(fileobj=r.raw)
    text = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
    reader = csv.DictReader(text, delimiter="\t")

    out = {}
    seen_line = kept = 0
    for row in reader:
        seen_line += 1
        if seen_line % 500000 == 0:
            print(f"      ...{seen_line} dong, giu {kept}")
        code = (row.get("code") or "").strip()
        name = (row.get("product_name") or "").strip()
        brand = (row.get("brands") or "").split(",")[0].strip()
        if not name or not brand or not VALID_EAN.match(code):
            continue
        # LOC CHAT: chi giu khi truong HANG (brands) chia se token thuong-hieu
        # dathang -> dac trung hon nhieu so voi loc theo ten (chan hang chung).
        if not (set(toks(brand)) & brands):
            continue
        if code in out:
            continue
        out[code] = {"name": name, "brand": brand,
                     "qty": (row.get("quantity") or "").strip()}
        kept += 1

    print(f"[3/3] Ghi {len(out)} ung vien OFF -> off_candidates.json")
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"XONG. Tong dong OFF doc: {seen_line}, giu lai: {kept}")


if __name__ == "__main__":
    main()
