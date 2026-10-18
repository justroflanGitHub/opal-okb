# -*- coding: utf-8 -*-
"""Глобальная регрессия D = bank − port по лучевым величинам зон.

По всем системам/зонам: D, z, W(порт), y_last, sinU', прод (мм|дптр),
попер, Н ЗР. Таблица для анализа вручную.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.golden_verify import (  # noqa: E402
    compare_system, parse_golden_prn, parse_golden_opj, opj_to_system,
    _n_media,
)
from analysis.aberrations import _compute_ray_start  # noqa: E402
from optics_utils import make_field_ray  # noqa: E402
from ray_tracing import Ray, trace_ray_through_system  # noqa: E402
from domain.calculations import paraxial_trace  # noqa: E402

_BANK_DIR = os.path.join(os.path.dirname(__file__), '..', 'reverse_data',
                         'golden', 'bank')


def probe_rays(name):
    """[(зона, bank, port, y_last, sinU, прод, попер, hzr)] волновых строк."""
    res = compare_system(name)
    prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
    opj = parse_golden_opj(os.path.join(r'C:\GOLDEN_DOS', name + '.OPJ'))
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    near = (opj['obj_type'] == 1)
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    hzr_vals = [r['h_zr'] for r in prn['axial2'].get('rows', {}).values()
                if r.get('h_zr') is not None]
    ax = max(hzr_vals) if hzr_vals else opj['aperture_semi']
    na = 0.0
    for (ws, nz), row in prn['gabarit'].items():
        if nz == 0 and row.get('Ax'):
            na = row['Ax']

    def ray(zone):
        if not near:
            return trace_ray_through_system(
                system, make_field_ray(system, 0.0, zone * ax, 0.0,
                                       z_start, z_pupil), wl)
        su = na * zone
        z_obj = opj['object_pos']
        if z_obj < 0.0:
            r = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1 - su * su))
        else:
            tu = su / math.sqrt(1 - su * su)
            z0 = -(abs(z_obj) + 100.0)
            r = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                    math.sqrt(1 - su * su))
        return trace_ray_through_system(system, r, wl)

    if not near:
        parax = paraxial_trace(system, wl=wl)
        z_start, z_pupil = _compute_ray_start(system, parax)

    out = []
    # карта зона → порт из строк сравнения (волновые)
    port_of = {}
    for r in res['rows']:
        if r[1] == 'волновые' and r[4] is not None:
            port_of[round(r[2], 3)] = r[4]
    for tg, et in prn['axial2'].get('rows', {}).items():
        if not et.get('wave') or et['wave'][0] is None:
            continue
        hzz = et.get('h_zr')
        if hzz is None or not ax:
            continue
        zone = hzz / ax if not near else hzz / (100.0 * na) * na / na
        # ближний: зона = sin(u)/NA; hzr = 100·tg u → зона ≈ (hzr/100)/NA
        zone = hzz / ax if not near else (hzz / 100.0) / na
        key = min(port_of, key=lambda k: abs(k - zone)) if port_of else None
        if key is None or abs(key - zone) > 0.06:
            continue
        bank = et['wave'][0]
        port = port_of[key]
        rr = ray(zone)
        if not rr.success or len(rr.path) < 2:
            continue
        pts = [p for p in rr.path if p[2] <= z_last + 1e-9]
        y_last = pts[-1][1]
        p0, p1 = rr.path[-3], rr.path[-2]
        dz = p1[2] - p0[2]
        t = (p1[1] - p0[1]) / dz if abs(dz) > 1e-12 else 0.0
        sinU = t / math.sqrt(1 + t * t)
        a1 = prn['axial1'].get('rows', {}).get(round(zone, 3), {})
        prod = a1.get('long', [None])[0]
        trans = a1.get('trans', [None])[0]
        out.append({'zone': zone, 'bank': bank, 'port': port,
                    'y_last': y_last, 'sinU': sinU, 'prod': prod,
                    'trans': trans, 'hzr': hzz})
    return out


def main():
    names = sys.argv[1:] or ['121', 'OKULAR', 'OBEKTIV', 'S_KOND1',
                             'KURSOVIK', 'OPTICS#1']
    hdr = ('sys', 'zone', 'D', 'W', 'D/W', 'y2', 'sinU', 'prod',
           'D/(W·z2)', 'D·z^-4')
    print('  ' + ' '.join(f'{h:>10}' for h in hdr))
    for name in names:
        try:
            rays = probe_rays(name)
        except Exception as e:               # noqa: BLE001
            print(f'{name}: FAIL {e!r}')
            continue
        for r in rays:
            D = r['bank'] - r['port']
            z, W = r['zone'], r['port']
            def f(v, fmt='10.4f'):
                return f'{v:>{fmt}}' if v is not None else f'{"—":>10}'
            print('  ' + ' '.join([
                f'{name[:8]:>10}', f'{z:>10.3f}', f(D), f'{W:10.2f}',
                f'{D / W:10.2e}' if W else f'{"—":>10}',
                f'{r["y_last"] ** 2:10.2f}', f'{r["sinU"]:10.5f}',
                f(r['prod'], '10.3f'),
                f'{D / (W * z * z):10.2e}' if W * z * z else f'{"—":>10}',
                f'{D / z ** 4:10.3f}' if z else f'{"—":>10}',
            ]))


if __name__ == '__main__':
    main()
