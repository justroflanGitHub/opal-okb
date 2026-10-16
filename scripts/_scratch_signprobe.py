"""Знаковая калибровка: W_edge vs сдвиг опорной сферы, маргинальный фокус."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, paraxial_trace
from optics_utils import get_effective_aperture, make_field_ray, compute_z_positions
from analysis import aberrations as ab


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


s = build_doublet(20.0)
wl = 0.58756
parax = paraxial_trace(s)
efl = abs(parax.get('focal_length', 0.0))
D = get_effective_aperture(s, default=10.0)
fnum = efl / D
z_pos = compute_z_positions(s)
bfd = parax.get('back_focal_distance', 0)
z_G = z_pos[-2] + bfd  # гауссова плоскость (как _paraxial_focus_z)
print(f"efl={efl:.3f} D={D:.3f} F#={fnum:.3f} bfd={bfd:.4f} z_G={z_G:.4f} "
      f"(именованная плоскость изображения: {z_pos[-1]:.4f})")

z_start, z_pupil = ab._compute_ray_start(s, parax)

# маргинальный и средне-зональный лучи: где пересекают ось
for py in (0.5, 0.7, 1.0):
    ray = make_field_ray(s, 0, py * D / 2, 0.0, z_start, z_pupil)
    res = ab.trace_ray_through_system(s, ray, wl)
    if res.success and len(res.path) >= 2:
        p1, p0 = res.path[-1], res.path[-2]
        slope = (p1[1] - p0[1]) / (p1[2] - p0[2])
        z_cross = p1[2] - p1[1] / slope
        print(f"  луч rho={py:.1f}: y@img={p1[1]*1e3:+9.2f} мкм  "
              f"пересечение оси z={z_cross:.4f} (dz от z_G = {z_cross - z_G:+.4f} мм)")

# W_edge против опорной сферы, центр которой сдвинут на delta
def w_edge_at(delta_mm, rho=1.0, rings=10):
    center = (0.0, 0.0, z_G + delta_mm)
    R = abs(center[2] - z_pos[-2])
    chief_opl = ab._chief_reference_opl(s, wl, 0.0, z_start, z_pupil, center, R)
    pts = ab._hexapolar_points(rings)
    tol = 1e-9
    got = [p for p in pts if abs(math.hypot(*p) - rho) < tol]
    px, py = got[0]
    ray = make_field_ray(s, px * D / 2, py * D / 2, 0.0, z_start, z_pupil)
    res = ab.trace_ray_through_system(s, ray, wl)
    return ab._ray_wavefront(s, res, chief_opl, center, R, wl)

print("\nW(rho=1) относительно опорной сферы с центром z_G + delta:")
base = w_edge_at(0.0)
print(f"  delta=0: W_edge={base:+.5f}λ")
for delta in (-0.536, -0.1, +0.1, +0.536):
    w = w_edge_at(delta)
    dw_per_mm = (w - base) / delta
    pred = 1.0 / (8 * fnum ** 2 * wl * 1e-3)  # волн/мм, если W += delta/(8 F#^2 lam)
    print(f"  delta={delta:+.3f} мм: W_edge={w:+.5f}λ  dW/ddelta={dw_per_mm:+.4f}λ/мм"
          f"  (предсказание ±{pred:.4f})")
