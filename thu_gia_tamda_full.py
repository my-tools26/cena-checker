# -*- coding: utf-8 -*-
"""Cao gia catalog Tamda Express (tamdaexpress.eu) - CAN DANG NHAP B2B.

Gia bi an sau dang nhap ("Dang nhap de xem gia") nen script mo mot cua so Chrome
that (khong headless), ban tu dang nhap 1 lan, roi script duyet danh muc doc
ten/gia/EAN -> tamda_full_prices.json.

MAC DINH = INCREMENTAL (chi them mat hang MOI):
  - Nap data cu tamda_full_prices.json, GIU nguyen.
  - Duyet danh muc voi sort MOI-NHAT-TRUOC; khi gap 3 trang lien tiep khong co
    hang moi -> dung (khoi cao het). Bo search sweep. -> nhanh hon nhieu.
  - Dung cho lich hang tuan (khi to roi het han thi hang moi tu vao).

  python thu_gia_tamda_full.py

CAO LAI TOAN BO (bo data cu + quet het moi trang + search sweep) - nen ~1 thang/lan
de bat het hang o sub-category sau:

  python thu_gia_tamda_full.py --full
"""
import json
import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

# Mac dinh CHAY INCREMENTAL: giu data cu, chi them mat hang MOI (sort moi-nhat
# truoc + dung som khi gap toan hang da biet, bo search sweep). Chay lai TOAN BO
# (bo data cu + quet het + search sweep) bang co --full (nen chay ~1 thang/lan).
FULL = "--full" in sys.argv
# So trang lien tiep KHONG co san pham moi -> coi nhu da toi vung da cao, dung
STOP_AFTER_ALLKNOWN = 3

BASE = "https://tamdaexpress.eu"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tamda_full_prices.json")

# Danh muc fallback neu tu dong kham pha that bai
CATS_FALLBACK = [
    "gastro", "do-uong-gastro", "drogerie", "banh-keo", "nuoc", "che-cafe",
    "gia-vi", "tre-em", "cho-meo", "do-choi", "do-gia-dung", "qua-tang",
    "hang-thoi-vu", "thuoc-la", "thuc-pham",
]

# Danh muc "MO COI": KHONG con link o menu trang chu (vd trang landing cu tu
# thoi COVID) -> discover_categories() KHONG BAO GIO tu tim ra, nhung van con
# ban hang that (phat hien 15/09/2026 qua EAN 8411660006295 Sanytol). LUON cao
# cung du discover thanh cong hay khong, de khong mat hang o day.
ORPHAN_CATS = [
    "anti-covid19-vi",
]

MAX_PAGES_PER_CAT = 120
EMPTY_PAGES_TO_STOP = 2


def wait_login(driver):
    print("Mo tamdaexpress.eu - hay dang nhap tai khoan B2B trong cua so Chrome vua mo...")
    driver.get(f"{BASE}/banh-keo.html")
    while True:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body_text = ""
        if "Đăng nhập để xem giá" not in body_text:
            print("Da phat hien dang nhap. Bat dau cao...")
            return
        time.sleep(2)


def parse_price(text):
    digits = re.sub(r"[^0-9]", "", text or "")
    if not digits:
        return None
    if len(digits) <= 2:
        return int(digits) / 100
    return int(digits[:-2]) + int(digits[-2:]) / 100


def extract_items(driver):
    try:
        grid = driver.find_element(By.CSS_SELECTOR, ".cat-view-grid")
    except Exception:
        return []
    cards = grid.find_elements(By.CSS_SELECTOR, ".product-item.ut2-gl__item")
    out = []
    for card in cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, ".product-title").text.strip()
        except Exception:
            continue
        try:
            price_txt = card.find_element(By.CSS_SELECTOR, ".ty-price").text
        except Exception:
            continue
        price = parse_price(price_txt)
        if price is None or not name:
            continue
        ean = None
        for feat in card.find_elements(By.CSS_SELECTOR, ".ut2-gl__feature"):
            m = re.search(r"EAN\s*(\d{8,14})", feat.text or "")
            if m:
                ean = m.group(1)
                break
        out.append({"name": name, "price": price, "ean": ean, "amount": "", "unit": ""})
    return out


