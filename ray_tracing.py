"""
OPAL-OKB - Реальная трассировка лучей
Реальный луч через сферические и асферические поверхности с законом Снеллиуса
"""
import math
from typing import List, Tuple, Optional
from optics_engine import OpticalSystem, Surface, ObjectType, Wavelength, SurfaceType
from glass_catalog import compute_refractive_index
from optics_utils import get_effective_aperture


class Ray:
    """Луч в 3D пространстве."""
    def __init__(self, x=0.0, y=0.0, z=0.0, k=0.0, l=0.0, m=1.0):
        # Точка: (x, y, z), направление: (k, l, m) - единичный вектор
        self.x = x; self.y = y; self.z = z
        self.k = k; self.l = l; self.m = m

    def __repr__(self):
        return f"Ray(o=({self.x:.4f},{self.y:.4f},{self.z:.4f}), d=({self.k:.4f},{self.l:.4f},{self.m:.4f}))"


class TraceResult:
    """Результат трассировки луча через систему."""
    def __init__(self):
        self.path = []         # [(x, y, z)] - точки пересечения
        self.success = True
        self.error = None      # Ошибка ('TIR', 'MISS', 'EDGE')
        self.surfaces_hit = 0
        self.opl = 0.0         # оптическая длина пути (OPL)

    def add_point(self, x, y, z):
        self.path.append((x, y, z))


