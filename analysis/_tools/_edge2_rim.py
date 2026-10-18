# -*- coding: utf-8 -*-
"""TASK_EDGE2: откуда λ — углы луча по поверхностям vs 1−λ(z).

λ(z) из Tg'-печати; кандидаты: на КАЖДОЙ поверхности i — угол сегмента
после преломления u_i (atan), sin_i, (1−cos u_i), u_i²/2, и те же с
показателем среды. Плюс углы запуска/выхода.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import (parse_golden_opj, parse_golden_prn,
                                    opj_to_system, paraxial_of,
                                    near_object_axial_fan, _n_media,
                                    _BANK_DIR)
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
    sp_prime = paraxial_of(system, wl)['sP_prime']
    fan = near_object_axial_fan(system, wl, [1.0, 0.866, 0.707, 0.5],
                                na, z_obj)
    L_p = fan[0]['L_p']
    # среды после каждой поверхности
    media = _n_media(system, wl)
    print('== %s: среды %s' % (name, ['%.4f' % m for m in media]))

    a1 = prn['axial1']['rows']
    a2 = prn['axial2']['rows']
    zones = sorted([z for z in a1 if z != 0.0], reverse=True)
    tg = {}
    for r in a2.values():
        if r.get('h_zr') and r['tg100']:
            z = min(zones, key=lambda zz: abs(
                100.0 * (na * zz) / math.sqrt(1 - (na * zz) ** 2)
                - r['h_zr']))
            tg[z] = r['tg100']

    def trace(su):
        ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1.0 - su * su))
        return trace_ray_through_system(system, ray, wl)

    # таблица: 1−λ по зонам + кандидаты по поверхностям
    print('зона | 1−λ(Tg\') | углы по сегментам: u_i, sin_i, 1−cos_i '
          '(после пов-ти i, среда n_i)')
    cache = {}
    for row in fan:
        z = row['zone']
        if not (row['ok'] and z in tg):
            continue
        lam = tg[z] / row['y_pupil']
        res = trace(na * z)
        cache[z] = (lam, res)
        segs = []
        for i in range(1, len(res.path) - 1):
            dz = res.path[i + 1][2] - res.path[i][2]
            sl = (res.path[i + 1][1] - res.path[i][1]) / dz
            u = math.atan(sl)
            sin_u = sl / math.sqrt(1 + sl * sl)
            segs.append('s%d[n%.2f] u=%.4f sin=%.4f 1mc=%.5f'
                        % (i, media[i] if i < len(media) else -1,
                           u, sin_u, 1.0 - math.cos(u)))
        print('%.3f| %.5f | launch u=%.4f 1mc=%.5f | %s'
              % (z, 1.0 - lam, math.asin(na * z),
                 1.0 - math.cos(math.asin(na * z)), ' | '.join(segs)))

    # сетка кандидатов: ищем (i, форма, множитель m) с 1−λ ≈ m·форма_i(z)
    # по всем зонам — минимум разброса отношения
    print('\nскан множителя: 1−λ / форма_i (стабильность по зонам):')
    forms = [('u2/2', lambda u, s: u * u / 2),
             ('sin2/2', lambda u, s: s * s / 2),
             ('1mc', lambda u, s: 1.0 - math.cos(u)),
             ('sin2', lambda u, s: s * s),
             ('u2', lambda u, s: u * u)]
    nsurf = len(system.surfaces)
    best = []
    for z in zones:
        if z not in cache:
            continue
        lam, res = cache[z]
        for i in range(1, len(res.path) - 1):
            dz = res.path[i + 1][2] - res.path[i][2]
            sl = (res.path[i + 1][1] - res.path[i][1]) / dz
            u, s = math.atan(sl), sl / math.sqrt(1 + sl * sl)
            ni = media[i] if i < len(media) else 1.0
            nb = media[i - 1] if i >= 1 else 1.0
            for mult_name, mult in (('', 1.0), ('n', ni), ('n2', ni * ni),
                                    ('/n', 1.0 / ni), ('1.5', 1.5),
                                    ('n_b', nb), ('n_b2', nb * nb),
                                    ('n_b-n', nb - ni), ('1/n_b', 1.0 / nb)):
                for fname, f in forms:
                    den = mult * f(u, s)
                    if abs(den) > 1e-12:
                        best.append((i, mult_name + fname,
                                     (1.0 - lam) / den, z))
    # группировка
    from collections import defaultdict
    grp = defaultdict(list)
    for i, tag, val, z in best:
        if val == val and abs(val) < 20:
            grp[(i, tag)].append((z, val))
    for (i, tag), vals in sorted(grp.items()):
        vs = [v for _, v in vals]
        if len(vs) >= 3:
            mean = sum(vs) / len(vs)
            spread = max(abs(v - mean) for v in vs) / abs(mean)
            if spread < 0.05:
                print('  s%d %-8s: mean=%8.4f spread=%5.1f%% (n=%d)'
                      % (i, tag, mean, 100 * spread, len(vs)))


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        main(nm)
