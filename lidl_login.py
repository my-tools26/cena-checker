# -*- coding: utf-8 -*-
"""Dang nhap Lidl Plus MOT LAN de luu token - sau do app tu doc kupony.

Yeu cau: Google Chrome da cai tren may.
Mat khau chi nhap tai may nay va chi gui truc tiep den Lidl, khong luu lai.
"""
import getpass
import json
import os
import sys

TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lidl_token.json")


def main():
    print("=" * 50)
    print("  DANG NHAP LIDL PLUS (chi can lam 1 lan)")
    print("=" * 50)
    print()
    phone = input("So dien thoai (dang +420xxxxxxxxx): ").strip()
    password = getpass.getpass("Mat khau Lidl Plus (go xong Enter, man hinh khong hien chu): ")
    print()
    print("Dang mo trinh duyet an va dang nhap... cho 15-30 giay.")
    print("Lidl se gui MA SMS den dien thoai cua ban - cho tin nhan den.")
    print()

    from lidlplus import LidlPlusApi

    api = LidlPlusApi("cs", "CZ")
    try:
        api.login(
            phone,
            password,
            verify_token_func=lambda: input("Nhap MA SMS vua nhan duoc: ").strip(),
        )
    except Exception as e:
        print(f"\nLOI dang nhap: {e}")
        print("Kiem tra: so dien thoai dung dang +420...? mat khau dung?")
        print("Google Chrome da cai chua?")
        sys.exit(1)

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"refresh_token": api.refresh_token}, f)

    print()
    print(f"THANH CONG! Da luu token vao {TOKEN_FILE}")
    print("Tu gio mo CENA.bat -> bam nut 'Kupony Lidl Plus' la xem duoc.")


if __name__ == "__main__":
    main()
