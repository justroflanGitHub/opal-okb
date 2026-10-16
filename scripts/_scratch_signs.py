# -*- coding: utf-8 -*-
"""Скретч: знаки сумм Зейделя ↔ трассировка (SI↔c3, SII↔a2, SIII↔a1-b1, SV↔a0, SIxp↔-df')."""
import math

from domain.models import create_demo_system_by_name, ObjectType
from domain.calculations import paraxial_trace, refractive_index
from analysis.aberrations import _compute_ray_start, _pupil_field_ray
from optics_utils import get_effective_aperture, get_primary_wl
import ray_native


def parax_data(system, wl):
    ns = len(system.surfaces)
    n = [1.0]
    for s in system.surfaces:
        n.append(-n[-1] if s.is_reflective
                 else refractive_index(s.glass, wl, None, getattr(s, 'n_override', None)))
    y = [0.0] * (ns + 1); nu = [0.0] * (ns + 1)
    y[0], nu[0] = 1.0, 0.0
    for i, s in enumerate(system.surfaces):
        R = s.radius if s.radius != 0 else math.inf
        nu[i + 1] = nu[i] - (y[i] * (n[i + 1] - n[i]) / R if R != math.inf else 0.0)
        y[i + 1] = y[i] + nu[i + 1] * s.thickness / n[i + 1]
    yb = [0.0] * (ns + 1); nub = [0.0] * (ns + 1)
    k = max(0, min(system.stop_surface - 1, ns - 1))
    yb[k], nub[k] = 0.0, 1.0
    for i in range(k - 1, -1, -1):
        s = system.surfaces[i]
        R = s.radius if s.radius != 0 else math.inf
        yb[i] = yb[i + 1] - nub[i + 1] * s.thickness / n[i + 1]
        nub[i] = nub[i + 1] + (yb[i] * (n[i + 1] - n[i]) / R if R != math.inf else 0.0)
    for i in range(k, ns):
        s = system.surfaces[i]
        R = s.radius if s.radius != 0 else math.inf
        nub[i + 1] = nub[i] - (yb[i] * (n[i + 1] - n[i]) / R if R != math.inf else 0.0)
        yb[i + 1] = yb[i] + nub[i + 1] * s.thickness / n[i + 1]
    return n, y, nu, yb, nub


def chief_scale(system, field_y, nub0):
    if system.object_type == ObjectType.INFINITE:
        return math.tan(math.radians(field_y)) / nub0
    d = abs(system.surfaces[0].thickness) if system.surfaces else 50.0
    return (-field_y / d) / nub0


def all_sums(system, wl, a, s, wl_lo=None, wl_hi=None):
    n, y, nu, yb, nub = parax_data(system, wl)
    ns = len(system.surfaces)
    S = dict(SI=0.0, SII=0.0, SIII=0.0, SIV=0.0, SV=0.0, SIxp=0.0, SIIxp=0.0)
    # дисперсии δn на каждой стороне поверхности (λmax − λmin)
    def dn(glass, n_ov):
        if glass == '' and not n_ov:
            return 0.0
        return (refractive_index(glass, wl_hi, None, n_ov)
                - refractive_index(glass, wl_lo, None, n_ov))
    for i in range(ns):
        surf = system.surfaces[i]
        R = surf.radius
        if R == 0:
            continue
        dinv = 1.0 / n[i + 1] - 1.0 / n[i]
        h = a * y[i]
        A = a * (nu[i] + n[i] * y[i] / R)
        Ab = s * (nub[i] + n[i] * yb[i] / R)
        S['SI'] += A * A * h * dinv
        S['SII'] += Ab * A * h * dinv
        S['SIII'] += Ab * Ab * h * dinv
        S['SIV'] += (n[i + 1] - n[i]) / (R * n[i] * n[i + 1])
        a_safe = A if abs(A) > 1e-12 else 1e-12
        S['SV'] += (Ab ** 3 / a_safe) * h * dinv + 3.0 * Ab * Ab * h * dinv
        # хроматические: δ(1/n) = −δn/n²
        if surf.is_reflective:
            dn1 = dn(system.surfaces[i - 1].glass if i else '',
                     getattr(system.surfaces[i - 1], 'n_override', None) if i else None)
            dn2 = -dn1
            n1v, n2v = n[i], n[i + 1]
        else:
            n_ov1 = getattr(system.surfaces[i - 1], 'n_override', None) if i else None
            dn1 = dn(system.surfaces[i - 1].glass if i else '', n_ov1)
            dn2 = dn(surf.glass, getattr(surf, 'n_override', None))
            n1v, n2v = n[i], n[i + 1]
        dchrom = -(dn2 / n2v ** 2 - dn1 / n1v ** 2)   # −δ(1/n)
        S['SIxp'] += A * h * dchrom
        S['SIIxp'] += Ab * h * dchrom
    return S, n[-1], a * nu[-1] / n[-1]


