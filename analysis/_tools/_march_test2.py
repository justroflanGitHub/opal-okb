# -*- coding: utf-8 -*-
"""Тест-2 марша: bank ?= V(точный OPL до вершины) + R₂(z) (параксиальное
замыкание 2-го порядка). Если T = bank−V−R₂ ≈ 0 — марш точен внутри
системы, отклонение банка = старшие порядки замыкания сферой.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.golden_verify import (  # noqa: E402
    parse_golden_prn, parse_golden_opj, opj_to_system, _n_media,
    _GOLDEN_DOS,
)
from analysis.aberrations import (  # noqa: E402
    _compute_ray_start, _air_exit_direction, _opl_to_reference_sphere,
)
from optics_utils import make_field_ray  # noqa: E402
from ray_tracing import Ray, trace_ray_through_system  # noqa: E402
from domain.calculations import paraxial_trace  # noqa: E402

_BANK_DIR = os.path.join(os.path.dirname(__file__), '..', 'reverse_data',
                         'golden', 'bank')


def V(system, res, wl):
    """Точный OPL до плоскости вершины последней поверхности, мм."""
    media = _n_media(system, wl)
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    opl = 0.0
    for i in range(len(res.path) - 1):
        p0, p1 = res.path[i], res.path[i + 1]
        if p1[2] > z_last + 1e-9:
            break
        opl += media[min(i, len(media) - 1)] * math.dist(p0, p1)
    pts = [p for p in res.path if p[2] <= z_last + 1e-9]
    return opl + (z_last - pts[-1][2])


def main():
    names = sys.argv[1:] or ['S_KOND1', 'OBEKTIV', 'OKULAR', '121',
                             'KURSOVIK', 'OPTICS#1']
    for name in names:
        prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
        opj = parse_golden_opj(os.path.join(_GOLDEN_DOS, name + '.OPJ'))
        system = opj_to_system(opj)
        wl = opj['wls'][0]
        lam = wl * 1e-3
        near = (opj['obj_type'] == 1)
        hzr = [r['h_zr'] for r in prn['axial2']['rows'].values()
               if r.get('h_zr') is not None]
        ax = max(hzr) if hzr else opj['aperture_semi']
        na = 0.0
        for (ws, nz), row in prn['gabarit'].items():
            if nz == 0 and row.get('Ax'):
                na = row['Ax']

        # зоны волновых строк по Н ЗР
        zones_sorted = sorted(prn['axial1']['rows'].keys(), reverse=True)
        scale = ax if not near else 100.0 * na
        used, wave = set(), []
        for tg, et in sorted(prn['axial2']['rows'].items(),
                             key=lambda kv: -kv[1]['tg100']):
            if not et.get('wave') or et['wave'][0] is None:
                continue
            hzz = et.get('h_zr')
            z = None
            if hzz is not None and scale:
                z = min(zones_sorted, key=lambda zz: abs(zz - hzz / scale))
            if z is None or z in used:
                z = next((zz for zz in zones_sorted if zz not in used), None)
            if z is None:
                break
            used.add(z)
            wave.append((z, et['wave'][0]))

        z_obj = opj.get('object_pos', 0.0)

        def ray(zone):
            if not near:
                return trace_ray_through_system(
                    system, make_field_ray(system, 0.0, zone * ax, 0.0,
                                           z_start, z_pupil), wl)
            su = na * zone
            if z_obj < 0.0:
                r = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1 - su * su))
            else:
                tu = su / math.sqrt(1 - su * su)
                z0 = -(abs(z_obj) + 100.0)
                r = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                        math.sqrt(1 - su * su))
            return trace_ray_through_system(system, r, wl)

        if not near:
            parax = paraxial_trace(system, wl=wl)
            z_start, z_pupil = _compute_ray_start(system, parax)
            chief = ray(0.0)
        else:
            if z_obj < 0.0:
                chief = trace_ray_through_system(
                    system, Ray(0.0, 0.0, z_obj, 0.0, 0.0, 1.0), wl)
            else:
                chief = trace_ray_through_system(
                    system, Ray(0.0, 0.0, -(abs(z_obj) + 100.0),
                                0.0, 0.0, 1.0), wl)
        vc = V(system, chief, wl)

        # параксиальное замыкание R2 = R(zs)/zs² (крошечная зона)
        zs = 0.02
        res = ray(zs)
        if not res.success:
            print(f'== {name}: zs-трейс упал')
            continue
        vz = V(system, res, wl)
        # W_port(zs): продление до опорной сферы/плоскости (как веер порта)
        d = _air_exit_direction(system, res, wl)
        z_last = sum(s.thickness for s in system.surfaces[:-1])
        if near:
            # ближняя ветка: сфера с центром в точке Гаусса
            from analysis.golden_verify import _paraxial_ray
            if z_obj < 0.0:
                y0, u0, z0p = 0.0, 0.05, z_obj
            else:
                z0p = -(abs(z_obj) + 100.0)
                u0 = -0.05
                y0 = (z_obj - z0p) * (-u0)
            yp, up = _paraxial_ray(system, wl, y0, u0, z0p)
            Lp = -yp / up if abs(up) > 1e-15 else None
            if Lp is None or abs(up) <= 1e-6:
                center = None
            else:
                center = (0.0, 0.0, z_last + Lp)
                rr = (z_last + Lp) - (z_last - 0.0)
            if z_obj > 0.0 and res.success:
                r0 = z_obj - res.path[0][2]
                # сагиттная поправка старта (как в веере)
                y0r = res.path[0][1]
                res.opl -= math.sqrt(r0 * r0 + y0r * y0r) - r0
            if center is None:
                wzs = (res.opl + (z_last - res.path[-1][2])
                       - (chief.opl)) / lam
            else:
                from analysis.aberrations import _opl_to_reference_sphere
                o2 = _opl_to_reference_sphere(res.opl, res.path[-1], d,
                                              center, Lp - 0.0) \
                    if d else None
                wzs = ((o2 if o2 is not None else res.opl) - chief.opl) / lam
        else:
            from analysis.aberrations import (_reference_sphere,
                                              _chief_reference_opl)
            parax = paraxial_trace(system, wl=wl)
            rc, R = _reference_sphere(system, 0.0, parax)
            oplc = _chief_reference_opl(system, wl, 0.0, z_start, z_pupil,
                                        rc, R)
            from analysis.aberrations import _opl_to_reference_sphere
            o2 = _opl_to_reference_sphere(res.opl, res.path[-1], d, rc, R) \
                if d else None
            wzs = ((o2 if o2 is not None else res.opl) - oplc) / lam
        Rs = wzs * lam - (vz - vc)
        print(f'== {name} λ={wl:.5f}: R2 = R(zs)/zs² = {Rs / zs / zs:.6e} мм'
              f'  ({Rs / zs / zs / lam:.4f} λ)')
        for zone, bank in wave:
            res = ray(zone)
            if not res.success:
                print(f'  з.{zone}: трейс упал')
                continue
            vz2 = V(system, res, wl)
            T = bank * lam - (vz2 - vc) - Rs * zone * zone / (zs * zs)
            print(f'  з.{zone}: bank={bank:10.4f}  T={T / lam:+10.4f}λ')


if __name__ == '__main__':
    main()
