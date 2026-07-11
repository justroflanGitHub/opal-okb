"""
glass_agf.py — OPAL-PC glass catalog from AGF (Zemax format).

277 glasses with Sellmeier dispersion coefficients.
Source: OPAL.AGF (from OPAL-PC, ИТМО, http://aco.ifmo.ru/developed.html)

Usage:
    from glass_agf import compute_n, get_glass_list
    
    n = compute_n('TK16', 0.54607)  # → 1.612596
    glasses = get_glass_list()       # → ['B510', 'B518', ...]
"""
import math
import os

# Transliteration map: AGF (Latin) → Russian (Cyrillic)
_LAT_TO_RUS = {
    'BK': 'БК', 'BF': 'БФ', 'BC': 'БК',  # БК for both BK and BC
    'STK': 'СТК', 'TK': 'ТК', 'TKN': 'ТКН', 'TKH': 'ТКН',
    'LF': 'ЛФ', 'TF': 'ТФ', 'TFK': 'ТФК',
    'OF': 'ОФ', 'FK': 'ФК',
    'K': 'К', 'F': 'Ф',
    'KVARCSTK': 'КВАРЦСТК', 'KVARC': 'КВАРЦ',
    'FLUOR': 'ФЛЮОРИТ',
    'PO': 'ПО', 'BO': 'БО',
    'FFS': 'ФФС',
    'CAF2': 'CaF2', 'CDTE': 'CdTe',
}

# Russian → Latin (reverse for lookup from LBO glass names)
_RUS_TO_LAT = {}
for lat, rus in _LAT_TO_RUS.items():
    if rus not in _RUS_TO_LAT:
        _RUS_TO_LAT[rus] = lat


def _agf_to_russian(name):
    """Convert AGF transliterated name to Russian."""
    name_upper = name.upper()
    # Try exact match first
    if name_upper in _LAT_TO_RUS:
        return _LAT_TO_RUS[name_upper]
    # Try prefix match (longest first)
    for lat in sorted(_LAT_TO_RUS.keys(), key=len, reverse=True):
        if name_upper.startswith(lat):
            rest = name[len(lat):]
            return _LAT_TO_RUS[lat] + rest
    return None


def _rus_to_latin(name):
    """Convert Russian name to AGF Latin."""
    name_upper = name.upper()
    if name_upper in _RUS_TO_LAT:
        return _RUS_TO_LAT[name_upper]
    for rus in sorted(_RUS_TO_LAT.keys(), key=len, reverse=True):
        if name_upper.startswith(rus):
            rest = name[len(rus):]
            return _RUS_TO_LAT[rus] + rest
    return None


# AGF record: name, nd, vd, cd_coeffs, ld_range
class AGFGlass:
    __slots__ = ('name', 'nd', 'vd', 'cd', 'ld', 'td')
    def __init__(self, name, nd, vd, cd, ld, td):
        self.name = name      # AGF name (Latin)
        self.nd = nd          # refractive index at d-line
        self.vd = vd          # Abbe number
        self.cd = cd          # Schott polynomial coefficients [C0..C5]
        self.ld = ld          # [lambda_min, lambda_max] in um
        self.td = td          # thermal coefficients

    def n(self, wavelength_um):
        """Compute refractive index at given wavelength (um) using Schott formula.
        
        Schott: n^2 = C0 + C1*w^2 + C2/w^2 + C3/w^4 + C4/w^6 + C5/w^8
        """
        cd = self.cd
        wl2 = wavelength_um * wavelength_um
        n2 = cd[0] if len(cd) > 0 else 1.0
        if len(cd) > 1: n2 += cd[1] * wl2
        if len(cd) > 2: n2 += cd[2] / wl2
        if len(cd) > 3: n2 += cd[3] / (wl2 * wl2)
        if len(cd) > 4: n2 += cd[4] / (wl2 ** 3)
        if len(cd) > 5: n2 += cd[5] / (wl2 ** 4)
        return math.sqrt(n2) if n2 > 0 else 1.0


# === Parse AGF file ===
_AGF_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'opal_ utils', 'glasscat', 'OPAL.AGF'
)

_CATALOG = None  # name → AGFGlass
_CATALOG_RUS = None  # Russian name → AGFGlass


