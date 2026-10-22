"""
OPAL-OKB — Команды Волны 3, домен «АБЕРРАЦИИ»: aber.* / chrom.* / seidel.* / adv.*

Обёртки над публичными точками входа analysis/aberrations.py,
analysis/chromatism.py, analysis/seidel_check.py, analysis/advanced.py
(чистые вычисления, без Qt). Уже покрытое Волной 1 НЕ дублируется:

* ``compute_field_aberrations`` → ``analyze.field_aberrations``;
* ``compute_spot_diagram`` + RMS-метрики → ``analyze.spot``
  (RMS-функции переиспользуются здесь как библиотечные);
* суммы Зейделя ``domain`` → ``calc.seidel`` (``seidel.sums`` —
  независимая реализация того же + хроматические SIхр/SIIхр).
"""
from optics_utils import get_primary_wl

from commands.base import Param
from commands.registry import Registry
from commands.systemio import resolve_system, system_source_params

#: Направления LSF/ESF (analysis/advanced.py: direction=).
LSF_DIRECTION_CHOICES = ("tangential", "sagittal")

#: Виды тест-объектов — ключи TEST_OBJECT_KINDS (analysis/advanced.py;
#: единственный источник списка там, здесь — choices параметра kind).
TEST_OBJECT_CHOICES = ("mira", "edge", "point", "sine")

#: Число лучей сетки зрачка для точечной диаграммы aber.mtf_geo
#: (та же сетка, что analyze.spot Волны 1).
MTF_GEO_SPOT_RAYS = 50


def _coerce_wl_flags(values: list) -> list:
    """Нормализовать флаги волн хроматизма для compute_chromatism_opal.

    CLI передаёт list строками (``"0,0.65627,2"``), JSON-REPL — числами.
    Семантика analysis/chromatism._flag_wavelength: ``int`` — 1-основной
    индекс длины волны (0 → основная λ), ``float > 0`` — прямое значение
    λ (мкм); целочисленные строки → int, остальные → float.
    """
    out = []
    for v in values:
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                v = float(v)
        out.append(v)
    return out


