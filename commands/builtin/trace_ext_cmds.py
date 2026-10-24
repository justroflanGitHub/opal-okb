"""
OPAL-OKB — Пакет R500-16: хвосты трассировки (tracex.*).

ТАБЛИЧНЫЕ И СВОДНЫЕ ВИДЫ ХОДА ЛУЧЕЙ, которых нет ни в Волнах 1/3
(``analyze.ray_fan``/``trace.*``/``beam.*``/``vign.*``/``tables.*``), ни
в R500-9..15: координаты/углы/ОПС ЗАДАННОГО луча по поверхностям, углы
падения/преломления (cos I, cos I'), предельные углы ПВО, клиренс луча
до диафрагмы, меридиональная таблица пучка (высоты+углы крайних и
главного), ход ОПС по поверхностям и сводка ОПС/ОПД габаритных лучей,
заполнение полудиаметров ходом крайнего луча, проекция зрачков на
поверхности, углы выходного конуса, таблица вершин/промежутков и сред
n(λ), зоны веера равной площади, сводки сетки 3D (статистика/срезанные
лучи), параксиальные хвосты: ynu-таблица базисных лучей, произвольный
параксиальный луч, ABCD-матрицы поверхностей/промежутков, инвариант
Лагранжа по промежуткам, параксиальный ход пучка по промежуткам.

Префикс ``tracex`` (а не ``trace``): исчерпывающий набор Волны 3
закреплён пином ``tests/test_commands_trace.py`` (категории trace/beam/
vign/tables, ровно 19 команд) — новые команды категорию ``trace`` не
занимают.

Движки не дублируются: трассировка — ``analysis.ray_tracing``
(``trace_ray_through_system``/``trace_grid_3d``), построители лучей
поля — ``analysis.aberrations`` (``_compute_ray_start`` /
``_pupil_field_ray`` / ``compute_gauge_rays``), геометрия нормалей —
``analysis.ray_tracing.surface_normal*``, локальные СК —
``domain.spatial.CoordBreak``, среды — ``domain.calculations.
refractive_index``, эффективный радиус ГОЭ — ``goe_effective_radius``,
зоны равной площади — ``analysis.tables.field_zones``, кардинальные
отрезки — ``domain.calculations.paraxial_trace``. Собственные хелперы
модуля — разбор пути луча на события-поверхности (по схеме
``analysis.beam_heights._surface_heights``) и перенос y/n·u по
поверхностям (``surface_data`` у ``paraxial_trace`` — документированная
заглушка ``[]``, пер-поверхностных состояний движок не отдаёт).
"""
import math

from optics_utils import get_effective_aperture, get_primary_wl

from commands.base import (
    ERR_INVALID_PARAM,
    Param,
    CommandError,
    sanitize_json,
)
from commands.registry import Registry
from commands.systemio import resolve_system, system_source_params

# ============================================================
# Именованные константы пакета
# ============================================================

#: Допуск сопоставления точки пути с плоскостью (мм) — как
#: ``beam_heights._Z_MATCH_TOL`` (gui/analysis_panel.py).
Z_MATCH_TOL = 1e-6

#: Зон веера по умолчанию (таблицы TABGL/TABOC — сетка равной площади).
FAN_ZONES_DEFAULT = 3

#: Колец/азимутов сетки 3D в сводках по умолчанию (как trace.grid3d).
GRID_RINGS_DEFAULT = 3
GRID_AZIMUTHS_DEFAULT = 8

#: Мастер-луч для сводок ОПС/ОПД (опорный луч разности хода).
OPL_REFERENCE_KEY = "chief"

#: Стартовая высота/угол параксиального луча по умолчанию (крайевой
#: базис Волны y=1, u=0 — нормировка ynu-таблиц).
PARAXIAL_Y0_DEFAULT = 1.0
PARAXIAL_U0_DEFAULT = 0.0

#: Минимум |C| матрицы системы, при котором определяется efl = −1/C.
MATRIX_C_TINY = 1e-12


# ============================================================
# Среды и разбор пути луча по поверхностям
# ============================================================

def _gap_media(system, wl: float) -> list:
    """Абсолютные n сред по промежуткам (длина ns+1).

    Промежуток 0 — перед первой поверхностью (воздух); промежуток i —
    после поверхности i−1. Зеркало среду не меняет (n = n предыдущего
    промежутка). Стёкла/n_override — domain.calculations.refractive_index
    (единственная реализация).
    """
    from domain.calculations import refractive_index
    media = [refractive_index("", wl)]
    for s in system.surfaces:
        if s.is_reflective:
            media.append(media[-1])
        else:
            media.append(refractive_index(
                s.glass, wl, None, getattr(s, "n_override", None)))
    return media


def _paraxial_media(system, wl: float) -> list:
    """Знаковые n сред параксиального переноса (длина ns+1).

    Как параксиальный движок (domain/calculations.py): после зеркала
    знак n меняется (обратный ход), дальше сохраняется знак предыдущей
    среды при смене стекла.
    """
    from domain.calculations import refractive_index
    media = [1.0]
    for s in system.surfaces:
        if s.is_reflective:
            media.append(-media[-1])
        else:
            n_next = refractive_index(
                s.glass, wl, None, getattr(s, "n_override", None))
            media.append((1.0 if media[-1] > 0 else -1.0) * n_next)
    return media


def _stop_plane(system) -> tuple:
    """(z_plane, on_surface_idx) плоскости диафрагмы — 1-индексация ND.

    Как трейсер/``paraxial_trace``: вершина поверхности stop_surface−1
    плюс stop_offset. ``on_surface_idx`` — 0-based индекс поверхности,
    на ВЕРШИНЕ которой лежит плоскость (SD=0: отдельной плоскости нет,
    обрезка — дело полудиаметра поверхности), иначе ``None``. Плоскость
    вне системы → ``(None, None)``.
    """
    from optics_utils import compute_z_positions
    z_pos = compute_z_positions(system)
    stop_idx = getattr(system, "stop_surface", -1)
    if not 1 <= stop_idx <= len(z_pos):
        return None, None
    z_stop = z_pos[stop_idx - 1] + getattr(system, "stop_offset", 0.0)
    for i, zv in enumerate(z_pos):
        if abs(z_stop - zv) <= 1e-6:
            return z_stop, i
    return z_stop, None


def _stop_z_on_vertex(system, stop_idx: int) -> float:
    """Z плоскости диафрагмы, совпадающей с вершиной поверхности
    ``stop_idx`` (1-индексация ND; SD=0 — смещения нет)."""
    from optics_utils import compute_z_positions
    return compute_z_positions(system)[stop_idx - 1]


