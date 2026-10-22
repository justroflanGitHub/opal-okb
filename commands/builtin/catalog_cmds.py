"""
OPAL-OKB — Команды catalog.*: стёкла (ГОСТ/.FIL/AGF) и библиотека систем.

Цепочка источников стёкол: ГОСТ (catalog/glass_catalog.py) → полный
каталог .FIL (catalog/glass_catalog_full.py) → AGF Zemax
(catalog/glass_agf.py, опционален — файла может не быть на стенде).
"""
from typing import Optional

from commands.base import ERR_NOT_FOUND, Param, CommandError
from commands.registry import Registry

SOURCE_GOST = "gost"
SOURCE_FIL = "fil"
SOURCE_AGF = "agf"


def _gost_catalog() -> dict:
    """Каталог ГОСТ (имя → (nd, vd, coeffs, λmin, λmax))."""
    from catalog.glass_catalog import GLASS_CATALOG
    return GLASS_CATALOG


def _fil_catalog() -> dict:
    """Полный каталог .FIL (имя → {nd, vd, coeffs, ...})."""
    from catalog.glass_catalog_full import list_glasses
    return list_glasses()


def _agf_lookup(name: str):
    """AGF-стекло по имени (латиница/русский алиас) или None.

    Файл OPAL.AGF на стенде может отсутствовать — тогда каталог пуст.
    """
    try:
        from catalog.glass_agf import get_glass
        return get_glass(name)
    except Exception:
        return None


def _agf_names():
    """Имена AGF-стёкол (пустой список, если файла нет)."""
    try:
        from catalog.glass_agf import get_glass_list
        return get_glass_list()
    except Exception:
        return []


def lookup_glass(name: str) -> Optional[dict]:
    """Найти стекло во всех источниках.

    Returns:
        ``{"name", "source", "nd", "vd", "coeffs", "lam_min", "lam_max"}``
        или ``None``.
    """
    upper = name.upper().strip()

    for key, entry in _gost_catalog().items():
        if key.upper() == upper:
            nd, vd, coeffs, lam_min, lam_max = entry
            return {"name": key, "source": SOURCE_GOST, "nd": nd,
                    "vd": vd, "coeffs": list(coeffs),
                    "lam_min": lam_min, "lam_max": lam_max}

    for key, entry in _fil_catalog().items():
        if key.upper() == upper:
            return {"name": key, "source": SOURCE_FIL,
                    "nd": entry.get("nd", 0.0), "vd": entry.get("vd", 0.0),
                    "coeffs": list(entry.get("coeffs", [])),
                    "lam_min": entry.get("lam_min"),
                    "lam_max": entry.get("lam_max")}

    agf = _agf_lookup(name)
    if agf is not None:
        ld = agf.ld or [None, None]
        return {"name": agf.name, "source": SOURCE_AGF, "nd": agf.nd,
                "vd": agf.vd, "coeffs": list(agf.cd or []),
                "lam_min": ld[0], "lam_max": ld[1] if len(ld) > 1 else None}
    return None


def refractive_index_for(entry: dict, wl: float) -> float:
    """n(λ) для найденного стекла — по формуле его источника."""
    if entry["source"] == SOURCE_AGF:
        from catalog.glass_agf import compute_n
        return compute_n(entry["name"], wl)
    from domain.calculations import refractive_index
    return refractive_index(entry["name"], wl)


def _library_summary() -> dict:
    """Библиотека систем (catalog/library.py) в JSON-совместимом виде."""
    from catalog.library import build_library
    library = build_library()
    categories = []
    for cat_name, entries in library.items():
        items = []
        for e in entries:
            item = {"name": e.get("name", "")}
            if e.get("file"):
                item["file"] = e["file"]
            if e.get("generator"):
                item["generator"] = e["generator"]
            if e.get("lbo_path"):
                item["lbo_path"] = e["lbo_path"]
                item["num_systems"] = e.get("num_systems")
            items.append(item)
        categories.append({"name": cat_name, "entries": items,
                           "count": len(items)})
    return {"categories": categories,
            "total": sum(c["count"] for c in categories)}


def register(registry: Registry) -> None:
    """Зарегистрировать все команды catalog.*."""

    @registry.command(
        "catalog.info", category="catalog",
        description="Источники данных: число стёкол по каталогам + библиотека",
        returns="счётчики стёкол (gost/fil/agf) и библиотеки систем",
        params=[])
    def catalog_info(ctx):
        return {
            "glasses": {
                SOURCE_GOST: len(_gost_catalog()),
                SOURCE_FIL: len(_fil_catalog()),
                SOURCE_AGF: len(_agf_names()),
            },
            "library": _library_summary()["total"],
        }

    @registry.command(
        "catalog.glass.get", category="catalog",
        description="Стекло по марке: nd, vd, коэффициенты дисперсии (+n(λ))",
        returns="данные стекла (+n при указании wl)",
        params=[
            Param("name", required=True, help="марка стекла (К8, ТФ1, TK16…)"),
            Param("wl", type="float",
                  help="длина волны, мкм — добавить n(λ)"),
        ])
    def catalog_glass_get(ctx, name, wl):
        entry = lookup_glass(name)
        if entry is None:
            raise CommandError(
                ERR_NOT_FOUND,
                f"стекло {name!r} не найдено (ГОСТ / .FIL / AGF); "
                f"см. catalog.glass.search")
        if wl is not None:
            entry["wl"] = wl
            entry["n"] = refractive_index_for(entry, wl)
        return entry

    @registry.command(
        "catalog.glass.search", category="catalog",
        description="Поиск стёкол по подстроке марки во всех каталогах",
        returns="список совпадений {name, source, nd, vd}",
        params=[
            Param("query", required=True, help="подстрока марки (К8, ТФ, BK…)"),
            Param("limit", type="int", default=50,
                  help="максимум записей в ответе"),
        ])
    def catalog_glass_search(ctx, query, limit):
        q = query.lower()
        matches = []

        for key, entry in sorted(_gost_catalog().items()):
            if q in key.lower():
                matches.append({"name": key, "source": SOURCE_GOST,
                                "nd": entry[0], "vd": entry[1]})
        for key, entry in sorted(_fil_catalog().items()):
            if q in key.lower():
                matches.append({"name": key, "source": SOURCE_FIL,
                                "nd": entry.get("nd", 0.0),
                                "vd": entry.get("vd", 0.0)})
        for name in _agf_names():
            if q in name.lower():
                agf = _agf_lookup(name)
                if agf is not None:
                    matches.append({"name": agf.name, "source": SOURCE_AGF,
                                    "nd": agf.nd, "vd": agf.vd})

        total = len(matches)
        return {"matches": matches[:max(0, limit)], "total": total,
                "truncated": total > limit}

    @registry.command(
        "catalog.library.list", category="catalog",
        description="Библиотека систем: генераторы, .OPJ архив, .LBO библиотеки",
        returns="категории библиотеки с записями",
        params=[])
    def catalog_library_list(ctx):
        return _library_summary()
