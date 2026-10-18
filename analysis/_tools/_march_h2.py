# -*- coding: utf-8 -*-
"""TASK_MARCH2 зонд H2: банк = OPL(до z_last) + Σ_s n·T_s·X_s²/2 − S·sin(u)?

Марш W₂ = Σ_s (L_s + QF_s/2)·Π head (телескоп); печать = ΔW₂ − S·sin u
(M.1/M.2). Порт = OPL до гауссовой сферы. Гипотеза: разность
D = банк − порт воспроизводится замыканием Коддингтона по поверхностям
T_s = ∂u/∂y (тангенциальная кривизна трубы, диффтрассировка) минус
терминальные члены (S·sin u, расширение до сферы).

Считаем для каждой зоны: D_pred = Σ n·T_s·X_s²/2 − S·sin(u) − n·t_ext
и сверяем с D = (банк − порт_волновая)·λ.
Запуск: py -X utf8 analysis/_tools/_march_h2.py [системы]
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.golden_verify import (  # noqa: E402
    parse_golden_prn, parse_golden_opj, opj_to_system, paraxial_of,
    _paraxial_ray, _n_media, _GOLDEN_DOS,
)
from analysis.aberrations import _compute_ray_start  # noqa: E402
from optics_utils import make_field_ray  # noqa: E402
from ray_tracing import Ray, trace_ray_through_system  # noqa: E402
from domain.calculations import paraxial_trace  # noqa: E402

_BANK_DIR = os.path.join(os.path.dirname(__file__), '..', 'reverse_data',
                         'golden', 'bank')


def _fan_zone_rows(name, bank_dir=_BANK_DIR, opj_dir=_GOLDEN_DOS):
    """Сшивка зон волновых строк (как compare_system, far-ветка)."""
    prn = parse_golden_prn(os.path.join(bank_dir, name + '.PRN'))
    opj = parse_golden_opj(os.path.join(opj_dir, name + '.OPJ'))
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    near = (opj['obj_type'] == 1)
    hzr_vals = [r['h_zr'] for r in prn['axial2'].get('rows', {}).values()
                if r.get('h_zr') is not None]
    ax_semi = max(hzr_vals) if hzr_vals else opj['aperture_semi']
    zones_sorted = sorted(prn['axial1'].get('rows', {}).keys(), reverse=True)
    na = 0.0
    for (ws, nz), row in prn['gabarit'].items():
        if nz == 0 and row.get('Ax'):
            na = row['Ax']
    scale = ax_semi if not near else 100.0 * (na or opj['aperture_semi'])
    used, wave_rows = set(), []
    for tg, et in sorted(prn['axial2'].get('rows', {}).items(),
                         key=lambda kv: -kv[1]['tg100']):
        if not et.get('wave') or et['wave'][0] is None:
            continue
        hzr = et.get('h_zr')
        z = None
        if hzr is not None and scale:
            z = min(zones_sorted, key=lambda zz: abs(zz - hzr / scale))
        if z is None or z in used:
            z = next((zz for zz in zones_sorted if zz not in used), None)
        if z is None:
            break
        used.add(z)
        wave_rows.append((z, et['wave'][0]))
    return prn, opj, system, wl, near, ax_semi, wave_rows


def _ray_of(system, near, z_obj, na, ax_semi, zone, wl):
    if not near:
        parax = paraxial_trace(system, wl=wl)
        z_start, z_pupil = _compute_ray_start(system, parax)
        return trace_ray_through_system(
            system, make_field_ray(system, 0.0, zone * ax_semi, 0.0,
                                   z_start, z_pupil), wl)
    su = na * zone
    if z_obj < 0.0:
        ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1.0 - su * su))
    else:
        tu = su / math.sqrt(1.0 - su * su)
        z0 = -(abs(z_obj) + 100.0)
        ray = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                  math.sqrt(1.0 - su * su))
    return trace_ray_through_system(system, ray, wl)


def _tube_T(system, res, res_dy, wl):
    """Тангенциальная кривизна трубы T_s = Δslope/Δy на каждой поверхности
    (пары точек path[i] двух лучей — зона и зона+dh)."""
    T = []
    n = min(len(res.path), len(res_dy.path))
    for i in range(n):
        p0, p1 = res.path[i], res_dy.path[i]
        if i == 0:
            T.append(None)
            continue
        pa, pb = res.path[i - 1], res_dy.path[i - 1]
        dy = p1[1] - p0[1]
        dyp = pb[1] - pa[1]
        dz = p1[2] - p0[2]
        dzp = pb[2] - pa[2]
        s0 = (p0[1] - pa[1]) / (p0[2] - pa[2]) if abs(p0[2] - pa[2]) > 1e-15 else 0.0
        s1 = (p1[1] - pb[1]) / (p1[2] - pb[2]) if abs(p1[2] - pb[2]) > 1e-15 else 0.0
        dy_tot = (p1[1] - pb[1]) if abs(p1[1] - pb[1]) > 1e-12 else None
        if dy_tot is None:
            T.append(None)
            continue
        T.append((s0 - s1) / dy_tot)   # ∂u_in/∂y (до поверхности i)
    return T


def main():
    names = sys.argv[1:] or ['121', 'OKULAR', 'KURSOVIK', 'US00KI02',
                             'HELIOS8', 'S_KOND1', 'OBEKTIV']
    lam_um_factor = 1.0
    for name in names:
        try:
            prn, opj, system, wl, near, ax_semi, wave_rows = _fan_zone_rows(name)
        except Exception as e:               # noqa: BLE001
            print(f'== {name}: FAIL {e!r}')
            continue
        z_obj = opj.get('object_pos', 0.0)
        na = 0.0
        for (ws, nz), row in prn['gabarit'].items():
            if nz == 0 and row.get('Ax'):
                na = row['Ax']
        lam = wl * 1e-3
        media = _n_media(system, wl)
        z_last = sum(s.thickness for s in system.surfaces[:-1])
        # гауссова плоскость
        if near:
            if z_obj < 0.0:
                y0, u0, z0p = 0.0, 0.05, z_obj
            else:
                z0p = -(abs(z_obj) + 100.0)
                u0 = -0.05
                y0 = (z_obj - z0p) * (-u0)
            yp, up = _paraxial_ray(system, wl, y0, u0, z0p)
            L_p = -yp / up if abs(up) > 1e-15 else None
        else:
            L_p = paraxial_of(system, wl)['bfd']
        print(f'== {name}  λ={wl:.4f}  L_p={L_p}  зона-строк={len(wave_rows)}')
        print(f"  {'zone':>6} {'банк':>10} {'D=банк-OPLv':>12}"
              f" {'D-Ssin':>12} {'ΣnTX²/2':>12} {'предсказD':>12} {'t_ext':>10}")
        for zone, bank in wave_rows:
            res = _ray_of(system, near, z_obj, na, ax_semi, zone, wl)
            res_dy = _ray_of(system, near, z_obj, na, ax_semi,
                             zone * (1.0 + 1e-4), wl)
            if not (res.success and res_dy.success
                    and len(res.path) >= 2):
                print(f'  {zone:>6.3f}: trace fail')
                continue
            # OPL до плоскости z_last по сегментам (марш-стоп)
            opl_v = 0.0
            pts = [p for p in res.path]
            for i in range(len(pts) - 1):
                p0, p1 = pts[i], pts[i + 1]
                if p1[2] > z_last + 1e-9 and p0[2] <= z_last + 1e-9:
                    # частичный сегмент до z_last
                    t = (z_last - p0[2]) / (p1[2] - p0[2])
                    pe = (p0[0] + t * (p1[0] - p0[0]),
                          p0[1] + t * (p1[1] - p0[1]), z_last)
                    opl_v += math.dist(p0, pe) * media[min(i, len(media) - 1)]
                    break
                opl_v += math.dist(p0, p1) * media[min(i, len(media) - 1)]
                if p1[2] > z_last - 1e-9:
                    break
            # главный луч (chief) той же схемой
            chief = _ray_of(system, near, z_obj, na, ax_semi, 0.0, wl)
            opl_cv = 0.0
            for i in range(len(chief.path) - 1):
                p0, p1 = chief.path[i], chief.path[i + 1]
                if p1[2] > z_last + 1e-9 and p0[2] <= z_last + 1e-9:
                    t = (z_last - p0[2]) / (p1[2] - p0[2])
                    pe = (p0[0] + t * (p1[0] - p0[0]),
                          p0[1] + t * (p1[1] - p0[1]), z_last)
                    opl_cv += math.dist(p0, pe) * media[min(i, len(media) - 1)]
                    break
                opl_cv += math.dist(p0, p1) * media[min(i, len(media) - 1)]
                if p1[2] > z_last - 1e-9:
                    break
            dOPL = (opl_v - opl_cv) / lam
            # выходная геометрия
            lastpts = [p for p in res.path if p[2] <= z_last + 1e-9]
            y_last = lastpts[-1][1]
            z_exit = lastpts[-1][2]
            p0, p1 = res.path[-3], res.path[-2]
            dz = p1[2] - p0[2]
            slope = (p1[1] - p0[1]) / dz if abs(dz) > 1e-12 else 0.0
            sinu = slope / math.sqrt(1.0 + slope * slope)
            Lz = (z_exit - y_last / slope - z_last
                  if abs(slope) > 1e-15 else None)
            S = (Lz - L_p) if (Lz is not None and L_p is not None) else None
            Ssin = (S * sinu / lam) if S is not None else None
            # расширение до гауссовой сферы (порт-замыкание)
            dz_img = (z_last + L_p) - z_exit if L_p is not None else 0.0
            y_img = y_last + slope * dz_img
            r_ref = abs(y_img) if L_p is not None else 0.0
            # точное t_ext: |P + t d − C| = R, C=(0,0,z_last+L_p)
            dy_, dz_ = sinu, math.sqrt(max(0.0, 1.0 - sinu * sinu))
            b = dz_ * L_p - y_last * dy_
            disc = b * b - y_last * y_last
            t_ext = (b - math.sqrt(disc)) if disc > 0 else 0.0
            # Σ n·T_s·X_s²/2
            T = _tube_T(system, res, res_dy, wl)
            sumT = 0.0
            for i, tval in enumerate(T):
                if tval is None:
                    continue
                y_s = res.path[i][1]
                sumT += media[min(i, len(media) - 1)] * tval * y_s * y_s / 2.0
            D = bank - dOPL
            Dpred = sumT / lam - (Ssin or 0.0) - t_ext / lam
            print(f'  {zone:>6.3f} {bank:>10.4f} {D:>12.4f}'
                  f' {D - (Ssin or 0):>12.4f} {sumT / lam:>12.4f}'
                  f' {Dpred:>12.4f} {t_ext:>10.5f}')


if __name__ == '__main__':
    main()