def _ray_events(system, points, error=None) -> tuple:
    """Разбор пути луча (``TraceResult.path`` / ``points`` габаритного
    луча) на события-поверхности.

    Схема ``beam_heights._surface_heights``: точка 0 — старт; точка в
    плоскости диафрагмы (вставляется трейсером) пропускается; последняя
    точка на плоскости изображения — отдельно. Возвращает
    ``(events, image_point)``; ``events`` — список по ДОСТИГНУТЫМ
    поверхностям в порядке встречи::

        {"surface": int (0-based), "path_idx": int, "point": (x, y, z)}

    Луч, срезанный кромкой (EDGE), даёт событие на срезавшей
    поверхности (точка пересечения добавлена трейсером); клиппинг
    диафрагмой (STOP, ``error='STOP'``) — точка на плоскости диафрагмы
    отбрасывается.
    """
    from optics_utils import compute_z_positions
    z_pos = compute_z_positions(system)
    stop_idx = getattr(system, "stop_surface", -1)
    z_stop, _on_surf = _stop_plane(system)
    n = len(system.surfaces)
    pts = list(points)
    if error == "STOP" and len(pts) > 1:
        pts = pts[:-1]            # последняя — клип диафрагмы, не поверхность
    events, image_point = [], None
    consumed = 0
    for j, point in enumerate(pts):
        if j == 0:
            continue
        if (j == len(pts) - 1 and consumed == n
                and abs(point[2] - z_pos[-1]) < Z_MATCH_TOL):
            image_point = point
            continue
        if (z_stop is not None and abs(point[2] - z_stop) < Z_MATCH_TOL
                and consumed >= stop_idx):
            continue               # точка в плоскости диафрагмы
        if consumed < n:
            events.append({"surface": consumed, "path_idx": j,
                           "point": point})
            consumed += 1
    return events, image_point


def _segment_dirs(points) -> list:
    """Единичные направления сегментов пути (конечные разности — как
    ``compute_gauge_rays``)."""
    dirs = []
    for p0, p1 in zip(points, points[1:]):
        dx, dy, dz = (p1[k] - p0[k] for k in range(3))
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        dirs.append((dx / d, dy / d, dz / d) if d > Z_MATCH_TOL
                    else (0.0, 0.0, 1.0))
    return dirs


def _slope_deg(direction) -> "tuple | None":
    """(u_y, u_x) — углы сегмента с осью Z в меридиональной/сагиттальной
    плоскостях, градусы."""
    k, l, m = direction
    return (math.degrees(math.atan2(l, m)),
            math.degrees(math.atan2(k, m)))


def _path_opl_cumulative(points, media_by_point: list) -> list:
    """Накопленный ОПС в каждой точке пути (Σ n·L по сегментам).

    ``media_by_point`` — индекс промежутка для сегмента, НАЧИНАЮЩЕГОСЯ
    в точке (той же длины, что ``points``; последний — не используется).
    """
    opl = 0.0
    out = [0.0]
    for j, (p0, p1) in enumerate(zip(points, points[1:])):
        d = math.sqrt(sum((p1[k] - p0[k]) ** 2 for k in range(3)))
        opl += media_by_point[j] * d
        out.append(opl)
    return out


def _point_gap_indices(system, points, events) -> list:
    """Индексы промежутков для сегментов пути (по событиям разбора).

    Сегмент, начинающийся в точке j, лежит в промежутке
    ``surface события + 1`` (0 — до первой поверхности).
    """
    n = len(system.surfaces)
    by_idx = {ev["path_idx"]: ev["surface"] for ev in events}
    gaps, current = [], 0
    for j in range(len(points)):
        if j in by_idx:                      # точка-событие поверхности
            current = by_idx[j] + 1
        gaps.append(min(current, n))
    return gaps


# ============================================================
# Построители лучей поля (через зрачковые координаты)
# ============================================================

def _trace_pupil_ray(system, wl: float, field_y: float,
                     rho_x: float, rho_y: float):
    """Реальная трассировка луча поля через точку входного зрачка.

    ``rho_x/rho_y`` — доли полуапертуры (aperture/2, мм в плоскости
    зрачка). Построитель — ``aberrations._pupil_field_ray`` (тот же,
    что у ``compute_gauge_rays``/TABESB); трассировка — точный трейсер.
    Возвращает ``TraceResult``.
    """
    from analysis.aberrations import _compute_ray_start, _pupil_field_ray
    from analysis.ray_tracing import trace_ray_through_system
    from optics_engine import paraxial_trace
    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)
    ray = _pupil_field_ray(system, rho_x * aperture / 2.0,
                           rho_y * aperture / 2.0, field_y,
                           z_start, z_pupil)
    return trace_ray_through_system(system, ray, wl)


def _ray_trace_dict(result) -> dict:
    """TraceResult → JSON-совместимый словарь (как trace.ray)."""
    return {
        "success": result.success,
        "error": result.error,
        "surfaces_hit": result.surfaces_hit,
        "opl": result.opl,
        "path": [[p[0], p[1], p[2]] for p in result.path],
    }


# ============================================================
# Параксиальный перенос y / n·u (собственный хелпер пакета)
# ============================================================

def _surface_power(surface, n_before: float, n_after: float,
                   wl: float) -> float:
    """Параксиальная сила поверхности φ (в редуцированных углах nu).

    Преломление φ = (n′ − n)/R, зеркало φ = −2n/R; R — эффективный
    радиус ГОЭ (:func:`domain.calculations.goe_effective_radius`).
    """
    from domain.calculations import goe_effective_radius
    radius = goe_effective_radius(surface, wl)
    if radius == 0:
        return 0.0
    if surface.is_reflective:
        return -2.0 * n_before / radius
    return (n_after - n_before) / radius


def _paraxial_propagate(system, wl: float, y0: float, nu0: float) -> dict:
    """Перенос параксиального луча (y, n·u) по поверхностям.

    Уравнения переноса — FORMULAS.md (§параксиал): преломление
    ``nu′ = nu − y·φ``, трансляция ``y′ = y + nu′·d/n′``. Состояния
    поверхностей ``surface_data`` у ``paraxial_trace`` — заглушка ``[]``
    (движок их не отдаёт), перенос реализован здесь на движковых
    величинах (n, φ, ГОЭ-радиус — domain.calculations).

    Возвращает::

        {"media": [...ns+1 знаковых n...],
         "surfaces": [{y, nu_before, nu_after, d, n_after, phi} × ns],
         "image_y": y на плоскости изображения,
         "image_nu": nu в пространстве изображений}
    """
    media = _paraxial_media(system, wl)
    y, nu = float(y0), float(nu0)
    rows = []
    for i, s in enumerate(system.surfaces):
        n_b, n_a = media[i], media[i + 1]
        phi = _surface_power(s, n_b, n_a, wl)
        nu_before = nu
        nu = nu - y * phi
        d = s.thickness
        rows.append({"y": y, "nu_before": nu_before, "nu_after": nu,
                     "d": d, "n_after": n_a, "phi": phi})
        if abs(n_a) > Z_MATCH_TOL:
            y = y + nu * d / n_a
    return {"media": media, "surfaces": rows,
            "image_y": y, "image_nu": nu}


def _paraxial_basis(system, wl: float) -> tuple:
    """Базисные лучи ynu: крайевой (y=1, nu=0) и «главный» (y=0, nu=1).

    Это те же базисные лучи, которыми ``paraxial_trace`` строит ABCD
    (A=y1, B=y2, C=nu1, D=nu2 на последней поверхности).
    """
    marg = _paraxial_propagate(system, wl, 1.0, 0.0)
    chief = _paraxial_propagate(system, wl, 0.0, 1.0)
    return marg, chief


