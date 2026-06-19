"""LBO OPJ decoder v2 — correct glass/SD mapping."""
import sys, os, struct, math, re, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optics_engine import (OpticalSystem, Surface, Wavelength, FieldPoint,
                            ObjectType, ApertureType)
from lbo_reader import load_lbo_fast


def decode_lbo_opj(data: bytes) -> OpticalSystem:
    if len(data) < 0x40:
        return OpticalSystem(name="empty")

    name = data[0x0C:0x34].decode('cp866', errors='replace').replace('\x00', '').strip()
    num_surf = struct.unpack_from('<H', data, 0x34)[0]
    num_wl = struct.unpack_from('<H', data, 0x38)[0]
    if not (0 < num_surf <= 50): num_surf = 0
    if not (0 < num_wl <= 10): num_wl = 0

    # Curvatures C=1/R at 0xA8
    curvatures = []
    for i in range(num_surf):
        off = 0xA8 + i * 8
        if off + 8 > len(data): break
        curvatures.append(struct.unpack_from('<d', data, off)[0])

    # Thicknesses
    thick_off = 0xA8 + num_surf * 8
    thicknesses = []
    for i in range(num_surf):
        off = thick_off + i * 8
        if off + 8 > len(data):
            thicknesses.append(0.0); continue
        d = struct.unpack_from('<d', data, off)[0]
        if abs(d) > 1e15:
            thicknesses.append(0.0); break
        thicknesses.append(d)
    while len(thicknesses) < num_surf:
        thicknesses.append(0.0)

    # Glass block
    vozdh = 'ВОЗДУХ'.encode('cp866')
    glass_off = data.find(vozdh)
    glass_names = []
    nglass_text = 0
    if glass_off >= 0:
        for i in range(num_surf + 1):
            off = glass_off + i * 8
            if off + 8 > len(data): break
            raw = data[off:off + 8]
            is_text = all(b >= 0x20 or b == 0 for b in raw)
            if not is_text and i > 0: break
            if not is_text and i == 0: continue
            gname = raw.decode('cp866', errors='replace').rstrip('\x00').strip()
            glass_names.append(gname)
            nglass_text = i + 1

    real_glasses = [g for g in glass_names if g.upper() not in ('ВОЗДУХ', 'AIR', '')]

    # Glass mapping with cemented detection
    # nglass=4, num_surf=7 → 3 air surfaces
    # Reserve 1 for trailing air → 2 inter-lens air gaps for 3 gaps between 4 lenses
    # → 1 cemented pair (3-2=1 gap missing)
    glass_for_surface = [''] * num_surf
    ng = len(real_glasses)
    gidx = 0
    si = 0
    nair_total = num_surf - ng  # total air surfaces
    nair_used = 0
    while gidx < ng and si < num_surf:
        glass_for_surface[si] = real_glasses[gidx]
        gidx += 1
        si += 1
        remaining_glass = ng - gidx
        remaining_surf = num_surf - si
        remaining_air = remaining_surf - remaining_glass
        # Insert air if: more than 1 air remains (1 reserved for trailing)
        if remaining_air > 1:
            nair_used += 1
            si += 1

    # Semi-diameters
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

    # Build system
    y_height = struct.unpack_from('<d', data, 0x58)[0] if len(data) > 0x60 else 10.0
    field_val = struct.unpack_from('<d', data, 0x74)[0] if len(data) > 0x7C else 0.0
    field_deg = math.degrees(abs(field_val)) if 0 < abs(field_val) < 0.1 else abs(field_val)

    # Wavelengths
    marker_off = thick_off
    while marker_off < len(data) - 8:
        v = struct.unpack_from('<d', data, marker_off)[0]
        if abs(v) > 1e15: break
        marker_off += 8
    wavelengths = []
    wl_scan = marker_off + 8
    while wl_scan + 8 <= len(data) and len(wavelengths) < num_wl:
        v = struct.unpack_from('<d', data, wl_scan)[0]
        if 0.3 < v < 3.0:
            wavelengths.append(v)
        wl_scan += 8
    if not wavelengths:
        wavelengths = [0.58930]

    sys_obj = OpticalSystem(name=name)
    sys_obj.object_type = ObjectType.INFINITE
    sys_obj.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys_obj.aperture_value = max(y_height * 2, 10.0)
    sys_obj.object_height = field_deg if field_deg > 0 else 5.0
    sys_obj.wavelengths = [Wavelength(wl, 1.0) for wl in wavelengths[:num_wl]]
    sys_obj.field_points = [FieldPoint(0.0)]
    if field_deg > 0:
        sys_obj.field_points.append(FieldPoint(field_deg))

    for i in range(num_surf):
        c = curvatures[i] if i < len(curvatures) else 0.0
        r = 1.0 / c if abs(c) > 1e-10 else 0.0
        d = thicknesses[i]
        sd = semi_diameters[i] if i < len(semi_diameters) else 10.0
        sys_obj.surfaces.append(Surface(radius=r, thickness=d, glass=glass_for_surface[i], semi_diameter=sd))

    sys_obj.stop_surface = 1
    f_match = re.search(r"f'=?(\d+)", name)
    f_target = float(f_match.group(1)) if f_match else 100.0
    if sys_obj.surfaces:
        sys_obj.surfaces[-1].thickness = f_target * 0.15

    return sys_obj


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from optics_engine import paraxial_trace

    systems = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
    print('=== Индустар-23у f\'=110 ===')
    s = decode_lbo_opj(systems[3]['opj_data'])
    for i, surf in enumerate(s.surfaces):
        print(f'  S{i}: R={surf.radius:>8.2f}, d={surf.thickness:.2f}, glass={surf.glass:<6}, D/2={surf.semi_diameter:.2f}')
    p = paraxial_trace(s)
    print(f'  f\' = {p.get("focal_length", 0):.2f}')

    print('\n=== Batch ===')
    for i in range(min(15, len(systems))):
        s = decode_lbo_opj(systems[i]['opj_data'])
        p = paraxial_trace(s)
        f = p.get('focal_length', 0)
        f_match = re.search(r"f'=?(\d+)", s.name)
        f_target = int(f_match.group(1)) if f_match else 0
        ratio = abs(f - f_target) / f_target if f_target else 0
        status = '✅' if ratio < 0.15 else ('⚠' if ratio < 0.4 else '❌')
        print(f'  {status} [{i}] {s.name[:35]:<35} f\'={f:.1f} (target={f_target})')
