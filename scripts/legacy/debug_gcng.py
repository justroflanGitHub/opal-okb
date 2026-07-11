import struct, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

opal = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

# GCNG.FIL — 37280 bytes, contains glass names?
gcng = os.path.join(opal, 'GCNG.FIL')
with open(gcng, 'rb') as f:
    data = f.read()

print(f"GCNG.FIL: {len(data)} bytes")
# rec_size = 37280 / 227 ≈ 164
rec_size = 164

for i in range(10):
    off = i * rec_size
    if off + rec_size > len(data): break
    chunk = data[off:off+20]
    # Try reading as cp866 string
    name = ''
    for j in range(rec_size):
        b = data[off + j]
        if b == 0:
            break
        if 0x20 <= b < 0xFF:
            name += chr(b) if b < 0x80 else '?'
        else:
            break
    
    # Try cp866
    raw = data[off:off+16]
    # Remove null bytes
    raw_clean = raw.split(b'\x00')[0]
    try:
        s = raw_clean.decode('cp866').strip()
    except:
        s = '?'
    print(f"  Rec {i}: '{s}'  hex={raw_clean.hex()}")
