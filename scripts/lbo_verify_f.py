# -*- coding: utf-8 -*-
"""Валидация LBO: f' из имени системы vs параксиальный расчёт, все системы.

Особые правила (docs/LBO_FORMAT.md, «Особые случаи»):
- Гидроруссары («f=» без апострофа + «Гидро»): подводные объективы, каталог
  указывает фокус в воде; сравниваем расчёт (воздух) · 1.331 = |f| каталога,
  знак — условность каталога.
- Одноцифровой f' в имени (|f|<10) при расчёте в 8–25 раз больше — усечённая
  запись каталога (Юпитер-24 «f'=1» = реально 12.2 мм, Википедия: кинообъектив
  8-мм плёнки «Кварц»); в статистику 1%/5% не входит, показывается отдельно.
"""
import sys, os, glob, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from fileio.lbo_io import load_lbo
from optics_engine import paraxial_trace

WATER_N = 1.331  # показатель преломления воды для «Гидроруссаров»


def target_f(name: str):
    """f' из имени → (значение, есть_ли_апостроф) | (None, ...)."""
    for pat, apos in ((r"f'=\s*(-?\d+(?:\.\d+)?)", True),
                      (r"f=\s*(-?\d+(?:\.\d+)?)", False),
                      (r"[fф]\s*'?\s*=\s*(-?\d+(?:\.\d+)?)", None)):
        m = re.search(pat, name)
        if m:
            return float(m.group(1)), apos
    return None, None


libs = glob.glob(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\*.LBO')
n_tot = n_named = n_within1 = n_within5 = n_trunc = 0
hydro = []
worst = []
per_lib = {}
for lb in sorted(libs):
    lib = os.path.basename(lb)
    st = per_lib.setdefault(lib, [0, 0, 0])  # named, within1, within5
    for s in load_lbo(lb):
        sys_obj = s.get('system')
        if sys_obj is None:
            continue
        n_tot += 1
        tf, apos = target_f(s['name'])
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
        st[0] += 1
        # Гидроруссар: каталог — фокус в воде, знак условен
        if apos is False and 'Гидро' in s['name']:
            err = abs(abs(f_eff) * WATER_N - abs(tf)) / abs(tf) * 100
            hydro.append((err, s['name'][:40], tf, round(f_eff * WATER_N, 2), lib))
            continue
        # усечённое одноцифровое имя (Юпитер-24 «f'=1» → 12.2 мм)
        if abs(tf) < 10 and 8 <= abs(f_eff) / abs(tf) <= 25:
            n_trunc += 1
            print(f'УСЕЧЕНО: {s["name"][:40]!r} имя f\'={tf}, расчёт {f_eff:.2f} — '
                  f'имя каталога потеряло разряд (см. docs/LBO_FORMAT.md)')
            continue
        err = abs(f_eff - tf) / abs(tf) * 100
        if err <= 1:
            n_within1 += 1
            st[1] += 1
        elif err <= 5:
            n_within5 += 1
            st[2] += 1
        worst.append((err, s['name'][:40], tf, round(f_eff, 2), lib))
worst.sort(reverse=True)
print(f"total={n_tot} with_f_in_name={n_named}")
print(f"within 1%: {n_within1} ({n_within1/max(1,n_named)*100:.0f}%)")
print(f"within 5%: {n_within5} ({n_within5/max(1,n_named)*100:.0f}%)")
print(f"усечённых имён (не в статистике): {n_trunc}")
print("Гидроруссары (f·1.331 vs каталог):")
for h in sorted(hydro):
    print(f"  {h[0]:6.1f}%  каталог={h[2]:8} расчёт·1.331={h[3]:9}  {h[1]}")
print("worst 10:")
for w in worst[:10]:
    print(f"  {w[0]:6.1f}%  target={w[2]:9} got={w[3]:9}  {w[4]:14} {w[1]}")
print("по библиотекам (именных / в 1% / в 5%):")
for lib, st in sorted(per_lib.items()):
    if st[0]:
        print(f"  {lib:14} {st[0]:4} {st[1]:4} {st[2]:4}")
