# -*- coding: utf-8 -*-
"""Численный зонд марша W₂ (TASK_MARCH, REVERSE_OPALDIS §MARCH).

Дизасм-факты (0x93f3/0x9435, ff9:19):
    W₂ = (W₂ + [3c20])·qword[head],  [3c20] = геом. длина сегмента луча,
    head = первый qword структуры 4d20/4c4a (пишется в ff9:19).
Кандидаты head → кандидатные суммы по сегментам луча:
    A: head = n_new      → W_A = Σ L_i·Π_{j>i} n_j
    B: head = n_old      → W_B = Σ L_i·Π_{j≥i} n_j
    C: head = n_new/n_old→ W_C = Σ L_i/n_i   (редуцированная)
    opl:  W = Σ n_i·L_i  (порт, текущий GREEN-эталон для 6 систем)
Печать (b5aa/Э19/b8e4): wave = (W₂_final − W₂_ref) − S_i·sin(u_i),
S_i = прод-значение зоны (банк), u_i — угол выхода.

Зонд: для каждой волновой строки банка печатает банк vs кандидаты
(разости зональный−главный, в λ), ищем совпадение ≤1e-2.
Запуск: py -X utf8 analysis/_tools/_march_probe.py [имена систем]
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.golden_verify import (  # noqa: E402
    parse_golden_prn, parse_golden_opj, opj_to_system, paraxial_of,
    _n_media, _GOLDEN_DOS,
)
from analysis.aberrations import _compute_ray_start  # noqa: E402
from optics_utils import make_field_ray  # noqa: E402
from ray_tracing import Ray, trace_ray_through_system  # noqa: E402
from domain.calculations import paraxial_trace  # noqa: E402

_BANK_DIR = os.path.join(os.path.dirname(__file__), '..', 'reverse_data',
                         'golden', 'bank')


def _seg_data(system, res, wl):
    """[(L_i, n_i)] по сегментам луча (start→...→последняя поверхность)."""
    media = _n_media(system, wl)
    out = []
    for i in range(len(res.path) - 1):
        p0, p1 = res.path[i], res.path[i + 1]
        L = math.dist(p0, p1)
        out.append((L, media[i]))
    return out


def _cands(segs):
    """Кандидатные суммы марша по сегментам [(L_i, n_i)]."""
    n = [m for _, m in segs]
    L = [l for l, _ in segs]
    k = len(segs)
    w_a = w_b = w_c = w_opl = 0.0
    for i in range(k):
        wa = 1.0
        for j in range(i + 1, k + 1):        # Π_{j>i} n_j (head=n_new)
            wa *= n[j] if j <= k else 1.0
        wb = n[i]
        for j in range(i + 1, k + 1):        # Π_{j≥i} n_j (head=n_old)
            wb *= n[j] if j <= k else 1.0
        w_a += L[i] * wa
        w_b += L[i] * wb
        w_c += L[i] / n[i]
        w_opl += L[i] * n[i]
    return {'A': w_a, 'B': w_b, 'C': w_c, 'opl': w_opl}


def _exit_angle(res):
    p0, p1 = res.path[-2], res.path[-1]
    dz = p1[2] - p0[2]
    t = (p1[1] - p0[1]) / dz if abs(dz) > 1e-12 else 0.0
    s = t / math.sqrt(1.0 + t * t)
    return s


def probe_system(name, bank_dir=_BANK_DIR, opj_dir=_GOLDEN_DOS):
    prn = parse_golden_prn(os.path.join(bank_dir, name + '.PRN'))
    opj = parse_golden_opj(os.path.join(opj_dir, name + '.OPJ'))
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    near = (opj['obj_type'] == 1)
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    hzr_vals = [r['h_zr'] for r in prn['axial2'].get('rows', {}).values()
                if r.get('h_zr') is not None]
    ax_semi = max(hzr_vals) if hzr_vals else opj['aperture_semi']

    # ── главный и зональные лучи ──
    rays = {}                                # zone -> (res_zone, res_chief, S)
    if not near:
        parax = paraxial_trace(system, wl=wl)
        z_start, z_pupil = _compute_ray_start(system, parax)
        chief = trace_ray_through_system(
            system, make_field_ray(system, 0.0, 0.0, 0.0, z_start, z_pupil),
            wl)
        for zone, et in sorted(prn['axial2'].get('rows', {}).items()):
            if not et.get('wave') or et['wave'][0] is None:
                continue
            res = trace_ray_through_system(
                system,
                make_field_ray(system, 0.0, zone * ax_semi, 0.0,
                               z_start, z_pupil), wl)
            a1 = prn['axial1'].get('rows', {}).get(zone, {})
            S = a1.get('long')[0] if a1.get('long') else None
            if not near and a1.get('long_dptr') is not None:
                S = None                     # дптр-прод — не мм
            rays[zone] = (res, chief, S)
    else:
        z_obj = opj['object_pos']
        na = ax_row_Ax(prn, opj)
        if z_obj < 0.0:
            chief = trace_ray_through_system(
                system, Ray(0.0, 0.0, z_obj, 0.0, 0.0, 1.0), wl)
        else:
            z0 = -(abs(z_obj) + 100.0)
            chief = trace_ray_through_system(
                system, Ray(0.0, 0.0, z0, 0.0, 0.0, 1.0), wl)
        for zone, et in sorted(prn['axial2'].get('rows', {}).items()):
            if not et.get('wave') or et['wave'][0] is None:
                continue
            su = na * zone
            if z_obj < 0.0:
                ray = Ray(0.0, 0.0, z_obj, 0.0, su,
                          math.sqrt(1.0 - su * su))
            else:
                tu = su / math.sqrt(1.0 - su * su)
                z0 = -(abs(z_obj) + 100.0)
                ray = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                          math.sqrt(1.0 - su * su))
            res = trace_ray_through_system(system, ray, wl)
            a1 = prn['axial1'].get('rows', {}).get(zone, {})
            S = a1.get('long')[0] if a1.get('long') else None
            rays[zone] = (res, chief, S)

    out = []
    lam_um = wl * 1e-3
    cz_all = None
    for zone, (res, chief, S) in rays.items():
        bank = prn['axial2']['rows'][zone]['wave'][0]
        if not (res.success and chief.success
                and len(res.path) >= 2 and len(chief.path) >= 2):
            out.append((zone, bank, None, 'трейс упал/TIR'))
            continue
        cz = _cands(_seg_data(system, chief, wl))
        cz_all = cz
        c = _cands(_seg_data(system, res, wl))
        sinu = _exit_angle(res)
        Ssin = (S * sinu / lam_um) if S is not None else None
        row = {'zone': zone, 'bank': bank, 'S': S, 'Ssin': Ssin}
        for key in ('A', 'B', 'C', 'opl'):
            d = (c[key] - cz[key]) / lam_um
            row[key] = d
            row[key + '+Ssin'] = d - Ssin if Ssin is not None else None
        out.append(row)
    return out, cz_all, system, wl


def ax_row_Ax(prn, opj):
    for (wl_str, n_zone), row in prn['gabarit'].items():
        if n_zone == 0:
            return row.get('Ax') or opj['aperture_semi']
    return opj['aperture_semi']


def main():
    names = sys.argv[1:] or ['121', 'OKULAR', 'OBEKTIV', 'S_KOND1',
                             'KURSOVIK', 'OPTICS#1']
    for name in names:
        try:
            rows, cz, system, wl = probe_system(name)
        except Exception as e:               # noqa: BLE001
            print(f'== {name}: FAIL {e!r}')
            continue
        print(f'== {name}  λ={wl}  поверхностей={len(system.surfaces)}')
        hdr = ('zone', 'bank', 'A', 'B', 'C', 'opl',
               'opl+Ssin', 'A+Ssin', 'B+Ssin', 'Ssin')
        print('  ' + '  '.join(f'{h:>10}' for h in hdr))
        for r in rows:
            if isinstance(r, tuple):
                print(f'  {r[0]}: {r[3]}')
                continue
            def f(v):
                return f'{v:10.3f}' if isinstance(v, float) else f'{"—":>10}'
            print('  ' + '  '.join([
                f"{r['zone']:<10.3f}", f(r['bank']).strip(),
                f(r['A']).strip(), f(r['B']).strip(), f(r['C']).strip(),
                f(r['opl']).strip(), f(r['opl+Ssin']).strip(),
                f(r['A+Ssin']).strip(), f(r['B+Ssin']).strip(),
                f(r['Ssin']).strip()]))
            for key in ('A', 'B', 'C', 'opl'):
                d = r[key] - r['bank']
                d2 = ((r[key + '+Ssin'] - r['bank'])
                      if r.get(key + '+Ssin') is not None else None)
                print(f'      Δ{key}: {d:+9.4f}'
                      + (f'   Δ{key}+Ssin: {d2:+9.4f}'
                         if d2 is not None else ''))


if __name__ == '__main__':
    main()
