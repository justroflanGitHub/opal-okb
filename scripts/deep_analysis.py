"""Deep analysis: find glass names and match to GCTG data."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# GCTG.FIL: 22368 bytes = 227 * 96 (pure binary coefficients, no names)
# GCON.FIL: 4264 bytes - some kind of index
# GDAT.FIL: 18640 bytes - starts with "11/11/82" date strings
# GLAS.FIL: 422 bytes - wavelength definitions

# Let me check GDAT more carefully - it has date strings + data
with open(os.path.join(base, 'GDAT.FIL'), 'rb') as f:
    gdat = f.read()

print(f"GDAT.FIL: {len(gdat)} bytes")
# Record pattern: starts with "11/11/82" at offset 0 and 80
# 18640 / 80 = 233 records? Let's check
record_size = 80
n_recs = len(gdat) // record_size
print(f"GDAT records (80 bytes): {n_recs}")
# Check for date pattern at each 80-byte boundary
for i in range(5):
    rec = gdat[i*record_size:(i+1)*record_size]
    date = rec[:8]
    print(f"  Record {i}: date={date}, hex={rec[:16].hex(' ')}")
    # After date (8 bytes), there should be data
    doubles = []
    for j in range(9):  # 9 doubles = 72 bytes
        off = 8 + j * 8
        if off + 8 <= len(rec):
            v = struct.unpack_from('<d', rec, off)[0]
            doubles.append(v)
    print(f"    doubles: {[f'{d:.6g}' for d in doubles]}")

# Now check GCNG.FIL (37280 bytes) - "new catalog"
with open(os.path.join(base, 'GCNG.FIL'), 'rb') as f:
    gcng = f.read()

print(f"\nGCNG.FIL: {len(gcng)} bytes")
# Try different record sizes
for rs in [80, 96, 104, 112, 160, 176]:
    if len(gcng) % rs == 0:
        n = len(gcng) // rs
        print(f"  {rs} bytes -> {n} records")
        # Check first record
        rec = gcng[:rs]
        doubles = []
        for j in range(rs // 8):
            v = struct.unpack_from('<d', rec, j * 8)[0]
            if 0.1 < abs(v) < 100:
                doubles.append((j, v))
        print(f"    Non-trivial doubles: {[(j, f'{v:.6g}') for j, v in doubles[:15]]}")
