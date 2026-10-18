# -*- coding: utf-8 -*-
"""TASK_EDGE2: точность λ-подгонки (q0,q1) по 12 уравнениям печати.

попер_банк = λ²·α_порт;  прод_банк = прод_прав/λ;  Tg'_банк = λ·y_pup.
Минимакс по q0,q1 → остатки по зонам. Плюс проверка sP' US00KI02
(деградация pupil-vergence → 1000/L при sP'→0).
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


def equations(name):
    """Список (вес-зона, вид, банк, порт-без-λ)."""
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
    a1 = prn['axial1']['rows']
    a2 = prn['axial2']['rows']
    zones = sorted([z for z in a1 if z != 0.0], reverse=True)
    eqs = []
    for row in fan:
        z = row['zone']
        if not row['ok']:
            continue
        b = a1.get(z)
        if not b:
            continue
        y_e, sl, L_z = row['y_exit'], row['slope'], row['L']
        y_g = y_e + sl * L_p
        pr_rule = 1000.0 / (L_z - sp_prime) - 1000.0 / D
        eqs.append((z, 'прод', b['long'][0], pr_rule, 1))
        eqs.append((z, 'попер', arcsec_of_ddmmss(b['trans'][0]),
                    -y_g / D * ARCSEC, 2))
    for r in a2.values():
        if r.get('h_zr') and r['tg100']:
            z = min(zones, key=lambda zz: abs(
                100.0 * (na * zz) / math.sqrt(1 - (na * zz) ** 2)
                - r['h_zr']))
            row = [rr for rr in fan if rr['zone'] == z]
            if row and row[0]['ok']:
                eqs.append((z, 'Tg', r['tg100'], row[0]['y_pupil'], 1))
    return eqs, sp_prime


def resid(name, q0, q1, verbose=True):
    eqs, sp = equations(name)
    worst = {}
    for z, kind, bank, port, power in eqs:
        lam = 1.0 - (q0 + q1 * z * z) * z * z
        pred = port * lam ** power
        d = abs(pred - bank) / abs(bank)
        key = (kind, z)
        worst[key] = d
        if verbose:
            print('  %s z%.3f: банк=%12.5f предикт=%12.5f d=%.2e'
                  % (kind, z, bank, pred, d))
    return worst


def fit(name):
    """Минимакс-скан (q0,q1)."""
    eqs, sp = equations(name)
    best = None
    q0 = 0.03
    while q0 < 0.05:
        q1 = 0.0
        while q1 < 0.005:
            mx = 0.0
            for z, kind, bank, port, power in eqs:
                lam = 1.0 - (q0 + q1 * z * z) * z * z
                mx = max(mx, abs(abs(port) * abs(lam) ** power
                                 - abs(bank)) / abs(bank))
            if best is None or mx < best[0]:
                best = (mx, q0, q1)
            q1 += 0.00005
        q0 += 0.0002
    print('== %s: минимакс q0=%.5f q1=%.5f max|d|=%.2e'
          % (name, best[1], best[2], best[0]))
    resid(name, best[1], best[2])
    return best


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        fit(nm)
    # US00KI02: sP' и деградация pupil-vergence
    opj, system, prn = load('US00KI02')
    wl = opj['wls'][0]
    sp = paraxial_of(system, wl)['sP_prime']
    print('\nUS00KI02 sP\'=%.5f (прод-правило дптр: 1000/L−1000/L_p сейчас '
          'GREEN 0.0; pupil-rule совпадает при sP\'→0 или |L|>>|sP\'|)' % sp)
