"""Проба 4: стабильность EQF-корня по кольцам; argmax Штреля."""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
from analysis.aberrations import trace_wavefront_hexapolar
from analysis.strehl import _pupil_grid_from_points, strehl_exact_from_wavefront


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
pts = trace_wavefront_hexapolar(s, wl=wl, field_y=0.0, num_rings=10)
rho2 = np.array([px*px+py*py for px, py, _ in pts])
W = np.array([w for _, _, w in pts])
r = np.sqrt(rho2)

# кольца для зоны/края — бины по r
def ring_mean(r_target, band):
    sel = np.abs(r - r_target) <= band
    if sel.sum() < 3:
        sel = np.abs(r - r_target) <= band * 2
    return W[sel].mean(), rho2[sel].mean(), int(sel.sum())

for rings in (6, 8, 10, 12, 14):
    p = trace_wavefront_hexapolar(s, wl=wl, field_y=0.0, num_rings=rings)
    r2 = np.array([px*px+py*py for px, py, _ in p])
    w = np.array([x for _, _, x in p])
    rr = np.sqrt(r2)
    d_ls = -np.cov(w, r2, bias=True)[0, 1] / np.var(r2)
    m7, k7, n7 = w[np.abs(rr-0.7) <= 0.7/rings*0.51], None, None
    # зона/край через бины
    sel_z = np.abs(rr - 0.7) <= max(0.7/rings*0.51, 0.045)
    sel_e = rr >= 1.0 - max(1.0/rings*0.51, 0.045)
    d_zone = (w[sel_z].mean() - w[sel_e].mean()) / (rho2_ := (sel_e, sel_z), r2[sel_e].mean() - r2[sel_z].mean())[1] if True else 0
    # EQF: равенство СКВ [0.3,0.7] и [0.7,1]
    mid = (rr >= 0.3) & (rr < 0.7)
    out = rr >= 0.7
    def f(d):
        return (w[mid] + d*r2[mid]).std() - (w[out] + d*r2[out]).std()
    ds = np.linspace(d_ls - 3, d_ls + 3, 6001)
    fs = np.array([f(d) for d in ds])
    sgn = np.where(np.diff(np.sign(fs)) != 0)[0]
    roots = []
    for i in sgn:
        roots.append(ds[i] - fs[i]*(ds[i+1]-ds[i])/(fs[i+1]-fs[i]))
    d_eqf = min(roots, key=lambda t: abs(t - d_ls)) if roots else float('nan')
    lo, hi = sorted((d_ls, d_zone))
    ok = lo <= d_eqf <= hi
    print(f"rings={rings:2d}: d_ls={d_ls:+.4f} d_zone={d_zone:+.4f} "
          f"roots={[f'{x:+.3f}' for x in roots]} eqf={d_eqf:+.4f} {'ВНУТРИ' if ok else 'ВНЕ'}")

# argmax Штреля
wf, mask = _pupil_grid_from_points(pts, grid_size=128)
xs = np.linspace(-1, 1, 128)
gx, gy = np.meshgrid(xs, xs)
r2g = gx**2 + gy**2
ds = np.linspace(2.0, 5.0, 61)
sv = [strehl_exact_from_wavefront(wf + d*r2g, mask) for d in ds]
sv = np.array([x if x else 0 for x in sv])
i0 = sv.argmax()
print(f"\nStrehl: argmax={ds[i0]:+.4f}λ (S={sv[i0]:.5f}); S(d_ls=3.4285)="
      f"{strehl_exact_from_wavefront(wf + 3.42854*r2g, mask):.5f}")
# парабола
if 0 < i0 < len(ds)-1:
    y0, y1, y2 = sv[i0-1], sv[i0], sv[i0+1]
    den = y0 - 2*y1 + y2
    dx = 0.5*(y0 - y2)/den*(ds[1]-ds[0]) if den != 0 else 0
    print(f"парабол. уточнение: {ds[i0]+dx:+.4f}λ")
