# -*- coding: utf-8 -*-
"""Giao dien web don gian cho Cena Checker - chay tren may, mo trong trinh duyet."""
import html as H
import os
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cena

PORT = int(__import__("os").environ.get("PORT", 8765))  # Render/hosting tu cap PORT
# Che do CONG KHAI (chay tren server cho nhieu nguoi dung):
#   set CENA_PUBLIC=1  ->  tat coupon Lidl Plus ca nhan, them trang gioi thieu
PUBLIC = bool(__import__("os").environ.get("CENA_PUBLIC"))

# Tu dien Viet -> Sec. Nguoi dung go CO DAU hay KHONG DAU deu duoc:
# input duoc strip_accents truoc khi tra cuu ("sữa tươi" -> "sua tuoi").
VI_CS = {
    # --- Sua, trung, bo sua ---
    "sua": "mleko", "sua tuoi": "cerstve mleko", "sua tiet trung": "trvanlive mleko",
    "sua hop": "trvanlive mleko",
    "sua chua": "jogurt", "sua dac": "kondenzovane mleko", "sua bot": "susene mleko",
    "pho mai": "syr", "pho mat": "syr", "bo": "maslo", "bo thuc vat": "margarin",
    "kem tuoi": "tocena zmrzlina", "trung": "vejce", "trung ga": "vejce",
    # --- Thit ca ---
    "thit": "maso", "thit ga": "kureci", "ga": "kureci", "duoi ga": "kureci",
    "canh ga": "kureci kridla", "dui ga": "kureci stehna", "uc ga": "kureci prsa",
    "thit heo": "veprove", "heo": "veprove", "thit lon": "veprove", "lon": "veprove",
    "thit bo": "hovezi", "suon": "zebra", "thit vit": "kachna", "vit": "kachna",
    "xuc xich": "parky", "lap xuong": "klobasa", "giam bong": "sunka",
    "ba roi": "slanina", "thit xong khoi": "slanina", "thit bam": "mlete maso",
    "ca": "ryba", "ca hoi": "losos", "ca ngu": "tunak", "ca thu": "makrela",
    "tom": "krevety", "muc": "kalamary",
    # --- Do kho, gia vi ---
    "gao": "ryze", "gao thom": "ryze jasminova", "mi": "nudle", "mi goi": "instantni nudle",
    "mi tom": "instantni nudle", "mi y": "spagety", "nui": "testoviny",
    "bot mi": "mouka", "duong": "cukr", "muoi": "sul", "dau an": "olej",
    "dau oliu": "olivovy olej", "nuoc mam": "rybi omacka", "nuoc tuong": "sojova omacka",
    "xi dau": "sojova omacka", "giam": "ocet", "tuong ot": "chilli omacka",
    "sot ca chua": "kecup", "mat ong": "med", "dau phong": "arasidy", "hat": "orisky",
    # --- Rau cu ---
    "rau": "zelenina", "ca chua": "rajcata", "khoai tay": "brambory",
    "hanh": "cibule", "hanh tay": "cibule", "toi": "cesnek", "gung": "zazvor",
    "ca rot": "mrkev", "dua chuot": "okurka", "dua leo": "okurka",
    "ot": "paprika", "ot chuong": "paprika", "bap cai": "zeli", "xa lach": "salat",
    "nam": "houby", "bong cai": "kvetak", "sup lo": "brokolice",
    "bap": "kukurice", "ngo": "kukurice", "dau hu": "tofu", "dau phu": "tofu",
    # --- Trai cay ---
    "chuoi": "banany", "tao": "jablka", "cam": "pomerance", "chanh": "citron",
    "dua hau": "meloun", "dau tay": "jahody", "dau": "jahody", "nho": "hrozny", "xoai": "mango",
    "dua": "kokos", "trai dua": "kokos", "thom": "ananas", "khom": "ananas",
    "buoi": "grapefruit", "le": "hrusky", "dao": "broskve", "man": "svestky",
    "qua bo": "avokado", "trai bo": "avokado", "viet quat": "boruvky",
    # --- Do uong ---
    "nuoc": "voda", "nuoc khoang": "mineralni voda", "nuoc suoi": "mineralni voda",
    "bia": "pivo", "ruou vang": "vino", "ruou manh": "vodka", "ruou": "alkohol",
    "nuoc ngot": "limonada",
    "coca": "coca cola", "nuoc cam": "pomerancovy dzus", "nuoc ep": "dzus",
    "ca phe": "kava", "tra": "caj", "che": "caj", "tra da": "ledovy caj",
    "tra sua": "bubble tea", "nuoc tang luc": "energeticky napoj",
    "nuoc dua": "kokosova voda", "sinh to": "smoothie",
    # --- Banh keo, an vat ---
    "banh mi": "chleba", "banh mi goi": "rohlik", "banh ngot": "kolace",
    "banh quy": "susenky", "banh keo": "sladkosti", "keo": "bonbony",
    "socola": "cokolada", "so co la": "cokolada", "kem": "zmrzlina",
    "khoai tay chien": "chipsy", "bim bim": "chipsy", "snack": "chipsy",
    "banh gato": "dort", "banh kem": "dort",
    # --- Do gia dung, drogerie ---
    "giay ve sinh": "toaletni papir", "khan giay": "ubrousky",
    "bot giat": "praci prasek", "nuoc giat": "praci gel", "nuoc xa vai": "avivaz",
    "nuoc rua chen": "prostredek na nadobi", "nuoc lau nha": "cistic podlah",
    "dau goi": "sampon", "sua tam": "sprchovy gel", "xa phong": "mydlo",
    "kem danh rang": "zubni pasta", "ban chai danh rang": "zubni kartacek",
    "ta": "plenky", "bim": "plenky", "ta em be": "plenky",
    "khu mui": "deodorant", "kem chong nang": "opalovaci krem",
    "chong muoi": "proti komarum", "thuoc xit muoi": "sprej proti hmyzu",
    # --- Thu cung ---
    "do cho": "pro psy", "do an cho cho": "pro psy",
    "thuc an cho": "pro psy", "hat cho cho": "granule",
    "do meo": "pro kocky", "do an cho meo": "pro kocky",
    "thuc an meo": "pro kocky", "hat cho meo": "granule",
    "pate meo": "kapsicky pro kocky", "cat ve sinh": "stelivo",
}


