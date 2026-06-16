import struct, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from opj_reader import load_opj

path = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\DEMON.OPJ'
s, info = load_opj(path)

print(f'Name: {s.name}')
print(f'Glass block offset: 0x{info["glass_block_offset"]:04X}')
print(f'Glass names ({len(info["glass_names"])}):')
for i, g in enumerate(info['glass_names']):
    print(f'  [{i}] "{g}"')

print(f'\nSurfaces ({len(s.surfaces)}):')
for i, surf in enumerate(s.surfaces):
    print(f'  S{i}: R={surf.radius:10.3f} d={surf.thickness:8.3f} glass="{surf.glass}"')
