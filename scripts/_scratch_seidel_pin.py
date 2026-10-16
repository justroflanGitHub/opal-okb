# -*- coding: utf-8 -*-
"""Скретч: пиновка констант Зейдель↔трассировка для A5 (TASK_SEIDEL).

1) SI → поперечная сферическая на гауссовой плоскости:  ε(ρ) = C·SI_a·ρ³
2) SII/SIII/SIV/SV → меридиональный веер на поле
3) SIxp → хроматический сдвиг фокуса (эталон: paraxial_trace на 2 λ)
"""
import math
import sys

from domain.models import create_demo_system_by_name
from domain.calculations import paraxial_trace, seidel_aberrations
from analysis.aberrations import _compute_ray_start, _pupil_field_ray
import ray_native
from optics_utils import get_effective_aperture, get_primary_wl


def parax_data(system, wl):
    """Параксиальные базисы: маргинальный y[0]=1,nu[0]=0; главный от стопа."""
    ns = len(system.surfaces)
    n = [1.0]
    from domain.calculations import refractive_index
    for s in system.surfaces:
        n.append(-n[-1] if s.is_reflective
                 else refractive_index(s.glass, wl, None, getattr(s, 'n_override', None)))
    y = [0.0] * (ns + 1); nu = [0.0] * (ns + 1)
    y[0], nu[0] = 1.0, 0.0
    for i, s in enumerate(system.surfaces):
        R = s.radius if s.radius != 0 else float('inf')
        if R != float('inf'):
            nu[i + 1] = nu[i] - y[i] * (n[i + 1] - n[i]) / R
        else:
            nu[i + 1] = nu[i]
        y[i + 1] = y[i] + nu[i + 1] * s.thickness / n[i + 1]
    # главный от стопа
    yb = [0.0] * (ns + 1); nub = [0.0] * (ns + 1)
    k = max(0, min(system.stop_surface - 1, ns - 1))
    yb[k], nub[k] = 0.0, 1.0
    for i in range(k - 1, -1, -1):
        s = system.surfaces[i]
        R = s.radius if s.radius != 0 else float('inf')
        yb[i] = yb[i + 1] - nub[i + 1] * s.thickness / n[i + 1]
        nub[i] = nub[i + 1] + (yb[i] * (n[i + 1] - n[i]) / R if R != float('inf') else 0.0)
    for i in range(k, ns):
        s = system.surfaces[i]
        R = s.radius if s.radius != 0 else float('inf')
        nub[i + 1] = nub[i] - (yb[i] * (n[i + 1] - n[i]) / R if R != float('inf') else 0.0)
        yb[i + 1] = yb[i] + nub[i + 1] * s.thickness / n[i + 1]
    return n, y, nu, yb, nub


def sums(system, wl, a, s_scale):
    """Суммы на реальной апертуре a и поле (масштаб главного s_scale)."""
    n, y, nu, yb, nub = parax_data(system, wl)
    ns = len(system.surfaces)
    A = [a * (nu[i] + n[i] * y[i] / (system.surfaces[i].radius or math.inf))
         if system.surfaces[i].radius else None for i in range(ns)]
    Ab = [s_scale * (nub[i] + n[i] * yb[i] / (system.surfaces[i].radius or math.inf))
          if system.surfaces[i].radius else None for i in range(ns)]
    S = dict(SI=0.0, SII=0.0, SIII=0.0, SIV=0.0, SV=0.0)
    for i in range(ns):
        s = system.surfaces[i]
        R = s.radius
        if R == 0:
            continue
        dinv = 1.0 / n[i + 1] - 1.0 / n[i]
        h = a * y[i]
        Ai, Abi = A[i], Ab[i]
        S['SI'] += Ai * Ai * h * dinv
        S['SII'] += Abi * Ai * h * dinv
        S['SIII'] += Abi * Abi * h * dinv
        S['SIV'] += (n[i + 1] - n[i]) / (R * n[i] * n[i + 1])
        a_safe = Ai if abs(Ai) > 1e-12 else 1e-12
        S['SV'] += (Abi ** 3 / a_safe) * h * dinv + 3.0 * Abi * Abi * h * dinv
    # u', n' в пространстве изображений
    np_img = n[-1]
    up = a * nu[-1] / np_img          # угол маргинального луча
    return S, np_img, up


def _at_focus(system, wl, result):
    """Координата луча на параксиальной фокальной плоскости (x, y)."""
    parax = paraxial_trace(system)
    z_pos = [0.0]
    for s in system.surfaces:
        z_pos.append(z_pos[-1] + s.thickness)
    z_focus = z_pos[-2] + parax['sF_prime']       # фокус от последней поверхности
    (x0, y0, z0), (x1, y1, z1) = result.path[-2], result.path[-1]
    dz = z_focus - z0
    dz_seg = z1 - z0
    t = dz / dz_seg if abs(dz_seg) > 1e-12 else 0.0
    return x0 + t * (x1 - x0), y0 + t * (y1 - y0)


