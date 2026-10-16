import sys
sys.stdout.reconfigure(encoding='utf-8')
from domain.models import OpticalSystem, Surface, SurfaceType
from analysis.aberrations import trace_wavefront_hexapolar
import collections

s = Surface(radius=200.0, thickness=-100.0, semi_diameter=10.0, conic_constant=-1.0, is_reflective=True)
sysm = OpticalSystem(name='parab', surfaces=[s])
W = trace_wavefront_hexapolar(sysm, wl=550.0, num_rings=4)
by_rho = collections.defaultdict(list)
for x, y, w in W:
    r = (x * x + y * y) ** 0.5
    by_rho[round(r, 1)].append(w)
for rho in sorted(by_rho):
    ws = by_rho[rho]
    print(f'rho={rho:.2f}: mean={sum(ws) / len(ws):+.6f} n={len(ws)} vals={[f"{w:+.4f}" for w in ws[:3]]}')
