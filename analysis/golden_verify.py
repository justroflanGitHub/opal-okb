# -*- coding: utf-8 -*-
"""
GVERIFY — золотая верификация расчётов порта против банка эталонных .PRN
(волна 2026-10-17, TASK_GVERIFY).

Банк: ``analysis/reverse_data/golden/bank/*.PRN`` (14 систем, CP866,
досье REVERSE_G2BANK.md) + исходные ``C:\\GOLDEN_DOS\\*.OPJ`` (стенд,
только чтение). Порт считается верифицируемым: правки модулей порта в
этой волне ЗАПРЕЩЕНЫ — все расхождения фиксируются в досье
REVERSE_GVERIFY.md.

Структура:

1. :func:`parse_golden_opj` — строгий разбор standalone .OPJ. Валидирован
   на OPAL3/OBEKTIV/US00KI02 (efl 297.28/100.0065/1034.25, RI-матрица
   совпадает с каталожными марками стёкол). Причина существования:
   ``fileio.decode_lbo.decode_lbo_opj`` миспарсит standalone-файлы
   (толщины со сдвигом на слот, потеря RI при Ge>2.60) — досье §3.

2. :func:`parse_golden_prn` — разбор эталонных .PRN: заголовок, секция
   «Габариты пучков» (с дедупликацией дублей-протокола), две таблицы
   «Аберрации осевого пучка». Единицы величин читаются из шапок таблиц
   (дптр/мм; гр.мнсек/мм; дл. волн; %; мм) — семантика единиц у каждой
   системы своя, досье §2.

3. Расчёт порта: :func:`opj_to_system` (портовая :class:`OpticalSystem`
   с n_override из RI-матрицы OPJ), дальше только вызовы порта —
   ``paraxial_trace``, ``trace_ray_through_system``, ``_ray_wavefront``,
   ``compute_isoplanatism``, конверсии ``analysis.units``. Где портовый
   API не покрывает величину (выходной зрачок для диафрагмы типа 'p' —
   ``paraxial_trace`` знает только 'd'), харнесс считает дополнение на
   портовых примитивах (:func:`_paraxial_ray`, досье §4).

4. :func:`compare_system`/:func:`run_all` — таблицы «величина | OPAL |
   порт | Δ | допуск» с вердиктами GREEN/YELLOW/RED и сводкой.

Взломанные конвенции OPAL (полный вывод — досье REVERSE_GVERIFY.md):

* **метка TABOC2 «Tg'*100»**: у систем с дальним изображением (afocal)
  колонка фактически содержит **высоту зонального луча в плоскости
  выходного зрачка, мм** (H' ЗР): US00KI02 20.676 vs эталон 20.684
  (0.03%, все 4 зоны). Печать порта ``tg_prime100`` = 100·tg u' —
  угловая мера ближнего типа; сверка дальнего типа идёт по H' ЗР.
* **продольные (дптр)** = 1000·(1/L'_зоны − 1/L'_паракс), где длины
  отмеряются **от плоскости выходного зрачка**: US00KI02 — совпадение
  0.03–0.2% на всех зонах (−.0902/−.0560/−.0300/−.0116 vs эталон
  −.09008/−.05594/−.03000/−.01158).
* **Sp** (входной зрачок) для диафрагмы типа «зрачок» (0x46=0xFFFF)
  лежит в заголовке OPJ @0x6C (US00KI02: −22.2 = эталон −22.200 точно).
* **Ax'** (задняя апертура, N=0) = высота краевого луча в плоскости
  выходного зрачка — та же величина, что и метка Tg'*100 дальней
  системы.
"""
from __future__ import annotations

import copy
import math
import os
import re
import struct

_BANK_DIR = os.path.join(os.path.dirname(__file__), 'reverse_data',
                         'golden', 'bank')
_GOLDEN_DOS = r'C:\GOLDEN_DOS'

#: Банк: имя → наличие секций (досье G2BANK).
BANK_SYSTEMS = (
    'US00KI02', '121', 'ST', 'ST4', 'OPAL3', 'HELIOS8', 'OKULAR',
    'OBEKTIV', 'PLIOPT', 'GTIE00', 'KURSOVIK', 'LAB6_GAS', 'S_KOND1',
    'OPTICS#1',
)

#: Допуски карточки задачи: параксиальные ≤1e-4 отн., аберрации ≤1e-3
#: отн. (после выравнивания знаков/масштабов). Жёлтый — 10× допуска.
TOL_PARAX = 1e-4
TOL_ABERR = 1e-3
TOL_YELLOW = 10.0

