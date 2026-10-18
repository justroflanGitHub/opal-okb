# -*- coding: utf-8 -*-
"""TASK_EDGE2: подразумеваемое выходное состояние банка.

Банк печатает пару (Tg'·100, попер) на зону. Если обе величины —
линейные комбинации ОДНОГО выходного состояния (y_B, u_B):
  Tg'·100 = 100·(y_B + u_B·sP')      (высота в плоскости выходного зрачка)
  попер   = −(y_B + u_B·L_p)/(L_p − sP')·206265  (текущая конвенция)
то банк решается в (y_B, u_B); сравнение с реальным лучом порта даёт
девиацию (Δy, Δu) — цель для марша. Также прод из L_m = −y_B/u_B.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import (parse_golden_opj, parse_golden_prn,
                                    opj_to_system, paraxial_of,
                                    arcsec_of_ddmmss, near_object_axial_fan,
                                    _BANK_DIR)

GOLDEN = r'C:\GOLDEN_DOS'
ARCSEC = 206264.80624709636


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
    sp_prime = paraxial_of(system, wl)['sP_prime']
    fan = near_object_axial_fan(system, wl, [1.0, 0.866, 0.707, 0.5],
                                na, z_obj)
    L_p = fan[0]['L_p']
    D = L_p - sp_prime
    z_last = sum(s.thickness for s in system.surfaces[:-1])

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
            bank[z]['h_zr'] = r['h_zr']

    print('== %s: L_p=%.4f sP\'=%.4f D=%.4f' % (name, L_p, sp_prime, D))
    print('зона | y_pup_B   y_pup_R   Δ%%    | y_g_B    y_g_R    Δ%%    |'
          ' u_B       u_R      Δu        | y_B       y_R      Δy')
    for row in fan:
        z = row['zone']
        b = bank.get(z)
        if not (b and row['ok'] and 'tg100' in b):
            continue
        # банк → состояние
        y_pup_B = b['tg100'] / 100.0            # Tg' = высота в зрачке
        y_g_B = -b['trans_as'] / ARCSEC * D     # попер-инверсия
        u_B = (y_g_B - y_pup_B) / D             # из разности
        y_B = y_pup_B - u_B * sp_prime
        # порт (реальный луч)
        y_e, sl = row['y_exit'], row['slope']
        y_g_R = y_e + sl * L_p
        y_pup_R = row.get('y_pupil')
        # прод из банка-состояния
        L_m = -y_B / u_B if abs(u_B) > 1e-15 else None
        prod_B = 1000.0 / L_m - 1000.0 / L_p if L_m else None
        print('%.3f| %8.4f %8.4f %+6.2f%% | %8.4f %8.4f %+6.2f%% |'
              ' %9.5f %9.5f %+9.5f | %8.4f %8.4f %+8.4f'
              % (z, y_pup_B, y_pup_R,
                 100.0 * (y_pup_B - y_pup_R) / y_pup_R,
                 y_g_B, y_g_R, 100.0 * (y_g_B - y_g_R) / y_g_R,
                 u_B, sl, u_B - sl, y_B, y_e, y_B - y_e))
        print('     прод_из_(y_B,u_B)=%9.4f  банк_прод=%9.4f  Δ=%+7.2f%%'
              % (prod_B, b['long'],
                 100.0 * (prod_B - b['long']) / b['long']))
        # девиации: как функция зоны
        print('     Δu/slope=%+7.4f  Δy/y_exit=%+7.4f  Δu/z³=%+9.6f'
              '  Δy/z³=%+9.6f  z²:Δu/z²=%+8.5f'
              % ((u_B - sl) / sl, (y_B - y_e) / y_e,
                 (u_B - sl) / z ** 3, (y_B - y_e) / z ** 3,
                 (u_B - sl) / z ** 2))


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
