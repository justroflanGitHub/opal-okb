# -*- coding: utf-8 -*-
"""
OPAL-OKB — OPAL-таблицы по полю: TABGL + TABPR2 (реверс §15, волна 5).

**TABGL** «Характеристики главных лучей пучков» (формат DS 0x9ea:
``(1x,i2,2(f7.3,f12.6),f9.4,f11.6,2f9.4,2f8.4)``; шапка 0xa22–0xb2d;
эталон — extracted/opal_okb/RT__2250.PRN, система «IR -.2X D=10 2W=72
10L 2USP» = запись 1 USBINOCL.LBO): сводка по зонам поля величин §7–§8
двойников порта —

===============  =====================  ================================
колонка OPAL     величина               источник порта
===============  =====================  ================================
предмет отн.     зона поля √(k/n)       :func:`field_zones`
предмет гр.мнсек −ω зоны (град)         :func:`_zone_field`
изображ. отн.    tan(ω'_z)/tan(ω'_max)  главный луч (см. :func:`_chief_exit`)
изображ. гр.мнсек ω' выхода (град)      он же
дисторсия %      (y'−y'_parax)/y'_parax как ``compute_field_aberrations``
дисторсия гр.мнсек Δω' = ω'−ω'_parax    реконструкция по эталону
Z'm, Z's         астигмат. отрезки, мм  :func:`aberrations.coddington_trace`
C'm, C's         радиусы каустики, мм   :func:`aberrations.caustic_radii`
===============  =====================  ================================

**TABPR2** «Хроматизм увеличения/положения» (формат DS 0xb3e:
``(1x,i3,4f9.4,2f10.5,2f9.4)``; шапка 0xb64–0xc3d, колонки — из дампа
OPALA.EXE: «Хроматизм увеличения Относительный/Абсолютный», «Хроматизм
положения Меридиональный/Сагиттальный», «Del %», «Dy'», «Z'm», «Z's»):
хроматические двойники величин TABGL на второй длине волны — механизм §9
(повторный прогон трейсера на другой λ), здесь — повторный прогон тех же
лучей с ``wl = wl_alt``. Хвост таблицы (Del %, Dy', Z'm, Z's) — величины
TABGL на λ₂ [ГИПОТЕЗА имени: «Del» = дисторсия, ср. REVERSE_MAP «Дисторсия
Del%»; «PR2» — НЕИЗВЕСТНО].

Форматы чисел — FORTRAN Fw.d **без ведущего нуля** («.816», «-.535640»;
нуль — «.0000», эталон RT__2250, строка N=0): эмуляция
:func:`_fwo`.

Расшифровка угловой меры «(гр.мнсек)» (эталон RT__2250, сверка
побайтово): печатается **градусы + минуты/100** — дробная часть числа
есть угловые минуты с десятыми-тысячными (``deg + min/100``), а НЕ
градусы×3600 (гипотеза ТЗ опровергнута эталоном). Верификация по
эталону: изображ. ω'=9.09104° → 9°05.4624' → печатано «9.054624» (точно);
дисторсия Δω'=−0.89273° → −0°53.564' → «-.535640» (точно); предмет зоны
√(2/3) от 36°: ω=30.657° → 30°39.43' → «-30.394300» (точно); «2W=72»
шапки ↔ −36.000000 (градусы).
"""
import math

from optics_engine import OpticalSystem, ObjectType, paraxial_trace
from optics_utils import get_primary_wl

from analysis.aberrations import (
    CODDINGTON_SD_INFLATE, _compute_ray_start, _exit_line, _field_chief_ray,
    caustic_radii, coddington_trace,
)
from analysis.chromatism import PAIR_WL_TOL
from utils.spectral_lines import spectral_line_by_name

#: λ линий C и d (мкм) — пара fallback «d→C» для монохромных систем.
WL_C = spectral_line_by_name('C').wavelength_nm / 1000.0
WL_D = spectral_line_by_name('d').wavelength_nm / 1000.0

