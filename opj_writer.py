"""
OPAL-OKB — OPJ File Writer
Запись OpticalSystem в бинарный формат .OPJ.

Формат файла:
  [0x00-0x01] uint16 — magic/version
  [0x02-0x0B] 10 bytes reserved
  [0x0C-0x33] 40 bytes — имя системы (cp866, padded 0x20)
  [0x34-0x35] int16 — количество поверхностей N
  [0x36-0x37] int16 — flags (обычно 1)
  [0x38-0x39] int16 — количество длин волн M
  [0x3A-0x57] reserved extension (заполнено 0x00)
  [0x58-...] surface data: N пар (R: double, d: double) = N*16 байт
  [...] wavelength data: M doubles = M*8 байт
  [...] glass block: (N+1) строк по 8 байт cp866
"""
import struct
import os


def save_opj(system, filepath):
    """
    Сохранить OpticalSystem в бинарный .OPJ файл.

    Args:
        system: OpticalSystem — оптическая система
        filepath: str — путь для сохранения
    """
    # Подготовка данных
    name = system.name[:38] if system.name else "System"
    surfaces = system.surfaces
    num_surf = len(surfaces)
    wavelengths = system.wavelengths if system.wavelengths else []
    num_wl = len(wavelengths)

    # === Build binary ===
    data = bytearray()

    # Header: magic/version (0x00-0x01)
    data += struct.pack('<H', 1)  # version 1

    # Reserved (0x02-0x0B) — 10 bytes
    data += b'\x00' * 10

    # System name (0x0C-0x33) — 40 bytes, cp866, padded with 0x20
    try:
        name_bytes = name.encode('cp866')
    except (UnicodeEncodeError, UnicodeDecodeError):
        name_bytes = name.encode('latin-1', errors='replace')
    name_padded = name_bytes[:40].ljust(40, b'\x20')
    data += name_padded

    # num_surf (0x34-0x35)
    data += struct.pack('<h', num_surf)

    # flags (0x36-0x37)
    data += struct.pack('<h', 1)

    # num_wl (0x38-0x39)
    data += struct.pack('<h', num_wl)

    # Reserved extension (0x3A-0x57) — pad to offset 0x58
    while len(data) < 0x58:
        data += b'\x00'

    # Surface data: N pairs of (R: double, d: double)
    for s in surfaces:
        r = s.radius if s.radius != 0 else 0.0
        d = s.thickness if s.thickness else 0.0
        data += struct.pack('<d', r)
        data += struct.pack('<d', d)

    # Wavelength data: M doubles
    for wl in wavelengths:
        data += struct.pack('<d', wl.value if wl.value else 0.58756)

    # Glass block: (N+1) strings of 8 bytes cp866
    # First entry = air before first surface
    glass_entries = []
    for s in surfaces:
        glass = s.glass.strip() if s.glass else ""
        glass_entries.append(glass)

    # Write glass block: first "ВОЗДУХ" (air before S1), then glass for each surface
    # Entry 0: air before first surface
    air_name = "ВОЗДУХ"
    try:
        air_bytes = air_name.encode('cp866')
    except:
        air_bytes = air_name.encode('latin-1')
    air_padded = air_bytes[:8].ljust(8, b'\x20')
    data += air_padded

    # Entries 1..N: glass for each surface (air after last surface with no glass)
    for glass in glass_entries:
        if not glass or glass.upper() in ('ВОЗДУХ', 'AIR', ''):
            glass = "ВОЗДУХ"
        try:
            g_bytes = glass.encode('cp866')
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                g_bytes = glass.encode('latin-1', errors='replace')
            except Exception:
                g_bytes = b'AIR'
        g_padded = g_bytes[:8].ljust(8, b'\x20')
        data += g_padded

    # Write to file
    with open(filepath, 'wb') as f:
        f.write(bytes(data))

    return filepath
