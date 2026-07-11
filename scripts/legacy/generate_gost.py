"""Generate glass_catalog_gost.py from GCTG .FIL — with name filtering"""
import sys, os, re, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fil_reader_v2 import parse_gctg

gctg_path = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\GCTG.FIL'
print("Loading GCTG...")
glasses = parse_gctg(gctg_path)
print(f"Raw: {len(glasses)} glasses")

# Filter: only valid glass names (letters, digits, hyphen)
def valid_name(n):
    n = n.strip()
    if not n or len(n) < 2:
        return False
    # Must contain at least one letter (Russian or Latin)
    if not re.search(r'[A-Za-zА-Яа-яЁё]', n):
        return False
    # Only allowed chars
    if not re.match(r'^[A-Za-zА-Яа-яЁё0-9\-\s]+$', n):
        return False
    return True

filtered = [g for g in glasses if valid_name(g['name'])]
print(f"Valid names: {len(filtered)}")

lines = [
    '"""',
    f'Каталог ГОСТ стёкол ({len(filtered)} марок) из GCTG',
    'Автогенерировано из GCTG.FIL',
    '"""',
    '',
    '# (nd, vd, C0, C1, C2, C3, C4, C5, lambda_min, lambda_max)',
    'GLASS_CATALOG_GOST = {',
]

for g in sorted(filtered, key=lambda x: x['name']):
    name = g['name'].strip()
    nd = g.get('nd', 0)
    vd = g.get('vd', 0)
    coeffs = g.get('coeffs', [0]*6)
    lmin = g.get('lambda_min', 0.365)
    lmax = g.get('lambda_max', 2.5)
    c_str = ', '.join(f'{c:.10e}' for c in coeffs)
    lines.append(f'    "{name}": ({nd:.6f}, {vd:.4f}, {c_str}, {lmin:.4f}, {lmax:.4f}),')

lines.append('}')
lines.append('')
lines.append('def compute_n(name, wl):')
lines.append('    """Показатель преломления (Герцбергер)."""')
lines.append('    e = GLASS_CATALOG_GOST.get(name)')
lines.append('    if e is None:')
lines.append('        raise ValueError(f"Glass {name} not found")')
lines.append('    C0, C1, C2, C3, C4, C5 = e[2:8]')
lines.append('    L = 1.0 / (wl**2 - 0.167**2)')
lines.append('    return C0 + C1*wl**2 + C2*wl**4 + C3*L + C4*L**2 + C5*L**3')
lines.append('')

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glass_catalog_gost.py')
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Written {len(filtered)} glasses")

from glass_catalog_gost import compute_n, GLASS_CATALOG_GOST
print(f"Total: {len(GLASS_CATALOG_GOST)}")
for name in ['К8', 'ТФ5', 'ТК16', 'БФ25', 'СТК3', 'Ф102', 'КФ4', 'ЛК6', 'КРС-6']:
    if name in GLASS_CATALOG_GOST:
        n = compute_n(name, 0.58756)
        nd = GLASS_CATALOG_GOST[name][0]
        print(f"  {name}: nd={nd:.4f}, n(587)={n:.6f}")
    else:
        print(f"  {name}: NOT FOUND")
