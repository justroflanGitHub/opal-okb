"""Test paraxial trace for Индустар-23у."""
import sys; sys.path.insert(0, '.')
from decode_lbo_opj import decode_lbo_opj
from lbo_reader import load_lbo_fast
from optics_engine import paraxial_trace

lens = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
s = decode_lbo_opj(lens[3]['opj_data'])  # Индустар-23у
print(f'System: {s.name}')
print(f'Surfaces: {len(s.surfaces)}')
for i, surf in enumerate(s.surfaces):
    no = bool(getattr(surf, 'n_override', None))
    print(f'  [{i}] R={surf.radius:.4f} d={surf.thickness:.4f} glass={surf.glass} n_override={no}')
print(f'Wavelengths: {[w.value for w in s.wavelengths]}')
print(f'Stop surface: {s.stop_surface}')
print(f'Aperture: type={s.aperture_type} value={s.aperture_value}')
print()

r = paraxial_trace(s)
print('Current paraxial results:')
print(f'  f          = {r.get("focal_length", 0):.4f}')
print(f'  f_prime    = {r.get("effective_focal_length", 0):.4f}')
print(f'  sF         = {r.get("sF", 0):.4f}')
print(f'  sF_prime   = {r.get("sF_prime", 0):.4f}')
print(f'  sH         = {r.get("sH", 0):.4f}')
print(f'  sH_prime   = {r.get("sH_prime", 0):.4f}')
print(f'  L          = {r.get("L", 0):.4f}')
print()
print('Expected values (from OPAL-PC):')
print('  F          = -109.6976')
print('  F_prime    = 109.6976')
print('  sF         = -95.5619')
print('  sF_prime   = 96.8032')
print('  sH         = 14.1357')
print('  sH_prime   = -12.8944')
print('  L          = 124.10')
