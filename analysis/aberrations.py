"""
OPAL-OKB - Анализ аберраций (Л1.4.6-Л1.4.7)
Графики: поперечные, продольные, волновые аберрации
Точечные диаграммы (Л1.6.1)
"""
import math
import numpy as np
from typing import List, Tuple, Dict
from optics_engine import OpticalSystem, Surface, ObjectType, Wavelength, FieldPoint, paraxial_trace
from ray_tracing import Ray, trace_ray_through_system
from glass_catalog import compute_refractive_index
from optics_utils import (compute_z_positions, get_primary_wl, get_effective_aperture,
                          make_field_ray, EPSILON, TINY)


def _compute_ray_start(system, parax):
    """Compute z_start and z_pupil for ray launching through entrance pupil."""
    sP = parax.get('sP', 0) if parax else 0
    # Entrance pupil relative to first surface vertex
    z_pupil = sP  # mm from first surface
    # Start well before the system
    z_start = -max(abs(z_pupil), 10.0) - 5.0
    return z_start, z_pupil


def _aim_at_pupil(pupil_x, pupil_y, z_start, z_pupil, sin_a, cos_a):
    """Back-project pupil coordinates to z_start plane.

    Field tilt is in Y direction (l=sin_a, m=cos_a).
    Returns (x_start, y_start) for ray at z_start.
    """
    dz = z_pupil - z_start
    x_start = pupil_x  # no tilt in X
    if cos_a > EPSILON:
        y_start = pupil_y - dz * sin_a / cos_a
    else:
        y_start = pupil_y
    return x_start, y_start


def trace_aberration_fan(sys: OpticalSystem, wl: float,
                          num_rays: int = 20, field_y: float = 0.0
                          ) -> List[Dict]:
    """
    Трассировка веера лучей для анализа аберраций.
    Возвращает список словарей с данными каждого луча.

    Для каждого луча:
    - pupil_y: зрачковая координата (0..1)
    - dy: поперечная аберрация (мм)
    - ds: продольная аберрация (мм)
    - wave: волновая аберрация (длины волн) - через OPL
    - y_img: высота на плоскости изображения
    """
    aperture = get_effective_aperture(sys, default=10.0)

    # Найдём фокальную плоскость через параксиальный расчёт
    parax = paraxial_trace(sys)
    bfd = parax.get('back_focal_distance', 0)
    efl = parax.get('focal_length', 0)

    # Z-позиции
    z_pos = compute_z_positions(sys)

    img_z = z_pos[-1]

    # ===== Вычисляем волновую аберрацию через OPL =====
    # 1. Определяем параксиальный фокус
    last_surf_z = z_pos[-2] if len(z_pos) > 1 else z_pos[-1]
    parax_focus_z = last_surf_z + bfd if bfd != 0 else img_z

    # 2. Радиус reference sphere
    ref_sphere_radius = parax_focus_z - last_surf_z
    if abs(ref_sphere_radius) < EPSILON:
        ref_sphere_radius = 1.0  # fallback

    # 3. Вычисляем z_start через входной зрачок
    z_start, z_pupil = _compute_ray_start(sys, parax)

    # 4. Трассируем главный луч (через центр зрачка) для OPL_chief
    if sys.object_type == ObjectType.INFINITE:
        chief_ray = make_field_ray(sys, 0, 0, field_y, z_start, z_pupil)
    else:
        obj_z = -sys.surfaces[0].thickness if sys.surfaces else -50
        chief_ray = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

    # Для осевого пучка (field_y=0) главный луч идёт вдоль оси
    chief_trace = trace_ray_through_system(sys, chief_ray, wl)
    opl_chief = chief_trace.opl if chief_trace.success else 0.0

    # Если главный луч успешен, добавим OPL от последней поверхности до reference sphere
    if chief_trace.success and len(chief_trace.path) >= 2:
        chief_last = chief_trace.path[-1]
        # OPL от img_z до reference sphere
        dz_to_ref = parax_focus_z - chief_last[2]
        # Среда после последней поверхности - воздух
        opl_chief += 1.0 * dz_to_ref  # n_air = 1

    results = []

    for i in range(num_rays):
        # Зрачковая координата от -1 до 1
        pupil_y = -1.0 + 2.0 * i / (num_rays - 1) if num_rays > 1 else 0.0
        y_start = pupil_y * aperture / 2

        # Создаём луч
        ray = make_field_ray(sys, 0, y_start, field_y, z_start, z_pupil)

        # Трассировка
        result = trace_ray_through_system(sys, ray, wl)

        if result.success and len(result.path) >= 2:
            last = result.path[-1]

            # Поперечная аберрация: отклонение от главного луча
            dy = last[1]

            # Продольная аберрация
            if len(result.path) >= 2:
                prev = result.path[-2]
                dz = last[2] - prev[2]
                slope_y = (last[1] - prev[1]) / dz if abs(dz) > EPSILON else 0
                ds = -dy / slope_y if abs(slope_y) > EPSILON else 0
            else:
                ds = 0

            # Волновая аберрация через OPL:
            # W = (OPL_луча_до_reference_sphere - OPL_главного_до_reference_sphere) / λ
            # OPL до reference sphere = result.opl + n_air * dist(ref_sphere_intersection)
            # Для простоты: propagate до parax_focus_z по прямой
            dz_to_focus = parax_focus_z - last[2]
            opl_full = result.opl + 1.0 * dz_to_focus  # n_air = 1
            wave = (opl_full - opl_chief) / wl if wl > 0 else 0.0

            results.append({
                'pupil_y': pupil_y,
                'dy': dy,
                'ds': ds,
                'wave': wave,
                'y_img': last[1],
                'z_img': last[2],
                'success': True,
            })
        else:
            results.append({
                'pupil_y': pupil_y,
                'dy': None,
                'ds': None,
                'wave': None,
                'y_img': None,
                'z_img': None,
                'success': False,
            })

    return results