def _parse_agf(path):
    """Parse AGF file into catalog."""
    catalog = {}
    catalog_rus = {}
    
    with open(path, 'r', errors='replace') as f:
        current = None
        for line in f:
            line = line.rstrip()
            if line.startswith('NM '):
                parts = line.split()
                name = parts[1] if len(parts) > 1 else '?'
                try:
                    nd = float(parts[4])
                    vd = float(parts[5])
                except (ValueError, IndexError):
                    nd = 0.0
                    vd = 0.0
                current = AGFGlass(name, nd, vd, [], [], [])
                catalog[name] = current
                # Also add Russian alias
                rus = _agf_to_russian(name)
                if rus:
                    catalog_rus[rus] = current
            elif line.startswith('CD ') and current is not None:
                current.cd = [float(v) for v in line.split()[1:]]
            elif line.startswith('LD ') and current is not None:
                current.ld = [float(v) for v in line.split()[1:]]
            elif line.startswith('TD ') and current is not None:
                current.td = [float(v) for v in line.split()[1:]]
    
    return catalog, catalog_rus


def _ensure_loaded():
    global _CATALOG, _CATALOG_RUS
    if _CATALOG is None:
        _CATALOG, _CATALOG_RUS = _parse_agf(_AGF_PATH)


def get_glass_list():
    """Return list of all AGF glass names (Latin)."""
    _ensure_loaded()
    return sorted(_CATALOG.keys())


def get_glass(name):
    """Get AGFGlass by name (Latin or Russian). Returns None if not found."""
    _ensure_loaded()
    if name in _CATALOG:
        return _CATALOG[name]
    if name in _CATALOG_RUS:
        return _CATALOG_RUS[name]
    # Try case-insensitive
    name_u = name.upper()
    for key in _CATALOG:
        if key.upper() == name_u:
            return _CATALOG[key]
    for key in _CATALOG_RUS:
        if key.upper() == name_u:
            return _CATALOG_RUS[key]
    return None


def compute_n(glass_name, wavelength_um):
    """Compute refractive index for glass at wavelength (μm).
    
    Args:
        glass_name: Latin ('TK16') or Russian ('ТК16')
        wavelength_um: wavelength in micrometers (e.g. 0.54607)
    
    Returns:
        n value, or 1.5 fallback if glass not found
    """
    g = get_glass(glass_name)
    if g is None:
        return 1.5  # fallback
    return g.n(wavelength_um)


def get_nd_vd(glass_name):
    """Get (nd, vd) for a glass. Returns (0, 0) if not found."""
    g = get_glass(glass_name)
    if g is None:
        return (0.0, 0.0)
    return (g.nd, g.vd)


# === Self-test ===
if __name__ == '__main__':
    _ensure_loaded()
    print(f"Loaded {len(_CATALOG)} glasses from AGF")
    print(f"Russian aliases: {len(_CATALOG_RUS)}")
    
    # Verify against known LBO n_override values
    tests = [
        ('TK16', 'ТК16', 0.54607, 1.612596),
        ('TK16', 'ТК16', 0.43405, 1.625977),
        ('TK16', 'ТК16', 0.65627, 1.609501),
        ('LF5',  'ЛФ5',  0.54607, 1.574899),
        ('K8',   'К8',   0.58930, 1.516300),
        ('K14',  'К14',  0.58930, 1.514703),
        ('F2',   'Ф2',   0.58930, 1.616400),
    ]
    
    print("\n=== Verification ===")
    all_ok = True
    for lat, rus, wl, expected in tests:
        n_lat = compute_n(lat, wl)
        n_rus = compute_n(rus, wl)
        ok = abs(n_lat - expected) < 0.0001 and abs(n_rus - expected) < 0.0001
        marker = 'OK' if ok else 'FAIL'
        print(f"  {marker} {lat:6s}/{rus:6s} n({wl:.5f}) = {n_lat:.6f} (expected {expected:.6f})")
        if not ok:
            all_ok = False
    
    # Show some Russian glasses
    print(f"\n=== Russian glasses in AGF ===")
    rus_glasses = sorted(_CATALOG_RUS.keys())
    print(f"Total: {len(rus_glasses)}")
    for name in rus_glasses[:20]:
        g = _CATALOG_RUS[name]
        print(f"  {name:12s} nd={g.nd:.6f} vd={g.vd:.4f}")
    
    print(f"\nTests: {'ALL PASSED' if all_ok else 'SOME FAILED'}")
