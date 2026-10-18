# -*- coding: utf-8 -*-
"""TASK_FINAL: OPTICS#1 — запуск веера ближнего/мнимого предмета.

§5.2: с per-λ Ax остатки коллапсируют в ΔL≈−0.0325·z², Δy≈+0.005·z³
(наклоны совпадают до 4–5 знаков). Тестируем сетки запуска:
  (a) sin-сетка: su = zone·NA (текущий порт);
  (b) tg-сетка: tu = zone·tg(arcsin NA);
  (c) прицел в плоскость S1 (z=0): y(0) = zone·y_rim(0);
  (d) прицел в плоскость входного зрачка (z=sP): y(sP) = zone·y_rim(sP).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.golden_verify import (parse_golden_opj, opj_to_system,
                                    parse_golden_prn, paraxial_of, _BANK_DIR)
from ray_tracing import Ray, trace_ray_through_system

GOLDEN = r'C:\GOLDEN_DOS'
NAME = 'OPTICS#1'

opj = parse_golden_opj(os.path.join(GOLDEN, NAME + '.OPJ'))
system = opj_to_system(opj)
prn = parse_golden_prn(os.path.join(_BANK_DIR, NAME + '.PRN'))
wl = opj['wls'][0]
na = 0.125
z_obj = opj['object_pos']
print(f'obj_type={opj["obj_type"]} z_obj={z_obj} na={na} wl0={wl}')
print('габарит N=0 Ax:', [r for r in prn.get('gabarit', {}).get('rows', [])
                          if r.get('N') == 0][:1])

# банк: осевые таблицы
for key in ('axial1', 'axial2'):
    print(f'\n{key}:')
    for label, r in sorted(prn[key]['rows'].items()):
        print('  ', label, r)

parax = paraxial_of(system, wl)
sP = parax['sP']
z_last = sum(s.thickness for s in system.surfaces[:-1])
print(f'\nsP={sP} sP\'={parax["sP_prime"]} z_last={z_last}')

# наклон/высота выхода текущего порта (sin-сетка) — референс для сеток


def trace_tu(tu, sign=-1.0):
    """Луч, идущий к точке предмета (0,0,z_obj): tg-угол tu (высота на
    единицу длины). z_obj>0: старт слева, наклон отрицательный."""
    su = tu / math.sqrt(1.0 + tu * tu)
    z0 = -(abs(z_obj) + 100.0)
    y0 = (z_obj - z0) * tu
    ray = Ray(0.0, y0, z0, 0.0, sign * su, math.sqrt(1.0 - su * su))
    return trace_ray_through_system(system, ray, wl)


# высоты rim-луча (зона 1) в характерных плоскостях
res1 = trace_tu(na / math.sqrt(1.0 - na * na))
if res1.success:
    # трассируем назад к z=0 и z=sP по终端 сегменту? Нужен вход: пересчитаем
    # входную геометрию: луч из z0 с y0, tu → y(0) = y0 + slope·(0−z0)
    z0 = -(abs(z_obj) + 100.0)
    y0 = (z_obj - z0) * (na / math.sqrt(1.0 - na * na))
    y_at0 = y0 - (na / math.sqrt(1.0 - na * na)) * (-z0)
    y_at0 = z_obj * (na / math.sqrt(1.0 - na * na))   # y на плоскости z=0
    y_at_sP = (z_obj - sP) * (na / math.sqrt(1.0 - na * na))
    print(f'rim: y(0)={y_at0:.4f} y(sP)={y_at_sP:.4f}')

    def exit_geom(res):
        prev, last = res.path[-2], res.path[-1]
        dz = last[2] - prev[2]
        slope = (last[1] - prev[1]) / dz
        return last[1], slope

    y1, s1 = exit_geom(res1)
    L1 = z_last - y1 / s1 - z_last  # от вершины
    L1 = -y1 / s1
    print(f'rim выход: y={y1:.4f} slope={s1:.6f} L={L1:.4f}')

    zones = (1.0, 0.8660254, 0.7071068, 0.5)
    variants = {}
    for zone in zones:
        # (a) sin-сетка
        su = na * zone
        variants.setdefault('a', []).append(su / math.sqrt(1.0 - su * su))
        # (b) tg-сетка
        variants.setdefault('b', []).append(
            zone * na / math.sqrt(1.0 - na * na))
        # (c) линейная высота на z=0 → tg = zone·y_at0/(z_obj−0)
        variants.setdefault('c', []).append(zone * y_at0 / z_obj)
        # (d) линейная высота в зрачке → tg к предмету от зрачка
        variants.setdefault('d', []).append(zone * y_at_sP / (z_obj - sP))

    for vname, tus in variants.items():
        print(f'\n— вариант ({vname}):')
        for zone, tu in zip(zones, tus):
            res = trace_tu(tu)
            if not res.success:
                print(f'  з.{zone:.4f}: FAIL {res.error}')
                continue
            y, sl = exit_geom(res)
            L = -y / sl
            print(f'  з.{zone:.4f}: y={y:+9.4f} slope·100={sl*100:+9.4f} '
                  f'L={L:+10.4f}')
