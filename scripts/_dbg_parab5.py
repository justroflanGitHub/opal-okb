import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from domain.models import OpticalSystem, Surface
from domain.calculations import paraxial_trace
from analysis.aberrations import (_reference_sphere, _compute_ray_start,
                                  _chief_reference_opl, _air_exit_direction,
                                  _opl_to_reference_sphere)
from analysis.ray_tracing import trace_ray_through_system, make_field_ray
from utils.optics_utils import get_primary_wl

s = Surface(radius=-200.0, thickness=-100.0, semi_diameter=10.0, conic_constant=-1.0, is_reflective=True)
sysm = OpticalSystem(name='parab', surfaces=[s])
wl = get_primary_wl(sysm)
parax = paraxial_trace(sysm)
print('parax:', {k: round(v, 4) for k, v in parax.items() if isinstance(v, (int, float))})
z_start, z_pupil = _compute_ray_start(sysm, parax)
ref_center, ref_r = _reference_sphere(sysm, 0.0, parax)
print('z_start', z_start, 'z_pupil', z_pupil)
print('ref_center', ref_center, 'ref_r', ref_r)

chief_opl = _chief_reference_opl(sysm, wl, 0.0, z_start, z_pupil, ref_center, ref_r)
print('chief_opl', chief_opl)

aperture = 10.0
ray = make_field_ray(sysm, 0.0, 0.2 * aperture / 2, 0.0, z_start, z_pupil)
print('ray:', ray)
res = trace_ray_through_system(sysm, ray, wl)
print('res.opl', res.opl, 'success', res.success)
for p in res.path:
    print('  ', [round(c, 4) for c in p])
d = _air_exit_direction(sysm, res, wl)
print('exit dir', d)
opl = _opl_to_reference_sphere(res.opl, res.path[-1], d, ref_center, ref_r)
print('opl_to_sphere', opl)
if opl is not None:
    print('W мм:', opl - chief_opl)
