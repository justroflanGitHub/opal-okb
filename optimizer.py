"""
OPAL-OKB — Оптимизация оптических систем
Методы: DLS (Damped Least Squares) и Nelder-Mead (Simplex)
Целевая функция: RMS пятна рассеяния
"""
import copy
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optics_engine import (OpticalSystem, Surface, Wavelength, FieldPoint,
                           ObjectType, ApertureType, paraxial_trace, seidel_aberrations)
from ray_tracing import trace_ray_through_system, Ray, trace_fan
from aberrations import compute_spot_diagram, compute_rms_spot


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _deepcopy_system(system: OpticalSystem) -> OpticalSystem:
    """Глубокая копия оптической системы."""
    return copy.deepcopy(system)


def _get_variable(system: OpticalSystem, surface_idx: int, param_type: str) -> float:
    """Получить значение переменной (radius или thickness)."""
    s = system.surfaces[surface_idx]
    if param_type == 'radius':
        return s.radius
    elif param_type == 'thickness':
        return s.thickness
    else:
        raise ValueError(f"Неизвестный тип параметра: {param_type}")


def _set_variable(system: OpticalSystem, surface_idx: int, param_type: str, value: float):
    """Установить значение переменной с clamp по границам."""
    s = system.surfaces[surface_idx]
    if param_type == 'radius':
        s.radius = value
    elif param_type == 'thickness':
        s.thickness = value
    else:
        raise ValueError(f"Неизвестный тип параметра: {param_type}")


def _clamp_variable(system: OpticalSystem, surface_idx: int, param_type: str,
                    vmin: float, vmax: float):
    """Ограничить значение переменной в пределах [vmin, vmax]."""
    val = _get_variable(system, surface_idx, param_type)
    clamped = max(vmin, min(vmax, val))
    _set_variable(system, surface_idx, param_type, clamped)


