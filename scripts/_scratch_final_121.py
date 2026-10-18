# -*- coding: utf-8 -*-
"""TASK_FINAL scratch: 121 — TIR-кромка з.1.0. Ветви замыкания волны.

Известно (досье §EDGE E1/E5, OPALDIS §3):
  h_TIR = 8.1004482239 (TIR на S4), печатный Ax = 8.1004;
  W параллельного семейства монотонно-положительна 199→307.85→309.5;
  банк з.1.0: −229.3374 (все три λ отрицательны), з.0.866: +75.2842;
  прод/попер з.1.0 банка = тот же луч, что порт на h=8.1004.
Проверяем ветви: (а) пропуск S4 (TIR→луч без отклонения), (б) зеркальный
TIR-отражение на S4, (в) скан h с тонким шагом, (г) вычет опорной сферы
с другими корнями/вершинами.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.golden_verify import (parse_golden_opj, opj_to_system,
                                    paraxial_of, axial_fan)
from ray_tracing import Ray, trace_ray_through_system
from analysis.aberrations import (_air_exit_direction,
                                  _opl_to_reference_sphere,
                                  _chief_reference_opl, _reference_sphere,
                                  _compute_ray_start)
from domain.calculations import paraxial_trace

OPJ = r'C:\GOLDEN_DOS\121.OPJ'
opj = parse_golden_opj(OPJ)
system = opj_to_system(opj)
wl = opj['wls'][0]
parax = paraxial_trace(system, wl=wl)
print('λ0 =', wl, 'Ax(print) = 8.1004, h_TIR = 8.1004482239')
print('sP =', parax.get('sP'), ' sP\' =', parax.get('sP_prime'),
      ' bfd =', parax.get('back_focal_distance'),
      ' L =', parax.get('L'))
z_last = sum(s.thickness for s in system.surfaces[:-1])
print('z_last =', z_last, ' nsurf =', len(system.surfaces))
for i, s in enumerate(system.surfaces):
    print(f'  S{i}: R={s.radius!r} d={s.thickness!r} glass={s.glass!r} '
          f'n_ovr={getattr(s, "n_override", None)!r}')

# ── банк ──
BANK = {1.0: (-555.75270, 115.848100, 20.845, -229.3374, 8.1004),
        0.866: (-1184.91000, 16.064060, -1.356, 75.2842, 7.0152),
        0.707: (767.17640, 4.522955, 0.590, 20.8678, 5.7279),
        0.500: (108.41830, 0.932533, 0.860, 3.5431, 4.0502)}

# опорная сфера порта (как в axial_fan)
ref_center, ref_r = _reference_sphere(system, 0.0, parax)
z_start, z_pupil = _compute_ray_start(system, parax)
opl_chief = _chief_reference_opl(system, wl, 0.0, z_start, z_pupil,
                                 ref_center, ref_r)
print('ref_center =', ref_center, ' R =', ref_r, ' z_pupil =', z_pupil)


def trace_h(h):
    """Параллельный луч с высоты h: полный прогон + детали на S4."""
    ray = Ray(0.0, h, z_start, 0.0, 0.0, 1.0)
    return trace_ray_through_system(system, ray, wl)


def wave_of(res):
    d = _air_exit_direction(system, res, wl)
    opl = _opl_to_reference_sphere(res.opl, res.path[-1], d,
                                   ref_center, ref_r)
    return (opl - opl_chief) / (wl * 1e-3), opl


def geom(res):
    prev, last = res.path[-2], res.path[-1]
    dz = last[2] - prev[2]
    slope = (last[1] - prev[1]) / dz if abs(dz) > 1e-12 else 0.0
    L = -last[1] / slope if abs(slope) > 1e-12 else None
    return last[1], slope, L


print('\n── зоны порта (высота = sin(угол)-сетка банка) ──')
for zone in (1.0, 0.8660254, 0.7071068, 0.5):
    h = zone * 8.1004
    res = trace_h(h)
    if not res.success:
        print(f'з.{zone:.4f} h={h:.5f}: FAIL {res.error}')
        continue
    w, opl = wave_of(res)
    y, sl, L = geom(res)
    bk = BANK[min(BANK, key=lambda k: abs(k - zone))]
    print(f'з.{zone:.4f} h={h:.5f}: W={w:+9.3f} (банк {bk[3]:+9.3f}) '
          f'прод={L:+10.3f} (банк {bk[0]:+10.3f}) y={y:+8.4f} '
          f'(банк {bk[1]:8.4f}) slope={sl:+.6f}')

print('\n── тонкий скан к кромке ──')
for h in (8.1004, 8.10040, 8.10043, 8.100447, 8.1004482, 8.10044822,
          8.100448223, 8.1004482239):
    res = trace_h(h)
    if not res.success:
        print(f'h={h:.10f}: FAIL ({res.error})')
        continue
    w, opl = wave_of(res)
    y, sl, L = geom(res)
    print(f'h={h:.10f}: W={w:+10.4f} прод={L:+10.3f} y={y:+8.4f} '
          f'нит={len(res.path)}')

print('\n── зона 1.0: ветви особой ситуации ──')
# (а) S4 пропущена: трассируем вручную S0..S3, затем прямой до плоскости
#     изображения без преломления на S4 и далее S5+ с преломлением
#     (реализация: копия системы с R4→1e15 — плоская S4, «окно»;
#      и вариант d=0/S4 выключена полностью нельзя — просто сравним)
import copy

h = 8.1004
print('(а) S4 → плоская (R=1e15), луч проходит без отклонения высоты:')
sys_flat = copy.deepcopy(system)
sys_flat.surfaces[4].radius = 1e15 if hasattr(sys_flat.surfaces[4], 'radius') \
    else sys_flat.surfaces[4].radius
res = trace_ray_through_system(sys_flat, Ray(0.0, h, z_start, 0.0, 0.0, 1.0),
                               wl)
if res.success:
    w, _ = wave_of(res)
    y, sl, L = geom(res)
    print(f'    W={w:+10.3f} (банк −229.337) прод={L} y={y} slope={sl}')
else:
    print('    FAIL', res.error)

# (б) зеркало на S4 (TIR-отражение): is_reflective на S4
sys_mir = copy.deepcopy(system)
sys_mir.surfaces[4].is_reflective = True
res = trace_ray_through_system(sys_mir, Ray(0.0, h, z_start, 0.0, 0.0, 1.0),
                               wl)
if res.success:
    w, _ = wave_of(res)
    y, sl, L = geom(res)
    print(f'(б) S4 зеркало: W={w:+10.3f} прод={L} y={y} slope={sl}')
else:
    print('(б) S4 зеркало: FAIL', res.error)
