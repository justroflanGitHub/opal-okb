# -*- coding: utf-8 -*-
"""
OPAL-OKB — световые высоты и экранные зоны: TABESB + TABEAP (реверс §14.1).

**TABESB** «Световые высоты» (формат DS 0xdb9: ``(1X,i3,f11.3,2f12.3,4f10.3)``;
шапка 0xde0–0xe66; перед таблицей «─ Длина волны -» DS 0xda0 — индекс λ
селектора ``[0x34c6]``, §14.2): высоты Y габаритных лучей НА КАЖДОЙ
ПОВЕРХНОСТИ (ANALIZE.DOC:731–753) —

===============  =====================================  ========================
колонка OPAL     величина                              источник порта
===============  =====================================  ========================
осевой пучок     крайний луч осевого пучка (поле 0,    ``compute_gauge_rays``
                 pupil_y=+1) — «координаты по поверх-  (луч «Верх», поле 0)
                 ностям габаритного луча осевого
                 пучка» (DOC:736–738)
Верхний, Нижний  предельные лучи пучка поля — край     ``compute_gauge_rays``
                 зрачка ±Ay (DOC:739–741)
Верхн.раб,       границы зоны прохождения пучка        :func:`_work_bounds`
Нижн.раб         (крайние проходящие лучи, с учётом    — база виньетирования
                 виньетирования; DOC:749–751 «рабочая  TABBEA: vignetting.compute_vignetting
                 — в пределах их поверхность работает»
Верхн.отв,       отверстия (clear aperture) = ±semi_   ``Surface.semi_diameter``
Нижн.отв         diameter (DOC:752–753 «в пределах
                 их поверхность свободно пропускает»)
===============  =====================================  ========================

**TABEAP** «Экранные зоны» (формат DS 0xece:
``(1X,i3,4f9.5,f9.4,2f8.3,2(1x,1a,1x,i3))``; шапка 0xf01–0xfa9 «Относительные
размеры экранирования │ смещение на экране │ Виньетирование │ Ограничения
(сверху/снизу)», ось ``x y x y``; рядом «Экранирующая поверхность» 0xead):
относительное экранирование на входном/выходном зрачке эллипсом для всех
пучков (ANALIZE.DOC:488–516, 559–566) — по строке на пучок:

* ``obsc_in_x/y`` — относительный размер экрана на входном зрачке, доли
  полной апертуры Ax/Ay (центральное экранирование → x=y=k);
* ``obsc_out_x/y`` — то же на выходном (линейность отображения
  диафрагмы в зрачки — размер в долях полной апертуры сохраняется);
* ``screen_shift`` — смещение центра эллипса экранирования относительно
  центра зрачка на экране (диафрагме), доли радиуса зрачка;
* ``vignetting_upper/lower`` — виньетирование верх/низ: отношение
  срезаемой части пучка к половине её диаметра, доли (DOC:549–551);
* ``limit_upper/lower`` — «Ограничения»: код + номер ограничивающей
  поверхности для верхнего/нижнего края пучка —
  :data:`vignetting.LIMIT_LETTERS`: «D» диафрагма / «P» поверхность /
  «M» зеркало-экран, нумерация с 1, 0 — диафрагма вне списка (§14.3 —
  [РЕКОНСТРУКЦИЯ: подлинные буквы НЕИЗВЕСТНО, раскладка TSR-буфера];
  единые с TABBEA).

Габаритная база — :func:`domain.calculations.compute_beam_geometry` (апертуры
Ax/Ay/Ax'/Ay'); трассировка не дублируется: лучи —
:func:`aberrations.compute_gauge_rays` / ``_pupil_field_ray`` +
:func:`ray_tracing.trace_ray_through_system` (точный трейсер с историей
координат). Виньетирование и ограничивающие элементы —
:func:`vignetting.compute_vignetting` (меридиональный веер, бисекция
:data:`VIGNETTING_BISECT_STEPS` по точному трейсеру ray_native) — те же
числа и буквы, что в TABBEA; параксиальное продолжение domain-трейсера
занижает зону косых пучков (Индустар-23у, поле 26°: 0.0/0.0 против
0.45/0.60 точного).

Форматы чисел — FORTRAN Fw.d без ведущего нуля (:func:`tables._fwo`,
эталонный стиль RT__2250.PRN). Раскладка шапок — [РЕКОНСТРУКЦИЯ]:
строки-коробки лежат в DS подряд (§14.0), точная нарезка печатальщика
[НЕИЗВЕСТНО: TSR-сегменты]; линейка шапки выровнена точно по границам
полей формата.
"""
from optics_engine import OpticalSystem, paraxial_trace
from optics_utils import compute_z_positions, get_effective_aperture, get_primary_wl

