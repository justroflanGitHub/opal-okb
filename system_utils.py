"""
OPAL-OKB — Утилиты для работы с оптическими системами
Оборачивание, масштабирование, стандартизация радиусов
"""
import copy
import bisect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optics_engine import OpticalSystem, Surface


# ============================================================
# Стандартные радиусы ГОСТ 1807-75 (ряд R40 + доп. для оптики)
# ============================================================
STANDARD_RADII = [
    5, 5.3, 5.6, 6, 6.3, 6.7, 7.1, 7.5, 8, 8.5, 9, 9.5,
    10, 10.6, 11.2, 11.8, 12.5, 13.2, 14, 15, 16, 17, 18, 19, 20,
    21.2, 22.4, 23.6, 25, 26.5, 28, 30, 31.5, 33.5, 35.5, 37.5,
    40, 42.5, 45, 47.5, 50, 53, 56, 60, 63, 67, 71, 75, 80,
    85, 90, 95, 100, 106, 112, 118, 125, 132, 140, 150, 160,
    170, 180, 190, 200, 212, 224, 236, 250, 265, 280, 300,
    315, 335, 355, 375, 400, 425, 450, 475, 500, 530, 560,
    600, 630, 670, 710, 750, 800, 850, 900, 950, 1000,
    1060, 1120, 1180, 1250, 1320, 1400, 1500, 1600,
    1700, 1800, 1900, 2000, 2120, 2240, 2360, 2500,
    3000, 4000, 5000
]


def nearest_standard_radius(radius: float) -> float:
    """Найти ближайший стандартный радиус по ГОСТ 1807-75.

    Для плоских поверхностей (R=0) возвращает 0.
    Для отрицательных радиусов сохраняет знак.

    Args:
        radius: Радиус кривизны (мм)

    Returns:
        Ближайший стандартный радиус (мм)
    """
    if radius == 0.0 or abs(radius) > 1e12:
        return 0.0

    sign = 1.0 if radius > 0 else -1.0
    r_abs = abs(radius)

    # Бинарный поиск позиции в STANDARD_RADII
    pos = bisect.bisect_left(STANDARD_RADII, r_abs)

    # Выбираем ближайший из двух соседей
    candidates = []
    if pos > 0:
        candidates.append(STANDARD_RADII[pos - 1])
    if pos < len(STANDARD_RADII):
        candidates.append(STANDARD_RADII[pos])

    if not candidates:
        return radius  # fallback — не должно произойти

    best = min(candidates, key=lambda r: abs(r - r_abs))
    return sign * best


def standardize_radii(system: OpticalSystem) -> OpticalSystem:
    """Заменить все нестандартные радиусы на ближайшие ГОСТ 1807-75.

    Создаёт копию системы. Плоские поверхности (R=0) не затрагиваются.

    Args:
        system: Исходная оптическая система

    Returns:
        Новая система со стандартизованными радиусами
    """
    result = copy.deepcopy(system)
    for s in result.surfaces:
        s.radius = nearest_standard_radius(s.radius)
    result.name = (result.name + " (ГОСТ)") if result.name else "ГОСТ стандартизация"
    return result


def get_radii_changes(system: OpticalSystem) -> list:
    """Получить список изменений радиусов при стандартизации.

    Returns:
        Список кортежей (surface_index, old_radius, new_radius, delta_percent)
    """
    changes = []
    for i, s in enumerate(system.surfaces):
        new_r = nearest_standard_radius(s.radius)
        if abs(new_r - s.radius) > 1e-6:
            if abs(s.radius) > 1e-12:
                delta_pct = (new_r - s.radius) / s.radius * 100.0
            else:
                delta_pct = 0.0
            changes.append((i, s.radius, new_r, delta_pct))
    return changes


