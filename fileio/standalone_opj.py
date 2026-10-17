"""Строгий парсер standalone .OPJ — вход порта (GFIX P5).

Раскладка OPAL-PC, валидирована банком эталонных .PRN
(analysis/REVERSE_GVERIFY.md §3, досье GFIX):

===  ==========================================================
0x0C имя 40 байт CP866
0x34 ns u16 — число поверхностей
0x36 flags u16 — 1 → один слот λ f32, 3 → три слота
0x3A ND u16 — поверхность диафрагмы (1-индексация, OPAL ND)
0x3C тип предмета: 0 дальний (∞), 1 ближний
0x3E тип изображения: 0 дальний, 1 ближний
0x46 тип диафрагмы: 0 'd', 1 'z', 0xFFFF 'p' (зрачок)
0x5C апертура f64 (полу-, мм)
0x6C SD f64 — смещение диафрагмы от поверхности ND (мм)
0x74/0x7C поле Y/X f64 (радианы)
0x9C λ f32 × слоты (неиспользуемые слоты дублируют λ0)
далее кривизны f64 × ns; толщины f64 × ns (последняя = 1e20);
gidx u16 × (ns+1) (1 = воздух, g>1 = строка RI g−1,
      0xFFFE/0xFFFF = зеркало — RI-строку не потребляют);
RI f64 (n_glass × n_λ), строка 0 = воздух; имена CP866 10-байтовыми
слотами от якоря «ВОЗДУХ»/'AIR'.
===  ==========================================================

Семантика диафрагмы (GFIX P1, досье REVERSE_GFIX.md §1): плоскость
диафрагмы = вершина поверхности ND−1 (0-индексация) + SD — для ВСЕХ
значений 0x46; тип — только способ ввода в UI OPAL.

Отличие от эвристик (opj_io.load_opj, decode_lbo_opj): раскладка
жёсткая, при любом выходе за пределы файла / мусорном индексе среды
кидается :class:`StandaloneOpjError` — вызовющий откатывается на
эвристики. Прежняя реализация жила в харнессе
(analysis/golden_verify.parse_golden_opj) и падала голым struct.error
на зеркальных маркерах (n_glass = max(gidx) без их исключения).
"""
import struct

#: 1e20-маркер конца цепочки толщин (последний слот = BFD неизвестен).
BIG_MARKER = 1e19

#: Маркеры зеркальных промежутков в gidx: среду не меняют, RI-строку
#: не потребляют (0xFFFE/0xFFFF; decode_lbo.Markers — те же).
MIRROR_MARKERS = (0xFFFE, 0xFFFF)

#: Диапазон λ standalone-записей, мкм (ИК-ГОЭ до 5, запас ×6).
_WL_MIN, _WL_MAX = 0.1, 30.0

_VOZDUH = 'ВОЗДУХ'.encode('cp866')
_AIR = b'AIR'


class StandaloneOpjError(ValueError):
    """Раскладка не соответствует standalone-OPJ: данные выходят за
    пределы файла либо индексы сред мусорные (например, ГОЭ-записи
    OPAL пишут 0xFFFD — досье REVERSE_GVERIFY.md §6)."""


def _need(data: bytes, off: int, size: int, what: str, source: str):
    """Границы файла: off+size ≤ len, иначе чистая ошибка раскладки."""
    if off < 0 or off + size > len(data):
        raise StandaloneOpjError(
            f'{what}: чтение {size} байт по смещению {off} за пределами '
            f'файла ({len(data)} байт){f" [{source}]" if source else ""}')


def _u16(data, off, what, source=''):
    _need(data, off, 2, what, source)
    return struct.unpack_from('<H', data, off)[0]


def _f32(data, off, what, source=''):
    _need(data, off, 4, what, source)
    return struct.unpack_from('<f', data, off)[0]


def _f64(data, off, what, source=''):
    _need(data, off, 8, what, source)
    return struct.unpack_from('<d', data, off)[0]


