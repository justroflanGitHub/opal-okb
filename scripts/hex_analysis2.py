"""Compact .OPJ format analysis"""
import struct, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

def compact_dump(data, max_bytes=300):
    lines = []
    for i in range(0, min(len(data), max_bytes), 16):
        chunk = data[i:i+16]
        hx = ' '.join(f'{b:02X}' for b in chunk)
        lines.append(f'{i:04X}: {hx}')
    if len(data) > max_bytes:
        lines.append(f'... ({len(data)-max_bytes} more bytes)')
    return '\n'.join(lines)

files = ['HELIOS8.OPJ', '1.OPJ', 'D2.OPJ', 'DEMON.OPJ', '222.OPJ']

for fname in files:
    path = os.path.join(opal_dir, fname)
    with open(path, 'rb') as f:
        data = f.read()
    
    h1, h2 = struct.unpack_from('<HH', data, 0)
    print(f'\n{"="*60}')
    print(f'{fname}: {len(data)} bytes, h1={h1}, h2={h2}')
    
    # Read all doubles (aligned to 8 bytes from offset 0)
    print(f'\nAll doubles (8-byte aligned from start):')
    for i in range(0, len(data)-7, 8):
        v = struct.unpack_from('<d', data, i)[0]
        if v != v: continue  # NaN
        if abs(v) > 1e15: continue
        label = ''
        if 0.3 < v < 3.0: label = f'  <-- wavelength? {v*1000:.1f}nm'
        elif 3 < abs(v) < 5000: label = '  <-- radius?'
        elif 0.001 < abs(v) < 200: label = '  <-- thickness/angle?'
        print(f'  [{i:4d}] = {v:20.10f}{label}')
    
    # Find cp866 strings
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
        print(f'\nStrings:')
        for off, s in strings[:10]:
            print(f'  @{off:4d}: "{s}"')
    
    # Compact hex
    print(f'\nHex (first 200 bytes):')
    print(compact_dump(data, 200))
