import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
opal = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

# GCON.FIL: 4264 bytes, header e9 00 = count 233
# Then pairs of uint16? Let's see
gcon = os.path.join(opal, 'GCON.FIL')
with open(gcon, 'rb') as f:
    data = f.read()

print(f"GCON.FIL: {len(data)} bytes")
count = struct.unpack_from('<H', data, 0)[0]
print(f"Count: {count}")

# Read uint16 values
vals = []
for i in range(min(count, 200)):
    v = struct.unpack_from('<H', data, 2 + i*2)[0]
    vals.append(v)

print(f"Values: {vals[:30]}")
print(f"Unique: {len(set(vals))}")

# These look like glass CODES (e.g., 2,3,4,5... 65001...)
# Glass names in OPAL use numeric codes: e.g. К8 = code 8, ТФ5 = code 105?
# Let me check: the existing glass_catalog.py has numeric codes

# GLAS.FIL might have the mapping!
glas = os.path.join(opal, 'GLAS.FIL')
with open(glas, 'rb') as f:
    glas_data = f.read()

print(f"\nGLAS.FIL: {len(glas_data)} bytes")
print(f"Header: {glas_data[:20].hex()}")
# 2a00692068204727 = "*. h G'"
# This is small (422 bytes) — probably index/mapping

# Let's just use glass_catalog_full.py which already has 889 glasses from .FIL
# The GCTG coefficients ARE correct — they just need names from the CON files

# Alternative approach: use the existing glass_catalog_full.py
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from glass_catalog_full import GlassCatalogFull

cat = GlassCatalogFull()
print(f"\nglass_catalog_full: {len(cat._catalog)} glasses loaded")

# List some GOST glasses
gost_glasses = [(k, v) for k, v in cat._catalog.items() if any(c in k for c in 'КБТФЛСО')]
print(f"GOST-like names: {len(gost_glasses)}")
for name, entry in sorted(gost_glasses)[:20]:
    print(f"  {name}: nd={entry.get('nd',0):.4f} vd={entry.get('vd',0):.2f}")