def _hexapolar_points(num_rings: int = 6) -> list[tuple[float, float]]:
    """Generate hexapolar pupil sampling points.

    Returns list of (px, py) normalized pupil coordinates.
    Rings: 0=center, 1=6 points, 2=12, ..., n=6*n points.
    Total points: 1 + 6*(1+2+...+n) = 1 + 3*n*(n+1).

    For num_rings=6: 127 points.

    Args:
        num_rings: Number of hexapolar rings (default 6 → 127 points).

    Returns:
        List of (px, py) tuples in range [-1, 1].
    """
    points = [(0.0, 0.0)]  # center
    for ring in range(1, num_rings + 1):
        r = ring / num_rings
        n_in_ring = 6 * ring
        for i in range(n_in_ring):
            angle = 2 * math.pi * i / n_in_ring
            points.append((r * math.cos(angle), r * math.sin(angle)))
    return points


def compute_spot_diagram(sys: OpticalSystem, wl: float = 0.58756,
                          num_rays: int = 50, field_y: float = 0.0,
                          sampling: str = "grid"
                          ) -> List[Tuple[float, float]]:
    """
    Точечная диаграмма (Л1.6.1).
    Трассировка сетки лучей на зрачке → координаты (dx, dy) на изображении.

    Args:
        sys: Оптическая система.
        wl: Длина волны (мкм).
        num_rays: Число лучей по стороне сетки (для 'grid') или
                  число колец (для 'hexapolar', по умолчанию 6 → 127 лучей).
        field_y: Угол поля (градусы).
        sampling: 'grid' (квадратная сетка с круглой маской, по умолчанию)
                  или 'hexapolar' (гексаполярная выборка — более равномерное
                  покрытие зрачка, без алиасинга по осям).
    """
    aperture = get_effective_aperture(sys, default=10.0)
    parax = paraxial_trace(sys)
    z_start, z_pupil = _compute_ray_start(sys, parax)

    # Главный луч (для определения центра)
    if sys.object_type == ObjectType.INFINITE:
        chief_ray = make_field_ray(sys, 0, 0, field_y, z_start, z_pupil)
    else:
        obj_z = -sys.surfaces[0].thickness if sys.surfaces else -50
        chief_ray = Ray(x=0, y=0, z=obj_z, k=0, l=0, m=1)

    chief_result = trace_ray_through_system(sys, chief_ray, wl)
    if not chief_result.success or not chief_result.path:
        return []

    chief_y = chief_result.path[-1][1]
    chief_x = chief_result.path[-1][0]

    # Построение списка зрачковых координат
    if sampling == "hexapolar":
        pupil_coords = _hexapolar_points(num_rings=num_rays if num_rays <= 20 else 6)
    else:
        pupil_coords = []
        for i in range(num_rays):
            for j in range(num_rays):
                px = -1.0 + 2.0 * i / (num_rays - 1) if num_rays > 1 else 0.0
                py = -1.0 + 2.0 * j / (num_rays - 1) if num_rays > 1 else 0.0
                if px**2 + py**2 <= 1.0:
                    pupil_coords.append((px, py))

    spots = []
    for px, py in pupil_coords:
        y_start = py * aperture / 2
        x_start = px * aperture / 2

        ray = make_field_ray(sys, x_start, y_start, field_y, z_start, z_pupil)

        result = trace_ray_through_system(sys, ray, wl)

        if result.success and result.path:
            last = result.path[-1]
            dx = last[0] - chief_x
            dy = last[1] - chief_y
            spots.append((dx, dy))

    return spots


def compute_rms_spot(spots: List[Tuple[float, float]]) -> float:
    """RMS радиус пятна рассеяния (мм)."""
    if not spots:
        return 0.0
    r2 = sum(dx**2 + dy**2 for dx, dy in spots) / len(spots)
    return math.sqrt(r2)


def compute_rms_spot_xy(spot_points: List[Tuple[float, float]]) -> Dict:
    """
    Раздельные RMS по X и Y + энергетический центр.

    Возвращает: {
        'rms_x': float,  # RMS по X (сагиттальный)
        'rms_y': float,  # RMS по Y (меридиональный)
        'centroid_x': float,  # энергетический центр X
        'centroid_y': float,  # энергетический центр Y
        'rms_total': float,  # общий RMS
    }
    """
    if not spot_points:
        return {'rms_x': 0.0, 'rms_y': 0.0, 'centroid_x': 0.0,
                'centroid_y': 0.0, 'rms_total': 0.0}
    n = len(spot_points)
    cx = sum(dx for dx, dy in spot_points) / n
    cy = sum(dy for dx, dy in spot_points) / n
    rms_x = math.sqrt(sum((dx - cx)**2 for dx, _ in spot_points) / n)
    rms_y = math.sqrt(sum((dy - cy)**2 for _, dy in spot_points) / n)
    rms_total = math.sqrt(sum((dx - cx)**2 + (dy - cy)**2 for dx, dy in spot_points) / n)
    return {
        'rms_x': rms_x,
        'rms_y': rms_y,
        'centroid_x': cx,
        'centroid_y': cy,
        'rms_total': rms_total,
    }


def _find_focal_z(rays_data, coord_key, slope_key, img_z, efl):
    """
    По вееру лучей найти z-позицию фокуса.
    rays_data: список словарей с координатами и наклонами
    coord_key: ключ координаты ('x' или 'y')
    slope_key: ключ наклона ('slope_x' или 'slope_y')
    """
    if len(rays_data) < 2:
        return img_z
    z_intersections = []
    for i in range(len(rays_data)):
        for j in range(i + 1, len(rays_data)):
            r1 = rays_data[i]
            r2 = rays_data[j]
            s1 = r1[slope_key]
            s2 = r2[slope_key]
            ds = s1 - s2
            if abs(ds) > 1e-12:
                v1 = r1[coord_key]
                v2 = r2[coord_key]
                z1 = r1['z']
                z2 = r2['z']
                z_int = (v2 - v1 - z2 * s2 + z1 * s1) / ds
                # Вес: ближе к зрачку - больше вес
                w = max(0.1, 1.0 - abs(r1['pupil'] + r2['pupil']) / 2)
                if abs(z_int - img_z) < abs(efl) * 3:  # sanity
                    z_intersections.append((z_int, w))
    if z_intersections:
        total_w = sum(w for _, w in z_intersections)
        return sum(z * w for z, w in z_intersections) / total_w if total_w > 0 else img_z
    return img_z