from analysis.aberrations import (_compute_ray_start, _pupil_field_ray,
                                  compute_gauge_rays)
from analysis.tables import _fwo
from analysis.vignetting import compute_vignetting
from domain.calculations import compute_beam_geometry
from ray_tracing import trace_ray_through_system

#: Ширины полей строк данных TABESB (после «1X,i3»): f11.3, 2×f12.3,
#: 4×f10.3 — формат DS 0xdb9.
TABESB_FIELD_SPECS = ((11, 3), (12, 3), (12, 3),
                      (10, 3), (10, 3), (10, 3), (10, 3))

#: Ключи строк TABESB в порядке колонок формата.
TABESB_KEYS = ('axial_y', 'upper_y', 'lower_y',
               'work_upper_y', 'work_lower_y',
               'aperture_upper', 'aperture_lower')

#: Колонки шапки TABESB: (ширина, подпись) — DS 0xde0–0xe66.
TABESB_COLUMNS = ((3, 'Пов'), (11, 'осевой пучок'), (12, 'Верхний'),
                  (12, 'Нижний'), (10, 'Верхн.раб'), (10, 'Нижн.раб'),
                  (10, 'Верхн.отв'), (10, 'Нижн.отв'))

#: Ширины числовых полей TABEAP (после «1X,i3»): 4×f9.5, f9.4, 2×f8.3 —
#: DS 0xece; хвост 2×(1x,1a,1x,i3) — пары «буква+N» (6 позиций каждая).
TABEAP_FIELD_SPECS = ((9, 5), (9, 5), (9, 5), (9, 5),
                      (9, 4), (8, 3), (8, 3))

#: Ключи строк TABEAP в порядке числовых колонок формата.
TABEAP_KEYS = ('obsc_in_x', 'obsc_in_y', 'obsc_out_x', 'obsc_out_y',
               'screen_shift', 'vignetting_upper', 'vignetting_lower')

#: Колонки шапки TABEAP: (ширина, подпись) — шапка 0xf01–0xfa9, ось «x y x y».
TABEAP_COLUMNS = ((3, 'N'), (9, 'вход x'), (9, 'вход y'), (9, 'выход x'),
                  (9, 'выход y'), (9, 'смещение'), (8, 'верх'),
                  (8, 'низ'), (6, 'верх'), (6, 'низ'))

#: Допуск сопоставления точки пути с плоскостью (мм) — как
#: ``_gauge_point_labels`` (gui/analysis_panel.py).
_Z_MATCH_TOL = 1e-6


# ── Трассировка: луч по зрачковой координате + высоты на поверхностях ──────

def _pupil_ray(system: OpticalSystem, wl: float, field_y: float,
               pupil_y: float):
    """Луч пучка ``field_y`` через точку ``pupil_y`` зрачка (доли Ay).

    Тот же построитель, что :func:`aberrations.compute_gauge_rays`
    (``_pupil_field_ray``), — трассировка не дублируется.
    """
    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)
    ray = _pupil_field_ray(system, 0.0, pupil_y * aperture / 2,
                           field_y, z_start, z_pupil)
    return trace_ray_through_system(system, ray, wl)


def _surface_heights(system: OpticalSystem, points):
    """Y-высоты луча на поверхностях + высота в плоскости изображения.

    Разбор пути (``TraceResult.path`` / ``points`` габаритного луча) по
    схеме ``_gauge_point_labels``: точка 0 — старт; точка в плоскости
    диафрагмы (вставляется трейсером после прохождения поверхности
    диафрагмы) пропускается; точка на плоскости изображения за
    последней поверхностью даёт ``image_y``. Поверхности нумеруются по
    порядку встречи; недошедшим лучам соответствуют ``None``.
    """
    z_pos = compute_z_positions(system)
    stop_idx = getattr(system, 'stop_surface', -1)
    # stop_surface — 1-индексация (OPAL ND): плоскость = вершина
    # поверхности stop_surface−1 + stop_offset
    z_stop = (z_pos[stop_idx - 1] + getattr(system, 'stop_offset', 0.0)
              if 1 <= stop_idx <= len(z_pos) else None)
    n = len(system.surfaces)
    heights = [None] * n
    consumed = 0
    image_y = None
    pts = points
    for j, (_x, y, z) in enumerate(pts):
        if j == 0:
            continue
        is_image = (j == len(pts) - 1 and consumed == n
                    and abs(z - z_pos[-1]) < _Z_MATCH_TOL)
        if is_image:
            image_y = y
            continue
        if (z_stop is not None and abs(z - z_stop) < _Z_MATCH_TOL
                and consumed > stop_idx):
            continue                       # точка в плоскости диафрагмы
        if consumed < n:
            heights[consumed] = y
            consumed += 1
    return heights, image_y


