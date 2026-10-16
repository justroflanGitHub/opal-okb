import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from domain.models import OpticalSystem, Surface, Wavelength
from domain.calculations import paraxial_trace, compute_z_positions

# линзовые: дублет-подобная и одиночная линза — сравнить z_pos[-1] vs last+bfd
def probe(name, surf):
    sysm = OpticalSystem(name=name, surfaces=surf)
    sysm.wavelengths = [Wavelength(0.5876)]
    parax = paraxial_trace(sysm)
    z = compute_z_positions(sysm)
    last = z[-2] if len(z) > 1 else z[-1]
    bfd = parax.get('back_focal_distance', 0)
    print(f'{name}: z_pos[-1]={z[-1]:8.4f}  last+bfd={last + bfd:8.4f}  equal={abs(z[-1] - (last + bfd)) < 1e-9}')

lens = [Surface(radius=100.0, thickness=5.0, glass='BK8', semi_diameter=10.0),
        Surface(radius=-100.0, thickness=95.0, glass='', semi_diameter=10.0)]
probe('singlet', lens)

dub = [Surface(radius=50.0, thickness=4.0, glass='K8', semi_diameter=8.0),
       Surface(radius=-80.0, thickness=2.0, glass='F1', semi_diameter=8.0),
       Surface(radius=-200.0, thickness=90.0, glass='', semi_diameter=8.0)]
probe('doublet', dub)

mir = [Surface(radius=-200.0, thickness=-100.0, semi_diameter=10.0, conic_constant=-1.0, is_reflective=True)]
probe('parab-mirror', mir)

cas = [Surface(radius=-400.0, thickness=-150.0, semi_diameter=40.0, is_reflective=True),
       Surface(radius=-140.0, thickness=175.0, semi_diameter=5.0, is_reflective=True),
       Surface(radius=0.0, thickness=25.0, semi_diameter=25.0)]
probe('cassegrain', cas)
