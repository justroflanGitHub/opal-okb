import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\GCTG.FIL'
with open(path, 'rb') as f:
    data = f.read()

rec_size = 96
# Dump first 3 records with ALL doubles
for i in range(3):
    off = 8 + i * rec_size
    print(f"\n=== Record {i} at offset {off} ===")
    for j in range(12):
        v = struct.unpack_from('<d', data, off + j*8)[0]
        print(f"  [{j:2d}] dbl={v:20.10f}")
