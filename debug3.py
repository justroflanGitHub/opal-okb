import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from decode_lbo_opj import decode_lbo_opj
from lbo_reader import load_lbo_fast

systems = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
for idx in [0, 2, 6, 11]:
    s = decode_lbo_opj(systems[idx]['opj_data'])
    print(f'\n[{idx}] {s.name[:40]}')
    for i, surf in enumerate(s.surfaces):
        n_ov = getattr(surf, 'n_override', {})
        n_val = list(n_ov.values())[0] if n_ov else 0
        n_str = f'n={n_val:.4f}' if n_val else ''
        g = surf.glass if surf.glass else 'air'
        print(f'  S{i}: R={surf.radius:>8.2f}, d={surf.thickness:.2f}, glass={g:<6} {n_str}')
