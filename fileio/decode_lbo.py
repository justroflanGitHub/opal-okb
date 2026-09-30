"""LBO OPJ decoder v4 — anchor-based robust parsing.

Формат записи (компактный LBO), подтверждён дампами:
  [0x0C] имя (40b cp866), [0x34] num_surf, [0x38] num_wl
  [0xA8] кривизны C=1/R: num_surf × float64
  [..  ] толщины d: (num_surf-1..num_surf) × float64; последний слот = BFD
         (значение или маркер 1e20, если неизвестен)
  [..  ] индексы стёкол: (num_surf+1) × uint16; 1=воздух, 2..=стёкла,
         65534/65535 = зеркало; перед S0 — среда до первой поверхности
  [..  ] (опц.) индексы длин волн: num_wl × uint16
  [..  ] RI-таблица: [воздух × nwl] + [стекло_i × nwl] float64 (n≈0.9..2.6)
  [..  ] имена стёкол: cp866 'ВОЗДУХ'+имена (слоты) ЛИБО ASCII 'AIR'+G-разделители
  [..  ] 00 00, int32, полудиаметры: num_surf × float32

v4: парсинг от якоря блока имён (ВОЗДУХ/AIR) вместо хрупкого маркера 1e20;
    RI-переопределения показателей преломления назначаются ПО ИНДЕКСУ стекла,
    поэтому корректная трассировка работает даже при мусорных/дублирующихся
    именах (G, G) или полном отсутствии блока имён.
"""
import struct
import math
import re

from optics_engine import (OpticalSystem, Surface, Wavelength, FieldPoint,
                            ObjectType, ApertureType)
from optics_utils import wl_name as _wl_name_lookup, EPSILON

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

# --- Константы формата (единое место; см. docstring модуля) ---
VOZDUH_BYTES = 'ВОЗДУХ'.encode('cp866')
AIR_BYTES = b'AIR'
AIRISH_NAMES = ('ВОЗДУХ', 'AIR', '', 'A', 'А')
MIRROR_INDEXES = (0xFFFE, 0xFFFF)      # 65534/65535 — зеркальная поверхность
MARKER_MIN, MARKER_MAX = 1e15, 1e25    # 1e20-маркер конца толщин (BFD неизвестен)
RI_MIN, RI_MAX = 0.90, 2.60            # диапазон показателей преломления
RI_AIR_EPS = 0.001                     # |n - 1.0| < eps → строка воздуха
CURV_ABS_MAX = 100.0                   # |C| 1/мм
THICK_ABS_MAX = 1e4                    # |d| мм (998 мм телескопических BFD — валидны)
TEXT_EXTRA = b'+-./()%!'               # доп. ASCII-байты в именах (ВОДА+20С и т.п.)
GLASS_NAME_MAXLEN = 10
SD_MIN, SD_MAX = 0.05, 500.0           # разумные полудиаметры, мм


def _sane(v: float, lo: float, hi: float) -> bool:
    """Конечное значение в [lo, hi] (ноль допускается всегда)."""
    return math.isfinite(v) and (v == 0.0 or lo <= abs(v) <= hi)


def _is_text_byte(b: int) -> bool:
    """Байт, встречающийся в именах стёкол (cp866 + ASCII + спецсимволы)."""
    if b == 0x20 or b in TEXT_EXTRA:
        return True
    if 0x30 <= b <= 0x39:      # 0-9
        return True
    if 0x41 <= b <= 0x5A:      # A-Z
        return True
    if 0x61 <= b <= 0x7A:      # a-z
        return True
    if 0x80 <= b <= 0xAF:      # cp866 А-Я
        return True
    if 0xE0 <= b <= 0xEF:      # cp866 р-я
        return True
    return False


def _read_d(data, off):
    if off < 0 or off + 8 > len(data):
        return None
    return struct.unpack_from('<d', data, off)[0]


# ------------------------------------------------------------------
# Анализ блока имён стёкол
# ------------------------------------------------------------------

