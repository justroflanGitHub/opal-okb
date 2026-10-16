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
z_start, z_pupil = _compute_ray_start(sysm, parax)
ref_center, ref_r = _reference_sphere(sysm, 0.0, parax)
chief_opl = _chief_reference_opl(sysm, wl, 0.0, z_start, z_pupil, ref_center, ref_r)
print('ref_center', ref_center, 'ref_r', ref_r, 'chief_opl', chief_opl)

from analysis.ray_tracing import get_effective_aperture
aperture = get_effective_aperture(sysm, default=10.0)
print('aperture used by hexapolar:', aperture)
for rho in (0.2, 0.5, 0.7, 0.8, 1.0):
    py = rho * aperture / 2
    ray = make_field_ray(sysm, 0.0, py, 0.0, z_start, z_pupil)
    res = trace_ray_through_system(sysm, ray, wl)
    if not res.success or not res.path:
        print(f'rho={rho}: FAIL {res.error}')
        continue
    d = _air_exit_direction(sysm, res, wl)
    opl = _opl_to_reference_sphere(res.opl, res.path[-1], d, ref_center, ref_r)
    W = (opl - chief_opl) if opl is not None else None
    print(f'rho={rho}: y_pupil={py:6.2f} opl={res.opl:9.3f} to_sphere={opl!r} W={W!r}')
