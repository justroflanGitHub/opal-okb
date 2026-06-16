"""Read GCTG properly — find glass names by cross-referencing with GCNG"""
import struct, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

opal = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

# GCTG.FIL — coefficients, 96 bytes per record, 227 records
# Format (from analysis of fil_reader_v2.py):
# [0:48] = 6 doubles (C0-C5)
# [48:56] = nd
# [56:64] = vd
# [64:72] = lambda_min
# [72:80] = lambda_max
# [80:96] = name? or more data

gctg = os.path.join(opal, 'GCTG.FIL')
with open(gctg, 'rb') as f:
    data = f.read()

rec_size = 96
n_recs = (len(data) - 8) // rec_size
print(f"GCTG: {n_recs} records")

# Check if offset [0:8] contains name or C0
for i in range(5):
    off = 8 + i * rec_size
    # Read first 8 bytes as string
    raw = data[off:off+8]
    hx = ' '.join(f'{b:02X}' for b in raw)
    v = struct.unpack_from('<d', data, off)[0]
    # Try cp866
    try:
        s = raw.decode('cp866', errors='replace').strip()
    except:
        s = '?'
    # Read 6 doubles
    c = [struct.unpack_from('<d', data, off + j*8)[0] for j in range(6)]
    nd = struct.unpack_from('<d', data, off + 48)[0]
    vd = struct.unpack_from('<d', data, off + 56)[0]
    print(f"  Rec {i}: C0={c[0]:.8f} C1={c[1]:.8f} nd={nd:.6f} vd={vd:.4f}")

# GCNG — what is the format? 164 bytes per record
gcng = os.path.join(opal, 'GCNG.FIL')
with open(gcng, 'rb') as f:
    gcng_data = f.read()

# Try rec_size = 37280/227 = 164.2 — not integer!
# Try 37280 / 232 = 160.7 — no
# Try (37280 - 8) / 227 = 164.1 — no
# Header is 0 bytes? Try (37280) / 227 = 164.3
# Check: 227 * 164 = 37228, 37280 - 37228 = 52 extra bytes
# Maybe rec_size = 164 with 52-byte header

# Actually, look at the GCON.FIL for structure hints
gcon = os.path.join(opal, 'GCON.FIL')
with open(gcon, 'rb') as f:
    gcon_data = f.read()

print(f"\nGCON.FIL: {len(gcon_data)} bytes")
# GCON likely contains record index/pointers
# (4264 - 8) / 227 = 18.7 — maybe 2 bytes per entry?
# 4264 / 227 ≈ 18.8
# (4264) / 226 = 18.9
# header: e9 00 02 00 03 00 04 00
print(f"Header: {gcon_data[:20].hex()}")
# Looks like: uint16 count=233 (0xe9), then indices 2,3,4...
count = struct.unpack_from('<H', gcon_data, 0)[0]
print(f"Count: {count}")

# So GCON is index: glass_number → something
# The actual names might be in GDOC.FIL
gdoc = os.path.join(opal, 'GDOC.FIL')
with open(gdoc, 'rb') as f:
    gdoc_data = f.read()

print(f"\nGDOC.FIL: {len(gdoc_data)} bytes")
print(f"Header: {gdoc_data[:20]}")
# hex: 2300202020834f43 = "#   " + cp866 "ОК"
# "#   ОК" — this looks like a document header

# Let's check: (1364 - 6) / 6 = ~226 records of 6 bytes each?
# Or (1364) / 227 = 6.0 — EXACTLY!
rec_size = 6
print(f"\nGDOC with rec_size=6:")
for i in range(10):
    off = i * rec_size
    raw = gdoc_data[off:off+6]
    hx = ' '.join(f'{b:02X}' for b in raw)
    try:
        s = raw.decode('cp866', errors='replace').strip()
    except:
        s = '?'
    print(f"  [{i}] {hx}  '{s}'")
