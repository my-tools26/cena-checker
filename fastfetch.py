# -*- coding: utf-8 -*-
"""Tai nhieu trang SONG SONG cho cac crawler (thay vong lap tung trang + sleep).

pages_parallel(get_page, max_pages, batch=4):
    get_page(n) -> list san pham cua trang n (tu thu lai ben trong neu can);
    tra ve [] khi het trang. Tai theo lo `batch` trang cung luc, giu DUNG thu
    tu, dung o trang rong dau tien. 4 luong la vua: nhanh ~3-4 lan ma khong
    doi site qua nhieu request mot luc (tranh bi chan).
"""
from concurrent.futures import ThreadPoolExecutor

BATCH = 4


def pages_parallel(get_page, max_pages, batch=BATCH, first=1, is_last=None):
    """is_last(items) -> True neu trang nay la trang cuoi (vd it hon kich thuoc
    trang) -> bo cac trang sau trong cung lo."""
    out = []
    n = first
    with ThreadPoolExecutor(batch) as ex:
        while n <= max_pages:
            nums = list(range(n, min(n + batch, max_pages + 1)))
            for items in ex.map(get_page, nums):
                if not items:
                    return out
                out.extend(items)
                if is_last and is_last(items):
                    return out
            n += batch
    return out


def map_parallel(fn, args, batch=BATCH):
    """Chay fn tren tung phan tu args song song, giu thu tu ket qua."""
    with ThreadPoolExecutor(batch) as ex:
        return list(ex.map(fn, args))