def _work_bounds(system: OpticalSystem, field_y: float, wl: float):
    """Границы зоны прохождения пучка по зрачку: ``(верх, низ)`` — доли Ay.

    Доли зрачка, до которых лучи ещё проходят (1 — край не срезан);
    база — :func:`vignetting.compute_vignetting` (меридиональный веер,
    бисекция :data:`VIGNETTING_BISECT_STEPS` по точному трейсеру) — те
    же числа, что виньетирование TABBEA (1 − % срезанного края).
    """
    vign = compute_vignetting(system, field_y, wl)
    return (1.0 - vign['vignet_up'] / 100.0,
            1.0 - vign['vignet_down'] / 100.0)


# ── Шапки (выравнивание — по границам полей формата) ───────────────────────

def _header_label_line(columns) -> str:
    """Строка подписей шапки: сегменты шириной колонок, «│» на границах."""
    return (' ' + '│'.join(label.center(width)
                            for width, label in columns)).rstrip()


def _header_ruler_line(columns) -> str:
    """Линейка шапки: «┴» точно на границах полей формата."""
    return ' ' + '┴'.join('─' * width for width, _label in columns)


#: Заголовок TABESB — строки шапки после титула и строки «Длина волны».
TABESB_HEADER = (_header_label_line(TABESB_COLUMNS),
                 _header_ruler_line(TABESB_COLUMNS))

#: Групповая строка TABEAP: сегменты шириной колонок формата
#: (3, 4×9, 9, 2×8, 2×6) — «│» на тех же границах, что у линейки.
TABEAP_GROUP_LINE = ' ' + '│'.join((
    'N'.ljust(3),
    'Относительные размеры экранирования'.center(36),
    'смещение'.center(9),
    'Виньетирование'.center(16),
    'Ограничения'.center(12),
))

TABEAP_HEADER = (TABEAP_GROUP_LINE,
                 _header_label_line(TABEAP_COLUMNS),
                 _header_ruler_line(TABEAP_COLUMNS))

TABESB_TITLE = 'Световые высоты'
TABEAP_TITLE = 'Экранные зоны (экранирование пучков)'


# ── TABESB ─────────────────────────────────────────────────────────────────

def _wl_index(system: OpticalSystem, wl: float) -> int:
    """Индекс λ (1-based) в ``system.wavelengths``; 0 — вне набора."""
    for i, w in enumerate(system.wavelengths):
        if abs(float(w.value) - wl) < 1e-6:
            return i + 1
    return 0


