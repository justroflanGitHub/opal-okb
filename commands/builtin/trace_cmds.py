"""
OPAL-OKB — Команды Волны 3 (домен «Трассировка и таблицы»): trace.*,
beam.*, vign.*, tables.*

Обёртки над ОСТАЛЬНЫМИ публичными точками входа модулей
``analysis/ray_tracing.py``, ``analysis/beam_heights.py``,
``analysis/vignetting.py``, ``analysis/tables.py`` (trace_fan /
tabgl_rows / tabpr2_rows уже обёрнуты Волной 1 как ``analyze.ray_fan``
/ ``analyze.tables.tabgl`` / ``analyze.tables.tabpr2`` — не дублируются).
Геометрические примитивы Снеллиуса (intersect_*/normal_*/refract) —
команды без системы: чистая геометрия луча.
"""
import math

from optics_utils import get_primary_wl

from commands.base import ERR_INVALID_PARAM, CommandError, Param
from commands.registry import Registry
from commands.systemio import resolve_system, system_source_params

#: Селектор колонок TABOC2 — ключи :data:`analysis.tables.TABOC2_COLUMNS`
#: (ровно 3 из 5, формат формы печатает три величины).
TABOC2_COLUMN_KEYS = ("wave", "iso", "h_zr", "z_m", "c_s")

#: Осевой эталонный набор колонок TABOC2 (RT__2236).
TABOC2_COLUMNS_DEFAULT = ["wave", "iso", "h_zr"]

#: Сетка узлов по умолчанию: виньетирование/зоны прохождения (15 — как
#: :data:`analysis.vignetting.LIGHT_GRID_N` / ``PASSAGE_GRID_N``).
GRID_N_DEFAULT = 15


def _unit_direction(k: float, l: float, m: float, prefix: str = "") -> tuple:
    """Направление луча, нормированное на единицу.

    Трейсер и пересечения считают ``t`` геометрическим расстоянием —
    направление обязано быть единичным вектором.

    Raises:
        CommandError: ``invalid_param`` — нулевой вектор направления.
    """
    norm = math.sqrt(k * k + l * l + m * m)
    if norm < 1e-12:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"{prefix}направление луча (k,l,m)=({k},{l},{m}) — нулевой "
            f"вектор; задайте ненулевое направление")
    return (k / norm, l / norm, m / norm)


def _make_ray(x: float, y: float, z: float, k: float, l: float, m: float):
    """``Ray`` из параметров команды (направление нормируется)."""
    from analysis.ray_tracing import Ray
    dk, dl, dm = _unit_direction(k, l, m)
    return Ray(x=x, y=y, z=z, k=dk, l=dl, m=dm)


def _floats(values) -> list:
    """Список чисел из параметра-list (CLI-csv даёт строки — привести)."""
    return [float(v) for v in values]


def _trace_dict(result) -> dict:
    """TraceResult → JSON-совместимый словарь (путь — список [x,y,z])."""
    return {
        "success": result.success,
        "error": result.error,
        "surfaces_hit": result.surfaces_hit,
        "opl": result.opl,
        "path": [[p[0], p[1], p[2]] for p in result.path],
    }