def trace_eps(system, wl, field_y, rho, sagittal=False):
    """Поперечная аберрация луча (ρ) на параксиальном фокусе, мм."""
    ap = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    z0, zp = _compute_ray_start(system, parax)
    px, py = (rho, 0.0) if sagittal else (0.0, rho)
    ray = _pupil_field_ray(system, px * ap / 2, py * ap / 2, field_y, z0, zp)
    r = ray_native.trace_batch(system, [(ray.x, ray.y, ray.z, ray.k, ray.l, ray.m)], wl)[0]
    if not r.success or len(r.path) < 2:
        return None
    x, y = _at_focus(system, wl, r)
    if field_y == 0.0:
        return (x if sagittal else y)
    # идеальная высота: параксиальный главный на фокусе (масштаб s)
    n, y_, nu_, yb, nub = parax_data(system, wl)
    ns = len(system.surfaces)
    s = chief_scale(system, field_y, wl)
    y_par_chief = s * (yb[ns - 1] + nub[ns - 1] * parax['sF_prime'] / n[ns])
    return (x if sagittal else y - y_par_chief)


def chief_scale(system, field_y, wl):
    n, y, nu, yb, nub = parax_data(system, wl)
    from domain.models import ObjectType
    if system.object_type == ObjectType.INFINITE:
        return math.tan(math.radians(field_y)) / nub[0]
    d = abs(system.surfaces[0].thickness) if system.surfaces else 50.0
    return (-field_y / d) / nub[0]


def fit_odd(eps):
    """ε(ρ)/ρ = c1 + c3·ρ² → (c1, c3) МНК."""
    import numpy as np
    rows, rhs = [], []
    for rho, e in eps:
        rows.append([1.0, rho * rho])
        rhs.append(e / rho)
    c, *_ = np.linalg.lstsq(rows, rhs, rcond=None)
    return c[0], c[1]


def fit_cubic(eps):
    """ε(ρ)=a0+a1ρ+a2ρ²+a3ρ³ → МНК."""
    import numpy as np
    rows, rhs = [], []
    for rho, e in eps:
        rows.append([1.0, rho, rho * rho, rho ** 3])
        rhs.append(e)
    c, *_ = np.linalg.lstsq(rows, rhs, rcond=None)
    return c


def main():
    for name, field in (('plano_convex', 2.0), ('achromat', 2.5), ('cook_doublet', 2.0)):
        sysm = create_demo_system_by_name(name)
        wl = get_primary_wl(sysm)
        a = get_effective_aperture(sysm, default=10.0) / 2.0
        # главный масштаб: поле в градусах → базис
        s = chief_scale(sysm, field, wl)
        S, np_img, up = sums(sysm, wl, a, s)
        print(f'== {name}: a={a}, field={field}°, u\'={up:.6f}, n\'={np_img}')
        print('   sums:', {k: f'{v:.6g}' for k, v in S.items()})
        K = -1.0 / (2.0 * np_img * up)   # общий множитель
        # осевой веер: ε(ρ) = c1·ρ + K·SI·ρ³
        eps = [(rho, trace_eps(sysm, wl, 0.0, rho)) for rho in (0.15, 0.25, 0.35, 0.45)]
        c1, c3 = fit_odd(eps)
        print(f'   axial: c3_traced={c3 * 1000:+.3f} мкм, K·SI={K * S["SI"] * 1000:+.3f} мкм, '
              f'ratio={c3 / (K * S["SI"]) if K * S["SI"] else float("nan"):.4f}')
        # меридиональный веер на поле: ε(ρ)=a0+a1ρ+a2ρ²+a3ρ³
        rhos = (-0.45, -0.35, -0.25, -0.15, 0.15, 0.25, 0.35, 0.45)
        eps = [(rho, trace_eps(sysm, wl, field, rho)) for rho in rhos]
        a0, a1, a2, a3 = fit_cubic(eps)
        print(f'   field: a0={a0 * 1000:+.2f} (K·SV={K * S["SV"] * 1000:+.2f}) ratio0={a0 / (K * S["SV"]) if K * S["SV"] else float("nan"):.4f}')
        print(f'          a2={a2 * 1000:+.2f} (3K·SII={3 * K * S["SII"] * 1000:+.2f}) ratio2={a2 / (3 * K * S["SII"]) if 3 * K * S["SII"] else float("nan"):.4f}')
        print(f'          a1={a1 * 1000:+.2f} (K(3SIII+SIV)={K * (3 * S["SIII"] + S["SIV"]) * 1000:+.2f}) ratio1={a1 / (K * (3 * S["SIII"] + S["SIV"])) if K * (3 * S["SIII"] + S["SIV"]) else float("nan"):.4f}')
        print(f'          a3={a3 * 1000:+.2f} (K·SI={K * S["SI"] * 1000:+.2f}) ratio3={a3 / (K * S["SI"]) if K * S["SI"] else float("nan"):.4f}')
        # сагиттальный: εx(ρ)=b1ρ (+K(SIII+SIV)... ) — только b1有意义
        eps = [(rho, trace_eps(sysm, wl, field, rho, sagittal=True)) for rho in (0.2, 0.35)]
        b1 = (eps[1][1] / eps[1][0] + eps[0][1] / eps[0][0]) / 2
        print(f'   sagittal: b1={b1 * 1000:+.2f} (K(SIII+SIV)/1?={K * (S["SIII"] + S["SIV"]) * 1000:+.2f}) ratios={b1 / (K * (S["SIII"] + S["SIV"])) if K * (S["SIII"] + S["SIV"]) else float("nan"):.4f}')


if __name__ == '__main__':
    main()
