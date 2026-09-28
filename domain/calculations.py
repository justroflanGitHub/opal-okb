"""
OPAL-OKB — Domain Calculations

Paraxial ray tracing, Seidel aberrations, refractive index,
beam geometry, and vignetting.

Extracted from optics_engine.py during package restructuring.
"""
import math
from typing import List, Optional, Tuple

from domain.models import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    ObjectType, ApertureType, SurfaceType,
    GlassCatalogEntry, _std_wavelengths,
)
from glass_catalog import compute_refractive_index
from domain.aperture import aperture_to_epd
from optics_utils import (
    compute_z_positions, get_primary_wl, get_effective_aperture,
    EPSILON, TINY, UNLIMITED_SD,
)


def apply_vignetting(system: OpticalSystem, field_y: float, ray_y: float,
                     ray_x: float = 0.0, sharp_edge: bool = True) -> bool:
    """
    Проверить виньетирование луча.
    Луч виньетируется если на любой поверхности полудиаметр луча
    превышает semi_diameter этой поверхности (с учётом кромки —
    см. :func:`effective_semi_diameter`).

    Возвращает True если луч виньетирован (отсекается),
    False если луч проходит.
    """
    if not system.surfaces:
        return False
    
    # Z-позиции
    z_pos = compute_z_positions(system)
    
    wl = get_primary_wl(system)
    
    # Начальные параметры луча
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        y = ray_y
        z = -50.0
        k = 0.0
        l = math.sin(angle)
        m = math.cos(angle)
    else:
        y = field_y
        z = -system.surfaces[0].thickness if system.surfaces else -50
        k = 0.0
        l = (ray_y - field_y) / abs(z) if abs(z) > EPSILON else 0.0
        m = 1.0
        norm = math.sqrt(k**2 + l**2 + m**2)
        k /= norm; l /= norm; m /= norm
    
    x = ray_x
    
    # Трассируем через поверхности, проверяя полудиаметр
    for i, s in enumerate(system.surfaces):
        R = s.radius if abs(s.radius) > EPSILON else 0.0
        z_surf = z_pos[i]
        
        if abs(m) < TINY:
            return True
        
        if R == 0:
            t = (z_surf - z) / m
        else:
            cz = z_surf + R
            dz_val = z - cz
            a = k**2 + l**2 + m**2
            b = 2 * (k * x + l * y + m * dz_val)
            c_val = x**2 + y**2 + dz_val**2 - R**2
            disc = b**2 - 4*a*c_val
            if disc < 0:
                return True
            sqrt_disc = math.sqrt(disc)
            t1 = (-b - sqrt_disc) / (2 * a)
            t2 = (-b + sqrt_disc) / (2 * a)
            t = t1 if t1 > EPSILON else t2
            if t < EPSILON:
                return True
        
        y_new = y + t * l
        x_new = x + t * k
        z_new = z + t * m
        
        # Проверка полудиаметра
        sd = effective_semi_diameter(
            s.semi_diameter if s.semi_diameter > 0 else UNLIMITED_SD,
            sharp_edge)
        r_hit = math.sqrt(x_new**2 + y_new**2)
        if r_hit > sd:
            return True
        
        # Приближённое преломление для продолжения трассировки
        if R != 0:
            n_before = 1.0 if i == 0 else refractive_index(system.surfaces[i-1].glass, wl)
            n_after = refractive_index(s.glass, wl)
            phi = (n_after - n_before) / R
            # Обновляем направление (параксиальное приближение)
            l_new = (l * n_before - y_new * phi) / n_after
            k_new = (k * n_before - x_new * phi) / n_after
            norm = math.sqrt(k_new**2 + l_new**2 + m**2)
            if norm > TINY:
                k, l = k_new / norm, l_new / norm
        
        y, x, z = y_new, x_new, z_new
    
    return False


def refractive_index(glass_name: str, wavelength_um: float, catalog: dict = None, n_override: dict = None) -> float:
    """
    Вычислить показатель преломления для заданной длины волны.
    Если n_override содержит значение для wavelength_um — использовать его.
    """
    if n_override:
        for wl_key, n_val in n_override.items():
            if abs(wl_key - wavelength_um) < 0.002:
                return n_val
    return compute_refractive_index(glass_name, wavelength_um)


