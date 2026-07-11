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


def vi_translate(q):
    """Dich tieng Viet (da bo dau) sang tieng Sec theo tu dien.
    Khong chi tra nguyen cum: neu ca cum khong co trong tu dien thi ghep tham lam
    tung cum con dai nhat (toi da 4 tu), tu nao khong dich duoc giu nguyen.
    Vi du: 'sua tuoi 1l' -> 'cerstve mleko 1l', 'gao thom lidl' -> 'ryze jasminova lidl'."""
    if q in VI_CS:
        return VI_CS[q]
    words = q.split()
    out, i, changed = [], 0, False
    while i < len(words):
        for k in range(min(4, len(words) - i), 0, -1):
            phrase = " ".join(words[i:i + k])
            if phrase in VI_CS:
                out.append(VI_CS[phrase])
                i += k
                changed = True
                break
        else:
            out.append(words[i])
            i += 1
    return " ".join(out) if changed else q


# Icon tu dong theo tu khoa trong ten san pham (tieng Sec, khong dau)
ICON_RULES = [
    ("banan", "🍌"), ("jablk", "🍎"), ("pomeranc", "🍊"), ("citron", "🍋"),
    ("meloun", "🍉"), ("jahod", "🍓"), ("hrozn", "🍇"), ("broskv", "🍑"),
    ("merunk", "🍑"), ("tresn", "🍒"), ("visn", "🍒"), ("svestk", "🟣"),
    ("mandarin", "🍊"), ("kiwi", "🥝"), ("ananas", "🍍"), ("mango", "🥭"),
    ("hrusk", "🍐"), ("boruvk", "🔵"), ("malin", "🍓"),
    ("avokad", "🥑"), ("rajc", "🍅"), ("brambor", "🥔"), ("mrkev", "🥕"),
    ("cibul", "🧅"), ("cesnek", "🧄"), ("okurk", "🥒"), ("salat", "🥬"),
    ("paprik", "🌶️"), ("kukuric", "🌽"),
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
    ("cukr", "🍬"), ("olej", "🌻"), ("kecup", "🍅"), ("majonez", "🥫"),
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
 :root{--bg:#ecece7;--text:#2c2c2a;--text-strong:#1c1c1a;--card:#f7f6f2;--card2:#e4e2da;
  --line:#dddbd2;--muted:#7a786f;--muted2:#8a887e;--accent:#b96a1e;--acc-strong:#8a4d10;
  --acc-bg:#f5e3cd;--acc-bg2:#efe7d8;--btn-txt:#fff;--accent-hover:#a55d15;
  --input-border:#c4b394;--chip-border:#c4c2b8;--exp-bg:#f7d4d4;--exp-txt:#8a1f1f;--gold:#8a6d1a}
 html.dark{--bg:#161614;--text:#e6e4dd;--text-strong:#f0efe8;--card:#232320;--card2:#2f2a22;
  --line:#35352f;--muted:#8f8f88;--muted2:#9a9a92;--accent:#f0a35e;--acc-strong:#f0a35e;
  --acc-bg:#3a2a15;--acc-bg2:#2e2418;--btn-txt:#161614;--accent-hover:#ffbe82;
  --input-border:#7a5a30;--chip-border:#4a4a44;--exp-bg:#5a1f1f;--exp-txt:#ffb4a8;--gold:#e8c15a}
 body{font-family:Segoe UI,Arial,sans-serif;max-width:1100px;margin:20px auto;padding:0 16px;background:var(--bg);color:var(--text)}
 a{color:var(--accent)}
 h1{color:var(--accent);margin-bottom:4px} h2{background:var(--acc-bg);color:var(--acc-strong);padding:8px 12px;border-radius:6px;margin-top:28px}
 h3{margin:24px 0 8px;color:var(--accent)}
 table{border-collapse:collapse;width:100%;background:var(--card);margin-bottom:12px;border-radius:10px;overflow:hidden}
 th{background:var(--card2);text-align:left;padding:8px;color:var(--muted)} td{padding:8px;border-top:1px solid var(--line);vertical-align:top}
 tr.best{background:var(--acc-bg)}
 .p{font-weight:bold;color:var(--acc-strong);white-space:nowrap} .s{font-weight:bold}
 .d{color:var(--acc-strong);font-weight:bold;white-space:nowrap} .a{color:var(--muted);font-size:.9em}
 .o{color:var(--muted);font-size:.85em} .n{max-width:260px}
 .searchbox{display:flex;gap:6px;margin:16px 0}
 input[type=text]{flex:1;min-width:0;font-size:1.1em;padding:10px;border:2px solid var(--input-border);border-radius:8px;background:var(--card);color:var(--text)}
 @media(max-width:600px){.searchbox button{padding:10px 12px;font-size:1em;white-space:nowrap}}
 select{background:var(--card);color:var(--text);border:1px solid var(--chip-border);border-radius:6px;padding:3px 6px}
 button,.bigbtn{font-size:1.1em;padding:12px 20px;background:var(--accent);color:var(--btn-txt);border:none;border-radius:8px;cursor:pointer;text-decoration:none;display:inline-block}
 button:hover,.bigbtn:hover{background:var(--accent-hover)}
 .chips{margin:10px 0} .chips a{display:inline-block;margin:4px 6px 0 0;padding:6px 14px;background:var(--card);border:1px solid var(--input-border);color:var(--accent);border-radius:20px;text-decoration:none;font-size:.95em}
 .chips a:hover{background:var(--acc-bg2)}
 .muted{color:var(--muted)} .muted a{color:var(--accent)}
 .back{margin-bottom:12px;display:inline-block}
 .cols{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
 .col{flex:1;min-width:340px}
 .colhead{font-size:1.2em;font-weight:bold;padding:10px 14px;border-radius:8px;color:#fff;margin-bottom:4px}
 .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:18px}
 .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
 .card .top{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px}
 .sbadge{border-radius:6px;padding:2px 8px;font-size:.78em;font-weight:bold;white-space:nowrap}
 .expb{background:var(--exp-bg);color:var(--exp-txt);border-radius:10px;padding:2px 8px;font-size:.72em;white-space:nowrap}
 .vald{font-size:.72em;color:var(--muted);white-space:nowrap}
 .card .nm{font-weight:bold;font-size:.93em;margin:0 0 2px;line-height:1.3;color:var(--text-strong)}
 .card .sub{color:var(--muted2);font-size:.78em;margin:0 0 8px;min-height:1.1em}
 .card .pr{font-size:1.45em;font-weight:bold;color:var(--acc-strong);white-space:nowrap}
 .pctb{background:var(--acc-bg);color:var(--acc-strong);border-radius:6px;padding:1px 7px;font-size:.78em;font-weight:bold}
 .chipbar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;align-items:center}
 .chipbar label{color:var(--muted)}
 .chip{border:1px solid var(--chip-border);border-radius:20px;padding:6px 14px;font-size:.88em;cursor:pointer;background:var(--card);color:var(--muted)}
 .chip.on{background:var(--acc-bg);color:var(--acc-strong);border-color:var(--acc-bg)}
 .appbar{display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--line);padding:8px 0;margin-bottom:14px;flex-wrap:wrap}
 .appbar .logo{font-size:1.15em;font-weight:bold;color:var(--accent);text-decoration:none}
 .navtabs{display:flex;gap:4px;margin-left:auto;flex-wrap:wrap}
 .navtabs a{padding:6px 13px;border-radius:8px;font-size:.92em;color:var(--muted);text-decoration:none}
 .navtabs a.on{background:var(--acc-bg);color:var(--acc-strong)}
 .navtabs a:hover{background:var(--acc-bg2);color:var(--accent)}
 #themebtn{background:none;border:1px solid var(--chip-border);color:var(--muted);border-radius:16px;padding:4px 12px;font-size:.9em;cursor:pointer}
 .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:8px;margin:14px 0}
 .catbtn{display:none;width:100%;text-align:left;background:var(--card);color:var(--accent);border:1px solid var(--input-border);border-radius:10px;padding:11px 14px;margin:14px 0 0;font-size:1em;font-weight:bold}
 @media(max-width:600px){
  .catbtn{display:none}
  .tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin:8px 0 0}
  .tiles .tile{padding:8px 2px;font-size:.7em}
  .tiles .tile .em{font-size:1.4em;margin-bottom:2px}
 }
 .tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 6px;text-align:center;text-decoration:none;color:var(--text);font-size:.85em}
 .tile:hover{border-color:var(--input-border);background:var(--acc-bg2)}
 .tile .em{font-size:1.6em;display:block;margin-bottom:4px}
 .rlist{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--card);margin-bottom:16px}
 .rrow{display:flex;align-items:center;gap:10px;padding:10px 14px;border-top:1px solid var(--line)}
 .rrow:first-child{border-top:none}
 .rrow.win{background:var(--acc-bg)}
 .rrow .rk{font-size:1.05em;font-weight:bold;color:var(--muted);min-width:24px;text-align:center}
 .rrow.win .rk{color:var(--gold)}
 .rrow .inf{flex:1;min-width:0}
 .rrow .inf p{margin:0}
 .rrow .pn{font-size:.95em;font-weight:bold;line-height:1.3;color:var(--text-strong)}
 .rrow .pm{font-size:.8em;color:var(--muted2)}
 .rrow .per{font-size:1.15em;font-weight:bold;color:var(--acc-strong);white-space:nowrap}
 .tagb{border-radius:6px;padding:1px 6px;font-size:.72em;font-weight:normal;white-space:nowrap;vertical-align:1px}
 .mx td.w{background:var(--acc-bg)}
 .mx td.w .mxp{color:var(--acc-strong);font-size:1.1em}
 .mx .mxp{display:block;font-weight:bold;color:var(--text-strong);white-space:nowrap}
 .mx a.it{color:var(--text-strong);text-decoration:none;font-weight:bold}
 .mx a.it:hover{color:var(--accent)}
 .viewtabs{display:flex;gap:6px;margin:0}
 .viewtabs button{flex:0 0 auto;font-size:.9em;padding:7px 16px;border-radius:20px;border:1px solid var(--input-border);background:var(--card);color:var(--muted);cursor:pointer}
 .viewtabs button.on{background:var(--accent);color:var(--btn-txt);border-color:var(--accent);font-weight:bold}
 .filterwrap{display:none;margin:2px 0 14px}
 .filterwrap.open{display:block}
 .storefilter{margin:8px 0 0;padding:10px 12px;border:1px solid var(--input-border);border-radius:12px;background:var(--card)}
 .strow{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin-bottom:6px}
 .stg{font-size:.82em;color:var(--muted);margin-right:4px;min-width:64px}
 .stp{font-size:.8em;padding:3px 10px;border-radius:14px;border:1px solid var(--input-border);background:var(--bg);color:var(--accent);cursor:pointer}
 .stp.off{opacity:.45;text-decoration:line-through;color:var(--muted)}
 .mxwrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
 .mxwrap table.mx{min-width:100%}
 .sfgroup{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0;align-items:center}
 .sfgroup .sfrow{display:contents}
 .sfrow .stp{font-size:.72em;padding:2px 7px}
 @media(max-width:640px){
  .sfgroup{display:block}
  .sfgroup .sfrow{display:flex;margin:3px 0;gap:3px;flex-wrap:nowrap;align-items:center}
  .sfrow .stp{flex:1 1 auto;text-align:center;padding:4px 2px}
  /* bang gia gon lai de 5 cot gan lot man dien thoai - can chi tiet thi zoom 2 ngon */
  .mx{font-size:.74em}
  .mx td, .mx th{padding:5px 3px}
  .mx td.w .mxp{font-size:1em}
  /* badge ten sieu thi PHAI duoc xuong dong ("Penny Market" -> 2 dong):
     nowrap la thu pham chinh lam bang rong 423px > man 390px */
  .sbadge{font-size:.85em;padding:1px 4px;display:inline-block;white-space:normal;line-height:1.2}
  /* trong o gia: badge / ⏰ / gia xep DOC nhu ben Ban buon -> cot hep lai */
  .mx td .expb{display:block;width:fit-content;margin:2px 0;font-size:.65em}
  .mx td .pctb{display:block;width:fit-content;font-size:.7em;padding:1px 4px;margin-top:2px}
  .mx td .vald{display:none}
 }
 .stact{margin-top:2px}
 .stact button{font-size:.78em;padding:3px 10px;margin-right:6px;border-radius:14px;border:1px solid var(--input-border);background:var(--bg);color:var(--muted);cursor:pointer}
