import struct, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

opal = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

# GDAT.FIL — glass names
gdat = os.path.join(opal, 'GDAT.FIL')
with open(gdat, 'rb') as f:
    data = f.read()

print(f"GDAT.FIL: {len(data)} bytes")
print(f"Header: '{data[:8].decode('ascii', errors='replace')}'")

# Records: (len - 8) / 227 ≈ 80 bytes each? or 82?
rec_size_options = [80, 82, 84, 88, 96]
for rs in rec_size_options:
    n_recs = (len(data) - 8) // rs
    print(f"\n  rec_size={rs}: {n_recs} records")

# Try 82 bytes (80 data + 2 something)
# First record at offset 8
for rs in [80, 82, 84]:
    print(f"\n=== Record size {rs} ===")
    for i in range(5):
        off = 8 + i * rs
        chunk = data[off:off+20]
        hx = ' '.join(f'{b:02X}' for b in chunk)
        try:
            s = chunk.decode('cp866', errors='replace').strip()
        except:
            s = '?'
        print(f"  Rec {i}: {hx}  '{s}'")
