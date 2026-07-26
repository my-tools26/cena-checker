# -*- coding: utf-8 -*-
"""Sinh du lieu cho ban WEB TINH (GitHub Pages) tu cac file JSON hien co.

Chay:  python build_static.py            (chi gop du lieu co san, nhanh)
       python build_static.py --retail   (gop + cao lai gia ban le tu kupi.cz)

Ket qua -> docs/data/*.json  (docs/ la thu muc GitHub Pages phuc vu)

Vi sao can: trinh duyet KHONG goi truc tiep kupi.cz duoc (chan CORS), nen gia
ban le phai duoc cao san thanh JSON. Cac catalog ban buon thi gop + nen lai
dang mang compact cho nhe (ten khoa dai -> bo het).
"""
import json
import os
import re
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "data")

# Ma so kho (dung trong file compact de tiet kiem dung luong)
SHOPS = [
    ("tamda", "Tamda Foods"),      # 0 - to roi tuan (gia the)
    ("tamda", "Tamda Foods"),      # 1 - catalog Tamda Express
    ("makro", "Makro"),            # 2
    ("bidfood", "Bidfood"),        # 3
    ("dathang", "dathang.cz"),     # 4
    ("linsan", "Linsan24h"),       # 5
    ("bombacena", "Bombacena"),    # 6
    ("ptt", "PTT Global"),         # 7
    ("jip", "JIP"),                # 8
]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def load(fn):
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ! {fn}: {e}")
        return None


def build_catalog():
    """Gop moi catalog ban buon -> mang compact:
       [ten, gia, quy_cach, ma_kho, so_chiec, ean]"""
    items = []
    srcs = [
        ("tamda_prices.json", 0, None),
        ("tamda_full_prices.json", 1, None),
        ("makro_full_prices.json", 2, None),
        ("bidfood_prices.json", 3, None),
        ("dathang_prices.json", 4, None),
        ("linsan_prices.json", 5, None),
        ("bombacena_prices.json", 6, None),
        ("pttglobal_prices.json", 7, None),
        ("jip_prices.json", 8, None),
    ]
    meta = {}
    for fn, sid, _ in srcs:
        d = load(fn)
        if not d:
            continue
        n0 = len(items)
        for it in d.get("items", []):
            name = (it.get("name") or "").strip()
            price = it.get("price")
            if not name or not price:
                continue
            ean = it.get("ean") or ""
            items.append([name, round(float(price), 2), it.get("amount", "") or "",
                          sid, int(it.get("pack") or 1), ean])
        meta[fn] = {"n": len(items) - n0, "date": d.get("date", ""),
                    "valid": d.get("valid", "")}
        print(f"  {fn:30s} +{len(items)-n0:6d}")

    # gia tu nhap tay (manual_prices.json)
    man = load("manual_prices.json")
    if man:
        slug2id = {"tamda": 1, "makro": 2, "bidfood": 3, "dathang": 4,
                   "linsan": 5, "bombacena": 6, "ptt": 7, "jip": 8}
        for it in man.get("items", []):
            sid = slug2id.get(it.get("slug"), 4)
            items.append([it["name"], round(float(it["price"]), 2),
                          it.get("amount", ""), sid, int(it.get("pack") or 1),
                          it.get("ean", "")])
        print(f"  {'manual_prices.json':30s} +{len(man.get('items', []))}")
    return items, meta


