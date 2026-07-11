"""Verify GOST glass catalog."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from glass_catalog_gost import GLASS_CATALOG_GOST, LAMBDA0_GOST

print(f"Total glasses: {len(GLASS_CATALOG_GOST)}")

# Test К8
e = GLASS_CATALOG_GOST.get('\u041A8')  # К8
if e:
    lam = 0.58756
    lam0 = LAMBDA0_GOST
    L = 1.0/(lam**2 - lam0**2)
    n = e[2] + e[3]*lam**2 + e[4]*lam**4 + e[5]*L + e[6]*L**2 + e[7]*L**3
    print(f"\u041A8: nd={e[0]:.6f}, n(0.58756)={n:.6f}, diff={abs(n-e[0]):.6f}")
else:
    print("К8 not found!")

# Test ТФ5
e = GLASS_CATALOG_GOST.get('\u0424\u04245')  # ТФ5
if e:
    lam = 0.58756
    lam0 = LAMBDA0_GOST
    L = 1.0/(lam**2 - lam0**2)
    n = e[2] + e[3]*lam**2 + e[4]*lam**4 + e[5]*L + e[6]*L**2 + e[7]*L**3
    print(f"\u0422\u04245: nd={e[0]:.6f}, n(0.58756)={n:.6f}, diff={abs(n-e[0]):.6f}")
else:
    print("ТФ5 not found!")

# Print first 10 entries
print("\nFirst 10 glasses:")
for i, (name, val) in enumerate(sorted(GLASS_CATALOG_GOST.items())):
    if i >= 10:
        break
    print(f"  {name}: nd={val[0]:.4f} vd={val[1]:.2f}")
