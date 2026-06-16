"""Match GCNG records to GCTG records via nd values, then create full catalog."""
import sys, io, struct, os, re, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# Parse GCNG for nd, vd
with open(os.path.join(base, 'GCNG.FIL'), 'rb') as f:
    gcng = f.read()

# Parse GCTG for Herzberger coefficients  
with open(os.path.join(base, 'GCTG.FIL'), 'rb') as f:
    gctg = f.read()

# Parse GCON for glass names
with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

# Extract glass names from GCON
name_section = con[602:4198]
name_text = name_section.decode('cp866')
glass_pattern = re.compile(r'^[А-ЯЁ]{1,4}\d{1,4}$')
all_tokens = name_text.split()
glass_names = [t for t in all_tokens if glass_pattern.match(t)]
print(f"Glass names from GCON: {len(glass_names)}")

# Extract GCNG nd, vd
gcng_entries = []
for i in range(233):
    rec = gcng[i*160:(i+1)*160]
    d = [struct.unpack_from('<d', rec, j*8)[0] for j in range(20)]
    gcng_entries.append({
        'rec': i,
        'nd': d[2],
        'nd_alt': d[3],  # maybe ne?
        'vd': d[4],
        'vd_alt': d[9],
    })

# Extract GCTG coefficients and compute nd
def herzberger(C0, C1, C2, C3, C4, C5, lam, lam0=0.167):
    denom = lam**2 - lam0**2
    if abs(denom) < 1e-12: denom = 1e-12
    L = 1.0/denom
    return C0 + C1*lam**2 + C2*lam**4 + C3*L + C4*L**2 + C5*L**3

gctg_entries = []
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    vals = [struct.unpack_from('<d', rec, j*8)[0] for j in range(12)]
    C0, C1, C2, C3, C4, C5 = vals[2], vals[3], vals[4], vals[5], vals[6], vals[7]
    
    nd = herzberger(C0, C1, C2, C3, C4, C5, 0.58756)
    gctg_entries.append({
        'rec': i, 'nd_computed': nd,
        'C0': C0, 'C1': C1, 'C2': C2, 'C3': C3, 'C4': C4, 'C5': C5,
    })

# Now, the GCNG records should be in the same order as the glass names from GCON
# Let me verify: pair GCNG[i] with glass_names[i]
# GCNG has 233 records, glass_names has 205

# The GCNG records with nd > 0 should correspond to the glass names
valid_gcng = [(i, e) for i, e in enumerate(gcng_entries) if e['nd'] > 1.0]
print(f"\nValid GCNG records (nd > 1.0): {len(valid_gcng)}")

# Print first 30 valid entries with their nd
print("\nValid GCNG entries:")
for i, (rec_i, e) in enumerate(valid_gcng[:30]):
    name = glass_names[i] if i < len(glass_names) else "???"
    print(f"  [{i}] gcng_rec={rec_i} nd={e['nd']:.6f} vd={e['vd']:.2f} name={name}")

# Verify К8
# К8 is at position 21 in glass_names (ЛК1=0, ЛК3=1, ..., К8=21)
k8_idx = glass_names.index('\u041A8')  # К8
print(f"\nК8 index: {k8_idx}")
print(f"  GCNG[{k8_idx}]: nd={valid_gcng[k8_idx][1]['nd']:.6f} vd={valid_gcng[k8_idx][1]['vd']:.2f}")

# Verify ТФ5
tf5_name = '\u0422\u04245'  # ТФ5
if tf5_name in glass_names:
    tf5_idx = glass_names.index(tf5_name)
    print(f"\nТФ5 index: {tf5_idx}")
    print(f"  GCNG[{tf5_idx}]: nd={valid_gcng[tf5_idx][1]['nd']:.6f} vd={valid_gcng[tf5_idx][1]['vd']:.2f}")
