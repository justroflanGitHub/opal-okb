"""
OPAL-OKB — Пакет R500-4: расширенный каталог стёкол и спектральные линии.

- ``catalog.glass.*`` — списки/фильтры/дисперсия/пары по каталогам
  ГОСТ/.FIL/AGF (поверх :mod:`commands.builtin.catalog_cmds` и
  :mod:`domain.calculations.refractive_index`, без дублей логики);
- ``catalog.achromat.options`` — варианты ахроматического дублета по
  парам стёкол (существующий дизайнер :func:`achromat.design_achromat`);
- ``catalog.spectral.*`` — справочник стандартных спектральных линий
  (единственный источник ``utils/spectral_lines.py``) и его привязка
  к рабочим λ системы;
- ``diagram.data/types`` — данные карты стёкол n–V headless (типы/цвета
  из :mod:`glass_diagram`).
"""
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

from commands.builtin.catalog_cmds import (
    SOURCE_AGF,
    SOURCE_FIL,
    SOURCE_GOST,
    _agf_names,
    _fil_catalog,
    _gost_catalog,
    lookup_glass,
    refractive_index_for,
)

#: Границы фильтра каталога по умолчанию (все стёкла).
ND_RANGE = (0.0, 100.0)
VD_RANGE = (0.0, 200.0)

#: Сортировки catalog.glass.filter/list.
ORDER_KEYS = ("name", "nd", "vd")

#: Число строк каталога в ответе по умолчанию.
GLASS_PAGE_DEFAULT = 50

#: Минимальная разность Vd пары крон+флинт (ахроматизация).
PAIR_MIN_VD_DIFF = 15.0

#: Минимальный Vd крона пары (реальные стёкла, не воздух/спецсреды).
CROWN_MIN_VD = 40.0

#: Минимальный Vd флинта пары (отсекает воздух и спецсреды с vd≈0).
FLINT_MIN_VD = 5.0

#: Имена «не-стёкол» в каталогах (воздух).
PAIR_AIR_NAMES = ("AIR", "ВОЗДУХ")

#: Точек кривой дисперсии catalog.glass.range по умолчанию.
RANGE_STEPS_DEFAULT = 10

#: Диапазон λ проекта, мкм (валидация range).
WL_BOUNDS_UM = (0.2, 10.0)


#: Приоритет источников при объединении без фильтра source:
#: одноимённые стёкла разных каталогов не дают дублей строк
#: (дедупликация — первыми идут старшие источники).
SOURCE_PRIORITY = (SOURCE_GOST, SOURCE_FIL, SOURCE_AGF)


def _iter_entries(source=None):
    """(имя, {nd, vd, source}) по каталогам; source — фильтр.

    Без фильтра имена дедуплицируются по :data:`SOURCE_PRIORITY`
    (ГОСТ > .FIL > AGF): страницы catalog.glass.list не пересекаются
    по именам, одноимённые стёкла разных источников не дублируются.
    """
    def _by_source(src):
        if src == SOURCE_GOST:
            for key, (nd, vd, *_rest) in sorted(_gost_catalog().items()):
                yield key, {"nd": nd, "vd": vd, "source": SOURCE_GOST}
        elif src == SOURCE_FIL:
            for key, entry in sorted(_fil_catalog().items()):
                yield key, {"nd": entry.get("nd", 0.0),
                            "vd": entry.get("vd", 0.0),
                            "source": SOURCE_FIL}
        elif src == SOURCE_AGF:
            from catalog.glass_agf import get_glass
            for name in _agf_names():
                glass = get_glass(name)
                if glass is not None:
                    yield glass.name, {"nd": glass.nd, "vd": glass.vd,
                                       "source": SOURCE_AGF}

    if source is not None:
        yield from _by_source(source)
        return
    seen = set()
    for src in SOURCE_PRIORITY:
        for key, entry in _by_source(src):
            if key not in seen:
                seen.add(key)
                yield key, entry


def _sorted_entries(entries, order_by, descending):
    """Сортировка списка записей по ключу (имя — всегда по возрастанию)."""
    if order_by == "name":
        return sorted(entries, key=lambda kv: kv[0], reverse=descending)
    return sorted(entries, key=lambda kv: kv[1].get(order_by) or 0.0,
                  reverse=descending)


