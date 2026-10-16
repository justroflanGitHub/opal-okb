"""
OPAL-OKB — Коэффициенты Цернике и карта волнового фронта
==========================================================
Zernike decomposition of wavefront aberrations.
"""
import math
import numpy as np
from typing import List, Tuple, Dict

from optics_engine import OpticalSystem, ObjectType, paraxial_trace
from ray_tracing import Ray, trace_ray_through_system
from glass_catalog import compute_refractive_index
from optics_utils import compute_z_positions, get_primary_wl, get_effective_aperture
from aberrations import (_compute_ray_start, _aim_at_pupil, _reference_sphere,
                         _air_exit_direction, _opl_to_reference_sphere)


# ── Zernike polynomial definitions (polar ρ, θ) ──────────────────────────

# (n, m, name) — up to order 4
ZERNIKE_TERMS = [
    (0,  0, 'Z00 Piston'),
    (1, -1, 'Z1-1 Tilt Y'),
    (1,  1, 'Z11 Tilt X'),
    (2, -2, 'Z2-2 Astig 45°'),
    (2,  0, 'Z20 Defocus'),
    (2,  2, 'Z22 Astig 0°'),
    (3, -3, 'Z3-3 Trefoil Y'),
    (3, -1, 'Z3-1 Coma Y'),
    (3,  1, 'Z31 Coma X'),
    (3,  3, 'Z33 Trefoil X'),
    (4, -4, 'Z4-4'),
    (4, -2, 'Z4-2 2nd Astig Y'),
    (4,  0, 'Z40 Spherical'),
    (4,  2, 'Z42 2nd Astig X'),
    (4,  4, 'Z44'),
]


# ── Noll normalization ───────────────────────────────────────────────────
# Each Zernike polynomial Z_n^m has RMS ≠ 1 over the unit disk.
# The Noll normalization factor N_n^m scales each polynomial to unit RMS:
#   N_n^m = sqrt(2(n+1))   for m ≠ 0
#   N_n^m = sqrt(n+1)        for m = 0
# Reference: R.J. Noll, "Zernike polynomials and atmospheric
# turbulence", J. Opt. Soc. Am. 66, 207-211 (1976).


def _noll_norm(n: int, m: int) -> float:
    """Noll normalization factor for Z_n^m so that RMS = 1 over unit disk."""
    if m == 0:
        return math.sqrt(n + 1)
    return math.sqrt(2 * (n + 1))


def _zernike_poly_noll(n: int, m: int, rho: float, theta: float) -> float:
    """Evaluate a Noll-normalized Zernike polynomial (unit RMS over unit disk)."""
    return _noll_norm(n, m) * _zernike_poly(n, m, rho, theta)