def paraxial_trace(sys: OpticalSystem, catalog: dict = None,
                   wl: float = None) -> dict:
    """
    Параксиальный расчёт оптической системы.
    Возвращает полный набор кардинальных отрезков и характеристик.

    Args:
        sys: Оптическая система.
        catalog: Каталог стёкол (None — встроенный).
        wl: Рабочая длина волны (мкм) для показателей преломления;
            ``None`` — основная λ системы. Позволяет сосчитать
            характеристики для любой λ без копии системы (п. 13 GAP v2).

    Note: sys.stop_type ('d', 'z', 'p') определяет тип диафрагмы, но
    текущий расчёт работает только с типом 'd' (апертурная диафрагма).
    Все существующие системы из LBO используют тип 'd'.

    Note: Surfaces with non-zero tilt/decenter are treated as
    ordinary surfaces in the paraxial approximation.  Full tilt
    support in paraxial optics requires ABCD matrix rotation which
    is not implemented here.  The paraxial results are therefore
    approximate for systems with tilted/decentered elements
    (точная трассировка таких поверхностей — analysis/ray_tracing.py
    через локальную СК domain/spatial.py, п. 17).
    """
    if not sys.surfaces:
        return {}

    results = {
        'focal_length': 0.0,         # Фокусное расстояние (мм)
        'back_focal_distance': 0.0,   # Задний фокальный отрезок
        'front_focal_distance': 0.0,
        'effective_focal_length': 0.0,
        'entrance_pupil': 0.0,
        'exit_pupil': 0.0,
        'pupil_location': 0.0,
        'magnification': 0.0,
        'surface_data': [],
        # Новые кардинальные отрезки:
        'sF': 0.0,               # расстояние от первой поверхности до переднего фокуса
        'sF_prime': 0.0,         # расстояние от последней поверхности до заднего фокуса
        'sH': 0.0,               # расстояние от первой поверхности до передней главной плоскости
        'sH_prime': 0.0,         # расстояние от последней поверхности до задней главной плоскости
        'L': 0.0,                # длина системы (сумма всех d)
        'sP': 0.0,               # положение входного зрачка от первой поверхности
        'sP_prime': 0.0,         # положение выходного зрачка от последней поверхности
        'V': 0.0,                # обобщённое увеличение
        'f_number': 0.0,         # f'/#
        'entrance_pupil_diameter': 0.0,  # D входного зрачка
    }

    wl_used = float(wl) if wl is not None else get_primary_wl(sys)
    results['wl'] = wl_used
    ns = len(sys.surfaces)

    # Показатели преломления для каждой среды (ns+1 сред)
    # Для зеркал: после отражения n меняет знак
    n_medium = [1.0]  # воздух перед системой
    for i in range(ns):
        s = sys.surfaces[i]
        if s.is_reflective:
            # Зеркало: после отражения n меняет знак
            n_medium.append(-n_medium[-1])
        else:
            n_medium.append(refractive_index(s.glass, wl_used, catalog, getattr(s, 'n_override', None)))

    # ===== Длина системы =====
    L = sum(s.thickness for s in sys.surfaces)
    results['L'] = L

    # ===== Параксиальный краевой луч 1: y=1, nu=0 (параллельный) =====
    y1 = [0.0] * (ns + 1)
    nu1 = [0.0] * (ns + 1)
    y1[0] = 1.0
    nu1[0] = 0.0

    for i in range(ns):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else 1e15
        n_b = n_medium[i]
        n_a = n_medium[i + 1]

        if s.is_reflective:
            # Зеркало: nu' = nu + 2*y*n/R (отражение)
            phi_i = -2.0 * n_b / R
        else:
            phi_i = (n_a - n_b) / R
        nu1[i] = nu1[i] - y1[i] * phi_i

        if i < ns - 1:
            d = s.thickness
            n_cur = n_medium[i + 1]
            y1[i + 1] = y1[i] + nu1[i] * d / n_cur
            nu1[i + 1] = nu1[i]
        else:
            d = s.thickness
            n_cur = n_medium[ns]
            y1[ns] = y1[i] + nu1[i] * d / n_cur

    # ===== Параксиальный луч 2: y=0, nu=1 (через ось на первой поверхности) =====
    y2 = [0.0] * (ns + 1)
    nu2 = [0.0] * (ns + 1)
    y2[0] = 0.0
    nu2[0] = 1.0

    for i in range(ns):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else 1e15
        n_b = n_medium[i]
        n_a = n_medium[i + 1]

        if s.is_reflective:
            phi_i = -2.0 * n_b / R
        else:
            phi_i = (n_a - n_b) / R
        nu2[i] = nu2[i] - y2[i] * phi_i

        if i < ns - 1:
            d = s.thickness
            n_cur = n_medium[i + 1]
            y2[i + 1] = y2[i] + nu2[i] * d / n_cur
            nu2[i + 1] = nu2[i]
        else:
            d = s.thickness
            n_cur = n_medium[ns]
            y2[ns] = y2[i] + nu2[i] * d / n_cur

    # ===== ABCD матрица =====
    # A = height of paraxial ray at last surface vertex (NOT after last thickness)
    # C = nu1[ns-1], D = nu2[ns-1]
    A_mat = y1[ns - 1] if ns > 0 else 0.0
    B_mat = y2[ns - 1] if ns > 0 else 0.0
    C_mat = nu1[ns - 1] if ns > 0 else 0.0
    D_mat = nu2[ns - 1] if ns > 0 else 0.0

    nu_last = C_mat

    if abs(nu_last) > TINY:
        efl = -1.0 / nu_last
        results['focal_length'] = efl
        results['effective_focal_length'] = efl

        # sF' = BFD = -A/C
        sF_prime = -A_mat / C_mat
        results['back_focal_distance'] = sF_prime
        results['sF_prime'] = sF_prime

        # sH' = sF' - f' = (1-A)/C
        sH_prime = (1.0 - A_mat) / C_mat
        results['sH_prime'] = sH_prime

        # sF = D/C (отрицательный для собирающей системы)
        sF = D_mat / C_mat
        results['sF'] = sF
        results['front_focal_distance'] = -sF  # FFD положительный

        # sH = sF + f' = (D-1)/C
        sH = (D_mat - 1.0) / C_mat
        results['sH'] = sH

    # ===== Положение зрачков (sP, sP') =====
    stop_idx = max(0, min(sys.stop_surface - 1, ns - 1))  # 0-based
    stop_off = getattr(sys, 'stop_offset', 0.0)  # смещение диафрагмы от stop_surface (мм)

    # Обратная трассировка от диафрагмы к первой поверхности
    # Диафрагма находится на z = z(stop_surface) + stop_offset
    # yb на диафрагме = 0, nub = 1
    yb = [0.0] * (ns + 1)
    nub = [0.0] * (ns + 1)
    yb[stop_idx] = 0.0
    nub[stop_idx] = 1.0

    # Сначала трассируем от stop_idx назад, учитывая смещение
    # Если stop_offset > 0, диафрагма между stop_idx и stop_idx+1
    # Сместим начальную точку: yb[stop_idx] уже = 0
    # Но при переносе назад к stop_idx нужно учесть смещение
    # yb_at_stop_surface = 0 - nub * stop_offset / n_medium[stop_idx]
    if stop_off > 0 and stop_idx < ns:
        n_after_stop = n_medium[stop_idx + 1]
        yb[stop_idx] = -nub[stop_idx] * stop_off / n_after_stop

    for i in range(stop_idx - 1, -1, -1):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else 1e15
        n1 = n_medium[i]
        n2 = n_medium[i + 1]
        d = s.thickness
        yb[i] = yb[i + 1] - nub[i + 1] * d / n_medium[i + 1]
        if R != 1e15:
            nub[i] = nub[i + 1] + yb[i] * (n2 - n1) / R
        else:
            nub[i] = nub[i + 1]

    # Прямая трассировка от stop_surface к последней поверхности
    # Сбросим yb на стоп-поверхности обратно (для прямого хода)
    yb[stop_idx] = 0.0
    nub[stop_idx] = 1.0
    if stop_off > 0 and stop_idx < ns:
        n_after_stop = n_medium[stop_idx + 1]
        # Перенос от диафрагмы вперёд к следующей поверхности
        d_to_next = sys.surfaces[stop_idx].thickness - stop_off
        if stop_idx + 1 <= ns:
            yb[stop_idx + 1] = nub[stop_idx] * stop_off / n_after_stop
            nub_next = nub[stop_idx]
    for i in range(stop_idx, ns):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else 1e15
        n1 = n_medium[i]
        n2 = n_medium[i + 1]
        if R != 1e15:
            nub[i] = nub[i] - yb[i] * (n2 - n1) / R
        if i < ns - 1:
            d = s.thickness
            yb[i + 1] = yb[i] + nub[i] * d / n_medium[i + 1]
            nub[i + 1] = nub[i]
        else:
            d = s.thickness
            yb[ns] = yb[i] + nub[i] * d / n_medium[ns]

    # Входной зрачок: расстояние от первой поверхности
    sP = 0.0
    if abs(nub[0]) > TINY:
        sP = -yb[0] / nub[0]
    results['sP'] = sP
    results['entrance_pupil'] = sP

    # Выходной зрачок: расстояние от последней поверхности
    sP_prime = 0.0
    nu_exit = nub[ns - 1] if ns > 0 else 0.0
    if abs(nu_exit) > TINY:
        sP_prime = -yb[ns] / nu_exit
    results['sP_prime'] = sP_prime
    results['exit_pupil'] = sP_prime
    results['pupil_location'] = sP_prime

    # ===== Увеличения изображения диафрагмы (пересчёт апертур, п. 12) =====
    # Трассирован луч через центр диафрагмы: y = 0 на диафрагме,
    # nu = 1 (приведённый угол). По инварианту Лагранжа для сопряжённых
    # плоскостей «диафрагма → зрачок» увеличение = 1/nu этого луча
    # в плоскости зрачка.
    nu_exit = nub[ns - 1] if ns > 0 else 0.0
    m_entrance = 1.0 / nub[0] if abs(nub[0]) > TINY else None
    m_exit = 1.0 / nu_exit if abs(nu_exit) > TINY else None
    results['entrance_pupil_magnification'] = m_entrance
    results['exit_pupil_magnification'] = m_exit
    if m_entrance and m_exit and abs(m_entrance) > TINY:
        results['pupil_magnification'] = m_exit / m_entrance

    # ===== f/# и входной зрачок (п. 12 GAP v2) =====
    # Любой способ задания апертуры (углы, NA', высота на диафрагме,
    # D, F/#, NA) приводится к диаметру входного зрачка — после
    # положения зрачков, на которые опираются пересчёты.
    efl = results.get('focal_length', 0.0)
    if abs(efl) > TINY:
        epd = aperture_to_epd(sys, sys.aperture_value, sys.aperture_type,
                              parax=results)
        if not epd or epd <= TINY:
            epd = abs(efl) / 4.0
        results['entrance_pupil_diameter'] = epd
        results['f_number'] = abs(efl) / epd if epd > 0 else 0.0

    # ===== Обобщённое увеличение V =====
    if sys.object_type == ObjectType.FINITE and abs(sys.object_height) > EPSILON:
        # Для конечного предмета: V = f' / (s + f') where s = -obj_dist
        if abs(nu_last) > TINY:
            obj_dist = sys.surfaces[0].thickness if sys.surfaces else 0.0
            if abs(obj_dist) > EPSILON:
                efl = results.get('focal_length', 0)
                s_val = -obj_dist
                if abs(s_val + efl) > EPSILON:
                    results['V'] = efl / (s_val + efl)
                    results['magnification'] = results['V']
    else:
        # Для бесконечного предмета: V = -f'
        efl = results.get('focal_length', 0)
        results['V'] = -efl
        results['magnification'] = -efl

    return results


