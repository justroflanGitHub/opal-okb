# -*- coding: utf-8 -*-
"""Скретч: одна преломляющая сфера — эталон для SI↔трассировка."""
import math

from domain.models import OpticalSystem, Surface, Wavelength, FieldPoint, ObjectType, ApertureType
from domain.calculations import paraxial_trace, refractive_index
from analysis.aberrations import _compute_ray_start, _pupil_field_ray
import ray_native

wl = 0.54607
R = 100.0
n2 = refractive_index('К8', wl)
sysm = OpticalSystem(name='single', object_type=ObjectType.INFINITE, object_height=1.0)
sysm.wavelengths = [Wavelength(wl)]
sysm.field_points = [FieldPoint(0.0)]
sysm.aperture_type = ApertureType.ENTRANCE_PUPIL
sysm.aperture_value = 20.0
sysm.surfaces = [Surface(radius=R, thickness=300.0, glass='К8', semi_diameter=50.0)]
sysm.stop_surface = 1

parax = paraxial_trace(sysm)
print('paraxial:', {k: round(v, 6) for k, v in parax.items() if isinstance(v, (int, float))})
n_img = n2
# маргинальный базис: y0=1 (h=a на апертуре a), u' = a*nu_end/n'
# параксиально: nu1 = -(n2-1)/R*y0 → u' = nu1/n2
u1 = -(n2 - 1.0) / R
up = u1 / n2
print(f'n2={n2}, u\'(базис y=1)={up:.6f}')

# ── ТОЧНЫЙ Snell (без порта): пересечение прямой || z высоты h со сферой ───
def exact_cross(h):
    import math as _m
    z_sag = R - _m.sqrt(R * R - h * h)
    sin_i = h / R
    sin_p = sin_i / n2
    i = _m.asin(sin_i)
    ip = _m.asin(sin_p)
    u_p = -_m.tan(i - ip)          # угол преломлённого луча к оси z
    return z_sag - h / u_p

z_focus_exact = R * n2 / (n2 - 1.0)   # параксиальный фокус от вершины (среда n2)
print('exact Snell: LSA/h² при h=1,2,3:')
for h in (1.0, 2.0, 3.0):
    print(f'   h={h}: LSA={exact_cross(h) - z_focus_exact:+.6f}, /h²={(exact_cross(h) - z_focus_exact) / h / h:+.8f}')

# SI замкнутой формой: A = h/R (u=0,n=1), Δ(1/n)=1/n2-1
for a in (2.0, 5.0):
    SI = (a / R) ** 2 * a * (1.0 / n2 - 1.0)
    # трассировка: луч || оси на высоте h
    results = []
    for frac in (0.3, 0.5, 0.7, 0.9):
        h = a * frac
        ray = _pupil_field_ray(sysm, 0.0, h, 0.0, -50.0, 0.0)
        r = ray_native.trace_batch(sysm, [(ray.x, ray.y, ray.z, ray.k, ray.l, ray.m)], wl)[0]
        # z пересечения оси: между последними точками
        (x1, y1, z1), (x2, y2, z2) = r.path[-2], r.path[-1]
        t = -y1 / (y2 - y1)
        z_cross = z1 + t * (z2 - z1)
        z_focus = R + parax['sF_prime']
        LSA = z_cross - z_focus
        # y на параксиальном фокусе
        y_f = y1 + (z_focus - z1) / (z2 - z1) * (y2 - y1)
        results.append((frac, h, LSA, y_f))
    # LSA(h) = k·h²;  ε(h) = c3·(h/a)³·? — считаем и то и то
    import numpy as np
    hh = np.array([r[1] for r in results]); ll = np.array([r[2] for r in results])
    yy = np.array([r[3] for r in results])
    k = float(np.sum(hh ** 2 * ll) / np.sum(hh ** 4))
    c3 = float(np.sum((hh / a) ** 3 * yy) / np.sum((hh / a) ** 6))
    print(f'a={a}: SI={SI:.6g}; k(LSA/h²)={k:.6g}; '
          f'-SI/(2n\'u\'²)={-SI / (2 * n_img * (a * up) ** 2):.6g}; '
          f'+SI/(2n\'u\'²)={SI / (2 * n_img * (a * up) ** 2):.6g}')
    print(f'      c3(ε/ρ³)={c3:.6g}; -SI/(2n\'u\')={-SI / (2 * n_img * a * up):.6g}; '
          f'+SI/(2n\'u\')={SI / (2 * n_img * a * up):.6g}')
