"""
OPAL-OKB — Пакет R500-8: допуски и чувствительность (TOLERANC.txt).

Конечноразностные чувствительности поверх СУЩЕСТВУЮЩИХ движков
(paraxial_trace / seidel_aberrations / compute_spot_diagram): новых
ядер нет — команды возмущают копию системы и меряют отклик метрики.

- ``tol.sensitivity.*`` — градиенты метрик по радиусам/толщинам/
  показателям/наклонам/децентрировкам;
- ``tol.inverse.*`` — обратная задача: допуск на параметр под бюджет
  отклонения метрики; ``tol.budget.split`` — RSS-распределение;
- ``tol.contributions/worst`` — сводные таблицы и топ параметров;
- ``tol.apply.perturbation`` — песочница возмущений (копия системы);
- ``tol.monte_carlo`` — детерминированный (seed) Монте-Карло разброс.
"""
import copy
import math
import random

from commands.base import ERR_INVALID_PARAM, Param, CommandError
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
)

from optics_utils import get_primary_wl

#: Шаг центральной разности по умолчанию: радиус/толщина, мм.
RADIUS_DELTA_MM = 0.01
#: Шаг по показателю преломления.
N_DELTA = 0.001
#: Шаг по наклону, град.
TILT_DELTA_DEG = 0.1
#: Шаг по децентрировке, мм.
DECENTER_DELTA_MM = 0.05

#: Число испытаний Монте-Карло по умолчанию.
MC_TRIALS_DEFAULT = 64

#: Seed генератора Монте-Карло (детерминизм тестов).
MC_SEED_DEFAULT = 20261023

#: Ключи сумм Зейделя в таблицах чувствительности.
SEIDEL_KEYS = ("SI", "SII", "SIII", "SIV", "SV")

#: Максимум строк в tol.worst по умолчанию.
WORST_LIMIT_DEFAULT = 10


def _efl(system, wl):
    """Метрика: фокусное расстояние параксиала."""
    from domain.calculations import paraxial_trace
    return paraxial_trace(system, wl=wl).get("focal_length")


def _spot_rms(system, wl, field_y, num_rays):
    """Метрика: RMS кружка на поле."""
    from analysis.aberrations import (
        compute_rms_spot,
        compute_spot_diagram,
    )
    spots = compute_spot_diagram(system, wl=wl, num_rays=num_rays,
                                 field_y=field_y)
    return compute_rms_spot(spots)


def _centroid(system, axis: int, wl, field_y, num_rays):
    """Метрика: центроид пятна по оси (0 — X, 1 — Y; boresight)."""
    from analysis.aberrations import compute_spot_diagram
    spots = compute_spot_diagram(system, wl=wl, num_rays=num_rays,
                                 field_y=field_y)
    return sum(p[axis] for p in spots) / len(spots) if spots else None


def _seidel_value(system, key):
    """Метрика: одна сумма Зейделя."""
    from domain.calculations import seidel_aberrations
    return seidel_aberrations(system).get(key)


def _central_diff(system, mutate, metric, delta):
    """(f(+δ) − f(−δ)) / 2δ на копиях системы."""
    plus = copy.deepcopy(system)
    mutate(plus, +delta)
    minus = copy.deepcopy(system)
    mutate(minus, -delta)
    f_plus, f_minus = metric(plus), metric(minus)
    if f_plus is None or f_minus is None:
        return None
    return (f_plus - f_minus) / (2.0 * delta)


def _surfaces_arg(system, index):
    """Список индексов поверхностей (все или один)."""
    if index is None:
        return list(range(system.num_surfaces))
    if not (0 <= index < system.num_surfaces):
        raise CommandError(
            ERR_INVALID_PARAM,
            f"index={index} вне 0..{system.num_surfaces - 1}")
    return [index]