#: Запас полудиаметров при трассировке главных лучей (как
#: ``compute_field_aberrations``/``coddington_trace``).
_SD_INFLATE = CODDINGTON_SD_INFLATE

#: Ширины полей строк данных TABGL (после «1x,i2»): f7.3, f12.6 ×2 пары,
#: f9.4 (дисторсия %), f11.6, f9.4 ×2, f8.4 ×2 — формат DS 0x9ea.
TABGL_FIELD_SPECS = ((7, 3), (12, 6), (7, 3), (12, 6), (9, 4),
                     (11, 6), (9, 4), (9, 4), (8, 4), (8, 4))

#: То же для TABPR2 (после «1x,i3»): 4×f9.4, 2×f10.5, 2×f9.4 — DS 0xb3e.
TABPR2_FIELD_SPECS = ((9, 4), (9, 4), (9, 4), (9, 4),
                      (10, 5), (10, 5), (9, 4), (9, 4))

#: Заголовок TABGL — эталон RT__2250.PRN (шапка DS 0xa22–0xb2d).
TABGL_HEADER = (
    '               Характеристики главных лучей пучков',
    ' ═ N│ Величина предмета│Величина изображ. │ Д и с т о р с и я │'
    'Астигмат.отрезки│Радиусы каустики',
    ' ═  │относ.│ (гр.мнсек)│относ.│ (гр.мнсек)│   %    │(гр.мнсек │'
    "  Z'm   │  Z's  │  C'm   │  C's",
    ' ═──┴──────┴───────────┴──────┴───────────┴────────┴──────────┴'
    '────────┴───────┴────────┴───────',
)

#: Заголовок TABPR2 — реконструкция по строкам шапки DS 0xb64–0xc3d
#: (точная нарезка строк печатальщика неизвестна — [ГИПОТЕЗА] выравнивания).
TABPR2_HEADER = (
    '               Хроматизм увеличения/положения',
    ' ═ N  │  Хроматизм  увеличения       │   Хроматизм положения     ═',
    ' ═    │  Относительный  Абсолютный  │  Меридиональный Сагиттальный'
    "  ═    │    Del %      Dy'   │     Z'm     Z's",
    ' ═────┴' + '─' * 8 + '┴' + '─' * 8 + '┴' + '─' * 8 + '┴' + '─' * 8
    + '┴' + '─' * 9 + '┴' + '─' * 9 + '┴' + '─' * 8 + '┴' + '─' * 8,
)


# ── Форматы чисел ─────────────────────────────────────────────────────────

def _fwo(value, width: int, decimals: int) -> str:
    """Поле FORTRAN ``Fw.d`` в стиле печати OPAL — без ведущего нуля.

    FORTRAN/Python дают «  0.816»; OPAL печатает «   .816», «   -.535640»
    (эталон RT__2250: ширина поля сохраняется, ведущий нуль мантиссы не
    печатается). ``None`` (луч не дошёл) — пробелы. Отрицательный нуль
    («-.0000») печатается как положительный (эталон, строка N=0).
    """
    if value is None:
        return ' ' * width
    text = f'{value:.{decimals}f}'
    if text.startswith('0.'):
        text = text[1:]
    elif text.startswith('-0.'):
        text = '-' + text[2:]
        # минус при нулевой мантиссе не печатается: -0.0000 → .0000
        if set(text[2:]) <= {'0'}:
            text = text[1:]
    if len(text) > width:                 # переполнение Fw.d — как FORTRAN
        return '*' * width
    return text.rjust(width)


def _grminsec(angle_deg: float) -> float:
    """Угол (град) в печатную меру «гр.мнсек»: градусы + минуты/100.

    Эталон RT__2250: 9.09104° → 9.054624; −0.89273° → −0.535640;
    −36° → −36.000000. Обратно: :func:`_from_grminsec`.
    """
    sign = -1.0 if angle_deg < 0 else 1.0
    a = abs(angle_deg)
    deg = math.floor(a)
    return sign * (deg + (a - deg) * 0.6)