def _merit_function(system: OpticalSystem,
                    variables: list,
                    num_rays: int = 30) -> float:
    """
    Целевая функция: взвешенное RMS пятна рассеяния по всем полям и длинам волн.

    Returns:
        RMS (мм) — чем меньше, тем лучше. Возвращает бесконечность при ошибке трассировки.
    """
    total_rms_sq = 0.0
    total_weight = 0.0

    for wl in system.wavelengths:
        wl_weight = wl.weight
        for fp in system.field_points:
            fp_weight = fp.weight
            spots = compute_spot_diagram(system, wl=wl.value, num_rays=num_rays,
                                         field_y=fp.y)
            if not spots:
                # Try with fewer rays or zero field as fallback
                spots = compute_spot_diagram(system, wl=wl.value, num_rays=max(5, num_rays//4), field_y=0.0)
                if not spots:
                    return float('inf')
            rms = compute_rms_spot(spots)
            w = wl_weight * fp_weight
            total_rms_sq += (rms ** 2) * w
            total_weight += w

    if total_weight == 0:
        return float('inf')

    return math.sqrt(total_rms_sq / total_weight)


def _apply_variables(system: OpticalSystem, x: list, variables: list):
    """Применить вектор переменных x к системе."""
    for i, (surf_idx, param_type, vmin, vmax) in enumerate(variables):
        _set_variable(system, surf_idx, param_type, x[i])
        _clamp_variable(system, surf_idx, param_type, vmin, vmax)


def _extract_variables(system: OpticalSystem, variables: list) -> list:
    """Извлечь текущие значения переменных из системы."""
    return [_get_variable(system, surf_idx, param_type)
            for surf_idx, param_type, vmin, vmax in variables]


# ---------------------------------------------------------------------------
# DLS — Damped Least Squares (Метод Левенберга-Марквардта)
# ---------------------------------------------------------------------------

def _finite_diff_jacobian(system: OpticalSystem, variables: list,
                          current_x: list, f0: float,
                          delta: float = 1e-4,
                          num_rays: int = 30) -> tuple:
    """
    Вычислить якобиан целевой функции конечными разностями.
    Возвращает (градиент, гессиан_аппрокс).

    Целевая функция φ = merit_function.
    Градиент: g[i] = (φ(x+δeᵢ) - φ(x)) / δ
    Якобиан:  J ≈ g (для скалярной целевой функции).
    """
    n = len(current_x)
    grad = [0.0] * n

    for i in range(n):
        x_plus = list(current_x)
        _, _, vmin, vmax = variables[i]
        step = delta * max(1.0, abs(current_x[i]))
        x_plus[i] = min(vmax, current_x[i] + step)

        sys_copy = _deepcopy_system(system)
        _apply_variables(sys_copy, x_plus, variables)
        f_plus = _merit_function(sys_copy, variables, num_rays=num_rays)

        if f_plus == float('inf'):
            f_plus = f0

        grad[i] = (f_plus - f0) / (x_plus[i] - current_x[i]) if abs(x_plus[i] - current_x[i]) > 1e-15 else 0.0

    return grad


def _dls_step(grad: list, damping: float, f_value: float) -> list:
    """
    Один шаг DLS (Levenberg-Marquardt).
    Для скалярной целевой функции φ:
      dx = -g / (||g||² + λ)
    Это эквивалентно (JᵀJ + λI)⁻¹ Jᵀφ для скалярного случая.
    """
    n = len(grad)
    g_norm_sq = sum(g * g for g in grad)

    if g_norm_sq < 1e-20:
        return [0.0] * n

    # Шаг: Δx = -g / (gᵀg + λ)
    # f_value используется для масштабирования демпфирования
    lam = damping * max(0.001, f_value)  # пропорционально φ
    scale = 1.0 / (g_norm_sq + lam)

    # Масштабируем шаг: увеличиваем для лучшей сходимости
    step_size = max(1.0, math.sqrt(g_norm_sq))
    dx = [-g * scale * step_size for g in grad]
    return dx


def optimize_dls(system: OpticalSystem,
                 variables: list,
                 max_iter: int = 50,
                 damping: float = 1.0,
                 tol: float = 1e-8,
                 num_rays: int = 30,
                 callback=None) -> OpticalSystem:
    """
    Damped Least Squares оптимизация.

    Args:
        system: оптическая система
        variables: [(surface_idx, 'radius'|'thickness', min, max), ...]
        max_iter: максимальное число итераций
        damping: начальный коэффициент демпфирования
        tol: допуск на изменение целевой функции
        num_rays: число лучей для spot diagram
        callback: callable(iteration, merit_value, x)

    Returns:
        Оптимизированная оптическая система
    """
    opt_sys = _deepcopy_system(system)
    x = _extract_variables(opt_sys, variables)

    f_current = _merit_function(opt_sys, variables, num_rays=num_rays)
    f_prev = f_current

    if callback:
        callback(0, f_current, list(x))

    adaptive_damping = damping

    for iteration in range(1, max_iter + 1):
        # Вычисляем градиент
        grad = _finite_diff_jacobian(opt_sys, variables, x, f_current, num_rays=num_rays)

        # DLS шаг
        dx = _dls_step(grad, adaptive_damping, f_current)

        # Проверяем, что шаг ненулевой
        dx_norm = math.sqrt(sum(d * d for d in dx))
        if dx_norm < 1e-15:
            break

        # Line search: пробуем шаг, если плохо — уменьшаем
        alpha = 1.0
        f_best = f_current
        x_best = list(x)
        improved = False

        for ls_attempt in range(15):  # до 15 попыток line search
            x_trial = list(x)
            for i in range(len(x)):
                x_trial[i] += alpha * dx[i]
                # Clamp
                _, _, vmin, vmax = variables[i]
                x_trial[i] = max(vmin, min(vmax, x_trial[i]))

            sys_trial = _deepcopy_system(system)
            _apply_variables(sys_trial, x_trial, variables)
            f_trial = _merit_function(sys_trial, variables, num_rays=num_rays)

            if f_trial < f_best:
                f_best = f_trial
                x_best = list(x_trial)
                improved = True
                break
            else:
                alpha *= 0.5

        f_prev = f_current

        if improved:
            # Уменьшаем демпфирование при успехе (больше свободы)
            adaptive_damping = max(1e-6, adaptive_damping * 0.5)
            x = x_best
            _apply_variables(opt_sys, x, variables)
            f_current = f_best
        else:
            # Увеличиваем демпфирование при неудаче (больше стабилизации)
            adaptive_damping *= 3.0

        if callback:
            callback(iteration, f_current, list(x))

        # Проверка сходимости
        if iteration > 1 and abs(f_prev - f_current) < tol * max(1.0, abs(f_current)):
            break

    return opt_sys


# ---------------------------------------------------------------------------
# Nelder-Mead Simplex
# ---------------------------------------------------------------------------

def _simplex_init(x0: list, variables: list, scale: float = 0.05) -> list:
    """
    Инициализация симплекса: n+1 вершин.
    Каждая вершина — вектор переменных.
    """
    n = len(x0)
    simplex = [list(x0)]

    for i in range(n):
        xi = list(x0)
        _, _, vmin, vmax = variables[i]
        step = scale * max(1.0, abs(x0[i]))
        xi[i] += step
        xi[i] = max(vmin, min(vmax, xi[i]))
        simplex.append(xi)

    return simplex


def optimize_simplex(system: OpticalSystem,
                     variables: list,
                     max_iter: int = 50,
                     tol: float = 1e-7,
                     num_rays: int = 30,
                     alpha_s: float = 1.0,   # reflection
                     gamma_s: float = 2.0,   # expansion
                     rho_s: float = 0.5,     # contraction
                     sigma_s: float = 0.5,   # shrink
                     callback=None) -> OpticalSystem:
    """
    Nelder-Mead Simplex оптимизация.

    Args:
        system: оптическая система
        variables: [(surface_idx, 'radius'|'thickness', min, max), ...]
        max_iter: максимальное число итераций
        tol: допуск на сходимость симплекса
        num_rays: число лучей для spot diagram
        callback: callable(iteration, merit_value, x)

    Returns:
        Оптимизированная оптическая система
    """
    opt_sys = _deepcopy_system(system)
    x0 = _extract_variables(opt_sys, variables)
    simplex = _simplex_init(x0, variables)

    def eval_point(x_pt):
        sys_eval = _deepcopy_system(system)
        _apply_variables(sys_eval, x_pt, variables)
        return _merit_function(sys_eval, variables, num_rays=num_rays)

    # Оценка всех вершин
    f_values = [eval_point(v) for v in simplex]

    for iteration in range(1, max_iter + 1):
        # Сортировка: лучшая (мин) → худшая (макс)
        order = sorted(range(len(simplex)), key=lambda i: f_values[i])
        simplex = [simplex[i] for i in order]
        f_values = [f_values[i] for i in order]

        n = len(x0)
        f_best = f_values[0]
        f_worst = f_values[-1]
        f_second_worst = f_values[-2]

        if callback:
            callback(iteration, f_best, list(simplex[0]))

        # Проверка сходимости: разброс значений
        if abs(f_worst - f_best) < tol * max(1.0, abs(f_best)):
            break

        # Центроид (без худшей точки)
        centroid = [0.0] * n
        for i in range(n):
            for j in range(n):
                centroid[j] += simplex[i][j]
        centroid = [c / n for c in centroid]

        # Отражение (reflection)
        xr = [centroid[j] + alpha_s * (centroid[j] - simplex[-1][j]) for j in range(n)]
        # Clamp
        for j in range(n):
            _, _, vmin, vmax = variables[j]
            xr[j] = max(vmin, min(vmax, xr[j]))

        fr = eval_point(xr)

        if f_best <= fr < f_second_worst:
            # Принимаем отражённую точку
            simplex[-1] = xr
            f_values[-1] = fr

        elif fr < f_best:
            # Расширение (expansion)
            xe = [centroid[j] + gamma_s * (xr[j] - centroid[j]) for j in range(n)]
            for j in range(n):
                _, _, vmin, vmax = variables[j]
                xe[j] = max(vmin, min(vmax, xe[j]))

            fe = eval_point(xe)
            if fe < fr:
                simplex[-1] = xe
                f_values[-1] = fe
            else:
                simplex[-1] = xr
                f_values[-1] = fr

        else:
            # Сжатие (contraction)
            xc = [centroid[j] + rho_s * (simplex[-1][j] - centroid[j]) for j in range(n)]
            for j in range(n):
                _, _, vmin, vmax = variables[j]
                xc[j] = max(vmin, min(vmax, xc[j]))

            fc = eval_point(xc)
            if fc < f_worst:
                simplex[-1] = xc
                f_values[-1] = fc
            else:
                # Уменьшение (shrink)
                for i in range(1, len(simplex)):
                    for j in range(n):
                        simplex[i][j] = simplex[0][j] + sigma_s * (simplex[i][j] - simplex[0][j])
                        _, _, vmin, vmax = variables[j]
                        simplex[i][j] = max(vmin, min(vmax, simplex[i][j]))
                    f_values[i] = eval_point(simplex[i])

    # Применяем лучшую точку
    best_idx = f_values.index(min(f_values))
    x_best = simplex[best_idx]
    _apply_variables(opt_sys, x_best, variables)

    return opt_sys


# ---------------------------------------------------------------------------
# Главный интерфейс
# ---------------------------------------------------------------------------

def optimize(system: OpticalSystem,
             variables: list,
             method: str = 'dls',
             max_iter: int = 50,
             callback=None,
             num_rays: int = 30) -> OpticalSystem:
    """
    Оптимизация оптической системы.

    Args:
        system: оптическая система (OpticalSystem)
        variables: список переменных:
            [(surface_idx, 'radius'|'thickness', min_value, max_value), ...]
        method: метод оптимизации — 'dls' или 'simplex'
        max_iter: максимальное число итераций
        callback: callable(iteration, merit_value, variables_list) для мониторинга
        num_rays: число лучей на одну сторону для spot diagram

    Returns:
        Оптимизированная копия оптической системы
    """

    # Валидация
    if not variables:
        raise ValueError("Список переменных пуст")

    for v in variables:
        if len(v) != 4:
            raise ValueError(f"Каждая переменная должна быть кортежем из 4 элементов: {v}")
        surf_idx, param_type, vmin, vmax = v
        if param_type not in ('radius', 'thickness'):
            raise ValueError(f"Тип параметра должен быть 'radius' или 'thickness': {param_type}")
        if surf_idx < 0 or surf_idx >= system.num_surfaces:
            raise ValueError(f"Индекс поверхности вне диапазона: {surf_idx}")
        if vmin > vmax:
            raise ValueError(f"min > max для переменной: {v}")

    if method == 'dls':
        return optimize_dls(system, variables, max_iter=max_iter,
                            num_rays=num_rays, callback=callback)
    elif method == 'simplex':
        return optimize_simplex(system, variables, max_iter=max_iter,
                                num_rays=num_rays, callback=callback)
    else:
        raise ValueError(f"Неизвестный метод оптимизации: {method}. Используйте 'dls' или 'simplex'")


# ---------------------------------------------------------------------------
# Подгонка характеристик (Fitting)
# ---------------------------------------------------------------------------

def fit_focal_length(system: OpticalSystem, target_f: float,
                     surface_idx: int, param_type: str = 'radius',
                     tol: float = 1e-6, max_iter: int = 100) -> OpticalSystem:
    """
    Подогнать радиус поверхности для заданного фокусного расстояния.
    Внимание: толщина поверхности практически не влияет на f'.
    """
    if param_type == 'thickness':
        # Толщина почти не меняет f' — подгон невозможен
        return _deepcopy_system(system)

    sys = _deepcopy_system(system)

    current_val = _get_variable(sys, surface_idx, param_type)

    # Определяем границы поиска
    if param_type == 'radius':
        # Радиус может быть от малого до очень большого
        if abs(current_val) < 1e-10:
            current_val = 100.0  # стартовое значение
        lo = current_val * 0.01
        hi = current_val * 100.0
        # Учитываем знак
        if current_val < 0:
            lo, hi = -abs(hi), -abs(lo)
    else:
        lo = 0.001
        hi = current_val * 10.0 if current_val > 0 else 1000.0

    def eval_f(val):
        _set_variable(sys, surface_idx, param_type, val)
        r = paraxial_trace(sys)
        return r.get('focal_length', 0)

    # Оцениваем текущее f
    _set_variable(sys, surface_idx, param_type, current_val)
    f_current = eval_f(current_val)

    if abs(f_current - target_f) < tol:
        return sys

    # Расширяем границы пока target_f не окажется в диапазоне
    f_lo = eval_f(lo)
    f_hi = eval_f(hi)

    for _ in range(20):
        if (f_lo - target_f) * (f_hi - target_f) <= 0:
            break
        if param_type == 'radius':
            if abs(lo) > 1e-10:
                lo *= 0.5
            if abs(hi) > 1e-10:
                hi *= 2.0
            if current_val < 0:
                lo, hi = -abs(hi), -abs(lo)
        else:
            lo = max(0.001, lo * 0.5)
            hi *= 2.0
        f_lo = eval_f(lo)
        f_hi = eval_f(hi)

    # Если не удалось найти границы — цель недостижима
    if (f_lo - target_f) * (f_hi - target_f) > 0:
        f_min = min(f_lo, f_hi, f_current)
        f_max = max(f_lo, f_hi, f_current)
        raise ValueError(
            f"Невозможно достичь f'={target_f:.4f} мм изменением параметра. "
            f"Достижимый диапазон: [{f_min:.4f}, {f_max:.4f}] мм."
        )

    # Бисекция
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f_mid = eval_f(mid)

        if abs(f_mid - target_f) < tol:
            _set_variable(sys, surface_idx, param_type, mid)
            return sys

        if (f_lo - target_f) * (f_mid - target_f) < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    _set_variable(sys, surface_idx, param_type, (lo + hi) / 2.0)
    return sys


def fit_bfd(system: OpticalSystem, target_bfd: float,
            surface_idx: int = -1, param_type: str = 'thickness',
            tol: float = 1e-6, max_iter: int = 100) -> OpticalSystem:
    """
    Подогнать толщину/радиус поверхности для заданного заднего фокального отрезка.
    По умолчанию подгоняет толщину последней поверхности.

    Args:
        system: оптическая система
        target_bfd: целевой BFD (мм)
        surface_idx: индекс поверхности (0-based), -1 = последняя
        param_type: 'thickness' или 'radius'
        tol: допуск на BFD (мм)
        max_iter: макс. число итераций

    Returns:
        Копия системы с подогнанным параметром
    """
    sys = _deepcopy_system(system)

    if surface_idx == -1:
        surface_idx = len(sys.surfaces) - 1

    current_val = _get_variable(sys, surface_idx, param_type)

    # Границы поиска
    if param_type == 'thickness':
        lo = 0.001
        hi = max(current_val * 5.0, abs(target_bfd) * 3.0, 1000.0)
    else:
        if abs(current_val) < 1e-10:
            current_val = 100.0
        lo = current_val * 0.01
        hi = current_val * 100.0
        if current_val < 0:
            lo, hi = -abs(hi), -abs(lo)

    def eval_bfd(val):
        _set_variable(sys, surface_idx, param_type, val)
        r = paraxial_trace(sys)
        return r.get('back_focal_distance', 0)

    # Проверка: меняется ли BFD при изменении параметра?
    # (толщина последней поверхности — это воздушный зазор до плоскости
    # изображения, он не влияет на положение фокуса относительно последней
    # поверхности)
    bfd_current = eval_bfd(current_val)
    probe_val = current_val * 1.01 + 0.1
    bfd_probe = eval_bfd(probe_val)
    _set_variable(sys, surface_idx, param_type, current_val)  # restore

    if abs(bfd_current - bfd_probe) < 1e-10:
        raise ValueError(
            f"Изменение {param_type} поверхности {surface_idx + 1} "
            f"не влияет на BFD. Выберите радиус или другую поверхность."
        )

    if abs(bfd_current - target_bfd) < tol:
        return sys

    bfd_lo = eval_bfd(lo)
    bfd_hi = eval_bfd(hi)

    # Расширяем границы
    for _ in range(20):
        if (bfd_lo - target_bfd) * (bfd_hi - target_bfd) <= 0:
            break
        if param_type == 'thickness':
            lo = max(0.001, lo * 0.5)
            hi *= 2.0
        else:
            if abs(lo) > 1e-10:
                lo *= 0.5
            if abs(hi) > 1e-10:
                hi *= 2.0
            if current_val < 0:
                lo, hi = -abs(hi), -abs(lo)
        bfd_lo = eval_bfd(lo)
        bfd_hi = eval_bfd(hi)

    # Если не удалось найти границы — цель недостижима
    if (bfd_lo - target_bfd) * (bfd_hi - target_bfd) > 0:
        bfd_min = min(bfd_lo, bfd_hi, bfd_current)
        bfd_max = max(bfd_lo, bfd_hi, bfd_current)
        raise ValueError(
            f"Невозможно достичь BFD={target_bfd:.4f} мм изменением параметра. "
            f"Достижимый диапазон: [{bfd_min:.4f}, {bfd_max:.4f}] мм."
        )

    # Бисекция
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        bfd_mid = eval_bfd(mid)

        if abs(bfd_mid - target_bfd) < tol:
            _set_variable(sys, surface_idx, param_type, mid)
            return sys

        if (bfd_lo - target_bfd) * (bfd_mid - target_bfd) < 0:
            hi = mid
            bfd_hi = bfd_mid
        else:
            lo = mid
            bfd_lo = bfd_mid

    _set_variable(sys, surface_idx, param_type, (lo + hi) / 2.0)
    return sys


def fit_magnification(system: OpticalSystem, target_mag: float,
                      surface_idx: int, param_type: str = 'radius',
                      tol: float = 1e-6, max_iter: int = 100) -> OpticalSystem:
    """
    Подогнать параметр для заданного увеличения.
    (Для систем с конечным предметом.)

    Args:
        system: оптическая система
        target_mag: целевое увеличение
        surface_idx: индекс поверхности
        param_type: 'radius' или 'thickness'
        tol: допуск
        max_iter: макс. число итераций

    Returns:
        Копия системы с подогнанным параметром
    """
    sys = _deepcopy_system(system)

    current_val = _get_variable(sys, surface_idx, param_type)

    if param_type == 'radius':
        lo = abs(current_val) * 0.01 if abs(current_val) > 1e-10 else 10.0
        hi = abs(current_val) * 100.0 if abs(current_val) > 1e-10 else 10000.0
        if current_val < 0:
            lo, hi = -hi, -lo
    else:
        lo = 0.001
        hi = max(current_val * 10.0, 1000.0)

    def eval_mag(val):
        _set_variable(sys, surface_idx, param_type, val)
        r = paraxial_trace(sys)
        return r.get('magnification', 0)

    mag_lo = eval_mag(lo)
    mag_hi = eval_mag(hi)

    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        mag_mid = eval_mag(mid)

        if abs(mag_mid - target_mag) < tol:
            _set_variable(sys, surface_idx, param_type, mid)
            return sys

        if (mag_lo - target_mag) * (mag_mid - target_mag) < 0:
            hi = mid
            mag_hi = mag_mid
        else:
            lo = mid
            mag_lo = mag_mid

    _set_variable(sys, surface_idx, param_type, (lo + hi) / 2.0)
    return sys


# ---------------------------------------------------------------------------
# Демо-система для тестирования
# ---------------------------------------------------------------------------

def create_optimization_demo() -> OpticalSystem:
    """
    Создать демо-систему для тестирования оптимизации:
    Двояковыпуклая линза с начальной сферической аберрацией.
    """
    sys = OpticalSystem(
        name="Демо: Двояковыпуклая линза (оптимизация)",
        object_type=ObjectType.INFINITE,
        object_height=5.0,
    )
    sys.wavelengths = [
        Wavelength(0.58756, 1.0, "d"),
    ]
    sys.field_points = [
        FieldPoint(0.0, weight=1.0),   # осевой пучок
    ]
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0  # мм
    sys.stop_surface = 1

    # Двояковыпуклая линза: R1 = 60, R2 = -60, d = 5, стекло К8
    # Воздушный промежуток до изображения = 55 мм
    sys.surfaces = [
        Surface(radius=60.0, thickness=5.0, glass="К8", semi_diameter=12.0),
        Surface(radius=-60.0, thickness=55.0, glass="", semi_diameter=12.0),
    ]

    return sys


def test_optimization():
    """Протестировать оптимизацию на демо-системе."""
    print("=" * 60)
    print("ТЕСТ ОПТИМИЗАЦИИ ОПТИЧЕСКОЙ СИСТЕМЫ")
    print("=" * 60)

    sys = create_optimization_demo()
    print(f"\nСистема: {sys.name}")
    print(f"Поверхности:")
    for i, s in enumerate(sys.surfaces):
        print(f"  {i}: R={s.radius:.2f}, d={s.thickness:.2f}, стекло={s.glass or 'воздух'}")
    print(f"Апертура: {sys.aperture_value} мм")

    # Начальный RMS
    spots_before = compute_spot_diagram(sys, wl=0.58756, num_rays=30, field_y=0.0)
    rms_before = compute_rms_spot(spots_before)
    print(f"\nНачальный RMS пятна рассеяния: {rms_before:.6f} мм")

    # Параксиальные характеристики
    parax = paraxial_trace(sys)
    print(f"Фокусное расстояние: {parax.get('focal_length', 0):.2f} мм")

    # Зейделевские суммы
    seidel = seidel_aberrations(sys)
    print(f"\nСуммы Зейделя:")
    for k, v in seidel.items():
        print(f"  {k}: {v:.6f}")

    # --- DLS оптимизация ---
    print("\n" + "-" * 40)
    print("DLS Оптимизация")
    print("-" * 40)

    # Варьируем радиусы обеих поверхностей и толщину линзы
    variables = [
        (0, 'radius', 30.0, 200.0),    # R1: от 30 до 200
        (1, 'radius', -200.0, -30.0),   # R2: от -200 до -30
        (0, 'thickness', 2.0, 15.0),    # d1: от 2 до 15
        (1, 'thickness', 30.0, 100.0),  # d2 (воздух): от 30 до 100
    ]

    history_dls = []

    def dls_callback(iteration, merit, x):
        history_dls.append((iteration, merit))
        if iteration % 5 == 0 or iteration == 0:
            print(f"  Итерация {iteration:3d}: RMS = {merit:.6f} мм, "
                  f"x = [{', '.join(f'{v:.3f}' for v in x)}]")

    opt_dls = optimize(sys, variables, method='dls', max_iter=100,
                       callback=dls_callback, num_rays=20)

    spots_dls = compute_spot_diagram(opt_dls, wl=0.58756, num_rays=30, field_y=0.0)
    rms_dls = compute_rms_spot(spots_dls)

    print(f"\nРезультат DLS:")
    improvement_dls = (1 - rms_dls / rms_before) * 100
    print(f"  RMS: {rms_before:.6f} -> {rms_dls:.6f} mm "
          f"(improvement: {improvement_dls:.1f}%)")
    for i, s in enumerate(opt_dls.surfaces):
        print(f"  Поверхность {i}: R={s.radius:.3f}, d={s.thickness:.3f}")

    parax_dls = paraxial_trace(opt_dls)
    print(f"  Фокусное расстояние: {parax_dls.get('focal_length', 0):.2f} мм")

    # --- Simplex оптимизация ---
    print("\n" + "-" * 40)
    print("Simplex (Nelder-Mead) Оптимизация")
    print("-" * 40)

    history_simplex = []

    def simplex_callback(iteration, merit, x):
        history_simplex.append((iteration, merit))
        if iteration % 10 == 0 or iteration <= 1:
            print(f"  Итерация {iteration:3d}: RMS = {merit:.6f} мм")

    opt_simplex = optimize(sys, variables, method='simplex', max_iter=100,
                           callback=simplex_callback, num_rays=20)

    spots_simplex = compute_spot_diagram(opt_simplex, wl=0.58756, num_rays=30, field_y=0.0)
    rms_simplex = compute_rms_spot(spots_simplex)

    print(f"\nРезультат Simplex:")
    improvement_sx = (1 - rms_simplex / rms_before) * 100
    print(f"  RMS: {rms_before:.6f} -> {rms_simplex:.6f} mm "
          f"(improvement: {improvement_sx:.1f}%)")
    for i, s in enumerate(opt_simplex.surfaces):
        print(f"  Поверхность {i}: R={s.radius:.3f}, d={s.thickness:.3f}")

    # --- Итоговая сводка ---
    print("\n" + "=" * 60)
    print("ИТОГОВАЯ СВОДКА")
    print("=" * 60)
    print(f"{'Метод':<15} {'RMS до':>12} {'RMS после':>12} {'Улучшение':>12}")
    print("-" * 60)
    print(f"{'DLS':<15} {rms_before:>12.6f} {rms_dls:>12.6f} {(1 - rms_dls / rms_before) * 100:>11.1f}%")
    print(f"{'Simplex':<15} {rms_before:>12.6f} {rms_simplex:>12.6f} {(1 - rms_simplex / rms_before) * 100:>11.1f}%")
    print("-" * 60)

    seidel_dls = seidel_aberrations(opt_dls)
    seidel_sx = seidel_aberrations(opt_simplex)
    print(f"\nСуммы Зейделя (SI — сферическая аберрация):")
    print(f"  Исходная:   SI = {seidel['SI']:.6f}")
    print(f"  DLS:        SI = {seidel_dls['SI']:.6f}")
    print(f"  Simplex:    SI = {seidel_sx['SI']:.6f}")

    return opt_dls, opt_simplex


if __name__ == "__main__":
    test_optimization()
