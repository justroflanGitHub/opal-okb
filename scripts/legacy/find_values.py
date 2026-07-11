"""Find known glass values in GCTG and GCNG to understand format."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# Known values to search for:
# К8: nd=1.5163, vd=64.1
# ТФ5: nd=1.7550, vd=27.5
# ЛК1: nd≈1.438, vd≈69

targets = {
    'К8_nd': 1.5163,
    'К8_vd': 64.1,
    'ТФ5_nd': 1.7550,
    'ТФ5_vd': 27.5,
}

def find_double_in_file(data, target, tolerance=0.001):
    """Find approximate double value in binary data."""
    target_bytes = struct.pack('<d', target)
    matches = []
    for i in range(0, len(data) - 7, 8):
        val = struct.unpack_from('<d', data, i)[0]
        if abs(val - target) < tolerance:
            matches.append((i, val))
    return matches

# Search in GCTG
print("=== GCTG.FIL ===")
with open(os.path.join(base, 'GCTG.FIL'), 'rb') as f:
    gctg = f.read()

for name, target in targets.items():
    matches = find_double_in_file(gctg, target)
    print(f"  {name} ({target}): {len(matches)} matches")
    for off, val in matches[:5]:
        rec_idx = off // 96
        rec_off = off % 96
        print(f"    offset={off} (rec={rec_idx}, within_rec={rec_off}) val={val:.6f}")

# Search in GCNG  
print("\n=== GCNG.FIL ===")
with open(os.path.join(base, 'GCNG.FIL'), 'rb') as f:
    gcng = f.read()

for name, target in targets.items():
    matches = find_double_in_file(gcng, target)
    print(f"  {name} ({target}): {len(matches)} matches")
    for off, val in matches[:5]:
        rec_idx = off // 160
        rec_off = off % 160
        print(f"    offset={off} (rec={rec_idx}, within_rec={rec_off}) val={val:.6f}")

# Also search in GDAT
print("\n=== GDAT.FIL ===")
with open(os.path.join(base, 'GDAT.FIL'), 'rb') as f:
    gdat = f.read()

for name, target in targets.items():
    matches = find_double_in_file(gdat, target)
    print(f"  {name} ({target}): {len(matches)} matches")
    for off, val in matches[:5]:
        rec_idx = off // 80
        rec_off = off % 80
        print(f"    offset={off} (rec={rec_idx}, within_rec={rec_off}) val={val:.6f}")

# Dump a GCTG record that should be К8 (search for C0 ≈ 1.509)
print("\n=== GCTG: Looking for К8 by C0 ≈ 1.509 ===")
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    # Try doubles at every 8-byte position
    vals = []
    for j in range(12):
        v = struct.unpack_from('<d', rec, j*8)[0]
        vals.append(v)
    # К8 should have C0 ≈ 1.509
    if 1.50 < vals[2] < 1.52:  # offset 16 = C0 in fil_reader_v2
        print(f"  Record {i}: vals = {[f'{v:.6f}' for v in vals]}")
        print(f"    As offset 0 double: {vals[0]:.10g}")
        print(f"    Full rec hex: {rec.hex(' ')}")
        break

# Dump a GCTG record for ТФ5 (C0 ≈ 1.741)
print("\n=== GCTG: Looking for ТФ5 by C0 ≈ 1.74 ===")
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    vals = [struct.unpack_from('<d', rec, j*8)[0] for j in range(12)]
    if 1.73 < vals[2] < 1.76:
        print(f"  Record {i}: vals = {[f'{v:.6f}' for v in vals]}")
        break
