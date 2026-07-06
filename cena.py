# -*- coding: utf-8 -*-
"""
Cena Checker - so sanh gia sieu thi Sec (du lieu tu kupi.cz)

Cach dung:
  python cena.py hledej banany          # tim gia re nhat cho 1 mat hang
  python cena.py deals                  # goi y top khuyen mai theo nhom hang
  python cena.py deals --top 5          # so deal moi nhom
  python cena.py deals --cat pivo       # chi 1 nhom
"""
import argparse
import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

BASE = "https://www.kupi.cz"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) cena-checker/1.0 (personal use)"}
DELAY = 2  # giay giua cac request - lich su voi server

# Cac nhom hang cho che do "deals" (slug tren kupi.cz)
CATEGORIES = {
    "banh keo / snack": "sladkosti-a-slane-snacky",
    "drogerie": "drogerie",
    "pivo (lon + chai)": "pivo",
    "do cho cho meo": "mazlicci",
    "banh mi / pecivo": "pecivo",
    "sua & trung": "mlecne-vyrobky-a-vejce",
    "rau cu qua": "ovoce-a-zelenina",
}

# Ngoai le: khong goi y ruou manh
LIQUOR_RE = re.compile(
    r"vodka|rum\b|tuzem|whisk|gin\b|lik[ée]r|brandy|co[gn]nac|slivovic|fernet|"
    r"becherovka|absinth|tequila|jager|griotka|metaxa|bourbon|destil",
    re.IGNORECASE,
)


