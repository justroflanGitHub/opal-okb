# -*- coding: utf-8 -*-
"""Массовая валидация декодера: f' из paraxial vs f' из имени системы."""
import sys, os, io, re, math, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.render_catalog import build_all_entries
from catalog.library import create_system_from_entry
from optics_engine import paraxial_trace

F_RE = re.compile(r"[fF]['′]?=\s*(-?\d+(?:\.\d+)?)")


def target_f(name):
    m = F_RE.search(name)
    return float(m.group(1)) if m else None


def main():
    entries = build_all_entries()
    total = good = close = bad = nof = empty = exc = 0
    fails = []
    for idx, e in enumerate(entries):
        total += 1
        try:
            s = create_system_from_entry(e["entry"])
        except Exception as ex:
            exc += 1
            fails.append((idx, e["name"], f"EXC {type(ex).__name__}"))
            continue
        n = len(s.surfaces) if s else 0
        if n == 0:
            empty += 1
            fails.append((idx, e["name"], "EMPTY"))
            continue
        p = paraxial_trace(s)
        f = p.get("focal_length", 0) or p.get("effective_focal_length", 0)
        tf = target_f(e["name"])
        if not tf or tf == 0:
            nof += 1
            continue
        if not f or not math.isfinite(f) or abs(f) < 1e-6:
            bad += 1
            fails.append((idx, e["name"], f"f'=0 (target {tf})"))
            continue
        ratio = abs(abs(f) - abs(tf)) / abs(tf)
        if ratio < 0.08:
            good += 1
        elif ratio < 0.25:
            close += 1
            fails.append((idx, e["name"], f"f'={f:.1f} vs {tf} ({ratio*100:.0f}%)"))
        else:
            bad += 1
            fails.append((idx, e["name"], f"f'={f:.1f} vs {tf} ({ratio*100:.0f}%)"))

    print(f"Итого {total}: точно {good}, близко {close}, мимо {bad}, "
          f"нет f' в имени {nof}, пустых {empty}, исключений {exc}")
    print("\nХудшие (первые 60):")
    for idx, nm, msg in fails[:60]:
        print(f"  [{idx}] {nm[:50]:<50} {msg}")


if __name__ == '__main__':
    main()
