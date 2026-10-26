# -*- coding: utf-8 -*-
"""Команды R500-18 «reserve ч.1» (commands/builtin/reserve_cmds.py):
хвосты карты стёкол (diagram.*), каталог-документация (catalog.*) и
остатки формул FORMULAS.md (calc.*) + таблица единиц печати — smoke
КАЖДОЙ команды пакета + сверки с прямыми вызовами движков.

Префиксы: категория ``diagram`` НЕ запинена (П4 уже добавлял
``diagram.data/types`` — пин Волны 3 ``tests/test_commands_opt.py``
проверяет только наличие OPT_COMMANDS); ``calc``/``catalog`` —
covered-категории Волны 1 (их smoke-записи живут в
``tests/test_commands_builtin.py``, здесь — полные прогоны пакета);
``units`` — категория П5 без пинов состава.

Демо-система — .json команд Волны 1 (.opj — для поленезависимых
команд); живая система контекста REPL — ``_resv_probe`` (без смены
текущей, drop после теста). AGF-зависимые проверки — условный skip:
OPAL.AGF лежит вне репо (локальные данные). Тесты .FIL-каталога —
маркер ``requires_fil`` (конвенция conftest).
"""
import json
import math
import os

import pytest

from commands import CommandContext, default_registry
from commands.base import CommandError
from commands.builtin import reserve_cmds
from optics_engine import OpticalSystem, Surface, Wavelength

from tests.conftest import requires_fil


def _agf_available() -> bool:
    """OPAL.AGF на стенде (файл вне репо — в CI его нет)."""
    try:
        from catalog.glass_agf import get_glass_list
        return len(get_glass_list()) > 0
    except Exception:
        return False


requires_agf = pytest.mark.skipif(
    not _agf_available(),
    reason="нет OPAL.AGF (локальные данные, не в git)")


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    # контракт: результат строго JSON-сериализуем
    json.dumps(result.data, ensure_ascii=False, allow_nan=False)
    return result.data


def fail(name, args, code):
    """Выполнить команду, ожидая ошибку с данным кодом."""
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error
    return result.error