def reverse_system(system: OpticalSystem) -> OpticalSystem:
    """
    Обернуть оптическую систему (зеркально).

    - Поверхности идут в обратном порядке
    - Знаки радиусов меняются на противоположные
    - Толщины перепривязываются к новым позициям
    - Стоп-поверхность пересчитывается

    Пример: [S1(d=5), S2(d=10), S3] → [S3(-R3, d=10), S2(-R2, d=5), S1(-R1, d=0)]
    """
    result = copy.deepcopy(system)

    n = len(result.surfaces)
    if n == 0:
        return result

    # Исходные толщины: d[i] = расстояние от поверхности i до i+1
    # После разворота поверхности идут в обратном порядке.
    # Новая поверхность j (0-based) = старая поверхность (n-1-j).
    # Толщина для новой поверхности j = старая толщина поверхности (n-2-j),
    # т.к. d[n-2-j] — это зазор между старыми поверхностями (n-2-j) и (n-1-j),
    # а в новом порядке поверхности (n-1-j) и (n-2-j) стоят рядом.

    # Собираем старые данные
    old_radii = [s.radius for s in result.surfaces]
    old_thicknesses = [s.thickness for s in result.surfaces]
    old_glasses = [s.glass for s in result.surfaces]

    # Перестраиваем поверхности в обратном порядке
    # Стекло и толщина описывают среду ПОСЛЕ поверхности.
    # При обороте среда между old[i] и old[i+1] (описанная old[i])
    # становится средой после new_surface(=old[i+1]).
    # Поэтому glass и thickness берутся из old[n-2-j].
    reversed_surfaces = []
    for j in range(n):
        old_idx = n - 1 - j  # surface from original
        s = copy.deepcopy(result.surfaces[old_idx])
        s.radius = -old_radii[old_idx]
        # Glass + thickness from the PREVIOUS surface in original (= space between them)
        if old_idx >= 1:
            s.glass = old_glasses[old_idx - 1]
            s.thickness = old_thicknesses[old_idx - 1]
        else:
            # Last reversed surface (was first original) — old object space
            s.glass = ""
            s.thickness = 0.0
        reversed_surfaces.append(s)

    # Добавить поверхность-воздух в начало (бывшая плоскость изображения)
    # Толщина = BFD, стекло = то что было после последней поверхности
    air_surf = Surface(
        radius=0.0,
        thickness=old_thicknesses[n - 1],
        glass=old_glasses[n - 1],
        semi_diameter=result.surfaces[-1].semi_diameter if result.surfaces else 10.0,
    )
    reversed_surfaces.insert(0, air_surf)

    result.surfaces = reversed_surfaces
    n_new = len(result.surfaces)

    # Пересчитываем стоп-поверхность (1-based)
    new_stop = n + 2 - system.stop_surface
    result.stop_surface = max(1, min(n_new, new_stop))

    # Дополнение: обратить тип предмета (FINITE ↔ INFINITE) —
    # при оборачивании предмет и изображение меняются местами,
    # но для сохранения корректности лучше оставить object_type как есть,
    # т.к. пользователь может скорректировать его вручную.

    result.name = (result.name + " (rev)") if result.name else "Reversed"
    return result


def scale_system(system: OpticalSystem, factor: float) -> OpticalSystem:
    """
    Масштабировать все линейные размеры на factor.

    - Радиусы: R *= factor
    - Толщины: d *= factor
    - Полудиаметры: sd *= factor
    - Апертура: aperture *= factor
    - Углы поля НЕ меняются (для бесконечного предмета)
    """
    if abs(factor) < 1e-15:
        raise ValueError("Коэффициент масштабирования не может быть нулевым")

    result = copy.deepcopy(system)

    for s in result.surfaces:
        s.radius *= factor
        s.thickness *= factor
        s.semi_diameter *= factor
        # Асферические коэффициенты — не масштабируем, они в безразмерном виде
        # (коэффициенты при y^4, y^6 и т.д. зависят от нормировки)

    result.aperture_value *= factor

    # object_height — линейный размер (для FINITE масштабируем)
    # Для INFINITE это угол (градусы) — НЕ масштабируем
    from optics_engine import ObjectType
    if result.object_type == ObjectType.FINITE:
        result.object_height *= factor

    result.name = (result.name + f" (x{factor:.4g})") if result.name else f"Scaled x{factor:.4g}"
    return result



if __name__ == "__main__":
    from optics_engine import create_demo_system

    print("=== Исходная система ===")
    sys_orig = create_demo_system()
    for i, s in enumerate(sys_orig.surfaces):
        print(f"  S{i+1}: R={s.radius:.2f}, d={s.thickness:.2f}, glass={s.glass}, sd={s.semi_diameter:.2f}")
    print(f"  Stop={sys_orig.stop_surface}, aperture={sys_orig.aperture_value}")

    print("\n=== Обёрнутая система ===")
    sys_rev = reverse_system(sys_orig)
    for i, s in enumerate(sys_rev.surfaces):
        print(f"  S{i+1}: R={s.radius:.2f}, d={s.thickness:.2f}, glass={s.glass}, sd={s.semi_diameter:.2f}")
    print(f"  Stop={sys_rev.stop_surface}, aperture={sys_rev.aperture_value}")

    print("\n=== Масhtab system (x2) ===")
    sys_sc = scale_system(sys_orig, 2.0)
    for i, s in enumerate(sys_sc.surfaces):
        print(f"  S{i+1}: R={s.radius:.2f}, d={s.thickness:.2f}, glass={s.glass}, sd={s.semi_diameter:.2f}")
    print(f"  Stop={sys_sc.stop_surface}, aperture={sys_sc.aperture_value}")
