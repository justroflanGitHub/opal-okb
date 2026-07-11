import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []

def log(msg):
    with open('diag_out.txt', 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

# Clear output
with open('diag_out.txt', 'w') as f:
    pass

import glass_catalog as gc
log(f"After import gc: ВОЗДУХ = {gc.compute_refractive_index('ВОЗДУХ', 0.58756)}")
log(f"After import gc: К8 = {gc.compute_refractive_index('К8', 0.58756)}")
log(f"After import gc: AIR = {gc.compute_refractive_index('AIR', 0.58756)}")

import importlib

# Import modules one by one and check
test_modules = ['optics_engine', 'ray_tracing', 'aberrations', 'optimizer', 'opj_reader', 'fil_reader_v2', 'visualization', 'analysis_gui', 'main']

for mod_name in test_modules:
    try:
        m = importlib.import_module(mod_name)
        log(f"import {mod_name}: OK")
    except Exception as e:
        log(f"import {mod_name}: FAIL - {e}")
    
    # Restore stdout
    try:
        sys.stdout = sys.__stdout__
    except:
        sys.stdout = open(1, 'w', encoding='utf-8', closefd=False)
    
    log(f"  ВОЗДУХ = {gc.compute_refractive_index('ВОЗДУХ', 0.58756)}")
    log(f"  К8 = {gc.compute_refractive_index('К8', 0.58756)}")
    log(f"  AIR = {gc.compute_refractive_index('AIR', 0.58756)}")
    log(f"  gc.GLASS_CATALOG keys: {list(gc.GLASS_CATALOG.keys())[:5]}")
    log(f"  'К8' in gc.GLASS_CATALOG: {'К8' in gc.GLASS_CATALOG}")

# Now test multi-wavelength
log("\n=== Multi-wavelength test ===")
oe = importlib.import_module('optics_engine')
rt = importlib.import_module('ray_tracing')
ab = importlib.import_module('aberrations')
sys.stdout = sys.__stdout__

sys_ab = oe.OpticalSystem()
sys_ab.aperture_value = 20.0
sys_ab.wavelengths = [oe.Wavelength(0.58756)]
sys_ab.field_points = [oe.FieldPoint(0.0)]
sys_ab.surfaces = [
    oe.Surface(radius=100.0, thickness=5.0, glass="К8", semi_diameter=12),
    oe.Surface(radius=-100.0, thickness=95.0, glass="", semi_diameter=12),
]

for wl in [0.48613, 0.54607, 0.58756, 0.65627]:
    n = gc.compute_refractive_index('К8', wl)
    log(f"  n(К8, {wl}) = {n:.6f}")

fan_d = ab.trace_aberration_fan(sys_ab, 0.58756, num_rays=10)
fan_F = ab.trace_aberration_fan(sys_ab, 0.48613, num_rays=10)
fan_C = ab.trace_aberration_fan(sys_ab, 0.65627, num_rays=10)

dy_d = [abs(r['dy']) for r in fan_d if r['success'] and r['dy'] is not None]
dy_F = [abs(r['dy']) for r in fan_F if r['success'] and r['dy'] is not None]
dy_C = [abs(r['dy']) for r in fan_C if r['success'] and r['dy'] is not None]

log(f"  Max dy (d): {max(dy_d) if dy_d else 'none'}")
log(f"  Max dy (F): {max(dy_F) if dy_F else 'none'}")
log(f"  Max dy (C): {max(dy_C) if dy_C else 'none'}")
