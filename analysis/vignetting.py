# -*- coding: utf-8 -*-
"""
OPAL-OKB — виньетирование, светораспределение и ограничивающие
поверхности (реверс §14.1 + §17.6, TASK_VIGNET).

Закрывает **вычислительный пробел №1** порта (REVERSE_0746.md §17.6):
в OPAL-PC колонки «Виньетир.»/«Светораспред.»/«Ограничения» таблицы
TABBEA считал режим «ограничивающая поверхность» [0x39D0] (досрочный
выход трейсера 0x10C9B–0x10DB7) и Σ-накопитель веера (0x10FB8–0x11035)
— в порте их не было вовсе. Здесь — прямые величины порта:

===============  ============================  ==========================
колонка TABBEA   величина                     источник порта
===============  ============================  ==========================
N                поле (порядок ``fields``)    —
Ax, Ay           передние апертуры, мм        compute_beam_geometry
Ax', Ay'         задние апертуры, мм          compute_beam_geometry
Sp, Sp'          входной/выходной зрачок, мм  paraxial_trace (sP/sP')
виньетир. верх/низ, % срезанного края        compute_vignetting
светораспределение верх/низ, доля            compute_light_distribution
ограничения 2×(буква+N)                       compute_vignetting
===============  ============================  ==========================

**TABBEA** (формат DS 0xc56:
``(1x,i2,2f8.5,2F8.5,2f10.3,2f6.3,2f6.1,2(1x,1a,1x,i3))``; шапка
0xc97–0xd4c «Апертуры │ Положение зрачков │ Виньетир. │ Светораспред │
Ограничения», ось «Ax Ay Ax' Ay' Sp Sp'»; словарь терминов §19.3.1).

Определения (ANALIZE.DOC, словарь REVERSE_NZR.md §19.3.1):

* **виньетирование** (:549–551) — отношение срезаемой части пучка к
  половине её диаметра, отдельно для верха и низа;
* **светораспределение** (:552–558) — отношение площади зрачка пучка
  (в обобщённых зрачковых координатах) к площади зрачка осевого пучка
  основной длины волны; для близкого изображения — функция
  освещённости.

Буквы кода «Ограничения» — [ГИПОТЕЗА]: какие буквы пишутся в буфер,
в реверсе не подтверждено (§14.3: раскладка TSR-буфера неизвестна);
подобраны по смыслу шапок TABBEA/TABEAP — см. :data:`LIMIT_LETTERS`.
"""
import math
from typing import Dict, List, Optional, Tuple

import ray_native
from optics_engine import FieldPoint, OpticalSystem, paraxial_trace
from optics_utils import get_effective_aperture, get_primary_wl

from analysis.aberrations import _compute_ray_start, _pupil_field_ray
from analysis.tables import _fwo
from domain.calculations import VIGNETTING_BISECT_STEPS, compute_beam_geometry

#: Коды ограничивающего элемента — колонка «Ограничения» TABBEA/TABEAP
#: (``2(1x,1a,1x,i3)`` — буква + номер поверхности). Буквы [ГИПОТЕЗА]
#: (§14.3), по смыслу шапок: диафрагма / поверхность / зеркало-экран.
LIMIT_LETTERS = {
    'diaphragm': 'D',   # апертурная диафрагма (N = stop_surface)
    'surface': 'P',     # линзовая поверхность (N — 1-значный номер OPAL)
    'mirror': 'M',      # зеркало-экран (ограничивающая поверхность отражает)
}

#: Ширины полей строк данных TABBEA после «1x,i2»: апертуры 4×f8.5,
#: зрачки 2×f10.3, виньетирование 2×f6.3, светораспределение 2×f6.1 —
#: формат DS 0xc56.
TABBEA_FIELD_SPECS = ((8, 5), (8, 5), (8, 5), (8, 5),
                      (10, 3), (10, 3),
                      (6, 3), (6, 3),
                      (6, 1), (6, 1))

#: Заголовок TABBEA — реконструкция по шапке DS 0xc97–0xd4c (точная
#: нарезка строк печатальщика неизвестна — TSR-сегменты §14.0; группы
#: «Апертуры │ Положение зрачков │ Виньетир. │ Светораспред │
#: Ограничения» и ось «Ax Ay Ax' Ay' Sp Sp'» восстановлены).
TABBEA_HEADER = (
    '               Апертурные характеристики пучков',
    ' ═ N │          Апертуры           │ Положение зрачков │Виньетир.│'
    'Светораспр│  Ограничения',
    " ═   │   Ax       Ay     │   Ax'      Ay'    │   Sp        Sp'   │"
    'верх  низ│верх  низ│верх    низ',
    ' ═───┴' + '─' * 8 + '┴' + '─' * 8 + '┴' + '─' * 8 + '┴' + '─' * 8
    + '┴' + '─' * 10 + '┴' + '─' * 10 + '┴' + '─' * 6 + '┴' + '─' * 6
    + '┴' + '─' * 6 + '┴' + '─' * 6 + '┴' + '─' * 6 + '┴' + '─' * 6,
)