def _find_glass_anchor(data: bytes):
    """Найти якорь блока имён. → (kind, names_start) | (None, -1).

    kind: 'ru' — cp866 ВОЗДУХ; 'us' — ASCII AIR (имена с G-разделителями).
    """
    voz = data.find(VOZDUH_BYTES)
    if voz >= 0:
        return 'ru', voz
    # AIR: пропускаем вхождения внутри слов (LAKN13... не содержит, но
    # перестрахуемся: требуем соседний текстовый байт или границу)
    pos = 0
    while True:
        air = data.find(AIR_BYTES, pos)
        if air < 0:
            return None, -1
        after = data[air + 3] if air + 3 < len(data) else 0
        before = data[air - 1] if air > 0 else 0x20
        if _is_text_byte(after) and (_is_text_byte(before) or before == 0):
            # начало блока: отступаем назад по пробелам (слот "     AIR")
            start = air
            while start > 0 and data[start - 1] == 0x20 and air - start < 8:
                start -= 1
            return 'us', start
        pos = air + 1


def _glass_text_run(data: bytes, start: int) -> bytes:
    """Собрать непрерывный текстовый буфер блока имён."""
    end = start
    while end < len(data) and _is_text_byte(data[end]):
        end += 1
    return data[start:end]


def _split_russian_names(text: str) -> list:
    """Разбить склеенный текст русских имён стёкол (ВОЗДУХФ16Л7...)."""
    if text.startswith('ВОЗДУХ'):
        names = ['ВОЗДУХ']
        rest = text[6:].strip()
    else:
        names = []
        rest = text.strip()

    known_glasses = set()
    try:
        from glass_catalog import GLASS_CATALOG
        known_glasses = set(k.upper() for k in GLASS_CATALOG.keys())
    except Exception:
        pass
    known_glasses.update(['КВАРЦ', 'КВАРЦСТК', 'ФЛЮОРИТ', 'ЗЕРКАЛО', 'ВОДА+20С'])

    pos = 0
    while pos < len(rest):
        while pos < len(rest) and rest[pos] == ' ':
            pos += 1
        if pos >= len(rest):
            break
        best_match = None
        for glen in range(min(GLASS_NAME_MAXLEN, len(rest) - pos), 0, -1):
            candidate = rest[pos:pos + glen].upper()
            if candidate in known_glasses:
                best_match = rest[pos:pos + glen]
                break
        if best_match:
            names.append(best_match)
            pos += len(best_match)
        else:
            end = rest.find(' ', pos)
            if end < 0:
                end = len(rest)
            glass_name = rest[pos:end].strip()
            if glass_name:
                names.append(glass_name)
            pos = end
    return names


def _split_us_names(raw: bytes) -> list:
    """Имена US-формата: записи с G-разделителем ("AIR","G","SF5","G",...).

    → список имён ['AIR', ''(generic), 'SF5', ...]; '' = безымянное generic-стекло.
    Обрезка/дополнение до нужного числа — в вызывающем коде (нужно знать ng).
    """
    text = raw.decode('latin-1', errors='replace').replace('\x00', ' ')
    names = [p.strip() for p in text.split('G')]
    return [n if n else '' for n in names]


# ------------------------------------------------------------------
# RI-таблица и индексы
# ------------------------------------------------------------------

def _scan_ri_backward(data: bytes, names_start: int, floor: int):
    """RI-таблица примыкает к блоку имён снизу (с допуском на выравнивание).

    → (ri_values, ri_start) | ([], -1)
    """
    best = ([], -1)
    for pad in range(16):
        vals = []
        off = names_start - pad - 8
        while off >= floor and len(vals) < 256:
            v = _read_d(data, off)
            if v is None or not (RI_MIN < v < RI_MAX):
                break
            vals.append(v)
            off -= 8
        vals.reverse()
        if len(vals) > len(best[0]):
            best = (vals, names_start - pad - 8 * len(vals) + 8)
    return best


def _scan_ri_forward(data: bytes, start: int, limit: int = 64):
    """RI-таблица вперёд (fallback, когда блок имён не найден).

    Начинаем с start, идём 8-байтовыми шагами (пробуя выравнивания 0..7),
    собираем double в RI-диапазоне, стоящие сплошной полосой.
    """
    best = []
    for pad in range(8):
        vals = []
        off = start + pad
        while off + 8 <= len(data) and len(vals) < limit:
            v = _read_d(data, off)
            if v is None or not (RI_MIN < v < RI_MAX):
                break
            vals.append(v)
            off += 8
        if len(vals) > len(best):
            best = vals
        if len(best) >= 8 and best[0] == 1.0:
            break
    return best


