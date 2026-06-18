# -*- coding: utf-8 -*-
"""Compare OPJ data extracted from LBO with standalone OPJ."""
import struct
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LBO_PATH = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\LENS.LBO'
OPJ_PATH = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\1.OPJ'

with open(LBO_PATH, 'rb') as f:
    lbo = f.read()

with open(OPJ_PATH, 'rb') as f:
    opj_standalone = f.read()

# Extract record 0 OPJ data
rec0_start = 0
rec0_opj_size = struct.unpack_from('<I', lbo, 18)[0]
rec0_opj = lbo[22:22+rec0_opj_size]

print(f"Standalone 1.OPJ: {len(opj_standalone)} bytes")
print(f"LBO record 0 OPJ: {rec0_opj_size} bytes")

# Compare structure
print("\n=== Standalone 1.OPJ structure ===")
print(f"  version: 0x{struct.unpack_from('<H', opj_standalone, 0)[0]:04x}")
print(f"  bytes 2-11: {' '.join(f'{b:02x}' for b in opj_standalone[2:12])}")
name_st = opj_standalone[0x0C:0x34].decode('cp866', errors='replace').strip()
print(f"  name@0x0C: {repr(name_st)}")
ns_st = struct.unpack_from('<h', opj_standalone, 0x34)[0]
flags_st = struct.unpack_from('<h', opj_standalone, 0x36)[0]
nw_st = struct.unpack_from('<h', opj_standalone, 0x38)[0]
print(f"  num_surf@0x34: {ns_st}")
print(f"  flags@0x36: {flags_st}")
print(f"  num_wl@0x38: {nw_st}")

print("\n=== LBO record 0 OPJ structure ===")
print(f"  version: 0x{struct.unpack_from('<H', rec0_opj, 0)[0]:04x}")
print(f"  bytes 2-11: {' '.join(f'{b:02x}' for b in rec0_opj[2:12])}")
name_lbo = rec0_opj[0x0C:0x34].decode('cp866', errors='replace').strip()
print(f"  name@0x0C: {repr(name_lbo)}")
ns_lbo = struct.unpack_from('<h', rec0_opj, 0x34)[0]
flags_lbo = struct.unpack_from('<h', rec0_opj, 0x36)[0]
nw_lbo = struct.unpack_from('<h', rec0_opj, 0x38)[0]
print(f"  num_surf@0x34: {ns_lbo}")
print(f"  flags@0x36: {flags_lbo}")
print(f"  num_wl@0x38: {nw_lbo}")

# Check what bytes 0-11 look like in LBO OPJ
print("\n=== LBO OPJ bytes 0-11 detailed ===")
for i in range(0, 12, 2):
    v = struct.unpack_from('<H', rec0_opj, i)[0]
    print(f"  offset {i}: 0x{v:04x} = {v}")

# Check if the first 12 bytes in LBO OPJ differ from standalone
# Standalone: 11 01 00 00 00 94 00 00 00 00 00 00
# LBO:        d3 00 00 00 00 94 00 00 00 00 00 00
# Differs in first 2 bytes! 0x00d3 vs 0x0111
# But bytes 2-11 are the same pattern (00 94 00 00 00 00 00 00) for 1.OPJ
# For LBO record 0: d3 00 00 00 00 94 00 00 00 00 00 00

# So the version field is different, but the rest of the header is the same format
# This means the OPJ reader should work on LBO-extracted OPJ data!

# Let's try running load_opj on the extracted data
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from opj_reader import load_opj
import tempfile, os

# Write extracted OPJ to temp file and load it
tmpfd, tmppath = tempfile.mkstemp(suffix='.OPJ')
try:
    os.write(tmpfd, rec0_opj)
    os.close(tmpfd)
    sys_obj, info = load_opj(tmppath)
    print(f"\n=== Parsed LBO record 0 OPJ ===")
    print(f"  Name: {sys_obj.name}")
    print(f"  Surfaces: {len(sys_obj.surfaces)}")
    print(f"  Wavelengths: {len(sys_obj.wavelengths)}")
    for i, s in enumerate(sys_obj.surfaces):
        print(f"    S{i}: R={s.radius:.2f}, d={s.thickness:.2f}, glass='{s.glass}'")
    print(f"  Warnings: {info.get('warnings', [])}")
finally:
    os.unlink(tmppath)

# Now check all 116 records
print("\n=== All records summary ===")
pattern = b'\x0c\x00'
positions = []
idx = 0
while True:
    pos = lbo.find(pattern, idx)
    if pos == -1:
        break
    after = lbo[pos+2:pos+14]
    if b'.OPJ' in after or b'.opj' in after:
        positions.append(pos)
    idx = pos + 1

ok = 0
fail = 0
for i, p in enumerate(positions):
    next_p = positions[i+1] if i+1 < len(positions) else len(lbo)
    fname = lbo[p+2:p+14].decode('ascii', errors='replace').strip()
    opj_sz = struct.unpack_from('<I', lbo, p+18)[0]
    opj_data = lbo[p+22:p+22+opj_sz]
    
    tmpfd, tmppath = tempfile.mkstemp(suffix='.OPJ')
    try:
        os.write(tmpfd, opj_data)
        os.close(tmpfd)
        sys_obj, info = load_opj(tmppath)
        ns = len(sys_obj.surfaces)
        nw = len(sys_obj.wavelengths)
        ok += 1
        if i < 5 or i >= len(positions) - 3:
            print(f"  [{i:3d}] {fname}: {ns} surf, {nw} wl — {sys_obj.name[:40]}")
    except Exception as e:
        fail += 1
        print(f"  [{i:3d}] {fname}: FAIL — {e}")
    finally:
        os.unlink(tmppath)

print(f"\nTotal: {ok} OK, {fail} FAIL out of {len(positions)} records")
