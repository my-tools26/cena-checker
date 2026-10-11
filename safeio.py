# -*- coding: utf-8 -*-
"""Ghi file AN TOAN (atomic): ghi ra <ten>.tmp, xong het moi doi ten de len file
that. May tat / app bi ngat GIUA LUC GHI -> file that van la ban cu nguyen ven,
khong bao gio con file cut nua voi (them 10/2026 de chong mat du lieu).

Dung thay open(path, "w", encoding="utf-8"):
    with atomic_open(path) as f: json.dump(data, f)
    json.dump(data, atomic_open(path))      # cung an toan (dong ngay khi het tham chieu)
Neu co loi trong khoi `with` -> bo file tam, file that giu nguyen.
"""
import os


class atomic_open:
    def __init__(self, path, mode="w", encoding="utf-8"):
        self.path = os.fspath(path)
        self.tmp = self.path + ".tmp"
        self._f = open(self.tmp, mode, encoding=encoding)
        self._done = False

    def write(self, s):
        return self._f.write(s)

    def close(self, commit=True):
        if self._done:
            return
        self._done = True
        self._f.flush()
        os.fsync(self._f.fileno())
        self._f.close()
        if commit:
            os.replace(self.tmp, self.path)
        else:
            try:
                os.remove(self.tmp)
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close(commit=exc_type is None)
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
