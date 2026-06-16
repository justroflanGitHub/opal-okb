"""Compact .OPJ format analysis - no stdout wrapper"""
import struct, os

opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
out_path = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\hex_report.txt'

files = ['HELIOS8.OPJ', '1.OPJ', 'D2.OPJ', 'DEMON.OPJ', '222.OPJ']
lines = []

for fname in files:
    path = os.path.join(opal_dir, fname)
    with open(path, 'rb') as f:
        data = f.read()
    
    h1, h2 = struct.unpack_from('<HH', data, 0)
    lines.append(f'\n{"="*60}')
    lines.append(f'{fname}: {len(data)} bytes, h1={h1}, h2={h2}')
    
    # Doubles
    lines.append(f'\nDoubles:')
    for i in range(0, len(data)-7, 8):
        v = struct.unpack_from('<d', data, i)[0]
        if v != v or abs(v) > 1e15:
            continue
        label = ''
        if 0.3 < v < 3.0: label = f'  WL? {v*1000:.1f}nm'
        elif 3 < abs(v) < 5000: label = '  R?'
        elif 0.001 < abs(v) < 200: label = '  d?'
        lines.append(f'  [{i:4d}] = {v:20.10f}{label}')
    
    # Strings
    strings = []
    i = 4
    while i < len(data):
        if data[i] >= 0x80:
            start = i
            while i < len(data) and data[i] >= 0x20 and data[i] < 0xFF:
                i += 1
            raw = data[start:i]
            if len(raw) >= 2:
                try:
                    s = raw.decode('cp866').strip()
                    strings.append((start, s))
                except: pass
        else:
            i += 1
    
    if strings:
        lines.append(f'\nStrings:')
        for off, s in strings[:10]:
            lines.append(f'  @{off:4d}: "{s}"')
    
    # Hex first 200
    lines.append(f'\nHex:')
    for i in range(0, min(200, len(data)), 16):
        chunk = data[i:i+16]
        hx = ' '.join(f'{b:02X}' for b in chunk)
        lines.append(f'{i:04X}: {hx}')

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('Done')
