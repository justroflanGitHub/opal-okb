"""
OPAL-OKB Windows 10 — Core Optical Engine
Based on reverse-engineered OPAL-PC specification

Optical system data model + paraxial ray tracing + Seidel aberrations
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_catalog import compute_refractive_index


class SurfaceType(Enum):
    SPHERE = 0        # Сферическая
    CONIC = 1         # Коническая (параболоид, эллипсоид, гиперболоид)
    ASPHERIC = 2      # Асферическая (полином)
    HOLOGRAM = 3      # ГОЭ (голограммный оптический элемент)
    GRATING = 4       # Дифракционная решётка
    TOROIDAL = 5      # Торическая


class ObjectType(Enum):
    FINITE = 1         # Предмет на конечном расстоянии (OB=1)
    INFINITE = 0       # Предмет в бесконечности (OB=0)


class ApertureType(Enum):
    ENTRANCE_PUPIL = 0    # Входной зрачок (диаметр)
    NUMERICAL_APERTURE = 1  # Числовая апертура
    F_NUMBER = 2          # Относительное отверстие (F/#)


@dataclass
class Surface:
    """Одна оптическая поверхность."""
    radius: float = 0.0          # Радиус кривизны (мм), 0 = плоскость
    thickness: float = 0.0       # Расстояние до следующей поверхности (мм)
    glass: str = ""              # Марка стекла или код среды
    semi_diameter: float = 0.0   # Полудиаметр (мм)
    surface_type: SurfaceType = SurfaceType.SPHERE
    conic_constant: float = 0.0  # Коническая постоянная (для CONIC)
    aspheric_coeffs: List[float] = field(default_factory=list)  # Асферические коэфф.
    is_reflective: bool = False   # Зеркальная поверхность?
    # Деформация (для SPTDEF)
    deformation_coeffs: List[float] = field(default_factory=list)
    # ГОЭ параметры
    hologram_order: float = 1.0
    hologram_wavelength: float = 0.6328  # мкм
    hologram_coeffs: List[float] = field(default_factory=list)
    # Override refractive index (if set, used instead of glass_catalog)
    n_override: dict = field(default_factory=dict)  # {wl_value: n}


@dataclass
class Wavelength:
    """Длина волны."""
    value: float          # мкм
    weight: float = 1.0   # Вес при оптимизации
    name: str = ""


@dataclass
class FieldPoint:
    """Точка поля (внеосевой пучок)."""
    y: float = 0.0       # Угловое поле (градусы) или высота (мм)
    x: float = 0.0       # Для 2D поля
    weight: float = 1.0
    # Параметры зрачка
    pupil_y: float = 1.0
    pupil_x: float = 0.0


@dataclass
class GlassCatalogEntry:
    """Запись в каталоге стёкол."""
    name: str
    nd: float           # Показатель преломления для d-линии (0.58756 мкм)
    ne: float           # Показатель преломления для e-линии (0.54607 мкм)
    vd: float           # Коэффициент дисперсии (Abbe) для d
    ve: float           # Коэффициент дисперсии для e
    # Коэффициенты дисперсионной формулы (Sellmeier / Herzberger)
    coeffs: List[float] = field(default_factory=list)
    # Ограничения
    transmission: dict = field(default_factory=dict)  # wavelength -> %


@dataclass
class OpticalSystem:
    """Полная оптическая система."""
    name: str = ""
    # Предмет
    object_type: ObjectType = ObjectType.INFINITE
    object_height: float = 0.0     # мм (для FINITE) или градусы (для INFINITE)
    object_distance: float = 0.0   # мм — расстояние от предмета до первой поверхности (для FINITE)
    # Поверхности
    surfaces: List[Surface] = field(default_factory=list)
    # Апертура
    aperture_type: ApertureType = ApertureType.ENTRANCE_PUPIL
    aperture_value: float = 0.0
    # Длины волн (до 5)
    wavelengths: List[Wavelength] = field(default_factory=list)
    # Точки поля (до 5)
    field_points: List[FieldPoint] = field(default_factory=list)
    # Стоп-поверхность (апертурная диафрагма)
    stop_surface: int = 1
    # Экранирование
    obscuration_ratio: float = 0.0  # 0 = нет экранирования, 0.3 = 30% центральное
    # Режимы расчёта габаритов (#15)
    beam_mode: str = "real"  # "real" | "given"
    sharp_edge: bool = True
    # Примечания
    comment: str = ""

    @property
    def num_surfaces(self) -> int:
        return len(self.surfaces)

    @property
    def image_index(self) -> int:
        return len(self.surfaces) - 1


# ============================================================
# Оптические расчёты
# ============================================================

def apply_vignetting(system: OpticalSystem, field_y: float, ray_y: float, ray_x: float = 0.0) -> bool:
    """
    Проверить виньетирование луча.
    Луч виньетируется если на любой поверхности полудиаметр луча
    превышает semi_diameter этой поверхности.
    
    Возвращает True если луч виньетирован (отсекается),
    False если луч проходит.
    """
    if not system.surfaces:
        return False
    
    # Z-позиции
    z_pos = [0.0]
    for s in system.surfaces:
        z_pos.append(z_pos[-1] + s.thickness)
    
    wl = system.wavelengths[0].value if system.wavelengths else 0.58756
    
    # Начальные параметры луча
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        y = ray_y
        z = -50.0
        k = math.sin(angle)
        l = 0.0
        m = math.cos(angle)
    else:
        y = field_y
        z = -system.surfaces[0].thickness if system.surfaces else -50
        k = 0.0
        l = (ray_y - field_y) / abs(z) if abs(z) > 1e-10 else 0.0
        m = 1.0
        norm = math.sqrt(k**2 + l**2 + m**2)
        k /= norm; l /= norm; m /= norm
    
    x = ray_x
    
    # Трассируем через поверхности, проверяя полудиаметр
    for i, s in enumerate(system.surfaces):
        R = s.radius if abs(s.radius) > 1e-10 else 0.0
        z_surf = z_pos[i]
        
        if abs(m) < 1e-15:
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
            t = t1 if t1 > 1e-10 else t2
            if t < 1e-10:
                return True
        
        y_new = y + t * l
        x_new = x + t * k
        z_new = z + t * m
        
        # Проверка полудиаметра
        sd = s.semi_diameter if s.semi_diameter > 0 else 1e6
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
            if norm > 1e-15:
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


def paraxial_trace(sys: OpticalSystem, catalog: dict = None) -> dict:
    """
    Параксиальный расчёт оптической системы.
    Возвращает полный набор кардинальных отрезков и характеристик.
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

    wl_primary = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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
            n_medium.append(refractive_index(s.glass, wl_primary, catalog, getattr(s, 'n_override', None)))

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

    if abs(nu_last) > 1e-15:
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

        # f/# и входной зрачок
        epd = sys.aperture_value if sys.aperture_value > 0 else abs(efl) / 4.0
        if sys.aperture_type == ApertureType.ENTRANCE_PUPIL:
            results['entrance_pupil_diameter'] = epd
        elif sys.aperture_type == ApertureType.F_NUMBER:
            results['entrance_pupil_diameter'] = abs(efl) / epd if epd > 0 else 0.0
        elif sys.aperture_type == ApertureType.NUMERICAL_APERTURE:
            results['entrance_pupil_diameter'] = 2.0 * abs(efl) * epd  # D = 2*f'*NA

        f_number = abs(efl) / results['entrance_pupil_diameter'] if results['entrance_pupil_diameter'] > 0 else 0.0
        results['f_number'] = f_number

    # ===== Положение зрачков (sP, sP') =====
    stop_idx = max(0, min(sys.stop_surface - 1, ns - 1))  # 0-based

    # Обратная трассировка от стопа к первой поверхности
    yb = [0.0] * (ns + 1)
    nub = [0.0] * (ns + 1)
    yb[stop_idx] = 0.0
    nub[stop_idx] = 1.0

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

    # Прямая трассировка от стопа к последней поверхности
    for i in range(stop_idx, ns):
        s = sys.surfaces[i]
        R = s.radius if s.radius != 0 else 1e15
        n1 = n_medium[i]
        n2 = n_medium[i + 1]
        if R != 1e15:
            nub[i] = nub[i] - yb[i] * (n2 - n1) / R
        else:
            pass
        if i < ns - 1:
            d = s.thickness
            yb[i + 1] = yb[i] + nub[i] * d / n_medium[i + 1]
            nub[i + 1] = nub[i]
        else:
            d = s.thickness
            yb[ns] = yb[i] + nub[i] * d / n_medium[ns]

    # Входной зрачок: расстояние от первой поверхности
    sP = 0.0
    if abs(nub[0]) > 1e-15:
        sP = -yb[0] / nub[0]
    results['sP'] = sP
    results['entrance_pupil'] = sP

    # Выходной зрачок: расстояние от последней поверхности
    sP_prime = 0.0
    nu_exit = nub[ns - 1] if ns > 0 else 0.0
    if abs(nu_exit) > 1e-15:
        sP_prime = -yb[ns] / nu_exit
    results['sP_prime'] = sP_prime
    results['exit_pupil'] = sP_prime
    results['pupil_location'] = sP_prime

    # ===== Обобщённое увеличение V =====
    if sys.object_type == ObjectType.FINITE and abs(sys.object_height) > 1e-10:
        # Для конечного предмета: V = s'/s
        # Параксиальное увеличение через кардинальные отрезки
        # Упрощённо: используем nu_last для оценки
        if abs(nu_last) > 1e-15:
            obj_dist = sys.surfaces[0].thickness if sys.surfaces else 0.0
            if abs(obj_dist) > 1e-10:
                # V = f' / (s - f') where s = -obj_dist
                efl = results.get('focal_length', 0)
                s_val = -obj_dist
                if abs(s_val - (-efl)) > 1e-10:
                    results['V'] = efl / (s_val + efl)
                    results['magnification'] = results['V']
    else:
        # Для бесконечного предмета V = 0 (в информационном плане)
        results['V'] = 0.0
        results['magnification'] = 0.0

    return results


