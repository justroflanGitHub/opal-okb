"""Проба 8: квадратурный Штрель на гекса-точках vs d_ls (hexa)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, paraxial_trace
from optics_utils import get_effective_aperture
from analysis.aberrations import trace_wavefront_hexapolar, _hexapolar_points


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


def d_ls_of(rho2, W):
    return -np.cov(W, rho2, bias=True)[0, 1] / np.var(rho2)


def s_quad(W, rho2, d):
    ph = np.exp(2j * np.pi * (W + d * rho2))
    return float(np.abs(ph.sum()) ** 2 / len(ph) ** 2)


def argmax_strehl(W, rho2, d0, span=3.0, n=601):
    ds = np.linspace(d0 - span, d0 + span, n)
    ss = np.array([s_quad(W, rho2, d) for d in ds])
    j = int(ss.argmax())
    if 0 < j < n - 1:  # параболическое уточнение
        z0, z1, z2 = ss[j - 1], ss[j], ss[j + 1]
        den = z0 - 2 * z1 + z2
        off = 0.5 * (z0 - z2) / den if den != 0 else 0.0
        off = max(-1.0, min(1.0, off))
        return ds[j] + off * (ds[1] - ds[0]), ss[j]
    return ds[j], ss[j]


print("— синтетика W = b·rho^4 (rings=10) —")
pts = _hexapolar_points(10)
rho2 = np.array([px * px + py * py for px, py in pts])
for b in (0.25, 1.0, 3.43):
    W = b * rho2 ** 2
    dls = d_ls_of(rho2, W)
    dst, S = argmax_strehl(W, rho2, dls)
    print(f"  b={b:5.2f}: d_ls={dls:+.5f}  d_Strehl={dst:+.5f}  "
          f"откл={100*(dst-dls)/abs(dls):+6.2f}%  S={S:.4f}")

print("\n— дублет (rings=10) —")
for aper in (12.0, 16.0, 20.0, 25.0):
    s = build_doublet(aper)
    parax = paraxial_trace(s)
    fnum = abs(parax.get('focal_length', 1)) / get_effective_aperture(s, default=aper)
    P = trace_wavefront_hexapolar(s, wl=0.58756, field_y=0.0, num_rings=10)
    r2 = np.array([px * px + py * py for px, py, _ in P])
    W = np.array([w for _, _, w in P])
    dls = d_ls_of(r2, W)
    dst, S = argmax_strehl(W, r2, dls)
    print(f"  aper={aper:4.1f}: F#={fnum:5.2f}  d_ls={dls:+.5f}  d_Strehl={dst:+.5f}  "
          f"откл={100*(dst-dls)/abs(dls):+6.2f}%  S={S:.4f}  W_edge={W[np.sqrt(r2)>0.99].mean():+.3f}")