def merge_items(collector, items):
    new = 0
    for it in items:
        key = it["ean"] or it["name"]
        if key not in collector:
            collector[key] = it
            new += 1
    return new


def discover_categories(driver):
    """Doc menu chinh de tim tat ca danh muc (ke ca sub-category)."""
    driver.get(BASE)
    time.sleep(2)
    slugs = set()
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        for a in links:
            href = a.get_attribute("href") or ""
            if href.startswith(BASE + "/") and href.endswith(".html"):
                slug = href[len(BASE) + 1:-5]  # bo ".html"
                if slug and "/" not in slug and not slug.startswith("search") \
                        and slug not in ("index", "profiles", "orders", "wishlist"):
                    slugs.add(slug)
    except Exception as e:
        print(f"Loi kham pha danh muc: {e}")
    if len(slugs) >= 10:
        print(f"Tu dong tim thay {len(slugs)} danh muc tu menu")
        return sorted(slugs)
    print(f"Chi tim thay {len(slugs)} danh muc, dung fallback")
    return CATS_FALLBACK


def crawl_category(driver, cat, collector):
    empty_streak = 0
    allknown_streak = 0
    for page in range(1, MAX_PAGES_PER_CAT + 1):
        if FULL:
            # TOAN BO: phan trang SEO nhu cu, khong sort
            url = f"{BASE}/{cat}.html" if page == 1 else f"{BASE}/{cat}-page-{page}.html"
        else:
            # INCREMENTAL: sort MOI-NHAT truoc + phan trang query de sort giu nguyen
            url = f"{BASE}/{cat}.html?sort_by=timestamp&sort_order=desc&page={page}"
        try:
            driver.get(url)
        except Exception as e:
            print(f"  [{cat} p{page}] loi mo trang: {e}")
            break
        time.sleep(1.0)
        items = extract_items(driver)
        if not items:
            empty_streak += 1
            if empty_streak >= EMPTY_PAGES_TO_STOP:
                break
            continue
        empty_streak = 0
        new = merge_items(collector, items)
        print(f"  [{cat} p{page}] {len(items)} san pham, +{new} moi (tong {len(collector)})")
        # INCREMENTAL: sort moi-nhat truoc -> khi da qua vung san pham moi,
        # cac trang sau toan hang cu -> dung som (khoi cao het 120 trang).
        if not FULL:
            allknown_streak = allknown_streak + 1 if new == 0 else 0
            if allknown_streak >= STOP_AFTER_ALLKNOWN:
                print(f"  [{cat}] {STOP_AFTER_ALLKNOWN} trang lien tiep khong co "
                      f"hang moi -> dung (incremental)")
                break


def search_sweep(driver, collector):
    """Tim kiem a-z, 0-9, cac ky tu Czech de bat san pham o sub-category sau."""
    queries = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["č", "ř", "š", "ž", "ů", "ď", "ť", "ň", "á", "é", "í", "ó", "ú", "ý"]
    before = len(collector)
    for q in queries:
        page = 1
        while page <= 30:
            url = (f"{BASE}/search.html?match=all&subcats=Y&pcode_from_q=Y"
                   f"&pshort=N&pfull=N&pname=Y&pkeywords=N"
                   f"&search_performed=Y&hidden=1&q={q}")
            if page > 1:
                url += f"&page={page}"
            try:
                driver.get(url)
            except Exception:
                break
            time.sleep(1.0)
            items = extract_items(driver)
            if not items:
                break
            new = merge_items(collector, items)
            if new > 0:
                print(f"  [search '{q}' p{page}] +{new} moi (tong {len(collector)})")
            page += 1
    added = len(collector) - before
    print(f"Search sweep: +{added} san pham moi")


