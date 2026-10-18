# -*- coding: utf-8 -*-
"""TASK_FINAL: κ-фит замыкания марша (квадратика на z_last) для волновых
колонок ближнего/дальнего предмета — все 4 зоны, λ0.

Модель (R1-методология, распространённая с мнимого на любые изображения):
  W_банк·λмм = ΔOPL(зон→z_last верш.) + (κ0 + κ2·z²)·y_exit²/2
Фит (κ0, κ2) МНК по 4 зонам; критерий закрытия: max|W_предск − W_банк|/|W|
≤ 1e-3 (GREEN). Также OPTICS#1: E2-λ прод/попер мм по 3 λ-колонкам
(запуск мнимого предмета: старт слева, прицел в (0,0,z_obj)).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.golden_verify import (parse_golden_opj, opj_to_system,
                                    parse_golden_prn, paraxial_of, _BANK_DIR)
from ray_tracing import Ray, trace_ray_through_system
from analysis.aberrations import opl_to_last_vertex

GOLDEN = r'C:\GOLDEN_DOS'
ZONES = (1.0, 0.8660254, 0.7071068, 0.5)
ZL = {1.0: '1.0  ', 0.8660254: '0.866', 0.7071068: '0.707', 0.5: '0.5  '}


def load(name):
    opj = parse_golden_opj(os.path.join(GOLDEN, name + '.OPJ'))
    system = opj_to_system(opj)
    prn = parse_golden_prn(os.path.join(_BANK_DIR, name + '.PRN'))
    return opj, system, prn


def na_of(prn):
    for r in prn.get('gabarit', {}).get('rows', []):
        if r.get('N') == 0:
            return r.get('Ax')
    return None


def bank_waves(prn):
    """λ0-волны по зонам: зона = h_zr/(макс h_zr) для близких (tg-сетка)
    или из осевой1; возвращаем {zone: W}."""
    rows = {r['h_zr']: r for r in prn['axial2']['rows'].values()
            if r.get('h_zr')}
    if not rows:
        return {}
    hmax = max(rows)
    out = {}
    for h, r in sorted(rows.items()):
        out[round(h / hmax, 6)] = r['wave'][0]
    return out


def lsq2(xs, ys):
    """МНК y = a + b·x."""
    n = len(xs)
    xb = sum(xs) / n
    yb = sum(ys) / n
    b = sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) \
        / sum((x - xb) ** 2 for x in xs)
    return yb - b * xb, b


print('═══ κ-фит волн (квадратика на z_last, κ0+κ2·z²) ═══')
for name in ('S_KOND1', 'OBEKTIV', 'OKULAR', 'KURSOVIK', 'HELIOS8'):
    opj, system, prn = load(name)
    wl = opj['wls'][0]
    near = opj['obj_type'] == 1
    z_obj = opj.get('object_pos', 0.0)
    bw = bank_waves(prn)
    if not bw:
        print(f'{name}: нет волн — пропуск')
        continue
    # зональный луч
    zone_of = {}
    for z in ZONES:
        best = min(bw, key=lambda k: abs(k - z))
        zone_of[z] = best

    def ray_for(zone, na):
        if near:
            su = na * zone
            if z_obj < 0:
                return Ray(0.0, 0.0, z_obj, 0.0, su,
                           math.sqrt(1 - su * su))
            z0 = -(abs(z_obj) + 100.0)
            tu = su / math.sqrt(1 - su * su)
            return Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                       math.sqrt(1 - su * su))
        hzr = [r for r in prn['axial2']['rows'].values() if r.get('h_zr')]
        ax = max(r['h_zr'] for r in hzr)
        return Ray(0.0, zone * ax, -30.0, 0.0, 0.0, 1.0)

    na = na_of(prn) or 0.3
    if near and z_obj > 0:
        chief = trace_ray_through_system(
            system, Ray(0.0, 0.0, -(abs(z_obj) + 100.0), 0.0, 0.0, 1.0), wl)
    elif near:
        chief = trace_ray_through_system(
            system, Ray(0.0, 0.0, z_obj, 0.0, 0.0, 1.0), wl)
    else:
        chief = trace_ray_through_system(
            system, Ray(0.0, 0.0, -30.0, 0.0, 0.0, 1.0), wl)
    if not chief.success:
        print(f'{name}: chief FAIL')
        continue
    opl_c = opl_to_last_vertex(system, chief, wl)
    ks, ys, ss = [], [], []
    raw = []
    for z in ZONES:
        res = trace_ray_through_system(system, ray_for(z, na), wl)
        if not res.success:
            print(f'{name} з.{ZL[z]}: FAIL')
            continue
        y = res.path[-1][1]
        dopl = opl_to_last_vertex(system, res, wl) - opl_c
        w_bank = bw[zone_of[z]]
        kap = 2.0 * (w_bank * wl * 1e-3 - dopl) / (y * y)
        ks.append(kap)
        ys.append((y, dopl, w_bank))
        ss.append(z * z)
        raw.append((z, y, dopl, w_bank, kap))
    if len(ks) < 3:
        print(f'{name}: <3 зон — пропуск')
        continue
    k0, k2 = lsq2(ss, ks)
    print(f'\n{name} (near={near}, NA/Ax={na}): κ0={k0:+.6f} κ2={k2:+.6f}')
    worst = 0.0
    for z, y, dopl, w_bank, kap in raw:
        w_fit = (dopl + (k0 + k2 * z * z) * y * y / 2.0) / (wl * 1e-3)
        rel = abs(w_fit - w_bank) / max(abs(w_bank), 1e-9)
        worst = max(worst, rel)
        print(f'  з.{ZL[z]}: κ_z={kap:+.6f} W_фит={w_fit:+10.4f} '
              f'W_банк={w_bank:+10.4f} отн={rel:.2e}')
    print(f'  → max отн. остаток {worst:.2e} '
          f'({"ЗАКРЫВАЕТСЯ" if worst <= 1e-3 else "НЕ ЗАКРЫВАЕТСЯ"})')

# ── OPTICS#1: E2-λ по 3 λ-колонкам (прод мм/попер мм) ──────────────────
print('\n═══ OPTICS#1 — E2-λ (прод/попер мм), запуск мнимого предмета ═══')
opj, system, prn = load('OPTICS#1')
z_obj = opj['object_pos']
NA = {0: 0.125, 1: 0.12587, 2: 0.12455}
BK = {
    1.0: ([-18.36569, -18.76918, -18.14647], [2.74072, 2.819948, 2.69778]),
    0.8660254: ([-18.20322, -18.59557, -17.98965],
                [2.349582, 2.416509, 2.31325]),
    0.7071068: ([-18.04523, -18.42691, -17.8371],
                [1.899372, 1.952696, 1.87038]),
    0.5: ([-17.89156, -18.26299, -17.68862], [1.329926, 1.366735, 1.30988]),
}
for iwl, wl in enumerate(opj['wls']):
    na = NA[iwl]
    print(f'λ{iwl}={wl:.4f} NA={na}:')
    for z in ZONES:
        su = na * z
        z0 = -(abs(z_obj) + 100.0)
        tu = su / math.sqrt(1 - su * su)
        ray = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                  math.sqrt(1 - su * su))
        res = trace_ray_through_system(system, ray, wl)
        if not res.success:
            print(f'  з.{ZL[z]}: FAIL {res.error}')
            continue
        prev, last = res.path[-2], res.path[-1]
        slope = (last[1] - prev[1]) / (last[2] - prev[2])
        L = -last[1] / slope
        lam_l = BK[z][0][iwl] / L
        lam_t = BK[z][1][iwl] / abs(last[1])
        print(f'  з.{ZL[z]}: прод λ={lam_l:.6f} q/z²={(1-lam_l)/(z*z):.3e} |'
              f' попер λ={lam_t:.6f} q/z²={(1-lam_t)/(z*z):.3e}')
