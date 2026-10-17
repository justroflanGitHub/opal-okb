"""OPAL-OKB — нативная трассировка лучей (фасад над C++ ядром ``_opal_native``).

Архитектура (TASK_NATIVE):
  * физика (пересечения, Снеллиус, OPL, координатные изломы) — ТОЛЬКО в C++
    (``native/src/raytrace.cpp``, побайтовый паритет с ``analysis/ray_tracing.py``);
  * дисперсия — только через существующий ``glass_catalog.compute_refractive_index``
    (вызывается здесь при подготовке поверхностей; в C++ формулы нет);
  * генерация лучей — только через существующие helpers ``optics_utils``
    (``get_effective_aperture`` / ``make_field_ray``) и ``optics_engine.paraxial_trace``;
  * ``analysis/ray_tracing.py`` — эталонный Python-референс для тестов паритета,
    остаётся нетронутым и используется как fallback, когда ``_opal_native.pyd``
    не собран.

Результат трассировки — :class:`TraceResultNative` (namedtuple с полями
``path / success / error / surfaces_hit / opl``), по интерфейсу совместимый
с :class:`analysis.ray_tracing.TraceResult`.
"""
from __future__ import annotations

import math
from typing import List, NamedTuple, Optional, Sequence, Tuple

import numpy as np

from domain.models import OpticalSystem, Surface, SurfaceType
from domain.spatial import CoordBreak
from glass_catalog import compute_refractive_index
from optics_utils import (
    EPSILON,  # noqa: F401 — реэкспорт для тестов; источник utils/optics_utils.py
    TINY,
    get_effective_aperture,
    make_field_ray,
)
from optics_engine import ObjectType, paraxial_trace
from analysis.ray_tracing import _compute_semi_diameter, trace_ray_through_system

try:
    import _opal_native as _native
    HAS_NATIVE: bool = True
except ImportError:  # pragma: no cover — зависит от окружения
    _native = None
    HAS_NATIVE = False

#: Максимальное число членов асферического полинома, поддержанных C++ ядром
#: (k2..k10 c запасом: A4..A18). Референс поддерживает произвольное число —
#: при переполнении фасад прозрачно уходит на Python-трассировку.
MAX_ASPHERIC_TERMS: int = 8

#: Допуск сопоставления длины волны в n_override (analysis/ray_tracing.py).
_N_OVERRIDE_WL_TOL: float = 0.002

_ERROR_STRINGS: List[Optional[str]] = [None, 'TIR', 'MISS', 'EDGE', 'STOP']
_OBSCURED = 'OBSCURED'


class TraceResultNative(NamedTuple):
    """Результат трассировки одного луча (аналог TraceResult из референса).

    Attributes:
        path: кортеж точек ``(x, y, z)`` в глобальной СК (включая стартовую).
        success: ``True`` — луч дошёл до конца без ошибок.
        error: ``None`` / ``'TIR'`` / ``'MISS'`` / ``'EDGE'`` / ``'STOP'`` /
            ``'OBSCURED'`` (последняя ставится при генерации веера).
        surfaces_hit: число поверхностей, реально пересечённых лучом.
        opl: оптическая длина пути (мм).
    """
    path: Tuple[Tuple[float, float, float], ...]
    success: bool
    error: Optional[str]
    surfaces_hit: int
    opl: float


def _n_override_lookup(surface: Surface, wl: float, n_default: float) -> float:
    """n поверхности c учётом ``n_override`` (точная копия логики референса).

    ``analysis.ray_tracing.trace_ray_through_system`` сканирует ``n_override``
    с допуском :data:`_N_OVERRIDE_WL_TOL` и берёт ПЕРВОЕ совпадение.
    """
    n_ov = getattr(surface, 'n_override', None)
    if n_ov:
        for wl_key, n_val in n_ov.items():
            if abs(wl_key - wl) < _N_OVERRIDE_WL_TOL:
                return float(n_val)
    return n_default


def _n_after(surface: Surface, wl: float) -> float:
    """Показатель преломления ПОСЛЕ поверхности (среда самой поверхности)."""
    return _n_override_lookup(surface, wl, compute_refractive_index(surface.glass, wl))