def compute_beam_geometry(system: OpticalSystem, wl: float = None) -> list:
    """
    Вычислить габариты пучков для всех полей.

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
    if wl is None:
        wl = system.wavelengths[0].value if system.wavelengths else 0.58756

    aperture = system.aperture_value if system.aperture_value > 0 else 10.0
    parax = paraxial_trace(system)
    efl = parax.get('focal_length', 0)
    fno = parax.get('f_number', 0)

    results = []

    for fp in (system.field_points if system.field_points else [FieldPoint(0.0)]):
        field_y = fp.y

        # Трассируем меридиональный веер для определения габаритов
        # Верхний луч (pupil_y = +1), нижний луч (pupil_y = -1), сагиттальный (pupil_x = +1)

        upper_y_start = aperture / 2.0
        lower_y_start = -aperture / 2.0
        sag_x_start = aperture / 2.0

        # Z-позиции поверхностей
        z_pos = [0.0]
        for s in system.surfaces:
            z_pos.append(z_pos[-1] + s.thickness)

        def _trace_marginal_ray(y_start, x_start, field_y_val):
            """Трассировка габаритного луча, возвращает (y_img, x_img, success, max_clear_aperture)"""
            if system.object_type == ObjectType.INFINITE:
                angle = math.radians(field_y_val) if field_y_val != 0 else 0.0
                ray_y = y_start
                ray_x = x_start
                k = math.sin(angle)
                l = 0.0
                m = math.cos(angle)
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray_y = y_start
                ray_x = x_start
                k = x_start / d if d > 0 else 0.0
                l = (y_start - field_y_val) / d if d > 0 else 0.0
                m = 1.0
                norm = math.sqrt(k**2 + l**2 + m**2)
                if norm > 1e-15:
                    k /= norm; l /= norm; m /= norm

            success = True
            last_y = 0.0
            last_x = 0.0
            z = -50.0 if system.object_type == ObjectType.INFINITE else (z_pos[0] - abs(system.surfaces[0].thickness) if system.surfaces else -50)
            y = ray_y
            x = ray_x

            for i, s in enumerate(system.surfaces):
                R = s.radius if abs(s.radius) > 1e-10 else 0.0
                z_surf = z_pos[i]

                if abs(m) < 1e-15:
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
                    t = t1 if t1 > 1e-10 else t2
                    if t < 1e-10:
                        success = False
                        break

                y_new = y + t * l
                x_new = x + t * k
                z_new = z + t * m

                # Проверка виньетирования
                sd = s.semi_diameter if s.semi_diameter > 0 else 1e6
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
                    if norm > 1e-15:
                        k, l = k_new / norm, l_new / norm

                y, x, z = y_new, x_new, z_new

            last_y = y
            last_x = x
            return last_y, last_x, success

        # Верхний луч
        uy, ux, upper_ok = _trace_marginal_ray(upper_y_start, 0.0, field_y)
        # Нижний луч
        ly, lx, lower_ok = _trace_marginal_ray(lower_y_start, 0.0, field_y)
        # Сагиттальный луч
        sy, sx, sag_ok = _trace_marginal_ray(0.0, sag_x_start, field_y)
        # Главный луч
        cy, cx, chief_ok = _trace_marginal_ray(0.0, 0.0, field_y)

        # Передние апертуры — полуширина пучка на входе
        Ax = aperture / 2.0  # сагиттальная
        Ay = aperture / 2.0  # меридиональная

        # Задние апертуры — через f/# и поле
        Ax_prime = 0.0
        Ay_prime = 0.0
        if abs(efl) > 1e-10 and fno > 0:
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
                for _ in range(20):
                    mid = (lo + hi) / 2.0
                    y_test = sign * mid * aperture / 2.0
                    _, _, ok = _trace_marginal_ray(y_test, 0.0, field_y)
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
    wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Преломляющий инвариант: A = nu[i+1] - nu[i]  (nu = n*u)
        A = nu[i + 1] - nu[i]
        A_bar = nub[i + 1] - nub[i]
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
        if abs(A) > 1e-15:
            SV += (A_bar ** 3 / A) * h * delta_n_inv
        SV += 3.0 * A_bar * A_bar * h * delta_n_inv

    return {'SI': SI, 'SII': SII, 'SIII': SIII, 'SIV': SIV, 'SV': SV}


def create_demo_system() -> OpticalSystem:
    """Создать демо-систему: тонкая линза f'≈77мм"""
    sys = OpticalSystem(
        name="Демо: Тонкая линза",
        object_type=ObjectType.INFINITE,
        object_height=5.0,
    )
    sys.wavelengths = _std_wavelengths()
    sys.field_points = [FieldPoint(0.0), FieldPoint(3.0), FieldPoint(5.0)]
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=50.0, thickness=5.0, glass="К8", semi_diameter=12.0),
        Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0),
    ]
    sys.stop_surface = 1
    return sys


