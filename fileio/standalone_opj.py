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
0x4C положение предмета f64 (мм от первой поверхности): <0 —
      действительный предмет слева, >0 — мнимый справа (P6.1, досье
      REVERSE_GVERIFY.md §3.7: ST4 −96.2046 = 1000/(Sp дптр) + sP)
0x46 тип диафрагмы: 0 'd', 1 'z', 0xFFFF 'p' (зрачок)
0x5C апертура f64 (полу-, мм)
0x6C SD f64 — смещение диафрагмы от поверхности ND (мм)
0x74/0x7C поле Y/X f64 (радианы)
0x9C λ f32 × слоты (неиспользуемые слоты дублируют λ0)
далее кривизны f64 × ns; толщины f64 × ns (последняя = 1e20);
gidx u16 × (ns+1) (1 = воздух, g>1 = строка RI g−1,
      0xFFFE/0xFFFF = зеркало — RI-строку не потребляют;
      0xFFFD = ГОЭ-голограмма — RI-строки не потребляет тоже,
      REVERSE_GTIE.md);
RI f64 (n_glass × n_λ), строка 0 = воздух; имена CP866 10-байтовыми
слотами от якоря «ВОЗДУХ»/'AIR'. За именами — общий хвост всех
OPJ: u32 = 202+2·ns (маркер записи), затем блок параметров
дифракционного элемента (ГОЭ/решётка; best-effort: λ записи
0.6328 HeNe у GTIE00) и скаляры/зоны — порт не разбирает.
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

#: Маркер ГОЭ-поверхности в gidx (голограммный оптический элемент,
#: досье REVERSE_GTIE.md): среду после поверхности не меняет и
#: RI-строку не потребляет — как зеркало, но поверхность
#: дифракционная. Пишется в слот СРЕДИ зеркальных маркеров
#: (GTIE00: [1,2,1,FFFF,FFFD,FFFF,1,…] — ГОЭ S3 в зеркальном
#: сэндвиче S2/S4), у решётки GTIN05 маркера нет — только FFFF.
GOE_MARKER = 0xFFFD

#: Диапазон λ standalone-записей, мкм (ИК-ГОЭ до 5, запас ×6).
_WL_MIN, _WL_MAX = 0.1, 30.0

#: Санитарные пределы prescription'а (синхронно decode_lbo:
#: CURV_ABS_MAX/THICK_ABS_MAX) — компакт-LBO блоб, случайно прошедший
#: смещения строгой раскладки, валится здесь на мусорных double.
_CURV_ABS_MAX = 100.0      # |C| 1/мм
_THICK_ABS_MAX = 1e4       # |d| мм (кроме маркера 1e20)
_RI_MIN, _RI_MAX = 0.5, 5.0   # показатели RI-матрицы (ИК: Ge n≈4.0 при 10 мкм)

_VOZDUH = 'ВОЗДУХ'.encode('cp866')
_AIR = b'AIR'


