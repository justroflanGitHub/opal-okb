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
        y_pup = y_exit + slope * sp_prime
        cands = {
            'cur: y_g/D_par': -y_g / D_par,
            'A: y_g/(L_z-sP\')': -y_g / (L_z - sp_prime),
            'A2: y_pup/(L_z-sP\')': -y_pup / (L_z - sp_prime),
            'A3: y_g/(L_z-sP\')/cos': -y_g / (L_z - sp_prime)
                / math.sqrt(1.0 + slope * slope),
            'A4: slope·(L_p-L_z)/(L_z-sP\')':
                -slope * (L_p - L_z) / (L_z - sp_prime),
        }
        out = ['з%.3f' % z]
        for k, v in cands.items():
            va = v * ARCSEC
            out.append('%s=%9.2f(%+6.2f%%)' % (k[:16], va,
                        100.0 * (va - b['trans_as']) / b['trans_as']))
        # диагностика: подразумеваемый числитель при D = L_z − sP′
        y_impl = -b['trans_as'] * (L_z - sp_prime) / ARCSEC
        print('  ' + '  '.join(out))
    # ГИПОТЕЗА ЭФФЕКТИВНОГО ЛУЧА: банк (прод, Tg', попер) согласован с
    # одним выходным состоянием (y_m, u_m):
    #   прод = 1000/L_m − 1000/L_p (L_m = −y_m/u_m)
    #   Tg'·100 = −100·u_m  ИЛИ  |y_pup,m| = |u_m·(sP'−L_m)|
    #   попер = −u_m·(L_p−L_m)/(L_m−sP')·206265
    print('\nэффективный луч: L_m из прод; u_m из Tg\' (2 семантики); '
          'предсказание попер против банка:')
    for row in fan:
        z = row['zone']
        b = bank.get(z)
        if not (b and row['ok'] and 'tg100' in b):
            continue
        L_m = 1.0 / (b['long'] / 1000.0 + 1.0 / L_p)
        tg = b['tg100']
        # семантика 1: Tg' = −100·u_m
        u1 = -tg / 100.0
        a1_ = -u1 * (L_p - L_m) / (L_m - sp_prime) * ARCSEC
        # семантика 2: Tg' = |y_pup,m| = |u_m·(sP'−L_m)|
        u2 = tg / (sp_prime - L_m)
        a2_ = -u2 * (L_p - L_m) / (L_m - sp_prime) * ARCSEC
        print('  з%.3f: L_m=%9.4f  u1=%9.5f α1=%9.2f(%+6.2f%%)  '
              'u2=%9.5f α2=%9.2f(%+6.2f%%)  банк=%9.2f'
              % (z, L_m, u1, a1_, 100.0 * (a1_ - b['trans_as']) / b['trans_as'],
                 u2, a2_, 100.0 * (a2_ - b['trans_as']) / b['trans_as'],
                 b['trans_as']))
    # то же самое, но (y_m,u_m) из реального луча порта — для контраста
    print('\nреальный луч порта: прод/Tg/попер из (y_exit,slope):')
    for row in fan:
        z = row['zone']
        b = bank.get(z)
        if not (b and row['ok'] and 'tg100' in b):
            continue
        y_e, u_e, L_r = row['y_exit'], row['slope'], row['L']
        prod_r = 1000.0 / L_r - 1000.0 / L_p
        tg_r = abs(u_e * (sp_prime - L_r))
        a_r = -u_e * (L_p - L_r) / (L_r - sp_prime) * ARCSEC
        print('  з%.3f: прод %8.3f (банк %8.3f, %+5.2f%%)  '
              'Tg|ypup| %7.3f (банк %7.3f, %+5.2f%%)  попер %9.2f '
              '(банк %9.2f, %+5.2f%%)'
              % (z, prod_r, b['long'],
                 100.0 * (prod_r - b['long']) / b['long'],
                 tg_r, b['tg100'],
                 100.0 * (tg_r - b['tg100']) / b['tg100'],
                 a_r, b['trans_as'],
                 100.0 * (a_r - b['trans_as']) / b['trans_as']))
    return fan, bank, L_p, sp_prime


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