def strip_accents(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")  # chu d gach tieng Viet khong nam trong NFD
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def parse_price(s: str):
    m = re.search(r"([\d\s]+[,.]?\d*)", s.replace("\xa0", " "))
    if not m:
        return None
    return float(m.group(1).replace(" ", "").replace(",", "."))


def parse_groups(soup: BeautifulSoup):
    """Tra ve list san pham: {name, amount, deals:[{shop, price, unit, pct, valid}]}"""
    products = []
    for group in soup.select("div.group_discounts"):
        name_el = group.select_one(".product_name h2 strong")
        if not name_el:
            continue
        name = clean(name_el.get_text())
        amount_el = group.select_one(".product_name h2 .nowrap")
        amount = clean(amount_el.get_text()) if amount_el else ""

        deals, seen = [], set()
        for row in group.select("div.discount_row"):
            did = row.get("data-discount")
            if did in seen:
                continue
            seen.add(did)
            shop_el = row.select_one(".discounts_shop_name span")
            price_el = row.select_one(".discount_price_value")
            if not shop_el or not price_el:
                continue
            unit_el = row.select_one(".price_per_unit")
            pct_el = row.select_one(".discount_percentage")
            valid_el = row.select_one(".discounts_validity")
            price = parse_price(price_el.get_text())
            if price is None:
                continue
            deals.append({
                "shop": clean(shop_el.get_text()),
                "price": price,
                "unit": clean(unit_el.get_text()) if unit_el else "",
                "pct": clean(pct_el.get_text()) if pct_el else "",
                "valid": clean(valid_el.get_text()) if valid_el else "",
            })
        if deals:
            deals.sort(key=lambda d: d["price"])
            products.append({"name": name, "amount": amount, "deals": deals})
    return products


def print_product(p, max_shops=6):
    print(f"\n=== {p['name']} {p['amount']} ===")
    for i, d in enumerate(p["deals"][:max_shops]):
        star = " <-- RE NHAT" if i == 0 else ""
        pct = f" ({d['pct']})" if d["pct"] else ""
        unit = f" | {d['unit']}" if d["unit"] else ""
        print(f"  {d['price']:>8.2f} Kc  {d['shop']:<22}{pct}{unit} | {d['valid']}{star}")


def cmd_hledej(query: str, limit: int):
    q = strip_accents(query)
    soup = fetch(f"{BASE}/hledej?f={requests.utils.quote(q)}")
    products = parse_groups(soup)
    if not products:
        print(f"Khong tim thay '{query}' tren kupi.cz")
        return
    print(f"Ket qua cho '{query}' ({len(products)} san pham, hien {min(limit, len(products))}):")
    for p in products[:limit]:
        print_product(p)


def cmd_deals(top: int, only_cat: str | None):
    for label, slug in CATEGORIES.items():
        if only_cat and only_cat.lower() not in (label.lower(), slug):
            continue
        print(f"\n{'#' * 60}\n##  {label.upper()}  (kupi.cz/slevy/{slug})\n{'#' * 60}")
        try:
            soup = fetch(f"{BASE}/slevy/{slug}")
        except Exception as e:
            print(f"  Loi tai nhom nay: {e}")
            continue
        products = parse_groups(soup)

        def best_pct(p):
            for d in p["deals"]:
                m = re.search(r"(\d+)", d["pct"])
                if m:
                    return int(m.group(1))
            return 0

        # Uu tien giam gia sau nhat
        products.sort(key=best_pct, reverse=True)
        for p in products[:top]:
            print_product(p, max_shops=3)
        time.sleep(DELAY)


def collect_all(top: int):
    """Thu thap deal tat ca cac nhom -> dict {label: [products]}"""
    data = {}
    for label, slug in CATEGORIES.items():
        try:
            soup = fetch(f"{BASE}/slevy/{slug}")
        except Exception:
            data[label] = []
            continue
        products = parse_groups(soup)

        def best_pct(p):
            for d in p["deals"]:
                m = re.search(r"(\d+)", d["pct"])
                if m:
                    return int(m.group(1))
            return 0

        products.sort(key=best_pct, reverse=True)
        data[label] = products[:top]
        time.sleep(DELAY)
    return data


def cmd_report(top: int):
    import datetime
    import html as H
    import os

    print("Dang thu thap du lieu tat ca cac nhom hang, cho khoang 20 giay...")
    data = collect_all(top)
    today = datetime.date.today().strftime("%d.%m.%Y")

    rows_html = []
    for label, products in data.items():
        rows_html.append(f'<h2>{H.escape(label.upper())}</h2>')
        if not products:
            rows_html.append("<p>Khong tai duoc nhom nay.</p>")
            continue
        rows_html.append('<table><tr><th>San pham</th><th>Gia re nhat</th>'
                         '<th>Sieu thi</th><th>Giam</th><th>Gia don vi</th><th>Han</th><th>Noi khac</th></tr>')
        for p in products:
            best = p["deals"][0]
            others = ", ".join(
                f'{d["shop"]} {d["price"]:.2f} Kč' for d in p["deals"][1:4]
            ) or "—"
            rows_html.append(
                "<tr>"
                f'<td class="n">{H.escape(p["name"])} <span class="a">{H.escape(p["amount"])}</span></td>'
                f'<td class="p">{best["price"]:.2f} Kč</td>'
                f'<td class="s">{H.escape(best["shop"])}</td>'
                f'<td class="d">{H.escape(best["pct"]) or "—"}</td>'
                f'<td>{H.escape(best["unit"]) or "—"}</td>'
                f'<td>{H.escape(best["valid"])}</td>'
                f'<td class="o">{H.escape(others)}</td>'
                "</tr>"
            )
        rows_html.append("</table>")

    page = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<title>Bao cao deal sieu thi Sec - {today}</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;max-width:1100px;margin:20px auto;padding:0 16px;background:#f7f7f5;color:#222}}
 h1{{color:#1a7a3a}} h2{{background:#1a7a3a;color:#fff;padding:8px 12px;border-radius:6px;margin-top:32px}}
 table{{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
 th{{background:#e8f3ec;text-align:left;padding:8px}} td{{padding:8px;border-top:1px solid #eee;vertical-align:top}}
 .p{{font-weight:bold;color:#c0392b;white-space:nowrap}} .s{{font-weight:bold}}
 .d{{color:#1a7a3a;font-weight:bold;white-space:nowrap}} .a{{color:#888;font-size:.9em}}
 .o{{color:#777;font-size:.85em}} .n{{max-width:260px}}
 footer{{margin:24px 0;color:#999;font-size:.85em}}
</style></head><body>
<h1>🛒 Deal siêu thị Séc — {today}</h1>
<p>Top {top} khuyến mãi mỗi nhóm hàng (giảm giá sâu nhất trước). Nguồn: kupi.cz. Đã loại rượu mạnh.</p>
{''.join(rows_html)}
<footer>Tạo bởi cena-checker — dùng cá nhân.</footer>
</body></html>"""

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bao-cao-tuan.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Da luu bao cao: {out}")
    os.startfile(out)


def main():
    ap = argparse.ArgumentParser(description="So sanh gia sieu thi Sec (kupi.cz)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("hledej", help="Tim gia mot mat hang")
    h.add_argument("query", nargs="+")
    h.add_argument("--limit", type=int, default=5, help="So san pham hien thi")

    d = sub.add_parser("deals", help="Goi y top khuyen mai theo nhom hang")
    d.add_argument("--top", type=int, default=10, help="So deal moi nhom (mac dinh 10)")
    d.add_argument("--cat", help="Chi mot nhom (vd: pivo, drogerie, mazlicci)")

    r = sub.add_parser("report", help="Xuat bao cao HTML tong hop, mo trong trinh duyet")
    r.add_argument("--top", type=int, default=10)

    args = ap.parse_args()
    if args.cmd == "hledej":
        cmd_hledej(" ".join(args.query), args.limit)
    elif args.cmd == "report":
        cmd_report(args.top)
    else:
        cmd_deals(args.top, args.cat)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