def load_existing():
    """Nap tamda_full_prices.json cu -> collector, de INCREMENTAL chi them hang moi.
    QUAN TRONG: neu file TON TAI nhung doc/parse loi thi PHAI DUNG (khong duoc
    tra ve {} coi nhu chua co gi -> an toan giam-manh se khong hoat dong dung,
    xem loi thuc te o thu_gia_bombacena.py 18/09/2026)."""
    if not os.path.exists(OUT):
        return {}
    try:
        data = json.load(open(OUT, encoding="utf-8"))
    except Exception as e:
        print(f"LOI NGHIEM TRONG: file cu {OUT} ton tai nhung doc/parse that bai "
              f"({e}). DUNG lai de tranh ghi de mat du lieu cu.")
        raise SystemExit(2)
    coll = {}
    for it in data.get("items", []):
        key = it.get("ean") or it.get("name")
        if key:
            coll[key] = it
    return coll


# ===== CHE DO NHANH (--fast): cao TOAN BO nhung khong mo tung trang =====
# Chrome chi de GIU PHIEN DANG NHAP; cac trang lay bang fetch() ngay trong tab
# tamdaexpress.eu (cookie phien tu gui kem, ke ca HttpOnly), nhieu trang SONG
# SONG, doc HTML bang DOMParser -> nhanh hon nhieu so voi driver.get tung trang.
FAST = "--fast" in sys.argv
FAST_PARALLEL = 8

FETCH_JS = r"""
const urls = arguments[0], done = arguments[arguments.length - 1];
function price(t) {
  const d = (t || '').replace(/\D/g, '');
  if (!d) return null;
  return d.length <= 2 ? +d / 100 : +d.slice(0, -2) + +d.slice(-2) / 100;
}
async function one(u) {
  try {
    const r = await fetch(u, {credentials: 'include'});
    if (!r.ok) return [];
    const t = await r.text();
    if (t.indexOf('Đăng nhập để xem giá') >= 0) return null;   // mat phien
    const doc = new DOMParser().parseFromString(t, 'text/html');
    const out = [];
    // trang danh muc co khung .cat-view-grid; trang TIM KIEM thi khong (tung lam
    // quet tim kiem ra 0 mon -> sot ~2000 mon o sub-category sau)
    const root = doc.querySelector('.cat-view-grid') || doc;
    root.querySelectorAll('.product-item.ut2-gl__item').forEach(c => {
      const n = c.querySelector('.product-title'), p = c.querySelector('.ty-price');
      const name = n ? n.textContent.trim() : '', pr = p ? price(p.textContent) : null;
      if (!name || pr === null) return;
      let ean = null;
      c.querySelectorAll('.ut2-gl__feature').forEach(f => {
        const m = (f.textContent || '').match(/EAN\s*(\d{8,14})/);
        if (m && !ean) ean = m[1];
      });
      out.push({name: name, price: pr, ean: ean, amount: '', unit: ''});
    });
    return out;
  } catch (e) { return []; }
}
Promise.all(urls.map(one)).then(done);
"""


def fetch_pages(driver, urls):
    driver.set_script_timeout(120)
    res = driver.execute_async_script(FETCH_JS, urls)
    if any(r is None for r in res):
        raise SystemExit("LOI: mat phien dang nhap giua chung (trang hien 'Dang nhap de xem gia')")
    return res


def crawl_paged_fast(driver, url_of, label, collector, max_pages=MAX_PAGES_PER_CAT):
    """Lay trang 1..N theo lo FAST_PARALLEL trang song song; dung khi gap trang
    rong hoac 1 lo khong them duoc mon nao (trang vuot cuoi co the lap lai)."""
    page = 1
    seen_here = set()   # khoa da gap TRONG danh muc nay (mon co the o nhieu danh muc)
    while page <= max_pages:
        nums = list(range(page, min(page + FAST_PARALLEL, max_pages + 1)))
        res = fetch_pages(driver, [url_of(n) for n in nums])
        got = new = 0
        stop = False
        for items in res:
            keys = {it["ean"] or it["name"] for it in items}
            if not items or keys <= seen_here:   # trang rong / lap lai -> het
                stop = True
                break
            seen_here |= keys
            got += len(items)
            new += merge_items(collector, items)
        print(f"  [{label} p{nums[0]}-{nums[-1]}] {got} san pham, +{new} moi (tong {len(collector)})")
        if stop:
            break
        page += FAST_PARALLEL


