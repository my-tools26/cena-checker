# -*- coding: utf-8 -*-
"""Thu thap EAN + ten mat hang tu e-shop JIP (jip-eshop.cz) qua API Luigi's Box.

Chay:  python thu_gtin_jip.py
Quet tu khoa a-z, 0-9 va ky tu tieng Sec, khu trung lap theo productID.
Ket qua gop vao ean_db.json (source=jip).
"""
import json
import os
import re
import string
import time

import requests

LB = "https://live.luigisbox.com/search"
TRACKER = "545544-1030761"
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ean_db.json")
QUERIES = list(string.ascii_lowercase) + list(string.digits) + \
    list("áčďéěíňóřšťúůýž") + ["ch"]


def load_db():
    with open(DB, encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    tmp = DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DB)


def lb_page(q, page):
    for attempt in range(3):
        try:
            r = requests.get(LB, params={
                "tracker_id": TRACKER, "q": q, "size": 200, "page": page}, timeout=45)
            if r.status_code == 200:
                return r.json().get("results", {})
            print(f"  q={q} p={page}: HTTP {r.status_code}")
            return {}
        except Exception as e:
            print(f"  q={q} p={page}: {e}, cho 15s")
            time.sleep(15)
    return {}


def main():
    db = load_db()
    seen = set()
    new = 0
    for q in QUERIES:
        page = 1
        got_q = 0
        while True:
            res = lb_page(q, page)
            hits = res.get("hits") or []
            if not hits:
                break
            for h in hits:
                a = h.get("attributes", {})
                pid = (a.get("productID") or [h.get("url")])[0]
                if pid in seen:
                    continue
                seen.add(pid)
                got_q += 1
                title = a.get("title")
                if isinstance(title, list):
                    title = title[0] if title else None
                for field in (a.get("ean") or []):
                    for e in re.findall(r"\d{8,14}", str(field)):
                        if e not in db["items"] and title:
                            db["items"][e] = {"name": title, "source": "jip"}
                            new += 1
            total = res.get("total_hits") or 0
            if page * 200 >= total or page >= 50:
                break
            page += 1
            time.sleep(0.4)
        save_db(db)
        print(f"[q={q}] +{got_q} sp moi | tong sp {len(seen)} | db {len(db['items'])} GTIN (+{new})")
        time.sleep(0.4)
    print(f"XONG jip: {len(seen)} san pham, db co {len(db['items'])} GTIN, them moi {new}")


if __name__ == "__main__":
    main()