# Строки таблицы «параксиальные характеристики по λ» (п. 13 GAP v2):
# (подпись, ключ результата paraxial_trace, формат вывода).
# Единственный источник набора строк — используется GUI и тестами.
PARAXIAL_WL_ROWS = (
    ("f' (мм)", 'focal_length', '.4f'),
    ("sF (мм)", 'sF', '.4f'),
    ("sF' (мм)", 'sF_prime', '.4f'),
    ("sH (мм)", 'sH', '.4f'),
    ("sH' (мм)", 'sH_prime', '.4f'),
    ("L (мм)", 'L', '.2f'),
    ("sP (мм)", 'sP', '.4f'),
    ("sP' (мм)", 'sP_prime', '.4f'),
    ("V", 'V', '.5f'),
    ("f/#", 'f_number', '.2f'),
    ("D вх.зр. (мм)", 'entrance_pupil_diameter', '.2f'),
)

# Ключи PARAXIAL_WL_ROWS с положениями зрачков (п. 16 GAP v2): эти
# строки переключаются в диоптрии (D = 1000/мм, OPAL-PC Л1.4.4),
# подпись «(мм)» заменяется на выбранную единицу.
PUPIL_POSITION_KEYS = ('sP', 'sP_prime')


def paraxial_trace_all_wavelengths(sys: OpticalSystem,
                                   catalog: dict = None) -> List[dict]:
    """
    Параксиальный расчёт для каждой рабочей λ системы (п. 13 GAP v2).

    Прогоняет :func:`paraxial_trace` для каждой λ из ``sys.wavelengths``
    с показателями преломления этой λ; первая λ — основная.
    Если λ не заданы — один расчёт для основной λ.

    Args:
        sys: Оптическая система (не изменяется).
        catalog: Каталог стёкол (None — встроенный).

    Returns:
        Список результатов paraxial_trace (по одному на λ); каждый
        результат содержит ключ ``'wl'`` с использованной λ (мкм).
    """
    wls = [w.value for w in sys.wavelengths] if sys.wavelengths else []
    if not wls:
        wls = [get_primary_wl(sys)]
    return [paraxial_trace(sys, catalog, wl) for wl in wls]


