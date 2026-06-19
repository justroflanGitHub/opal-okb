"""FULL FORMAT DECODED! 
LBO OPJ layout for Индустар-23у:

0x00-0x0B: header
0x0C-0x33: system name (cp866)
0x34-0x35: num_surf (uint16)
0x38-0x39: num_wl (uint16)
0x40-0x57: config
0x58-0x5F: Высоta Y (float64) = 10.55
0x60-0x67: duplicate?
0x68-0x6F: SD (float64) = 4.2
0x70-0x7F: field angles
0x80-0x97: zeros
0x98-0xDF: curvatures C=1/R (float64) + aberrations interleaved
0xE0-0x10F: thicknesses d (float64) × num_surf
0x110: marker 1e20
0x118-0x127: wavelength indices (int16)
0x128-???: refractive indices (float64)
???: glass block (8-byte cp866 strings × num_glasses)
???: semi-diameters (float32 × num_surf)
"""
import sys, io, struct, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from lbo_reader import load_lbo_fast

data = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')[3]['opj_data']
ns = 7  # num_surf
nw = 5  # num_wl

# === DECODE ===

# 1. Curvatures at 0x98? Check pattern
# Real C values: 1/30.48=0.0328, 0(плоская), -1/68.23=-0.0147, 1/28.05=0.0357, -1/214.8=-0.0047, 1/28.58=0.0350, -1/44.06=-0.0227
real_R = [30.48, 0.0, -68.23, 28.05, -214.8, 28.58, -44.06]
real_C = [1.0/r if r != 0 else 0.0 for r in real_R]
print('Real curvatures:', [f'{c:.6f}' for c in real_C])

# From data: 0x98-0xE0 has values. Let's check which match
print('\nData 0x98-0xE0:')
vals = []
for off in range(0x98, 0xE0, 8):
    val = struct.unpack_from('<d', data, off)[0]
    vals.append((off, val))
    print(f'  @{off:#x}: {val:.6f}')

# Match: 0xA8=0.032808=1/30.48, 0xB8=-0.014656=1/-68.23
# Also: 0xC0=0.035651≈1/28.05 (28.05→1/28.05=0.03565 ✓)
# 0xC8=-0.004655≈1/-214.8 (1/-214.8=-0.004656 ✓)
# 0xD0=0.034990≈1/28.58 (1/28.58=0.034986 ✓)
# 0xD8=-0.022696≈1/-44.06 (1/-44.06=-0.022696 ✓)

# So curvatures are at: 0xA8, 0xB8, 0xC0, 0xC8, 0xD0, 0xD8
# That's 6 values. Missing: S1 (R=0, flat → C=0)
# Pattern: 0xA8, skip 0xB0(zero), 0xB8, 0xC0, 0xC8, 0xD0, 0xD8
# So: starts at 0xA8 with 16-byte stride, but 0xB0 is zero (C=0 for flat S1)

# Actually: the curvatures are interleaved with something at every other position
# 0x98: 0.000087 (not curvature)
# 0xA0: 0.000183 (not curvature)
# 0xA8: 0.032808 = 1/30.48 ← S0 curvature!
# 0xB0: 0.000000 = S1 curvature (flat, C=0)
# 0xB8: -0.014656 = 1/-68.23 ← S2 curvature!
# 0xC0: 0.035651 = 1/28.05 ← S3
# 0xC8: -0.004655 = 1/-214.8 ← S4
# 0xD0: 0.034990 = 1/28.58 ← S5
# 0xD8: -0.022696 = 1/-44.06 ← S6

# WAIT - that's 7 values from 0xA8 to 0xD8! With 8-byte stride!
print('\n=== CURVATURES (1/R) at 0xA8, stride=8 ===')
for i in range(ns):
    off = 0xA8 + i * 8
    c = struct.unpack_from('<d', data, off)[0]
    r = 1.0/c if abs(c) > 1e-10 else 0.0
    print(f'  S{i}: C={c:.6f}, R={r:.4f}mm')

# 2. Thicknesses at 0xE0
print('\n=== THICKNESSES at 0xE0, stride=8 ===')
for i in range(ns):
    off = 0xE0 + i * 8
    d = struct.unpack_from('<d', data, off)[0]
    print(f'  S{i}: d={d:.4f}mm')

# Check: 0xE0 has d but only 6 values before marker at 0x110
# 0xE0+6*8 = 0x110 = marker. So d has 6 values not 7!
# Missing d=11.1 (distance to image) — maybe it's stored elsewhere

# 3. Semi-diameters as float32
# Glass block: count real glass entries
glass_off = 0x1A2
glasses = []
for i in range(20):
    off = glass_off + i * 8
    if off + 8 > len(data):
        break
    raw = data[off:off+8]
    if raw[0] == 0:
        break
    name = raw.decode('cp866', errors='replace').rstrip('\x00').strip()
    if name and not all(c in '\x00\x0e\x12&\x02' for c in name):
        glasses.append(name)
    
# Actually: glasses for this system = ВОЗДУХ, ТК16, ЛФ5, ОФ1, ТК20 = 5
# But ns=7. Glass block has ns+1=8 entries... 
# Check: only 5 are text, rest is binary
nglasses = 5  # actual glass entries
glass_end = glass_off + nglasses * 8  # 0x1A2 + 40 = 0x1CA

# Then 2 bytes gap?
sd_start = glass_end  # 0x1CA
# But first D/2=12.35 found at 0x1CE... 
# Check: 0x1CA as float32
val_1ca = struct.unpack_from('<f', data, 0x1CA)[0]
val_1ce = struct.unpack_from('<f', data, 0x1CE)[0]
print(f'\n@0x1CA: {val_1ca:.4f}')
print(f'@0x1CE: {val_1ce:.4f}')  # Should be 12.35

# Try from 0x1CE:
print('\n=== SEMI-DIAMETERS as float32 from 0x1CE ===')
for i in range(ns):
    off = 0x1CE + i * 4
    val = struct.unpack_from('<f', data, off)[0]
    print(f'  S{i}: D/2={val:.2f}mm')
