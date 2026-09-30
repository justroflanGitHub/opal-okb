# -*- coding: utf-8 -*-
"""Сравнение load_opj vs decode_lbo_opj на standalone .OPJ файлах."""
import sys, os, io, struct, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from opj_reader import load_opj
from decode_lbo_opj import decode_lbo_opj
from optics_engine import paraxial_trace

opj_files = sorted(glob.glob(os.path.join(BASE_DIR, 'extracted', 'opal_okb', '*.OPJ')))
print(f"files: {len(opj_files)}")

n_opj_glass = 0
n_lbo_glass = 0
n_both = 0
rows = []
for path in opj_files:
    with open(path, 'rb') as f:
        data = f.read()
    try:
        s1, info = load_opj(path)
    except Exception as ex:
        s1 = None
    try:
        s2 = decode_lbo_opj(data)
    except Exception:
        s2 = None
    g1 = sum(1 for s in (s1.surfaces if s1 else []) if s.glass)
    g2 = sum(1 for s in (s2.surfaces if s2 else []) if s.glass)
    f1 = abs(paraxial_trace(s1).get('focal_length', 0)) if s1 and s1.surfaces else 0
    f2 = abs(paraxial_trace(s2).get('focal_length', 0)) if s2 and s2.surfaces else 0
    if g1: n_opj_glass += 1
    if g2: n_lbo_glass += 1
    if g1 and g2: n_both += 1
    rows.append((os.path.basename(path), len(s1.surfaces if s1 else []), g1, len(s2.surfaces if s2 else []), g2, f1, f2))

print(f"load_opj: glass in {n_opj_glass}/{len(rows)}")
print(f"decode_lbo: glass in {n_lbo_glass}/{len(rows)}")
print(f"both: {n_both}")
print()
for r in rows[:20]:
    print(f"  {r[0]:<14} opj: {r[1]:>2}surf {r[2]:>2}glass f'={r[5]:.1f} | lbo: {r[3]:>2}surf {r[4]:>2}glass f'={r[6]:.1f}")
