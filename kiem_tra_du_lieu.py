# -*- coding: utf-8 -*-
"""CHOT KIEM TRA truoc moi lan commit (git pre-commit hook goi tu dong) — chong
day du lieu hong/thieu len web (10/2026, sau cac vu: Bombacena mat 28k mon, tu
dien mat 34 muc, Makro dung 18 ngay).

So ban SAP COMMIT (staged) voi ban dang co tren git (HEAD), CHAN commit neu:
  - file .json nao khong doc duoc
  - kho nao (*_prices.json) giam > 10% so mon
  - docs/data/catalog.json giam > 10% so mon
  - tu dien docs/data/dict.json IT muc hon truoc
  - khuyen mai docs/data/retail.json duoi 300 mon
  - kho nao (*_prices.json) co 1 SAN PHAM (cung ma: slug ?url=, href, code,
    sku_key) xuat hien NHIEU DONG -> 1 mon nhieu gia tren web (loi Bombacena
    15/10/2026: 1 mon nam o akce/nealko/novinky luu 3 dong, cao nhanh chi cap
    nhat 1 dong, cac dong kia giu gia cu). Crawler phai khoa theo MA SAN PHAM.
Co chu dich giam that (vd kho ngung ban nhieu hang): dat bien moi truong
CENA_CHO_PHEP_GIAM=1 roi commit lai — CHI KHI NGUOI DUNG XAC NHAN. Routine tu
dong KHONG BAO GIO tu dat bien nay: bi chan -> giu nguyen, bao loi trong bao cao.

Cai hook (1 lan, neu clone lai repo):
  printf '#!/bin/sh\nPYTHONUTF8=1 python kiem_tra_du_lieu.py\n' > .git/hooks/pre-commit

Chay tay:  python kiem_tra_du_lieu.py      (kiem cac file dang staged)
"""
import json
import os
import subprocess
import sys
from collections import Counter
from urllib.parse import parse_qs, urlparse

MAX_DROP = 0.10


def git(*a):
    return subprocess.run(["git", *a], capture_output=True)


def staged_files():
    out = git("diff", "--cached", "--name-only", "--diff-filter=AM").stdout.decode("utf-8", "replace")
    return [f for f in out.splitlines() if f.endswith(".json")]


def load(ref_path):
    r = git("show", ref_path)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout.decode("utf-8"))


def count(d):
    if isinstance(d, dict):
        return len(d.get("items", d))
    return len(d) if isinstance(d, list) else 0


def product_id(it):
    """Ma dinh danh san pham trong 1 kho (None neu kho khong co ma)."""
    if not isinstance(it, dict):
        return None
    h = it.get("href") or it.get("url")
    if h:
        q = parse_qs(urlparse(h).query)
        return "url:" + (q["url"][0] if q.get("url") else urlparse(h).path.rstrip("/"))
    for k in ("code", "sku_key"):
        if it.get(k):
            return f"{k}:{it[k]}"
    return None


def duplicate_ids(d):
    items = d.get("items", d) if isinstance(d, dict) else d
    if isinstance(items, dict):
        items = list(items.values())
    c = Counter(i for i in map(product_id, items or []) if i)
    return [k for k, n in c.items() if n > 1]


def main():
    errs = []
    for f in staged_files():
        try:
            new = load(":" + f)
        except Exception as e:
            errs.append(f"{f}: KHONG DOC DUOC ({e})")
            continue
        if f.startswith("docs/data/ean/") or new is None:
            continue
        try:
            old = load("HEAD:" + f)
        except Exception:
            old = None
        n_new, n_old = count(new), count(old) if old is not None else 0
        name = os.path.basename(f)
        if f.endswith("_prices.json") or f == "docs/data/catalog.json":
            if n_old and n_new < n_old * (1 - MAX_DROP):
                errs.append(f"{f}: so mon giam {n_old} -> {n_new} (>{int(MAX_DROP*100)}%)")
            dup = duplicate_ids(new) if f.endswith("_prices.json") else []
            if dup:
                errs.append(f"{f}: {len(dup)} san pham bi LAP nhieu dong (vd {dup[:3]})"
                            " -> 1 mon nhieu gia; sua crawler khoa theo ma san pham")
        elif f == "docs/data/dict.json":
            if n_old and n_new < n_old:
                errs.append(f"{f}: tu dien giam {n_old} -> {n_new} muc")
        elif f == "docs/data/retail.json":
            if n_new < 300:
                errs.append(f"{f}: khuyen mai chi con {n_new} mon (< 300)")
    if errs:
        print("CHAN COMMIT — du lieu bat thuong (giu nguyen ban tren git):")
        for e in errs:
            print("  -", e)
        if os.environ.get("CENA_CHO_PHEP_GIAM") == "1":
            print("CENA_CHO_PHEP_GIAM=1 -> van cho commit (nguoi dung xac nhan giam co chu dich)")
            return 0
        print("Neu giam la THAT (co chu dich): dat CENA_CHO_PHEP_GIAM=1 roi commit lai.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
