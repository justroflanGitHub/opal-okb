"""Extract GCTG glasses and print as Python dict."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fil_reader_v2 import parse_gctg

entries = parse_gctg(r'extracted\opal_okb\GCTG.FIL')
print(f"Total GCTG entries: {len(entries)}")

# Also check FCTG and HCTG
fctg = parse_gctg(r'extracted\opal_okb\FCTG.FIL')
print(f"Total FCTG entries: {len(fctg)}")

hctg = parse_gctg(r'extracted\opal_okb\HCTG.FIL')
print(f"Total HCTG entries: {len(hctg)}")

# Verify К8
for e in entries:
    if e['name'] == 'К8':
        print(f"\nК8 verification:")
        print(f"  nd={e['nd']:.6f}")
        print(f"  vd={e['vd']:.2f}")
        # Compute n at 0.58756
        lam = 0.58756
        lam0 = 0.167
        L = 1.0/(lam**2 - lam0**2)
        n = e['C0'] + e['C1']*lam**2 + e['C2']*lam**4 + e['C3']*L + e['C4']*L**2 + e['C5']*L**3
        print(f"  n(0.58756) computed = {n:.6f}")
        break

for e in entries:
    if e['name'] == 'ТФ5':
        print(f"\nТФ5 verification:")
        print(f"  nd={e['nd']:.6f}")
        print(f"  vd={e['vd']:.2f}")
        lam = 0.58756
        lam0 = 0.167
        L = 1.0/(lam**2 - lam0**2)
        n = e['C0'] + e['C1']*lam**2 + e['C2']*lam**4 + e['C3']*L + e['C4']*L**2 + e['C5']*L**3
        print(f"  n(0.58756) computed = {n:.6f}")
        break

# Write all GCTG entries to a data file for import
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glass_catalog_gost.py')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('"""\n')
    f.write('OPAL-OKB — Каталог оптических стёкол ГОСТ (GCTG)\n')
    f.write('Автоматически сгенерирован из GCTG.FIL\n')
    f.write('Формула Герцбергера: n(λ) = C0 + C1*λ² + C2*λ⁴ + C3*L + C4*L² + C5*L³\n')
    f.write('где L = 1/(λ² - λ0²), λ0 = 0.167 мкм\n')
    f.write(f'Содержит {len(entries)} стёкол\n')
    f.write('"""\n\n')
    f.write('# λ0 для видимого диапазона\n')
    f.write('LAMBDA0_GOST = 0.167  # мкм\n\n')
    f.write('# Формат: имя -> (nd, vd, C0, C1, C2, C3, C4, C5, lambda_min, lambda_max)\n')
    f.write('GLASS_CATALOG_GOST = {\n')
    
    for e in sorted(entries, key=lambda x: x['name']):
        lam_min = e['lam_min'] if e['lam_min'] > 0 else 0.365
        lam_max = e['lam_max'] if e['lam_max'] > 0 else 2.6
        f.write(f'    "{e["name"]}": (')
        f.write(f'{e["nd"]:.6f}, {e["vd"]:.4f}, ')
        f.write(f'{e["C0"]:.10g}, {e["C1"]:.10g}, {e["C2"]:.10g}, ')
        f.write(f'{e["C3"]:.10g}, {e["C4"]:.10g}, {e["C5"]:.10g}, ')
        f.write(f'{lam_min:.4f}, {lam_max:.4f}')
        f.write('),\n')
    
    f.write('}\n\n')

print(f"\nWritten to: {out_path}")
print(f"Total glasses in file: {len(entries)}")
