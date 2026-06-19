import sys, io, struct, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from lbo_reader import load_lbo_fast

systems = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
for s in systems:
    data = s['opj_data']
    name = data[0x0c:0x34].decode('cp866', errors='replace').replace('\x00','').strip()
    if '23' in name:
        print(f'\n=== {s["filename"]}: {name} ===')
        ns = struct.unpack_from('<H', data, 0x34)[0]
        nw = struct.unpack_from('<H', data, 0x38)[0]
        print(f'  nsurf={ns}, nwl={nw}, size={len(data)}')
        
        # Glass block
        vozdh = data.find('ВОЗДУХ'.encode('cp866'))
        if vozdh >= 0:
            print(f'  Glass @{vozdh:#x}:')
            for i in range(ns + 1):
                off = vozdh + i * 8
                g = data[off:off+8].decode('cp866', errors='replace').rstrip('\x00').strip()
                print(f'    {i}: {g!r}')
        
        # Full hex dump
        print(f'  Hex dump:')
        for i in range(0, min(len(data), 400), 16):
            h = ' '.join(f'{b:02x}' for b in data[i:i+16])
            a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f'    {i:04x}: {h}  {a}')