def tabesb_rows(system: OpticalSystem, field_y: float = 0.0,
                wl: float = None) -> list:
    """Световые высоты габаритных лучей по поверхностям (TABESB, §14.1).

    Для каждой поверхности i (строка ``n = i+1``, 1-based как в OPAL):

    * ``axial_y`` — высота крайнего луча осевого пучка (поле 0,
      pupil_y=+1; DOC:736–738 — выводится всегда);
    * ``upper_y``/``lower_y`` — предельные лучи пучка поля ``field_y``
      (край зрачка ±Ay);
    * ``work_upper_y``/``work_lower_y`` — верхняя/нижняя рабочие высоты:
      высоты крайних проходящих лучей (зона прохождения с учётом
      виньетирования, :func:`_work_bounds`);
    * ``aperture_upper``/``aperture_lower`` — верхнее/нижнее отверстия
      (clear aperture) = ±``semi_diameter`` (``None`` — не задан).

    Если трейсер дошёл до плоскости изображения за последней
    поверхностью, добавляется замыкающая строка ``n = len+1``
    (в OPAL-системах LBO плоскость изображения — сама последняя
    поверхность, и замыкающей строки нет).

    Args:
        system: Оптическая система.
        field_y: Поле пучка (град / мм) — знак OPAL: предмет
            отрицательный (как :func:`tables._zone_field`).
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        Список словарей-строк; каждая несёт мету ``wl``/``wl_index``
        (индекс селектора «─ Длина волны -», §14.2) и ``field_y``.
        ``None`` — луч не дошёл до поверхности (печать — пробелы).
    """
    if not system.surfaces:
        return []
    if wl is None:
        wl = get_primary_wl(system)

    # Габаритная база — compute_beam_geometry ('given': та же апертура
    # Ay, которой масштабируются зрачковые координаты лучей); лучи с
    # историей — compute_gauge_rays (крайние) + _pupil_ray (рабочие).
    axial_rays = compute_gauge_rays(system, wl=wl, field_y=0.0)
    field_rays = (axial_rays if field_y == 0
                  else compute_gauge_rays(system, wl=wl, field_y=field_y))
    pass_upper, pass_lower = _work_bounds(system, field_y, wl)

    series = {
        'axial_y': _surface_heights(system, axial_rays[0]['points']),
        'upper_y': _surface_heights(system, field_rays[0]['points']),
        'lower_y': _surface_heights(system, field_rays[1]['points']),
        'work_upper_y': _surface_heights(
            system, _pupil_ray(system, wl, field_y, pass_upper).path),
        'work_lower_y': _surface_heights(
            system, _pupil_ray(system, wl, field_y, -pass_lower).path),
    }
    wl_idx = _wl_index(system, wl)
    n = len(system.surfaces)
    has_image = any(img is not None
                    for _heights, img in series.values())

    rows = []
    for i in range(n):
        s = system.surfaces[i]
        sd = s.semi_diameter if s.semi_diameter > 0 else None
        rows.append({
            'n': i + 1,
            'axial_y': series['axial_y'][0][i],
            'upper_y': series['upper_y'][0][i],
            'lower_y': series['lower_y'][0][i],
            'work_upper_y': series['work_upper_y'][0][i],
            'work_lower_y': series['work_lower_y'][0][i],
            'aperture_upper': sd,
            'aperture_lower': -sd if sd is not None else None,
            'wl': wl, 'wl_index': wl_idx, 'field_y': field_y,
        })
    if has_image:
        rows.append({
            'n': n + 1,
            'axial_y': series['axial_y'][1],
            'upper_y': series['upper_y'][1],
            'lower_y': series['lower_y'][1],
            'work_upper_y': series['work_upper_y'][1],
            'work_lower_y': series['work_lower_y'][1],
            'aperture_upper': None, 'aperture_lower': None,
            'wl': wl, 'wl_index': wl_idx, 'field_y': field_y,
        })
    return rows


def format_tabesb(rows) -> str:
    """Таблица TABESB целиком: титул + «─ Длина волны -» + шапка + данные.

    Формат DS 0xdb9 ``(1X,i3,f11.3,2f12.3,4f10.3)`` плюс строка
    «─ Длина волны - <N>» (DS 0xda0; N — индекс λ селектора ``[0x34c6]``,
    §14.2). Числа — Fw.d без ведущего нуля (:func:`tables._fwo`).
    """
    wl_idx = rows[0].get('wl_index', 0) if rows else 0
    lines = [TABESB_TITLE.center(79).rstrip(), f'─ Длина волны - {wl_idx}',
             *TABESB_HEADER]
    for row in rows:
        n_field = f"{row['n']:3d}"
        line = ' ' + n_field + ''.join(
            _fwo(row.get(key), w, d)
            for key, (w, d) in zip(TABESB_KEYS, TABESB_FIELD_SPECS))
        lines.append(line.rstrip())
    return '\n'.join(lines)


# ── TABEAP ─────────────────────────────────────────────────────────────────

def _y_at_z(points, z_plane: float):
    """Y-координата луча в плоскости ``z_plane`` (линейная интерполяция).

    ``None`` — плоскость вне пути луча.
    """
    for (x0, y0, z0), (x1, y1, z1) in zip(points, points[1:]):
        lo, hi = min(z0, z1), max(z0, z1)
        if lo - _Z_MATCH_TOL <= z_plane <= hi + _Z_MATCH_TOL:
            dz = z1 - z0
            if abs(dz) < _Z_MATCH_TOL:
                return y0
            return y0 + (z_plane - z0) / dz * (y1 - y0)
    return None