def _ri_layout(ri: list, ng: int, num_wl: int):
    """Определить (nair, nwl) для RI-таблицы: total = nair + ng*nwl.

    Приоритет: таблицы с ведущей строкой воздуха (≈1.0); nair=0 только если
    ri не начинается с 1.0 вовсе (водные системы без воздушной строки).
    """
    total = len(ri)
    if ng <= 0 or total <= 0:
        return 0, 0
    nair_lead = 0
    for v in ri:
        if abs(v - 1.0) < RI_AIR_EPS:
            nair_lead += 1
        else:
            break
    # приоритет: заявленное num_wl, затем типичные 3, потом убывание
    candidates = [num_wl, 3, 4, 2, 5, 6, 7, 8, 1]
    if nair_lead > 0:
        for nwl in candidates:
            if nwl <= 0:
                continue
            nair = total - ng * nwl
            if 1 <= nair <= min(nair_lead, nwl):
                return nair, nwl
        return 0, 0
    # без ведущей строки воздуха: возможна раскладка nair=0
    for nwl in candidates:
        if nwl <= 0:
            continue
        if total == ng * nwl:
            return 0, nwl
    return 0, 0


def _scan_indices(data: bytes, thick_end: int, idx_end: int, num_surf: int,
                  limit: int):
    """Индексы стёкол — окно uint16 между толщинами и RI-блоком.

    Окно может начинаться с мусора (хвост маркера/выравнивание) — пробуем
    каждое смещение, пока не найдём непрерывную серию из num_surf+1 валидных
    значений (<= limit, 0 или зеркальные). Ведущие/хвостовые нули серии
    отбрасываются.
    → список длиной num_surf+1 (по умолчанию 1=воздух).
    """
    if idx_end <= thick_end:
        return [1] * (num_surf + 1)
    need = num_surf + 1
    window_end = min(idx_end, thick_end + (num_surf + 16) * 2)

    def _valid(v):
        return v == 0 or v <= limit or v in MIRROR_INDEXES

    raw = None
    for start in range(thick_end, window_end - need * 2 + 2, 2):
        off = start
        run = []
        while off + 2 <= window_end and len(run) < need + 8:
            v = struct.unpack_from('<H', data, off)[0]
            if _valid(v):
                run.append(v)
                off += 2
            else:
                break
        if len(run) >= need:
            raw = run
            break
    if raw is None:
        return [1] * need
    while raw and raw[0] == 0:
        raw.pop(0)
    while raw and raw[-1] == 0:
        raw.pop()
    if len(raw) == need:
        return raw
    if len(raw) > need:
        return raw[:need] if raw[0] == 1 else raw[-need:]
    return ([1] + raw + [1] * need)[:need]


# ------------------------------------------------------------------
# Полудиаметры
# ------------------------------------------------------------------

def _scan_semi_diameters(data: bytes, names_end: int, num_surf: int):
    """Полудиаметры: после блока имён → 00 00, счётчик (int32 или int16), float32 × num_surf."""
    off = names_end
    # пропуск NUL/пробелов
    limit = min(names_end + 16, len(data))
    while off < limit and data[off] in (0x00, 0x20):
        off += 1
    if off + 4 > len(data):
        return []
    # счётчик: int32 (обычно 2*num_surf) или int16
    cnt32 = struct.unpack_from('<I', data, off)[0]
    if cnt32 <= 0x200:
        off += 4
    else:
        cnt16 = cnt32 & 0xFFFF
        if cnt16 > 0x200:
            return []
        off += 2
    sds = []
    for i in range(num_surf):
        if off + 4 > len(data):
            break
        v = struct.unpack_from('<f', data, off)[0]
        off += 4
        if math.isnan(v) or math.isinf(v) or not (SD_MIN <= v <= SD_MAX):
            return []
        sds.append(v)
    return sds if len(sds) == num_surf else []


# ------------------------------------------------------------------
# Основной декодер
# ------------------------------------------------------------------