class StandaloneOpjError(ValueError):
    """Раскладка не соответствует standalone-OPJ: данные выходят за
    пределы файла либо индексы сред мусорные."""


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
    object_pos = _f64(data, 0x4C, 'положение предмета', source)
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
    for i, c in enumerate(curv):
        if not -_CURV_ABS_MAX <= c <= _CURV_ABS_MAX:
            raise StandaloneOpjError(
                f'кривизна S{i} = {c} вне ±{_CURV_ABS_MAX} 1/мм — блок '
                f'кривизн не по строгой раскладке{f" [{source}]" if source else ""}')
    th_off = curv_off + 8 * ns
    thick = [_f64(data, th_off + 8 * i, f'толщина S{i}', source)
             for i in range(ns)]
    for i, d in enumerate(thick):
        if abs(d) < BIG_MARKER and not -_THICK_ABS_MAX <= d <= _THICK_ABS_MAX:
            raise StandaloneOpjError(
                f'толщина S{i} = {d} вне ±{_THICK_ABS_MAX} мм — блок '
                f'толщин не по строгой раскладке{f" [{source}]" if source else ""}')
    if thick[-1] < BIG_MARKER:
        warnings.append(
            f'маркер 1e20 не в d[{ns - 1}] (d={thick[-1]:.6g}) — '
            f'раскладка толщин сомнительна')

    gidx_off = th_off + 8 * ns
    gidx = [_u16(data, gidx_off + 2 * i, f'gidx S{i}', source)
            for i in range(ns + 1)]
    for g in gidx:
        if g not in MIRROR_MARKERS and g != GOE_MARKER and g >= 0xFFFC:
            raise StandaloneOpjError(
                f'неизвестный индекс среды {g} в gidx={gidx} — запись не '
                f'standalone-OPJ{f" [{source}]" if source else ""}')
    # зеркальные/ГОЭ-маркеры RI-строку не потребляют
    n_glass = max((g for g in gidx if g < GOE_MARKER), default=1)
    mirrors = sorted(i for i in range(ns)
                     if gidx[i + 1] in MIRROR_MARKERS or gidx[i] in MIRROR_MARKERS)
    #: ГОЭ-поверхности: маркер стоит в слоте среды ПОСЛЕ поверхности.
    goe = sorted(i for i in range(ns) if gidx[i + 1] == GOE_MARKER)

    ri_off = gidx_off + 2 * (ns + 1)
    ri = [[_f64(data, ri_off + 8 * (row * len(wls) + col),
                f'RI[{row}][{col}]', source)
           for col in range(len(wls))] for row in range(n_glass)]
    for row in ri:
        for v in row:
            if not _RI_MIN < v < _RI_MAX:
                raise StandaloneOpjError(
                    f'показатель {v} вне {_RI_MIN}..{_RI_MAX} — RI-матрица '
                    f'не по строгой раскладке{f" [{source}]" if source else ""}')

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

    # блок параметров ГОЭ (досье REVERSE_GTIE.md): за именами u32 =
    # 202+2·ns — маркер записи (сверен GTIE00/GTIN05/US00KI02), затем
    # запись дифракционного элемента: эхо u16 0xFFFD … u16 ns (≤0x40
    # байт) … f32×8 — у GTIE00 λ записи 0.6328 (HeNe) в слоте 4.
    # Best-effort: неудачный скан не валит разбор.
    goe_info = {'surfaces': goe, 'rec': None, 'wlh': None}
    if goe:
        m = tail.find(struct.pack('<H', GOE_MARKER))
        ns_pos = -1
        if m >= 0:
            for off in range(m + 2, min(m + 0x40, len(tail) - 1), 2):
                if struct.unpack_from('<H', tail, off)[0] == ns:
                    ns_pos = off
                    break
        if ns_pos >= 0 and ns_pos + 0xA + 32 <= len(tail):
            rec = list(struct.unpack_from('<8f', tail, ns_pos + 0xA))
            goe_info['rec'] = rec
            if _WL_MIN < rec[4] < _WL_MAX:
                goe_info['wlh'] = float(rec[4])
        warnings.append(
            f'ГОЭ-поверхность {", S".join(map(str, goe))}: дифракция не '
            f'смоделирована — заглушка (отражение, параметры записи '
            f'в ключе goe)')

    return {
        'name': name, 'ns': ns, 'flags': flags, 'wls': wls,
        'obj_type': obj_type, 'img_type': img_type, 'stop_type': stop_type,
        'stop_nd': stop_nd, 'object_pos': object_pos,
        'aperture_semi': aperture, 'pupil_pos': pupil_pos,
        'field_y_rad': field_y, 'field_x_rad': field_x,
        'curv': curv, 'thick': thick, 'gidx': gidx, 'ri': ri,
        'names': names, 'mirrors': mirrors, 'goe': goe_info,
        'warnings': warnings, 'source': source,
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

    ГОЭ-маркер 0xFFFD → заглушка (REVERSE_GTIE.md): поверхность
    ``is_reflective`` с кривизной/толщиной из OPJ и ``glass='ГОЭ'``,
    дифракция записи НЕ смоделирована (λ записи и сырая таблица
    параметров — в ``opj['goe']``); прочие поверхности честные.
    """
    from optics_engine import (ApertureType, FieldPoint, ObjectType,
                               OpticalSystem, Surface, Wavelength)
    import math

    ns, wls, ri = opj['ns'], opj['wls'], opj['ri']
    mirrors = set(opj.get('mirrors', ()))
    goe = set(opj.get('goe', {}).get('surfaces', ()))
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
            glass=('ГОЭ' if i in goe else
                   'ЗЕРКАЛО' if i in mirrors else ''),
            # 0 → UNLIMITED_SD трейсера: полудиаметры поверхностей в OPJ
            # не хранятся, клиппинг выключен — сверка расчёта без
            # виньетирования (ST4: вход zone 1.0 = 12.6 мм у S0)
            semi_diameter=0.0,
            n_override=n_ov,
        )
        if i in mirrors or i in goe:
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
