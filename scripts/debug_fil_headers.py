import struct, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

opal = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

# Check each .FIL file header
for f in sorted(os.listdir(opal)):
    if not f.upper().endswith('.FIL'):
        continue
    path = os.path.join(opal, f)
    with open(path, 'rb') as fh:
        data = fh.read(100)
    size = os.path.getsize(path)
    header = data[:8]
    # Try to show as text
    txt = ''
    for b in header:
        if 0x20 <= b < 0x7F:
            txt += chr(b)
        else:
            txt += '.'
    print(f'{f:<20} {size:>8}b  header={txt}  hex={header.hex()}')