def decode_lbo_opj(data: bytes) -> OpticalSystem:
    if len(data) < 0x40:
        return OpticalSystem(name="empty")

    name = data[0x0C:0x34].decode('cp866', errors='replace').replace('\x00', '').strip()
    num_surf = struct.unpack_from('<H', data, 0x34)[0]
    num_wl = struct.unpack_from('<H', data, 0x38)[0]
    if not (0 < num_surf <= 50):
        num_surf = 0
    if not (0 < num_wl <= 10):
        num_wl = 0
    if num_surf == 0:
        return OpticalSystem(name=name)

    # 1. Кривизны: num_surf × float64 от 0xA8; при мусоре — сдвиг заголовка;
    #    если и это не нашлось — raw-чтение (совместимость со старым поведением:
    # мусорные ~0 кривизны дают плоские поверхности вместо пустой системы)
    curvatures = []
    curv_off = 0xA8
    for attempt_off in range(0xA8, 0xA8 + 0xE0, 8):
        vals = []
        ok = True
        for i in range(num_surf):
            v = _read_d(data, attempt_off + i * 8)
            if v is None or not math.isfinite(v) or not _sane(v, 1e-12, CURV_ABS_MAX):
                ok = False
                break
            vals.append(v)
        if ok:
            curvatures = vals
            curv_off = attempt_off
            break
    if not curvatures:
        raw_fallback = True
        curvatures = []
        for i in range(num_surf):
            v = _read_d(data, 0xA8 + i * 8)
            if v is None or not math.isfinite(v):
                v = 0.0
            curvatures.append(v)
        curv_off = 0xA8
    else:
        raw_fallback = False
    thick_off = curv_off + num_surf * 8
    floor = thick_off

    # 2. Толщины: до num_surf слотов; последний = BFD (значение или маркер 1e20)
    thicknesses = []
    bfd_unknown = False
    slots_consumed = 0
    for i in range(num_surf):
        v = _read_d(data, thick_off + i * 8)
        if v is None:
            break
        slots_consumed = i + 1
        if MARKER_MIN < abs(v) < MARKER_MAX:
            if i == num_surf - 1:
                bfd_unknown = True    # BFD неизвестен — вычислим параксиально
                break
            elif i == num_surf - 2:
                # standalone .OPJ: последняя поверхность в счётчике служебная
                # (например, плоскость изображения); реальных — на одну меньше,
                # маркер стоит в её слоте BFD
                num_surf = i + 1
                curvatures = curvatures[:num_surf]
                thicknesses = thicknesses[:num_surf]
                slots_consumed = i + 1
                bfd_unknown = True
                break
            else:
                num_surf = i          # маркер внутри — реальных поверхностей меньше
                curvatures = curvatures[:num_surf]
                thicknesses = thicknesses[:num_surf]
                slots_consumed = i
                break
        if not _sane(v, 1e-12, THICK_ABS_MAX) and not (raw_fallback and math.isfinite(v)):
            slots_consumed = i
            break
        thicknesses.append(v if _sane(v, 1e-12, THICK_ABS_MAX) else 0.0)
    if num_surf == 0:
        return OpticalSystem(name=name)
    while len(thicknesses) < num_surf:
        thicknesses.append(0.0)
    if bfd_unknown:
        thicknesses[-1] = 0.0
    # после num_surf полных толщин может стоять завершающий маркер 1e20 —
    # пропускаем его при определении конца блока толщин
    if slots_consumed >= num_surf:
        v_extra = _read_d(data, thick_off + num_surf * 8)
        if v_extra is not None and MARKER_MIN < abs(v_extra) < MARKER_MAX:
            slots_consumed = num_surf + 1
    thick_end = thick_off + max(slots_consumed, len(thicknesses)) * 8

    # 3. Якорь блока имён
    kind, names_start = _find_glass_anchor(data)
    names = []
    names_end = -1
    if kind is not None:
        raw = _glass_text_run(data, names_start)
        names_end = names_start + len(raw)
        if kind == 'ru':
            names = _split_russian_names(raw.decode('cp866', errors='replace'))
        else:
            names = _split_us_names(raw)

    # 4. RI-таблица (от якоря имён назад; при отсутствии якоря — вперёд)
    ri, ri_start = [], -1
    if names_start >= 0:
        ri, ri_start = _scan_ri_backward(data, names_start, floor)
    if not ri:
        ri = _scan_ri_forward(data, thick_end + (num_surf + 1) * 2)

    # 5. Индексы стёкол: окно между толщинами и RI
    ng_names = max(len(names) - 1, 0)
    idx_limit = ng_names + 2 if ng_names else 64
    idx_end = ri_start if ri_start > 0 else (
        names_start if names_start >= 0 else thick_end + (num_surf + 1) * 2)
    glass_idx = _scan_indices(data, thick_end, idx_end, num_surf, idx_limit)
    max_gi = max((g for g in glass_idx if g not in MIRROR_INDEXES), default=1)
    ng = max(max_gi - 1, 0)

    # 5a. Подгоняем число имён под фактическое ng (US-формат: G-разделители)
    if ng > 0 and len(names) >= 1:
        if len(names) < ng + 1:
            # пробуем 'J'-склейки (BAF3JLASF013 → BAF3 + JLASF013)
            while len(names) < ng + 1:
                for k, nm in enumerate(names):
                    j = nm.find('J', 1)
                    if j > 1 and j + 1 < len(nm):
                        names[k] = nm[:j]
                        names.insert(k + 1, nm[j:])
                        break
                else:
                    break
            names = names + [''] * (ng + 1 - len(names))
        else:
            names = names[:ng + 1]

    # 5b. RI-раскладка [воздух × nwl] + [стёкла × nwl];
    #     строк в таблице = по именам (могут быть неиспользуемые стёкла),
    #     но не меньше max_gi-1 (безымянные generic-стёкла)
    ri_ng = max(len(names) - 1, ng) if names else ng
    nair, nwl = _ri_layout(ri, ri_ng, num_wl)

    # 5c. n_override по индексу стекла (строка RI-таблицы)
    def ri_row_for(gi):
        if not ri or nwl <= 0 or gi < 2:
            return []
        row = nair + (gi - 2) * nwl
        return ri[row:row + nwl]

    # 6. Полудиаметры
    semi_diameters = []
    if names_end >= 0:
        semi_diameters = _scan_semi_diameters(data, names_end, num_surf)

    # 7. Длины волн: индексы между индексами стёкол и RI; при нуле — стандарт
    wavelengths = []
    wl_probe = (thick_end + (num_surf + 1) * 2)
    for i in range(num_wl):
        off = wl_probe + i * 2
        if off + 2 > len(data):
            break
        wavelengths.append(OPAL_WL.get(struct.unpack_from('<H', data, off)[0], 0.0))
    wavelengths = [w for w in wavelengths if w > 0.0]
    if not wavelengths:
        from optics_engine import _std_wavelengths
        wavelengths = [w.value for w in _std_wavelengths()]

    # 8. Служебные поля заголовка
    obj_type_code = struct.unpack_from('<H', data, 0x3C)[0] if len(data) > 0x3D else 0
    stop_type_code = struct.unpack_from('<H', data, 0x46)[0] if len(data) > 0x47 else 0
    field_val = struct.unpack_from('<d', data, 0x74)[0] if len(data) > 0x7C else 0.0
    if 0 < abs(field_val) < 1.0:
        field_deg = math.degrees(abs(field_val))
    elif abs(field_val) >= 1.0:
        field_deg = abs(field_val)
    else:
        field_deg = 0.0
    stop_surface_num = struct.unpack_from('<H', data, 0x3A)[0] if len(data) > 0x3B else 0
    ap_val_5c = abs(struct.unpack_from('<d', data, 0x5C)[0]) if len(data) > 0x63 else 0.0
    if math.isnan(ap_val_5c) or ap_val_5c > 1e4:
        ap_val_5c = 0.0
    stop_offset = struct.unpack_from('<d', data, 0x6C)[0] if len(data) > 0x73 else 0.0
    if math.isnan(stop_offset):
        stop_offset = 0.0

    sys_obj = OpticalSystem(name=name)
    sys_obj.object_type = ObjectType.FINITE if obj_type_code == 1 else ObjectType.INFINITE
    img_type_3e = struct.unpack_from('<H', data, 0x3E)[0] if len(data) > 0x3F else 1
    sys_obj.image_type = ObjectType.FINITE if img_type_3e == 1 else ObjectType.INFINITE
    sys_obj.object_height = field_deg if field_deg > 0.001 else 0.0

    if ap_val_5c > 0 and ap_val_5c < 1.0:
        sys_obj.aperture_type = ApertureType.NUMERICAL_APERTURE
        sys_obj.aperture_value = ap_val_5c
    else:
        sys_obj.aperture_type = ApertureType.ENTRANCE_PUPIL
        if ap_val_5c >= 1.0:
            sys_obj.aperture_value = ap_val_5c * 2
        elif semi_diameters:
            sys_obj.aperture_value = max(semi_diameters) * 2
        else:
            sys_obj.aperture_value = 20.0

    sys_obj.wavelengths = [Wavelength(wl, 1.0, _wl_name_lookup(wl)) for wl in wavelengths]
    sys_obj.field_points = [FieldPoint(0.0)]
    if field_deg > 0:
        sys_obj.field_points.append(FieldPoint(field_deg))

    # 9. Поверхности
    for i in range(num_surf):
        c = curvatures[i] if i < len(curvatures) else 0.0
        r = 1.0 / c if abs(c) > EPSILON else 0.0
        d = thicknesses[i] if i < len(thicknesses) else 0.0
        sd = semi_diameters[i] if i < len(semi_diameters) else 0.0  # 0 → заменим по апертуре

        gi = glass_idx[i + 1] if i + 1 < len(glass_idx) else 1
        gi_before = glass_idx[i] if i < len(glass_idx) else 1
        is_mirror = gi in MIRROR_INDEXES or gi_before in MIRROR_INDEXES

        glass = ''
        if is_mirror:
            glass = 'ЗЕРКАЛО'
        elif 1 <= gi - 1 < len(names):
            gname = names[gi - 1]
            if gname.upper() not in AIRISH_NAMES:
                glass = gname

        surf = Surface(radius=r, thickness=d, glass=glass, semi_diameter=sd)
        if is_mirror:
            surf.is_reflective = True
            surf.glass = 'ЗЕРКАЛО'

        row = ri_row_for(gi)
        if row and not is_mirror:
            n_ov = {}
            for wi, wl_val in enumerate(wavelengths[:len(row)]):
                n_ov[wl_val] = row[wi]
            if n_ov:
                surf.n_override = n_ov
        elif is_mirror and ri:
            # зеркальная поверхность — среда не меняется, но медиум перед ней
            # мог быть стеклом; n_override не нужен
            pass

        sys_obj.surfaces.append(surf)

    # 10. Диафрагма
    if 1 <= stop_surface_num <= num_surf:
        sys_obj.stop_surface = stop_surface_num
    else:
        sys_obj.stop_surface = 1
    sys_obj.stop_offset = stop_offset
    sys_obj.stop_type = {0: 'd', 1: 'z', 65535: 'p'}.get(stop_type_code, 'd')

    # 11. BFD, апертура NA→D, починка полудиаметров (как в v3)
    if sys_obj.surfaces:
        from optics_engine import paraxial_trace as _pt
        _parax = _pt(sys_obj)
        _bfd = _parax.get('back_focal_distance', 0)
        if _bfd and abs(_bfd) > 0.1:
            sys_obj.surfaces[-1].thickness = abs(_bfd)

        if sys_obj.aperture_type == ApertureType.NUMERICAL_APERTURE and sys_obj.aperture_value < 1.0:
            _efl = _parax.get('focal_length', 0) or _parax.get('effective_focal_length', 0)
            if _efl and abs(_efl) > 0.1:
                _D = 2.0 * sys_obj.aperture_value * abs(_efl)
                if _D > 1.0:
                    sys_obj.aperture_value = _D
                    sys_obj.aperture_type = ApertureType.ENTRANCE_PUPIL

        _ap_eff = sys_obj.aperture_value
        if _ap_eff > 1.0:
            _min_sd = _ap_eff / 4.0
            for s in sys_obj.surfaces:
                if s.semi_diameter <= 0 or s.semi_diameter > 1e6 or s.semi_diameter < _min_sd:
                    s.semi_diameter = _ap_eff / 2.0 * 1.1

    return sys_obj


if __name__ == '__main__':
    import io
    import sys as _sys
    _sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding='utf-8')
    from optics_engine import paraxial_trace
    from lbo_reader import load_lbo_fast

    systems = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
    print('=== Индустар-23у f\'=110 ===')
    s = decode_lbo_opj(systems[3]['opj_data'])
    for i, surf in enumerate(s.surfaces):
        print(f'  S{i}: R={surf.radius:>8.2f}, d={surf.thickness:.2f}, '
              f'glass={surf.glass or "воздух":<6}, D/2={surf.semi_diameter:.2f}')
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
