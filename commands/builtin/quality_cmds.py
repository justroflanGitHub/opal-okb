"""
OPAL-OKB — Пакет R500-10: сводные метрики качества (quality).

ГОТОВЫЕ СВОДЫ/скаляры/паспорта как композиция существующих движков
(analysis/psf_mtf, analysis/aberrations, analysis/strehl,
analysis/advanced, domain.calculations.paraxial_trace) и сестринских
команд (mtf.curve, diffr.mtf.limited, calc.airy, quality.check.*).
Новых ядер нет; сырые развёртки — домен ``sweep.*`` (R500-7), здесь —
итоговые таблицы/числа/вердикты:

- ``quality.ee.*`` — диаметры зон задержанной энергии (50/80/90 %)
  геометрически и по дифракционной ФРТ;
- ``quality.spot.summary`` / ``quality.fields.summary`` — RMS по полям
  и λ, полихроматические своды;
- ``quality.mtf.*`` — MTF на заданных частотах по полям, полихрома,
  предельная частота порога, площадь под ЧКХ, гео vs дифракция;
- ``quality.strehl.summary`` / ``quality.wavefront.summary`` —
  полихроматический Штрель по полям, СКВ волнового фронта по полю;
- ``quality.passport`` / ``quality.compare`` — паспорт системы и
  сравнение двух систем по сводным метрикам;
- ``quality.check.*`` — пороговые проверки (MTF/Штрель/RMS/ФКЭ) с
  вердиктом pass/fail; ``quality.check.all`` — агрегат;
- ``quality.regime`` — чем ограничено пятно: дифракция или аберрации.
"""
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

#: Доли задержанной энергии по умолчанию (диаметры зон 50/80/90 %).
EE_FRACTIONS_DEFAULT = (0.5, 0.8, 0.9)

#: Доля энергии для одиночной проверки/свода (диаметр зоны 90 %).
EE_FRACTION_DEFAULT = 0.9

#: Частоты ЧКХ по умолчанию для матрицы MTF, лин/мм.
MTF_FREQS_DEFAULT = (20.0, 50.0, 100.0)

#: Частота ЧКХ по умолчанию для одиночных срезов, лин/мм.
MTF_FREQ_DEFAULT = 50.0

#: Лучей сетки зрачка в геометрических сводках пятна.
SPOT_RAYS_DEFAULT = 20

#: Лучей точечной диаграммы в геометрической ФКЭ.
EE_RAYS_DEFAULT = 100

#: Граница «дифракционно ограничена»: RMS пятна < 0.5·r_Эйри.
REGIME_DIFFRACTION_MAX_RATIO = 0.5

#: Граница «аберрационно ограничена»: RMS пятна > 2·r_Эйри.
REGIME_ABERATION_MIN_RATIO = 2.0

#: Первый нуль дискa Эйри: r₁ = 1.22·λ·F/# (мкм при λ в мкм).
AIRY_FIRST_ZERO = 1.22

#: Суффиксы служебных имён систем в контексте (живой объект →
#: сестринская команда; разные суффиксы исключают коллизии при
#: вложенных вызовах quality.check.all → quality.check.* → mtf.curve).
_PROBE_TAGS = {
    "mtf": "_quality_mtf",
    "chkmtf": "_quality_chkmtf",
    "all": "_quality_all",
    "area": "_quality_area",
    "pass": "_quality_pass",
    "cmp": "_quality_cmp",
}


def _put_probe(ctx, system, tag: str) -> str:
    """Положить систему в контекст под служебным именем (для execute)."""
    key = _PROBE_TAGS[tag]
    ctx.put_system(key, system, make_current=False)
    return key


def _fractions_arg(fractions):
    """Доли энергии: явный список или умолчание 50/80/90 %."""
    if not fractions:
        return list(EE_FRACTIONS_DEFAULT)
    values = [float(f) for f in fractions]
    if not all(0.0 < f <= 1.0 for f in values):
        raise CommandError(ERR_INVALID_PARAM,
                           "доли энергии должны быть в (0; 1]")
    return values


def _mtf_curve(registry: Registry, ctx, system, tag: str,
               field_y: float, wl=None) -> dict:
    """Сечения ЧКХ через сестринскую команду ``mtf.curve``.

    (Живой объект передаётся служебным именем в контексте; после
    вызова имя удаляется.)
    """
    key = _put_probe(ctx, system, tag)
    args = {"system": key, "field_y": field_y}
    if wl is not None:
        args["wl"] = wl
    result = registry.execute("mtf.curve", ctx, args)
    ctx.drop_system(key)
    if not result.ok:
        raise CommandError(result.error["code"],
                           result.error["message"])
    return result.data


