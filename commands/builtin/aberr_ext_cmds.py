"""
OPAL-OKB — Пакет R500-17: хвосты анализа аберраций (aberx.*).

ПОЛЕВЫЕ, ЗОНАЛЬНЫЕ И ХРОМАТИЧЕСКИЕ РАЗРЕЗЫ АБЕРРАЦИЙ, которых нет ни в
Волнах 1/3 (``analyze.field_aberrations``/``aber.*``/``chrom.*``/
``seidel.*``), ни в R500-7..16: карта поперечных аберраций поле×зона
(мер/саг), меридиональная волновая W(ρ) по полям, решётки поле×λ
(СКВ волнового, пятна), PV волнового по полям, кривая дисторсии с
полиномиальным фитом, кривые астигматизма/фокальных поверхностей,
зонные фокусы Z(±ρ) (танг/саг), эмпирическая кривизна Петцваля против
1/SIV, осевой хроматизм (BFD/EFL по λ), хроматизм увеличения (главный
луч по λ), хроматическая волновая разность dW(λ), веер по всем λ,
кома-веер по зонам и кривая комы по полям, продольная сферическая по
зонам с фитом ds ≈ c₂ρ²+c₄ρ⁴, апертурная зависимость краевой
аберрации, таблица поперечных по зонам равной площади, boresight
(центроид против главного луча), лучший дефокус по полям с хроматическим
сдвигом, вклады поверхностей в суммы Зейделя SI..SV (проценты).

Префикс ``aberx`` (а не ``aber``): состав домена «АБЕРРАЦИИ» Волны 3
закреплён пином ``tests/test_commands_aber.py`` (``DOMAIN_COMMANDS`` —
31 команда с точными категориями aber/chrom/seidel/adv) — новые
команды категорию ``aber`` не занимают (как ``tracex`` в П16).

Движки не дублируются: веера/пятна/волновой фронт —
``analysis.aberrations`` (``compute_oblique_fan`` → [ρ, dy_мер мкм,
dy_саг мкм], ``trace_aberration_fan`` → {pupil_y, dy, ds, wave},
``trace_wavefront_hexapolar``, ``compute_spot_diagram``,
``compute_spot_diagram_at_defocus``, ``compute_rms_spot_xy``,
``coddington_trace``, ``caustic_radii``), построители лучей поля —
``_field_chief_ray``/``_pupil_field_ray``/``_compute_ray_start`` (те
же, что у габаритных лучей TABESB), параксиал по λ —
``domain.calculations.paraxial_trace(wl=...)``, суммы Зейделя —
``analysis.seidel_check.seidel_sums`` + базис ``_paraxial_auxiliary``,
зоны равной площади — ``analysis.tables.field_zones``, фиты —
``numpy.polyfit``. Собственные хелперы модуля — точка изображения
главного луча поля, конец луча по зрачковой координате и пер-поверхностные
вклады Зейделя (движок ``seidel_sums`` отдаёт только итоги; формулы
поверхностей — FORMULAS.md §Зейдель, паритет с движком проверяется
тестом).
"""
import copy
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

# Поля/λ/TINY — общие хелперы пакетов R500 (правило №1).
from commands.builtin._r500_common import TINY
from commands.builtin._r500_common import fields_arg as _fields_arg
from commands.builtin._r500_common import wls_arg as _wls_arg

# ============================================================
# Именованные константы пакета
# ============================================================

#: Лучей веера по умолчанию (нечётное: ρ=0 — главный луч в сетке).
FAN_RAYS_DEFAULT = 9

#: Зон равной площади по умолчанию (таблицы TABGL/TABOC).
ZONES_DEFAULT = 3

#: Колец гексаполярной сетки зрачка по умолчанию (3 → 37 точек).
NUM_RINGS_DEFAULT = 3

#: Лучей по стороне сетки пятна по умолчанию.
SPOT_RAYS_DEFAULT = 15

#: Степень полинома дисторсии по полю (классика: k₃·f³ + k₅·f⁵).
DISTORTION_FIT_DEGREE = 3

#: Диапазон скана лучшего фокуса (± мм от плоскости изображения).
#: Демо-системы имеют продольную сферическую ~2 мм — диапазон должен
#: накрывать фактический лучший фокус, иначе минимум ложится на край
#: сетки (флаг ``best_at_boundary``).
DEFOCUS_RANGE_DEFAULT = 3.0

#: Точек скана лучшего фокуса.
DEFOCUS_POINTS_DEFAULT = 9

#: Доли зрачка зонных фокусов Z(±ρ) по умолчанию.
ZONAL_FRACTIONS_DEFAULT = (0.25, 0.5, 0.75, 1.0)

#: Отношение T/S комы 3-го порядка (тангенциальная = 3 сагиттальная).
COMA_TANGENTIAL_OVER_SAGITTAL = 3.0

#: Число членов фита продольной сферической (ds ≈ c₂·ρ² + c₄·ρ⁴).
SPHERICAL_FIT_TERMS = 2

#: Зона классической оценки сферической (луч 0.707 — площадь 1/2).
SPHERICAL_ZONAL_RHO = 0.7071

#: Порог «разумного» продольного отрезка для фита сферической (мм):
#: зоны с вырожденным наклоном у фокуса дают |ds|→∞ — из фита
#: исключаются, в таблице остаются.
DS_SANE_MM = 1.0e4

#: Перевод мм → мкм.
UM_PER_MM = 1000.0


# ============================================================
# Общие аргументы-списки и лучевые хелперы пакета
# ============================================================


def _chief_image_point(system, wl: float, field_y: float):
    """Точка изображения главного луча поля ``(x, y)`` или ``None``.

    Построитель — ``aberrations._field_chief_ray`` (тот же, что у
    следа Коддингтона и каустик); трассировка — точный трейсер.
    """
    from analysis.aberrations import _compute_ray_start, _field_chief_ray
    from analysis.ray_tracing import trace_ray_through_system
    from optics_engine import paraxial_trace
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)
    chief = _field_chief_ray(system, field_y, z_start, z_pupil)
    result = trace_ray_through_system(system, chief, wl)
    if result.success and result.path:
        last = result.path[-1]
        return (last[0], last[1])
    return None


def _pupil_ray_result(system, wl: float, field_y: float,
                      rho_x: float, rho_y: float):
    """``TraceResult`` луча поля через зрачковую координату.

    ``rho_x/rho_y`` — доли полуапертуры; построитель
    ``aberrations._pupil_field_ray`` (как ``compute_gauge_rays``/TABESB).
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


def _pupil_ray_end(system, wl: float, field_y: float,
                   rho_x: float, rho_y: float):
    """Конечная точка луча поля через зрачковую координату или ``None``."""
    result = _pupil_ray_result(system, wl, field_y, rho_x, rho_y)
    if result.success and result.path:
        return result.path[-1]
    return None


def _round6(value: float) -> float:
    """Ключ сопоставления точек зрачка между λ (гексаполярная сетка
    воспроизводится детерминированно — округление до 1e-6)."""
    return round(float(value), 6)


def _paraxial_image_height(system, field_y: float) -> float:
    """Параксиальная высота изображения (Гаусс): f′·tan σ / высота предмета.

    Конвенция ``compute_field_aberrations`` /
    ``compute_chief_ray_characteristics`` (единый источник формулы).
    """
    from optics_engine import ObjectType, paraxial_trace
    efl = paraxial_trace(system).get("focal_length", 0.0)
    if system.object_type == ObjectType.INFINITE and abs(efl) > TINY:
        return efl * math.tan(math.radians(field_y))
    return float(field_y)


def _rms(values) -> "float | None":
    """СКВ по списку (None → None)."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return math.sqrt(sum(v * v for v in vals) / len(vals))


