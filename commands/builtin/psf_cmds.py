"""
OPAL-OKB — Команды Волны 3 (домен «Дифракция и волновой фронт»).

Обёртки публичных точек входа модулей анализа (правило волн: обёртки,
нижние слои не меняются):

* ``psf.*``   — analysis/psf_mtf.py: ФРЛ, ФКЭ, миры, секция протокола
  (сама ФРТ ``psf_grid`` уже обёрнута командой Волны 1 ``analyze.psf``);
* ``mtf.*``   — analysis/psf_mtf.py: ОПФ из ФРТ (сечения мер/саг);
* ``diffr.*`` — analysis/diffraction.py: карта волнового фронта,
  дифракционная/полихроматическая/безаберрационная ЧКХ;
* ``strehl.*``— analysis/strehl.py: Марешаль + точный FFT-Штрель;
* ``zern.*``  — analysis/zernike.py + разложение OPAL-28 из psf_mtf.py;
* ``focus.*`` — analysis/focus_criteria.py: плоскости оптимального фокуса.

Функции с массивным входом/выходом (``strehl_exact_from_wavefront``,
``fit_zernike`` с готовой картой W, ``zernike_basis``) отдельно не
обёрнуты: их системные пути закрыты командами ``strehl.calc``,
``zern.decompose`` и ``zern.reconstruct``.
"""
import math

from optics_utils import get_primary_wl

from commands.base import (
    ERR_INVALID_PARAM,
    CommandError,
    Param,
)
from commands.registry import Registry
from commands.systemio import resolve_system, system_source_params

#: Ориентации миры (psf_mtf.render_test_target).
TARGET_ORIENTATIONS = ("tangential", "sagittal")

#: Типы мир: синусная и шпальная (меандр).
TARGET_KINDS = ("sine", "bar")

#: Чало Эйри: радиус первого тёмного кольца = 1.22·λ·F#.
AIRY_FACTOR = 1.22


# ============================================================
# Общие локальные хелперы (адаптер, не домен)
# ============================================================

def _resolve_wl(system, wl):
    """Рабочая λ, мкм: явная или основная λ системы."""
    return wl if wl is not None else get_primary_wl(system)


def _psf_of(system, field_y=0.0, wl=None, defocus=0.0):
    """Результат psf_grid; ``None``-ФРТ → CommandError с reason домена."""
    from analysis.psf_mtf import psf_grid
    res = psf_grid(system, field_y=field_y, wl=wl, defocus=defocus)
    if res.get("psf") is None:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"ФРТ не построена: {res.get('reason', 'неизвестно')}")
    return res


def _wavefront_stats(wavefront, mask):
    """СКВ/размах W по зрачку (те же формулы, что diffraction.py)."""
    import numpy as np
    inside = np.asarray(wavefront)[np.asarray(mask) > 0]
    if inside.size == 0:
        return {"rms": None, "pv": None, "num_points": 0}
    return {"rms": float(np.sqrt(np.mean(inside ** 2))),
            "pv": float(np.ptp(inside)),
            "num_points": int(inside.size)}


def _parse_points(points, param_name="points"):
    """Точки зрачка [[px, py, W], ...] → список кортежей (валидация)."""
    if not isinstance(points, (list, tuple)) or not points:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: нужен непустой список "
            f"[[px, py, W], ...]")
    parsed = []
    for i, item in enumerate(points):
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"параметр {param_name!r}[{i}]: нужна тройка "
                f"[px, py, W], получено {item!r}")
        try:
            parsed.append((float(item[0]), float(item[1]), float(item[2])))
        except (TypeError, ValueError) as exc:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"параметр {param_name!r}[{i}]: не числа {item!r}") from exc
    return parsed


def _parse_coeffs(coeffs, param_name="coeffs"):
    """Коэффициенты Цернике (список чисел) → list[float]."""
    if not isinstance(coeffs, (list, tuple)) or not coeffs:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: нужен непустой список чисел")
    try:
        return [float(c) for c in coeffs]
    except (TypeError, ValueError) as exc:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: все элементы — числа") from exc