def _zernike_poly(n: int, m: int, rho: float, theta: float) -> float:
    """Evaluate a single (unnormalized) Zernike polynomial Z_n^m(ρ, θ).

    Kept for backward compatibility. For unit-RMS (Noll) version use
    _zernike_poly_noll().
    """
    if n == 0 and m == 0:
        return 1.0
    elif n == 1 and m == 1:
        return rho * math.cos(theta)
    elif n == 1 and m == -1:
        return rho * math.sin(theta)
    elif n == 2 and m == 0:
        return 2 * rho**2 - 1
    elif n == 2 and m == 2:
        return rho**2 * math.cos(2 * theta)
    elif n == 2 and m == -2:
        return rho**2 * math.sin(2 * theta)
    elif n == 3 and m == 1:
        return (3 * rho**3 - 2 * rho) * math.cos(theta)
    elif n == 3 and m == -1:
        return (3 * rho**3 - 2 * rho) * math.sin(theta)
    elif n == 3 and m == 3:
        return rho**3 * math.cos(3 * theta)
    elif n == 3 and m == -3:
        return rho**3 * math.sin(3 * theta)
    elif n == 4 and m == 0:
        return 6 * rho**4 - 6 * rho**2 + 1
    elif n == 4 and m == 2:
        return (4 * rho**4 - 3 * rho**2) * math.cos(2 * theta)
    elif n == 4 and m == -2:
        return (4 * rho**4 - 3 * rho**2) * math.sin(2 * theta)
    elif n == 4 and m == 4:
        return rho**4 * math.cos(4 * theta)
    elif n == 4 and m == -4:
        return rho**4 * math.sin(4 * theta)
    else:
        # General radial polynomial (rarely needed for n<=4)
        abs_m = abs(m)
        # Radial polynomial R_n^|m|(ρ)
        R = 0.0
        for s in range((n - abs_m) // 2 + 1):
            num = (-1)**s * math.factorial(n - s)
            den = (math.factorial(s)
                   * math.factorial((n + abs_m) // 2 - s)
                   * math.factorial((n - abs_m) // 2 - s))
            R += num / den * rho**(n - 2 * s)
        if m >= 0:
            return R * math.cos(m * theta)
        else:
            return R * math.sin(abs_m * theta)


def _compute_opl_for_ray(system: OpticalSystem, ray: Ray, wl: float) -> float:
    """Compute optical path length for a ray through the system.
    Uses result.opl from the trace engine (handles mirrors and refractive indices correctly).
    """
    result = trace_ray_through_system(system, ray, wl)
    if not result.success or len(result.path) < 2:
        return float('inf')
    return result.opl


def _compute_opl_to_ref_sphere(system: OpticalSystem, ray: Ray, wl: float,
                                 ref_cx: float, ref_cy: float, ref_cz: float,
                                 R_ref: float, n_air: float = 1.0) -> float:
    """OPL от старта луча до опорной сферы, мм.

    Трассирует луч и замыкает его на опорную сферу ВДОЛЬ направления
    луча в воздухе (общая логика :func:`aberrations._opl_to_reference_sphere`).

    Args:
        system: Optical system.
        ray: Input ray.
        wl: Wavelength in micrometers.
        ref_cx, ref_cy, ref_cz: Reference sphere center coordinates.
        R_ref: Reference sphere radius.
        n_air: Refractive index of image-space medium (default 1.0).

    Returns:
        OPL to reference sphere in mm, or float('inf') if ray fails.
    """
    result = trace_ray_through_system(system, ray, wl)
    if not result.success or len(result.path) < 2:
        return float('inf')
    direction = _air_exit_direction(system, result, wl)
    opl = _opl_to_reference_sphere(result.opl, result.path[-1], direction,
                                   (ref_cx, ref_cy, ref_cz), R_ref,
                                   n_air=n_air)
    return float('inf') if opl is None else opl


def fit_zernike_coefficients(points: List[Tuple[float, float, float]],
                             max_order: int = 4) -> List[Tuple[float, str]]:
    """МНК-подгонка коэффициентов Цернике по точкам зрачка.

    Единственная реализация подгонки (используется квадратурной сеткой
    ``compute_zernike_coefficients`` и гексаполярной сеткой зрачка в
    глобальном разложении ``compute_global_zernike``).

    Args:
        points: Список ``(px, py, W)`` — нормированные координаты зрачка
            (−1..1) и волновая аберрация в длинах волн.
        max_order: Максимальный порядок полиномов.

    Returns:
        Список ``(coeff, name)`` по :data:`ZERNIKE_TERMS`; нули, если
        точек меньше, чем членов разложения.
    """
    terms = [(n, m, name) for n, m, name in ZERNIKE_TERMS if n <= max_order]
    if len(points) < len(terms):
        return [(0.0, name) for _, _, name in terms]

    Z = np.zeros((len(points), len(terms)))
    W_vec = np.zeros(len(points))
    for k, (px, py, W) in enumerate(points):
        W_vec[k] = W
        rho = math.sqrt(px * px + py * py)
        theta = math.atan2(py, px)
        for t, (n, m, _) in enumerate(terms):
            Z[k, t] = _zernike_poly_noll(n, m, rho, theta)

    try:
        coeffs, _, _, _ = np.linalg.lstsq(Z, W_vec, rcond=None)
    except np.linalg.LinAlgError:
        coeffs = np.zeros(len(terms))

    return [(float(c), name) for c, (_, _, name) in zip(coeffs, terms)]


def compute_zernike_coefficients(system: OpticalSystem,
                                  wl: float = 0.58756,
                                  field_y: float = 0.0,
                                  num_rays: int = 64,
                                  max_order: int = 4,
                                  defocus_offset: float = 0.0) -> List[Tuple[float, str]]:
    """
    Разложение волновой аберрации по полиномам Цернике.

    Zernike polynomials Z_n^m (n=0..max_order, m=-n..n)
    W(ρ,θ) = Σ a_nm * Z_n^m(ρ,θ)

    1. Трассировать лучи через сетку на зрачке
    2. Вычислить W для каждого луча (OPL-based)
    3. Аппроксимировать полиномами Цернике (least squares)

    Возвращает: list of (coeff, name) — например:
    [(0.0, 'Z00 Piston'), (-0.5, 'Z1-1 Tilt Y'), (2.3, 'Z20 Defocus'), ...]
    """
    aperture = get_effective_aperture(system, default=10.0)

    # Collect valid ray data: (px, py, W)
    ray_data = []

    parax_zk = paraxial_trace(system)
    z_start_zk, z_pupil_zk = _compute_ray_start(system, parax_zk)
    (ref_cx, ref_cy, ref_cz), R_ref = _reference_sphere(system, field_y,
                                                        parax_zk)

    # Chief ray OPL
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        cx_s, cy_s = _aim_at_pupil(0, 0, z_start_zk, z_pupil_zk, sin_a, cos_a)
        chief_ray = Ray(x=cx_s, y=cy_s, z=z_start_zk, k=0, l=math.sin(angle), m=math.cos(angle))
    else:
        obj_z = -system.surfaces[0].thickness if system.surfaces else -50
        chief_ray = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

    # ===== Reference sphere parameters =====
    (ref_cx, ref_cy, ref_cz), R_ref = _reference_sphere(system, field_y,
                                                        parax_zk)

    chief_opl = _compute_opl_to_ref_sphere(system, chief_ray, wl,
                                             ref_cx, ref_cy, ref_cz, R_ref)

    for i in range(num_rays):
        for j in range(num_rays):
            px = -1.0 + 2.0 * j / (num_rays - 1) if num_rays > 1 else 0.0
            py = -1.0 + 2.0 * i / (num_rays - 1) if num_rays > 1 else 0.0
            r2 = px**2 + py**2
            if r2 > 1.0:
                continue

            y_start = py * aperture / 2
            x_start = px * aperture / 2

            if system.object_type == ObjectType.INFINITE:
                angle = math.radians(field_y) if field_y != 0 else 0.0
                sin_a, cos_a = math.sin(angle), math.cos(angle)
                rx_s, ry_s = _aim_at_pupil(x_start, y_start, z_start_zk, z_pupil_zk, sin_a, cos_a)
                ray = Ray(x=rx_s, y=ry_s, z=z_start_zk,
                          k=0, l=math.sin(angle), m=math.cos(angle))
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray = Ray(x=x_start, y=field_y, z=obj_z,
                          k=x_start / d, l=(y_start - field_y) / d, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            opl = _compute_opl_to_ref_sphere(system, ray, wl,
                                                ref_cx, ref_cy, ref_cz, R_ref)
            if opl == float('inf'):
                continue

            # Add defocus offset contribution
            if abs(defocus_offset) > 1e-12:
                opl += defocus_offset  # OPL in mm

            opd = opl - chief_opl
            W = opd / (wl * 1e-3)  # in wavelengths

            ray_data.append((px, py, W))

    return fit_zernike_coefficients(ray_data, max_order=max_order)


def compute_wavefront_map_2d(system: OpticalSystem,
                               wl: float = 0.58756,
                               field_y: float = 0.0,
                               grid_size: int = 64,
                               defocus_offset: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    2D карта волновой аберрации на зрачке.

    Возвращает:
        wavefront: 2D массив W(x,y) в длинах волн
        coords: 1D массив нормированных координат зрачка (-1..1)
        pupil_mask: 2D массив (1 внутри зрачка, 0 снаружи)
    """
    aperture = get_effective_aperture(system, default=10.0)

    parax_wm = paraxial_trace(system)
    z_start_wm, z_pupil_wm = _compute_ray_start(system, parax_wm)
    (ref_cx_wm, ref_cy_wm, ref_cz_wm), R_ref_wm = _reference_sphere(
        system, field_y, parax_wm)

    # Chief ray OPL
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        cx_s, cy_s = _aim_at_pupil(0, 0, z_start_wm, z_pupil_wm, sin_a, cos_a)
        chief_ray = Ray(x=cx_s, y=cy_s, z=z_start_wm, k=0, l=math.sin(angle), m=math.cos(angle))
    else:
        obj_z = -system.surfaces[0].thickness if system.surfaces else -50
        chief_ray = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

    # ===== Reference sphere parameters =====
    # Chief OPL to reference sphere — ноль отсчёта W
    chief_opl = _compute_opl_to_ref_sphere(system, chief_ray, wl,
                                             ref_cx_wm, ref_cy_wm, ref_cz_wm, R_ref_wm)

    coords = np.linspace(-1, 1, grid_size)
    wavefront = np.zeros((grid_size, grid_size))
    pupil_mask = np.zeros((grid_size, grid_size))

    for i in range(grid_size):
        for j in range(grid_size):
            px = coords[j]
            py = coords[i]
            r2 = px**2 + py**2
            if r2 > 1.0:
                continue

            pupil_mask[i, j] = 1.0

            y_start = py * aperture / 2
            x_start = px * aperture / 2

            if system.object_type == ObjectType.INFINITE:
                angle = math.radians(field_y) if field_y != 0 else 0.0
                sin_a, cos_a = math.sin(angle), math.cos(angle)
                rx_s, ry_s = _aim_at_pupil(x_start, y_start, z_start_wm, z_pupil_wm, sin_a, cos_a)
                ray = Ray(x=rx_s, y=ry_s, z=z_start_wm,
                          k=0, l=math.sin(angle), m=math.cos(angle))
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray = Ray(x=x_start, y=field_y, z=obj_z,
                          k=x_start / d, l=(y_start - field_y) / d, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            opl = _compute_opl_to_ref_sphere(system, ray, wl,
                                                ref_cx_wm, ref_cy_wm, ref_cz_wm, R_ref_wm)
            if opl == float('inf'):
                continue

            if abs(defocus_offset) > 1e-12:
                opl += defocus_offset

            opd = opl - chief_opl
            wavefront[i, j] = opd / (wl * 1e-3)

    return wavefront, coords, pupil_mask


def _subtract_coeff_lists(a: List[Tuple[float, str]],
                          b: List[Tuple[float, str]]) -> List[Tuple[float, str]]:
    """Почленная разность двух списков коэффициентов ``[(coeff, name)]``: a − b."""
    return [(ca - cb, name) for (ca, _), (cb, name) in zip(a, b)]


def compute_zernike_chromatic(system, num_rays=64, max_order=4):
    """
    Цернике для каждой рабочей длины волны + разности от первичной λ.

    Возвращает: {
        <имя λ>: [(coeff, name), ...],               # коэффициенты для каждой λ
        'delta_<λ>−<λ перв>': [(coeff, name), ...],  # Z_nm(λ) − Z_nm(λ перв)
    }
    Первичная λ — первая длина волны системы (``get_primary_wl``).
    """
    result = {}

    # Собираем коэффициенты для каждой длины волны
    wl_coeffs = {}
    for wl_obj in system.wavelengths:
        wl_name = wl_obj.name if wl_obj.name else f"{wl_obj.value:.3f}"
        coeffs = compute_zernike_coefficients(system, wl=wl_obj.value,
                                               num_rays=num_rays,
                                               max_order=max_order)
        wl_coeffs[wl_name] = coeffs
        wl_coeffs[wl_obj.value] = coeffs  # ключ по значению тоже
        result[wl_name] = coeffs

    # Разности каждой не-первичной λ от первичной
    primary_wl = get_primary_wl(system)
    primary_name = None
    for wl_obj in system.wavelengths:
        if abs(wl_obj.value - primary_wl) < 1e-9:
            primary_name = (wl_obj.name if wl_obj.name
                            else f"{wl_obj.value:.3f}")
            break
    if primary_name is not None and primary_name in wl_coeffs:
        primary_coeffs = wl_coeffs[primary_name]
        for wl_obj in system.wavelengths:
            name = wl_obj.name if wl_obj.name else f"{wl_obj.value:.3f}"
            if name == primary_name:
                continue
            result[f'delta_{name}−{primary_name}'] = _subtract_coeff_lists(
                wl_coeffs[name], primary_coeffs)

    return result


# ── Глобальное разложение: поле × λ × зрачок ──────────────────────────────

GLOBAL_ZERNIKE_MAX_ORDER = 4    # порядок полиномов Цернике
GLOBAL_TEXT_COEFF_FMT = '{:+8.4f}'   # формат коэффициентов в текстовой таблице
GLOBAL_TEXT_LABEL_W = 18             # ширина колонки метки (поле, λ)


def compute_global_zernike(system: OpticalSystem,
                           num_rings: int = 4,
                           max_order: int = GLOBAL_ZERNIKE_MAX_ORDER,
                           num_fields: int = 5) -> Dict:
    """Глобальное разложение Цернике: Z_nm для каждой (точка поля × λ).

    Для каждой комбинации трассируется пучок на гексаполярной сетке
    зрачка (:func:`aberrations.trace_wavefront_hexapolar`, пункт 2) и
    коэффициенты подгоняются МНК
    (:func:`fit_zernike_coefficients`).

    Args:
        system: Оптическая система.
        num_rings: Кольца гексаполярной сетки зрачка (4 → 61 точка).
        max_order: Максимальный порядок полиномов Цернике.
        num_fields: Число точек поля, если поле системы не задано.

    Returns:
        ``{'fields': [поле, ...], 'wavelengths': [λ, ...],
        'coeffs': {(field, wl): [(coeff, name), ...]}}``
    """
    from aberrations import (analysis_field_points,
                             trace_wavefront_hexapolar)
    fields = analysis_field_points(system, num_fields=num_fields)
    wavelengths = ([w.value for w in system.wavelengths]
                   if system.wavelengths else [get_primary_wl(system)])

    coeffs: Dict[Tuple[float, float], List[Tuple[float, str]]] = {}
    for field_y in fields:
        for wl in wavelengths:
            points = trace_wavefront_hexapolar(system, wl=wl,
                                               field_y=field_y,
                                               num_rings=num_rings)
            coeffs[(field_y, wl)] = fit_zernike_coefficients(
                points, max_order=max_order)
    return {'fields': fields, 'wavelengths': wavelengths, 'coeffs': coeffs}


def format_global_zernike_text(result: Dict,
                               wl_names: Dict[float, str] = None) -> str:
    """Текстовая таблица глобального разложения Цернике.

    Строки — комбинации (поле, λ), колонки — полиномы Z_nm; ширина
    фиксированная (моноширинный шрифт).
    """
    if not result or not result.get('coeffs'):
        return 'Нет данных'
    wl_names = wl_names or {}

    def _wl_label(wl: float) -> str:
        name = wl_names.get(wl, '')
        return f"{name} {wl:.3f}" if name else f"{wl:.3f}"

    terms = [name for _, name in result['coeffs'][
        tuple(result['coeffs'].keys())[0]]]
    short = [n.split()[0] for n in terms]

    lines = ['Глобальное разложение Цернике: поле × λ',
             f"Число комбинаций: {len(result['coeffs'])}",
             '']
    header = ('Поле'.rjust(GLOBAL_TEXT_LABEL_W - 6)
              + 'λ, мкм'.rjust(GLOBAL_TEXT_LABEL_W - 4)
              + ''.join(c.rjust(9) for c in short))
    lines.append(header)
    lines.append('-' * len(header))
    for field_y in result['fields']:
        for wl in result['wavelengths']:
            key = (field_y, wl)
            if key not in result['coeffs']:
                continue
            row = (f"{field_y:>{GLOBAL_TEXT_LABEL_W - 6}.3f}"
                   f"{_wl_label(wl):>{GLOBAL_TEXT_LABEL_W - 4}.{GLOBAL_TEXT_LABEL_W}}"
                   + ''.join(GLOBAL_TEXT_COEFF_FMT.format(c)
                             for c, _ in result['coeffs'][key]))
            lines.append(row)
    return '\n'.join(lines)


# ── OPAL-базис 28 членов, n ≤ 12 (реверс OPAVA, REVERSE_OPAVA.md §4/§8) ─────
#
# OPAVA (работа WA) раскладывает волновой фронт по 28 полиномам Цернике —
# таблица пар (n, m) в DGROUP:0B76, ASCII «00 20 40 … 66»: только косинусные
# члены (m ≥ 0) до n = 12. Азимут φ отсчитывается от меридиональной
# плоскости (оси Y — плоскости поля), поэтому cos-базис полон для фронтов,
# симметричных относительно меридиональной плоскости (W(−x, y) = W(x, y) —
# все осесимметричные системы с полем в меридиональной плоскости):
# sin-члены тождественно нулевые, кома/дисторсия ловятся членами (n, 1).
#
# Марки коэффициентов «C x IJ» (ANALIZE.DOC §5.2): x — степень разложения
# по хроматизму (0 = монохроматическое), I — степень по радиусу (n),
# J — степень по азимуту (m); цифры — шестнадцатеричные, как в таблице
# OPAVA («C x20» … «C x66»). Нормировка — Noll (единичный СКВ на единичном
# круге), σ² волнового фронта = Σ c².

#: Пары (n, m) базиса OPAL/OPAVA — 28 членов, n ≤ 12, m ≥ 0 (косинусные).
ZERNIKE_TERMS_28: List[Tuple[int, int]] = [
    (0, 0), (2, 0), (4, 0), (6, 0), (8, 0), (10, 0), (12, 0),
    (1, 1), (3, 1), (5, 1), (7, 1), (9, 1), (11, 1),
    (2, 2), (4, 2), (6, 2), (8, 2), (10, 2),
    (3, 3), (5, 3), (7, 3), (9, 3),
    (4, 4), (6, 4), (8, 4),
    (5, 5), (7, 5),
    (6, 6),
]

#: Марки «C xIJ» (зональное разложение OPAVA, I = n, J = m, hex-цифры).
ZERNIKE_MARKS_28: List[str] = [f'C x{n:X}{m:X}' for n, m in ZERNIKE_TERMS_28]

#: Имена классических аберраций (формы VAFORUS.DAT *vnb.sf); высшие
#: порядки в OPAVA имени не имеют (марка только).
_ZERNIKE_OPAL_NAMES: Dict[Tuple[int, int], str] = {
    (0, 0): 'Пистон',
    (1, 1): 'Дисторсия',
    (2, 0): 'Расфокусировка',
    (2, 2): 'Астигматизм',
    (3, 1): 'Кома',
    (4, 0): 'Сферическая',
    (6, 0): 'Сферическая 2',
    (8, 0): 'Сферическая 3',
}


def zernike_term_name(n: int, m: int) -> str:
    """Имя члена (n, m) OPAL-базиса: классическая аберрация или «n=… m=…»."""
    return _ZERNIKE_OPAL_NAMES.get((n, m), f'n={n} m={m}')


def _radial_coeffs(n: int, m: int) -> List[Tuple[int, float]]:
    """Радиальный полином R_n^|m|(ρ) как список ``(степень, коэффициент)``.

    R_n^m(ρ) = Σ_s (−1)^s·(n−s)! / (s!·((n+m)/2−s)!·((n−m)/2−s)!) · ρ^{n−2s}
    (m — неотрицательная степень азимута).
    """
    terms = []
    for s in range((n - m) // 2 + 1):
        c = ((-1) ** s * math.factorial(n - s)
             / (math.factorial(s)
                * math.factorial((n + m) // 2 - s)
                * math.factorial((n - m) // 2 - s)))
        terms.append((n - 2 * s, c))
    return terms


def _zernike_grid(n: int, m: int, gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    """Noll-нормированный Z_n^m на решётке (вне единичного круга — 0).

    Азимут φ — от оси Y (меридиональная плоскость): φ = atan2(x, y).
    """
    rho2 = gx ** 2 + gy ** 2
    rho = np.sqrt(rho2)
    radial = np.zeros_like(rho)
    for power, c in _radial_coeffs(n, abs(m)):
        radial += c * rho ** power
    phi = np.arctan2(gx, gy)
    value = _noll_norm(n, abs(m)) * radial * np.cos(abs(m) * phi)
    return np.where(rho2 <= 1.0, value, 0.0)


def _basis_stack(xs: np.ndarray, ys: np.ndarray,
                 terms: List[Tuple[int, int]]) -> np.ndarray:
    """Базис на решётке с осями X (``xs``) и Y (``ys``): (K, Ny, Nx)."""
    gx, gy = np.meshgrid(xs, ys)
    return np.stack([_zernike_grid(n, m, gx, gy) for n, m in terms])


def _grid_axes(grid) -> Tuple[np.ndarray, np.ndarray]:
    """Оси решётки X/Y из параметра ``grid``: N | ось | пара (Nx, Ny)."""
    if isinstance(grid, (tuple, list)) and len(grid) == 2 \
            and all(np.isscalar(g) for g in grid):
        nx, ny = int(grid[0]), int(grid[1])
        return (np.linspace(-1.0, 1.0, nx), np.linspace(-1.0, 1.0, ny))
    if np.isscalar(grid):
        coords = np.linspace(-1.0, 1.0, int(grid))
        return (coords, coords.copy())
    coords = np.asarray(grid, dtype=float)
    return (coords, coords.copy())


def zernike_basis(grid, terms: List[Tuple[int, int]] = ZERNIKE_TERMS_28
                  ) -> np.ndarray:
    """Базис Цернике OPAL на квадратной решётке зрачка.

    Args:
        grid: Размер решётки N (координаты −1..1, как у
            :func:`strehl._pupil_grid_from_points`), готовая ось координат
            (1D-массив, общая для X и Y) либо пара ``(Nx, Ny)``.
        terms: Список пар (n, m); по умолчанию :data:`ZERNIKE_TERMS_28`.

    Returns:
        Массив ``(len(terms), Ny, Nx)``; строки — Y, столбцы — X,
        Noll-нормировка (СКВ = 1 на единичном круге), вне круга — 0.
    """
    xs, ys = _grid_axes(grid)
    return _basis_stack(xs, ys, terms)


def fit_zernike(W: np.ndarray, mask: np.ndarray,
                terms: List[Tuple[int, int]] = ZERNIKE_TERMS_28
                ) -> Tuple[np.ndarray, float]:
    """МНК-разложение карты волнового фронта по базису Цернике (как OPAVA).

    Строит нормальные уравнения по точкам зрачка (``mask ≥ 0.5``) и решает
    МНК (:func:`numpy.linalg.lstsq`); базис Noll-нормирован, поэтому
    коэффициенты — вклады с единичным СКВ: σ² ≈ Σ c_k².

    Args:
        W: Карта волновой аберрации (длины волн), (Ny, Nx).
        mask: Маска зрачка (≥ 0.5 — внутри), той же формы.
        terms: Пары (n, m) базиса.

    Returns:
        ``(coeffs, residual_rms)`` — коэффициенты ``(len(terms),)`` и
        СКВ остатка (W − аппроксимация) по зрачку, длины волн.

    Raises:
        ValueError: Точек зрачка меньше, чем членов базиса.
    """
    W = np.asarray(W, dtype=float)
    inside = np.asarray(mask) >= 0.5
    if inside.shape != W.shape:
        raise ValueError(f'форма W {W.shape} ≠ формы маски {inside.shape}')
    if int(inside.sum()) < len(terms):
        raise ValueError(f'точек зрачка {int(inside.sum())} < '
                         f'членов базиса {len(terms)}')

    xs = np.linspace(-1.0, 1.0, W.shape[1])
    ys = np.linspace(-1.0, 1.0, W.shape[0])
    basis = _basis_stack(xs, ys, terms)              # (K, Ny, Nx)
    Zm = basis[:, inside].T                          # (N, K)
    coeffs, _, _, _ = np.linalg.lstsq(Zm, W[inside], rcond=None)
    residual = W[inside] - Zm @ coeffs
    residual_rms = math.sqrt(float(np.mean(residual ** 2)))
    return coeffs, residual_rms


def fit_zernike_points(points: List[Tuple[float, float, float]],
                       terms: List[Tuple[int, int]] = ZERNIKE_TERMS_28
                       ) -> Tuple[np.ndarray, float]:
    """МНК-разложение по рассеянным точкам зрачка — как OPAVA (лучи, не сетка).

    Базис вычисляется прямо в точках выборки зрачка (например,
    гексаполярная сетка :func:`aberrations.trace_wavefront_hexapolar`),
    без промежуточной интерполяции на решётку.

    Внимание: сумма Σc² равна площадному σ² единичного круга; σ по самим
    точкам (равные веса, как у :func:`strehl._wavefront_sigma`) содержит
    смещение выборки (кольца гексагональной сетки весят не по площади).

    Args:
        points: Список ``(px, py, W)`` — нормированные координаты зрачка
            (−1..1) и волновая аберрация (длины волн).
        terms: Пары (n, m) базиса.

    Returns:
        ``(coeffs, residual_rms)`` — как у :func:`fit_zernike`.

    Raises:
        ValueError: Точек меньше, чем членов базиса.
    """
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 3 or pts.shape[0] == 0:
        raise ValueError('points — список (px, py, W)')
    if pts.shape[0] < len(terms):
        raise ValueError(f'точек зрачка {pts.shape[0]} < '
                         f'членов базиса {len(terms)}')
    Zm = np.stack([_zernike_grid(n, m, pts[:, 0], pts[:, 1])
                   for n, m in terms]).T                  # (N, K)
    coeffs, _, _, _ = np.linalg.lstsq(Zm, pts[:, 2], rcond=None)
    residual = pts[:, 2] - Zm @ coeffs
    residual_rms = math.sqrt(float(np.mean(residual ** 2)))
    return coeffs, residual_rms


def zernike_reconstruct(coeffs, grid,
                        terms: List[Tuple[int, int]] = ZERNIKE_TERMS_28
                        ) -> np.ndarray:
    """Волновой фронт по коэффициентам: ``W = Σ c_k·Z_k`` (длины волн).

    Args:
        coeffs: Коэффициенты из :func:`fit_zernike` (или список).
        grid: Решётка — размер N, ось координат или пара ``(Nx, Ny)``
            (см. :func:`zernike_basis`).
        terms: Пары (n, m) базиса (должны соответствовать coeffs).

    Returns:
        Карта ``(Ny, Nx)``; вне единичного круга — 0.
    """
    coeffs = np.asarray(coeffs, dtype=float)
    basis = zernike_basis(grid, terms=terms[:len(coeffs)])
    return np.tensordot(coeffs, basis, axes=1)


def strehl_from_zernike(coeffs,
                        terms: List[Tuple[int, int]] = ZERNIKE_TERMS_28
                        ) -> float:
    """Число Штреля по коэффициентам Цернике (Марешаль).

    Noll-нормировка даёт σ² = Σ c_k² (пистон исключён — на пик PSF не
    влияет): ``S = exp(−(2π·σ)²)``; в линейном виде ``S ≈ 1 − (2π)²·Σc²``.
    Совпадает с :func:`strehl.strehl_marechal` от σ подгонки (тест,
    допуск 2 %).

    Args:
        coeffs: Коэффициенты :func:`fit_zernike` (длины волн).
        terms: Пары (n, m) базиса.

    Returns:
        Число Штреля в (0, 1].
    """
    from strehl import strehl_marechal   # формула-эталон волны 6
    coeffs = np.asarray(coeffs, dtype=float)
    variance = 0.0
    for c, (n, m) in zip(coeffs, terms):
        if (n, m) != (0, 0):             # пистон не снижает пик PSF
            variance += float(c) ** 2
    return strehl_marechal(math.sqrt(variance))


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    from optics_engine import create_demo_system

    print("=== Коэффициенты Цернике ===\n")
    sys_opt = create_demo_system()
    print(f"Система: {sys_opt.name}\n")

    coeffs = compute_zernike_coefficients(sys_opt, wl=0.58756, num_rays=32, max_order=4)
    print(f"{'Полином':<22} {'Коэффициент':>12}")
    print("-" * 36)
    for val, name in coeffs:
        print(f"{name:<22} {val:>+12.5f}")

    # Wavefront map
    wf, coords, mask = compute_wavefront_map_2d(sys_opt, grid_size=32)
    valid = wf[mask > 0]
    print(f"\nВолновой фронт: min={valid.min():.3f}, max={valid.max():.3f}, "
          f"PV={valid.max()-valid.min():.3f} λ")
    print("\nГотово!")