#: Сетка зрачка для светораспределения: нечётная n×n по квадрату
#: [−1, 1]², учитываются узлы единичного круга (≈π/4·n² точек).
LIGHT_GRID_N = 15


# ── Ограничивающие элементы ────────────────────────────────────────────────

def _stop_limit(system: OpticalSystem) -> Tuple[str, int]:
    """Ограничение «апертурная диафрагма»: ``('D', N)``.

    N = ``stop_surface`` (1-значная нумерация OPAL), если стоп лежит
    на поверхности списка; иначе 0 — «0 = апертурная диафрагма»
    (виртуальный стоп вне списка поверхностей, §14.3).
    """
    ns = len(system.surfaces)
    n = int(getattr(system, 'stop_surface', 0) or 0)
    if not 1 <= n <= ns:
        n = 0
    return (LIMIT_LETTERS['diaphragm'], n)


def _limit_from_failure(system: OpticalSystem, result
                        ) -> Tuple[str, int]:
    """Ограничивающий элемент по упавшему краевому лучу.

    Отображение ошибок трейсера (``trace_ray_through_system`` /
    ``ray_native.trace_batch``): ``'EDGE'``/``'MISS'`` — луч срезан
    полудиаметром поверхности ``surfaces_hit`` (счётчик срезавшую
    поверхность не включает); ``'TIR'`` — падение на самой
    ``surfaces_hit`` (она уже посчитана). Отражающая поверхность —
    код 'M' (зеркало-экран), линзовая — 'P'; ``'STOP'`` и прочее —
    диафрагма 'D'.
    """
    if result is None or result.error in (None, 'STOP'):
        return _stop_limit(system)
    idx = result.surfaces_hit
    if result.error == 'TIR':
        idx -= 1
    if not 0 <= idx < len(system.surfaces):
        return _stop_limit(system)
    key = 'mirror' if system.surfaces[idx].is_reflective else 'surface'
    return (LIMIT_LETTERS[key], idx + 1)     # нумерация поверхностей с 1


# ── Виньетирование ─────────────────────────────────────────────────────────

def compute_vignetting(system: OpticalSystem, field_y: float,
                       wl: Optional[float] = None) -> Dict:
    """Виньетирование верх/низ пучка на поле ``field_y`` (TABBEA, §14.1).

    Определение ANALIZE.DOC:549–551 (словарь §19.3.1): отношение
    срезаемой части пучка к половине её диаметра, отдельно для верха и
    низа. Метод — меридиональный веер через входной зрачок (лучи
    :func:`aberrations._pupil_field_ray`, трассировка батчем
    ``ray_native`` до плоскости изображения — «best-focus»):
    краевой луч зрачка (rel_y = ±1) трассируется первым — если прошёл,
    край не срезан (0 %, пучок ограничен апертурной диафрагмой, код
    'D'); иначе бинарным поиском (:data:`VIGNETTING_BISECT_STEPS`)
    ищется максимальный прошедший rel_y, виньетирование = доля
    срезанного зрачкового интервала (1 − rel_y), % — «первая
    поверхность, где луч срезан», по ошибке краевого луча.

    Центральное экранирование (``obscuration_ratio``) края не срезает
    (это «экранные зоны» TABEAP, §14.4): здесь оно только поднимает
    флаг ``obscured``; уменьшение площади от экрана считает
    :func:`compute_light_distribution`.

    Args:
        system: Оптическая система (не изменяется).
        field_y: Угол поля (град) для INFINITE / высота предмета (мм)
            для FINITE.
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        ``{'vignet_up': %, 'vignet_down': %,
        'limit_up': (буква, N), 'limit_down': (буква, N),
        'obscured': bool}`` — буквы :data:`LIMIT_LETTERS`, N — номер
        поверхности (1-значная нумерация OPAL; 0 = диафрагма).
    """
    empty = {'vignet_up': 0.0, 'vignet_down': 0.0,
             'limit_up': _stop_limit(system),
             'limit_down': _stop_limit(system), 'obscured': False}
    if not system.surfaces:
        return dict(empty)
    if wl is None:
        wl = get_primary_wl(system)
    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)

    def trace(rel: float, sign: float):
        """Луч веера на относительной зрачковой высоте sign·rel."""
        ray = _pupil_field_ray(system, 0.0, sign * rel * aperture / 2.0,
                               field_y, z_start, z_pupil)
        return ray_native.trace_batch(
            system, [(ray.x, ray.y, ray.z, ray.k, ray.l, ray.m)], wl)[0]

    out = dict(empty)
    for key, sign in (('up', 1.0), ('down', -1.0)):
        edge = trace(1.0, sign)
        if edge.success:
            continue                      # край не срезан: 0 %, диафрагма
        lo, hi = 0.0, 1.0                 # [0..rel]: главный луч → край
        for _ in range(VIGNETTING_BISECT_STEPS):
            mid = (lo + hi) / 2.0
            if trace(mid, sign).success:
                lo = mid
            else:
                hi = mid
        out[f'vignet_{key}'] = (1.0 - lo) * 100.0
        out[f'limit_{key}'] = _limit_from_failure(system, edge)
    out['obscured'] = bool(getattr(system, 'obscuration_ratio', 0.0) > 0.0)
    return out


