"""Analyze GCTG.FIL binary structure."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

filepath = r'extracted\opal_okb\GCTG.FIL'
with open(filepath, 'rb') as f:
    data = f.read()

print(f"File size: {len(data)} bytes")
print(f"227 records * 96 = {227*96}")
print(f"Remainder: {len(data) % 96}")

# Check for a header
print(f"\nFirst 100 bytes (hex):")
print(data[:100].hex(' '))

# Check if there's a recognizable string somewhere
print(f"\nFirst 200 bytes (repr):")
print(repr(data[:200]))

# Try reading as text
print(f"\nFirst 200 bytes (cp866):")
try:
    print(data[:200].decode('cp866'))
except:
    print("(failed)")

# Search for К8 signature
# К8 in cp866 would be 0x8A 0x38 (or similar)
# In cp1251: 0xCA 0x38
import re
for encoding in ['cp866', 'cp1251', 'utf-8', 'latin-1']:
    try:
        k8_bytes = 'К8'.encode(encoding)
        pos = data.find(k8_bytes)
        if pos >= 0:
            print(f"\nFound 'К8' at offset {pos} in {encoding}")
            print(f"  Context (hex): {data[pos-16:pos+32].hex(' ')}")
    except:
        pass

# Also search for plain "K8"
k8_pos = data.find(b'K8')
if k8_pos >= 0:
    print(f"\nFound 'K8' at offset {k8_pos}")
    print(f"  Context: {data[k8_pos-16:k8_pos+32].hex(' ')}")
