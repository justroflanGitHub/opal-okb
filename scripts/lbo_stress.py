# -*- coding: utf-8 -*-
"""Нагрузочный тест всех LBO-библиотек: полный проход, R/d поверхностей."""
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from fileio.lbo_io import load_lbo

libs = glob.glob(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\*.LBO')
tot_ok = tot_bad = tot_surf = zero_r = 0
first_bad = []
for lb in sorted(libs):
    systems = load_lbo(lb)
    bad = []
    for s in systems:
        sys_obj = s.get('system')
        if sys_obj is None or not getattr(sys_obj, 'surfaces', None):
            bad.append((s.get('name', '?')[:24], '; '.join(s.get('warnings', [])[:1])))
            continue
        for sf in sys_obj.surfaces:
            r = getattr(sf, 'radius_mm', None)
            if r is None:
                r = getattr(sf, 'radius', None)
            tot_surf += 1
            if r in (None, 0.0):
                zero_r += 1
        tot_ok += 1
    tot_bad += len(bad)
    if bad and len(first_bad) < 8:
        first_bad.extend([(os.path.basename(lb),) + b for b in bad[:2]])
    print(f"{os.path.basename(lb):16} n={len(systems):3} ok={len(systems)-len(bad):3} bad={len(bad)}")
print(f"TOTAL ok={tot_ok} bad={tot_bad} surf={tot_surf} zero_R={zero_r}")
for fb in first_bad[:10]:
    print("  BAD:", fb)