# ── Светораспределение ─────────────────────────────────────────────────────

def compute_light_distribution(system: OpticalSystem, fields,
                               wl: Optional[float] = None,
                               grid_n: int = LIGHT_GRID_N) -> List[Dict]:
    """Светораспределение по полям (TABBEA §14.1 + Σ-накопитель §17.6).

    Определение ANALIZE.DOC:552–558 (словарь §19.3.1): отношение
    площади зрачка пучка — в обобщённых зрачковых координатах,
    нормированных на радиус входного зрачка осевого пучка основной λ —
    к площади зрачка осевого пучка. Метод — прямой эквивалент обратной
    трассировки «от поля через апертурную диафрагму»: единичный зрачок
    сканируется сеткой ``grid_n × grid_n`` (узлы круга), луч каждого
    узла трассируется батчем; зона прохождения = узлы с дошедшими
    лучами, доля площади = доля прошедших узлов от всех узлов круга
    (знаменатель — «площадь зрачка осевого пучка»: экран не вычитается
    и у осевого пучка, поэтому экранированная система даёт < 1 уже на
    осевом поле). Центральное экранирование блокирует узлы
    |ρ| < ``obscuration_ratio`` (правило ``trace_fan``).

    «Верх/низ» — доли по половинам зрачка (py > 0 / py < 0), каждая
    нормирована на свою половину площади осевого зрачка (у
    невиньетированной системы — 1.0).

    Σ-накопитель §17.6 (0x10FB8–0x11035 — накопительная сумма координат
    веера в кэш-ячейку): ``centroid_y`` — центроид прошедших лучей
    сетки на плоскости изображения (Σ y / число лучей); у
    невиньетированного осевого пучка симметричной системы — 0.

    Args:
        system: Оптическая система (не изменяется).
        fields: Поля (град / мм).
        wl: Длина волны (мкм); None → основная λ системы.
        grid_n: Узлов сетки по оси зрачка (нечётное; ≥ 3).

    Returns:
        Список словарей (по одному на поле): ``field_y, light_up,
        light_down, light_total, centroid_y, n_samples, n_passed``;
        доли 0..1; ``None`` — нет узлов в половине зрачка / ни один
        луч не прошёл (centroid).
    """
    fields = list(fields)
    if not system.surfaces or not fields:
        return []
    if wl is None:
        wl = get_primary_wl(system)
    aperture = get_effective_aperture(system, default=10.0)
    radius = aperture / 2.0
    obscuration = float(getattr(system, 'obscuration_ratio', 0.0) or 0.0)
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)

    grid_n = max(3, int(grid_n))
    if grid_n % 2 == 0:
        grid_n += 1                        # симметричная сетка
    coords = [2.0 * i / (grid_n - 1) - 1.0 for i in range(grid_n)]
    nodes = [(px, py) for py in coords for px in coords
             if px * px + py * py <= 1.0]

    results = []
    for field_y in fields:
        rays: List[Tuple[float, ...]] = []
        slots: List[Optional[int]] = []    # узел → индекс луча (None — экран)
        for px, py in nodes:
            if math.hypot(px, py) < obscuration:
                slots.append(None)
                continue
            ray = _pupil_field_ray(system, px * radius, py * radius,
                                   field_y, z_start, z_pupil)
            rays.append((ray.x, ray.y, ray.z, ray.k, ray.l, ray.m))
            slots.append(len(rays) - 1)
        traced = ray_native.trace_batch(system, rays, wl)

        def passed(slot: Optional[int]) -> bool:
            return slot is not None and traced[slot].success

        n_up = sum(1 for _, py in nodes if py > 0)
        n_dn = sum(1 for _, py in nodes if py < 0)
        p_up = sum(1 for (px, py), slot in zip(nodes, slots)
                   if py > 0 and passed(slot))
        p_dn = sum(1 for (px, py), slot in zip(nodes, slots)
                   if py < 0 and passed(slot))
        p_all = sum(1 for slot in slots if passed(slot))
        ys = [traced[slot].path[-1][1] for slot in slots
              if passed(slot) and traced[slot].path]
        results.append({
            'field_y': field_y,
            'light_up': (p_up / n_up) if n_up else None,
            'light_down': (p_dn / n_dn) if n_dn else None,
            'light_total': (p_all / len(nodes)) if nodes else None,
            'centroid_y': (sum(ys) / len(ys)) if ys else None,
            'n_samples': len(nodes),
            'n_passed': p_all,
        })
    return results


