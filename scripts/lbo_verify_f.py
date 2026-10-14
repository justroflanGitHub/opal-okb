# -*- coding: utf-8 -*-
"""Валидация LBO: f' из имени системы vs параксиальный расчёт, все 612 систем."""
import sys, os, glob, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from fileio.lbo_io import load_lbo
from optics_engine import paraxial_trace

def target_f(name: str):
    for pat in (r"f'?=\s*(-?\d+(?:\.\d+)?)",
                r"f'\s*=\s*(-?\d+(?:\.\d+)?)",
                r"[fф]\s*'?\s*=\s*(-?\d+(?:\.\d+)?)"):
        m = re.search(pat, name)
        if m:
            return float(m.group(1))
    return None

libs = glob.glob(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\*.LBO')
_debug = ["", ""]
n_tot = n_named = n_within1 = n_within5 = 0
worst = []
for lb in sorted(libs):
    for s in load_lbo(lb):
        sys_obj = s.get('system')
        if sys_obj is None:
            continue
        n_tot += 1
        tf = target_f(s['name'])
        if n_tot <= 2 or 'Индустар-7' in s['name']:
            print('SAMPLE name:', repr(s['name'][:30]), '-> tf =', tf)
            import re as _re
            print('  pat1:', _re.search(r"f'?=\s*(-?\d+(?:\.\d+)?)", s['name']))
        if tf is None or abs(tf) < 1e-9:
            continue
        try:
            parax = paraxial_trace(sys_obj)
            f_eff = parax.get('effective_focal_length', parax.get('focal_length')) if isinstance(parax, dict) else getattr(parax, 'efl', None)
        except Exception:
            f_eff = None
        if f_eff is None:
            continue
        n_named += 1
        err = abs(f_eff - tf) / abs(tf) * 100
        if err <= 1: n_within1 += 1
        elif err <= 5: n_within5 += 1
        worst.append((err, s['name'][:40], tf, round(f_eff, 2), os.path.basename(lb)))
worst.sort(reverse=True)
print(f"total={n_tot} with_f_in_name={n_named}")
print(f"within 1%: {n_within1} ({n_within1/max(1,n_named)*100:.0f}%)")
print(f"within 5%: {n_within5} ({n_within5/max(1,n_named)*100:.0f}%)")
print("worst 10:")
for w in worst[:10]:
    print(f"  {w[0]:6.1f}%  target={w[2]:9} got={w[3]:9}  {w[4]:14} {w[1]}")
