# -*- coding: utf-8 -*-
"""TASK_EDGE2: из какого состояния OPAL печатает поперечную (гр.мнсек).

Банк-подсказка §4.3(iii): D(попер) = −y_g·206265/α_банк экстраполирует к
(L_p − sP′) с остатком ∝ zone². Пробы замен знаменателя/числителя на
зонально-лучевые (аберрированные) величины против банка.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import (parse_golden_opj, parse_golden_prn,
                                    opj_to_system, paraxial_of,
                                    _paraxial_ray, arcsec_of_ddmmss,
                                    near_object_axial_fan, _BANK_DIR)
from ray_tracing import Ray, trace_ray_through_system

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
    pp = paraxial_of(system, wl)
    sp_prime = pp['sP_prime']
    fan = near_object_axial_fan(system, wl, [1.0, 0.866, 0.707, 0.5],
                                na, z_obj)
    L_p = fan[0]['L_p']
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    print('== %s: z_obj=%.4f NA=%.5f L_p=%.4f sP\'=%.4f z_last=%.4f'
          % (name, z_obj, na, L_p, sp_prime, z_last))

    a1 = prn['axial1']['rows']
    zones = sorted([z for z in a1 if z != 0.0], reverse=True)
    bank = {z: {'long': a1[z]['long'][0],
                'trans_as': arcsec_of_ddmmss(a1[z]['trans'][0])} for z in zones}

    print('\nзона  банк_попер\"     порт_попер\"   отнош.   |  D_банк   D_паракс  ΔD      ΔD/z²')
    for row in fan:
        z = row['zone']
        b = bank.get(z)
        if not (b and row['ok']):
            continue
        y_exit, slope = row['y_exit'], row['slope']
        y_g = y_exit + slope * L_p            # числитель текущего правила
        D_par = L_p - sp_prime
        alpha_port = -y_g / D_par * ARCSEC
        D_bank = -y_g * ARCSEC / b['trans_as']
        print('%.3f  %10.2f  %12.2f  %7.4f  | %9.3f %9.3f %8.3f %8.3f'
              % (z, b['trans_as'], alpha_port, b['trans_as'] / alpha_port,
                 D_bank, D_par, D_bank - D_par,
                 (D_bank - D_par) / (z * z)))

    # кандидаты знаменателя/числителя из зонального луча
    print('\nкандидаты α (arcsec) и отклонение от банка:')
    for row in fan:
        z = row['zone']
        b = bank.get(z)
        if not (b and row['ok']):
            continue
        y_exit, slope, L_z = row['y_exit'], row['slope'], row['L']
        y_g = y_exit + slope * L_p
        D_par = L_p - sp_prime
        cands = {
            'cur: y_g/D_par': -y_g / D_par,
            'A: y_g/(L_z-sP\')': -y_g / (L_z - sp_prime),
            'B: y_z/(D_par)': -(y_exit + slope * L_z) / D_par,
            'C: y_z/(L_z-sP\')': -(y_exit + slope * L_z) / (L_z - sp_prime),
            'D: y_exit/(L_z-sP\')': -y_exit / (L_z - sp_prime),
            'E: y_g/(L_z-sP\'+dy?)': None,
        }
        out = ['з%.3f' % z]
        for k, v in cands.items():
            if v is None:
                continue
            va = v * ARCSEC
            out.append('%s=%9.2f(%+6.2f%%)' % (k[:16], va,
                        100.0 * (va - b['trans_as']) / b['trans_as']))
        print('  ' + '  '.join(out))
    return fan, bank, L_p, sp_prime


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