# ── TABBEA ─────────────────────────────────────────────────────────────────

def tabbea_rows(system: OpticalSystem, fields=None,
                wl: Optional[float] = None) -> List[Dict]:
    """Строки TABBEA — апертурные характеристики по полям (§14.1).

    По строке на поле: апертуры Ax/Ay/Ax'/Ay' и виньетирование —
    :func:`domain.calculations.compute_beam_geometry` (словарь §19.3.1
    вяжет колонки именно к нему; габариты считаются на подменённом
    ``field_points`` — система восстанавливается), положение зрачков
    Sp/Sp' — :func:`paraxial_trace` (sP/sP' — «расстояние от первой
    (последней) поверхности», ANALIZE.DOC:427–432), виньетирование и
    ограничения — :func:`compute_vignetting`, светораспределение —
    :func:`compute_light_distribution` (поля — одним прогоном).

    Args:
        system: Оптическая система (возвращается неизменной).
        fields: Поля (град / мм); None → ``system.field_points``,
            при пустом списке — осевое поле [0].
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        Список словарей-строк с ключами ``n, field_y, Ax, Ay, Ax_prime,
        Ay_prime, Sp, Sp_prime, vignet_up, vignet_down, light_up,
        light_down, limit_up, limit_down, obscured`` (доли
        светораспределения 0..1; в :func:`format_tabbea` печатаются
        в %). Пустая система — строки нулей с пробелами
        светораспределения.
    """
    if fields is None:
        fields = ([fp.y for fp in system.field_points]
                  if system.field_points else [0.0])
    fields = list(fields)
    if not system.surfaces:
        return [{'n': i + 1, 'field_y': f,
                 'Ax': 0.0, 'Ay': 0.0, 'Ax_prime': 0.0, 'Ay_prime': 0.0,
                 'Sp': 0.0, 'Sp_prime': 0.0,
                 'vignet_up': 0.0, 'vignet_down': 0.0,
                 'light_up': None, 'light_down': None,
                 'limit_up': _stop_limit(system),
                 'limit_down': _stop_limit(system), 'obscured': False}
                for i, f in enumerate(fields)]

    if wl is None:
        wl = get_primary_wl(system)
    parax = paraxial_trace(system)
    lights = compute_light_distribution(system, fields, wl=wl)

    orig_fields = system.field_points
    rows: List[Dict] = []
    try:
        for i, (field_y, light) in enumerate(zip(fields, lights), start=1):
            system.field_points = [FieldPoint(field_y)]
            geom = compute_beam_geometry(system, wl=wl)[0]
            vign = compute_vignetting(system, field_y, wl=wl)
            rows.append({
                'n': i,
                'field_y': field_y,
                'Ax': geom.get('Ax', 0.0),
                'Ay': geom.get('Ay', 0.0),
                'Ax_prime': geom.get('Ax_prime', 0.0),
                'Ay_prime': geom.get('Ay_prime', 0.0),
                'Sp': parax.get('sP', 0.0),
                'Sp_prime': parax.get('sP_prime', 0.0),
                'vignet_up': vign['vignet_up'],
                'vignet_down': vign['vignet_down'],
                'light_up': light.get('light_up') if light else None,
                'light_down': light.get('light_down') if light else None,
                'limit_up': vign['limit_up'],
                'limit_down': vign['limit_down'],
                'obscured': vign['obscured'],
            })
    finally:
        system.field_points = orig_fields
    return rows


