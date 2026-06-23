"""
OPAL-OKB — OPJ File Reader v5
Полный парсинг бинарных файлов .OPJ → OpticalSystem с извлечением имён стёкол.

Формат файла:
  [0x00-0x01] uint16 — magic/version
  [0x02-0x0B] 10 bytes reserved
  [0x0C-0x33] 40 bytes — имя системы (cp866, padded 0x20)
  [0x34-0x35] int16 — количество поверхностей N (включая фиктивные)
  [0x36-0x37] int16 — flags (обычно 1)
  [0x38-0x39] int16 — количество длин волн M
  [0x3A-...] header extension
  [...] surface data: N пар (R: double, d: double) = N*16 байт
  [...] wavelength/field data
  [...] glass block: (N+1) строк по 8 байт cp866
"""
import struct
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, ObjectType, ApertureType


# Константа: большой double, означающий "нет данных" / конец реальных поверхностей
_MAX_VALID_RADIUS = 1e10
_MARKER_DOUBLE = 0x4415AF1D78858C40  # common marker byte pattern


def _read_glass_name(data, offset):
    """Прочитать 8-байтное имя стекла в cp866."""
    raw = data[offset:offset + 8]
    if len(raw) < 8:
        return "", offset + 8
    try:
        name = raw.decode('cp866').strip().replace('\x00', '')
    except:
        name = raw.decode('latin-1').strip().replace('\x00', '')
    return name, offset + 8


def _find_glass_block(data, num_surf, search_start=0):
    """
    Найти блок имён стёкол в файле.
    Ищем паттерн: 8 байт spaces + cp866 "ВОЗДУХ" (82 8E 87 84 93 95) или AIR.
    """
    # ВОЗДУХ в cp866: 82 8E 87 84 93 95
    vozdukh = bytes([0x82, 0x8E, 0x87, 0x84, 0x93, 0x95])
    # AIR: 41 49 52
    
    for i in range(search_start, len(data) - 8):
        # Check for "ВОЗДУХ" preceded by spaces
        if data[i:i+6] == vozdukh:
            # Verify preceding bytes are spaces (0x20)
            pre = data[max(0, i-2):i]
            if all(b == 0x20 for b in pre):
                # Found! Glass block starts at i - 2 (to include preceding spaces)
                glass_start = i - 2
                return glass_start
        # Also check "  ВОЗДУХ" pattern directly
        if i + 8 <= len(data) and data[i:i+2] == b'\x20\x20' and data[i+2:i+8] == vozdukh:
            return i
    
    return -1


def _find_surface_block(data, num_surf, num_wl):
    """
    Найти начало блока данных поверхностей.
    Стратегия: surface data содержит пары (R, d) где R >= 1 (или 0 для плоскости).
    Разница с aberration data: аберрации маленькие (|v| < 1), радиусы >= 1.
    Ищем самый длинный run валидных пар.
    """
    best_start = -1
    best_count = 0
    
    for start in range(0x58, min(0x200, len(data)), 8):
        count = 0
        for i in range(min(num_surf, 20)):
            off = start + i * 16
            if off + 16 > len(data):
                break
            r = struct.unpack_from('<d', data, off)[0]
            d = struct.unpack_from('<d', data, off + 8)[0]
            # Valid surface: R >= 1 (or 0 for flat), d >= 0
            r_ok = (r == 0.0) or (1.0 <= abs(r) < _MAX_VALID_RADIUS)
            d_ok = (d >= 0 and d < 500) or abs(d) < 1e-10
            if r_ok and d_ok:
                count += 1
            else:
                break  # Stop at first invalid
        if count > best_count:
            best_count = count
            best_start = start
    
    return best_start


