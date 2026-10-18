# -*- coding: utf-8 -*-
"""TASK_RESID R1: численная реконструкция марша Коддингтона OPAL для мнимого
изображения (OPTICS#1). Дизасм-модель (REVERSE_TRACE §7/§8 + REVERSE_OPALDIS §1):

- марш = дифференциальный след вдоль ЗОННОГО луча (записи B1 = (u_m, u_s) —
  наклоны соседей, [3C98] = Π v_s, v = n^k);
- замыкание per-surface: W2 += QF(x_s,y_s)·A_s/2, QF = x2·T11 + 2xy·T12 + y2·T22
  (ось симметрии: QF = y2·T22), A_s = mixed = [3C98]/(u_m·u_s²);
- итог: W = ΔOPL(→z_last) + Σ_s QF_s·A_s/2.

Скрипт перебирает варианты (Π, якорь дифференциала, степени u) и сверяет
Σ-замыкание с банком OPTICS#1 (4 зоны × 3 λ = 12 уравнений).
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import (parse_golden_opj, opj_to_system,
                                    paraxial_of, _paraxial_ray)
from ray_tracing import Ray, trace_ray_through_system

OPJ = r'C:\GOLDEN_DOS\OPTICS#1.OPJ'
BANK = {  # zone: [wl0, wl1, wl2] волновые из TABOC2
    1.0:   [-316.0417, -326.6506, -310.3036],
    0.866: [-235.8764, -243.7305, -231.6246],
    0.707: [-156.5002, -161.6708, -153.6989],
    0.5:   [-77.8839, -80.4379, -76.4992],
}
ZONES = [1.0, 0.866, 0.707, 0.5]
NA = 0.125


def fan_ray(z_obj, zone, wl, dmer=0.0, xsag=0.0, dzone=0.0):
    """Луч веера: зона zone±dmer (мер) либо zone c поперечным сдвигом xsag
    (саг, мм на сфере старта). Возврат Ray."""
    su = NA * (zone + dzone + dmer)
    su = min(max(su, -0.999), 0.999)
    tu = su / math.sqrt(1.0 - su * su)
    z0 = -(abs(z_obj) + 100.0)
    y0 = (z_obj - z0) * tu + xsag
    return Ray(xsag and 0.0 or 0.0, y0, z0, 0.0, -su,
               math.sqrt(1.0 - su * su))


def surface_state(system, res):
    """Высоты луча на каждой поверхности (по точкам path; path[i] = точка
    на поверхности i) + терминальная. Возвращает список y на поверхностях."""
    return [p[1] for p in res.path], [p[2] for p in res.path]


def probe(variant_pi=1, variant_u='ms2', use_T=True, basis='zone',
          dzone=1e-4, verbose=False):
    opj = parse_golden_opj(OPJ)
    system = opj_to_system(opj)
    z_obj = opj['object_pos']
    nsurf = len(system.surfaces)
    out = {}
    for iwl, wl in enumerate(opj['wls']):
        # показатели сред вдоль пути (n после каждой поверхности)
        from domain.calculations import refractive_index
        ns = [1.0]
        for s in system.surfaces:
            ns.append(refractive_index(s.glass, wl, None,
                                       getattr(s, 'n_override', None)))
        chief = trace_ray_through_system(system,
                                         Ray(0, 0, -(abs(z_obj) + 100.0),
                                             0, 0, 1.0), wl)
        for zone in ZONES:
            r0 = trace_ray_through_system(
                system, fan_ray(z_obj, zone, wl), wl)
            # дифференциальные соседи: мер (зона+δ) и «саг» (мер-сосед вниз)
            rp = trace_ray_through_system(
                system, fan_ray(z_obj, zone, wl, dzone=dzone), wl)
            rm = trace_ray_through_system(
                system, fan_ray(z_obj, zone, wl, dzone=-dzone), wl)
            ys0, zs0 = surface_state(system, r0)
            ysp, zsp = surface_state(system, rp)
            ysm, zsm = surface_state(system, rm)
            # OPL до z_last (вычет сагиттного эксцесса старта)
            ray = fan_ray(z_obj, zone, wl)
            r0c = z_obj - ray.z
            opl = r0.opl - (math.sqrt(r0c * r0c + ray.y * ray.y) - r0c)
            dOPL = opl - chief.opl
            # per-surface замыкание
            nrec = min(len(ys0), len(ysp))
            closure = 0.0
            pi = 1.0
            for k in range(nrec - 1):        # поверхности 0..ns-2 (не терминал)
                u_m = (ysp[k] - ysm[k]) / (2 * dzone * NA)  # dY/dNA
                u_s = u_m                     # осевой веер: мер=саг
                pi *= ns[k + 1] / ns[0] if False else ns[k + 1] ** variant_pi
                if variant_u == 'ms2':
                    A = pi / (u_m * u_s * u_s)
                elif variant_u == 'm3':
                    A = pi / (u_m ** 3)
                T = 1.0
                if use_T:
                    T = u_m                   # «тензор» кандидат
                closure += T * A * ys0[k] ** 2 / 2.0
            W = (dOPL + closure) / (wl * 1e-3)
            out[(iwl, zone)] = W
            if verbose:
                print('  λ%d з%.3f: dOPL %+.5f closure %+.5f → W %+.2f '
                      '(банк %+.2f)' % (iwl, zone, dOPL, closure, W,
                                        BANK[zone][iwl]))
    return out


def score(out):
    rel = []
    for (iwl, zone), W in sorted(out.items()):
        b = BANK[zone][iwl]
        rel.append(abs(W - b) / abs(b))
    return max(rel), sum(rel) / len(rel)


if __name__ == '__main__':
    for pi in (0, 1):
        for vu in ('ms2', 'm3'):
            for ut in (False, True):
                out = probe(variant_pi=pi, variant_u=vu, use_T=ut)
                mx, av = score(out)
                print('Πn^%d u=%s T=%s: max %.3f avg %.3f' % (
                    pi, vu, ut, mx, av))