def register(registry: Registry) -> None:
    """Зарегистрировать команды допусков (R500-8)."""

    # ============================================================
    # Чувствительность EFL
    # ============================================================

    @registry.command(
        "tol.sensitivity.radius", category="tol",
        description="Чувствительность f′ к радиусам поверхностей "
                    "(центральная разность, мм⁻¹)",
        returns="{wl, delta_mm, rows: [{index, d_efl_d_r}]}",
        params=system_source_params() + [
            Param("index", type="int", help="одна поверхность (0-based)"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_sensitivity_radius(ctx, file, system, lbo_index, lbo_name,
                               index, delta, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if delta <= 0:
            raise CommandError(ERR_INVALID_PARAM, "delta > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i in _surfaces_arg(sys_obj, index):
            def mutate(s, d, i=i):
                s.surfaces[i].radius += d
            rows.append({"index": i, "radius": sys_obj.surfaces[i].radius,
                         "d_efl_d_r": _central_diff(
                             sys_obj, mutate,
                             lambda s: _efl(s, wl_eff), delta)})
        return {"wl": wl_eff, "delta_mm": delta, "rows": rows}

    @registry.command(
        "tol.sensitivity.thickness", category="tol",
        description="Чувствительность f′ к толщинам поверхностей",
        returns="{wl, delta_mm, rows: [{index, d_efl_d_d}]}",
        params=system_source_params() + [
            Param("index", type="int", help="одна поверхность (0-based)"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_sensitivity_thickness(ctx, file, system, lbo_index, lbo_name,
                                  index, delta, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if delta <= 0:
            raise CommandError(ERR_INVALID_PARAM, "delta > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i in _surfaces_arg(sys_obj, index):
            def mutate(s, d, i=i):
                s.surfaces[i].thickness += d
            rows.append({"index": i,
                         "thickness": sys_obj.surfaces[i].thickness,
                         "d_efl_d_d": _central_diff(
                             sys_obj, mutate,
                             lambda s: _efl(s, wl_eff), delta)})
        return {"wl": wl_eff, "delta_mm": delta, "rows": rows}

    @registry.command(
        "tol.sensitivity.glass", category="tol",
        description="Чувствительность f′ к показателю преломления "
                    "стёкол (Δn через n_override)",
        returns="{wl, delta_n, rows: [{index, glass, d_efl_d_n}]}",
        params=system_source_params() + [
            Param("index", type="int", help="одна поверхность (0-based)"),
            Param("delta", type="float", default=N_DELTA,
                  help="шаг разности по n"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_sensitivity_glass(ctx, file, system, lbo_index, lbo_name,
                              index, delta, wl):
        from domain.calculations import refractive_index
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if delta <= 0:
            raise CommandError(ERR_INVALID_PARAM, "delta > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i in _surfaces_arg(sys_obj, index):
            glass = sys_obj.surfaces[i].glass
            if not glass:
                continue  # воздух: n фиксирован

            def mutate(s, d, i=i, glass=glass, wl_eff=wl_eff):
                n0 = refractive_index(glass, wl_eff,
                                      n_override=s.surfaces[i].n_override
                                      or None)
                s.surfaces[i].n_override = {wl_eff: n0 + d}
            rows.append({"index": i, "glass": glass,
                         "d_efl_d_n": _central_diff(
                             sys_obj, mutate,
                             lambda s: _efl(s, wl_eff), delta)})
        return {"wl": wl_eff, "delta_n": delta, "rows": rows}

    # ============================================================
    # Чувствительность аберраций/пятна
    # ============================================================

    @registry.command(
        "tol.sensitivity.seidel.radius", category="tol",
        description="Чувствительность сумм Зейделя к радиусам (какая "
                    "поверхность управляет какой аберрацией)",
        returns="{wl, delta_mm, rows: [{index, dS.._d_r: {...}}]}",
        params=system_source_params() + [
            Param("index", type="int", help="одна поверхность (0-based)"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_sensitivity_seidel_radius(ctx, file, system, lbo_index,
                                      lbo_name, index, delta, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if delta <= 0:
            raise CommandError(ERR_INVALID_PARAM, "delta > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i in _surfaces_arg(sys_obj, index):
            def mutate(s, d, i=i):
                s.surfaces[i].radius += d
            grads = {}
            for key in SEIDEL_KEYS:
                grads[f"d{key}_d_r"] = _central_diff(
                    sys_obj, mutate,
                    lambda s, k=key: _seidel_value(s, k), delta)
            rows.append({"index": i, **grads})
        return {"wl": wl_eff, "delta_mm": delta, "rows": rows}

    @registry.command(
        "tol.sensitivity.spot.radius", category="tol",
        description="Чувствительность RMS кружка к радиусам поверхностей",
        returns="{wl, delta_mm, rows: [{index, d_rms_d_r}]}",
        params=system_source_params() + [
            Param("index", type="int", help="одна поверхность (0-based)"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=15, help="лучей сетки"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_sensitivity_spot_radius(ctx, file, system, lbo_index, lbo_name,
                                    index, delta, field_y, num_rays, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if delta <= 0:
            raise CommandError(ERR_INVALID_PARAM, "delta > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i in _surfaces_arg(sys_obj, index):
            def mutate(s, d, i=i):
                s.surfaces[i].radius += d
            rows.append({"index": i, "d_rms_d_r": _central_diff(
                sys_obj, mutate,
                lambda s: _spot_rms(s, wl_eff, field_y, num_rays), delta)})
        return {"wl": wl_eff, "field_y": field_y, "delta_mm": delta,
                "rows": rows}

    @registry.command(
        "tol.sensitivity.tilt", category="tol",
        description="Чувствительность Y-центроида пятна (boresight) к "
                    "наклонам поверхностей (tilt_x, град): мм смещения "
                    "на градус",
        returns="{wl, delta_deg, rows: [{index, d_centroid_d_tilt}]}",
        params=system_source_params() + [
            Param("index", type="int", help="одна поверхность (0-based)"),
            Param("delta", type="float", default=TILT_DELTA_DEG,
                  help="шаг разности, град"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=15, help="лучей сетки"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_sensitivity_tilt(ctx, file, system, lbo_index, lbo_name,
                             index, delta, field_y, num_rays, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if delta <= 0:
            raise CommandError(ERR_INVALID_PARAM, "delta > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i in _surfaces_arg(sys_obj, index):
            def mutate(s, d, i=i):
                s.surfaces[i].tilt_x += d
            rows.append({"index": i, "d_centroid_d_tilt": _central_diff(
                sys_obj, mutate,
                lambda s: _centroid(s, 1, wl_eff, field_y, num_rays),
                delta)})
        return {"wl": wl_eff, "field_y": field_y, "delta_deg": delta,
                "rows": rows}

    @registry.command(
        "tol.sensitivity.decenter", category="tol",
        description="Чувствительность Y-центроида пятна (boresight) к "
                    "децентрировкам поверхностей (decenter_x, мм)",
        returns="{wl, delta_mm, rows: [{index, d_centroid_d_dec}]}",
        params=system_source_params() + [
            Param("index", type="int", help="одна поверхность (0-based)"),
            Param("delta", type="float", default=DECENTER_DELTA_MM,
                  help="шаг разности, мм"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=15, help="лучей сетки"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_sensitivity_decenter(ctx, file, system, lbo_index, lbo_name,
                                 index, delta, field_y, num_rays, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if delta <= 0:
            raise CommandError(ERR_INVALID_PARAM, "delta > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i in _surfaces_arg(sys_obj, index):
            def mutate(s, d, i=i):
                s.surfaces[i].decenter_x += d
            rows.append({"index": i, "d_centroid_d_dec": _central_diff(
                sys_obj, mutate,
                lambda s: _centroid(s, 0, wl_eff, field_y, num_rays),
                delta)})
        return {"wl": wl_eff, "field_y": field_y, "delta_mm": delta,
                "rows": rows}

    # ============================================================
    # Сводки и обратные допуски
    # ============================================================

    @registry.command(
        "tol.contributions", category="tol",
        description="Сводная таблица чувствительностей f′: радиусы + "
                    "толщины + стёкла, ранжирование поверхностей",
        returns="{rows: [{index, d_efl_d_r, d_efl_d_d, d_efl_d_n, max_g}]}",
        params=system_source_params() + [
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_contributions(ctx, file, system, lbo_index, lbo_name,
                          delta, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        radius = registry.execute(
            "tol.sensitivity.radius", ctx,
            {"system": _put_probe(ctx, sys_obj), "delta": delta,
             "wl": wl_eff}).data
        thickness = registry.execute(
            "tol.sensitivity.thickness", ctx,
            {"system": _put_probe(ctx, sys_obj), "delta": delta,
             "wl": wl_eff}).data
        glass = registry.execute(
            "tol.sensitivity.glass", ctx,
            {"system": _put_probe(ctx, sys_obj), "delta": N_DELTA,
             "wl": wl_eff}).data
        by_index = {}
        for row in radius["rows"]:
            by_index.setdefault(row["index"], {})["d_efl_d_r"] = \
                row["d_efl_d_r"]
        for row in thickness["rows"]:
            by_index.setdefault(row["index"], {})["d_efl_d_d"] = \
                row["d_efl_d_d"]
        for row in glass["rows"]:
            by_index.setdefault(row["index"], {})["d_efl_d_n"] = \
                row["d_efl_d_n"]
        rows = []
        for i, grads in sorted(by_index.items()):
            values = [abs(v) for v in grads.values() if v is not None]
            rows.append({"index": i, **grads,
                         "max_g": max(values) if values else 0.0})
        rows.sort(key=lambda r: -r["max_g"])
        return {"wl": wl_eff, "rows": rows}

    @registry.command(
        "tol.worst", category="tol",
        description="Топ параметров по чувствительности f′ "
                    "(радиусы/толщины/стёкла)",
        returns="{worst: [{surface, param, grad}]}",
        params=system_source_params() + [
            Param("limit", type="int", default=WORST_LIMIT_DEFAULT,
                  help="максимум строк"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_worst(ctx, file, system, lbo_index, lbo_name, limit, delta,
                  wl):
        data = registry.execute(
            "tol.contributions", ctx,
            {"system": _put_probe(ctx, resolve_system(
                ctx, file, system, lbo_index, lbo_name)),
             "delta": delta, "wl": wl}).data
        worst = []
        for row in data["rows"]:
            for param, key in (("radius", "d_efl_d_r"),
                               ("thickness", "d_efl_d_d"),
                               ("glass n", "d_efl_d_n")):
                value = row.get(key)
                if value is not None:
                    worst.append({"surface": row["index"], "param": param,
                                  "grad": value, "abs_grad": abs(value)})
        worst.sort(key=lambda w: -w["abs_grad"])
        return {"worst": worst[:max(0, limit)]}

    @registry.command(
        "tol.inverse.radius", category="tol",
        description="Допуск на радиус каждой поверхности под бюджет "
                    "|Δf′| ≤ budget (линейная оценка)",
        returns="{budget_mm, rows: [{index, grad, tolerance_mm}]}",
        params=system_source_params() + [
            Param("budget", type="float", required=True,
                  help="бюджет |Δf′|, мм"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_inverse_radius(ctx, file, system, lbo_index, lbo_name,
                           budget, delta, wl):
        if budget <= 0:
            raise CommandError(ERR_INVALID_PARAM, "budget > 0")
        sens = registry.execute(
            "tol.sensitivity.radius", ctx,
            {"system": _put_probe(ctx, resolve_system(
                ctx, file, system, lbo_index, lbo_name)),
             "delta": delta, "wl": wl}).data
        rows = []
        for row in sens["rows"]:
            grad = row["d_efl_d_r"]
            rows.append({"index": row["index"], "grad": grad,
                         "tolerance_mm": (budget / abs(grad)
                                          if grad not in (None, 0.0)
                                          else None)})
        return {"budget_mm": budget, "rows": rows}

    @registry.command(
        "tol.inverse.thickness", category="tol",
        description="Допуск на толщину каждой поверхности под бюджет "
                    "|Δf′| ≤ budget",
        returns="{budget_mm, rows: [{index, grad, tolerance_mm}]}",
        params=system_source_params() + [
            Param("budget", type="float", required=True,
                  help="бюджет |Δf′|, мм"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_inverse_thickness(ctx, file, system, lbo_index, lbo_name,
                              budget, delta, wl):
        if budget <= 0:
            raise CommandError(ERR_INVALID_PARAM, "budget > 0")
        sens = registry.execute(
            "tol.sensitivity.thickness", ctx,
            {"system": _put_probe(ctx, resolve_system(
                ctx, file, system, lbo_index, lbo_name)),
             "delta": delta, "wl": wl}).data
        rows = []
        for row in sens["rows"]:
            grad = row["d_efl_d_d"]
            rows.append({"index": row["index"], "grad": grad,
                         "tolerance_mm": (budget / abs(grad)
                                          if grad not in (None, 0.0)
                                          else None)})
        return {"budget_mm": budget, "rows": rows}

    @registry.command(
        "tol.budget.split", category="tol",
        description="RSS-распределение бюджета |Δf′| по параметрам: "
                    "равные доли, tᵢ = budget/(gᵢ·√N)",
        returns="{budget_mm, rows: [{surface, param, grad, tolerance_mm}]}",
        params=system_source_params() + [
            Param("budget", type="float", required=True,
                  help="бюджет |Δf′|, мм (RSS)"),
            Param("delta", type="float", default=RADIUS_DELTA_MM,
                  help="шаг разности, мм"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_budget_split(ctx, file, system, lbo_index, lbo_name,
                         budget, delta, wl):
        if budget <= 0:
            raise CommandError(ERR_INVALID_PARAM, "budget > 0")
        contributions = registry.execute(
            "tol.contributions", ctx,
            {"system": _put_probe(ctx, resolve_system(
                ctx, file, system, lbo_index, lbo_name)),
             "delta": delta, "wl": wl}).data
        items = []
        for row in contributions["rows"]:
            for param, key in (("radius", "d_efl_d_r"),
                               ("thickness", "d_efl_d_d"),
                               ("glass n", "d_efl_d_n")):
                grad = row.get(key)
                if grad not in (None, 0.0):
                    items.append({"surface": row["index"], "param": param,
                                  "grad": grad})
        n = len(items)
        if n == 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "нет возмущаемых параметров")
        scale = math.sqrt(n)
        for item in items:
            item["tolerance_mm"] = budget / (abs(item["grad"]) * scale)
        return {"budget_mm": budget, "num_params": n, "rows": items}

    @registry.command(
        "tol.rss.combine", category="tol",
        description="СКО-комбинация вкладов (RSS): √Σ(Δfᵢ)²",
        returns="{contributions, rss}",
        params=[
            Param("contributions", type="list", required=True,
                  help="список вкладов Δfᵢ (числа)"),
        ])
    def tol_rss_combine(ctx, contributions):
        if not contributions:
            raise CommandError(ERR_INVALID_PARAM, "contributions пуст")
        try:
            values = [float(v) for v in contributions]
        except (TypeError, ValueError) as exc:
            raise CommandError(ERR_INVALID_PARAM,
                               f"нужны числа: {exc}") from exc
        rss = math.sqrt(sum(v * v for v in values))
        return {"contributions": values, "rss": rss}

    # ============================================================
    # Песочница и Монте-Карло
    # ============================================================

    @registry.command(
        "tol.apply.perturbation", category="tol",
        description="Применить возмущения к копии системы и вернуть "
                    "отклик f′/RMS (песочница без правки исходника)",
        returns="{efl_base, efl_perturbed, d_efl, rms_base, rms_perturbed}",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="поверхность (0-based)"),
            Param("dr", type="float", default=0.0,
                  help="приращение радиуса, мм"),
            Param("dd", type="float", default=0.0,
                  help="приращение толщины, мм"),
            Param("field_y", type="float", default=0.0, help="поле RMS"),
            Param("num_rays", type="int", default=15, help="лучей сетки"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_apply_perturbation(ctx, file, system, lbo_index, lbo_name,
                               index, dr, dd, field_y, num_rays, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        _surfaces_arg(sys_obj, index)  # валидация
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        perturbed = copy.deepcopy(sys_obj)
        perturbed.surfaces[index].radius += dr
        perturbed.surfaces[index].thickness += dd
        efl_base = _efl(sys_obj, wl_eff)
        efl_new = _efl(perturbed, wl_eff)
        return {
            "index": index, "dr": dr, "dd": dd, "wl": wl_eff,
            "efl_base": efl_base, "efl_perturbed": efl_new,
            "d_efl": (efl_new - efl_base)
            if efl_base is not None and efl_new is not None else None,
            "rms_base": _spot_rms(sys_obj, wl_eff, field_y, num_rays),
            "rms_perturbed": _spot_rms(perturbed, wl_eff, field_y,
                                       num_rays),
        }

    @registry.command(
        "tol.monte_carlo", category="tol",
        description="Монте-Карло разброс f′ при равномерных ошибках "
                    "радиусов/толщин (детерминирован seed)",
        returns="{trials, radius_tol, thickness_tol, stats, samples}",
        params=system_source_params() + [
            Param("trials", type="int", default=MC_TRIALS_DEFAULT,
                  help="число испытаний"),
            Param("radius_tol", type="float", default=RADIUS_DELTA_MM,
                  help="±допуск радиуса, мм"),
            Param("thickness_tol", type="float", default=RADIUS_DELTA_MM,
                  help="±допуск толщины, мм"),
            Param("seed", type="int", default=MC_SEED_DEFAULT,
                  help="seed генератора (воспроизводимость)"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def tol_monte_carlo(ctx, file, system, lbo_index, lbo_name, trials,
                        radius_tol, thickness_tol, seed, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if trials < 2:
            raise CommandError(ERR_INVALID_PARAM, "trials ≥ 2")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rng = random.Random(seed)
        efl0 = _efl(sys_obj, wl_eff)
        samples = []
        for _ in range(trials):
            probe = copy.deepcopy(sys_obj)
            for s in probe.surfaces:
                s.radius += rng.uniform(-radius_tol, radius_tol)
                s.thickness += rng.uniform(-thickness_tol, thickness_tol)
            value = _efl(probe, wl_eff)
            if value is not None:
                samples.append(value - efl0)
        if not samples:
            raise CommandError(ERR_INVALID_PARAM,
                               "ни одно испытание не посчиталось")
        mean = sum(samples) / len(samples)
        std = math.sqrt(sum((v - mean) ** 2 for v in samples)
                        / max(1, len(samples) - 1))
        ordered = sorted(samples)
        mid = len(ordered) // 2
        return {
            "trials": len(samples), "seed": seed,
            "radius_tol": radius_tol, "thickness_tol": thickness_tol,
            "stats": {"mean": mean, "std": std,
                      "min": ordered[0], "max": ordered[-1],
                      "median": (ordered[mid] if len(ordered) % 2
                                 else 0.5 * (ordered[mid - 1]
                                             + ordered[mid]))},
            "samples_head": samples[:WORST_LIMIT_DEFAULT],
        }


def _put_probe(ctx, system) -> str:
    """Положить систему в контекст под служебным именем (для execute)."""
    key = "_tol_probe"
    ctx.put_system(key, system, make_current=False)
    return key