def _std_wavelengths():
    """Стандартный набор длин волн: e, G', C."""
    return [
        Wavelength(0.54607, 1.0, "e"),
        Wavelength(0.43405, 1.0, "G'"),
        Wavelength(0.65627, 1.0, "C"),
    ]


def _std_fields(*angles):
    return [FieldPoint(a) for a in angles]


def create_demo_system_by_name(name: str) -> OpticalSystem:
    """Создать демо-систему по имени."""
    systems = {
        "achromat": _demo_achromat,
        "cook_doublet": _demo_cook_doublet,
        "telephoto": _demo_telephoto,
        "petzval": _demo_petzval,
        "mirror": _demo_mirror,
        "meniscus": _demo_meniscus,
        "plano_convex": _demo_plano_convex,
    }
    fn = systems.get(name, create_demo_system)
    return fn()


def _demo_achromat() -> OpticalSystem:
    """Ахроматический дублет f'≈100мм, К8+ТФ1."""
    sys = OpticalSystem(name="Ахромат К8+ТФ1", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0, 5.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=62.0, thickness=6.0, glass="К8", semi_diameter=12.0),
        Surface(radius=-44.0, thickness=2.5, glass="ТФ1", semi_diameter=11.5),
        Surface(radius=-130.0, thickness=95.0, glass="", semi_diameter=12.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_cook_doublet() -> OpticalSystem:
    """Дублет Кука — классический ахромат f/5 f'≈100."""
    sys = OpticalSystem(name="Дублет Кука f/5", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 2.5, 5.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=55.0, thickness=8.0, glass="К8", semi_diameter=11.0),
        Surface(radius=-38.0, thickness=3.0, glass="ТФ2", semi_diameter=10.5),
        Surface(radius=-120.0, thickness=92.0, glass="", semi_diameter=11.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_telephoto() -> OpticalSystem:
    """Телеобъектив — 4 поверхности, отрицательный задний компонент."""
    sys = OpticalSystem(name="Телеобъектив", object_type=ObjectType.INFINITE, object_height=3.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 1.5, 3.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 15.0
    sys.surfaces = [
        Surface(radius=40.0, thickness=6.0, glass="К8", semi_diameter=10.0),
        Surface(radius=-60.0, thickness=25.0, glass="", semi_diameter=9.5),
        Surface(radius=-30.0, thickness=3.0, glass="ТФ1", semi_diameter=7.0),
        Surface(radius=45.0, thickness=40.0, glass="", semi_diameter=7.5),
    ]
    sys.stop_surface = 1
    return sys


def _demo_petzval() -> OpticalSystem:
    """Объектив Петцваля — 2 склеенных дублета, светосильный."""
    sys = OpticalSystem(name="Объектив Петцваля", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 25.0
    sys.surfaces = [
        Surface(radius=75.0, thickness=10.0, glass="К8", semi_diameter=16.0),
        Surface(radius=-55.0, thickness=3.0, glass="ТФ2", semi_diameter=15.5),
        Surface(radius=-200.0, thickness=40.0, glass="", semi_diameter=15.0),
        Surface(radius=50.0, thickness=5.0, glass="К8", semi_diameter=10.0),
        Surface(radius=-45.0, thickness=2.0, glass="ТФ1", semi_diameter=9.5),
        Surface(radius=80.0, thickness=35.0, glass="", semi_diameter=10.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_mirror() -> OpticalSystem:
    """Вогнутое сферическое зеркало f'≈200мм."""
    sys = OpticalSystem(name="Вогнутое зеркало", object_type=ObjectType.INFINITE, object_height=1.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 0.5, 1.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 40.0
    sys.surfaces = [
        Surface(radius=-400.0, thickness=-200.0, glass="", semi_diameter=22.0, is_reflective=True),
        Surface(radius=0.0, thickness=0.0, glass="", semi_diameter=5.0),  # плоскость изображения
    ]
    sys.stop_surface = 1
    return sys


def _demo_meniscus() -> OpticalSystem:
    """Менисковая линза (Росс) — обе поверхности выпуклые."""
    sys = OpticalSystem(name="Мениск Росса", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=45.0, thickness=10.0, glass="К8", semi_diameter=14.0),
        Surface(radius=55.0, thickness=80.0, glass="", semi_diameter=14.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_plano_convex() -> OpticalSystem:
    """Плоско-выпуклая линза — минимальная сферическая аберрация при правильной ориентации."""
    sys = OpticalSystem(name="Плоско-выпуклая линза", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0, 5.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=50.0, thickness=5.0, glass="К8", semi_diameter=12.0),
        Surface(radius=0.0, thickness=93.0, glass="", semi_diameter=12.0),  # плоская
    ]
    sys.stop_surface = 1
    return sys


if __name__ == "__main__":
    sys = create_demo_system()
    print(f"System: {sys.name}")
    print(f"Surfaces: {sys.num_surfaces}")
    print(f"Wavelengths: {[(w.value, w.name) for w in sys.wavelengths]}")
    
    result = paraxial_trace(sys)
    print(f"\nParaxial results:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    seidel = seidel_aberrations(sys)
    print(f"\nSeidel sums:")
    for k, v in seidel.items():
        print(f"  {k}: {v:.6f}")