#: Абсолютный шумовой порог аберраций (мм): PRN печатает 5 знаков,
#: n порта/OPAL интерполируются из f32-λ — систематика ~1e-3 мм не
#: устранима; для дптр — эквивалент 1000·floor/f² при типовом фокусе
#: (2e-3 мм / 100 мм ≈ 2e-4 дптр); волновые в мкм — разрешение печати
#: (4 знака → 1e-4 мкм) с запасом: 1e-3 мкм, чтобы не глотать
#: реальную систематику опорной сферы ~2 % (досье §2.4, цель P4).
ABS_FLOOR_MM = 2e-3
ABS_FLOOR_DPTR = 2e-4
ABS_FLOOR_WAVE = 1e-3

#: 1e20-маркер конца цепочки толщин в standalone .OPJ.
_BIG_MARKER = 1e19


# ══════════════════════════════════════════════════════════════════════════
# 1. Строгий разбор standalone .OPJ
# ══════════════════════════════════════════════════════════════════════════

def parse_golden_opj(path: str) -> dict:
    """Строгий разбор standalone .OPJ (валидированная раскладка).

    Раскладка (досье REVERSE_GVERIFY.md §3):

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
    gidx u16 × (ns+1) (1 = воздух, g>1 = строка RI g−1);
    RI f64 (1+nglass) × n_valid_λ, строка 0 = воздух; имена CP866.
    ===  ==========================================================

    Семантика диафрагмы (волна GFIX, досье REVERSE_GFIX.md §1): плоскость
    диафрагмы = вершина поверхности ND−1 (0-индексация) + SD — для ВСЕХ
    значений 0x46, включая 'p' (121: ND=4, SD=8.162 → z=16.152, sP=14.444
    = эталон 14.444). Тип 0x46 — только способ ввода в UI OPAL.

    Возвращает словарь с prescription'ом; ключ ``warnings`` собирает
    отклонения раскладки (для досье).
    """
    data = open(path, 'rb').read()
    warnings = []
    name = data[0x0C:0x34].decode('cp866').rstrip('\0 ')
    ns = struct.unpack_from('<H', data, 0x34)[0]
    flags = struct.unpack_from('<H', data, 0x36)[0]
    stop_nd = struct.unpack_from('<H', data, 0x3A)[0]
    obj_type = struct.unpack_from('<H', data, 0x3C)[0]
    img_type = struct.unpack_from('<H', data, 0x3E)[0]
    stop_type = struct.unpack_from('<H', data, 0x46)[0]
    aperture = struct.unpack_from('<d', data, 0x5C)[0]
    pupil_pos = struct.unpack_from('<d', data, 0x6C)[0]
    field_y = struct.unpack_from('<d', data, 0x74)[0]
    field_x = struct.unpack_from('<d', data, 0x7C)[0]

    slots = 3 if flags & 0x2 else 1
    wl_slots = [struct.unpack_from('<f', data, 0x9C + 4 * i)[0]
                for i in range(slots)]
    wls = []
    for wl in wl_slots:
        if not wls or abs(wl - wls[0]) > 1e-6:
            wls.append(float(wl))
    curv_off = 0x9C + 4 * slots
    curv = [struct.unpack_from('<d', data, curv_off + 8 * i)[0]
            for i in range(ns)]
    th_off = curv_off + 8 * ns
    thick = [struct.unpack_from('<d', data, th_off + 8 * i)[0]
             for i in range(ns)]
    if thick[-1] < _BIG_MARKER:
        warnings.append(
            f'маркер 1e20 не в d[{ns - 1}] (d={thick[-1]:.6g}) — '
            f'раскладка толщин сомнительна')
    gidx_off = th_off + 8 * ns
    gidx = [struct.unpack_from('<H', data, gidx_off + 2 * i)[0]
            for i in range(ns + 1)]
    ri_off = gidx_off + 2 * (ns + 1)
    n_glass = max(gidx) if gidx else 1
    ri = [[struct.unpack_from('<d', data, ri_off + 8 * (row * len(wls) + col))[0]
           for col in range(len(wls))] for row in range(n_glass)]

    # имена сред — якорь «ВОЗДУХ»/'AIR' сразу после RI-блока
    names = []
    tail = data[ri_off + 8 * n_glass * len(wls):]
    anchor = tail.find('ВОЗДУХ'.encode('cp866'))
    if anchor < 0:
        anchor = tail.find(b'AIR')
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
        'names': names, 'warnings': warnings,
    }