def trace_at_focus(system, wl, field_y, rho, sagittal=False):
    ap = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    z0, zp = _compute_ray_start(system, parax)
    px, py = (rho, 0.0) if sagittal else (0.0, rho)
    ray = _pupil_field_ray(system, px * ap / 2, py * ap / 2, field_y, z0, zp)
    r = ray_native.trace_batch(system, [(ray.x, ray.y, ray.z, ray.k, ray.l, ray.m)], wl)[0]
    if not r.success or len(r.path) < 2:
        return None
    # фокус: маргинальный базис пересекает ось после последней поверхности
    n, y, nu, yb, nub = parax_data(system, wl)
    ns = len(system.surfaces)
    z_pos = [0.0]
    for surf in system.surfaces:
        z_pos.append(z_pos[-1] + surf.thickness)
    z_img = z_pos[ns]
    slope = nu[ns] / n[ns]
    z_focus = z_img - y[ns] / slope if abs(slope) > 1e-15 else z_img
    (x0, y0, z0p), (x1, y1, z1) = r.path[-2], r.path[-1]
    dzs = z1 - z0p
    t = (z_focus - z0p) / dzs if abs(dzs) > 1e-12 else 0.0
    x, yv = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    if field_y == 0.0:
        return x if sagittal else yv
    s = chief_scale(system, field_y, nub[0])
    y_par_chief = s * (yb[ns] + nub[ns] * (z_focus - z_img) / n[ns])
    return x if sagittal else yv - y_par_chief


def fit_poly(pairs, deg=3):
    import numpy as np
    A = [[rho ** k for k in range(deg + 1)] for rho, _ in pairs]
    b = [e for _, e in pairs]
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    return c


def main():
    from domain.calculations import seidel_aberrations
    for name, field in (('plano_convex', 2.0), ('achromat', 2.5), ('cook_doublet', 2.0),
                        ('telephoto', 1.5), ('meniscus', 2.0), ('petzval', 2.0)):
        sysm = create_demo_system_by_name(name)
        wl = get_primary_wl(sysm)
        a = get_effective_aperture(sysm, default=10.0) / 2.0
        n, y, nu, yb, nub = parax_data(sysm, wl)
        s = chief_scale(sysm, field, nub[0])
        wls = sorted(w.value for w in sysm.wavelengths)
        S, np_img, up = all_sums(sysm, wl, a, s, wl_lo=wls[0], wl_hi=wls[-1])
        # паритет с портом (базис y=1 → SI·a³; главный базис nub=1 → SII·s)
        port = seidel_aberrations(sysm)
        parity = (abs(port['SI'] - S['SI'] / a ** 3) < 1e-9
                  and abs(port['SII'] - S['SII'] / s) < 1e-9
                  and abs(port['SIII'] - S['SIII'] / s ** 2) < 1e-9
                  and abs(port['SV'] - S['SV'] / s ** 3) < 1e-9)
        # осевой c3: ε = c1ρ + c3ρ³ + c5ρ⁵ (3 параметра)
        rhos_a = (0.1, 0.2, 0.3, 0.4, 0.5)
        import numpy as np2
        pairs = [(rho, trace_at_focus(sysm, wl, 0.0, rho)) for rho in rhos_a]
        rows = [[1.0, rho * rho, rho ** 4] for rho, e in pairs]
        rhs = [e / rho for rho, e in pairs]
        cc, *_ = np2.linalg.lstsq(np2.array(rows), np2.array(rhs), rcond=None)
        c1, c3, c5 = (float(v) for v in cc)
        # поле: a0..a3 + саг b1
        rhos = (-0.4, -0.25, -0.12, 0.12, 0.25, 0.4)
        fan = [(rho, trace_at_focus(sysm, wl, field, rho)) for rho in rhos]
        a0, a1, a2, a3 = fit_poly(fan)
        sag = [(rho, trace_at_focus(sysm, wl, field, rho, sagittal=True)) for rho in (0.2, 0.35)]
        b1 = (sag[0][1] / sag[0][0] + sag[1][1] / sag[1][0]) / 2
        # хроматизм: δf' между λmax/λmin
        f1 = paraxial_trace(sysm, wl=wls[0])['back_focal_distance']
        f2 = paraxial_trace(sysm, wl=wls[-1])['back_focal_distance']
        df = f2 - f1
        print(f'== {name} parity={parity}: SI={S["SI"]:+.5f} c3={c3 * 1000:+.2f}мкм | SII={S["SII"]:+.5f} a2={a2 * 1000:+.2f}мкм | '
              f'SIII={S["SIII"]:+.6f} a1-b1={(a1 - b1) * 1000:+.2f}мкм | SV={S["SV"]:+.6f} a0={a0 * 1000:+.2f}мкм | '
              f'SIxp={S["SIxp"]:+.6f} δf\'={df:+.4f}мм | SIIxp={S["SIIxp"]:+.6f}')
        def sg(x):
            return '+' if x > 0 else ('-' if x < 0 else '0')
        print(f'   знаки: SI/c3 {sg(S["SI"])}{sg(c3)} SII/a2 {sg(S["SII"])}{sg(a2)} '
              f'SIII/(a1-b1) {sg(S["SIII"])}{sg(a1 - b1)} SV/a0 {sg(S["SV"])}{sg(a0)} '
              f'SIxp/-df\' {sg(S["SIxp"])}{sg(-df)}')


if __name__ == '__main__':
    main()
