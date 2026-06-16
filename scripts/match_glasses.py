"""Properly extract glass names from GCON and match to GCNG data."""
import sys, io, struct, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# Parse GCON.FIL for glass names
with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

# Parse GCNG.FIL for glass data (nd, vd, coefficients)
with open(os.path.join(base, 'GCNG.FIL'), 'rb') as f:
    gcng = f.read()

# Parse GCTG.FIL for Herzberger coefficients
with open(os.path.join(base, 'GCTG.FIL'), 'rb') as f:
    gctg = f.read()

# Extract glass names from GCON
# Names are 8-byte entries starting at offset 652 (after header strings)
# But we need to figure out exactly where each glass name starts

# Strategy: decode the entire name section as cp866 text, then split into names
# The name section starts at offset 602 (after index table + padding)
name_section = con[602:4198]
name_text = name_section.decode('cp866')
print(f"Name section length: {len(name_text)} chars")
print(f"Name section text:\n{name_text[:200]}")

# The names seem to be variable-width but separated by spaces
# Let me split by whitespace and filter
name_tokens = name_text.split()
print(f"\nName tokens ({len(name_tokens)}):")
for i, t in enumerate(name_tokens[:50]):
    print(f"  [{i}] {t}")
print("  ...")
for i, t in enumerate(name_tokens[-20:], len(name_tokens)-20):
    print(f"  [{i}] {t}")

# Now let me check: are there 233 names?
print(f"\nTotal name tokens: {len(name_tokens)}")

# Actually the names include group labels like ВОЗДУХ, ФИЗЛ, etc.
# Let me filter for only glass-name-like tokens (Cyrillic+digits)
glass_pattern = re.compile(r'^[А-ЯЁ]{1,4}\d{1,4}$')
glass_names = [(i, t) for i, t in enumerate(name_tokens) if glass_pattern.match(t)]
print(f"\nGlass-name tokens: {len(glass_names)}")
for i, (idx, name) in enumerate(glass_names[:30]):
    print(f"  [{i}] token_idx={idx} name={name}")

# Hmm, this still doesn't give us 233 names. Let me try a completely different approach.
# Instead of GCON, let me use the GCTG coefficients + known ГОСТ data.

# Better idea: extract ALL GCTG coefficients, compute nd and vd,
# then match to a known reference table.

# First, let me understand the GCTG record format by examining multiple records
print("\n\n=== GCTG format analysis ===")
print("Checking record layout by looking at which offsets have C0-like values...")

# For each record, find which double offset has the C0-like value (1.3-2.2)
c0_offsets = {}
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    for j in range(12):
        v = struct.unpack_from('<d', rec, j*8)[0]
        if 1.2 < v < 2.5:
            c0_offsets.setdefault(j, 0)
            c0_offsets[j] += 1

print(f"C0-like value count per double offset: {c0_offsets}")
# This should tell us which offset contains C0

# Now let me check the format more carefully by looking at К8
# К8 has nd=1.5163. Let me find which GCTG record is К8 by matching computed nd
lam = 0.58756
lam0 = 0.167
L = 1.0/(lam**2 - lam0**2)

# Also compute at F and C lines for vd
lamF = 0.48613
lamC = 0.65627
LF = 1.0/(lamF**2 - lam0**2)
LC = 1.0/(lamC**2 - lam0**2)

def herzberger(C0, C1, C2, C3, C4, C5, lam, lam0=0.167):
    denom = lam**2 - lam0**2
    if abs(denom) < 1e-12: denom = 1e-12
    L = 1.0/denom
    return C0 + C1*lam**2 + C2*lam**4 + C3*L + C4*L**2 + C5*L**3

# Extract all GCTG records
gctg_entries = []
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    # Based on analysis: C0 at offset 16 (double[2])
    vals = [struct.unpack_from('<d', rec, j*8)[0] for j in range(12)]
    C0, C1, C2, C3, C4, C5 = vals[2], vals[3], vals[4], vals[5], vals[6], vals[7]
    
    nd = herzberger(C0, C1, C2, C3, C4, C5, 0.58756)
    nF = herzberger(C0, C1, C2, C3, C4, C5, 0.48613)
    nC = herzberger(C0, C1, C2, C3, C4, C5, 0.65627)
    
    vd = (nd - 1) / (nF - nC) if abs(nF - nC) > 1e-10 else 0
    
    gctg_entries.append({
        'rec': i, 'nd': nd, 'vd': vd,
        'C0': C0, 'C1': C1, 'C2': C2, 'C3': C3, 'C4': C4, 'C5': C5,
        'vals': vals
    })

# Find К8 (nd≈1.5163, vd≈64.1)
print("\nLooking for К8 (nd≈1.5163, vd≈64.1):")
for e in gctg_entries:
    if abs(e['nd'] - 1.5163) < 0.001 and abs(e['vd'] - 64.1) < 1:
        print(f"  rec={e['rec']} nd={e['nd']:.6f} vd={e['vd']:.2f} C0={e['C0']:.6f}")

# Find ТФ5 (nd≈1.7550, vd≈27.5)
print("\nLooking for ТФ5 (nd≈1.7550, vd≈27.5):")
for e in gctg_entries:
    if abs(e['nd'] - 1.7550) < 0.001 and abs(e['vd'] - 27.5) < 1:
        print(f"  rec={e['rec']} nd={e['nd']:.6f} vd={e['vd']:.2f} C0={e['C0']:.6f}")

# Now let me also check: what's at offsets 8-15 in GCTG records?
# vals[0] and vals[1] 
print("\nFirst few GCTG records vals[0] and vals[1]:")
for i in range(10):
    e = gctg_entries[i]
    print(f"  rec={i} vals[0]={e['vals'][0]:.10g} vals[1]={e['vals'][1]:.10g} nd={e['nd']:.4f} vd={e['vd']:.1f}")
