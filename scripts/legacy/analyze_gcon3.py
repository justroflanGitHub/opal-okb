"""Parse GCON.FIL properly to extract glass names and match to GCTG."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

# GCON format: 
# First section: 16-bit indices (2 bytes each)
# The end of file (offset ~4052) has zeros then a character table
# Name section starts around offset 625

# Find the name section start
# Look for the pattern of 8-byte padded names
# Names are at fixed 8-byte intervals

# Let's find the exact start by looking for the first recognizable glass name
# "ЛК1" in cp866 is 8b 8a 31
# Found at offset 655. But before that, there are other strings starting from 625

# Let's dump from 620 onwards
name_start = 620
print("Hex dump of name section:")
for i in range(name_start, min(name_start + 200, len(con)), 8):
    chunk = con[i:i+8]
    hex_str = ' '.join(f'{chunk[j]:02x}' for j in range(len(chunk)))
    try:
        name = chunk.decode('cp866').strip('\x00 ')
    except:
        name = '?'
    print(f"  {i:4d}: {hex_str}  '{name}'")

# Actually let me look more carefully
# From the earlier analysis:
# offset 625: ЛКЕДР.МС (8 bytes)
# offset 633: another name?
# offset 641: another name?

# Let me check what's before 625
print("\nBefore name section:")
for i in range(600, 632, 8):
    chunk = con[i:i+8]
    hex_str = ' '.join(f'{chunk[j]:02x}' for j in range(len(chunk)))
    try:
        name = chunk.decode('cp866').strip('\x00 ')
    except:
        name = '?'
    print(f"  {i:4d}: {hex_str}  '{name}'")

# So the structure of GCON might be:
# - Header/index section (16-bit LE values)
# - Name table (8 bytes per name)
# - Character set table at the end

# The 16-bit indices might point to positions in the name table
# Let's count: 4264 total bytes
# If names start at offset 625 and each is 8 bytes:
# (4052 - 625) / 8 = 428.375 -> not exact

# Let me try a different approach - find all 8-byte aligned name-like strings
names = []
for i in range(0, len(con) - 8, 8):
    chunk = con[i:i+8]
    if chunk == b'\x00' * 8:
        continue
    # Check if it looks like a padded name (Cyrillic/digits/spaces)
    try:
        s = chunk.decode('cp866')
        stripped = s.strip('\x00 ')
        if stripped and len(stripped) >= 2:
            # Check if it contains at least one cp866 Cyrillic char (0x80-0x9F, 0xA0-0xAF, 0xE0-0xEF)
            has_cyrillic = any(0x80 <= b <= 0x9F or 0xA0 <= b <= 0xAF or 0xE0 <= b <= 0xEF for b in chunk)
            has_digit = any(0x30 <= b <= 0x39 for b in chunk)
            if has_cyrillic and has_digit:
                names.append((i, stripped))
    except:
        pass

print(f"\nFound {len(names)} glass-like names")
for off, name in names[:30]:
    print(f"  {off:4d}: '{name}'")
if len(names) > 30:
    print(f"  ... and {len(names)-30} more")

# Now let me also understand the index table
# Read the first section as 16-bit LE values
indices = []
for i in range(0, len(con) - 1, 2):
    val = struct.unpack_from('<H', con, i)[0]
    if val == 0 and i > 600:
        break
    indices.append(val)
    
print(f"\nFirst 50 indices: {indices[:50]}")
print(f"Total indices: {len(indices)}")