def format_tabbea(rows) -> str:
    """Таблица TABBEA целиком: реконструированная шапка + строки данных.

    Данные — формат DS 0xc56 плюс один ведущий пробел печатальщика
    (как ``format_tabgl``): 1 + 1 + 2 + 32 + 20 + 12 + 12 + 12 = 92
    символа. Светораспределение печатается в % (единицы колонок —
    словарь §19.3.1), виньетирование уже в %. Пары «Ограничения» —
    ``2(1x,1a,1x,i3)``: пробел, буква кода, пробел, номер поверхности
    шириной 3. Формат чисел — :func:`tables._fwo` (FORTRAN Fw.d без
    ведущего нуля, переполнение — звёздочки).
    """
    lines = list(TABBEA_HEADER)
    numeric_keys = ('Ax', 'Ay', 'Ax_prime', 'Ay_prime', 'Sp', 'Sp_prime',
                    'vignet_up', 'vignet_down', 'light_up', 'light_down')
    for row in rows:
        values = []
        for key in numeric_keys:
            value = row.get(key)
            if key.startswith('light') and value is not None:
                value = value * 100.0       # доля → %
            values.append(value)
        n_field = (f"{row.get('n'):2d}" if row.get('n') is not None else '  ')
        line = '  ' + n_field + ''.join(
            _fwo(v, w, d) for v, (w, d) in zip(values, TABBEA_FIELD_SPECS))
        for key in ('limit_up', 'limit_down'):
            letter, surf = row.get(key) or (' ', 0)
            line += f' {letter} {surf:3d}'
        lines.append(line.rstrip())
    return '\n'.join(lines)


# ══ A4: реальное экранирование — зоны прохождения (TASK_SEIDEL) ═════════════
#
# Режим «ЭКРАНИРОВАНИЕ ПУЧКОВ — реальное» (ANALIZE.DOC:488–516, §4.4;
# MANUAL.DOC §2.2.4.3): поиск зон прохождения лучей на ВСЕХ поверхностях
# с учётом «загораживания» (центральный экран перед системой — правило
# запуска |ρ| ≥ k) и рабочих зон самих поверхностей (semi_diameter,
# EDGE-кромка трейсера). Базовый уровень (первая режущая поверхность) —
# compute_vignetting выше; здесь — честный проход всех поверхностей и
# эллипс экранирования на входном зрачке («полные габариты» TABBEA vs
# «габариты экранов» TABEAP, §14.4/§17.6).

#: Узлов меридионального веера зон прохождения по диаметру зрачка
#: (нечётное; симметричная сетка).
PASSAGE_GRID_N = 15

#: Допуск сопоставления точки пути с плоскостью (мм) — как
#: ``beam_heights._Z_MATCH_TOL``.
_PASSAGE_Z_TOL = 1e-6


def _path_surface_points(system: OpticalSystem, result):
    """Точки пути луча на поверхностях + точка изображения.

    Разбор пути — по схеме ``beam_heights._surface_heights``: точка 0 —
    старт; точка в плоскости диафрагмы (вставляется трейсером после
    прохождения поверхности стопа) пропускается; замыкающая точка за
    последней поверхностью в плоскости изображения — отдельно
    (``image_pt``). Возвращает список длины ``len(surfaces)``: элемент
    ``i`` — ``(x, y, z)`` на поверхности ``i`` или ``None`` (луч не
    дошёл). Срезанный кромкой (EDGE) луч свою точку на поверхности
    имеет — точку кромки: геометрически дошёл, апертуру не прошёл.
    """
    from optics_utils import compute_z_positions
    pts = list(getattr(result, 'path', None) or [])
    n = len(system.surfaces)
    out: List[Optional[Tuple[float, float, float]]] = [None] * n
    image_pt = None
    if not pts:
        return out, image_pt
    z_pos = compute_z_positions(system)
    stop_idx = getattr(system, 'stop_surface', -1)
    # stop_surface — 1-индексация (OPAL ND): плоскость = вершина
    # поверхности stop_surface−1 + stop_offset
    z_stop = (z_pos[stop_idx - 1] + getattr(system, 'stop_offset', 0.0)
              if 1 <= stop_idx <= len(z_pos) else None)
    consumed = 0
    for j, (x, y, z) in enumerate(pts):
        if j == 0:
            continue
        is_image = (j == len(pts) - 1 and consumed == n
                    and abs(z - z_pos[-1]) < _PASSAGE_Z_TOL)
        if is_image:
            image_pt = (x, y, z)
            continue
        if (z_stop is not None and abs(z - z_stop) < _PASSAGE_Z_TOL
                and consumed > stop_idx):
            continue                     # точка в плоскости диафрагмы
        if consumed < n:
            out[consumed] = (x, y, z)
            consumed += 1
    return out, image_pt


