# -*- coding: utf-8 -*-
"""Khop san pham dathang.cz (khong co ma vach) voi EAN that.

CHIEN LUOC (sau lo thu 200 + Milky Way):
  - Nguon ung vien = TAT CA ma vach that tu 5 catalog da co EAN san
    (Tamda / Makro / PTT / Linsan / JIP, ~85k ma), KHONG chi Makro.
  - Cham diem uu tien THUONG HIEU: chi token "dac trung" (hiem, IDF cao) moi
    duoc tinh -> chan tu chung ("cokoladovy", "napoj"...) bam nham.
  - BAT BUOC cung dung tich + bien the giong nhau (Milky Way vs Duo).
  - Khong dung so anh: da chung minh pHash/histogram thua voi 2 anh chup khac
    nhau (cung SP van diem <= doi chung). Anh -> de duyet tay.

Chay:  python match_dathang.py --limit 200
Ket qua: _match_out/report.html  (mat thuong kiem tra) + candidates.json
"""
import argparse
import html as H
import json
import math
import os
import re
import time
import unicodedata
from collections import defaultdict

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_match_out")
os.makedirs(OUT, exist_ok=True)

UA = {"User-Agent": "CenaChecker/1.0 (personal, price-compare for VN community in CZ)"}
DATHANG_API = "https://www.dathang.cz/wp-json/wc/store/v1/products"

# 5 nguon da co EAN san -> lam kho ung vien.  (sid de biet EAN tu dau)
CATALOG_SRCS = [
    ("tamda_full_prices.json", "Tamda"),
    ("makro_full_prices.json", "Makro"),
    ("pttglobal_prices.json", "PTT"),
    ("linsan_prices.json", "Linsan"),
    ("jip_prices.json", "JIP"),
]

STOP = {"kart", "bal", "krt", "the", "pro", "bez", "cca", "set", "kus", "kusu",
        "and", "with", "new", "mix", "ks", "bpo", "vyr", "orig"}
VARIANT = {"zero", "light", "duo", "max", "cherry", "vanilla", "vanilka",
           "lemon", "citron", "jahoda", "bily", "cerny", "free", "diet",
           "original", "salt", "ice"}


def strip_accents(s):
    s = (s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def clean(s):
    return H.unescape(re.sub(r"\s+", " ", s or "")).strip()


def norm_size(s):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|ks)\b", strip_accents(s))
    if not m:
        return ""
    n = float(m.group(1).replace(",", ".")); u = m.group(2)
    if u == "g": n /= 1000; u = "kg"
    if u == "ml": n /= 1000; u = "l"
    return f"{round(n, 4)}{u}"


def tokens(name):
    out = []
    for t in re.split(r"[^a-z0-9]+", strip_accents(name)):
        if len(t) < 3 or t.isdigit() or t in STOP:
            continue
        if re.fullmatch(r"\d+[a-z]*", t):      # 350g, 6ks, 24bal
            continue
        out.append(t)
    return out


def variants_of(name):
    n = strip_accents(name)
    return frozenset(w for w in VARIANT if w in n)


# ---------------- nap ung vien tu 5 catalog co EAN ----------------
def load_candidates():
    cands = {}     # ean -> {name, size, toks(set), vars, src}
    for fn, src in CATALOG_SRCS:
        p = os.path.join(HERE, fn)
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        for it in d.get("items", []):
            ean = (it.get("ean") or "").strip()
            if not ean.isdigit() or len(ean) < 8:
                continue
            if ean in cands:
                continue
            nm = it.get("name", "")
            ordered = tokens(nm)
            if not ordered:
                continue
            cands[ean] = {"name": nm, "size": norm_size(it.get("amount") or nm),
                          "toks": set(ordered), "first": ordered[0],
                          "vars": variants_of(nm), "src": src}
    return cands


def build_index(cands):
    tok2ean = defaultdict(set)
    first_count = defaultdict(int)
    for ean, c in cands.items():
        for t in c["toks"]:
            tok2ean[t].add(ean)
        first_count[c["first"]] += 1
    N = len(cands)
    idf = {t: math.log(N / len(s)) for t, s in tok2ean.items()}
    df = {t: len(s) for t, s in tok2ean.items()}
    distinctive = {t for t, c in df.items() if c <= max(3, int(N * 0.0025))}
    # THUONG HIEU = token thuong DUNG DAU ten nha cung cap (Makro/Tamda ghi brand
    # dau tien). Loc theo ty le "lam token dau" >= 35% -> chan tu ta/mui vi.
    brand = {t for t in tok2ean
             if len(t) >= 4 and first_count.get(t, 0) >= 2
             and first_count.get(t, 0) / df[t] >= 0.35}
    return {"tok2ean": tok2ean, "idf": idf, "distinctive": distinctive,
            "brand": brand, "N": N}


