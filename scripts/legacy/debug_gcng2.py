import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\GCNG.FIL'
with open(path, 'rb') as f:
    data = f.read()

print(f"GCNG.FIL: {len(data)} bytes")

# Try to find glass name patterns
# К8 in cp866: 8A 38
# ТФ5 in cp866: 92 94 35
# Search for these patterns
patterns = {
    'К8': bytes([0x8A, 0x38]),
    'ТФ5': bytes([0x92, 0x94, 0x35]),
    'К14': bytes([0x8A, 0x31, 0x34]),
}

for name, pat in patterns.items():
    idx = data.find(pat)
    if idx >= 0:
        context = data[max(0,idx-4):idx+12]
        hx = ' '.join(f'{b:02X}' for b in context)
        print(f"  Found '{name}' at offset {idx}: {hx}")
    else:
        print(f"  '{name}' NOT FOUND")

# Try different record sizes
for rec_size in [160, 162, 164, 168]:
    n = len(data) // rec_size
    print(f"\n  rec_size={rec_size}: {n} records")
    # Read first 3 records, try to find name
    for i in range(min(3, n)):
        off = i * rec_size
        # Try reading name from different offsets
        for name_off in [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 148, 152]:
            raw = data[off+name_off:off+name_off+8]
            if len(raw) < 8: continue
            # Check if looks like cp866 name
            try:
                s = raw.decode('cp866', errors='replace').strip()
                if s and any(c.isalpha() for c in s) and len(s) >= 2:
                    # Verify it's not garbage
                    non_print = sum(1 for c in s if not c.isalnum() and c not in '- ')
                    if non_print <= 1:
                        print(f"    Rec {i} offset {name_off}: '{s}'")
            except:
                pass
