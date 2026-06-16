import struct, os

opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
out = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\hex_report.txt'
lines = []

for fname in ['HELIOS8.OPJ', '1.OPJ', 'D2.OPJ', 'DEMON.OPJ', '222.OPJ']:
    path = os.path.join(opal_dir, fname)
    with open(path, 'rb') as f:
        data = f.read()
    
    h1, h2 = struct.unpack_from('<HH', data, 0)
    lines.append(f'\n{"="*60}')
    lines.append(f'{fname}: {len(data)} bytes, h1={h1}, h2={h2}')
    
    # Doubles only
    lines.append('Doubles:')
    for i in range(0, len(data)-7, 8):
        v = struct.unpack_from('<d', data, i)[0]
        if v != v or abs(v) > 1e15:
            continue
        label = ''
        if 0.3 < v < 3.0: label = ' WL'
        elif 3 < abs(v) < 5000: label = ' R'
        elif 0.001 < abs(v) < 200: label = ' d'
        lines.append(f'  [{i:4d}]={v:16.8f}{label}')

    # Hex first 128
    lines.append('Hex128:')
    for i in range(0, min(128, len(data)), 16):
        chunk = data[i:i+16]
        hx = ' '.join(f'{b:02X}' for b in chunk)
        lines.append(f'{i:04X}: {hx}')

with open(out, 'w') as f:
    f.write('\n'.join(lines))
print('DONE')