def _from_grminsec(value: float) -> float:
    """Обратное преобразование «гр.мнсек» в градусы (для тестов/разбора)."""
    sign = -1.0 if value < 0 else 1.0
    a = abs(value)
    deg = math.floor(a + 1e-9)
    return sign * (deg + (a - deg) / 0.6)


# ── Зоны поля и углы ──────────────────────────────────────────────────────

def field_zones(n_zones: int) -> list:
    """Зоны поля равной площади: 1, √((n−1)/n), …, √(1/n).

    Эталон RT__2250 при n=3: 1.000/.816/.577 = 1, √(2/3), √(1/3)
    (зоны по квадрату поля — та же схема, что зоны зрачка RT__2236:
    1/.866/.707/.5).
    """
    n_zones = max(1, int(n_zones))
    return [math.sqrt(k / n_zones) for k in range(n_zones, 0, -1)]


def max_field(system: OpticalSystem) -> float:
    """Максимальное поле системы (град для INFINITE / мм для FINITE).

    Порядок как ``_reference_field_deg``: точки поля → object_height;
    без fallback (0.0 = поля нет — табличный вывод только осевой).
    """
    fields = [abs(fp.y) for fp in (system.field_points or [])]
    if fields:
        return max(fields)
    height = getattr(system, 'object_height', 0) or 0
    return abs(height)


def _zone_field(system: OpticalSystem, zone: float, field_max: float):
    """Поле зоны: (field_y для трейсера, ω предмета в град, со знаком OPAL).

    Зона — доля параксиальной высоты изображения. Дальний тип:
    y'_parax ∝ tan(ω) ⇒ ω = atan(zone·tan(ω_max)) (эталон: зона √(2/3)
    от 36° → 30.677° vs печать «-30.394300» = 30.657°, совпадение
    ≤0.08%). Ближний тип: зона — доля высоты предмета, угол от первой
    поверхности.

    Знак OPAL: предмет печатается отрицательным (эталон −36.000000 при
    поле +36°), трассировка ведётся в той же системе знаков.
    """
    if system.object_type == ObjectType.INFINITE:
        omega = math.degrees(math.atan(zone * math.tan(
            math.radians(field_max))))
        return -omega, -omega
    d_obj = abs(system.surfaces[0].thickness) if system.surfaces else 50.0
    height = zone * field_max
    omega = math.degrees(math.atan2(height, d_obj)) if d_obj > 0 else 0.0
    return -height, -omega


def _chief_exit(system: OpticalSystem, wl: float, field_y: float,
                parax: dict = None):
    """Главный луч поля: ``(y' на изображении, ω' выхода в град)``.

    Трассировка с запасом полудиаметров (приём
    ``compute_field_aberrations``: главный луч косого пучка на краю поля
    упирается в исходные кромки LBO). ``None`` — луч не прошёл.
    """
    if not system.surfaces:
        return None
    parax = parax if parax is not None else paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)
    ray = _field_chief_ray(system, field_y, z_start, z_pupil)
    orig = [s.semi_diameter for s in system.surfaces]
    for s in system.surfaces:
        if s.semi_diameter > 0:
            s.semi_diameter = abs(s.semi_diameter) * _SD_INFLATE
    try:
        line = _exit_line(system, ray, wl)
    finally:
        for i, s in enumerate(system.surfaces):
            s.semi_diameter = orig[i]
    if line is None:
        return None
    return line[1], math.degrees(math.atan(line[4]))


def _paraxial_image_height(system: OpticalSystem, field_y: float,
                           parax: dict) -> float:
    """Параксиальная высота изображения для поля ``field_y``.

    Дальний тип: y' = f'·tan(ω) (как ``compute_field_aberrations``);
    ближний: y' = V·h (при нулевом V — сама высота предмета, там же).
    """
    if system.object_type == ObjectType.INFINITE:
        return parax.get('focal_length', 0.0) * math.tan(
            math.radians(field_y))
    v = parax.get('V', 0.0) or 0.0
    return v * field_y if abs(v) > 1e-12 else field_y