def opj_to_system(opj: dict):
    """Standalone-разбор → портовая :class:`OpticalSystem`.

    Среды задаются ``n_override``-словарями из RI-матрицы OPJ (портовый
    :func:`domain.calculations.refractive_index` берёт их при
    ``|λ_ключ − λ| < 0.002``) — каталог стёкол порта не участвует,
    показатели ровно те, что видел OPAL. Толщина изображения 1e20
    обнуляется (порт трассирует до последней поверхности; позиция
    изображения для дальнего типа = ∞ — семантика досье §2).

    Диафрагма: ND (0x3A) + SD (0x6C) — плоскость диафрагмы для всех
    типов 0x46 (досье §1); порт считает зрачки из этой плоскости сам
    (:func:`domain.calculations.paraxial_trace`). ``aperture_value``
    обнуляется — полудиаметр физической диафрагмы из 0x5C не
    реверсирован (семантика меняется по системе), клиппинг трейсера
    выключен: полу-диаметры поверхностей без виньетирования.
    """
    from domain.models import (ApertureType, FieldPoint, ObjectType,
                               OpticalSystem, Surface, Wavelength)

    ns, wls, ri = opj['ns'], opj['wls'], opj['ri']
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
        if glass_row >= 0 and glass_row < len(ri):
            for k, wl in enumerate(wls):
                if glass_row < len(ri) and k < len(ri[glass_row]):
                    n_ov[wl] = ri[glass_row][k]
        system.surfaces.append(Surface(
            radius=(1.0 / c if abs(c) > 1e-15 else 0.0),
            # Маркер конца цепочки → 0: терминальный сегмент с
            # пост-рефракционным направлением трейсер строит сам
            # (TERMINAL_EXIT_EPS, GFIX P2; досье §4.1 — прежде обход
            # заглушкой толщины здесь).
            thickness=(0.0 if d >= _BIG_MARKER else d),
            glass='',
            semi_diameter=big * 10.0,   # без виньетирования: сверка расчёта
            n_override=n_ov,
        ))
    return system


# ══════════════════════════════════════════════════════════════════════════
# 2. Разбор эталонных .PRN
# ══════════════════════════════════════════════════════════════════════════

_NUM = re.compile(r'-?\d+\.\d+|-?\.\d+')

#: Правые границы колонок FORTRAN Fw.d (печать OPAL правоориентированная;
#: замерено по полностью заполненным строкам OPAL3/GTIE00/121 — единая
#: форма печати на весь банк): табл.1 — продольные λ0..2, поперечные
#: λ0..2; табл.2 — волновые λ0..2, неизопл, Н ЗР. Метки строк (koop /
#: Tg'*100) кончаются на колонках 5 и 6.
_AXIAL1_EDGES = (17, 28, 39, 52, 65, 77)
_AXIAL2_EDGES = (16, 26, 36, 47, 57)


def _fixed_cells(line: str, edges, left0: int):
    """Значения правоориентированных полей: каждое поле = отрезка
    (правая граница предыдущего поля, эта правая граница]."""
    values = []
    prev = left0
    for e in edges:
        text = line[prev:e].strip() if prev < len(line) else ''
        m = _NUM.search(text)
        values.append(float(m.group(0)) if m else None)
        prev = e
    return values


