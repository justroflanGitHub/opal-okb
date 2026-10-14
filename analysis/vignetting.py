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