def parse_standalone_opj(data: bytes, source: str = '') -> dict:
    """Строгий разбор standalone-OPJ → prescription-словарь.

    Ключ ``warnings`` собирает допустимые отклонения (маркер 1e20 не в
    последнем слоте толщин — OPAL иногда пишет 0 или фактический BFD);
    недопустимые (мусорный gidx, RI за пределами файла) — исключение
    :class:`StandaloneOpjError`.
    """
    _need(data, 0x34, 2, 'заголовок', source)
    warnings = []
    name = data[0x0C:0x34].decode('cp866', 'replace').rstrip('\0 ')
    ns = _u16(data, 0x34, 'ns', source)
    if not 0 < ns <= 64:
        raise StandaloneOpjError(f'ns={ns} вне диапазона 1..64{f" [{source}]" if source else ""}')
    flags = _u16(data, 0x36, 'flags', source)
    stop_nd = _u16(data, 0x3A, 'ND', source)
    obj_type = _u16(data, 0x3C, 'тип предмета', source)
    img_type = _u16(data, 0x3E, 'тип изображения', source)
    stop_type = _u16(data, 0x46, 'тип диафрагмы', source)
    aperture = _f64(data, 0x5C, 'апертура', source)
    pupil_pos = _f64(data, 0x6C, 'SD', source)
    field_y = _f64(data, 0x74, 'поле Y', source)
    field_x = _f64(data, 0x7C, 'поле X', source)

    slots = 3 if flags & 0x2 else 1
    wl_slots = [_f32(data, 0x9C + 4 * i, f'λ{i}', source)
                for i in range(slots)]
    for wl in wl_slots:
        if not _WL_MIN < wl < _WL_MAX:
            raise StandaloneOpjError(
                f'λ={wl} вне { _WL_MIN}..{_WL_MAX} мкм — раскладка λ '
                f'сомнительна{f" [{source}]" if source else ""}')
    wls = []
    for wl in wl_slots:
        if not wls or abs(wl - wls[0]) > 1e-6:
            wls.append(float(wl))

    curv_off = 0x9C + 4 * slots
    curv = [_f64(data, curv_off + 8 * i, f'кривизна S{i}', source)
            for i in range(ns)]
    th_off = curv_off + 8 * ns
    thick = [_f64(data, th_off + 8 * i, f'толщина S{i}', source)
             for i in range(ns)]
    if thick[-1] < BIG_MARKER:
        warnings.append(
            f'маркер 1e20 не в d[{ns - 1}] (d={thick[-1]:.6g}) — '
            f'раскладка толщин сомнительна')

    gidx_off = th_off + 8 * ns
    gidx = [_u16(data, gidx_off + 2 * i, f'gidx S{i}', source)
            for i in range(ns + 1)]
    for g in gidx:
        if g >= 0xFFFE and g not in MIRROR_MARKERS:
            raise StandaloneOpjError(
                f'неизвестный индекс среды {g} в gidx={gidx} — запись не '
                f'standalone-OPJ (ГОЭ, досье §6){f" [{source}]" if source else ""}')
    # зеркальные маркеры RI-строку не потребляют
    n_glass = max((g for g in gidx if g < 0xFFFE), default=1)
    mirrors = sorted(i for i in range(ns)
                     if gidx[i + 1] in MIRROR_MARKERS or gidx[i] in MIRROR_MARKERS)

    ri_off = gidx_off + 2 * (ns + 1)
    ri = [[_f64(data, ri_off + 8 * (row * len(wls) + col),
                f'RI[{row}][{col}]', source)
           for col in range(len(wls))] for row in range(n_glass)]

    # имена сред — якорь «ВОЗДУХ»/'AIR' сразу после RI-блока
    names = []
    tail = data[ri_off + 8 * n_glass * len(wls):]
    anchor = tail.find(_VOZDUH)
    if anchor < 0:
        anchor = tail.find(_AIR)
    if anchor >= 0:
        pos = anchor
        while pos < len(tail) and len(names) < n_glass:
            nm = tail[pos:pos + 10].split(b'\0')[0].decode('cp866',
                                                           'replace').strip()
            if nm:
                names.append(nm)
            pos += 10

    return {
        'name': name, 'ns': ns, 'flags': flags, 'wls': wls,
        'obj_type': obj_type, 'img_type': img_type, 'stop_type': stop_type,
        'stop_nd': stop_nd,
        'aperture_semi': aperture, 'pupil_pos': pupil_pos,
        'field_y_rad': field_y, 'field_x_rad': field_x,
        'curv': curv, 'thick': thick, 'gidx': gidx, 'ri': ri,
        'names': names, 'mirrors': mirrors, 'warnings': warnings,
        'source': source,
    }