# --------------------------------------------------------------------------- #
# Режимы расчёта габаритов пучков (п. 15 GAP v2)
# --------------------------------------------------------------------------- #

BEAM_SEMI_MODES = (
    ('given', 'Заданные'),   # по заданной апертуре системы
    ('real', 'Реальные'),    # по фактическим полудиаметрам поверхностей
)

#: Скругление кромки — доля полудиаметра, теряемая при флаге
#: «острый край» = выкл (кромка линзы скруглена, световой проём меньше).
EDGE_ROUND_FRACTION = 0.05

#: Шагов бинарного поиска (виньетирование по полю, реальный габарит пучка).
VIGNETTING_BISECT_STEPS = 20


def effective_semi_diameter(semi_diameter: float, sharp_edge: bool = True) -> float:
    """Действующий полудиаметр поверхности с учётом кромки.

    ``sharp_edge=True`` — виньетирование по острому краю (весь
    полудиаметр); ``False`` — кромка скруглена: световой проём меньше
    на :data:`EDGE_ROUND_FRACTION` от полудиаметра. Нулевой/
    отрицательный полудиаметр (не задан) проходит без изменений.

    Единственное место, где применяется «острый край» — используют и
    :func:`apply_vignetting`, и расчёт габаритов пучков.
    """
    if semi_diameter <= 0:
        return semi_diameter
    if sharp_edge:
        return semi_diameter
    return semi_diameter * (1.0 - EDGE_ROUND_FRACTION)


