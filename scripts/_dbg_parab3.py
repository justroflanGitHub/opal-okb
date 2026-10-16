import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from domain.models import OpticalSystem, Surface, SurfaceType
from analysis.ray_tracing import intersect_aspheric, Ray

s = Surface(radius=200.0, thickness=-100.0, semi_diameter=10.0, conic_constant=-1.0, is_reflective=True)
ray = Ray(x=0.0, y=5.0, z=-1000.0, k=0.0, l=0.0, m=1.0)
hit = intersect_aspheric(ray, 200.0, 0.0, conic_k=-1.0)
print('intersect_aspheric:', hit)
# аналитика параболы: z = y^2/400 = 0.0625
# и вторая проверка: где вызывается intersect_aspheric в основном цикле?
import inspect, analysis.ray_tracing as rt
src = inspect.getsource(rt.trace_ray_through_system)
i = src.find('intersect_aspheric')
print('---call-site---')
print(src[max(0, i-700):i+300])
