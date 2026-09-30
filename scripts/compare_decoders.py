# -*- coding: utf-8 -*-
"""Сравнение старого и нового декодера по f'-метрике + счётчики стёкол."""
import sys, os, io, re, math, importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.render_catalog import build_all_entries
from optics_engine import paraxial_trace

# старый декодер как отдельный модуль
spec = importlib.util.spec_from_file_location("old_decode", os.path.join(BASE_DIR, 'scripts', '_old_decode_lbo.py'))
old_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_mod)

from fileio.decode_lbo import decode_lbo_opj as new_decode

F_RE = re.compile(r"[fF]['′]?=\s*(-?\d+(?:\.\d+)?)")


def target_f(name):
    m = F_RE.search(name)
    return float(m.group(1)) if m else None


def score(decode_fn, data):
    try:
        s = decode_fn(data)
    except Exception:
        return None
    n = len(s.surfaces) if s else 0
    if n == 0:
        return ('empty', 0, 0)
    p = paraxial_trace(s)
    f = p.get("focal_length", 0) or p.get("effective_focal_length", 0)
    n_glass = sum(1 for sf in s.surfaces if sf.glass)
    n_ovr = sum(1 for sf in s.surfaces if getattr(sf, 'n_override', None))
    return (f, n_glass, n_ovr)


def main():
    entries = build_all_entries()
    stats = {'new_better': 0, 'old_better': 0, 'same': 0, 'diff': []}
    for idx, e in enumerate(entries):
        entry = e["entry"]
        if not entry.get("opj_data"):
            continue  # только LBO
        data = entry["opj_data"]
        old = score(old_mod.decode_lbo_opj, data)
        new = score(new_decode, data)
        tf = target_f(e["name"])
        if old is None or new is None:
            continue
        def err(res):
            f, ng_, no = res
            if f == 'empty':
                return 999.0
            if not tf or not f or not math.isfinite(f):
                return None
            return abs(abs(f) - abs(tf)) / abs(tf)
        eo, en_ = err(old), err(new)
        if eo is None or en_ is None:
            continue
        if en_ < eo - 0.02:
            stats['new_better'] += 1
        elif eo < en_ - 0.02:
            stats['old_better'] += 1
            stats['diff'].append((idx, e['name'], old[0], new[0]))
        else:
            stats['same'] += 1
    print(stats['new_better'], 'улучшено,', stats['old_better'], 'ухудшено,', stats['same'], 'равно')
    for idx, nm, fo, fn_ in stats['diff'][:40]:
        print(f"  ХУЖЕ [{idx}] {nm[:45]:<45} old f'={fo:.1f} new f'={fn_:.1f}")


if __name__ == '__main__':
    main()
