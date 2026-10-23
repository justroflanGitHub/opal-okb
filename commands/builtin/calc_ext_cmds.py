"""
OPAL-OKB — Пакет R500-6: расширенные расчётные команды calc.*.

- обёртки движков domain/calculations.py без команд: показатель
  преломления, ГЮЭ-радиусы, эффективные полудиаметры, виньетирование
  одного луча;
- производные параксиальные своды (кардинальные точки, зрачки,
  увеличение, Лагранж-инвариант, NA) — композиция paraxial_trace;
- геометрия/формулы (сагитты, силы поверхностей, тонкая линза, Эйри,
  дифракционный срез, ГРИП, ОПС, сопряжённые отрезки).
"""
import math

from commands.base import (
    ERR_INVALID_PARAM,
    ERR_NOT_FOUND,
    Param,
    CommandError,
)
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
)

from optics_utils import get_primary_wl

#: Коэффициент диска Эйри (первый нуль J1): d = 2·1.22·λ·F/#.
AIRY_FIRST_ZERO = 1.22

#: Показатель преломления воздуха (рабочая среда вне стёкол).
AIR_N = 1.0

#: Плоскость: радиус 0 в конвенции проекта (сагитта 0).
FLAT_RADIUS = 0.0


def _parax(system, wl):
    """Параксиальный расчёт с явной λ."""
    from domain.calculations import paraxial_trace
    return paraxial_trace(system, wl=wl)


def _sagitta(radius: float, height: float, conic: float = 0.0) -> float:
    """Сагитта сферы/коники: z = c h² / (1 + √(1 − (1+k) c² h²))."""
    if radius == FLAT_RADIUS:
        return 0.0
    c = 1.0 / radius
    disc = 1.0 - (1.0 + conic) * c * c * height * height
    if disc < 0.0:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"высота {height} вне апертуры R={radius} (дискриминант<0)")
    return c * height * height / (1.0 + math.sqrt(disc))


def _medium_n(system, index: int, wl: float) -> float:
    """n среды после поверхности index (стекло поверхности или воздух)."""
    from domain.calculations import refractive_index
    glass = system.surfaces[index].glass if index >= 0 else ""
    return refractive_index(glass, wl) if glass else AIR_N