def standalone_to_system(opj: dict):
    """Standalone-разбор → портовая :class:`OpticalSystem`.

    Среды задаются ``n_override``-словарями из RI-матрицы OPJ (портовый
    :func:`domain.calculations.refractive_index` берёт их при
    ``|λ_ключ − λ| < 0.002``) — каталог стёкол порта не участвует,
    показатели ровно те, что видел OPAL. Толщина изображения 1e20
    обнуляется (терминальный сегмент с пост-рефракционным направлением
    трейсер строит сам, TERMINAL_EXIT_EPS — GFIX P2).

    Диафрагма: ND (0x3A) + SD (0x6C) — плоскость диафрагмы для всех
    типов 0x46 (GFIX P1); порт считает зрачки из этой плоскости сам
    (:func:`domain.calculations.paraxial_trace`). ``aperture_value``
    обнуляется — полудиаметр физической диафрагмы из 0x5C не
    реверсирован, клиппинг трейсера выключен: полу-диаметры поверхностей
    без виньетирования.

    Зеркальные маркеры gidx → ``is_reflective`` поверхности (среда
    зеркального промежутка не меняется — n_override не назначается).
    """
    from optics_engine import (ApertureType, FieldPoint, ObjectType,
                               OpticalSystem, Surface, Wavelength)
    import math

    ns, wls, ri = opj['ns'], opj['wls'], opj['ri']
    mirrors = set(opj.get('mirrors', ()))
    system = OpticalSystem(name=opj['name'])
    system.object_type = (ObjectType.INFINITE if opj['obj_type'] == 0
                          else ObjectType.FINITE)
    system.image_type = (ObjectType.INFINITE if opj['img_type'] == 0
                         else ObjectType.FINITE)
    system.stop_type = {0: 'd', 1: 'z', 0xFFFF: 'p'}.get(opj['stop_type'], 'd')
    system.stop_surface = max(1, opj.get('stop_nd', 1))
    system.stop_offset = opj['pupil_pos']
    system.aperture_type = ApertureType.ENTRANCE_PUPIL
    system.aperture_value = 0.0
    system.wavelengths = [Wavelength(wl, 1.0, '') for wl in wls]
    if opj['field_y_rad']:
        system.field_points = [FieldPoint(y=math.degrees(opj['field_y_rad']))]

    big = max(1.0, abs(opj['aperture_semi']) * 4)
    for i in range(ns):
        c = opj['curv'][i]
        d = opj['thick'][i]
        glass_row = opj['gidx'][i + 1] - 1  # среда ПОСЛЕ поверхности i
        n_ov = {}
        if i not in mirrors and glass_row >= 0 and glass_row < len(ri):
            for k, wl in enumerate(wls):
                if glass_row < len(ri) and k < len(ri[glass_row]):
                    n_ov[wl] = ri[glass_row][k]
        surf = Surface(
            radius=(1.0 / c if abs(c) > 1e-15 else 0.0),
            thickness=(0.0 if d >= BIG_MARKER else d),
            glass=('ЗЕРКАЛО' if i in mirrors else ''),
            semi_diameter=big * 10.0,   # без виньетирования: сверка расчёта
            n_override=n_ov,
        )
        if i in mirrors:
            surf.is_reflective = True
        system.surfaces.append(surf)
    return system


def load_standalone_opj(path) -> tuple:
    """Файл standalone-OPJ → (OpticalSystem, info-словарь).

    info = prescription-словарь :func:`parse_standalone_opj` (ключи
    ``warnings``/``mirrors`` — для отчёта загрузчика).
    """
    data = open(path, 'rb').read()
    opj = parse_standalone_opj(data, source=str(path))
    return standalone_to_system(opj), opj
