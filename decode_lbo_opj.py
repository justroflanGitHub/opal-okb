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
            thicknesses.append(0.0); break
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
        wavelengths.append(OPAL_WL.get(wl_idx, 0.58930))
    if not wavelengths:
        wavelengths = [0.58930]

    # 6. Glass block: search ВОЗДУХ
    vozdh = 'ВОЗДУХ'.encode('cp866')
    glass_off = data.find(vozdh)
    glass_names = []
    nglass_text = 0
    if glass_off >= 0:
        for i in range(num_surf + 1):
            off = glass_off + i * 8
            if off + 8 > len(data): break
            raw = data[off:off + 8]
            # Strict validation: glass names contain only cp866 letters,
            # digits, spaces, and null padding
            def _is_glass_byte(b):
                if b == 0 or b == 0x20: return True  # null/space
                if 0x30 <= b <= 0x39: return True     # 0-9
                if 0x41 <= b <= 0x5A: return True     # A-Z
                if 0x61 <= b <= 0x7A: return True     # a-z
                if 0x80 <= b <= 0xAF: return True     # cp866 А-п
                if 0xE0 <= b <= 0xEF: return True     # cp866 р-я
                return False
            is_text = all(_is_glass_byte(b) for b in raw)
            if not is_text: break
            gname = raw.decode('cp866', errors='replace').rstrip('\x00').strip()
            glass_names.append(gname)
            nglass_text = i + 1

    # 7. Map glass indices to glass names
    # glass_indices[i] = glass BEFORE surface i (medium to the left)
    # For our Surface model: glass = medium AFTER surface = glass_indices[i+1]
    # glass_indices[0] = leading ВОЗДУХ (before S0)
    glass_for_surface = []
    for i in range(num_surf):
        # Glass AFTER surface i = glass at position i+1 in indices
        gi = glass_indices[i + 1] if i + 1 < len(glass_indices) else 1
        name_idx = gi - 1  # 0-based into glass_names
        if 0 <= name_idx < len(glass_names):
            gname = glass_names[name_idx]
            if gname.upper() in ('ВОЗДУХ', 'AIR', ''):
                glass_for_surface.append('')
            else:
                glass_for_surface.append(gname)
        else:
            glass_for_surface.append('')

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
    y_height = struct.unpack_from('<d', data, 0x58)[0] if len(data) > 0x60 else 10.0
    field_val = struct.unpack_from('<d', data, 0x74)[0] if len(data) > 0x7C else 0.0
    field_deg = math.degrees(abs(field_val)) if 0 < abs(field_val) < 0.1 else abs(field_val)

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
        surf = Surface(radius=r, thickness=d, glass=glass_for_surface[i], semi_diameter=sd)

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

    sys_obj.stop_surface = 1

    # Estimate BFD
    f_match = re.search(r"f'=?([\d.]+)", name)
    f_target = float(f_match.group(1)) if f_match else 100.0
    if sys_obj.surfaces:
        best_d = f_target * 0.15
        best_err = 1e10
        for trial_d in [f_target * k for k in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]]:
            sys_obj.surfaces[-1].thickness = trial_d
            from optics_engine import paraxial_trace as _pt
            _p = _pt(sys_obj)
            _f = abs(_p.get('focal_length', 0))
            _err = abs(_f - f_target)
            if _err < best_err:
                best_err = _err
                best_d = trial_d
        sys_obj.surfaces[-1].thickness = best_d

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
