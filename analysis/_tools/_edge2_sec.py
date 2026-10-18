# -*- coding: utf-8 -*-
"""TASK_EDGE2: единый множитель длин (1+q·z²) в печати прод/Tg'/попер.

Наблюдение: банк = pupil-referenced геометрия реального луча, но ВСЕ
ДЛИНЫ масштабированы (1+q·z²): Tg' — один множитель, попер — квадрат
(числитель·знаменатель), прод(дптр) — деление. q ≈ slope²/2 (sec-семья
точной тригонометрии против линеаризованной). Тест: q из кандидатов
углов + проверка цензорных систем (их q·z² должно быть ≤1e-3).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import (parse_golden_opj, parse_golden_prn,
                                    opj_to_system, paraxial_of,
                                    arcsec_of_ddmmss, near_object_axial_fan,
                                    port_axial_rows, axial_fan, _BANK_DIR)
from ray_tracing import Ray, trace_ray_through_system

GOLDEN = r'C:\GOLDEN_DOS'
ARCSEC = 206264.80624709636


def load(name):
    opj = parse_golden_opj(os.path.join(GOLDEN, name + '.OPJ'))
    system = opj_to_system(opj)
    prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
    return opj, system, prn


def near_state(name):
    """(зона → состояние) для ближнего предмета."""
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
    return opj, prn, fan, L_p, sp_prime, na


def main(name):
    opj, prn, fan, L_p, sp_prime, na = near_state(name)
    wl = opj['wls'][0]
    D = L_p - sp_prime
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
    print('== %s: L_p=%.4f sP\'=%.4f' % (name, L_p, sp_prime))
    print('зона | q_Tg      q_попер/2  q_прод    | slope²/2  atan²/2  '
          '| прод_прав(1/(Lz-sP\'))  банк     Δ%')
    for row in fan:
        z = row['zone']
        b = bank.get(z)
        if not (b and row['ok'] and 'tg100' in b):
            continue
        y_e, sl, L_z = row['y_exit'], row['slope'], row['L']
        y_g = y_e + sl * L_p
        y_pup = row['y_pupil']
        # эмпирические q из трёх печатей
        q_tg = (b['tg100'] / y_pup - 1.0) / (z * z)
        q_tr = (b['trans_as'] / (-y_g / D * ARCSEC) - 1.0) / (2.0 * z * z)
        prod_rule = (1000.0 / (L_z - sp_prime) - 1000.0 / D)
        q_pr = (1.0 - b['long'] / prod_rule) / (z * z)
        print('%.3f| %9.5f %9.5f %9.5f | %9.5f %9.5f | %10.4f %9.4f %+6.2f%%'
              % (z, q_tg, q_tr, q_pr, sl * sl / 2.0,
                 math.atan(sl) ** 2 / 2.0, prod_rule, b['long'],
                 100.0 * (prod_rule - b['long']) / b['long']))
    return


def censor(name):
    """Цензор: q·z² для GREEN-систем должно быть ≤1e-3."""
    opj, prn, fan, L_p, sp_prime, na = near_state(name)
    if fan[0]['L_p'] is None:
        print('== %s: афокальный (L_p=None), попер=slope-ветка' % name)
        return
    a1 = prn['axial1']['rows']
    zones = sorted([z for z in a1 if z != 0.0], reverse=True)
    print('== %s: slope²/2 по зонам (порог цензоры q·z²≤1e-3):' % name)
    for row in fan:
        z = row['zone']
        if row['ok']:
            sl = row['slope']
            print('  z%.3f slope=%9.5f slope²/2=%9.6f atan²/2=%9.6f'
                  % (z, sl, sl * sl / 2, math.atan(sl) ** 2 / 2))


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
    print()
    for nm in ('121', 'ST4', 'LAB6_GAS', 'KURSOVIK'):
        try:
            censor(nm)
        except Exception as exc:
            print('== %s: %r' % (nm, exc))
