"""
OPAL-OKB — Команды analyze.*: реальные лучи, аберрации, ФРТ, таблицы.

Обёртки над главными точками входа пакета analysis (покрыты тестами,
не требуют Qt): веер лучей, внеосевые аберрации, точечная диаграмма,
ФРТ/ОПФ (psf_grid), таблицы TABGL/TABPR2.
"""
from optics_utils import get_primary_wl

from commands.base import Param
from commands.registry import Registry
from commands.systemio import resolve_system, system_source_params

#: Способы выборки зрачка для точечной диаграммы (aberrations.py).
SPOT_SAMPLING_CHOICES = ("grid", "hexapolar")

#: Скалярные ключи psf_grid, попадающие в ответ всегда (без решёток).
PSF_SCALAR_KEYS = ("wl", "field_y", "defocus", "fill", "strehl",
                   "cutoff_lpmm", "nyquist_lpmm", "pitch_um", "D", "f",
                   "f_number", "grid", "pad", "M", "obscuration", "reason")


def _pupil_y(i: int, num_rays: int, pupil_range: float) -> float:
    """Нормированная высота i-го луча веера (формула analysis.trace_fan)."""
    if num_rays > 1:
        return -pupil_range + 2.0 * pupil_range * i / (num_rays - 1)
    return 0.0


def register(registry: Registry) -> None:
    """Зарегистрировать все команды analyze.*."""

    @registry.command(
        "analyze.ray_fan", category="analyze",
        description="Меридиональный веер лучей: трассировка через систему",
        returns="список лучей {pupil_y, success, error, opl, path}",
        params=system_source_params([
            Param("num_rays", type="int", default=9,
                  help="число лучей веера"),
            Param("pupil_range", type="float", default=1.0,
                  help="диапазон зрачка (0..1)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
        ]))
    def analyze_ray_fan(ctx, file, system, lbo_index, lbo_name,
                        num_rays, pupil_range, wl, field_y):
        from analysis.ray_tracing import trace_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        results = trace_fan(sys_obj, num_rays=num_rays,
                            pupil_range=pupil_range, wl=wl_eff,
                            field_y=field_y)
        rays = [{
            "pupil_y": _pupil_y(i, num_rays, pupil_range),
            "success": r.success,
            "error": r.error,
            "surfaces_hit": r.surfaces_hit,
            "opl": r.opl,
            "path": [[p[0], p[1], p[2]] for p in r.path],
        } for i, r in enumerate(results)]
        return {"wl": wl_eff, "field_y": field_y, "num_rays": num_rays,
                "rays": rays}

    @registry.command(
        "analyze.field_aberrations", category="analyze",
        description="Внеосевые аберрации по полям: дисторсия, астигматизм, кома",
        returns="список {field_y, distortion, astigmatism, z_m, z_s, coma}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("fields", type="list",
                  help="список полей (град); по умолчанию — поля системы"),
            Param("num_fan_rays", type="int", default=15,
                  help="лучей в веере на поле"),
        ]))
    def analyze_field_aberrations(ctx, file, system, lbo_index, lbo_name,
                                  wl, fields, num_fan_rays):
        from analysis.aberrations import compute_field_aberrations
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        field_points = [(float(f),) for f in fields] if fields else None
        rows = compute_field_aberrations(
            sys_obj, wl=wl_eff, field_points=field_points,
            num_fan_rays=num_fan_rays)
        return {"wl": wl_eff, "fields": rows}

    @registry.command(
        "analyze.spot", category="analyze",
        description="Точечная диаграмма: пятно + RMS по осям и центроид",
        returns="точки пятна (мм) + RMS-метрики",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("num_rays", type="int", default=50,
                  help="лучей по стороне сетки / колец гексаполярной сетки"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("sampling", choices=list(SPOT_SAMPLING_CHOICES),
                  default="grid", help="способ выборки зрачка"),
        ]))
    def analyze_spot(ctx, file, system, lbo_index, lbo_name,
                     wl, num_rays, field_y, sampling):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_rms_spot_xy,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        spots = compute_spot_diagram(sys_obj, wl=wl_eff, num_rays=num_rays,
                                     field_y=field_y, sampling=sampling)
        return {
            "wl": wl_eff,
            "field_y": field_y,
            "sampling": sampling,
            "num_points": len(spots),
            "spots": [[dx, dy] for dx, dy in spots],
            "rms": compute_rms_spot(spots),
            "rms_xy": compute_rms_spot_xy(list(spots)),
        }

    @registry.command(
        "analyze.psf", category="analyze",
        description="ФРТ (psf_grid): Штрель, срез ОПФ, решётки — по запросу",
        returns="скалярные метрики ФРТ (+psf/wavefront при include_grid)",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
            Param("include_grid", type="bool", default=False,
                  help="включить решётки psf/wavefront/оси (большой объём)"),
        ]))
    def analyze_psf(ctx, file, system, lbo_index, lbo_name,
                    field_y, wl, defocus, include_grid):
        from analysis.psf_mtf import psf_grid
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = psf_grid(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        out = {key: float(res[key]) if isinstance(res.get(key), float)
               else res.get(key)
               for key in PSF_SCALAR_KEYS if key in res}
        if include_grid and res.get("psf") is not None:
            out["psf"] = res["psf"].tolist()
            out["wavefront"] = res["wavefront"].tolist()
            out["y_um"] = res["y_um"].tolist()
            out["x_um"] = res["x_um"].tolist()
        return out

    @registry.command(
        "analyze.tables.tabgl", category="analyze",
        description="Таблица TABGL: главные лучи по зонам поля (§15.1)",
        returns="строки таблицы + текстовый формат OPAL",
        params=system_source_params([
            Param("n_zones", type="int", default=3,
                  help="число зон поля (осевая строка — сверх)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def analyze_tables_tabgl(ctx, file, system, lbo_index, lbo_name,
                             n_zones, wl):
        from analysis.tables import format_tabgl, tabgl_rows
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = tabgl_rows(sys_obj, n_zones=n_zones, wl=wl)
        return {"rows": rows, "text": format_tabgl(rows)}

    @registry.command(
        "analyze.tables.tabpr2", category="analyze",
        description="Таблица TABPR2: хроматизм по зонам поля (§15.2)",
        returns="строки таблицы + текстовый формат OPAL",
        params=system_source_params([
            Param("wl_main", type="float",
                  help="основная λ, мкм (по умолчанию — основная λ системы)"),
            Param("wl_alt", type="float",
                  help="вторая λ пары (по умолчанию — вторая λ системы)"),
            Param("n_zones", type="int", default=3, help="число зон поля"),
        ]))
    def analyze_tables_tabpr2(ctx, file, system, lbo_index, lbo_name,
                              wl_main, wl_alt, n_zones):
        from analysis.tables import format_tabpr2, tabpr2_rows
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = tabpr2_rows(sys_obj, wl_main=wl_main, wl_alt=wl_alt,
                           n_zones=n_zones)
        return {"rows": rows, "text": format_tabpr2(rows)}