def _trace_beam_ray(system: OpticalSystem, z_pos: list, wl: float,
                    y_start: float, x_start: float, field_y: float,
                    sharp_edge: bool = True) -> Tuple[float, float, bool]:
    """Трассировка габаритного луча через систему.

    Возвращает ``(y_img, x_img, success)``; ``success=False`` — луч
    виньетирован или не пересёк поверхность. Используется расчётом
    габаритов пучков (:func:`compute_beam_geometry`,
    :func:`real_beam_aperture`).
    """
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        ray_y = y_start
        ray_x = x_start
        k = 0.0
        l = math.sin(angle)
        m = math.cos(angle)
    else:
        obj_z = -system.surfaces[0].thickness if system.surfaces else -50
        d = abs(obj_z)
        ray_y = y_start
        ray_x = x_start
        k = x_start / d if d > 0 else 0.0
        l = (y_start - field_y) / d if d > 0 else 0.0
        m = 1.0
        norm = math.sqrt(k**2 + l**2 + m**2)
        if norm > TINY:
            k /= norm; l /= norm; m /= norm

    success = True
    z = -50.0 if system.object_type == ObjectType.INFINITE else (z_pos[0] - abs(system.surfaces[0].thickness) if system.surfaces else -50)
    y = ray_y
    x = ray_x

    for i, s in enumerate(system.surfaces):
        R = s.radius if abs(s.radius) > EPSILON else 0.0
        z_surf = z_pos[i]

        if abs(m) < TINY:
            success = False
            break

        if R == 0:
            t = (z_surf - z) / m
        else:
            cz = z_surf + R
            dz_val = z - cz
            a_coef = k**2 + l**2 + m**2
            b_coef = 2 * (k * x + l * y + m * dz_val)
            c_val = x**2 + y**2 + dz_val**2 - R**2
            disc = b_coef**2 - 4*a_coef*c_val
            if disc < 0:
                success = False
                break
            sqrt_disc = math.sqrt(disc)
            t1 = (-b_coef - sqrt_disc) / (2 * a_coef)
            t2 = (-b_coef + sqrt_disc) / (2 * a_coef)
            t = t1 if t1 > EPSILON else t2
            if t < EPSILON:
                success = False
                break

        y_new = y + t * l
        x_new = x + t * k
        z_new = z + t * m

        # Проверка виньетирования (с учётом кромки)
        sd = effective_semi_diameter(
            s.semi_diameter if s.semi_diameter > 0 else UNLIMITED_SD,
            sharp_edge)
        r_hit = math.sqrt(x_new**2 + y_new**2)
        if r_hit > sd:
            success = False
            break

        # Преломление
        if R != 0:
            n_before = 1.0 if i == 0 else refractive_index(system.surfaces[i-1].glass, wl, None, getattr(system.surfaces[i-1], 'n_override', None))
            n_after = refractive_index(s.glass, wl, None, getattr(s, 'n_override', None))
            phi = (n_after - n_before) / R
            l_new = (l * n_before - y_new * phi) / n_after
            k_new = (k * n_before - x_new * phi) / n_after
            norm = math.sqrt(k_new**2 + l_new**2 + m**2)
            if norm > TINY:
                k, l = k_new / norm, l_new / norm

        y, x, z = y_new, x_new, z_new

    return y, x, success