def tabeap_rows(system: OpticalSystem, wl: float = None) -> list:
    """Экранные зоны экранирования по пучкам (TABEAP, §14.1).

    По строке на каждый пучок (``field_points``, включая осевой; без
    точек поля — одна осевая строка). Относительные размеры экрана —
    центральное экранирование ``system.obscuration_ratio`` в долях
    полных апертур входного/выходного зрачка (габаритная база —
    :func:`compute_beam_geometry`: линейность отображения диафрагмы в
    зрачки сохраняет относительный размер k). Смещение — высота
    главного луча в плоскости диафрагмы в долях радиуса зрачка (для
    центрального экрана без поля — 0; при k=0 экрана нет — 0).
    Виньетирование (доли срезанного края, DOC:549–551) и «Ограничения»
    (буквы :data:`vignetting.LIMIT_LETTERS`) —
    :func:`vignetting.compute_vignetting`, как в TABBEA.

    Для систем без экранирования колонки размеров/смещения — нули.

    Args:
        system: Оптическая система.
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        Список словарей-строк (ключи ``n, field_y, obsc_in_x, obsc_in_y,
        obsc_out_x, obsc_out_y, screen_shift, vignetting_upper,
        vignetting_lower, limit_upper, limit_lower, obscuration,
        stop_surface``); ``limit_*`` — ``(буква, N)`` или ``None``.
    """
    if wl is None:
        wl = get_primary_wl(system)
    if not system.surfaces:
        return []

    k = abs(getattr(system, 'obscuration_ratio', 0.0) or 0.0)
    # Габаритная база: Ay/Ax/Ax'/Ay' пучков (нормировка зрачка)
    geo = compute_beam_geometry(system, wl=wl)
    ay = geo[0]['Ay'] if geo else get_effective_aperture(system, default=10.0) / 2.0
    z_pos = compute_z_positions(system)
    stop_idx = getattr(system, 'stop_surface', -1)
    # stop_surface — 1-индексация (OPAL ND): плоскость = вершина
    # поверхности stop_surface−1 + stop_offset
    z_stop = (z_pos[stop_idx - 1] + getattr(system, 'stop_offset', 0.0)
              if 1 <= stop_idx <= len(z_pos) else None)

    fields = [fp.y for fp in (system.field_points or [])] or [0.0]
    rows = []
    for n, field_y in enumerate(fields, start=1):
        vign = compute_vignetting(system, field_y, wl)
        chief = compute_gauge_rays(system, wl=wl, field_y=field_y)[2]
        shift = 0.0
        if k > 0 and ay > 1e-12 and z_stop is not None:
            y_chief = _y_at_z(chief['points'], z_stop)
            if y_chief is not None:
                shift = y_chief / ay
        rows.append({
            'n': n, 'field_y': field_y,
            'obsc_in_x': k, 'obsc_in_y': k,
            'obsc_out_x': k, 'obsc_out_y': k,
            'screen_shift': shift,
            'vignetting_upper': vign['vignet_up'] / 100.0,
            'vignetting_lower': vign['vignet_down'] / 100.0,
            'limit_upper': vign['limit_up'],
            'limit_lower': vign['limit_down'],
            'obscuration': k,
            'stop_surface': stop_idx,
        })
    return rows


def _format_limit_pair(pair) -> str:
    """Пара «(1x,1a,1x,i3)»: буква + номер поверхности (или пробелы)."""
    if pair is None:
        return ' ' * 6
    letter, num = pair
    return f' {letter} {num:3d}'


def format_tabeap(rows) -> str:
    """Таблица TABEAP целиком: титул + экран + шапка + данные.

    Формат DS 0xece ``(1X,i3,4f9.5,f9.4,2f8.3,2(1x,1a,1x,i3))``. Строка
    «Экранирующая поверхность» (DS 0xead): условный номер 0 —
    апертурная диафрагма (ANALIZE.DOC:508–509); без экранирования
    строка не печатается.
    """
    k = rows[0].get('obscuration', 0.0) if rows else 0.0
    lines = [TABEAP_TITLE.center(77).rstrip()]
    if k > 0:
        lines.append('Экранирующая поверхность 0 (апертурная диафрагма)')
    lines += list(TABEAP_HEADER)
    for row in rows:
        n_field = f"{row['n']:3d}"
        line = ' ' + n_field + ''.join(
            _fwo(row.get(key), w, d)
            for key, (w, d) in zip(TABEAP_KEYS, TABEAP_FIELD_SPECS))
        line += _format_limit_pair(row.get('limit_upper'))
        line += _format_limit_pair(row.get('limit_lower'))
        lines.append(line.rstrip())
    return '\n'.join(lines)