def load_tudien():
    """Nap them tu dien tu tudien.xlsx (cot A hoac B = tieng Viet, cot C = tieng Sec).
    Sua file Excel -> khoi dong lai app la co hieu luc. Loi/thieu file thi bo qua."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tudien.xlsx")
    if not os.path.exists(path):
        return
    try:
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True).active
        n = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[2]:
                continue
            cs = cena.strip_accents(str(row[2]).strip().lower())
            for col in (0, 1):
                if row[col]:
                    vi = cena.strip_accents(str(row[col]).strip().lower())
                    if vi and vi != cs:
                        VI_CS[vi] = cs
                        n += 1
        print(f"Da nap {n} muc tu dien tu tudien.xlsx")
    except Exception as e:
        print(f"Khong doc duoc tudien.xlsx: {e}")


load_tudien()

# Icon tu dong theo tu khoa trong ten san pham (tieng Sec, khong dau)
ICON_RULES = [
    ("banan", "🍌"), ("jablk", "🍎"), ("pomeranc", "🍊"), ("citron", "🍋"),
    ("meloun", "🍉"), ("jahod", "🍓"), ("hrozn", "🍇"), ("broskv", "🍑"),
    ("merunk", "🍑"), ("tresn", "🍒"), ("visn", "🍒"), ("svestk", "🟣"),
    ("mandarin", "🍊"), ("kiwi", "🥝"), ("ananas", "🍍"), ("mango", "🥭"),
    ("hrusk", "🍐"), ("boruvk", "🫐"), ("malin", "🍓"),
    ("avokad", "🥑"), ("rajc", "🍅"), ("brambor", "🥔"), ("mrkev", "🥕"),
    ("cibul", "🧅"), ("cesnek", "🧄"), ("okurk", "🥒"), ("salat", "🥬"),
    ("paprik", "🫑"), ("kukuric", "🌽"),
    ("mleko", "🥛"), ("jogurt", "🥛"), ("smetana", "🥛"), ("maslo", "🧈"),
    ("syr", "🧀"), ("eidam", "🧀"), ("mozzarel", "🧀"), ("vejce", "🥚"), ("vajec", "🥚"),
    ("kurec", "🍗"), ("kure", "🍗"), ("veprov", "🥩"), ("hovez", "🥩"),
    ("sunka", "🥓"), ("slanin", "🥓"), ("salam", "🥓"), ("klobas", "🌭"),
    ("parky", "🌭"), ("ryb", "🐟"), ("losos", "🐟"), ("tunak", "🐟"), ("krevet", "🦐"),
    ("chleb", "🍞"), ("rohlik", "🥖"), ("bageta", "🥖"), ("croissant", "🥐"),
    ("kobliha", "🍩"), ("kolac", "🍰"), ("dort", "🍰"),
    ("cokolad", "🍫"), ("bonbon", "🍬"), ("zele", "🍬"), ("lizatk", "🍭"),
    ("susenk", "🍪"), ("oplatk", "🍪"), ("tycink", "🍫"), ("chips", "🍟"),
    ("krekry", "🍘"), ("zmrzlin", "🍦"), ("nanuk", "🍦"),
    ("pivo", "🍺"), ("lezak", "🍺"), ("radler", "🍺"), ("vino", "🍷"),
    ("kava", "☕"), ("caj", "🍵"), ("dzus", "🧃"), ("limonad", "🥤"),
    ("cola", "🥤"), ("miner", "💧"), ("voda", "💧"), ("energ", "⚡"),
    ("ryze", "🍚"), ("testovin", "🍝"), ("spaget", "🍝"), ("mouka", "🌾"),
    ("cukr", "🍬"), ("olej", "🫒"), ("kecup", "🍅"), ("majonez", "🥫"),
    ("konzerv", "🥫"), ("polevk", "🍲"), ("pizza", "🍕"),
    ("toaletni", "🧻"), ("papir", "🧻"), ("praci", "🧺"), ("gel", "🧴"),
    ("sampon", "🧴"), ("sprchov", "🧴"), ("mydlo", "🧼"), ("zubni", "🦷"),
    ("plenky", "👶"), ("cistic", "🧽"), ("wc", "🚽"), ("osvezovac", "🌸"),
    ("deodorant", "🧴"), ("kremy", "🧴"), ("ubrousk", "🧻"),
    ("pes", "🐶"), ("psy", "🐶"), ("granule", "🐶"), ("kocic", "🐱"),
    ("kocky", "🐱"), ("kapsick", "🐱"),
]


def icon_for(name: str) -> str:
    n = cena.strip_accents(name.lower())
    for kw, ico in ICON_RULES:
        if kw in n:
            return ico + " "
    return "🛒 "


CSS = """
 body{font-family:Segoe UI,Arial,sans-serif;max-width:1100px;margin:20px auto;padding:0 16px;background:#161614;color:#e6e4dd}
 a{color:#7ac68f}
 h1{color:#7ac68f;margin-bottom:4px} h2{background:#1a7a3a;color:#fff;padding:8px 12px;border-radius:6px;margin-top:28px}
 h3{margin:24px 0 8px;color:#7ac68f}
 table{border-collapse:collapse;width:100%;background:#232320;margin-bottom:12px;border-radius:10px;overflow:hidden}
 th{background:#2b3a2f;text-align:left;padding:8px;color:#cfe8d6} td{padding:8px;border-top:1px solid #35352f;vertical-align:top}
 tr.best{background:#41381c}
 .p{font-weight:bold;color:#ff8a7a;white-space:nowrap} .s{font-weight:bold}
 .d{color:#8fd6a4;font-weight:bold;white-space:nowrap} .a{color:#8f8f88;font-size:.9em}
 .o{color:#8f8f88;font-size:.85em} .n{max-width:260px}
 .searchbox{display:flex;gap:8px;margin:16px 0}
 input[type=text]{flex:1;font-size:1.3em;padding:12px;border:2px solid #2f7a46;border-radius:8px;background:#232320;color:#e6e4dd}
 select{background:#232320;color:#e6e4dd;border:1px solid #555;border-radius:6px;padding:3px 6px}
 button,.bigbtn{font-size:1.1em;padding:12px 20px;background:#1a7a3a;color:#fff;border:none;border-radius:8px;cursor:pointer;text-decoration:none;display:inline-block}
 button:hover,.bigbtn:hover{background:#239b4d}
 .chips{margin:10px 0} .chips a{display:inline-block;margin:4px 6px 0 0;padding:6px 14px;background:#232320;border:1px solid #2f7a46;color:#7ac68f;border-radius:20px;text-decoration:none;font-size:.95em}
 .chips a:hover{background:#203327}
 .muted{color:#8f8f88} .muted a{color:#7ac68f}
 .back{margin-bottom:12px;display:inline-block}
 .cols{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
 .col{flex:1;min-width:340px}
 .colhead{font-size:1.2em;font-weight:bold;padding:10px 14px;border-radius:8px;color:#fff;margin-bottom:4px}
 .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:18px}
 .card{background:#232320;border:1px solid #35352f;border-radius:12px;padding:12px 14px}
 .card .top{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px}
 .sbadge{border-radius:6px;padding:2px 8px;font-size:.78em;font-weight:bold;white-space:nowrap}
 .expb{background:#5a1f1f;color:#ffb4a8;border-radius:10px;padding:2px 8px;font-size:.72em;white-space:nowrap}
 .vald{font-size:.72em;color:#8f8f88;white-space:nowrap}
 .card .nm{font-weight:bold;font-size:.93em;margin:0 0 2px;line-height:1.3;color:#f0efe8}
 .card .sub{color:#9a9a92;font-size:.78em;margin:0 0 8px;min-height:1.1em}
 .card .pr{font-size:1.45em;font-weight:bold;color:#ff8a7a;white-space:nowrap}
 .pctb{background:#23401f;color:#9fdc8f;border-radius:6px;padding:1px 7px;font-size:.78em;font-weight:bold}
 .chipbar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;align-items:center}
 .chipbar label{color:#bdbdb4}
 .chip{border:1px solid #4a4a44;border-radius:20px;padding:6px 14px;font-size:.88em;cursor:pointer;background:#232320;color:#bdbdb4}
 .chip.on{background:#1a7a3a;color:#fff;border-color:#1a7a3a}
 .appbar{display:flex;align-items:center;gap:10px;border-bottom:1px solid #35352f;padding:8px 0;margin-bottom:14px;flex-wrap:wrap}
 .appbar .logo{font-size:1.15em;font-weight:bold;color:#7ac68f;text-decoration:none}
 .navtabs{display:flex;gap:4px;margin-left:auto;flex-wrap:wrap}
 .navtabs a{padding:6px 13px;border-radius:8px;font-size:.92em;color:#bdbdb4;text-decoration:none}
 .navtabs a.on{background:#1a7a3a;color:#fff}
 .navtabs a:hover{background:#203327;color:#7ac68f}
 .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:8px;margin:14px 0}
 .tile{background:#232320;border:1px solid #35352f;border-radius:12px;padding:12px 6px;text-align:center;text-decoration:none;color:#d8d6cf;font-size:.85em}
 .tile:hover{border-color:#2f7a46;background:#203327}
 .tile .em{font-size:1.6em;display:block;margin-bottom:4px}
 .rlist{border:1px solid #35352f;border-radius:12px;overflow:hidden;background:#232320;margin-bottom:16px}
 .rrow{display:flex;align-items:center;gap:10px;padding:10px 14px;border-top:1px solid #35352f}
 .rrow:first-child{border-top:none}
 .rrow.win{background:#41381c}
 .rrow .rk{font-size:1.05em;font-weight:bold;color:#8f8f88;min-width:24px;text-align:center}
 .rrow.win .rk{color:#e8c15a}
 .rrow .inf{flex:1;min-width:0}
 .rrow .inf p{margin:0}
 .rrow .pn{font-size:.95em;font-weight:bold;line-height:1.3;color:#f0efe8}
 .rrow .pm{font-size:.8em;color:#9a9a92}
 .rrow .per{font-size:1.15em;font-weight:bold;color:#ff8a7a;white-space:nowrap}
 .tagb{border-radius:6px;padding:1px 6px;font-size:.72em;font-weight:normal;white-space:nowrap;vertical-align:1px}
 .mx td.w{background:#23401f}
 .mx td.w .mxp{color:#ff8a7a;font-size:1.1em}
 .mx .mxp{display:block;font-weight:bold;color:#d8d6cf;white-space:nowrap}
 .mx a.it{color:#f0efe8;text-decoration:none;font-weight:bold}
 .mx a.it:hover{color:#7ac68f}
"""

NAV_ITEMS = [("/", "Trang chủ"), ("/akce", "Akce"), ("/hoaqua", "Rau quả"), ("/banbuon", "Bán buôn")]


APP_VERSION = "v2.1 · 07.07.2026"


def shell(body, active="/"):
    tabs = "".join(
        f'<a href="{href}"{" class=\"on\"" if href == active else ""}>{label}</a>'
        for href, label in NAV_ITEMS)
    searchbar = ('<form class="searchbox" action="/hledej" method="get">'
                 '<input type="text" name="q" placeholder="Gõ mặt hàng: sữa tươi / đùi gà / gạo thơm...">'
                 '<button type="submit">🔍 Tìm</button></form>')
    return (PAGE_TOP
            + f'<div class="appbar"><a class="logo" href="/">🛒 Cena Checker</a>'
            f'<nav class="navtabs">{tabs}</nav></div>{searchbar}'
            + body
            + f"<p style='text-align:center;color:#5a5a54;font-size:.8em;margin:30px 0 10px'>"
              f"Cena Checker {APP_VERSION}</p></body></html>")

# Mau nhan cho tung chuoi (nen, chu)
SHOP_COLOR = [
    ("lidl", "#E6F1FB", "#0C447C"), ("kaufland", "#FAECE7", "#712B13"),
    ("billa", "#E1F5EE", "#085041"), ("penny", "#FBEAF0", "#72243E"),
    ("tesco", "#DBE4F7", "#0B2E6B"), ("albert", "#E1F5EE", "#0F6E56"),
    ("globus", "#FAEEDA", "#633806"), ("tamda", "#FFE3CC", "#8A4B00"),
    ("makro", "#DDE6F2", "#003B7E"), ("jip", "#FCEBEB", "#C8102E"),
    ("coop", "#EAF3DE", "#3B6D11"), ("dm", "#EEEDFE", "#3C3489"),
    ("hru", "#FAEEDA", "#854F0B"), ("flop", "#FBEAF0", "#993556"),
]


def shop_badge(shop):
    s = cena.strip_accents(shop.lower())
    for key, bg, fg in SHOP_COLOR:
        if key in s:
            return f"<span class='sbadge' style='background:{bg};color:{fg}'>{H.escape(shop)}</span>"
    return f"<span class='sbadge' style='background:#F1EFE8;color:#444441'>{H.escape(shop)}</span>"


def deal_card(name, amount, shop, price, pct="", unit="", valid="", exp=False):
    m = _re.search(r"(\d+)", pct or "")
    pctnum = m.group(1) if m else "0"
    right = (f"<span class='expb'>⏰ {H.escape(valid) or 'sắp hết'}</span>" if exp
             else f"<span class='vald'>{H.escape(valid)}</span>")
    pctb = f" <span class='pctb'>{H.escape(pct)}</span>" if pct else ""
    sub = " · ".join(x for x in (amount, unit) if x)
    return (f"<div class='card' data-shop=\"{H.escape(shop)}\" data-exp='{1 if exp else 0}' "
            f"data-pct='{pctnum}' data-price='{price}'>"
            f"<div class='top'>{shop_badge(shop)}{right}</div>"
            f"<p class='nm'>{icon_for(name)}{H.escape(name)}</p>"
            f"<p class='sub'>{H.escape(sub)}</p>"
            f"<span class='pr'>{price:.2f} Kč</span>{pctb}</div>")


def pairs_cards(pairs):
    return "".join(
        deal_card(p["name"], p["amount"], d["shop"], d["price"], d["pct"],
                  d["unit"], d["valid"], exp=bool(d.get("_exp")))
        for p, d in pairs)

PAGE_TOP = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cena Checker</title><style>{CSS}</style></head><body>"""


_home_cache = {"t": 0, "expiring": [], "fresh": [], "active": []}


def build_home_suggestions():
    """Quet cac nhom hang kupi, phan loai: het akce hom nay / deal moi bat dau."""
    import datetime
    import time as _t
    if _t.time() - _home_cache["t"] < 3 * 3600 and (_home_cache["expiring"] or _home_cache["fresh"]):
        return _home_cache["expiring"], _home_cache["fresh"]
    today = datetime.date.today()
    expiring, fresh, active, seen = [], [], [], set()
    for slug in cena.CATEGORIES.values():
        try:
            soup = cena.fetch(f"{cena.BASE}/slevy/{slug}")
        except Exception:
            continue
        for p in cena.parse_groups(soup):
            if p["name"] in seen:
                continue
            seen.add(p["name"])
            # quet TAT CA cac deal (moi sieu thi), khong chi deal re nhat
            exp_deal, fresh_deal, act_deal = None, None, None
            tomorrow = today + datetime.timedelta(days=1)
            for d in p["deals"]:
                valid = d["valid"]
                v_plain = cena.strip_accents(valid)
                if "dnes konci" in v_plain or "zitra konci" in v_plain:
                    if exp_deal is None:
                        exp_deal = d
                    continue
                dates = _re.findall(r"(\d{1,2})\.\s*(\d{1,2})\.", valid)
                if not dates:
                    continue
                try:
                    end = datetime.date(today.year, int(dates[-1][1]), int(dates[-1][0]))
                    start = datetime.date(today.year, int(dates[0][1]), int(dates[0][0]))
                except ValueError:
                    continue
                # het han hom nay/ngay mai -> "sap het akce"
                if exp_deal is None and today <= end <= tomorrow:
                    exp_deal = d
                # bat dau trong tuong lai -> "to roi moi"
                elif fresh_deal is None and len(dates) >= 2 and start > today:
                    fresh_deal = d
                # dang chay (da bat dau, con hon 1 ngay) -> "dang dien ra"
                elif act_deal is None and end > tomorrow and (len(dates) < 2 or start <= today):
                    act_deal = d
            if exp_deal:
                exp_deal["_exp"] = True  # danh dau: sap het han
                expiring.append((p, exp_deal))
            if fresh_deal:
                fresh.append((p, fresh_deal))
            if act_deal:
                active.append((p, act_deal))
        _t.sleep(1)

    def by_pct(lst):
        def pct(pair):
            m = _re.search(r"(\d+)", pair[1]["pct"] or "")
            return int(m.group(1)) if m else 0
        lst.sort(key=pct, reverse=True)

    for lst in (expiring, fresh, active):
        by_pct(lst)
    _home_cache.update({"t": _t.time(), "expiring": expiring, "fresh": fresh, "active": active})
    return expiring, fresh


def suggest_table(pairs, heading, color):
    return (f"<h2 style='background:{color}'>{heading}</h2>"
            f"<div class='cards'>{pairs_cards(pairs)}</div>")


def home_suggestions_html():
    import random
    try:
        expiring, fresh = build_home_suggestions()
    except Exception:
        return ""
    if not fresh:
        return ""
    prods, seen = [], set()
    for p, _ in fresh:
        if p["name"] not in seen:
            seen.add(p["name"])
            prods.append(p)
    return product_matrix(prods[:15], "🆕 TỜ RƠI MỚI — deal sắp bắt đầu",
                          note="Khuyến mãi của tờ rơi tuần mới, chưa/vừa bắt đầu — lên kế hoạch đi chợ trước.",
                          show_exp=False)


import re as _re

FRUIT_RE = _re.compile(
    r"banan|jablk|pomeranc|mandarin|citron|limet|grep|grapefruit|meloun|jahod|"
    r"boruvk|malin|ostruzin|rybiz|hrozn|mango|kokos|ananas|hrusk|broskv|nektarin|"
    r"svestk|tresn|visn|kiwi|avokad|granat|marakuj|papaj|lici|datl|fik|merunk|ovoce",
    _re.IGNORECASE)


CAT_PAGES = {
    "ovoce-a-zelenina": ("🍉🥕", "Hoa quả & rau củ"),
    "maso-drubez-a-ryby": ("🥩", "Thịt cá"),
    "mlecne-vyrobky-a-vejce": ("🥛🥚", "Sữa & trứng"),
    "pecivo": ("🍞", "Bánh mì"),
    "sladkosti-a-slane-snacky": ("🍫", "Bánh kẹo & snack"),
    "pivo": ("🍺", "Bia"),
    "nealko-napoje": ("🥤", "Đồ uống"),
    "drogerie": ("🧴", "Drogerie"),
    "mazlicci": ("🐶🐱", "Thú cưng"),
}


def category_html(slug):
    em, title = CAT_PAGES.get(slug, ("🛒", slug))
    products = list(shop_products(slug))

    def best_pct(p):
        m = _re.search(r"(\d+)", p["deals"][0]["pct"] or "")
        return int(m.group(1)) if m else 0

    products.sort(key=best_pct, reverse=True)
    body = f"<h1>{em} {H.escape(title)} — khuyến mãi tuần này</h1>"
    if not products:
        body += "<p>Không tải được dữ liệu — thử lại sau vài phút.</p>"
    else:
        body += product_matrix(
            products, f"{em} {len(products)} mặt hàng",
            note="Giá gói · cột ✅ = nơi rẻ nhất · (giá/đơn vị) ghi nhỏ · xếp theo mức giảm sâu nhất.")
    active = "/hoaqua" if slug == "ovoce-a-zelenina" else ""
    return shell(body, active)


def akce_html():
    build_home_suggestions()  # dam bao cache day du
    active = _home_cache["active"]
    expiring = _home_cache["expiring"]
    fresh = _home_cache["fresh"]
    body = ("<h1>📢 Tổng hợp AKCE</h1>"
            "<p class='muted'>Quét từ 7 nhóm hàng chính trên Kupi, xếp theo mức giảm sâu nhất trong từng phần.</p>")
    running = expiring + active

    def pct_of(pair):
        m = _re.search(r"(\d+)", pair[1]["pct"] or "")
        return int(m.group(1)) if m else 0

    running.sort(key=pct_of, reverse=True)
    if running:
        prods, seen2 = [], set()
        for p, _ in running:
            if p["name"] not in seen2:
                seen2.add(p["name"])
                prods.append(p)
        body += product_matrix(
            prods, f"🔥 AKCE ĐANG DIỄN RA ({len(prods)} mặt hàng)",
            note="Giá gói, cột ✅ = nơi rẻ nhất; ⏰ = hết hôm nay/ngày mai; (giá/đơn vị) ghi nhỏ bên dưới.")
    if fresh:
        prods, seen3 = [], set()
        for p, _ in fresh:
            if p["name"] not in seen3:
                seen3.add(p["name"])
                prods.append(p)
        body += product_matrix(prods[:30], f"🆕 TỜ RƠI MỚI — sắp bắt đầu ({len(prods)} mặt hàng)",
                               show_exp=False)
    if not (active or expiring or fresh):
        body += "<p>Không tải được dữ liệu — thử lại sau vài phút.</p>"
    return shell(body, "/akce")


# Bang ma tran gia trang chinh: (nhan VN, tu khoa kupi, don vi chuan)
STAPLES_ALL = [
    ("🥚 Trứng", "vejce", "ks"),
    ("🥛 Sữa hộp", "trvanlive mleko", "l"),
    ("🥛 Sữa tươi", "cerstve mleko", "l"),
    ("🍌 Chuối", "banany", "kg"),
    ("🍎 Táo", "jablka", "kg"),
    ("🍊 Cam", "pomerance", "kg"),
    ("🍉 Dưa hấu", "meloun", "kg"),
    ("🍓 Dâu tây", "jahody", "kg"),
    ("🍗 Ức gà", "kureci prsa", "kg"),
    ("🍗 Đùi gà", "kureci stehna", "kg"),
    ("🥩 Thịt heo", "veprove", "kg"),
    ("🥩 Thịt bò", "hovezi", "kg"),
    ("🌭 Xúc xích", "parky", "kg"),
    ("🥓 Giăm bông", "sunka", "kg"),
    ("🐟 Cá hồi", "losos", "kg"),
    ("🍚 Gạo thơm", "ryze jasminova", "kg"),
    ("🍝 Mì ống", "testoviny", "kg"),
    ("🧈 Bơ", "maslo", "kg"),
    ("🧀 Phô mai Eidam", "eidam", "kg"),
    ("🥛 Sữa chua", "jogurt", "kg"),
    ("🥔 Khoai tây", "brambory", "kg"),
    ("🍅 Cà chua", "rajcata", "kg"),
    ("🥒 Dưa chuột", "okurky", "kg"),
    ("🫑 Ớt chuông", "paprika", "kg"),
    ("🍺 Bia", "pivo", "l"),
    ("🧃 Nước ép", "dzus", "l"),
    ("💧 Nước khoáng", "mineralni voda", "l"),
    ("☕ Cà phê", "kava", "kg"),
    ("🧻 Giấy vệ sinh", "toaletni papir", "ks"),
    ("🧺 Bột giặt", "praci prasek", "kg"),
]
_matrix_cache = {"t": 0, "rows": []}


def deal_expiring(valid):
    """True neu deal het han hom nay/ngay mai (theo chuoi 'valid' cua kupi)."""
    import datetime
    v_plain = cena.strip_accents(valid or "")
    if "dnes konci" in v_plain or "zitra konci" in v_plain:
        return True
    dates = _re.findall(r"(\d{1,2})\.\s*(\d{1,2})\.", valid or "")
    if not dates:
        return False
    today = datetime.date.today()
    try:
        end = datetime.date(today.year, int(dates[-1][1]), int(dates[-1][0]))
    except ValueError:
        return False
    return today <= end <= today + datetime.timedelta(days=1)


def build_matrix():
    import time as _t
    if _t.time() - _matrix_cache["t"] < 600 and _matrix_cache["rows"]:
        return _matrix_cache["rows"]
    rows = []
    for label, qcz, unit in STAPLES_ALL:
        best = {}  # shop -> (gia/don vi, gia goi, so luong, sap het han)

        def consider(shop, price, unitstr="", amount="", exp=False):
            pu = parse_unit_price(unitstr) if unitstr else None
            if pu is None:
                pu = parse_amount_price(amount, price)
            if pu and pu[1] == unit:
                if shop not in best or pu[0] < best[shop][0]:
                    best[shop] = (pu[0], price, amount or "", exp)

        try:
            soup = cena.fetch(f"{cena.BASE}/hledej?f={urllib.parse.quote(qcz)}")
            for p in cena.parse_groups(soup):
                for d in p["deals"]:
                    consider(d["shop"], d["price"], d["unit"], p["amount"],
                             exp=deal_expiring(d.get("valid")))
        except Exception:
            pass
        tdata, thits = tamda_matches(qcz)
        for it in thits:
            consider("Tamda", it["price"], amount=it["amount"])
        _d, tesco_hits = tesco_matches(qcz)
        for it in tesco_hits:
            consider("Tesco online", it["price"], unitstr=it["unit"])
        ranked = sorted(best.items(), key=lambda kv: kv[1][0])[:4]
        if ranked:
            rows.append((label, qcz, unit, ranked))
        _t.sleep(1)
    _matrix_cache.update({"t": _t.time(), "rows": rows})
    return rows


def matrix_html():
    import random as _rand
    try:
        all_rows = build_matrix()
    except Exception:
        return ""
    if not all_rows:
        return ""
    rows = _rand.sample(all_rows, min(10, len(all_rows)))
    out = ("<h2 style='margin-top:14px'>💡 MUA GÌ Ở ĐÂU HÔM NAY — giá gói, xếp theo giá quy đổi</h2>"
           "<p class='muted' style='margin:4px 0 8px'>⏰ = hết hôm nay/ngày mai · (giá/đơn vị) ghi nhỏ bên dưới.</p>"
           "<table class='mx'><tr><th style='width:24%'>Mặt hàng</th>"
           "<th style='background:#23401f;color:#9fdc8f'>✅ Rẻ nhất</th><th>#2</th><th>#3</th><th>#4</th></tr>")
    for label, qcz, unit, ranked in rows:
        out += (f"<tr><td><a class='it' href='/hledej?q={urllib.parse.quote(qcz)}'>{H.escape(label)}</a>"
                f"<span class='a'> /{UNIT_SHORT[unit]}</span></td>")
        for i in range(4):
            if i < len(ranked):
                shop, (per, price, amt, exp) = ranked[i]
                cls = " class='w'" if i == 0 else ""
                amt_s = f" {H.escape(amt)}" if amt else ""
                exp_s = " <span class='expb'>⏰</span>" if exp else ""
                out += (f"<td{cls}>{shop_badge(shop)}{exp_s}"
                        f"<span class='mxp'>{price:.2f} Kč{amt_s}</span>"
                        f"<span class='a'>({per:.2f} Kč/{UNIT_SHORT[unit]})</span></td>")
            else:
                out += "<td class='a'>—</td>"
        out += "</tr>"
    out += "</table><p class='muted' style='margin-top:-4px'>Bấm tên mặt hàng để xem đầy đủ mọi siêu thị · cập nhật mỗi 10 phút</p>"
    return out


def product_matrix(products, heading, max_cols=4, note="", show_exp=True):
    """Bang ma tran: hang = mat hang, cot = cac sieu thi re nhat (gia GOI, kem gia/don vi nho)."""
    if not products:
        return ""

    def best_pct(p):
        m = _re.search(r"(\d+)", p["deals"][0]["pct"] or "")
        return int(m.group(1)) if m else 0

    products = sorted(products, key=best_pct, reverse=True)
    head_cols = "".join(
        f"<th>{'✅ Rẻ nhất' if i == 0 else '#%d' % (i + 1)}</th>" for i in range(max_cols))
    head_cols = head_cols.replace("<th>✅ Rẻ nhất</th>",
                                  "<th style='background:#23401f;color:#9fdc8f'>✅ Rẻ nhất</th>")
    out = (f"<h2>{heading}</h2>"
           + (f"<p class='muted'>{note}</p>" if note else "")
           + f"<table class='mx'><tr><th style='width:26%'>Mặt hàng</th>{head_cols}</tr>")
    for p in products:
        deals = sorted(p["deals"], key=lambda d: d["price"])[:max_cols]
        amount = f" <span class='a'>{H.escape(p['amount'])}</span>" if p["amount"] else ""
        out += (f"<tr><td>{icon_for(p['name'])}<b>{H.escape(p['name'])}</b>{amount}</td>")
        for i in range(max_cols):
            if i < len(deals):
                d = deals[i]
                exp = " <span class='expb'>⏰</span>" if show_exp and d.get("_exp") else ""
                unit_small = f"<span class='a'>{H.escape(d['unit'])}</span>" if d["unit"] else ""
                pct = f" <span class='pctb'>{H.escape(d['pct'])}</span>" if d["pct"] else ""
                out += (f"<td{' class=\"w\"' if i == 0 else ''}>{shop_badge(d['shop'])}{exp}"
                        f"<span class='mxp'>{d['price']:.2f} Kč{pct}</span>{unit_small}</td>")
            else:
                out += "<td class='a'>—</td>"
        out += "</tr>"
    return out + "</table>"


HOME_TILES = [
    ("🍎", "Rau quả", "/hoaqua"),
    ("🥩", "Thịt cá", "/kategorie/maso-drubez-a-ryby"),
    ("🥛", "Sữa trứng", "/kategorie/mlecne-vyrobky-a-vejce"),
    ("🍞", "Bánh mì", "/kategorie/pecivo"),
    ("🍫", "Bánh kẹo", "/kategorie/sladkosti-a-slane-snacky"),
    ("🍺", "Bia", "/kategorie/pivo"),
    ("🥤", "Đồ uống", "/kategorie/nealko-napoje"),
    ("🧴", "Drogerie", "/kategorie/drogerie"),
    ("🐶", "Thú cưng", "/kategorie/mazlicci"),
    ("📦", "Bán buôn", "/banbuon"),
]


def home_html():
    tiles = "".join(
        f'<a class="tile" href="{u}"><span class="em">{e}</span>{t}</a>'
        for e, t, u in HOME_TILES)
    body = f"""
<p class="muted">So sánh giá siêu thị Séc — gõ tiếng Việt có dấu hoặc không dấu đều được.</p>
<div class="tiles">{tiles}</div>
{matrix_html()}
{home_suggestions_html()}
<p class="muted" style="margin-top:24px">Nguồn tham khảo: kupi.cz, tamdafoods.eu · <a href="/gioithieu">Giới thiệu &amp; miễn trừ trách nhiệm</a></p>"""
    return shell(body, "/")


_BB_STOP = {"a", "s", "v", "z", "na", "do", "od", "po", "the", "cca", "kus", "ks",
            "kg", "g", "l", "ml", "balení", "baleni"}


def _bb_tokens(name):
    """Tu khoa chinh cua ten hang (bo dau, bo so luong/don vi) de ghep hang giua cac kho."""
    n = cena.strip_accents(name.lower())
    n = _re.sub(r"[\d]+[,.]?\d*\s*(kg|g|l|ml|ks|%)?", " ", n)
    return {w for w in _re.split(r"[^a-z]+", n) if len(w) >= 3 and w not in _BB_STOP}


def _bb_match(t1, t2):
    """2 mat hang coi la trung khi chung >=2 tu khoa (hoac tap nho nam tron trong tap lon)."""
    if not t1 or not t2:
        return False
    common = t1 & t2
    small = min(t1, t2, key=len)
    return len(common) >= 2 or (len(common) >= 1 and common == small)


def banbuon_html():
    body = ("<h1>📦 Bán buôn — Tamda / Makro / JIP</h1>"
            "<p class='muted'>Giá gói · (giá/đơn vị) ghi nhỏ · ô xanh ✅ = kho rẻ nhất khi có "
            "cùng mặt hàng ở nhiều kho. Tamda = giá với thẻ, theo tờ rơi tuần.</p>")

    # Gom deal 3 kho ve 1 danh sach: moi item = {name, amount, offers{col: deal}}
    items = []
    data = load_tamda()
    if data:
        for it in data["items"]:
            items.append({"name": it["name"], "amount": it["amount"],
                          "toks": _bb_tokens(it["name"]),
                          "offers": {"tamda": {"shop": "Tamda Foods", "price": it["price"],
                                               "pct": "", "unit": "", "amount": it["amount"]}}})
    for col in ("makro", "jip"):
        for p in shop_products(col):
            d = min(p["deals"], key=lambda d: d["price"])
            toks = _bb_tokens(p["name"])
            offer = {"shop": d["shop"], "price": d["price"], "pct": d["pct"],
                     "unit": d["unit"], "amount": p["amount"], "_exp": d.get("_exp")}
            hit = next((x for x in items if col not in x["offers"] and _bb_match(x["toks"], toks)), None)
            if hit:
                hit["offers"][col] = offer
            else:
                items.append({"name": p["name"], "amount": p["amount"],
                              "toks": toks, "offers": {col: offer}})

    if not items:
        return shell(body + "<p class='muted'>Chưa có dữ liệu bán buôn.</p>", "/banbuon")

    # Hang co o >=2 kho len dau, sau do theo % giam gia
    def sort_key(x):
        pcts = [int(m.group(1)) for o in x["offers"].values()
                for m in [_re.search(r"(\d+)", o["pct"] or "")] if m]
        return (-len(x["offers"]), -(max(pcts) if pcts else 0))

    items.sort(key=sort_key)
    ncmp = sum(1 for x in items if len(x["offers"]) >= 2)
    valid_s = f" · Tamda: {H.escape(data['valid'])}" if data else ""
    body += (f"<h2>📦 SO SÁNH 3 KHO — {len(items)} mặt hàng, {ncmp} có ở ≥2 kho{valid_s}</h2>"
             "<table class='mx'><tr><th style='width:30%'>Mặt hàng</th>"
             "<th style='background:#3a2a15;color:#ffb27a'>🅣 Tamda</th>"
             "<th style='background:#1c2940;color:#9fc0ee'>Ⓜ Makro</th>"
             "<th style='background:#3a1c1c;color:#f0a0a0'>🄹 JIP</th></tr>")
    for x in items:
        amount = f" <span class='a'>{H.escape(x['amount'])}</span>" if x["amount"] else ""
        body += f"<tr><td>{icon_for(x['name'])}<b>{H.escape(x['name'])}</b>{amount}</td>"
        # Chon kho re nhat: uu tien so theo gia/don vi (khi cung don vi), khong thi so gia goi
        best = None
        if len(x["offers"]) >= 2:
            pus = {c: parse_amount_price(o["amount"], o["price"]) for c, o in x["offers"].items()}
            units = {pu[1] for pu in pus.values() if pu}
            if len(units) == 1 and all(pus.values()):
                best = min(pus, key=lambda c: pus[c][0])
            else:
                best = min(x["offers"], key=lambda c: x["offers"][c]["price"])
        for col in ("tamda", "makro", "jip"):
            o = x["offers"].get(col)
            if not o:
                body += "<td class='a'>—</td>"
                continue
            pu = parse_amount_price(o["amount"], o["price"])
            per_s = (f"<span class='a'>({pu[0]:.2f} Kč/{UNIT_SHORT[pu[1]]})</span>" if pu
                     else (f"<span class='a'>{H.escape(o['unit'])}</span>" if o["unit"] else ""))
            pct = f" <span class='pctb'>{H.escape(o['pct'])}</span>" if o["pct"] else ""
            exp = " <span class='expb'>⏰</span>" if o.get("_exp") else ""
            win = " class='w'" if col == best else ""
            tick = "✅ " if col == best else ""
            body += (f"<td{win}>{exp}<span class='mxp'>{tick}{o['price']:.2f} Kč{pct}</span>{per_s}</td>")
        body += "</tr>"
    body += ("</table><p class='muted' style='margin-top:-4px'>"
             "Makro/JIP: deal từ kupi.cz · ghép mặt hàng giữa các kho là tự động, có thể lệch quy cách gói.</p>")
    return shell(body, "/banbuon")


GIOITHIEU_BODY = """
<h1>ℹ️ Giới thiệu</h1>
<p><b>Cena Checker</b> là công cụ phi lợi nhuận giúp cộng đồng người Việt tại Séc so sánh
giá khuyến mãi giữa các siêu thị bán lẻ (Kaufland, Lidl, Billa, Penny, Tesco, Albert, Globus...)
và bán buôn (Tamda Foods, Makro, JIP). Hỗ trợ tìm kiếm bằng tiếng Việt có dấu hoặc không dấu.</p>
<h2>Miễn trừ trách nhiệm</h2>
<p>· Dữ liệu giá được tổng hợp tự động từ các nguồn công khai (kupi.cz, tờ rơi chính thức của
các chuỗi) và <b>chỉ mang tính tham khảo</b> — giá thực tế tại cửa hàng có thể khác.<br>
· Trang này <b>không liên kết, không đại diện</b> cho Kupi.cz, Tamda Foods, Makro, Lidl
hay bất kỳ chuỗi siêu thị nào.<br>
· Chúng tôi không chịu trách nhiệm cho quyết định mua sắm dựa trên thông tin tại đây.<br>
· Dữ liệu Tamda cập nhật thủ công theo tuần từ tờ rơi chính thức, có thể chậm vài ngày.</p>
<p class="muted">Góp ý / báo lỗi: liên hệ người quản trị trang.</p>"""


def product_table(p, max_shops=6):
    rows = []
    for i, d in enumerate(p["deals"][:max_shops]):
        cls = ' class="best"' if i == 0 else ""
        star = " ⭐ RẺ NHẤT" if i == 0 else ""
        rows.append(
            f"<tr{cls}><td class='s'>{H.escape(d['shop'])}{star}</td>"
            f"<td class='p'>{d['price']:.2f} Kč</td>"
            f"<td class='d'>{H.escape(d['pct']) or '—'}</td>"
            f"<td>{H.escape(d['unit']) or '—'}</td>"
            f"<td>{H.escape(d['valid'])}</td></tr>"
        )
    return (f"<h2>{icon_for(p['name'])}{H.escape(p['name'])} <span class='a'>{H.escape(p['amount'])}</span></h2>"
            f"<table><tr><th>Siêu thị</th><th>Giá</th><th>Giảm</th><th>Giá đơn vị</th><th>Hạn khuyến mãi</th></tr>"
            + "".join(rows) + "</table>")


import re as _re

UNIT_LABEL = {"ks": "1 cái/quả", "kg": "1 kg", "l": "1 lít"}


def parse_unit_price(unit_str):
    """'28,67 Kč / 100 g' -> (2.867*100=286.7/kg? no: 28.67*10, 'kg'). Tra ve (gia quy doi, don vi chuan) hoac None."""
    m = _re.search(r"([\d\s]+,?\d*)\s*Kč\s*/\s*(\d+)\s*(ks|kg|g|l|ml)", unit_str.replace("\xa0", " "))
    if not m:
        return None
    val = float(m.group(1).replace(" ", "").replace(",", "."))
    qty = int(m.group(2))
    unit = m.group(3)
    per_one = val / qty
    if unit == "g":
        return per_one * 1000, "kg"
    if unit == "ml":
        return per_one * 1000, "l"
    return per_one, unit


def ranking_tables(products):
    """Bang xep hang tong: gom moi deal, quy ve gia don vi, xep re -> dat."""
    groups = {}
    for p in products:
        for d in p["deals"]:
            parsed = parse_unit_price(d["unit"])
            if not parsed:
                continue
            per_one, unit = parsed
            groups.setdefault(unit, []).append((per_one, p, d))
    if not groups:
        return ""
    body = "<h2>🏆 XẾP HẠNG: RẺ NHẤT TÍNH TRÊN ĐƠN VỊ</h2>"
    for unit in ("ks", "kg", "l"):
        if unit not in groups:
            continue
        rows = sorted(groups[unit], key=lambda x: x[0])
        body += (f"<h3>Giá cho {UNIT_LABEL[unit]}</h3>"
                 "<table><tr><th>#</th><th>Sản phẩm</th><th>Gói</th><th>Siêu thị</th>"
                 f"<th>Giá / {UNIT_LABEL[unit]}</th><th>Giá gói</th><th>Hạn</th></tr>")
        for i, (per_one, p, d) in enumerate(rows[:10], 1):
            cls = ' class="best"' if i == 1 else ""
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, str(i))
            body += (f"<tr{cls}><td>{medal}</td>"
                     f"<td class='n'>{icon_for(p['name'])}{H.escape(p['name'])}</td>"
                     f"<td>{H.escape(p['amount']) or '—'}</td>"
                     f"<td class='s'>{H.escape(d['shop'])}</td>"
                     f"<td style='font-weight:bold;white-space:nowrap'>{per_one:.2f} Kč</td>"
                     f"<td class='p'>{d['price']:.2f} Kč</td>"
                     f"<td>{H.escape(d['valid'])}</td></tr>")
        body += "</table>"
    return body


TAMDA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tamda_prices.json")


def load_tamda():
    import json
    if not os.path.exists(TAMDA_FILE):
        return None
    with open(TAMDA_FILE, encoding="utf-8") as f:
        return json.load(f)


def tamda_matches(query_cs):
    data = load_tamda()
    if not data:
        return None, []
    q = cena.strip_accents(query_cs.lower())
    hits = [it for it in data["items"]
            if all(w in cena.strip_accents(it["name"].lower()) for w in q.split())]
    return data, hits


def tamda_table(data, items):
    cards = "".join(
        deal_card(it["name"], it["amount"], "Tamda Foods", it["price"],
                  valid=f"thẻ Tamda · {data['valid']}")
        for it in items)
    return (f"<h2 style='background:#e8681a'>🅣 TAMDA FOODS <span style='font-weight:normal;font-size:.8em'>"
            f"(giá với thẻ Tamda · {H.escape(data['valid'])})</span></h2>"
            f"<div class='cards'>{cards}</div>")


# Cac chuoi BAN BUON: tach khoi cot ban le
WHOLESALE_KEYWORDS = ("jip", "makro")
_shop_cache = {}


def shop_products(slug):
    """Deal cua 1 chuoi tu kupi.cz/slevy/<slug> (cache 1h)."""
    import time as _t
    c = _shop_cache.setdefault(slug, {"t": 0, "products": []})
    if _t.time() - c["t"] > 3600:
        try:
            soup = cena.fetch(f"{cena.BASE}/slevy/{slug}")
            c["products"] = cena.parse_groups(soup)
            c["t"] = _t.time()
        except Exception:
            pass
    return c["products"]


def shop_matches(slug, query_cs):
    q = cena.strip_accents(query_cs.lower())
    return [p for p in shop_products(slug)
            if all(w in cena.strip_accents(p["name"].lower()) for w in q.split())]


def shop_table(products, heading, color, note=""):
    note_html = f" <span style='font-weight:normal;font-size:.8em'>({note})</span>" if note else ""
    cards = "".join(
        deal_card(p["name"], p["amount"], p["deals"][0]["shop"], p["deals"][0]["price"],
                  p["deals"][0]["pct"], p["deals"][0]["unit"], p["deals"][0]["valid"])
        for p in products)
    return (f"<h2 style='background:{color}'>{heading}{note_html}</h2>"
            f"<div class='cards'>{cards}</div>")


def split_wholesale_deals(products):
    """Tach cac deal JIP/Makro ra khoi ket qua Kupi (de khoi lan vao cot ban le)."""
    pulled = []
    for p in products:
        keep, moved = [], []
        for d in p["deals"]:
            (moved if any(k in d["shop"].lower() for k in WHOLESALE_KEYWORDS) else keep).append(d)
        p["deals"] = keep
        for d in moved:
            pulled.append({"name": p["name"], "amount": p["amount"], "deals": [d]})
    return [p for p in products if p["deals"]], pulled


_lidl_cache = {"t": 0, "items": []}


def lidl_coupons():
    """Coupon Lidl Plus (cache 1h). Tra ve [] neu chua dang nhap/loi."""
    import json
    import time as _t
    if PUBLIC or not os.path.exists(TOKEN_FILE):
        return []
    if _t.time() - _lidl_cache["t"] > 3600:
        try:
            from lidlplus import LidlPlusApi
            with open(TOKEN_FILE, encoding="utf-8") as f:
                token = json.load(f)["refresh_token"]
            api = LidlPlusApi("cs", "CZ", refresh_token=token)
            coupons = api.coupons()
            items = coupons.get("coupons", coupons) if isinstance(coupons, dict) else coupons
            _lidl_cache["items"] = [c for c in items if isinstance(c, dict)]
            _lidl_cache["t"] = _t.time()
        except Exception:
            pass
    return _lidl_cache["items"]


def lidl_coupon_matches(query_cs):
    q = cena.strip_accents(query_cs.lower())
    hits = []
    for c in lidl_coupons():
        text = " ".join(str(c.get(k) or "") for k in ("title", "promotionTitle", "description", "offerTitle"))
        if all(w in cena.strip_accents(text.lower()) for w in q.split()):
            hits.append(c)
    return hits


def lidl_coupon_table(items):
    rows = ""
    for c in items:
        title = c.get("title") or c.get("promotionTitle") or c.get("description") or "?"
        offer = c.get("offerTitle") or c.get("discount") or c.get("offerDescription") or ""
        valid = (c.get("endValidityDate") or c.get("validTo") or "")[:10]
        rows += (f"<tr><td class='s'>🎟️ {H.escape(str(title))}</td>"
                 f"<td class='p'>{H.escape(str(offer))}</td><td>{H.escape(valid)}</td></tr>")
    return ("<h2 style='background:#0050aa'>🎟️ COUPON LIDL PLUS CỦA BẠN</h2>"
            "<table><tr><th>Coupon</th><th>Ưu đãi</th><th>Hạn</th></tr>" + rows + "</table>")


TESCO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesco_prices.json")


def tesco_matches(query_cs):
    import json
    if not os.path.exists(TESCO_FILE):
        return None, []
    with open(TESCO_FILE, encoding="utf-8") as f:
        data = json.load(f)
    q = cena.strip_accents(query_cs.lower())
    hits = [it for it in data["items"]
            if all(w in cena.strip_accents(it["name"].lower()) for w in q.split())]
    return data, hits


def tesco_table(data, items):
    cards = ""
    for it in items:
        valid = ("💳 Clubcard · " if it.get("cc") else "") + (it["valid"] or "giá thường")
        cards += deal_card(it["name"], it["amount"], "Tesco", it["price"],
                           unit=it["unit"], valid=valid)
    return (f"<h2 style='background:#00539f'>🅃 TESCO ONLINE <span style='font-weight:normal;font-size:.8em'>"
            f"(cả giá thường + giá thẻ Clubcard · cập nhật {H.escape(data['updated'])})</span></h2>"
            f"<div class='cards'>{cards}</div>")


def parse_amount_price(amount, price):
    """'10 ks' + 29.90 -> (2.99, 'ks'); '4,54 kg' + 230 -> (50.66, 'kg')."""
    m = _re.search(r"([\d]+[,.]?\d*)\s*(kg|g|l|ml|ks)\b", (amount or "").lower())
    if not m:
        return None
    qty = float(m.group(1).replace(",", "."))
    if qty <= 0:
        return None
    u = m.group(2)
    if u == "g":
        return price * 1000 / qty, "kg"
    if u == "ml":
        return price * 1000 / qty, "l"
    return price / qty, u


UNIT_SHORT = {"ks": "quả/cái", "kg": "kg", "l": "lít"}


EAN_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ean_db.json")


def ean_lookup(code):
    """Tra ma vach EAN: database rieng truoc, roi Open Food Facts, UPCitemdb."""
    import requests as _req
    # 0) Database rieng (thu thap tu Makro GTIN)
    try:
        import json as _json
        with open(EAN_DB_FILE, encoding="utf-8") as f:
            it = _json.load(f)["items"].get(code)
        if it:
            return it["name"]
    except Exception:
        pass
    # 1) Open Food Facts (khong gioi han)
    try:
        r = _req.get(f"https://world.openfoodfacts.org/api/v2/product/{code}.json",
                     headers={"User-Agent": "CenaChecker/1.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == 1:
                p = data.get("product", {})
                name = (p.get("product_name_cs") or p.get("product_name_cz")
                        or p.get("product_name") or p.get("generic_name"))
                if name:
                    return name
    except Exception:
        pass
    # 2) UPCitemdb trial (100 req/ngay, khong can key)
    try:
        r = _req.get(f"https://api.upcitemdb.com/prod/trial/lookup?upc={code}",
                     headers={"Accept": "application/json", "User-Agent": "CenaChecker/1.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            if items:
                return items[0].get("title") or items[0].get("brand")
    except Exception:
        pass
    return None


def search_html(query):
    raw_query = query.strip()
    ean_name = None
    if _re.fullmatch(r"\d{8,14}", raw_query):
        ean_name = ean_lookup(raw_query)
    q = cena.strip_accents((ean_name or raw_query).lower())
    q = VI_CS.get(q, q)
    soup = cena.fetch(f"{cena.BASE}/hledej?f={urllib.parse.quote(q)}")
    products = cena.parse_groups(soup)
    tdata, thits = tamda_matches(q)
    mhits = shop_matches("makro", q)
    jhits = shop_matches("jip", q)
    tesco_data, tesco_hits = tesco_matches(q)
    lhits = lidl_coupon_matches(q)

    # --- Gom MOI nguon vao 1 danh sach hop nhat ---
    entries = []

    def addE(name, amount, shop, price, valid="", pct="", unitstr="", tags=(), typ="retail"):
        pu = parse_unit_price(unitstr) if unitstr else None
        if pu is None:
            pu = parse_amount_price(amount, price)
        entries.append({"per": pu[0] if pu else None, "unit": pu[1] if pu else None,
                        "name": name, "amount": amount, "shop": shop, "price": price,
                        "valid": valid, "pct": pct, "tags": list(tags), "typ": typ})

    for p in products:
        for d in p["deals"]:
            wh = any(k in d["shop"].lower() for k in WHOLESALE_KEYWORDS)
            addE(p["name"], p["amount"], d["shop"], d["price"], d["valid"], d["pct"],
                 d["unit"], ["bán buôn"] if wh else [], "wholesale" if wh else "retail")
    for it in thits:
        addE(it["name"], it["amount"], "Tamda Foods", it["price"], tdata["valid"],
             tags=["thẻ Tamda", "bán buôn"], typ="wholesale")
    for p in mhits + jhits:
        d = p["deals"][0]
        addE(p["name"], p["amount"], d["shop"], d["price"], d["valid"], d["pct"],
             d["unit"], ["bán buôn"], "wholesale")
    for it in tesco_hits:
        addE(it["name"], it["amount"], "Tesco online", it["price"], it["valid"],
             unitstr=it["unit"], tags=(["💳 Clubcard"] if it.get("cc") else []), typ="retail")

    body = f"<h1>Kết quả: {H.escape(query)}</h1>"
    if ean_name:
        body += f'<p class="muted">📦 Mã vạch nhận diện: <b>{H.escape(ean_name)}</b> → tìm giá <b>{H.escape(q)}</b></p>'
    elif q != cena.strip_accents(raw_query.lower()):
        body += f'<p class="muted">(tự dịch sang tiếng Séc: <b>{H.escape(q)}</b>)</p>'
    if not entries:
        body += "<p>Không tìm thấy gì. Thử từ khác hoặc tên tiếng Séc?</p>"
        return shell(body, "")

    if lhits:
        body += lidl_coupon_table(lhits)

    # --- Gom theo ten mat hang, moi mat hang lay 4 sieu thi re nhat ---
    by_name = {}
    for e in entries:
        key = e["name"]
        if key not in by_name:
            by_name[key] = {"name": e["name"], "amount": e["amount"], "shops": []}
        by_name[key]["shops"].append(e)

    head_cols = ("<th style='background:#23401f;color:#9fdc8f'>✅ Rẻ nhất</th>"
                 "<th>#2</th><th>#3</th><th>#4</th>")
    out = (f"<h2>🏆 So sánh giá — {len(by_name)} mặt hàng, mọi nguồn gộp chung</h2>"
           f"<table class='mx'><tr><th style='width:26%'>Mặt hàng</th>{head_cols}</tr>")
    for key, item in by_name.items():
        ranked = sorted(item["shops"], key=lambda e: e["per"] if e["per"] else 9999999)[:4]
        amount = f" <span class='a'>{H.escape(item['amount'])}</span>" if item["amount"] else ""
        out += f"<tr><td>{icon_for(item['name'])}<b>{H.escape(item['name'])}</b>{amount}</td>"
        for i in range(4):
            if i < len(ranked):
                e = ranked[i]
                tags = "".join(
                    f" <span class='tagb' style='background:#1a3a2a;color:#9fdc8f'>{H.escape(t)}</span>"
                    for t in e["tags"])
                per_s = f"<span class='a'>({e['per']:.2f} Kč/{UNIT_SHORT[e['unit']]})</span>" if e["per"] else ""
                pct_s = f" <span class='pctb'>{H.escape(e['pct'])}</span>" if e["pct"] else ""
                cls = " class='w'" if i == 0 else ""
                out += (f"<td{cls}>{shop_badge(e['shop'])}"
                        f"<span class='mxp'>{e['price']:.2f} Kč{pct_s}</span>"
                        f"{per_s}{tags}</td>")
            else:
                out += "<td class='a'>—</td>"
        out += "</tr>"
    out += "</table>"
    body += out
    return shell(body, "")


def report_html():
    data = cena.collect_all(10)
    body = '<a class="back" href="/">← Về trang chính</a><h1>📋 Deal tuần này theo nhóm hàng</h1>'
    cat_icons = {"banh keo / snack": "🍫", "drogerie": "🧴", "pivo (lon + chai)": "🍺",
                 "do cho cho meo": "🐶🐱", "banh mi / pecivo": "🥖", "sua & trung": "🥛🥚",
                 "rau cu qua": "🥕"}
    for label, products in data.items():
        body += f"<h2>{cat_icons.get(label, '🛒')} {H.escape(label.upper())}</h2>"
        if not products:
            body += "<p>Không tải được nhóm này.</p>"
            continue
        body += ("<table><tr><th>Sản phẩm</th><th>Giá rẻ nhất</th><th>Siêu thị</th>"
                 "<th>Giảm</th><th>Giá đơn vị</th><th>Hạn</th><th>Nơi khác</th></tr>")
        for p in products:
            best = p["deals"][0]
            others = ", ".join(f'{d["shop"]} {d["price"]:.2f}' for d in p["deals"][1:4]) or "—"
            body += (f"<tr><td class='n'>{icon_for(p['name'])}{H.escape(p['name'])} <span class='a'>{H.escape(p['amount'])}</span></td>"
                     f"<td class='p'>{best['price']:.2f} Kč</td><td class='s'>{H.escape(best['shop'])}</td>"
                     f"<td class='d'>{H.escape(best['pct']) or '—'}</td><td>{H.escape(best['unit']) or '—'}</td>"
                     f"<td>{H.escape(best['valid'])}</td><td class='o'>{H.escape(others)}</td></tr>")
        body += "</table>"
    return PAGE_TOP + body + "</body></html>"


TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lidl_token.json")


def kupony_html():
    import json

    if not os.path.exists(TOKEN_FILE):
        return (PAGE_TOP + '<a class="back" href="/">← Về trang chính</a>'
                "<h1>🎟️ Kupony Lidl Plus</h1>"
                "<p>Chưa đăng nhập. Hãy <b>nháy đúp file <code>LIDL-DANGNHAP.bat</code></b> "
                "trong thư mục cena-checker (chỉ cần làm 1 lần), rồi quay lại đây bấm lại.</p></body></html>")

    from lidlplus import LidlPlusApi

    with open(TOKEN_FILE, encoding="utf-8") as f:
        token = json.load(f)["refresh_token"]
    api = LidlPlusApi("cs", "CZ", refresh_token=token)
    coupons = api.coupons()
    items = coupons.get("coupons", coupons) if isinstance(coupons, dict) else coupons

    body = '<a class="back" href="/">← Về trang chính</a><h1>🎟️ Kupony Lidl Plus của bạn</h1>'
    if not items:
        body += "<p>Không có coupon nào đang hoạt động.</p>"
    else:
        body += ("<table><tr><th></th><th>Coupon</th><th>Ưu đãi</th><th>Hạn dùng</th><th>Đã kích hoạt?</th></tr>")
        for c in items:
            if not isinstance(c, dict):
                continue
            title = c.get("title") or c.get("promotionTitle") or c.get("description") or "?"
            offer = c.get("offerTitle") or c.get("discount") or c.get("offerDescription") or ""
            valid = (c.get("endValidityDate") or c.get("validTo") or "")[:10]
            active = "✅" if c.get("isActivated") or c.get("isRedeemed") is False and c.get("isActivated") else "—"
            img = c.get("image") or c.get("imageUrl") or ""
            img_tag = f'<img src="{H.escape(img)}" width="60">' if img else ""
            body += (f"<tr><td>{img_tag}</td><td class='s'>{H.escape(str(title))}</td>"
                     f"<td class='p'>{H.escape(str(offer))}</td><td>{H.escape(str(valid))}</td>"
                     f"<td>{active}</td></tr>")
        body += "</table>"
    body += '<p class="muted">Nguồn: tài khoản Lidl Plus của bạn (API không chính thức — dùng cá nhân).</p>'
    return PAGE_TOP + body + "</body></html>"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # tat log cho gon
        pass

    def send_page(self, content: str):
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/hledej":
                q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
                self.send_page(search_html(q) if q.strip() else home_html())
            elif parsed.path == "/report":
                self.send_page(report_html())
            elif parsed.path == "/akce":
                self.send_page(akce_html())
            elif parsed.path == "/hoaqua":
                self.send_page(category_html("ovoce-a-zelenina"))
            elif parsed.path.startswith("/kategorie/"):
                self.send_page(category_html(parsed.path.split("/kategorie/", 1)[1]))
            elif parsed.path == "/banbuon":
                self.send_page(banbuon_html())
            elif parsed.path == "/gioithieu":
                self.send_page(shell(GIOITHIEU_BODY, ""))
            elif parsed.path == "/kupony":
                self.send_page("Tinh nang nay chi co o ban chay tren may ca nhan." if PUBLIC else kupony_html())
            elif parsed.path in ("/makro", "/jip"):
                slug = parsed.path[1:]
                ps = shop_products(slug)
                title, color = (("Ⓜ MAKRO", "#003b7e") if slug == "makro"
                                else ("🄹 JIP Cash & Carry", "#c8102e"))
                page = (PAGE_TOP + '<a class="back" href="/">← Về trang chính</a>'
                        f"<h1>{title} — deal nổi bật tuần này</h1>"
                        + (shop_table(ps, title, color) if ps else "<p>Không tải được dữ liệu.</p>")
                        + "</body></html>")
                self.send_page(page)
            elif parsed.path == "/tamda":
                data = load_tamda()
                if data:
                    page = (PAGE_TOP + '<a class="back" href="/">← Về trang chính</a>'
                            f"<h1>🅣 Tamda Foods — {H.escape(data['letak'])}</h1>"
                            f"<p class='muted'>{H.escape(data['note'])}</p>"
                            + tamda_table(data, data["items"]) + "</body></html>")
                else:
                    page = PAGE_TOP + "<p>Chưa có dữ liệu Tamda.</p></body></html>"
                self.send_page(page)
            elif parsed.path == "/favicon.ico":
                self.send_response(404); self.end_headers()
            else:
                self.send_page(home_html())
        except Exception as e:
            self.send_page(PAGE_TOP + f'<a href="/">← Về trang chính</a><p>Lỗi: {H.escape(str(e))}</p></body></html>')


def get_lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def main():
    # 0.0.0.0 = cho phep dien thoai cung WiFi truy cap
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    if not PUBLIC:
        threading.Timer(0.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"Cena Checker dang chay tai http://127.0.0.1:{PORT}")
    ip = get_lan_ip()
    if ip:
        print()
        print("=" * 46)
        print(f"  DIEN THOAI (cung WiFi) mo:  http://{ip}:{PORT}")
        print("=" * 46)
    print("Dong cua so nay de tat.")
    server.serve_forever()


if __name__ == "__main__":
    main()