def real_beam_aperture(system: OpticalSystem, wl: float = None,
                       sharp_edge: bool = True) -> Optional[float]:
    """Диаметр наибольшего осевого пучка, проходящего по фактическим
    полудиаметрам поверхностей (режим габаритов «Реальные»).

    Бинарным поиском (по трассировке :func:`_trace_beam_ray`) ищется
    максимальная полувысота луча на входе, при которой осевой пучок
    (оба крайних меридиональных луча) нигде не виньетируется. Верхняя
    граница поиска — наименьший действующий полудиаметр поверхностей.

    Возвращает ``None``, если ни у одной поверхности полудиаметр не
    задан (режим вырождается — считать «по фактическому» не по чему);
    вызывающий код откатывается на заданную апертуру системы.
    """
    if not system.surfaces:
        return None
    sds = [s.semi_diameter for s in system.surfaces if s.semi_diameter > 0]
    if not sds:
        return None

    if wl is None:
        wl = get_primary_wl(system)
    z_pos = compute_z_positions(system)
    cap = min(effective_semi_diameter(sd, sharp_edge) for sd in sds)

    def passes(half_height: float) -> bool:
        upper = _trace_beam_ray(system, z_pos, wl, half_height, 0.0, 0.0,
                                sharp_edge)
        lower = _trace_beam_ray(system, z_pos, wl, -half_height, 0.0, 0.0,
                                sharp_edge)
        return upper[2] and lower[2]

    lo, hi = 0.0, cap
    for _ in range(VIGNETTING_BISECT_STEPS):
        mid = (lo + hi) / 2.0
        if passes(mid):
            lo = mid
        else:
            hi = mid
    return 2.0 * lo