def _n_before(system: OpticalSystem, i: int, wl: float) -> float:
    """Показатель преломления ПЕРЕД поверхностью ``i``.

    Для ``i == 0`` — среда перед системой (воздух, без override — как в
    референсе); иначе — среда предыдущей поверхности с её ``n_override``.
    """
    if i == 0:
        return compute_refractive_index("", wl)
    return _n_after(system.surfaces[i - 1], wl)


# ---------------------------------------------------------------------------
# Подготовка данных поверхностей
# ---------------------------------------------------------------------------

_SURFACE_DTYPE: Optional[np.dtype] = None


def surface_dtype() -> np.dtype:
    """Structured dtype для массива поверхностей (спецификация — из C++).

    Единственный источник раскладки ``SurfaceData`` — модуль
    ``_opal_native`` (``offsetof``-ы возвращаются C++ стороной), поэтому
    Python и C++ не могут разойтись.
    """
    global _SURFACE_DTYPE
    if _SURFACE_DTYPE is None:
        spec = _native.surface_dtype()
        _SURFACE_DTYPE = np.dtype({
            'names': list(spec['names']),
            'formats': list(spec['formats']),
            'offsets': list(spec['offsets']),
            'itemsize': int(spec['itemsize']),
        })
    return _SURFACE_DTYPE


def native_supports(system: OpticalSystem) -> bool:
    """``True``, если все поверхности системы покрываются C++ ядром.

    Ограничение: не более :data:`MAX_ASPHERIC_TERMS` членов асферического
    полинома (референс допускает произвольное число). Системы с большим
    числом членов трассируются Python-fallback'ом.
    """
    return HAS_NATIVE and all(
        len(s.aspheric_coeffs) <= MAX_ASPHERIC_TERMS for s in system.surfaces)


def prepare_surfaces(system: OpticalSystem, wl: float) -> np.ndarray:
    """Собрать массив ``SurfaceData`` из системы для данной длины волны.

    Показатели преломления вычисляются здесь (через
    ``glass_catalog.compute_refractive_index`` + ``n_override``); в C++
    формулы дисперсии нет. Полудиаметры — эффективные, через референсный
    ``_compute_semi_diameter``. Матрицы координатных изломов — из
    ``domain.spatial.CoordBreak`` (единственная реализация).

    Args:
        system: оптическая система (не модифицируется).
        wl: рабочая длина волны (мкм).

    Returns:
        ``np.ndarray`` формы ``(N,)`` со structured dtype из
        :func:`surface_dtype`.

    Raises:
        ValueError: у поверхности больше :data:`MAX_ASPHERIC_TERMS`
            асферических членов (C++ ядро их не поддерживает).
    """
    dt = surface_dtype()
    n = len(system.surfaces)
    arr = np.zeros(n, dtype=dt)

    # aperture для детекции «богусного» полудиаметра — как в референсе:
    # aperture = getattr(sys, 'aperture_value', 0) or 20.0
    aperture = getattr(system, 'aperture_value', 0) or 20.0
    stop_idx = getattr(system, 'stop_surface', -1)

    z = 0.0
    for i, s in enumerate(system.surfaces):
        rec = arr[i]
        coeffs = s.aspheric_coeffs
        if len(coeffs) > MAX_ASPHERIC_TERMS:
            raise ValueError(
                f"поверхность {i}: {len(coeffs)} асферических членов > "
                f"{MAX_ASPHERIC_TERMS} — трассируй Python-референсом")

        rec['R'] = s.radius
        rec['z_surf'] = z
        rec['conic_k'] = s.conic_constant
        for j in range(MAX_ASPHERIC_TERMS):
            rec['c%d' % j] = float(coeffs[j]) if j < len(coeffs) else 0.0
        rec['n_before'] = _n_before(system, i, wl)
        rec['n_after'] = _n_after(s, wl)
        rec['semi_diameter'] = _compute_semi_diameter(s, aperture)

        cb = CoordBreak.from_surface(s, z)
        rec['is_coord_break'] = 0 if cb.is_identity else 1
        m = cb.matrix if cb.matrix is not None else (1.0, 0.0, 0.0,
                                                     0.0, 1.0, 0.0,
                                                     0.0, 0.0, 1.0)
        for j in range(9):
            rec['m%d%d' % divmod(j, 3)] = m[j]
        rec['cb_dx'] = s.decenter_x
        rec['cb_dy'] = s.decenter_y
        rec['tilt0'] = s.tilt_x
        rec['tilt1'] = s.tilt_y
        rec['tilt2'] = s.tilt_z

        rec['num_coeffs'] = len(coeffs)
        # Условие асферической ветви — как в trace_ray_through_system:
        # surface_type != SPHERE or |conic| > TINY or len(coeffs) > 0
        rec['is_aspheric'] = int(
            s.surface_type != SurfaceType.SPHERE
            or abs(s.conic_constant) > TINY
            or len(coeffs) > 0)
        rec['is_mirror'] = int(bool(s.is_reflective))
        rec['is_stop'] = int(i == stop_idx)

        z += s.thickness
    return arr


