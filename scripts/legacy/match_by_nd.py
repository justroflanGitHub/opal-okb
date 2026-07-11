"""Match GCNG to GCTG by nd values, then identify glasses using known ГОСТ data."""
import sys, io, struct, os, re, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

with open(os.path.join(base, 'GCNG.FIL'), 'rb') as f:
    gcng = f.read()
with open(os.path.join(base, 'GCTG.FIL'), 'rb') as f:
    gctg = f.read()
with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

# Known ГОСТ glasses with reference nd, vd
GOST_REFERENCE = {
    '\u041A8': (1.5163, 64.1),      # К8
    '\u0422\u04245': (1.7550, 27.5),  # ТФ5
    '\u0411\u041A10': (1.5688, 56.0), # БК10
    '\u0422\u041A16': (1.6126, 58.3), # ТК16
    '\u0424\u04241': (1.6126, 36.9),  # ТФ1 - actually let me look up real values
    '\u041B\u041A5': (1.4874, 70.0),  # ЛК5 - approx
}

# GCNG already has nd and vd
# Let me look at GCNG record structure more carefully
# GCNG record 14 (identified as К8 by nd=1.516302, vd=64.05)
rec14 = gcng[14*160:15*160]
d14 = [struct.unpack_from('<d', rec14, j*8)[0] for j in range(20)]
print("GCNG record 14 (К8):")
for j, v in enumerate(d14):
    if abs(v) > 1e-15:
        print(f"  [{j*8:3d}] d[{j:2d}] = {v:20.12g}")

# For К8: nd=1.516302 (d[2]), vd=64.054 (d[4])
# d[5]=-0.09264, d[6]=0.0001303, d[7]=-0.003827, d[8]=-0.582504, d[9]=63.872
# d[10]=-0.08796, d[11]=-0.01348, d[12]=-0.004670, d[13]=-0.52621

# Maybe d[5]-d[10] or similar are Herzberger-like coefficients?
# Let me check: for К8, the Herzberger formula should give nd=1.5163 at λ=0.58756

# Try: C0=d[5], C1=d[6], C2=d[7], C3=d[8], C4=d[11], C5=d[12]
def herzberger(C0, C1, C2, C3, C4, C5, lam, lam0=0.167):
    denom = lam**2 - lam0**2
    if abs(denom) < 1e-12: denom = 1e-12
    L = 1.0/denom
    return C0 + C1*lam**2 + C2*lam**4 + C3*L + C4*L**2 + C5*L**3

# GCNG has two sets of data per record - perhaps d/e line coefficients?
# d[2]=nd (d-line), d[3]=ne (e-line)?
# d[4]=vd (d-line), d[9]=ve (e-line)?
# d[5]-d[8]: first set of coefficients
# d[10]-d[13]: second set

# Let me test different coefficient combinations
lam_d = 0.58756
lam_e = 0.54607

print("\nTesting coefficient combinations for К8:")
for c0_idx in range(5, 14):
    for c1_idx in range(c0_idx+1, 14):
        # Try using d[c0_idx] as C0
        c0 = d14[c0_idx]
        if not (-2 < c0 < 3):
            continue

# Let me take a different approach. Let me look at GCTG which definitely has
# Herzberger coefficients, and match to GCNG by nd value.

# Extract all GCTG records
gctg_list = []
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    vals = [struct.unpack_from('<d', rec, j*8)[0] for j in range(12)]
    C0, C1, C2, C3, C4, C5 = vals[2], vals[3], vals[4], vals[5], vals[6], vals[7]
    nd = herzberger(C0, C1, C2, C3, C4, C5, lam_d)
    nF = herzberger(C0, C1, C2, C3, C4, C5, 0.48613)
    nC = herzberger(C0, C1, C2, C3, C4, C5, 0.65627)
    vd = (nd - 1)/(nF - nC) if abs(nF - nC) > 1e-10 else 0
    gctg_list.append({
        'rec': i, 'nd': nd, 'vd': vd,
        'C0': C0, 'C1': C1, 'C2': C2, 'C3': C3, 'C4': C4, 'C5': C5,
    })

# Extract all GCNG records
gcng_list = []
for i in range(233):
    rec = gcng[i*160:(i+1)*160]
    d = [struct.unpack_from('<d', rec, j*8)[0] for j in range(20)]
    gcng_list.append({'rec': i, 'nd': d[2], 'vd': d[4]})

# Match GCNG to GCTG by nd
matches = []
for g in gcng_list:
    if g['nd'] < 1.1:
        continue
    best_match = None
    best_diff = 999
    for t in gctg_list:
        diff = abs(g['nd'] - t['nd'])
        if diff < best_diff:
            best_diff = diff
            best_match = t
    if best_diff < 0.001:
        matches.append((g, best_match, best_diff))

print(f"\nMatched {len(matches)} GCNG -> GCTG records")
print("First 30 matches:")
for g, t, diff in matches[:30]:
    print(f"  GCNG[{g['rec']:3d}] nd={g['nd']:.6f} vd={g['vd']:.2f} <-> GCTG[{t['rec']:3d}] nd={t['nd']:.6f} vd={t['vd']:.2f} diff={diff:.8f}")

# Check К8
print("\n\nVerification:")
for g, t, diff in matches:
    if abs(g['nd'] - 1.5163) < 0.001:
        print(f"  К8 candidate: GCNG[{g['rec']}] nd={g['nd']:.6f} vd={g['vd']:.2f} <-> GCTG[{t['rec']}] diff={diff:.8f}")
        print(f"    GCTG: C0={t['C0']:.8f} C1={t['C1']:.8f} C2={t['C2']:.8f}")
        print(f"          C3={t['C3']:.8f} C4={t['C4']:.8f} C5={t['C5']:.8f}")
        break

# ТФ5
for g, t, diff in matches:
    if abs(g['nd'] - 1.7550) < 0.001:
        print(f"  ТФ5 candidate: GCNG[{g['rec']}] nd={g['nd']:.6f} vd={g['vd']:.2f} <-> GCTG[{t['rec']}] diff={diff:.8f}")
        break