"""

NAV_ITEMS = [("/", "Trang chủ"), ("/akce", "Akce"), ("/banbuon", "Bán buôn")]


APP_VERSION = "v7.3 · 11.07.2026"

# Quet ma vach bang camera: uu tien BarcodeDetector cua trinh duyet (nhanh, nhay),
# khong co thi dung html5-qrcode. Camera FullHD + den flash.
SCAN_JS = """
<script>
(function(){
  var btn=document.getElementById('scanbtn'), box=document.getElementById('scanbox'),
      closeBtn=document.getElementById('scanclose'),
      scanner=null, stream=null, rafId=null;
  if(!btn) return;
  // Chi hien nut camera tren dien thoai/di dong; web-may tinh an di
  var isMobile=/Android|iPhone|iPad|iPod|Mobile|Windows Phone|webOS|BlackBerry|Opera Mini|IEMobile/i.test(navigator.userAgent);
  if(!isMobile){ btn.style.display='none'; return; }
  var FORMATS=['ean_13','ean_8','upc_a','upc_e','code_128'];
  function found(code){ stop();
    window.location='/hledej?q='+encodeURIComponent(code)+(window.SCANLOC?'&loc='+window.SCANLOC:'')+(window.SCANVIEW&&window.SCANVIEW!=='all'?'&view='+window.SCANVIEW:''); }
  function stop(){
    if(rafId){ cancelAnimationFrame(rafId); rafId=null; }
    if(stream){ stream.getTracks().forEach(function(t){t.stop();}); stream=null; }
    if(scanner){ scanner.stop().catch(function(){}); scanner=null; }
    box.style.display='none';
  }
  // Duong 1: BarcodeDetector native (Android Chrome) - nhay nhat
  function startNative(){
    var det=new BarcodeDetector({formats:FORMATS});
    var v=document.createElement('video');
    v.setAttribute('playsinline',''); v.style.width='100%'; v.style.borderRadius='10px';
    document.getElementById('scanview').innerHTML=''; document.getElementById('scanview').appendChild(v);
    navigator.mediaDevices.getUserMedia({video:{facingMode:'environment',
        width:{ideal:1920},height:{ideal:1080},focusMode:'continuous'}})
      .then(function(s){
        stream=s; v.srcObject=s; v.play();
        var busy=false;
        (function loop(){
          rafId=requestAnimationFrame(loop);
          if(busy||v.readyState<2) return;
          busy=true;
          det.detect(v).then(function(codes){
            busy=false;
            if(codes.length) found(codes[0].rawValue);
          }).catch(function(){busy=false;});
        })();
      })
      .catch(function(e){ stop(); alert('Không mở được camera: '+e.message+'\\nHãy cho phép quyền camera.'); });
  }
  // Duong 2: html5-qrcode fallback (iPhone Safari...)
  function startLib(){
    scanner=new Html5Qrcode('scanview');
    scanner.start({facingMode:'environment'},
      {fps:15, qrbox:{width:300,height:180}, disableFlip:true,
       videoConstraints:{facingMode:'environment',width:{ideal:1920},height:{ideal:1080}},
       formatsToSupport:[Html5QrcodeSupportedFormats.EAN_13,Html5QrcodeSupportedFormats.EAN_8,
                         Html5QrcodeSupportedFormats.UPC_A,Html5QrcodeSupportedFormats.UPC_E,
                         Html5QrcodeSupportedFormats.CODE_128]},
      function(code){ found(code); },
      function(){}).catch(function(e){
        stop(); alert('Không mở được camera: '+e+'\\nHãy cho phép quyền camera trong trình duyệt.');
      });
  }
  btn.addEventListener('click',function(){
    box.style.display='block';
    if('BarcodeDetector' in window){
      BarcodeDetector.getSupportedFormats().then(function(fs){
        if(fs.indexOf('ean_13')>=0) startNative(); else loadLib();
      }).catch(loadLib);
    } else loadLib();
    function loadLib(){
      if(window.Html5Qrcode){ startLib(); return; }
      var s=document.createElement('script');
      s.src='https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
      s.onload=startLib;
      s.onerror=function(){ stop(); alert('Không tải được thư viện quét mã — kiểm tra mạng.'); };
      document.head.appendChild(s);
    }
  });
  closeBtn.addEventListener('click',stop);
})();
</script>"""


THEME_JS = """<script>
(function(){
  var b=document.getElementById('themebtn');
  function icon(){ b.textContent=document.documentElement.classList.contains('dark')?'☀':'🌙'; }
  b.addEventListener('click',function(){
    var d=document.documentElement.classList.toggle('dark');
    localStorage.setItem('cctheme', d?'dark':'light'); icon();
  });
  icon();
})();
</script>"""


VIEWTABS_JS = """<script>
(function(){
  var KEY='cc_view';
  var params=new URLSearchParams(location.search);
  var urlView=params.get('view');
  var view=urlView || localStorage.getItem(KEY) || 'all';
  if(urlView) localStorage.setItem(KEY, urlView);
  window.SCANVIEW=view;
  var form=document.querySelector('form.searchbox');
  if(form){ var h=document.createElement('input'); h.type='hidden'; h.name='view'; h.value=view; form.appendChild(h); }
  var box=document.getElementById('viewtabs');
  if(!box) return;
  box.querySelectorAll('button').forEach(function(b){
    if(b.getAttribute('data-v')===view) b.classList.add('on');
    b.addEventListener('click',function(){
      var v=b.getAttribute('data-v'); localStorage.setItem(KEY, v);
      var p=new URLSearchParams(location.search);
      if(p.get('q')){ p.set('view', v); location.search=p.toString(); }
      else { box.querySelectorAll('button').forEach(function(x){x.classList.remove('on');}); b.classList.add('on'); window.SCANVIEW=v; if(form){ [...form.elements].forEach(function(e){if(e.name==='view')e.value=v;}); } }
    });
  });
})();
</script>"""


STORE_GROUPS = [
    ("🏪 Bán lẻ", [("lidl", "Lidl"), ("kaufland", "Kaufland"), ("billa", "Billa"),
                   ("penny", "Penny"), ("tesco", "Tesco"), ("albert", "Albert"),
                   ("globus", "Globus"), ("coop", "COOP"), ("hruska", "Hruška"),
                   ("flop", "Flop"), ("ratio", "Ratio"), ("kosik", "Košík")]),
    ("📦 Bán buôn", [("makro", "Makro"), ("jip", "JIP"), ("tamda", "Tamda"),
                     ("bidfood", "Bidfood"), ("dathang", "dathang"),
                     ("linsan", "Linsan"), ("bombacena", "Bombacena")]),
]


def _store_filter_html():
    rows = ""
    for grp, stores in STORE_GROUPS:
        pills = "".join(
            f'<button class="stp" data-k="{k}">{H.escape(lbl)}</button>' for k, lbl in stores)
        rows += f'<div class="strow"><span class="stg">{grp}</span>{pills}</div>'
    return ('<div id="storefilter" class="storefilter">'
            + rows
            + '<div class="stact"><button id="stall">✓ Chọn hết</button>'
              '<button id="stnone">✗ Bỏ hết</button></div></div>')


STORE_FILTER_HTML = _store_filter_html()

STOREFILTER_JS = """<script>
(function(){
  var KEY='cc_hidden_shops';
  var panel=document.getElementById('filterwrap');
  var input=document.querySelector('form.searchbox input[type=text]');
  if(!panel||!input) return;
  function norm(s){ return (s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,''); }
  function hidden(){ try{return JSON.parse(localStorage.getItem(KEY)||'[]');}catch(e){return [];} }
  function save(a){ localStorage.setItem(KEY, JSON.stringify(a)); }
  function apply(){
    var h=hidden();
    document.querySelectorAll('td[data-shop]').forEach(function(td){
      var s=norm(td.getAttribute('data-shop'));
      var hide=h.some(function(k){ return s.indexOf(k)>=0; });
      if(hide){ if(!td.dataset.orig) td.dataset.orig=td.innerHTML; td.innerHTML="<span class='a'>ẩn</span>"; }
      else if(td.dataset.orig){ td.innerHTML=td.dataset.orig; td.removeAttribute('data-orig'); }
    });
  }
  function paint(){
    var h=hidden();
    panel.querySelectorAll('.stp').forEach(function(b){
      b.classList.toggle('off', h.indexOf(b.getAttribute('data-k'))>=0);
    });
  }
  panel.querySelectorAll('.stp').forEach(function(b){
    b.addEventListener('click',function(){
      var k=b.getAttribute('data-k'); var h=hidden(); var i=h.indexOf(k);
      if(i>=0) h.splice(i,1); else h.push(k);
      save(h); paint(); apply();
    });
  });
  document.getElementById('stall').addEventListener('click',function(){ save([]); paint(); apply(); });
  document.getElementById('stnone').addEventListener('click',function(){
    var all=[]; panel.querySelectorAll('.stp').forEach(function(b){ all.push(b.getAttribute('data-k')); });
    save(all); paint(); apply();
  });
  function show(){ panel.classList.add('open'); }
  function hide(){ panel.classList.remove('open'); }
  input.addEventListener('focus', show);
  input.addEventListener('click', show);
  document.addEventListener('click', function(e){
    if(!panel.contains(e.target) && e.target!==input) hide();
  });
  paint();
  window.addEventListener('load', apply);
  setTimeout(apply, 300);
})();
</script>"""


def shell(body, active="/"):
    tabs = "".join(
        f'<a href="{href}"{" class=\"on\"" if href == active else ""}>{label}</a>'
        for href, label in NAV_ITEMS)
    scanloc = "<script>window.SCANLOC='banbuon';</script>" if active == "/banbuon" else ""
    searchbar = (scanloc
                 + '<form class="searchbox" action="/hledej" method="get">'
                 + ('<input type="hidden" name="loc" value="banbuon">' if active == "/banbuon" else '')
                 + '<input type="text" name="q" autocomplete="off" autocorrect="off" '
                 'autocapitalize="off" spellcheck="false" '
                 'placeholder="Gõ mặt hàng: sữa tươi / đùi gà / gạo thơm...">'
                 '<button type="button" id="scanbtn" title="Quét mã vạch bằng camera" '
                 'style="padding:12px 16px;background:#2b5fa7">📷</button>'
                 '<button type="submit">🔍 Tìm</button></form>'
                 '<div id="filterwrap" class="filterwrap">'
                 '<div class="viewtabs" id="viewtabs">'
                 '<button data-v="all">Tất cả</button>'
                 '<button data-v="retail">🏪 Siêu thị</button>'
                 '<button data-v="wholesale">📦 Bán buôn</button></div>'
                 + STORE_FILTER_HTML + '</div>'
                 + VIEWTABS_JS + STOREFILTER_JS
                 + '<div id="scanbox" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);'
                 'z-index:9999;padding:16px;text-align:center">'
                 '<p style="color:#fff;font-size:1em;margin:6px 0">Giơ camera vào mã vạch sản phẩm</p>'
                 '<div id="scanview" style="max-width:480px;margin:0 auto;max-height:65vh;overflow:hidden"></div>'
                 '<style>#scanview video{width:100%;max-height:65vh;object-fit:cover;border-radius:10px}</style>'
                 '<button id="scanclose" style="margin-top:12px;background:#a33;padding:10px 26px">✖ Đóng</button></div>'
                 + SCAN_JS)
    return (PAGE_TOP
            + f'<div class="appbar"><a class="logo" href="/">🛒 Cena Checker</a>'
            f'<nav class="navtabs">{tabs}</nav>'
            '<button id="themebtn" title="Đổi nền sáng/tối">🌙</button></div>'
            + THEME_JS + searchbar
            + body
            + f"<p style='text-align:center;color:var(--muted2);font-size:.8em;margin:30px 0 10px'>"
              f"Cena Checker {APP_VERSION}</p></body></html>")

# Mau nhan cho tung chuoi (nen, chu)
SHOP_COLOR = [
    ("lidl", "#E6F1FB", "#0C447C"), ("kaufland", "#FAECE7", "#712B13"),
    ("billa", "#E1F5EE", "#085041"), ("penny", "#FBEAF0", "#72243E"),
    ("tesco", "#DBE4F7", "#0B2E6B"), ("albert", "#E1F5EE", "#0F6E56"),
    ("globus", "#FAEEDA", "#633806"), ("tamda", "#FFE3CC", "#8A4B00"),
    ("makro", "#DDE6F2", "#003B7E"), ("jip", "#FCEBEB", "#C8102E"),
    ("coop", "#EAF3DE", "#3B6D11"), ("dm", "#EEEDFE", "#3C3489"), ("bidfood", "#E1F5E9", "#0F6E3B"),
    ("dathang", "#FDEEE0", "#9A4B10"), ("linsan", "#FCEBEB", "#B01818"), ("bombacena", "#FBEAF0", "#93264A"),
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
<script>if(localStorage.getItem('cctheme')==='dark')document.documentElement.classList.add('dark');</script>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#161614">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Cena Checker</title><style>{CSS}</style></head><body>"""