def _system_params(system: OpticalSystem, wl: float) -> dict:
    """Системные величины трассировки (точная копия преамбулы референса).

    Восстанавливает z-позиции вершин, параметры диафрагмы (включая
    детекцию «aperture_value хранит F/# или NA»), n среды перед системой
    и признак распространения до плоскости изображения.
    """
    z_positions = [0.0]
    for s in system.surfaces:
        z_positions.append(z_positions[-1] + s.thickness)

    stop_surf_idx = getattr(system, 'stop_surface', -1)
    stop_offset = getattr(system, 'stop_offset', 0.0)
    # Detect bogus aperture_value (F/# or NA stored instead of diameter)
    raw_aperture = getattr(system, 'aperture_value', 0)
    if raw_aperture > 0 and raw_aperture < 1.0:
        real_sd_vals = [s2.semi_diameter for s2 in system.surfaces
                        if s2.semi_diameter > raw_aperture]
        if real_sd_vals:
            raw_aperture = max(real_sd_vals) * 2.0
    stop_radius = raw_aperture / 2.0 if raw_aperture > 0 else 0.0

    # stop_surface — 1-индексация (как в paraxial_trace/OPAL ND):
    # плоскость диафрагмы = вершина поверхности stop_surface−1 + stop_offset.
    # Диафрагма НА поверхности (SD=0) — отдельная плоскость не нужна:
    # обрезает полудиаметр самой поверхности (синхронно с
    # analysis/ray_tracing.trace_ray_through_system).
    has_stop = 1 <= stop_surf_idx <= len(system.surfaces)
    z_stop = (z_positions[stop_surf_idx - 1] + stop_offset) if has_stop else 0.0
    if has_stop and any(abs(z_stop - zv) <= 1e-6 for zv in z_positions):
        has_stop = False
        z_stop = 0.0

    last = system.surfaces[-1] if system.surfaces else None
    return dict(
        wl=wl,
        has_stop=has_stop,
        z_stop=z_stop,
        stop_radius=stop_radius,
        n_start=compute_refractive_index("", wl),
        propagate_to_image=bool(last is not None and last.thickness != 0),
        img_z=z_positions[-1],
    )


def _wrap_native_result(path_flat: np.ndarray, offsets: np.ndarray,
                        i: int, error_code: int, opl: float,
                        surfaces_hit: int) -> TraceResultNative:
    """Собрать TraceResultNative из CSR-строки батча (одиночные лучи)."""
    # tolist() даёт чистые Python float — как у TraceResult референса
    path = tuple(map(tuple, path_flat[offsets[i]:offsets[i + 1]].tolist()))
    return TraceResultNative(
        path=path,
        success=(error_code == 0),
        error=(_ERROR_STRINGS[error_code]
               if 0 <= error_code < len(_ERROR_STRINGS) else str(error_code)),
        surfaces_hit=int(surfaces_hit),
        opl=float(opl),
    )


# ---------------------------------------------------------------------------
# Трассировка
# ---------------------------------------------------------------------------

