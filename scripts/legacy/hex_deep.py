"""Deep analysis — hex dump only, no string scan"""
import struct, os

opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
out = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\hex_deep.txt'

lines = []

for fname in ['HELIOS8.OPJ', '222.OPJ', 'DEMON.OPJ', 'D2.OPJ']:
    path = os.path.join(opal_dir, fname)
    with open(path, 'rb') as f:
        data = f.read()
    
    num_surf = struct.unpack_from('<h', data, 0x34)[0]
    num_wl = struct.unpack_from('<h', data, 0x38)[0]
    
    lines.append(f'\n{"="*70}')
    lines.append(f'{fname}: {len(data)} bytes, N={num_surf}, WL={num_wl}')
    
    # Full hex dump from offset 0x3A with annotations
    for i in range(0, len(data), 8):
        if i + 8 > len(data): break
        chunk = data[i:i+8]
        hx = ' '.join(f'{b:02X}' for b in chunk)
        
        v = struct.unpack_from('<d', data, i)[0]
        dbl_str = ''
        if v == v and abs(v) < 1e15:
            if v != 0.0:
                dbl_str = f'  = {v:16.8f}'
        
        # Mark if non-zero ASCII
        ascii_hint = ''
        if any(0x80 <= b for b in chunk):
            try:
                s = chunk.decode('cp866', errors='replace').strip()
                ascii_hint = f'  [{s}]'
            except: pass
        
        lines.append(f'{i:04X}: {hx} {dbl_str}{ascii_hint}')

with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('DONE')
