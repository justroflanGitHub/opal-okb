"""Parse GCON.FIL correctly by understanding its full structure."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

# First value might be count
count = struct.unpack_from('<H', con, 0)[0]
print(f"Count (first value): {count}")

# Read 16-bit values
vals = []
for i in range(0, len(con), 2):
    v = struct.unpack_from('<H', con, i)[0]
    vals.append(v)

# Find where values stop being "normal" (small indices)
# The name section should have byte values that decode to Cyrillic text
print(f"\nValues around transition:")
for i in range(290, 330):
    off = i * 2
    if off < len(con):
        v = vals[i]
        # Also show as bytes
        b0, b1 = con[off], con[off+1] if off+1 < len(con) else 0
        try:
            txt = con[off:off+2].decode('cp866')
        except:
            txt = '??'
        print(f"  val[{i}] @ {off}: {v:5d} (0x{v:04x}) bytes={b0:02x}{b1:02x} cp866='{txt}'")

# Let's try: 234 entries (1 count + 233 indices) = 468 bytes
# Names start at offset 468?
print(f"\nAt offset 468:")
for i in range(468, min(468 + 160, len(con)), 8):
    chunk = con[i:i+8]
    try:
        name = chunk.decode('cp866').strip('\x00 ')
    except:
        name = '?'
    print(f"  {i}: {chunk.hex(' ')}  '{name}'")

# Hmm, let me look at the structure differently
# The first 300 bytes are all 16-bit indices
# Let me look at bytes 300-700 for a transition
print(f"\nLooking for transition (bytes 300-700):")
for i in range(300, min(700, len(con)), 8):
    chunk = con[i:i+8]
    hex_str = chunk.hex(' ')
    try:
        name = chunk.decode('cp866').strip('\x00 ')
    except:
        name = '?'
    # Check if any byte is in Cyrillic range
    has_cyr = any(0x80 <= b <= 0x9F or 0xA0 <= b <= 0xAF for b in chunk)
    marker = " <-- cyr" if has_cyr else ""
    print(f"  {i}: {hex_str}  '{name}'{marker}")