MANIFEST = """{
 "name": "Cena Checker",
 "short_name": "CenaCheck",
 "description": "So sanh gia sieu thi Sec - quet ma vach, tim tieng Viet",
 "start_url": "/",
 "display": "standalone",
 "background_color": "#161614",
 "theme_color": "#161614",
 "icons": [{
   "src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%23161614'/%3E%3Ctext x='50' y='68' font-size='52' text-anchor='middle'%3E%F0%9F%9B%92%3C/text%3E%3C/svg%3E",
   "sizes": "any", "type": "image/svg+xml", "purpose": "any"
 }]
}"""


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


def _retail_only(prods):
    """Trang chu chi hien gia ban le: bo deal Makro/JIP/Tamda/Bidfood khoi tung san pham."""
    out = []
    for p in prods:
        deals = [d for d in p["deals"]
                 if not any(k in d["shop"].lower() for k in WHOLESALE_KEYWORDS)]
        if deals:
            q = dict(p)
            q["deals"] = deals
            out.append(q)
    return out


def home_suggestions_html():
    # Chi con "TO ROI MOI" — hang sap het akce da don vao "Mua gi o dau hom nay"
    try:
        _expiring, fresh = build_home_suggestions()
    except Exception:
        return ""
    if not fresh:
        return ""
    fprods, seen = [], set()
    for p, _ in fresh:
        if p["name"] not in seen:
            seen.add(p["name"])
            fprods.append(p)
    return product_matrix(
        _retail_only(fprods)[:15], "🆕 TỜ RƠI MỚI — deal sắp bắt đầu",
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
    "kava": ("☕", "Cà phê & trà"),
    "drogerie": ("🧴", "Drogerie"),
    "mazlicci": ("🐶🐱", "Thú cưng"),
}


_KAVA_RE = _re.compile(r"kava|kavov|caffe|espresso|cappuccino|nescafe|tchibo|jacobs|"
                       r"douwe|jihlavanka|dolce gusto|\bcaj\b|cajov|teekanne|pickwick", _re.I)


def category_html(slug):
    em, title = CAT_PAGES.get(slug, ("🛒", slug))
    products = list(shop_products(slug))
    # Kupi xep ca phe/tra vao nhom nealko-napoje -> don sang trang "Ca phe & tra"
    # (trang /kategorie/kava da co du), khoi lan 2 nhom
    if slug == "nealko-napoje":
        products = [p for p in products
                    if not _KAVA_RE.search(cena.strip_accents(p["name"]))]

    def best_pct(p):
        m = _re.search(r"(\d+)", p["deals"][0]["pct"] or "")
        return int(m.group(1)) if m else 0

    products.sort(key=best_pct, reverse=True)
    body = (f"<h1 style='font-size:1.15em'>{em} {H.escape(title)} — khuyến mãi tuần này</h1>"
            + ALLSHOP_FILTER_HTML)
    if not products:
        body += "<p>Không tải được dữ liệu — thử lại sau vài phút.</p>"
    else:
        body += product_matrix(
            products, f"{em} {len(products)} mặt hàng",
            note="Giá gói · cột ✅ = nơi rẻ nhất · (giá/đơn vị) ghi nhỏ · xếp theo mức giảm sâu nhất.")
    body += RETAIL_FILTER_JS
    active = "/hoaqua" if slug == "ovoce-a-zelenina" else ""
    return shell(body, active)


