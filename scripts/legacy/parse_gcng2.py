"""Understand GCNG format and extract all glasses with names."""
import sys, io, struct, os, re, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

with open(os.path.join(base, 'GCNG.FIL'), 'rb') as f:
    gcng = f.read()

with open(os.path.join(base, 'GCTG.FIL'), 'rb') as f:
    gctg = f.read()

# GCNG: 233 records x 160 bytes
# Let me dump first 5 records completely
print("=== GCNG Records 0-4 ===")
for rec_i in range(5):
    rec = gcng[rec_i*160:(rec_i+1)*160]
    print(f"\nRecord {rec_i}:")
    for j in range(20):
        v = struct.unpack_from('<d', rec, j*8)[0]
        if abs(v) > 1e-15:
            print(f"  [{j*8:3d}] d[{j:2d}] = {v:20.12g}")

# Now let me understand: GCNG double[2] = nd, double[4] = vd?
# Record 0: d[2]=1.332986, d[4]=55.3166 - this looks like quartz or some light glass
# Record 14: d[2]=1.516302, d[4]=64.0536 - К8!

# Let me check: what glass has nd=1.332986, vd=55.3?
# This could be FK (fluorite crown) or quartz glass
# Actually SiO2 (fused silica) has nd≈1.4585, not 1.333
# Could this be water?? nd of water ≈ 1.333!

# Let me extract nd, vd for all GCNG records
print("\n\n=== All GCNG nd, vd values ===")
gcng_entries = []
for i in range(233):
    rec = gcng[i*160:(i+1)*160]
    d = [struct.unpack_from('<d', rec, j*8)[0] for j in range(20)]
    nd = d[2]
    vd = d[4]
    gcng_entries.append({'rec': i, 'nd': nd, 'vd': vd, 'd': d})

# Print sorted by nd
gcng_sorted = sorted(gcng_entries, key=lambda x: x['nd'])
for e in gcng_sorted[:20]:
    print(f"  rec={e['rec']:3d} nd={e['nd']:.6f} vd={e['vd']:.2f}")
print("  ...")
for e in gcng_sorted[-10:]:
    print(f"  rec={e['rec']:3d} nd={e['nd']:.6f} vd={e['vd']:.2f}")

# Now the GCON.FIL has glass names. Let me extract them properly.
# From earlier analysis: names at 8-byte intervals starting around offset 650
# Let me try to extract them by scanning for 8-byte blocks

with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

# The name section starts after the index section + padding
# Let me find where the first recognizable glass name starts
# First glass name: ЛК1 at offset ~652 (0-indexed)

# Actually let me try to read the whole GCON structure:
# Offset 0: count (16-bit) = 233
# Offset 2: 233 x 16-bit indices = 466 bytes
# Offset 468: ??? (padding?)
# After padding: name table

# Let me check: 468 bytes of index data, then what?
print(f"\n=== GCON structure analysis ===")
count = struct.unpack_from('<H', con, 0)[0]
print(f"Count: {count}")

# Read 233 indices
indices = []
for i in range(count):
    v = struct.unpack_from('<H', con, 2 + i*2)[0]
    indices.append(v)

print(f"Indices: {indices[:20]}...")

# After indices: offset 2 + 233*2 = 468
# Check what's at 468
print(f"\nAt offset 468: {con[468:476].hex(' ')}")

# Let me look at offset 468 to 600
print(f"\nOffset 468-600:")
for i in range(468, 600, 8):
    chunk = con[i:i+8]
    try:
        name = chunk.decode('cp866').strip('\x00 ')
    except:
        name = '?'
    print(f"  {i}: {chunk.hex(' ')}  '{name}'")

# Then name section
print(f"\nOffset 600-900 (name section):")
for i in range(600, min(900, len(con)), 8):
    chunk = con[i:i+8]
    try:
        name = chunk.decode('cp866').strip('\x00 ')
    except:
        name = '?'
    print(f"  {i}: {chunk.hex(' ')}  '{name}'")
