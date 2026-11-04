# Tai cac ma vach nguoi dung "day" tren web DA DUOC DUYET (Sheet chi tra dong da tick)
# -> ean_taught.json {"items": {ma: ten mon trong catalog}}. build_static.py doc file nay.
# URL lay tu TEACH_URL trong docs/app.js (1 cho duy nhat). Bo tick/xoa dong tren Sheet
# -> lan chay sau ma do tu mat. Dong moi hon ghi de dong cu.
import json, re, sys, urllib.request
from safeio import atomic_open

src = open("docs/app.js", encoding="utf-8").read()
m = re.search(r"var TEACH_URL = '([^']*)'", src)
url = m.group(1) if m else ""
if not url:
    print("TEACH_URL chua dat trong docs/app.js -> bo qua")
    sys.exit(0)
try:
    with urllib.request.urlopen(url, timeout=60) as r:
        rows = json.load(r).get("rows", [])
except Exception as e:
    print("Khong tai duoc Google Sheet:", e)
    sys.exit(0)            # khong lam hong routine; giu ean_taught.json cu

items = {}
for row in rows:
    code = re.sub(r"\D", "", str(row.get("ean", "")))
    name = str(row.get("name", "")).strip()
    if 8 <= len(code) <= 14 and name:
        try:
            price = round(float(str(row.get("price", "")).replace(",", ".")), 2)
        except ValueError:
            price = None
        items[code] = {"name": name, "price": price, "weight": str(row.get("weight", "")).strip(),
                       "origin": str(row.get("origin", "")).strip(),
                       "category": str(row.get("category", "")).strip()}
with atomic_open("ean_taught.json") as f:
    json.dump({"_note": "Ma vach nguoi dung day tren web (Google Sheet). Tu sinh boi "
                        "thu_ma_day.py - dung sua tay.", "items": items},
              f, ensure_ascii=False, indent=1)
print(f"ma day: {len(items)} ma tu {len(rows)} dong Sheet")