def build_ean_shards(catalog):
    """Chia database ma vach theo 3 so dau -> QUET MA chi tai 1 manh ~20KB
    (khong phai tai ca catalog 1.9MB). Moi manh: {ma: [ten, [[kho,gia,quy_cach,so_chiec],...]]}"""
    db = load("ean_db.json")
    shards = {}
    n = 0
    if db:
        for code, v in db.get("items", {}).items():
            if not code or not code.isdigit():
                continue
            shards.setdefault(code[:3], {})[code] = [v.get("name", ""), []]
            n += 1
    # gan GIA tu catalog vao tung ma (de quet xong thay gia ngay)
    for it in catalog:
        e = it[5]
        if not e or not e.isdigit():
            continue
        rec = shards.setdefault(e[:3], {}).setdefault(e, [it[0], []])
        rec[1].append([it[3], it[1], it[2], it[4]])  # kho, gia, quy cach, so chiec
        if not rec[0]:
            rec[0] = it[0]
    # Chia nho THICH UNG: manh nao qua dong (ma Sec deu bat dau 859) thi tach
    # sau them 1-2 chu so nua, de moi lan quet chi tai vai chuc KB.
    LIMIT = 1500
    MAXLEN = 8
    final = {}

    def split(pref, m):
        """De quy: manh nao > LIMIT thi tach sau them 1 chu so."""
        if len(m) <= LIMIT or len(pref) >= MAXLEN:
            final[pref] = m
            return
        sub = {}
        for code, v in m.items():
            sub.setdefault(code[:len(pref) + 1], {})[code] = v
        if len(sub) <= 1:          # khong tach duoc nua (ma trung nhau)
            final[pref] = m
            return
        for p, mm in sub.items():
            split(p, mm)

    for pref, m in list(shards.items()):
        split(pref, m)

    d = os.path.join(OUT, "ean")
    os.makedirs(d, exist_ok=True)
    for k in os.listdir(d):
        os.remove(os.path.join(d, k))
    for pref, m in final.items():
        with open(os.path.join(d, f"{pref}.json"), "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, separators=(",", ":"))
    # danh sach do dai prefix de trinh duyet biet tai file nao
    with open(os.path.join(d, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(final), f, separators=(",", ":"))
    big = max((len(m) for m in final.values()), default=0)
    print(f"  ean_db -> {len(final)} manh ({n} ma), manh lon nhat {big} ma")
    return len(final)


def build_dict():
    """Tu dien Viet -> Sec tu tudien.xlsx."""
    out = {}
    try:
        import openpyxl
        ws = openpyxl.load_workbook(os.path.join(HERE, "tudien.xlsx"),
                                    read_only=True).active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[2]:
                continue
            cs = strip_accents(str(row[2]).strip())
            for col in (0, 1):
                if row[col]:
                    vi = strip_accents(str(row[col]).strip())
                    if vi and vi != cs:
                        out[vi] = cs
    except Exception as e:
        print(f"  ! tudien: {e}")
    print(f"  tu dien: {len(out)} muc")
    return out


def build_retail():
    """Cao gia khuyen mai ban le tu kupi.cz -> JSON (trinh duyet khong tu goi duoc)."""
    sys.path.insert(0, HERE)
    import cena
    import urllib.parse
    slugs = ["lidl", "kaufland", "billa", "penny-market", "tesco", "albert",
             "globus", "coop", "hruska", "flop", "ratio", "kosik",
             "makro", "jip"]  # them ban buon co deal akce -> hien o trang Akce
    cats = ["ovoce-a-zelenina", "maso-drubez-a-ryby", "mlecne-vyrobky-a-vejce",
            "pecivo", "sladkosti-a-slane-snacky", "pivo", "nealko-napoje",
            "kava", "drogerie", "mazlicci"]
    seen, prods = set(), []

    def add(ps):
        for p in ps:
            key = p["name"] + "|" + p.get("amount", "")
            if key in seen or not p.get("deals"):
                continue
            seen.add(key)
            prods.append([p["name"], p.get("amount", ""),
                          [[d["shop"], round(float(d["price"]), 2),
                            d.get("unit", ""), d.get("pct", ""), d.get("valid", "")]
                           for d in p["deals"]]])

    for slug in cats + slugs:
        # kupi dung chung duong dan /slevy/<slug> cho CA nhom hang lan sieu thi
        url = f"{cena.BASE}/slevy/{slug}"
        try:
            add(cena.parse_groups(cena.fetch(url)))
            print(f"  kupi/{slug:24s} tong {len(prods)}")
        except Exception as e:
            print(f"  ! kupi/{slug}: {e}")
        time.sleep(0.6)
    # them cac mat hang thiet yeu (tim theo tu khoa)
    from app import STAPLES_ALL
    for _lbl, q, _u in STAPLES_ALL:
        try:
            add(cena.parse_groups(cena.fetch(
                f"{cena.BASE}/hledej?f={urllib.parse.quote(q)}")))
        except Exception:
            pass
        time.sleep(0.5)
    # Tamda to roi (nguon da cao san) -> gop vao Akce, uu tien truoc kupi
    td = load("tamda_prices.json")
    if td:
        n0 = len(prods)
        for it in td.get("items", []):
            nm = (it.get("name") or "").strip()
            if not nm or not it.get("price"):
                continue
            key = nm + "|" + (it.get("amount", "") or "")
            if key in seen:
                continue
            seen.add(key)
            prods.append([nm, it.get("amount", "") or "",
                          [["Tamda Foods", round(float(it["price"]), 2),
                            it.get("unit", "") or "", "", td.get("valid", "") or ""]]])
        print(f"  tamda to roi              +{len(prods) - n0}")
    print(f"  ban le: {len(prods)} mat hang")
    return prods


def main():
    os.makedirs(OUT, exist_ok=True)
    print("== Gop catalog ban buon ==")
    catalog, meta = build_catalog()
    with open(os.path.join(OUT, "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  TONG: {len(catalog)} mat hang")

    print("== Ma vach ==")
    build_ean_shards(catalog)

    print("== Tu dien ==")
    with open(os.path.join(OUT, "dict.json"), "w", encoding="utf-8") as f:
        json.dump(build_dict(), f, ensure_ascii=False, separators=(",", ":"))

    if "--retail" in sys.argv:
        print("== Gia ban le (kupi.cz) ==")
        retail = build_retail()
        with open(os.path.join(OUT, "retail.json"), "w", encoding="utf-8") as f:
            json.dump({"date": time.strftime("%Y-%m-%d"), "items": retail},
                      f, ensure_ascii=False, separators=(",", ":"))

    # thong tin chung cho trang web
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"built": time.strftime("%Y-%m-%d %H:%M"),
                   "shops": [s[1] for s in SHOPS], "sources": meta},
                  f, ensure_ascii=False)

    print("\nXONG. Dung luong docs/data:")
    tot = 0
    for root, _d, files in os.walk(OUT):
        for fn in files:
            tot += os.path.getsize(os.path.join(root, fn))
    print(f"  {tot/1048576:.1f} MB")


if __name__ == "__main__":
    main()