def crawl_all_fast(driver, cats, collector):
    for cat in cats:
        crawl_paged_fast(driver, lambda n, c=cat: f"{BASE}/{c}.html" if n == 1
                         else f"{BASE}/{c}-page-{n}.html", cat, collector)
    print("\n=== SEARCH SWEEP nhanh (bat san pham o sub-category sau) ===")
    qs = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["č", "ř", "š", "ž", "ů", "á", "é", "í", "ý"]
    for q in qs:
        base = (f"{BASE}/search.html?match=all&subcats=Y&pcode_from_q=Y&pshort=N&pfull=N"
                f"&pname=Y&pkeywords=N&search_performed=Y&hidden=1&q={q}")
        crawl_paged_fast(driver, lambda n, b=base: b if n == 1 else f"{b}&page={n}",
                         f"search {q}", collector, max_pages=60)


def main():
    if FAST:
        globals()["FULL"] = True   # --fast = cao TOAN BO, chi khac cach lay trang
    mode = ("TOAN BO NHANH (--fast, fetch song song)" if FAST else
            "TOAN BO (--full)" if FULL else "INCREMENTAL (chi them hang moi)")
    print(f"Che do: {mode}")
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=vi-VN")
    # HO SO CHROME RIENG giu dang nhap Tamda qua nhieu lan chay -> routine tu chay
    # khong can login lai (chi login lai khi phien het han). KHONG dung profile
    # Chrome chinh cua user (tranh xung dot khi Chrome dang mo).
    profile = os.path.join(HERE, ".chrome-tamda-profile")
    options.add_argument(f"--user-data-dir={profile}")
    # BAT luu mat khau Chrome (Selenium mac dinh tat) -> lan sau tu dien dang nhap
    options.add_experimental_option("prefs", {
        "credentials_enable_service": True,
        "profile.password_manager_enabled": True})
    driver = webdriver.Chrome(options=options)

    all_items = {} if FULL else load_existing()
    before = len(all_items)
    old_n = len(load_existing())
    print(f"Data cu: {before} san pham" if not FULL else "Cao lai tu dau")
    try:
        wait_login(driver)
        cats = discover_categories(driver)
        # luon them danh muc mo coi (khong co trong menu -> discover bo sot)
        cats = cats + [c for c in ORPHAN_CATS if c not in cats]
        if FAST:
            driver.get(f"{BASE}/banh-keo.html")   # tab cung domain de fetch kem phien
            crawl_all_fast(driver, cats, all_items)
            cats = []                              # bo vong lap cham ben duoi
        for cat in cats:
            print(f"=== [{cat}] ===")
            crawl_category(driver, cat, all_items)
        if FULL and not FAST:
            print(f"\n=== SEARCH SWEEP (bat san pham sot) ===")
            search_sweep(driver, all_items)
    finally:
        driver.quit()

    added = len(all_items) - before
    # An toan: incremental KHONG duoc lam giam so luong (neu cao loi ra rong ->
    # giu data cu, khong ghi de).
    if not FULL and os.path.exists(OUT) and len(all_items) < before:
        print(f"LOI: sau khi cao con {len(all_items)} < data cu {before} - "
              f"nghi cao loi, KHONG ghi de.")
        raise SystemExit(2)
    # An toan cho cao toan bo: ra it hon 90% data cu -> nghi loi (mat phien,
    # site doi giao dien...) -> KHONG ghi de.
    if FULL and old_n and len(all_items) < old_n * 0.9:
        print(f"LOI: cao toan bo chi ra {len(all_items)} < 90% data cu {old_n}, KHONG ghi de.")
        raise SystemExit(2)

    result = {
        "date": time.strftime("%Y-%m-%d"),
        "shop": "tamda_full",
        "items": list(all_items.values()),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"XONG: {len(result['items'])} san pham (+{added} moi) -> {OUT}")


if __name__ == "__main__":
    main()