def match_one(name, amount, cands, idx, topk=4):
    tok2ean, idf = idx["tok2ean"], idx["idf"]
    distinctive, brand = idx["distinctive"], idx["brand"]
    tks = set(tokens(name))
    sz = norm_size(amount) or norm_size(name)
    myvars = variants_of(name)
    my_brand = tks & brand
    my_distinct = tks & distinctive

    scores = defaultdict(float)
    shared = defaultdict(list)
    sh_brand = defaultdict(list)
    for t in tks:
        w = idf.get(t, 0)
        for ean in tok2ean.get(t, ()):
            scores[ean] += w
            if t in distinctive:
                shared[ean].append(t)
            if t in brand:
                sh_brand[ean].append(t)

    ranked = []
    for ean, sc in scores.items():
        c = cands[ean]
        # (1) PHAI chia se it nhat 1 THUONG HIEU that (khong phai tu chung/mui vi)
        if not sh_brand.get(ean):
            continue
        # (2) cung size (neu ca hai deu ghi)
        if sz and c["size"] and sz != c["size"]:
            continue
        # (3) bien the khong duoc mau thuan
        if myvars and c["vars"] and not (myvars & c["vars"]):
            continue
        # (4) XUNG DOT MUI VI: ca hai ben deu co 1 tu dac trung ma ben kia khong co
        #     (vd Haribo LEMONADE vs COLA, Kotanyi PEPR vs ANYZ) -> danh dau
        cand_distinct = c["toks"] & distinctive
        conflict = bool(my_distinct - cand_distinct) and bool(cand_distinct - my_distinct)
        ranked.append((ean, round(sc, 3), shared[ean], sh_brand[ean], conflict))
    ranked.sort(key=lambda x: -x[1])
    return ranked[:topk], sz, sorted(my_brand)


# ---------------- tai dathang ----------------
def fetch_dathang(limit, force_ids=()):
    prods, page, seen = [], 1, set()
    while len(prods) < limit:
        r = requests.get(DATHANG_API, params={"per_page": 100, "page": page},
                         headers=UA, timeout=45)
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        for p in data:
            imgs = p.get("images") or []
            prods.append({"id": p.get("id"), "name": clean(p.get("name")),
                          "amount": "", "img": imgs[0].get("src") if imgs else "",
                          "price": (p.get("prices") or {}).get("price")})
            seen.add(p.get("id"))
        page += 1
        time.sleep(0.3)
    prods = prods[:limit]
    for fid in force_ids:
        if any(x["id"] == fid for x in prods):
            continue
        r = requests.get(f"{DATHANG_API}/{fid}", headers=UA, timeout=45)
        if r.status_code == 200:
            p = r.json()
            imgs = p.get("images") or []
            prods.append({"id": p.get("id"), "name": clean(p.get("name")),
                          "amount": "", "img": imgs[0].get("src") if imgs else "",
                          "price": (p.get("prices") or {}).get("price"), "_forced": True})
    return prods


CLEAR_MIN = 8.0     # diem toi thieu de coi la "ro rang"
DOMINATE = 1.3      # top phai vuot troi hon nhi bao nhieu lan
STRONG_SCORE = 12.0  # 1 tu dac trung van chap nhan neu diem >= muc nay


def is_clear(cand):
    """cand[0] = (ean, score, shared_distinctive, shared_brand, conflict)."""
    top = cand[0][1]
    second = cand[1][1] if len(cand) > 1 else 0
    if cand[0][4]:                       # xung dot mui vi -> khong ro rang
        return False
    if top < CLEAR_MIN or top < second * DOMINATE:
        return False
    # can 2 tu dac trung khop, HOAC 1 tu nhung diem cao han han (chan Haribo-dao-cat-banh)
    return len(cand[0][2]) >= 2 or top >= STRONG_SCORE