def akce_html():
    build_home_suggestions()  # dam bao cache day du
    active = _home_cache["active"]
    expiring = _home_cache["expiring"]
    fresh = _home_cache["fresh"]
    tiles = "".join(f'<a class="tile" href="{u}"><span class="em">{e}</span>{t}</a>'
                    for e, t, u in HOME_TILES)
    body = f'<div class="tiles">{tiles}</div>' + RETAIL_FILTER_HTML
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
    body += ("<h1 style='font-size:1.15em'>📢 Tổng hợp AKCE</h1>"
             "<p class='muted'>Quét từ 7 nhóm hàng chính trên Kupi, xếp theo mức giảm sâu nhất trong từng phần.</p>")
    body += RETAIL_FILTER_JS
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
    ("🌶️ Ớt chuông", "paprika", "kg"),
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


def exp_short_date(valid):
    """Ngay het han ngan gon de hien canh ⏰: 'hôm nay' / 'ngày mai' / 'DD.M.'."""
    import datetime
    v_plain = cena.strip_accents(valid or "")
    if "dnes konci" in v_plain:
        return "hôm nay"
    if "zitra konci" in v_plain:
        return "ngày mai"
    dates = _re.findall(r"(\d{1,2})\.\s*(\d{1,2})\.", valid or "")
    if not dates:
        return ""
    today = datetime.date.today()
    try:
        end = datetime.date(today.year, int(dates[-1][1]), int(dates[-1][0]))
    except ValueError:
        return ""
    if end == today:
        return "hôm nay"
    if end == today + datetime.timedelta(days=1):
        return "ngày mai"
    return f"{end.day}.{end.month}."


def build_matrix():
    """Moi hang = 1 san pham cu the (nhu TO ROI MOI): ten day du + quy cach,
    cot = cac sieu thi ban dung san pham do (kupi da gom nhom san pham)."""
    import time as _t
    if _t.time() - _matrix_cache["t"] < 86400 and _matrix_cache["rows"]:
        return _matrix_cache["rows"]
    prods, seen = [], set()
    for label, qcz, unit in STAPLES_ALL:
        try:
            soup = cena.fetch(f"{cena.BASE}/hledej?f={urllib.parse.quote(qcz)}")
        except Exception:
            continue
        for p in cena.parse_groups(soup):
            if p["name"] in seen or not p["deals"]:
                continue
            seen.add(p["name"])
            # Trang chu chi hien gia BAN LE - deal Makro/JIP/Tamda/Bidfood bo ra
            # (xem ban buon o trang /banbuon)
            p["deals"] = [d for d in p["deals"]
                          if not any(k in d["shop"].lower() for k in WHOLESALE_KEYWORDS)]
            if not p["deals"]:
                continue
            for d in p["deals"]:
                d["_exp"] = deal_expiring(d.get("valid"))
            prods.append(p)
        _t.sleep(1)
    _matrix_cache.update({"t": _t.time(), "rows": prods})
    return prods


def matrix_html():
    import random as _rand
    try:
        all_rows = build_matrix()
    except Exception:
        return ""
    if not all_rows:
        return ""
    # Hang SAP HET akce (moi danh muc) -> don chung, product_matrix se xep len dau
    exp_prods = []
    try:
        expiring, _f = build_home_suggestions()
        eseen = set()
        for p, _d in expiring:
            if p["name"] not in eseen:
                eseen.add(p["name"])
                exp_prods.append(p)
    except Exception:
        pass
    exp_names = {p["name"] for p in exp_prods}
    staples = [r for r in all_rows if r["name"] not in exp_names]
    # Hang sap het akce luon co mat (uu tien 8 mon) + do them mat hang thiet yeu
    # ngau nhien cho du ~14 dong; product_matrix xep theo % giam (khong ghim dau)
    keep_exp = exp_prods[:8]
    fill = max(0, 14 - len(keep_exp))
    picks = _rand.sample(staples, min(fill, len(staples)))
    combined = keep_exp + picks
    out = product_matrix(
        _retail_only(combined), "💡 MUA GÌ Ở ĐÂU HÔM NAY",
        note="⏰ = sắp hết akce (hôm nay/ngày mai, kèm ngày) · (giá/đơn vị) ghi nhỏ · F5 đổi mặt hàng.")
    out += "<p class='muted' style='margin-top:-4px'>Cập nhật 1 lần mỗi ngày</p>"
    return out


# Nut loc sieu thi BAN LE tren Trang chu / Akce: an/hien o gia cua sieu thi do
# trong cac bang product_matrix; hidden -> cac gia con lai tu don sang trai.
# Lua chon luu localStorage (retail_off).
def _two_rows(buttons):
    """May tinh: tat ca nut 1 hang ngang. Di dong: chia dung 2 hang can nhau
    (le thi hang tren it hon 1, vd 3+4; chan chia deu, vd 6+6)."""
    half = len(buttons) // 2
    return ("<div class='sfgroup'>"
            "<div class='sfrow'>" + "".join(buttons[:half]) + "</div>"
            "<div class='sfrow'>" + "".join(buttons[half:]) + "</div>"
            "</div>")


RETAIL_FILTER_HTML = _two_rows([f"<button class='stp' data-rshop='{k}'>{lbl}</button>"
                                for k, lbl in STORE_GROUPS[0][1]])
# Trang danh muc (Rau qua ... Thu cung): ca ban le lan ban buon
ALLSHOP_FILTER_HTML = (RETAIL_FILTER_HTML
                       + _two_rows([f"<button class='stp' data-rshop='{k}'>{lbl}</button>"
                                    for k, lbl in STORE_GROUPS[1][1]]))
RETAIL_FILTER_JS = """<script>
(function(){
  var KEY='retail_off';
  var off; try{ off=JSON.parse(localStorage.getItem(KEY)||'[]'); }catch(e){ off=[]; }
  function apply(){
    document.querySelectorAll('[data-rshop]').forEach(function(b){
      b.classList.toggle('off', off.indexOf(b.dataset.rshop)>=0);
    });
    document.querySelectorAll('td[data-shop]').forEach(function(c){
      c.style.display = c.dataset.shop && off.indexOf(c.dataset.shop)>=0 ? 'none' : '';
    });
    // mat hang het noi ban (moi o gia deu bi an) -> an ca hang
    document.querySelectorAll('tr').forEach(function(r){
      var cells=r.querySelectorAll('td[data-shop]');
      if(!cells.length) return;
      var vis=0; cells.forEach(function(c){ if(c.style.display!=='none') vis++; });
      r.style.display = vis ? '' : 'none';
    });
  }
  document.querySelectorAll('[data-rshop]').forEach(function(b){
    b.addEventListener('click', function(){
      var k=b.dataset.rshop, i=off.indexOf(k);
      if(i>=0) off.splice(i,1); else off.push(k);
      localStorage.setItem(KEY, JSON.stringify(off));
      apply();
    });
  });
  apply();
})();
</script>"""


_RETAIL_KEYS = ("lidl", "kaufland", "billa", "penny", "tesco", "albert", "globus",
                "coop", "hruska", "flop", "ratio", "kosik", "makro", "jip", "tamda",
                "bidfood", "dathang", "linsan", "bombacena")


def _shop_slug(shop):
    s = cena.strip_accents(shop.lower())
    for k in _RETAIL_KEYS:
        if k in s:
            return k
    return ""


def product_matrix(products, heading, max_cols=3, note="", show_exp=True):
    """Bang ma tran: hang = mat hang, cot = cac sieu thi re nhat (gia GOI, kem gia/don vi nho)."""
    if not products:
        return ""

    def best_pct(p):
        m = _re.search(r"(\d+)", p["deals"][0]["pct"] or "")
        return int(m.group(1)) if m else 0

    # Xep theo % giam gia manh nhat (hang sap het akce KHONG ghim len dau,
    # nam xen theo giam gia binh thuong — chi khac la co ⏰ + ngay)
    products = sorted(products, key=best_pct, reverse=True)
    head_cols = "".join(
        f"<th>{'✅ Rẻ nhất' if i == 0 else '#%d' % (i + 1)}</th>" for i in range(max_cols))
    head_cols = head_cols.replace("<th>✅ Rẻ nhất</th>",
                                  "<th style='background:var(--acc-bg);color:var(--acc-strong)'>✅ Rẻ nhất</th>")
    out = (f"<h2 style='font-size:.95em'>{heading}</h2><div class='mxwrap'>"
           + f"<table class='mx'><tr><th style='width:26%'>Mặt hàng</th>{head_cols}</tr>")
    for p in products:
        by_price = sorted(p["deals"], key=lambda d: d["price"])
        deals = by_price[:max_cols]
        # Dam bao deal SAP HET akce co mat trong cot hien thi (de ⏰ hien nhieu hon);
        # cot 1 van la re nhat, deal sap het chen vao cot cuoi neu chua co
        if show_exp and not any(d.get("_exp") for d in deals):
            ed = next((d for d in by_price if d.get("_exp")), None)
            if ed is not None and len(deals) == max_cols:
                deals = sorted(deals[:max_cols - 1] + [ed], key=lambda d: d["price"])
        amount = f" <span class='a'>{H.escape(p['amount'])}</span>" if p["amount"] else ""
        out += (f"<tr><td>{icon_for(p['name'])}<b>{H.escape(p['name'])}</b>{amount}</td>")
        for i in range(max_cols):
            if i < len(deals):
                d = deals[i]
                exp = ""
                if show_exp and d.get("_exp"):
                    _dt = exp_short_date(d.get("valid"))
                    exp = f" <span class='expb'>⏰ {H.escape(_dt)}</span>" if _dt else " <span class='expb'>⏰</span>"
                unit_small = f"<span class='a'>{H.escape(d['unit'])}</span>" if d["unit"] else ""
                pct = f" <span class='pctb'>{H.escape(d['pct'])}</span>" if d["pct"] else ""
                out += (f"<td{' class=\"w\"' if i == 0 else ''} data-shop='{_shop_slug(d['shop'])}'>"
                        f"{shop_badge(d['shop'])}{exp}"
                        f"<span class='mxp'>{d['price']:.2f} Kč{pct}</span>{unit_small}</td>")
            else:
                out += "<td class='a'>—</td>"
        out += "</tr>"
    return out + "</table></div>" + (f"<p class='muted' style='font-size:.85em'>{note}</p>" if note else "")