def trace_batch(system: OpticalSystem, rays: Sequence[Sequence[float]],
                wl: float = 0.58756) -> List[TraceResultNative]:
    """Протрассировать пучок лучей через систему.

    Использует C++ ядро, если оно собрано и система им покрывается;
    иначе — Python-референс ``trace_ray_through_system`` с тем же
    интерфейсом результатов.

    Args:
        system: оптическая система.
        rays: массив лучей ``(N, 6)`` — ``(x, y, z, k, l, m)``.
        wl: рабочая длина волны (мкм).

    Returns:
        Список :class:`TraceResultNative` длины ``N``.
    """
    if not system.surfaces:
        return []

    use_native = native_supports(system)
    if use_native:
        surfaces = prepare_surfaces(system, wl)
        params = _system_params(system, wl)
        rays_arr = np.ascontiguousarray(rays, dtype=np.float64)
        if rays_arr.ndim != 2 or rays_arr.shape[1] != 6:
            raise ValueError("rays: ожидается массив (N, 6) — x,y,z,k,l,m")
        batch = _native.trace_batch(surfaces, rays_arr, **params)
        # CSR-распаковка: скаляры → списки одним вызовом, потом срезы списков
        offs = batch['path_offsets'].tolist()
        pts = batch['path_flat'].tolist()
        opl = batch['opl'].tolist()
        ec = batch['error_code'].tolist()
        sh = batch['surfaces_hit'].tolist()
        results = []
        for i in range(len(opl)):
            code = ec[i]
            results.append(TraceResultNative(
                path=tuple(map(tuple, pts[offs[i]:offs[i + 1]])),
                success=(code == 0),
                error=(_ERROR_STRINGS[code]
                       if 0 <= code < len(_ERROR_STRINGS) else str(code)),
                surfaces_hit=sh[i],
                opl=opl[i]))
        return results

    # Python-fallback (тот же интерфейс результатов)
    results = []
    for ray6 in rays:
        r = trace_ray_through_system(
            system,
            _ray_from_seq(ray6), wl)
        results.append(TraceResultNative(
            path=tuple(r.path),
            success=r.success,
            error=r.error,
            surfaces_hit=r.surfaces_hit,
            opl=r.opl))
    return results


def trace_one(system: OpticalSystem, ray: Sequence[float],
              wl: float = 0.58756) -> TraceResultNative:
    """Трассировка одиночного луча ``(x, y, z, k, l, m)`` (паритет/отладка)."""
    res = trace_batch(system, [ray], wl)
    return res[0]


def _ray_from_seq(ray6: Sequence[float]):
    """Луч референсного типа из последовательности из 6 чисел."""
    from analysis.ray_tracing import Ray
    x, y, z, k, l, m = (float(v) for v in ray6)
    return Ray(x=x, y=y, z=z, k=k, l=l, m=m)


# ---------------------------------------------------------------------------
# Веер лучей (fan) — генерация как в референсном trace_fan
# ---------------------------------------------------------------------------

def _fan_aperture(system: OpticalSystem) -> float:
    """Эффективная апертура веера (копия преамбулы trace_fan)."""
    aperture = get_effective_aperture(system, default=10.0)
    if aperture < 1.0:
        # Auto-reduce: aperture похож на F/# или NA — оценим по полуdiameters
        real_sd = [s2.semi_diameter for s2 in system.surfaces
                   if s2.semi_diameter > 1.0]
        if real_sd:
            aperture = max(real_sd) * 1.2
        else:
            efl = paraxial_trace(system).get('focal_length', 0)
            if efl and abs(efl) > 0.1:
                # aperture is NA → D = 2*NA*f'
                aperture = 2.0 * aperture * abs(efl)
            else:
                aperture = 20.0  # last resort
    return aperture


