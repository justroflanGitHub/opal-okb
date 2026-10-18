# -*- coding: utf-8 -*-
"""TASK_EDGE2: батарея угловых кандидатов поперечной печати.

α_cur = −(δy + δu·L_p)/(L_p − sP′) (текущее правило, хорда из зрачка).
Кандидаты: чисто угловые (δu vs параксиальный наклон), смешанные
(разные числители/знаменатели), с параксиальным вычитанием по зонам.
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
    if z_obj < 0.0:
        y0_par, u0_par, z0_par = 0.0, 0.05, z_obj
    else:
        z0_par = -(abs(z_obj) + 100.0)
        u0_par = -0.05
        y0_par = (z_obj - z0_par) * (-u0_par)
    fan = near_object_axial_fan(system, wl, [1.0, 0.866, 0.707, 0.5],
                                na, z_obj)
    L_p = fan[0]['L_p']

    a1 = prn['axial1']['rows']
    a2 = prn['axial2']['rows']
    zones = sorted([z for z in a1 if z != 0.0], reverse=True)
    bank = {z: {'trans_as': arcsec_of_ddmmss(a1[z]['trans'][0])} for z in zones}
    tg100 = {}
    for r in a2.values():
        if r.get('h_zr') and r['tg100']:
            z = min(zones, key=lambda zz: abs(
                100.0 * (na * zz) / math.sqrt(1 - (na * zz) ** 2)
                - r['h_zr']))
            tg100[z] = r['tg100']

    print('== %s: L_p=%.4f sP\'=%.4f' % (name, L_p, sp_prime))
    # параксиальные наклоны выхода по зонам (2 семантики запуска)
    upar = {}
    for z in zones:
        su = na * z
        tu = su / math.sqrt(1.0 - su * su)
        for tag, u0 in (('sin', su), ('tan', tu)):
            if z_obj < 0.0:
                y0 = 0.0
            else:
                z0s = -(abs(z_obj) + 100.0)
                y0 = (z_obj - z0s) * (tu if tag == 'tan' else su)
                u0 = -u0
            y_pp, u_pp = _paraxial_ray(system, wl, y0, u0, z0_par)
            upar[(z, tag)] = u_pp
            if tag == 'sin':
                upar[(z, 'y')] = y_pp

    hdr = ('зона   банк"     cur        Δ%    | ang_sin    Δ%    | '
           'ang_tan    Δ%    | ypup/D     Δ%    | δu·Lp/D')
    print(hdr)
    for row in fan:
        z = row['zone']
        b = bank.get(z)
        if not (b and row['ok']):
            continue
        y_e, sl, L_z = row['y_exit'], row['slope'], row['L']
        y_g = y_e + sl * L_p
        D = L_p - sp_prime
        y_pup = row.get('y_pupil')
        y_par = upar[(z, 'y')]
        u_s, u_t = upar[(z, 'sin')], upar[(z, 'tan')]
        cands = [
            ('cur', -y_g / D),
            ('ang_sin', -(sl - u_s)),
            ('ang_tan', -(sl - u_t)),
            ('ypup/D', -y_pup / D),
            ('duL/D', -(sl - u_s) * L_p / D),
            ('dyD', -(y_e - y_par * 0 - 0) / D),
        ]
        out = ['%.3f %9.2f' % (z, b['trans_as'])]
        for k, v in cands:
            va = v * ARCSEC
            out.append('%9.2f %+6.2f%%' % (va,
                        100.0 * (va - b['trans_as']) / b['trans_as']))
        # где лежит банк между cur и ang?
        lo, hi = sorted([abs(cands[0][1]), abs(cands[1][1])])
        ba = abs(b['trans_as'] / ARCSEC)
        frac = (ba - lo) / (hi - lo) if hi > lo else float('nan')
        out.append('| банк между cur/ang: %.3f' % frac)
        print('  ' + '  '.join(out))


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
