# -*- coding: utf-8 -*-
"""TASK_FINAL: численные пробы оставшихся конвенций.

A. OKULAR (afocal, близкий предмет): волна vs плоскость замыкания
   (z_last, z_last+sP', z_last−|sP'|, зрачок марша) — ищем δz-константу.
B. S_KOND1 (близкий предмет, реальное изображение): подразумеваемая
   κ(z) квадратичного замыкания на z_last — профиль по зонам.
C. KURSOVIK: λ-профиль прод(дптр)/попер(arcsec) по зонам (печать марша).
D. OPTICS#1: E2-λ по 3 λ-колонкам (прод мм / попер мм) — общность q.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.golden_verify import (parse_golden_opj, opj_to_system,
                                    parse_golden_prn, paraxial_of,
                                    near_object_axial_fan, _BANK_DIR)
from ray_tracing import Ray, trace_ray_through_system
from analysis.aberrations import (_air_exit_direction,
                                  _opl_to_reference_sphere,
                                  opl_to_last_vertex)
from domain.calculations import paraxial_trace

GOLDEN = r'C:\GOLDEN_DOS'


def load(name):
    opj = parse_golden_opj(os.path.join(GOLDEN, name + '.OPJ'))
    system = opj_to_system(opj)
    prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
    return opj, system, prn


ZONES = (1.0, 0.8660254, 0.7071068, 0.5)
ZONELAB = {1.0: '1.0', 0.8660254: '0.866', 0.7071068: '0.707', 0.5: '0.5'}

# ── A. OKULAR: плоскость замыкания волны ────────────────────────────────
print('═══ A. OKULAR — волна vs плоскость замыкания')
opj, system, prn = load('OKULAR')
wls = opj['wls']
BANK_W = {-106.0768: 1.0, -71.3209: 0.8660254, -33.8234: 0.7071068,
          -8.5228: 0.5}
for iwl, wl in enumerate(wls):
    parax = paraxial_of(system, wl)
    sP = parax['sP_prime']
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    z_obj = opj['object_pos']
    na = 0.351
    # волны по зонам с замыканием на плоскость z_close
    z_pup = z_last + sP
    chief = trace_ray_through_system(
        system, Ray(0.0, 0.0, z_obj, 0.0, 0.0, 1.0), wl)

    def opl_at_plane(res, z_close):
        d = _air_exit_direction(system, res, wl)
        return res.opl + (z_close - res.path[-1][2]) / d[2]

    opl_chief = opl_at_plane(chief, z_pup)
    for zone in ZONES:
        su = na * zone
        ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1 - su * su))
        res = trace_ray_through_system(system, ray, wl)
        if not res.success:
            continue
        w_pup = (opl_at_plane(res, z_pup) - opl_chief) / (wl * 1e-3)
        slope = None
        prev, last = res.path[-2], res.path[-1]
        dz = last[2] - prev[2]
        slope = (last[1] - prev[1]) / dz
        w_bank = [k for k, z in BANK_W.items() if abs(z - zone) < 1e-9][0]
        # какая плоскость даёт банк: δz·(cos u'−cos u'_chief)=ΔOPL
        d_opl = (w_bank - w_pup) * wl * 1e-3
        # cos(u') - cos(u'_c)= sqrt(1/(1+slope²)) - 1 (chief осевой)
        du = 1.0 / math.sqrt(1 + slope * slope) - 1.0
        dz_implied = d_opl / du if abs(du) > 1e-12 else None
        print(f'  λ{iwl} з.{ZONELAB[zone]}: W_порт={w_pup:+9.3f} '
              f'(плоск. зрачка) банк={w_bank:+9.3f} '
              f'δz={dz_implied:+.4f} slope={slope:+.4f}')

# ── B. S_KOND1: κ(z) квадратичного замыкания ────────────────────────────
print('\n═══ B. S_KOND1 — подразумеваемая κ(z) на z_last')
opj, system, prn = load('S_KOND1')
BANK_W = {1.0: -137.7, 0.8660254: -74.052}
wl = opj['wls'][0]
parax = paraxial_of(system, wl)
z_last = sum(s.thickness for s in system.surfaces[:-1])
z_obj = opj['object_pos']
na = 0.351 if 'S_KOND1' != 'S_KOND1' else None
# NA из габарита
ax_row = None
for r in prn.get('gabarit', {}).get('rows', []):
    if r.get('N') == 0:
        ax_row = r
        break
na = ax_row['Ax'] if ax_row else 0.3
print(f'  NA={na}')
chief = trace_ray_through_system(
    system, Ray(0.0, 0.0, z_obj, 0.0, 0.0, 1.0), wl)
opl_chief_zl = opl_to_last_vertex(system, chief, wl)
for zone, w_bank in sorted(BANK_W.items(), reverse=True):
    su = na * zone
    ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1 - su * su))
    res = trace_ray_through_system(system, ray, wl)
    if not res.success:
        print(f'  з.{ZONELAB[zone]}: FAIL')
        continue
    y = res.path[-1][1]
    opl_zl = opl_to_last_vertex(system, res, wl)
    kap = 2.0 * (w_bank * wl * 1e-3 - (opl_zl - opl_chief_zl)) / (y * y)
    print(f'  з.{ZONELAB[zone]}: y={y:+8.4f} κ_z={kap:+.6f} '
          f'(зона²={zone * zone:.3f})')

# ── C. KURSOVIK: λ-профиль прод/попер ──────────────────────────────────
print('\n═══ C. KURSOVIK — λ(z) прод(дптр)/попер(arcsec)')
opj, system, prn = load('KURSOVIK')
wl = opj['wls'][0]
parax = paraxial_of(system, wl)
z_last = sum(s.thickness for s in system.surfaces[:-1])
ax = 18.4911
# порт-формулы дальней ветки (golden_verify §4.1)
from analysis.golden_verify import axial_fan, _paraxial_ray
from analysis.units import mm_to_dioptres
fan = axial_fan(system, wl, list(ZONES), ax)
y_p, u_p = _paraxial_ray(system, wl, ax, 0.0, 0.0)
L_parax = -y_p / u_p
sp = parax['sP_prime']
BK_LONG = {1.0: -16.14054, 0.8660254: -9.44541, 0.7071068: -4.76259,
           0.5: -1.72336}
BK_TRANS = {1.0: -3.203017, 0.8660254: -1.420964, 0.7071068: -0.421818,
            0.5: -0.105303}
for ray in fan:
    zone = ray['zone']
    if not ray['ok']:
        continue
    lp_z = ray['L'] - sp
    lp_p = L_parax - sp
    long_d = mm_to_dioptres(lp_z) - mm_to_dioptres(lp_p)
    y_g = ray['y_exit'] + ray['slope'] * L_parax
    trans_a = -y_g / (L_parax - sp) * 206264.80624709636
    lam_long = BK_LONG[zone] / long_d
    from analysis.golden_verify import arcsec_of_ddmmss
    lam_tr = BK_TRANS[zone] / arcsec_of_ddmmss(trans_a) * 1.0 \
        if False else None
    # попер в секундах: банк DD.MMSSss → сек
    bk_tr_sec = arcsec_of_ddmmss(BK_TRANS[zone])
    lam_tr = bk_tr_sec / trans_a
    print(f'  з.{ZONELAB[zone]}: прод порт={long_d:+9.4f} банк='
          f'{BK_LONG[zone]:+9.4f} λ₁={lam_long:.6f} | попер порт='
          f'{trans_a:+10.2f}" банк={bk_tr_sec:+10.2f}" λ_t={lam_tr:.6f}')

# ── D. OPTICS#1: E2-λ по λ-колонкам ────────────────────────────────────
print('\n═══ D. OPTICS#1 — λ(z) прод(мм)/попер(мм), 3 колонки')
opj, system, prn = load('OPTICS#1')
z_obj = opj['object_pos']
NA_BY_WL = {0: 0.125, 1: 0.12587, 2: 0.12455}
BK = {  # zone: (прод[3λ], попер[3λ])
    0.5: ([-17.89156, -18.26299, -17.68862], [1.329926, 1.366735, 1.30988]),
    0.7071068: ([-18.04523, -18.42691, -17.8371],
                [1.899372, 1.952696, 1.87038]),
    0.8660254: ([-18.20322, -18.59557, -17.98965],
                [2.349582, 2.416509, 2.31325]),
    1.0: ([-18.36569, -18.76918, -18.14647], [2.74072, 2.819948, 2.69778]),
}
for iwl, wl in enumerate(opj['wls']):
    na = NA_BY_WL[iwl]
    print(f'  λ{iwl}={wl:.4f} NA={na}:')
    for zone in ZONES:
        su = na * zone
        ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1 - su * su))
        res = trace_ray_through_system(system, ray, wl)
        if not res.success:
            continue
        prev, last = res.path[-2], res.path[-1]
        slope = (last[1] - prev[1]) / (last[2] - prev[2])
        L = -last[1] / slope
        lam_long = BK[zone][0][iwl] / L
        lam_tr = BK[zone][1][iwl] / abs(last[1])
        q_long = 1 - lam_long
        q_tr = 1 - lam_tr
        print(f'    з.{ZONELAB[zone]}: прод λ={lam_long:.6f} '
              f'(q/z²={q_long / (zone * zone):.2e}) | попер λ={lam_tr:.6f} '
              f'(q/z²={q_tr / (zone * zone):.2e})')
