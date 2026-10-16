"""Проба 6: радиальный профиль W_grid (IDW) vs кольцевые средние."""
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


wl = 0.58756
s = build_doublet(12.0)
pts = trace_wavefront_hexapolar(s, wl=wl, field_y=0.0, num_rings=10)
r2 = np.array([px*px+py*py for px, py, _ in pts])
W = np.array([w for _, _, w in pts])
r = np.sqrt(r2)

wf, mask = _pupil_grid_from_points(pts, grid_size=128)
n = 128
xs = np.linspace(-1, 1, n)
gx, gy = np.meshgrid(xs, xs)
rg = np.sqrt(gx**2 + gy**2)
m = mask >= 0.5

print(" r     W_кольцо   W_grid(бин)   n_grid")
for rr in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99):
    sel = np.abs(r - rr) < 0.04
    mring = m & (np.abs(rg - rr) < 0.02)
    print(f" {rr:.2f}  {W[sel].mean():+9.5f}  {wf[mring].mean():+9.5f}  {mring.sum()}")

# LS на решётке
r2g = gx**2 + gy**2
d_ls_grid = -np.cov(wf[m], r2g[m], bias=True)[0, 1] / np.var(r2g[m])
d_ls_hex = -np.cov(W, r2, bias=True)[0, 1] / np.var(r2)
print(f"\nd_ls(гекса)={d_ls_hex:+.5f}  d_ls(решётка)={d_ls_grid:+.5f}")

# то же для синтетики W = -0.4*rho^4 (без интерполяции, чистая решётка)
w_syn = -0.4 * r2g**2
d_syn = -np.cov(w_syn[m], r2g[m], bias=True)[0, 1] / np.var(r2g[m])
print(f"синтетика b*rho^4 на решётке: d_ls={d_syn:+.5f} (точно b=-0.4 → +0.4)")

# а теперь синтетика ЧЕРЕЗ гекса+IDW
syn_pts = [(px, py, -0.4*(px*px+py*py)**2) for px, py, _ in pts]
wf2, _ = _pupil_grid_from_points(syn_pts, grid_size=128)
d_syn2 = -np.cov(wf2[m], r2g[m], bias=True)[0, 1] / np.var(r2g[m])
r2s = np.array([px*px+py*py for px, py, _ in syn_pts])
Ws = np.array([w for _, _, w in syn_pts])
d_syn2_hex = -np.cov(Ws, r2s, bias=True)[0, 1] / np.var(r2s)
print(f"синтетика гекса→IDW: d_ls(решётка)={d_syn2:+.5f}  d_ls(гекса)={d_syn2_hex:+.5f}")