def _mtf_at_freqs(freqs, curve: dict):
    """Значения MTF (мер/саг) на частотах; выше среза — 0."""
    import numpy as np
    axis = np.asarray(curve["freq_lpmm"], dtype=float)
    tan = np.asarray(curve["tan"], dtype=float)
    sag = np.asarray(curve["sag"], dtype=float)
    cutoff = float(curve["cutoff_lpmm"])
    rows = []
    for freq in freqs:
        if freq <= 0:
            raise CommandError(ERR_INVALID_PARAM, "частоты > 0")
        value = (float(np.interp(freq, axis, tan)) if freq <= cutoff
                 else 0.0)
        value_s = (float(np.interp(freq, axis, sag)) if freq <= cutoff
                   else 0.0)
        rows.append({"freq_lpmm": float(freq),
                     "mtf_t": max(0.0, value),
                     "mtf_s": max(0.0, value_s)})
    return rows, cutoff


def _limit_freq(values, axis, cutoff: float, threshold: float) -> float:
    """Максимальная частота, где MTF ещё ≥ threshold (сечение кривой)."""
    for i, value in enumerate(values):
        if value < threshold:
            if i == 0:
                return 0.0
            f0, f1 = axis[i - 1], axis[i]
            v0, v1 = values[i - 1], value
            if f1 <= f0 or v0 == v1:
                return float(f0)
            # линейная интерполяция точки v = threshold
            return float(f0 + (threshold - v0) * (f1 - f0) / (v1 - v0))
    return float(min(cutoff, float(axis[-1])))


def _ee_diameters_geometric(system, fractions, field_y, wl, num_rays):
    """Диаметры зон энергии (мкм) по геометрической ФКЭ (compute_enc)."""
    import numpy as np
    from analysis.advanced import compute_enc
    r_um, enc = compute_enc(system, wl=wl, num_rays=num_rays,
                            field_y=field_y)
    if len(r_um) < 2 or float(enc[-1]) < max(fractions):
        raise CommandError(ERR_INVALID_PARAM,
                           f"ФКЭ не построена на поле {field_y}")
    return [{"fraction": fraction,
             "diameter_um": 2.0 * float(np.interp(fraction, enc, r_um))}
            for fraction in fractions]


def _ee_diameters_psf(system, fractions, field_y, wl):
    """Диаметры зон энергии (мкм) по дифракционной ФРТ (§9.3)."""
    import numpy as np
    from analysis.psf_mtf import encircled_energy, psf_grid
    res = psf_grid(system, field_y=field_y, wl=wl)
    if res.get("psf") is None:
        raise CommandError(ERR_INVALID_PARAM,
                           f"ФРТ не построена: {res.get('reason')}")
    r_um, ee = encircled_energy(res["psf"], res["pitch_um"])
    return [{"fraction": fraction,
             "diameter_um": 2.0 * float(np.interp(fraction, ee, r_um))}
            for fraction in fractions], res


def _rms_poly(system, num_rays, field_y) -> float:
    """Полихроматический RMS пятна на поле (мм), движок analysis."""
    from analysis.aberrations import compute_polychromatic_rms
    return float(compute_polychromatic_rms(system, num_rays=num_rays,
                                           field_y=field_y))


