"""Find glass names and map them to GCTG entries by position."""
import sys, io, struct, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# GCON.FIL has glass names embedded. Let me extract them properly.
# The names are at 8-byte intervals starting somewhere around offset 600-660.
# Let me scan ALL 8-byte aligned positions for valid glass names.

with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

# Find all positions where we have a pattern like [spaces/cyrillic][cyrillic][digits][spaces]
glass_names = []
for i in range(0, len(con) - 8, 1):
    chunk = con[i:i+8]
    try:
        s = chunk.decode('cp866')
        stripped = s.strip('\x00 ')
        if not stripped or len(stripped) < 2:
            continue
    except:
        continue
    
    # Check for glass name pattern: Cyrillic letters followed by optional Cyrillic + digits
    # Valid: К8, БК10, ТК21, ЛК107, ФК14, ТФ5, СТК3, etc.
    if re.match(r'^[А-ЯЁ]{1,4}\d{1,4}$', stripped):
        glass_names.append((i, stripped))

print(f"Found {len(glass_names)} glass names at specific offsets")
for off, name in glass_names[:30]:
    print(f"  {off}: '{name}'")
print("  ...")
for off, name in glass_names[-10:]:
    print(f"  {off}: '{name}'")

# Now let's figure out the mapping to GCTG records
# GCON might be sorted by the glass code (index in first section)
# GCTG has 227 records, presumably in the same order

# Read GCTG
with open(os.path.join(base, 'GCTG.FIL'), 'rb') as f:
    gctg = f.read()

# Extract all 227 GCTG records
gctg_records = []
for i in range(227):
    rec = gctg[i*96:(i+1)*96]
    # Extract doubles starting at offset 16
    C0 = struct.unpack_from('<d', rec, 16)[0]
    nd = struct.unpack_from('<d', rec, 64)[0]
    vd = struct.unpack_from('<d', rec, 72)[0]
    gctg_records.append({
        'index': i,
        'C0': C0,
        'nd': nd,
        'vd': vd,
    })

print(f"\nFirst 5 GCTG records:")
for r in gctg_records[:5]:
    print(f"  [{r['index']}] C0={r['C0']:.6f} nd={r['nd']:.4f} vd={r['vd']:.2f}")

# The glass names from GCON should map to GCTG records by position
# But first I need to understand the ordering

# Check if the 16-bit indices in GCON point to positions in GCTG
# First GCON value = 233 (count), then indices
# Let me read the indices
con_indices = []
for i in range(1, len(con)//2):
    v = struct.unpack_from('<H', con, i*2)[0]
    if v == 0 and i > 250:  # Stop at first zero after initial data
        break
    con_indices.append(v)

print(f"\nGCON indices: {len(con_indices)} values")
print(f"  First 30: {con_indices[:30]}")
print(f"  Last 30: {con_indices[-30:]}")

# These indices are like: 2, 3, 4, 5, 6, 7, 101, 102, 103, 104, 301, 302, ...
# Pattern: XYY where X=group (0=ЛК, 1=К, 2=БК, 3=КФ?, 4=ТК, 5=БФ?, ...)
# And YY = number within group
# 2=ЛК2?, 3=К3?, ...

# Actually let me check: if glass_names[0] = ЛК1, and con_indices[0] = 2,
# then index 2 maps to name offset for ЛК1?
# glass_names offsets: let's see the first few
# The first glass name found was at some offset...

# Let me try a direct positional mapping:
# GCON has 233 indices -> 233 GCTG records (227 + 6 extra?)
# Or maybe the names are in the same order as GCTG records

# Let me just try: name[i] corresponds to gctg_records[i]
# First, extract ALL names in order from GCON

# Get unique glass names sorted by offset
seen = set()
ordered_names = []
for off, name in glass_names:
    if name not in seen:
        seen.add(name)
        ordered_names.append(name)

print(f"\nOrdered glass names ({len(ordered_names)} unique):")
for i, name in enumerate(ordered_names[:30]):
    print(f"  [{i}] {name}")
if len(ordered_names) > 30:
    print(f"  ... ({len(ordered_names)} total)")

# Test: does ordered_names[0] (ЛК1) match gctg_records[0] (nd=?)?
print(f"\nMatching test:")
for i in range(min(5, len(ordered_names), len(gctg_records))):
    print(f"  [{i}] name={ordered_names[i]}, nd={gctg_records[i]['nd']:.4f}, vd={gctg_records[i]['vd']:.2f}")
