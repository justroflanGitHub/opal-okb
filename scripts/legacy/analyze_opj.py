import struct, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

files = ['HELIOS8.OPJ', 'GTIE00.OPJ', '1.OPJ', 'DEMON.OPJ', 'YBBS77_.OPJ', 'D2.OPJ', '222.OPJ']
base = r'extracted\opal_okb'

for fname in files:
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        print(f"SKIP: {fname}")
        continue
    with open(path, 'rb') as f:
        data = f.read()
    
    print(f'\n===== {fname} ({len(data)} bytes) =====')
    
    # Decode header region
    h32 = struct.unpack_from('<I', data, 0)[0]
    h16a, h16b = struct.unpack_from('<HH', data, 0)
    print(f'  Bytes 0-3: uint32={h32}, uint16[0]={h16a}, uint16[1]={h16b}')
    
    b4_5 = struct.unpack_from('<H', data, 4)[0]
    b6_7 = struct.unpack_from('<H', data, 6)[0]
    print(f'  Bytes 4-7: uint16@4={b4_5} ({b4_5:#06x}), uint16@6={b6_7} ({b6_7:#06x})')
    
    b8_11 = struct.unpack_from('<I', data, 8)[0]
    print(f'  Bytes 8-11: uint32={b8_11}')
    
    # Name: offset 12, 40 bytes
    name_raw = data[12:52]
    try:
        name = name_raw.decode('cp866').strip()
    except:
        name = name_raw.decode('latin-1').strip()
    print(f'  Name (12-51): "{name}"')
    
    # Parameters at 0x34 as uint16s
    params = []
    for i in range(0x34, min(0x44, len(data)), 2):
        v = struct.unpack_from('<H', data, i)[0]
        params.append(v)
    print(f'  Params@0x34 (uint16[]): {params}')
    nss = params[0] if params else 0
    print(f'  -> NSS (surfaces) = {nss}')
    
    # Read doubles from 0x40 onward
    print(f'  Doubles from 0x40 to 0x200:')
    for i in range(0x40, min(0x200, len(data)-7), 8):
        v = struct.unpack_from('<d', data, i)[0]
        if v != 0 and abs(v) < 1e15 and v == v:  # not zero, not inf, not NaN
            print(f'    @{i:04X} ({i:4d}): {v:20.10f}')
    
    # Find ВОЗДУХ
    air = 'ВОЗДУХ'.encode('cp866')
    idx = data.find(air)
    if idx >= 0:
        print(f'  ВОЗДУХ at offset 0x{idx:04X} ({idx})')
        # Read glass block: scan for 8-byte string blocks
        # Go backward to find start
        start = idx
        while start > 0x40 and all(b >= 0x20 for b in data[start-1:start+7]):
            start -= 1
            if start < 0x40:
                break
        
        # Actually, let's just read consecutive 8-byte blocks from a reasonable start
        # The glass block should contain the ВОЗДУХ and other glass names
        # Let's find the actual glass block boundaries
        
        # Find start: first byte >= 0x20 that's part of a string block
        # Start from ВОЗДУХ position and go backwards
        pos = idx
        while pos > 0x40:
            chunk = data[pos-8:pos]
            if all(0x20 <= b < 0x100 for b in chunk):
                pos -= 8
            else:
                break
        glass_start = pos
        
        glasses = []
        pos = glass_start
        while pos + 8 <= len(data):
            chunk = data[pos:pos+8]
            if all(0x20 <= b < 0x100 for b in chunk):
                try:
                    g = chunk.decode('cp866').strip()
                    if g:
                        glasses.append((pos, g))
                    pos += 8
                except:
                    break
            else:
                break
        
        print(f'  Glass block starts at 0x{glass_start:04X} ({glass_start}), {len(glasses)} entries:')
        for off, g in glasses:
            print(f'    @{off:04X}: "{g}"')
        print(f'  Glass block ends at 0x{pos:04X} ({pos})')
    else:
        print(f'  ВОЗДУХ NOT FOUND')
