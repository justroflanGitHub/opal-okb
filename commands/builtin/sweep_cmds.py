"""
OPAL-OKB — Пакет R500-7: развёртки (sweep) и верифицируемые величины
3-го порядка (seidel3).

- ``sweep.*`` — развёртки характеристик по полям/λ/дефокусу/зонам
  зрачка/апертуре/азимутам/положению диафрагмы — циклы поверх
  СУЩЕСТВУЮЩИХ движков (compute_spot_diagram*, compute_geometric_mtf,
  compute_strehl, compute_oblique_fan, trace_grid_3d, compute_enc,
  compute_lsf, seidel_aberrations, zern.wavefront). Новых ядер нет;
- ``seidel3.*`` — только величины, выводимые из сумм Зейделя порта без
  неформализованных констант связки: сумма Петцваля → радиус поля,
  ранжирование/нормировка сумм, хроматизм положения/увеличения через
  параксиальный расчёт по λ (сравни с seidel.check_tracing для
  трассировочных коэффициентов).

Заблокировано (R500_PACKAGES): поперечные/продольные аберрации в мм
прямо из SI..SV — нормировка вспомогательных лучей порта не
формализована (analysis/seidel_check.py: «константы связки не
сверяются»).
"""
import copy
import math

from commands.base import ERR_INVALID_PARAM, Param, CommandError
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
)

from optics_utils import get_primary_wl

from commands.builtin._r500_common import fields_arg as _fields_arg
from commands.builtin._r500_common import system_wls as _wls_arg

#: Число точек развёрток по умолчанию.
SWEEP_STEPS_DEFAULT = 9

#: Диапазон дефокуса по умолчанию, мм.
DEFOCUS_RANGE_DEFAULT = (-1.0, 1.0)

#: Азимуты сечений по умолчанию, град (мер/наклон/саг).
AZIMUTHS_DEFAULT = (0.0, 45.0, 90.0)

#: Метки сумм Зейделя для ранжирования.
SEIDEL_LABELS = {
    "SI": "сферическая аберрация",
    "SII": "кома",
    "SIII": "астигматизм",
    "SIV": "кривизна поля (Петцваль)",
    "SV": "дисторсия",
}


def _linspace(lo: float, hi: float, steps: int):
    """Равномерная сетка steps точек (steps ≥ 2)."""
    if steps < 2:
        raise CommandError(ERR_INVALID_PARAM, "steps ≥ 2")
    return [lo + (hi - lo) * i / (steps - 1) for i in range(steps)]


def _fwhm_um(profile, axis) -> float:
    """Ширина на половине максимума (мкм) по профилю и оси."""
    import numpy as np
    peak = float(np.max(profile))
    if peak <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "профиль вырожден (max ≤ 0)")
    above = [i for i, v in enumerate(profile) if v >= 0.5 * peak]
    return float(axis[above[-1]] - axis[above[0]])


