"""
OPAL-OKB — Пакет R500-18 «reserve ч.1»: хвосты карты стёкол,
каталог-документация и остатки формул FORMULAS.md.

Три семейства (префиксы выбраны по пинам tests/: категория ``diagram``
не запинена — П4 уже расширял её ``diagram.data/types`` поверх пина
``tests/test_commands_opt.py`` (там только список OPT_COMMANDS на
наличие); ``calc``/``catalog`` — категории Волны 1, расширялись П4/П6
со smoke-записями в ``tests/test_commands_builtin.py``):

- ``diagram.*`` — покрытие каталога на карте n–Vd сеткой, статистика
  типов (плотность/центроиды), крон/флинт по зонам Vd, границы карты
  (bbox + стандартное окно + выбросы), стёкла системы на карте,
  выборка стекла по позиции (ближайшее к nd/Vd);
- ``catalog.stats/sources.compare/glass.multi/availability`` — свод
  по источникам, пересечения имён (AGF — по русским алиасам),
  стёкла в нескольких источниках, доступность марки + синонимы;
- ``calc.*`` — не обёрнутые verified-формулы FORMULAS.md/документации
  порта: продольные аберрации в дптр от выходного зрачка (§3),
  поперечные в «гр.мнсек» из центра выходного зрачка (§3), зрачковые
  координаты зон (§3), метка Tg′×100 TABOC2 (§3), запуск осевого
  веера (§3/GFIX P6), множитель печати λ(z) E2 (§3, движок
  ``edge2_print_lambda``), кривизна опорной сферы мнимого изображения
  (§2/GFIX R1, ``virtual_wave_kappa``), κ(λ)/C_eff ГОЭ (§5),
  replay-условие δ = rec₀·λ₀/λ (§5), ГРИП по допускам СКW/СКR
  (ANALIZE §5.3), конверсия дефокуса мм↔волны (PARAXIAL_DEFOCUS_
  FACTOR); ``units.print.table`` — таблица единиц печати ближний/
  дальний тип (REVERSE_NZR §19.2).

Движки не дублируются: итератор каталогов и фильтр воздуха —
``glass_ext_cmds._iter_entries``/``PAIR_AIR_NAMES``, типы/цвета —
``glass_diagram``, алиасы AGF — ``catalog.glass_agf``, единицы —
``analysis.units``, λ(z)/κ(λ) — ``analysis.aberrations``,
пятна/волновой фронт — ``analysis.aberrations`` + команда
``zern.wavefront`` (через ``registry.execute`` внутри ``register``,
как sweep), конверсия дефокуса — хелпер ``adv_ext_cmds``
(PARAXIAL_DEFOCUS_FACTOR). Физика не выдумывается: каждая формула —
с указанием раздела FORMULAS.md/досье.
"""
import math

from commands.base import (
    ERR_INVALID_PARAM,
    ERR_NOT_FOUND,
    Param,
    CommandError,
    sanitize_json,
)
from commands.registry import Registry
from commands.systemio import resolve_system, system_source_params

from commands.builtin.catalog_cmds import (
    SOURCE_AGF,
    SOURCE_FIL,
    SOURCE_GOST,
    _agf_names,
    _fil_catalog,
    _gost_catalog,
)
from commands.builtin.glass_ext_cmds import PAIR_AIR_NAMES, _iter_entries

# TINY/finite — общие хелперы пакетов R500 (правило №1).
from commands.builtin._r500_common import TINY
from commands.builtin._r500_common import finite as _finite

# ============================================================
# Именованные константы пакета
# ============================================================

#: Стандартное окно карты стёкол (оси plot_glass_diagram, glass_diagram).
VD_VIEW = (20.0, 80.0)
ND_VIEW = (1.45, 1.85)

#: Ячеек сетки покрытия по умолчанию (диаграмма.coverage).
VD_BINS_DEFAULT = 6
ND_BINS_DEFAULT = 8

#: Ячеек в «топе» покрытия и имён в примере.
COVERAGE_TOP_CELLS_DEFAULT = 5
COVERAGE_NAMES_PER_CELL = 5

#: Ширина зоны Vd для крон/флинт и сводных полос (диаграмма Аббе).
VD_BAND_STEP_DEFAULT = 10.0

#: Типы семейства кронов (ГОСТ-префиксы марок).
CROWN_TYPES = ("К", "БК", "ТК", "ЛК", "ФК", "СТК")

#: Типы семейства флинтов.
FLINT_TYPES = ("Ф", "ТФ", "БФ", "ЛФ", "ОФ")

#: Семейства по типу марки.
FAMILY_CROWN = "crown"
FAMILY_FLINT = "flint"
FAMILY_OTHER = "other"

#: Метка неклассифицированных марок (сгенерированные имена .FIL).
TYPE_OTHER_LABEL = "прочие"

#: Фильтр «реальных» стёкол: воздух/спецсреды имеют nd ≤ 1, vd ≤ 0.
REAL_ND_MIN = 1.0
REAL_VD_MIN = 0.0

#: Строк в ответе catalog.sources.compare / catalog.availability.
COMPARE_SAMPLE_DEFAULT = 10

#: Максимум строк catalog.glass.multi по умолчанию.
MULTI_LIMIT_DEFAULT = 50

#: Минимум источников в catalog.glass.multi.
MULTI_MIN_SOURCES = 2

#: Ближайших стёкол в diagram.pick по умолчанию.
PICK_LIMIT_DEFAULT = 10

#: Семейства печати λ-закона E2 (EDGE2_PRINT_LAMBDA, §3).
EDGE2_KINDS = ("прод", "попер", "Tg")

#: Система банка κ-таблиц мнимого изображения (GFIX R1).
VIRTUAL_KAPPA_SYSTEM = "OPTICS#1"

#: λ записи ГОЭ HeNe (FORMULAS.md §5, GTIE00).
GOE_RECORD_WL_UM = 0.6328

#: Критерии ГРИП (ANALIZE §5.3): СКW — волновой (λ), СКR — пятно (мм).
CRITERION_WAVE_RMS = "wave_rms"
CRITERION_SPOT_RMS = "spot_rms"
CRITERIA = (CRITERION_WAVE_RMS, CRITERION_SPOT_RMS)

#: Полудиапазон скана дефокуса по критериям, мм.
DEFOCUS_SPOT_RANGE_DEFAULT = 1.0
DEFOCUS_WAVE_RANGE_DEFAULT = 0.3

#: Точек скана дефокуса (нечётное: центр — плоскость Гаусса).
DEFOCUS_STEPS_DEFAULT = 21
DEFOCUS_STEPS_MIN = 3

#: Лучей пятна / решётка волнового фронта для критериев ГРИП.
SPOT_RAYS_DEFAULT = 64
WAVE_GRID_DEFAULT = 32

#: Таблица единиц печати OPAL «ближний/дальний тип» — REVERSE_NZR
#: §19.2 / ANALIZE.DOC:659–680 (пул юнитов OPALA.EXE 0x44500–0x445B8);
#: каноническое место описания — шапка analysis/units.py.
PRINT_UNITS_TABLE = (
    ("поперечные аберрации", "мм", "гр.мнсек"),
    ("продольные аберрации", "мм", "дптр"),
    ("Z'm / Z's", "мм", "дптр (от выходного зрачка)"),
    ("зрачковые координаты", "tg·100 / tg'·100", "H ЗР / H' ЗР (мм)"),
    ("сдвиг DS', ЧКХ", "мм, лин/мм", "дптр, лин/мин"),
    ("предмет/изображение", "мм", "гр.мнсек (½ углового поля)"),
)


