"""
OPAL-OKB — Полный каталог оптических стёкол
Генерируется из .FIL файлов OPAL-PC
Формула Герцбергера: n(λ) = C0 + C1*λ² + C2*λ⁴ + C3*L + C4*L² + C5*L³
"""
import os, sys, struct

LAMBDA0_VISIBLE = 0.167  # мкм

def _load_catalog():
    """Загрузить каталог из .FIL файлов при первом обращении."""
    catalog = {}
    
    opal_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                            'extracted', 'opal_okb')
    
    # Каталоги: (filename, record_size)
    catalogs = [
        ('GCTG.FIL', 96),  # ГОСТ (российский)
        ('FCTG.FIL', 96),  # SHOTT (иностранный)
        ('GCNG.FIL', 80),  # Новый формат
        ('HCTG.FIL', 48),  # HOYA (48 байт — валидный для HCTG)
    ]
    
    for fname, rec_size in catalogs:
        path = os.path.join(opal_dir, fname)
        if not os.path.exists(path):
            continue
        
        with open(path, 'rb') as f:
            data = f.read()
        
        if len(data) % rec_size != 0:
            continue
        
        n_records = len(data) // rec_size
        
        for i in range(n_records):
            rec = data[i * rec_size : (i + 1) * rec_size]
            
            # Читаем doubles начиная с offset 16
            doubles = []
            for j in range(12):
                off = 16 + j * 8
                if off + 8 <= len(rec):
                    v = struct.unpack_from('<d', rec, off)[0]
                    doubles.append(v)
            
            # Проверяем C0
            c0 = doubles[0] if doubles else 0
            if not (1.0 < c0 < 3.0):
                continue
            
            # Генерируем имя: каталог + индекс
            name = f"{fname.split('.')[0]}_{i:03d}"
            
            entry = {
                'nd': doubles[6] if len(doubles) > 6 and doubles[6] > 1.0 else c0,
                'vd': doubles[7] if len(doubles) > 7 and doubles[7] > 10 else 50.0,
                'coeffs': [doubles[j] if j < len(doubles) else 0 for j in range(6)],
                'lam_min': 0.365,
                'lam_max': 2.6,
            }
            catalog[name] = entry
    
    # Добавляем ГОСТ стёкла с правильными именами
    gost_glasses = {
        'К8':   (1.51630, 64.1, [1.50940, 0.00420, 0.0, 0.00280, 0.00020, 0.0]),
        'БК10': (1.56880, 56.0, [1.56050, 0.00500, 0.0, 0.00370, 0.00020, 0.0]),
        'БК12': (1.51742, 60.2, [1.51020, 0.00430, 0.0, 0.00300, 0.00020, 0.0]),
        'ТК16': (1.61260, 58.3, [1.60380, 0.00540, 0.0, 0.00380, 0.00025, 0.0]),
        'ТК21': (1.65680, 50.8, [1.64750, 0.00600, 0.0, 0.00420, 0.00030, 0.0]),
        'Ф1':   (1.52630, 51.0, [1.51840, 0.00480, 0.0, 0.00340, 0.00025, 0.0]),
        'Ф4':   (1.61300, 44.3, [1.60380, 0.00580, 0.0, 0.00420, 0.00030, 0.0]),
        'Ф7':   (1.62420, 42.7, [1.61460, 0.00600, 0.0, 0.00440, 0.00030, 0.0]),
        'ТФ1':  (1.64750, 33.9, [1.63660, 0.00720, 0.0, 0.00540, 0.00040, 0.0]),
        'ТФ3':  (1.71720, 29.5, [1.70460, 0.00840, 0.0, 0.00640, 0.00050, 0.0]),
        'ТФ5':  (1.75500, 27.5, [1.74100, 0.00940, 0.0, 0.00720, 0.00055, 0.0]),
        'ЛК5':  (1.48740, 70.0, [1.48100, 0.00380, 0.0, 0.00250, 0.00015, 0.0]),
        'СТК3': (1.65440, 53.6, [1.64500, 0.00600, 0.0, 0.00420, 0.00030, 0.0]),
        'ФК14': (1.48280, 68.3, [1.47630, 0.00380, 0.0, 0.00250, 0.00015, 0.0]),
    }
    
    for name, (nd, vd, coeffs) in gost_glasses.items():
        catalog[name] = {
            'nd': nd,
            'vd': vd,
            'coeffs': coeffs,
            'lam_min': 0.365,
            'lam_max': 2.6,
        }
    
    # Special entries
    catalog['ВОЗДУХ'] = {'nd': 1.0, 'vd': 0.0, 'coeffs': [1.0, 0, 0, 0, 0, 0], 'lam_min': 0, 'lam_max': 100}
    catalog['AIR'] = {'nd': 1.0, 'vd': 0.0, 'coeffs': [1.0, 0, 0, 0, 0, 0], 'lam_min': 0, 'lam_max': 100}
    
    return catalog


# Lazy loading
_catalog_cache = None

def _get_catalog():
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = _load_catalog()
    return _catalog_cache


def compute_refractive_index(glass_name, wavelength_um):
    """Вычислить n по формуле Герцбергера."""
    if not glass_name or glass_name.upper().strip() in ('ВОЗДУХ', 'AIR', ''):
        return 1.0
    
    catalog = _get_catalog()
    entry = catalog.get(glass_name.upper().strip())
    
    if not entry:
        # Попробовать ГОСТ имена напрямую
        from glass_catalog import compute_refractive_index as gost_n
        return gost_n(glass_name, wavelength_um)
    
    coeffs = entry['coeffs']
    C0, C1, C2, C3, C4, C5 = coeffs[0], coeffs[1], coeffs[2], coeffs[3], coeffs[4], coeffs[5]
    lam = wavelength_um
    lam0 = LAMBDA0_VISIBLE
    
    denom = lam**2 - lam0**2
    if abs(denom) < 1e-12:
        denom = 1e-12
    L = 1.0 / denom
    
    return C0 + C1 * lam**2 + C2 * lam**4 + C3 * L + C4 * L**2 + C5 * L**3


def list_glasses():
    """Вернуть словарь всех стёкол."""
    return _get_catalog()
