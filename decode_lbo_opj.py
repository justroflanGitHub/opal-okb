"""LBO OPJ decoder v3 — glass index array based mapping."""
import sys, os, struct, math, re, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optics_engine import (OpticalSystem, Surface, Wavelength, FieldPoint,
                            ObjectType, ApertureType)
from lbo_reader import load_lbo_fast

# OPAL-PC standard wavelength table (by index)
OPAL_WL = {
    1: 0.58930,  # d-line (Na)
    2: 0.48613,  # F-line (H)
    3: 0.65627,  # C-line (H)
    4: 0.43584,  # g-line (Hg)
    5: 0.58756,  # d-line (He)
    6: 0.70652,  # r-line (He)
    7: 0.66782,  # B-line (He)
    8: 0.50858,  # e-line (Hg)
}


def decode_lbo_opj(data: bytes) -> OpticalSystem:
    if len(data) < 0x40:
        return OpticalSystem(name="empty")

    name = data[0x0C:0x34].decode('cp866', errors='replace').replace('\x00', '').strip()
    num_surf = struct.unpack_from('<H', data, 0x34)[0]
    num_wl = struct.unpack_from('<H', data, 0x38)[0]
    if not (0 < num_surf <= 50): num_surf = 0
    if not (0 < num_wl <= 10): num_wl = 0

    # 1. Curvatures C=1/R at 0xA8, float64 × num_surf
    curvatures = []
    for i in range(num_surf):
        off = 0xA8 + i * 8
        if off + 8 > len(data): break
        curvatures.append(struct.unpack_from('<d', data, off)[0])

    # 2. Thicknesses after curvatures, float64 × num_surf
    thick_off = 0xA8 + num_surf * 8
    thicknesses = []
    for i in range(num_surf):
        off = thick_off + i * 8
        if off + 8 > len(data):
            thicknesses.append(0.0); continue
        d = struct.unpack_from('<d', data, off)[0]
        if abs(d) > 1e15:
            # Маркер 1e20 = последняя толщина (BFD) неизвестна
            thicknesses.append(0.0)
            if i < num_surf - 1:
                break  # настоящий маркер, обрываем
            else:
                continue  # последняя поверхность — оставляем 0, вычислим позже
        thicknesses.append(d)
    while len(thicknesses) < num_surf:
        thicknesses.append(0.0)

    # 3. Find 1e20 marker
    marker_off = thick_off
    while marker_off < len(data) - 8:
        v = struct.unpack_from('<d', data, marker_off)[0]
        if abs(v) > 1e15 and abs(v) < 1e25:
            break
        marker_off += 8

    # 4. Glass index array: int16 values after marker
    # Index 1 = ВОЗДУХ, 2 = first glass in block, etc.
    # glass_for_surface[i] = glass AFTER surface i = glass_names[indices[i] - 1]
    idx_scan = marker_off + 8
    glass_indices = []
    for i in range(num_surf + 1):
        off = idx_scan + i * 2
        if off + 2 > len(data): break
        glass_indices.append(struct.unpack_from('<H', data, off)[0])

    # 5. Wavelength indices (after glass indices)
    wl_idx_off = idx_scan + (num_surf + 1) * 2
    wavelengths = []
    for i in range(num_wl):
        off = wl_idx_off + i * 2
        if off + 2 > len(data): break
        wl_idx = struct.unpack_from('<H', data, off)[0]
        wavelengths.append(OPAL_WL.get(wl_idx, 0.0))
    # Фильтруем нули — нет реальных данных о длинах волн в LBO
    wavelengths = [w for w in wavelengths if w > 0.0]
    # Если длины волн не найдены — используем стандартный набор e, G', C
    if not wavelengths:
        from optics_engine import _std_wavelengths
        _std = _std_wavelengths()
        wavelengths = [w.value for w in _std]

    # 6. Glass block: search ВОЗДУХ
    vozdh = 'ВОЗДУХ'.encode('cp866')
    glass_off = data.find(vozdh)
    glass_names = []
    nglass_text = 0
    if glass_off >= 0:
        # Сначала читаем по 8-байтным слотам
        # Но некоторые имена длиннее 8 байт (КВАРЦСТК=8, склеено с предыдущим)
        # Поэтому: собираем весь текстовый блок, потом разбиваем по смыслу
        raw_glass_bytes = b''
        for i in range(num_surf + 2):
            off = glass_off + i * 8
            if off + 8 > len(data): break
            raw = data[off:off + 8]
            def _is_glass_byte(b):
                if b == 0 or b == 0x20: return True
                if 0x30 <= b <= 0x39: return True
                if 0x41 <= b <= 0x5A: return True
                if 0x61 <= b <= 0x7A: return True
                if 0x80 <= b <= 0xAF: return True
                if 0xE0 <= b <= 0xEF: return True
                return False
            if not all(_is_glass_byte(b) for b in raw):
                break
            raw_glass_bytes += raw
            nglass_text = i + 1
        
        # Разбиваем накопленный текст на отдельные имена стёкол
        # Известные имена: ВОЗДУХ, КВАРЦ, КВАРЦСТК, К8, ТФ1, etc.
        # Алгоритм: ищем ВОЗДУХ в начале, потом парсим остальные
        full_text = raw_glass_bytes.decode('cp866', errors='replace').replace('\x00', ' ')
        # Убираем множественные пробелы
        while '  ' in full_text:
            full_text = full_text.replace('  ', ' ')
        full_text = full_text.strip()
        
        # Если ВОЗДУХ в начале — это первое стекло
        if full_text.startswith('ВОЗДУХ'):
            glass_names.append('ВОЗДУХ')
            rest = full_text[6:].strip()
        else:
            rest = full_text
        
        # Разбиваем остаток на имена
        # Используем базу российских стёкол для распознавания
        known_glasses = set()
        try:
            from glass_catalog import GLASS_CATALOG
            known_glasses = set(k.upper() for k in GLASS_CATALOG.keys())
        except:
            pass
        # Добавляем специальные "стекла"
        known_glasses.update(['КВАРЦ', 'КВАРЦСТК', 'ФЛЮОРИТ', 'ЗЕРКАЛО'])
        
        pos = 0
        while pos < len(rest):
            # Пропускаем пробелы
            while pos < len(rest) and rest[pos] == ' ':
                pos += 1
            if pos >= len(rest):
                break
            # Ищем самое длинное совпадение из known_glasses
            best_match = None
            for glen in range(min(10, len(rest) - pos), 0, -1):
                candidate = rest[pos:pos+glen].upper()
                if candidate in known_glasses:
                    best_match = rest[pos:pos+glen]
                    break
            if best_match:
                glass_names.append(best_match)
                pos += len(best_match)
            else:
                # Берём до следующего пробела или конца
                end = rest.find(' ', pos)
                if end < 0: end = len(rest)
                glass_name = rest[pos:end].strip()
                if glass_name:
                    glass_names.append(glass_name)
                pos = end

    # 7. Map glass indices to glass names
    # glass_indices[i] = glass BEFORE surface i (medium to the left)
    # For our Surface model: glass = medium AFTER surface = glass_indices[i+1]
    # glass_indices[0] = leading ВОЗДУХ (before S0)
    # Special: glass_index = 65535 (0xFFFF) = ЗЕРКАЛО
    glass_for_surface = []
    is_mirror_surface = []
    for i in range(num_surf):
        gi = glass_indices[i + 1] if i + 1 < len(glass_indices) else 1
        gi_before = glass_indices[i] if i < len(glass_indices) else 1
        # Зеркальная поверхность: glass_index = 65535 до или после
        is_mirror = (gi == 65535 or gi == 0xFFFF or
                     gi_before == 65535 or gi_before == 0xFFFF)
        if is_mirror:
            glass_for_surface.append('ЗЕРКАЛО')
            is_mirror_surface.append(True)
        else:
            name_idx = gi - 1
            if 0 <= name_idx < len(glass_names):
                gname = glass_names[name_idx]
                if gname.upper() in ('ВОЗДУХ', 'AIR', ''):
                    glass_for_surface.append('')
                else:
                    glass_for_surface.append(gname)
            else:
                glass_for_surface.append('')
            is_mirror_surface.append(False)

    # 8. Semi-diameters: float32 after glass block + 4-byte gap
    sd_base = glass_off + nglass_text * 8 + 4 if glass_off >= 0 else 0
    semi_diameters = []
    if sd_base > 0:
        for i in range(num_surf):
            off = sd_base + i * 4
            if off + 4 > len(data): break
            v = struct.unpack_from('<f', data, off)[0]
            if math.isnan(v) or math.isinf(v): v = 10.0
            semi_diameters.append(v)
    if len(semi_diameters) < num_surf:
        semi_diameters = [10.0] * num_surf

    # 9. RI block: compact [air×1.0] + [glasses×ri_per_wl]
    # Find RI by scanning after wavelength indices for doubles in 0.9-2.5
    ri_scan = wl_idx_off + num_wl * 2
    ri_scan = (ri_scan + 7) & ~7  # align to 8 bytes
    ri_values = []
    off = ri_scan
    while off + 8 <= len(data) and len(ri_values) < num_surf * num_wl:
        v = struct.unpack_from('<d', data, off)[0]
        if math.isnan(v) or math.isinf(v): break
        if 0.9 < v < 2.5:
            ri_values.append(v)
        elif ri_values:
            break
        off += 8

    # Determine RI layout: count air entries (leading 1.0s) + glasses
    real_glasses = [g for g in glass_names if g.upper() not in ('ВОЗДУХ', 'AIR', '')]
    ng = len(real_glasses)
    nair_ri = 0
    for v in ri_values:
        if abs(v - 1.0) < 0.001:
            nair_ri += 1
        else:
            break
    ri_per_wl = (len(ri_values) - nair_ri) // ng if ng > 0 else 0

    # 10. Build system
    # 0x3C = Тип предмета: 0=дальний (∞), 1=ближний (конечный)
    obj_type_code = struct.unpack_from('<H', data, 0x3C)[0] if len(data) > 0x3D else 0
    # 0x46 = Тип изображения: 0=ближний, 65535=дальний (∞)
    img_type_code = struct.unpack_from('<H', data, 0x46)[0] if len(data) > 0x47 else 0
    # Field value at 0x74: stored as radians for INFINITE object
    field_val = struct.unpack_from('<d', data, 0x74)[0] if len(data) > 0x7C else 0.0
    if 0 < abs(field_val) < 1.0:
        field_deg = math.degrees(abs(field_val))
    elif abs(field_val) >= 1.0:
        field_deg = abs(field_val)
    else:
        field_deg = 0.0
    
    # 0x3A = ND (номер поверхности диафрагмы)
    stop_surface_num = struct.unpack_from('<H', data, 0x3A)[0] if len(data) > 0x3B else 0
    # 0x5C = апертура (Y/2 мм или NA)
    ap_val_5c = abs(struct.unpack_from('<d', data, 0x5C)[0]) if len(data) > 0x63 else 0.0
    if math.isnan(ap_val_5c) or ap_val_5c > 1e4:
        ap_val_5c = 0.0
    # 0x6C = SD (смещение диафрагмы, мм)
    stop_offset = struct.unpack_from('<d', data, 0x6C)[0] if len(data) > 0x73 else 0.0
    if math.isnan(stop_offset):
        stop_offset = 0.0
    # 0x70 = неизв. (возможно виньетирование или спец параметр)
    val_70 = struct.unpack_from('<d', data, 0x70)[0] if len(data) > 0x77 else 0.0
    if math.isnan(val_70):
        val_70 = 0.0
    
    sys_obj = OpticalSystem(name=name)
    # Тип предмета: 0x3C — 0=дальний(∞), 1=ближний
    sys_obj.object_type = ObjectType.FINITE if obj_type_code == 1 else ObjectType.INFINITE
    # Тип изображения: 0x4A — 0=ближний, 1=дальний(∞)
    img_type_4a = struct.unpack_from('<H', data, 0x4A)[0] if len(data) > 0x4B else 0
    sys_obj.image_type = ObjectType.INFINITE if img_type_4a == 1 else ObjectType.FINITE
    sys_obj.object_height = field_deg if field_deg > 0.001 else 0.0
    
    # Апертура: автоопределение типа по значению 0x5C
    if ap_val_5c > 0 and ap_val_5c < 1.0:
        # NA (sin) — для светосильных и зеркальных систем
        sys_obj.aperture_type = ApertureType.NUMERICAL_APERTURE
        sys_obj.aperture_value = ap_val_5c
    else:
        # D/2 (мм) — высота по Y
        sys_obj.aperture_type = ApertureType.ENTRANCE_PUPIL
        if ap_val_5c >= 1.0:
            sys_obj.aperture_value = ap_val_5c * 2  # D/2 → D
        elif semi_diameters:
            sys_obj.aperture_value = max(semi_diameters) * 2
        else:
            sys_obj.aperture_value = 20.0
    # Длины волн с именами стандартных линий
    _wl_names = {0.54607: 'e', 0.43405: "G'", 0.65627: 'C',
                 0.58756: 'd', 0.48613: 'F', 0.43584: 'g',
                 0.40466: 'h', 0.36501: 'i', 0.70652: 'r',
                 0.85211: 's', 0.64385: "C'", 0.47999: "F'",
                 0.58930: 'D'}
    _wl_list = []
    for wl in wavelengths:
        wl_name = ''
        for wlv, wln in _wl_names.items():
            if abs(wl - wlv) < 0.0002:
                wl_name = wln
                break
        _wl_list.append(Wavelength(wl, 1.0, wl_name))
    sys_obj.wavelengths = _wl_list
    sys_obj.field_points = [FieldPoint(0.0)]
    if field_deg > 0:
        sys_obj.field_points.append(FieldPoint(field_deg))

    for i in range(num_surf):
        c = curvatures[i] if i < len(curvatures) else 0.0
        r = 1.0 / c if abs(c) > 1e-10 else 0.0
        d = thicknesses[i]
        sd = semi_diameters[i] if i < len(semi_diameters) else 10.0
        surf = Surface(radius=r, thickness=d, glass=glass_for_surface[i], semi_diameter=sd)

        # Зеркальная поверхность
        if i < len(is_mirror_surface) and is_mirror_surface[i]:
            surf.is_reflective = True
            surf.glass = 'ЗЕРКАЛО'

        # Set n_override from RI block
        if glass_for_surface[i]:
            # Find glass index in real_glasses
            gi_real = real_glasses.index(glass_for_surface[i]) if glass_for_surface[i] in real_glasses else -1
            if gi_real >= 0 and ri_per_wl > 0:
                ri_start_idx = nair_ri + gi_real * ri_per_wl
                n_ov = {}
                for wi in range(min(ri_per_wl, len(wavelengths))):
                    ri_idx = ri_start_idx + wi
                    if ri_idx < len(ri_values):
                        wl_val = wavelengths[wi] if wi < len(wavelengths) else 0.589
                        n_ov[wl_val] = ri_values[ri_idx]
                if n_ov:
                    surf.n_override = n_ov

        sys_obj.surfaces.append(surf)

    # Номер поверхности диафрагмы (ND из LBO) и смещение (SD)
    if 1 <= stop_surface_num <= num_surf:
        sys_obj.stop_surface = stop_surface_num
    else:
        sys_obj.stop_surface = 1
    sys_obj.stop_offset = stop_offset

    # Вычислить BFD и установить толщину последней поверхности
    if sys_obj.surfaces:
        from optics_engine import paraxial_trace as _pt
        _parax = _pt(sys_obj)
        _bfd = _parax.get('back_focal_distance', 0)
        if _bfd and abs(_bfd) > 0.1:
            sys_obj.surfaces[-1].thickness = abs(_bfd)

    return sys_obj


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from optics_engine import paraxial_trace

    systems = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
    print('=== Индустар-23у f\'=110 ===')
    s = decode_lbo_opj(systems[3]['opj_data'])
    for i, surf in enumerate(s.surfaces):
        print(f'  S{i}: R={surf.radius:>8.2f}, d={surf.thickness:.2f}, glass={surf.glass or "воздух":<6}, D/2={surf.semi_diameter:.2f}')
    p = paraxial_trace(s)
    print(f'  f\' = {p.get("focal_length", 0):.2f}')

    print('\n=== Batch ===')
    for i in range(min(20, len(systems))):
        s = decode_lbo_opj(systems[i]['opj_data'])
        p = paraxial_trace(s)
        f = p.get('focal_length', 0)
        f_match = re.search(r"f'=?(\d+)", s.name)
        f_target = int(f_match.group(1)) if f_match else 0
        ratio = abs(f - f_target) / f_target if f_target else 0
        status = '✅' if ratio < 0.05 else ('⚠' if ratio < 0.15 else '❌')
        print(f'  {status} [{i}] {s.name[:35]:<35} f\'={f:.1f} (target={f_target})')