# ============================================================
# Общие хелперы пакета
# ============================================================

def _is_real_glass(name: str, entry: dict) -> bool:
    """Реальное стекло: не воздух/спецсреда, nd > 1, Vd > 0."""
    if name.upper() in PAIR_AIR_NAMES:
        return False
    nd = entry.get("nd") or 0.0
    vd = entry.get("vd") or 0.0
    return nd > REAL_ND_MIN and vd > REAL_VD_MIN


def _real_entries(source=None):
    """(имя, {nd, vd, source}) только реальные стёкла (без воздуха)."""
    for name, entry in _iter_entries(source):
        if _is_real_glass(name, entry):
            yield name, entry


def _type_label(name: str, source: str = None) -> str:
    """Тип марки (К/БК/ТФ/…); для AGF — по русскому алиасу.

    Латинские имена AGF (TK16) не матчатся русскими префиксами
    :func:`glass_diagram.get_glass_type_label` — тип берётся по
    алиасу из ``catalog.glass_agf._agf_to_russian``.
    """
    from glass_diagram import get_glass_type_label
    label = get_glass_type_label(name)
    if not label and source == SOURCE_AGF:
        from catalog.glass_agf import _agf_to_russian
        alias = _agf_to_russian(name)
        if alias:
            label = get_glass_type_label(alias)
    return label


def _family_of(type_label: str) -> str:
    """Семейство по типу марки: crown / flint / other."""
    if type_label in CROWN_TYPES:
        return FAMILY_CROWN
    if type_label in FLINT_TYPES:
        return FAMILY_FLINT
    return FAMILY_OTHER


def _type_bucket(name: str, source: str = None) -> str:
    """Тип марки для сводок: '' → «прочие»."""
    return _type_label(name, source) or TYPE_OTHER_LABEL


def _lin_grid(lo: float, hi: float, bins: int) -> list:
    """Равномерные границы bins ячеек [lo, hi] (bins+1 значений)."""
    return [lo + (hi - lo) * i / bins for i in range(bins + 1)]


def _vd_bands(step: float) -> list:
    """Полосы Vd шириной step по окну карты (последняя — до 80)."""
    edges = []
    v = VD_VIEW[0]
    while v < VD_VIEW[1] - TINY:
        edges.append((v, min(v + step, VD_VIEW[1])))
        v += step
    return edges


