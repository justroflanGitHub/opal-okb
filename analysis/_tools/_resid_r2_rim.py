# -*- coding: utf-8 -*-
"""TASK_RESID R2: кромка OBEKTIV/OKULAR — где OPAL определяет зональный луч.

Обе системы — ближний предмет (obj=1), дальнее изображение: строки прод
дптр = 1000/L − 1000/L_p, попер гр.мнсек = −y_гаусс/(L_p − sP′)·206265,
Tg′·100 = |y_зрачок|, Н ЗР = 100·tg u. Дефицит банка/порта ∝ zone² —
гипотеза (б): зональный веер OPAL определён высотами на ограничивающей
поверхности (габарит «Ограничения: к 3»), не углами arcsin(zone·NA).

Проба: зональный луч = луч с высотой zone·h_rim на поверхности-якоре;
секанта по углу запуска. Сверка всех величин с банком.
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


def load(name):
    opj = parse_golden_opj(os.path.join(GOLDEN, name + '.OPJ'))
    system = opj_to_system(opj)
    prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
    return opj, system, prn


def fan_ray(z_obj, na, zone):
    su = na * zone
    tu = su / math.sqrt(1.0 - su * su)
    return Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1.0 - su * su)), tu


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
    y0p, u0p, z0p = 0.0, 0.05, z_obj
    y_p, u_p = _paraxial_ray(system, wl, y0p, u0p, z0p)
    L_p = -y_p / u_p
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    ns = len(system.surfaces)
    print('== %s: z_obj=%.4f NA=%.5f L_p=%.4f sP\'=%.4f z_last=%.4f ns=%d'
          % (name, z_obj, na, L_p, sp_prime, z_last, ns))

    def trace(su):
        ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1.0 - su * su))
        return trace_ray_through_system(system, ray, wl)

    def rows(res):
        prev, last = res.path[-2], res.path[-1]
        dz = last[2] - prev[2]
        slope = (last[1] - prev[1]) / dz if abs(dz) > 1e-12 else None
        if slope is None:
            return None
        L = last[2] - last[1] / slope - z_last
        y_pupil = last[1] + slope * ((z_last + sp_prime) - last[2])
        y_g = last[1] + slope * L_p
        return {
            'L': L, 'slope': slope, 'y_pupil': y_pupil, 'y_exit': last[1],
            'long_dptr': 1000.0 / L - 1000.0 / L_p if abs(L) > 1e-9 else None,
            'trans_as': -y_g / (L_p - sp_prime) * ARCSEC,
        }

    rim = trace(na)
    print('rim (з.1.0 arcsin NA) path:')
    for i, p in enumerate(rim.path):
        print('  [%d] z=%10.4f y=%10.4f' % (i, p[2], p[1]))
    rim_h = [p[1] for p in rim.path]

    # банк
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

    print('\n-- порт (углы arcsin(zone·NA)):')
    for z in zones:
        res = trace(na * z)
        r = rows(res)
        b = bank[z]
        print('  з%.3f: прод %8.3f (банк %8.3f)  попер %9.2f (%9.2f)  '
              'Tg %7.3f (%7.3f)  W %9.3f (%9.3f)  НЗР %7.3f (%7.3f)' % (
                  z, r['long_dptr'], b['long'], r['trans_as'], b['trans_as'],
                  abs(r['y_pupil']), b.get('tg100', float('nan')),
                  float('nan'), b.get('wave', float('nan')),
                  100.0 * na * z / math.sqrt(1 - (na * z) ** 2),
                  b.get('h_zr', float('nan'))))

    # якоря высот: каждая точка пути rim (кроме запуска)
    for idx in range(1, len(rim.path)):
        print('\n-- якорь [%d] z=%.3f h_rim=%.4f: h = zone·h_rim' % (
            idx, rim.path[idx][2], rim_h[idx]))
        bad = 0
        for z in zones:
            target = z * rim_h[idx]
            # секанта по su
            a, b = 0.5 * na * z, 1.0 * na * z
            ra, rb = trace(a), trace(b)
            if not (ra.success and rb.success):
                print('   з%.3f: старт не прошёл' % z)
                bad += 1
                break
            fa, fb = ra.path[idx][1], rb.path[idx][1]
            res = None
            for _ in range(60):
                if abs(fb - fa) < 1e-15:
                    break
                c = b + (target - fb) * (b - a) / (fb - fa)
                if not (1e-6 < c < 0.999):
                    break
                rc = trace(c)
                if not rc.success:
                    break
                fc = rc.path[idx][1]
                a, fa, b, fb, res = b, fb, c, fc, rc
                if abs(fb - target) < 1e-10:
                    break
            if res is None or abs(fb - target) > 1e-7:
                print('   з%.3f: секанта не сошлась' % z)
                bad += 1
                break
            r = rows(res)
            bk = bank[z]
            print('   з%.3f: прод %8.3f (%8.3f)  попер %9.2f (%9.2f)  '
                  'Tg %7.3f (%7.3f)' % (
                      z, r['long_dptr'], bk['long'],
                      r['trans_as'], bk['trans_as'],
                      abs(r['y_pupil']), bk.get('tg100', float('nan'))))
        if bad:
            continue


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