def _axial_row(**extra) -> dict:
    """Осевая строка N=0 (вся — нули, эталон RT__2250)."""
    row = {'n': 0, 'zone': 0.0}
    for key in ('obj_rel', 'obj_grminsec', 'img_rel', 'img_grminsec',
                'distortion_pct', 'distortion_grminsec',
                'z_m', 'z_s', 'c_m', 'c_s',
                'mag_rel_pct', 'mag_abs_mm', 'pos_m_mm', 'pos_s_mm',
                'del_pct', 'dy_prime_mm'):
        row[key] = 0.0
    row.update(extra)
    return row


# ── TABGL ─────────────────────────────────────────────────────────────────

def tabgl_rows(system: OpticalSystem, n_zones: int = 3,
               wl: float = None) -> list:
    """Сводка главных лучей по зонам поля (TABGL, реверс §15.1).

    Для каждой зоны поля (N = 1..n_zones от края к центру, зоны
    :func:`field_zones`): предмет отн.+угол, изображение отн.+угол,
    дисторсия %+угол, Z'm, Z's (отрезки от плоскости Гаусса, §7),
    C'm, C's (радиусы каустики, §8). Замыкает осевая строка N=0 (все
    нули, эталон). Расчёты не дублируются: след Коддингтона —
    :func:`aberrations.coddington_trace`, каустики —
    :func:`aberrations.caustic_radii`, главный луч — общий хелпер
    ``_exit_line`` (как ``compute_chromatism_opal``).

    Args:
        system: Оптическая система (не изменяется).
        n_zones: Число зон поля (0-я осевая строка добавляется сверх).
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        Список словарей-строк (ключи ``n, zone, obj_rel,
        obj_grminsec, img_rel, img_grminsec, distortion_pct,
        distortion_grminsec, z_m, z_s, c_m, c_s``; угловые «гр.мнсек»-
        значения уже в печатной мере :func:`_grminsec`). Величина
        ``None`` — главный луч зоны не дошёл (вывод — пробелы).
        При нулевом поле — единственная осевая строка.
    """
    if wl is None:
        wl = get_primary_wl(system)
    rows = []
    field_max = max_field(system)
    if field_max <= 0 or not system.surfaces:
        return [_axial_row()]

    parax = paraxial_trace(system)
    zones = field_zones(n_zones)
    entries = []
    for zone in zones:
        field_y, obj_angle = _zone_field(system, zone, field_max)
        exit_pair = _chief_exit(system, wl, field_y, parax)
        y_img, w_exit = (exit_pair if exit_pair is not None
                         else (None, None))
        y_parax = _paraxial_image_height(system, field_y, parax)
        if y_img is not None and abs(y_parax) > 1e-12:
            dist_pct = (y_img - y_parax) / y_parax * 100.0
        else:
            dist_pct = None

        cod = coddington_trace(system, wl=wl, field_y=field_y)
        cau = caustic_radii(system, wl=wl, field_y=field_y)
        entries.append({
            'zone': zone,
            'obj_rel': zone,
            'obj_grminsec': _grminsec(obj_angle),
            'y_img': y_img,
            'w_exit': w_exit,
            'dist_pct': dist_pct,
            'z_m': cod.get('delta_zm') if cod else None,
            'z_s': cod.get('delta_zs') if cod else None,
            'c_m': cau.get('r_m') if cau else None,
            'c_s': cau.get('r_s') if cau else None,
        })

    # ω' полной зоны — знаменатель «изображ. относ.» (tan-пропорция,
    # эталон .841/.614 = tan(ω'_z)/tan(ω'_max)); k=1.0 при вырождении
    tan_full = (math.tan(math.radians(entries[0]['w_exit']))
                if entries[0]['w_exit'] is not None else 0.0)
    for idx, e in enumerate(entries, start=1):
        if e['w_exit'] is not None and abs(tan_full) > 1e-15:
            img_rel = math.tan(math.radians(e['w_exit'])) / tan_full
        else:
            img_rel = None

        # Угловой двойник дисторсии: ω'_parax из той же относительной
        # ошибки, что % (tan(ω'_parax) = tan(ω')/(1+d/100)); эталон
        # zone1: Δω' = −0.895° ≈ печать «-.535640» (реконструкция ±2%)
        dist_gms = None
        if e['w_exit'] is not None and e['dist_pct'] is not None \
                and abs(1.0 + e['dist_pct'] / 100.0) > 1e-9:
            w_parax = math.degrees(math.atan(math.tan(
                math.radians(e['w_exit'])) / (1.0 + e['dist_pct'] / 100.0)))
            dist_gms = _grminsec(e['w_exit'] - w_parax)

        rows.append({
            'n': idx,
            'zone': e['zone'],
            'obj_rel': e['obj_rel'],
            'obj_grminsec': e['obj_grminsec'],
            'img_rel': img_rel,
            'img_grminsec': _grminsec(e['w_exit'])
            if e['w_exit'] is not None else None,
            'distortion_pct': e['dist_pct'],
            'distortion_grminsec': dist_gms,
            'z_m': e['z_m'],
            'z_s': e['z_s'],
            'c_m': e['c_m'],
            'c_s': e['c_s'],
        })
    rows.append(_axial_row())
    return rows


