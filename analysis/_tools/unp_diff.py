# -*- coding: utf-8 -*-
"""TASK_UNP §3+§7: диф-карта функций plain-зоны между старым (OPAL, база 1000:0000)
и новым (OPALA_unp, база 0000:0000) декомпилами + верификация контрольных функций.

Отображение: old_linear = new_linear + 0x10000 (plain-зона new 0x0..0x3F600).
Выход: analysis/reverse_data/_unp_diff.txt
"""
import sys

NEW = r"C:\tools\rea-out\decomp_opala_unp\_funcs.txt"
OLD = r"C:\tools\rea-out\decomp_opala\_funcs.txt"
OUT = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\_unp_diff.txt"
SHIFT = 0x10000
PLAIN_END = 0x3F600  # конец plain-зоны (линейный, новый образ)

def load(path):
    d = {}
    for ln in open(path):
        parts = ln.rstrip("\n").split("|")
        if len(parts) != 5:
            continue
        entry, name, size, ninsn, h = parts
        seg, off = entry.split(":")
        lin = (int(seg, 16) << 4) + int(off, 16)
        d[lin] = (entry, name, int(size), int(ninsn), h)
    return d

new = load(NEW)
old = load(OLD)

# контрольные функции из задачи: f344 f359 93f3 9897 0746 (plain-имена из старого проекта)
CHECK_NEW = {"f344": None, "f359": None, "93f3": None, "9897": None, "0746": None}

out = open(OUT, "w", encoding="utf-8")
W = out.write

W("# диф-карта: old(OPAL,base10000) -> new(UNP,base0), SHIFT=0x10000\n")
W("old funcs: %d, new funcs: %d\n\n" % (len(old), len(new)))

# --- 1. верификация: старые функции, чей образ попадает в plain-зону ---
matched = same = diff = missing = 0
mism_list = []
for olin, (oe, onm, osz, oni, oh) in sorted(old.items()):
    nlin = olin - SHIFT
    if nlin < 0 or nlin >= PLAIN_END:
        continue  # вне plain-зоны (например, за 0x4F600 — быть не должно)
    matched += 1
    if nlin not in new:
        missing += 1
        mism_list.append(("MISSING", olin, oe, onm, osz))
        continue
    ne, nnm, nsz, nni, nh = new[nlin]
    if oh == nh and osz == nsz:
        same += 1
    else:
        diff += 1
        mism_list.append(("CHANGED", olin, "%s->%s" % (oe, ne), onm, "%d->%d" % (osz, nsz)))

W("== верификация plain-зоны ==\n")
W("старых функций в plain-зоне: %d\n  идентичны (hash+size): %d\n  изменены: %d\n  отсутствуют в новом: %d\n\n" % (
    matched, same, diff, missing))
if mism_list:
    for t, olin, e, nm, sz in mism_list[:80]:
        W("  %-8s old_lin=%#x %s %s size=%s\n" % (t, olin, e, nm, sz))
    if len(mism_list) > 80:
        W("  ... ещё %d\n" % (len(mism_list) - 80))
    W("\n")

# --- 2. новые функции: нет соответствия в старом ---
W("== функции БЕЗ аналога в старом декомпиле ==\n")
SEGN = [(0x00000, 0x0FF90, "CODE_MAIN"), (0x0FF90, 0x1F780, "CODE_MATH (0x0FF9)"),
        (0x1F780, 0x2E730, "CODE_RTL1 (0x1F78)"), (0x2E730, 0x3E730, "CODE_RTL2 (0x2E73)"),
        (0x3E730, 0x3F600, "RTL_TAIL (0x3E73)"), (0x3F600, 0x46170, "OVERLAY (0x3F60)"),
        (0x46170, 0x5C000, "DATA/DGROUP")]
new_only = [nlin for nlin in new if (nlin + SHIFT) not in old]
by_seg = {}
for nlin in new_only:
    for lo, hi, nm in SEGN:
        if lo <= nlin < hi:
            by_seg.setdefault(nm, []).append(nlin)
            break
    else:
        by_seg.setdefault("???", []).append(nlin)
for nm in [s[2] for s in SEGN] + (["???"] if "???" in by_seg else []):
    if nm not in by_seg:
        continue
    lst = sorted(by_seg[nm])
    W("\n-- %s: %d функций --\n" % (nm, len(lst)))
    for nlin in lst:
        ne, nnm, nsz, nni, nh = new[nlin]
        W("  new_lin=%#07x %s %-20s size=%-5d insn=%d\n" % (nlin, ne, nnm, nsz, nni))

W("\n== сводка ==\n")
W("всего новых (без аналога): %d из %d\n" % (len(new_only), len(new)))
for nm in [s[2] for s in SEGN] + (["???"] if "???" in by_seg else []):
    if nm in by_seg:
        W("  %-18s %d\n" % (nm, len(by_seg[nm])))
out.close()
print("written", OUT)
print("matched=%d same=%d changed=%d missing=%d new_only=%d" % (matched, same, diff, missing, len(new_only)))