def run(limit, force_ids):
    print("[1/3] Nap ung vien tu 5 catalog co EAN ...")
    cands = load_candidates()
    idx = build_index(cands)
    print(f"      {idx['N']} ma vach · {len(idx['brand'])} token thuong-hieu")

    print(f"[2/3] Tai {limit} san pham dathang ...")
    prods = fetch_dathang(limit, force_ids)
    print(f"      {len(prods)} san pham")

    print("[3/3] Khop ten ...")
    rows = []
    clear = ambig = none = 0
    for p in prods:
        cand, sz, mydist = match_one(p["name"], p["amount"], cands, idx)
        decision, chosen = "none", None
        if cand:
            if is_clear(cand):
                decision, chosen = "clear", cand[0][0]; clear += 1
            else:
                decision = "review"; ambig += 1
        else:
            none += 1
        rows.append({"id": p["id"], "name": p["name"], "img": p["img"],
                     "price": p["price"], "size": sz, "mydist": mydist,
                     "forced": p.get("_forced", False), "decision": decision,
                     "chosen": chosen,
                     "cands": [{"ean": e, "score": s, "shared": shb,
                                "name": cands[e]["name"], "src": cands[e]["src"],
                                "size": cands[e]["size"]} for e, s, sh, shb, cf in cand]})

    with open(os.path.join(OUT, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    write_html(rows, {"clear": clear, "review": ambig, "none": none, "total": len(rows)})

    print("XONG.")
    print(f"  Ro rang (auto)  : {clear}")
    print(f"  Map mo (duyet)  : {ambig}")
    print(f"  Khong ung vien  : {none}")
    print(f"  -> {os.path.join(OUT, 'report.html')}")
    # in nhanh vai ket qua ro rang de xem chat luong ngay
    print("\n  === Mau 'ro rang' ===")
    shown = 0
    for r in rows:
        if r["decision"] == "clear":
            c = r["cands"][0]
            print(f"   [{c['src']}] {r['name'][:42]:42s} -> {c['ean']} {c['name'][:38]} (diem {c['score']})")
            shown += 1
            if shown >= 15:
                break


def write_html(rows, stats):
    badge = {"clear": ("#0F6E3B", "RÕ RÀNG"), "review": ("#9A6A00", "DUYỆT TAY"),
             "none": ("#999", "KHÔNG CÓ")}
    out = ["""<!doctype html><meta charset=utf-8><title>Khớp dathang → EAN</title>
<style>body{font-family:system-ui,Arial;margin:20px;color:#222}
.row{border:1px solid #e3e3e3;border-radius:8px;padding:10px;margin:9px 0;display:flex;gap:14px}
.row img.main{width:90px;height:90px;object-fit:contain;border:1px solid #ccc;border-radius:6px;background:#fff}
.b{color:#fff;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600}
h1{font-size:20px}.st{background:#f5f5f5;padding:10px;border-radius:8px;display:inline-block}
.forced{outline:3px solid #ffcf33}.c{font-size:12.5px;margin:2px 0;padding:3px 6px;border-radius:5px;background:#fafafa}
.win{background:#eafbef}.src{color:#0b5cad;font-weight:600}.sh{color:#0F6E3B}</style>"""]
    out.append(f"<h1>Khớp dathang → EAN — lô thử {stats['total']} món</h1>")
    out.append(f"<p class=st>✅ rõ ràng (auto): <b>{stats['clear']}</b> &nbsp;|&nbsp; "
               f"✋ duyệt tay: <b>{stats['review']}</b> &nbsp;|&nbsp; "
               f"∅ không ứng viên: <b>{stats['none']}</b></p>")
    order = {"clear": 0, "review": 1, "none": 2}
    for r in sorted(rows, key=lambda r: (not r["forced"], order[r["decision"]])):
        col, lbl = badge[r["decision"]]
        main = (f"<img class=main src='{H.escape(r['img'])}'>" if r["img"]
                else "<div style='width:90px;color:#ccc;font-size:11px'>ko ảnh</div>")
        cds = ""
        for i, c in enumerate(r["cands"]):
            sh = " ".join(c["shared"])
            cds += (f"<div class='c{' win' if c['ean']==r['chosen'] else ''}'>"
                    f"<span class=src>{c['src']}</span> "
                    f"<code>{c['ean']}</code> · {H.escape(c['name'][:60])} "
                    f"<span style='color:#888'>[{c['size'] or '?'}]</span> · "
                    f"điểm {c['score']} · <span class=sh>{H.escape(sh)}</span></div>")
        cls = "row forced" if r["forced"] else "row"
        out.append(f"<div class='{cls}'>{main}<div style='flex:1'>"
                   f"<span class=b style='background:{col}'>{lbl}</span> "
                   f"<b>{H.escape(r['name'])}</b> "
                   f"<span style='color:#888'>· size {r['size'] or '?'} · thương hiệu: "
                   f"{H.escape(' '.join(r['mydist']) or '—')}</span>"
                   f"{' <b style=color:#c90>[MILKY WAY test]</b>' if r['forced'] else ''}"
                   f"{cds or '<div class=c style=color:#bbb>— không tìm được ứng viên nào —</div>'}"
                   f"</div></div>")
    with open(os.path.join(OUT, "report.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def _norm_name(s):
    """Chuan hoa ten de map tay khop du lech dau/khoang trang/gach ngang."""
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(s)).strip()


def load_manual_map():
    """dathang_ean_map.json: {"map": {ten dathang: ean}} - uu tien hon auto-match.
    Nguoi dung tu them khi biet EAN (vd hang doc quyen khong NCC nao khac ban)."""
    p = os.path.join(HERE, "dathang_ean_map.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    return {_norm_name(k): str(v).strip() for k, v in d.get("map", {}).items() if v}


def apply_to_file():
    """Khop TOAN BO dathang_prices.json -> gan 'ean' cho nhom RO RANG, ghi lai file."""
    print("[1/3] Nap ung vien tu 5 catalog co EAN ...")
    cands = load_candidates()
    idx = build_index(cands)
    print(f"      {idx['N']} ma vach · {len(idx['brand'])} token thuong-hieu")

    manual = load_manual_map()
    path = os.path.join(HERE, "dathang_prices.json")
    data = json.load(open(path, encoding="utf-8"))
    items = data.get("items", [])
    print(f"[2/3] Khop {len(items)} mon (co {len(manual)} map tay) ...")

    clear = review = none = man = 0
    report = []
    for it in items:
        it.pop("ean", None)               # xoa ean cu (chay lai sach se)
        # MAP TAY uu tien tuyet doi
        mk = _norm_name(it.get("name", ""))
        if mk in manual:
            it["ean"] = manual[mk]; man += 1
            report.append({"name": it["name"], "ean": manual[mk], "src": "TAY",
                           "cand": "(map thủ công)", "score": 999})
            continue
        cand, sz, mydist = match_one(it.get("name", ""), it.get("amount", ""),
                                     cands, idx)
        decision, chosen = "none", None
        if cand:
            if is_clear(cand):
                it["ean"] = cand[0][0]
                decision, chosen = "clear", cand[0][0]; clear += 1
            else:
                decision = "review"; review += 1
        else:
            none += 1
        if decision == "clear":
            c0 = cands[chosen]
            report.append({"name": it["name"], "ean": chosen, "src": c0["src"],
                           "cand": c0["name"], "score": cand[0][1]})

    # sao luu + ghi lai (git van revert duoc)
    json.dump(data, open(path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(report, open(os.path.join(OUT, "applied_clear.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    _write_apply_html(report, {"clear": clear, "review": review,
                               "none": none, "total": len(items)})
    print("[3/3] Da ghi ean vao dathang_prices.json")
    print(f"  Map tay (uu tien)   : {man}")
    print(f"  Ro rang (da gan EAN): {clear}")
    print(f"  Map mo (bo trong)   : {review}")
    print(f"  Khong ung vien      : {none}")
    print(f"  -> soi lai: {os.path.join(OUT, 'applied.html')}")


def _write_apply_html(report, stats):
    out = ["""<!doctype html><meta charset=utf-8><title>dathang đã gắn EAN</title>
<style>body{font-family:system-ui,Arial;margin:20px;color:#222}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #e3e3e3;padding:5px 8px;font-size:13px;text-align:left}
th{background:#f5f5f5}.src{color:#0b5cad;font-weight:600}h1{font-size:20px}
tr:hover{background:#fafafa}code{color:#0F6E3B}</style>"""]
    out.append(f"<h1>dathang đã gắn EAN — {stats['clear']} món rõ ràng "
               f"(map mờ {stats['review']}, không có {stats['none']}, tổng {stats['total']})</h1>")
    out.append("<table><tr><th>#</th><th>Tên dathang</th><th>EAN</th><th>Nguồn</th>"
               "<th>Khớp với</th><th>Điểm</th></tr>")
    for i, r in enumerate(sorted(report, key=lambda x: -x["score"]), 1):
        out.append(f"<tr><td>{i}</td><td>{H.escape(r['name'][:70])}</td>"
                   f"<td><code>{r['ean']}</code></td><td class=src>{r['src']}</td>"
                   f"<td>{H.escape(r['cand'][:70])}</td><td>{r['score']}</td></tr>")
    out.append("</table>")
    open(os.path.join(OUT, "applied.html"), "w", encoding="utf-8").write("\n".join(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--force", default="18871")
    ap.add_argument("--apply", action="store_true",
                    help="Khop toan bo dathang_prices.json va ghi ean vao file")
    args = ap.parse_args()
    if args.apply:
        apply_to_file()
    else:
        fids = [int(x) for x in args.force.split(",") if x.strip().isdigit()]
        run(args.limit, fids)
