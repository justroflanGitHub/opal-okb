"""Parse GCNG.FIL (233 records x 160 bytes) and map to glass names."""
import sys, io, struct, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# Parse GCNG.FIL
with open(os.path.join(base, 'GCNG.FIL'), 'rb') as f:
    gcng = f.read()

print(f"GCNG.FIL: {len(gcng)} bytes, 233 records x 160 bytes")

# Dump a few records to understand the 160-byte format
for rec_i in [0, 14, 131]:  # 0=first, 14=К8_nd match, 131=ТФ5_nd match
    rec = gcng[rec_i*160:(rec_i+1)*160]
    print(f"\nRecord {rec_i}:")
    doubles = []
    for j in range(20):  # 20 doubles = 160 bytes
        v = struct.unpack_from('<d', rec, j*8)[0]
        doubles.append(v)
    for j, v in enumerate(doubles):
        if abs(v) > 1e-10:
            print(f"  [{j*8:3d}] double[{j:2d}] = {v:.10g}")
    
    # Also check if there's text in the first bytes
    text_chunk = rec[:8]
    try:
        name = text_chunk.decode('cp866').strip('\x00 ')
        if name:
            print(f"  Text at 0: '{name}'")
    except:
        pass
    
    text_chunk = rec[:16]
    hex_str = text_chunk.hex(' ')
    print(f"  First 16 bytes hex: {hex_str}")

# Now parse GCTG with known format
print("\n\n=== GCTG proper parsing ===")
with open(os.path.join(base, 'GCTG.FIL'), 'rb') as f:
    gctg = f.read()

# GCTG: 227 records x 96 bytes
# Format: 12 doubles (offset 0, 8, 16, ..., 88)
# offset 0: small value (weight?)
# offset 8: small value  
# offset 16: C0
# offset 24: C1
# offset 32: C2
# offset 40: C3
# offset 48: C4
# offset 56: C5
# offset 64-88: additional data

# Let me parse ALL GCTG records and check their C0 values
gctg_entries = []
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    vals = [struct.unpack_from('<d', rec, j*8)[0] for j in range(12)]
    gctg_entries.append(vals)

# Sort by C0 to find the glass ordering
gctg_sorted = sorted(enumerate(gctg_entries), key=lambda x: x[1][2])
print("GCTG records sorted by C0 (first 30):")
for idx, vals in gctg_sorted[:30]:
    print(f"  rec={idx:3d} C0={vals[2]:.6f} C1={vals[3]:.6f}")

# Now try to identify К8: C0 should give n(0.58756) ≈ 1.5163
# Let me compute n(0.58756) for each record and find К8
print("\nComputing n(0.58756) to find К8:")
lam = 0.58756
lam0 = 0.167
L = 1.0/(lam**2 - lam0**2)

for idx, vals in enumerate(gctg_entries):
    C0, C1, C2, C3, C4, C5 = vals[2], vals[3], vals[4], vals[5], vals[6], vals[7]
    n = C0 + C1*lam**2 + C2*lam**4 + C3*L + C4*L**2 + C5*L**3
    if abs(n - 1.5163) < 0.001:
        print(f"  rec={idx:3d} n(d)={n:.6f} C0={C0:.6f} C1={C1:.6f}")

print("\nComputing n(0.58756) to find ТФ5:")
for idx, vals in enumerate(gctg_entries):
    C0, C1, C2, C3, C4, C5 = vals[2], vals[3], vals[4], vals[5], vals[6], vals[7]
    n = C0 + C1*lam**2 + C2*lam**4 + C3*L + C4*L**2 + C5*L**3
    if abs(n - 1.7550) < 0.001:
        print(f"  rec={idx:3d} n(d)={n:.6f} C0={C0:.6f} C1={C1:.6f}")
