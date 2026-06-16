"""Analyze GCON.FIL structure - find name table."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

with open(os.path.join(base, 'GCON.FIL'), 'rb') as f:
    con = f.read()

print(f"GCON.FIL: {len(con)} bytes")

# Print hex dump of last 500 bytes
print("\nLast 500 bytes hex dump:")
start = max(0, len(con) - 500)
for i in range(start, len(con), 16):
    hex_str = ' '.join(f'{con[i+j]:02x}' for j in range(min(16, len(con)-i)))
    ascii_str = ''
    for j in range(min(16, len(con)-i)):
        b = con[i+j]
        if 0x20 <= b < 0x7f:
            ascii_str += chr(b)
        elif 0x80 <= b:
            try:
                ascii_str += bytes([b]).decode('cp866')
            except:
                ascii_str += '.'
        else:
            ascii_str += '.'
    print(f"  {i:4d}: {hex_str:<48s} {ascii_str}")

# Try to find where the index table ends and names begin
# Look for the transition from 16-bit values to text
print("\nSearching for name section...")
# Glass names are typically uppercase Cyrillic + digits
# In cp866, Cyrillic uppercase is 0x80-0x9F, lowercase 0xA0-0xAF, 0xE0-0xEF
for i in range(len(con) - 10):
    # Look for patterns like "К8" in cp866 = 0x8A 0x38
    # or "ЛК" = 0x8B 0x8A
    if con[i:i+2] == b'\x8b\x8a' or con[i:i+2] == b'\x8a\x38':
        print(f"  Found at offset {i}: {con[i:i+8].hex(' ')}")
        try:
            s = con[i:i+8].decode('cp866')
            print(f"    cp866: '{s}'")
        except:
            pass
