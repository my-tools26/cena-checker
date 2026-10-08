# -*- coding: utf-8 -*-
"""Tu dong lam moi cookie cho cac kho B2B dung requests+cookie file (PTT Global,
Bidfood, JUNIORpapir) - THAY vi phai F12 > Application > Cookies > copy tay.

Co che: moi site co 1 HO SO CHROME RIENG (persistent, luu trong
.chrome-cookie-profiles/<site>/) giong thu_gia_tamda_full.py. Lan dau chay,
Chrome mo ra, BAN dang nhap 1 lan; script cho toi khi thay dau hieu da dang
nhap roi TU DOC cookie tu trinh duyet va ghi vao <site>_cookie.json. Lan sau
chay lai, phien cu con song (session cookie thuong song vai tuan) -> KHONG can
dang nhap lai, script tu lam moi file cookie trong vai giay.

Chay tat ca:      python refresh_cookies.py
Chay 1 site:       python refresh_cookies.py ptt
                    python refresh_cookies.py bidfood
                    python refresh_cookies.py juniorpapir

Sau khi chay xong, cookie moi da nam san trong *_cookie.json -> chay thang
thu_gia_pttglobal.py / thu_gia_bidfood.py / thu_gia_juniorpapir.py nhu binh
thuong, khong can sua gi them.
"""
import json
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_ROOT = os.path.join(HERE, ".chrome-cookie-profiles")

SITES = {
    "ptt": {
        "url": "https://www.pttglobal.eu/",
        "cookie_file": "pttglobal_cookie.json",
        "keep": ["PHPSESSID"],  # crawler chi can PHPSESSID
        # dau hieu DA dang nhap: link "Odhlásit" (dang xuat) xuat hien
        "logged_in_text": "Odhlásit",
        "alt_marker": "s31-article-price-DPH",
    },
    "bidfood": {
        "url": "https://www.mujbidfood.cz/",
        "cookie_file": "bidfood_cookie.json",
        "keep": None,  # giu TAT CA cookie (crawler doc theo dict day du)
        "logged_in_text": "Odhlásit",
    },
    "juniorpapir": {
        "url": "https://www.juniorpapir.cz/",
        "cookie_file": "juniorpapir_cookie.json",
        "keep": [".BSCTOK2", ".BSSTOK2"],
        "logged_in_text": "UserPanelView",  # kiem tra trong page_source, khong phai text hien
    },
}


def make_driver(site_key):
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=vi-VN")
    profile = os.path.join(PROFILE_ROOT, site_key)
    options.add_argument(f"--user-data-dir={profile}")
    # BAT luu mat khau cua Chrome (Selenium mac dinh TAT): lan dau user bam
    # "Luu mat khau" -> lan sau Chrome TU DIEN ten + mat khau, khoi go lai.
    options.add_experimental_option("prefs", {
        "credentials_enable_service": True,
        "profile.password_manager_enabled": True})
    return webdriver.Chrome(options=options)


def is_logged_in(driver, cfg):
    if cfg["logged_in_text"] == "UserPanelView":
        return "UserPanelView" in driver.page_source and "settings" in driver.page_source
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        src = driver.page_source
    except Exception:
        body = src = ""
    # "Odhlasit" co the nam trong menu AN (khong co trong chu hien) -> xet ca HTML;
    # PTT: gia "bez DPH" chi hien khi da dang nhap B2B
    return (cfg["logged_in_text"] in body or cfg["logged_in_text"] in src
            or cfg.get("alt_marker", "\x00") in src)


def refresh_one(site_key):
    cfg = SITES[site_key]
    print(f"\n=== {site_key} ({cfg['url']}) ===")
    driver = make_driver(site_key)
    try:
        driver.get(cfg["url"])
        time.sleep(2)
        if not is_logged_in(driver, cfg):
            print(f"  Chua dang nhap (hoac phien het han). Hay DANG NHAP "
                  f"{site_key} trong cua so Chrome vua mo (toi doi toi 5 phut)...")
            # CHI NHIN trang hien tai, KHONG tai lai: truoc day reload moi ~4s
            # lam DONG o dang nhap user dang go (loi user bao 06/10/2026).
            waited = 0
            while waited < 300:
                time.sleep(3)
                waited += 3
                try:
                    if is_logged_in(driver, cfg):
                        break
                except Exception:
                    pass   # trang dang chuyen huong sau khi bam Dang nhap
            if not is_logged_in(driver, cfg):
                # dang nhap xong co the van o trang con -> tai lai trang chu 1 lan de chac
                try:
                    driver.get(cfg["url"]); time.sleep(2)
                except Exception:
                    pass
            if not is_logged_in(driver, cfg):
                print(f"  BO QUA {site_key}: khong thay dang nhap sau 5 phut.")
                return False
        print(f"  Da dang nhap {site_key}. Doc cookie ...")
        cookies = driver.get_cookies()
        out = {}
        for c in cookies:
            if cfg["keep"] is None or c["name"] in cfg["keep"]:
                out[c["name"]] = c["value"]
        if not out:
            print(f"  LOI: khong doc duoc cookie can thiet cho {site_key}.")
            return False
        path = os.path.join(HERE, cfg["cookie_file"])
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  Ghi {len(out)} cookie -> {cfg['cookie_file']}")
        return True
    finally:
        driver.quit()


def main():
    targets = sys.argv[1:] or list(SITES.keys())
    bad = [t for t in targets if t not in SITES]
    if bad:
        print(f"Khong nhan dien: {bad}. Cac lua chon: {list(SITES.keys())}")
        raise SystemExit(1)
    results = {}
    for t in targets:
        results[t] = refresh_one(t)
    print("\n=== TOM TAT ===")
    for t, ok in results.items():
        print(f"  {t}: {'OK' if ok else 'THAT BAI/BO QUA'}")


if __name__ == "__main__":
    main()
