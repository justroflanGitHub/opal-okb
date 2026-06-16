"""Hex dump key OPJ files for format analysis."""
import struct, os

opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
files = ['HELIOS8.OPJ', 'GTIE00.OPJ', '1.OPJ', 'DEMON.OPJ', 'YBBS77_.OPJ']

for fname in files:
    path = os.path.join(opal_dir, fname)
    if not os.path.exists(path):
        print(f'{fname}: NOT FOUND')
        continue
    with open(path, 'rb') as f:
        data = f.read()
    print(f'\n{"="*70}')
    print(f'{fname} ({len(data)} bytes)')
    print(f'{"="*70}')
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f'  {i:04X}: {hex_part:<48} {ascii_part}')