def _require_glass(name: str) -> dict:
    """Стекло из всех источников или not_found."""
    entry = lookup_glass(name)
    if entry is None:
        raise CommandError(
            ERR_NOT_FOUND,
            f"стекло {name!r} не найдено (ГОСТ / .FIL / AGF); "
            f"см. catalog.glass.search")
    return entry


def register(registry: Registry) -> None:
    """Зарегистрировать команды каталога стёкол (R500-4)."""

    # ============================================================
    # Списки и фильтры
    # ============================================================

    @registry.command(
        "catalog.glass.list", category="catalog",
        description="Постраничный список стёкол (имя, nd, Vd) по источнику",
        returns="{total, entries: [{name, nd, vd, source}]}",
        params=[
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
            Param("limit", type="int", default=GLASS_PAGE_DEFAULT,
                  help="строк в ответе"),
            Param("offset", type="int", default=0,
                  help="смещение страницы"),
            Param("order_by", choices=list(ORDER_KEYS), default="name",
                  help="ключ сортировки"),
            Param("descending", type="bool", default=False,
                  help="обратный порядок"),
        ])
    def catalog_glass_list(ctx, source, limit, offset, order_by,
                           descending):
        entries = _sorted_entries(list(_iter_entries(source)), order_by,
                                  descending)
        window = entries[max(0, offset):max(0, offset) + max(0, limit)]
        return {"total": len(entries),
                "entries": [{"name": k, **v} for k, v in window]}

    @registry.command(
        "catalog.glass.filter", category="catalog",
        description="Фильтр стёкол по диапазонам nd/Vd (подбор замен)",
        returns="{total, entries: [{name, nd, vd, source}]}",
        params=[
            Param("nd_min", type="float", help="нижняя граница nd"),
            Param("nd_max", type="float", help="верхняя граница nd"),
            Param("vd_min", type="float", help="нижняя граница Vd"),
            Param("vd_max", type="float", help="верхняя граница Vd"),
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
            Param("order_by", choices=list(ORDER_KEYS), default="vd",
                  help="ключ сортировки"),
            Param("descending", type="bool", default=False,
                  help="обратный порядок"),
            Param("limit", type="int", default=GLASS_PAGE_DEFAULT,
                  help="строк в ответе"),
        ])
    def catalog_glass_filter(ctx, nd_min, nd_max, vd_min, vd_max, source,
                             order_by, descending, limit):
        nd_lo, nd_hi = ND_RANGE
        vd_lo, vd_hi = VD_RANGE
        if nd_min is not None or nd_max is not None:
            nd_lo = nd_min if nd_min is not None else ND_RANGE[0]
            nd_hi = nd_max if nd_max is not None else ND_RANGE[1]
            if nd_lo > nd_hi:
                raise CommandError(ERR_INVALID_PARAM,
                                   "nd_min > nd_max")
        if vd_min is not None or vd_max is not None:
            vd_lo = vd_min if vd_min is not None else VD_RANGE[0]
            vd_hi = vd_max if vd_max is not None else VD_RANGE[1]
            if vd_lo > vd_hi:
                raise CommandError(ERR_INVALID_PARAM,
                                   "vd_min > vd_max")
        out = []
        for name, entry in _iter_entries(source):
            nd, vd = entry.get("nd", 0.0), entry.get("vd", 0.0)
            if nd_lo <= nd <= nd_hi and vd_lo <= vd <= vd_hi:
                out.append((name, entry))
        out = _sorted_entries(out, order_by, descending)
        return {"total": len(out),
                "entries": [{"name": k, **v}
                            for k, v in out[:max(0, limit)]]}

    @registry.command(
        "catalog.sources", category="catalog",
        description="Источники данных о стёклах: состав и охват",
        returns="по источникам: счётчик, диапазоны nd/Vd",
        params=[])
    def catalog_sources(ctx):
        stats = {}
        for source in (SOURCE_GOST, SOURCE_FIL, SOURCE_AGF):
            entries = list(_iter_entries(source))
            if not entries:
                stats[source] = {"count": 0}
                continue
            nds = [e["nd"] for _k, e in entries if e.get("nd")]
            vds = [e["vd"] for _k, e in entries if e.get("vd")]
            stats[source] = {
                "count": len(entries),
                "nd_min": min(nds) if nds else None,
                "nd_max": max(nds) if nds else None,
                "vd_min": min(vds) if vds else None,
                "vd_max": max(vds) if vds else None,
            }
        return {"sources": stats}

    @registry.command(
        "catalog.agf.status", category="catalog",
        description="AGF-каталог Zemax: доступность и число стёкол",
        returns="{available, count}",
        params=[])
    def catalog_agf_status(ctx):
        names = _agf_names()
        return {"available": bool(names), "count": len(names)}

    # ============================================================
    # Дисперсия и метрики одного стекла
    # ============================================================

    @registry.command(
        "catalog.glass.dispersion", category="catalog",
        description="n(λ) стекла на списке длин волн",
        returns="{name, source, rows: [{wl, n}]}",
        params=[
            Param("name", required=True, help="марка стекла"),
            Param("wavelengths", type="list", required=True,
                  help="список λ, мкм"),
        ])
    def catalog_glass_dispersion(ctx, name, wavelengths):
        entry = _require_glass(name)
        rows = []
        for wl in wavelengths:
            rows.append({"wl": float(wl),
                         "n": refractive_index_for(entry, float(wl))})
        return {"name": entry["name"], "source": entry["source"],
                "rows": rows}

    @registry.command(
        "catalog.glass.range", category="catalog",
        description="Кривая дисперсии n(λ) по диапазону",
        returns="{name, source, points: [{wl, n}], steps}",
        params=[
            Param("name", required=True, help="марка стекла"),
            Param("wl_min", type="float", default=0.4,
                  help="начало диапазона, мкм"),
            Param("wl_max", type="float", default=0.8,
                  help="конец диапазона, мкм"),
            Param("steps", type="int", default=RANGE_STEPS_DEFAULT,
                  help="число точек"),
        ])
    def catalog_glass_range(ctx, name, wl_min, wl_max, steps):
        entry = _require_glass(name)
        if not (WL_BOUNDS_UM[0] <= wl_min < wl_max <= WL_BOUNDS_UM[1]):
            raise CommandError(
                ERR_INVALID_PARAM,
                f"диапазон λ должен быть {WL_BOUNDS_UM[0]} ≤ wl_min < "
                f"wl_max ≤ {WL_BOUNDS_UM[1]} мкм")
        if steps < 2:
            raise CommandError(ERR_INVALID_PARAM, "steps ≥ 2")
        points = []
        for i in range(steps):
            wl = wl_min + (wl_max - wl_min) * i / (steps - 1)
            points.append({"wl": wl,
                           "n": refractive_index_for(entry, wl)})
        return {"name": entry["name"], "source": entry["source"],
                "steps": steps, "points": points}

    @registry.command(
        "catalog.glass.abbe", category="catalog",
        description="Число Аббе Vd расчётом n(λ) по формуле каталога "
                    "(F 486.1 / d 587.6 / C 656.3 нм)",
        returns="{name, nd, nF, nd_line, nC, vd_calc, vd_catalog}",
        params=[
            Param("name", required=True, help="марка стекла"),
        ])
    def catalog_glass_abbe(ctx, name):
        from utils.spectral_lines import spectral_line_by_name
        entry = _require_glass(name)
        wls = {key: spectral_line_by_name(key).wavelength_um
               for key in ("F", "d", "C")}
        nF = refractive_index_for(entry, wls["F"])
        nd = refractive_index_for(entry, wls["d"])
        nC = refractive_index_for(entry, wls["C"])
        vd_calc = (nd - 1.0) / (nF - nC)
        return {"name": entry["name"], "source": entry["source"],
                "nF": nF, "nd_line": nd, "nC": nC,
                "vd_calc": vd_calc, "vd_catalog": entry.get("vd")}

    @registry.command(
        "catalog.glass.compare", category="catalog",
        description="Сравнение двух стёкол: Δnd, ΔVd, n(λ)",
        returns="{a, b, d_nd, d_vd, n_a, n_b, d_n}",
        params=[
            Param("a", required=True, help="марка первого стекла"),
            Param("b", required=True, help="марка второго стекла"),
            Param("wl", type="float", default=0.58756,
                  help="λ для сравнения n, мкм"),
        ])
    def catalog_glass_compare(ctx, a, b, wl):
        ea, eb = _require_glass(a), _require_glass(b)
        n_a = refractive_index_for(ea, wl)
        n_b = refractive_index_for(eb, wl)
        return {"a": ea["name"], "b": eb["name"],
                "d_nd": eb["nd"] - ea["nd"],
                "d_vd": (eb["vd"] or 0.0) - (ea["vd"] or 0.0),
                "wl": wl, "n_a": n_a, "n_b": n_b, "d_n": n_b - n_a}

    @registry.command(
        "catalog.glass.similar", category="catalog",
        description="Соседние стёкла по (nd, Vd) — кандидаты на замену",
        returns="{name, matches: [{name, d_nd, d_vd, source}]}",
        params=[
            Param("name", required=True, help="марка стекла-эталона"),
            Param("nd_tol", type="float", default=0.01,
                  help="допуск по nd"),
            Param("vd_tol", type="float", default=3.0,
                  help="допуск по Vd"),
            Param("limit", type="int", default=GLASS_PAGE_DEFAULT,
                  help="максимум строк"),
        ])
    def catalog_glass_similar(ctx, name, nd_tol, vd_tol, limit):
        entry = _require_glass(name)
        nd0, vd0 = entry["nd"], entry.get("vd") or 0.0
        matches = []
        for other, e in _iter_entries():
            if other == entry["name"]:
                continue
            d_nd = (e.get("nd") or 0.0) - nd0
            d_vd = (e.get("vd") or 0.0) - vd0
            if abs(d_nd) <= nd_tol and abs(d_vd) <= vd_tol:
                matches.append({"name": other, "d_nd": d_nd,
                                "d_vd": d_vd, "source": e["source"]})
        matches.sort(key=lambda m: abs(m["d_nd"]) + abs(m["d_vd"]))
        return {"name": entry["name"],
                "matches": matches[:max(0, limit)]}

    @registry.command(
        "catalog.glass.valid", category="catalog",
        description="Применимость стекла на длине волны (диапазон "
                    "каталога + n)",
        returns="{name, wl, in_range, lam_min, lam_max, n}",
        params=[
            Param("name", required=True, help="марка стекла"),
            Param("wl", type="float", required=True, help="λ, мкм"),
        ])
    def catalog_glass_valid(ctx, name, wl):
        entry = _require_glass(name)
        lam_min, lam_max = entry.get("lam_min"), entry.get("lam_max")
        in_range = True
        if lam_min is not None and wl < lam_min:
            in_range = False
        if lam_max is not None and wl > lam_max:
            in_range = False
        return {"name": entry["name"], "wl": wl, "in_range": in_range,
                "lam_min": lam_min, "lam_max": lam_max,
                "n": refractive_index_for(entry, wl)}

    @registry.command(
        "catalog.glass.pairs", category="catalog",
        description="Пары крон+флинт для ахромата (ΔVd ≥ min_vd_diff)",
        returns="{pairs: [{crown, flint, vd_crown, vd_flint, d_vd}]}",
        params=[
            Param("name", help="марка одного из стёкол пары (фильтр)"),
            Param("min_vd_diff", type="float", default=PAIR_MIN_VD_DIFF,
                  help="минимальная разность Vd"),
            Param("limit", type="int", default=GLASS_PAGE_DEFAULT,
                  help="максимум пар"),
        ])
    def catalog_glass_pairs(ctx, name, min_vd_diff, limit):
        entries = {k: v for k, v in _iter_entries()}
        crowns = [(k, e) for k, e in entries.items()
                  if (e.get("vd") or 0.0) >= CROWN_MIN_VD]
        flints = [(k, e) for k, e in entries.items()
                  if (e.get("vd") or 0.0) >= FLINT_MIN_VD
                  and k.upper() not in PAIR_AIR_NAMES]
        pairs = []
        for crown, ec in crowns:
            for flint, ef in flints:
                d_vd = (ec.get("vd") or 0.0) - (ef.get("vd") or 0.0)
                if d_vd < min_vd_diff or crown == flint:
                    continue
                if name and name not in (crown, flint):
                    continue
                pairs.append({"crown": crown, "flint": flint,
                              "vd_crown": ec.get("vd"),
                              "vd_flint": ef.get("vd"), "d_vd": d_vd})
        pairs.sort(key=lambda p: -p["d_vd"])
        return {"min_vd_diff": min_vd_diff,
                "pairs": pairs[:max(0, limit)]}

    # ============================================================
    # Варианты ахромата (существующий дизайнер achromat.py)
    # ============================================================

    @registry.command(
        "catalog.achromat.options", category="catalog",
        description="Варианты ахроматического дублета по парам стёкол "
                    "(дизайнер achromat.design_achromat): радиусы/толщины",
        returns="{focal_length, options: [{crown, flint, radii, ok}]}",
        params=[
            Param("focal_length", type="float", required=True,
                  help="фокусное расстояние, мм"),
            Param("crown", help="крон (по умолчанию — перебор К8/БК10)"),
            Param("flint", help="флинт (по умолчанию — ТФ5/ТФ3/Ф4)"),
            Param("limit", type="int", default=6,
                  help="максимум вариантов"),
        ])
    def catalog_achromat_options(ctx, focal_length, crown, flint, limit):
        from achromat import GLASS_PAIRS, design_achromat
        wanted = [(crown or c, flint or f) for c, f in GLASS_PAIRS]
        options = []
        seen = set()
        for c, f in wanted:
            if (c, f) in seen:
                continue
            seen.add((c, f))
            try:
                system = design_achromat(focal_length, c, f)
            except Exception as exc:
                options.append({"crown": c, "flint": f, "ok": False,
                                "error": str(exc)[:120]})
                continue
            options.append({
                "crown": c, "flint": f, "ok": True,
                "radii": [s.radius for s in system.surfaces],
                "thicknesses": [s.thickness for s in system.surfaces],
                "efl": focal_length,
            })
        return {"focal_length": focal_length,
                "options": options[:max(0, limit)]}

    # ============================================================
    # Спектральные линии (utils/spectral_lines.py — единственный источник)
    # ============================================================

    @registry.command(
        "catalog.spectral.lines", category="spectral",
        description="Справочник стандартных спектральных линий "
                    "(λ, элемент, цвет)",
        returns="{count, lines: [{name, wavelength_nm, element, color}]}",
        params=[])
    def catalog_spectral_lines(ctx):
        from utils.spectral_lines import SPECTRAL_LINES
        return {"count": len(SPECTRAL_LINES),
                "lines": [{"name": ln.name,
                           "wavelength_nm": ln.wavelength_nm,
                           "wavelength_um": ln.wavelength_um,
                           "element": ln.element, "color": ln.color}
                          for ln in SPECTRAL_LINES]}

    @registry.command(
        "catalog.spectral.get", category="spectral",
        description="Спектральная линия по обозначению (F, d, C', t…)",
        returns="{name, wavelength_nm, element, color, text}",
        params=[
            Param("name", required=True, help="обозначение линии"),
        ])
    def catalog_spectral_get(ctx, name):
        from utils.spectral_lines import (format_spectral_line,
                                          spectral_line_by_name)
        line = spectral_line_by_name(name)
        if line is None:
            from utils.spectral_lines import SPECTRAL_LINES
            raise CommandError(
                ERR_NOT_FOUND,
                f"линии {name!r} нет; справочник: "
                f"{[ln.name for ln in SPECTRAL_LINES]}")
        return {"name": line.name, "wavelength_nm": line.wavelength_nm,
                "wavelength_um": line.wavelength_um,
                "element": line.element, "color": line.color,
                "text": format_spectral_line(line)}

    @registry.command(
        "catalog.spectral.nearest", category="spectral",
        description="Ближайшая стандартная линия к длине волны",
        returns="{wl, line: {...}, distance_nm}",
        params=[
            Param("wl", type="float", required=True,
                  help="длина волны, мкм"),
        ])
    def catalog_spectral_nearest(ctx, wl):
        from utils.spectral_lines import SPECTRAL_LINES
        best = min(SPECTRAL_LINES,
                   key=lambda ln: abs(ln.wavelength_um - wl))
        return {"wl": wl,
                "line": {"name": best.name,
                         "wavelength_nm": best.wavelength_nm,
                         "element": best.element, "color": best.color},
                "distance_nm": abs(best.wavelength_um - wl) * 1000.0}

    @registry.command(
        "catalog.spectral.element", category="spectral",
        description="Линии по элементу-источнику (Hg, H, He, Na, Cd, K, Cs)",
        returns="{element, lines: [...]}",
        params=[
            Param("element", required=True, help="символ элемента"),
        ])
    def catalog_spectral_element(ctx, element):
        from utils.spectral_lines import SPECTRAL_LINES
        wanted = element.strip().capitalize()
        lines = [{"name": ln.name, "wavelength_nm": ln.wavelength_nm,
                  "color": ln.color}
                 for ln in SPECTRAL_LINES if ln.element == wanted]
        if not lines:
            raise CommandError(
                ERR_NOT_FOUND,
                f"элемента {element!r} нет в справочнике; доступны: "
                f"{sorted({ln.element for ln in SPECTRAL_LINES})}")
        return {"element": wanted, "lines": lines}

    @registry.command(
        "catalog.spectral.match", category="spectral",
        description="Рабочие λ системы ↔ стандартные линии (ближайшие, "
                    "допуск справочника)",
        returns="{rows: [{wl, line, distance_nm, matched}]}",
        params=system_source_params())
    def catalog_spectral_match(ctx, file, system, lbo_index, lbo_name):
        from utils.spectral_lines import (SPECTRAL_LINES,
                                          WL_MATCH_TOL_NM)
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for w in sys_obj.wavelengths:
            best = min(SPECTRAL_LINES,
                       key=lambda ln: abs(ln.wavelength_um - w.value))
            distance_nm = abs(best.wavelength_um - w.value) * 1000.0
            rows.append({"wl": w.value, "wl_name": w.name,
                         "line": best.name,
                         "distance_nm": distance_nm,
                         "matched": distance_nm <= WL_MATCH_TOL_NM})
        return {"tolerance_nm": WL_MATCH_TOL_NM, "rows": rows}

    # ============================================================
    # Данные карты стёкол (headless)
    # ============================================================

    @registry.command(
        "diagram.data", category="diagram",
        description="Точки карты стёкол n–V: {name, nd, vd, тип, цвет} "
                    "(данные для построения/подсветки)",
        returns="{count, glasses: [{name, nd, vd, type, color, highlight}]}",
        params=[
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — ГОСТ+.FIL)"),
            Param("highlight", type="list",
                  help="имена стёкол системы для пометки"),
            Param("limit", type="int",
                  help="максимум точек (по умолчанию — все)"),
        ])
    def diagram_data(ctx, source, highlight, limit):
        from glass_diagram import get_glass_color, get_glass_type_label
        wanted = {str(h).upper() for h in (highlight or [])}
        glasses = []
        for name, entry in _iter_entries(source):
            glasses.append({
                "name": name, "nd": entry.get("nd"),
                "vd": entry.get("vd"),
                "type": get_glass_type_label(name),
                "color": get_glass_color(name),
                "highlight": name.upper() in wanted,
            })
        if limit:
            glasses = glasses[:max(0, limit)]
        return {"count": len(glasses),
                "highlighted": sum(1 for g in glasses if g["highlight"]),
                "glasses": glasses}

    @registry.command(
        "diagram.types", category="diagram",
        description="Типы стёкол (К/БК/ТК/ТФ/…) и их представительство "
                    "в каталогах",
        returns="{types: [{type, count}]}",
        params=[
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
        ])
    def diagram_types(ctx, source):
        from glass_diagram import get_glass_type_label
        counts = {}
        for name, _entry in _iter_entries(source):
            label = get_glass_type_label(name) or "прочие"
            counts[label] = counts.get(label, 0) + 1
        types = [{"type": k, "count": v}
                 for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
        return {"types": types, "count": len(types)}
