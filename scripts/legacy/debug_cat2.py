import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')

from glass_catalog_full import _get_catalog

cat = _get_catalog()
print(f"Total glasses: {len(cat)}")

# Show first 20
for i, (name, entry) in enumerate(sorted(cat.items())[:20]):
    print(f"  {name}: nd={entry.get('nd',0):.4f}")

# Count GOST glasses
gost = [k for k in cat if any(c in k for c in 'КБТФЛСО')]
print(f"\nGOST-like: {len(gost)}")
for name in sorted(gost)[:30]:
    e = cat[name]
    print(f"  {name}: nd={e.get('nd',0):.4f}")