def _mm(value) -> float:
    """float из параметра (CLI-csv даёт строки — привести)."""
    return float(value)


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать команды пакета R500-16 (tracex.*)."""

    # ----------------------------------------------------------
    # Луч по поверхностям
    # ----------------------------------------------------------

    @registry.command(
        "tracex.ray.surfaces", category="tracex",
        description="Таблица ЗАДАННОГО луча по поверхностям: координаты, "
                    "углы сегментов, ОПС нарастающим итогом (Снеллиус, "
                    "точный трейсер)",
        returns="{success, error, opl_total, rows: [{n, x, y, z, "
                "u_y_deg, u_x_deg, opl_cum_mm, clipped?}], image}",
        params=system_source_params([
            Param("x", type="float", default=0.0, help="старт луча X, мм"),
            Param("y", type="float", default=0.0, help="старт луча Y, мм"),
            Param("z", type="float", default=0.0, help="старт луча Z, мм"),
            Param("k", type="float", default=0.0,
                  help="направление X (нормируется)"),
            Param("l", type="float", default=0.0,
                  help="направление Y (нормируется)"),
            Param("m", type="float", default=1.0,
                  help="направление Z (нормируется)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_ray_surfaces(ctx, file, system, lbo_index, lbo_name,
                            x, y, z, k, l, m, wl):
        from analysis.ray_tracing import Ray, trace_ray_through_system
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        norm = math.sqrt(k * k + l * l + m * m)
        if norm < 1e-12:
            raise CommandError(ERR_INVALID_PARAM,
                               "направление луча — нулевой вектор")
        ray = Ray(x, y, z, k / norm, l / norm, m / norm)
        result = trace_ray_through_system(sys_obj, ray, wl_eff)
        media = _gap_media(sys_obj, wl_eff)
        events, img = _ray_events(sys_obj, result.path, result.error)
        gap_of_point = _point_gap_indices(sys_obj, result.path, events)
        opl_cum = _path_opl_cumulative(result.path,
                                       [media[g] for g in gap_of_point])
        dirs = _segment_dirs(result.path)
        n = len(sys_obj.surfaces)
        rows = [{"n": i + 1, "x": None, "y": None, "z": None,
                 "u_y_deg": None, "u_x_deg": None, "opl_cum_mm": None}
                for i in range(n)]
        for ev in events:
            i, j, p = ev["surface"], ev["path_idx"], ev["point"]
            u = _slope_deg(dirs[j]) if j < len(dirs) else None
            rows[i].update({"x": p[0], "y": p[1], "z": p[2],
                            "u_y_deg": u[0] if u else None,
                            "u_x_deg": u[1] if u else None,
                            "opl_cum_mm": opl_cum[j]})
            if not result.success and i >= result.surfaces_hit \
                    and result.error == "EDGE":
                rows[i]["clipped"] = True
        return {"wl": wl_eff, "success": result.success,
                "error": result.error, "surfaces_hit": result.surfaces_hit,
                "opl_total_mm": result.opl, "rows": sanitize_json(rows),
                "image": ([img[0], img[1], img[2]] if img else None)}

    @registry.command(
        "tracex.ray.angles", category="tracex",
        description="Углы падения/преломления ЗАДАННОГО луча на каждой "
                    "поверхности: cos I, cos I', I, I' (нормали — в "
                    "локальной СК поверхности)",
        returns="{success, error, rows: [{n, cos_i, cos_t, i_deg, "
                "t_deg, n_before, n_after, reflective, tir_margin}]}",
        params=system_source_params([
            Param("x", type="float", default=0.0, help="старт луча X, мм"),
            Param("y", type="float", default=0.0, help="старт луча Y, мм"),
            Param("z", type="float", default=0.0, help="старт луча Z, мм"),
            Param("k", type="float", default=0.0,
                  help="направление X (нормируется)"),
            Param("l", type="float", default=0.0,
                  help="направление Y (нормируется)"),
            Param("m", type="float", default=1.0,
                  help="направление Z (нормируется)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_ray_angles(ctx, file, system, lbo_index, lbo_name,
                          x, y, z, k, l, m, wl):
        from analysis.ray_tracing import (
            Ray,
            surface_normal,
            surface_normal_aspheric,
            trace_ray_through_system,
        )
        from domain.spatial import CoordBreak
        from optics_utils import compute_z_positions
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        norm = math.sqrt(k * k + l * l + m * m)
        if norm < 1e-12:
            raise CommandError(ERR_INVALID_PARAM,
                               "направление луча — нулевой вектор")
        ray = Ray(x, y, z, k / norm, l / norm, m / norm)
        result = trace_ray_through_system(sys_obj, ray, wl_eff)
        media = _gap_media(sys_obj, wl_eff)
        dirs = _segment_dirs(result.path)
        events, _img = _ray_events(sys_obj, result.path, result.error)
        z_pos = compute_z_positions(sys_obj)
        rows = []
        for ev in events:
            i, j, p = ev["surface"], ev["path_idx"], ev["point"]
            s = sys_obj.surfaces[i]
            cb = CoordBreak.from_surface(s, z_pos[i])
            lx, ly, lz = (cb.point_to_local(p) if not cb.is_identity
                          else (p[0], p[1], p[2]))
            d_in = dirs[j - 1] if j >= 1 else None
            if d_in is not None and not cb.is_identity:
                d_in = cb.dir_to_local(d_in)
            d_out = dirs[j] if j < len(dirs) else None
            if d_out is not None and not cb.is_identity:
                d_out = cb.dir_to_local(d_out)
            if s.aspheric_coeffs or abs(s.conic_constant) > 1e-9:
                nx, ny, nz = surface_normal_aspheric(
                    lx, ly, lz, s.radius, 0.0,
                    conic_k=s.conic_constant,
                    aspheric_coeffs=list(s.aspheric_coeffs))
            else:
                nx, ny, nz = surface_normal(lx, ly, lz, s.radius, 0.0)
            # Ориентация нормали — к падающему лучу (как refract()
            # трейсера): при cos I < 0 нормаль переворачивается. Тогда
            # cos I = −(d_in·n); преломлённый луч — по другую сторону
            # нормали: cos I' = −(d_out·n). Отражение: I' = I.
            cos_i = (-(d_in[0] * nx + d_in[1] * ny + d_in[2] * nz)
                     if d_in else None)
            if cos_i is not None and cos_i < 0:
                nx, ny, nz = -nx, -ny, -nz
                cos_i = -cos_i
            if s.is_reflective:
                cos_t = cos_i
            else:
                cos_t = (-(d_out[0] * nx + d_out[1] * ny + d_out[2] * nz)
                         if d_out else None)
            i_deg = (math.degrees(math.acos(max(-1.0, min(1.0, cos_i))))
                     if cos_i is not None else None)
            t_deg = (math.degrees(math.acos(max(-1.0, min(1.0, cos_t))))
                     if cos_t is not None else None)
            n1, n2 = media[i], media[i + 1]
            # Запас до ПВО: sin I ≤ n2/n1 (для n1>n2)
            margin = None
            if not s.is_reflective and cos_i is not None and n1 > n2:
                sin_i = math.sqrt(max(0.0, 1.0 - cos_i * cos_i))
                margin = (n2 / n1) - sin_i
            rows.append({"n": i + 1, "cos_i": cos_i, "cos_t": cos_t,
                         "i_deg": i_deg, "t_deg": t_deg,
                         "n_before": n1, "n_after": n2,
                         "reflective": bool(s.is_reflective),
                         "tir_margin": margin})
        return {"wl": wl_eff, "success": result.success,
                "error": result.error,
                "rows": sanitize_json(rows)}

    @registry.command(
        "tracex.ray.pupil", category="tracex",
        description="Трассировка луча ПОЛЯ через заданную точку входного "
                    "зрачка (доли полуапертуры; построитель габаритных "
                    "лучей TABESB)",
        returns="{wl, field_y, rho_x, rho_y, success, error, "
                "surfaces_hit, opl, path}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("rho_x", type="float", default=0.0,
                  help="точка зрачка X, доли полуапертуры (−1..1)"),
            Param("rho_y", type="float", default=0.0,
                  help="точка зрачка Y, доли полуапертуры (−1..1)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_ray_pupil(ctx, file, system, lbo_index, lbo_name,
                         field_y, rho_x, rho_y, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        result = _trace_pupil_ray(sys_obj, wl_eff, field_y,
                                  _mm(rho_x), _mm(rho_y))
        out = {"wl": wl_eff, "field_y": field_y,
               "rho_x": rho_x, "rho_y": rho_y}
        out.update(_ray_trace_dict(result))
        return out

    @registry.command(
        "tracex.ray.multi_wl", category="tracex",
        description="Луч поля через точку зрачка по ВСЕМ λ системы: "
                    "координаты на изображении и ОПС по длинам волн",
        returns="{rows: [{wl, success, error, last_point, y_img, opl}]}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("rho_x", type="float", default=0.0,
                  help="точка зрачка X, доли полуапертуры"),
            Param("rho_y", type="float", default=0.0,
                  help="точка зрачка Y, доли полуапертуры"),
        ]))
    def tracex_ray_multi_wl(ctx, file, system, lbo_index, lbo_name,
                            field_y, rho_x, rho_y):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wls = [float(w.value) for w in
               (sys_obj.wavelengths or [])] or [get_primary_wl(sys_obj)]
        rows = []
        for wl in wls:
            result = _trace_pupil_ray(sys_obj, wl, field_y,
                                      _mm(rho_x), _mm(rho_y))
            last = result.path[-1] if result.path else None
            rows.append({"wl": wl, "success": result.success,
                         "error": result.error,
                         "last_point": ([last[0], last[1], last[2]]
                                        if last else None),
                         "y_img": (last[1] if last else None),
                         "opl": result.opl})
        return {"field_y": field_y, "rho_x": rho_x, "rho_y": rho_y,
                "rows": sanitize_json(rows)}

    # ----------------------------------------------------------
    # Диафрагма / ПВО
    # ----------------------------------------------------------

    @registry.command(
        "tracex.stop.clearance", category="tracex",
        description="Клиренс луча до края апертурной диафрагмы: положение "
                    "луча в плоскости диафрагмы, запас в мм и долях радиуса "
                    "(диафрагма НА поверхности — клиренс до её полудиаметра)",
        returns="{stop_surface, stop_z, on_surface, stop_radius_mm, "
                "r_at_stop, clearance_mm, clearance_frac, reached, passed}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("rho_x", type="float", default=0.0,
                  help="точка зрачка X, доли полуапертуры"),
            Param("rho_y", type="float", default=0.0,
                  help="точка зрачка Y, доли полуапертуры"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_stop_clearance(ctx, file, system, lbo_index, lbo_name,
                              field_y, rho_x, rho_y, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        z_stop, on_surface = _stop_plane(sys_obj)
        stop_radius = None
        if z_stop is None:
            stop_idx = getattr(sys_obj, "stop_surface", -1)
            if not 1 <= stop_idx <= len(sys_obj.surfaces):
                raise CommandError(
                    ERR_INVALID_PARAM,
                    "диафрагма не задана (stop_surface вне системы) — "
                    "клиренс считать не по чему")
            # Диафрагма на вершине поверхности (SD=0): край диафрагмы —
            # полудиаметр самой поверхности (как обрезает трейсер).
            sd = sys_obj.surfaces[stop_idx - 1].semi_diameter
            if sd and sd > 0:
                z_stop = _stop_z_on_vertex(sys_obj, stop_idx)
                stop_radius = float(sd)
                on_surface = stop_idx - 1
        if z_stop is None:
            raise CommandError(
                ERR_INVALID_PARAM,
                "диафрагма на поверхности без полудиаметра — край "
                "диафрагмы не определён")
        if stop_radius is None:
            stop_radius = get_effective_aperture(
                sys_obj, default=10.0) / 2.0
        result = _trace_pupil_ray(sys_obj, wl_eff, field_y,
                                  _mm(rho_x), _mm(rho_y))
        hit = None
        for p0, p1 in zip(result.path, result.path[1:]):
            lo, hi = min(p0[2], p1[2]), max(p0[2], p1[2])
            if lo - Z_MATCH_TOL <= z_stop <= hi + Z_MATCH_TOL:
                dz = p1[2] - p0[2]
                if abs(dz) < Z_MATCH_TOL:
                    hit = p0
                    break
                t = (z_stop - p0[2]) / dz
                hit = tuple(p0[k] + t * (p1[k] - p0[k]) for k in range(3))
                break
        base = {"stop_surface": getattr(sys_obj, "stop_surface", 0),
                "stop_z": z_stop,
                "on_surface": (on_surface + 1 if on_surface is not None
                               else None),
                "stop_radius_mm": stop_radius,
                "ray_success": result.success, "ray_error": result.error}
        if hit is None:
            base.update({"r_at_stop": None, "clearance_mm": None,
                         "clearance_frac": None, "reached": False,
                         "passed": None})
            return base
        r = math.hypot(hit[0], hit[1])
        clearance = stop_radius - r
        base.update({
            "r_at_stop": r, "x_at_stop": hit[0], "y_at_stop": hit[1],
            "clearance_mm": clearance,
            "clearance_frac": (clearance / stop_radius
                               if stop_radius > 0 else None),
            "reached": True, "passed": r <= stop_radius + 1e-9})
        return base

    @registry.command(
        "tracex.tir.critical", category="tracex",
        description="Предельные углы полного внутреннего отражения по "
                    "поверхностям (asin n₂/n₁ для сред с n₁>n₂)",
        returns="{rows: [{n, glass, n_before, n_after, critical_deg, "
                "tir_possible, reflective}]}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_tir_critical(ctx, file, system, lbo_index, lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        media = _gap_media(sys_obj, wl_eff)
        rows = []
        for i, s in enumerate(sys_obj.surfaces):
            n1, n2 = media[i], media[i + 1]
            critical, possible = None, False
            if not s.is_reflective and n1 > n2 > 0:
                critical = math.degrees(math.asin(n2 / n1))
                possible = True
            rows.append({"n": i + 1, "glass": s.glass or "",
                         "n_before": n1, "n_after": n2,
                         "critical_deg": critical,
                         "tir_possible": possible,
                         "reflective": bool(s.is_reflective)})
        return {"wl": wl_eff, "rows": sanitize_json(rows)}

    # ----------------------------------------------------------
    # Габаритные лучи: таблицы пучка
    # ----------------------------------------------------------

    @registry.command(
        "tracex.meridional.table", category="tracex",
        description="Меридиональная таблица пучка: высоты и углы верхнего/"
                    "нижнего крайних и главного лучей по поверхностям, "
                    "полувысота и угол конуса пучка",
        returns="{rows: [{n, y_upper, y_lower, y_chief, u_upper_deg, "
                "u_lower_deg, u_chief_deg, semi_height, "
                "cone_half_deg}], image_row}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_meridional_table(ctx, file, system, lbo_index, lbo_name,
                                field_y, wl):
        from analysis.aberrations import compute_gauge_rays
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rays = {r["key"]: r for r in
                compute_gauge_rays(sys_obj, wl=wl_eff, field_y=field_y)}

        def _series(key):
            r = rays[key]
            events, img = _ray_events(sys_obj, r["points"], r["error"])
            heights = {ev["surface"]: ev["point"][1] for ev in events}
            slopes = {}
            for ev in events:
                j = ev["path_idx"]
                if j < len(r["directions"]):
                    slopes[ev["surface"]] = _slope_deg(
                        r["directions"][j])[0]
            img_slope = (_slope_deg(r["directions"][-1])[0]
                         if r["directions"] else None)
            return heights, slopes, (img[1] if img else None), img_slope

        up = _series("upper")
        low = _series("lower")
        chief = _series("chief")
        n = len(sys_obj.surfaces)
        rows = []
        for i in range(n):
            y_u, y_l, y_c = up[0].get(i), low[0].get(i), chief[0].get(i)
            u_u, u_l = up[1].get(i), low[1].get(i)
            semi = None
            if y_u is not None and y_l is not None:
                semi = (y_u - y_l) / 2.0
            cone = None
            if u_u is not None and u_l is not None:
                cone = (u_u - u_l) / 2.0
            rows.append({"n": i + 1, "y_upper": y_u, "y_lower": y_l,
                         "y_chief": y_c, "u_upper_deg": u_u,
                         "u_lower_deg": u_l, "u_chief_deg": chief[1].get(i),
                         "semi_height": semi, "cone_half_deg": cone})
        image_row = None
        if up[2] is not None or low[2] is not None or chief[2] is not None:
            image_row = {"y_upper": up[2], "y_lower": low[2],
                         "y_chief": chief[2],
                         "u_upper_deg": up[3], "u_lower_deg": low[3],
                         "u_chief_deg": chief[3]}
        return {"wl": wl_eff, "field_y": field_y,
                "rows": sanitize_json(rows),
                "image_row": sanitize_json(image_row)}

    @registry.command(
        "tracex.opl.table", category="tracex",
        description="Ход ОПС по поверхностям для габаритных лучей пучка "
                    "(верх/низ/главный/саг±1): n·L нарастающим итогом",
        returns="{rows: [{n, opl_upper, opl_lower, opl_chief, "
                "opl_sag_plus, opl_sag_minus}], keys}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_opl_table(ctx, file, system, lbo_index, lbo_name,
                         field_y, wl):
        from analysis.aberrations import compute_gauge_rays
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        media = _gap_media(sys_obj, wl_eff)
        rays = compute_gauge_rays(sys_obj, wl=wl_eff, field_y=field_y)
        series = {}
        for r in rays:
            events, _img = _ray_events(sys_obj, r["points"], r["error"])
            gap_of_point = _point_gap_indices(sys_obj, r["points"],
                                              events)
            cum = _path_opl_cumulative(
                r["points"], [media[g] for g in gap_of_point])
            series[r["key"]] = {ev["surface"]: cum[ev["path_idx"]]
                                for ev in events}
        keys = [r["key"] for r in rays]
        rows = []
        for i in range(len(sys_obj.surfaces)):
            row = {"n": i + 1}
            for key in keys:
                row[f"opl_{key}"] = series[key].get(i)
            rows.append(row)
        return {"wl": wl_eff, "field_y": field_y, "keys": keys,
                "rows": sanitize_json(rows)}

    @registry.command(
        "tracex.opl.summary", category="tracex",
        description="Сводка длины пути и ОПС габаритных лучей до плоскости "
                "изображения + ОПД относительно главного луча (мм и волны)",
        returns="{rays: [{key, label, success, path_length, opl, "
                "d_opl_mm, d_opl_waves}], mean_opl, opd_spread_mm}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_opl_summary(ctx, file, system, lbo_index, lbo_name,
                           field_y, wl):
        from analysis.aberrations import compute_gauge_rays
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rays = compute_gauge_rays(sys_obj, wl=wl_eff, field_y=field_y)
        opl_chief = next((r["opl"] for r in rays
                          if r["key"] == OPL_REFERENCE_KEY
                          and r["success"]), None)
        out_rays = []
        for r in rays:
            d_mm = (r["opl"] - opl_chief
                    if opl_chief is not None and r["success"] else None)
            out_rays.append({
                "key": r["key"], "label": r["label"],
                "success": r["success"], "error": r["error"],
                "path_length": r["path_length"], "opl": r["opl"],
                "d_opl_mm": d_mm,
                "d_opl_waves": (d_mm / (wl_eff * 1e-3)
                                if d_mm is not None else None)})
        opds = [r["d_opl_mm"] for r in out_rays
                if r["d_opl_mm"] is not None]
        return {"wl": wl_eff, "field_y": field_y, "rays": out_rays,
                "mean_opl": (sum(r["opl"] for r in out_rays
                                 if r["success"])
                             / max(1, sum(1 for r in out_rays
                                          if r["success"]))),
                "opd_spread_mm": (max(opds) - min(opds)
                                  if len(opds) >= 2 else 0.0)}

    @registry.command(
        "tracex.apertures.fill", category="tracex",
        description="Заполнение полудиаметров поверхностей ходом крайних "
                    "лучей пучка: высоты, доля заполнения, минимально "
                    "необходимый полудиаметр",
        returns="{rows: [{n, semi_diameter, y_upper, y_lower, y_max_abs, "
                "fill_fraction, min_sd_required, violation}]}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_apertures_fill(ctx, file, system, lbo_index, lbo_name,
                              field_y, wl):
        from analysis.aberrations import compute_gauge_rays
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rays = {r["key"]: r for r in
                compute_gauge_rays(sys_obj, wl=wl_eff, field_y=field_y)}
        heights = {}
        for key in ("upper", "lower"):
            r = rays[key]
            heights[key] = {ev["surface"]: ev["point"][1]
                            for ev in _ray_events(
                                sys_obj, r["points"], r["error"])[0]}
        rows = []
        for i, s in enumerate(sys_obj.surfaces):
            y_u = heights["upper"].get(i)
            y_l = heights["lower"].get(i)
            y_max = (max(abs(v) for v in (y_u, y_l) if v is not None)
                     if y_u is not None or y_l is not None else None)
            sd = s.semi_diameter if s.semi_diameter > 0 else None
            fill = (y_max / sd if y_max is not None and sd else None)
            rows.append({"n": i + 1, "semi_diameter": sd,
                         "y_upper": y_u, "y_lower": y_l,
                         "y_max_abs": y_max, "fill_fraction": fill,
                         "min_sd_required": y_max,
                         "violation": bool(fill is not None
                                           and fill > 1.0)})
        return {"wl": wl_eff, "field_y": field_y,
                "rows": sanitize_json(rows)}

    @registry.command(
        "tracex.pupils.surfaces", category="tracex",
        description="Проекция зрачков на поверхности: высоты главного "
                    "луча (центры зрачков) и полувысоты пучка по "
                    "поверхностям + отрезки входного/выходного зрачка",
        returns="{entrance_pupil_z, exit_pupil_z, epd_mm, rows: [{n, z, "
                "pupil_center_y, dz_to_entrance, dz_to_exit, "
                "semi_height_up, semi_height_low}]}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_pupils_surfaces(ctx, file, system, lbo_index, lbo_name,
                               field_y, wl):
        from analysis.aberrations import compute_gauge_rays
        from optics_engine import paraxial_trace
        from optics_utils import compute_z_positions
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parax = paraxial_trace(sys_obj)
        rays = {r["key"]: r for r in
                compute_gauge_rays(sys_obj, wl=wl_eff, field_y=field_y)}
        heights = {
            key: {ev["surface"]: ev["point"][1] for ev in _ray_events(
                sys_obj, rays[key]["points"], rays[key]["error"])[0]}
            for key in ("upper", "lower", "chief")}
        z_pos = compute_z_positions(sys_obj)
        z_exit = (z_pos[-2] + parax.get("sP_prime", 0.0)
                  if len(z_pos) > 1 else parax.get("sP_prime", 0.0))
        z_entrance = parax.get("sP", 0.0)
        rows = []
        for i in range(len(sys_obj.surfaces)):
            y_c = heights["chief"].get(i)
            y_u, y_l = heights["upper"].get(i), heights["lower"].get(i)
            rows.append({
                "n": i + 1, "z": z_pos[i], "pupil_center_y": y_c,
                "dz_to_entrance": z_entrance - z_pos[i],
                "dz_to_exit": z_exit - z_pos[i],
                "semi_height_up": (y_u - y_c
                                   if y_u is not None and y_c is not None
                                   else None),
                "semi_height_low": (y_l - y_c
                                    if y_l is not None and y_c is not None
                                    else None)})
        return {"wl": wl_eff, "field_y": field_y,
                "entrance_pupil_z": z_entrance, "exit_pupil_z": z_exit,
                "epd_mm": parax.get("entrance_pupil_diameter"),
                "rows": sanitize_json(rows)}

    @registry.command(
        "tracex.exit.cone", category="tracex",
        description="Выходной конус пучка: углы крайних лучей в "
                    "пространстве изображений, диаметр пучка на "
                    "изображении, NA' и рабочее F/# (сравнение с "
                    "параксиальным)",
        returns="{u_upper_deg, u_lower_deg, half_angle_deg, "
                "beam_diameter_mm, na_prime, f_number_real, "
                "f_number_paraxial}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_exit_cone(ctx, file, system, lbo_index, lbo_name,
                         field_y, wl):
        from analysis.aberrations import compute_gauge_rays
        from optics_engine import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rays = {r["key"]: r for r in
                compute_gauge_rays(sys_obj, wl=wl_eff, field_y=field_y)}
        up, low = rays["upper"], rays["lower"]

        def _last_angle(r):
            if not r["directions"]:
                return None
            return _slope_deg(r["directions"][-1])[0]

        def _img_y(r):
            img = _ray_events(sys_obj, r["points"], r["error"])[1]
            return img[1] if img else None

        u_up, u_low = _last_angle(up), _last_angle(low)
        half = (abs(u_up - u_low) / 2.0
                if u_up is not None and u_low is not None else None)
        y_up, y_low = _img_y(up), _img_y(low)
        diameter = (abs(y_up - y_low)
                    if y_up is not None and y_low is not None else None)
        n_img = _gap_media(sys_obj, wl_eff)[-1]
        na = (n_img * math.sin(math.radians(half))
              if half is not None else None)
        f_real = (1.0 / (2.0 * math.tan(math.radians(half)))
                  if half is not None and abs(half) > 1e-9 else None)
        return {"wl": wl_eff, "field_y": field_y,
                "u_upper_deg": u_up, "u_lower_deg": u_low,
                "half_angle_deg": half,
                "beam_diameter_mm": diameter, "na_prime": na,
                "f_number_real": f_real,
                "f_number_paraxial": paraxial_trace(sys_obj).get(
                    "f_number")}

    # ----------------------------------------------------------
    # Поверхности / среды
    # ----------------------------------------------------------

    @registry.command(
        "tracex.surface.vertices", category="tracex",
        description="Таблица вершин поверхностей: Z-координаты, расстояния "
                    "между вершинами, радиусы, стёкла, полудиаметры, "
                    "длина хода нарастающим итогом",
        returns="{rows: [{n, z_vertex, radius, glass, semi_diameter, "
                "thickness, dz_to_next, track_cum}], total_track_mm}",
        params=system_source_params())
    def tracex_surface_vertices(ctx, file, system, lbo_index, lbo_name):
        from optics_utils import compute_z_positions
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        z_pos = compute_z_positions(sys_obj)
        rows = []
        for i, s in enumerate(sys_obj.surfaces):
            rows.append({
                "n": i + 1, "z_vertex": z_pos[i], "radius": s.radius,
                "glass": s.glass or "",
                "semi_diameter": (s.semi_diameter if s.semi_diameter > 0
                                  else None),
                "thickness": s.thickness,
                "dz_to_next": z_pos[i + 1] - z_pos[i],
                "track_cum": z_pos[i]})
        return {"total_track_mm": z_pos[-1], "rows": sanitize_json(rows)}

    @registry.command(
        "tracex.surface.glasses", category="tracex",
        description="Таблица сред по поверхностям для трассируемой λ: "
                    "стекло, n до/после, скачок Δn (зеркала — без "
                    "скачка)",
        returns="{rows: [{n, glass, n_before, n_after, dn, reflective}]}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_surface_glasses(ctx, file, system, lbo_index, lbo_name,
                               wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        media = _gap_media(sys_obj, wl_eff)
        rows = []
        for i, s in enumerate(sys_obj.surfaces):
            n1, n2 = media[i], media[i + 1]
            rows.append({"n": i + 1, "glass": s.glass or "",
                         "n_before": n1, "n_after": n2,
                         "dn": (0.0 if s.is_reflective else n2 - n1),
                         "reflective": bool(s.is_reflective)})
        return {"wl": wl_eff, "image_space_n": media[-1],
                "rows": sanitize_json(rows)}

    # ----------------------------------------------------------
    # Сетки и веера: зоны/статистика
    # ----------------------------------------------------------

    @registry.command(
        "tracex.fan.zones", category="tracex",
        description="Меридиональный веер по ЗОНАМ зрачка равной площади "
                    "(1, √((n−1)/n), ...): координаты на изображении и "
                    "поперечная аберрация относительно главного луча",
        returns="{zones: [{rho, success, error, y_img, dy_vs_chief, "
                "opl}]}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("n_zones", type="int", default=FAN_ZONES_DEFAULT,
                  help=f"число зон (по умолчанию {FAN_ZONES_DEFAULT})"),
            Param("zones", type="list",
                  help="явный список зон (доли зрачка, допускаются "
                       "отрицательные; по умолчанию — зоны равной "
                       "площади + главный)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_fan_zones(ctx, file, system, lbo_index, lbo_name,
                         field_y, n_zones, zones, wl):
        from analysis.tables import field_zones
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if zones:
            rho_list = sorted({_mm(v) for v in zones})
        else:
            rho_list = sorted({0.0} | set(field_zones(max(1, n_zones))))
        chief = _trace_pupil_ray(sys_obj, wl_eff, field_y, 0.0, 0.0)
        chief_y = chief.path[-1][1] if chief.success and chief.path \
            else None
        rows = []
        for rho in rho_list:
            result = _trace_pupil_ray(sys_obj, wl_eff, field_y,
                                      0.0, rho)
            y_img = (result.path[-1][1]
                     if result.success and result.path else None)
            rows.append({"rho": rho, "success": result.success,
                         "error": result.error, "y_img": y_img,
                         "dy_vs_chief": (y_img - chief_y
                                         if y_img is not None
                                         and chief_y is not None
                                         else None),
                         "opl": result.opl})
        return {"wl": wl_eff, "field_y": field_y, "zones": rows}

    @registry.command(
        "tracex.grid.stats", category="tracex",
        description="Сводка сетки 3D по кольцам зрачка: доли успеха, "
                    "разбивка по ошибкам трассировки, статистика ОПС и "
                    "разброс точек на изображении",
        returns="{total, success, failed, by_error, opl_min, opl_max, "
                "opl_mean, last_point_rms, max_radius_mm}",
        params=system_source_params([
            Param("num_rings", type="int", default=GRID_RINGS_DEFAULT,
                  help="колец зрачка"),
            Param("num_azimuths", type="int",
                  default=GRID_AZIMUTHS_DEFAULT,
                  help="азимутальных лучей на кольцо"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_grid_stats(ctx, file, system, lbo_index, lbo_name,
                          num_rings, num_azimuths, field_y, wl):
        from analysis.ray_tracing import trace_grid_3d
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rings = trace_grid_3d(sys_obj, num_rings=num_rings,
                              num_azimuths=num_azimuths, wl=wl_eff,
                              field_y=field_y)
        flat = [r for ring in rings for r in ring]
        ok = [r for r in flat if r.success]
        by_error = {}
        for r in flat:
            if not r.success:
                by_error[r.error] = by_error.get(r.error, 0) + 1
        opls = [r.opl for r in ok]
        points = [(r.path[-1][0], r.path[-1][1]) for r in ok if r.path]
        cx = sum(p[0] for p in points) / len(points) if points else 0.0
        cy = sum(p[1] for p in points) / len(points) if points else 0.0
        radii = [math.hypot(p[0] - cx, p[1] - cy) for p in points]
        return {"wl": wl_eff, "field_y": field_y,
                "num_rings": num_rings, "num_azimuths": num_azimuths,
                "total": len(flat), "success": len(ok),
                "failed": len(flat) - len(ok), "by_error": by_error,
                "opl_min": min(opls) if opls else None,
                "opl_max": max(opls) if opls else None,
                "opl_mean": (sum(opls) / len(opls) if opls else None),
                "last_point_rms": (math.sqrt(sum(r * r for r in radii)
                                             / len(radii))
                                   if radii else None),
                "max_radius_mm": max(radii) if radii else None}

    @registry.command(
        "tracex.vignetted.rays", category="tracex",
        description="Срезанные лучи сетки 3D: какие лучи по кольцам/"
                    "азимутам не прошли и на какой ошибке (EDGE — кромка, "
                    "STOP — диафрагма, MISS/TIR)",
        returns="{total, failed, rays: [{rho, phi_deg, error, "
                "surfaces_hit, last_point}]}",
        params=system_source_params([
            Param("num_rings", type="int", default=GRID_RINGS_DEFAULT,
                  help="колец зрачка"),
            Param("num_azimuths", type="int",
                  default=GRID_AZIMUTHS_DEFAULT,
                  help="азимутальных лучей на кольцо"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_vignetted_rays(ctx, file, system, lbo_index, lbo_name,
                              num_rings, num_azimuths, field_y, wl):
        from analysis.ray_tracing import trace_grid_3d
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rings = trace_grid_3d(sys_obj, num_rings=num_rings,
                              num_azimuths=num_azimuths, wl=wl_eff,
                              field_y=field_y)
        rays_out, total = [], 0
        for ring_idx, ring in enumerate(rings):
            rho = 0.0 if ring_idx == 0 else (ring_idx + 1) / num_rings
            for j, r in enumerate(ring):
                total += 1
                if r.success:
                    continue
                last = r.path[-1] if r.path else None
                rays_out.append({
                    "rho": rho,
                    "phi_deg": (0.0 if len(ring) == 1
                                else 360.0 * j / num_azimuths),
                    "error": r.error, "surfaces_hit": r.surfaces_hit,
                    "last_point": ([last[0], last[1], last[2]]
                                   if last else None)})
        return {"wl": wl_eff, "field_y": field_y, "total": total,
                "failed": len(rays_out), "rays": rays_out}

    # ----------------------------------------------------------
    # Параксиальные хвосты
    # ----------------------------------------------------------

    @registry.command(
        "tracex.ynu.table", category="tracex",
        description="ynu-таблица базисных параксиальных лучей по "
                    "поверхностям: y и n·u крайевого (y=1, u=0) и "
                    "главного (y=0, u=1) лучей + кардинальные итоги",
        returns="{start, rows: [{n, y_marginal, nu_marginal, y_chief, "
                "nu_chief}], image, efl, bfd}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_ynu_table(ctx, file, system, lbo_index, lbo_name, wl):
        from optics_engine import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if not sys_obj.surfaces:
            raise CommandError(ERR_INVALID_PARAM,
                               "система без поверхностей")
        marg, chief = _paraxial_basis(sys_obj, wl_eff)
        rows = []
        for i, (sm, sc) in enumerate(zip(marg["surfaces"],
                                         chief["surfaces"])):
            rows.append({"n": i + 1, "y_marginal": sm["y"],
                         "nu_marginal": sm["nu_after"],
                         "y_chief": sc["y"],
                         "nu_chief": sc["nu_after"]})
        parax = paraxial_trace(sys_obj)
        return {"wl": wl_eff,
                "start": {"y_marginal": 1.0, "nu_marginal": 0.0,
                          "y_chief": 0.0, "nu_chief": 1.0},
                "rows": sanitize_json(rows),
                "image": {"y_marginal": marg["image_y"],
                          "nu_marginal": marg["image_nu"],
                          "y_chief": chief["image_y"],
                          "nu_chief": chief["image_nu"]},
                "efl": parax.get("focal_length"),
                "bfd": parax.get("back_focal_distance")}

    @registry.command(
        "tracex.paraxial.ray", category="tracex",
        description="Параксиальная трассировка ПРОИЗВОЛЬНОГО луча "
                    "(y₀, u₀ на первой поверхности) по поверхностям: y, "
                    "n·u и углы до/после преломления",
        returns="{y0, u0_rad, rows: [{n, y, u_before_rad, u_after_rad, "
                "nu_after, n_after, phi}], image_y, image_u_rad}",
        params=system_source_params([
            Param("y0", type="float", default=PARAXIAL_Y0_DEFAULT,
                  help="высота луча на первой поверхности, мм"),
            Param("u0", type="float", default=PARAXIAL_U0_DEFAULT,
                  help="угол с осью в предметном пространстве, радианы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_paraxial_ray(ctx, file, system, lbo_index, lbo_name,
                            y0, u0, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if not sys_obj.surfaces:
            raise CommandError(ERR_INVALID_PARAM,
                               "система без поверхностей")
        state = _paraxial_propagate(sys_obj, wl_eff, _mm(y0), _mm(u0))
        media = state["media"]
        rows = []
        for i, row in enumerate(state["surfaces"]):
            n_b = media[i]
            rows.append({
                "n": i + 1, "y": row["y"],
                "u_before_rad": (row["nu_before"] / n_b
                                 if abs(n_b) > Z_MATCH_TOL else None),
                "u_after_rad": (row["nu_after"] / row["n_after"]
                                if abs(row["n_after"]) > Z_MATCH_TOL
                                else None),
                "nu_after": row["nu_after"],
                "n_after": row["n_after"], "phi": row["phi"]})
        n_exit = media[-1]
        return {"wl": wl_eff, "y0": float(y0), "u0_rad": float(u0),
                "rows": sanitize_json(rows),
                "image_y": state["image_y"],
                "image_u_rad": (state["image_nu"] / n_exit
                                if abs(n_exit) > Z_MATCH_TOL else None)}

    @registry.command(
        "tracex.paraxial.matrices", category="tracex",
        description="ABCD-матрицы параксиального переноса: матрицы "
                    "преломления/отражения по поверхностям, трансляции по "
                    "промежуткам и накопленная матрица системы (efl = "
                    "−1/C, сверка с paraxial_trace)",
        returns="{surfaces: [{n, kind, phi, M}], gaps: [{after_n, d, "
                "n, T}], system_ABCD, det, efl_from_matrix, "
                "efl_paraxial}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_paraxial_matrices(ctx, file, system, lbo_index, lbo_name,
                                 wl):
        from optics_engine import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if not sys_obj.surfaces:
            raise CommandError(ERR_INVALID_PARAM,
                               "система без поверхностей")
        state = _paraxial_propagate(sys_obj, wl_eff, 1.0, 0.0)
        media = state["media"]
        surface_rows, gap_rows = [], []
        # Накопленная матрица (y, nu): v' = M·v
        a, b = 1.0, 0.0
        c, d = 0.0, 1.0
        for i, row in enumerate(state["surfaces"]):
            s = sys_obj.surfaces[i]
            phi = row["phi"]
            # преломление: [[1,0],[-phi,1]] → умножение СЛЕВА
            a, b, c, d = a, b, c - phi * a, d - phi * b
            surface_rows.append({
                "n": i + 1,
                "kind": ("reflect" if s.is_reflective else "refract"),
                "phi": phi, "M": [[1.0, 0.0], [-phi, 1.0]]})
            # трансляция толщины поверхности i: [[1, d/n],[0,1]]
            dd, nn = row["d"], row["n_after"]
            if abs(nn) > Z_MATCH_TOL and dd != 0.0:
                a, b, c, d = a + dd / nn * c, b + dd / nn * d, c, d
                gap_rows.append({"after_n": i + 1, "d": dd, "n": nn,
                                 "T": [[1.0, dd / nn], [0.0, 1.0]]})
        det = a * d - b * c
        efl_matrix = (-1.0 / c if abs(c) > MATRIX_C_TINY else None)
        return {"wl": wl_eff, "surfaces": surface_rows, "gaps": gap_rows,
                "system_ABCD": [[a, b], [c, d]], "det": det,
                "efl_from_matrix": efl_matrix,
                "efl_paraxial": paraxial_trace(sys_obj).get(
                    "focal_length")}

    @registry.command(
        "tracex.paraxial.invariants", category="tracex",
        description="Инвариант Лагранжа-Гельмгольца по промежуткам: "
                    "H = y_гл·(nu)_кр − y_кр·(nu)_гл в каждом промежутке "
                    "(проверка постоянства параксиального переноса)",
        returns="{rows: [{gap, after_n, n_medium, H}], H_min, H_max, "
                "drift}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_paraxial_invariants(ctx, file, system, lbo_index,
                                   lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if not sys_obj.surfaces:
            raise CommandError(ERR_INVALID_PARAM,
                               "система без поверхностей")
        marg, chief = _paraxial_basis(sys_obj, wl_eff)
        media = marg["media"]

        def _states(state):
            """(y, nu) в каждом промежутке: 0 — предметное пространство,
            i — после поверхности i−1 (на входе поверхности i)."""
            pairs = [(1.0 if state is marg else 0.0,
                      0.0 if state is marg else 1.0)]  # старт базиса
            for row in state["surfaces"]:
                pairs.append((row["y"], row["nu_after"]))
            return pairs

        m_states, c_states = _states(marg), _states(chief)
        rows = []
        for g, (m_pair, c_pair) in enumerate(zip(m_states, c_states)):
            h = c_pair[0] * m_pair[1] - m_pair[0] * c_pair[1]
            rows.append({"gap": g, "after_n": g, "n_medium": media[g],
                         "y_marginal": m_pair[0], "nu_marginal": m_pair[1],
                         "y_chief": c_pair[0], "nu_chief": c_pair[1],
                         "H": h})
        values = [r["H"] for r in rows]
        return {"wl": wl_eff, "rows": sanitize_json(rows),
                "H_min": min(values), "H_max": max(values),
                "drift": max(values) - min(values)}

    @registry.command(
        "tracex.paraxial.gaps", category="tracex",
        description="Параксиальный ход пучка по промежуткам: высота "
                    "крайевого луча на границах, угол, диаметр пучка, "
                    "увеличение промежутка (масштаб — реальный зрачок)",
        returns="{scale_mm, rows: [{gap, after_n, d, n, y_start, "
                "y_end, u_deg, beam_diameter, magnification}]}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def tracex_paraxial_gaps(ctx, file, system, lbo_index, lbo_name, wl):
        from optics_engine import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if not sys_obj.surfaces:
            raise CommandError(ERR_INVALID_PARAM,
                               "система без поверхностей")
        marg, _chief = _paraxial_basis(sys_obj, wl_eff)
        media = marg["media"]
        # Масштаб реального пучка: базисный луч y=1 на первой
        # поверхности; реальный крайний луч проходит край диафрагмы
        # (радиус epd/2 в её плоскости). Приведение — через высоту
        # базисного луча в плоскости диафрагмы (линейность параксиальной
        # оптики); если плоскость вне хода — пучок на входе = epd/2.
        parax = paraxial_trace(sys_obj)
        base_radius = (parax.get("entrance_pupil_diameter") or
                       get_effective_aperture(sys_obj, default=10.0)) / 2.0
        z_stop = parax.get("stop_z", 0.0)
        h_stop, z_run = None, 0.0
        for i, row in enumerate(marg["surfaces"]):
            n_here = media[i + 1]
            span_end = z_run + row["d"]
            if z_run - Z_MATCH_TOL <= z_stop <= span_end + Z_MATCH_TOL \
                    and abs(n_here) > Z_MATCH_TOL:
                h_stop = row["y"] + row["nu_after"] / n_here * (
                    z_stop - z_run)
                break
            z_run = span_end
        if h_stop is None or abs(h_stop) < Z_MATCH_TOL:
            scale = base_radius
        else:
            scale = base_radius / abs(h_stop)
        rows = []
        y_prev = marg["surfaces"][0]["y"] * scale
        for i, row in enumerate(marg["surfaces"]):
            n_here = media[i + 1]
            d = row["d"]
            y_end = (marg["surfaces"][i + 1]["y"] * scale
                     if i + 1 < len(marg["surfaces"])
                     else marg["image_y"] * scale)
            u_deg = (math.degrees(math.atan(row["nu_after"] / n_here))
                     if abs(n_here) > Z_MATCH_TOL else None)
            rows.append({
                "gap": i + 1, "after_n": i + 1, "d": d, "n": n_here,
                "y_start": y_prev, "y_end": y_end, "u_deg": u_deg,
                "beam_diameter": (2.0 * abs(y_end)
                                  if y_end is not None else None),
                "magnification": (y_end / y_prev
                                  if y_end is not None and y_prev
                                  and abs(y_prev) > Z_MATCH_TOL else None)})
            y_prev = y_end
        return {"wl": wl_eff, "scale_mm": scale,
                "rows": sanitize_json(rows)}
