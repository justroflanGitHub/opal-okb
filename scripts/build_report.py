# -*- coding: utf-8 -*-
"""Сборка report.md: отчёт о проверке отображения оптических систем каталога OPAL."""
import json
import os
from collections import OrderedDict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
manifest = json.load(open(os.path.join(BASE, "screenshots", "catalog_check", "manifest_full.json"), encoding="utf-8"))
verdicts = {}
for line in open(os.path.join(BASE, "screenshots", "catalog_check", "results.jsonl"), encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    verdicts[r["idx"]] = r

CAT_ORDER = ["Ахроматические дублеты", "OPAL системы (.OPJ)", "LBO: BINOCUL", "LBO: LENS",
             "LBO: LENS_SPC", "LBO: MICROLEN", "LBO: OCULAR", "LBO: REPROD", "LBO: RUSSAR",
             "LBO: USBINOCL", "LBO: USEYE", "LBO: USLENS", "LBO: USMICRO", "LBO: USREPROD", "LBO: ZOOM"]

VERDICT_RU = {"OK": "✅ корректно", "FAIL": "❌ некорректно", "UNSURE": "⚠️ не уверен"}

# сводка
summary = OrderedDict()
for m in manifest:
    v = verdicts.get(m["idx"], {})
    cat = m["category"]
    s = summary.setdefault(cat, {"OK": 0, "FAIL": 0, "UNSURE": 0, "total": 0})
    s[v.get("verdict", "?")] = s.get(v.get("verdict", "?"), 0) + 1
    s["total"] += 1

tot_ok = sum(c["OK"] for c in summary.values())
tot_fail = sum(c["FAIL"] for c in summary.values())
tot_uns = sum(c["UNSURE"] for c in summary.values())

out = []
out.append("# Отчёт: проверка отображения оптических систем каталога OPAL-OKB\n")
out.append("**Дата:** 2026-09-30  ")
out.append("**Всего систем:** 697  ")
out.append(f"**Отображается корректно:** {tot_ok}  ")
out.append(f"**Отображается некорректно:** {tot_fail}  ")
out.append(f"**Не уверен (UNSURE):** {tot_uns}\n")
out.append("## Методика\n")
out.append("1. Для каждой системы каталога выполнен офскрин-рендер (`scripts/render_catalog.py`): система загружается")
out.append("   через `catalog.library.create_system_from_entry` и отображается тем же виджетом `OpticalSystemView`,")
out.append("   что и в GUI, затем сохраняется PNG (1280×800, `screenshots/catalog_check/NNNN.png`).")
out.append("   Не создавшие PNG системы: 10 — загружаются пустыми (0 поверхностей), 14 — зависают при трассировке/рендере (>60 с).")
out.append("2. Для каждой из 697 систем запущен отдельный субагент (не более 2 параллельно), который визуально")
out.append("   проверял PNG по критериям: контуры оптики нарисованы; лучи преломляются/отражаются на поверхностях;")
out.append("   пучок идёт через систему и сходится у плоскости изображения; нет артефактов. Вердикты: OK / FAIL / UNSURE («не уверен»).")
out.append("3. Системы без PNG проверялись субагентом независимо: воспроизведение загрузки (`scripts/check_one.py`) либо")
out.append("   подтверждение зависания; вердикт FAIL.\n")
out.append("### Типичные дефекты, встреченные в FAIL\n")
out.append("- лучи идут прямыми параллельными линиями через систему без изломов (преломление не отображено) — самая массовая проблема, в основном в LBO-библиотеках USLENS/RUSSAR/USEYE;")
out.append("- пучок обрывается на первой поверхности или внутри системы, не доходя до плоскости изображения;")
out.append("- контуры оптики не нарисованы или вырождены (полосы, зигзаги, «крылья», вертикальные линии-артефакты);")
out.append("- система загружается пустой (0 поверхностей) — отображать нечего;")
out.append("- зависание приложения при построении схемы (>60 с).\n")
out.append("## Сводка по категориям\n")
out.append("| Категория | Всего | ✅ | ❌ | ⚠️ |")
out.append("|---|---|---|---|---|")
for cat in CAT_ORDER:
    c = summary.get(cat, {"total": 0, "OK": 0, "FAIL": 0, "UNSURE": 0})
    out.append(f"| {cat} | {c['total']} | {c['OK']} | {c['FAIL']} | {c['UNSURE']} |")
out.append(f"| **Итого** | **697** | **{tot_ok}** | **{tot_fail}** | **{tot_uns}** |\n")
out.append("## Результаты по системам\n")

def esc(s):
    return s.replace("|", "\\|").strip() or "—"

for cat in CAT_ORDER:
    items = [m for m in manifest if m["category"] == cat]
    if not items:
        continue
    out.append(f"### {cat}\n")
    out.append("| № | Система | Отображение | Комментарий |")
    out.append("|---:|---|---|---|")
    for m in items:
        v = verdicts.get(m["idx"], {})
        vd = v.get("verdict", "?")
        ru = VERDICT_RU.get(vd, vd)
        issues = esc(v.get("issues", ""))
        out.append(f"| {m['idx']} | {esc(m['name'])} | {ru} | {issues} |")
    out.append("")

path = os.path.join(BASE, "report.md")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written:", path, "lines:", len(out))