def _no_agf(monkeypatch):
    """CI-режим: OPAL.AGF отсутствует — пустой AGF-каталог."""
    import catalog.glass_agf as agf
    monkeypatch.setattr(
        agf, "_AGF_PATH", os.path.join("Z:", "no-such-dir", "OPAL.AGF"))
    monkeypatch.setattr(agf, "_CATALOG", None)
    monkeypatch.setattr(agf, "_CATALOG_RUS", None)


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    """Демо-ахромат (.json) — стёкла К8 + ТФ1, λ e/G'/C."""
    from domain.models import create_demo_system_by_name
    from fileio.json_io import save_json
    path = str(tmp_path_factory.mktemp("commands_r500_18") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


@pytest.fixture(scope="module")
def demo_opj(tmp_path_factory):
    """Демо-ахромат (.opj) — для поленезависимых команд."""
    from domain.models import create_demo_system_by_name
    from fileio.opj_io import save_opj
    path = str(tmp_path_factory.mktemp("commands_r500_18") / "demo.opj")
    save_opj(create_demo_system_by_name("achromat"), path)
    return path


def _probe_system() -> OpticalSystem:
    """Дублет К8+ТФ5 (стёкла обеих семейств карты)."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.aperture_value = 10.0
    s.surfaces = [
        Surface(radius=80, glass="К8", thickness=25),
        Surface(radius=-60, glass="ТФ5", thickness=3),
        Surface(radius=-200, glass="", thickness=70),
    ]
    return s


@pytest.fixture
def ctx_probe():
    """REPL-контекст с живой системой '_resv_probe' (не текущая)."""
    ctx = CommandContext()
    ctx.put_system("_resv_probe", _probe_system(), make_current=False)
    yield ctx
    ctx.drop_system("_resv_probe")


# --------------------------------------------------------------------------- #
# Состав пакета и полное smoke-покрытие
# --------------------------------------------------------------------------- #

#: Все 22 команды пакета (имя → категория).
RESERVE_COMMANDS = {
    "diagram.coverage": "diagram",
    "diagram.type.stats": "diagram",
    "diagram.crown.flint": "diagram",
    "diagram.bbox": "diagram",
    "diagram.system": "diagram",
    "diagram.pick": "diagram",
    "catalog.stats": "catalog",
    "catalog.sources.compare": "catalog",
    "catalog.glass.multi": "catalog",
    "catalog.availability": "catalog",
    "calc.aber.dioptre": "calc",
    "calc.aber.grminsec": "calc",
    "calc.pupil.zone": "calc",
    "calc.tgprime.label": "calc",
    "calc.fan.launch": "calc",
    "calc.edge2.lambda": "calc",
    "calc.virtual.kappa": "calc",
    "calc.goe.kappa": "calc",
    "calc.goe.replay": "calc",
    "calc.depth.criteria": "calc",
    "calc.defocus.convert": "calc",
    "units.print.table": "units",
}


class TestRegistration:
    def test_all_commands_registered(self):
        for name, category in RESERVE_COMMANDS.items():
            assert default_registry.has(name), name
            assert default_registry.get(name).category == category, name

    def test_no_dups_with_builtin(self):
        """Повторная регистрация модуля — duplicate_command."""
        with pytest.raises(CommandError) as exc:
            reserve_cmds.register(default_registry)
        assert exc.value.code == "duplicate_command"

    def test_diagram_category_extended(self):
        """Категория diagram: 4 (Волна 3 + П4) + 6 пакета = 10."""
        names = [n for n in default_registry.names()
                 if default_registry.get(n).category == "diagram"]
        assert len(names) == 10
        assert {"diagram.data", "diagram.types", "diagram.render",
                "diagram.glasses"} <= set(names)


def _smoke_args(demo_json, demo_opj):
    return {
        "diagram.coverage": {"vd_bins": 4, "nd_bins": 5},
        "diagram.type.stats": {},
        "diagram.crown.flint": {},
        "diagram.bbox": {},
        "diagram.system": {"file": demo_json},
        "diagram.pick": {"nd": 1.5163, "vd": 64.1},
        "catalog.stats": {},
        "catalog.sources.compare": {},
        "catalog.glass.multi": {"limit": 5},
        "catalog.availability": {"name": "К8"},
        "calc.aber.dioptre": {"L_zone_mm": 95.0, "L_parax_mm": 96.0},
        "calc.aber.grminsec": {"dy_mm": -0.04, "L_mm": 96.0},
        "calc.pupil.zone": {"zones": [0.5, 1.0], "ax_mm": 5.0,
                            "na": 0.25},
        "calc.tgprime.label": {"h_out_mm": -3.2, "u_prime_deg": 2.0},
        "calc.fan.launch": {"zones": [0.5, 1.0], "ax_mm": 5.0,
                            "na": 0.25},
        "calc.edge2.lambda": {"system": "OBEKTIV", "kind": "прод",
                              "zones": [0.5, 1.0]},
        "calc.virtual.kappa": {"wl": 0.54607},
        "calc.goe.kappa": {"wl": 4.25, "curvature_c": 0.01},
        "calc.goe.replay": {"rec0": 0.1342, "wl": 0.6328},
        "calc.depth.criteria": {"file": demo_opj, "criterion": "spot_rms",
                                "max_value": 0.5, "defocus_range": 0.3,
                                "steps": 7, "num_rays": 30},
        "calc.defocus.convert": {"file": demo_opj, "defocus_mm": 0.1},
        "units.print.table": {},
    }


def test_every_command_has_smoke(demo_json, demo_opj):
    """Полный набор пакета покрыт smoke-аргументами — не больше и не
    меньше (команды пакета == smoke-набор)."""
    assert set(_smoke_args(demo_json, demo_opj)) == set(RESERVE_COMMANDS)


def test_smoke_every_command(demo_json, demo_opj):
    """Каждая команда пакета выполняется на демо-данных (строгий JSON)."""
    for name, args in sorted(_smoke_args(demo_json, demo_opj).items()):
        run(name, args)


# --------------------------------------------------------------------------- #
# diagram.* — карта стёкол
# --------------------------------------------------------------------------- #

class TestDiagram:
    def test_coverage_grid_sums(self):
        """Сумма ячеек == стёкла в окне; топ-ячейки отсортированы."""
        data = run("diagram.coverage",
                   {"source": "gost", "vd_bins": 4, "nd_bins": 5,
                    "top_cells": 3})
        assert data["total"] == 28          # ГОСТ без воздуха/спецсред
        assert data["in_view"] == sum(c["count"] for c in data["cells"])
        assert data["in_view"] + data["outside_view"] == data["total"]
        assert data["occupied"] <= 4 * 5
        assert data["occupancy_pct"] == pytest.approx(
            100.0 * data["occupied"] / 20.0)
        counts = [t["count"] for t in data["top"]]
        assert counts == sorted(counts, reverse=True) and counts[0] > 0
        assert len(data["vd_edges"]) == 5 and len(data["nd_edges"]) == 6
        cell = data["cells"][0]
        assert cell["vd_from"] == pytest.approx(20.0)
        assert cell["nd_to"] == pytest.approx(1.45 + 0.4 / 5)

    def test_coverage_all_sources(self):
        """Все источники: объединение БЕЗ дублей имён (CI: ГОСТ+.FIL).

        Регрессия дедупа _iter_entries: раньше 42 = 28 ГОСТ + 14 дубликатов
        .FIL-пересечений; теперь объединение уникальных имён — на CI это 28,
        локально с AGF больше. Дубликаты строк — ошибка контракта.
        """
        data = run("diagram.coverage", {})
        assert data["total"] >= 28           # уникальные реальные стёкла (CI-база)
        assert data["source"] == "all"
        gost = run("diagram.coverage", {"source": "gost"})
        assert data["total"] >= gost["total"]  # объединение не уже одиночного источника

    def test_type_stats_gost_counts(self):
        """Плотность типов ГОСТ: К=7 (с КВАРЦ*), ТФ=4; центры по каталогу."""
        data = run("diagram.type.stats", {"source": "gost"})
        types = {t["type"]: t for t in data["types"]}
        assert data["total"] == 28 and data["unclassified"] == 0
        assert sum(t["count"] for t in data["types"]) == 28
        assert types["К"]["count"] == 7 and types["ТФ"]["count"] == 4
        # центроид ТФ: vd_mean по (33.9, 32.2, 29.5, 27.5) — каталог ГОСТ
        assert types["ТФ"]["vd_mean"] == pytest.approx(
            (33.9 + 32.2 + 29.5 + 27.5) / 4, abs=1e-9)
        assert types["ТФ"]["family"] == "flint"
        assert types["К"]["family"] == "crown"
        assert types["ТФ"]["vd_min"] == pytest.approx(27.5)
        assert types["ТФ"]["nd_max"] == pytest.approx(1.755)

    def test_crown_flint_gost(self):
        """Семейства ГОСТ: 17 кронов / 11 флинтов; граница — полоса
        50..60 (единственная смешанная); перекрытие Vd = 51.8−50.8."""
        data = run("diagram.crown.flint", {"source": "gost"})
        assert data["family_stats"]["crown"]["count"] == 17
        assert data["family_stats"]["flint"]["count"] == 11
        assert data["family_stats"]["other"]["count"] == 0
        assert data["family_stats"]["crown"]["vd_min"] == pytest.approx(
            50.8)
        assert data["family_stats"]["flint"]["vd_max"] == pytest.approx(
            51.8)
        assert data["mixed_bands"] == [{"vd_from": 50.0, "vd_to": 60.0}]
        assert data["vd_overlap"] == pytest.approx(1.0)
        band_sum = sum(b["crown"] + b["flint"] + b["other"]
                       for b in data["bands"])
        assert band_sum == 28 and data["outside"] == 0

    def test_bbox_gost(self):
        """Границы ГОСТ-каталога: nd 1.45846..1.755, Vd 27.5..70."""
        data = run("diagram.bbox", {"source": "gost"})
        assert data["bbox"] == {"nd_min": pytest.approx(1.45846),
                                "nd_max": pytest.approx(1.755),
                                "vd_min": pytest.approx(27.5),
                                "vd_max": pytest.approx(70.0)}
        assert data["view"] == {"vd": [20.0, 80.0], "nd": [1.45, 1.85]}
        assert data["outside_view"] == 0

    def test_system_demo_achromat(self, demo_json):
        """Стёкла демо-системы на карте: К8 (крон) + ТФ1 (флинт)."""
        data = run("diagram.system", {"file": demo_json})
        rows = {g["glass"]: g for g in data["glasses"]}
        assert set(rows) == {"К8", "ТФ1"}
        assert rows["К8"]["family"] == "crown"
        assert rows["ТФ1"]["family"] == "flint"
        assert rows["К8"]["type"] == "К" and rows["ТФ1"]["type"] == "ТФ"
        assert "gost" in rows["К8"]["sources"]
        assert rows["К8"]["nd"] == pytest.approx(1.5163)
        assert data["summary"]["by_family"] == {"crown": 1, "flint": 1}
        assert data["summary"]["found"] == 2
        assert len(data["summary"]["by_vd_band"]) == 2  # 30-40 и 60-70

    def test_system_live_context(self, ctx_probe):
        """Живая система контекста REPL по имени (без смены текущей)."""
        data = run("diagram.system", {"system": "_resv_probe"},
                   ctx=ctx_probe)
        assert [g["glass"] for g in data["glasses"]] == ["К8", "ТФ5"]
        assert ctx_probe.current is None  # текущая не менялась

    def test_pick_exact_position(self):
        """Точка (nd, Vd) стекла К8 → ближайшее оно само (dist=0)."""
        data = run("diagram.pick",
                   {"nd": 1.5163, "vd": 64.1, "source": "gost"})
        assert data["nearest"]["name"] == "К8"
        assert data["nearest"]["dist"] == pytest.approx(0.0, abs=1e-9)
        assert data["count"] == 28

    def test_pick_sorted_and_flint(self):
        """Метрика монотонна; тяжёлый флинт ближе к (1.75, 28)."""
        data = run("diagram.pick",
                   {"nd": 1.75, "vd": 28.0, "source": "gost"})
        dists = [m["dist"] for m in data["matches"]]
        assert dists == sorted(dists)
        assert data["nearest"]["name"] == "ТФ5"
        assert data["nearest"]["type"] == "ТФ"


# --------------------------------------------------------------------------- #
# catalog.* — свод источников и доступность
# --------------------------------------------------------------------------- #

class TestCatalogStats:
    def test_gost_counts_and_balance(self):
        """ГОСТ: 30 всего / 28 реальных / 2 отфильтрованных (воздух)."""
        data = run("catalog.stats", {})
        assert data["sources"]["gost"] == {"total": 30, "real": 28,
                                           "filtered": 2}
        assert data["sources"]["fil"]["total"] >= 16
        # баланс: union == сумма уникальных + мультиисточниковые
        assert data["union"] == (sum(data["unique"].values())
                                 + data["multi_source"])

    def test_multi_at_least_gost_fil(self):
        """Мультиисточниковые: ≥14 (пересечение ГОСТ/.FIL-базы)."""
        data = run("catalog.stats", {})
        assert data["multi_source"] >= 14

    @requires_fil
    def test_fil_full_catalog(self):
        """Локально .FIL полный: 889 записей, 887 реальных стёкол."""
        data = run("catalog.stats", {})
        assert data["sources"]["fil"]["real"] == 887


class TestSourcesCompare:
    def test_gost_fil_intersection_14(self):
        """ГОСТ ∩ .FIL = 14 имён (встроенная .FIL-база ГОСТ-марок) —
        выполняется и в CI (база .FIL в репо), и локально."""
        data = run("catalog.sources.compare", {"limit": 5})
        pair = data["pairwise"]["gost_fil"]
        assert pair["count"] == 14
        assert "К8" in pair["sample"]
        assert data["all_three"]["count"] <= pair["count"]
        assert data["counts"]["gost"] == 28

    def test_unique_balance(self):
        """union compare == union stats (общий канонизатор имён)."""
        data = run("catalog.sources.compare", {})
        stats = run("catalog.stats", {})
        assert data["union"] == stats["union"]
        assert data["unique"] == stats["unique"]
        assert data["counts"]["gost"] == stats["sources"]["gost"]["real"]

    @requires_agf
    def test_agf_intersections_local(self):
        """Локально (OPAL.AGF): ГОСТ ∩ AGF = 23, .FIL ∩ AGF = 13
        (по русским алиасам), все три = 13."""
        data = run("catalog.sources.compare", {})
        assert data["pairwise"]["gost_agf"]["count"] == 23
        assert data["pairwise"]["fil_agf"]["count"] == 13
        assert data["all_three"]["count"] == 13


class TestGlassMulti:
    def test_entries_structure(self):
        data = run("catalog.glass.multi", {"limit": 50})
        assert data["total"] >= 14
        for entry in data["entries"]:
            assert entry["sources_count"] == len(entry["sources"])
            assert entry["sources_count"] >= 2
        k8 = next(e for e in data["entries"] if e["name"] == "К8")
        assert {"gost", "fil"} <= set(k8["sources"])
        assert k8["d_nd"] < 0.01   # одинаковые марки — близкие nd

    def test_min_sources_three(self):
        data = run("catalog.glass.multi", {"min_sources": 3, "limit": 5})
        for entry in data["entries"]:
            assert entry["sources_count"] == 3

    def test_bad_min_sources(self):
        fail("catalog.glass.multi", {"min_sources": 4}, "invalid_param")


class TestAvailability:
    def test_k8_primary_gost(self):
        """К8: приоритет ГОСТ, есть и в .FIL; nd совпадает с каталогом."""
        data = run("catalog.availability", {"name": "К8"})
        assert data["primary"] == "gost" and data["canonical"] == "К8"
        sources = {s["source"]: s for s in data["sources"]}
        assert {"gost", "fil"} <= set(sources)
        assert sources["gost"]["nd"] == pytest.approx(1.5163)
        assert sources["gost"]["vd"] == pytest.approx(64.1)

    def test_not_found(self):
        fail("catalog.availability", {"name": "НЕТ_ТАКОГО_СТЕКЛА"},
             "not_found")

    def test_without_agf_no_internal_error(self, monkeypatch):
        """CI-режим (нет OPAL.AGF): availability деградирует, а не
        internal_error; ГОСТ/.FIL работают, мусор — not_found.

        Регрессия merge-фикса: catalog.availability падал с
        FileNotFoundError (OPAL.AGF) на CI — вместо деградации.
        """
        _no_agf(monkeypatch)
        data = run("catalog.availability", {"name": "К8"})
        assert data["primary"] == "gost" and data["canonical"] == "К8"
        sources = {s["source"] for s in data["sources"]}
        assert "gost" in sources and "agf" not in sources
        fail("catalog.availability", {"name": "НЕТ_ТАКОГО_СТЕКЛА"},
             "not_found")

    def test_diagram_system_without_agf(self, monkeypatch, demo_json):
        """CI-режим: diagram.system строит карту без AGF-источника."""
        _no_agf(monkeypatch)
        data = run("diagram.system", {"file": demo_json})
        assert data["glasses"], "карта стёкол системы пуста"
        for entry in data["glasses"]:
            assert entry.get("source") != "agf"

    @requires_agf
    def test_latin_query_and_synonyms(self):
        """Латиница AGF: TK16 → AGF + синоним ТК16; ТК16 — во всех
        трёх источниках (локально)."""
        latin = run("catalog.availability", {"name": "TK16"})
        assert latin["primary"] == "agf"
        assert "ТК16" in latin["synonyms"]
        cyr = run("catalog.availability", {"name": "ТК16"})
        assert {s["source"] for s in cyr["sources"]} == {
            "gost", "fil", "agf"}
        assert "TK16" in cyr["synonyms"]


# --------------------------------------------------------------------------- #
# calc.* — формулы FORMULAS.md (паритеты с движками)
# --------------------------------------------------------------------------- #

class TestAberFormulas:
    def test_dioptre_parity(self):
        """дптр = 1000/L_зоны − 1000/L_паракс (FORMULAS §3)."""
        from analysis.units import mm_to_dioptres
        data = run("calc.aber.dioptre",
                   {"L_zone_mm": 95.0, "L_parax_mm": 96.0})
        assert data["zone_dpt"] == pytest.approx(mm_to_dioptres(95.0))
        assert data["parax_dpt"] == pytest.approx(1000.0 / 96.0)
        assert data["dioptres"] == pytest.approx(
            1000.0 / 95.0 - 1000.0 / 96.0)

    def test_dioptre_zero_is_null(self):
        """L′ = 0 → пустая ячейка печати (∞) — None, а не ошибка."""
        data = run("calc.aber.dioptre",
                   {"L_zone_mm": 0.0, "L_parax_mm": 96.0})
        assert data["zone_dpt"] is None and data["dioptres"] is None

    def test_grminsec_parity(self):
        """угол = atan2(Δy, L′) из центра выходного зрачка; печать —
        гр.мнсек движком analysis.units."""
        from analysis.units import deg_to_gms, grminsec
        data = run("calc.aber.grminsec", {"dy_mm": -0.0401, "L_mm": 96.0})
        angle = math.degrees(math.atan2(-0.0401, 96.0))
        assert data["angle_deg"] == pytest.approx(angle)
        assert data["grminsec"] == pytest.approx(grminsec(angle))
        assert data["print"] == deg_to_gms(angle)


class TestPupilFormulas:
    def test_pupil_zone_parity(self):
        """H ЗР = зона·Ax (pupil_h_mm); ближний = 100·tg(arcsin(зона·NA))."""
        from analysis.units import pupil_h_mm, tg100
        data = run("calc.pupil.zone",
                   {"zones": [0.5, 1.0], "ax_mm": 5.0, "na": 0.25})
        for row, zone in zip(data["rows"], (0.5, 1.0)):
            assert row["zone"] == zone
            assert row["h_far_mm"] == pytest.approx(
                pupil_h_mm(zone, 5.0))
            expected = tg100(math.degrees(math.asin(zone * 0.25)))
            assert row["h_near_tg100"] == pytest.approx(expected)

    def test_fan_launch_parity(self):
        """Запуск веера: высота зона·Ax; угол arcsin(зона·NA) (GFIX P6)."""
        data = run("calc.fan.launch",
                   {"zones": [0.5, 1.0], "ax_mm": 5.0, "na": 0.25})
        for row, zone in zip(data["rows"], (0.5, 1.0)):
            assert row["far_y_mm"] == pytest.approx(zone * 5.0)
            assert row["near_u_deg"] == pytest.approx(
                math.degrees(math.asin(zone * 0.25)))

    def test_tgprime_label(self):
        """Метка TABOC2: дальнее |H′| мм; ближнее −100·tg u′."""
        from analysis.units import tg100
        data = run("calc.tgprime.label",
                   {"h_out_mm": -3.2, "u_prime_deg": 2.0})
        assert data["far_label_mm"] == pytest.approx(3.2)
        assert data["near_label_tg100"] == pytest.approx(-tg100(2.0))

    def test_validation_errors(self):
        fail("calc.pupil.zone", {"zones": [0.5]}, "invalid_param")
        fail("calc.pupil.zone",
             {"zones": [0.5], "ax_mm": 5.0, "na": 1.5}, "invalid_param")
        fail("calc.fan.launch", {"zones": [0.5]}, "invalid_param")
        fail("calc.tgprime.label", {}, "invalid_param")


class TestEdge2Lambda:
    def test_formula_values(self):
        """λ(z) = 1−(q0+q1·z²)·z²; OBEKTIV/прод: λ(1) = 1−(q0+q1)."""
        data = run("calc.edge2.lambda",
                   {"system": "OBEKTIV", "kind": "прод",
                    "zones": [0.5, 1.0]})
        assert (data["q0"], data["q1"]) == (0.03640, 0.00145)
        by_zone = {r["zone"]: r["lambda"] for r in data["rows"]}
        assert by_zone[1.0] == pytest.approx(1.0 - (0.03640 + 0.00145))
        assert by_zone[0.5] == pytest.approx(
            1.0 - (0.03640 + 0.00145 * 0.25) * 0.25)

    def test_engine_parity(self):
        from analysis.aberrations import (EDGE2_PRINT_LAMBDA,
                                          edge2_print_lambda)
        zones = [0.25, 0.7, 0.9]
        data = run("calc.edge2.lambda",
                   {"system": "OKULAR", "kind": "Tg", "zones": zones})
        for row, zone in zip(data["rows"], zones):
            assert row["lambda"] == pytest.approx(
                edge2_print_lambda(EDGE2_PRINT_LAMBDA["OKULAR"], "Tg",
                                   zone))

    def test_missing_family(self):
        """OPTICS#1 не имеет семейства Tg в банке — not_found."""
        fail("calc.edge2.lambda",
             {"system": "OPTICS#1", "kind": "Tg", "zones": [1.0]},
             "not_found")


class TestVirtualKappa:
    def test_table_values(self):
        """(κ0, κ2) = банк VIRTUAL_WAVE_KAPPA['OPTICS#1'] на 0.54607."""
        data = run("calc.virtual.kappa", {"wl": 0.54607})
        assert data["kappa0"] == pytest.approx(-0.10516667)
        assert data["kappa2"] == pytest.approx(0.00436667)
        assert data["r_ref_mm"] == pytest.approx(1.0 / -0.10516667)
        assert data["available_wls"] == [0.43405, 0.54607, 0.65628]

    def test_wl_not_in_table(self):
        fail("calc.virtual.kappa", {"wl": 0.58756}, "not_found")


class TestGoeFormulas:
    def test_kappa_at_design_wl(self):
        """κ(λ0) = κ0; C_eff = κ·C; R_eff = 1/C_eff (FORMULAS §5)."""
        data = run("calc.goe.kappa", {"wl": 4.25, "curvature_c": 0.01})
        assert data["kappa"] == pytest.approx(1.089185)
        assert data["c_eff"] == pytest.approx(0.01 * 1.089185)
        assert data["r_eff_mm"] == pytest.approx(1.0 / (0.01 * 1.089185))

    def test_kappa_law(self):
        """κ(λ) = κ0 + κ1·(λ−λ0) — закон GTIE00 (GOE_KAPPA_LAW)."""
        data = run("calc.goe.kappa", {"wl": 0.6328})
        expected = 1.089185 + 5.27e-4 * (0.6328 - 4.25)
        assert data["kappa"] == pytest.approx(expected)
        custom = run("calc.goe.kappa",
                     {"wl": 1.0, "k0": 1.0, "k1": 0.0, "wl0": 0.5})
        assert custom["kappa"] == pytest.approx(1.0)
        assert custom["c_eff"] is None

    def test_replay(self):
        """δ = rec₀·λ₀/λ: на λ0 δ=rec0; на 2λ0 — половина."""
        data = run("calc.goe.replay", {"rec0": 0.1342, "wl": 0.6328})
        assert data["delta"] == pytest.approx(0.1342)
        doubled = run("calc.goe.replay",
                      {"rec0": 0.1342, "wl": 1.2656, "lambda0": 0.6328})
        assert doubled["delta"] == pytest.approx(0.1342 / 2.0)
        fail("calc.goe.replay", {"rec0": 1.0, "wl": 0.0},
             "invalid_param")


class TestDepthCriteria:
    def test_spot_satisfied(self, demo_json):
        data = run("calc.depth.criteria", {
            "file": demo_json, "criterion": "spot_rms",
            "max_value": 0.2, "defocus_range": 2.0, "steps": 21,
            "num_rays": 40})
        assert data["satisfied"] is True
        assert data["unit"] == "mm"
        assert data["near_mm"] <= data["best_focus_mm"] <= data["far_mm"]
        assert data["depth_mm"] == pytest.approx(
            data["far_mm"] - data["near_mm"])
        assert len(data["rows"]) == 21
        assert data["min_value"] <= data["max_value"]
        center = data["rows"][10]
        assert center["defocus_mm"] == pytest.approx(0.0)

    def test_spot_center_parity(self, demo_json):
        """Значение в плоскости Гаусса == прямой движок пятна."""
        from analysis.aberrations import (compute_rms_spot_xy,
                                          compute_spot_diagram_at_defocus)
        from fileio.json_io import load_json
        system = load_json(demo_json)
        spots = compute_spot_diagram_at_defocus(
            system, wl=0.54607, num_rays=30, field_y=0.0, defocus_mm=0.0)
        expected = compute_rms_spot_xy(spots)["rms_total"]
        data = run("calc.depth.criteria", {
            "file": demo_json, "criterion": "spot_rms",
            "max_value": 0.5, "defocus_range": 0.3, "steps": 7,
            "num_rays": 30})
        center = data["rows"][3]
        assert center["defocus_mm"] == pytest.approx(0.0)
        assert center["value"] == pytest.approx(expected)

    def test_wave_satisfied(self, demo_json):
        """СКW: rms карты W + параксиальный дефокус w=W_край·ρ²."""
        import numpy as np
        from analysis.zernike import compute_wavefront_map_2d
        from fileio.json_io import load_json
        system = load_json(demo_json)
        data = run("calc.depth.criteria", {
            "file": demo_json, "criterion": "wave_rms",
            "max_value": 0.5, "defocus_range": 0.2, "steps": 11,
            "grid_size": 24})
        assert data["satisfied"] is True and data["unit"] == "wl"
        assert data["waves_per_mm"] > 0
        assert data["near_mm"] <= data["best_focus_mm"] <= data["far_mm"]
        # паритет в плоскости Гаусса: rms чистой карты W по зрачку
        wavefront, _coords, mask = compute_wavefront_map_2d(
            system, wl=0.54607, field_y=0.0, grid_size=24)
        inside = np.asarray(wavefront)[np.asarray(mask) > 0]
        center = data["rows"][5]
        assert center["defocus_mm"] == pytest.approx(0.0)
        assert center["value"] == pytest.approx(
            float(np.sqrt(np.mean(inside ** 2))))
        # у демо-ахромата есть дефокусная аберрация: минимум ниже центра
        assert data["min_value"] < center["value"]

    def test_below_threshold(self, demo_json):
        """Допуск ниже минимума — интервал пуст (satisfied False)."""
        data = run("calc.depth.criteria", {
            "file": demo_json, "criterion": "spot_rms",
            "max_value": 0.001, "defocus_range": 0.3, "steps": 7,
            "num_rays": 30})
        assert data["satisfied"] is False
        assert data["depth_mm"] == 0.0 and data["near_mm"] is None

    def test_errors(self, demo_json):
        fail("calc.depth.criteria",
             {"file": demo_json, "criterion": "spot_rms",
              "max_value": 0.0}, "invalid_param")
        fail("calc.depth.criteria",
             {"file": demo_json, "criterion": "spot_rms",
              "max_value": 0.1, "steps": 2}, "invalid_param")
        fail("calc.depth.criteria",
             {"file": demo_json, "criterion": "нет", "max_value": 0.1},
             "invalid_param")


class TestDefocusConvert:
    def test_round_trip_and_na(self, demo_json):
        """мм → волны → мм; согласованность wpm = 0.5·NA′²/(λ·1e-3)."""
        forward = run("calc.defocus.convert",
                      {"file": demo_json, "defocus_mm": 0.1, "wl": 0.54607})
        wpm = forward["waves_per_mm"]
        assert forward["waves"] == pytest.approx(0.1 * wpm)
        back = run("calc.defocus.convert",
                   {"file": demo_json, "waves": forward["waves"],
                    "wl": 0.54607})
        assert back["defocus_mm"] == pytest.approx(0.1)
        na = run("calc.aperture.na", {"file": demo_json, "wl": 0.54607})
        assert wpm == pytest.approx(
            0.5 * na["na_image"] ** 2 / (0.54607 * 1e-3))
        assert forward["na_image"] == pytest.approx(
            math.sqrt(2.0 * wpm * 0.54607 * 1e-3))

    def test_requires_a_value(self, demo_json):
        fail("calc.defocus.convert", {"file": demo_json},
             "invalid_param")


# --------------------------------------------------------------------------- #
# units.print.table — единицы печати OPAL
# --------------------------------------------------------------------------- #

class TestPrintUnits:
    def test_table_rows(self):
        data = run("units.print.table", {})
        assert data["count"] == 6
        rows = {r["quantity"]: r for r in data["rows"]}
        assert rows["поперечные аберрации"]["near"] == "мм"
        assert rows["поперечные аберрации"]["far"] == "гр.мнсек"
        assert rows["продольные аберрации"]["far"] == "дптр"
        assert "REVERSE_NZR" in data["source"]
