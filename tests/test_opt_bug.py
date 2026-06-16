import sys
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from optics_engine import create_demo_system
from aberrations import compute_spot_diagram, compute_rms_spot

s = create_demo_system()
print(f'System: {s.name}')
print(f'Field points: {[(fp.y, fp.weight) for fp in s.field_points]}')
print(f'Wavelengths: {[(wl.value, wl.weight) for wl in s.wavelengths]}')

for wl in s.wavelengths:
    for fp in s.field_points:
        spots = compute_spot_diagram(s, wl=wl.value, num_rays=20, field_y=fp.y)
        rms = compute_rms_spot(spots)
        print(f'  wl={wl.value:.4f}, field={fp.y:.1f}: spots={len(spots)}, rms={rms:.4f}')
