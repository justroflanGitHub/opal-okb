# -*- coding: utf-8 -*-
"""Analyze LBO file format."""
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

print(f"LENS.LBO: {len(lbo)} bytes")
print(f"1.OPJ: {len(opj_standalone)} bytes")

# Find all record markers
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

print(f"Records found: {len(positions)}")

# Analyze record 0 in detail
pos0 = positions[0]
pos1 = positions[1]
rec_size = pos1 - pos0
print(f"\n=== Record 0: offset {pos0}, size {rec_size} ===")

# Header: marker (2) + filename (12) = 14 bytes
filename = lbo[pos0+2:pos0+14].decode('ascii', errors='replace').strip()
print(f"Filename: {filename}")

# Bytes after filename
header = lbo[pos0+14:pos0+26]
print(f"Header after filename (12 bytes): {' '.join(f'{b:02x}' for b in header)}")

# Theory 1: OPJ data starts at offset 14 (right after marker+filename)
opj_theory1 = lbo[pos0+14:pos1]
print(f"\nTheory 1: OPJ starts at offset+14, size={len(opj_theory1)}")
print(f"  First bytes: {' '.join(f'{b:02x}' for b in opj_theory1[:16])}")
if len(opj_theory1) > 0x34:
    name1 = opj_theory1[0x0C:0x34].decode('cp866', errors='replace')
    print(f"  Name at OPJ+0x0C: {repr(name1.strip())}")
    ns1 = struct.unpack_from('<h', opj_theory1, 0x34)[0]
    print(f"  num_surf at OPJ+0x34: {ns1}")

# Theory 2: There's a 4-byte field, then 4-byte OPJ size, then OPJ data
# Bytes 14-17: 8d 61 63 1a (could be date/checksum/random)
# Bytes 18-21: 2e 02 00 00 = 558
# Bytes 22+: OPJ data
opj_size_field = struct.unpack_from('<I', lbo, pos0+18)[0]
print(f"\nTheory 2: uint32 at offset+18 = {opj_size_field} (= OPJ size?)")
opj_theory2 = lbo[pos0+22:pos0+22+opj_size_field]
print(f"  OPJ data: offset+22, size={len(opj_theory2)}")
print(f"  First bytes: {' '.join(f'{b:02x}' for b in opj_theory2[:16])}")
if len(opj_theory2) > 0x34:
    name2 = opj_theory2[0x0C:0x34].decode('cp866', errors='replace')
    print(f"  Name at OPJ+0x0C: {repr(name2.strip())}")
    ns2 = struct.unpack_from('<h', opj_theory2, 0x34)[0]
    print(f"  num_surf at OPJ+0x34: {ns2}")

# Theory 3: bytes 14-17 = uint32 (some field), bytes 18-21 = description_size, bytes 22-25 = opj_size
desc_size_field = struct.unpack_from('<I', lbo, pos0+22)[0]
print(f"\nTheory 3: uint32 at offset+22 = {desc_size_field}")

# Let me try: offset 14-17 could be timestamp/random, 18-21 = OPJ data length
# Then OPJ data starts at offset 22
# Check: 22 + 558 = 580 = rec_size! ✓

# Now check: does the OPJ data at offset 22 make sense?
# If OPJ starts at offset 22, OPJ offset 0x0C = absolute offset 34
# But the cp866 text we saw starts at offset 26...
# Unless OPJ has a shorter header in LBO format

# Actually, let me check if there's a description BEFORE the OPJ data
# Maybe: marker(2) + filename(12) + header(4) + opj_size(4) + description(N) + opj_data(opj_size)
# Where N varies... but then records wouldn't have fixed header

# Let me check if 558 matches for all records
print("\n=== Checking OPJ size field for all records ===")
for i in range(min(10, len(positions))):
    p = positions[i]
    next_p = positions[i+1] if i+1 < len(positions) else len(lbo)
    rec_sz = next_p - p
    fname = lbo[p+2:p+14].decode('ascii', errors='replace').strip()
    sz_field = struct.unpack_from('<I', lbo, p+18)[0]
    extra = lbo[p+14:p+18]
    extra_hex = ' '.join(f'{b:02x}' for b in extra)
    # Check if sz_field + 22 = rec_sz
    diff = rec_sz - sz_field
    print(f"  {fname}: rec_size={rec_sz}, opj_size_field={sz_field}, diff={diff}, extra={extra_hex}")

# Also compare OPJ structures
print("\n=== Comparing 1.OPJ with LBO record OPJ ===")
print(f"1.OPJ first 40 bytes:")
for i in range(0, 40, 8):
    print(f"  {' '.join(f'{b:02x}' for b in opj_standalone[i:i+8])}")

# Let me try one more thing: maybe the 4 bytes at offset 14-17 are part of OPJ
# and the OPJ has a different version in LBO
# Let's see if treating offset 14 as OPJ start gives valid num_surf/num_wl
print("\n=== Treating LBO offset+14 as OPJ start (record 0) ===")
for i in range(min(5, len(positions))):
    p = positions[i]
    next_p = positions[i+1] if i+1 < len(positions) else len(lbo)
    fname = lbo[p+2:p+14].decode('ascii', errors='replace').strip()
    opj_data = lbo[p+14:next_p]
    
    ver = struct.unpack_from('<H', opj_data, 0)[0]
    name = opj_data[0x0C:0x34].decode('cp866', errors='replace').strip()
    ns = struct.unpack_from('<h', opj_data, 0x34)[0]
    nw = struct.unpack_from('<h', opj_data, 0x38)[0]
    print(f"  {fname}: ver=0x{ver:04x}, name={repr(name[:30])}, num_surf={ns}, num_wl={nw}")