def find_passage_zones(system: OpticalSystem, field_y: float,
                       wl: Optional[float] = None,
                       grid_n: int = PASSAGE_GRID_N) -> Dict:
    """Зоны прохождения пучка по ВСЕМ поверхностям (ANALIZE.DOC §2.2.4.3).

    «Реальное экранирование» (§4.4): пучок поля ``field_y`` —
    меридиональный веер из ``grid_n`` лучей через диаметр входного
    зрачка (лучи :func:`aberrations._pupil_field_ray`, трассировка
    батчем ``ray_native``). На каждой поверхности, до которой лучи
    дошли, — интервал высот зоны (кольцо по MANUAL.DOC §2.2.4.3:
    «наружный + внутренний размеры, внутренний может быть 0»):

    * ``crossed`` — [min, max] высот всех лучей, дошедших до
      поверхности (включая срезанные кромкой — их точка лежит на
      самой поверхности);
    * ``passed`` — то же для лучей, дошедших до изображения;
    * ``outer``/``inner`` — наружный/внутренний размеры зоны
      прохождения: max|y| и min|y| по ``passed`` («захватывает ось» —
      inner 0); ``center`` — середина ``passed`` (эксцентричная зона —
      эллипс экранирования смещён, ≠ 0);
    * ``blocked_here`` — число лучей, срезанных именно этой
      поверхностью (EDGE/TIR), ``limit`` — код «Ограничения»
      (:data:`LIMIT_LETTERS`).

    Центральное экранирование ``obscuration_ratio`` — «загораживание»
    на входе: узлы |ρ| < k не запускаются (правило ``trace_fan``, как
    :func:`compute_light_distribution`) — «коэффициент экранирования»
    моделирует вторичное зеркало/отверстие перед системой.

    Args:
        system: Оптическая система (не изменяется).
        field_y: Угол поля (град) для INFINITE / высота (мм) для FINITE.
        wl: Длина волны (мкм); None → основная λ системы.
        grid_n: Узлов веера по диаметру зрачка (нечётное; ≥ 3).

    Returns:
        ``{'field_y', 'wl', 'grid_n', 'obscuration_ratio', 'n_rays',
        'n_blocked_launch', 'n_traced', 'n_passed', 'passage_fraction',
        'vignetted', 'surfaces': [dict по поверхностям с ключами
        'n', 'z', 'semi_diameter', 'crossed', 'passed', 'outer',
        'inner', 'center', 'blocked_here', 'limit']}`` — только
        поверхности, которых достиг хотя бы один луч.
    """
    if not system.surfaces:
        return {'field_y': field_y, 'wl': wl, 'grid_n': grid_n,
                'obscuration_ratio': 0.0, 'n_rays': 0,
                'n_blocked_launch': 0, 'n_traced': 0, 'n_passed': 0,
                'passage_fraction': None, 'vignetted': False,
                'surfaces': []}
    if wl is None:
        wl = get_primary_wl(system)
    radius = get_effective_aperture(system, default=10.0) / 2.0
    k = abs(float(getattr(system, 'obscuration_ratio', 0.0) or 0.0))
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)

    grid_n = max(3, int(grid_n))
    if grid_n % 2 == 0:
        grid_n += 1
    rhos = [2.0 * i / (grid_n - 1) - 1.0 for i in range(grid_n)]
    if k > 0.0:                          # граничные узлы ±k — край
        rhos += [k, -k]                  # загораживания (внутренний
    rhos = sorted(set(round(r, 12) for r in rhos))
    rays: List[Tuple[float, ...]] = []
    slots: List[Optional[int]] = []      # узел → луч (None — загораживание)
    for rho in rhos:
        if abs(rho) < k:
            slots.append(None)
            continue
        ray = _pupil_field_ray(system, 0.0, rho * radius, field_y,
                               z_start, z_pupil)
        rays.append((ray.x, ray.y, ray.z, ray.k, ray.l, ray.m))
        slots.append(len(rays) - 1)
    traced = ray_native.trace_batch(system, rays, wl)

    ns = len(system.surfaces)
    crossed: List[List[float]] = [[] for _ in range(ns)]
    passed: List[List[float]] = [[] for _ in range(ns)]
    blocked: List[int] = [0] * ns
    limits: List[Optional[Tuple[str, int]]] = [None] * ns
    n_passed = 0
    for slot in slots:
        if slot is None:
            continue
        res = traced[slot]
        points, image_pt = _path_surface_points(system, res)
        for i, pt in enumerate(points):
            if pt is not None:
                crossed[i].append(pt[1])
                if res.success:
                    passed[i].append(pt[1])
        if res.success:
            n_passed += 1
        elif res.error in ('EDGE', 'MISS', 'TIR'):
            letter, num = _limit_from_failure(system, res)
            idx = num - 1
            if 0 <= idx < ns:
                blocked[idx] += 1
                limits[idx] = (letter, num)

    n_traced = len(rays)
    surfaces = []
    from optics_utils import compute_z_positions
    z_pos = compute_z_positions(system)
    for i in range(ns):
        if not crossed[i]:
            continue
        pmin = min(passed[i]) if passed[i] else None
        pmax = max(passed[i]) if passed[i] else None
        if passed[i]:
            abs_hs = [abs(v) for v in passed[i]]
            inner = min(abs_hs)            # кольцо: min |y| (0 — лучи
            outer = max(abs_hs)            # через ось); max |y| — наружный
            center = (pmin + pmax) / 2.0
        else:
            inner = outer = center = 0.0
        surfaces.append({
            'n': i + 1,
            'z': z_pos[i],
            'semi_diameter': system.surfaces[i].semi_diameter,
            'crossed': [min(crossed[i]), max(crossed[i])],
            'passed': [pmin, pmax],
            'outer': outer,
            'inner': inner,
            'center': center,
            'blocked_here': blocked[i],
            'limit': limits[i],
        })
    return {
        'field_y': field_y, 'wl': wl, 'grid_n': grid_n,
        'obscuration_ratio': k,
        'n_rays': len(slots), 'n_blocked_launch': len(slots) - n_traced,
        'n_traced': n_traced, 'n_passed': n_passed,
        'passage_fraction': (n_passed / n_traced) if n_traced else None,
        'vignetted': n_passed < n_traced,
        'surfaces': surfaces,
    }