HOME_TILES = [
    ("🍎", "Rau quả", "/hoaqua"),
    ("🥩", "Thịt cá", "/kategorie/maso-drubez-a-ryby"),
    ("🥛", "Sữa trứng", "/kategorie/mlecne-vyrobky-a-vejce"),
    ("🍞", "Bánh mì", "/kategorie/pecivo"),
    ("🍫", "Bánh kẹo", "/kategorie/sladkosti-a-slane-snacky"),
    ("🍺", "Bia", "/kategorie/pivo"),
    ("🥤", "Đồ uống", "/kategorie/nealko-napoje"),
    ("☕", "Cà phê & trà", "/kategorie/kava"),
    ("🧴", "Drogerie", "/kategorie/drogerie"),
    ("🐶", "Thú cưng", "/kategorie/mazlicci"),
]


def home_html():
    tiles = "".join(
        f'<a class="tile" href="{u}"><span class="em">{e}</span>{t}</a>'
        for e, t, u in HOME_TILES)
    body = f"""
<div class="tiles">{tiles}</div>
{RETAIL_FILTER_HTML}
{matrix_html()}
{home_suggestions_html()}
<p class="muted" style="margin-top:24px">So sánh giá siêu thị Séc — gõ tiếng Việt có dấu hoặc không dấu đều được.<br>Nguồn tham khảo: kupi.cz, tamdafoods.eu, makro.cz, jip-eshop.cz, mujbidfood.cz · <a href="/gioithieu">Giới thiệu &amp; miễn trừ trách nhiệm</a></p>
{RETAIL_FILTER_JS}"""
    return shell(body, "/")


_BB_STOP = {"a", "s", "v", "z", "na", "do", "od", "po", "the", "cca", "kus", "ks",
            "kg", "g", "l", "ml", "balení", "baleni",
            # tu mo ta chung chung - khong duoc tinh la "trung ten" khi ghep hang
            # (vd "Red Bull sugar free" tung ghep nham "Mizu guarana sugar free")
            "sugar", "free", "zero", "light", "bez", "cukru", "original", "classic",
            "edition", "style", "plech", "sklo", "pet", "mini", "maxi", "extra",
            "premium", "fresh", "new", "novy", "nova", "mraz", "mrazene", "cerstve",
            "cerstvy", "vaz", "susene", "instantni", "svetly", "lezak", "vycepni",
            "tmavy", "polotmavy", "nealko", "nealkoholicke"}


def _bb_tokens(name):
    """Tu khoa chinh cua ten hang (bo dau, bo so luong/don vi) de ghep hang giua cac kho."""
    n = cena.strip_accents(name.lower())
    n = _re.sub(r"[\d]+[,.]?\d*\s*(kg|g|l|ml|ks|%)?", " ", n)
    return {w for w in _re.split(r"[^a-z]+", n) if len(w) >= 3 and w not in _BB_STOP}


# Tu "chung chung" theo du lieu: xuat hien trong >=150 san pham thi khong du
# dac trung de ghep 2 mat hang (pivo, kava, praci, prasek, mango, ice...).
_bb_df_cache = {"built": False, "generic": set()}


def _bb_generic():
    if _bb_df_cache["built"]:
        return _bb_df_cache["generic"]
    import collections
    import json
    cnt = collections.Counter()
    here = os.path.dirname(os.path.abspath(__file__))
    for fn in ("tamda_full_prices.json", "makro_full_prices.json", "bidfood_prices.json",
               "dathang_prices.json", "linsan_prices.json", "bombacena_prices.json"):
        try:
            with open(os.path.join(here, fn), encoding="utf-8") as f:
                for it in json.load(f)["items"]:
                    for t in _bb_tokens(it["name"]):
                        cnt[t] += 1
        except Exception:
            pass
    _bb_df_cache["generic"] = {t for t, c in cnt.items() if c >= 150}
    _bb_df_cache["counts"] = dict(cnt)
    _bb_df_cache["built"] = True
    return _bb_df_cache["generic"]


def _bb_match(t1, t2):
    """2 mat hang coi la trung khi chung >=2 tu khoa (hoac tap nho nam tron trong
    tap lon), TRONG DO it nhat 1 tu phai la tu dac trung hiem (ten hang/san pham),
    khong tinh tu chung chung nhu pivo/kava/praci/mango (xem _bb_generic)."""
    if not t1 or not t2:
        return False
    common = t1 & t2
    if not common - _bb_generic():
        return False
    # luat "mo neo": tu hiem nhat cua ten (thuong la ten hang) phai trung -
    # chan kieu Nivea Sun spray ghep Airwick Sun spray (chi trung tu phu)
    cnt = _bb_df_cache.get("counts", {})
    a1 = min(t1, key=lambda t: cnt.get(t, 0))
    a2 = min(t2, key=lambda t: cnt.get(t, 0))
    if a1 not in common and a2 not in common:
        return False
    small = min(t1, t2, key=len)
    return len(common) >= 2 or (len(common) >= 1 and common == small)


def _amt_parse(a):
    """Doc quy cach: '1 kg' -> (1000,'g'); ho tro loc/thung 'N x ...' ('6 x 1 l' -> (6000,'ml'))."""
    s = (a or "").lower().replace(",", ".")
    m = _re.search(r"(?:(\d+)\s*[x×]\s*)?(\d+[.]?\d*)\s*(kg|g|l|ml|ks)\b", s)
    if not m:
        return None
    mult = int(m.group(1)) if m.group(1) else 1
    v, u = float(m.group(2)) * mult, m.group(3)
    if u == "kg":
        v, u = v * 1000, "g"
    elif u == "l":
        v, u = v * 1000, "ml"
    return (v, u)


def _merge_ok(t1, a1, t2, a2):
    """Dieu kien ghep 2 mat hang giua 2 kho: ten trung (_bb_match) + quy cach khop
    (ke ca loc/thung: 6 x 1 l != 1 l). Neu 1 trong 2 ben KHONG doc duoc quy cach
    (vape, '5 davek', 'dle vahy'...) thi chi ghep khi ten trung RAT manh
    (>=2 tu dac trung hiem chung) - tha de trong con hon ghep sai gia."""
    if not _bb_match(t1, t2):
        return False
    p1, p2 = _amt_parse(a1), _amt_parse(a2)
    if p1 and p2:
        return p1 == p2
    return len((t1 & t2) - _bb_generic()) >= 2