def register(registry: Registry) -> None:
    """Зарегистрировать команды sweep/seidel3 (R500-7)."""

    # ============================================================
    # Развёртки по полям
    # ============================================================

    @registry.command(
        "sweep.fields.spot_rms", category="sweep",
        description="RMS кружка рассеяния по полям (мм): полный и по "
                    "осям",
        returns="{wl, rows: [{field_y, rms, rms_x, rms_y, num_points}]}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=30, help="лучей сетки"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_fields_spot_rms(ctx, file, system, lbo_index, lbo_name,
                              fields, num_rays, wl):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_rms_spot_xy,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            spots = compute_spot_diagram(sys_obj, wl=wl_eff,
                                         num_rays=num_rays,
                                         field_y=field)
            xy = compute_rms_spot_xy(spots)
            rows.append({"field_y": field,
                         "rms": compute_rms_spot(spots),
                         "rms_x": xy["rms_x"], "rms_y": xy["rms_y"],
                         "num_points": len(spots)})
        return {"wl": wl_eff, "rows": rows, "num_fields": len(rows)}

    @registry.command(
        "sweep.fields.mtf", category="sweep",
        description="Геометрическая ЧКХ на частоте по полям "
                    "(танг./саг.)",
        returns="{wl, freq_lpmm, rows: [{field_y, mtf_t, mtf_s}]}",
        params=system_source_params() + [
            Param("freq_lpmm", type="float", default=50.0,
                  help="частота, лин/мм"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=40,
                  help="лучей точечной диаграммы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_fields_mtf(ctx, file, system, lbo_index, lbo_name,
                         freq_lpmm, fields, num_rays, wl):
        from analysis.aberrations import (
            compute_geometric_mtf,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            spots = compute_spot_diagram(sys_obj, wl=wl_eff,
                                         num_rays=num_rays,
                                         field_y=field)
            curve = compute_geometric_mtf(spots, max_freq=freq_lpmm,
                                          num_freqs=1)
            # кривая: [(0, 1, 1), (freq, t, s)] — частота 0 всегда 1
            _f0, t0, s0 = curve[0]
            _f1, t1, s1 = curve[1] if len(curve) > 1 else (0.0, t0, s0)
            rows.append({"field_y": field, "mtf_t": t1, "mtf_s": s1,
                         "dc_t": t0})
        return {"wl": wl_eff, "freq_lpmm": freq_lpmm, "rows": rows}

    @registry.command(
        "sweep.fields.strehl", category="sweep",
        description="Число Штреля по полям (точное по волновому фронту)",
        returns="{wl, rows: [{field_y, strehl_exact, sigma_w, validity}]}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_fields_strehl(ctx, file, system, lbo_index, lbo_name,
                            fields, wl):
        from analysis.strehl import compute_strehl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            strehl = compute_strehl(sys_obj, wl=wl_eff, field_y=field)
            rows.append({"field_y": field,
                         "strehl_exact": strehl.get("strehl_exact"),
                         "sigma_w": strehl.get("sigma_w"),
                         "validity": strehl.get("validity")})
        return {"wl": wl_eff, "rows": rows}

    @registry.command(
        "sweep.fields.enc", category="sweep",
        description="Доля энергии в кружке радиуса r по полям (ФКЭ)",
        returns="{wl, radius_um, rows: [{field_y, enc}]}",
        params=system_source_params() + [
            Param("radius_um", type="float", default=20.0,
                  help="радиус кружка, мкм"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=100, help="лучей"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_fields_enc(ctx, file, system, lbo_index, lbo_name,
                         radius_um, fields, num_rays, wl):
        import numpy as np
        from analysis.advanced import compute_enc
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            r_um, enc = compute_enc(sys_obj, wl=wl_eff,
                                    num_rays=num_rays, field_y=field)
            rows.append({"field_y": field,
                         "enc": float(np.interp(radius_um, r_um, enc))})
        return {"wl": wl_eff, "radius_um": radius_um, "rows": rows}

    @registry.command(
        "sweep.fields.lsf_width", category="sweep",
        description="Ширина ФРЛ на половине максимума (FWHM, мкм) по "
                    "полям",
        returns="{wl, rows: [{field_y, fwhm_um}]}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=64, help="сетка зрачка"),
            Param("direction", choices=["tangential", "sagittal"],
                  default="tangential", help="направление щели"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_fields_lsf_width(ctx, file, system, lbo_index, lbo_name,
                               fields, num_rays, direction, wl):
        from analysis.advanced import compute_lsf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            lsf, axis = compute_lsf(sys_obj, wl=wl_eff,
                                    num_rays=num_rays, field_y=field,
                                    direction=direction)
            rows.append({"field_y": field,
                         "fwhm_um": _fwhm_um(lsf, axis)})
        return {"wl": wl_eff, "direction": direction, "rows": rows}

    @registry.command(
        "sweep.fields.chrom_shift", category="sweep",
        description="Смещение центроида пятна между крайними λ по полям "
                    "(хроматизм увеличения, мм)",
        returns="{wl_lo, wl_hi, rows: [{field_y, shift_mm, dy}]}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=30, help="лучей сетки"),
        ])
    def sweep_fields_chrom_shift(ctx, file, system, lbo_index, lbo_name,
                                 fields, num_rays):
        from analysis.aberrations import compute_spot_diagram
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wls = _wls_arg(sys_obj)
        if len(wls) < 2:
            raise CommandError(ERR_INVALID_PARAM,
                               "нужны ≥2 рабочих λ (хроматизм)")
        rows = []
        for field in _fields_arg(sys_obj, fields):
            centroids = {}
            for wl in (wls[0], wls[-1]):
                spots = compute_spot_diagram(sys_obj, wl=wl,
                                             num_rays=num_rays,
                                             field_y=field)
                if not spots:
                    raise CommandError(ERR_INVALID_PARAM,
                                       f"веер не дошёл (поле {field})")
                cx = sum(p[0] for p in spots) / len(spots)
                cy = sum(p[1] for p in spots) / len(spots)
                centroids[wl] = (cx, cy)
            (x1, y1), (x2, y2) = centroids[wls[0]], centroids[wls[-1]]
            rows.append({"field_y": field,
                         "shift_mm": math.hypot(x2 - x1, y2 - y1),
                         "dy": y2 - y1, "dx": x2 - x1})
        return {"wl_lo": wls[0], "wl_hi": wls[-1], "rows": rows}

    # ============================================================
    # Развёртки по λ
    # ============================================================

    @registry.command(
        "sweep.wl.spot_rms", category="sweep",
        description="RMS кружка по рабочим λ системы (на поле)",
        returns="{rows: [{wl, rms, num_points}]}",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=30, help="лучей сетки"),
        ])
    def sweep_wl_spot_rms(ctx, file, system, lbo_index, lbo_name,
                          field_y, num_rays):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for wl in _wls_arg(sys_obj):
            spots = compute_spot_diagram(sys_obj, wl=wl,
                                         num_rays=num_rays,
                                         field_y=field_y)
            rows.append({"wl": wl, "rms": compute_rms_spot(spots),
                         "num_points": len(spots)})
        return {"field_y": field_y, "rows": rows}

    @registry.command(
        "sweep.wl.strehl", category="sweep",
        description="Число Штреля по рабочим λ (на поле)",
        returns="{rows: [{wl, strehl_exact, sigma_w}]}",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
        ])
    def sweep_wl_strehl(ctx, file, system, lbo_index, lbo_name, field_y):
        from analysis.strehl import compute_strehl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for wl in _wls_arg(sys_obj):
            strehl = compute_strehl(sys_obj, wl=wl, field_y=field_y)
            rows.append({"wl": wl,
                         "strehl_exact": strehl.get("strehl_exact"),
                         "sigma_w": strehl.get("sigma_w")})
        return {"field_y": field_y, "rows": rows}

    # ============================================================
    # Развёртки по дефокусу
    # ============================================================

    @registry.command(
        "sweep.defocus.spot_rms", category="sweep",
        description="RMS кружка по дефокусу (плоскость наилучшей "
                    "установки геометрически)",
        returns="{wl, rows: [{defocus_mm, rms}], best}",
        params=system_source_params() + [
            Param("defocus_min", type="float",
                  default=DEFOCUS_RANGE_DEFAULT[0], help="начало, мм"),
            Param("defocus_max", type="float",
                  default=DEFOCUS_RANGE_DEFAULT[1], help="конец, мм"),
            Param("steps", type="int", default=SWEEP_STEPS_DEFAULT,
                  help="точек развёртки"),
            Param("num_rays", type="int", default=30, help="лучей сетки"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_defocus_spot_rms(ctx, file, system, lbo_index, lbo_name,
                               defocus_min, defocus_max, steps, num_rays,
                               field_y, wl):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram_at_defocus,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if defocus_min >= defocus_max:
            raise CommandError(ERR_INVALID_PARAM, "defocus_min < defocus_max")
        rows = []
        for d in _linspace(defocus_min, defocus_max, steps):
            spots = compute_spot_diagram_at_defocus(
                sys_obj, wl=wl_eff, num_rays=num_rays,
                field_y=field_y, defocus_mm=d)
            rows.append({"defocus_mm": d,
                         "rms": compute_rms_spot(spots)})
        best = min(rows, key=lambda r: r["rms"])
        return {"wl": wl_eff, "field_y": field_y, "rows": rows,
                "best": best}

    @registry.command(
        "sweep.defocus.wavefront_rms", category="sweep",
        description="RMS волнового фронта по дефокусу (λ на краю зрачка)",
        returns="{wl, rows: [{defocus_wl, rms_wl, pv_wl}], best}",
        params=system_source_params() + [
            Param("defocus_min", type="float", default=-2.0,
                  help="начало, длины волн"),
            Param("defocus_max", type="float", default=2.0,
                  help="конец, длины волн"),
            Param("steps", type="int", default=SWEEP_STEPS_DEFAULT,
                  help="точек развёртки"),
            Param("grid_size", type="int", default=32,
                  help="решётка зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_defocus_wavefront_rms(ctx, file, system, lbo_index,
                                    lbo_name, defocus_min, defocus_max,
                                    steps, grid_size, field_y, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if defocus_min >= defocus_max:
            raise CommandError(ERR_INVALID_PARAM, "defocus_min < defocus_max")
        # живой объект → сестринская команда через контекст (без файла)
        source_key = "_sweep_defocus_src"
        ctx.put_system(source_key, sys_obj, make_current=False)
        rows = []
        for d in _linspace(defocus_min, defocus_max, steps):
            result = registry.execute(
                "zern.wavefront", ctx,
                {"system": source_key, "grid_size": grid_size,
                 "field_y": field_y, "defocus_offset": d, "wl": wl_eff})
            if not result.ok:
                raise CommandError(result.error["code"],
                                   result.error["message"])
            rows.append({"defocus_wl": d,
                         "rms_wl": result.data["rms"],
                         "pv_wl": result.data["pv"]})
        ctx.drop_system(source_key)
        best = min(rows, key=lambda r: r["rms_wl"])
        return {"wl": wl_eff, "field_y": field_y, "rows": rows,
                "best": best}

    # ============================================================
    # Зоны зрачка / азимуты / апертура / диафрагма
    # ============================================================

    @registry.command(
        "sweep.zones.spot", category="sweep",
        description="RMS пятна по кольцам зрачка (зональная "
                    "декомпозиция)",
        returns="{wl, rows: [{ring, rho, rms, num_points}]}",
        params=system_source_params() + [
            Param("num_rings", type="int", default=4, help="колец зрачка"),
            Param("num_azimuths", type="int", default=8,
                  help="азимутов на кольцо"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_zones_spot(ctx, file, system, lbo_index, lbo_name,
                         num_rings, num_azimuths, field_y, wl):
        from analysis.ray_tracing import trace_grid_3d
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rings = trace_grid_3d(sys_obj, num_rings=num_rings,
                              num_azimuths=num_azimuths, wl=wl_eff,
                              field_y=field_y)
        rows = []
        for ring_idx, ring in enumerate(rings):
            rho = 0.0 if ring_idx == 0 else (ring_idx + 1) / num_rings
            pts = [r.path[-1][:2] for r in ring
                   if getattr(r, "success", False) and r.path]
            if not pts:
                rows.append({"ring": ring_idx, "rho": rho, "rms": None,
                             "num_points": 0})
                continue
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            rms = math.sqrt(sum((p[0] - cx) ** 2 + (p[1] - cy) ** 2
                                for p in pts) / len(pts))
            rows.append({"ring": ring_idx, "rho": rho, "rms": rms,
                         "num_points": len(pts)})
        return {"wl": wl_eff, "field_y": field_y, "rows": rows}

    @registry.command(
        "sweep.azimuth.aberrations", category="sweep",
        description="Поперечная аберрация веера по азимутам сечений "
                    "(0° — мер., 90° — саг.)",
        returns="{wl, rows: [{azimuth_deg, rms_dy, max_dy}]}",
        params=system_source_params() + [
            Param("azimuths", type="list",
                  help="список азимутов, град; по умолчанию 0/45/90"),
            Param("field_y", type="float", required=True, help="поле"),
            Param("num_rays", type="int", default=15, help="лучей веера"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_azimuth_aberrations(ctx, file, system, lbo_index, lbo_name,
                                  azimuths, field_y, num_rays, wl):
        from analysis.aberrations import compute_oblique_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        angles = [float(a) for a in azimuths] if azimuths \
            else list(AZIMUTHS_DEFAULT)
        rows = []
        for angle in angles:
            fan = compute_oblique_fan(sys_obj, wl=wl_eff,
                                      num_rays=num_rays,
                                      field_y=field_y,
                                      azimuth_deg=angle)
            dys = fan[1]  # строка 1 — поперечная аберрация по ρ
            rows.append({"azimuth_deg": angle,
                         "rms_dy": math.sqrt(
                             sum(v * v for v in dys) / len(dys)),
                         "max_dy": max(abs(v) for v in dys)})
        return {"wl": wl_eff, "field_y": field_y, "rows": rows}

    @registry.command(
        "sweep.aperture.spot_rms", category="sweep",
        description="RMS кружка по диаметрам зрачка (апертуре)",
        returns="{wl, rows: [{epd_mm, rms}]}",
        params=system_source_params() + [
            Param("apertures", type="list", required=True,
                  help="диаметры входного зрачка, мм"),
            Param("num_rays", type="int", default=30, help="лучей сетки"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_aperture_spot_rms(ctx, file, system, lbo_index, lbo_name,
                                apertures, num_rays, field_y, wl):
        from domain.models import ApertureType
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if not apertures:
            raise CommandError(ERR_INVALID_PARAM, "apertures пуст")
        rows = []
        for epd in apertures:
            probe = copy.deepcopy(sys_obj)
            probe.aperture_type = ApertureType.ENTRANCE_PUPIL
            probe.aperture_value = float(epd)
            spots = compute_spot_diagram(probe, wl=wl_eff,
                                         num_rays=num_rays,
                                         field_y=field_y)
            rows.append({"epd_mm": float(epd),
                         "rms": compute_rms_spot(spots)})
        return {"wl": wl_eff, "field_y": field_y, "rows": rows}

    @registry.command(
        "sweep.stop.seidel", category="sweep",
        description="Суммы Зейделя SI..SV по положениям апертурной "
                    "диафрагмы (теория переноса диафрагмы)",
        returns="{wl, rows: [{stop_surface, SI, SII, SIII, SIV, SV}]}",
        params=system_source_params() + [
            Param("stop_surfaces", type="list",
                  help="позиции диафрагмы (0-based); по умолчанию — все"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def sweep_stop_seidel(ctx, file, system, lbo_index, lbo_name,
                          stop_surfaces, wl):
        from domain.calculations import seidel_aberrations
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        positions = ([int(p) for p in stop_surfaces] if stop_surfaces
                     else list(range(sys_obj.num_surfaces)))
        rows = []
        for pos in positions:
            if not (0 <= pos < sys_obj.num_surfaces):
                raise CommandError(ERR_INVALID_PARAM,
                                   f"stop_surface={pos} вне диапазона")
            probe = copy.deepcopy(sys_obj)
            probe.stop_surface = pos
            sums = seidel_aberrations(probe)
            rows.append({"stop_surface": pos,
                         **{k: sums[k] for k in SEIDEL_LABELS}})
        return {"wl": wl_eff, "rows": rows}

    # ============================================================
    # seidel3.* — верифицируемые величины из сумм
    # ============================================================

    @registry.command(
        "seidel3.petzval.radius", category="seidel3",
        description="Радиус кривизны поверхности Петцваля из суммы SIV "
                    "(SIV = Σ(n′−n)/(R·n·n′) = 1/R_p)",
        returns="{wl, SIV, petzval_radius_mm}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def seidel3_petzval_radius(ctx, file, system, lbo_index, lbo_name, wl):
        from domain.calculations import seidel_aberrations
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        sums = seidel_aberrations(sys_obj)
        s4 = sums["SIV"]
        if abs(s4) < 1e-15:
            raise CommandError(ERR_INVALID_PARAM,
                               "SIV ≈ 0: поле Петцваля плоское (R→∞)")
        return {"wl": wl_eff, "SIV": s4,
                "petzval_radius_mm": 1.0 / s4}

    @registry.command(
        "seidel3.sums.ranking", category="seidel3",
        description="Ранжирование сумм Зейделя по модулю с метками "
                    "аберраций и долями",
        returns="{wl, ranking: [{sum, label, value, share}]}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def seidel3_sums_ranking(ctx, file, system, lbo_index, lbo_name, wl):
        from domain.calculations import seidel_aberrations
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        sums = seidel_aberrations(sys_obj)
        top = max(abs(v) for v in sums.values()) or 1.0
        ranking = sorted(
            ({"sum": k, "label": SEIDEL_LABELS[k], "value": sums[k],
              "share": abs(sums[k]) / top}
             for k in SEIDEL_LABELS),
            key=lambda r: -r["share"])
        return {"wl": wl_eff, "ranking": ranking}

    @registry.command(
        "seidel3.sums.normalized", category="seidel3",
        description="Суммы Зейделя, нормированные на SI (относительная "
                    "картина коррекции)",
        returns="{wl, SI, ratios: {SII: SII/SI, ...}}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def seidel3_sums_normalized(ctx, file, system, lbo_index, lbo_name,
                                wl):
        from domain.calculations import seidel_aberrations
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        sums = seidel_aberrations(sys_obj)
        if abs(sums["SI"]) < 1e-15:
            raise CommandError(ERR_INVALID_PARAM,
                               "SI ≈ 0: нормировка на SI невозможна")
        return {"wl": wl_eff, "SI": sums["SI"],
                "ratios": {k: sums[k] / sums["SI"]
                           for k in ("SII", "SIII", "SIV", "SV")}}

    @registry.command(
        "seidel3.chromatic.position", category="seidel3",
        description="Хроматизм положения: f′ и BFD по всем рабочим λ, "
                    "Δf′ между крайними",
        returns="{rows: [{wl, f_prime, bfd}], delta_f_mm, wl_lo, wl_hi}",
        params=system_source_params())
    def seidel3_chromatic_position(ctx, file, system, lbo_index, lbo_name):
        from domain.calculations import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wls = _wls_arg(sys_obj)
        if len(wls) < 2:
            raise CommandError(ERR_INVALID_PARAM, "нужны ≥2 рабочих λ")
        rows = []
        for wl in wls:
            parax = paraxial_trace(sys_obj, wl=wl)
            rows.append({"wl": wl,
                         "f_prime": parax.get("focal_length"),
                         "bfd": parax.get("back_focal_distance")})
        return {"rows": rows, "wl_lo": wls[0], "wl_hi": wls[-1],
                "delta_f_mm": rows[-1]["f_prime"] - rows[0]["f_prime"]}

    @registry.command(
        "seidel3.chromatic.magnitude", category="seidel3",
        description="Хроматизм увеличения: V(λ) по рабочим λ и "
                    "относительное изменение",
        returns="{rows: [{wl, V}], delta_V_pct, wl_lo, wl_hi}",
        params=system_source_params())
    def seidel3_chromatic_magnitude(ctx, file, system, lbo_index,
                                    lbo_name):
        from domain.calculations import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wls = _wls_arg(sys_obj)
        if len(wls) < 2:
            raise CommandError(ERR_INVALID_PARAM, "нужны ≥2 рабочих λ")
        rows = []
        for wl in wls:
            parax = paraxial_trace(sys_obj, wl=wl)
            rows.append({"wl": wl, "V": parax.get("V")})
        v_lo = rows[0]["V"] or 0.0
        v_hi = rows[-1]["V"] or 0.0
        base = abs(v_lo) or 1.0
        return {"rows": rows, "wl_lo": wls[0], "wl_hi": wls[-1],
                "delta_V_pct": (v_hi - v_lo) / base * 100.0}
