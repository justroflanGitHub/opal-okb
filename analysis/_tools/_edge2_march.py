# -*- coding: utf-8 -*-
"""TASK_EDGE2: матрица «марш = параксиальный перенос с реальными семенами».

Гипотеза: печатные прод/Tg'/попер = состояние ЛИНЕЙНОГО марша
(параксиальный перенос), засеянного реальными величинами луча на
некоторой плоскости (запуск/поверхность1/кромка). Скан плоскостей
засева × формул против банка OBEKTIV/OKULAR.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import (parse_golden_opj, parse_golden_prn,
                                    opj_to_system, paraxial_of,
                                    _paraxial_ray, arcsec_of_ddmmss,
                                    _BANK_DIR)
from ray_tracing import Ray, trace_ray_through_system

GOLDEN = r'C:\GOLDEN_DOS'
ARCSEC = 206264.80624709636
ZONES = [1.0, 0.866, 0.707, 0.5]


def load(name):
    opj = parse_golden_opj(os.path.join(GOLDEN, name + '.OPJ'))
    system = opj_to_system(opj)
    prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
    return opj, system, prn


def main(name):
    opj, system, prn = load(name)
    wl = opj['wls'][0]
    z_obj = opj['object_pos']
    na = None
    for (wls, nz), r in prn['gabarit'].items():
        if nz == 0:
            na = r['Ax']
            break
    pp = paraxial_of(system, wl)
    sp_prime = pp['sP_prime']
    y_p0, u_p0 = 0.0, 0.05
    if z_obj >= 0.0:
        z0_par = -(abs(z_obj) + 100.0)
        y_p0, u_p0 = (z_obj - z0_par) * 0.05, -0.05
    else:
        z0_par = z_obj
    y_p, u_p = _paraxial_ray(system, wl, y_p0, u_p0, z0_par)
    L_p = -y_p / u_p
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    print('== %s: z_obj=%.4f NA=%.5f L_p=%.5f sP\'=%.5f z_last=%.4f'
          % (name, z_obj, na, L_p, sp_prime, z_last))

    a1 = prn['axial1']['rows']
    a2 = prn['axial2']['rows']
    zones = sorted([z for z in a1 if z != 0.0], reverse=True)
    bank = {z: {'long': a1[z]['long'][0],
                'trans_as': arcsec_of_ddmmss(a1[z]['trans'][0])} for z in zones}
    for r in a2.values():
        if r.get('h_zr') and r['tg100']:
            z = min(zones, key=lambda zz: abs(
                100.0 * (na * zz) / math.sqrt(1 - (na * zz) ** 2)
                - r['h_zr']))
            bank[z]['tg100'] = r['tg100']
            bank[z]['wave'] = r['wave'][0] if r['wave'] else None
            bank[z]['h_zr'] = r['h_zr']

    def trace(su):
        if z_obj < 0.0:
            ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1.0 - su * su))
        else:
            z0 = -(abs(z_obj) + 100.0)
            tu = su / math.sqrt(1.0 - su * su)
            ray = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                      math.sqrt(1.0 - su * su))
        return trace_ray_through_system(system, ray, wl)

    # реальные семена на каждой поверхности (после преломления) + запуск
    seed_planes = [('launch', None)]
    ns = len(system.surfaces)
    for si in range(ns):
        seed_planes.append(('surf%d' % (si + 1), si))
    # реальные пути зоны (для семян и для формул с реальным лучом)
    real = {}
    for z in zones:
        res = trace(na * z)
        real[z] = res

    print('\nскан: плоскость засева × формула попер; отклонение от банка, %')
    for pname, si in seed_planes:
        errs_t, errs_l, errs_p = [], [], []
        detail = []
        for z in zones:
            b = bank[z]
            res = real[z]
            if pname == 'launch':
                su = na * z
                tu = su / math.sqrt(1.0 - su * su)
                if z_obj < 0.0:
                    y0, u0, z0 = 0.0, tu, z_obj
                else:
                    z0s = -(abs(z_obj) + 100.0)
                    y0, u0 = (z_obj - z0s) * tu, -tu
            else:
                p_prev, p = res.path[si], res.path[si + 1]
                # наклон сегмента после поверхности si (до след.)
                p_next = res.path[si + 2] if si + 2 < len(res.path) else None
                if p_next is None:
                    continue
                dz = p_next[2] - p[2]
                u_seg = (p_next[1] - p[1]) / dz
                y0, u0, z0 = p[1], u_seg, p[2]
            y_m, u_m = _paraxial_ray(system, wl, y0, u0, z0)
            L_m = -y_m / u_m
            y_g_m = y_m + u_m * L_p
            f1 = -y_g_m / (L_m - sp_prime) * ARCSEC
            f2 = -y_g_m / (L_p - sp_prime) * ARCSEC
            tg1 = abs(100.0 * u_m)
            tg2 = abs(y_m + u_m * sp_prime)
            pr1 = 1000.0 / L_m - 1000.0 / L_p
            pr2 = (1000.0 / (L_m - sp_prime)
                   - 1000.0 / (L_p - sp_prime))
            et = min(abs(f1 - b['trans_as']) / abs(b['trans_as']),
                     abs(f2 - b['trans_as']) / abs(b['trans_as']))
            errs_t.append(et)
            best_f = ('F1' if abs(f1 - b['trans_as'])
                      < abs(f2 - b['trans_as']) else 'F2')
            errs_l.append(min(abs(pr1 - b['long']) / abs(b['long']),
                              abs(pr2 - b['long']) / abs(b['long'])))
            if 'tg100' in b:
                errs_p.append(min(
                    abs(tg1 - b['tg100']) / abs(b['tg100']),
                    abs(tg2 - b['tg100']) / abs(b['tg100'])))
            detail.append('z%.3f:%s %+.2f%%/(F2 %+.2f%%)'
                          % (z, best_f,
                             100.0 * (f1 - b['trans_as']) / b['trans_as'],
                             100.0 * (f2 - b['trans_as']) / b['trans_as']))
        print('  %-7s попер: %s | max %.2f%%  Tg max %.2f%%  прод max %.2f%%'
              % (pname, '  '.join(detail), 100.0 * max(errs_t),
                 100.0 * (max(errs_p) if errs_p else float('nan')),
                 100.0 * max(errs_l)))


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