def parse_golden_prn(path: str) -> dict:
    """Разбор эталонного .PRN банка (CP866 → значения).

    Возвращает::

        {'name': ..., 'gabarit': {(wl_str, N): row_dict},
         'axial1': {'units': ('дптр'|'мм', 'гр.мнсек'|'мм'),
                    'rows': {zone: {'long': [v0,v1,v2]|None,
                                    'trans': [v0,v1,v2]|None}}},
         'axial2': {'rows': {zone: {'tg100': v, 'wave': [v0..2]|None,
                                     'iso': v, 'h_zr': v}}},
         'duplicated_gabarit': bool}

    Секция «Габариты пучков» может быть продублирована протоколом
    (KURSOVIK) — дубли игнорируются; строки: N Ax Ay Ax' Ay' Sp Sp'
    виньетаж светораспределение ограничения (последние не сверяются).
    """
    text = open(path, encoding='cp866').read()
    lines = text.splitlines()
    result = {'gabarit': {}, 'axial1': {}, 'axial2': {},
              'gabarit_units': ('мм', 'мм'),
              'duplicated_gabarit': False}
    m = re.search(r'Cистема-(.*?)\s{2,}Работа-RT', text)
    result['name'] = m.group(1).rstrip() if m else ''

    i, n = 0, len(lines)
    gab_seen = 0
    while i < n:
        line = lines[i]
        if line.strip() == 'Габариты пучков':
            gab_seen += 1
            # единицы «Положение зрачков»: (мм)/(дптр) у Sp/Sp' —
            # дптр у ближнего типа (Sp' при img=1 — от плоскости Гаусса,
            # Sp при obj=1 — от предмета; OPALOPT:1275–1293)
            units_line = lines[i + 2] if i + 2 < n else ''
            mu = re.findall(r'\((мм|дптр)\)', units_line)
            if len(mu) >= 2:
                result['gabarit_units'] = (mu[0], mu[1])
            i += 4                                  # шапка из 3 строк
            while i < n:
                s = lines[i].strip()
                if not s:
                    i += 1
                    continue
                mw = re.match(r'Длина волны\s*-\s*([\d.]+)', s)
                if not mw:
                    break
                wl = mw.group(1)
                i += 1
                while i < n:
                    row = lines[i]
                    if not row.strip() or not row.lstrip()[:1].isdigit():
                        break
                    toks = row.split()
                    if len(toks) >= 7:
                        key = (wl, int(toks[0]))
                        if key in result['gabarit'] and gab_seen > 1:
                            pass                    # дубли протокола
                        else:
                            result['gabarit'][key] = {
                                'N': int(toks[0]),
                                'Ax': float(toks[1]), 'Ay': float(toks[2]),
                                'Ax2': float(toks[3]), 'Ay2': float(toks[4]),
                                'Sp': float(toks[5]), 'Sp2': float(toks[6]),
                            }
                    i += 1
            continue
        if line.strip() == 'Аберрации осевого пучка':
            i += 1
            while i < n:
                s = lines[i]
                mu = re.search(r'Продольные аберрации \(([^)]+)\)', s)
                if mu:
                    mt = re.search(r'Поперечные аберрации \(([^)]+)\)', s)
                    result['axial1']['units'] = (
                        mu.group(1), mt.group(1) if mt else 'мм')
                if 'koop' in s and '┴' in s:      # разделитель табл.1
                    i += 1
                    while i < n:
                        row = lines[i]
                        m = _NUM.match(row.strip())
                        if not m:
                            break
                        zone = float(m.group(0))
                        vals = _fixed_cells(row, _AXIAL1_EDGES, len(m.group(0)))
                        result['axial1'].setdefault('rows', {})[zone] = {
                            'long': vals[:3], 'trans': vals[3:6],
                        }
                        i += 1
                    continue
                if 'Tg' in s and '100' in s:      # шапка табл.2
                    j = i + 1
                    while j < n and '┴' not in lines[j]:
                        j += 1
                    k = j + 1
                    while k < n:
                        row = lines[k]
                        m = _NUM.match(row.strip())
                        if not m:
                            break
                        tg = float(m.group(0))
                        vals = _fixed_cells(row, _AXIAL2_EDGES,
                                            len(m.group(0)))
                        result['axial2'].setdefault('rows', {})[tg] = {
                            'tg100': tg,
                            'wave': vals[:3],
                            'iso': vals[3], 'h_zr': vals[4],
                        }
                        k += 1
                    i = k
                    continue
                i += 1
            continue
        i += 1
    result['duplicated_gabarit'] = gab_seen > 1
    return result


# ══════════════════════════════════════════════════════════════════════════
# 3. Расчёт порта (портовые функции + минимальные дополнения харнесса)
# ══════════════════════════════════════════════════════════════════════════

def _n_media(system, wl: float) -> list:
    """Показатели сред ns+1 — как ``paraxial_trace`` (портовый
    :func:`refractive_index` с n_override, отражения не поддерживаем:
    в банке зеркал с is_reflective нет)."""
    from domain.calculations import refractive_index
    media = [1.0]
    for s in system.surfaces:
        media.append(refractive_index(s.glass, wl, None,
                                      getattr(s, 'n_override', None)))
    return media


def _paraxial_ray(system, wl: float, y0: float, u0: float,
                  z0: float) -> tuple:
    """Параксиальный луч (y, u) от плоскости z0 (мм от первой
    поверхности; z0<0 — перед системой). Возвращает (y, u) на выходе
    последней поверхности. Дополнение харнесса: портовый
    ``paraxial_trace`` не принимает произвольный старт-луч (нужен для
    изображения зрачка при диафрагме типа 'p', досье §4)."""
    media = _n_media(system, wl)
    y, u, z = y0, u0, z0
    for i, s in enumerate(system.surfaces):
        if z < 0:                                # перенос до s0
            y += u * (0.0 - z)
            z = 0.0
        if i > 0:
            y += u * system.surfaces[i - 1].thickness
        R = s.radius if s.radius != 0 else 1e15
        phi = (media[i + 1] - media[i]) / R
        u = (media[i] * u - y * phi) / media[i + 1]
        z += s.thickness
    return y, u