def _make_fan_rays(system: OpticalSystem, num_rays: int, pupil_range: float,
                   wl: float, field_y: float
                   ) -> Tuple[np.ndarray, np.ndarray]:
    """Сгенерировать лучи веера (структура ``_do_trace`` референса trace_fan).

    Векторизация байт-точна: INFINITE-ветвь ``make_field_ray`` аффинна по
    ``pupil_y`` (``y = pupil_y − C``, направление постоянно) — одна проба
    при ``pupil_y = 0`` даёт все константы, а ``fl(−C + p) == fl(p − C)``
    в IEEE-арифметике (сложение коммутативно); FINITE-ветвь — конструкция
    референса (луч из точки предмета в точку зрачка) той же очерёдностью
    операций, поэлементно.

    Returns:
        ``(rays, blocked)``: массив ``(N, 6)`` и маска экранированных лучей.
    """
    obscuration = getattr(system, 'obscuration_ratio', 0.0)
    aperture = _fan_aperture(system)

    # py = -pr + 2·pr·i/(num_rays-1) — та же очерёдность операций, поэлементно
    if num_rays > 1:
        i = np.arange(num_rays, dtype=np.float64)
        py = -pupil_range + 2 * pupil_range * i / (num_rays - 1)
    else:
        py = np.zeros(1)
    # Экранирование: |ρ| < obscuration_ratio → луч блокируется
    blocked = np.abs(py) < obscuration

    y_start = py * aperture / 2  # референс: y_start = py * aperture / 2

    if system.object_type == ObjectType.INFINITE:
        z_pupil = paraxial_trace(system).get('sP', 0)
        z_start = -max(abs(z_pupil), 10.0) - 5.0
        probe = make_field_ray(system, 0.0, 0.0, field_y, z_start, z_pupil)
        # y(pupil_y) = pupil_y − C = probe.y + y_start (проба: pupil_y = 0)
        y = probe.y + y_start
        rays = np.column_stack([
            np.full(num_rays, probe.x), y, np.full(num_rays, z_start),
            np.full(num_rays, probe.k), np.full(num_rays, probe.l),
            np.full(num_rays, probe.m)])
    else:
        sF = paraxial_trace(system).get('sF', 0)
        obj_dist = abs(sF) if sF and abs(sF) > 1e-6 else 100.0
        obj_y = field_y
        l = y_start - obj_y           # l = y_start − obj_y
        m = np.full(num_rays, obj_dist)
        k = np.zeros(num_rays)
        # **2 в референсе = CPython float_pow → C pow(x, 2.0); np.power с
        # показателем 2.0 тоже зовёт pow поэлементно (не целочисленный путь).
        norm = np.sqrt(np.power(k, 2.0) + np.power(l, 2.0) + np.power(m, 2.0))
        rays = np.column_stack([
            np.zeros(num_rays), np.full(num_rays, obj_y),
            np.full(num_rays, -obj_dist),
            k / norm, l / norm, m / norm])
    return np.ascontiguousarray(rays), blocked


def _trace_fan_once(system: OpticalSystem, num_rays: int, pupil_range: float,
                    wl: float, field_y: float) -> List[TraceResultNative]:
    """Один проход веера (лучи + трассировка одним батчем)."""
    rays, blocked = _make_fan_rays(system, num_rays, pupil_range, wl, field_y)
    # Трассируем только нескрытые лучи (блокированные в батч не попадают)
    res = trace_batch(system, rays[~blocked], wl)
    out: List[TraceResultNative] = []
    j = 0
    for i in range(num_rays):
        if blocked[i]:
            out.append(TraceResultNative(path=(), success=False,
                                         error=_OBSCURED, surfaces_hit=0, opl=0.0))
        else:
            out.append(res[j])
            j += 1
    return out


def trace_fan_native(system: OpticalSystem, num_rays: int = 7,
                     pupil_range: float = 1.0, wl: float = 0.58756,
                     field_y: float = 0.0) -> List[TraceResultNative]:
    """Веер лучей в меридиональной плоскости (аналог ``trace_fan``).

    Генерация лучей повторяет референс (включая auto-reduce зрачка при
    тотальном отказе лучей), трассировка — одним C++ батчем.

    Args:
        system: оптическая система.
        num_rays: количество лучей.
        pupil_range: диапазон зрачка (0..1).
        wl: рабочая длина волны (мкм).
        field_y: смещение по полю (мм или градусы).

    Returns:
        Список :class:`TraceResultNative` длины ``num_rays``.
    """
    results = _trace_fan_once(system, num_rays, pupil_range, wl, field_y)

    # Auto-reduce: если все лучи упали с EDGE или MISS — пробуем меньший зрачок
    edge_count = sum(1 for r in results if r.error == 'EDGE')
    miss_count = sum(1 for r in results if r.error == 'MISS')
    ok_count = sum(1 for r in results if r.success)
    if ok_count == 0 and (edge_count > 0 or miss_count > 0):
        for reduction in [0.3, 0.1, 0.03, 0.01, 0.003]:
            if reduction >= pupil_range:
                continue
            results = _trace_fan_once(system, num_rays, reduction, wl, field_y)
            ok_count = sum(1 for r in results if r.success)
            if ok_count > 0:
                break
    return results


# ---------------------------------------------------------------------------
# 3D сетка по зрачку — генерация как в референсном trace_grid_3d
# ---------------------------------------------------------------------------

