import struct

path = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\DEMON.OPJ'
with open(path, 'rb') as f:
    data = f.read()

num_surf = struct.unpack_from('<h', data, 0x34)[0]
print(f'N={num_surf}')

# Try reading 2 doubles per surface from 0x128
start = 0x128
print(f'\nSurface data from 0x{start:04X}:')
for i in range(num_surf):
    r = struct.unpack_from('<d', data, start + i*16)[0]
    d = struct.unpack_from('<d', data, start + i*16 + 8)[0]
    print(f'  S{i:2d}: R={r:12.4f}, d={d:10.4f}')

# Glass names: find the block of 8-byte cp866 strings
# Known: ВОЗДУХ is at 0x1F6 (from hex dump: 0x1F4 has "  ВО")
# Actually from dump: 0x1F4 = "  ВОЗДУХ"
glass_block_start = 0x1F4
print(f'\nGlass names from 0x{glass_block_start:04X}:')
for i in range(num_surf + 1):
    raw = data[glass_block_start + i*8 : glass_block_start + i*8 + 8]
    s = raw.decode('cp866', errors='replace').strip().replace('\x00','')
    print(f'  Glass {i:2d}: "{s}"')