def register(registry: Registry) -> None:
    """Зарегистрировать все команды trace.*/beam.*/vign.*/tables.*."""

    # ============================================================
    # trace.* — analysis/ray_tracing.py
    # ============================================================

    @registry.command(
        "trace.ray", category="trace",
        description="Трассировка одного луча через систему "
                    "(точка + направление, Снеллиус)",
        returns="{success, error, surfaces_hit, opl, path}",
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
    def trace_ray(ctx, file, system, lbo_index, lbo_name,
                  x, y, z, k, l, m, wl):
        from analysis.ray_tracing import trace_ray_through_system
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        ray = _make_ray(x, y, z, k, l, m)
        result = trace_ray_through_system(sys_obj, ray, wl_eff)
        out = {"wl": wl_eff, "origin": [ray.x, ray.y, ray.z],
               "direction": [ray.k, ray.l, ray.m]}
        out.update(_trace_dict(result))
        return out

    @registry.command(
        "trace.grid3d", category="trace",
        description="3D-сетка лучей по кольцам входного зрачка "
                    "(кольца × азимуты)",
        returns="кольца лучей {rho, phi_deg, success, error, opl, "
                "last_point (+path при include_path)}",
        params=system_source_params([
            Param("num_rings", type="int", default=3,
                  help="число колец зрачка (первое — центральный луч)"),
            Param("num_azimuths", type="int", default=8,
                  help="число азимутальных лучей на кольцо"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("include_path", type="bool", default=False,
                  help="включить полные пути лучей (большой объём)"),
        ]))
    def trace_grid3d(ctx, file, system, lbo_index, lbo_name, num_rings,
                     num_azimuths, wl, field_y, include_path):
        from analysis.ray_tracing import trace_grid_3d
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rings = trace_grid_3d(sys_obj, num_rings=num_rings,
                              num_azimuths=num_azimuths, wl=wl_eff,
                              field_y=field_y)
        # Доли радиуса зрачка: ring 0 — центральный луч (rho 0, в том
        # числе вырожденное num_rings=1 — все лучи в центре), кольцо i≥1
        # — (i+1)/num_rings (как построитель сетки); азимут луча j —
        # 360°·j/num_azimuths.
        out_rings = []
        for ring_idx, ring in enumerate(rings):
            rho = 0.0 if ring_idx == 0 else (ring_idx + 1) / num_rings
            rays_out = []
            for j, r in enumerate(ring):
                entry = {
                    "rho": rho,
                    "phi_deg": (0.0 if len(ring) == 1
                                else 360.0 * j / num_azimuths),
                    "success": r.success,
                    "error": r.error,
                    "surfaces_hit": r.surfaces_hit,
                    "opl": r.opl,
                    "last_point": ([r.path[-1][0], r.path[-1][1],
                                    r.path[-1][2]] if r.path else None),
                }
                if include_path:
                    entry["path"] = [[p[0], p[1], p[2]] for p in r.path]
                rays_out.append(entry)
            out_rings.append(rays_out)
        return {"wl": wl_eff, "field_y": field_y, "num_rings": num_rings,
                "num_azimuths": num_azimuths, "rings": out_rings}

    @registry.command(
        "trace.focal_spot", category="trace",
        description="Точечная диаграмма в фокальной плоскости (веер на "
                    "поле 0, отклонения от главного луча)",
        returns="точки пятна (dx, dy) в мм",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("num_rays", type="int", default=20,
                  help="лучей в осевом веере"),
        ]))
    def trace_focal_spot(ctx, file, system, lbo_index, lbo_name, wl,
                         num_rays):
        from analysis.ray_tracing import get_focal_spot
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        spots = get_focal_spot(sys_obj, wl=wl_eff, num_rays=num_rays)
        return {"wl": wl_eff, "num_rays": num_rays,
                "num_points": len(spots),
                "spots": [[dx, dy] for dx, dy in spots]}

    @registry.command(
        "trace.intersect.sphere", category="trace",
        description="Пересечение луча со сферой/плоскостью (без системы)",
        returns="{hit: [x,y,z]|null, t: расстояние|null}",
        params=[
            Param("x", type="float", default=0.0, help="старт луча X, мм"),
            Param("y", type="float", default=0.0, help="старт луча Y, мм"),
            Param("z", type="float", default=0.0, help="старт луча Z, мм"),
            Param("k", type="float", default=0.0,
                  help="направление X (нормируется)"),
            Param("l", type="float", default=0.0,
                  help="направление Y (нормируется)"),
            Param("m", type="float", default=1.0,
                  help="направление Z (нормируется)"),
            Param("radius", type="float", default=0.0,
                  help="радиус кривизны, мм (0 — плоскость)"),
            Param("z_surf", type="float", default=0.0,
                  help="Z-вершина поверхности, мм"),
        ])
    def trace_intersect_sphere(ctx, x, y, z, k, l, m, radius, z_surf):
        from analysis.ray_tracing import intersect_sphere
        ray = _make_ray(x, y, z, k, l, m)
        hit = intersect_sphere(ray, radius, z_surf)
        return {"hit": (list(hit[:3]) if hit is not None else None),
                "t": (hit[3] if hit is not None else None)}

    @registry.command(
        "trace.intersect.aspheric", category="trace",
        description="Пересечение луча с асферой (коника + полином, Ньютон)",
        returns="{hit: [x,y,z]|null, t: расстояние|null}",
        params=[
            Param("x", type="float", default=0.0, help="старт луча X, мм"),
            Param("y", type="float", default=0.0, help="старт луча Y, мм"),
            Param("z", type="float", default=0.0, help="старт луча Z, мм"),
            Param("k", type="float", default=0.0,
                  help="направление X (нормируется)"),
            Param("l", type="float", default=0.0,
                  help="направление Y (нормируется)"),
            Param("m", type="float", default=1.0,
                  help="направление Z (нормируется)"),
            Param("radius", type="float", default=0.0,
                  help="радиус базовой кривизны, мм (0 — плоскость)"),
            Param("z_surf", type="float", default=0.0,
                  help="Z-вершина поверхности, мм"),
            Param("conic_k", type="float", default=0.0,
                  help="коническая постоянная"),
            Param("aspheric_coeffs", type="list", default=[],
                  help="коэффициенты A4, A6, ... (r⁴, r⁶, ...)"),
        ])
    def trace_intersect_aspheric(ctx, x, y, z, k, l, m, radius, z_surf,
                                 conic_k, aspheric_coeffs):
        from analysis.ray_tracing import intersect_aspheric
        ray = _make_ray(x, y, z, k, l, m)
        hit = intersect_aspheric(ray, radius, z_surf, conic_k=conic_k,
                                 aspheric_coeffs=_floats(aspheric_coeffs))
        return {"hit": (list(hit[:3]) if hit is not None else None),
                "t": (hit[3] if hit is not None else None)}

    @registry.command(
        "trace.normal.sphere", category="trace",
        description="Нормаль к сферической поверхности в точке (без системы)",
        returns="{normal: [nx,ny,nz]}",
        params=[
            Param("x", type="float", required=True,
                  help="точка на поверхности X, мм"),
            Param("y", type="float", required=True,
                  help="точка на поверхности Y, мм"),
            Param("z", type="float", required=True,
                  help="точка на поверхности Z, мм"),
            Param("radius", type="float", default=0.0,
                  help="радиус кривизны, мм (0 — плоскость)"),
            Param("z_surf", type="float", default=0.0,
                  help="Z-вершина поверхности, мм"),
        ])
    def trace_normal_sphere(ctx, x, y, z, radius, z_surf):
        from analysis.ray_tracing import surface_normal
        nx, ny, nz = surface_normal(x, y, z, radius, z_surf)
        return {"normal": [nx, ny, nz]}

    @registry.command(
        "trace.normal.aspheric", category="trace",
        description="Нормаль к асферической поверхности в точке",
        returns="{normal: [nx,ny,nz]}",
        params=[
            Param("x", type="float", required=True,
                  help="точка на поверхности X, мм"),
            Param("y", type="float", required=True,
                  help="точка на поверхности Y, мм"),
            Param("z", type="float", required=True,
                  help="точка на поверхности Z, мм"),
            Param("radius", type="float", default=0.0,
                  help="радиус базовой кривизны, мм (0 — плоскость)"),
            Param("z_surf", type="float", default=0.0,
                  help="Z-вершина поверхности, мм"),
            Param("conic_k", type="float", default=0.0,
                  help="коническая постоянная"),
            Param("aspheric_coeffs", type="list", default=[],
                  help="коэффициенты A4, A6, ... (r⁴, r⁶, ...)"),
        ])
    def trace_normal_aspheric(ctx, x, y, z, radius, z_surf, conic_k,
                              aspheric_coeffs):
        from analysis.ray_tracing import surface_normal_aspheric
        nx, ny, nz = surface_normal_aspheric(
            x, y, z, radius, z_surf, conic_k=conic_k,
            aspheric_coeffs=_floats(aspheric_coeffs))
        return {"normal": [nx, ny, nz]}

    @registry.command(
        "trace.refract", category="trace",
        description="Преломление по Снеллиусу в векторной форме",
        returns="{refracted: [k',l',m']|null, tir: bool}",
        params=[
            Param("k", type="float", required=True, help="направление X"),
            Param("l", type="float", required=True, help="направление Y"),
            Param("m", type="float", required=True, help="направление Z"),
            Param("nx", type="float", required=True,
                  help="нормаль X (единичная)"),
            Param("ny", type="float", required=True,
                  help="нормаль Y (единичная)"),
            Param("nz", type="float", required=True,
                  help="нормаль Z (единичная)"),
            Param("n1", type="float", required=True,
                  help="показатель преломления среды луча"),
            Param("n2", type="float", required=True,
                  help="показатель преломления второй среды"),
        ])
    def trace_refract(ctx, k, l, m, nx, ny, nz, n1, n2):
        from analysis.ray_tracing import refract
        dk, dl, dm = _unit_direction(k, l, m)
        refracted = refract(dk, dl, dm, nx, ny, nz, n1, n2)
        return {"refracted": (list(refracted) if refracted is not None
                              else None),
                "tir": refracted is None}

    # ============================================================
    # beam.* — analysis/beam_heights.py (TABESB / TABEAP)
    # ============================================================

    @registry.command(
        "beam.heights", category="beam",
        description="Световые высоты габаритных лучей по поверхностям "
                    "(таблица TABESB, §14.1)",
        returns="строки таблицы + текстовый формат OPAL",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле пучка (град / мм; знак OPAL — предмет "
                       "отрицательный)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def beam_heights(ctx, file, system, lbo_index, lbo_name, field_y, wl):
        from analysis.beam_heights import format_tabesb, tabesb_rows
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = tabesb_rows(sys_obj, field_y=field_y, wl=wl_eff)
        return {"wl": wl_eff, "field_y": field_y, "rows": rows,
                "text": format_tabesb(rows)}

    @registry.command(
        "beam.screen_zones", category="beam",
        description="Экранные зоны: относительное экранирование зрачков "
                    "по пучкам (таблица TABEAP, §14.1)",
        returns="строки таблицы + текстовый формат OPAL",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def beam_screen_zones(ctx, file, system, lbo_index, lbo_name, wl):
        from analysis.beam_heights import format_tabeap, tabeap_rows
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = tabeap_rows(sys_obj, wl=wl_eff)
        return {"wl": wl_eff, "rows": rows, "text": format_tabeap(rows)}

    # ============================================================
    # vign.* — analysis/vignetting.py (TABBEA + прямые величины)
    # ============================================================

    @registry.command(
        "vign.compute", category="vign",
        description="Виньетирование верх/низ пучка + ограничивающий "
                    "элемент (бисекция по точному трейсеру)",
        returns="{vignet_up, vignet_down, limit_up, limit_down, obscured}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def vign_compute(ctx, file, system, lbo_index, lbo_name, field_y, wl):
        from analysis.vignetting import compute_vignetting
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        out = compute_vignetting(sys_obj, field_y, wl=wl_eff)
        out["wl"] = wl_eff
        out["field_y"] = field_y
        return out

    @registry.command(
        "vign.light", category="vign",
        description="Светораспределение по полям: доля площади зрачка + "
                    "центроид (сетка по единичному кругу)",
        returns="строки {field_y, light_up, light_down, light_total, "
                "centroid_y, n_samples, n_passed}",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей (град/мм); по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("grid_n", type="int", default=GRID_N_DEFAULT,
                  help="узлов сетки зрачка по оси (нечётное)"),
        ]))
    def vign_light(ctx, file, system, lbo_index, lbo_name, fields, wl,
                   grid_n):
        from analysis.vignetting import compute_light_distribution
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        # Дефолт полей — как tabbea_rows: точки поля системы, при пустом
        # списке — осевое поле [0].
        field_list = _floats(fields) if fields else (
            [float(fp.y) for fp in (sys_obj.field_points or [])] or [0.0])
        rows = compute_light_distribution(sys_obj, field_list,
                                          wl=wl_eff, grid_n=grid_n)
        return {"wl": wl_eff, "grid_n": grid_n, "fields": rows}

    @registry.command(
        "vign.tabbea", category="vign",
        description="Апертурные характеристики пучков: апертуры, зрачки, "
                    "виньетирование, светораспределение (таблица TABBEA)",
        returns="строки таблицы + текстовый формат OPAL",
        params=system_source_params([
            Param("fields", type="list",
                  help="список полей (град/мм); по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def vign_tabbea(ctx, file, system, lbo_index, lbo_name, fields, wl):
        from analysis.vignetting import format_tabbea, tabbea_rows
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        field_list = _floats(fields) if fields else None
        rows = tabbea_rows(sys_obj, fields=field_list, wl=wl_eff)
        return {"wl": wl_eff, "rows": rows, "text": format_tabbea(rows)}

    @registry.command(
        "vign.passage_zones", category="vign",
        description="Зоны прохождения пучка по ВСЕМ поверхностям "
                    "(«реальное экранирование», веер по диаметру зрачка)",
        returns="{passage_fraction, vignetted, surfaces: [{n, crossed, "
                "passed, outer, inner, center, blocked_here, limit}]}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("grid_n", type="int", default=GRID_N_DEFAULT,
                  help="узлов веера по диаметру зрачка (нечётное)"),
        ]))
    def vign_passage_zones(ctx, file, system, lbo_index, lbo_name, field_y,
                           wl, grid_n):
        from analysis.vignetting import find_passage_zones
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        return find_passage_zones(sys_obj, field_y, wl=wl_eff,
                                  grid_n=grid_n)

    @registry.command(
        "vign.real_obscuration", category="vign",
        description="«Габариты экранов»: эллипс экранирования на входном "
                    "зрачке, бисекция по 4 полуосям (TABEAP)",
        returns="{full_diameter_y/x, screen_diameter_y/x, "
                "obscuration_fraction, screen_shift, minimal_obscuration, "
                "cutters}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def vign_real_obscuration(ctx, file, system, lbo_index, lbo_name,
                              field_y, wl):
        from analysis.vignetting import real_obscuration
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        return real_obscuration(sys_obj, field_y, wl=wl_eff)

    # ============================================================
    # tables.* — analysis/tables.py (TABOC1/TABOC2 + зоны поля)
    # ============================================================

    @registry.command(
        "tables.taboc1", category="tables",
        description="Остаточные аберрации осевого пучка по зонам зрачка: "
                    "продольные + поперечные (таблица TABOC1, §11.3)",
        returns="строки таблицы + текстовый формат OPAL",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("n_zones", type="int", default=4,
                  help="число зон зрачка (осевая строка — сверх)"),
        ]))
    def tables_taboc1(ctx, file, system, lbo_index, lbo_name, wl, n_zones):
        from analysis.tables import format_taboc1, taboc1_rows
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = taboc1_rows(sys_obj, wl=wl_eff, n_zones=n_zones)
        return {"wl": wl_eff, "rows": rows, "text": format_taboc1(rows)}

    @registry.command(
        "tables.taboc2", category="tables",
        description="Волновые/остаточные аберрации осевого пучка по зонам "
                    "зрачка (таблица TABOC2: волновые, неизопл., Н ЗР, ...)",
        returns="строки таблицы + текст (3 величины из 5 по селектору)",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("n_zones", type="int", default=4,
                  help="число зон зрачка (осевая строка — сверх)"),
            Param("num_rays", type="int", default=20,
                  help="лучей веера неизопланатизма"),
            Param("columns", type="list", default=TABOC2_COLUMNS_DEFAULT,
                  help=f"селектор колонок: ровно 3 из {list(TABOC2_COLUMN_KEYS)}"),
        ]))
    def tables_taboc2(ctx, file, system, lbo_index, lbo_name, wl, n_zones,
                      num_rays, columns):
        from analysis.tables import format_taboc2, taboc2_rows
        cols = [str(c) for c in columns or []]
        unknown = [c for c in cols if c not in TABOC2_COLUMN_KEYS]
        if unknown or len(cols) != 3:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"параметр 'columns': нужно ровно 3 ключа из "
                f"{list(TABOC2_COLUMN_KEYS)}; получено: {cols}")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        rows = taboc2_rows(sys_obj, wl=wl_eff, n_zones=n_zones,
                           num_rays=num_rays)
        return {"wl": wl_eff, "columns": cols, "rows": rows,
                "text": format_taboc2(rows, columns=cols)}

    @registry.command(
        "tables.field_zones", category="tables",
        description="Зоны поля/зрачка равной площади: 1, √((n−1)/n), …, "
                    "√(1/n) (сетка таблиц TABGL/TABOC)",
        returns="{n_zones, zones: [1, √((n−1)/n), ...]}",
        params=[
            Param("n_zones", type="int", default=3,
                  help="число зон (≥1)"),
        ])
    def tables_field_zones(ctx, n_zones):
        from analysis.tables import field_zones
        return {"n_zones": max(1, int(n_zones)),
                "zones": field_zones(n_zones)}

    @registry.command(
        "tables.max_field", category="tables",
        description="Максимальное поле системы (град для INFINITE / мм "
                    "для FINITE) — база зон табличного вывода",
        returns="{max_field: число (0 — поля нет)}",
        params=system_source_params())
    def tables_max_field(ctx, file, system, lbo_index, lbo_name):
        from analysis.tables import max_field
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"max_field": max_field(sys_obj)}