def load_opj(filepath):
    """
    Загрузить .OPJ файл → (OpticalSystem, info_dict)
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    
    fname = os.path.basename(filepath)
    info = {'filename': fname, 'size': len(data), 'warnings': []}
    
    if len(data) < 0x40:
        return OpticalSystem(name=fname), info
    
    # System name (0x0C-0x33, 40 bytes)
    try:
        sys_name = data[0x0C:0x34].decode('cp866').replace('\x00', '').strip()
    except:
        sys_name = fname
    if not sys_name:
        sys_name = fname
    
    # Counts
    num_surf = struct.unpack_from('<h', data, 0x34)[0]
    num_wl = struct.unpack_from('<h', data, 0x38)[0]
    
    if not (0 < num_surf <= 160):
        info['warnings'].append(f'num_surf={num_surf}')
        num_surf = 0
    if not (0 < num_wl <= 10):
        num_wl = 0
    
    info['num_surfaces'] = num_surf
    info['num_wavelengths'] = num_wl
    
    sys = OpticalSystem(name=sys_name)
    sys.object_type = ObjectType.INFINITE
    
    # === Find glass block ===
    glass_start = _find_glass_block(data, num_surf)
    info['glass_block_offset'] = glass_start
    
    glass_names = []
    if glass_start >= 0:
        # Read glass names: 8-byte cp866 strings until we hit a null byte
        # at the start of a record (means end of glass block)
        for i in range(num_surf + 1):
            off = glass_start + i * 8
            if off + 8 > len(data):
                break
            # Check if this is still a glass name (starts with 0x20 or >= 0x80)
            first_byte = data[off]
            if first_byte == 0x00:
                break  # End of glass block
            name, _ = _read_glass_name(data, off)
            glass_names.append(name)
    
    info['glass_names'] = glass_names
    
    # === Find surface data block ===
    surf_start = _find_surface_block(data, num_surf, num_wl)
    info['surface_block_offset'] = surf_start
    
    surfaces = []
    if surf_start >= 0:
        for i in range(num_surf):
            off = surf_start + i * 16
            if off + 16 > len(data):
                break
            r = struct.unpack_from('<d', data, off)[0]
            d = struct.unpack_from('<d', data, off + 8)[0]
            
            # Validate: skip garbage values
            import math
            if math.isnan(r) or math.isnan(d):
                break
            if math.isinf(r) or math.isinf(d):
                break
            if abs(d) > 1e6:  # thickness > 1000m = garbage
                break
            if abs(r) > 0 and abs(r) < 1e-10:  # denormalized double
                break
            
            # Skip marker/end doubles
            if abs(r) > _MAX_VALID_RADIUS:
                break
            if r == 0.0 and d == 0.0 and len(surfaces) > 0:
                # Could be trailing empty surfaces — check if glass is empty too
                gi = i + 1
                glass_check = glass_names[gi] if gi < len(glass_names) else ""
                if not glass_check.strip():
                    break
            
            # glass_names[0] = "ВОЗДУХ" (air before S0), glass_names[i+1] = glass for surface i
            gi = i + 1
            glass = glass_names[gi] if gi < len(glass_names) else ""
            # Clean glass name
            glass = glass.strip()
            # Empty, spaces, or air keywords → empty (no glass)
            if glass in ('ВОЗДУХ', 'AIR', '', 'А', 'A', ' '):
                glass = ""
            # Single char that's not a known glass → empty
            if glass and len(glass) <= 1:
                glass = ""
            # Remove trailing garbage (non-alphanumeric)
            if glass:
                import re
                glass = re.sub(r'[^A-Za-zА-Яа-яЁё0-9\-]+$', '', glass)
                if not glass or glass == '-':
                    glass = ""
            
            surfaces.append(Surface(
                radius=r,
                thickness=d,
                glass=glass,
                semi_diameter=10.0,
            ))
    
    # === Extract wavelengths ===
    # Wavelengths are stored as doubles in the range 0.3-3.0 (micrometers)
    # They appear between surface block and glass block
    wavelengths = []
    wl_search_start = surf_start + num_surf * 16 if surf_start >= 0 else 0x58
    wl_search_end = glass_start if glass_start >= 0 else len(data)
    
    seen_offsets = set()
    for i in range(wl_search_start, min(wl_search_end, len(data)) - 7, 8):
        v = struct.unpack_from('<d', data, i)[0]
        if v == v and 0.35 < v < 2.5 and i not in seen_offsets:
            wavelengths.append(v)
            seen_offsets.add(i)
            if len(wavelengths) >= 5:
                break
    
    # If no wavelengths found between blocks, search entire file
    if not wavelengths:
        for i in range(0, len(data) - 7, 8):
            v = struct.unpack_from('<d', data, i)[0]
            if v == v and 0.35 < v < 2.5:
                wavelengths.append(v)
                if len(wavelengths) >= 5:
                    break
    
    # Длины волн: если не найдены — стандарт e, G', C
    from optics_engine import _std_wavelengths
    if not wavelengths:
        sys.wavelengths = _std_wavelengths()
    else:
        # Назначаем имена стандартных линий
        _wl_names = {0.54607: 'e', 0.43405: "G'", 0.65627: 'C',
                     0.58756: 'd', 0.48613: 'F', 0.43584: 'g',
                     0.40466: 'h', 0.36501: 'i', 0.70652: 'r',
                     0.85211: 's', 0.64385: "C'", 0.47999: "F'"}
        wl_list = []
        for w in wavelengths:
            name = ''
            for wlv, wln in _wl_names.items():
                if abs(w - wlv) < 0.0002:
                    name = wln
                    break
            wl_list.append(Wavelength(w, 1.0, name))
        sys.wavelengths = wl_list
    sys.surfaces = surfaces
    sys.stop_surface = 1
    sys.aperture_value = 20.0
    info['surfaces_parsed'] = len(surfaces)
    
    return sys, info


def load_all_opj(directory):
    """Загрузить все .OPJ файлы. Вернуть список (filename, system, info)."""
    results = []
    for fname in sorted(os.listdir(directory)):
        if fname.upper().endswith('.OPJ'):
            path = os.path.join(directory, fname)
            try:
                sys, info = load_opj(path)
                results.append((fname, sys, info))
            except Exception as e:
                results.append((fname, None, {'error': str(e)}))
    return results


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
    results = load_all_opj(opal_dir)
    
    ok = sum(1 for _, s, _ in results if s is not None)
    fail = sum(1 for _, s, _ in results if s is None)
    total_surf = sum(len(s.surfaces) for _, s, _ in results if s is not None)
    with_glass = sum(1 for _, s, _ in results if s is not None and any(surf.glass for surf in s.surfaces))
    
    print(f"OPJ files: {len(results)} total, {ok} OK, {fail} failed")
    print(f"Total surfaces: {total_surf}, Files with glass names: {with_glass}")
    print()
    
    print(f"{'File':<20} {'Surf':>5} {'WL':>4} {'Glasses':>20} {'Name':>20}")
    print("-" * 80)
    for fname, s, info in results:
        if s is None:
            print(f"{fname:<20} FAIL: {info.get('error','?')}")
            continue
        ns = info['surfaces_parsed']
        nw = len(s.wavelengths)
        glasses = ','.join(surf.glass for surf in s.surfaces if surf.glass)[:20]
        name = s.name[:20]
        print(f"{fname:<20} {ns:>5} {nw:>4} {glasses:>20} {name:>20}")