def format_tabgl(rows) -> str:
    """Таблица TABGL целиком: заголовок эталона + строки данных.

    Данные — формат DS 0x9ea плюс один ведущий пробел печатальщика
    (строки эталона 96 символов: 1x+1x+i2 = 4 позиции на N).
    """
    lines = list(TABGL_HEADER)
    for row in rows:
        values = (row.get('n'), row.get('obj_rel'), row.get('obj_grminsec'),
                  row.get('img_rel'), row.get('img_grminsec'),
                  row.get('distortion_pct'), row.get('distortion_grminsec'),
                  row.get('z_m'), row.get('z_s'),
                  row.get('c_m'), row.get('c_s'))
        n_field = f'{values[0]:2d}' if values[0] is not None else '  '
        line = '  ' + n_field + ''.join(
            _fwo(v, w, d) for v, (w, d) in zip(values[1:], TABGL_FIELD_SPECS))
        lines.append(line.rstrip())
    return '\n'.join(lines)


# ── TABPR2 ────────────────────────────────────────────────────────────────

def _resolve_alt_wl(system: OpticalSystem, wl_main: float,
                    wl_alt: float = None) -> float:
    """Вторая длина волны пары (мкм).

    Явная ``wl_alt`` → она; иначе первая отличная λ из
    ``system.wavelengths``; иначе пара «d→C»: C, а если основная сама C —
    d (монохромный fallback задачи).
    """
    if wl_alt is not None:
        return float(wl_alt)
    for w in system.wavelengths:
        value = float(w.value)
        if abs(value - wl_main) >= PAIR_WL_TOL:
            return value
    alt = WL_C if abs(WL_C - wl_main) >= PAIR_WL_TOL else WL_D
    return alt