def register(registry: Registry) -> None:
    """Зарегистрировать все команды домена (aber/chrom/seidel/adv)."""

    # ================================================================
    # aber.* — analysis/aberrations.py
    # ================================================================

    @registry.command(
        "aber.fan", category="aber",
        description="Веер аберраций: поперечные dy, продольные ds, "
                    "волновые W (OPL до опорной сферы)",
        returns="строки веера {pupil_y, dy, ds, wave, y_img, z_img, success}",
        params=system_source_params([
            Param("num_rays", type="int", default=20,
                  help="лучей веера (сетка зрачка −1..1)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_fan(ctx, file, system, lbo_index, lbo_name,
                 num_rays, field_y, wl):
        from analysis.aberrations import trace_aberration_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = trace_aberration_fan(sys_obj, wl=wl_eff,
                                    num_rays=num_rays, field_y=field_y)
        return {"wl": wl_eff, "field_y": field_y, "num_rays": num_rays,
                "rays": rows}

    @registry.command(
        "aber.chief", category="aber",
        description="Аберрации главных лучей по полям: дисторсия, "
                    "отрезки Z'm/Z's, хроматизм увеличения",
        returns="строки {field_y, distortion_abs, distortion_rel, Zm, Zs, "
                "lateral_color, lateral_color_pct}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_chief(ctx, file, system, lbo_index, lbo_name, wl):
        from analysis.aberrations import compute_chief_ray_characteristics
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = compute_chief_ray_characteristics(sys_obj, wl=wl_eff)
        return {"wl": wl_eff, "rows": rows}

    @registry.command(
        "aber.focus_curve", category="aber",
        description="Фокусировочная кривая: MTF vs смещение плоскости "
                    "изображения (RMS пятна по трассировке)",
        returns="кривая [(defocus_мм, mtf), ...] от найденного фокуса",
        params=system_source_params([
            Param("num_points", type="int", default=40,
                  help="точек кривой"),
            Param("defocus_range", type="float", default=2.0,
                  help="±мм отклонения плоскости"),
            Param("freq_lpmm", type="float", default=50.0,
                  help="частота оценки MTF (лин/мм)"),
            Param("num_rays", type="int", default=30,
                  help="лучей по стороне сетки зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_focus_curve(ctx, file, system, lbo_index, lbo_name,
                         num_points, defocus_range, freq_lpmm, num_rays,
                         field_y, wl):
        from analysis.aberrations import compute_focus_curve
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        curve = compute_focus_curve(
            sys_obj, wl=wl_eff, num_points=num_points,
            defocus_range=defocus_range, freq_lpmm=freq_lpmm,
            num_rays=num_rays, field_y=field_y)
        return {"wl": wl_eff, "freq_lpmm": freq_lpmm,
                "defocus_range": defocus_range,
                "curve": [[d, m] for d, m in curve]}

    @registry.command(
        "aber.spot_poly", category="aber",
        description="Полихроматическая точечная диаграмма: все рабочие λ "
                    "системы, точки с индексом волны",
        returns="точки [[dx, dy, wl_index], ...] (мм)",
        params=system_source_params([
            Param("num_rays", type="int", default=40,
                  help="лучей по стороне сетки зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
        ]))
    def aber_spot_poly(ctx, file, system, lbo_index, lbo_name,
                       num_rays, field_y):
        from analysis.aberrations import compute_spot_diagram_polychromatic
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        spots = compute_spot_diagram_polychromatic(
            sys_obj, num_rays=num_rays, field_y=field_y)
        return {"field_y": field_y,
                "wavelengths": [w.value for w in sys_obj.wavelengths],
                "spots": [[dx, dy, i] for dx, dy, i in spots]}

    @registry.command(
        "aber.rms_poly", category="aber",
        description="Взвешенный RMS пятна по всем полям и длинам волн",
        returns="скаляр RMS (мм); null — если ни один луч не дошёл",
        params=system_source_params([
            Param("num_rays", type="int", default=30,
                  help="лучей по стороне сетки зрачка"),
            Param("field_y", type="float",
                  help="одно поле вместо точек поля системы"),
        ]))
    def aber_rms_poly(ctx, file, system, lbo_index, lbo_name,
                      num_rays, field_y):
        from analysis.aberrations import compute_polychromatic_rms
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rms = compute_polychromatic_rms(sys_obj, num_rays=num_rays,
                                        field_y=field_y)
        return {"num_rays": num_rays, "field_y": field_y, "rms": rms}

    @registry.command(
        "aber.spot_heatmap", category="aber",
        description="Топограмма плотности пятна рассеяния (гистограмма "
                    "точек, нормированная на максимум)",
        returns="диапазоны + заполнение (+ решётка heatmap при include_grid)",
        params=system_source_params([
            Param("num_rays", type="int", default=500,
                  help="число лучей пятна (сетка √N × √N)"),
            Param("grid_size", type="int", default=100,
                  help="размер гистограммы grid_size × grid_size"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("include_grid", type="bool", default=False,
                  help="включить решётку heatmap (большой объём)"),
        ]))
    def aber_spot_heatmap(ctx, file, system, lbo_index, lbo_name,
                          num_rays, grid_size, field_y, wl, include_grid):
        from analysis.aberrations import compute_spot_heatmap
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        heatmap, x_range, y_range = compute_spot_heatmap(
            sys_obj, wl=wl_eff, num_rays=num_rays, field_y=field_y,
            grid_size=grid_size)
        filled = int((heatmap > 0).sum())
        out = {
            "wl": wl_eff, "field_y": field_y, "grid_size": grid_size,
            "x_range": list(x_range), "y_range": list(y_range),
            "filled_cells": filled,
            "fill": filled / heatmap.size,
        }
        if include_grid:
            out["heatmap"] = heatmap.tolist()
        return out

    @registry.command(
        "aber.mtf_geo", category="aber",
        description="Геометрическая ЧКХ: FFT гистограммы точечной "
                    "диаграммы (танг./саг. срезы)",
        returns="строки [freq_лин/мм, MTF_tangential, MTF_sagittal]",
        params=system_source_params([
            Param("max_freq", type="float", default=100.0,
                  help="максимальная частота (лин/мм)"),
            Param("num_freqs", type="int", default=20,
                  help="число частот (плюс нулевая)"),
            Param("num_rays", type="int", default=MTF_GEO_SPOT_RAYS,
                  help="лучей по стороне сетки зрачка пятна"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_mtf_geo(ctx, file, system, lbo_index, lbo_name,
                     max_freq, num_freqs, num_rays, field_y, wl):
        from analysis.aberrations import (
            compute_geometric_mtf,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        spots = compute_spot_diagram(sys_obj, wl=wl_eff, num_rays=num_rays,
                                     field_y=field_y)
        mtf = compute_geometric_mtf(spots, max_freq=max_freq,
                                    num_freqs=num_freqs)
        return {"wl": wl_eff, "field_y": field_y, "num_points": len(spots),
                "mtf": [[f, t, s] for f, t, s in mtf]}

    @registry.command(
        "aber.spot_defocus", category="aber",
        description="Точечная диаграмма при смещении плоскости изображения",
        returns="точки относительно центроида (мм) + RMS",
        params=system_source_params([
            Param("defocus_mm", type="float", default=0.0,
                  help="смещение плоскости (+ дальше от системы)"),
            Param("num_rays", type="int", default=100,
                  help="лучей по стороне сетки зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_spot_defocus(ctx, file, system, lbo_index, lbo_name,
                          defocus_mm, num_rays, field_y, wl):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram_at_defocus,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        spots = compute_spot_diagram_at_defocus(
            sys_obj, wl=wl_eff, num_rays=num_rays, field_y=field_y,
            defocus_mm=defocus_mm)
        return {"wl": wl_eff, "field_y": field_y,
                "defocus_mm": defocus_mm, "num_points": len(spots),
                "rms": compute_rms_spot(spots),
                "spots": [[dx, dy] for dx, dy in spots]}

    @registry.command(
        "aber.focus_diagrams", category="aber",
        description="Фокусировочные диаграммы: 5 точечных диаграмм при "
                    "defocus = 0, ±ΔS', ±2ΔS'",
        returns="по метке позиции {defocus_mm, rms} (+spots при "
                "include_spots) и общий max_range",
        params=system_source_params([
            Param("focus_step_mm", type="float", default=0.1,
                  help="шаг фокусировки ΔS' (мм, настройка анализа)"),
            Param("num_rays", type="int", default=60,
                  help="лучей сетки зрачка на позицию"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("include_spots", type="bool", default=False,
                  help="включить точки пятен (большой объём)"),
        ]))
    def aber_focus_diagrams(ctx, file, system, lbo_index, lbo_name,
                            focus_step_mm, num_rays, field_y, wl,
                            include_spots):
        from analysis.aberrations import compute_focus_diagrams
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        diagrams, max_range = compute_focus_diagrams(
            sys_obj, wl=wl_eff, field_y=field_y,
            focus_step_mm=focus_step_mm, num_rays=num_rays)
        out = {"wl": wl_eff, "field_y": field_y,
               "focus_step_mm": focus_step_mm, "max_range": max_range,
               "diagrams": {}}
        for label, (spots, rms, defocus_mm) in diagrams.items():
            entry = {"defocus_mm": defocus_mm, "rms": rms}
            if include_spots:
                entry["spots"] = [[dx, dy] for dx, dy in spots]
            out["diagrams"][label] = entry
        return out

    @registry.command(
        "aber.isoplanatism", category="aber",
        description="Неизопланатизм осевого пучка: η(h) — изменение "
                    "поперечной аберрации при малом смещении предмета",
        returns="высоты зрачка + безразмерные η (0 = изопланатизм)",
        params=system_source_params([
            Param("num_rays", type="int", default=20,
                  help="лучей веера на каждую пробу поля"),
            Param("field_eps", type="float",
                  help="малое смещение поля ε; по умолчанию — авто "
                       "(5% макс. поля / типовое по типу предмета)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_isoplanatism(ctx, file, system, lbo_index, lbo_name,
                          num_rays, field_eps, wl):
        from analysis.aberrations import compute_isoplanatism
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        pupils, eta = compute_isoplanatism(
            sys_obj, wl=wl_eff, num_rays=num_rays, field_eps=field_eps)
        return {"wl": wl_eff, "num_rays": num_rays, "field_eps": field_eps,
                "pupil": list(pupils), "eta": list(eta)}

    @registry.command(
        "aber.oblique_fan", category="aber",
        description="Аберрации в косом сечении: веер под азимутальным "
                    "углом (0° — меридиональное, 90° — сагиттальное)",
        returns="высоты зрачка + dy меридиональное/сагиттальное (мкм)",
        params=system_source_params([
            Param("azimuth_deg", type="float", default=45.0,
                  help="азимут сечения (град, нормализуется к [0, 360))"),
            Param("num_rays", type="int", default=20, help="лучей веера"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_oblique_fan(ctx, file, system, lbo_index, lbo_name,
                         azimuth_deg, num_rays, field_y, wl):
        from analysis.aberrations import (
            compute_oblique_fan,
            normalize_azimuth_deg,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        pupils, dy_mer, dy_sag = compute_oblique_fan(
            sys_obj, wl=wl_eff, num_rays=num_rays, field_y=field_y,
            azimuth_deg=azimuth_deg)
        return {"wl": wl_eff, "field_y": field_y,
                "azimuth_deg": normalize_azimuth_deg(azimuth_deg),
                "pupil": list(pupils), "dy_mer_um": list(dy_mer),
                "dy_sag_um": list(dy_sag)}

    @registry.command(
        "aber.gauge_rays", category="aber",
        description="Габаритные лучи пучка (верх/низ/главный/саг±1): "
                    "координаты на поверхностях, направления, OPL",
        returns="5 лучей {key, label, points, directions, "
                "segment_lengths, path_length, opl}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_gauge_rays(ctx, file, system, lbo_index, lbo_name,
                        field_y, wl):
        from analysis.aberrations import compute_gauge_rays
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rays = compute_gauge_rays(sys_obj, wl=wl_eff, field_y=field_y)
        return {"wl": wl_eff, "field_y": field_y, "rays": [{
            "key": r["key"], "label": r["label"], "short": r["short"],
            "pupil": list(r["pupil"]), "success": r["success"],
            "error": r["error"],
            "points": [[p[0], p[1], p[2]] for p in r["points"]],
            "directions": [list(d) for d in r["directions"]],
            "segment_lengths": list(r["segment_lengths"]),
            "path_length": r["path_length"], "opl": r["opl"],
        } for r in rays]}

    @registry.command(
        "aber.ray_coordinates", category="aber",
        description="Координаты габаритных лучей (верхний/нижний/главный) "
                    "на каждой поверхности и плоскости изображения",
        returns="строки {surface, x/y/z_upper, x/y/z_lower, x/y/z_chief}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_ray_coordinates(ctx, file, system, lbo_index, lbo_name,
                             field_y, wl):
        from analysis.aberrations import compute_ray_coordinates
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = compute_ray_coordinates(sys_obj, wl=wl_eff,
                                       field_y=field_y)
        return {"wl": wl_eff, "field_y": field_y, "rows": rows}

    @registry.command(
        "aber.fields", category="aber",
        description="Точки поля для анализа по полю: все точки системы "
                    "(0 добавляется) или равномерная сетка",
        returns="список полей (град/мм)",
        params=system_source_params([
            Param("num_fields", type="int", default=5,
                  help="число точек, если поле системы не задано"),
        ]))
    def aber_fields(ctx, file, system, lbo_index, lbo_name, num_fields):
        from analysis.aberrations import analysis_field_points
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"fields": analysis_field_points(sys_obj,
                                                num_fields=num_fields)}

    @registry.command(
        "aber.wavefront", category="aber",
        description="Волновая аберрация W на гексаполярной сетке зрачка "
                    "(OPL до опорной сферы, в длинах волн)",
        returns="точки [px, py, W]",
        params=system_source_params([
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rings", type="int", default=4,
                  help="колец гексаполярной сетки (4 → 61 точка)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_wavefront(ctx, file, system, lbo_index, lbo_name,
                       field_y, num_rings, wl):
        from analysis.aberrations import trace_wavefront_hexapolar
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        points = trace_wavefront_hexapolar(
            sys_obj, wl=wl_eff, field_y=field_y, num_rings=num_rings)
        return {"wl": wl_eff, "field_y": field_y, "num_rings": num_rings,
                "points": [[px, py, w] for px, py, w in points]}

    @registry.command(
        "aber.wavefront_rms", category="aber",
        description="СКВ волновой аберрации W по полю (гексаполярная "
                    "сетка зрачка в каждой точке поля)",
        returns="поля + СКВ (длины волн; null — лучей мало)",
        params=system_source_params([
            Param("num_rings", type="int", default=4,
                  help="колец гексаполярной сетки зрачка"),
            Param("num_fields", type="int", default=5,
                  help="точек поля, если поле системы не задано"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_wavefront_rms(ctx, file, system, lbo_index, lbo_name,
                           num_rings, num_fields, wl):
        from analysis.aberrations import compute_wavefront_rms_vs_field
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        fields, rms = compute_wavefront_rms_vs_field(
            sys_obj, wl=wl_eff, num_rings=num_rings,
            num_fields=num_fields)
        return {"wl": wl_eff, "fields": list(fields), "rms": list(rms)}

    @registry.command(
        "aber.coddington", category="aber",
        description="След Коддингтона вдоль главного луча: отрезки "
                    "Z'm/Z's, астигматизм (дифференциальный реверс §7)",
        returns="{z_m, z_s, delta_zm, delta_zs, astigmatism, u_m, u_s, "
                "t_m, t_s}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_coddington(ctx, file, system, lbo_index, lbo_name,
                        field_y, wl):
        from analysis.aberrations import coddington_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        out = coddington_trace(sys_obj, wl=wl_eff, field_y=field_y)
        out["wl"] = wl_eff
        out["field_y"] = field_y
        return out

    @registry.command(
        "aber.caustic", category="aber",
        description="Радиусы кривизны каустик 2-го порядка (меридиональная/"
                "сагиттальная) у фокусов Коддингтона",
        returns="{r_m, r_s, r_m_rel, r_s_rel, method, ...} (мм / % от f')",
        params=system_source_params([
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("ray_halfheight", type="float",
                  help="высота δ крайних лучей (мм); по умолчанию — 1% "
                       "радиуса зрачка"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def aber_caustic(ctx, file, system, lbo_index, lbo_name,
                     field_y, ray_halfheight, wl):
        from analysis.aberrations import caustic_radii
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        out = caustic_radii(sys_obj, wl=wl_eff, field_y=field_y,
                            ray_halfheight=ray_halfheight)
        out["wl"] = wl_eff
        out["field_y"] = field_y
        return out

    # ================================================================
    # chrom.* — analysis/chromatism.py
    # ================================================================

    @registry.command(
        "chrom.opal", category="chrom",
        description="OPAL-режим хроматизма: повторная трассировка с λ "
                    "помеченных поверхностей; таблица TABAX3",
        returns="{wl_main, mode, field_y, rows, text} — строки TABAX3 + "
                "текстовый формат OPAL",
        params=system_source_params([
            Param("wl_main", type="float",
                  help="основная λ пары (мкм); по умолчанию — основная λ "
                       "системы"),
            Param("wl_flags", type="list",
                  help="флаги волн по поверхностям: 0 — основная λ, int ≥ 1 "
                       "— индекс λ системы (1-основной), float > 0 — λ мкм; "
                       "по умолчанию — Surface.wl_flag / fallback по всем λ"),
            Param("field_y", type="float",
                  help="поле главного луча; по умолчанию — максимальное "
                       "поле системы"),
        ]))
    def chrom_opal(ctx, file, system, lbo_index, lbo_name,
                   wl_main, wl_flags, field_y):
        from analysis.chromatism import compute_chromatism_opal, format_tabax3
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        result = compute_chromatism_opal(
            sys_obj, wl_main=wl_main,
            wl_flags=_coerce_wl_flags(wl_flags) if wl_flags else None,
            field_y=field_y)
        return {"wl_main": result["wl_main"], "mode": result["mode"],
                "field_y": result["field_y"], "rows": result["rows"],
                "text": format_tabax3(result)}

    # ================================================================
    # seidel.* — analysis/seidel_check.py
    # ================================================================

    @registry.command(
        "seidel.sums", category="seidel",
        description="Суммы Зейделя SI..SV + хроматические SIхр/SIIхр "
                    "(независимая реализация для контроля паритета)",
        returns="{SI..SV, SIxp, SIIxp, wl, wl_lo, wl_hi, chromatic}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def seidel_sums_cmd(ctx, file, system, lbo_index, lbo_name, wl):
        from analysis.seidel_check import seidel_sums
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        return seidel_sums(sys_obj, wl=wl_eff)

    @registry.command(
        "seidel.check_tracing", category="seidel",
        description="Численная сверка сумм Зейделя с трассировкой: "
                    "коэффициенты 3-го порядка (МНК по веерам), знаки",
        returns="{sums, axial, field, chromatic, signs, orders}",
        params=system_source_params([
            Param("field_y", type="float", required=True,
                  help="поле полевого веера (град/мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def seidel_check_tracing(ctx, file, system, lbo_index, lbo_name,
                             field_y, wl):
        from analysis.seidel_check import compare_with_tracing
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        return compare_with_tracing(sys_obj, field_y=field_y, wl=wl_eff)

    @registry.command(
        "seidel.vs_golden", category="seidel",
        description="Сверка сумм Зейделя с секцией golden .PRN OPAL "
                    "(sumsed): знаки + отношения Sₖ/S1",
        returns="{status: matched|mismatch|skipped, signs, ratios, ...}",
        params=system_source_params([
            Param("prn", required=True,
                  help="путь к .PRN OPAL (cp866)"),
            Param("tol", type="float", default=0.05,
                  help="допуск относительного расхождения отношений"),
        ]))
    def seidel_vs_golden_cmd(ctx, file, system, lbo_index, lbo_name,
                             prn, tol):
        from analysis.seidel_check import seidel_vs_golden
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return seidel_vs_golden(sys_obj, prn, tol=tol)

    @registry.command(
        "seidel.parse_prn", category="seidel",
        description="Строки секции сумм Зейделя из .PRN OPAL (sumsed, "
                    "cp866) — без системы",
        returns="строки {n, S1..S5, S1xp, S2xp} (может быть пусто)",
        params=[
            Param("prn", required=True, help="путь к .PRN OPAL (cp866)"),
        ])
    def seidel_parse_prn(ctx, prn):
        from analysis.seidel_check import parse_prn_seidel
        rows = parse_prn_seidel(prn)
        return {"rows": rows, "num_rows": len(rows)}

    # ================================================================
    # adv.* — analysis/advanced.py
    # ================================================================

    @registry.command(
        "adv.psf", category="adv",
        description="Дифракционная ФРТ через FFT зрачковой функции "
                    "(с параксиальным дефокусом)",
        returns="масштаб изображения (+решётки psf/x/y при include_grid)",
        params=system_source_params([
            Param("num_rays", type="int", default=128,
                  help="размер сетки зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("defocus_mm", type="float", default=0.0,
                  help="смещение плоскости установки (мм)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("include_grid", type="bool", default=False,
                  help="включить решётки psf/x_um/y_um (большой объём)"),
        ]))
    def adv_psf(ctx, file, system, lbo_index, lbo_name,
                num_rays, field_y, defocus_mm, wl, include_grid):
        from analysis.advanced import compute_psf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        psf, dx, dy = compute_psf(sys_obj, wl=wl_eff, num_rays=num_rays,
                                  field_y=field_y,
                                  defocus_mm=defocus_mm)
        out = {"wl": wl_eff, "num_rays": num_rays, "field_y": field_y,
               "defocus_mm": defocus_mm,
               "pixel_um": float(dx[1] - dx[0]),
               "x_range_um": [float(dx[0]), float(dx[-1])],
               "y_range_um": [float(dy[0]), float(dy[-1])]}
        if include_grid:
            out["psf"] = psf.tolist()
            out["x_um"] = dx.tolist()
            out["y_um"] = dy.tolist()
        return out

    @registry.command(
        "adv.lsf", category="adv",
        description="ФРЛ (LSF): интеграл ФРТ по одному направлению — "
                    "отклик на щель",
        returns="профиль lsf (нормирован на 1) + ось (мкм)",
        params=system_source_params([
            Param("direction", choices=list(LSF_DIRECTION_CHOICES),
                  default="tangential",
                  help="tangential — LSF(x) (вертикальная щель), "
                       "sagittal — LSF(y)"),
            Param("num_rays", type="int", default=128,
                  help="размер сетки зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_lsf(ctx, file, system, lbo_index, lbo_name,
                direction, num_rays, field_y, wl):
        from analysis.advanced import compute_lsf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        lsf, axis = compute_lsf(sys_obj, wl=wl_eff, num_rays=num_rays,
                                field_y=field_y, direction=direction)
        return {"wl": wl_eff, "direction": direction, "field_y": field_y,
                "x_um": axis.tolist(), "lsf": lsf.tolist()}

    @registry.command(
        "adv.enc", category="adv",
        description="ФКЭ (Encircled Energy): доля энергии пятна внутри "
                    "радиуса r (геометрически, по точечной диаграмме)",
        returns="радиусы (мкм) + доли энергии [0..1]",
        params=system_source_params([
            Param("num_rays", type="int", default=200,
                  help="лучей точечной диаграммы"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_enc(ctx, file, system, lbo_index, lbo_name,
                num_rays, field_y, wl):
        from analysis.advanced import compute_enc
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        r_um, enc = compute_enc(sys_obj, wl=wl_eff, num_rays=num_rays,
                                field_y=field_y)
        return {"wl": wl_eff, "field_y": field_y,
                "r_um": r_um.tolist(), "enc": enc.tolist()}

    @registry.command(
        "adv.ptf", category="adv",
        description="ФКП (PTF): фазовая ЧКХ = arg(OTF), тангенциальная и "
                    "сагиттальная",
        returns="{freqs, ptf_tangential, ptf_sagittal, cutoff_freq}",
        params=system_source_params([
            Param("num_rays", type="int", default=128,
                  help="размер сетки зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_ptf(ctx, file, system, lbo_index, lbo_name,
                num_rays, field_y, wl):
        from analysis.advanced import compute_ptf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        return compute_ptf(sys_obj, wl=wl_eff, num_rays=num_rays,
                           field_y=field_y)

    @registry.command(
        "adv.bar_image", category="adv",
        description="Симуляция изображения штриховой миры: свёртка "
                    "идеального профиля с ФРЛ",
        returns="ось (мкм) + идеальный и размытый профили",
        params=system_source_params([
            Param("bar_freq_lp_mm", type="float", default=10.0,
                  help="частота миры (лин/мм)"),
            Param("num_bars", type="int", default=5,
                  help="число штрихов (параметр сигнатуры)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_bar_image(ctx, file, system, lbo_index, lbo_name,
                      bar_freq_lp_mm, num_bars, field_y, wl):
        from analysis.advanced import compute_bar_target_image
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        x_um, ideal, blurred = compute_bar_target_image(
            sys_obj, wl=wl_eff, field_y=field_y, num_bars=num_bars,
            bar_freq_lp_mm=bar_freq_lp_mm)
        return {"wl": wl_eff, "field_y": field_y,
                "bar_freq_lp_mm": bar_freq_lp_mm,
                "x_um": x_um.tolist(), "ideal": ideal.tolist(),
                "blurred": blurred.tolist()}

    @registry.command(
        "adv.bar_mtf", category="adv",
        description="Таблица MTF по штриховой мире: контраст размытого "
                    "изображения на заданных частотах",
        returns="строки {freq, contrast_ideal, contrast_real, mtf}",
        params=system_source_params([
            Param("freq_list", type="list",
                  help="частоты (лин/мм); по умолчанию — [5, 10, 20, 30, "
                       "50, 80, 100]"),
            Param("num_bars", type="int", default=5,
                  help="число штрихов (параметр сигнатуры)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_bar_mtf(ctx, file, system, lbo_index, lbo_name,
                    freq_list, num_bars, field_y, wl):
        from analysis.advanced import compute_bar_target_mtf_table
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        freqs = [float(f) for f in freq_list] if freq_list else None
        rows = compute_bar_target_mtf_table(
            sys_obj, wl=wl_eff, field_y=field_y, num_bars=num_bars,
            freq_list=freqs)
        return {"wl": wl_eff, "field_y": field_y,
                "rows": [{k: float(v) if isinstance(v, float) else v
                          for k, v in row.items()} for row in rows]}

    @registry.command(
        "adv.esf", category="adv",
        description="ФКР (ESF): отклик на резкий край — интеграл ФРЛ "
                    "(тангенциальной)",
        returns="ось (мкм) + ESF от 0 до 1",
        params=system_source_params([
            Param("num_points", type="int", default=100,
                  help="параметр сигнатуры (сетка задаётся ФРЛ)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_esf(ctx, file, system, lbo_index, lbo_name,
                num_points, field_y, wl):
        from analysis.advanced import compute_esf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        x_um, esf = compute_esf(sys_obj, wl=wl_eff, field_y=field_y,
                                num_points=num_points)
        return {"wl": wl_eff, "field_y": field_y,
                "x_um": x_um.tolist(), "esf": esf.tolist()}

    @registry.command(
        "adv.object_image", category="adv",
        description="Симуляция изображения тест-объекта (мира/край/точка/"
                    "синус) — свёртка с дифракционной ФРТ",
        returns="метаданные + производные (+x/y/ideal/image/psf при "
                "include_grid)",
        params=system_source_params([
            Param("kind", choices=list(TEST_OBJECT_CHOICES),
                  default="mira", help="вид тест-объекта"),
            Param("num_rays", type="int", default=128,
                  help="размер сетки ФРТ"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("defocus_mm", type="float", default=0.0,
                  help="смещение плоскости установки (мм)"),
            Param("freq_lp_mm", type="float", default=10.0,
                  help="частота первой группы миры / синусоиды (лин/мм)"),
            Param("num_bars", type="int", default=6,
                  help="число групп штрихов миры"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("include_grid", type="bool", default=False,
                  help="включить решётки x/y/ideal/image/psf"),
        ]))
    def adv_object_image(ctx, file, system, lbo_index, lbo_name,
                         kind, num_rays, field_y, defocus_mm, freq_lp_mm,
                         num_bars, wl, include_grid):
        from analysis.advanced import compute_test_object_image
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        res = compute_test_object_image(
            sys_obj, kind=kind, wl=wl_eff, field_y=field_y,
            defocus_mm=defocus_mm, num_rays=num_rays,
            freq_lp_mm=freq_lp_mm, num_bars=num_bars)
        out = {"kind": kind, "wl": wl_eff, "field_y": field_y,
               "defocus_mm": res["defocus_mm"],
               "freq_lp_mm": res["freq_lp_mm"],
               "num_bars": res["num_bars"], "num_rays": num_rays,
               "image_peak": float(res["image"].max()),
               "image_mean": float(res["image"].mean())}
        if include_grid:
            out["x_um"] = res["x"].tolist()
            out["y_um"] = res["y"].tolist()
            out["ideal"] = res["ideal"].tolist()
            out["image"] = res["image"].tolist()
            out["psf"] = res["psf"].tolist()
        return out