def real_obscuration(system: OpticalSystem, field_y: float,
                     wl: Optional[float] = None) -> Dict:
    """«Габариты экранов»: реальное экранирование пучка эллипсом (TABEAP).

    Зона прохождения пучка на входном зрачке ищется бисекцией
    (:data:`VIGNETTING_BISECT_STEPS`) по 4 полуосям — ±y (меридиональные)
    и ±x (сагиттальные): ``rho_hi`` — максимальная зрачковая координата
    проходящего луча (наружная граница зоны), ``rho_lo`` — минимальная
    (внутренняя: центральный экран; правило запуска |ρ| ≥ k задаёт
    нижнюю границу моделью «загораживания»). Из границ собирается
    эллипс экранирования на входном зрачке (ANALIZE.DOC:488–516):

    * ``full_diameter_y/x`` — «полные габариты» (TABBEA): удвоенные
      наружные полуоси эллипса пучка, мм;
    * ``screen_diameter_y/x`` — «габариты экранов» (TABEAP):
      удвоенные внутренние полуоси эллипса экранирования (центральный
      экран: вторичное зеркало, отверстие, загораживание), мм;
    * ``obscuration_fraction`` — относительное экранирование по
      площади (отношение произведений полуосей, π сокращается);
    * ``screen_shift`` — смещение центра эллипса экранирования
      относительно центра зрачка, доли радиуса зрачка;
    * ``minimal_obscuration`` — «коэффициент экранирования»
      (ANALIZE.DOC:508–516): наименьшее относительное центральное
      экранирование осевого пучка — max по поверхностям inner/outer
      зон прохождения осевого пучка (:func:`find_passage_zones`, поле
      0);
    * ``cutters`` — «экранирующие поверхности»: коды «Ограничения»
      срезавших кромки (у невыигьетированного пучка — пусто).

    Args:
        system: Оптическая система (не изменяется).
        field_y: Угол поля (град) / высота предмета (мм).
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        Словарь с ключами ``field_y, wl, outer_rho_hi_up/down/left/
        right, outer_rho_lo_*, inner/outer_semi_y/x, inner/outer_
        shift_y, full_diameter_y/x, screen_diameter_y/x,
        obscuration_fraction, screen_shift, minimal_obscuration,
        cutters, passage_fraction`` (ρ — доли радиуса зрачка, полуоси —
        мм; полностью завиньетированная сторона — 0).
    """
    empty = {
        'field_y': field_y, 'wl': wl,
        'outer_rho_hi_up': 0.0, 'outer_rho_hi_down': 0.0,
        'outer_rho_hi_left': 0.0, 'outer_rho_hi_right': 0.0,
        'outer_rho_lo_up': 0.0, 'outer_rho_lo_down': 0.0,
        'outer_rho_lo_left': 0.0, 'outer_rho_lo_right': 0.0,
        'outer_semi_y': 0.0, 'outer_semi_x': 0.0,
        'outer_shift_y': 0.0,
        'inner_semi_y': 0.0, 'inner_semi_x': 0.0,
        'inner_shift_y': 0.0,
        'full_diameter_y': 0.0, 'full_diameter_x': 0.0,
        'screen_diameter_y': 0.0, 'screen_diameter_x': 0.0,
        'obscuration_fraction': 0.0, 'screen_shift': 0.0,
        'minimal_obscuration': 0.0, 'cutters': [],
        'passage_fraction': None,
    }
    if not system.surfaces:
        return dict(empty)
    if wl is None:
        wl = get_primary_wl(system)
    radius = get_effective_aperture(system, default=10.0) / 2.0
    k = abs(float(getattr(system, 'obscuration_ratio', 0.0) or 0.0))
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)

    def trace(t: float, dx: float, dy: float):
        """Луч на зрачковой координате t·(dx,dy)·radius (доли радиуса)."""
        ray = _pupil_field_ray(system, dx * t * radius, dy * t * radius,
                               field_y, z_start, z_pupil)
        return ray_native.trace_batch(
            system, [(ray.x, ray.y, ray.z, ray.k, ray.l, ray.m)], wl)[0]

    def bisect(lo_ok: float, hi_fail: float, dx: float, dy: float,
               want: str):
        """Граница зоны: ``'hi'`` — max проходящего, ``'lo'`` — min."""
        for _ in range(VIGNETTING_BISECT_STEPS):
            mid = (lo_ok + hi_fail) / 2.0
            ok = trace(mid, dx, dy).success
            if (ok and want == 'hi') or (not ok and want == 'lo'):
                lo_ok = mid
            else:
                hi_fail = mid
        return (lo_ok + hi_fail) / 2.0

    out = dict(empty)
    cutters: List[Tuple[str, int]] = []
    for axis, (dx, dy) in (('up', (0.0, 1.0)), ('down', (0.0, -1.0)),
                           ('left', (-1.0, 0.0)), ('right', (1.0, 0.0))):
        edge = trace(1.0, dx, dy)
        if edge.success:
            rho_hi = 1.0                    # край не срезан
        else:
            anchor = None                   # ищем проходящий луч стороны
            for i in range(1, 16):
                t = 1.0 - i / 16.0
                if t <= k:
                    break
                if trace(t, dx, dy).success:
                    anchor = t
                    break
            if anchor is None:
                continue                    # сторона полностью срезана
            rho_hi = bisect(anchor, 1.0, dx, dy, 'hi')
            cutters.append(_limit_from_failure(system, edge))
        # внутренняя граница: правило запуска |ρ| ≥ k — пол модели
        if k > 0.0:
            if rho_hi >= k and trace(k, dx, dy).success:
                rho_lo = k
            elif rho_hi > 0.0:
                rho_lo = bisect(k, rho_hi, dx, dy, 'lo')
            else:
                rho_lo = 0.0
        else:
            if trace(0.0, dx, dy).success:
                rho_lo = 0.0
            else:
                rho_lo = bisect(0.0, rho_hi if rho_hi > 0 else 1.0,
                                dx, dy, 'lo')
        out[f'outer_rho_hi_{axis}'] = rho_hi
        out[f'outer_rho_lo_{axis}'] = min(rho_lo, rho_hi)

    hi_y_up = out['outer_rho_hi_up']
    hi_y_dn = out['outer_rho_hi_down']
    hi_x_lf = out['outer_rho_hi_left']
    hi_x_rt = out['outer_rho_hi_right']
    lo_y_up = out['outer_rho_lo_up']
    lo_y_dn = out['outer_rho_lo_down']
    lo_x_lf = out['outer_rho_lo_left']
    lo_x_rt = out['outer_rho_lo_right']
    out['outer_semi_y'] = (hi_y_up + hi_y_dn) / 2.0 * radius
    out['outer_shift_y'] = (hi_y_up - hi_y_dn) / 2.0 * radius
    out['outer_semi_x'] = (hi_x_lf + hi_x_rt) / 2.0 * radius
    out['inner_semi_y'] = (lo_y_up + lo_y_dn) / 2.0 * radius
    out['inner_shift_y'] = (lo_y_up - lo_y_dn) / 2.0 * radius
    out['inner_semi_x'] = (lo_x_lf + lo_x_rt) / 2.0 * radius
    out['full_diameter_y'] = 2.0 * out['outer_semi_y']
    out['full_diameter_x'] = 2.0 * out['outer_semi_x']
    out['screen_diameter_y'] = 2.0 * out['inner_semi_y']
    out['screen_diameter_x'] = 2.0 * out['inner_semi_x']
    denom = out['outer_semi_y'] * out['outer_semi_x']
    out['obscuration_fraction'] = (
        out['inner_semi_y'] * out['inner_semi_x'] / denom
        if denom > 1e-12 else 0.0)
    out['screen_shift'] = (out['inner_shift_y'] / out['outer_semi_y']
                           if out['outer_semi_y'] > 1e-12 else 0.0)
    seen = []
    for pair in cutters:
        if pair not in seen:
            seen.append(pair)
    out['cutters'] = seen

    # «Коэффициент экранирования»: осевой пучок — max inner/outer по
    # поверхностям с реальным габаритом пучка (у поверхностей вблизи
    # фокуса outer — пятно, а не габарит; порог 5 % радиуса зрачка).
    axial = find_passage_zones(system, 0.0, wl=wl)
    out['passage_fraction'] = axial.get('passage_fraction')
    ratios = [sf['inner'] / sf['outer']
              for sf in axial.get('surfaces', [])
              if sf['outer'] >= 0.05 * radius]
    out['minimal_obscuration'] = max(ratios) if ratios else 0.0
    return out