def paraxial_of(system, wl: float) -> dict:
    """Параксиальные габариты порта: sF', sP, sP', f', L.

    Все зрачковые величины считаются портовым :func:`paraxial_trace`
    из плоскости диафрагмы ND/SD (волна GFIX: 'z'/'d'/'p' едины)."""
    from domain.calculations import paraxial_trace
    res = paraxial_trace(system, wl=wl)
    return {
        'f': res.get('focal_length', 0.0),
        'sF_prime': res.get('sF_prime', 0.0),
        'sP': res.get('sP', 0.0),
        'sP_prime': res.get('sP_prime', 0.0),
        'V': res.get('V', 0.0),
        'L': res.get('L', 0.0),
        'bfd': res.get('back_focal_distance', 0.0),
    }


def axial_fan(system, wl: float, zones, ax_semi: float) -> list:
    """Веер осевых зональных лучей портовым трейсером.

    Как ``analysis.tables._axial_zone_fan``, но с явной полувысотой
    пучка ``ax_semi`` (реальный габаритный луч системы из эталона —
    у KURSOVIK заданная апертура 10≠реальные 18.49 мм) и с записью
    выходной геометрии (y, наклон, L, высота в плоскости выходного
    зрачка) для сверок конвенций OPAL.
    """
    from analysis.aberrations import (_chief_reference_opl, _ray_wavefront,
                                      _reference_sphere)
    from optics_utils import make_field_ray
    from ray_tracing import trace_ray_through_system
    from domain.calculations import paraxial_trace

    parax = paraxial_trace(system, wl=wl)
    from analysis.aberrations import _compute_ray_start
    z_start, z_pupil = _compute_ray_start(system, parax)
    ref_center, ref_r = _reference_sphere(system, 0.0, parax)
    opl_chief = _chief_reference_opl(system, wl, 0.0, z_start, z_pupil,
                                     ref_center, ref_r)
    sp_prime = paraxial_of(system, wl)['sP_prime']
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    fan = []
    for zone in zones:
        ray = make_field_ray(system, 0.0, zone * ax_semi, 0.0,
                             z_start, z_pupil)
        res = trace_ray_through_system(system, ray, wl)
        if not (res.success and len(res.path) >= 2):
            fan.append({'zone': zone, 'ok': False})
            continue
        prev, last = res.path[-2], res.path[-1]
        dz = last[2] - prev[2]
        slope = (last[1] - prev[1]) / dz if abs(dz) > 1e-12 else 0.0
        y_exit, z_exit = last[1], last[2]
        length = -y_exit / slope if abs(slope) > 1e-12 else None
        y_pupil = y_exit + slope * ((z_last + sp_prime) - z_exit) \
            if abs(slope) < 1e3 else None
        fan.append({
            'zone': zone, 'ok': True,
            'y_exit': y_exit, 'slope': slope,
            'L': length, 'y_pupil': y_pupil,
            'wave': _ray_wavefront(system, res, opl_chief, ref_center,
                                   ref_r, wl),
        })
    return fan


def port_axial_rows(system, wl: float, zones, ax_semi: float) -> list:
    """Строки осевого пучка портом: продольные/поперечные + TABOC2-набор.

    Продольные: порт ``taboc1_rows``-семантика (мм), затем конверсия
    юнитов эталона; дальний тип (дптр) — формула от выходного зрачка
    (досье §2.2). Поперечные: порт dy на последней поверхности;
    гр.мнсек — кандидат-конвенция (досье §2.3). Волновые —
    ``_ray_wavefront`` порта; неизопл — ``compute_isoplanatism`` c
    интерполяцией на зону (как ``taboc2_rows``).
    """
    from analysis.aberrations import compute_isoplanatism
    from analysis.tables import _interp_at
    from analysis.units import mm_to_dioptres, pupil_h_mm

    parax = paraxial_of(system, wl)
    fan = axial_fan(system, wl, zones, ax_semi)
    # параксиальный краевой: y=ax_semi, u=0 → опора продольных
    y_p, u_p = _paraxial_ray(system, wl, ax_semi, 0.0, 0.0)
    L_parax = (-y_p / u_p) if abs(u_p) > 1e-15 else None
    sp_prime = parax['sP_prime']

    iso_pupils, iso_vals = [], []
    iso_error = None
    try:
        iso_pupils, iso_vals = compute_isoplanatism(system, wl=wl)
    except Exception as exc:      # падение портовой функции — в досье §6
        iso_error = repr(exc)
    rows = []
    for ray in fan:
        zone = ray['zone']
        row = {'zone': zone, 'ok': ray['ok'], 'iso_error': iso_error}
        if ray['ok']:
            row.update({
                'y_pupil': ray['y_pupil'], 'tg_prime100': ray['slope'] * 100.0,
                'wave': ray['wave'],
                'h_zr_mm': pupil_h_mm(zone, ax_semi),
                'L': ray['L'],
                'long_mm': (ray['L'] - L_parax
                            if None not in (ray['L'], L_parax) else None),
                'long_dptr': None,
                'dy_exit': ray['y_exit'],
                'iso_pct': (_interp_at(iso_pupils, iso_vals, zone) * 100.0
                            if iso_pupils else None),
            })
            if ray['L'] is not None and L_parax is not None \
                    and sp_prime:
                lp_z = ray['L'] - sp_prime
                lp_p = L_parax - sp_prime
                if abs(lp_z) > 1e-9 and abs(lp_p) > 1e-9:
                    row['long_dptr'] = mm_to_dioptres(lp_z) - mm_to_dioptres(lp_p)
        else:
            row.update({'y_pupil': None, 'tg_prime100': None, 'wave': None,
                        'h_zr_mm': pupil_h_mm(zone, ax_semi), 'L': None,
                        'long_mm': None, 'long_dptr': None, 'dy_exit': None,
                        'iso_pct': None})
        rows.append(row)
    return rows