def _classic_terms(max_order):
    """Классический базис ZERNIKE_TERMS до порядка включительно."""
    from analysis.zernike import ZERNIKE_TERMS
    return [(n, m, name) for n, m, name in ZERNIKE_TERMS
            if n <= max_order]


def _coeff_rows(result_coeffs, max_order):
    """[(coeff, name)] классического разложения → строки с (n, m)."""
    terms = _classic_terms(max_order)
    return [{"n": n, "m": m, "name": name, "coeff": float(c)}
            for (c, _name), (n, m, name) in zip(result_coeffs, terms)]


def register(registry: Registry) -> None:
    """Зарегистрировать все команды домена «Дифракция и волновой фронт»."""

    # ========================================================
    # psf.* — ФРЛ, ФКЭ, миры, протокол (analysis/psf_mtf.py)
    # ========================================================

    @registry.command(
        "psf.lsf", category="psf",
        description="ФРЛ — изображение бесконечной линии (§9.4): "
                    "профили ФРТ меридиональный/сагиттальный",
        returns="профили meridional/sagittal + ось координат (мкм)",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def psf_lsf(ctx, file, system, lbo_index, lbo_name,
                field_y, wl, defocus):
        from analysis.psf_mtf import lsf_from_psf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        lsf = lsf_from_psf(res["psf"], res["pitch_um"])
        return {"wl": res["wl"], "field_y": field_y,
                "defocus": defocus, "pitch_um": res["pitch_um"],
                "coord_um": lsf["coord_um"].tolist(),
                "meridional": lsf["meridional"].tolist(),
                "sagittal": lsf["sagittal"].tolist()}

    @registry.command(
        "psf.encircled", category="psf",
        description="ФКЭ — доля энергии ФРТ в круге радиуса r от "
                    "энергетического центра (§9.3)",
        returns="кривая r_um/ee + радиусы 50 %/80 % и пятно Эйри",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def psf_encircled(ctx, file, system, lbo_index, lbo_name,
                      field_y, wl, defocus):
        import numpy as np
        from analysis.psf_mtf import encircled_energy
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        r_um, ee = encircled_energy(res["psf"], res["pitch_um"])
        r50 = float(np.interp(0.5, ee, r_um))
        r80 = float(np.interp(0.8, ee, r_um))
        f_number = res.get("f_number")
        airy_um = (AIRY_FACTOR * res["wl"] * f_number
                   if f_number else None)
        return {"wl": res["wl"], "field_y": field_y,
                "defocus": defocus, "pitch_um": res["pitch_um"],
                "r_um": r_um.tolist(), "ee": ee.tolist(),
                "r50_um": r50, "r80_um": r80, "airy_um": airy_um}

    @registry.command(
        "psf.target", category="psf",
        description="Изображение миры (§9.5): свёртка с ФРЛ; контраст "
                    "синус-миры на частоте ν равен MTF(ν)",
        returns="профили объект/изображение + контраст Михельсона",
        params=system_source_params([
            Param("freq_lpmm", type="float", required=True,
                  help="частота миры, лин/мм"),
            Param("orientation", choices=list(TARGET_ORIENTATIONS),
                  default="tangential",
                  help="штрихи вдоль X (tangential) или вдоль Y"),
            Param("kind", choices=list(TARGET_KINDS), default="sine",
                  help="синус-мира или шпальная (меандр)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def psf_target(ctx, file, system, lbo_index, lbo_name, freq_lpmm,
                   orientation, kind, field_y, wl, defocus):
        from analysis.psf_mtf import render_test_target
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        target = render_test_target(res["psf"], res["pitch_um"],
                                    freq_lpmm, orientation=orientation,
                                    kind=kind)
        return {"wl": res["wl"], "field_y": field_y,
                "defocus": defocus,
                "freq_lpmm": float(target["freq_lpmm"]),
                "period_um": float(target["period_um"]),
                "orientation": target["orientation"],
                "kind": target["kind"],
                "contrast": float(target["contrast"]),
                "coord_um": target["coord_um"].tolist(),
                "object": target["object"].tolist(),
                "image": target["image"].tolist()}

    @registry.command(
        "psf.section", category="psf",
        description="Секция протокола «ФРТ/ОПФ»: Штрель, срез, ЧКХ "
                    "0.2..1.0·νc (опция — разложение Цернике)",
        returns="текст секции протокола расчёта",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("zernike", type="bool", default=False,
                  help="добавить разложение Цернике (28 членов OPAVA)"),
        ]))
    def psf_section(ctx, file, system, lbo_index, lbo_name,
                    field_y, zernike):
        from analysis.psf_mtf import format_psf_mtf_section
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = format_psf_mtf_section(sys_obj, field_y=field_y,
                                      zernike=zernike)
        return {"field_y": field_y, "zernike": zernike, "text": text}

    # ========================================================
    # mtf.* — ОПФ из ФРТ (analysis/psf_mtf.py)
    # ========================================================

    @registry.command(
        "mtf.curve", category="mtf",
        description="ОПФ/ЧКХ из ФРТ (§9.6): сечения меридиональное/"
                    "сагиттальное до Найквиста решётки ФРТ",
        returns="freq_lpmm + tan/sag (линии/мм, доли единицы)",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def mtf_curve(ctx, file, system, lbo_index, lbo_name,
                  field_y, wl, defocus):
        from analysis.psf_mtf import mtf_from_psf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        mtf = mtf_from_psf(res["psf"], res["pitch_um"])
        return {"wl": res["wl"], "field_y": field_y,
                "defocus": defocus,
                "freq_lpmm": mtf["freq_lpmm"].tolist(),
                "tan": mtf["tan"].tolist(),
                "sag": mtf["sag"].tolist(),
                "cutoff_lpmm": float(res["cutoff_lpmm"]),
                "nyquist_lpmm": float(mtf["nyquist_lpmm"]),
                "df_lpmm": float(mtf["df_lpmm"])}

    # ========================================================
    # diffr.* — дифракционная ЧКХ (analysis/diffraction.py)
    # ========================================================

    @registry.command(
        "diffr.wavefront", category="diffr",
        description="Карта волнового фронта W на зрачке (опорная сфера "
                    "параксиального изображения)",
        returns="СКВ/PV фронта по зрачку (+решётки W и маска по запросу)",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("grid_size", type="int", default=64,
                  help="решётка зрачка (N×N лучей)"),
            Param("include_grid", type="bool", default=False,
                  help="включить карту W и маску зрачка (N² значений)"),
        ]))
    def diffr_wavefront(ctx, file, system, lbo_index, lbo_name, wl,
                        field_y, grid_size, include_grid):
        from analysis.diffraction import compute_wavefront_map
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        wavefront, mask = compute_wavefront_map(
            sys_obj, wl=wl_eff, grid_size=grid_size, field_y=field_y)
        out = {"wl": wl_eff, "field_y": field_y,
               "grid_size": grid_size,
               **_wavefront_stats(wavefront, mask)}
        if include_grid:
            out["wavefront"] = wavefront.tolist()
            out["pupil_mask"] = mask.tolist()
        return out

    @registry.command(
        "diffr.mtf", category="diffr",
        description="Дифракционная ЧКХ через FFT автокорреляции зрачка "
                    "(Л1.7.1): сечения мер/саг + СКВ/PV фронта",
        returns="freqs + mtf_tangential/mtf_sagittal + cutoff_lpmm",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("grid_size", type="int", default=64,
                  help="решётка зрачка (N×N лучей)"),
            Param("max_freq_lpmm", type="float",
                  help="верхняя частота, лин/мм (по умолчанию — срез)"),
        ]))
    def diffr_mtf(ctx, file, system, lbo_index, lbo_name, wl,
                  grid_size, max_freq_lpmm):
        from analysis.diffraction import compute_diffraction_mtf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        return {"wl": wl_eff,
                **compute_diffraction_mtf(sys_obj, wl=wl_eff,
                                          grid_size=grid_size,
                                          max_freq_lpmm=max_freq_lpmm)}

    @registry.command(
        "diffr.mtf.quick", category="diffr",
        description="Быстрая дифракционная ЧКХ (решётка зрачка 32×32)",
        returns="как diffr.mtf (freqs + мер/саг + cutoff)",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def diffr_mtf_quick(ctx, file, system, lbo_index, lbo_name, wl):
        from analysis.diffraction import compute_diffraction_mtf_quick
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        return {"wl": wl_eff,
                **compute_diffraction_mtf_quick(sys_obj, wl=wl_eff)}

    @registry.command(
        "diffr.mtf.poly", category="diffr",
        description="Полихроматическая дифракционная ЧКХ: взвешенная "
                    "сумма по всем λ системы (веса λ)",
        returns="freqs + mtf_tangential/mtf_sagittal + cutoff_lpmm",
        params=system_source_params([
            Param("grid_size", type="int", default=64,
                  help="решётка зрачка (N×N лучей)"),
            Param("max_freq_lpmm", type="float",
                  help="верхняя частота, лин/мм (по умолчанию — срез)"),
        ]))
    def diffr_mtf_poly(ctx, file, system, lbo_index, lbo_name,
                       grid_size, max_freq_lpmm):
        from analysis.diffraction import compute_polychromatic_mtf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return compute_polychromatic_mtf(sys_obj, grid_size=grid_size,
                                         max_freq_lpmm=max_freq_lpmm)

    @registry.command(
        "diffr.mtf.limited", category="diffr",
        description="Безаберрационная (дифракционно-ограниченная) ЧКХ "
                    "круглого зрачка: аналитическая формула",
        returns="freqs + mtf + cutoff_lpmm (эталон для сравнения)",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def diffr_mtf_limited(ctx, file, system, lbo_index, lbo_name, wl):
        from analysis.diffraction import compute_diffraction_limited_mtf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        return {"wl": wl_eff,
                **compute_diffraction_limited_mtf(sys_obj, wl=wl_eff)}

    # ========================================================
    # strehl.* — число Штреля (analysis/strehl.py)
    # ========================================================

    @registry.command(
        "strehl.marechal", category="strehl",
        description="Аппроксимация Марешаля S = exp(−(2π·σ)²) из СКВ "
                    "волновой аберрации",
        returns="число Штреля (0, 1]",
        params=[Param("sigma_w", type="float", required=True,
                      help="СКВ волновой аберрации, длины волн")])
    def strehl_marechal_cmd(ctx, sigma_w):
        from analysis.strehl import strehl_marechal
        return {"sigma_w": sigma_w, "strehl": strehl_marechal(sigma_w)}

    @registry.command(
        "strehl.calc", category="strehl",
        description="Число Штреля двумя способами: Марешаль + точный "
                    "FFT-PSF (полихроматически при wl не задана)",
        returns="strehl_marechal/strehl_exact/sigma_w/validity + per_wl",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — все λ системы)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("include_text", type="bool", default=False,
                  help="добавить строку и tooltip GUI (strehl_tooltip)"),
        ]))
    def strehl_calc(ctx, file, system, lbo_index, lbo_name, wl,
                    field_y, include_text):
        from analysis.strehl import (
            compute_strehl,
            format_strehl,
            strehl_tooltip,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        result = compute_strehl(sys_obj, wl=wl, field_y=field_y)
        if include_text:
            result["text"] = format_strehl(result)
            result["tooltip"] = strehl_tooltip(result)
        return result

    # ========================================================
    # zern.* — Цернике (analysis/zernike.py + psf_mtf)
    # ========================================================

    @registry.command(
        "zern.terms", category="zern",
        description="Базисы Цернике реестра: классический (n≤4, ±m) и "
                    "OPAL/OPAVA (28 членов, n≤12, m≥0, марки «C xIJ»)",
        returns="два списка членов с (n, m), марками и именами",
        params=[])
    def zern_terms(ctx):
        from analysis.zernike import (
            ZERNIKE_MARKS_28,
            ZERNIKE_TERMS,
            ZERNIKE_TERMS_28,
            zernike_term_name,
        )
        return {
            "classic": [{"n": n, "m": m, "name": name}
                        for n, m, name in ZERNIKE_TERMS],
            "opal": [{"n": n, "m": m, "mark": mark,
                      "name": zernike_term_name(n, m)}
                     for (n, m), mark in zip(ZERNIKE_TERMS_28,
                                             ZERNIKE_MARKS_28)],
        }

    @registry.command(
        "zern.coeffs", category="zern",
        description="Коэффициенты Цернике волнового фронта (классический "
                    "базис n≤4): трассировка сетки лучей + МНК",
        returns="список {n, m, name, coeff} (длины волн)",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("num_rays", type="int", default=64,
                  help="лучей по стороне квадратной сетки зрачка"),
            Param("max_order", type="int", default=4,
                  help="максимальный порядок полиномов"),
            Param("defocus_offset", type="float", default=0.0,
                  help="смещение OPL, мм (моделируемый дефокус)"),
        ]))
    def zern_coeffs(ctx, file, system, lbo_index, lbo_name, wl, field_y,
                    num_rays, max_order, defocus_offset):
        from analysis.zernike import compute_zernike_coefficients
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        coeffs = compute_zernike_coefficients(
            sys_obj, wl=wl_eff, field_y=field_y, num_rays=num_rays,
            max_order=max_order, defocus_offset=defocus_offset)
        return {"wl": wl_eff, "field_y": field_y, "num_rays": num_rays,
                "max_order": max_order,
                "coeffs": _coeff_rows(coeffs, max_order)}

    @registry.command(
        "zern.coeffs.fit", category="zern",
        description="МНК-подгонка классических коэффициентов Цернике "
                    "по готовым точкам зрачка (без трассировки)",
        returns="список {n, m, name, coeff}",
        params=[
            Param("points", type="list", required=True,
                  help="точки зрачка [[px, py, W], ...] (−1..1, волны)"),
            Param("max_order", type="int", default=4,
                  help="максимальный порядок полиномов"),
        ])
    def zern_coeffs_fit(ctx, points, max_order):
        from analysis.zernike import fit_zernike_coefficients
        parsed = _parse_points(points)
        coeffs = fit_zernike_coefficients(parsed, max_order=max_order)
        return {"max_order": max_order,
                "num_points": len(parsed),
                "coeffs": _coeff_rows(coeffs, max_order)}

    @registry.command(
        "zern.wavefront", category="zern",
        description="2D-карта волновой аберрации на зрачке (OPL до "
                    "опорной сферы, с опцией смещения-дефокуса)",
        returns="СКВ/PV фронта по зрачку (+решётка W и маска по запросу)",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("grid_size", type="int", default=64,
                  help="решётка зрачка (N×N лучей)"),
            Param("defocus_offset", type="float", default=0.0,
                  help="смещение OPL, мм (моделируемый дефокус)"),
            Param("include_grid", type="bool", default=False,
                  help="включить карту W, маску и ось координат"),
        ]))
    def zern_wavefront(ctx, file, system, lbo_index, lbo_name, wl,
                       field_y, grid_size, defocus_offset, include_grid):
        from analysis.zernike import compute_wavefront_map_2d
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        wavefront, coords, mask = compute_wavefront_map_2d(
            sys_obj, wl=wl_eff, field_y=field_y, grid_size=grid_size,
            defocus_offset=defocus_offset)
        out = {"wl": wl_eff, "field_y": field_y,
               "grid_size": grid_size,
               "defocus_offset": defocus_offset,
               **_wavefront_stats(wavefront, mask)}
        if include_grid:
            out["coords"] = coords.tolist()
            out["wavefront"] = wavefront.tolist()
            out["pupil_mask"] = mask.tolist()
        return out

    @registry.command(
        "zern.chromatic", category="zern",
        description="Коэффициенты Цернике на каждой λ системы + разности "
                    "от первичной λ (хроматизм разложения)",
        returns="by_wavelength: {λ: coeffs} и delta_λ−λперв",
        params=system_source_params([
            Param("num_rays", type="int", default=64,
                  help="лучей по стороне сетки зрачка"),
            Param("max_order", type="int", default=4,
                  help="максимальный порядок полиномов"),
        ]))
    def zern_chromatic(ctx, file, system, lbo_index, lbo_name,
                       num_rays, max_order):
        from analysis.zernike import compute_zernike_chromatic
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        result = compute_zernike_chromatic(sys_obj, num_rays=num_rays,
                                           max_order=max_order)
        return {"num_rays": num_rays, "max_order": max_order,
                "by_wavelength": result}

    @registry.command(
        "zern.global", category="zern",
        description="Глобальное разложение Цернике: коэффициенты для "
                    "каждой комбинации (точка поля × λ) + таблица",
        returns="combos [{field, wl, coeffs}] + текстовая таблица",
        params=system_source_params([
            Param("num_rings", type="int", default=4,
                  help="кольца гексаполярной сетки зрачка"),
            Param("max_order", type="int", default=4,
                  help="максимальный порядок полиномов"),
            Param("num_fields", type="int", default=5,
                  help="число точек поля, если поле не задано"),
        ]))
    def zern_global(ctx, file, system, lbo_index, lbo_name, num_rings,
                    max_order, num_fields):
        from analysis.zernike import (
            compute_global_zernike,
            format_global_zernike_text,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        result = compute_global_zernike(sys_obj, num_rings=num_rings,
                                        max_order=max_order,
                                        num_fields=num_fields)
        wl_names = {w.value: w.name for w in sys_obj.wavelengths
                    if getattr(w, "name", None)}
        return {
            "fields": [float(f) for f in result["fields"]],
            "wavelengths": [float(w) for w in result["wavelengths"]],
            "combos": [{"field": float(field), "wl": float(wl),
                        "coeffs": _coeff_rows(result["coeffs"][
                            (field, wl)], max_order)}
                       for field, wl in result["coeffs"]],
            "text": format_global_zernike_text(result, wl_names),
        }

    @registry.command(
        "zern.fit_points", category="zern",
        description="МНК-разложение по рассеянным точкам зрачка в базисе "
                    "OPAL-28 (Noll-нормировка, σ² ≈ Σc²)",
        returns="коэффициенты + марки/имена + СКВ остатка + Штрель",
        params=[
            Param("points", type="list", required=True,
                  help="точки зрачка [[px, py, W], ...] (−1..1, волны); "
                       "нужно ≥ 28 точек"),
        ])
    def zern_fit_points(ctx, points):
        from analysis.zernike import (
            ZERNIKE_MARKS_28,
            ZERNIKE_TERMS_28,
            fit_zernike_points,
            strehl_from_zernike,
            zernike_term_name,
        )
        parsed = _parse_points(points)
        if len(parsed) < len(ZERNIKE_TERMS_28):
            raise CommandError(
                ERR_INVALID_PARAM,
                f"точек {len(parsed)} < членов базиса "
                f"{len(ZERNIKE_TERMS_28)}")
        coeffs, residual_rms = fit_zernike_points(parsed)
        return {
            "coeffs": coeffs.tolist(),
            "residual_rms": float(residual_rms),
            "strehl_zernike": strehl_from_zernike(coeffs),
            "marks": list(ZERNIKE_MARKS_28),
            "names": [zernike_term_name(n, m) for n, m in
                      ZERNIKE_TERMS_28],
        }

    @registry.command(
        "zern.reconstruct", category="zern",
        description="Волновой фронт по коэффициентам базиса OPAL-28: "
                    "W = Σ c_k·Z_k (+ метрики по зрачку)",
        returns="СКВ/PV реконструкции (+карта W по запросу)",
        params=[
            Param("coeffs", type="list", required=True,
                  help="коэффициенты [c0..c27] (или короче — первые члены)"),
            Param("grid", type="int", default=32,
                  help="решётка N×N для реконструкции"),
            Param("include_grid", type="bool", default=False,
                  help="включить карту W (N² значений)"),
        ])
    def zern_reconstruct(ctx, coeffs, grid, include_grid):
        import numpy as np
        from analysis.zernike import zernike_reconstruct
        parsed = _parse_coeffs(coeffs)
        wavefront = zernike_reconstruct(parsed, grid)
        xs = np.linspace(-1.0, 1.0, wavefront.shape[1])
        gy, gx = np.meshgrid(xs, xs)
        mask = (gx ** 2 + gy ** 2) <= 1.0
        out = {"num_terms": len(parsed), "grid": grid,
               **_wavefront_stats(wavefront, mask)}
        if include_grid:
            out["wavefront"] = wavefront.tolist()
        return out

    @registry.command(
        "zern.strehl", category="zern",
        description="Штрель (Марешаль) из коэффициентов Цернике "
                    "Noll-нормировки: S = exp(−(2π)²·Σc²) без пистона",
        returns="strehl + sigma_w = sqrt(Σc²)",
        params=[
            Param("coeffs", type="list", required=True,
                  help="коэффициенты базиса (первый член — пистон)"),
        ])
    def zern_strehl(ctx, coeffs):
        from analysis.zernike import ZERNIKE_TERMS_28, strehl_from_zernike
        parsed = _parse_coeffs(coeffs)
        terms = ZERNIKE_TERMS_28[:len(parsed)]
        variance = sum(c * c for c, (n, m) in zip(parsed, terms)
                       if (n, m) != (0, 0))
        return {"strehl": strehl_from_zernike(parsed),
                "sigma_w": math.sqrt(variance),
                "num_terms": len(parsed)}

    @registry.command(
        "zern.decompose", category="zern",
        description="Разложение волнового фронта по базису OPAL-28 "
                    "(марки «C xIJ», вклад в СКВ, Штрель Марешаля)",
        returns="28 коэффициентов + вклады % + sigma_w + strehl_zernike",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def zern_decompose(ctx, file, system, lbo_index, lbo_name,
                       field_y, wl):
        from analysis.psf_mtf import zernike_decomposition
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        dec = zernike_decomposition(sys_obj, field_y=field_y, wl=wl)
        if dec.get("coeffs") is None:
            return {"reason": dec.get("reason", ""),
                    "coeffs": None, "wl": dec.get("wl"),
                    "field_y": dec.get("field_y")}
        return {
            "coeffs": dec["coeffs"].tolist(),
            "residual_rms": float(dec["residual_rms"]),
            "sigma_w": float(dec["sigma_w"]),
            "strehl_zernike": float(dec["strehl_zernike"]),
            "contributions_pct": [None if c is None else float(c)
                                  for c in dec["contributions_pct"]],
            "terms": [[n, m] for n, m in dec["terms"]],
            "marks": list(dec["marks"]),
            "names": list(dec["names"]),
            "wl": dec.get("wl"), "field_y": dec.get("field_y"),
            "num_points": dec.get("num_points"),
        }

    @registry.command(
        "zern.protocol", category="zern",
        description="Секция протокола «Разложение Цернике»: марки "
                    "«C xIJ», коэффициенты и вклад в СКВ (как OPAVA WGLB)",
        returns="текст секции протокола",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def zern_protocol(ctx, file, system, lbo_index, lbo_name,
                      field_y, wl):
        from analysis.psf_mtf import format_zernike_section
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = format_zernike_section(sys_obj, field_y=field_y, wl=wl)
        return {"field_y": field_y, "wl": wl, "text": text}

    # ========================================================
    # focus.* — критерии оптимального фокуса (focus_criteria.py)
    # ========================================================

    def _focus_params():
        """Общий хвост параметров команд фокуса."""
        return system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — λ макс. веса)"),
        ])

    @registry.command(
        "focus.min_rms", category="focus",
        description="Плоскость min RMS волнового фронта: Δz от плоскости "
                    "Гаусса (наименьшие квадраты по W и ρ²)",
        returns="dz_mm — сдвиг фокальной плоскости, мм",
        params=_focus_params())
    def focus_min_rms(ctx, file, system, lbo_index, lbo_name,
                      field_y, wl):
        from analysis.focus_criteria import focus_min_rms_wavefront
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        dz = focus_min_rms_wavefront(sys_obj, field=field_y, wl=wl)
        return {"field_y": field_y, "wl": _resolve_wl(sys_obj, wl),
                "dz_mm": dz}

    @registry.command(
        "focus.max_strehl", category="focus",
        description="Плоскость максимума Штреля (квадратура по "
                    "гексаполярным точкам зрачка)",
        returns="dz_mm — сдвиг фокальной плоскости, мм",
        params=_focus_params())
    def focus_max_strehl(ctx, file, system, lbo_index, lbo_name,
                         field_y, wl):
        from analysis.focus_criteria import focus_max_strehl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        dz = focus_max_strehl(sys_obj, field=field_y, wl=wl)
        return {"field_y": field_y, "wl": _resolve_wl(sys_obj, wl),
                "dz_mm": dz}

    @registry.command(
        "focus.zone_best", category="focus",
        description="Зональный баланс W(0.7) = W(1): классическая "
                    "плоскость наилучшей установки",
        returns="dz_mm — сдвиг фокальной плоскости, мм",
        params=_focus_params())
    def focus_zone_best(ctx, file, system, lbo_index, lbo_name,
                        field_y, wl):
        from analysis.focus_criteria import focus_zone_best
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        dz = focus_zone_best(sys_obj, field=field_y, wl=wl)
        return {"field_y": field_y, "wl": _resolve_wl(sys_obj, wl),
                "dz_mm": dz}

    @registry.command(
        "focus.min_spot", category="focus",
        description="Плоскость min RMS геометрического пятна (круг "
                    "наименьшего рассеяния, без дифракции)",
        returns="dz_mm — сдвиг фокальной плоскости, мм",
        params=_focus_params())
    def focus_min_spot(ctx, file, system, lbo_index, lbo_name,
                       field_y, wl):
        from analysis.focus_criteria import focus_min_spot_rms
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        dz = focus_min_spot_rms(sys_obj, field=field_y, wl=wl)
        return {"field_y": field_y, "wl": _resolve_wl(sys_obj, wl),
                "dz_mm": dz}

    @registry.command(
        "focus.eqf", category="focus",
        description="EQF «равнофокусность» OPAL (гипотеза): паритет СКВ "
                    "зон зрачка [0.3, 0.7] и [0.7, 1.0]",
        returns="dz_mm, d_waves, converged, residual, rms_in/rms_out",
        params=_focus_params())
    def focus_eqf(ctx, file, system, lbo_index, lbo_name, field_y, wl):
        from analysis.focus_criteria import eqf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        result = eqf(sys_obj, field=field_y, wl=wl)
        result["field_y"] = field_y
        result["wl"] = _resolve_wl(sys_obj, wl)
        return result

    @registry.command(
        "focus.all", category="focus",
        description="Сводка всех критериев фокуса + лучшая плоскость по "
                    "OPAL (EQF, при несходимости — min RMS(W))",
        returns="все плоскости (мм), Штрель в максимуме, meta (F#, z_G…)",
        params=_focus_params())
    def focus_all(ctx, file, system, lbo_index, lbo_name, field_y, wl):
        from analysis.focus_criteria import all_focus_criteria
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return all_focus_criteria(sys_obj, field=field_y, wl=wl)
