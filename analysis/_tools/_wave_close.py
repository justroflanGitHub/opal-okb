# -*- coding: utf-8 -*-
"""Тест «печать = OPL до вершины последней поверхности + QF(y²)/2»
(замыкание марша 0xd074). Если B4Y_eff = 2·Q2/(n·y²) постоянна по
зонам системы — замыкание чисто квадратичное, и её происхождение
можно вывести геометрически.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.golden_verify import (  # noqa: E402
    parse_golden_prn, parse_golden_opj, opj_to_system, _n_media,
    _GOLDEN_DOS,
)
from analysis.aberrations import _compute_ray_start  # noqa: E402
from optics_utils import make_field_ray  # noqa: E402
from ray_tracing import Ray, trace_ray_through_system  # noqa: E402
from domain.calculations import paraxial_trace  # noqa: E402

_BANK_DIR = os.path.join(os.path.dirname(__file__), '..', 'reverse_data',
                         'golden', 'bank')


def opl_vertex(system, res, wl):
    """OPL луча до ПЛОСКОСТИ вершины последней поверхности (проекция)."""
    media = _n_media(system, wl)
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    opl = 0.0
    for i in range(len(res.path) - 1):
        p0, p1 = res.path[i], res.path[i + 1]
        if p1[2] > z_last + 1e-9:           # сегмент за последней
            break
        opl += media[min(i, len(media) - 1)] * math.dist(p0, p1)
    # терминальный отрезок от последней поверхности до плоскости z_last
    last = res.path[-1]
    dz_last = z_last - [p[2] for p in res.path
                        if p[2] <= z_last + 1e-9][-1][2]
    return opl + dz_last                    # воздух, n=1, вдоль оси-z


def main():
    names = sys.argv[1:] or ['121', 'OKULAR', 'OBEKTIV', 'S_KOND1',
                             'KURSOVIK', 'OPTICS#1', 'US00KI02']
    for name in names:
        prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
        opj = parse_golden_opj(os.path.join(_GOLDEN_DOS, name + '.OPJ'))
        system = opj_to_system(opj)
        wl = opj['wls'][0]
        near = (opj['obj_type'] == 1)
        lam = wl * 1e-3
        nsurf = len(system.surfaces)
        z_last = sum(s.thickness for s in system.surfaces[:-1])
        hzr_vals = [r['h_zr'] for r in prn['axial2'].get('rows', {}).values()
                    if r.get('h_zr') is not None]
        ax_semi = max(hzr_vals) if hzr_vals else opj['aperture_semi']
        na = 0.0
        for (ws, nz), row in prn['gabarit'].items():
            if nz == 0 and row.get('Ax'):
                na = row['Ax']
        if not na:
            na = opj['aperture_semi']

        # сшивка зон как в compare_system
        zones_sorted = sorted(prn['axial1'].get('rows', {}).keys(),
                              reverse=True)
        scale = ax_semi if not near else 100.0 * na
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
                z = next((zz for zz in zones_sorted if zz not in used),
                         None)
            if z is None:
                break
            used.add(z)
            wave_rows.append((z, et['wave'][0]))

        if not near:
            parax = paraxial_trace(system, wl=wl)
            z_start, z_pupil = _compute_ray_start(system, parax)
            chief = trace_ray_through_system(
                system, make_field_ray(system, 0.0, 0.0, 0.0,
                                       z_start, z_pupil), wl)

            def zray(zone):
                return trace_ray_through_system(
                    system, make_field_ray(system, 0.0, zone * ax_semi, 0.0,
                                           z_start, z_pupil), wl)
        else:
            z_obj = opj['object_pos']
            if z_obj < 0.0:
                chief = trace_ray_through_system(
                    system, Ray(0.0, 0.0, z_obj, 0.0, 0.0, 1.0), wl)
            else:
                chief = trace_ray_through_system(
                    system, Ray(0.0, 0.0, -(abs(z_obj) + 100.0),
                                0.0, 0.0, 1.0), wl)

            def zray(zone):
                su = na * zone
                if z_obj < 0.0:
                    ray = Ray(0.0, 0.0, z_obj, 0.0, su,
                              math.sqrt(1.0 - su * su))
                else:
                    tu = su / math.sqrt(1.0 - su * su)
                    z0 = -(abs(z_obj) + 100.0)
                    ray = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                              math.sqrt(1.0 - su * su))
                return trace_ray_through_system(system, ray, wl)

        oplv_c = opl_vertex(system, chief, wl)
        print(f'== {name}  λ={wl:.5f}  nsurf={nsurf}')
        print(f"  {'zone':>6} {'bank':>10} {'V(λ)':>11} {'Q2=bank-V':>10}"
              f" {'Q2(мм)':>9} {'y_last':>8} {'sinU':>8} {'B4Yeff':>11}"
              f" {'B4Yeff·z?':>2}")
        for zone, bank in wave_rows:
            res = zray(zone)
            if not res.success or len(res.path) < 2:
                print(f'  {zone:>6.3f} {bank:>10.4f}  trace fail')
                continue
            V = (opl_vertex(system, res, wl) - oplv_c) / lam
            Q2 = bank - V
            Q2mm = Q2 * lam
            # точка на последней поверхности и угол выхода
            lastpts = [p for p in res.path if p[2] <= z_last + 1e-9]
            y_last = lastpts[-1][1] if lastpts else res.path[-1][1]
            p0, p1 = res.path[-3], res.path[-2]
            dz = p1[2] - p0[2]
            t = (p1[1] - p0[1]) / dz if abs(dz) > 1e-12 else 0.0
            su = t / math.sqrt(1 + t * t)
            b4 = 2.0 * Q2mm / (y_last * y_last) if y_last else 0.0
            print(f'  {zone:>6.3f} {bank:>10.4f} {V:>11.4f} {Q2:>10.4f}'
                  f' {Q2mm:>9.5f} {y_last:>8.3f} {su:>8.5f} {b4:>11.6f}')


if __name__ == '__main__':
    main()
