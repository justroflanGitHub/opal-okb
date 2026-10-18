# -*- coding: utf-8 -*-
"""TASK_FINAL: волновой кластер — подразумеваемый центр опорной сферы.

Для каждой системы/зоны решаем C_z: сфера с центром (0,0,z_last+C) и
вершиной в плоскости выходного зрачка даёт W = W_банка. Если C_z ≈ const
по зонам → конвенция центра (не Гаусс); сравнить с z_m/z_s/mixed.
Плюс: подразумеваемая квадратичная κ_z на z_last (как OPALDIS §2.2).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.golden_verify import (parse_golden_opj, opj_to_system,
                                    paraxial_of)
from ray_tracing import Ray, trace_ray_through_system
from analysis.aberrations import (_air_exit_direction,
                                  opl_to_last_vertex,
                                  _compute_ray_start)
from domain.calculations import paraxial_trace

GOLDEN = r'C:\GOLDEN_DOS'

# банк: волны λ0 по зонам (зона → W_банка)
BANK_WAVE = {
    '121':     {1.0: -229.3374, 0.866: 75.2842, 0.707: 20.8678, 0.5: 3.5431},
    'OKULAR':  {1.0: -106.0768, 0.866: -71.3209, 0.707: -33.8234,
                0.5: -8.5228},
    'KURSOVIK': {1.0: 67.7269, 0.866: 32.1398, 0.707: 11.7577, 0.5: 2.3526},
    'OBEKTIV': {1.0: -146.3286},
    'S_KOND1': {1.0: -137.7, 0.866: -74.052},
    'HELIOS8': {1.0: -0.2163},
    'US00KI02': {1.0: 0.7532, 0.866: 0.362, 0.707: 0.1354, 0.5: 0.0279},
}

# фан-зоны банка: sin-сетка (0.8660254, 0.7071068)
ZONES_SIN = {1.0: 1.0, 0.866: 0.8660254, 0.707: 0.7071068, 0.5: 0.5}


def solve_center(system, wl, z_last, z_pup, w_target, ray_fn, opl_chief,
                 lo, hi, tol=1e-9):
    """Бисекция C: W(сфера центр z_last+C, вершина z_pup) = w_target."""
    from analysis.aberrations import _opl_to_reference_sphere

    def w_of(c):
        center = (0.0, 0.0, z_last + c)
        r = abs((z_last + c) - z_pup)
        res = ray_fn()
        d = _air_exit_direction(system, res, wl)
        opl = _opl_to_reference_sphere(res.opl, res.path[-1], d, center, r)
        return (opl - opl_chief) / (wl * 1e-3)

    flo, fhi = w_of(lo) - w_target, w_of(hi) - w_target
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        fm = w_of(mid) - w_target
        if abs(fm) < tol or hi - lo < tol * max(1, abs(mid)):
            return mid
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


for name, waves in BANK_WAVE.items():
    opj = parse_golden_opj(os.path.join(GOLDEN, name + '.OPJ'))
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    parax = paraxial_trace(system, wl=wl)
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    sp = parax.get('sP_prime')
    z_pup = z_last + sp
    gauss_off = parax.get('back_focal_distance')
    z_start, z_pupil = _compute_ray_start(system, parax)
    near = (opj['obj_type'] == 1)
    z_obj = opj.get('object_pos', 0.0)
    print(f'\n══ {name}: obj={opj["obj_type"]} img={opj["img_type"]} '
          f'λ={wl:.4f} z_last={z_last:.3f} sP\'={sp:.3f} '
          f'gauss_off={gauss_off:.3f} z_obj={z_obj}')
    # Ax веера: из Н ЗР банка (как харнесс) — берём из габарита Ax печатной
    from analysis.golden_verify import parse_golden_prn, _BANK_DIR
    prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
    hzr = {r['h_zr']: r for r in prn['axial2']['rows'].values()
           if r.get('h_zr')}
    ax = max(hzr)
    print(f'   Ax={ax:.4f}  (Н ЗР зоны: {sorted(hzr, reverse=True)})')

    def chief_opl():
        ray = Ray(0.0, 0.0, z_obj if near else z_start, 0.0, 0.0, 1.0)
        if near and z_obj > 0:
            ray = Ray(0.0, 0.0, -(abs(z_obj) + 100.0), 0.0, 0.0, 1.0)
        res = trace_ray_through_system(system, ray, wl)
        from analysis.aberrations import _opl_to_reference_sphere
        d = _air_exit_direction(system, res, wl)
        center = (0.0, 0.0, z_last + gauss_off)
        r = abs(center[2] - z_pup)
        opl = _opl_to_reference_sphere(res.opl, res.path[-1], d, center, r)
        return opl

    opl_chief = chief_opl()

    for zone, w_bank in sorted(waves.items()):
        zz = ZONES_SIN[zone]
        if near:
            na = ax if ax < 1 else None   # Ax в дптр-сетке Н ЗР = 100·tg
            su = None
            # Н ЗР = 100·tg u → tg u = hzr/100
            hzr_z = min(hzr, key=lambda h: abs(h - zz * ax))
            tu = hzr_z / 100.0
            su = tu / math.sqrt(1 + tu * tu)
            if z_obj < 0:
                ray0 = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1 - su * su))
            else:
                z0 = -(abs(z_obj) + 100.0)
                ray0 = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                           math.sqrt(1 - su * su))
        else:
            ray0 = Ray(0.0, zz * ax, z_start, 0.0, 0.0, 1.0)

        def ray_fn(ray0=ray0):
            return trace_ray_through_system(system, ray0, wl)

        res = ray_fn()
        if not res.success:
            print(f'   з.{zone}: FAIL {res.error}')
            continue
        d = _air_exit_direction(system, res, wl)
        y_exit = res.path[-1][1]
        # κ_z на z_last: W = ΔOPL(→z_last) + κ·y²/2  (κ при y_chief≈0)
        opl_zl = opl_to_last_vertex(system, res, wl)
        chief_zl = opl_to_last_vertex(
            system, trace_ray_through_system(
                system, Ray(0.0, 0.0, ray0.z, 0.0, 0.0, 1.0), wl), wl) \
            if not near else None
        if near:
            ray_c = Ray(0.0, 0.0, z_obj, 0.0, 0.0, 1.0) if z_obj < 0 else \
                Ray(0.0, 0.0, -(abs(z_obj) + 100.0), 0.0, 0.0, 1.0)
            chief_zl = opl_to_last_vertex(
                system, trace_ray_through_system(system, ray_c, wl), wl)
        # центр-бисекция
        c = solve_center(system, wl, z_last, z_pup, w_bank, ray_fn,
                         opl_chief, gauss_off - 3000.0, gauss_off + 3000.0)
        # порт-W при Гаусс-центре
        from analysis.aberrations import _opl_to_reference_sphere
        center = (0.0, 0.0, z_last + gauss_off)
        r = abs(center[2] - z_pup)
        opl = _opl_to_reference_sphere(res.opl, res.path[-1], d, center, r)
        w_port = (opl - opl_chief) / (wl * 1e-3)
        d_opl = (w_bank - w_port) * wl * 1e-3
        kap = 2.0 * (w_bank * wl * 1e-3
                     - (opl_zl - chief_zl)) / (y_exit * y_exit) \
            if y_exit else None
        c_txt = f'{c:.3f}' if c is not None else '—'
        print(f'   з.{zone:.3f}: W_банк={w_bank:+10.4f} W_порт={w_port:+10.4f}'
              f' Δ={w_bank - w_port:+8.4f}λ C_z={c_txt} '
              f'(гаусс {gauss_off:.3f}) κ_z={kap:+.6f}' if kap is not None
              else f'   з.{zone:.3f}: κ=—')
