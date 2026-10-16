"""Проба 7: прямая проверка IDW в точке (0.1, 0)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
from analysis.aberrations import trace_wavefront_hexapolar
from analysis.strehl import _pupil_grid_from_points


def build_doublet(aperture):
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


s = build_doublet(12.0)
pts = trace_wavefront_hexapolar(s, wl=0.58756, field_y=0.0, num_rings=10)
wf, mask = _pupil_grid_from_points(pts, grid_size=128)

xs = np.linspace(-1, 1, 128)
gx, gy = np.meshgrid(xs, xs)
rg = np.sqrt(gx**2 + gy**2)
m = mask >= 0.5

# центр решётки и точка на r=0.1
ic = 63  # xs[63] = -1+126/127 = -0.00787, xs[64]=+0.00787
print(f"wf[63,63] (r~0.011) = {wf[63,63]:+.6f}")
print(f"wf[63,64] (r~0.011) = {wf[63,64]:+.6f}")
j = int(np.argmin(np.abs(xs - 0.1)))
print(f"xs[{j}]={xs[j]:+.5f}; wf[63,{j}] = {wf[63,j]:+.6f}")

# ручной IDW в (0.1, 0)
sample = np.array([(px, py) for px, py, _ in pts])
values = np.array([w for _, _, w in pts])
soft = (2/127)**2
p = np.array([xs[j], 0.0])
d2 = ((sample - p)**2).sum(axis=1)
wts = 1.0/(d2 + soft)
manual = (wts*values).sum()/wts.sum()
print(f"ручной IDW({xs[j]:.4f},0) = {manual:+.6f}")
# топ-вклады
idx = np.argsort(wts)[::-1][:6]
for i in idx:
    print(f"   w={wts[i]:9.1f} d2={d2[i]:.6f} W={values[i]:+.6f} pt={sample[i]}")

# кольцевые средние решётки — аккуратно, шагом 0.05
print("\nпрофиль решётки (широкие бины):")
for r0 in (0.1, 0.3, 0.5, 0.7, 0.9):
    sel = m & (np.abs(rg - r0) < 0.05)
    print(f"  r={r0}: W_grid={wf[sel].mean():+.5f} (n={sel.sum()})")
