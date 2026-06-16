"""
OPAL-OKB — FIL Glass Catalog Reader v2
Точное извлечение стёкол из бинарных .FIL файлов
"""
import struct, os, sys, io

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def parse_gctg(filepath, record_size=96):
    """
    Парсинг каталога стёкол в формате GCTG/FCTG.
    Формат записи (96 байт):
      [0..7]   - марка стекла (8 байт, cp866/ascii)
      [8..9]   - код (2 байта, int16)
      [10..11] - группа/подгруппа
      [12..15] - флаги
      [16..23] - C0 (double, ≈1.3..2.0, показатель преломления)
      [24..31] - C1
      [32..39] - C2  
      [40..47] - C3
      [48..55] - C4
      [56..63] - C5
      [64..71] - nd или ne (double)
      [72..79] - vd или ve (double)
      [80..87] - λ_min (double, мкм)
      [88..95] - λ_max (double, мкм)
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    
    fname = os.path.basename(filepath)
    n_records = len(data) // record_size
    
    if len(data) % record_size != 0:
        print(f"  {fname}: {len(data)} байт не кратно {record_size}")
        return []
    
    entries = []
    for i in range(n_records):
        rec = data[i * record_size : (i + 1) * record_size]
        
        # Марка стекла
        name_raw = rec[0:8]
        try:
            name = name_raw.decode('cp866').strip()
        except:
            name = name_raw.decode('latin-1').strip()
        name = name.replace('\x00', '').strip()
        
        if not name or len(name) < 1:
            continue
        
        # Код
        code = struct.unpack_from('<H', rec, 8)[0]
        
        # Doubles
        doubles = []
        for j in range(12):  # Пробуем 12 doubles
            off = 16 + j * 8
            if off + 8 <= len(rec):
                v = struct.unpack_from('<d', rec, off)[0]
                doubles.append(v)
            else:
                doubles.append(0)
        
        # Проверяем валидность: C0 должен быть ≈1.3-2.5
        c0 = doubles[0] if doubles else 0
        if not (1.0 < c0 < 3.0):
            continue
        
        entry = {
            'name': name,
            'code': code,
            'C0': doubles[0],
            'C1': doubles[1] if len(doubles) > 1 else 0,
            'C2': doubles[2] if len(doubles) > 2 else 0,
            'C3': doubles[3] if len(doubles) > 3 else 0,
            'C4': doubles[4] if len(doubles) > 4 else 0,
            'C5': doubles[5] if len(doubles) > 5 else 0,
            'nd': doubles[6] if len(doubles) > 6 else 0,
            'vd': doubles[7] if len(doubles) > 7 else 0,
            'lam_min': doubles[8] if len(doubles) > 8 else 0,
            'lam_max': doubles[9] if len(doubles) > 9 else 0,
        }
        entries.append(entry)
    
    return entries


def parse_all_catalogs(directory):
    """Парсинг всех каталогов стёкол."""
    # Известные каталоги (F=foreign/SHOTT, G=российский/ГОСТ, H=HOYA)
    catalogs = {
        'FCTG.FIL': ('Иностранные (SHOTT)', 96),
        'GCTG.FIL': ('Российский (ГОСТ)', 96),
        'HCTG.FIL': ('HOYA (Япония)', 96),
        'GCNG.FIL': ('Каталог NEW', None),
    }
    
    all_glasses = {}
    
    for fname, (desc, rec_size) in catalogs.items():
        path = os.path.join(directory, fname)
        if not os.path.exists(path):
            continue
        
        if rec_size:
            entries = parse_gctg(path, rec_size)
        else:
            # GCNG — попробуем разные размеры
            entries = []
            for rs in [96, 104, 112, 88, 80, 128, 144, 160, 176]:
                e = parse_gctg(path, rs)
                if len(e) > len(entries):
                    entries = e
                    rec_size = rs
        
        print(f"\n{'='*60}")
        print(f"{fname} — {desc}")
        print(f"Записей: {len(entries)}, размер записи: {rec_size}")
        print(f"{'='*60}")
        
        for e in entries[:30]:
            nd_str = f"nd={e['nd']:.4f}" if e['nd'] > 0 else "nd=?"
            vd_str = f"vd={e['vd']:.1f}" if e['vd'] > 0 else "vd=?"
            print(f"  {e['name']:>10}  {nd_str}  {vd_str}  C0={e['C0']:.6f}")
        
        if len(entries) > 30:
            print(f"  ... и ещё {len(entries) - 30} записей")
        
        for e in entries:
            all_glasses[e['name']] = e
    
    # Сводка
    print(f"\n\n{'='*60}")
    print(f"ИТОГО: {len(all_glasses)} уникальных стёкол из всех каталогов")
    print(f"{'='*60}")
    
    return all_glasses


def generate_catalog_py(glasses, output_path):
    """Генерация Python файла каталога."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('OPAL-OKB — Полный каталог оптических стёкол\n')
        f.write('Автоматически сгенерирован из .FIL файлов OPAL-PC\n')
        f.write('Формула Герцбергера: n(λ) = C0 + C1*λ² + C2*λ⁴ + C3*L + C4*L² + C5*L³\n')
        f.write('где L = 1/(λ² - λ0²), λ0 = 0.167 мкм\n')
        f.write('"""\n\n')
        f.write('LAMBDA0_VISIBLE = 0.167  # мкм\n\n')
        f.write('GLASS_CATALOG = {\n')
        
        for name, e in sorted(glasses.items()):
            c = [e['C0'], e['C1'], e['C2'], e['C3'], e['C4'], e['C5']]
            nd = e['nd'] if e['nd'] > 0 else 0
            vd = e['vd'] if e['vd'] > 0 else 0
            lam_min = e['lam_min'] if e['lam_min'] > 0 else 0.365
            lam_max = e['lam_max'] if e['lam_max'] > 0 else 2.6
            
            f.write(f'    "{name}": ({nd:.4f}, {vd:.2f}, {c}, {lam_min:.3f}, {lam_max:.3f}),\n')
        
        f.write('}\n\n')
        f.write('def compute_refractive_index(glass_name, wavelength_um):\n')
        f.write('    """Вычислить n по формуле Герцбергера."""\n')
        f.write('    if not glass_name or glass_name.upper().strip() in ("ВОЗДУХ", "AIR", ""):\n')
        f.write('        return 1.0\n')
        f.write('    entry = GLASS_CATALOG.get(glass_name.upper().strip())\n')
        f.write('    if not entry:\n')
        f.write('        return 1.5  # fallback\n')
        f.write('    nd, vd, coeffs, lam_min, lam_max = entry\n')
        f.write('    C0, C1, C2, C3, C4, C5 = coeffs\n')
        f.write('    lam = wavelength_um\n')
        f.write('    lam0 = LAMBDA0_VISIBLE\n')
        f.write('    denom = lam**2 - lam0**2\n')
        f.write('    if abs(denom) < 1e-12: denom = 1e-12\n')
        f.write('    L = 1.0 / denom\n')
        f.write('    return C0 + C1*lam**2 + C2*lam**4 + C3*L + C4*L**2 + C5*L**3\n')


if __name__ == "__main__":
    opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
    glasses = parse_all_catalogs(opal_dir)
    
    # Генерируем полный каталог
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glass_catalog_full.py')
    generate_catalog_py(glasses, out)
    print(f"\nФайл каталога: {out}")