def compute_field_aberrations(system: OpticalSystem,
                               wl: float = 0.58756,
                               field_points: list = None,
                               num_fan_rays: int = 15
                              ) -> list:
    """
    Для каждой точки поля вычисляет внеосевые аберрации:
    - distortion: дисторсия (%)
    - astigmatism: Z'm - Z's (астигматизм, мм)
    - field_curvature: Z'm, Z's (кривизна поля, мм)
    - coma: кома (мм)

    Поле задано как угол в градусах; луч трассируется с наклоном
    в y-z плоскости (l=sin(angle)). Поэтому координата изображения
    по y = меридиональная, по x = сагиттальная.

    Возвращает: [{field_y, distortion, astigmatism, z_m, z_s, coma}, ...]
    """
    if field_points is None:
        field_points = [(fp.y,) for fp in system.field_points] if system.field_points else []
    if not field_points:
        return []

    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    efl = parax.get('focal_length', 0)

    # Z-позиции поверхностей
    z_pos = compute_z_positions(system)
    img_z = z_pos[-1]

    results = []

    # Temporarily increase semi_diameters so field rays can pass through
    # (LBO semi_diameters are often slightly underestimated)
    _orig_sds = [s.semi_diameter for s in system.surfaces]
    for s in system.surfaces:
        if s.semi_diameter > 0:
            s.semi_diameter = abs(s.semi_diameter) * 1.4

    for fp in field_points:
        field_y = fp[0] if isinstance(fp, (list, tuple)) else fp
        if field_y == 0:
            results.append({
                'field_y': 0.0,
                'distortion': 0.0,
                'astigmatism': 0.0,
                'z_m': 0.0,
                'z_s': 0.0,
                'coma': 0.0,
            })
            continue

        angle = math.radians(field_y)
        sin_a, cos_a = math.sin(angle), math.cos(angle)

        # ===== 1. Главный луч (через центр входного зрачка) =====
        # Используем входной зрачок из параксиального расчёта
        z_start, z_pupil = _compute_ray_start(system, parax)
        
        if system.object_type == ObjectType.INFINITE:
            chief_ray = make_field_ray(system, 0, 0, field_y, z_start, z_pupil)
        else:
            obj_z = -system.surfaces[0].thickness if system.surfaces else -50
            chief_ray = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

        chief_result = trace_ray_through_system(system, chief_ray, wl)
        if not chief_result.success or len(chief_result.path) < 2:
            results.append({'field_y': field_y, 'distortion': None,
                           'astigmatism': None, 'z_m': None, 'z_s': None, 'coma': None})
            continue

        chief_last = chief_result.path[-1]
        chief_y_img = chief_last[1]  # меридиональная координата (Y)

        # Параксиальная высота изображения (по Y)
        # Chief ray: l=+sin(angle) → идёт в +Y. Изображение в -Y (inverted).
        # Но луч идёт через систему и выходит в +Y → изображение inverted = +Y
        # На практике: chief_y_img имеет тот же знак, что и поле
        if abs(efl) > 0 and system.object_type == ObjectType.INFINITE:
            y_parax = efl * math.tan(angle)  # без минуса: chief ray +Y → image +Y
        else:
            y_parax = field_y

        # ===== 2. Меридиональный веер (в плоскости Y-Z, varying y_start) =====
        merid_rays = []
        for i in range(num_fan_rays):
            py = -1.0 + 2.0 * i / (num_fan_rays - 1)
            y_start = py * aperture / 2

            if system.object_type == ObjectType.INFINITE:
                # Лучи с полевым углом + смещение по Y — aim through entrance pupil
                ray = make_field_ray(system, 0, y_start, field_y, z_start, z_pupil)
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray = Ray(x=0, y=y_start + field_y, z=obj_z,
                         k=0, l=y_start / d, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            res = trace_ray_through_system(system, ray, wl)
            if res.success and len(res.path) >= 2:
                last = res.path[-1]
                prev = res.path[-2]
                dz = last[2] - prev[2]
                slope_y = (last[1] - prev[1]) / dz if abs(dz) > 1e-12 else 0
                merid_rays.append({'y': last[1], 'z': last[2],
                                   'slope_y': slope_y, 'pupil': py})

        # ===== 3. Сагиттальный веер (в плоскости X-Z, varying x_start) =====
        sag_rays = []
        for i in range(num_fan_rays):
            px = -1.0 + 2.0 * i / (num_fan_rays - 1)
            x_start = px * aperture / 2

            if system.object_type == ObjectType.INFINITE:
                # Сагиттальный луч: поле по Y, смещение по X — aim through entrance pupil
                ray = make_field_ray(system, x_start, 0, field_y, z_start, z_pupil)
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray = Ray(x=x_start, y=field_y, z=obj_z,
                         k=x_start / d, l=0, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            res = trace_ray_through_system(system, ray, wl)
            if res.success and len(res.path) >= 2:
                last = res.path[-1]
                prev = res.path[-2]
                dz = last[2] - prev[2]
                slope_x = (last[0] - prev[0]) / dz if abs(dz) > 1e-12 else 0
                sag_rays.append({'x': last[0], 'z': last[2],
                                 'slope_x': slope_x, 'pupil': px})

        # ===== 4. Фокальные расстояния =====
        z_m = _find_focal_z(merid_rays, 'y', 'slope_y', img_z, efl)
        z_s = _find_focal_z(sag_rays, 'x', 'slope_x', img_z, efl)

        delta_zm = z_m - img_z
        delta_zs = z_s - img_z
        astigmatism = delta_zm - delta_zs

        # ===== 5. Дисторсия =====
        distortion = ((chief_y_img - y_parax) / y_parax * 100.0) if abs(y_parax) > EPSILON else 0.0

        # ===== 6. Кома =====
        # Асимметрия меридионального веера: (y_upper + y_lower)/2 - y_chief
        coma = 0.0
        coma_pairs = 0
        for i in range(len(merid_rays)):
            for j in range(i + 1, len(merid_rays)):
                if abs(merid_rays[i]['pupil'] + merid_rays[j]['pupil']) < 0.15:
                    mid_y = (merid_rays[i]['y'] + merid_rays[j]['y']) / 2
                    coma += mid_y - chief_y_img
                    coma_pairs += 1
        if coma_pairs > 0:
            coma /= coma_pairs

        results.append({
            'field_y': field_y,
            'distortion': distortion,
            'astigmatism': astigmatism,
            'z_m': delta_zm,
            'z_s': delta_zs,
            'coma': coma,
        })

    # Restore original semi_diameters
    for i, s in enumerate(system.surfaces):
        s.semi_diameter = _orig_sds[i]

    return results


def compute_chief_ray_characteristics(system: OpticalSystem, wl: float = None) -> list:
    """
    Аберрации главных лучей для каждого field_point.

    Возвращает для каждого field_point:
    {
        'field_y': float,
        'distortion_abs': float,    # абсолютная дисторсия (мм)
        'distortion_rel': float,    # относительная дисторсия (%)
        'Zm': float,                # астигматический отрезок меридиональный (мм)
        'Zs': float,                # астигматический отрезок сагиттальный (мм)
        'lateral_color': float,     # хроматизм увеличения (мм)
        'lateral_color_pct': float, # хроматизм увеличения (%)
    }
    """
    if wl is None:
        wl = get_primary_wl(system)

    parax = paraxial_trace(system)
    efl = parax.get('focal_length', 0)

    # Z-позиции поверхностей
    z_pos = compute_z_positions(system)
    img_z = z_pos[-1]

    aperture = get_effective_aperture(system, default=10.0)

    results = []

    for fp in (system.field_points if system.field_points else [FieldPoint(0.0)]):
        field_y = fp.y

        if field_y == 0:
            results.append({
                'field_y': 0.0,
                'distortion_abs': 0.0,
                'distortion_rel': 0.0,
                'Zm': 0.0,
                'Zs': 0.0,
                'lateral_color': 0.0,
                'lateral_color_pct': 0.0,
            })
            continue

        angle = math.radians(field_y)
        sin_a, cos_a = math.sin(angle), math.cos(angle)

        # ===== Главный луч (через центр зрачка) =====
        z_start, z_pupil = _compute_ray_start(system, parax)
        if system.object_type == ObjectType.INFINITE:
            chief_ray = make_field_ray(system, 0, 0, field_y, z_start, z_pupil)
        else:
            obj_z = -system.surfaces[0].thickness if system.surfaces else -50
            chief_ray = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

        chief_result = trace_ray_through_system(system, chief_ray, wl)
        if not chief_result.success or len(chief_result.path) < 2:
            results.append({
                'field_y': field_y, 'distortion_abs': 0.0, 'distortion_rel': 0.0,
                'Zm': 0.0, 'Zs': 0.0, 'lateral_color': 0.0, 'lateral_color_pct': 0.0,
            })
            continue

        chief_last = chief_result.path[-1]
        chief_y_img = chief_last[1]  # меридиональная координата (Y в y-z плоскости)

        # Параксиальная высота изображения
        if abs(efl) > 0 and system.object_type == ObjectType.INFINITE:
            y_parax = efl * math.tan(angle)
        else:
            y_parax = field_y

        # ===== Дисторсия =====
        dist_abs = chief_y_img - y_parax
        dist_rel = (dist_abs / y_parax * 100.0) if abs(y_parax) > EPSILON else 0.0

        # ===== Астигматические отрезки Z'm, Z's =====
        # Через меридиональный и сагиттальный веера
        num_fan = 15

        # Меридиональный веер (в Y-Z плоскости, pupil в Y)
        merid_rays = []
        for i in range(num_fan):
            py = -1.0 + 2.0 * i / (num_fan - 1)
            y_start = py * aperture / 2
            if system.object_type == ObjectType.INFINITE:
                ray = make_field_ray(system, 0, y_start, field_y, z_start, z_pupil)
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray = Ray(x=0, y=y_start + field_y, z=obj_z, k=0, l=y_start / d, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm
            res = trace_ray_through_system(system, ray, wl)
            if res.success and len(res.path) >= 2:
                last = res.path[-1]
                prev = res.path[-2]
                dz = last[2] - prev[2]
                slope_y = (last[1] - prev[1]) / dz if abs(dz) > 1e-12 else 0
                merid_rays.append({'y': last[1], 'z': last[2], 'slope_y': slope_y, 'pupil': py})

        # Сагиттальный веер (в X-Z плоскости, pupil в X)
        sag_rays = []
        for i in range(num_fan):
            px = -1.0 + 2.0 * i / (num_fan - 1)
            x_start = px * aperture / 2
            if system.object_type == ObjectType.INFINITE:
                ray = make_field_ray(system, x_start, 0, field_y, z_start, z_pupil)
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray = Ray(x=x_start, y=field_y, z=obj_z, k=x_start / d, l=0, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm
            res = trace_ray_through_system(system, ray, wl)
            if res.success and len(res.path) >= 2:
                last = res.path[-1]
                prev = res.path[-2]
                dz = last[2] - prev[2]
                slope_x = (last[0] - prev[0]) / dz if abs(dz) > 1e-12 else 0
                sag_rays.append({'x': last[0], 'z': last[2], 'slope_x': slope_x, 'pupil': px})

        Zm = _find_focal_z(merid_rays, 'y', 'slope_y', img_z, efl) - img_z
        Zs = _find_focal_z(sag_rays, 'x', 'slope_x', img_z, efl) - img_z

        # ===== Хроматизм увеличения =====
        lateral_color = 0.0
        if len(system.wavelengths) >= 2:
            wl_ref = system.wavelengths[0].value
            wl_other = system.wavelengths[-1].value  # крайняя длина волны

            # Главный луч для другой длины волны
            if system.object_type == ObjectType.INFINITE:
                chief2 = make_field_ray(system, 0, 0, field_y, z_start, z_pupil)
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                chief2 = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

            chief2_result = trace_ray_through_system(system, chief2, wl_other)
            if chief2_result.success and chief2_result.path:
                chief2_y = chief2_result.path[-1][1]
                lateral_color = chief2_y - chief_y_img
                lateral_color_pct = (lateral_color / y_parax * 100.0) if abs(y_parax) > EPSILON else 0.0
            else:
                lateral_color_pct = 0.0
        else:
            lateral_color_pct = 0.0

        results.append({
            'field_y': field_y,
            'distortion_abs': dist_abs,
            'distortion_rel': dist_rel,
            'Zm': Zm,
            'Zs': Zs,
            'lateral_color': lateral_color,
            'lateral_color_pct': lateral_color_pct,
        })

    return results


def compute_focus_curve(system, wl=0.58756, num_points=40, defocus_range=2.0,
                        freq_lpmm=50.0, num_rays=30, field_y=0.0) -> list:
    """
    Фокусировочная кривая: MTF vs смещение плоскости изображения (Л1.7.4).

    Возвращает [(defocus_mm, mtf_value), ...]
    defocus_range: ±мм от лучшей фокальной плоскости
    freq_lpmm: частота для оценки MTF (лин/мм)

    Метод: трассируем лучи через систему, затем для каждого смещения
    propagated лучи до нужной z-плоскости и вычисляем RMS пятна → MTF.
    Автоматически находит лучшую фокальную плоскость через предварительный
    грубый поиск.
    """
    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)

    # Трассируем сетку лучей на зрачке - получаем позиции и направления
    # на выходе в плоскость изображения
    exit_rays = []  # [(x, y, z, kx, ky)]  - kx,ky = dx/dz, dy/dz

    for i in range(num_rays):
        for j in range(num_rays):
            px = -1.0 + 2.0 * i / (num_rays - 1) if num_rays > 1 else 0.0
            py = -1.0 + 2.0 * j / (num_rays - 1) if num_rays > 1 else 0.0

            if px**2 + py**2 > 1.0:
                continue

            y_start = py * aperture / 2
            x_start = px * aperture / 2

            ray = make_field_ray(system, x_start, y_start, field_y, z_start, z_pupil)

            result = trace_ray_through_system(system, ray, wl)

            if result.success and len(result.path) >= 2:
                last = result.path[-1]
                prev = result.path[-2]
                dz = last[2] - prev[2]
                if abs(dz) > 1e-12:
                    kx = (last[0] - prev[0]) / dz
                    ky = (last[1] - prev[1]) / dz
                    exit_rays.append((last[0], last[1], last[2], kx, ky))

    if not exit_rays:
        return []

    # Z-позиция номинальной плоскости изображения
    z_pos = compute_z_positions(system)
    img_z_nominal = z_pos[-1]

    def _rms_at_z(target_z):
        """Вычислить RMS пятна при заданной z-позиции."""
        xs, ys = [], []
        for (rx, ry, rz, kx, ky) in exit_rays:
            dz = target_z - rz
            xs.append(rx + kx * dz)
            ys.append(ry + ky * dz)
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        r2 = sum((x - cx)**2 + (y - cy)**2 for x, y in zip(xs, ys)) / len(xs)
        return math.sqrt(r2)

    # Фаза 1: грубый поиск лучшего фокуса
    # Ищем в широком диапазоне (до ±EFL или ±50мм)
    parax = paraxial_trace(system)
    efl = abs(parax.get('focal_length', 50))
    coarse_range = min(max(efl * 0.5, 10.0), 100.0)
    coarse_steps = 50
    best_z = img_z_nominal
    best_rms = float('inf')

    for ic in range(coarse_steps + 1):
        dz = -coarse_range + 2.0 * coarse_range * ic / coarse_steps
        z_test = img_z_nominal + dz
        rms = _rms_at_z(z_test)
        if rms < best_rms:
            best_rms = rms
            best_z = z_test

    # Фаза 2: тонкий скан вокруг найденного фокуса
    curve = []
    for ip in range(num_points):
        defocus = -defocus_range + 2.0 * defocus_range * ip / (num_points - 1) if num_points > 1 else 0.0
        target_z = best_z + defocus
        rms = _rms_at_z(target_z)

        # MTF - нормализованная оценка качества через RMS пятна
        # Аппроксимация: MTF ≈ 1/(1 + (π·σ·ν)2)
        # σ = RMS радиус (мм), ν = частота (лин/мм)
        mtf = 1.0 / (1.0 + (math.pi * rms * freq_lpmm)**2)
        mtf = max(0.0, min(1.0, mtf))

        curve.append((defocus, mtf))

    return curve


def compute_spot_diagram_polychromatic(sys: OpticalSystem,
                                         num_rays: int = 40,
                                         field_y: float = 0.0
                                         ) -> List[Tuple[float, float, int]]:
    """
    Полихроматическая точечная диаграмма.
    Трассирует лучи для каждой длины волны из system.wavelengths.

    Возвращает: список (x, y, wavelength_index) для каждой точки.
    """
    spots = []
    for wl_idx, wl in enumerate(sys.wavelengths):
        mono_spots = compute_spot_diagram(sys, wl=wl.value, num_rays=num_rays, field_y=field_y)
        for dx, dy in mono_spots:
            spots.append((dx, dy, wl_idx))
    return spots


def compute_polychromatic_rms(sys: OpticalSystem, num_rays: int = 30, field_y: float = None):
    """
    RMS пятна рассеяния по всем полям и длинам волн.
    Взвешенная сумма: sqrt(Σ(w_i * rms_i2) / Σ(w_i))
    """
    total_rms_sq = 0.0
    total_weight = 0.0

    fields = [field_y] if field_y is not None else [fp.y for fp in sys.field_points] if sys.field_points else [0.0]

    for wl in sys.wavelengths:
        wl_weight = wl.weight
        for fy in fields:
            fp_weight = 1.0
            if sys.field_points:
                for fp in sys.field_points:
                    if abs(fp.y - fy) < 1e-6:
                        fp_weight = fp.weight
                        break
            spots = compute_spot_diagram(sys, wl=wl.value, num_rays=num_rays, field_y=fy)
            if not spots:
                continue
            rms = compute_rms_spot(spots)
            w = wl_weight * fp_weight
            total_rms_sq += (rms ** 2) * w
            total_weight += w

    if total_weight == 0:
        return float('inf')

    return math.sqrt(total_rms_sq / total_weight)


def compute_spot_heatmap(system, wl=0.58756, num_rays=500, field_y=0.0, grid_size=100):
    """
    Топограмма плотности точек пятна рассеяния.

    1. Трассировать num_rays лучей → spot diagram (x, y)
    2. Создать grid_size × grid_size гистограмму
    3. Нормировать: максимум = 1.0

    Возвращает: (heatmap, x_range, y_range)
        heatmap: 2D массив (grid_size × grid_size), нормированный [0, 1]
        x_range: (x_min, x_max) в мм
        y_range: (y_min, y_max) в мм
    """
    import numpy as _np

    # Получаем точки пятна (сетка на зрачке)
    # Используем квадратную сетку num_rays × num_rays, отбираем внутри круга
    side = int(math.sqrt(num_rays))
    if side < 2:
        side = 2

    spots = compute_spot_diagram(system, wl=wl, num_rays=side, field_y=field_y)
    if not spots:
        empty = _np.zeros((grid_size, grid_size))
        return empty, (0.0, 0.0), (0.0, 0.0)

    xs = [dx for dx, dy in spots]
    ys = [dy for dx, dy in spots]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Добавляем небольшой запас
    margin_x = max((x_max - x_min) * 0.1, 1e-6)
    margin_y = max((y_max - y_min) * 0.1, 1e-6)
    x_min -= margin_x
    x_max += margin_x
    y_min -= margin_y
    y_max += margin_y

    # Делаем квадратную область
    x_range = x_max - x_min
    y_range = y_max - y_min
    max_range = max(x_range, y_range)
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    x_min = x_center - max_range / 2
    x_max = x_center + max_range / 2
    y_min = y_center - max_range / 2
    y_max = y_center + max_range / 2

    # Создаём гистограмму
    heatmap = _np.zeros((grid_size, grid_size), dtype=_np.float64)

    for dx, dy in spots:
        ix = int((dx - x_min) / (x_max - x_min) * (grid_size - 1))
        iy = int((dy - y_min) / (y_max - y_min) * (grid_size - 1))
        if 0 <= ix < grid_size and 0 <= iy < grid_size:
            heatmap[iy, ix] += 1.0

    # Нормируем
    max_val = heatmap.max()
    if max_val > 0:
        heatmap /= max_val

    return heatmap, (x_min, x_max), (y_min, y_max)


def compute_geometric_mtf(spots: List[Tuple[float, float]],
                           max_freq: float = 100.0,
                           num_freqs: int = 20) -> List[Tuple[float, float, float]]:
    """
    Геометрическая ЧКХ (Л1.6.7).
    Возвращает [(freq, MTF_tangential, MTF_sagittal), ...]

    Метод: FFT точечной диаграммы.
    1. Создать гистограмму точек на 2D сетке
    2. FFT → |FFT|2 = PSF
    3. FFT(PSF) → OTF → |OTF| = MTF
    """
    if not spots or len(spots) < 10:
        return []

    # Диапазон частот (лин/мм)
    freqs = [max_freq * i / num_freqs for i in range(num_freqs + 1)]

    # Размер сетки (степень двойки для FFT)
    N = 256

    # Определяем масштаб: размер поля в мм
    if not spots:
        return []

    dx_vals = [dx for dx, dy in spots]
    dy_vals = [dy for dx, dy in spots]

    max_range = max(
        max(abs(v) for v in dx_vals) if dx_vals else 0.001,
        max(abs(v) for v in dy_vals) if dy_vals else 0.001
    )
    max_range = max(max_range, 1e-6)

    # Поле: ±field_size мм
    field_size = max_range * 1.5  # с запасом
    pixel_size = 2 * field_size / N  # мм/пиксель

    # Создаём гистограмму (PSF)
    psf = [[0.0] * N for _ in range(N)]

    for dx, dy in spots:
        # Координаты в пикселях
        ix = int((dx + field_size) / pixel_size)
        iy = int((dy + field_size) / pixel_size)
        if 0 <= ix < N and 0 <= iy < N:
            psf[iy][ix] += 1.0

    # Нормализация
    total = sum(sum(row) for row in psf)
    if total < TINY:
        return [(f, 0.0, 0.0) for f in freqs]

    for iy in range(N):
        for ix in range(N):
            psf[iy][ix] /= total

    # FFT 2D — FFT PSF → OTF (numpy for performance)
    otf = _fft2d(np.asarray(psf))

    # |OTF| = MTF; нормализация: MTF(0) = 1
    mtf_abs = np.abs(otf)
    dc_val = mtf_abs[0, 0]
    if dc_val < TINY:
        dc_val = 1.0
    mtf_2d = mtf_abs / dc_val

    # Разрешение в частотах: df = 1 / (N * pixel_size) лин/мм
    df = 1.0 / (N * pixel_size)

    # Извлекаем MTF для заданных частот
    # Тангенциальная: срез по оси x (freq_x)
    # Сагиттальная: срез по оси y (freq_y)
    mtf_data = []
    half_N = N // 2

    for freq in freqs:
        if freq == 0:
            mtf_data.append((0, 1.0, 1.0))
            continue

        # Индекс в массиве для данной частоты
        # Частоты в FFT: 0..half_N-1 соответствуют 0..(half_N-1)*df
        # Потом half_N..N-1 - отрицательные частоты
        k = freq / df
        k_int = int(round(k))

        if k_int >= half_N:
            mtf_data.append((freq, 0.0, 0.0))
            continue

        # Тангенциальная: частота по оси x (горизонтальная)
        # MTF_t = mtf_2d[0, k_int]  - срез по y=0
        mtf_t = float(mtf_2d[0, k_int])

        # Сагиттальная: частота по оси y (вертикальная)
        # MTF_s = mtf_2d[k_int, 0]  - срез по x=0
        mtf_s = float(mtf_2d[k_int, 0])

        mtf_data.append((freq, max(0.0, mtf_t), max(0.0, mtf_s)))

    return mtf_data


def compute_spot_diagram_at_defocus(system, wl=0.58756, num_rays=100, field_y=0.0, defocus_mm=0.0):
    """
    Spot diagram со смещением плоскости изображения.
    defocus_mm > 0 = дальше от системы, < 0 = ближе.

    Метод: трассируем лучи, на выходе имеем (x, y, z, kx, ky),
    propagate каждый луч на целевую z-плоскость.
    Возвращает: [(dx, dy), ...] относительно центроида.
    """
    aperture = get_effective_aperture(system, default=10.0)
    parax_fc = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax_fc)

    # Z-позиции поверхностей
    z_pos = compute_z_positions(system)
    img_z = z_pos[-1]
    target_z = img_z + defocus_mm

    # Трассируем сетку лучей
    exit_rays = []  # [(x, y, z, kx, ky)]
    for i in range(num_rays):
        for j in range(num_rays):
            px = -1.0 + 2.0 * i / (num_rays - 1) if num_rays > 1 else 0.0
            py = -1.0 + 2.0 * j / (num_rays - 1) if num_rays > 1 else 0.0
            if px**2 + py**2 > 1.0:
                continue
            y_start = py * aperture / 2
            x_start = px * aperture / 2
            ray = make_field_ray(system, x_start, y_start, field_y, z_start, z_pupil)
            result = trace_ray_through_system(system, ray, wl)
            if result.success and len(result.path) >= 2:
                last = result.path[-1]
                prev = result.path[-2]
                dz = last[2] - prev[2]
                if abs(dz) > 1e-12:
                    kx = (last[0] - prev[0]) / dz
                    ky = (last[1] - prev[1]) / dz
                    exit_rays.append((last[0], last[1], last[2], kx, ky))

    if not exit_rays:
        return []

    # Propagate до target_z
    propagated = []
    for (rx, ry, rz, kx, ky) in exit_rays:
        dz = target_z - rz
        propagated.append((rx + kx * dz, ry + ky * dz))

    # Центроид
    n = len(propagated)
    cx = sum(dx for dx, dy in propagated) / n
    cy = sum(dy for dx, dy in propagated) / n

    return [(dx - cx, dy - cy) for dx, dy in propagated]


def _fft1d(data):
    """1D FFT wrapper. Uses numpy for performance."""
    return np.fft.fft(data)


def _fft2d(data2d):
    """2D FFT wrapper. Uses numpy for performance."""
    return np.fft.fft2(data2d)


def compute_isoplanatism(system, wl=0.58756, num_rays=20, field_y=0.0):
    """
    Вычислить неизопланатизм (нарушение изопланатизма).

    Неизопланатизм = разность между поперечной аберрацией реального луча
    и линейной аппроксимацией по полю.

    Для осевого пучка: η = Δy'_real(h) - Δy'_paraxial(h)
    где h - высота на зрачке.

    Параксиальная аппроксимация строится по линейной регрессии Δy'(h).

    Возвращает: (pupil_heights, isoplanatism_values_um)
    """
    fan = trace_aberration_fan(system, wl, num_rays=num_rays, field_y=field_y)

    # Собираем успешные лучи
    successful = [(r['pupil_y'], r['dy']) for r in fan if r['success']]
    if len(successful) < 3:
        return ([], [])

    # Линейная аппроксимация: Δy'_paraxial(h) = a * h + b
    # Используем все точки для линейной регрессии (least squares).
    n = len(successful)
    sum_h = sum(h for h, _ in successful)
    sum_dy = sum(dy for _, dy in successful)
    sum_h2 = sum(h * h for h, _ in successful)
    sum_hdy = sum(h * dy for h, dy in successful)

    denom = n * sum_h2 - sum_h * sum_h
    if abs(denom) < TINY:
        return ([], [])

    a = (n * sum_hdy - sum_h * sum_dy) / denom
    b = (sum_dy - a * sum_h) / n

    # Неизопланатизм = отклонение от линейной аппроксимации
    pupils = []
    iso_vals = []  # в мкм
    for h, dy in successful:
        dy_paraxial = a * h + b
        eta = (dy - dy_paraxial) * 1000.0  # мм -> мкм
        pupils.append(h)
        iso_vals.append(eta)

    return (pupils, iso_vals)


def compute_oblique_fan(system, wl=0.58756, num_rays=20, field_y=0.0, azimuth_deg=45.0):
    """
    Аберрации в косом сечении.
    azimuth_deg=0 → меридиональное, =90 → сагиттальное, =45 → косое.

    Возвращает: (pupil_heights, dy_mer_um, dy_sag_um)
        pupil_heights: list of float (-1..1)
        dy_mer_um: поперечная аберрация в меридиональной плоскости (мкм)
        dy_sag_um: поперечная аберрация в сагиттальной плоскости (мкм)
    """
    aperture = get_effective_aperture(system, default=10.0)
    az = math.radians(azimuth_deg)
    parax_of = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax_of)

    # Главный луч для определения центра
    if system.object_type == ObjectType.INFINITE:
        chief_ray = make_field_ray(system, 0, 0, field_y, z_start, z_pupil)
    else:
        obj_z = -system.surfaces[0].thickness if system.surfaces else -50
        chief_ray = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

    chief_result = trace_ray_through_system(system, chief_ray, wl)
    if not chief_result.success or not chief_result.path:
        return ([], [], [])
    chief_x = chief_result.path[-1][0]
    chief_y = chief_result.path[-1][1]

    pupil_heights = []
    dy_mer_um = []
    dy_sag_um = []

    for i in range(num_rays):
        h = -1.0 + 2.0 * i / (num_rays - 1) if num_rays > 1 else 0.0

        # Раскладываем зрачковую координату по меридиональному и сагиттальному направлениям
        # с учётом азимутального угла
        y_start = h * math.cos(az) * aperture / 2  # меридиональная компонента
        x_start = h * math.sin(az) * aperture / 2  # сагиттальная компонента

        if system.object_type == ObjectType.INFINITE:
            ray = make_field_ray(system, x_start, y_start, field_y, z_start, z_pupil)
        else:
            obj_z = -system.surfaces[0].thickness if system.surfaces else -50
            d = abs(obj_z)
            ray = Ray(x=x_start, y=y_start, z=obj_z,
                     k=x_start/d, l=(y_start - field_y)/d, m=1)
            norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
            ray.k /= norm; ray.l /= norm; ray.m /= norm

        result = trace_ray_through_system(system, ray, wl)

        if result.success and result.path:
            last = result.path[-1]
            dx = (last[0] - chief_x) * 1000  # мм -> мкм
            dy = (last[1] - chief_y) * 1000  # мм -> мкм
            pupil_heights.append(h)
            dy_mer_um.append(dy)
            dy_sag_um.append(dx)
        else:
            pupil_heights.append(h)
            dy_mer_um.append(None)
            dy_sag_um.append(None)

    return (pupil_heights, dy_mer_um, dy_sag_um)


def compute_ray_coordinates(system, wl=0.58756, field_y=0.0):
    """
    Координаты габаритных лучей на каждой поверхности.

    Возвращает: list of dicts:
    [
        {'surface': 0, 'x_upper': .., 'y_upper': .., 'z_upper': ..,
         'x_lower': .., 'y_lower': .., 'z_lower': ..,
         'x_chief': .., 'y_chief': .., 'z_chief': ..},
        ...
    ]
    """
    aperture = get_effective_aperture(system, default=10.0)
    parax_rc = paraxial_trace(system)
    z_start_rc, z_pupil_rc = _compute_ray_start(system, parax_rc)

    # Три луча: верхний, нижний, главный
    # Верхний луч (pupil_y = +1)
    y_up = aperture / 2
    # Нижний луч (pupil_y = -1)
    y_low = -aperture / 2

    def _make_ray(y_start, x_start=0.0):
        return make_field_ray(system, x_start, y_start, field_y, z_start_rc, z_pupil_rc)

    # Трассируем три луча
    upper_result = trace_ray_through_system(system, _make_ray(y_up), wl)
    lower_result = trace_ray_through_system(system, _make_ray(y_low), wl)
    chief_result = trace_ray_through_system(system, _make_ray(0.0), wl)

    # Определяем количество поверхностей + стартовая точка
    n_surfs = len(system.surfaces)
    # path содержит n_surfs+1 точку (начальная + на каждой поверхности)
    # Если есть толщина после последней поверхности, path может содержать ещё одну точку

    # Z-позиции поверхностей
    z_pos = compute_z_positions(system)

    results = []

    # Для каждой поверхности (включая плоскость изображения)
    max_points = max(
        len(upper_result.path) if upper_result.success else 0,
        len(lower_result.path) if lower_result.success else 0,
        len(chief_result.path) if chief_result.success else 0,
    )

    for i in range(max_points):
        entry = {'surface': i}

        if upper_result.success and i < len(upper_result.path):
            p = upper_result.path[i]
            entry['x_upper'] = p[0]
            entry['y_upper'] = p[1]
            entry['z_upper'] = p[2]
        else:
            entry['x_upper'] = None
            entry['y_upper'] = None
            entry['z_upper'] = None

        if lower_result.success and i < len(lower_result.path):
            p = lower_result.path[i]
            entry['x_lower'] = p[0]
            entry['y_lower'] = p[1]
            entry['z_lower'] = p[2]
        else:
            entry['x_lower'] = None
            entry['y_lower'] = None
            entry['z_lower'] = None

        if chief_result.success and i < len(chief_result.path):
            p = chief_result.path[i]
            entry['x_chief'] = p[0]
            entry['y_chief'] = p[1]
            entry['z_chief'] = p[2]
        else:
            entry['x_chief'] = None
            entry['y_chief'] = None
            entry['z_chief'] = None

        results.append(entry)

    return results


def compute_wavefront_rms_vs_field(system, wl=0.58756, num_rays=50, num_fields=10):
    """
    СКВ волновой аберрации по полю.

    Для каждой точки поля (0..max_field):
    1. Трассировать лучи
    2. Вычислить W (OPL-based)
    3. RMS = sqrt(mean(W2))

    Также: RMS за вычетом дефокуса, за вычетом наклона.

    Возвращает: (field_y_values, rms_wavelengths, rms_no_defocus, rms_no_tilt)
        rms_wavelengths: полное СКВ в длинах волн
        rms_no_defocus: СКВ после вычета наилучшего дефокуса (W2 = W - a*(2h2-1))
        rms_no_tilt: СКВ после вычета наилучшего наклона (W3 = W - b*h)
    """
    # Определяем диапазон поля
    if system.field_points:
        max_field = max(fp.y for fp in system.field_points)
    else:
        max_field = 0.0

    if max_field <= 0:
        max_field = 5.0  # градусов по умолчанию

    field_values = [max_field * i / max(num_fields - 1, 1) for i in range(num_fields)]

    rms_full = []
    rms_no_def = []
    rms_no_tilt = []

    for field_y in field_values:
        fan = trace_aberration_fan(system, wl, num_rays=num_rays, field_y=field_y)

        # Собираем W и зрачковые координаты
        pts = [(r['pupil_y'], r['wave']) for r in fan if r['success']]
        if len(pts) < 3:
            rms_full.append(float('nan'))
            rms_no_def.append(float('nan'))
            rms_no_tilt.append(float('nan'))
            continue

        hs = [h for h, _ in pts]
        ws = [w for _, w in pts]
        n = len(ws)

        # Полное СКВ
        mean_w2 = sum(w * w for w in ws) / n
        rms_full.append(math.sqrt(mean_w2))

        # За вычетом дефокуса: W' = W - a*(2*h2 - 1)
        # Минимизируем sum(W')2 по a
        # a = sum(W_i * f_i) / sum(f_i2),  f_i = 2*h_i2 - 1
        fs = [2 * h * h - 1 for h in hs]
        sum_wf = sum(w * f for w, f in zip(ws, fs))
        sum_f2 = sum(f * f for f in fs)
        if abs(sum_f2) > TINY:
            a_def = sum_wf / sum_f2
        else:
            a_def = 0.0
        ws_no_def = [w - a_def * f for w, f in zip(ws, fs)]
        rms_no_def.append(math.sqrt(sum(w * w for w in ws_no_def) / n))

        # За вычетом наклона (тильта): W'' = W - b*h
        # b = sum(W_i * h_i) / sum(h_i2)
        sum_wh = sum(w * h for w, h in zip(ws, hs))
        sum_h2 = sum(h * h for h in hs)
        if abs(sum_h2) > TINY:
            b_tilt = sum_wh / sum_h2
        else:
            b_tilt = 0.0
        ws_no_tilt = [w - b_tilt * h for w, h in zip(ws, hs)]
        rms_no_tilt.append(math.sqrt(sum(w * w for w in ws_no_tilt) / n))

    return (field_values, rms_full, rms_no_def, rms_no_tilt)
