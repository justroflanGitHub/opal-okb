"""Проба 2: выходные лучи через нормированное направление; спот-RMS вокруг z_G."""
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
K = 8 * fnum ** 2 * wl * 1e-3  # мм на волну на краю
z_pos = compute_z_positions(s)
bfd = parax.get('back_focal_distance', 0)
z_G = z_pos[-2] + bfd
print(f"F#={fnum:.3f} z_G={z_G:.4f} K(мм/волну)={K*1e3:.2f} мкм")

z_start, z_pupil = ab._compute_ray_start(s, parax)


def exit_rays(n=30, field_y=0.0):
    rays = []
    for i in range(n):
        for j in range(n):
            px = -1 + 2 * i / (n - 1)
            py = -1 + 2 * j / (n - 1)
            if px ** 2 + py ** 2 <= 1.0:
                rays.append(make_field_ray(s, px * D / 2, py * D / 2,
                                           field_y, z_start, z_pupil))
    out = []
    for res in ab._trace_ray_list(s, rays, wl):
        if res.success and len(res.path) >= 2:
            u = ab._air_exit_direction(s, res, wl)
            if u is None or u[2] < 1e-6:
                continue
            p = res.path[-1]
            out.append((p[0], p[1], p[2], u[0] / u[2], u[1] / u[2]))
    return out


er = exit_rays()
print(f"выходных лучей: {len(er)}")


def rms_spot_at(z_t):
    xs = np.array([x + kx * (z_t - z) for x, y, z, kx, ky in er])
    ys = np.array([y + ky * (z_t - z) for x, y, z, kx, ky in er])
    return math.sqrt(((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2).mean())


print("RMS пятна вокруг z_G:")
for dz in (-1.0, -0.7, -0.536, -0.4, -0.25, 0.0, 0.25, 0.5, 0.736, 1.0):
    print(f"  dz={dz:+.3f}: {rms_spot_at(z_G + dz) * 1e3:8.3f} мкм")

zs = np.linspace(z_G - 2, z_G + 2, 4001)
rms = np.array([rms_spot_at(z) for z in zs])
i0 = int(rms.argmin())
print(f"\nmin spot RMS: dz={zs[i0] - z_G:+.5f} мм "
      f"(= {(zs[i0]-z_G)/K:+.5f}λ), RMS={rms[i0]*1e3:.3f} мкм")

# маргинальный луч: пересечение оси (через нормированное направление)
for py in (0.5, 0.7, 1.0):
    ray = make_field_ray(s, 0, py * D / 2, 0.0, z_start, z_pupil)
    res = ab.trace_ray_through_system(s, ray, wl)
    u = ab._air_exit_direction(s, res, wl)
    p = res.path[-1]
    z_cross = p[2] - p[1] / (u[1] / u[2])
    print(f"  луч rho={py:.1f}: ось в dz={z_cross - z_G:+.4f} мм")
