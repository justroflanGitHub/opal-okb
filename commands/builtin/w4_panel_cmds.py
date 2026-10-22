"""
OPAL-OKB — Команды Волны 4 (src=panel): gap-команды панели анализа.

Правила Волн 1/3: без Qt, JSON-контракт, обёртки над analysis/*
(нижние слои не меняются). Закрывают данные, которые нужны живым
таблицам ``gui/analysis_panel.py``, но не покрыты командами Волн 1+3:

* ``panel.spot.summary`` — сводка точечной диаграммы по каждой рабочей λ
  + полихроматическая строка (RMS по осям, центроид, макс. радиус);
  объединяет ``analyze.spot`` / ``aber.spot_poly`` / ``aber.rms_poly``
  в один вызов точно по строкам таблицы «Точечная диагр.»;
* ``panel.psf.stats`` — скалярные метрики дифракционной ФРТ для таблицы
  «PSF» (пиксель/максимум/центр пика/ширины мер/саг по полумаксимуму);
  решётки ФРТ в UI не передаются — только метрики.

``commands/builtin/__init__.py`` НЕ трогается (координатор соберёт ветки
после мержа): GUI регистрирует команды сам через :func:`ensure_registered`.
"""
import math

from optics_utils import get_primary_wl

from commands.base import Param
from commands.registry import Registry, default_registry
from commands.systemio import resolve_system, system_source_params

#: Резервная λ (мкм), когда у системы не задано ни одной (как в панели).
FALLBACK_WL_UM = 0.58756

#: Лучей точечной диаграммы в таблице панели (живой расчёт до Волны 4).
SPOT_TABLE_NUM_RAYS = 40

#: Лучей сетки зрачка ФРТ в таблице панели (живой расчёт до Волны 4).
PSF_TABLE_NUM_RAYS = 64


def _spot_row(kind: str, wl, points, rms) -> dict:
    """Строка сводки пятна: RMS по осям/центроид (analysis) + макс. радиус."""
    from analysis.aberrations import compute_rms_spot_xy
    rms_xy = compute_rms_spot_xy(list(points))
    max_r = max((math.sqrt(dx ** 2 + dy ** 2) for dx, dy in points),
                default=0.0)
    return {"kind": kind, "wl": wl, "num_points": len(points),
            "rms": float(rms), "rms_x": rms_xy["rms_x"],
            "rms_y": rms_xy["rms_y"], "centroid_y": rms_xy["centroid_y"],
            "max_r": float(max_r)}


def register(registry: Registry) -> None:
    """Зарегистрировать все команды panel.* (Волна 4, src=panel)."""

    @registry.command(
        "panel.spot.summary", category="panel",
        description="Сводка точечной диаграммы для таблицы панели: по "
                    "каждой рабочей λ + полихроматическая строка (RMS по "
                    "осям, центроид, макс. радиус)",
        returns="rows [{kind: mono|poly, wl, num_points, rms, rms_x, "
                "rms_y, centroid_y, max_r}]",
        params=system_source_params([
            Param("num_rays", type="int", default=SPOT_TABLE_NUM_RAYS,
                  help="лучей по стороне сетки зрачка"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
        ]))
    def panel_spot_summary(ctx, file, system, lbo_index, lbo_name,
                           num_rays, field_y):
        from analysis.aberrations import (
            compute_polychromatic_rms,
            compute_rms_spot,
            compute_spot_diagram,
            compute_spot_diagram_polychromatic,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_list = ([w.value for w in sys_obj.wavelengths]
                   if sys_obj.wavelengths else [FALLBACK_WL_UM])
        rows = []
        for wl in wl_list:
            spots = compute_spot_diagram(sys_obj, wl=wl, num_rays=num_rays,
                                         field_y=field_y)
            rows.append(_spot_row("mono", wl, spots, compute_rms_spot(spots)))
        if len(wl_list) > 1:
            poly = compute_spot_diagram_polychromatic(
                sys_obj, num_rays=num_rays, field_y=field_y)
            rms = compute_polychromatic_rms(sys_obj, num_rays=num_rays,
                                            field_y=field_y)
            rows.append(_spot_row(
                "poly", None, [(dx, dy) for dx, dy, _ in poly], rms))
        return {"field_y": field_y, "num_rays": num_rays,
                "num_wavelengths": len(wl_list), "rows": rows}

    @registry.command(
        "panel.psf.stats", category="panel",
        description="Скалярные метрики дифракционной ФРТ для таблицы "
                    "панели: размер пикселя, максимум, центр пика, ширины "
                    "меридиональная/сагиттальная по полумаксимуму",
        returns="{wl, num_rays, pixel_um, max_intensity, center_x_um, "
                "center_y_um, width_mer_um, width_sag_um}",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("num_rays", type="int", default=PSF_TABLE_NUM_RAYS,
                  help="размер сетки зрачка ФРТ"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("defocus_mm", type="float", default=0.0,
                  help="смещение плоскости установки, мм"),
        ]))
    def panel_psf_stats(ctx, file, system, lbo_index, lbo_name,
                        wl, num_rays, field_y, defocus_mm):
        import numpy as np
        from analysis.advanced import compute_psf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        psf, dx, dy = compute_psf(sys_obj, wl=wl_eff, num_rays=num_rays,
                                  field_y=field_y, defocus_mm=defocus_mm)
        if psf is None:
            return {"wl": wl_eff, "num_rays": num_rays,
                    "reason": "ФРТ не построена"}
        # Метрики живой таблицы «PSF» панели (перенесены из analysis_panel)
        pix_size = ((dx.max() - dx.min()) / len(dx)) if len(dx) > 1 else 0.0
        max_intens = float(psf.max())
        cy, cx = np.unravel_index(np.argmax(psf), psf.shape)
        center_x = float(dx[cx]) if cx < len(dx) else 0.0
        center_y = float(dy[cy]) if cy < len(dy) else 0.0
        half_max = max_intens / 2
        try:
            w_mer = float((dx.max() - dx.min()) / len(dx)
                          * np.sum(psf[cy, :] > half_max))
            w_sag = float((dy.max() - dy.min()) / len(dy)
                          * np.sum(psf[:, cx] > half_max))
        except Exception:
            w_mer = w_sag = 0.0
        return {"wl": wl_eff, "num_rays": num_rays,
                "pixel_um": float(pix_size),
                "max_intensity": max_intens,
                "center_x_um": center_x, "center_y_um": center_y,
                "width_mer_um": w_mer, "width_sag_um": w_sag}


#: Команда-маркер: регистрация w4_panel_cmds уже выполнена.
_PANEL_MARK = "panel.spot.summary"


def ensure_registered(registry: Registry = None) -> Registry:
    """Идемпотентно зарегистрировать команды panel.* в реестр.

    ``commands/builtin/__init__.py`` не знает о Волнах 4 (координатор
    соберёт ветки после мержа), поэтому GUI регистрирует gap-команды
    сам при создании панели.
    """
    reg = registry if registry is not None else default_registry
    if not reg.has(_PANEL_MARK):
        register(reg)
    return reg
