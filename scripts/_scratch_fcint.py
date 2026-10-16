"""Проба 10: интеграция focus_criteria на дублете."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
from analysis import focus_criteria as fc


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


for aper in (16.0, 20.0):
    s = build_doublet(aper)
    t0 = time.time()
    res = fc.all_focus_criteria(s)
    dt = time.time() - t0
    print(f"=== дублет aper={aper} ({dt:.1f}s) ===")
    print(f"  min_rms_W  = {res['min_rms_wavefront_mm']:+.5f} мм  (σ={res['rms_wavefront_at_min']:.4f}λ)")
    print(f"  max_strehl = {res['max_strehl_mm']:+.5f} мм  (S={res['strehl_at_max']:.4f})")
    print(f"  min_spot   = {res['min_spot_rms_mm']:+.5f} мм  (RMS={res['spot_rms_mm_at_min']*1e3:.2f} мкм)")
    print(f"  zone_best  = {res['zone_best_mm']:+.5f} мм")
    print(f"  eqf        = {res['eqf_mm']:+.5f} мм  converged={res['eqf']['converged']} "
          f"res={res['eqf']['residual']:.2e} rms_in={res['eqf']['rms_in']:.4f} rms_out={res['eqf']['rms_out']:.4f}")
    print(f"  best_opal  = {res['best_opal_mm']:+.5f} мм ({res['best_opal_source']})")
    m = res['meta']
    print(f"  meta: F#={m['f_number']:.3f} z_G={m['z_G_mm']:.3f} точек={m['num_points']} "
          f"мм/волну={m['mm_per_edge_wave']*1e3:.1f} мкм")
    a, b = sorted((res['min_rms_wavefront_mm'], res['zone_best_mm']))
    e = res['eqf_mm']
    print(f"  EQF между min_rms и zone? {a <= e <= b}")