def banbuon_html(page=1):
    # Khoi gioi thieu chuyen xuong CUOI trang (yeu cau nguoi dung) - dau trang
    # danh cho nut chon kho + bang, mo trang la thay hang ngay.
    intro = ("<h1 style='font-size:1.15em'>📦 Bán buôn — Tamda / Makro / JIP / Bidfood / dathang / Linsan / Bombacena</h1>"
             "<p class='muted'>Giá gói · (giá/đơn vị) ghi nhỏ · ô xanh ✅ = kho rẻ nhất khi có "
             "cùng mặt hàng ở nhiều kho. <b>Tất cả giá đã gồm DPH (s DPH)</b>. "
             "Tamda = giá với thẻ (tờ rơi tuần), hoặc giá thường từ Tamda Express "
             "khi hàng không có trong tờ rơi · dathang/Linsan/Bombacena = hàng châu Á.</p>")
    tiles = "".join(f'<a class="tile" href="{u}"><span class="em">{e}</span>{t}</a>'
                    for e, t, u in HOME_TILES)
    body = f'<div class="tiles">{tiles}</div>'

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
            hit = next((x for x in items if col not in x["offers"]
                        and _merge_ok(x["toks"], x["amount"], toks, p["amount"])), None)
            if hit:
                hit["offers"][col] = offer
            else:
                items.append({"name": p["name"], "amount": p["amount"],
                              "toks": toks, "offers": {col: offer}})
    # Bidfood: chi ghep vao mat hang da co (4300+ items, khong liet ke rieng)
    bdata = load_bidfood()
    if bdata:
        for it in bdata["items"]:
            toks = _bb_tokens(it["name"])
            hit = next((x for x in items if "bidfood" not in x["offers"]
                        and _merge_ok(x["toks"], x["amount"], toks, it.get("amount", ""))), None)
            if hit:
                hit["offers"]["bidfood"] = {"shop": "Bidfood", "price": it["price"],
                                            "pct": it.get("pct", ""), "unit": "",
                                            "amount": it.get("amount", "")}

    # 3 nha do hang Viet (dathang, Linsan, Bombacena): liet ke rieng cac mat hang
    # cua ho (khong chi ghep vao hang co san) vi day la nguon hang chau A dac thu
    vn_extra_cols = []
    for slug, shopname in VN_SHOPS:
        vdata = load_vnshop(slug)
        if not vdata:
            continue
        vn_extra_cols.append((slug, shopname))
        for it in vdata["items"]:
            toks = _bb_tokens(it["name"])
            hit = next((x for x in items if slug not in x["offers"]
                        and _merge_ok(x["toks"], x["amount"], toks, it.get("amount", ""))), None)
            if hit:
                hit["offers"][slug] = {"shop": shopname, "price": it["price"],
                                       "pct": "", "unit": it.get("unit", ""),
                                       "amount": it.get("amount", "")}
            else:
                items.append({"name": it["name"], "amount": it.get("amount", ""),
                              "toks": toks, "offers": {slug: {
                                  "shop": shopname, "price": it["price"], "pct": "",
                                  "unit": it.get("unit", ""), "amount": it.get("amount", "")}}})

    # Catalog day du (Tamda Express ~17k, Makro sortiment ~19k): gia THUONG s DPH.
    # Chi DIEN vao cot con trong cua hang da co deal (khong them chuc nghin hang moi
    # lam nang trang) - muon xem mat hang bat ky thi dung o tim kiem, da tra du catalog.
    def fill_from_catalog(data, col, shopname):
        if not data:
            return
        idx = data.get("_tok_index")
        if idx is None:
            idx = {}
            for it in data["items"]:
                it["_toks"] = _bb_tokens(it["name"])
                for t in it["_toks"]:
                    idx.setdefault(t, []).append(it)
            data["_tok_index"] = idx
        for x in items:
            if col in x["offers"]:
                continue
            cands = {id(it): it for t in x["toks"] for it in idx.get(t, [])}
            it = next((m for m in cands.values()
                       if _merge_ok(x["toks"], x.get("amount"), m["_toks"], m.get("amount"))), None)
            if it is None:
                continue
            x["offers"][col] = {"shop": shopname, "price": it["price"], "pct": "",
                                "unit": it.get("unit", ""), "amount": it.get("amount", "")}

    fill_from_catalog(load_tamda_full(), "tamda", "Tamda Foods")
    fill_from_catalog(load_makro_full(), "makro", "Makro")

    if not items:
        return shell(body + "<p class='muted'>Chưa có dữ liệu bán buôn.</p>", "/banbuon")

    # Hang co o >=2 kho len dau, sau do theo % giam gia
    def sort_key(x):
        pcts = [int(m.group(1)) for o in x["offers"].values()
                for m in [_re.search(r"(\d+)", o["pct"] or "")] if m]
        return (-len(x["offers"]), -(max(pcts) if pcts else 0))

    items.sort(key=sort_key)
    ncmp = sum(1 for x in items if len(x["offers"]) >= 2)
    # Phan trang: 30 mat hang/trang, day so trang de mo tiep
    PER_PAGE = 30
    npages = max(1, (len(items) + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, npages))
    page_items = items[(page - 1) * PER_PAGE: page * PER_PAGE]

    def pager():
        if npages <= 1:
            return ""
        nums = sorted({1, 2, npages - 1, npages,
                       page - 2, page - 1, page, page + 1, page + 2}
                      & set(range(1, npages + 1)))
        parts, prev = [], 0
        for n in nums:
            if n - prev > 1:
                parts.append("<span class='a'>…</span>")
            if n == page:
                parts.append(f"<b style='padding:6px 10px'>{n}</b>")
            else:
                parts.append(f"<a href='/banbuon?p={n}' style='padding:6px 10px'>{n}</a>")
            prev = n
        return ("<p style='text-align:center;font-size:1.1em'>"
                + ("" if page == 1 else f"<a href='/banbuon?p={page - 1}' style='padding:6px 10px'>‹ Trước</a>")
                + "".join(parts)
                + ("" if page == npages else f"<a href='/banbuon?p={page + 1}' style='padding:6px 10px'>Sau ›</a>")
                + "</p>")

    valid_s = f" · Tamda: {H.escape(data['valid'])}" if data else ""
    all_cols = [("tamda", "🅣 Tamda", "#e8681a"), ("makro", "Ⓜ Makro", "#3a7bc0"),
                ("jip", "🄹 JIP", "#c8102e")]
    if bdata:
        all_cols.append(("bidfood", "🅑 Bidfood", "#1d9e75"))
    vn_icons = {"dathang": "🅳 dathang", "linsan": "🅻 Linsan", "bombacena": "🅱 Bombacena"}
    for slug, shopname in vn_extra_cols:
        all_cols.append((slug, vn_icons.get(slug, shopname), "#c8102e"))
    col_keys = [c[0] for c in all_cols]
    # Nut loc kho: bat/tat cot truc tiep tren trang, khong can qua khung tim.
    # Lua chon luu localStorage (bb_cols_off) - lan sau mo lai van giu.
    filter_html = _two_rows([f"<button class='stp' data-bbcol='{c[0]}'>{c[1]}</button>"
                             for c in all_cols])
    filter_js = """<script>
(function(){
  var KEY='bb_cols_off';
  var off; try{ off=JSON.parse(localStorage.getItem(KEY)||'[]'); }catch(e){ off=[]; }
  function apply(){
    document.querySelectorAll('[data-bbcol]').forEach(function(b){
      b.classList.toggle('off', off.indexOf(b.dataset.bbcol)>=0);
    });
    document.querySelectorAll('td[data-shop]').forEach(function(c){
      c.style.display = off.indexOf(c.dataset.shop)>=0 ? 'none' : '';
    });
    // mat hang het noi ban (moi o gia deu bi an) -> an ca hang
    document.querySelectorAll('tr').forEach(function(r){
      var cells=r.querySelectorAll('td[data-shop]');
      if(!cells.length) return;
      var vis=0; cells.forEach(function(c){ if(c.style.display!=='none') vis++; });
      r.style.display = vis ? '' : 'none';
    });
  }
  document.querySelectorAll('[data-bbcol]').forEach(function(b){
    b.addEventListener('click', function(){
      var k=b.dataset.bbcol, i=off.indexOf(k);
      if(i>=0) off.splice(i,1); else off.push(k);
      localStorage.setItem(KEY, JSON.stringify(off));
      apply();
    });
  });
  apply();
})();
</script>"""
    stats = (f"<p class='muted' style='font-size:.8em;margin:2px 0'>📦 {len(items)} mặt hàng"
             f" · {ncmp} có ở ≥2 kho{valid_s} · trang {page}/{npages}</p>")
    MAXC = 3  # giong Trang chu/Akce nhung 3 cot: ✅ Re nhat / #2 / #3
    head_cols = ("<th style='background:var(--acc-bg);color:var(--acc-strong)'>✅ Rẻ nhất</th>"
                 + "".join(f"<th>#{i + 2}</th>" for i in range(MAXC - 1)))
    shop_of = {"tamda": "Tamda Foods", "makro": "Makro", "jip": "JIP", "bidfood": "Bidfood",
               "dathang": "dathang", "linsan": "Linsan", "bombacena": "Bombacena"}
    body += (filter_html + pager()
             + "<div class='mxwrap'><table class='mx'><tr><th style='width:26%'>Mặt hàng</th>"
             + head_cols + "</tr>")
    for x in page_items:
        amount = f" <span class='a'>{H.escape(x['amount'])}</span>" if x["amount"] else ""
        body += f"<tr><td>{icon_for(x['name'])}<b>{H.escape(x['name'])}</b>{amount}</td>"
        ranked = sorted(x["offers"].items(), key=lambda co: co[1]["price"])[:MAXC]
        for i in range(MAXC):
            if i >= len(ranked):
                body += "<td class='a'>—</td>"
                continue
            col, o = ranked[i]
            pu = parse_amount_price(o["amount"], o["price"])
            per_s = (f"<span class='a'>({pu[0]:.2f} Kč/{UNIT_SHORT[pu[1]]})</span>" if pu
                     else (f"<span class='a'>{H.escape(o['unit'])}</span>" if o["unit"] else ""))
            pct = f" <span class='pctb'>{H.escape(o['pct'])}</span>" if o["pct"] else ""
            exp = " <span class='expb'>⏰</span>" if o.get("_exp") else ""
            win = " class='w'" if i == 0 else ""
            body += (f"<td{win} data-shop='{col}'>{shop_badge(shop_of.get(col, o['shop']))}{exp}"
                     f"<span class='mxp'>{o['price']:.2f} Kč{pct}</span>{per_s}</td>")
        body += "</tr>"
    body += ("</table></div><p class='muted' style='margin-top:-4px'>"
             "Makro/JIP: deal từ kupi.cz · chỉ ghép khi trùng quy cách gói.</p>") + pager() + stats + intro + filter_js
    return shell(body, "/banbuon")