def tabpr2_rows(system: OpticalSystem, wl_main: float = None,
                wl_alt: float = None, n_zones: int = 3) -> list:
    """Хроматизм увеличения/положения по зонам поля (TABPR2, §15.2).

    Повторный расчёт величин TABGL на второй λ (механизм §9 — тот же
    луч, другие показатели преломления; порт трассирует с ``wl=wl_alt``
    напрямую). Для каждой зоны:

    * ``mag_rel_pct`` — хроматизм увеличения относительный,
      (y'₂−y'₁)/y'₁·100 (%);
    * ``mag_abs_mm`` — хроматизм увеличения абсолютный, y'₂−y'₁ (мм);
    * ``pos_m_mm``, ``pos_s_mm`` — хроматизм положения меридиональный/
      сагиттальный, ΔZ'm/ΔZ's (мм);
    * ``del_pct`` — дисторсия на λ₂ (%) [ГИПОТЕЗА: «Del» = дисторсия];
    * ``dy_prime_mm`` — высота главного луча y' на λ₂ (мм);
    * ``z_m``, ``z_s`` — астигматические отрезки на λ₂ (мм).

    Осевая строка N=0 — нули (как TABGL; эталонного вывода TABPR2 нет).

    Args:
        system: Оптическая система (не изменяется).
        wl_main: Основная λ (мкм); None → основная λ системы.
        wl_alt: Вторая λ пары; None → вторая λ ``system.wavelengths``,
            иначе пара d→C (см. :func:`_resolve_alt_wl`).
        n_zones: Число зон поля.

    Returns:
        Список словарей-строк + осевая строка N=0; ``None`` — луч зоны
        не дошёл. При нулевом поле — единственная осевая строка.
    """
    if wl_main is None:
        wl_main = get_primary_wl(system)
    wl_alt = _resolve_alt_wl(system, wl_main, wl_alt)
    field_max = max_field(system)
    if field_max <= 0 or not system.surfaces:
        return [_axial_row(wl_main=wl_main, wl_alt=wl_alt)]

    parax_main = paraxial_trace(system, wl=wl_main)
    parax_alt = paraxial_trace(system, wl=wl_alt)
    rows = []
    for idx, zone in enumerate(field_zones(n_zones), start=1):
        field_y, _ = _zone_field(system, zone, field_max)

        exit1 = _chief_exit(system, wl_main, field_y, parax_main)
        exit2 = _chief_exit(system, wl_alt, field_y, parax_alt)
        y1 = exit1[0] if exit1 is not None else None
        y2 = exit2[0] if exit2 is not None else None
        if y1 is not None and y2 is not None:
            mag_abs = y2 - y1
            mag_rel = mag_abs / y1 * 100.0 if abs(y1) > 1e-12 else None
        else:
            mag_abs = mag_rel = None

        cod1 = coddington_trace(system, wl=wl_main, field_y=field_y)
        cod2 = coddington_trace(system, wl=wl_alt, field_y=field_y)
        zm1, zs1 = (cod1.get('delta_zm'), cod1.get('delta_zs')) \
            if cod1 else (None, None)
        zm2, zs2 = (cod2.get('delta_zm'), cod2.get('delta_zs')) \
            if cod2 else (None, None)
        pos_m = zm2 - zm1 if None not in (zm1, zm2) else None
        pos_s = zs2 - zs1 if None not in (zs1, zs2) else None

        # Дисторсия на λ₂ (та же формула, что TABGL, на своей параксиали)
        del_pct = None
        if y2 is not None:
            y_parax2 = _paraxial_image_height(system, field_y, parax_alt)
            if abs(y_parax2) > 1e-12:
                del_pct = (y2 - y_parax2) / y_parax2 * 100.0

        rows.append({
            'n': idx, 'zone': zone,
            'mag_rel_pct': mag_rel, 'mag_abs_mm': mag_abs,
            'pos_m_mm': pos_m, 'pos_s_mm': pos_s,
            'del_pct': del_pct, 'dy_prime_mm': y2,
            'z_m': zm2, 'z_s': zs2,
        })
    rows.append(_axial_row(wl_main=wl_main, wl_alt=wl_alt))
    return rows


def format_tabpr2(rows) -> str:
    """Таблица TABPR2 целиком: реконструированный заголовок + данные.

    Ведущий пробел печатальщика — как у TABGL (эталонного вывода нет).
    """
    lines = list(TABPR2_HEADER)
    for row in rows:
        values = (row.get('n'), row.get('mag_rel_pct'),
                  row.get('mag_abs_mm'), row.get('pos_m_mm'),
                  row.get('pos_s_mm'), row.get('del_pct'),
                  row.get('dy_prime_mm'), row.get('z_m'), row.get('z_s'))
        n_field = f'{values[0]:3d}' if values[0] is not None else '   '
        line = '  ' + n_field + ''.join(
            _fwo(v, w, d) for v, (w, d) in zip(values[1:], TABPR2_FIELD_SPECS))
        lines.append(line.rstrip())
    return '\n'.join(lines)