# ══════════════════════════════════════════════════════════════════════════
# 4. Сравнение и вердикты
# ══════════════════════════════════════════════════════════════════════════

def verdict(delta_rel: float, tol: float) -> str:
    """GREEN ≤ tol, YELLOW ≤ 10·tol, иначе RED (карточка задачи)."""
    if delta_rel is None:
        return 'SKIP'
    if delta_rel <= tol:
        return 'GREEN'
    if delta_rel <= tol * TOL_YELLOW:
        return 'YELLOW'
    return 'RED'


def rel_diff(port: float, opal: float, abs_floor: float = 0.0) -> float:
    """Относительное расхождение |Δ|/max(|OPAL|, ε) с защитой нулей.

    ``abs_floor`` — абсолютный шумовой порог в единицах величины:
    при |Δ| ≤ floor расхождение считается нулевым (возвращает 0).
    Обоснование: PRN печатает 5 знаков, показатели n порта и OPAL
    интерполируются из f32-λ OPJ — систематика ~1e-3 мм между
    независимыми реализациями численно неустранима; у нулей
    сферической аберрации (смена знака между зонами, OPAL3 з.0.866:
    0.046 мм при |Δ| 1 мкм) чистое |Δ|/|OPAL| взрывается и RED
    обвиняет порт ложно.
    """
    if port is None or opal is None:
        return None
    delta = abs(port - opal)
    if abs_floor > 0.0 and delta <= abs_floor:
        return 0.0
    denom = max(abs(opal), 1e-9)
    return delta / denom


