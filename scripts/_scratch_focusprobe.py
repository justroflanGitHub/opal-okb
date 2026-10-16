"""Численный эксперимент TASK_FOCUS: критерии оптимального фокуса на дублете.

d_ls (min RMS W), d_zone (равенство W на краю и зоне 0.7), корни паритета
|W(0.3)|=|W(0.7)|, min spot RMS — в волнах и в мм (Δz = 8·F#²·λ·d).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, paraxial_trace
from optics_utils import get_effective_aperture
from analysis.aberrations import trace_wavefront_hexapolar, _hexapolar_points, _compute_ray_start
import ray_native
from analysis.aberrations import _trace_ray_list


def build_doublet(aperture=20.0):
    s = OpticalSystem(name='doublet')
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5, semi_diameter=aperture / 2 + 2),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=aperture / 2 + 2),
        Surface(radius=-200, glass='', thickness=0, semi_diameter=aperture / 2 + 2),
    ]
    s.stop_surface = 1
    s.aperture_value = aperture
    return s


NUM_RINGS = 10


def ring_stats(system, wl=0.58756, field_y=0.0, num_rings=NUM_RINGS):
    pts = trace_wavefront_hexapolar(system, wl=wl, field_y=field_y, num_rings=num_rings)
    by_ring = {}  # r -> [(rho2, W)]
    for px, py, w in pts:
        r = math.hypot(px, py)
        ring = round(r * num_rings)
        by_ring.setdefault(ring, []).append((px * px + py * py, w))
    stats = {}
    for ring, vals in sorted(by_ring.items()):
        arr = np.array(vals)
        stats[ring / num_rings] = (arr[:, 0].mean(), arr[:, 1].mean(), arr[:, 1].std())
    return stats, pts


def main():
    s = build_doublet(20.0)
    wl = 0.58756
    parax = paraxial_trace(s)
    efl = abs(parax.get('focal_length', 0.0))
    D = get_effective_aperture(s, default=10.0)
    fnum = efl / D
    k_mm_per_wave = 8.0 * fnum * fnum * wl * 1e-3
    print(f"efl={efl:.3f} мм  D={D:.3f} мм  F#={fnum:.3f}  "
          f"1 волна на краю = {k_mm_per_wave*1e3:.4f} мкм")

    stats, pts = ring_stats(s)
    print("\nкольца (r: <rho2>, <W>, std W):")
    for r, (k, m, sd) in stats.items():
        print(f"  r={r:.2f}: k={k:.4f}  m={m:+.5f}λ  std={sd:.5f}λ")

    rho2 = np.array([px * px + py * py for px, py, _ in pts])
    W = np.array([w for _, _, w in pts])

    # min RMS W: least squares  Var(W + d·rho2) -> d = -Cov/Var
    cov = ((W - W.mean()) * (rho2 - rho2.mean())).mean()
    var = ((rho2 - rho2.mean()) ** 2).mean()
    d_ls = -cov / var
    print(f"\nd_ls (min RMS W)      = {d_ls:+.5f}λ  "
          f"({d_ls * k_mm_per_wave:+.5f} мм)")

    # зона 0.7: равенство W на краю (r=1) и зоне (r=0.7)
    m_e, k_e = stats[1.0][1], stats[1.0][0]
    m_z, k_z = stats[0.7][1], stats[0.7][0]
    d_zone = (m_z - m_e) / (k_e - k_z)
    print(f"d_zone (W(1)=W(0.7))  = {d_zone:+.5f}λ  "
          f"({d_zone * k_mm_per_wave:+.5f} мм)")

    # паритет 0.3/0.7: |m3 + d*k3| = |m7 + d*k7|
    m_i, k_i = stats[0.3][1], stats[0.3][0]
    m_o, k_o = stats[0.7][1], stats[0.7][0]

    def f(d):
        return abs(m_i + d * k_i) - abs(m_o + d * k_o)

    ds = np.linspace(-4, 2, 12001)
    fs = np.array([f(d) for d in ds])
    roots = []
    for i in range(len(ds) - 1):
        if fs[i] == 0.0 or fs[i] * fs[i + 1] < 0:
            # линейная интерполяция (f кусочно-линейна)
            d0, d1, f0, f1 = ds[i], ds[i + 1], fs[i], fs[i + 1]
            roots.append(d0 - f0 * (d1 - d0) / (f1 - f0))
    print(f"\nкорни паритета 0.3/0.7: {[f'{r:+.5f}' for r in roots]}")
    for r in roots:
        print(f"   d={r:+.5f}λ ({r * k_mm_per_wave:+.5f} мм)"
              f"  внутри [{min(d_ls, d_zone):+.4f}, {max(d_ls, d_zone):+.4f}]?"
              f" {'ДА' if min(d_ls, d_zone) <= r <= max(d_ls, d_zone) else 'нет'}")
    print(f"f(d_ls)={f(d_ls):+.5f}  f(d_zone)={f(d_zone):+.5f}")

    # min spot RMS (геометрия): exit rays -> propagate
    aperture = D
    z_start, z_pupil = _compute_ray_start(s, parax)
    rays = []
    n = 30
    for i in range(n):
        for j in range(n):
            px = -1 + 2 * i / (n - 1)
            py = -1 + 2 * j / (n - 1)
            if px ** 2 + py ** 2 <= 1:
                from optics_utils import make_field_ray
                rays.append(make_field_ray(s, px * aperture / 2, py * aperture / 2,
                                           0.0, z_start, z_pupil))
    exit_rays = []
    for res in _trace_ray_list(s, rays, wl):
        if res.success and len(res.path) >= 2:
            last, prev = res.path[-1], res.path[-2]
            dz = last[2] - prev[2]
            if abs(dz) > 1e-12:
                exit_rays.append((last[0], last[1], last[2],
                                  (last[0] - prev[0]) / dz, (last[1] - prev[1]) / dz))

    def rms_at(dz_mm):
        xs = np.array([x + kx * (dz_mm - z) for x, y, z, kx, ky in exit_rays])
        ys = np.array([y + ky * (dz_mm - z) for x, y, z, kx, ky in exit_rays])
        xs, ys = xs - xs.mean(), ys - ys.mean()
        return math.sqrt((xs ** 2 + ys ** 2).mean())

    from optics_utils import compute_z_positions
    img_z = compute_z_positions(s)[-1]
    print(f"\nimg_z={img_z:.4f}; выходные z лучей: "
          f"min={min(z for *_ , z, _, _ in [(x,y,z,kx,ky) for x,y,z,kx,ky in exit_rays]):.4f} "
          f"max={max(z for x,y,z,kx,ky in exit_rays):.4f}")
    print("RMS пятна по dz (мм):")
    for dz in (-2, -1, -0.5, 0, 0.25, 0.5, 1, 2, 5, 10, 15):
        print(f"   dz={dz:+6.2f}: {rms_at(img_z + dz) * 1e3:9.3f} мкм")

    zs = np.linspace(-15, 15, 3001) + img_z
    rms = np.array([rms_at(z) for z in zs])
    i0 = rms.argmin()
    # параболическая уточнялка
    z0, z1, z2 = zs[i0 - 1], zs[i0], zs[i0 + 1]
    r0, r1, r2 = rms[i0 - 1], rms[i0], rms[i0 + 1]
    den = (r0 - 2 * r1 + r2)
    zmin = z1 + 0.5 * (z0 - z2) * (r0 - r2) / (2 * den) if den != 0 else z1
    print(f"\nmin spot RMS: dz={zmin:+.5f} мм (RMS={rms_at(zmin)*1e3:.3f} мкм)")
    d_spot = zmin / k_mm_per_wave
    print(f"  в волнах: {d_spot:+.5f}λ")
    print(f"  для сравнения: d_ls={d_ls * k_mm_per_wave:+.5f} мм, "
          f"d_zone={d_zone * k_mm_per_wave:+.5f} мм")

    # Strehl scan
    from analysis.strehl import _pupil_grid_from_points, strehl_exact_from_wavefront
    wf, mask = _pupil_grid_from_points(pts, grid_size=128)
    xs_ = np.linspace(-1, 1, 128)
    gx, gy = np.meshgrid(xs_, xs_)
    r2g = gx ** 2 + gy ** 2
    ds2 = np.linspace(d_ls - 1.5, d_ls + 1.5, 41)
    strl = []
    for d in ds2:
        s_e = strehl_exact_from_wavefront(wf + d * r2g, mask)
        strl.append(s_e if s_e is not None else 0.0)
    strl = np.array(strl)
    j0 = strl.argmax()
    print(f"\nmax Strehl: d={ds2[j0]:+.5f}λ ({ds2[j0]*k_mm_per_wave:+.5f} мм), "
          f"S={strl[j0]:.4f}")
    print(f"  S(d_ls)={strehl_exact_from_wavefront(wf + d_ls * r2g, mask):.4f}")

    print("\n— сводка (мм) —")
    for name, d in (('min_rms_W', d_ls), ('max_strehl', ds2[j0]),
                    ('zone_best', d_zone), ('min_spot', d_spot)):
        print(f"  {name:12s} {d * k_mm_per_wave:+.5f} мм")


if __name__ == '__main__':
    main()