def intersect_aspheric(ray: Ray, R: float, z_surf: float,
                        conic_k: float = 0.0,
                        aspheric_coeffs: list = None,
                        max_iter: int = 20, tol: float = 1e-10) -> Optional[Tuple[float, float, float, float]]:
    """
    Пересечение луча с асферической поверхностью (итерационный метод Ньютона).

    Уравнение поверхности:
      z(r) = (c·r²)/(1 + √(1-(1+k)·c²·r²)) + A4·r⁴ + A6·r⁶ + A8·r⁸ + A10·r¹⁰
    где c = 1/R, r² = x² + y²

    Если k=0 и нет коэфф., сводится к сфере.
    """
    if aspheric_coeffs is None:
        aspheric_coeffs = []

    # Если это чистая сфера — используем быстрый аналитический метод
    if abs(conic_k) < 1e-15 and len(aspheric_coeffs) == 0:
        return intersect_sphere(ray, R, z_surf)

    # c = 1/R; для плоскости c=0
    c = 1.0 / R if abs(R) > 1e-10 else 0.0

    # Начальное приближение: пересечение с базовой сферой (или плоскостью)
    init = intersect_sphere(ray, R, z_surf)
    if init is None:
        return None
    x0, y0, z0, _ = init

    # Итерации Ньютона: находим точку на асферике ближе к лучу
    x, y, z = x0, y0, z0

    for _ in range(max_iter):
        r_sq = x * x + y * y
        r = math.sqrt(r_sq) if r_sq > 0 else 0.0

        # Асферический sag
        z_asph = z_surf  # вершина
        if abs(c) > 1e-15 and r_sq > 0:
            k1c_sq = (1.0 + conic_k) * c * c
            disc = 1.0 - k1c_sq * r_sq
            if disc < 0:
                disc = 0.0
            z_asph += c * r_sq / (1.0 + math.sqrt(disc))
        # Полиномиальные добавки
        r2 = r_sq
        for j, coeff in enumerate(aspheric_coeffs):
            power = 2 * (j + 2)  # A4->r⁴, A6->r⁶, ...
            z_asph += coeff * (r2 ** (power // 2))

        # Вектор от текущей точки до асферической поверхности
        dz = z_asph - z

        # Нормаль к асферике в точке (x, y, z_asph)
        # dz/dr = d/dr [c·r²/(1+√(1-(1+k)·c²·r²)) + Σ Ai·r^(2i+2)]
        dz_dr = 0.0
        if abs(c) > 1e-15 and r > 1e-15:
            k1c_sq = (1.0 + conic_k) * c * c
            disc = 1.0 - k1c_sq * r_sq
            if disc < 1e-15:
                disc = 1e-15
            sqrt_disc = math.sqrt(disc)
            dz_dr = c * r / sqrt_disc

        # Добавка от полинома: d/dr[A₄r⁴ + A₆r⁶ + ...] = 4A₄r³ + 6A₆r⁵ + ...
        for j, coeff in enumerate(aspheric_coeffs):
            exp = 2 * (j + 2)  # степень r в самом члене: 4, 6, 8, ...
            dz_dr += coeff * exp * (r ** (exp - 1)) if r > 1e-15 else 0.0

        # Нормаль: (-dz/dr * x/r, -dz/dr * y/r, 1), нормализованная
        if r > 1e-15:
            nx = -dz_dr * x / r
            ny = -dz_dr * y / r
        else:
            nx, ny = 0.0, 0.0
        nz = 1.0
        n_len = math.sqrt(nx * nx + ny * ny + nz * nz)
        if n_len > 1e-15:
            nx /= n_len; ny /= n_len; nz /= n_len

        # Коррекция: проецируем луч на асферику
        # ray direction: (k, l, m)
        # dot(normal, direction)
        dot_nd = nx * ray.k + ny * ray.l + nz * ray.m
        if abs(dot_nd) < 1e-15:
            break

        # Корректирующее смещение вдоль луча
        dt = (nx * (x - ray.x) + ny * (y - ray.y) + nz * (z - ray.z)) / dot_nd

        # Двигаем точку вдоль луча
        x = x + dt * ray.k
        y = y + dt * ray.l
        z = z + dt * ray.m

        # Пересчитываем z_asph для новых x,y
        r_sq = x * x + y * y
        r = math.sqrt(r_sq) if r_sq > 0 else 0.0
        z_asph_new = z_surf
        if abs(c) > 1e-15 and r_sq > 0:
            k1c_sq = (1.0 + conic_k) * c * c
            disc = 1.0 - k1c_sq * r_sq
            if disc < 0:
                disc = 0.0
            z_asph_new += c * r_sq / (1.0 + math.sqrt(disc))
        r2 = r_sq
        for j, coeff in enumerate(aspheric_coeffs):
            power = 2 * (j + 2)
            z_asph_new += coeff * (r2 ** (power // 2))
        
        # Snap z to surface
        z = z_asph_new

        if abs(dt) < tol:
            break

    t = math.sqrt((x - ray.x) ** 2 + (y - ray.y) ** 2 + (z - ray.z) ** 2)
    if t < 1e-10:
        return None

    return (x, y, z, t)


def surface_normal_aspheric(x: float, y: float, z: float,
                            R: float, z_surf: float,
                            conic_k: float = 0.0,
                            aspheric_coeffs: list = None) -> Tuple[float, float, float]:
    """
    Единичная нормаль к асферической поверхности в точке (x, y, z).
    """
    if aspheric_coeffs is None:
        aspheric_coeffs = []

    if abs(conic_k) < 1e-15 and len(aspheric_coeffs) == 0:
        return surface_normal(x, y, z, R, z_surf)

    c = 1.0 / R if abs(R) > 1e-10 else 0.0
    r_sq = x * x + y * y
    r = math.sqrt(r_sq) if r_sq > 0 else 0.0

    # dz/dr для конической части
    dz_dr = 0.0
    if abs(c) > 1e-15 and r > 1e-15:
        k1c_sq = (1.0 + conic_k) * c * c
        disc = 1.0 - k1c_sq * r_sq
        if disc < 1e-15:
            disc = 1e-15
        dz_dr = c * r / math.sqrt(disc)

    # dz/dr для полиномиальных членов: d/dr[A₄r⁴ + A₆r⁶ + ...] = 4A₄r³ + 6A₆r⁵ + ...
    for j, coeff in enumerate(aspheric_coeffs):
        exp = 2 * (j + 2)  # степень r в самом члене: 4, 6, 8, ...
        if r > 1e-15:
            dz_dr += coeff * exp * (r ** (exp - 1))

    if r > 1e-15:
        nx = -dz_dr * x / r
        ny = -dz_dr * y / r
    else:
        nx, ny = 0.0, 0.0
    nz = 1.0
    n_len = math.sqrt(nx * nx + ny * ny + nz * nz)
    if n_len > 1e-15:
        return (nx / n_len, ny / n_len, nz / n_len)
    return (0.0, 0.0, 1.0)


def intersect_sphere(ray: Ray, R: float, z_surf: float) -> Optional[Tuple[float, float, float, float]]:
    """
    Пересечение луча со сферической поверхностью.
    R > 0: центр справа от вершины
    R < 0: центр слева от вершины
    Возвращает (x, y, z, t) или None
    """
    if abs(R) < 1e-10:
        # Плоская поверхность
        if abs(ray.m) < 1e-15:
            return None
        t = (z_surf - ray.z) / ray.m
        x = ray.x + t * ray.k
        y = ray.y + t * ray.l
        return (x, y, z_surf, t)

    # Сфера с центром в (0, 0, z_surf + R)
    cx, cy, cz = 0.0, 0.0, z_surf + R

    dx = ray.x - cx
    dy = ray.y - cy
    dz = ray.z - cz

    a = ray.k**2 + ray.l**2 + ray.m**2  # = 1 для единичного вектора
    b = 2 * (dx * ray.k + dy * ray.l + dz * ray.m)
    c = dx**2 + dy**2 + dz**2 - R**2

    disc = b**2 - 4*a*c
    if disc < 0:
        return None

    sqrt_disc = math.sqrt(disc)
    t1 = (-b - sqrt_disc) / (2 * a)
    t2 = (-b + sqrt_disc) / (2 * a)

    # Выбираем пересечение:
    # - Если луч внутри сферы (c < 0): берём t2 (выход из сферы, ближе к вершине)
    # - Если луч снаружи: берём ближайшее положительное t
    if c < 0:
        # Внутри сферы - берём t2 (выход)
        t = t2
    else:
        # Снаружи - берём ближайшее t>0
        t = t1 if t1 > 1e-10 else t2

    if t < 1e-10:
        return None

    x = ray.x + t * ray.k
    y = ray.y + t * ray.l
    z = ray.z + t * ray.m

    return (x, y, z, t)


def refract(k, l, m, nx, ny, nz, n1, n2):
    """
    Преломление по закону Снеллиуса в векторной форме.
    (k,l,m) - единичный вектор направления луча
    (nx,ny,nz) - единичная нормаль к поверхности (в сторону падающего луча)
    n1, n2 - показатели преломления
    Возвращает (k', l', m') или None (TIR)
    """
    cos_i = -(k * nx + l * ny + m * nz)
    if cos_i < 0:
        # Нормаль направлена неправильно
        nx, ny, nz = -nx, -ny, -nz
        cos_i = -cos_i

    eta = n1 / n2
    sin2_t = eta**2 * (1 - cos_i**2)

    if sin2_t > 1.0:
        return None  # TIR

    cos_t = math.sqrt(1 - sin2_t)

    k_new = eta * k + (eta * cos_i - cos_t) * nx
    l_new = eta * l + (eta * cos_i - cos_t) * ny
    m_new = eta * m + (eta * cos_i - cos_t) * nz

    # Нормализация
    norm = math.sqrt(k_new**2 + l_new**2 + m_new**2)
    return (k_new/norm, l_new/norm, m_new/norm)


def surface_normal(x, y, z, R, z_surf):
    """
    Единичная нормаль к сферической поверхности в точке (x, y, z).
    Направлена от центра кривизны к точке.
    """
    if abs(R) < 1e-10:
        # Плоская: нормаль вдоль оси
        return (0.0, 0.0, 1.0)

    cx, cy, cz = 0.0, 0.0, z_surf + R
    nx = x - cx
    ny = y - cy
    nz = z - cz
    norm = math.sqrt(nx**2 + ny**2 + nz**2)
    if norm < 1e-15:
        return (0.0, 0.0, 1.0)
    return (nx/norm, ny/norm, nz/norm)


def trace_ray_through_system(sys: OpticalSystem, ray: Ray, wl: float = 0.58756) -> TraceResult:
    """
    Трассировка реального луча через оптическую систему.
    Возвращает TraceResult с путём луча.
    """
    result = TraceResult()
    result.add_point(ray.x, ray.y, ray.z)

    current_ray = Ray(ray.x, ray.y, ray.z, ray.k, ray.l, ray.m)
    
    # Z-координаты вершин поверхностей
    z_positions = [0.0]
    for i, s in enumerate(sys.surfaces):
        z_positions.append(z_positions[-1] + s.thickness)
    
    # Определяем показатель преломления среды, в которой луч начинает
    # (до первой поверхности — воздух/вакуум)
    current_n = compute_refractive_index("", wl)  # n среды перед системой
    
    # Параметры диафрагмы (aperture stop)
    stop_surf_idx = getattr(sys, 'stop_surface', -1)
    stop_offset = getattr(sys, 'stop_offset', 0.0)
    # Detect bogus aperture_value (F/# or NA stored instead of diameter)
    raw_aperture = getattr(sys, 'aperture_value', 0)
    if raw_aperture > 0 and raw_aperture < 1.0:
        # Likely F/# or normalized value; use max semi_diameter instead
        real_sd_vals = [s2.semi_diameter for s2 in sys.surfaces if s2.semi_diameter > raw_aperture]
        if real_sd_vals:
            raw_aperture = max(real_sd_vals) * 2.0
    stop_radius = raw_aperture / 2.0 if raw_aperture > 0 else 0
    # aperture_value = D (полный диаметр), stop_radius = D/2 = радиус
    # Z-позиция диафрагмы
    z_stop = None
    if 0 <= stop_surf_idx < len(z_positions):
        z_stop = z_positions[stop_surf_idx] + stop_offset
    
    for i, s in enumerate(sys.surfaces):
        z_surf = z_positions[i]
        
        # Проверка диафрагмы: если она между лучом и следующей поверхностью
        if z_stop is not None and z_stop > current_ray.z + 1e-10 and z_stop < z_surf - 1e-10:
            if abs(current_ray.m) > 1e-15:
                dt_stop = (z_stop - current_ray.z) / current_ray.m
                sx = current_ray.x + dt_stop * current_ray.k
                sy = current_ray.y + dt_stop * current_ray.l
                r_at_stop = math.sqrt(sx**2 + sy**2)
                if stop_radius > 0 and r_at_stop > stop_radius:
                    result.success = False
                    result.error = 'STOP'
                    result.add_point(sx, sy, z_stop)
                    result.opl += current_n * dt_stop
                    return result
                # Луч прошёл диафрагму — добавим точку
                result.add_point(sx, sy, z_stop)
                result.opl += current_n * dt_stop
                current_ray.x = sx
                current_ray.y = sy
                current_ray.z = z_stop
        R = s.radius if abs(s.radius) > 1e-10 else 0.0
        
        # Пересечение с поверхностью
        if s.surface_type != SurfaceType.SPHERE or abs(s.conic_constant) > 1e-15 or len(s.aspheric_coeffs) > 0:
            hit = intersect_aspheric(current_ray, R, z_surf,
                                     conic_k=s.conic_constant,
                                     aspheric_coeffs=s.aspheric_coeffs)
        else:
            hit = intersect_sphere(current_ray, R, z_surf)
        if hit is None:
            # If surface is behind the ray (e.g. virtual surface in mirror/laser systems),
            # skip it and continue tracing
            going_forward = current_ray.m > 0
            surface_behind = (z_surf < current_ray.z - 1e-6) if going_forward else (z_surf > current_ray.z + 1e-6)
            if surface_behind:
                # Skip this virtual surface — don't refract, just continue
                continue
            result.success = False
            result.error = 'MISS'
            return result
        
        hx, hy, hz, t = hit
        
        # Проверка полудиаметра
        # Skip EDGE check for bogus semi_diameters (decoder artifacts):
        # Real semi_diameters should be comparable to aperture, not tiny fractions.
        # If semi_diameter > 0 but < aperture/10, it's likely a decoder artifact.
        aperture = getattr(sys, 'aperture_value', 0) or 20.0
        if s.semi_diameter > 0 and s.semi_diameter < aperture / 10.0:
            semi_d = 1e6  # bogus semi_diameter — treat as unlimited
        else:
            semi_d = abs(s.semi_diameter) if s.semi_diameter > 0 else 1e6
        r_hit = math.sqrt(hx**2 + hy**2)
        if r_hit > semi_d:
            result.success = False
            result.error = 'EDGE'
            result.add_point(hx, hy, hz)
            # Накапливаем OPL до этой точки
            result.opl += current_n * t
            return result
        
        # Накапливаем OPL: n * геометрическое расстояние
        result.opl += current_n * t
        
        result.add_point(hx, hy, hz)
        result.surfaces_hit += 1
        
        # Обновляем позицию луча на точку попадания
        current_ray.x = hx
        current_ray.y = hy
        current_ray.z = hz
        
        # Нормаль
        if s.surface_type != SurfaceType.SPHERE or abs(s.conic_constant) > 1e-15 or len(s.aspheric_coeffs) > 0:
            nx, ny, nz = surface_normal_aspheric(hx, hy, hz, R, z_surf,
                                                  conic_k=s.conic_constant,
                                                  aspheric_coeffs=s.aspheric_coeffs)
        else:
            nx, ny, nz = surface_normal(hx, hy, hz, R, z_surf)
        
        # Показатели преломления
        if i == 0:
            n1 = compute_refractive_index("", wl)
        else:
            prev_s = sys.surfaces[i-1]
            n1 = compute_refractive_index(prev_s.glass, wl)
            # Check n_override on previous surface
            n_ov = getattr(prev_s, 'n_override', None)
            if n_ov:
                for wl_key, n_val in n_ov.items():
                    if abs(wl_key - wl) < 0.002:
                        n1 = n_val
                        break
        n2 = compute_refractive_index(s.glass, wl)
        n_ov2 = getattr(s, 'n_override', None)
        if n_ov2:
            for wl_key, n_val in n_ov2.items():
                if abs(wl_key - wl) < 0.002:
                    n2 = n_val
                    break
        
        # После преломления/отражения луч находится в среде с n2
        current_n = n2
        
        if s.is_reflective:
            # Отражение: среда не меняется, n остаётся прежним
            current_n = n1
            dot = current_ray.k * nx + current_ray.l * ny + current_ray.m * nz
            current_ray.k = current_ray.k - 2 * dot * nx
            current_ray.l = current_ray.l - 2 * dot * ny
            current_ray.m = current_ray.m - 2 * dot * nz
        else:
            # Преломление
            ref = refract(current_ray.k, current_ray.l, current_ray.m,
                         nx, ny, nz, n1, n2)
            if ref is None:
                result.success = False
                result.error = 'TIR'
                return result
            current_ray.k, current_ray.l, current_ray.m = ref
    
    # После последней поверхности — propagate до плоскости изображения
    if sys.surfaces:
        last = sys.surfaces[-1]
        if last.thickness != 0 and abs(current_ray.m) > 1e-15:
            img_z = z_positions[-1]
            dt = (img_z - current_ray.z) / current_ray.m
            ix = current_ray.x + dt * current_ray.k
            iy = current_ray.y + dt * current_ray.l
            # OPL от последней поверхности до плоскости изображения
            result.opl += current_n * dt
            result.add_point(ix, iy, img_z)
    
    return result


def trace_fan(sys: OpticalSystem, num_rays: int = 7,
              pupil_range: float = 1.0, wl: float = 0.58756,
              field_y: float = 0.0) -> List[TraceResult]:
    """
    Трассировка веера лучей (fan) в меридиональной плоскости.
    num_rays: количество лучей
    pupil_range: диапазон зрачка (0..1)
    field_y: смещение по полю (мм или градусы)
    Лучи с |ρ| < obscuration_ratio отсекаются (центральное экранирование).
    """
    obscuration = getattr(sys, 'obscuration_ratio', 0.0)
    aperture = get_effective_aperture(sys, default=10.0)

    # Auto-reduce: if aperture_value looks like F/# or NA (very small),
    # estimate real aperture from max semi_diameter
    if aperture < 1.0:
        # semi_diameters may also be normalized/bogus
        # Only trust sd values that are reasonable (> 1.0 mm)
        real_sd = [s2.semi_diameter for s2 in sys.surfaces if s2.semi_diameter > 1.0]
        if real_sd:
            aperture = max(real_sd) * 1.2
        else:
            # semi_diameters also bogus — compute from NA and focal length
            from optics_engine import paraxial_trace as _pt
            _efl = _pt(sys).get('focal_length', 0)
            if _efl and abs(_efl) > 0.1:
                # aperture is NA → D = 2*NA*f'
                aperture = 2.0 * aperture * abs(_efl)
            else:
                aperture = 20.0  # last resort

    def _do_trace(pr):
        """Trace num_rays with given pupil_range, return list of TraceResult."""
        res = []
        for i in range(num_rays):
            py = -pr + 2 * pr * i / (num_rays - 1) if num_rays > 1 else 0.0

            # Проверка экранирования: |ρ| < obscuration_ratio → луч блокируется
            if obscuration > 0 and abs(py) < obscuration:
                blocked = TraceResult()
                blocked.success = False
                blocked.error = 'OBSCURED'
                res.append(blocked)
                continue

            y_start = py * aperture / 2

            if sys.object_type == ObjectType.INFINITE:
                angle = math.radians(field_y) if field_y != 0 else 0.0
                sin_a, cos_a = math.sin(angle), math.cos(angle)
                # Use entrance pupil position from paraxial trace
                from optics_engine import paraxial_trace as _pt
                _parax = _pt(sys)
                sP = _parax.get('sP', 0)
                z_pupil = sP
                z_start = -max(abs(z_pupil), 10.0) - 5.0
                dz = z_pupil - z_start
                if cos_a > 1e-10:
                    y_at_start = y_start - dz * sin_a / cos_a
                else:
                    y_at_start = y_start
                ray = Ray(x=0, y=y_at_start, z=z_start, k=0, l=sin_a, m=cos_a)
            else:
                from optics_engine import paraxial_trace
                parax = paraxial_trace(sys)
                sF = parax.get('sF', 0)
                obj_dist = abs(sF) if sF and abs(sF) > 1e-6 else 100.0
                obj_y = field_y
                ray = Ray(x=0, y=obj_y, z=-obj_dist,
                         k=0, l=y_start - obj_y, m=obj_dist)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            res.append(trace_ray_through_system(sys, ray, wl))
        return res

    results = _do_trace(pupil_range)

    # Auto-reduce: if all rays failed with EDGE or MISS, try smaller pupil_range
    edge_count = sum(1 for r in results if r.error == 'EDGE')
    miss_count = sum(1 for r in results if r.error == 'MISS')
    ok_count = sum(1 for r in results if r.success)
    if ok_count == 0 and (edge_count > 0 or miss_count > 0):
        for reduction in [0.3, 0.1, 0.03, 0.01, 0.003]:
            if reduction >= pupil_range:
                continue
            results = _do_trace(reduction)
            ok_count = sum(1 for r in results if r.success)
            if ok_count > 0:
                break

    return results


def trace_grid_3d(sys: OpticalSystem, num_rings: int = 3, num_azimuths: int = 8,
                   wl: float = 0.546, field_y: float = 0.0) -> List[List['TraceResult']]:
    """
    3D ray tracing: generate a grid of rays across the entrance pupil.
    
    For each ring (0..num_rings-1) and each azimuthal position (0..num_azimuths-1),
    create a ray that passes through that point in the entrance pupil.
    
    Returns List[List[TraceResult]] - outer list per ring, inner list per azimuth.
    """
    # Compute aperture radius
    aperture = get_effective_aperture(sys, default=20.0)
    # Detect bogus aperture_value (F/# or NA stored instead of diameter)
    real_sd = [s.semi_diameter for s in sys.surfaces if s.semi_diameter > aperture / 10.0]
    if aperture < 1.0 and real_sd:
        aperture = max(real_sd) * 2.0
    pupil_radius = aperture / 2.0
    
    # Compute z-position of entrance pupil (approximately at stop surface + offset)
    stop_idx = getattr(sys, 'stop_surface', 1)
    stop_off = getattr(sys, 'stop_offset', 0.0)
    z_pupil = 0.0
    for j in range(min(stop_idx, len(sys.surfaces))):
        z_pupil += sys.surfaces[j].thickness
    z_pupil += stop_off
    
    # For infinite object: field angle
    is_infinite = (sys.object_type == ObjectType.INFINITE)
    angle = math.radians(field_y) if (is_infinite and field_y != 0) else 0.0
    
    # Starting z position (before the system)
    z_start = -1.0 if is_infinite else z_pupil - 1.0
    
    results = []
    
    for ring in range(num_rings):
        # ring 0 = center, then increasing radii
        if num_rings == 1:
            r = 0.0
        else:
            r = (ring + 1) / num_rings * pupil_radius
        
        # Special case: ring 0 with r=0 is just a single ray at center
        if ring == 0 and num_rings > 1:
            # Include center ray
            ring_results = []
            if is_infinite:
                # Ray starts at z_start, aimed at (0, 0) at z_pupil with field angle
                # For on-axis (field_y=0): ray goes straight along z
                # For off-axis: ray has tilt
                dz = z_pupil - z_start
                y_at_start = -dz * math.sin(angle) / math.cos(angle) if abs(math.cos(angle)) > 1e-10 else 0.0
                ray = Ray(x=0, y=y_at_start, z=z_start,
                         k=math.sin(angle) if field_y != 0 else 0.0,
                         l=0.0,
                         m=math.cos(angle) if field_y != 0 else 1.0)
            else:
                from optics_engine import paraxial_trace
                parax = paraxial_trace(sys)
                sF = parax.get('sF', 0)
                obj_dist = abs(sF) if sF and abs(sF) > 1e-6 else 100.0
                obj_y = field_y
                ray = Ray(x=0, y=obj_y, z=-obj_dist,
                         k=0, l=0.0 - obj_y, m=obj_dist)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm
            
            ring_results.append(trace_ray_through_system(sys, ray, wl))
            results.append(ring_results)
            continue
        
        ring_results = []
        for az in range(num_azimuths):
            az_angle = 2 * math.pi * az / num_azimuths
            px = r * math.cos(az_angle)
            py = r * math.sin(az_angle)
            
            if is_infinite:
                # Ray must pass through (px, py) at z_pupil
                # Direction has tilt from field angle
                # The ray starts at z_start, and at z_pupil it should be at (px, py)
                # For field angle in Y direction: direction = (0, sin(angle), cos(angle))
                # But we need the ray to hit (px, py) at z_pupil
                # Start position: at z_start, the ray is at:
                #   x = px (no x-field angle)
                #   y = py - dz * sin(angle)/cos(angle)
                dz = z_pupil - z_start
                y_at_start = py - dz * math.sin(angle) / math.cos(angle) if abs(math.cos(angle)) > 1e-10 else py
                
                ray = Ray(x=px, y=y_at_start, z=z_start,
                         k=0.0,
                         l=math.sin(angle) if field_y != 0 else 0.0,
                         m=math.cos(angle) if field_y != 0 else 1.0)
            else:
                from optics_engine import paraxial_trace
                parax = paraxial_trace(sys)
                sF = parax.get('sF', 0)
                obj_dist = abs(sF) if sF and abs(sF) > 1e-6 else 100.0
                obj_y = field_y
                # Aim from object point to pupil point
                dx = px - 0.0
                dy = py - obj_y
                dz_val = z_pupil - (-obj_dist)
                ray = Ray(x=0, y=obj_y, z=-obj_dist,
                         k=dx, l=dy, m=dz_val)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm
            
            ring_results.append(trace_ray_through_system(sys, ray, wl))
        
        results.append(ring_results)
    
    return results


def get_focal_spot(sys: OpticalSystem, wl: float = 0.58756, num_rays: int = 20) -> List[Tuple[float, float]]:
    """
    Точечная диаграмма в фокальной плоскости (Л1.6.1 Точечная диаграмма).
    Возвращает список (dx, dy) - отклонения от главного луча.
    """
    # Найдём фокальную плоскость через параксиальный расчёт
    from optics_engine import paraxial_trace
    parax = paraxial_trace(sys)
    bfd = parax.get('back_focal_distance', 0)

    if bfd == 0:
        return []

    # Трассировка веера лучей
    rays_y = trace_fan(sys, num_rays=num_rays, pupil_range=1.0, wl=wl, field_y=0.0)

    spots = []
    for r in rays_y:
        if r.success and len(r.path) > 1:
            last = r.path[-1]
            spots.append((last[0], last[1]))

    return spots
