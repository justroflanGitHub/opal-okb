"""Analyze all G-files for glass names."""
import sys, io, struct, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = r'extracted\opal_okb'

# Check GDAT.FIL - might contain glass data with names
for fname in ['GDAT.FIL', 'GCON.FIL', 'GCNG.FIL', 'GCRG.FIL', 'GDOC.FIL', 'GUNF.FIL']:
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        continue
    with open(path, 'rb') as f:
        data = f.read()
    print(f"\n{'='*60}")
    print(f"{fname}: {len(data)} bytes")
    print(f"First 200 bytes (hex): {data[:200].hex(' ')}")
    print(f"First 200 bytes (repr): {repr(data[:200])}")
    # Try to find text
    text_parts = []
    for enc in ['cp866', 'cp1251']:
        try:
            t = data.decode(enc, errors='replace')
            # Find printable runs
            import re
            runs = re.findall(r'[\w\u0400-\u04FF]{2,}', t)
            if runs:
                print(f"  Text runs ({enc}): {runs[:20]}")
        except:
            pass

# Check GLAS.FIL (422 bytes - small)
for fname in ['GLAS.FIL']:
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        continue
    with open(path, 'rb') as f:
        data = f.read()
    print(f"\n{'='*60}")
    print(f"{fname}: {len(data)} bytes")
    print(f"All (hex): {data.hex(' ')}")
    print(f"All (repr): {repr(data)}")
