import struct, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

def find_all_doubles(data, min_val=-1e10, max_val=1e10):
    """Find all offsets where a reasonable double exists."""
    results = []
    for i in range(0, len(data) - 7):
        v = struct.unpack_from('<d', data, i)[0]
        if v == v and abs(v) < 1e15 and v != 0:
            results.append((i, v))
    return results

files = ['HELIOS8.OPJ', 'GTIE00.OPJ', '1.OPJ', 'DEMON.OPJ', 'YBBS77_.OPJ', 'D2.OPJ', '222.OPJ']

for fname in files:
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        continue
    with open(path, 'rb') as f:
        data = f.read()
    
    print(f'\n===== {fname} ({len(data)} bytes) =====')
    
    # Header
    nss = struct.unpack_from('<H', data, 0x34)[0]
    param2 = struct.unpack_from('<H', data, 0x36)[0]
    param3 = struct.unpack_from('<H', data, 0x38)[0]
    param4 = struct.unpack_from('<H', data, 0x3A)[0]
    param5 = struct.unpack_from('<H', data, 0x3C)[0]
    param6 = struct.unpack_from('<H', data, 0x3E)[0]
    
    name = data[12:52].decode('cp866', errors='replace').strip()
    print(f'  Name: "{name}", NSS={nss}, p2={param2}, p3={param3}, p4={param4}, p5={param5}, p6={param6}')
    
    # Find glass block
    air = 'ВОЗДУХ'.encode('cp866')
    air_idx = data.find(air)
    glass_end = air_idx + 8 if air_idx >= 0 else len(data)
    
    # All non-zero doubles in the data area (0x40 to glass start)
    doubles = find_all_doubles(data[0x40:min(air_idx, len(data)) if air_idx >= 0 else len(data)])
    # Adjust offsets
    doubles = [(off + 0x40, v) for off, v in doubles]
    
    # Classify doubles by range
    print(f'\n  All non-zero doubles ({len(doubles)} found):')
    for off, v in doubles:
        category = ''
        if 0.3 <= v <= 0.8:
            category = ' <-- WAVELENGTH?'
        elif 5 <= abs(v) <= 5000:
            category = ' <-- RADIUS?'
        elif 0.01 <= abs(v) <= 100:
            category = ' <-- THICKNESS?'
        elif 1 <= v <= 5:
            category = ' <-- refr.index?'
        elif abs(v) < 0.001:
            category = ' (tiny)'
        elif abs(v) > 100:
            category = ' (large)'
        print(f'    @{off:04X} ({off:4d}): {v:20.10f}{category}')
    
    # Now try to find the doubles block that starts with meaningful values
    # Look for sequences where doubles at stride 8 from some base offset are all reasonable
    print(f'\n  Looking for aligned double sequences...')
    for base_off in range(0x40, 0x48):
        vals = []
        off = base_off
        while off + 8 <= (air_idx if air_idx >= 0 else len(data)):
            v = struct.unpack_from('<d', data, off)[0]
            vals.append((off, v))
            off += 8
        
        # Count meaningful values (not zero, not denormal)
        meaningful = [(o, v) for o, v in vals if v != 0 and abs(v) > 1e-10 and abs(v) < 1e15 and v == v]
        if meaningful:
            print(f'    Base 0x{base_off:04X}: {len(meaningful)} meaningful / {len(vals)} total')
            # Show first 20 meaningful
            for o, v in meaningful[:20]:
                print(f'      @{o:04X}: {v:16.8f}')
