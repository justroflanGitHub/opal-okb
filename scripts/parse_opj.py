import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\1.OPJ', 'rb') as f:
    data = f.read()

print(f'File size: {len(data)} bytes = {len(data)/8:.1f} doubles')
print()

# Header as 16-bit ints
h1, h2 = struct.unpack_from('<HH', data, 0)
print(f'Header: {h1}, {h2}')

# Read as doubles
print()
print('=== Doubles ===')
for i in range(0, min(len(data), 300), 8):
    val = struct.unpack_from('<d', data, i)[0]
    if abs(val) > 0.001 and abs(val) < 1e10:
        print(f'  [{i:3d}] = {val:20.10f}')

# Find strings
air = 'ВОЗДУХ'.encode('cp866')
idx = data.find(air)
if idx >= 0:
    print(f'\nString found at offset {idx}')
    # Read surrounding context as cp866
    chunk = data[idx:idx+40]
    print(f'  decoded: {chunk.decode("cp866", errors="replace")}')

# Try reading a larger OPJ
print()
for fname in ['HELIOS8.OPJ', 'GTIE00.OPJ', 'YBBS77_.OPJ', 'DEMON.OPJ']:
    import os
    path = os.path.join(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb', fname)
    if os.path.exists(path):
        with open(path, 'rb') as f2:
            d2 = f2.read()
        print(f'{fname}: {len(d2)} bytes')
        # Show header
        h = struct.unpack_from('<HH', d2, 0)
        print(f'  Header: {h}')
        # First doubles
        vals = []
        for j in range(4, min(len(d2), 100), 8):
            v = struct.unpack_from('<d', d2, j)[0]
            if abs(v) > 0.001 and abs(v) < 1e10:
                vals.append(f'{v:.6f}')
        print(f'  Doubles: {", ".join(vals[:10])}')
        # Find strings
        for enc_name in ['cp866', 'cp1251']:
            try:
                # Find readable text
                text = d2.decode(enc_name, errors='ignore')
                readable = [c for c in text if c.isprintable() and c not in '\x00']
                runs = []
                current = ''
                for c in text:
                    if c.isprintable() and ord(c) > 32:
                        current += c
                    else:
                        if len(current) > 3:
                            runs.append(current)
                        current = ''
                if runs:
                    print(f'  Strings ({enc_name}): {runs[:15]}')
            except:
                pass
        print()