GIOITHIEU_BODY = """
<h1>ℹ️ Giới thiệu</h1>
<p><b>Cena Checker</b> là công cụ phi lợi nhuận giúp cộng đồng người Việt tại Séc so sánh
giá khuyến mãi giữa các siêu thị bán lẻ (Kaufland, Lidl, Billa, Penny, Tesco, Albert, Globus...)
và bán buôn (Tamda Foods, Makro, JIP, Bidfood). Hỗ trợ tìm kiếm bằng tiếng Việt có dấu hoặc
không dấu, và quét mã vạch sản phẩm bằng camera điện thoại.</p>
<h2>Miễn trừ trách nhiệm</h2>
<p>· Dữ liệu giá được tổng hợp tự động từ các nguồn công khai (kupi.cz, tờ rơi chính thức của
các chuỗi) và <b>chỉ mang tính tham khảo</b> — giá thực tế tại cửa hàng có thể khác.<br>
· Trang này <b>không liên kết, không đại diện</b> cho Kupi.cz, Tamda Foods, Makro, JIP,
Bidfood, Lidl hay bất kỳ chuỗi siêu thị nào.<br>
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


BIDFOOD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bidfood_prices.json")


def load_bidfood():
    import json
    if not os.path.exists(BIDFOOD_FILE):
        return None
    with open(BIDFOOD_FILE, encoding="utf-8") as f:
        return json.load(f)


def bidfood_matches(query_cs):
    data = load_bidfood()
    if not data:
        return None, []
    q = cena.strip_accents(query_cs.lower())
    hits = [it for it in data["items"]
            if all(w in cena.strip_accents(it["name"].lower()) for w in q.split())]
    return data, hits


# Cac shop Viet/chau A: file JSON {shop, items:[{name, price, amount, unit}]}.
# Ten hang co the la tieng Viet (bun, banh trang...) hoac tieng Sec.
VN_SHOPS = [
    ("dathang", "dathang.cz"),
    ("linsan", "Linsan24h"),
    ("bombacena", "Bombacena"),
]
_vnshop_cache = {}


def load_vnshop(slug):
    import json
    import time as _t
    c = _vnshop_cache.get(slug)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{slug}_prices.json")
    if c and _t.time() - c[0] < 600:
        return c[1]
    data = None
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
    _vnshop_cache[slug] = (_t.time(), data)
    return data


def vnshop_matches(slug, query_raw, query_cs):
    """Khop ca tu khoa goc (tieng Viet khong dau) lan ban dich tieng Sec."""
    data = load_vnshop(slug)
    if not data:
        return None, []
    terms = []
    for qq in (query_raw, query_cs):
        w = [x for x in cena.strip_accents(qq.lower()).split() if x]
        if w:
            terms.append(w)
    hits = []
    for it in data["items"]:
        n = cena.strip_accents(it["name"].lower())
        if any(all(x in n for x in ws) for ws in terms):
            hits.append(it)
    return data, hits


_tamda_full_cache = {"t": 0, "data": None}


def load_tamda_full():
    """Catalog day du Tamda Express (tamdaexpress.eu, can dang nhap) - gia thuong,
    khong chi tuan flyer. File nay co truong 'ean' de tra chinh xac theo ma vach."""
    import json
    import time as _t
    if _tamda_full_cache["data"] and _t.time() - _tamda_full_cache["t"] < 600:
        return _tamda_full_cache["data"]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tamda_full_prices.json")
    data = None
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["_ean_index"] = {it["ean"]: it for it in data["items"] if it.get("ean")}
        except Exception:
            data = None
    _tamda_full_cache["t"] = _t.time()
    _tamda_full_cache["data"] = data
    return data


def tamda_full_ean_price(code):
    """Tra gia CHINH XAC theo ma vach tu catalog Tamda Express (khong qua fuzzy-match ten)."""
    data = load_tamda_full()
    if not data:
        return None
    idx = data.get("_ean_index", {})
    for c in ean_variants(code):
        if c in idx:
            return idx[c]
    return None


def _catalog_matches(data, query_raw, query_cs):
    if not data:
        return None, []
    terms = []
    for qq in (query_raw, query_cs):
        w = [x for x in cena.strip_accents(qq.lower()).split() if x]
        if w:
            terms.append(w)
    hits = []
    for it in data["items"]:
        n = cena.strip_accents(it["name"].lower())
        if any(all(x in n for x in ws) for ws in terms):
            hits.append(it)
    return data, hits


def tamda_full_matches(query_raw, query_cs):
    return _catalog_matches(load_tamda_full(), query_raw, query_cs)


_makro_full_cache = {"t": 0, "data": None}


def load_makro_full():
    """Catalog day du sortiment.makro.cz (~19k mat hang) - gia THUONG s DPH
    (API tra gia net, script thu_gia_makro.py da tinh 12%/21%). Co truong 'ean'."""
    import json
    import time as _t
    if _makro_full_cache["data"] and _t.time() - _makro_full_cache["t"] < 600:
        return _makro_full_cache["data"]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "makro_full_prices.json")
    data = None
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["_ean_index"] = {it["ean"]: it for it in data["items"] if it.get("ean")}
        except Exception:
            data = None
    _makro_full_cache["t"] = _t.time()
    _makro_full_cache["data"] = data
    return data


def makro_full_ean_price(code):
    data = load_makro_full()
    if not data:
        return None
    idx = data.get("_ean_index", {})
    for c in ean_variants(code):
        if c in idx:
            return idx[c]
    return None


def makro_full_matches(query_raw, query_cs):
    return _catalog_matches(load_makro_full(), query_raw, query_cs)


def tamda_table(data, items):
    cards = "".join(
        deal_card(it["name"], it["amount"], "Tamda Foods", it["price"],
                  valid=f"thẻ Tamda · {data['valid']}")
        for it in items)
    return (f"<h2 style='background:#e8681a'>🅣 TAMDA FOODS <span style='font-weight:normal;font-size:.8em'>"
            f"(giá với thẻ Tamda · {H.escape(data['valid'])})</span></h2>"
            f"<div class='cards'>{cards}</div>")


# Cac chuoi BAN BUON: tach khoi cot ban le
WHOLESALE_KEYWORDS = ("jip", "makro", "tamda", "bidfood")
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


def ean_variants(code):
    """Cac bien the cua ma vach go tay: 12 so co the la EAN-13 thieu so kiem tra
    (tu tinh va them vao) hoac UPC-A (them so 0 dau); 14 so GTIN bo so 0 dau."""
    out = [code]
    if len(code) == 12:
        s = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(code))
        out.append(code + str((10 - s % 10) % 10))  # EAN-13 = 12 so + so kiem tra
        out.append("0" + code)                       # UPC-A -> EAN-13
    if len(code) == 14 and code[0] == "0":
        out.append(code[1:])
    if len(code) == 13 and code[0] == "0":
        out.append(code[1:])
    return out


def ean_lookup(code):
    """Tra ma vach EAN: database rieng truoc, roi Open Food Facts, UPCitemdb."""
    import requests as _req
    # 0) Database rieng (thu thap tu Makro GTIN)
    try:
        import json as _json
        with open(EAN_DB_FILE, encoding="utf-8") as f:
            items = _json.load(f)["items"]
        for c in ean_variants(code):
            it = items.get(c)
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




def ean_name_variants(name):
    """Cac bien the tu khoa tu ten san pham EAN: bo khoi luong/dung tich, rut ngan dan."""
    n = _re.sub(r"\b\d+[,.]?\d*\s*(g|kg|ml|l|ks|x)\b\.?", " ", name, flags=_re.I)
    n = _re.sub(r"[()%/]", " ", n)
    words = n.split()
    out = []
    for k in (len(words), 3, 2, 1):
        if 0 < k <= len(words):
            v = " ".join(words[:k])
            if v and v not in out:
                out.append(v)
    return out


def search_html(query, only="", view="all"):
    if only == "banbuon":
        view = "wholesale"
    raw_query = query.strip()
    ean_name = None
    if _re.fullmatch(r"\d{8,14}", raw_query):
        ean_name = ean_lookup(raw_query)
    q = cena.strip_accents((ean_name or raw_query).lower())
    q = vi_translate(q)
    soup = cena.fetch(f"{cena.BASE}/hledej?f={urllib.parse.quote(q)}")
    products = cena.parse_groups(soup)
    tdata, thits = tamda_matches(q)
    mhits = shop_matches("makro", q)
    jhits = shop_matches("jip", q)
    tesco_data, tesco_hits = tesco_matches(q)
    lhits = lidl_coupon_matches(q)
    bdata, bhits = bidfood_matches(q)
    raw_norm = cena.strip_accents(raw_query.lower())
    vnhits = {slug: vnshop_matches(slug, raw_norm, q)[1] for slug, _ in VN_SHOPS}
    any_vn = any(vnhits.values())
    tfdata, tfhits = tamda_full_matches(raw_norm, q)
    mfdata, mfhits = makro_full_matches(raw_norm, q)
    # Tra CHINH XAC theo ma vach trong catalog day du (khong phu thuoc ten
    # rut gon co khop hay khong) - giai quyet ca truong hop ten EAN qua chi tiet/la.
    is_ean = bool(_re.fullmatch(r"\d{8,14}", raw_query))
    ean_price_hit = tamda_full_ean_price(raw_query) if is_ean else None
    makro_ean_hit = makro_full_ean_price(raw_query) if is_ean else None

    # Ten EAN thuong qua chi tiet (kem 75g, 500ml...) -> khong ra gia.
    # Thu rut gon dan cho den khi co ket qua.
    if ean_name and not (products or thits or mhits or jhits or tesco_hits or lhits or bhits
                         or any_vn or tfhits or mfhits or ean_price_hit or makro_ean_hit):
        for variant in ean_name_variants(ean_name)[1:]:
            q2 = cena.strip_accents(variant.lower())
            try:
                soup = cena.fetch(f"{cena.BASE}/hledej?f={urllib.parse.quote(q2)}")
                products = cena.parse_groups(soup)
            except Exception:
                products = []
            tdata, thits = tamda_matches(q2)
            mhits = shop_matches("makro", q2)
            jhits = shop_matches("jip", q2)
            tesco_data, tesco_hits = tesco_matches(q2)
            lhits = lidl_coupon_matches(q2)
            bdata, bhits = bidfood_matches(q2)
            vnhits = {slug: vnshop_matches(slug, raw_norm, q2)[1] for slug, _ in VN_SHOPS}
            any_vn = any(vnhits.values())
            tfdata, tfhits = tamda_full_matches(raw_norm, q2)
            mfdata, mfhits = makro_full_matches(raw_norm, q2)
            if (products or thits or mhits or jhits or tesco_hits or lhits or bhits
                    or any_vn or tfhits or mfhits):
                q = q2
                break

    # --- Gom MOI nguon vao 1 danh sach hop nhat ---
    entries = []
    _seenE = set()

    def addE(name, amount, shop, price, valid="", pct="", unitstr="", tags=(), typ="retail"):
        # khu trung lap: cung shop + cung gia + cung ten thi chi hien 1 lan
        try:
            key = (shop.lower(), round(float(price), 2), cena.strip_accents(name.lower()))
        except (ValueError, TypeError):
            key = (shop.lower(), str(price), cena.strip_accents(name.lower()))
        if key in _seenE:
            return
        _seenE.add(key)
        pu = parse_unit_price(unitstr) if unitstr else None
        if pu is None:
            pu = parse_amount_price(amount, price)
        tags = list(tags)
        if typ == "wholesale" and "s DPH" not in tags:
            tags.append("s DPH")
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
    for it in bhits[:20]:
        addE(it["name"], it.get("amount", ""), "Bidfood", it["price"],
             pct=it.get("pct", ""), tags=["bán buôn"], typ="wholesale")
    for slug, shopname in VN_SHOPS:
        for it in vnhits.get(slug, [])[:20]:
            addE(it["name"], it.get("amount", ""), shopname, it["price"],
                 unitstr=it.get("unit", ""), tags=["hàng Việt"], typ="wholesale")
    tf_names_added = set()
    for it in tfhits[:20]:
        addE(it["name"], it.get("amount", ""), "Tamda Foods", it["price"],
             unitstr=it.get("unit", ""), tags=["bán buôn"], typ="wholesale")
        tf_names_added.add(it["name"])
    if ean_price_hit and ean_price_hit["name"] not in tf_names_added:
        addE(ean_price_hit["name"], ean_price_hit.get("amount", ""), "Tamda Foods",
             ean_price_hit["price"], unitstr=ean_price_hit.get("unit", ""),
             tags=["bán buôn"], typ="wholesale")
    mf_names_added = set()

    def _mf_tags(it):
        # DPH Makro co ngoai le 12/21% kho doan chinh xac -> hien kem gia net de doi chieu
        net = it.get("price_net")
        return ["bán buôn"] + ([f"bez DPH {net:.2f}"] if net else [])

    for it in mfhits[:20]:
        addE(it["name"], it.get("amount", ""), "Makro", it["price"],
             unitstr=it.get("unit", ""), tags=_mf_tags(it), typ="wholesale")
        mf_names_added.add(it["name"])
    if makro_ean_hit and makro_ean_hit["name"] not in mf_names_added:
        addE(makro_ean_hit["name"], makro_ean_hit.get("amount", ""), "Makro",
             makro_ean_hit["price"], unitstr=makro_ean_hit.get("unit", ""),
             tags=_mf_tags(makro_ean_hit), typ="wholesale")

    # Loc theo view: retail (sieu thi ban le) / wholesale (ban buon) / all
    if view == "retail":
        entries = [e for e in entries if e["typ"] == "retail"]
    elif view == "wholesale":
        entries = [e for e in entries if e["typ"] == "wholesale"]
        lhits = []
    else:
        # che do Tat ca: gan nhan phan biet le/buon
        for e in entries:
            lbl = "📦 buôn" if e["typ"] == "wholesale" else "🏪 lẻ"
            if lbl not in e["tags"]:
                e["tags"] = [lbl] + [t for t in e["tags"] if t not in ("bán buôn", "hàng Việt")]

    body = f"<h1>Kết quả: {H.escape(query)}</h1>"
    if view == "retail":
        body += '<p class="muted">🏪 Đang hiện <b>giá siêu thị (bán lẻ)</b> — đổi bằng nút phía trên.</p>'
    elif view == "wholesale":
        body += '<p class="muted">📦 Đang hiện <b>giá bán buôn</b> (Makro/JIP/Tamda/Bidfood/dathang/Linsan) — đổi bằng nút phía trên.</p>'
    if ean_name:
        body += f'<p class="muted">📦 Mã vạch nhận diện: <b>{H.escape(ean_name)}</b> → tìm giá <b>{H.escape(q)}</b></p>'
    elif q != cena.strip_accents(raw_query.lower()):
        body += f'<p class="muted">(tự dịch sang tiếng Séc: <b>{H.escape(q)}</b>)</p>'
    if not entries:
        body += "<p>Không tìm thấy gì. Thử từ khác hoặc tên tiếng Séc?</p>"
        return shell(body, "/banbuon" if only == "banbuon" else "")

    if lhits:
        body += lidl_coupon_table(lhits)

    # --- Gom theo ten mat hang, moi mat hang lay 4 sieu thi re nhat ---
    by_name = {}
    for e in entries:
        key = e["name"]
        if key not in by_name:
            by_name[key] = {"name": e["name"], "amount": e["amount"], "shops": []}
        by_name[key]["shops"].append(e)

    def render_table(items, heading):
        head_cols = ("<th style='background:var(--acc-bg);color:var(--acc-strong)'>✅ Rẻ nhất</th>"
                     "<th>#2</th><th>#3</th>")
        out = (f"<h2>{heading}</h2>"
               f"<div class='mxwrap'><table class='mx'><tr><th style='width:26%'>Mặt hàng</th>{head_cols}</tr>")
        for item in items:
            ranked = sorted(item["shops"], key=lambda e: e["per"] if e["per"] else 9999999)[:3]
            amount = f" <span class='a'>{H.escape(item['amount'])}</span>" if item["amount"] else ""
            out += f"<tr><td>{icon_for(item['name'])}<b>{H.escape(item['name'])}</b>{amount}</td>"
            for i in range(3):
                if i < len(ranked):
                    e = ranked[i]
                    tags = "".join(
                        f" <span class='tagb' style='background:var(--acc-bg);color:var(--acc-strong)'>{H.escape(t)}</span>"
                        for t in e["tags"])
                    per_s = f"<span class='a'>({e['per']:.2f} Kč/{UNIT_SHORT[e['unit']]})</span>" if e["per"] else ""
                    pct_s = f" <span class='pctb'>{H.escape(e['pct'])}</span>" if e["pct"] else ""
                    cls = " class='w'" if i == 0 else ""
                    out += (f"<td{cls} data-shop=\"{H.escape(e['shop'])}\">{shop_badge(e['shop'])}"
                            f"<span class='mxp'>{e['price']:.2f} Kč{pct_s}</span>"
                            f"{per_s}{tags}</td>")
                else:
                    out += "<td class='a'>—</td>"
            out += "</tr>"
        return out + "</table></div>"

    items = list(by_name.values())
    if ean_name:
        # Tach: dung san pham quet (ten chua du tu khoa chinh) / hang tuong tu
        _STOP = {"a", "s", "v", "z", "the", "и"}
        toks = [w for w in cena.strip_accents(
                    _re.sub(r"\b\d+[,.]?\d*\s*(g|kg|ml|l|ks|x)\b\.?", " ", ean_name, flags=_re.I).lower()
                ).split() if len(w) >= 3 and w not in _STOP]

        def hits(nm):
            n = cena.strip_accents(nm.lower())
            return sum(1 for t in toks if t in n)

        # "Dung san pham" = nhom khop nhieu tu khoa nhat (it nhat 2 tu,
        # hoac khop het khi ten chi co 1 tu)
        scores = {it["name"]: hits(it["name"]) for it in items}
        max_hit = max(scores.values()) if scores else 0
        threshold_ok = toks and (max_hit >= 2 or max_hit == len(toks))
        ean_norm = cena.strip_accents(ean_name.lower())

        def rev_contained(nm):
            # ten nhom hang (vd "Kofola") nam tron trong ten san pham quet
            n = cena.strip_accents(nm.lower()).strip()
            return len(n) >= 4 and n in ean_norm

        exact = [it for it in items
                 if (threshold_ok and scores[it["name"]] == max_hit) or rev_contained(it["name"])]
        similar = [it for it in items if it not in exact]
        if exact:
            body += render_table(exact, f"✅ Đúng sản phẩm quét — {len(exact)} kết quả")
            if similar:
                body += render_table(similar, f"🔍 Sản phẩm tương tự — {len(similar)} mặt hàng")
        else:
            body += ("<p style='background:var(--acc-bg);padding:10px 14px;border-radius:8px'>"
                     f"⚠️ <b>{H.escape(ean_name)}</b> hiện <b>không có khuyến mãi</b> ở siêu thị nào "
                     "trong dữ liệu — dưới đây là sản phẩm tương tự cùng hãng/loại.</p>")
            body += render_table(similar, f"🔍 Sản phẩm tương tự — {len(similar)} mặt hàng")
    else:
        body += render_table(items, f"🏆 So sánh giá — {len(items)} mặt hàng, mọi nguồn gộp chung")
    return shell(body, "/banbuon" if only == "banbuon" else "")


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
                qs = urllib.parse.parse_qs(parsed.query)
                q = qs.get("q", [""])[0]
                loc = qs.get("loc", [""])[0]
                view = qs.get("view", ["all"])[0]
                self.send_page(search_html(q, only=loc, view=view) if q.strip() else home_html())
            elif parsed.path == "/manifest.json":
                data = MANIFEST.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/manifest+json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif parsed.path == "/report":
                self.send_page(report_html())
            elif parsed.path == "/akce":
                self.send_page(akce_html())
            elif parsed.path == "/hoaqua":
                self.send_page(category_html("ovoce-a-zelenina"))
            elif parsed.path.startswith("/kategorie/"):
                self.send_page(category_html(parsed.path.split("/kategorie/", 1)[1]))
            elif parsed.path == "/banbuon":
                bp = urllib.parse.parse_qs(parsed.query).get("p", ["1"])[0]
                self.send_page(banbuon_html(int(bp) if bp.isdigit() else 1))
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