def _std(values: list) -> float:
    """СКО (смещённое) по списку."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _gost_hit(name: str):
    """(имя_как_в_каталоге, nd, vd) по ГОСТ или None."""
    upper = name.upper().strip()
    for key, entry in _gost_catalog().items():
        if key.upper() == upper:
            return {"name": key, "nd": entry[0], "vd": entry[1]}
    return None


def _fil_hit(name: str):
    """(имя, nd, vd) по .FIL или None."""
    upper = name.upper().strip()
    for key, entry in _fil_catalog().items():
        if key.upper() == upper:
            return {"name": key, "nd": entry.get("nd", 0.0),
                    "vd": entry.get("vd", 0.0)}
    return None


def _agf_hit(name: str):
    """(латиница, nd, vd, алиас) по AGF или None (файла может не быть)."""
    from catalog.glass_agf import _agf_to_russian, get_glass
    glass = get_glass(name)
    if glass is None:
        return None
    return {"name": glass.name, "nd": glass.nd, "vd": glass.vd,
            "alias": _agf_to_russian(glass.name)}


def _source_hits(name: str) -> dict:
    """Вхождения марки по источникам: {source: {name, nd, vd}}."""
    hits = {}
    gost = _gost_hit(name)
    if gost is not None:
        hits[SOURCE_GOST] = gost
    fil = _fil_hit(name)
    if fil is not None:
        hits[SOURCE_FIL] = fil
    agf = _agf_hit(name)
    if agf is not None:
        hits[SOURCE_AGF] = {k: agf[k] for k in ("name", "nd", "vd")}
        if agf["alias"]:
            hits[SOURCE_AGF]["alias"] = agf["alias"]
    return hits


def _canonical_maps() -> dict:
    """Канонизированные карты реальных стёкол: {source: {ключ: hit}}.

    Ключ — имя в верхнем регистре (для AGF предпочитается русский
    алиас — сквозная сопоставимость с ГОСТ/.FIL); hit —
    ``{name, nd, vd}``.
    """
    maps = {SOURCE_GOST: {}, SOURCE_FIL: {}, SOURCE_AGF: {}}
    for name, entry in _iter_entries(SOURCE_GOST):
        if _is_real_glass(name, entry):
            maps[SOURCE_GOST][name.upper()] = {
                "name": name, "nd": entry.get("nd"), "vd": entry.get("vd")}
    for name, entry in _iter_entries(SOURCE_FIL):
        if _is_real_glass(name, entry):
            maps[SOURCE_FIL][name.upper()] = {
                "name": name, "nd": entry.get("nd"), "vd": entry.get("vd")}
    for name in _agf_names():
        hit = _agf_hit(name)
        if hit is None or not _is_real_glass(name, hit):
            continue
        entry = {"name": hit["name"], "nd": hit["nd"], "vd": hit["vd"]}
        maps[SOURCE_AGF][hit["alias"].upper() if hit["alias"]
                         else hit["name"].upper()] = entry
    return maps


def _waves_per_mm(system, wl: float) -> float:
    """Дефокус (волны на краю зрачка) на мм осевого сдвига.

    Хелпер П14 ``adv_ext_cmds._defocus_waves_per_mm`` (формула
    W = PARAXIAL_DEFOCUS_FACTOR·Δz·NA′²/λ, analysis/advanced) —
    единая точка конверсии, здесь не дублируется.
    """
    from commands.builtin.adv_ext_cmds import _defocus_waves_per_mm
    return _defocus_waves_per_mm(system, wl)


def _defocus_grid(defocus_range: float, num_points: int) -> list:
    """Равномерная сетка ±range (нечётное число точек ≥ 3)."""
    if defocus_range <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "defocus_range должен быть > 0")
    if num_points < DEFOCUS_STEPS_MIN:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"steps ≥ {DEFOCUS_STEPS_MIN} (нечётное: центр — Гаусс)")
    n = num_points if num_points % 2 == 1 else num_points + 1
    return [-defocus_range + 2.0 * defocus_range * i / (n - 1)
            for i in range(n)]


def _crossing(d_lo: float, v_lo: float, d_hi: float, v_hi: float,
              threshold: float) -> float:
    """Точка пересечения порога между двумя узлами (линейно)."""
    if abs(v_lo - v_hi) < TINY:
        return d_hi
    frac = (v_lo - threshold) / (v_lo - v_hi)
    return d_lo + frac * (d_hi - d_lo)


def _criteria_bounds(grid: list, values: list, threshold: float) -> dict:
    """Границы интервала ≤ threshold вокруг минимума (ANALIZE §5.3).

    Возвращает ``{near, far, best, min_value, satisfied, clipped_near,
    clipped_far}`` (линейная интерполяция пересечений; None — если
    порог не достигнут нигде).
    """
    best_i = min(range(len(values)), key=lambda i: values[i])
    best = float(grid[best_i])
    min_value = float(values[best_i])
    if min_value > threshold:
        return {"near": None, "far": None, "best": best,
                "min_value": min_value, "satisfied": False,
                "clipped_near": False, "clipped_far": False}
    i = best_i
    while i > 0 and values[i - 1] <= threshold:
        i -= 1
    clipped_near = i == 0 and values[0] <= threshold
    if i == 0:
        near = float(grid[0])
    else:
        near = _crossing(grid[i - 1], values[i - 1],
                         grid[i], values[i], threshold)
    j = best_i
    while j < len(values) - 1 and values[j + 1] <= threshold:
        j += 1
    clipped_far = j == len(values) - 1 and values[-1] <= threshold
    if j == len(values) - 1:
        far = float(grid[-1])
    else:
        far = _crossing(grid[j], values[j],
                        grid[j + 1], values[j + 1], threshold)
    return {"near": near, "far": far, "best": best,
            "min_value": min_value, "satisfied": True,
            "clipped_near": clipped_near, "clipped_far": clipped_far}


def _zones_arg(zones) -> list:
    """Непустой список зон (числа)."""
    if not isinstance(zones, (list, tuple)) or not zones:
        raise CommandError(ERR_INVALID_PARAM,
                           "zones: нужен непустой список чисел")
    try:
        return [float(z) for z in zones]
    except (TypeError, ValueError) as exc:
        raise CommandError(ERR_INVALID_PARAM,
                           "zones: все элементы — числа") from exc


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать команды пакета R500-18 (reserve ч.1)."""

    # ----------------------------------------------------------
    # diagram.* — карта стёкол n–Vd (данные, не картинка)
    # ----------------------------------------------------------

    @registry.command(
        "diagram.coverage", category="diagram",
        description="Покрытие каталога на карте n–Vd: гистограмма "
                    "плотности по сетке окна просмотра, занятость "
                    "ячеек и самые населённые зоны",
        returns="{total, in_view, outside_view, vd_edges, nd_edges, "
                "cells: [{i, j, vd_from, vd_to, nd_from, nd_to, count}], "
                "occupied, occupancy_pct, top: [{i, j, count, names}]}",
        params=[
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
            Param("vd_bins", type="int", default=VD_BINS_DEFAULT,
                  help=f"ячеек по Vd (по умолчанию {VD_BINS_DEFAULT})"),
            Param("nd_bins", type="int", default=ND_BINS_DEFAULT,
                  help=f"ячеек по nd (по умолчанию {ND_BINS_DEFAULT})"),
            Param("top_cells", type="int",
                  default=COVERAGE_TOP_CELLS_DEFAULT,
                  help="сколько ячеек в «топе» (0 — не считать)"),
        ])
    def diagram_coverage(ctx, source, vd_bins, nd_bins, top_cells):
        if vd_bins < 1 or nd_bins < 1:
            raise CommandError(ERR_INVALID_PARAM, "vd_bins/nd_bins ≥ 1")
        vd_edges = _lin_grid(VD_VIEW[0], VD_VIEW[1], vd_bins)
        nd_edges = _lin_grid(ND_VIEW[0], ND_VIEW[1], nd_bins)
        cells = [[0] * nd_bins for _ in range(vd_bins)]
        names = [[[] for _ in range(nd_bins)] for _ in range(vd_bins)]
        total = in_view = 0
        for name, entry in _real_entries(source):
            total += 1
            nd, vd = entry["nd"], entry["vd"]
            if not (VD_VIEW[0] <= vd <= VD_VIEW[1]
                    and ND_VIEW[0] <= nd <= ND_VIEW[1]):
                continue
            in_view += 1
            i = min(int((vd - VD_VIEW[0]) / (VD_VIEW[1] - VD_VIEW[0])
                        * vd_bins), vd_bins - 1)
            j = min(int((nd - ND_VIEW[0]) / (ND_VIEW[1] - ND_VIEW[0])
                        * nd_bins), nd_bins - 1)
            cells[i][j] += 1
            names[i][j].append(name)
        occupied = sum(1 for row in cells for c in row if c > 0)
        cell_rows = [
            {"i": i, "j": j,
             "vd_from": vd_edges[i], "vd_to": vd_edges[i + 1],
             "nd_from": nd_edges[j], "nd_to": nd_edges[j + 1],
             "count": cells[i][j]}
            for i in range(vd_bins) for j in range(nd_bins)]
        top = []
        if top_cells:
            flat = sorted(((cells[i][j], i, j)
                           for i in range(vd_bins)
                           for j in range(nd_bins)), reverse=True)
            for count, i, j in flat[:max(0, top_cells)]:
                if count <= 0:
                    break
                top.append({"i": i, "j": j, "count": count,
                            "names": names[i][j][:COVERAGE_NAMES_PER_CELL]})
        return {
            "source": source or "all", "total": total,
            "in_view": in_view, "outside_view": total - in_view,
            "view": {"vd": list(VD_VIEW), "nd": list(ND_VIEW)},
            "vd_edges": vd_edges, "nd_edges": nd_edges,
            "cells": cell_rows, "occupied": occupied,
            "occupancy_pct": (100.0 * occupied / (vd_bins * nd_bins)
                              if vd_bins * nd_bins else 0.0),
            "top": top,
        }

    @registry.command(
        "diagram.type.stats", category="diagram",
        description="Диаграмма Аббе по типам: плотность каждого типа — "
                    "счётчик, центроид (nd, Vd), разброс и диапазоны",
        returns="{total, types: [{type, family, count, nd_mean, nd_std, "
                "vd_mean, vd_std, nd_min, nd_max, vd_min, vd_max}], "
                "unclassified}",
        params=[
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
        ])
    def diagram_type_stats(ctx, source):
        by_type = {}
        total = 0
        for name, entry in _real_entries(source):
            total += 1
            bucket = _type_bucket(name, entry.get("source"))
            by_type.setdefault(bucket, {"nd": [], "vd": []})
            by_type[bucket]["nd"].append(entry["nd"])
            by_type[bucket]["vd"].append(entry["vd"])
        rows = []
        for bucket, vals in by_type.items():
            nds, vds = vals["nd"], vals["vd"]
            rows.append({
                "type": bucket,
                "family": _family_of(
                    bucket if bucket != TYPE_OTHER_LABEL else ""),
                "count": len(nds),
                "nd_mean": sum(nds) / len(nds),
                "nd_std": _std(nds),
                "vd_mean": sum(vds) / len(vds),
                "vd_std": _std(vds),
                "nd_min": min(nds), "nd_max": max(nds),
                "vd_min": min(vds), "vd_max": max(vds),
            })
        rows.sort(key=lambda r: (-r["count"], r["type"]))
        return {"source": source or "all", "total": total,
                "types": rows,
                "unclassified": len(
                    by_type.get(TYPE_OTHER_LABEL, {"nd": []})["nd"])}

    @registry.command(
        "diagram.crown.flint", category="diagram",
        description="Кроны против флинтов по зонам Vd: счётчики семейств "
                    "в полосах Vd, диапазоны семейств и граница "
                    "смешанных зон (карта n–Vd)",
        returns="{vd_step, bands: [{vd_from, vd_to, crown, flint, other}], "
                "family_stats: {crown/flint/other: {count, vd_min, "
                "vd_max}}, mixed_bands, vd_overlap, outside}",
        params=[
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
            Param("vd_step", type="float", default=VD_BAND_STEP_DEFAULT,
                  help=f"ширина полосы Vd (по умолчанию "
                       f"{VD_BAND_STEP_DEFAULT:g})"),
        ])
    def diagram_crown_flint(ctx, source, vd_step):
        if not (0 < vd_step <= VD_VIEW[1] - VD_VIEW[0]):
            raise CommandError(
                ERR_INVALID_PARAM,
                f"vd_step: 0 < step ≤ {VD_VIEW[1] - VD_VIEW[0]:g}")
        bands = [{"vd_from": lo, "vd_to": hi, "crown": 0, "flint": 0,
                  "other": 0} for lo, hi in _vd_bands(vd_step)]
        stats = {FAMILY_CROWN: {"vd": []}, FAMILY_FLINT: {"vd": []},
                 FAMILY_OTHER: {"vd": []}}
        outside = 0
        for name, entry in _real_entries(source):
            family = _family_of(_type_label(name, entry.get("source")))
            stats[family]["vd"].append(entry["vd"])
            vd = entry["vd"]
            if not VD_VIEW[0] <= vd <= VD_VIEW[1]:
                outside += 1
                continue
            for band in bands:
                if band["vd_from"] <= vd <= band["vd_to"]:
                    band[family] += 1
                    break
        family_stats = {}
        for family, vals in stats.items():
            vds = vals["vd"]
            if not vds:
                family_stats[family] = {"count": 0}
                continue
            family_stats[family] = {"count": len(vds),
                                    "vd_min": min(vds),
                                    "vd_max": max(vds)}
        mixed = [{"vd_from": b["vd_from"], "vd_to": b["vd_to"]}
                 for b in bands if b["crown"] > 0 and b["flint"] > 0]
        crown_vds = stats[FAMILY_CROWN]["vd"]
        flint_vds = stats[FAMILY_FLINT]["vd"]
        overlap = 0.0
        if crown_vds and flint_vds:
            overlap = max(0.0, min(max(crown_vds), max(flint_vds))
                          - max(min(crown_vds), min(flint_vds)))
        return {"source": source or "all", "vd_step": vd_step,
                "bands": bands, "family_stats": family_stats,
                "mixed_bands": mixed, "vd_overlap": overlap,
                "outside": outside}

    @registry.command(
        "diagram.bbox", category="diagram",
        description="Границы диапазона nd/Vd каталога (bbox реальных "
                    "стёкол), стандартное окно карты и выбросы за окно",
        returns="{total, bbox: {nd_min, nd_max, vd_min, vd_max}, view, "
                "outside_view, outliers: [{name, nd, vd, source}]}",
        params=[
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
        ])
    def diagram_bbox(ctx, source):
        nds, vds = [], []
        all_entries = []
        for name, entry in _real_entries(source):
            nds.append(entry["nd"])
            vds.append(entry["vd"])
            all_entries.append((name, entry))
        if not nds:
            raise CommandError(
                ERR_NOT_FOUND,
                "в выбранном источнике нет реальных стёкол "
                "(или источник недоступен)")
        outliers = [
            {"name": name, "nd": entry["nd"], "vd": entry["vd"],
             "source": entry["source"]}
            for name, entry in all_entries
            if not (VD_VIEW[0] <= entry["vd"] <= VD_VIEW[1]
                    and ND_VIEW[0] <= entry["nd"] <= ND_VIEW[1])]
        outliers.sort(key=lambda o: (-abs(o["vd"] - VD_VIEW[0]
                                          if o["vd"] < VD_VIEW[0]
                                          else o["vd"] - VD_VIEW[1])
                                     if not VD_VIEW[0] <= o["vd"]
                                     <= VD_VIEW[1] else 0.0))
        return {
            "source": source or "all", "total": len(nds),
            "bbox": {"nd_min": min(nds), "nd_max": max(nds),
                     "vd_min": min(vds), "vd_max": max(vds)},
            "view": {"vd": list(VD_VIEW), "nd": list(ND_VIEW)},
            "outside_view": len(outliers),
            "outliers": outliers[:COMPARE_SAMPLE_DEFAULT],
        }

    @registry.command(
        "diagram.system", category="diagram",
        description="Стёкла системы на карте n–Vd: для каждой марки — "
                    "nd/Vd, тип, семейство, источники; свод — сколько "
                    "стёкол системы в каких типах/семействах/зонах Vd",
        returns="{glasses: [{glass, found, nd, vd, type, family, sources, "
                "vd_band}], summary: {total, found, not_found, by_type, "
                "by_family, by_vd_band, outside_view}}",
        params=system_source_params())
    def diagram_system(ctx, file, system, lbo_index, lbo_name):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        seen = []
        for surf in sys_obj.surfaces:
            glass = (surf.glass or "").strip()
            if (glass and glass.upper() not in PAIR_AIR_NAMES
                    and glass not in seen):
                seen.append(glass)
        bands = _vd_bands(VD_BAND_STEP_DEFAULT)
        rows = []
        by_type, by_family, by_vd_band = {}, {}, []
        band_counts = [0] * len(bands)
        outside = not_found = 0
        for glass in seen:
            hits = _source_hits(glass)
            row = {"glass": glass, "found": bool(hits),
                   "nd": None, "vd": None, "type": TYPE_OTHER_LABEL,
                   "family": FAMILY_OTHER, "sources": sorted(hits),
                   "vd_band": None}
            if hits:
                first_src = next((s for s in (SOURCE_GOST, SOURCE_FIL,
                                              SOURCE_AGF) if s in hits),
                                 None)
                first = hits[first_src]
                row["nd"], row["vd"] = first["nd"], first["vd"]
                row["type"] = _type_bucket(first["name"], first_src)
                row["family"] = _family_of(
                    row["type"] if row["type"] != TYPE_OTHER_LABEL else "")
                by_type[row["type"]] = by_type.get(row["type"], 0) + 1
                by_family[row["family"]] = \
                    by_family.get(row["family"], 0) + 1
                if row["vd"] is not None and VD_VIEW[0] <= row["vd"] \
                        <= VD_VIEW[1]:
                    for k, (lo, hi) in enumerate(bands):
                        if lo <= row["vd"] <= hi:
                            band_counts[k] += 1
                            row["vd_band"] = {"vd_from": lo, "vd_to": hi}
                            break
                else:
                    outside += 1
            else:
                not_found += 1
            rows.append(row)
        for k, (lo, hi) in enumerate(bands):
            if band_counts[k]:
                by_vd_band.append({"vd_from": lo, "vd_to": hi,
                                   "count": band_counts[k]})
        return {"glasses": rows,
                "summary": {"total": len(rows),
                            "found": len(rows) - not_found,
                            "not_found": not_found,
                            "by_type": by_type, "by_family": by_family,
                            "by_vd_band": by_vd_band,
                            "outside_view": outside}}

    @registry.command(
        "diagram.pick", category="diagram",
        description="Выборка стекла по позиции на карте: ближайшие к "
                    "заданной точке (nd, Vd) марки — евклидова метрика, "
                    "нормированная на окно карты",
        returns="{nd, vd, count, nearest: {...}, matches: [{name, nd, vd, "
                "d_nd, d_vd, dist, type, source}]}",
        params=[
            Param("nd", type="float", required=True,
                  help="показатель преломления nd точки"),
            Param("vd", type="float", required=True,
                  help="число Аббе Vd точки"),
            Param("source", choices=[SOURCE_GOST, SOURCE_FIL, SOURCE_AGF],
                  help="каталог (по умолчанию — все)"),
            Param("limit", type="int", default=PICK_LIMIT_DEFAULT,
                  help="сколько ближайших вернуть"),
        ])
    def diagram_pick(ctx, nd, vd, source, limit):
        nd_span = ND_VIEW[1] - ND_VIEW[0]
        vd_span = VD_VIEW[1] - VD_VIEW[0]
        matches = []
        for name, entry in _real_entries(source):
            d_nd = entry["nd"] - nd
            d_vd = entry["vd"] - vd
            dist = math.sqrt((d_nd / nd_span) ** 2 + (d_vd / vd_span) ** 2)
            matches.append({"name": name, "nd": entry["nd"],
                            "vd": entry["vd"], "d_nd": d_nd,
                            "d_vd": d_vd, "dist": dist,
                            "type": _type_bucket(name, entry["source"]),
                            "source": entry["source"]})
        matches.sort(key=lambda m: (m["dist"], m["name"]))
        window = matches[:max(0, limit)]
        return {"nd": nd, "vd": vd, "count": len(matches),
                "nearest": window[0] if window else None,
                "matches": window}

    # ----------------------------------------------------------
    # catalog.* — свод источников и доступность марок
    # ----------------------------------------------------------

    @registry.command(
        "catalog.stats", category="catalog",
        description="Свод по всем источникам стёкол: счётчики всего/"
                    "реальных/отфильтрованных, объединение имён, "
                    "стёкла в нескольких источниках, уникальные",
        returns="{sources: {gost/fil/agf: {total, real, filtered}}, "
                "union, multi_source, unique: {источник: count}}",
        params=[])
    def catalog_stats(ctx):
        maps = _canonical_maps()
        sources = {}
        for src in (SOURCE_GOST, SOURCE_FIL, SOURCE_AGF):
            entries = list(_iter_entries(src))
            real = sum(1 for name, e in entries if _is_real_glass(name, e))
            sources[src] = {"total": len(entries), "real": real,
                            "filtered": len(entries) - real}
        keys = {src: set(maps[src]) for src in maps}
        union = set().union(*keys.values()) if keys else set()
        multi = set()
        for key in union:
            if sum(1 for src in keys if key in keys[src]) >= 2:
                multi.add(key)
        unique = {src: sum(1 for key in keys[src]
                           if sum(1 for s2 in keys if key in keys[s2]) == 1)
                  for src in keys}
        return {"sources": sources, "union": len(union),
                "multi_source": len(multi), "unique": unique}

    @registry.command(
        "catalog.sources.compare", category="catalog",
        description="Пересечения имён стёкол между источниками "
                    "(ГОСТ/.FIL/AGF; AGF — по русским алиасам): пары, "
                    "общее пересечение, образцы",
        returns="{counts, pairwise: {gost_fil/gost_agf/fil_agf: {count, "
                "sample}}, all_three: {count, sample}, union, unique}",
        params=[
            Param("limit", type="int", default=COMPARE_SAMPLE_DEFAULT,
                  help="размер образцов-списков"),
        ])
    def catalog_sources_compare(ctx, limit):
        maps = _canonical_maps()
        keys = {src: set(maps[src]) for src in maps}
        counts = {src: len(keys[src]) for src in keys}

        def _inter(a, b):
            return sorted(keys[a] & keys[b])

        def _pair(a, b):
            common = _inter(a, b)
            return {"count": len(common),
                    "sample": common[:max(0, limit)]}
        three = sorted(keys[SOURCE_GOST] & keys[SOURCE_FIL]
                       & keys[SOURCE_AGF])
        union = set().union(*keys.values()) if keys else set()
        unique = {src: sum(1 for key in keys[src]
                           if sum(1 for s2 in keys if key in keys[s2]) == 1)
                  for src in keys}
        return {
            "counts": counts,
            "pairwise": {"gost_fil": _pair(SOURCE_GOST, SOURCE_FIL),
                         "gost_agf": _pair(SOURCE_GOST, SOURCE_AGF),
                         "fil_agf": _pair(SOURCE_FIL, SOURCE_AGF)},
            "all_three": {"count": len(three),
                          "sample": three[:max(0, limit)]},
            "union": len(union), "unique": unique,
            "agf_alias_matched": True,
        }

    @registry.command(
        "catalog.glass.multi", category="catalog",
        description="Стёкла, доступные сразу в нескольких источниках "
                    "(ГОСТ/.FIL/AGF, сопоставление по имени/алиасу): "
                    "nd/Vd каждого вхождения и разброс nd между "
                    "источниками",
        returns="{total, entries: [{name, sources: {источник: {name, "
                "nd, vd}}, sources_count, d_nd, d_vd}]}",
        params=[
            Param("min_sources", type="int", default=MULTI_MIN_SOURCES,
                  help="минимум источников (2 или 3)"),
            Param("limit", type="int", default=MULTI_LIMIT_DEFAULT,
                  help="максимум строк"),
        ])
    def catalog_glass_multi(ctx, min_sources, limit):
        if min_sources not in (2, 3):
            raise CommandError(ERR_INVALID_PARAM,
                               "min_sources: 2 или 3")
        maps = _canonical_maps()
        by_name = {}
        for src in (SOURCE_GOST, SOURCE_FIL, SOURCE_AGF):
            for key, hit in maps[src].items():
                by_name.setdefault(key, {})[src] = hit
        entries = []
        for key, sources in sorted(by_name.items()):
            if len(sources) < min_sources:
                continue
            nds = [h["nd"] for h in sources.values() if h["nd"]]
            vds = [h["vd"] for h in sources.values() if h["vd"]]
            preferred = next((sources[s] for s in (SOURCE_GOST, SOURCE_FIL,
                                                   SOURCE_AGF)
                              if s in sources), None)
            entries.append({
                "name": preferred["name"],
                "sources": {src: {"name": h["name"], "nd": h["nd"],
                                  "vd": h["vd"]}
                            for src, h in sorted(sources.items())},
                "sources_count": len(sources),
                "d_nd": (max(nds) - min(nds)) if len(nds) > 1 else 0.0,
                "d_vd": (max(vds) - min(vds)) if len(vds) > 1 else 0.0,
            })
        entries.sort(key=lambda e: (-e["sources_count"], e["name"]))
        return {"total": len(entries),
                "entries": entries[:max(0, limit)]}

    @registry.command(
        "catalog.availability", category="catalog",
        description="Доступность марки стекла: в каких источниках есть "
                    "(ГОСТ/.FIL/AGF), nd/Vd каждого вхождения и синонимы "
                    "(латиница ↔ русская транслитерация AGF)",
        returns="{query, canonical, primary, sources: [{source, name, "
                "nd, vd, alias}], synonyms}",
        params=[
            Param("name", required=True, help="марка стекла"),
        ])
    def catalog_availability(ctx, name):
        hits = _source_hits(name)
        if not hits:
            raise CommandError(
                ERR_NOT_FOUND,
                f"стекло {name!r} не найдено ни в одном источнике "
                f"(ГОСТ / .FIL / AGF); см. catalog.glass.search")
        ordered = [src for src in (SOURCE_GOST, SOURCE_FIL, SOURCE_AGF)
                   if src in hits]
        primary = ordered[0]
        canonical = hits[primary]["name"]
        synonyms = []
        for src in ordered:
            if src == SOURCE_AGF:
                hit = hits[src]
                if hit.get("alias") and hit["alias"] != canonical.upper():
                    synonyms.append(hit["alias"])
                if hit["name"].upper() != canonical.upper():
                    synonyms.append(hit["name"])
        if name.upper() != canonical.upper() and name not in synonyms:
            synonyms.insert(0, name)
        return {"query": name, "canonical": canonical, "primary": primary,
                "sources": [{"source": src,
                             "name": hits[src]["name"],
                             "nd": hits[src]["nd"],
                             "vd": hits[src]["vd"],
                             "alias": hits[src].get("alias")}
                            for src in ordered],
                "synonyms": synonyms}

    # ----------------------------------------------------------
    # calc.* — формулы FORMULAS.md, не обёрнутые ранее
    # ----------------------------------------------------------

    @registry.command(
        "calc.aber.dioptre", category="calc",
        description="Продольная аберрация в диоптриях от плоскости "
                    "ВЫХОДНОГО ЗРАЧКА: дптр = 1000/L′_зоны − 1000/L′_паракс "
                    "(FORMULAS.md §3, GVERIFY §2.2; L′=0 → пустая ячейка "
                    "печати OPAL — null)",
        returns="{L_zone_mm, L_parax_mm, zone_dpt, parax_dpt, dioptres}",
        params=[
            Param("L_zone_mm", type="float", required=True,
                  help="отрезок зонального луча от выходного зрачка, мм"),
            Param("L_parax_mm", type="float", required=True,
                  help="параксиальный отрезок от выходного зрачка, мм"),
        ])
    def calc_aber_dioptre(ctx, L_zone_mm, L_parax_mm):
        from analysis.units import mm_to_dioptres
        L_zone = _finite(L_zone_mm, "L_zone_mm")
        L_parax = _finite(L_parax_mm, "L_parax_mm")
        zone_dpt = mm_to_dioptres(L_zone)
        parax_dpt = mm_to_dioptres(L_parax)
        dioptres = None
        if zone_dpt is not None and parax_dpt is not None:
            dioptres = zone_dpt - parax_dpt
        return {"L_zone_mm": L_zone, "L_parax_mm": L_parax,
                "zone_dpt": zone_dpt, "parax_dpt": parax_dpt,
                "dioptres": dioptres}

    @registry.command(
        "calc.aber.grminsec", category="calc",
        description="Поперечная аберрация в мере «гр.мнсек»: угол "
                    "atan2(Δy, L′) из ЦЕНТРА выходного зрачка на точку "
                    "луча в плоскости Гаусса + печать DD.MMSS (FORMULAS.md"
                    " §3, OPALDIS OD3)",
        returns="{dy_mm, L_mm, angle_deg, grminsec, print}",
        params=[
            Param("dy_mm", type="float", required=True,
                  help="поперечная аберрация Δy, мм"),
            Param("L_mm", type="float", required=True,
                  help="отрезок от центра выходного зрачка, мм"),
        ])
    def calc_aber_grminsec(ctx, dy_mm, L_mm):
        from analysis.units import deg_to_gms, grminsec
        dy = _finite(dy_mm, "dy_mm")
        length = _finite(L_mm, "L_mm")
        angle_deg = math.degrees(math.atan2(dy, length))
        return {"dy_mm": dy, "L_mm": length, "angle_deg": angle_deg,
                "angle_rad": math.atan2(dy, length),
                "grminsec": grminsec(angle_deg),
                "print": deg_to_gms(angle_deg)}

    @registry.command(
        "calc.pupil.zone", category="calc",
        description="Зрачковые координаты зоны (FORMULAS.md §3, REVERSE_"
                    "NZR): дальний предмет H ЗР = зона·Ax (мм); ближний "
                    "предмет H = 100·tg(arcsin(зона·NA)) в единицах tg×100",
        returns="{ax_mm, na, rows: [{zone, h_far_mm, h_near_tg100}]}",
        params=[
            Param("zones", type="list", required=True,
                  help="зоны зрачка (доли полуапертуры)"),
            Param("ax_mm", type="float",
                  help="полувысота зрачка Ax, мм (дальний предмет)"),
            Param("na", type="float",
                  help="числовая апертура предмета (ближний предмет)"),
        ])
    def calc_pupil_zone(ctx, zones, ax_mm, na):
        from analysis.units import pupil_h_mm, tg100
        zones_v = _zones_arg(zones)
        if ax_mm is None and na is None:
            raise CommandError(ERR_INVALID_PARAM,
                               "задайте ax_mm (дальний) или na (ближний)")
        if na is not None and not (0.0 < na < 1.0):
            raise CommandError(ERR_INVALID_PARAM,
                               "na: 0 < NA < 1 (синус угла)")
        rows = []
        for zone in zones_v:
            h_near = None
            if na is not None:
                if abs(zone) > 1.0 + TINY or abs(zone * na) > 1.0:
                    raise CommandError(
                        ERR_INVALID_PARAM,
                        f"зона {zone}: |зона·NA| ≤ 1 (зона — доля "
                        f"полуапертуры)")
                h_near = tg100(math.degrees(math.asin(zone * na)))
            rows.append({"zone": zone,
                         "h_far_mm": (pupil_h_mm(zone, ax_mm)
                                      if ax_mm is not None else None),
                         "h_near_tg100": h_near})
        return {"ax_mm": ax_mm, "na": na, "rows": sanitize_json(rows)}

    @registry.command(
        "calc.tgprime.label", category="calc",
        description="Метка Tg′×100 таблицы TABOC2 (FORMULAS.md §3): "
                    "дальнее изображение — |H′ ЗР| в мм; ближнее — "
                    "−100·tg u′ (единицы tg′×100)",
        returns="{h_out_mm, u_prime_deg, far_label_mm, near_label_tg100}",
        params=[
            Param("h_out_mm", type="float",
                  help="высота зонального луча в выходном зрачке, мм "
                       "(дальний тип изображения)"),
            Param("u_prime_deg", type="float",
                  help="выходной наклон зонального луча u′, град "
                       "(ближний тип изображения)"),
        ])
    def calc_tgprime_label(ctx, h_out_mm, u_prime_deg):
        from analysis.units import tg100
        if h_out_mm is None and u_prime_deg is None:
            raise CommandError(ERR_INVALID_PARAM,
                               "задайте h_out_mm (дальний тип) или "
                               "u_prime_deg (ближний тип)")
        return {
            "h_out_mm": h_out_mm, "u_prime_deg": u_prime_deg,
            "far_label_mm": (abs(_finite(h_out_mm, "h_out_mm"))
                             if h_out_mm is not None else None),
            "near_label_tg100": (-tg100(_finite(u_prime_deg,
                                                "u_prime_deg"))
                                 if u_prime_deg is not None else None),
        }

    @registry.command(
        "calc.fan.launch", category="calc",
        description="Запуск лучей осевого веера (FORMULAS.md §3, GFIX "
                    "P6): дальний предмет — по высоте зона·Ax параллельно "
                    "оси; ближний — по углу arcsin(зона·NA) от точки "
                    "предмета (Ax = sin NA)",
        returns="{ax_mm, na, rows: [{zone, far_y_mm, near_u_deg}]}",
        params=[
            Param("zones", type="list", required=True,
                  help="зоны зрачка (доли полуапертуры)"),
            Param("ax_mm", type="float",
                  help="полувысота зрачка Ax, мм (дальний предмет)"),
            Param("na", type="float",
                  help="числовая апертура предмета (ближний предмет)"),
        ])
    def calc_fan_launch(ctx, zones, ax_mm, na):
        from analysis.units import pupil_h_mm
        zones_v = _zones_arg(zones)
        if ax_mm is None and na is None:
            raise CommandError(ERR_INVALID_PARAM,
                               "задайте ax_mm (дальний) или na (ближний)")
        if na is not None and not (0.0 < na < 1.0):
            raise CommandError(ERR_INVALID_PARAM,
                               "na: 0 < NA < 1 (синус угла)")
        rows = []
        for zone in zones_v:
            near_u = None
            if na is not None:
                if abs(zone) > 1.0 + TINY or abs(zone * na) > 1.0:
                    raise CommandError(
                        ERR_INVALID_PARAM,
                        f"зона {zone}: |зона·NA| ≤ 1 (зона — доля "
                        f"полуапертуры)")
                near_u = math.degrees(math.asin(zone * na))
            rows.append({"zone": zone,
                         "far_y_mm": (pupil_h_mm(zone, ax_mm)
                                      if ax_mm is not None else None),
                         "near_u_deg": near_u})
        return {"ax_mm": ax_mm, "na": na, "rows": sanitize_json(rows)}

    @registry.command(
        "calc.edge2.lambda", category="calc",
        description="Множитель печати λ(z) = 1 − (q0 + q1·z²)·z² "
                    "ближнего предмета E2 (FORMULAS.md §3, REVERSE_OPALDIS"
                    " §4.3(vii); q-пары банка — analysis.aberrations."
                    "EDGE2_PRINT_LAMBDA, верифицировано золотыми "
                    "прогонами)",
        returns="{system, kind, q0, q1, rows: [{zone, lambda}]}",
        params=[
            Param("system", required=True,
                  choices=sorted(("OBEKTIV", "OKULAR", "OPTICS#1")),
                  help="система банка E2"),
            Param("kind", required=True, choices=list(EDGE2_KINDS),
                  help="семейство печати (прод/попер/Tg)"),
            Param("zones", type="list", required=True,
                  help="зоны зрачка z (доли полуапертуры)"),
        ])
    def calc_edge2_lambda(ctx, system, kind, zones):
        from analysis.aberrations import EDGE2_PRINT_LAMBDA, edge2_print_lambda
        table = EDGE2_PRINT_LAMBDA.get(system, {})
        q = table.get(kind)
        if q is None:
            raise CommandError(
                ERR_NOT_FOUND,
                f"в банке E2 нет семейства {kind!r} для системы "
                f"{system!r}; доступно: {sorted(table)}")
        rows = []
        for zone in _zones_arg(zones):
            rows.append({"zone": zone,
                         "lambda": edge2_print_lambda(table, kind, zone)})
        return {"system": system, "kind": kind, "q0": q[0], "q1": q[1],
                "rows": rows}

    @registry.command(
        "calc.virtual.kappa", category="calc",
        description="Кривизна опорной сферы волновых мнимого изображения "
                    "(FORMULAS.md §2, GFIX R1): (κ0, κ2) для λ из банка "
                    "VIRTUAL_WAVE_KAPPA + радиус якоря 1/κ0",
        returns="{wl, system, kappa0, kappa2, r_ref_mm, available_wls}",
        params=[
            Param("wl", type="float", required=True,
                  help="длина волны, мкм (допуск банка 2e-3)"),
        ])
    def calc_virtual_kappa(ctx, wl):
        from analysis.aberrations import (VIRTUAL_WAVE_KAPPA,
                                          virtual_wave_kappa)
        table = VIRTUAL_WAVE_KAPPA[VIRTUAL_KAPPA_SYSTEM]
        pair = virtual_wave_kappa(table, wl)
        if pair is None:
            raise CommandError(
                ERR_NOT_FOUND,
                f"λ={wl} нет в κ-таблице системы {VIRTUAL_KAPPA_SYSTEM!r} "
                f"(допуск 2e-3 мкм); доступно: "
                f"{sorted(table)}")
        return {"wl": wl, "system": VIRTUAL_KAPPA_SYSTEM,
                "kappa0": pair[0], "kappa2": pair[1],
                "r_ref_mm": (1.0 / pair[0] if abs(pair[0]) > TINY
                             else None),
                "available_wls": sorted(table)}

    @registry.command(
        "calc.goe.kappa", category="calc",
        description="Закон эффективной кривизны ГОЭ (FORMULAS.md §5, "
                    "REVERSE_GOE_MODEL §3): κ(λ) = κ0 + κ1·(λ − λ0) и "
                    "C_eff(λ) = κ(λ)·C (по умолчанию — пин GTIE00, "
                    "domain.calculations.GOE_KAPPA_LAW)",
        returns="{wl, k0, k1, wl0, kappa, curvature_c, c_eff, r_eff_mm}",
        params=[
            Param("wl", type="float", required=True,
                  help="длина волны расчёта, мкм"),
            Param("k0", type="float",
                  help="κ_design (по умолчанию — пин GTIE00)"),
            Param("k1", type="float",
                  help="dκ/dλ, 1/мкм (по умолчанию — пин GTIE00)"),
            Param("wl0", type="float",
                  help="λ записи, мкм (по умолчанию — пин GTIE00)"),
            Param("curvature_c", type="float",
                  help="кривизна поверхности C, 1/мм (для C_eff и R_eff)"),
        ])
    def calc_goe_kappa(ctx, wl, k0, k1, wl0, curvature_c):
        from domain.calculations import GOE_KAPPA_LAW
        kappa0 = k0 if k0 is not None else GOE_KAPPA_LAW[0]
        kappa1 = k1 if k1 is not None else GOE_KAPPA_LAW[1]
        wl_design = wl0 if wl0 is not None else GOE_KAPPA_LAW[2]
        if wl <= 0:
            raise CommandError(ERR_INVALID_PARAM, "wl > 0")
        kappa = kappa0 + kappa1 * (wl - wl_design)
        c_eff = r_eff = None
        if curvature_c is not None:
            c_eff = curvature_c * kappa
            if abs(c_eff) > TINY:
                r_eff = 1.0 / c_eff
        return {"wl": wl, "k0": kappa0, "k1": kappa1, "wl0": wl_design,
                "kappa": kappa, "curvature_c": curvature_c,
                "c_eff": c_eff, "r_eff_mm": r_eff}

    @registry.command(
        "calc.goe.replay", category="calc",
        description="Replay-условие ГОЭ (FORMULAS.md §5): фаза решётки "
                    "на длине волны расчёта δ = rec₀·λ₀/λ — "
                    "дифракционная добавка ∝ λ0/λ (REVERSE_GOE_MODEL: "
                    "отклонение ±0.1342 = rec[0]·λ0/λ у GTIE00)",
        returns="{rec0, lambda0, wl, delta}",
        params=[
            Param("rec0", type="float", required=True,
                  help="записанная фаза решётки rec₀ (на λ0)"),
            Param("wl", type="float", required=True,
                  help="длина волны расчёта, мкм"),
            Param("lambda0", type="float", default=GOE_RECORD_WL_UM,
                  help=f"λ записи, мкм (по умолчанию HeNe "
                       f"{GOE_RECORD_WL_UM:g})"),
        ])
    def calc_goe_replay(ctx, rec0, wl, lambda0):
        rec0 = _finite(rec0, "rec0")
        wl = _finite(wl, "wl")
        lambda0 = _finite(lambda0, "lambda0")
        if wl <= 0 or lambda0 <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "wl и lambda0 должны быть > 0")
        return {"rec0": rec0, "lambda0": lambda0, "wl": wl,
                "delta": rec0 * lambda0 / wl}

    @registry.command(
        "calc.depth.criteria", category="calc",
        description="Границы глубины резко изображаемого пространства по "
                    "допускам критериев (ANALIZE §5.3: «положения "
                    "индивидуальных границ глубины резкости из условия, "
                    "чтобы не превышать максимально допустимых значений "
                    "СКW (СКR)»): скан дефокуса, интервал где критерий "
                    "≤ допуска",
        returns="{criterion, max_value, unit, wl, field_y, defocus_range, "
                "steps, waves_per_mm, best_focus_mm, min_value, near_mm, "
                "far_mm, depth_mm, satisfied, clipped_near, clipped_far, "
                "rows: [{defocus_mm, value}]}",
        params=system_source_params() + [
            Param("criterion", required=True, choices=list(CRITERIA),
                  help="СКW (wave_rms, допуск в λ) или СКR (spot_rms, "
                       "допуск в мм)"),
            Param("max_value", type="float", required=True,
                  help="максимально допустимое значение критерия"),
            Param("defocus_range", type="float",
                  help="полудиапазон скана, мм (по умолчанию 1.0 для "
                       "пятна, 0.3 для волнового)"),
            Param("steps", type="int", default=DEFOCUS_STEPS_DEFAULT,
                  help=f"точек скана ≥ {DEFOCUS_STEPS_MIN} (нечётное)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная)"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей пятна (СКR)"),
            Param("grid_size", type="int", default=WAVE_GRID_DEFAULT,
                  help="решётка зрачка (СКW)"),
        ])
    def calc_depth_criteria(ctx, file, system, lbo_index, lbo_name,
                            criterion, max_value, defocus_range, steps,
                            field_y, wl, num_rays, grid_size):
        from optics_utils import get_primary_wl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if max_value <= 0:
            raise CommandError(ERR_INVALID_PARAM, "max_value > 0")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        if defocus_range is None:
            defocus_range = (DEFOCUS_WAVE_RANGE_DEFAULT
                             if criterion == CRITERION_WAVE_RMS
                             else DEFOCUS_SPOT_RANGE_DEFAULT)
        grid = _defocus_grid(defocus_range, steps)

        if criterion == CRITERION_SPOT_RMS:
            from analysis.aberrations import (compute_rms_spot_xy,
                                              compute_spot_diagram_at_defocus)

            def _value(d):
                spots = compute_spot_diagram_at_defocus(
                    sys_obj, wl=wl_eff, num_rays=num_rays,
                    field_y=field_y, defocus_mm=d)
                return compute_rms_spot_xy(spots)["rms_total"]
            waves_per_mm = None
            unit = "mm"
        else:
            # СКW: карта W по зрачку (analysis.zernike) + параксиальный
            # дефокус w(ρ) = W_край·ρ² (модель analysis.advanced.
            # compute_psf: w_defocus = PARAXIAL_DEFOCUS_FACTOR·Δz·NA′²·ρ²,
            # W_край/мм — хелпер П14). Пистон карты не искажается
            # (в отличие от defocus_offset zern.wavefront — это OPL-мм).
            import numpy as np
            from analysis.zernike import compute_wavefront_map_2d
            waves_per_mm = _waves_per_mm(sys_obj, wl_eff)
            wavefront, coords, mask = compute_wavefront_map_2d(
                sys_obj, wl=wl_eff, field_y=field_y, grid_size=grid_size)
            inside = np.asarray(mask) > 0
            grid_x, grid_y = np.meshgrid(coords, coords)
            r2_inside = (grid_x ** 2 + grid_y ** 2)[inside]
            w_inside = np.asarray(wavefront)[inside]

            def _value(d):
                shifted = w_inside + waves_per_mm * d * r2_inside
                return float(np.sqrt(np.mean(shifted ** 2)))
            unit = "wl"

        values = [_value(d) for d in grid]
        bounds = _criteria_bounds(grid, values, max_value)
        depth = (bounds["far"] - bounds["near"]
                 if bounds["near"] is not None else 0.0)
        return {
            "criterion": criterion, "max_value": max_value, "unit": unit,
            "wl": wl_eff, "field_y": field_y,
            "defocus_range": defocus_range, "steps": len(grid),
            "waves_per_mm": waves_per_mm,
            "best_focus_mm": bounds["best"],
            "min_value": bounds["min_value"],
            "near_mm": bounds["near"], "far_mm": bounds["far"],
            "depth_mm": depth, "satisfied": bounds["satisfied"],
            "clipped_near": bounds["clipped_near"],
            "clipped_far": bounds["clipped_far"],
            "rows": sanitize_json([{"defocus_mm": d, "value": v}
                                   for d, v in zip(grid, values)]),
        }

    @registry.command(
        "calc.defocus.convert", category="calc",
        description="Конверсия дефокуса мм ↔ волны на краю зрачка: "
                    "W = PARAXIAL_DEFOCUS_FACTOR·Δz·NA′²/λ (формула "
                    "analysis/advanced.compute_psf; хелпер П14 — "
                    "adv_ext_cmds._defocus_waves_per_mm)",
        returns="{wl, na_image, waves_per_mm, defocus_mm, waves}",
        params=system_source_params() + [
            Param("defocus_mm", type="float",
                  help="осевой сдвиг плоскости, мм"),
            Param("waves", type="float",
                  help="дефокус на краю зрачка, волны"),
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная)"),
        ])
    def calc_defocus_convert(ctx, file, system, lbo_index, lbo_name,
                             defocus_mm, waves, wl):
        from optics_utils import get_primary_wl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if defocus_mm is None and waves is None:
            raise CommandError(ERR_INVALID_PARAM,
                               "задайте defocus_mm или waves")
        wl_eff = wl if wl is not None else get_primary_wl(sys_obj)
        wpm = _waves_per_mm(sys_obj, wl_eff)
        if wpm <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "нулевой масштаб дефокуса (NA′ = 0)")
        out_mm = out_waves = None
        if defocus_mm is not None:
            out_mm = _finite(defocus_mm, "defocus_mm")
            out_waves = out_mm * wpm
        if waves is not None:
            w = _finite(waves, "waves")
            out_waves = w
            if out_mm is None:
                out_mm = w / wpm
        na_img = math.sqrt(2.0 * wpm * wl_eff * 1e-3)
        return {"wl": wl_eff, "na_image": na_img, "waves_per_mm": wpm,
                "defocus_mm": out_mm, "waves": out_waves}

    # ----------------------------------------------------------
    # units.* — таблица единиц печати
    # ----------------------------------------------------------

    @registry.command(
        "units.print.table", category="units",
        description="Таблица единиц печати OPAL «ближний/дальний тип» "
                    "(REVERSE_NZR §19.2 / ANALIZE.DOC:659–680): какие "
                    "единицы печатает OPAL для величин анализа",
        returns="{count, rows: [{quantity, near, far}], source}",
        params=[])
    def units_print_table(ctx):
        rows = [{"quantity": q, "near": near, "far": far}
                for q, near, far in PRINT_UNITS_TABLE]
        return {"count": len(rows), "rows": rows,
                "source": "REVERSE_NZR §19.2 (пул юнитов OPALA.EXE "
                          "0x44500–0x445B8; см. analysis/units.py)"}
