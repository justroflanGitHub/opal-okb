# -*- coding: utf-8 -*-
"""TASK_RESID R1: численная реконструкция марша Коддингтона OPAL для мнимого
изображения (OPTICS#1). Дизасм-модель (REVERSE_TRACE §7/§8 + OPALDIS §1):

- марш = дифференциальный след вдоль ЗОННОГО луча (B1 = (u_m,u_s) — наклоны,
  [3C98] = Π v_s, v = n^k); замыкание per-surface W2 += y_s²·T_s·A_s/2,
  A_s = mixed = [3C98]/(u_m·u_s²), T = тензор [3D80];
- итог W = ΔOPL(→плоскость z_last) + Σ_s y_s²·T_s·A_s/2.

Сверка с банком OPTICS#1 (4 зоны × 3 λ).
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import (parse_golden_opj, opj_to_system,
                                    _n_media)
from ray_tracing import Ray, trace_ray_through_system

OPJ = r'C:\GOLDEN_DOS\OPTICS#1.OPJ'
BANK = {
    1.0:   [-316.0417, -326.6506, -310.3036],
    0.866: [-235.8764, -243.7305, -231.6246],
    0.707: [-156.5002, -161.6708, -153.6989],
    0.5:   [-77.8839, -80.4379, -76.4992],
}
ZONES = [1.0, 0.866, 0.707, 0.5]
NA = 0.125


def fan_ray(z_obj, z0, dzone):
    su = NA * (1.0 + dzone)
    tu = su / math.sqrt(1.0 - su * su)
    return Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
               math.sqrt(1.0 - su * su))


def fan_states(system, wl, z_obj, zone, dzone, z0, z_last):
    """Луч зона+dzone: списки y_s (сферы) и slope_s (после s), OPL к z_last."""
    su = NA * (zone + dzone)
    su = min(max(su, -0.999), 0.999)
    tu = su / math.sqrt(1.0 - su * su)
    ray = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
              math.sqrt(1.0 - su * su))
    res = trace_ray_through_system(system, ray, wl)
    ys = [p[1] for p in res.path]
    zs = [p[2] for p in res.path]
    slopes = [None] + [(ys[k + 1] - ys[k]) / (zs[k + 1] - zs[k])
                       for k in range(len(ys) - 1)]
    # OPL: + доводка по воздуху до плоскости z_last (финальный сегмент)
    yL, zL = ys[-1], zs[-1]
    sl = slopes[-1]
    opl = res.opl
    if abs(sl) > 1e-15:
        opl += (z_last - zL) * math.sqrt(1.0 + sl * sl)
    if dzone == 0.0:                      # сагиттная поправка старта
        r0 = z_obj - ray.z
        opl -= math.sqrt(r0 * r0 + ray.y * ray.y) - r0
    return ys, slopes, opl


def chief_opl(system, wl, z0, z_last):
    res = trace_ray_through_system(
        system, Ray(0.0, 0.0, z0, 0.0, 0.0, 1.0), wl)
    zs = [p[2] for p in res.path]
    return res.opl + (z_last - zs[-1])


def probe(pi_exp=1, u_form='ms2', t_form='u', last=False, dz=1e-3,
          verbose=False):
    opj = parse_golden_opj(OPJ)
    system = opj_to_system(opj)
    z_obj = opj['object_pos']
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    z0 = -(abs(z_obj) + 100.0)
    out = {}
    for iwl, wl in enumerate(opj['wls']):
        media = _n_media(system, wl)
        opl_c = chief_opl(system, wl, z0, z_last)
        for zone in ZONES:
            ys0, sl0, opl0 = fan_states(system, wl, z_obj, zone, 0.0,
                                        z0, z_last)
            ysp, slp, _ = fan_states(system, wl, z_obj, zone, +dz, z0, z_last)
            ysm, slm, _ = fan_states(system, wl, z_obj, zone, -dz, z0, z_last)
            nrec = len(ys0)
            hi = min(nrec - 1, len(media) - 1) if last else \
                min(nrec - 2, len(media) - 1)
            closure = 0.0
            pi = 1.0
            for k in range(1, hi + 1):       # поверхности 1..ns(-1)
                u_m = (slp[k] - slm[k]) / (2 * dz * NA)
                u_s = u_m
                ysp_k = ysp[k] if k < len(ysp) else ysp[-1]
                ysm_k = ysm[k] if k < len(ysm) else ysm[-1]
                pi *= media[k] ** pi_exp
                if u_form == 'ms2':
                    A = pi / (u_m * u_s * u_s)
                elif u_form == 'm3':
                    A = pi / (u_m ** 3)
                T = {'1': 1.0, 'u': u_m}[t_form]
                closure += T * A * ys0[k] ** 2 / 2.0
            W = (opl0 - opl_c + closure) / (wl * 1e-3)
            out[(iwl, zone)] = (W, (opl0 - opl_c) / (wl * 1e-3), closure)
            if verbose:
                print('  λ%d з%.3f: ΔOPL %+.1fλ clos %+.2fмм → W %+.1f '
                      '(банк %+.1f)' % (
                          iwl, zone, out[(iwl, zone)][1], closure, W,
                          BANK[zone][iwl]))
    return out


def score(out):
    rel = [abs(out[k][0] - BANK[k[1]][k[0]]) / abs(BANK[k[1]][k[0]])
           for k in out]
    return max(rel), sum(rel) / len(rel)


if __name__ == '__main__':
    opj = parse_golden_opj(OPJ)
    system = opj_to_system(opj)
    z0 = -(abs(opj['object_pos']) + 100.0)
    ys, sl, opl = fan_states(system, opj['wls'][0], opj['object_pos'],
                             1.0, 0.0, z0,
                             sum(s.thickness for s in system.surfaces[:-1]))
    print('path len', len(ys), 'y:', ['%.4f' % v for v in ys])
    print('slopes:', ['%.6f' % v for v in sl[1:]])
    print('OPL', opl)
    for pi in (0, 1):
        for uf in ('ms2', 'm3'):
            for tf in ('1', 'u'):
                out = probe(pi_exp=pi, u_form=uf, t_form=tf)
                mx, av = score(out)
                print('Πn^%d u=%s T=%s: max %.3f avg %.4f' % (
                    pi, uf, tf, mx, av))
