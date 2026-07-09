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


def _zernike_poly(n: int, m: int, rho: float, theta: float) -> float:
    """Evaluate a single Zernike polynomial Z_n^m(ρ, θ)."""
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
    """Compute optical path length for a ray through the system."""
    result = trace_ray_through_system(system, ray, wl)
    if not result.success or len(result.path) < 2:
        return float('inf')
    opl = 0.0
    for k in range(len(result.path) - 1):
        p1 = result.path[k]
        p2 = result.path[k + 1]
        if k == 0:
            n = 1.0
        else:
            idx = min(k - 1, len(system.surfaces) - 1)
            n = compute_refractive_index(system.surfaces[idx].glass, wl)
        dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
        opl += n * dist
    return opl


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

    # Build list of terms up to max_order
    terms = [(n, m, name) for n, m, name in ZERNIKE_TERMS if n <= max_order]

    # Collect valid ray data: (rho, theta, W)
    ray_data = []

    # Chief ray OPL
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        chief_ray = Ray(x=0, y=0, z=-50, k=math.sin(angle), l=0, m=math.cos(angle))
    else:
        chief_ray = Ray(x=0, y=field_y, z=-50, k=0, l=0, m=1)

    chief_opl = _compute_opl_for_ray(system, chief_ray, wl)

    # Z-positions for defocus propagation
    z_pos = compute_z_positions(system)
    last_surf_z = z_pos[-2] if len(z_pos) > 1 else z_pos[-1]

    for i in range(num_rays):
        for j in range(num_rays):
            px = -1.0 + 2.0 * j / (num_rays - 1) if num_rays > 1 else 0.0
            py = -1.0 + 2.0 * i / (num_rays - 1) if num_rays > 1 else 0.0
            r2 = px**2 + py**2
            if r2 > 1.0:
                continue

            rho = math.sqrt(r2)
            theta = math.atan2(py, px)

            y_start = py * aperture / 2
            x_start = px * aperture / 2

            if system.object_type == ObjectType.INFINITE:
                angle = math.radians(field_y) if field_y != 0 else 0.0
                ray = Ray(x=x_start, y=y_start, z=-50,
                          k=math.sin(angle), l=0, m=math.cos(angle))
            else:
                ray = Ray(x=x_start, y=field_y, z=-50,
                          k=x_start / 50, l=(y_start - field_y) / 50, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            opl = _compute_opl_for_ray(system, ray, wl)
            if opl == float('inf'):
                continue

            # Add defocus offset contribution
            if abs(defocus_offset) > 1e-12:
                opl += defocus_offset  # OPL in mm

            opd = opl - chief_opl
            W = opd / (wl * 1e-3)  # in wavelengths

            ray_data.append((rho, theta, W))

    if len(ray_data) < len(terms):
        # Not enough data points, return zeros
        return [(0.0, name) for _, _, name in terms]

    # Build matrix for least squares: W = Z @ a
    num_pts = len(ray_data)
    num_terms = len(terms)
    Z = np.zeros((num_pts, num_terms))
    W_vec = np.zeros(num_pts)

    for k, (rho, theta, W) in enumerate(ray_data):
        W_vec[k] = W
        for t, (n, m, _) in enumerate(terms):
            Z[k, t] = _zernike_poly(n, m, rho, theta)

    # Least squares: a = (Z^T Z)^-1 Z^T W
    try:
        coeffs, _, _, _ = np.linalg.lstsq(Z, W_vec, rcond=None)
    except np.linalg.LinAlgError:
        coeffs = np.zeros(num_terms)

    result = []
    for t, (n, m, name) in enumerate(terms):
        result.append((float(coeffs[t]), name))

    return result


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

    # Chief ray OPL
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        chief_ray = Ray(x=0, y=0, z=-50, k=math.sin(angle), l=0, m=math.cos(angle))
    else:
        chief_ray = Ray(x=0, y=field_y, z=-50, k=0, l=0, m=1)

    chief_opl = _compute_opl_for_ray(system, chief_ray, wl)

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
                ray = Ray(x=x_start, y=y_start, z=-50,
                          k=math.sin(angle), l=0, m=math.cos(angle))
            else:
                ray = Ray(x=x_start, y=field_y, z=-50,
                          k=x_start / 50, l=(y_start - field_y) / 50, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            opl = _compute_opl_for_ray(system, ray, wl)
            if opl == float('inf'):
                continue

            if abs(defocus_offset) > 1e-12:
                opl += defocus_offset

            opd = opl - chief_opl
            wavefront[i, j] = opd / (wl * 1e-3)

    return wavefront, coords, pupil_mask


def compute_zernike_chromatic(system, num_rays=64, max_order=4):
    """
    Цернике для каждой длины волны + разности.
    
    Возвращает: {
        wl_name: [(coeff, name), ...],
        'delta_F-d': [(coeff, name), ...],
        'delta_C-d': [(coeff, name), ...]
    }
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
    
    # Разности: F-d и C-d (если есть соответствующие длины волн)
    # Ищем по именам и значениям
    wl_by_name = {}
    wl_by_value = {}
    for wl_obj in system.wavelengths:
        name = wl_obj.name if wl_obj.name else ""
        wl_by_name[name] = wl_obj.value
        wl_by_value[wl_obj.value] = name
    
    # Стандартные соответствия
    f_names = ['F', "F'"]
    c_names = ['C', "C'"]
    d_names = ['d', 'D', 'e']
    
    f_wl = None
    c_wl = None
    d_wl = None
    
    # Ищем по именам
    for name in f_names:
        if name in wl_by_name:
            f_wl = wl_by_name[name]
            break
    for name in c_names:
        if name in wl_by_name:
            c_wl = wl_by_name[name]
            break
    for name in d_names:
        if name in wl_by_name:
            d_wl = wl_by_name[name]
            break
    
    # Если по именам не нашли — по значениям
    if f_wl is None:
        for wl_obj in system.wavelengths:
            if abs(wl_obj.value - 0.48613) < 0.002:
                f_wl = wl_obj.value
                break
    if c_wl is None:
        for wl_obj in system.wavelengths:
            if abs(wl_obj.value - 0.65627) < 0.002:
                c_wl = wl_obj.value
                break
    if d_wl is None:
        # Берём основную (первую) длину волны
        d_wl = get_primary_wl(system)
    
    # Вычисляем разности
    if f_wl is not None and f_wl in wl_coeffs and d_wl in wl_coeffs:
        f_c = wl_coeffs[f_wl]
        d_c = wl_coeffs[d_wl]
        delta = [(fc - dc, name) for (fc, _), (dc, name) in zip(f_c, d_c)]
        result['delta_F-d'] = delta
    
    if c_wl is not None and c_wl in wl_coeffs and d_wl in wl_coeffs:
        c_c = wl_coeffs[c_wl]
        d_c = wl_coeffs[d_wl]
        delta = [(cc - dc, name) for (cc, _), (dc, name) in zip(c_c, d_c)]
        result['delta_C-d'] = delta
    
    return result


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
