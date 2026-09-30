# -*- coding: utf-8 -*-
"""Офскрин-рендер всех систем каталога OPAL в PNG (для визуальной проверки отображения).

Каждая система загружается через catalog.library.create_system_from_entry
и отображается тем же виджетом, что и в GUI (visualization.OpticalSystemView),
затем виджет рендерится в PNG.

Запуск:
    py scripts/render_catalog.py            # все системы
    py scripts/render_catalog.py --only 5   # первые 5 (тест)

Результат: screenshots/catalog_check/manifest.json + PNG-файлы.
"""
import os
import sys
import json
import time
import argparse
import traceback

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

OUT_DIR = os.path.join(BASE_DIR, "screenshots", "catalog_check")
TIMEOUT_S = 60.0


def sanitize(name):
    keep = "".join(c if (c.isalnum() or c in "-_. ") else "_" for c in name)
    return keep.strip().replace(" ", "_")[:80] or "unnamed"


def build_all_entries():
    """Единый список систем каталога: ахроматы, OPJ, LBO (развёрнутые)."""
    from catalog.library import build_library, expand_lbo
    entries = []
    lib = build_library()
    for cat in ("Ахроматические дублеты", "OPAL системы (.OPJ)"):
        for e in lib[cat]:
            entries.append({"category": cat, "name": e["name"], "entry": e})
    for e in lib["LBO библиотеки"]:
        for s in expand_lbo(e["lbo_path"]):
            entries.append({"category": f"LBO: {e['lbo_name']}", "name": s["name"], "entry": s})
    return entries


def render_one(task):
    """Загрузить систему и отрендерить в PNG. Вызывается в дочернем процессе."""
    idx, category, name, entry = task
    slug = f"{idx:04d}_{sanitize(category.replace(': ', '_').replace(' ', '_'))}_{sanitize(name)}"
    png_path = os.path.join(OUT_DIR, slug + ".png")
    rec = {
        "idx": idx,
        "category": category,
        "name": name,
        "png": os.path.relpath(png_path, BASE_DIR).replace("\\", "/"),
        "status": "ok",
        "error": "",
        "surfaces": 0,
        "ms": 0,
    }
    t0 = time.time()
    try:
        from catalog.library import create_system_from_entry
        sys_obj = create_system_from_entry(entry)
        if sys_obj is None or not getattr(sys_obj, "surfaces", None):
            rec["status"] = "error"
            rec["error"] = "load: system has no surfaces"
            return rec
        rec["surfaces"] = len(sys_obj.surfaces)

        from PyQt5.QtWidgets import QApplication
        from visualization import OpticalSystemView
        app = QApplication.instance() or QApplication(sys.argv[:1])

        view = OpticalSystemView()
        view.resize(1280, 800)
        view.set_system(sys_obj)          # как в main.py при загрузке системы
        app.processEvents()
        pix = view.grab()
        ok = pix.save(png_path, "PNG")
        if not ok or not os.path.isfile(png_path) or os.path.getsize(png_path) < 1000:
            rec["status"] = "error"
            rec["error"] = "render: failed to save PNG"
            return rec
    except Exception:
        rec["status"] = "error"
        rec["error"] = traceback.format_exc(limit=3).strip().replace("\n", " | ")[-500:]
    finally:
        rec["ms"] = int((time.time() - t0) * 1000)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0, help="render only first N (debug)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    entries = build_all_entries()
    if args.only:
        entries = entries[: args.only]
    if args.start:
        entries = entries[args.start:]
    print(f"Total systems to render: {len(entries)}", flush=True)

    # Мультипроцессная обработка: per-task дедлайн через apply_async +
    # убийство пула, если задача не уложилась. Уже отрендеренные PNG
    # пропускаем (возобновление после сбоя).
    import multiprocessing as mp
    import glob as _g
    ctx = mp.get_context("spawn")

    tasks = [(i, e["category"], e["name"], e["entry"]) for i, e in
             zip(range(args.start, args.start + len(entries)), entries)]
    todo = []
    for t in tasks:
        if _g.glob(os.path.join(OUT_DIR, f"{t[0]:04d}_*.png")):
            continue
        todo.append(t)
    print(f"To render now: {len(todo)} (rest already done)", flush=True)

    results = []

    while todo:
        pool = ctx.Pool(args.workers, maxtasksperchild=8)
        got, pending_ids = [], set()
        try:
            async_results = {t[0]: pool.apply_async(render_one, (t,)) for t in todo}
            deadline = {t[0]: time.time() + TIMEOUT_S for t in todo}
            while async_results:
                now = time.time()
                if any(now > deadline[i] for i in async_results):
                    pending_ids = set(async_results)  # дедлайн: пул будет убит
                    break
                for idx in list(async_results):
                    ar = async_results[idx]
                    if ar.ready():
                        try:
                            got.append(ar.get(timeout=1))
                        except Exception:
                            pass
                        del async_results[idx]
                if async_results:
                    time.sleep(0.5)
        finally:
            pool.terminate()
            pool.join()
        results.extend(got)

        if not pending_ids:
            break
        for t in todo:
            if t[0] in pending_ids:
                results.append({
                    "idx": t[0], "category": t[1], "name": t[2],
                    "png": "", "status": "hang",
                    "error": f"hang: render did not finish in {TIMEOUT_S}s (terminated)",
                    "surfaces": 0, "ms": TIMEOUT_S * 1000,
                })
                print(f"  [{t[0]}] HANG {t[2][:50]}", flush=True)
        todo = [t for t in todo if t[0] not in pending_ids]

    results.sort(key=lambda r: r["idx"])

    manifest = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)

    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_err = sum(1 for r in results if r["status"] == "error")
    n_hang = sum(1 for r in results if r["status"] == "hang")
    print(f"Done: ok={n_ok} error={n_err} hang={n_hang} -> {manifest}", flush=True)


if __name__ == "__main__":
    main()