def _fan_guard(num_rays: int) -> int:
    """Веер ≥ 3 лучей (пары ±ρ и центр)."""
    n = int(num_rays)
    if n < 3:
        raise CommandError(ERR_INVALID_PARAM,
                           "num_rays ≥ 3 (нужны пары ±ρ и центр веера)")
    return n


def _defocus_grid(defocus_range: float, num_points: int) -> list:
    """Равномерная сетка дефокуса ±range (num_points ≥ 2)."""
    if defocus_range <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "defocus_range должен быть > 0")
    if num_points < 2:
        raise CommandError(ERR_INVALID_PARAM, "num_points ≥ 2")
    return [-defocus_range + 2.0 * defocus_range * i / (num_points - 1)
            for i in range(num_points)]


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать команды пакета R500-17 (aberx.*)."""

    # ----------------------------------------------------------
    # Карты поле × зона / поле × λ
    # ----------------------------------------------------------

    @registry.command(
        "aberx.map.grid", category="aberx",
        description="Карта поперечных аберраций поле×зона: матрица dy "
                    "меридионального и сагиттального сечений по зонам "
                    "зрачка (мкм, относительно главного луча)",
        returns="{wl, num_rays, rows: [{field_y, rho, dy_mer_um, "
                "dy_sag_um}], by_field: [{field_y, rms_dy_mer_um, "
                "max_dy_mer_um, rms_dy_sag_um, max_dy_sag_um, failed}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help=f"лучей веера в сечении (≥3; по умолчанию "
                       f"{FAN_RAYS_DEFAULT})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_map_grid(ctx, file, system, lbo_index, lbo_name,
                       fields, num_rays, wl):
        from analysis.aberrations import compute_oblique_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        n_fan = _fan_guard(num_rays)
        rows, by_field = [], []
        for field in _fields_arg(sys_obj, fields):
            rho_m, dy_mer, _ = compute_oblique_fan(
                sys_obj, wl=wl_eff, num_rays=n_fan, field_y=field,
                azimuth_deg=0.0)
            _, _, dy_sag = compute_oblique_fan(
                sys_obj, wl=wl_eff, num_rays=n_fan, field_y=field,
                azimuth_deg=90.0)
            for rho, d_mer, d_sag in zip(rho_m, dy_mer, dy_sag):
                rows.append({"field_y": field, "rho": rho,
                             "dy_mer_um": d_mer, "dy_sag_um": d_sag})
            mer_ok = [v for v in dy_mer if v is not None]
            sag_ok = [v for v in dy_sag if v is not None]
            by_field.append({
                "field_y": field,
                "rms_dy_mer_um": _rms(dy_mer),
                "max_dy_mer_um": (max(abs(v) for v in mer_ok)
                                  if mer_ok else None),
                "rms_dy_sag_um": _rms(dy_sag),
                "max_dy_sag_um": (max(abs(v) for v in sag_ok)
                                  if sag_ok else None),
                "failed_mer": n_fan - len(mer_ok),
                "failed_sag": n_fan - len(sag_ok)})
        return {"wl": wl_eff, "num_rays": n_fan,
                "rows": sanitize_json(rows),
                "by_field": sanitize_json(by_field)}

    @registry.command(
        "aberx.wf.rho", category="aberx",
        description="Меридиональная волновая аберрация W(ρ) по полям: "
                    "карта поле×зона (W в длинах волн, ноль отсчёта — "
                    "главный луч, опорная сфера в параксиальном фокусе)",
        returns="{wl, num_rays, rows: [{field_y, rho, wave}], by_field: "
                "[{field_y, pv, rms, n_points}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help=f"лучей веера (≥3; по умолчанию {FAN_RAYS_DEFAULT})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_wf_rho(ctx, file, system, lbo_index, lbo_name,
                     fields, num_rays, wl):
        from analysis.aberrations import trace_aberration_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        n_fan = _fan_guard(num_rays)
        rows, by_field = [], []
        for field in _fields_arg(sys_obj, fields):
            fan = trace_aberration_fan(sys_obj, wl_eff,
                                       num_rays=n_fan, field_y=field)
            waves = [r["wave"] for r in fan if r["success"]]
            for r in fan:
                rows.append({"field_y": field, "rho": r["pupil_y"],
                             "wave": r["wave"] if r["success"] else None})
            by_field.append({
                "field_y": field,
                "pv": (max(waves) - min(waves) if waves else None),
                "rms": (_rms([w - sum(waves) / len(waves) for w in waves])
                        if waves else None),
                "n_points": len(waves)})
        return {"wl": wl_eff, "num_rays": n_fan,
                "rows": sanitize_json(rows),
                "by_field": sanitize_json(by_field)}

    @registry.command(
        "aberx.rms.grid", category="aberx",
        description="Решётка «поле × λ → СКВ волновой аберрации» "
                    "(гексаполярная сетка зрачка, СКВ от среднего по "
                    "зрачку, в длинах волн)",
        returns="{rows: [{field_y, wl, rms_wl, n_points}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wls", type="list",
                  help="список λ, мкм; по умолчанию — рабочие λ системы"),
            Param("num_rings", type="int", default=NUM_RINGS_DEFAULT,
                  help=f"колец гексаполярной сетки (по умолчанию "
                       f"{NUM_RINGS_DEFAULT})"),
        ]))
    def aberx_rms_grid(ctx, file, system, lbo_index, lbo_name,
                       fields, wls, num_rings):
        from analysis.aberrations import trace_wavefront_hexapolar
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            for wl in _wls_arg(sys_obj, wls):
                points = trace_wavefront_hexapolar(
                    sys_obj, wl=wl, field_y=field,
                    num_rings=int(num_rings))
                ws = [w for _, _, w in points]
                if ws:
                    mean_w = sum(ws) / len(ws)
                    rms = math.sqrt(
                        sum((w - mean_w) ** 2 for w in ws) / len(ws))
                else:
                    rms = None
                rows.append({"field_y": field, "wl": wl,
                             "rms_wl": rms, "n_points": len(ws)})
        return {"num_rings": int(num_rings), "rows": sanitize_json(rows)}

    @registry.command(
        "aberx.wf.pv", category="aberx",
        description="Пик-валлей волновой аберрации по полям: min/max/W_pv/"
                    "среднее/СКВ на гексаполярной сетке зрачка + худшее "
                    "поле по PV",
        returns="{wl, num_rings, rows: [{field_y, w_min, w_max, pv, mean, "
                "rms, n_points}], worst_field, worst_pv}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rings", type="int", default=NUM_RINGS_DEFAULT,
                  help="колец гексаполярной сетки зрачка"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_wf_pv(ctx, file, system, lbo_index, lbo_name,
                    fields, num_rings, wl):
        from analysis.aberrations import trace_wavefront_hexapolar
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            points = trace_wavefront_hexapolar(
                sys_obj, wl=wl_eff, field_y=field,
                num_rings=int(num_rings))
            ws = [w for _, _, w in points]
            if not ws:
                rows.append({"field_y": field, "w_min": None,
                             "w_max": None, "pv": None, "mean": None,
                             "rms": None, "n_points": 0})
                continue
            mean_w = sum(ws) / len(ws)
            rows.append({
                "field_y": field, "w_min": min(ws), "w_max": max(ws),
                "pv": max(ws) - min(ws), "mean": mean_w,
                "rms": math.sqrt(
                    sum((w - mean_w) ** 2 for w in ws) / len(ws)),
                "n_points": len(ws)})
        valid = [r for r in rows if r["pv"] is not None]
        if not valid:
            raise CommandError(ERR_INVALID_PARAM,
                               "волновой фронт не трассируется ни на одном "
                               "поле")
        worst = max(valid, key=lambda r: r["pv"])
        return {"wl": wl_eff, "num_rings": int(num_rings),
                "rows": sanitize_json(rows),
                "worst_field": worst["field_y"], "worst_pv": worst["pv"]}

    # ----------------------------------------------------------
    # Дисторсия / астигматизм / Петцваль
    # ----------------------------------------------------------

    @registry.command(
        "aberx.distortion.curve", category="aberx",
        description="Кривая дисторсии по полям: высота главного луча, "
                    "гауссова высота, абсолютная/относительная дисторсия "
                    "+ полиномиальный фит dist(f) с максимальной "
                    "невязкой",
        returns="{wl, efl, rows: [{field_y, y_chief_mm, y_parax_mm, "
                "dist_abs_mm, dist_pct}], fit: {degree, coeffs, "
                "resid_max_pct} | null}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("fit_degree", type="int", default=DISTORTION_FIT_DEGREE,
                  help=f"степень полинома дисторсии (по умолчанию "
                       f"{DISTORTION_FIT_DEGREE})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_distortion_curve(ctx, file, system, lbo_index, lbo_name,
                               fields, fit_degree, wl):
        import numpy as np
        from optics_engine import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        degree = int(fit_degree)
        if degree < 1:
            raise CommandError(ERR_INVALID_PARAM, "fit_degree ≥ 1")
        efl = paraxial_trace(sys_obj).get("focal_length", 0.0)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            point = _chief_image_point(sys_obj, wl_eff, field)
            y_parax = _paraxial_image_height(sys_obj, field)
            if point is None:
                rows.append({"field_y": field, "y_chief_mm": None,
                             "y_parax_mm": y_parax, "dist_abs_mm": None,
                             "dist_pct": None})
                continue
            y_chief = point[1]
            dist_abs = y_chief - y_parax
            rows.append({
                "field_y": field, "y_chief_mm": y_chief,
                "y_parax_mm": y_parax, "dist_abs_mm": dist_abs,
                "dist_pct": (dist_abs / y_parax * 100.0
                             if abs(y_parax) > TINY else None)})
        fit = None
        pts = [(r["field_y"], r["dist_pct"] if r["dist_pct"] is not None
                else 0.0) for r in rows if r["field_y"] != 0.0]
        # Точка (0, 0) — легитимный якорь фита: дисторсия на оси
        # тождественно нуль. Степень адаптивно понижается до числа
        # точек − 1 (запрошенная имеет смысл только на густой сетке).
        pts = [(0.0, 0.0)] + pts
        degree_eff = min(degree, len(pts) - 1)
        if degree_eff >= 1:
            xs = np.array([p[0] for p in pts], dtype=float)
            ys = np.array([p[1] for p in pts], dtype=float)
            coeffs_desc = np.polyfit(xs, ys, degree_eff)
            resid = ys - np.polyval(coeffs_desc, xs)
            fit = {
                "degree": degree_eff,
                # коэффициенты по возрастанию степени (c0 + c1·f + ...)
                "coeffs": [float(c) for c in coeffs_desc[::-1]],
                "resid_max_pct": float(np.max(np.abs(resid)))}
        return {"wl": wl_eff, "efl": efl, "rows": sanitize_json(rows),
                "fit": sanitize_json(fit)}

    @registry.command(
        "aberx.astig.curve", category="aberx",
        description="Кривая астигматизма по полям: отрезки Z'm/Z's "
                    "следа Коддингтона (мм от плоскости Гаусса), "
                    "разность Z'm−Z's, худшее поле",
        returns="{wl, rows: [{field_y, delta_zm, delta_zs, astigmatism, "
                "t_m, t_s}], worst: {field_y, astigmatism} | null}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_astig_curve(ctx, file, system, lbo_index, lbo_name,
                          fields, wl):
        from analysis.aberrations import coddington_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            cod = coddington_trace(sys_obj, wl=wl_eff, field_y=field)
            rows.append({
                "field_y": field,
                "delta_zm": cod.get("delta_zm"),
                "delta_zs": cod.get("delta_zs"),
                "astigmatism": cod.get("astigmatism"),
                "t_m": cod.get("t_m"), "t_s": cod.get("t_s")})
        valid = [r for r in rows if r["astigmatism"] is not None
                 and r["field_y"] != 0.0]
        worst = None
        if valid:
            w = max(valid, key=lambda r: abs(r["astigmatism"]))
            worst = {"field_y": w["field_y"],
                     "astigmatism": w["astigmatism"]}
        return {"wl": wl_eff, "rows": sanitize_json(rows),
                "worst": sanitize_json(worst)}

    @registry.command(
        "aberx.petzval.check", category="aberx",
        description="Кривизна поля Петцваля из хода: поверхность "
                    "Петцваля z_p = (3·Z's − Z'm)/2 по полям (третий "
                    "порядок: танг. = z_p + 3A/2, саг. = z_p + A/2), "
                    "эмпирический радиус из фита z_p ≈ z₀ + y²/(2R) "
                    "против −1/SIV сумм Зейделя",
        returns="{wl, rows: [{field_y, y_img_mm, z_petzval}], "
                "petzval_radius_empirical_mm, petzval_radius_seidel_mm, "
                "SIV, deviation_pct} | null-поля при нехватке поля",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей (нужно ≥2 внеосевых); по умолчанию "
                       "— поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_petzval_check(ctx, file, system, lbo_index, lbo_name,
                            fields, wl):
        import numpy as np
        from analysis.aberrations import coddington_trace
        from domain.calculations import seidel_aberrations
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            cod = coddington_trace(sys_obj, wl=wl_eff, field_y=field)
            zm, zs = cod.get("delta_zm"), cod.get("delta_zs")
            point = _chief_image_point(sys_obj, wl_eff, field)
            rows.append({
                "field_y": field,
                "y_img_mm": (point[1] if point else None),
                "z_petzval": ((3.0 * zs - zm) / 2.0
                              if zm is not None and zs is not None
                              else None)})
        pts = [(r["y_img_mm"], r["z_petzval"]) for r in rows
               if r["y_img_mm"] is not None and r["z_petzval"] is not None
               and abs(r["y_img_mm"]) > TINY and r["field_y"] != 0.0]
        r_emp = None
        if len(pts) >= 2:
            y2 = np.array([p[0] ** 2 for p in pts], dtype=float)
            zz = np.array([p[1] for p in pts], dtype=float)
            slope, _intercept = np.polyfit(y2, zz, 1)
            if abs(slope) > TINY:
                # Сагитта сферы: z(y) = y²/(2R) ⇒ R = 1/(2·slope).
                r_emp = 1.0 / (2.0 * float(slope))
        sums = seidel_aberrations(sys_obj)
        s4 = sums["SIV"]
        # Знак: SIV = 1/R_p в конвенции Зейделя, сагитта поверхности
        # Петцваля z = −y²·SIV/2 — сверка с −1/SIV.
        r_seidel = (-1.0 / s4 if abs(s4) > TINY else None)
        deviation = None
        if r_emp is not None and r_seidel is not None:
            deviation = (abs(r_emp - r_seidel) / abs(r_seidel) * 100.0)
        return {"wl": wl_eff, "rows": sanitize_json(rows),
                "petzval_radius_empirical_mm": r_emp,
                "petzval_radius_seidel_mm": r_seidel, "SIV": s4,
                "deviation_pct": sanitize_json(deviation)}

    # ----------------------------------------------------------
    # Хроматические разрезы
    # ----------------------------------------------------------

    @registry.command(
        "aberx.chrom.focus_shift", category="aberx",
        description="Осевой хроматизм: параксиальные EFL/BFD по каждой "
                    "рабочей λ, сдвиги относительно основной λ и полный "
                    "разброс (вторичный спектр, мм)",
        returns="{wl_ref, rows: [{wl, efl_mm, bfd_mm, d_efl_mm, "
                "d_bfd_mm}], efl_spread_mm, bfd_spread_mm}",
        params=system_source_params([
            Param("wls", type="list",
                  help="список λ, мкм; по умолчанию — рабочие λ системы"),
        ]))
    def aberx_chrom_focus_shift(ctx, file, system, lbo_index, lbo_name,
                                wls):
        from domain.calculations import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_ref = get_primary_wl(sys_obj)
        base = paraxial_trace(sys_obj, wl=wl_ref)
        rows = []
        for wl in _wls_arg(sys_obj, wls):
            parax = paraxial_trace(sys_obj, wl=wl)
            rows.append({
                "wl": wl,
                "efl_mm": parax.get("focal_length"),
                "bfd_mm": parax.get("back_focal_distance"),
                "d_efl_mm": (parax.get("focal_length", 0.0)
                             - base.get("focal_length", 0.0)),
                "d_bfd_mm": (parax.get("back_focal_distance", 0.0)
                             - base.get("back_focal_distance", 0.0))})
        efls = [r["efl_mm"] for r in rows if r["efl_mm"] is not None]
        bfds = [r["bfd_mm"] for r in rows if r["bfd_mm"] is not None]
        return {"wl_ref": wl_ref, "rows": sanitize_json(rows),
                "efl_spread_mm": (max(efls) - min(efls)
                                  if len(efls) >= 2 else 0.0),
                "bfd_spread_mm": (max(bfds) - min(bfds)
                                  if len(bfds) >= 2 else 0.0)}

    @registry.command(
        "aberx.chrom.magnification", category="aberx",
        description="Хроматизм увеличения: высота главного луча по λ на "
                    "каждом поле, сдвиг dy против основной λ, "
                    "относительное увеличение и поперечный хроматизм "
                    "по полю",
        returns="{wl_ref, rows: [{field_y, wl, y_chief_mm, dy_vs_ref_mm, "
                "magnification_rel}], by_field: [{field_y, "
                "lateral_color_mm, lateral_color_pct}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wls", type="list",
                  help="список λ, мкм; по умолчанию — рабочие λ системы"),
        ]))
    def aberx_chrom_magnification(ctx, file, system, lbo_index,
                                  lbo_name, fields, wls):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_ref = get_primary_wl(sys_obj)
        wl_list = _wls_arg(sys_obj, wls)
        rows, by_field = [], []
        for field in _fields_arg(sys_obj, fields):
            heights = {}
            for wl in wl_list:
                point = _chief_image_point(sys_obj, wl, field)
                if point is not None:
                    heights[wl] = point[1]
            y_ref = heights.get(wl_ref)
            if y_ref is None:
                y_ref = next(iter(heights.values()), None)
            for wl in wl_list:
                y_chief = heights.get(wl)
                rows.append({
                    "field_y": field, "wl": wl, "y_chief_mm": y_chief,
                    "dy_vs_ref_mm": (y_chief - y_ref
                                     if y_chief is not None
                                     and y_ref is not None else None),
                    "magnification_rel": (y_chief / y_ref
                                          if y_chief is not None
                                          and y_ref
                                          and abs(y_ref) > TINY
                                          else None)})
            values = [v for v in heights.values()]
            by_field.append({
                "field_y": field,
                "lateral_color_mm": (max(values) - min(values)
                                     if len(values) >= 2 else 0.0),
                "lateral_color_pct": (
                    (max(values) - min(values)) / abs(y_ref) * 100.0
                    if len(values) >= 2 and y_ref
                    and abs(y_ref) > TINY else 0.0)})
        return {"wl_ref": wl_ref, "rows": sanitize_json(rows),
                "by_field": sanitize_json(by_field)}

    @registry.command(
        "aberx.wf.chrom", category="aberx",
        description="Хроматическая волновая разность dW(λ): волновой "
                    "фронт на гексаполярной сетке для каждой λ против "
                    "основной λ в тех же точках зрачка (длины волн)",
        returns="{wl_ref, num_rings, rows: [{wl, dW_rms, dW_pv, n_points, "
                "points: [[px, py, dW], ...]}]}",
        params=system_source_params([
            Param("field_y", type="float", required=True,
                  help="поле (град / мм)"),
            Param("wls", type="list",
                  help="список λ, мкм; по умолчанию — рабочие λ системы"),
            Param("num_rings", type="int", default=NUM_RINGS_DEFAULT,
                  help="колец гексаполярной сетки зрачка"),
        ]))
    def aberx_wf_chrom(ctx, file, system, lbo_index, lbo_name,
                       field_y, wls, num_rings):
        from analysis.aberrations import trace_wavefront_hexapolar
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_ref = get_primary_wl(sys_obj)
        ref = {(_round6(px), _round6(py)): w
               for px, py, w in trace_wavefront_hexapolar(
                   sys_obj, wl=wl_ref, field_y=field_y,
                   num_rings=int(num_rings))}
        rows = []
        for wl in _wls_arg(sys_obj, wls):
            points, dws = [], []
            for px, py, w in trace_wavefront_hexapolar(
                    sys_obj, wl=wl, field_y=field_y,
                    num_rings=int(num_rings)):
                key = (_round6(px), _round6(py))
                if key not in ref:
                    continue
                dw = w - ref[key]
                dws.append(dw)
                points.append([px, py, dw])
            if dws:
                rms = math.sqrt(sum(d * d for d in dws) / len(dws))
                pv = max(dws) - min(dws)
            else:
                rms, pv = None, None
            rows.append({"wl": wl, "dW_rms": rms, "dW_pv": pv,
                         "n_points": len(dws), "points": points})
        return {"wl_ref": wl_ref, "num_rings": int(num_rings),
                "rows": sanitize_json(rows)}

    @registry.command(
        "aberx.fan.chrom", category="aberx",
        description="Веер сечения по ВСЕМ λ системы на поле: dy "
                    "меридиональная/сагиттальная (мкм, относительно "
                    "главного луча) по зонам ρ и сводка по λ",
        returns="{field_y, azimuth_deg, rows: [{wl, rho, dy_mer_um, "
                "dy_sag_um}], by_wl: [{wl, rms_dy_mer_um, "
                "max_abs_dy_mer_um}]}",
        params=system_source_params([
            Param("field_y", type="float", required=True,
                  help="поле (град / мм)"),
            Param("wls", type="list",
                  help="список λ, мкм; по умолчанию — рабочие λ системы"),
            Param("num_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help=f"лучей веера (≥3; по умолчанию {FAN_RAYS_DEFAULT})"),
            Param("azimuth_deg", type="float", default=0.0,
                  help="азимут сечения (0 — меридиональное, 90 — "
                       "сагиттальное)"),
        ]))
    def aberx_fan_chrom(ctx, file, system, lbo_index, lbo_name,
                        field_y, wls, num_rays, azimuth_deg):
        from analysis.aberrations import compute_oblique_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        n_fan = _fan_guard(num_rays)
        rows, by_wl = [], []
        for wl_i in _wls_arg(sys_obj, wls):
            rho, dy_mer, dy_sag = compute_oblique_fan(
                sys_obj, wl=wl_i, num_rays=n_fan, field_y=field_y,
                azimuth_deg=float(azimuth_deg))
            for r, d_mer, d_sag in zip(rho, dy_mer, dy_sag):
                rows.append({"wl": wl_i, "rho": r,
                             "dy_mer_um": d_mer, "dy_sag_um": d_sag})
            mer_ok = [v for v in dy_mer if v is not None]
            by_wl.append({
                "wl": wl_i,
                "rms_dy_mer_um": _rms(dy_mer),
                "max_abs_dy_mer_um": (max(abs(v) for v in mer_ok)
                                      if mer_ok else None)})
        return {"field_y": field_y, "azimuth_deg": float(azimuth_deg),
                "rows": sanitize_json(rows), "by_wl": sanitize_json(by_wl)}

    # ----------------------------------------------------------
    # Пятна: решётки, boresight, лучший фокус
    # ----------------------------------------------------------

    @registry.command(
        "aberx.spot.grid", category="aberx",
        description="Решётка пятен поле×λ: RMS общий и раздельно по "
                    "меридиональной/сагиттальной осям, отношение осей, "
                    "центроид (числа, не картинка)",
        returns="{num_rays, rows: [{field_y, wl, n_points, rms_total_mm, "
                "rms_x_mm, rms_y_mm, rms_y_over_x, centroid_x_mm, "
                "centroid_y_mm}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wls", type="list",
                  help="список λ, мкм; по умолчанию — рабочие λ системы"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help=f"лучей по стороне сетки (по умолчанию "
                       f"{SPOT_RAYS_DEFAULT})"),
        ]))
    def aberx_spot_grid(ctx, file, system, lbo_index, lbo_name,
                        fields, wls, num_rays):
        from analysis.aberrations import (
            compute_rms_spot_xy,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            for wl in _wls_arg(sys_obj, wls):
                spots = compute_spot_diagram(
                    sys_obj, wl=wl, num_rays=int(num_rays),
                    field_y=field)
                if not spots:
                    rows.append({"field_y": field, "wl": wl,
                                 "n_points": 0, "rms_total_mm": None,
                                 "rms_x_mm": None, "rms_y_mm": None,
                                 "rms_y_over_x": None,
                                 "centroid_x_mm": None,
                                 "centroid_y_mm": None})
                    continue
                xy = compute_rms_spot_xy(spots)
                rows.append({
                    "field_y": field, "wl": wl, "n_points": len(spots),
                    "rms_total_mm": xy["rms_total"],
                    "rms_x_mm": xy["rms_x"], "rms_y_mm": xy["rms_y"],
                    "rms_y_over_x": (xy["rms_y"] / xy["rms_x"]
                                     if xy["rms_x"] > TINY else None),
                    "centroid_x_mm": xy["centroid_x"],
                    "centroid_y_mm": xy["centroid_y"]})
        return {"num_rays": int(num_rays),
                "rows": sanitize_json(rows)}

    @registry.command(
        "aberx.centroid.fields", category="aberx",
        description="Boresight по полям: положение центроида пятна против "
                    "главного луча и параксиальной высоты — смещение "
                    "энергетического центра, абсолютная дисторсия "
                    "главного луча",
        returns="{wl, num_rays, rows: [{field_y, chief_x_mm, chief_y_mm, "
                "centroid_x_mm, centroid_y_mm, centroid_shift_um, "
                "y_parax_mm, dist_abs_mm, dist_pct}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей по стороне сетки"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_centroid_fields(ctx, file, system, lbo_index, lbo_name,
                              fields, num_rays, wl):
        from analysis.aberrations import (
            compute_rms_spot_xy,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            chief = _chief_image_point(sys_obj, wl_eff, field)
            y_parax = _paraxial_image_height(sys_obj, field)
            spots = compute_spot_diagram(
                sys_obj, wl=wl_eff, num_rays=int(num_rays),
                field_y=field)
            xy = (compute_rms_spot_xy(spots) if spots else None)
            shift = None
            if chief is not None and xy is not None:
                shift = math.hypot(xy["centroid_x"] - chief[0],
                                   xy["centroid_y"] - chief[1]) * UM_PER_MM
            rows.append({
                "field_y": field,
                "chief_x_mm": (chief[0] if chief else None),
                "chief_y_mm": (chief[1] if chief else None),
                "centroid_x_mm": (xy["centroid_x"] if xy else None),
                "centroid_y_mm": (xy["centroid_y"] if xy else None),
                "centroid_shift_um": shift,
                "y_parax_mm": y_parax,
                "dist_abs_mm": (chief[1] - y_parax
                                if chief else None),
                "dist_pct": ((chief[1] - y_parax) / y_parax * 100.0
                             if chief and abs(y_parax) > TINY else None)})
        return {"wl": wl_eff, "num_rays": int(num_rays),
                "rows": sanitize_json(rows)}

    @registry.command(
        "aberx.bestfocus.fields", category="aberx",
        description="Наилучший дефокус (минимум RMS пятна) по полям и λ + "
                    "хроматический сдвиг лучшего фокуса между крайними λ "
                    "(полевая кривизна пятна и её хроматизм)",
        returns="{defocus_range, num_points, rows: [{field_y, wl, "
                "best_defocus_mm, min_rms_mm, rms_at_zero_mm, "
                "best_at_boundary}], by_field: [{field_y, "
                "chrom_shift_mm}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wls", type="list",
                  help="список λ, мкм; по умолчанию — только основная"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей по стороне сетки"),
            Param("defocus_range", type="float",
                  default=DEFOCUS_RANGE_DEFAULT,
                  help=f"± мм скана (по умолчанию "
                       f"{DEFOCUS_RANGE_DEFAULT})"),
            Param("num_points", type="int", default=DEFOCUS_POINTS_DEFAULT,
                  help=f"точек скана (по умолчанию "
                       f"{DEFOCUS_POINTS_DEFAULT})"),
        ]))
    def aberx_bestfocus_fields(ctx, file, system, lbo_index, lbo_name,
                               fields, wls, num_rays, defocus_range,
                               num_points):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram_at_defocus,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_list = ([float(w) for w in wls] if wls
                   else [get_primary_wl(sys_obj)])
        grid = _defocus_grid(float(defocus_range), int(num_points))
        rows, by_field = [], []
        for field in _fields_arg(sys_obj, fields):
            best_by_wl = {}
            for wl in wl_list:
                rms_curve = []
                for defocus in grid:
                    spots = compute_spot_diagram_at_defocus(
                        sys_obj, wl=wl, num_rays=int(num_rays),
                        field_y=field, defocus_mm=defocus)
                    rms_curve.append(
                        (defocus, compute_rms_spot(spots), len(spots)))
                if not any(n > 0 for _, _, n in rms_curve):
                    rows.append({"field_y": field, "wl": wl,
                                 "best_defocus_mm": None,
                                 "min_rms_mm": None,
                                 "rms_at_zero_mm": None})
                    continue
                valid = [(d, r) for d, r, n in rms_curve if n > 0]
                best_d, best_r = min(valid, key=lambda p: p[1])
                rms_zero = next((r for d, r in valid if abs(d) < TINY),
                                None)
                best_by_wl[wl] = best_d
                rows.append({"field_y": field, "wl": wl,
                             "best_defocus_mm": best_d,
                             "min_rms_mm": best_r,
                             "rms_at_zero_mm": rms_zero,
                             "best_at_boundary": best_d in (
                                 grid[0], grid[-1])})
            if len(best_by_wl) >= 2:
                values = [best_by_wl[wl] for wl in wl_list
                          if wl in best_by_wl]
                chrom = max(values) - min(values)
            else:
                chrom = 0.0
            by_field.append({"field_y": field, "chrom_shift_mm": chrom})
        return {"defocus_range": float(defocus_range),
                "num_points": int(num_points),
                "rows": sanitize_json(rows),
                "by_field": sanitize_json(by_field)}

    # ----------------------------------------------------------
    # Кома / сферическая / апертурная зависимость
    # ----------------------------------------------------------

    @registry.command(
        "aberx.coma.fan", category="aberx",
        description="Кома-веер по зонам зрачка на поле: асимметрия "
                    "меридионального веера dy(+ρ)+dy(−ρ), тангенциальная "
                    "кома (край) и сагиттальная (из наклонного хода "
                    "сагиттального веера), отношение T/S (3-й порядок: 3)",
        returns="{wl, field_y, num_rays, rows: [{rho, dy_plus_um, "
                "dy_minus_um, asym_um}], tangential_coma_um, "
                "sagittal_coma_um, ratio_t_over_s, "
                "ratio_t_over_s_3rd_order}",
        params=system_source_params([
            Param("field_y", type="float", required=True,
                  help="поле (град / мм)"),
            Param("num_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help=f"лучей веера (≥3; по умолчанию {FAN_RAYS_DEFAULT})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_coma_fan(ctx, file, system, lbo_index, lbo_name,
                       field_y, num_rays, wl):
        from analysis.aberrations import compute_oblique_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        n_fan = _fan_guard(num_rays)
        rho, dy_mer, _ = compute_oblique_fan(
            sys_obj, wl=wl_eff, num_rays=n_fan, field_y=field_y,
            azimuth_deg=0.0)
        _, dy_mer_sag90, _ = compute_oblique_fan(
            sys_obj, wl=wl_eff, num_rays=n_fan, field_y=field_y,
            azimuth_deg=90.0)
        rows = []
        for i in range(n_fan // 2):
            j = n_fan - 1 - i
            d_plus, d_minus = dy_mer[j], dy_mer[i]
            asym = ((d_plus + d_minus) / 2.0
                    if d_plus is not None and d_minus is not None
                    else None)
            rows.append({"rho": abs(rho[j]), "dy_plus_um": d_plus,
                         "dy_minus_um": d_minus, "asym_um": asym})
        t_coma = None
        if dy_mer[0] is not None and dy_mer[-1] is not None:
            t_coma = dy_mer[0] + dy_mer[-1]
        s_coma = dy_mer_sag90[-1] if dy_mer_sag90[-1] is not None else None
        ratio = (t_coma / s_coma if t_coma is not None and s_coma
                 and abs(s_coma) > TINY else None)
        return {"wl": wl_eff, "field_y": field_y, "num_rays": n_fan,
                "rows": sanitize_json(rows),
                "tangential_coma_um": t_coma,
                "sagittal_coma_um": s_coma,
                "ratio_t_over_s": sanitize_json(ratio),
                "ratio_t_over_s_3rd_order": COMA_TANGENTIAL_OVER_SAGITTAL}

    @registry.command(
        "aberx.coma.fields", category="aberx",
        description="Кривая комы по полям: тангенциальная кома "
                    "(dy(+1)+dy(−1) меридионального веера) и "
                    "сагиттальная (край сагиттального веера) по полям, "
                    "мкм",
        returns="{wl, num_rays, rows: [{field_y, t_coma_um, s_coma_um, "
                "ratio_t_over_s}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help=f"лучей веера (≥3; по умолчанию {FAN_RAYS_DEFAULT})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_coma_fields(ctx, file, system, lbo_index, lbo_name,
                          fields, num_rays, wl):
        from analysis.aberrations import compute_oblique_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        n_fan = _fan_guard(num_rays)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            _, dy_mer, _ = compute_oblique_fan(
                sys_obj, wl=wl_eff, num_rays=n_fan, field_y=field,
                azimuth_deg=0.0)
            _, dy_mer_sag90, _ = compute_oblique_fan(
                sys_obj, wl=wl_eff, num_rays=n_fan, field_y=field,
                azimuth_deg=90.0)
            t_coma = (dy_mer[0] + dy_mer[-1]
                      if dy_mer[0] is not None
                      and dy_mer[-1] is not None else None)
            s_coma = (dy_mer_sag90[-1]
                      if dy_mer_sag90[-1] is not None else None)
            rows.append({
                "field_y": field, "t_coma_um": t_coma,
                "s_coma_um": s_coma,
                "ratio_t_over_s": (t_coma / s_coma
                                   if t_coma is not None and s_coma
                                   and abs(s_coma) > TINY else None)})
        return {"wl": wl_eff, "num_rays": n_fan,
                "rows": sanitize_json(rows)}

    @registry.command(
        "aberx.spherical.zones", category="aberx",
        description="Продольная сферическая аберрация по зонам зрачка "
                    "(осевое поле): поперечная dy и продольная ds "
                    "(z-пересечение луча зоны с осью — классическая "
                    "LA) + фит ds ≈ c₂·ρ² + c₄·ρ⁴, отрезки LA края и "
                    "зоны 0.707",
        returns="{wl, field_y, num_rays, rows: [{rho, dy_um, ds_mm}], "
                "fit: {coeffs: [c2, c4], resid_max_mm} | null, "
                "la_edge_mm, la_zonal_mm}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм); осевое — 0"),
            Param("num_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help=f"лучей веера (≥3; по умолчанию {FAN_RAYS_DEFAULT})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_spherical_zones(ctx, file, system, lbo_index, lbo_name,
                              field_y, num_rays, wl):
        import numpy as np
        from analysis.aberrations import trace_aberration_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        n_fan = _fan_guard(num_rays)
        fan = trace_aberration_fan(sys_obj, wl_eff, num_rays=n_fan,
                                   field_y=field_y)
        y_ref = next((r["y_img"] for r in fan
                      if r["success"] and abs(r["pupil_y"]) < TINY),
                     None)
        if y_ref is None:
            chief = _chief_image_point(sys_obj, wl_eff, field_y)
            y_ref = chief[1] if chief else 0.0
        rows = []
        for r in fan:
            if not r["success"]:
                rows.append({"rho": r["pupil_y"], "dy_um": None,
                             "ds_mm": None})
                continue
            rows.append({
                "rho": r["pupil_y"],
                "dy_um": (r["y_img"] - y_ref) * UM_PER_MM,
                "ds_mm": r["ds"]})
        valid = [(abs(r["rho"]), r["ds_mm"]) for r in rows
                 if r["ds_mm"] is not None and abs(r["rho"]) > TINY
                 and math.isfinite(r["ds_mm"])
                 and abs(r["ds_mm"]) < DS_SANE_MM]
        # Фит ds(u) = c2·u + c4·u², u = ρ²: продольная аберрация
        # конечна у зон, дошедших до плоскости изображения с ненулевым
        # наклоном (вырожденные |ds| ≥ DS_SANE_MM исключены).
        fit = None
        if len(valid) >= SPHERICAL_FIT_TERMS + 1:
            us = np.array([rho * rho for rho, _ in valid], dtype=float)
            dss = np.array([ds for _, ds in valid], dtype=float)
            coeffs_desc = np.polyfit(us, dss, SPHERICAL_FIT_TERMS)
            resid = dss - np.polyval(coeffs_desc, us)
            fit = {"coeffs": [float(c) for c in coeffs_desc[::-1]],
                   "resid_max_mm": float(np.max(np.abs(resid)))}
        la_edge = next((r["ds_mm"] for r in rows
                        if r["ds_mm"] is not None
                        and abs(abs(r["rho"]) - 1.0) < 1e-9), None)
        zonal = min(((abs(abs(r["rho"]) - SPHERICAL_ZONAL_RHO), r["ds_mm"])
                     for r in rows if r["ds_mm"] is not None),
                    key=lambda p: p[0], default=(None, None))
        return {"wl": wl_eff, "field_y": field_y, "num_rays": n_fan,
                "rows": sanitize_json(rows), "fit": sanitize_json(fit),
                "la_edge_mm": sanitize_json(la_edge),
                "la_zonal_mm": sanitize_json(zonal[1])}

    @registry.command(
        "aberx.aperture.aberrations", category="aberx",
        description="Апертурная зависимость аберраций: краевая "
                    "поперечная dy(±1) и продольная LA края "
                    "меридионального веера при разных диаметрах "
                    "входного зрачка + отношение dy/D³ (сферическая "
                    "∝ D³)",
        returns="{wl, field_y, num_rays, rows: [{epd_mm, dy_plus_edge_um, "
                "dy_minus_edge_um, la_edge_mm, dy_over_d3}]}",
        params=system_source_params([
            Param("apertures", type="list", required=True,
                  help="диаметры входного зрачка, мм (≥2 значащих)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град / мм)"),
            Param("num_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help=f"лучей веера (≥3; по умолчанию {FAN_RAYS_DEFAULT})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_aperture_aberrations(ctx, file, system, lbo_index,
                                   lbo_name, apertures, field_y,
                                   num_rays, wl):
        from domain.models import ApertureType
        from analysis.aberrations import trace_aberration_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        n_fan = _fan_guard(num_rays)
        epd_list = sorted({float(v) for v in apertures if float(v) > 0})
        if not epd_list:
            raise CommandError(ERR_INVALID_PARAM,
                               "apertures пуст или все значения ≤ 0")
        rows = []
        for epd in epd_list:
            probe = copy.deepcopy(sys_obj)
            probe.aperture_type = ApertureType.ENTRANCE_PUPIL
            probe.aperture_value = epd
            fan = trace_aberration_fan(probe, wl_eff, num_rays=n_fan,
                                       field_y=field_y)
            y_ref = next((r["y_img"] for r in fan
                          if r["success"] and abs(r["pupil_y"]) < TINY),
                         0.0)
            plus = next((r for r in fan if r["pupil_y"] == 1.0), None)
            minus = next((r for r in fan if r["pupil_y"] == -1.0), None)
            dy_plus = ((plus["y_img"] - y_ref) * UM_PER_MM
                       if plus and plus["success"] else None)
            dy_minus = ((minus["y_img"] - y_ref) * UM_PER_MM
                        if minus and minus["success"] else None)
            la_edge = (plus["ds"] if plus and plus["success"] else None)
            rows.append({
                "epd_mm": epd,
                "dy_plus_edge_um": dy_plus,
                "dy_minus_edge_um": dy_minus,
                "la_edge_mm": la_edge,
                "dy_over_d3": (dy_plus / epd ** 3
                               if dy_plus is not None else None)})
        return {"wl": wl_eff, "field_y": field_y, "num_rays": n_fan,
                "rows": sanitize_json(rows)}

    # ----------------------------------------------------------
    # Зональные таблицы и фокальные поверхности
    # ----------------------------------------------------------

    @registry.command(
        "aberx.transverse.zones", category="aberx",
        description="Таблица поперечных аберраций заданного поля по "
                    "зонам зрачка равной площади (1, √((n−1)/n), ...): "
                    "dy меридионального и сагиттального сечений, мкм "
                    "относительно главного луча",
        returns="{wl, field_y, chief: [x, y], rows: [{rho, dy_mer_um, "
                "dy_sag_um, mer_success, sag_success}]}",
        params=system_source_params([
            Param("field_y", type="float", required=True,
                  help="поле (град / мм)"),
            Param("n_zones", type="int", default=ZONES_DEFAULT,
                  help=f"зон равной площади (по умолчанию "
                       f"{ZONES_DEFAULT})"),
            Param("zones", type="list",
                  help="явный список зон (доли зрачка, допускаются "
                       "отрицательные); по умолчанию — зоны равной "
                       "площади обеих знаков"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_transverse_zones(ctx, file, system, lbo_index, lbo_name,
                               field_y, n_zones, zones, wl):
        from analysis.tables import field_zones
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if zones:
            rho_list = sorted({float(v) for v in zones})
        else:
            equal_area = set(field_zones(max(1, int(n_zones))))
            rho_list = sorted({0.0} | equal_area
                              | {-v for v in equal_area})
        chief = _chief_image_point(sys_obj, wl_eff, field_y)
        rows = []
        for rho in rho_list:
            mer_end = _pupil_ray_end(sys_obj, wl_eff, field_y, 0.0, rho)
            sag_end = _pupil_ray_end(sys_obj, wl_eff, field_y, rho, 0.0)
            dy_mer = ((mer_end[1] - chief[1]) * UM_PER_MM
                      if mer_end is not None and chief is not None
                      else None)
            dy_sag = ((sag_end[0] - chief[0]) * UM_PER_MM
                      if sag_end is not None and chief is not None
                      else None)
            rows.append({"rho": rho, "dy_mer_um": dy_mer,
                         "dy_sag_um": dy_sag,
                         "mer_success": mer_end is not None,
                         "sag_success": sag_end is not None})
        return {"wl": wl_eff, "field_y": field_y,
                "chief": ([chief[0], chief[1]] if chief else None),
                "rows": sanitize_json(rows)}

    @registry.command(
        "aberx.focal.zonal", category="aberx",
        description="Зонные фокусы Z(±ρ) тангенциальной и сагиттальной "
                    "плоскостей на поле: пересечения лучей зон с "
                    "главным лучом (диагностика каустик) — данные "
                    "фокальных поверхностей по зонам",
        returns="{wl, field_y, z_m0, z_s0, rows: [{rho, z_m_plus, "
                "z_m_minus, z_m_mid, z_s_plus, z_s_minus, z_s_mid}]}",
        params=system_source_params([
            Param("field_y", type="float", required=True,
                  help="поле (град / мм)"),
            Param("zones", type="list",
                  help=f"доли зрачка (по умолчанию "
                       f"{list(ZONAL_FRACTIONS_DEFAULT)})"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_focal_zonal(ctx, file, system, lbo_index, lbo_name,
                          field_y, zones, wl):
        from analysis.aberrations import caustic_radii
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        fracs = (sorted({float(v) for v in zones
                         if 0.0 < float(v) <= 1.0})
                 if zones else list(ZONAL_FRACTIONS_DEFAULT))
        if not fracs:
            raise CommandError(ERR_INVALID_PARAM,
                               "zones пуст (нет долей зрачка 0..1]")
        pupil_r = get_effective_aperture(sys_obj, default=10.0) / 2.0
        if pupil_r <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "апертура системы не задана (радиус "
                               "зрачка ≤ 0)")
        base = caustic_radii(sys_obj, wl=wl_eff, field_y=field_y)
        rows = []
        for frac in fracs:
            if frac <= 0 or frac > 1:
                continue
            diag = caustic_radii(sys_obj, wl=wl_eff, field_y=field_y,
                                 ray_halfheight=frac * pupil_r)
            rows.append({
                "rho": frac,
                "z_m_plus": diag.get("z_m_plus"),
                "z_m_minus": diag.get("z_m_minus"),
                "z_m_mid": ((diag.get("z_m_plus") + diag.get("z_m_minus"))
                            / 2.0 if diag.get("z_m_plus") is not None
                            and diag.get("z_m_minus") is not None
                            else None),
                "z_s_plus": diag.get("z_s_plus"),
                "z_s_minus": diag.get("z_s_minus"),
                "z_s_mid": ((diag.get("z_s_plus") + diag.get("z_s_minus"))
                            / 2.0 if diag.get("z_s_plus") is not None
                            and diag.get("z_s_minus") is not None
                            else None)})
        return {"wl": wl_eff, "field_y": field_y,
                "z_m0": base.get("z_m0"), "z_s0": base.get("z_s0"),
                "rows": sanitize_json(rows)}

    @registry.command(
        "aberx.longitudinal.fields", category="aberx",
        description="Продольные отрезки крайних лучей по полям: Z, где "
                    "верхний/нижний крайние меридиональные лучи "
                    "догоняют высоту главного луча, средний сдвиг "
                    "относительно плоскости изображения и разброс",
        returns="{wl, rows: [{field_y, z_upper_mm, z_lower_mm, "
                "mean_shift_mm, spread_mm}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_longitudinal_fields(ctx, file, system, lbo_index,
                                  lbo_name, fields, wl):
        from optics_utils import compute_z_positions
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        img_z = compute_z_positions(sys_obj)[-1]
        rows = []
        for field in _fields_arg(sys_obj, fields):
            chief = _chief_image_point(sys_obj, wl_eff, field)
            if chief is None:
                rows.append({"field_y": field, "z_upper_mm": None,
                             "z_lower_mm": None, "mean_shift_mm": None,
                             "spread_mm": None})
                continue
            chief_y = chief[1]

            def _cross_z(rho_y, field=field, chief_y=chief_y):
                """Z пересечения луча зоны ρ с высотой главного луча.

                Конечные разности двух последних точек пути (как
                ``compute_gauge_rays``); ``None`` — луч не дошёл/наклон
                вырожден.
                """
                result = _pupil_ray_result(sys_obj, wl_eff, field,
                                           0.0, rho_y)
                if not result.success or len(result.path) < 2:
                    return None
                last, prev = result.path[-1], result.path[-2]
                dz = last[2] - prev[2]
                if abs(dz) < TINY:
                    return None
                slope = (last[1] - prev[1]) / dz
                if abs(slope) < TINY:
                    return None
                return last[2] + (chief_y - last[1]) / slope

            z_up, z_low = _cross_z(1.0), _cross_z(-1.0)
            both = [z for z in (z_up, z_low) if z is not None]
            rows.append({
                "field_y": field, "z_upper_mm": z_up,
                "z_lower_mm": z_low,
                "mean_shift_mm": (sum(both) / len(both) - img_z
                                  if both else None),
                "spread_mm": (abs(z_up - z_low)
                              if z_up is not None and z_low is not None
                              else None)})
        return {"wl": wl_eff, "img_z_mm": img_z,
                "rows": sanitize_json(rows)}

    # ----------------------------------------------------------
    # Зейдель: вклады поверхностей
    # ----------------------------------------------------------

    @registry.command(
        "aberx.seidel.shares", category="aberx",
        description="Вклады отдельных поверхностей в суммы Зейделя "
                    "SI..SV + хроматические SIхр/SIIхр: абсолютные "
                    "значения и процентные доли (паритет итогов с "
                    "seidel.sums проверяется)",
        returns="{wl, rows: [{n, glass, radius, SI, SI_share_pct, SII, "
                "..., SIIxp_share_pct}], totals, parity_ok}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aberx_seidel_shares(ctx, file, system, lbo_index, lbo_name, wl):
        from analysis.seidel_check import _paraxial_auxiliary, seidel_sums
        from domain.calculations import refractive_index
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        totals = seidel_sums(sys_obj, wl=wl_eff)
        wls = sorted(float(w.value) for w in sys_obj.wavelengths)
        wl_lo, wl_hi = (wls[0], wls[-1]) if len(wls) >= 2 else (wl_eff,
                                                                wl_eff)
        chromatic = (totals.get("chromatic", False)
                     and abs(wl_hi - wl_lo) > 1e-12)

        def _dn(glass, n_ov):
            if glass == "" and not n_ov:
                return 0.0
            return (refractive_index(glass, wl_hi, None, n_ov)
                    - refractive_index(glass, wl_lo, None, n_ov))

        n, y, nu, yb, nub = _paraxial_auxiliary(sys_obj, wl_eff)
        keys = ("SI", "SII", "SIII", "SIV", "SV", "SIxp", "SIIxp")
        sums = {k: 0.0 for k in keys}
        rows = []
        for i, surf in enumerate(sys_obj.surfaces):
            row = {"n": i + 1, "glass": surf.glass or "",
                   "radius": surf.radius,
                   "reflective": bool(surf.is_reflective)}
            contrib = {k: 0.0 for k in keys}
            radius = surf.radius
            if radius != 0:
                dinv = 1.0 / n[i + 1] - 1.0 / n[i]
                h = y[i]
                a_inv = nu[i] + n[i] * y[i] / radius
                ab_inv = nub[i] + n[i] * yb[i] / radius
                contrib["SI"] = a_inv * a_inv * h * dinv
                contrib["SII"] = ab_inv * a_inv * h * dinv
                contrib["SIII"] = ab_inv * ab_inv * h * dinv
                contrib["SIV"] = ((n[i + 1] - n[i])
                                  / (radius * n[i] * n[i + 1]))
                a_safe = a_inv if abs(a_inv) > 1e-12 else 1e-12
                contrib["SV"] = ((ab_inv ** 3 / a_safe) * h * dinv
                                 + 3.0 * ab_inv * ab_inv * h * dinv)
                if chromatic:
                    if surf.is_reflective:
                        dn1 = _dn(sys_obj.surfaces[i - 1].glass if i
                                  else "",
                                  getattr(sys_obj.surfaces[i - 1],
                                          "n_override", None) if i
                                  else None)
                        dn2 = -dn1
                    else:
                        n_ov1 = (getattr(sys_obj.surfaces[i - 1],
                                         "n_override", None) if i
                                 else None)
                        dn1 = _dn(sys_obj.surfaces[i - 1].glass if i
                                  else "", n_ov1)
                        dn2 = _dn(surf.glass,
                                  getattr(surf, "n_override", None))
                    dchrom = -(dn2 / n[i + 1] ** 2 - dn1 / n[i] ** 2)
                    contrib["SIxp"] = a_inv * h * dchrom
                    contrib["SIIxp"] = ab_inv * h * dchrom
            for k in keys:
                sums[k] += contrib[k]
                total = totals.get(k, 0.0)
                row[k] = contrib[k]
                row[f"{k}_share_pct"] = (contrib[k] / total * 100.0
                                         if abs(total) > TINY else None)
            rows.append(row)
        parity_ok = all(
            abs(sums[k] - totals.get(k, 0.0)) <= 1e-9 * max(
                1.0, abs(totals.get(k, 0.0)))
            for k in keys if k in totals)
        return {"wl": wl_eff, "rows": sanitize_json(rows),
                "totals": {k: totals.get(k) for k in keys},
                "parity_ok": parity_ok}
