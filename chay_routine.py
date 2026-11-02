# -*- coding: utf-8 -*-
"""MOT LENH DUY NHAT cho cac routine (scheduled task) cao gia Cena Checker.

Vi sao (02/11/2026): routine tu nghi ra lenh ghep (`cd ...; git status | ...;
python -c "..."`) -> khong khop quyen da cho -> dung lai cho nguoi bam duyet,
khong ai bam -> du lieu cu ca tuan ma lich van bao "succeeded". Gio routine chi
can chay DUNG 1 lenh co dinh (da cho phep san trong settings.json):

    python C:/Users/charl/Downloads/cena-checker/chay_routine.py <viec> [<viec> ...]

Viec:  akce       cao lai Akce kupi.cz (bo qua neu hom nay da cao)
       linsan     Lin San
       bombacena  Bombacena (full)
       dathang    dathang.cz (full) + gan EAN
       juniorpapir / bidfood / ptt   (can cookie con han)
       tudong     akce + moi kho cong khai cu hon 8 ngay
Script tu: git pull -> cao -> build_static -> tang version web -> git add DUNG
file da cao -> commit -> push. Chot pre-commit (kiem_tra_du_lieu.py) chan thi
DUNG, giu nguyen, bao loi — KHONG BAO GIO tu dat CENA_CHO_PHEP_GIAM.
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1")
ENV.pop("CENA_CHO_PHEP_GIAM", None)

# viec -> (cac lenh python, file can git add, file gia de doc ngay)
JOBS = {
    "linsan": ([["thu_gia_linsan.py"]], ["linsan_prices.json"], "linsan_prices.json"),
    "bombacena": ([["thu_gia_bombacena.py", "--full"]],
                  ["bombacena_prices.json", "bombacena_ean.json"], "bombacena_prices.json"),
    "dathang": ([["thu_gia_dathang.py", "--full"], ["thu_ean_dathang_page.py"],
                 ["-W", "ignore", "thu_ean_dathang_img.py"], ["match_dathang.py", "--apply"]],
                ["dathang_prices.json", "dathang_page_ean.json", "dathang_img_ean.json"],
                "dathang_prices.json"),
    "juniorpapir": ([["thu_gia_juniorpapir.py"]], ["juniorpapir_prices.json"], "juniorpapir_prices.json"),
    "bidfood": ([["thu_gia_bidfood.py"]], ["bidfood_prices.json"], "bidfood_prices.json"),
    "ptt": ([["thu_gia_pttglobal.py"]], ["pttglobal_prices.json"], "pttglobal_prices.json"),
}
PUBLIC = ["linsan", "bombacena", "dathang"]   # khong can dang nhap/cookie
MAX_AGE_DAYS = 8


def log(msg):
    print(msg, flush=True)


def run(args, timeout=3600):
    r = subprocess.run(args, cwd=HERE, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-4:])
    return r.returncode, tail


def git(*a):
    return run(["git", *a], timeout=600)


def file_date(fn):
    try:
        return json.load(open(os.path.join(HERE, fn), encoding="utf-8")).get("date", "")
    except Exception:
        return ""


def count(fn):
    try:
        return len(json.load(open(os.path.join(HERE, fn), encoding="utf-8")).get("items", []))
    except Exception:
        return 0


def age_days(fn):
    d = file_date(fn)
    try:
        return (time.time() - time.mktime(time.strptime(d, "%Y-%m-%d"))) / 86400
    except Exception:
        return 999


def bump_version():
    files = [os.path.join(HERE, "docs", "app.js"), os.path.join(HERE, "docs", "index.html")]
    txt = open(files[1], encoding="utf-8").read()
    m = re.search(r"\?v=(\d+\.\d+\.\d+\.)(\d+)", txt)
    if not m:
        return None
    old = m.group(1) + m.group(2)
    new = m.group(1) + str(int(m.group(2)) + 1)
    for f in files:
        s = open(f, encoding="utf-8").read()
        open(f, "w", encoding="utf-8", newline="").write(s.replace(old, new))
    return new


def main():
    wanted = [a.lower() for a in sys.argv[1:]] or ["tudong"]
    if "tudong" in wanted:
        wanted = ["akce"] + [j for j in PUBLIC if age_days(JOBS[j][2]) > MAX_AGE_DAYS]
    today = time.strftime("%Y-%m-%d")

    code, out = git("pull", "--ff-only", "origin", "master")
    if code:
        log(f"LOI git pull: {out}")
        return 1

    add, report, failed = [], [], []
    for job in wanted:
        if job == "akce":
            continue
        if job not in JOBS:
            log(f"Bo qua viec la: {job}")
            continue
        cmds, files, main_file = JOBS[job]
        before = count(main_file)
        ok = True
        for c in cmds:
            code, out = run([PY, *c])
            if code:
                ok = False
                failed.append(f"{job}: {c[-1] if c[0] != '-W' else c[2]} loi -> {out}")
                break
        if ok:
            add += files
            report.append(f"{job}: {count(main_file)} mon (truoc {before}), ngay {file_date(main_file)}")

    do_akce = "akce" in wanted and file_date(os.path.join("docs", "data", "retail.json")) != today
    code, out = run([PY, "build_static.py"] + (["--retail"] if do_akce else []))
    if code:
        log(f"LOI build_static: {out}")
        return 1
    if do_akce:
        add += ["kupi_cat_cache.json"]
        report.append(f"akce: {count(os.path.join('docs', 'data', 'retail.json'))} mon, ngay {today}")
    elif "akce" in wanted:
        report.append("akce: hom nay da cao roi, bo qua")
    if len(json.load(open(os.path.join(HERE, "docs", "data", "dict.json"), encoding="utf-8"))) == 0:
        log("LOI: dict.json rong (thieu openpyxl?) -> KHONG commit")
        return 1

    add += ["docs/data"]
    git("add", *[f for f in add if os.path.exists(os.path.join(HERE, f))])
    if git("diff", "--cached", "--quiet")[0] == 0:
        log("Khong co gi thay doi.\n" + "\n".join(report + failed))
        return 1 if failed else 0
    ver = bump_version()
    git("add", "docs/app.js", "docs/index.html")
    msg = (f"Routine {time.strftime('%d.%m')}: " + ", ".join(wanted)
           + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    code, out = git("commit", "-m", msg)
    if code:
        log("CHOT KIEM TRA CHAN COMMIT (giu nguyen, khong push):\n" + out)
        return 1
    code, out = git("push", "origin", "master")
    if code:
        log(f"LOI git push: {out}")
        return 1
    log(f"DA PUSH (web v{ver}).\n" + "\n".join(report + failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
