import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from domain.models import OpticalSystem, Surface
from analysis.aberrations import trace_wavefront_hexapolar
from analysis.ray_tracing import trace_ray_through_system, Ray
import collections

# ВОГНУТЫЙ параболоид: R=-200 (конвенция порта), F=100, D=20 (ideal on-axis)
s = Surface(radius=-200.0, thickness=-100.0, semi_diameter=10.0, conic_constant=-1.0, is_reflective=True)
sysm = OpticalSystem(name='parab', surfaces=[s])

print('--- лучи (параллельный пучок) ---')
for hy in (0.5, 5.0, 7.0, 9.9):
    ray = Ray(x=0.0, y=hy, z=-1000.0, k=0.0, l=0.0, m=1.0)
    res = trace_ray_through_system(sysm, ray, wl=0.55)
    last = res.path[-1] if res.path else None
    print(f'y={hy:4.1f} ok={res.success} err={res.error} last=({last[0]:8.4f},{last[1]:9.4f},{last[2]:9.4f})')

print('--- W hexapolar ---')
W = trace_wavefront_hexapolar(sysm, wl=0.55, num_rings=4)
by_rho = collections.defaultdict(list)
for x, y, w in W:
    r = (x * x + y * y) ** 0.5
    by_rho[round(r, 1)].append(w)
for rho in sorted(by_rho):
    ws = by_rho[rho]
    print(f'rho={rho:.2f}: mean={sum(ws) / len(ws):+.6f} (дл. волн: {sum(ws)/len(ws)/0.00055:+.4f}) n={len(ws)}')
