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
    ("tamda", "Tamda Foods"),      # 0 - to roi + catalog gop chung
    ("makro", "Makro"),            # 1
    ("bidfood", "Bidfood"),        # 2
    ("dathang", "dathang.cz"),     # 3
    ("linsan", "Linsan24h"),       # 4
    ("bombacena", "Bombacena"),    # 5
    ("ptt", "PTT Global"),         # 6
    ("jip", "JIP"),                # 7
]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def norm_amt(s):
    """'330 ml' va '0,33 l' -> cung mot chuoi. Dung de so khop dung tich."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|ks)\b", strip_accents(s))
    if not m:
        return ""
    n = float(m.group(1).replace(",", ".")); u = m.group(2)
    if u == "g": n /= 1000; u = "kg"
    if u == "ml": n /= 1000; u = "l"
    return f"{round(n, 4)}{u}"


# tu chi BIEN THE (mui vi/loai) - khi khop theo ten, 2 ben phai giong nhau de
# khong ghep nham (vd ban Zero vs ban thuong).
VARIANT_WORDS = ("zero", "light", "cherry", "vanilla", "lemon", "lime", "free",
                 "diet", "max", "sprite", "fanta", "pomeranc", "citron", "jahoda",
                 "bez cukru")


def _brand_toks(name):
    return [t for t in re.split(r"[^a-z0-9]+", strip_accents(name))
            if len(t) >= 3 and not t.isdigit()]


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
        ("tamda_full_prices.json", 0, None),
        ("makro_full_prices.json", 1, None),
        ("bidfood_prices.json", 2, None),
        ("dathang_prices.json", 3, None),
        ("linsan_prices.json", 4, None),
        ("bombacena_prices.json", 5, None),
        ("pttglobal_prices.json", 6, None),
        ("jip_prices.json", 7, None),
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
        slug2id = {"tamda": 0, "makro": 1, "bidfood": 2, "dathang": 3,
                   "linsan": 4, "bombacena": 5, "ptt": 6, "jip": 7}
        for it in man.get("items", []):
            sid = slug2id.get(it.get("slug"), 4)
            items.append([it["name"], round(float(it["price"]), 2),
                          it.get("amount", ""), sid, int(it.get("pack") or 1),
                          it.get("ean", "")])
        print(f"  {'manual_prices.json':30s} +{len(man.get('items', []))}")

    # TRON DEU cac kho theo vong tron: neu de nguyen thu tu file nguon thi trang 1
    # cua /banbuon toan Tamda, con Makro/JIP nam tan hang tram-nghin trang sau.
    # Gom theo SLUG (Tamda co 2 nguon 0+1 -> chung 1 suat).
    buckets = {}
    for it in items:
        buckets.setdefault(SHOPS[it[3]][0], []).append(it)
    order = sorted(buckets, key=lambda k: -len(buckets[k]))
    mixed, idx = [], 0
    while len(mixed) < len(items):
        placed = False
        for slug in order:
            b = buckets[slug]
            if idx < len(b):
                mixed.append(b[idx])
                placed = True
        if not placed:
            break
        idx += 1
    print("  tron deu: " + ", ".join(f"{s}={len(buckets[s])}" for s in order))
    return mixed, meta


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
    # === GHEP GIA cho ma CHI CO TEN (chua gan gia) ===
    # ~49% ma chi co ten (Luigi's Box, hoac kho khong ghi ma vach trong bang gia).
    # Ghep theo THUONG HIEU (tu dau) + DUNG TICH, chan nham bien the -> quet ra
    # gia ngay. Danh dau rec[2]=1 = "suy theo ten" (khong phai trung ma vach that).
    idx = {}
    for it in catalog:
        amt = norm_amt(it[2]) or norm_amt(it[0])
        if not amt:
            continue
        tk = _brand_toks(it[0])
        if not tk:
            continue
        idx.setdefault((tk[0], amt), []).append(it)
    enriched = 0
    for m in shards.values():
        for code, rec in m.items():
            if rec[1] or not rec[0]:
                continue
            amt = norm_amt(rec[0])
            tk = _brand_toks(rec[0])
            if not amt or not tk:
                continue
            cand = idx.get((tk[0], amt))
            if not cand:
                continue
            nm = strip_accents(rec[0])
            my_vars = frozenset(w for w in VARIANT_WORDS if w in nm)
            best = {}
            for it in cand:
                cn = strip_accents(it[0])
                if frozenset(w for w in VARIANT_WORDS if w in cn) != my_vars:
                    continue
                cur = best.get(it[3])
                if cur is None or it[1] < cur[1]:
                    best[it[3]] = [it[3], it[1], it[2], it[4]]
            if best:
                rec[1] = list(best.values())
                rec.append(1)          # danh dau: gia suy theo ten
                enriched += 1
    print(f"  ghep gia theo ten cho {enriched} ma chi co ten")

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
    # Danh sach prefix de trinh duyet biet tai manh nao.
    # KHONG dat ten bat dau bang "_": GitHub Pages chay Jekyll va Jekyll BO QUA
    # moi file/thu muc bat dau bang gach duoi -> file bi 404 -> quet ma vach hong.
    with open(os.path.join(d, "shards.json"), "w", encoding="utf-8") as f:
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

    def canon_shop(s):
        """kupi ghi 'TAMDA FOODS', to roi ghi 'Tamda Foods' -> cung 1 sieu thi."""
        return "Tamda Foods" if strip_accents(s).startswith("tamda") else s

    def add(ps):
        for p in ps:
            key = p["name"] + "|" + p.get("amount", "")
            if key in seen or not p.get("deals"):
                continue
            seen.add(key)
            prods.append([p["name"], p.get("amount", ""),
                          [[canon_shop(d["shop"]), round(float(d["price"]), 2),
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