def compute_beam_geometry(system: OpticalSystem, wl: float = None,
                          semi_mode: str = 'given',
                          sharp_edge: bool = True) -> list:
    """
    Вычислить габариты пучков для всех полей.

    Args:
        system: Оптическая система.
        wl: Длина волны (None — основная).
        semi_mode: Режим габаритов — ``'given'`` (по заданной апертуре
            системы) или ``'real'`` (по фактическим полудиаметрам
            поверхностей, см. :func:`real_beam_aperture`); ключи —
            :data:`BEAM_SEMI_MODES`.
        sharp_edge: Виньетирование по острому краю (без скругления
            кромки), см. :func:`effective_semi_diameter`.

    Возвращает для каждого field_point:
    {
        'field_y': float,
        'Ax': float,              # передняя апертура X (сагиттальная)
        'Ay': float,              # передняя апертура Y (меридиональная)
        'Ax_prime': float,        # задняя апертура X
        'Ay_prime': float,        # задняя апертура Y
        'vignetting_upper': float,   # коэффициент верхнего виньетирования
        'vignetting_lower': float,   # коэффициент нижнего виньетирования
        'relative_illumination': float,  # светораспределение (доля от осевого)
    }
    """
    mode_keys = [key for key, _ in BEAM_SEMI_MODES]
    if semi_mode not in mode_keys:
        raise ValueError(f"неизвестный режим габаритов: {semi_mode!r} "
                         f"(допустимо {mode_keys})")

    if wl is None:
        wl = get_primary_wl(system)

    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    efl = parax.get('focal_length', 0)
    fno = parax.get('f_number', 0)
    if semi_mode == 'real':
        real_d = real_beam_aperture(system, wl=wl, sharp_edge=sharp_edge)
        if real_d is not None and real_d > EPSILON:
            # Пучок ограничен фактическими полудиаметрами поверхностей,
            # а не заданной апертурой; f/# — от этого же пучка.
            aperture = real_d
            if abs(efl) > EPSILON:
                fno = efl / aperture

    z_pos = compute_z_positions(system)

    results = []

    for fp in (system.field_points if system.field_points else [FieldPoint(0.0)]):
        field_y = fp.y

        # Трассируем меридиональный веер для определения габаритов
        # Верхний луч (pupil_y = +1), нижний луч (pupil_y = -1), сагиттальный (pupil_x = +1)

        upper_y_start = aperture / 2.0
        lower_y_start = -aperture / 2.0
        sag_x_start = aperture / 2.0

        # Верхний луч
        uy, ux, upper_ok = _trace_beam_ray(system, z_pos, wl, upper_y_start, 0.0, field_y, sharp_edge)
        # Нижний луч
        ly, lx, lower_ok = _trace_beam_ray(system, z_pos, wl, lower_y_start, 0.0, field_y, sharp_edge)
        # Сагиттальный луч
        sy, sx, sag_ok = _trace_beam_ray(system, z_pos, wl, 0.0, sag_x_start, field_y, sharp_edge)
        # Главный луч
        cy, cx, chief_ok = _trace_beam_ray(system, z_pos, wl, 0.0, 0.0, field_y, sharp_edge)

        # Передние апертуры — полуширина пучка на входе
        Ax = aperture / 2.0  # сагиттальная
        Ay = aperture / 2.0  # меридиональная

        # Задние апертуры — через f/# и поле
        Ax_prime = 0.0
        Ay_prime = 0.0
        if abs(efl) > EPSILON and fno > 0:
            # Задняя апертура осевого пучка
            Ax_prime = efl / (2.0 * fno) if fno > 0 else 0
            Ay_prime = Ax_prime

        # Виньетирование: доля пучка, прошедшего без отсечения
        # Верхнее: ищем максимальный pupil_y при котором верхний луч ещё проходит
        vign_upper = 1.0
        vign_lower = 1.0
        if field_y != 0:
            # Ищем виньетирование бинарным поиском
            for sign, label in [(1.0, 'upper'), (-1.0, 'lower')]:
                lo, hi = 0.0, 1.0
                best = 0.0
                for _ in range(VIGNETTING_BISECT_STEPS):
                    mid = (lo + hi) / 2.0
                    y_test = sign * mid * aperture / 2.0
                    _, _, ok = _trace_beam_ray(system, z_pos, wl, y_test, 0.0, field_y, sharp_edge)
                    if ok:
                        best = mid
                        lo = mid
                    else:
                        hi = mid
                if sign > 0:
                    vign_upper = best
                else:
                    vign_lower = best

        # Светораспределение: cos⁴(θ) приближение
        rel_illum = 1.0
        if field_y != 0 and system.object_type == ObjectType.INFINITE:
            angle = math.radians(field_y)
            rel_illum = math.cos(angle) ** 4
            # Корректировка на виньетирование
            rel_illum *= (vign_upper + vign_lower) / 2.0

        results.append({
            'field_y': field_y,
            'Ax': Ax,
            'Ay': Ay,
            'Ax_prime': Ax_prime,
            'Ay_prime': Ay_prime,
            'vignetting_upper': vign_upper,
            'vignetting_lower': vign_lower,
            'relative_illumination': rel_illum,
        })

    return results


