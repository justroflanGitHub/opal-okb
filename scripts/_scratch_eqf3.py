"""Проба 5: подбор апертуры дублета для теста 1 (min_RMS ~ max_Strehl ±5%)."""
import math, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
from analysis.aberrations import trace_wavefront_hexapolar
from analysis.strehl import _pupil_grid_from_points, strehl_exact_from_wavefront


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
xs = np.linspace(-1, 1, 128)
gx, gy = np.meshgrid(xs, xs)
r2g = gx**2 + gy**2

for aper in (8.0, 10.0, 12.0, 14.0, 16.0):
    s = build_doublet(aper)
    pts = trace_wavefront_hexapolar(s, wl=wl, field_y=0.0, num_rings=10)
    r2 = np.array([px*px+py*py for px, py, _ in pts])
    W = np.array([w for _, _, w in pts])
    d_ls = -np.cov(W, r2, bias=True)[0, 1] / np.var(r2)
    wf, mask = _pupil_grid_from_points(pts, grid_size=128)
    span = max(1.0, abs(d_ls) + 1.0)
    ds = np.linspace(d_ls - span, d_ls + span, 41)
    sv = np.array([strehl_exact_from_wavefront(wf + d*r2g, mask) or 0.0 for d in ds])
    i0 = sv.argmax()
    y0, y1, y2 = sv[i0-1], sv[i0], sv[i0+1]
    den = y0 - 2*y1 + y2
    d_st = ds[i0] + (0.5*(y0 - y2)/den*(ds[1]-ds[0]) if den != 0 else 0.0)
    Wb = W + d_ls*r2
    sigma = Wb.std()
    diff_pct = abs(d_st - d_ls)/max(abs(d_ls), 1e-9)*100
    print(f"aper={aper:4.1f}: W_edge={W[r2>0.99].mean():+.3f}λ d_ls={d_ls:+.4f} "
          f"d_strehl={d_st:+.4f} (S={sv[i0]:.4f}, σ_ls={sigma:.4f}λ) "
          f"расхождение={diff_pct:5.1f}%")

t0 = time.time()
for _ in range(10):
    trace_wavefront_hexapolar(build_doublet(12.0), wl=wl, field_y=0.0, num_rings=10)
print(f"\n10 трассировок 331 луч: {time.time()-t0:.2f} с")
