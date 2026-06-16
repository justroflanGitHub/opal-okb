"""Deep hex analysis of .OPJ files"""
import struct, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

def hex_dump(data, start=0, length=None, annotations=None):
    if length is None: length = len(data)
    lines = []
    for i in range(0, min(length, len(data)-start), 16):
        chunk = data[start+i:start+i+16]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        cp = ''
        try:
            cp = chunk.decode('cp866', errors='replace')
            cp = ''.join(c if c.isprintable() else '.' for c in cp)
        except: pass
        note = ''
        if annotations:
            for off, txt in annotations:
                if start+i <= off < start+i+16:
                    note = f'  <-- {txt}'
        lines.append(f'{start+i:04X}: {hex_part:<48} {cp}{note}')
    return '\n'.join(lines)

# Analyze multiple files
files = ['HELIOS8.OPJ', '1.OPJ', 'GTIE00.OPJ', 'DEMON.OPJ', 'D2.OPJ', '222.OPJ']

for fname in files:
    path = os.path.join(opal_dir, fname)
    if not os.path.exists(path):
        continue
    with open(path, 'rb') as f:
        data = f.read()
    
    h1, h2 = struct.unpack_from('<HH', data, 0)
    
    # Find all cp866 strings
    strings = []
    i = 4
    while i < len(data):
        if data[i] >= 0x80 or (0x41 <= data[i] <= 0x5A):
            start = i
            while i < len(data) and data[i] >= 0x20 and data[i] < 0xFF:
                i += 1
            raw = data[start:i]
            if len(raw) >= 2:
                try:
                    s = raw.decode('cp866')
                    if any(c.isalpha() for c in s):
                        strings.append((start, s.strip()))
                except: pass
        else:
            i += 1
    
    # Find meaningful doubles
    doubles = []
    for i in range(0, len(data)-7, 8):
        v = struct.unpack_from('<d', data, i)[0]
        if v == v and abs(v) < 1e15:  # not NaN/inf
            doubles.append((i, v))
    
    print(f'\n{"="*70}')
    print(f'{fname}: {len(data)} bytes, header=({h1}, {h2})')
    print(f'{"="*70}')
    print(f'Strings: {len(strings)}')
    for off, s in strings[:10]:
        print(f'  @{off:4d}: "{s}"')
    
    # Classify doubles
    radii = [(o,v) for o,v in doubles if 3 < abs(v) < 5000]
    thick = [(o,v) for o,v in doubles if 0.001 < abs(v) < 300]
    wl = [(o,v) for o,v in doubles if 0.3 < v < 3.0]
    aperture = [(o,v) for o,v in doubles if 5 < abs(v) < 200]
    
    print(f'\nRadii candidates ({len(radii)}):')
    for o,v in radii[:10]:
        print(f'  @{o:4d}: {v:12.4f}')
    
    print(f'\nWavelength candidates ({len(wl)}):')
    for o,v in wl[:10]:
        print(f'  @{o:4d}: {v:12.6f} um = {v*1000:.1f} nm')
    
    # Full hex dump
    print(f'\nFull dump:')
    print(hex_dump(data, 0, len(data)))