def seidel_aberrations(sys: OpticalSystem, catalog: dict = None) -> dict:
    """
    Вычисление сумм Зейделя (3-го порядка).
    SI — сферическая аберрация
    SII — кома
    SIII — астигматизм
    SIV — кривизна поля
    SV — дисторсия
    """
    wl = get_primary_wl(sys)
    ns = len(sys.surfaces)
    if ns < 2:
        return {'SI': 0, 'SII': 0, 'SIII': 0, 'SIV': 0, 'SV': 0}

    # Показатели преломления
    n_vals = [1.0]  # перед первой поверхностью — воздух
    for i, s in enumerate(sys.surfaces):
        if s.is_reflective:
            n_vals.append(-n_vals[-1])
        else:
            n_vals.append(refractive_index(s.glass, wl, catalog, getattr(s, 'n_override', None)))

    # ===== Параксиальный краевой луч (marginal ray) =====
    # y[0]=1, nu[0]=0 — параллельный оси на единичной высоте
    y = [0.0] * (ns + 1)
    nu = [0.0] * (ns + 1)
    y[0] = 1.0
    nu[0] = 0.0

    for i in range(ns):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else float('inf')
        if s.is_reflective:
            if R != float('inf'):
                nu[i + 1] = nu[i] - y[i] * (-2.0 * n_vals[i] / R)
            else:
                nu[i + 1] = nu[i]
        else:
            if R != float('inf'):
                nu[i + 1] = nu[i] - y[i] * (n_vals[i + 1] - n_vals[i]) / R
            else:
                nu[i + 1] = nu[i]
        if i < ns - 1:
            y[i + 1] = y[i] + nu[i + 1] * s.thickness / n_vals[i + 1]
        else:
            y[i + 1] = y[i] + nu[i + 1] * s.thickness / n_vals[i + 1]

    # ===== Параксиальный главный луч (chief ray) =====
    # Рассчитываем от положения диафрагмы (stop surface)
    yb = [0.0] * (ns + 1)
    nub = [0.0] * (ns + 1)

    stop_idx = max(0, min(sys.stop_surface - 1, ns - 1))  # 0-based, clamped

    # Главный луч проходит через центр диафрагмы: yb[stop_idx] = 0
    # Трассируем от стопа: yb=0 на стопе, nub=1 (единичный угол)
    yb[stop_idx] = 0.0
    nub[stop_idx] = 1.0

    # Обратный ход от стопа к поверхности 0
    for i in range(stop_idx - 1, -1, -1):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else float('inf')
        n1 = n_vals[i]
        n2 = n_vals[i + 1]
        d = s.thickness
        # Перенос назад: yb[i] = yb[i+1] - nub[i+1] * d / n_vals[i+1]
        yb[i] = yb[i + 1] - nub[i + 1] * d / n_vals[i + 1]
        # Преломление назад: nub[i] = nub[i+1] + yb[i] * (n2-n1)/R
        if R != float('inf'):
            nub[i] = nub[i + 1] + yb[i] * (n2 - n1) / R
        else:
            nub[i] = nub[i + 1]

    # Прямой ход от стопа до конца
    for i in range(stop_idx, ns):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else float('inf')
        n1 = n_vals[i]
        n2 = n_vals[i + 1]
        if R != float('inf'):
            nub[i + 1] = nub[i] - yb[i] * (n2 - n1) / R
        else:
            nub[i + 1] = nub[i]
        if i < ns - 1:
            yb[i + 1] = yb[i] + nub[i + 1] * s.thickness / n_vals[i + 1]
        else:
            yb[i + 1] = yb[i] + nub[i + 1] * s.thickness / n_vals[i + 1]

    # ===== Суммы Зейделя =====
    SI = 0.0
    SII = 0.0
    SIII = 0.0
    SIV = 0.0
    SV = 0.0

    for i in range(ns):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else float('inf')
        if R == float('inf'):
            continue
        n1 = n_vals[i]
        n2 = n_vals[i + 1]
        delta_n_inv = 1.0 / n2 - 1.0 / n1  # Δ(n⁻¹)

        # Преломляющий инвариант Зейделя: A = n_i * (u_i + h/R) = nu_i + n_i*h/R
        A = nu[i] + n_vals[i] * y[i] / R
        A_bar = nub[i] + n_vals[i] * yb[i] / R
        h = y[i]

        # SI — сферическая аберрация
        SI += A * A * h * delta_n_inv
        # SII — кома
        SII += A_bar * A * h * delta_n_inv
        # SIII — астигматизм
        SIII += A_bar * A_bar * h * delta_n_inv
        # SIV — кривизна поля (Петцваль)
        SIV += (n2 - n1) / (R * n1 * n2)
        # SV — дисторсия
        # SV = (Ā³/A + 3Ā²) · h · Δ(n⁻¹)
        # При A→0 член Ā³/A физически означает большую дисторсию 3-го порядка
        # от данной поверхности. Это не численный артефакт — поверхность вблизи
        # апертурной диафрагмы с A≈0 и Ā≠0 вносит доминирующий вклад в SV.
        # Формула точна для 3-го порядка; при малых |A| высшие порядки могут
        # компенсировать, но в Seidel сумме используется именно 3-й порядок.
        # Защита от точного деления на ноль:
        a_safe = A if abs(A) > TINY else (TINY if A >= 0 else -TINY)
        SV += (A_bar ** 3 / a_safe) * h * delta_n_inv
        SV += 3.0 * A_bar * A_bar * h * delta_n_inv

    return {'SI': SI, 'SII': SII, 'SIII': SIII, 'SIV': SIV, 'SV': SV}