def register(registry: Registry) -> None:
    """Зарегистрировать команды качества (R500-10)."""

    # ============================================================
    # Зоны задержанной энергии (encircled energy)
    # ============================================================

    @registry.command(
        "quality.ee.diameters", category="quality",
        description="Диаметры зон задержанной энергии (50/80/90 %) по "
                    "полям — геометрически, по точечной диаграмме",
        returns="{wl, rows: [{field_y, diameters: "
                "[{fraction, diameter_um}]}]}",
        params=system_source_params() + [
            Param("fractions", type="list",
                  help="доли энергии; по умолчанию [0.5, 0.8, 0.9]"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=EE_RAYS_DEFAULT,
                  help="лучей точечной диаграммы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_ee_diameters(ctx, file, system, lbo_index, lbo_name,
                             fractions, fields, num_rays, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parts = _fractions_arg(fractions)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            rows.append({"field_y": field, "diameters":
                         _ee_diameters_geometric(
                             sys_obj, parts, field, wl_eff, num_rays)})
        return {"wl": wl_eff, "rows": rows}

    @registry.command(
        "quality.ee.diameters.psf", category="quality",
        description="Диаметры зон задержанной энергии по дифракционной "
                    "ФРТ (§9.3): Fraction → D = 2r, с пятном Эйри",
        returns="{wl, field_y, diameters: [{fraction, diameter_um}], "
                "airy_um, pitch_um}",
        params=system_source_params() + [
            Param("fractions", type="list",
                  help="доли энергии; по умолчанию [0.5, 0.8, 0.9]"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_ee_diameters_psf(ctx, file, system, lbo_index, lbo_name,
                                 fractions, field_y, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parts = _fractions_arg(fractions)
        diameters, res = _ee_diameters_psf(sys_obj, parts, field_y,
                                           wl_eff)
        f_number = res.get("f_number")
        return {"wl": wl_eff, "field_y": field_y,
                "diameters": diameters,
                "airy_um": (AIRY_FIRST_ZERO * wl_eff * f_number
                            if f_number else None),
                "pitch_um": res["pitch_um"]}

    # ============================================================
    # Сводки пятна / полей
    # ============================================================

    @registry.command(
        "quality.spot.summary", category="quality",
        description="RMS кружка рассеяния по полям и рабочим λ + "
                    "полихроматический RMS и худшее поле",
        returns="{rows: [{field_y, by_wl: [{wl, rms}], rms_poly}], "
                "summary: {max_rms, max_field}}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
        ])
    def quality_spot_summary(ctx, file, system, lbo_index, lbo_name,
                             fields, num_rays):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            by_wl = []
            for wl in _wls_arg(sys_obj):
                spots = compute_spot_diagram(sys_obj, wl=wl,
                                             num_rays=num_rays,
                                             field_y=field)
                by_wl.append({"wl": wl, "rms": compute_rms_spot(spots)})
            rows.append({"field_y": field, "by_wl": by_wl,
                         "rms_poly": _rms_poly(sys_obj, num_rays, field)})
        worst = max(rows, key=lambda r: r["rms_poly"])
        return {"rows": rows,
                "summary": {"max_rms": worst["rms_poly"],
                            "max_field": worst["field_y"]}}

    @registry.command(
        "quality.fields.summary", category="quality",
        description="Сводная таблица качества по полям: полихроматич. "
                    "RMS, Штрель, MTF на частоте (мер/саг), диаметр зоны "
                    "90 % энергии",
        returns="{freq_lpmm, rows: [{field_y, rms_poly, strehl_exact, "
                "mtf_t, mtf_s, d90_um}]}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота ЧКХ, лин/мм"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
        ])
    def quality_fields_summary(ctx, file, system, lbo_index, lbo_name,
                               fields, freq_lpmm, num_rays):
        from analysis.strehl import compute_strehl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            curve = _mtf_curve(registry, ctx, sys_obj, "mtf",
                               field_y=field, wl=wl_eff)
            mtf_rows, _cutoff = _mtf_at_freqs([freq_lpmm], curve)
            strehl = compute_strehl(sys_obj, field_y=field)
            rows.append({
                "field_y": field,
                "rms_poly": _rms_poly(sys_obj, num_rays, field),
                "strehl_exact": strehl.get("strehl_exact"),
                "mtf_t": mtf_rows[0]["mtf_t"],
                "mtf_s": mtf_rows[0]["mtf_s"],
                "d90_um": _ee_diameters_geometric(
                    sys_obj, [EE_FRACTION_DEFAULT], field, wl_eff,
                    num_rays)[0]["diameter_um"],
            })
        return {"freq_lpmm": freq_lpmm, "wl": wl_eff, "rows": rows}

    # ============================================================
    # MTF: матрицы частот, полихрома, пределы, площадь
    # ============================================================

    @registry.command(
        "quality.mtf.matrix", category="quality",
        description="Матрица дифракционной ЧКХ: заданные частоты × поля "
                    "(сечения мер/саг; выше среза — 0)",
        returns="{wl, freqs, rows: [{field_y, mtf: [{freq_lpmm, "
                "mtf_t, mtf_s}]}], cutoff_lpmm}",
        params=system_source_params() + [
            Param("freqs", type="list",
                  help="частоты, лин/мм; по умолчанию [20, 50, 100]"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_mtf_matrix(ctx, file, system, lbo_index, lbo_name,
                           freqs, fields, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        freq_list = [float(f) for f in freqs] if freqs \
            else list(MTF_FREQS_DEFAULT)
        rows = []
        cutoff = None
        for field in _fields_arg(sys_obj, fields):
            curve = _mtf_curve(registry, ctx, sys_obj, "mtf",
                               field_y=field, wl=wl_eff)
            mtf_rows, cutoff = _mtf_at_freqs(freq_list, curve)
            rows.append({"field_y": field, "mtf": mtf_rows})
        return {"wl": wl_eff, "freqs": freq_list, "rows": rows,
                "cutoff_lpmm": cutoff}

    @registry.command(
        "quality.mtf.poly", category="quality",
        description="Полихроматическая дифракционная ЧКХ на заданных "
                    "частотах (взвешенное среднее по рабочим λ системы)",
        returns="{field_y, wls: [{wl, weight}], rows: [{freq_lpmm, "
                "mtf_t, mtf_s}]}",
        params=system_source_params() + [
            Param("freqs", type="list",
                  help="частоты, лин/мм; по умолчанию [20, 50, 100]"),
            Param("field_y", type="float", default=0.0, help="поле"),
        ])
    def quality_mtf_poly(ctx, file, system, lbo_index, lbo_name,
                         freqs, field_y):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if not sys_obj.wavelengths:
            raise CommandError(ERR_INVALID_PARAM,
                               "у системы нет рабочих λ (полихроматизм)")
        freq_list = [float(f) for f in freqs] if freqs \
            else list(MTF_FREQS_DEFAULT)
        acc = {float(freq): [0.0, 0.0] for freq in freq_list}
        total_w = 0.0
        for wl_obj in sys_obj.wavelengths:
            curve = _mtf_curve(registry, ctx, sys_obj, "mtf",
                               field_y=field_y, wl=wl_obj.value)
            mtf_rows, _cutoff = _mtf_at_freqs(freq_list, curve)
            weight = wl_obj.weight
            total_w += weight
            for row in mtf_rows:
                acc[row["freq_lpmm"]][0] += weight * row["mtf_t"]
                acc[row["freq_lpmm"]][1] += weight * row["mtf_s"]
        if total_w <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "сумма весов λ должна быть > 0")
        rows = [{"freq_lpmm": freq, "mtf_t": t / total_w,
                 "mtf_s": s / total_w}
                for freq, (t, s) in acc.items()]
        return {"field_y": field_y,
                "wls": [{"wl": w.value, "weight": w.weight}
                        for w in sys_obj.wavelengths],
                "rows": rows}

    @registry.command(
        "quality.mtf.limit_freq", category="quality",
        description="Предельная частота ЧКХ: где MTF впервые падает ниже "
                    "порога (сечения мер/саг по полям)",
        returns="{wl, threshold, rows: [{field_y, limit_t, limit_s}], "
                "min_limit_lpmm}",
        params=system_source_params() + [
            Param("threshold", type="float", required=True,
                  help="порог MTF, доли единицы (0; 1)"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_mtf_limit_freq(ctx, file, system, lbo_index, lbo_name,
                               threshold, fields, wl):
        import numpy as np
        if not 0.0 < threshold < 1.0:
            raise CommandError(ERR_INVALID_PARAM,
                               "порог MTF в (0; 1)")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            curve = _mtf_curve(registry, ctx, sys_obj, "mtf",
                               field_y=field, wl=wl_eff)
            axis = np.asarray(curve["freq_lpmm"], dtype=float)
            limit_t = _limit_freq(curve["tan"], axis,
                                  float(curve["cutoff_lpmm"]), threshold)
            limit_s = _limit_freq(curve["sag"], axis,
                                  float(curve["cutoff_lpmm"]), threshold)
            rows.append({"field_y": field, "limit_t": limit_t,
                         "limit_s": limit_s})
        worst = min(min(r["limit_t"], r["limit_s"]) for r in rows)
        return {"wl": wl_eff, "threshold": threshold, "rows": rows,
                "min_limit_lpmm": worst}

    @registry.command(
        "quality.mtf.area", category="quality",
        description="Интегральная ЧКХ: площадь под сечениями мер/саг "
                    "(нормирована на срез) и доля от дифракционного "
                    "предела",
        returns="{wl, field_y, area_t, area_s, ideal_area, ratio_t, "
                "ratio_s, cutoff_lpmm}",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_mtf_area(ctx, file, system, lbo_index, lbo_name,
                         field_y, wl):
        import numpy as np
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        curve = _mtf_curve(registry, ctx, sys_obj, "mtf",
                           field_y=field_y, wl=wl_eff)
        cutoff = float(curve["cutoff_lpmm"])
        axis = np.asarray(curve["freq_lpmm"], dtype=float)
        inside = axis <= cutoff

        def _area(values) -> float:
            data = np.asarray(values, dtype=float)[inside]
            return float(np.trapezoid(data, axis[inside]) / cutoff)

        # эталон: безаберрационная ЧКХ круглого зрачка (сестринская)
        key = _put_probe(ctx, sys_obj, "area")
        ideal_res = registry.execute(
            "diffr.mtf.limited", ctx, {"system": key, "wl": wl_eff})
        ctx.drop_system(key)
        if not ideal_res.ok:
            raise CommandError(ideal_res.error["code"],
                               ideal_res.error["message"])
        i_axis = np.asarray(ideal_res.data["freqs"], dtype=float)
        i_data = np.asarray(ideal_res.data["mtf"], dtype=float)
        ideal_area = float(
            np.trapezoid(i_data, i_axis)
            / ideal_res.data["cutoff_freq"])
        area_t = _area(curve["tan"])
        area_s = _area(curve["sag"])
        return {"wl": wl_eff, "field_y": field_y, "cutoff_lpmm": cutoff,
                "area_t": area_t, "area_s": area_s,
                "ideal_area": ideal_area,
                "ratio_t": area_t / ideal_area,
                "ratio_s": area_s / ideal_area}

    @registry.command(
        "quality.mtf.geo_vs_diff", category="quality",
        description="Геометрическая vs дифракционная ЧКХ на частоте: "
                    "насколько аберрации снижают контраст от предела",
        returns="{wl, field_y, freq_lpmm, diff_t, diff_s, geo_t, geo_s, "
                "ratio_t, ratio_s}",
        params=system_source_params() + [
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота, лин/мм"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=40,
                  help="лучей точечной диаграммы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_mtf_geo_vs_diff(ctx, file, system, lbo_index, lbo_name,
                                freq_lpmm, field_y, num_rays, wl):
        from analysis.aberrations import (
            compute_geometric_mtf,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        curve = _mtf_curve(registry, ctx, sys_obj, "mtf",
                           field_y=field_y, wl=wl_eff)
        mtf_rows, _cutoff = _mtf_at_freqs([freq_lpmm], curve)
        spots = compute_spot_diagram(sys_obj, wl=wl_eff,
                                     num_rays=num_rays,
                                     field_y=field_y)
        geo = compute_geometric_mtf(spots, max_freq=freq_lpmm,
                                    num_freqs=1)
        _f0, _t0, _s0 = geo[0]
        _f1, geo_t, geo_s = geo[1] if len(geo) > 1 else (0.0, 0.0, 0.0)
        diff_t, diff_s = mtf_rows[0]["mtf_t"], mtf_rows[0]["mtf_s"]
        return {"wl": wl_eff, "field_y": field_y,
                "freq_lpmm": freq_lpmm,
                "diff_t": diff_t, "diff_s": diff_s,
                "geo_t": float(geo_t), "geo_s": float(geo_s),
                "ratio_t": (float(geo_t) / diff_t) if diff_t > 0 else None,
                "ratio_s": (float(geo_s) / diff_s) if diff_s > 0 else None}

    # ============================================================
    # Штрель и волновой фронт: своды по полям
    # ============================================================

    @registry.command(
        "quality.strehl.summary", category="quality",
        description="Полихроматический Штрель по полям (Марешаль + "
                    "точный) с худшим полем и средним",
        returns="{rows: [{field_y, strehl_exact, strehl_marechal, "
                "sigma_w, validity}], worst: {field_y, strehl_exact}, "
                "mean_exact}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
        ])
    def quality_strehl_summary(ctx, file, system, lbo_index, lbo_name,
                               fields):
        from analysis.strehl import compute_strehl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            strehl = compute_strehl(sys_obj, field_y=field)
            rows.append({"field_y": field,
                         "strehl_exact": strehl.get("strehl_exact"),
                         "strehl_marechal": strehl.get("strehl_marechal"),
                         "sigma_w": strehl.get("sigma_w"),
                         "validity": strehl.get("validity")})
        exact = [(r["field_y"], r["strehl_exact"]) for r in rows
                 if r["strehl_exact"] is not None]
        if not exact:
            raise CommandError(ERR_INVALID_PARAM,
                               "Штрель не посчитан ни на одном поле")
        worst_field, worst_value = min(exact, key=lambda p: p[1])
        mean_exact = sum(v for _, v in exact) / len(exact)
        return {"rows": rows,
                "worst": {"field_y": worst_field,
                          "strehl_exact": worst_value},
                "mean_exact": mean_exact}

    @registry.command(
        "quality.wavefront.summary", category="quality",
        description="СКВ волнового фронта по полю + Штрель Марешаля в "
                    "худшей точке поля",
        returns="{wl, rows: [{field_y, rms_wl}], max_rms_wl, max_field, "
                "strehl_marechal_max}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_wavefront_summary(ctx, file, system, lbo_index, lbo_name,
                                  wl):
        from analysis.aberrations import compute_wavefront_rms_vs_field
        from analysis.strehl import strehl_marechal
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        fields, rms_values = compute_wavefront_rms_vs_field(
            sys_obj, wl=wl_eff)
        rows = []
        valid = []
        for field, rms in zip(fields, rms_values):
            ok = math.isfinite(rms)
            rows.append({"field_y": float(field),
                         "rms_wl": float(rms) if ok else None})
            if ok:
                valid.append((float(field), float(rms)))
        if not valid:
            raise CommandError(ERR_INVALID_PARAM,
                               "СКВ волнового фронта не посчитана")
        max_field, max_rms = max(valid, key=lambda p: p[1])
        return {"wl": wl_eff, "rows": rows, "max_rms_wl": max_rms,
                "max_field": max_field,
                "strehl_marechal_max": strehl_marechal(max_rms)}

    # ============================================================
    # Паспорт и сравнение систем
    # ============================================================

    def _passport(registry_, ctx_, sys_obj, freq_lpmm, num_rays,
                  tag="pass") -> dict:
        """Свод ключевых величин системы (для паспорта и сравнения)."""
        from domain.calculations import paraxial_trace
        from analysis.strehl import compute_strehl
        wl_eff = get_primary_wl(sys_obj)
        parax = paraxial_trace(sys_obj, wl=wl_eff)
        fields = [fp.y for fp in sys_obj.field_points] or [0.0]
        rms_axis = _rms_poly(sys_obj, num_rays, 0.0)
        rms_rows = [(f, _rms_poly(sys_obj, num_rays, f)) for f in fields]
        worst_field, worst_rms = max(rms_rows, key=lambda p: p[1])
        curve = _mtf_curve(registry_, ctx_, sys_obj, tag,
                           field_y=0.0, wl=wl_eff)
        mtf_rows, cutoff = _mtf_at_freqs([freq_lpmm], curve)
        strehl = compute_strehl(sys_obj, field_y=0.0)
        airy = registry.execute("calc.airy", ctx_, {
            "f_number": float(abs(parax["f_number"])), "wl": wl_eff})
        if not airy.ok:
            raise CommandError(airy.error["code"], airy.error["message"])
        return {
            "num_surfaces": sys_obj.num_surfaces,
            "efl_mm": float(abs(parax["focal_length"])),
            "f_number": float(abs(parax["f_number"])),
            "epd_mm": float(abs(parax["entrance_pupil_diameter"])),
            "bfd_mm": float(abs(parax["back_focal_distance"])),
            "max_field": max(fields),
            "num_wavelengths": len(_wls_arg(sys_obj)),
            "rms_axis_mm": rms_axis,
            "rms_worst_mm": worst_rms,
            "rms_worst_field": worst_field,
            "strehl_exact": strehl.get("strehl_exact"),
            "mtf_t": mtf_rows[0]["mtf_t"],
            "mtf_s": mtf_rows[0]["mtf_s"],
            "cutoff_lpmm": cutoff,
            "airy_diameter_um": airy.data["diameter_um"],
        }

    @registry.command(
        "quality.passport", category="quality",
        description="Паспорт системы: параксиальные величины (efl, F/#, "
                    "апертура), RMS по полям, полихроматический Штрель, "
                    "MTF на частоте, дифракционный предел",
        returns="{name, wavelengths, fields, paraxial: {...}, quality: "
                "{...}}",
        params=system_source_params() + [
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота ЧКХ паспорта, лин/мм"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
        ])
    def quality_passport(ctx, file, system, lbo_index, lbo_name,
                         freq_lpmm, num_rays):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        scalars = _passport(registry, ctx, sys_obj, freq_lpmm,
                            num_rays)
        return {
            "name": getattr(sys_obj, "name", None),
            "wavelengths": [{"wl": w.value, "weight": w.weight,
                             "name": w.name}
                            for w in sys_obj.wavelengths],
            "fields": [fp.y for fp in sys_obj.field_points],
            "freq_lpmm": freq_lpmm,
            **scalars,
        }

    @registry.command(
        "quality.compare", category="quality",
        description="Сравнение двух систем по сводным метрикам "
                    "(efl, F/#, апертура, RMS, Штрель, MTF, срез ЧКХ)",
        returns="{freq_lpmm, rows: [{metric, a, b, delta}]}",
        params=[
            Param("file_a", required=True, help="файл первой системы"),
            Param("file_b", required=True, help="файл второй системы"),
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота ЧКХ, лин/мм"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
        ])
    def quality_compare(ctx, file_a, file_b, freq_lpmm, num_rays):
        from commands.systemio import load_system
        sys_a = load_system(file_a)
        sys_b = load_system(file_b)
        metrics_a = _passport(registry, ctx, sys_a, freq_lpmm,
                              num_rays, tag="cmp")
        metrics_b = _passport(registry, ctx, sys_b, freq_lpmm,
                              num_rays, tag="cmp")
        rows = []
        for key in metrics_a:
            va, vb = metrics_a[key], metrics_b[key]
            if isinstance(va, bool) or va is None or vb is None:
                delta = None
            else:
                delta = vb - va if isinstance(va, (int, float)) else None
            rows.append({"metric": key, "a": va, "b": vb,
                         "delta": delta})
        return {"freq_lpmm": freq_lpmm, "rows": rows,
                "count": len(rows)}

    # ============================================================
    # Пороговые проверки (pass/fail)
    # ============================================================

    @registry.command(
        "quality.check.mtf", category="quality",
        description="Пороговая проверка MTF: контраст на частоте не "
                    "ниже порога во всех полях (сечения мер/саг)",
        returns="{wl, freq_lpmm, threshold, rows: [{field_y, mtf_t, "
                "mtf_s, pass_t, pass_s}], pass}",
        params=system_source_params() + [
            Param("threshold", type="float", required=True,
                  help="порог MTF, доли единицы (0; 1)"),
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота ЧКХ, лин/мм"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_check_mtf(ctx, file, system, lbo_index, lbo_name,
                          threshold, freq_lpmm, fields, wl):
        if not 0.0 < threshold < 1.0:
            raise CommandError(ERR_INVALID_PARAM, "порог MTF в (0; 1)")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            curve = _mtf_curve(registry, ctx, sys_obj, "chkmtf",
                               field_y=field, wl=wl_eff)
            mtf_rows, _cutoff = _mtf_at_freqs([freq_lpmm], curve)
            row = mtf_rows[0]
            rows.append({"field_y": field,
                         "mtf_t": row["mtf_t"], "mtf_s": row["mtf_s"],
                         "pass_t": row["mtf_t"] >= threshold,
                         "pass_s": row["mtf_s"] >= threshold})
        return {"wl": wl_eff, "freq_lpmm": freq_lpmm,
                "threshold": threshold, "rows": rows,
                "pass": all(r["pass_t"] and r["pass_s"] for r in rows)}

    @registry.command(
        "quality.check.strehl", category="quality",
        description="Пороговая проверка Штреля: полихроматический Штрель "
                    "не ниже порога во всех полях",
        returns="{threshold, rows: [{field_y, strehl_exact, pass}], "
                "pass, worst}",
        params=system_source_params() + [
            Param("threshold", type="float", required=True,
                  help="порог Штреля, доли единицы (0; 1)"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
        ])
    def quality_check_strehl(ctx, file, system, lbo_index, lbo_name,
                             threshold, fields):
        from analysis.strehl import compute_strehl
        if not 0.0 < threshold < 1.0:
            raise CommandError(ERR_INVALID_PARAM, "порог Штреля в (0; 1)")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            strehl = compute_strehl(sys_obj, field_y=field)
            value = strehl.get("strehl_exact")
            rows.append({"field_y": field, "strehl_exact": value,
                         "pass": value is not None
                         and value >= threshold})
        exact = [r for r in rows if r["strehl_exact"] is not None]
        if not exact:
            raise CommandError(ERR_INVALID_PARAM,
                               "Штрель не посчитан ни на одном поле")
        worst = min(exact, key=lambda r: r["strehl_exact"])
        return {"threshold": threshold, "rows": rows,
                "pass": all(r["pass"] for r in rows), "worst": worst}

    @registry.command(
        "quality.check.spot", category="quality",
        description="Пороговая проверка пятна: полихроматический RMS не "
                    "больше порога (мкм) во всех полях",
        returns="{threshold_um, rows: [{field_y, rms_um, pass}], pass, "
                "worst}",
        params=system_source_params() + [
            Param("threshold_um", type="float", required=True,
                  help="порог RMS пятна, мкм"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
        ])
    def quality_check_spot(ctx, file, system, lbo_index, lbo_name,
                           threshold_um, fields, num_rays):
        if threshold_um <= 0:
            raise CommandError(ERR_INVALID_PARAM, "порог > 0 (мкм)")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            rms_um = _rms_poly(sys_obj, num_rays, field) * 1000.0
            rows.append({"field_y": field, "rms_um": rms_um,
                         "pass": rms_um <= threshold_um})
        worst = max(rows, key=lambda r: r["rms_um"])
        return {"threshold_um": threshold_um, "rows": rows,
                "pass": all(r["pass"] for r in rows), "worst": worst}

    @registry.command(
        "quality.check.ee", category="quality",
        description="Пороговая проверка ФКЭ: диаметр зоны заданной доли "
                    "энергии не больше порога (мкм) во всех полях",
        returns="{wl, fraction, threshold_um, rows: [{field_y, "
                "diameter_um, pass}], pass, worst}",
        params=system_source_params() + [
            Param("threshold_um", type="float", required=True,
                  help="порог диаметра зоны, мкм"),
            Param("fraction", type="float", default=EE_FRACTION_DEFAULT,
                  help="доля энергии в зоне (по умолчанию 0.9)"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=EE_RAYS_DEFAULT,
                  help="лучей точечной диаграммы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def quality_check_ee(ctx, file, system, lbo_index, lbo_name,
                         threshold_um, fraction, fields, num_rays, wl):
        if threshold_um <= 0:
            raise CommandError(ERR_INVALID_PARAM, "порог > 0 (мкм)")
        if not 0.0 < fraction <= 1.0:
            raise CommandError(ERR_INVALID_PARAM, "доля энергии в (0; 1]")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            diameter = _ee_diameters_geometric(
                sys_obj, [fraction], field, wl_eff, num_rays)[0]
            rows.append({"field_y": field,
                         "diameter_um": diameter["diameter_um"],
                         "pass": diameter["diameter_um"] <= threshold_um})
        worst = max(rows, key=lambda r: r["diameter_um"])
        return {"wl": wl_eff, "fraction": fraction,
                "threshold_um": threshold_um, "rows": rows,
                "pass": all(r["pass"] for r in rows), "worst": worst}

    @registry.command(
        "quality.check.all", category="quality",
        description="Агрегат пороговых проверок (MTF/Штрель/RMS/ФКЭ) с "
                    "общим вердиктом; пороги опциональны — заданный "
                    "порог включает проверку",
        returns="{checks: [{check, pass, detail}], pass, num_checks}",
        params=system_source_params() + [
            Param("mtf_min", type="float",
                  help="порог MTF на частоте (0; 1)"),
            Param("strehl_min", type="float",
                  help="порог Штреля (0; 1)"),
            Param("rms_max_um", type="float", help="порог RMS пятна, мкм"),
            Param("ee_max_um", type="float",
                  help="порог диаметра зоны 90 % энергии, мкм"),
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота ЧКХ, лин/мм"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
        ])
    def quality_check_all(ctx, file, system, lbo_index, lbo_name,
                          mtf_min, strehl_min, rms_max_um, ee_max_um,
                          freq_lpmm, fields, num_rays):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        plan = [
            ("quality.check.mtf", mtf_min is not None,
             {"threshold": mtf_min, "freq_lpmm": freq_lpmm,
              "fields": fields}),
            ("quality.check.strehl", strehl_min is not None,
             {"threshold": strehl_min, "fields": fields}),
            ("quality.check.spot", rms_max_um is not None,
             {"threshold_um": rms_max_um, "fields": fields,
              "num_rays": num_rays}),
            ("quality.check.ee", ee_max_um is not None,
             {"threshold_um": ee_max_um, "fields": fields,
              "num_rays": num_rays}),
        ]
        enabled = [item for item in plan if item[1]]
        if not enabled:
            raise CommandError(ERR_INVALID_PARAM,
                               "задайте хотя бы один порог (mtf_min / "
                               "strehl_min / rms_max_um / ee_max_um)")
        key = _put_probe(ctx, sys_obj, "all")
        checks = []
        try:
            for name, _flag, extra in enabled:
                result = registry.execute(name, ctx,
                                          {"system": key, **extra})
                if not result.ok:
                    raise CommandError(result.error["code"],
                                       result.error["message"])
                data = result.data
                checks.append({
                    "check": name.split(".")[-1],
                    "pass": bool(data["pass"]),
                    "worst": data.get("worst"),
                })
        finally:
            ctx.drop_system(key)
        return {"checks": checks, "num_checks": len(checks),
                "pass": all(c["pass"] for c in checks)}

    # ============================================================
    # Режим ограничения качества
    # ============================================================

    @registry.command(
        "quality.regime", category="quality",
        description="Чем ограничено пятно: сравнение полихроматического "
                    "RMS с радиусом диска Эйри (дифракция/аберрации)",
        returns="{f_number, wl, airy_radius_um, rms_um, ratio, regime}",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
        ])
    def quality_regime(ctx, file, system, lbo_index, lbo_name,
                       field_y, num_rays):
        from domain.calculations import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = get_primary_wl(sys_obj)
        f_number = abs(paraxial_trace(sys_obj, wl=wl_eff)["f_number"])
        if f_number <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "F/# ≤ 0: апертура не задана")
        airy = registry.execute(
            "calc.airy", ctx,
            {"f_number": float(f_number), "wl": wl_eff})
        if not airy.ok:
            raise CommandError(airy.error["code"], airy.error["message"])
        rms_um = _rms_poly(sys_obj, num_rays, field_y) * 1000.0
        radius_um = airy.data["radius_um"]
        ratio = rms_um / radius_um
        if ratio < REGIME_DIFFRACTION_MAX_RATIO:
            regime = "diffraction_limited"
        elif ratio > REGIME_ABERATION_MIN_RATIO:
            regime = "aberration_limited"
        else:
            regime = "comparable"
        return {"wl": wl_eff, "f_number": f_number,
                "airy_radius_um": radius_um, "rms_um": rms_um,
                "ratio": ratio, "regime": regime}
