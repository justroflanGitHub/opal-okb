"""Parse GCON.FIL to get glass names and map them to GCTG entries."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# Parse GCON.FIL
with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con_data = f.read()

print(f"GCON.FIL: {len(con_data)} bytes")

# GCON appears to be: array of 16-bit indices, then names
# Let's try to decode the whole thing in cp866
text = con_data.decode('cp866', errors='replace')
print(f"Full text (first 500 chars):\n{text[:500]}")
print(f"\nFull text (last 200 chars):\n{text[-200:]}")

# Let's look at it differently - find the text portion
# GLAS.FIL had text names like "i h G'g F'F e d D C'C r A' t"
# GCON seems to have glass names
# Let's look for patterns

# Try to find all glass names by scanning for recognizable patterns
import re
# Glass names are typically: К8, БК10, ТК16, etc.
# In cp866: Cyrillic letters followed by digits
all_names = re.findall(r'[А-Яа-яЁё]{1,4}\d{1,3}', text)
print(f"\nGlass names found: {all_names[:50]}")
print(f"Total names: {len(all_names)}")

# Also check if there's a clear structure
# GCON size: 4264 bytes = 2 bytes * 2132 words? No...
# 4264 / 2 = 2132 entries (16-bit)
# Or maybe it has a different format

# Let's try to understand the format by looking at hex
print(f"\nGCON hex (first 300 bytes):")
for i in range(0, min(300, len(con_data)), 16):
    hex_str = ' '.join(f'{con_data[i+j]:02x}' for j in range(min(16, len(con_data)-i)))
    ascii_str = ''
    for j in range(min(16, len(con_data)-i)):
        b = con_data[i+j]
        if 0x20 <= b < 0x7f:
            ascii_str += chr(b)
        elif 0x80 <= b < 0xf0:
            try:
                ascii_str += bytes([b]).decode('cp866')
            except:
                ascii_str += '.'
        else:
            ascii_str += '.'
    print(f"  {i:4d}: {hex_str:<48s} {ascii_str}")