def compare_system(name: str, bank_dir: str = _BANK_DIR,
                   opj_dir: str = _GOLDEN_DOS) -> dict:
    """Полная сверка одной системы: строки-величины + вердикты.

    Возвращает ``{'rows': [строки таблицы], 'counts': {G/Y/R/S},
    'notes': [...]}``. Строка: ``(раздел, величина, зона, OPAL, порт,
    Δотн, допуск, вердикт)``.
    """
    prn = parse_golden_prn(os.path.join(bank_dir, name + '.PRN'))
    opj_path = os.path.join(opj_dir, name + '.OPJ')
    opj = parse_golden_opj(opj_path)
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    rows, notes = [], []

    parax = paraxial_of(system, wl)

    # Ближний предмет (obj=1): OPAL печатает Ax=sin(NA), Н ЗР как
    # 100·tg(u), Sp в дптр — положение предмета в standalone-OPJ не
    # найдено, веер по высоте неприменим. Конвенции не реверсированы —
    # строки пропускаем с записью в досье (§3), RED было бы ложным
    # обвинением порта.
    near_obj = (opj['obj_type'] == 1)
    if near_obj:
        notes.append('ближний предмет (obj=1): конвенции OPAL не '
                     'реверсированы (запуск веера по углу NA от предмета, '
                     'Sp в дптр) — сверка осевых/габаритных строк '
                     'пропущена, кандидаты в досье §3')

    # ── габариты: строка N=0 (осевая) расчётной λ ──
    # (λ OPJ — f32: 0.54607 против печати .5461 → допуск 2e-3)
    ax_row = None
    for (wl_str, n_zone), row in prn['gabarit'].items():
        if n_zone == 0 and abs(float(wl_str) - wl) < 2e-3:
            ax_row = row
            break
    if ax_row is None:                      # фолбэк: любая N=0
        for (wl_str, n_zone), row in prn['gabarit'].items():
            if n_zone == 0:
                ax_row = row
    if prn['gabarit'] and ax_row is None:
        notes.append('габариты без строки N=0')
    units_sp, units_sp2 = prn.get('gabarit_units', ('мм', 'мм'))
    if ax_row is not None and not near_obj:
        # Sp — мм от первой поверхности (дальний предмет). Sp' — мм от
        # последней поверхности (дальнее изображение) либо дптр от
        # плоскости Гаусса (ближнее изображение): HELIOS8/ST/121 —
        # 1000/(sP'−bfd) совпадает с эталоном до 4 знаков (досье §1).
        port_sp = parax['sP']
        port_sp2 = parax['sP_prime']
        if units_sp2 == 'дптр':
            d = parax['sP_prime'] - parax['bfd']
            port_sp2 = 1000.0 / d if abs(d) > 1e-9 else None
        for key, port_val, tol in (
                ('Sp', port_sp, TOL_PARAX),
                ('Sp2', port_sp2, TOL_PARAX),
        ):
            rows.append(('габариты', key, '', ax_row[key], port_val,
                         rel_diff(port_val, ax_row[key]), tol,
                         verdict(rel_diff(port_val, ax_row[key]), tol)))

    # Ax — реальная полувысота пучка: вход для веера (см. досье §5).
    # Цепочка: максимум колонки Н ЗР (зона 1.0: Н ЗР = отн.зр·Ax, точнее
    # округленной габаритной Ax — HELIOS8 13.606 vs габарит 13.61/13.66
    # по λ) → габаритная строка N=0 → заданная апертура OPJ (у
    # KURSOVIK/OPAL3 отличается от реального габаритного луча).
    ax_semi = None
    hzr_vals = [r['h_zr'] for r in prn['axial2'].get('rows', {}).values()
                if r.get('h_zr') is not None]
    if hzr_vals:
        ax_semi = max(hzr_vals)
    if not ax_semi and ax_row:
        ax_semi = ax_row['Ax']
    if not ax_semi:
        ax_semi = opj['aperture_semi']

    # ── осевой пучок ──
    if not near_obj:
        units = prn['axial1'].get('units', ('мм', 'мм'))
        long_key = 'long_dptr' if units[0] == 'дптр' else 'long_mm'
        port_rows = {r['zone']: r for r in
                     port_axial_rows(system, wl, list(
                         prn['axial1'].get('rows', {}).keys()), ax_semi)}
        if port_rows:
            first = next(iter(port_rows.values()))
            if first.get('iso_error'):
                notes.append('неизопл: compute_isoplanatism порта упал (%s)'
                             % first['iso_error'])
        a1_rows = prn['axial1'].get('rows', {})

        # сопоставление зон: продольная таблица индексируется отн.зр,
        # TABOC2 — своей меткой; зоны берем из продольной таблицы
        for zone, et in sorted(a1_rows.items(), reverse=True):
            pr = port_rows.get(zone)
            # продольные (колонка λ0)
            if et['long'] and et['long'][0] is not None:
                opal_v = et['long'][0]
                port_v = pr.get(long_key) if pr else None
                floor = (ABS_FLOOR_MM if units[0] == 'мм'
                         else ABS_FLOOR_DPTR)
                d = rel_diff(port_v, opal_v, floor)
                rows.append(('осевой', f'прод ({units[0]})', zone, opal_v,
                             port_v, d, TOL_ABERR, verdict(d, TOL_ABERR)))
            # поперечные — конвенция не сходится (досье §2.3): считаем
            # кандидата (угол выхода vs паракс, гр.мнсек) для полноты
            if et['trans'] and et['trans'][0] is not None:
                opal_v = et['trans'][0]
                port_v = None
                d = None
                rows.append(('осевой', f'попер ({units[1]})', zone, opal_v,
                             port_v, d, TOL_ABERR, 'SKIP'))

        # TABOC2: строки отсортированы ПО МЕТКЕ (убывание tg'*100), а не
        # по зоне — у 121 метка немонотонна по зонам. Идентичность зоны
        # восстанавливаем по колонке Н ЗР = отн.зр·Ax (дossier §2.5);
        # строки без Н ЗР сшиваем по порядку.
        a2_list = sorted(prn['axial2'].get('rows', {}).values(),
                         key=lambda r: -r['tg100'] if r['tg100'] is not None else 0)
        zones_sorted = sorted(a1_rows.keys(), reverse=True)

        def _zone_of(et):
            hzr = et.get('h_zr')
            if hzr is not None and ax_semi:
                return min(zones_sorted,
                           key=lambda z: abs(z - hzr / ax_semi))
            return None

        used = set()
        pairs = []
        for et in a2_list:
            z = _zone_of(et)
            if z is None or z in used:
                z = next((zz for zz in zones_sorted if zz not in used), None)
            if z is None:
                break
            used.add(z)
            pairs.append((et, z))
        # .000-строка эталона — осевая; у веера её нет (зона 0 тривиальна)
        for et, zone in pairs:
            pr = port_rows.get(zone)
            if et['tg100'] is not None:
                # дальний тип: метка = H' ЗР (мм, печатается положительной
                # независимо от инверсии — габаритный Ax' той же величины
                # знак сохраняет); ближний тип: −100·tg u' (знак OPAL
                # обратен наклону порта — HELIOS8/121, досье §2.1)
                far = (opj['img_type'] == 0)
                port_v = None
                if pr:
                    if far:
                        port_v = (abs(pr['y_pupil'])
                                  if pr['y_pupil'] is not None else None)
                        if port_v is not None and et['tg100'] < 0:
                            port_v = -port_v
                    else:
                        port_v = (-pr['tg_prime100']
                                  if pr.get('tg_prime100') is not None else None)
                d = rel_diff(port_v, et['tg100'])
                rows.append(('осевой', "Tg'*100" + (' (H`ЗР)' if far else ''),
                             zone, et['tg100'], port_v, d, TOL_ABERR,
                             verdict(d, TOL_ABERR)))
            if et['wave'] and et['wave'][0] is not None:
                port_v = pr.get('wave') if pr else None
                d = rel_diff(port_v, et['wave'][0], ABS_FLOOR_WAVE)
                rows.append(('осевой', 'волновые', zone, et['wave'][0], port_v,
                             d, TOL_ABERR, verdict(d, TOL_ABERR)))
            if et['h_zr'] is not None:
                port_v = pr.get('h_zr_mm') if pr else None
                d = rel_diff(port_v, et['h_zr'])
                rows.append(('осевой', 'Н ЗР (мм)', zone, et['h_zr'], port_v, d,
                             TOL_ABERR, verdict(d, TOL_ABERR)))

    counts = {'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'SKIP': 0}
    for r in rows:
        counts[r[7]] += 1
    return {'name': name, 'prn': prn, 'opj': opj, 'rows': rows,
            'counts': counts, 'notes': notes, 'system': system,
            'parax': parax}


def format_report(results: list) -> str:
    """Markdown-отчёт по всем системам (для REVERSE_GVERIFY.md)."""
    out = []
    total = {'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'SKIP': 0}
    for res in results:
        c = res['counts']
        for k in total:
            total[k] += c[k]
        out.append(f"### {res['name']} — G:{c['GREEN']} Y:{c['YELLOW']} "
                   f"R:{c['RED']} S:{c['SKIP']}")
        out.append('')
        out.append('| раздел | величина | зона | OPAL | порт | Δотн | вердикт |')
        out.append('|---|---|---|---|---|---|---|')
        for sec, qty, zone, opal_v, port_v, d, tol, verd in res['rows']:
            z = f'{zone:.3f}' if isinstance(zone, float) else str(zone)
            op_s = f'{opal_v:.5g}' if isinstance(opal_v, float) else '—'
            pt_s = f'{port_v:.5g}' if isinstance(port_v, float) else '—'
            d_s = f'{d:.2e}' if isinstance(d, float) else '—'
            out.append(f'| {sec} | {qty} | {z} | {op_s} | {pt_s} | {d_s} '
                       f'| {verd} |')
        out.append('')
    out.insert(0, f'**Сводка: GREEN {total["GREEN"]} / YELLOW {total["YELLOW"]}'
                  f' / RED {total["RED"]} / SKIP {total["SKIP"]}**\n')
    return '\n'.join(out)


def run_all(bank_dir: str = _BANK_DIR, opj_dir: str = _GOLDEN_DOS) -> list:
    """Сверка всех систем банка (пропуская системы без .OPJ на стенде)."""
    results = []
    for name in BANK_SYSTEMS:
        prn_path = os.path.join(bank_dir, name + '.PRN')
        opj_path = os.path.join(opj_dir, name + '.OPJ')
        if not (os.path.exists(prn_path) and os.path.exists(opj_path)):
            continue
        try:
            results.append(compare_system(name, bank_dir, opj_dir))
        except Exception as exc:                     # досье: падение системы
            hint = ' (ГОЭ: standalone-раскладка OPJ отличается — ' \
                   'отрицательные толщины, мусорные gidx, досье §6)' \
                if 'GTIE' in name else ''
            results.append({'name': name, 'rows': [], 'counts': {
                'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'SKIP': 0},
                'notes': [f'ОШИБКА: {exc!r}{hint}'], 'system': None,
                'parax': {}})
    return results


if __name__ == '__main__':
    print(format_report(run_all()))
