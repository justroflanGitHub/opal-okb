"""Comprehensive binary analysis of OPJ files."""
import struct, os

opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

def decode_tp_real6(data, offset):
    """Decode Turbo Pascal 6-byte Real."""
    if offset + 6 > len(data):
        return None, offset + 6
    b = data[offset:offset+6]
    # TP Real: byte[0] = exponent (biased by 129)
    # byte[1..4] = mantissa low bytes, byte[5] = mantissa high byte + sign (bit 7)
    exp = b[0]
    if exp == 0:
        return 0.0, offset + 6
    sign = (b[5] >> 7) & 1
    mantissa = b[5] & 0x7F
    for i in range(4, 0, -1):
        mantissa = mantissa * 256 + b[i]
    # value = (-1)^sign * mantissa * 2^(exp - 129 - 39)
    val = (-1)**sign * mantissa * (2.0 ** (exp - 129 - 39))
    return val, offset + 6

def analyze(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    fname = os.path.basename(filepath)
    
    print(f'\n{"="*70}')
    print(f'{fname} ({len(data)} bytes)')
    print(f'{"="*70}')
    
    # Bytes 0-3
    h1, h2 = struct.unpack_from('<HH', data, 0)
    print(f'Header uint16: {h1}, {h2}')
    
    # Try as uint32
    h32 = struct.unpack_from('<I', data, 0)[0]
    print(f'Header uint32: {h32}')
    
    # Bytes 4-11
    print(f'Bytes 4-11: {" ".join(f"{data[i]:02X}" for i in range(4,12))}')
    
    # Name at bytes 12-51
    name_raw = data[12:52]
    try:
        name = name_raw.decode('cp866').strip()
    except:
        name = name_raw.decode('latin-1').strip()
    print(f'Name (12-51): "{name}"')
    
    # Parameters at offset 0x34
    params = []
    for i in range(12):
        v = struct.unpack_from('<H', data, 0x34 + i*2)[0]
        params.append(v)
    print(f'Params @0x34 (12x uint16): {params}')
    
    # Try to interpret params
    nss = params[0]
    nla = params[1]
    print(f'  NSS={nss}, NLA={nla}')
    
    # After params: zeros then doubles
    # Find where doubles start
    # From 0x4C onwards (after params at 0x34 + 24 = 0x4C)
    # Actually params go from 0x34 to 0x34+24-1 = 0x4B
    # Then 0x4C onwards
    
    # Let me read doubles starting from different offsets
    for start_offset in [0x4C, 0x50, 0x58, 0x5C]:
        doubles = []
        off = start_offset
        count = 0
        while off + 8 <= len(data) and count < 40:
            v = struct.unpack_from('<d', data, off)[0]
            doubles.append((off, v))
            off += 8
            count += 1
        
        # Check if first values make sense as radii
        reasonable = sum(1 for _, v in doubles[:nss] if abs(v) < 100000 and v == v)
        print(f'  Doubles from 0x{start_offset:X}: first {nss} reasonable = {reasonable}/{nss}')
        if reasonable > 0:
            for i, (o, v) in enumerate(doubles[:min(nss*2+5, 25)]):
                print(f'    @{o:04X}: {v:14.6f}')
    
    # Also try TP 6-byte reals from 0x4C
    print(f'\n  TP 6-byte reals from 0x4C:')
    off = 0x4C
    for i in range(min(nss*2+5, 25)):
        if off + 6 > len(data):
            break
        v, off = decode_tp_real6(data, off)
        print(f'    @{off-6:04X}: {v:14.6f}')
    
    # Glass names - search for cp866 strings
    print(f'\n  Glass names (searching for cp866 strings):')
    glass_start = None
    for i in range(len(data) - 5):
        # Look for "ВОЗДУХ" pattern: 82 8E 87 84 93 95
        if data[i:i+6] == bytes([0x82, 0x8E, 0x87, 0x84, 0x93, 0x95]):
            glass_start = i
            break
    
    if glass_start:
        print(f'  Found "ВОЗДУХ" at offset 0x{glass_start:X}')
        # Read surrounding area as cp866 string
        # Try to find all glass names - they seem to be space-separated
        glass_area = data[glass_start:]
        # Find end of glass area (look for null or binary data)
        end = 0
        for i in range(len(glass_area)):
            if glass_area[i] == 0:
                end = i
                break
        if end > 0:
            glass_str = glass_area[:end].decode('cp866', errors='replace')
            print(f'  Glass area: "{glass_str}"')
            # Split into individual names - fixed width?
            # Let's see if they're 6 chars each or 8 chars each
            for width in [6, 7, 8, 10]:
                names = [glass_str[i:i+width].strip() for i in range(0, len(glass_str), width)]
                if all(len(n) <= width for n in names):
                    print(f'    Width {width}: {names}')

files = ['HELIOS8.OPJ', 'GTIE00.OPJ', '1.OPJ', 'DEMON.OPJ', 'YBBS77_.OPJ']
for f in files:
    path = os.path.join(opal_dir, f)
    if os.path.exists(path):
        analyze(path)
