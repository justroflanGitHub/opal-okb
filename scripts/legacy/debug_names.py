import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fil_reader_v2 import parse_gctg
glasses = parse_gctg(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\GCTG.FIL')
print(f"Total: {len(glasses)}")
for g in glasses[:10]:
    name = g['name']
    print(f"  name='{name}' len={len(name)} bytes={name.encode('utf-8')[:20]} nd={g.get('nd',0):.4f}")
