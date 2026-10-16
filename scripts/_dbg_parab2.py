import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from domain.models import OpticalSystem, Surface
from analysis.ray_tracing import trace_ray_through_system, Ray

s = Surface(radius=200.0, thickness=-100.0, semi_diameter=10.0, conic_constant=-1.0, is_reflective=True)
sysm = OpticalSystem(name='parab', surfaces=[s])

for hy in (0.5, 5.0, 9.9):
    ray = Ray(x=0.0, y=hy, z=-1000.0, k=0.0, l=0.0, m=1.0)
    res = trace_ray_through_system(sysm, ray, wl=0.55)
    print(f'y={hy}: ok={res.success} err={res.error}')
    for i, p in enumerate(res.path):
        print(f'  path[{i}]=({p[0]:8.4f},{p[1]:9.4f},{p[2]:9.4f})')
