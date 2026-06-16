import struct, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\GCTG.FIL'
with open(path, 'rb') as f:
    data = f.read()

print(f"GCTG.FIL: {len(data)} bytes")
print(f"Header: {data[:8]}")

# First record starts at offset 8 (after header)
# Try different offsets for glass name
rec_size = 96
for name_off in [0, 4, 8, 16]:
    print(f"\n--- Name at offset {name_off} in record ---")
    for i in range(5):
        rec_start = 8 + i * rec_size
        raw = data[rec_start + name_off : rec_start + name_off + 12]
        hx = ' '.join(f'{b:02X}' for b in raw)
        
        # Try cp866
        try:
            s = raw.decode('cp866').strip()
        except:
            s = '?'
        print(f"  Rec {i}: @{rec_start+name_off:4d} {hx}  cp866='{s}'")

# Also dump first record raw
print(f"\nFirst record (96 bytes from offset 8):")
for j in range(12):
    off = 8 + j*8
    chunk = data[off:off+8]
    hx = ' '.join(f'{b:02X}' for b in chunk)
    v = struct.unpack_from('<d', data, off)[0]
    print(f'  {off:4d}: {hx}  dbl={v:16.8f}')