def trace_grid_3d_native(system: OpticalSystem, num_rings: int = 3,
                         num_azimuths: int = 8, wl: float = 0.546,
                         field_y: float = 0.0
                         ) -> List[List[TraceResultNative]]:
    """Сетка лучей по кольцам входного зрачка (аналог ``trace_grid_3d``).

    Args:
        system: оптическая система.
        num_rings: число колец (кольцо 0 при ``num_rings > 1`` — центральный луч).
        num_azimuths: число азимутальных позиций на кольце.
        wl: рабочая длина волны (мкм).
        field_y: угол поля (градусы) для INFINITE или высота (мм) для FINITE.

    Returns:
        ``List[List[TraceResultNative]]`` — внешние список по кольцам,
        внутренние по азимутам (структура как у референса).
    """
    aperture = get_effective_aperture(system, default=20.0)
    # Detect bogus aperture_value (F/# or NA stored instead of diameter)
    real_sd = [s.semi_diameter for s in system.surfaces
               if s.semi_diameter > aperture / 10.0]
    if aperture < 1.0 and real_sd:
        aperture = max(real_sd) * 2.0
    pupil_radius = aperture / 2.0

    # z-позиция входного зрачка (≈ stop surface + offset)
    stop_idx = getattr(system, 'stop_surface', 1)
    stop_off = getattr(system, 'stop_offset', 0.0)
    z_pupil = 0.0
    for j in range(min(stop_idx, len(system.surfaces))):
        z_pupil += system.surfaces[j].thickness
    z_pupil += stop_off

    is_infinite = (system.object_type == ObjectType.INFINITE)
    angle = math.radians(field_y) if (is_infinite and field_y != 0) else 0.0
    z_start = -1.0 if is_infinite else z_pupil - 1.0

    # Структура лучей: rings × azimuths; ring 0 при num_rings>1 — один луч.
    layout: List[int] = []           # сколько лучей в каждом кольце
    rays_flat: List[Sequence[float]] = []

    parax = None
    sF = None
    if not is_infinite:
        parax = paraxial_trace(system)
        sF = parax.get('sF', 0)
    obj_dist = abs(sF) if (sF and abs(sF) > 1e-6) else 100.0

    for ring in range(num_rings):
        if num_rings == 1:
            r = 0.0
        else:
            r = (ring + 1) / num_rings * pupil_radius

        # Кольцо 0 (num_rings > 1) — единственный центральный луч
        if ring == 0 and num_rings > 1:
            if is_infinite:
                dz = z_pupil - z_start
                y_at_start = (-dz * math.sin(angle) / math.cos(angle)
                              if abs(math.cos(angle)) > EPSILON else 0.0)
                rays_flat.append((
                    0.0, y_at_start, z_start,
                    math.sin(angle) if field_y != 0 else 0.0,
                    0.0,
                    math.cos(angle) if field_y != 0 else 1.0))
            else:
                obj_y = field_y
                k, l, m = 0.0, 0.0 - obj_y, obj_dist
                # **2 — как в референсе (CPython float_pow → C pow)
                norm = math.sqrt(k ** 2 + l ** 2 + m ** 2)
                rays_flat.append((0.0, obj_y, -obj_dist,
                                  k / norm, l / norm, m / norm))
            layout.append(1)
            continue

        for az in range(num_azimuths):
            az_angle = 2 * math.pi * az / num_azimuths
            px = r * math.cos(az_angle)
            py = r * math.sin(az_angle)

            if is_infinite:
                ray = make_field_ray(system, px, py, field_y, z_start, z_pupil)
                rays_flat.append((ray.x, ray.y, ray.z, ray.k, ray.l, ray.m))
            else:
                obj_y = field_y
                dx = px - 0.0
                dy = py - obj_y
                dz_val = z_pupil - (-obj_dist)
                k, l, m = dx, dy, dz_val
                # **2 — как в референсе (CPython float_pow → C pow)
                norm = math.sqrt(k ** 2 + l ** 2 + m ** 2)
                rays_flat.append((0.0, obj_y, -obj_dist,
                                  k / norm, l / norm, m / norm))
        layout.append(num_azimuths)

    results = trace_batch(system, rays_flat, wl)

    out: List[List[TraceResultNative]] = []
    pos = 0
    for count in layout:
        out.append(list(results[pos:pos + count]))
        pos += count
    return out