def register(registry: Registry) -> None:
    """Зарегистрировать расширенные calc.* (R500-6)."""

    # ============================================================
    # Обёртки движков domain/calculations.py
    # ============================================================

    @registry.command(
        "calc.n", category="calc",
        description="Показатель преломления стекла на длине волны "
                    "(все каталоги: ГОСТ/.FIL/AGF)",
        returns="{name, source, wl, n}",
        params=[
            Param("glass", required=True, help="марка стекла"),
            Param("wl", type="float", default=0.58756,
                  help="длина волны, мкм"),
        ])
    def calc_n(ctx, glass, wl):
        from commands.builtin.catalog_cmds import (
            lookup_glass, refractive_index_for)
        entry = lookup_glass(glass)
        if entry is None:
            raise CommandError(ERR_NOT_FOUND,
                               f"стекло {glass!r} не найдено в каталогах")
        return {"name": entry["name"], "source": entry["source"],
                "wl": wl, "n": refractive_index_for(entry, wl)}

    @registry.command(
        "calc.goe.radius", category="calc",
        description="ГЮЭ-радиус поверхности (годная область установки "
                    "лучей) на длине волны",
        returns="{index, glass, radius}",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс поверхности (0-based)"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_goe_radius(ctx, file, system, lbo_index, lbo_name, index, wl):
        from domain.calculations import goe_effective_radius
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if not (0 <= index < sys_obj.num_surfaces):
            raise CommandError(ERR_INVALID_PARAM,
                               f"index={index} вне 0..{sys_obj.num_surfaces-1}")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        return {"index": index, "wl": wl_eff,
                "glass": sys_obj.surfaces[index].glass,
                "radius": goe_effective_radius(sys_obj.surfaces[index],
                                               wl_eff)}

    @registry.command(
        "calc.goe.table", category="calc",
        description="ГЮЭ-радиусы всех поверхностей системы",
        returns="{wl, rows: [{index, glass, radius, semi_diameter}]}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_goe_table(ctx, file, system, lbo_index, lbo_name, wl):
        from domain.calculations import goe_effective_radius
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        for i, s in enumerate(sys_obj.surfaces):
            rows.append({"index": i, "glass": s.glass,
                         "radius": goe_effective_radius(s, wl_eff),
                         "semi_diameter": s.semi_diameter})
        return {"wl": wl_eff, "rows": rows}

    @registry.command(
        "calc.semi_effective", category="calc",
        description="Эффективный полудиаметр (острая кромка срезает "
                    "2% запас на фаску)",
        returns="{semi_diameter, sharp_edge, effective}",
        params=[
            Param("semi_diameter", type="float", required=True,
                  help="полудиаметр, мм"),
            Param("sharp_edge", type="bool", default=True,
                  help="острая кромка (влияет на эффективный размер)"),
        ])
    def calc_semi_effective(ctx, semi_diameter, sharp_edge):
        from domain.calculations import effective_semi_diameter
        return {"semi_diameter": semi_diameter, "sharp_edge": sharp_edge,
                "effective": effective_semi_diameter(semi_diameter,
                                                     sharp_edge)}

    @registry.command(
        "calc.vignetting.apply", category="calc",
        description="Виньетируется ли луч (высоты ray_y/ray_x, мм, на "
                    "первой поверхности) на поле field_y",
        returns="{field_y, ray_y, ray_x, vignetted, passes}",
        params=system_source_params() + [
            Param("field_y", type="float", required=True, help="поле"),
            Param("ray_y", type="float", required=True,
                  help="высота луча, мм"),
            Param("ray_x", type="float", default=0.0,
                  help="саг. высота луча, мм"),
            Param("sharp_edge", type="bool", default=True,
                  help="острая кромка"),
        ])
    def calc_vignetting_apply(ctx, file, system, lbo_index, lbo_name,
                              field_y, ray_y, ray_x, sharp_edge):
        from domain.calculations import apply_vignetting
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        vignetted = apply_vignetting(sys_obj, field_y, ray_y, ray_x,
                                     sharp_edge)
        return {"field_y": field_y, "ray_y": ray_y, "ray_x": ray_x,
                "vignetted": vignetted, "passes": not vignetted}

    # ============================================================
    # Параксиальные своды (производные paraxial_trace)
    # ============================================================

    @registry.command(
        "calc.cardinals", category="calc",
        description="Кардинальные точки: фокусы F/F′, главные плоскости "
                    "H/H′, фокусные расстояния",
        returns="{f, f_prime, sF, sF_prime, sH, sH_prime, "
                "back_focal_distance, front_focal_distance}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_cardinals(ctx, file, system, lbo_index, lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parax = _parax(sys_obj, wl_eff)
        return {"wl": wl_eff,
                "f": -abs(parax["effective_focal_length"]),
                "f_prime": parax["effective_focal_length"],
                "sF": parax.get("sF"), "sF_prime": parax.get("sF_prime"),
                "sH": parax.get("sH"), "sH_prime": parax.get("sH_prime"),
                "back_focal_distance": parax.get("back_focal_distance"),
                "front_focal_distance": parax.get("front_focal_distance")}

    @registry.command(
        "calc.pupils", category="calc",
        description="Зрачки системы: входной/выходной (положения от "
                    "первой/последней поверхности, диаметры, увеличения)",
        returns="{sP, sP_prime, entrance_diameter, magnifications}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_pupils(ctx, file, system, lbo_index, lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parax = _parax(sys_obj, wl_eff)
        return {"wl": wl_eff,
                "sP": parax.get("sP"), "sP_prime": parax.get("sP_prime"),
                "entrance_diameter": parax.get("entrance_pupil_diameter"),
                "entrance_pupil_magnification":
                    parax.get("entrance_pupil_magnification"),
                "pupil_magnification": parax.get("pupil_magnification")}

    @registry.command(
        "calc.magnification", category="calc",
        description="Увеличение системы V и продольный масштаб L "
                    "(параксиальный расчёт)",
        returns="{V, L}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_magnification(ctx, file, system, lbo_index, lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parax = _parax(sys_obj, wl_eff)
        return {"wl": wl_eff, "V": parax.get("V"), "L": parax.get("L")}

    @registry.command(
        "calc.lagrange", category="calc",
        description="Инвариант Лагранжа-Гельмгольца H = n·(D/2)·tg ω_max "
                    "(n=1, воздух)",
        returns="{H, epd_mm, max_field, wl}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_lagrange(ctx, file, system, lbo_index, lbo_name, wl):
        from analysis.tables import max_field
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parax = _parax(sys_obj, wl_eff)
        epd = parax.get("entrance_pupil_diameter") or 0.0
        field = max_field(sys_obj)
        if epd <= 0 or field <= 0:
            raise CommandError(
                ERR_INVALID_PARAM,
                "инвариант не определён: нулевой зрачок или поле")
        return {"wl": wl_eff, "epd_mm": epd, "max_field": field,
                "H": 0.5 * epd * math.tan(math.radians(field))}

    @registry.command(
        "calc.aperture.na", category="calc",
        description="Числовые апертуры: в пространстве изображений "
                    "NA′ = D/(2f′) и предмета NA = NA′·|V|",
        returns="{na_image, na_object, f_number}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_aperture_na(ctx, file, system, lbo_index, lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        parax = _parax(sys_obj, wl_eff)
        epd = parax.get("entrance_pupil_diameter") or 0.0
        efl = abs(parax.get("effective_focal_length") or 0.0)
        if epd <= 0 or efl <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "NA не определена: вырожденный параксиал")
        na_image = epd / (2.0 * efl)
        na_image = min(na_image, 1.0)
        v = abs(parax.get("V") or 0.0)
        return {"wl": wl_eff, "na_image": na_image,
                "na_object": min(na_image * v, 1.0) if v else None,
                "f_number": parax.get("f_number")}

    # ============================================================
    # Геометрия и формулы
    # ============================================================

    @registry.command(
        "calc.sagitta", category="calc",
        description="Сагитта поверхности на высоте (сфера/коника)",
        returns="{radius, height, conic_constant, sag}",
        params=[
            Param("radius", type="float", required=True,
                  help="радиус, мм (0 — плоскость)"),
            Param("height", type="float", required=True,
                  help="высота от оси, мм"),
            Param("conic_constant", type="float", default=0.0,
                  help="коническая постоянная k"),
        ])
    def calc_sagitta(ctx, radius, height, conic_constant):
        return {"radius": radius, "height": height,
                "conic_constant": conic_constant,
                "sag": _sagitta(radius, height, conic_constant)}

    @registry.command(
        "calc.sagitta.table", category="calc",
        description="Сагитты поверхностей системы на заданных высотах",
        returns="{rows: [{index, radius, height, sag}], heights}",
        params=system_source_params() + [
            Param("heights", type="list", required=True,
                  help="высоты от оси, мм"),
        ])
    def calc_sagitta_table(ctx, file, system, lbo_index, lbo_name,
                           heights):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for i, s in enumerate(sys_obj.surfaces):
            for height in heights:
                rows.append({
                    "index": i, "radius": s.radius,
                    "height": float(height),
                    "sag": _sagitta(s.radius, float(height),
                                    s.conic_constant),
                })
        return {"heights": [float(h) for h in heights], "rows": rows}

    @registry.command(
        "calc.power.surface", category="calc",
        description="Сила сферической поверхности Φ = (n₂−n₁)/R, дптр",
        returns="{n1, n2, radius, power_dpt}",
        params=[
            Param("n1", type="float", required=True,
                  help="n среды до поверхности"),
            Param("n2", type="float", required=True,
                  help="n среды после поверхности"),
            Param("radius", type="float", required=True,
                  help="радиус, мм (0 — плоскость, Φ=0)"),
        ])
    def calc_power_surface(ctx, n1, n2, radius):
        if radius == FLAT_RADIUS:
            power = 0.0
        else:
            power = (n2 - n1) / radius * 1000.0
        return {"n1": n1, "n2": n2, "radius": radius,
                "power_dpt": power}

    @registry.command(
        "calc.power.thin_lens", category="calc",
        description="Тонкая линза: 1/f′ = (n−1)(1/r₁ − 1/r₂)",
        returns="{n, r1, r2, f_prime, power_dpt}",
        params=[
            Param("n", type="float", required=True, help="n материала"),
            Param("r1", type="float", required=True,
                  help="первый радиус, мм (0 — плоскость)"),
            Param("r2", type="float", required=True,
                  help="второй радиус, мм (0 — плоскость)"),
        ])
    def calc_power_thin_lens(ctx, n, r1, r2):
        inv_r1 = 0.0 if r1 == FLAT_RADIUS else 1.0 / r1
        inv_r2 = 0.0 if r2 == FLAT_RADIUS else 1.0 / r2
        power = (n - 1.0) * (inv_r1 - inv_r2)  # 1/мм
        if power == 0.0:
            raise CommandError(ERR_INVALID_PARAM,
                               "афокальная комбинация: f′ = ∞")
        return {"n": n, "r1": r1, "r2": r2,
                "f_prime": 1.0 / power, "power_dpt": power * 1000.0}

    @registry.command(
        "calc.power.table", category="calc",
        description="Силы поверхностей системы Φᵢ = (nᵢ₊₁−nᵢ)/Rᵢ по "
                    "стёклам (n воздуха = 1)",
        returns="{wl, rows: [{index, n_before, n_after, radius, power_dpt}]}",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_power_table(ctx, file, system, lbo_index, lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = []
        total = 0.0
        for i, s in enumerate(sys_obj.surfaces):
            n_before = AIR_N if i == 0 else _medium_n(sys_obj, i - 1, wl_eff)
            n_after = _medium_n(sys_obj, i, wl_eff)
            power = (0.0 if s.radius == FLAT_RADIUS
                     else (n_after - n_before) / s.radius * 1000.0)
            total += power
            rows.append({"index": i, "glass": s.glass,
                         "n_before": n_before, "n_after": n_after,
                         "radius": s.radius, "power_dpt": power})
        return {"wl": wl_eff, "rows": rows, "total_thin_dpt": total}

    @registry.command(
        "calc.airy", category="calc",
        description="Дифракционный диск Эйри: d = 2·1.22·λ·F/#",
        returns="{f_number, wl, radius_um, diameter_um}",
        params=[
            Param("f_number", type="float", required=True,
                  help="диафрагменное число"),
            Param("wl", type="float", default=0.54607,
                  help="длина волны, мкм"),
        ])
    def calc_airy(ctx, f_number, wl):
        if f_number <= 0:
            raise CommandError(ERR_INVALID_PARAM, "F/# должен быть > 0")
        diameter = 2.0 * AIRY_FIRST_ZERO * wl * f_number
        return {"f_number": f_number, "wl": wl,
                "radius_um": diameter / 2.0, "diameter_um": diameter}

    @registry.command(
        "calc.diffraction.cutoff", category="calc",
        description="Дифракционный срез ЧКХ: ν_c = 1/(λ·F/#), лин/мм",
        returns="{f_number, wl, cutoff_lpmm}",
        params=[
            Param("f_number", type="float", required=True,
                  help="диафрагменное число"),
            Param("wl", type="float", default=0.54607,
                  help="длина волны, мкм"),
        ])
    def calc_diffraction_cutoff(ctx, f_number, wl):
        if f_number <= 0 or wl <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "F/# и λ должны быть > 0")
        return {"f_number": f_number, "wl": wl,
                "cutoff_lpmm": 1.0 / (wl * 1e-3 * f_number)}

    @registry.command(
        "calc.depth_of_field", category="calc",
        description="ГРИП (геометрическая): ±Δ = c·F/#·(1+m), "
                    "полная глубина 2Δ",
        returns="{f_number, coc_um, magnification, plus_minus_mm, total_mm}",
        params=[
            Param("f_number", type="float", required=True,
                  help="диафрагменное число"),
            Param("coc_um", type="float", required=True,
                  help="круг нерезкости, мкм"),
            Param("magnification", type="float", default=0.0,
                  help="увеличение (макро-режим)"),
        ])
    def calc_depth_of_field(ctx, f_number, coc_um, magnification):
        if f_number <= 0 or coc_um <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "F/# и круг нерезкости должны быть > 0")
        half = coc_um * 1e-3 * f_number * (1.0 + abs(magnification))
        return {"f_number": f_number, "coc_um": coc_um,
                "magnification": magnification,
                "plus_minus_mm": half, "total_mm": 2.0 * half}

    @registry.command(
        "calc.opl", category="calc",
        description="Оптическая длина пути Σ nᵢ·Lᵢ по участкам",
        returns="{segments, total_opl_mm}",
        params=[
            Param("segments", type="list", required=True,
                  help="список [{n, length}] (длина, мм)"),
        ])
    def calc_opl(ctx, segments):
        if not segments:
            raise CommandError(ERR_INVALID_PARAM, "segments пуст")
        rows, total = [], 0.0
        for seg in segments:
            try:
                n = float(seg["n"])
                length = float(seg["length"])
            except (KeyError, TypeError, ValueError) as exc:
                raise CommandError(
                    ERR_INVALID_PARAM,
                    f"сегмент {seg!r}: нужны ключи n и length") from exc
            rows.append({"n": n, "length": length, "opl": n * length})
            total += n * length
        return {"segments": rows, "total_opl_mm": total}

    @registry.command(
        "calc.conjugate.solve", category="calc",
        description="Сопряжённые отрезки (формула отрезков, "
                    "1/s′ − 1/s = 1/f′): по s → s′, V; или по V → s",
        returns="{f_prime, s, s_prime, V}",
        params=system_source_params() + [
            Param("f_override", type="float",
                  help="f′ явно, мм (по умолчанию — параксиал системы)"),
            Param("s", type="float",
                  help="отрезок предмета от H, мм (s<0 — реальный предмет)"),
            Param("V_target", type="float",
                  help="искомое увеличение (знак — инверсия изображения)"),
        ])
    def calc_conjugate_solve(ctx, file, system, lbo_index, lbo_name,
                             f_override, s, V_target):
        if (s is None) == (V_target is None):
            raise CommandError(ERR_INVALID_PARAM,
                               "задайте ровно одно из s / V_target")
        if f_override is not None:
            f_prime = f_override
        else:
            sys_obj = resolve_system(ctx, file, system, lbo_index,
                                     lbo_name)
            f_prime = abs(_parax(sys_obj, None)["effective_focal_length"])
        if f_prime == 0:
            raise CommandError(ERR_INVALID_PARAM, "f′ = 0")
        if s is not None:
            if s == 0.0:
                raise CommandError(ERR_INVALID_PARAM,
                                   "s=0: предмет в главной плоскости")
            denom = 1.0 / f_prime + 1.0 / s
            if denom == 0.0:
                raise CommandError(ERR_INVALID_PARAM,
                                   f"s={s} = −f′: изображение в "
                                   f"бесконечности")
            s_prime = 1.0 / denom
            v = s_prime / s
        else:
            if V_target == 0:
                raise CommandError(ERR_INVALID_PARAM, "V=0 вырождено")
            s = f_prime * (1.0 - V_target) / V_target
            denom = 1.0 / f_prime + 1.0 / s
            s_prime = 1.0 / denom if denom != 0.0 else None
            v = V_target
        return {"f_prime": f_prime, "s": s, "s_prime": s_prime, "V": v}
