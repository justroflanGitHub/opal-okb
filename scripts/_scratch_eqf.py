"""Проба 3: какие зонные паритеты дают корень между d_ls и d_zone."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, paraxial_trace
from optics_utils import get_effective_aperture
from analysis.aberrations import trace_wavefront_hexapolar


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


RINGS = 10
s = build_doublet(20.0)
wl = 0.58756
pts = trace_wavefront_hexapolar(s, wl=wl, field_y=0.0, num_rings=RINGS)
rho2 = np.array([px * px + py * py for px, py, _ in pts])
W = np.array([w for _, _, w in pts])

d_ls = -np.cov(W, rho2, bias=True)[0, 1] / np.var(rho2)
m = {}
k = {}
for ring in range(RINGS + 1):
    sel = np.array([abs(math.hypot(px, py) - ring / RINGS) < 1e-9
                    for px, py, _ in pts])
    if sel.any():
        m[ring / RINGS] = W[sel].mean()
        k[ring / RINGS] = rho2[sel].mean()
d_zone = (m[0.7] - m[1.0]) / (k[1.0] - k[0.7])
print(f"d_ls={d_ls:.5f}  d_zone={d_zone:.5f}  интервал [{min(d_ls,d_zone):.4f}, {max(d_ls,d_zone):.4f}]")


def in_interval(d):
    lo, hi = sorted((d_ls, d_zone))
    return lo <= d <= hi


def roots(f, lo=-10.0, hi=15.0, n=25001):
    ds = np.linspace(lo, hi, n)
    fs = np.array([f(d) for d in ds])
    out = []
    for i in range(len(ds) - 1):
        if fs[i] == 0.0 or fs[i] * fs[i + 1] < 0:
            d0, d1, f0, f1 = ds[i], ds[i + 1], fs[i], fs[i + 1]
            out.append(d0 - f0 * (d1 - d0) / (f1 - f0))
    return out


def zone_sel(rmin, rmax):
    r = np.sqrt(rho2)
    return (r >= rmin - 1e-9) & (r <= rmax + 1e-9)


def zone_rms(d, sel):
    v = W[sel] + d * rho2[sel]
    return v.std()


def zone_mean(d, sel):
    return (W[sel] + d * rho2[sel]).mean()


print("\n— равенство RMS зон (Equal Quality) —")
for (a, b, name) in [
    ((0.0, 0.5), (0.5, 1.0), "[0,.5] vs [.5,1]"),
    ((0.0, 0.7), (0.7, 1.0), "[0,.7] vs [.7,1]"),
    ((0.3, 0.7), (0.0, 0.3), "[.3,.7] vs [0,.3]"),
    ((0.3, 0.7), (0.7, 1.0), "[.3,.7] vs [.7,1]"),
]:
    s1, s2 = zone_sel(*a), zone_sel(*b)
    f = lambda d: zone_rms(d, s1) - zone_rms(d, s2)
    rr = roots(f)
    verdict = ['ВНУТРИ' if in_interval(r) else 'нет' for r in rr]
    print(f"  {name}: корни {[f'{r:+.4f}' for r in rr]} {verdict}")

print("\n— равенство |mean W| зон (паритет модулей) —")
for (a, b, name) in [
    ((0.0, 0.5), (0.5, 1.0), "[0,.5] vs [.5,1]"),
    ((0.0, 0.7), (0.7, 1.0), "[0,.7] vs [.7,1]"),
    ((0.3, 0.7), (0.0, 0.3), "[.3,.7] vs [0,.3]"),
    ((0.3, 0.7), (0.7, 1.0), "[.3,.7] vs [.7,1]"),
    ((0.0, 0.3), (0.7, 1.0), "[0,.3] vs [.7,1]"),
]:
    s1, s2 = zone_sel(*a), zone_sel(*b)
    f = lambda d: abs(zone_mean(d, s1)) - abs(zone_mean(d, s2))
    rr = roots(f)
    verdict = ['ВНУТРИ' if in_interval(r) else 'нет' for r in rr]
    print(f"  {name}: корни {[f'{r:+.4f}' for r in rr]} {verdict}")

print("\n— равенство W на паре колец (in-phase: W(r1)=W(r2)) —")
for r1 in (0.2, 0.3, 0.4, 0.5):
    for r2 in (0.7, 1.0):
        d = (m[r1] - m[r2]) / (k[r2] - k[r1])
        print(f"  W({r1})=W({r2}): d={d:+.4f} {'ВНУТРИ' if in_interval(d) else 'нет'}")

print("\n— PV-минимакс по зонам (minimize max|W| на [a,b]) —")
for (a, b) in [(0.0, 1.0), (0.3, 1.0), (0.3, 0.7), (0.0, 0.7)]:
    sel = zone_sel(a, b)
    ds = np.linspace(0, 8, 8001)
    mx = np.array([np.abs(W[sel] + d * rho2[sel]).max() for d in ds])
    print(f"  [{a},{b}]: d*={ds[mx.argmin()]:+.4f} "
          f"{'ВНУТРИ' if in_interval(ds[mx.argmin()]) else 'нет'}")
