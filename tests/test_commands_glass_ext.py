"""R500-4: каталог стёкол и спектральные линии
(commands/builtin/glass_ext_cmds.py).

Всё headless: каталоги ГОСТ/.FIL/AGF, справочник utils/spectral_lines,
дизайнер achromat. AGF может отсутствовать на стенде — тесты AGF-части
не требуют конкретных марок (кроме согласованного поведения).
"""
import os

import pytest

from commands import CommandContext, default_registry

from tests.conftest import requires_fil


def run(name, args=None):
    result = default_registry.execute(name, CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    from domain.models import create_demo_system_by_name
    from fileio.json_io import save_json
    path = str(tmp_path_factory.mktemp("glass_ext") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


class TestGlassLists:
    def test_list_paging_and_order(self):
        page1 = run("catalog.glass.list", {"limit": 5, "offset": 0})
        page2 = run("catalog.glass.list", {"limit": 5, "offset": 5})
        assert page1["total"] == page2["total"]
        names1 = [e["name"] for e in page1["entries"]]
        names2 = [e["name"] for e in page2["entries"]]
        assert not set(names1) & set(names2)
        by_vd = run("catalog.glass.list",
                    {"limit": 3, "order_by": "vd", "descending": True})
        vds = [e["vd"] for e in by_vd["entries"]]
        assert vds == sorted(vds, reverse=True)

    def test_list_no_duplicate_names_without_agf(self, monkeypatch):
        """CI-режим (нет OPAL.AGF): объединённый список без дублей имён.

        Регрессия merge-фикса: БК12 из ГОСТ и .FIL давал пересечение
        страниц catalog.glass.list на CI (падал test_list_paging_and_order).
        """
        import catalog.glass_agf as agf
        monkeypatch.setattr(
            agf, "_AGF_PATH", os.path.join("Z:", "no-such-dir", "OPAL.AGF"))
        monkeypatch.setattr(agf, "_CATALOG", None)
        monkeypatch.setattr(agf, "_CATALOG_RUS", None)
        data = run("catalog.glass.list", {"limit": 100000})
        names = [e["name"] for e in data["entries"]]
        assert names, "каталог пуст — ГОСТ/.FIL не загрузились"
        assert len(names) == len(set(names)), "дубли имён между источниками"
        page1 = run("catalog.glass.list", {"limit": 5, "offset": 0})
        page2 = run("catalog.glass.list", {"limit": 5, "offset": 5})
        assert not ({e["name"] for e in page1["entries"]}
                    & {e["name"] for e in page2["entries"]})

    def test_filter_by_vd(self):
        data = run("catalog.glass.filter",
                   {"vd_min": 50.0, "vd_max": 65.0, "limit": 200})
        assert data["total"] > 0
        assert all(50.0 <= e["vd"] <= 65.0 for e in data["entries"])

    def test_filter_bad_range(self):
        fail("catalog.glass.filter", {"nd_min": 2.0, "nd_max": 1.0},
             "invalid_param")

    @requires_fil
    def test_sources_counts(self):
        data = run("catalog.sources")
        assert data["sources"]["gost"]["count"] >= 25
        assert data["sources"]["fil"]["count"] > 100
        assert data["sources"]["fil"]["nd_max"] > 1.8  # ИК-стёкла

    def test_agf_status_shape(self):
        data = run("catalog.agf.status")
        assert data["available"] == (data["count"] > 0)


class TestGlassMetrics:
    def test_dispersion_monotonic_n(self):
        data = run("catalog.glass.dispersion",
                   {"name": "К8",
                    "wavelengths": [0.43583, 0.48613, 0.58756, 0.65627]})
        ns = [r["n"] for r in data["rows"]]
        assert ns == sorted(ns, reverse=True)  # дисперсия: n падает с λ

    def test_range_curve(self):
        data = run("catalog.glass.range",
                   {"name": "ТФ1", "wl_min": 0.45, "wl_max": 0.65,
                    "steps": 5})
        wls = [p["wl"] for p in data["points"]]
        assert wls == pytest.approx([0.45, 0.50, 0.55, 0.60, 0.65])
        assert data["points"][-1]["n"] < data["points"][0]["n"]

    def test_range_bad_args(self):
        fail("catalog.glass.range", {"name": "К8", "wl_min": 0.9,
                                     "wl_max": 0.4}, "invalid_param")
        fail("catalog.glass.range", {"name": "К8", "steps": 1},
             "invalid_param")

    def test_abbe_shape(self):
        data = run("catalog.glass.abbe", {"name": "К8"})
        # коэффициенты каталога приближённые: сверяем форму, не точное
        # совпадение с заявленным Vd (оба значения возвращаются рядом)
        assert data["nF"] > data["nd_line"] > data["nC"]
        assert 30.0 < data["vd_calc"] < 90.0
        assert data["vd_catalog"] == pytest.approx(64.1, abs=0.1)

    def test_compare(self):
        data = run("catalog.glass.compare", {"a": "К8", "b": "ТФ1"})
        assert data["d_nd"] == pytest.approx(0.1312, abs=1e-3)
        assert data["d_vd"] < -20  # флинт заметно дисперсионнее

    def test_similar_returns_neighbors(self):
        data = run("catalog.glass.similar",
                   {"name": "К8", "nd_tol": 0.02, "vd_tol": 5.0,
                    "limit": 10})
        assert data["matches"]
        assert all(abs(m["d_nd"]) <= 0.02 and abs(m["d_vd"]) <= 5.0
                   for m in data["matches"])

    def test_valid_range(self):
        ok = run("catalog.glass.valid", {"name": "К8", "wl": 0.55})
        assert ok["in_range"] is True
        data = run("catalog.glass.valid", {"name": "К8", "wl": 5.0})
        assert data["in_range"] is False  # далеко за пределами

    def test_pairs_crown_flint(self):
        data = run("catalog.glass.pairs", {"name": "К8", "limit": 10})
        assert data["pairs"]
        for pair in data["pairs"]:
            assert pair["crown"] == "К8"
            assert pair["d_vd"] >= data["min_vd_diff"]
            assert pair["vd_flint"] > 0
            assert pair["flint"].upper() not in ("AIR", "ВОЗДУХ")
        # сортировка по убыванию d_vd
        d_vds = [p["d_vd"] for p in data["pairs"]]
        assert d_vds == sorted(d_vds, reverse=True)

    def test_unknown_glass(self):
        fail("catalog.glass.dispersion",
             {"name": "НЕТ_СТЕКЛА", "wavelengths": [0.5]}, "not_found")


class TestAchromatOptions:
    def test_options_radii(self):
        data = run("catalog.achromat.options", {"focal_length": 100.0})
        assert len(data["options"]) >= 2
        pair = data["options"][0]
        assert pair["ok"] and len(pair["radii"]) == 3
        assert pair["radii"][0] != pair["radii"][1]

    def test_fixed_pair(self):
        data = run("catalog.achromat.options",
                   {"focal_length": 200.0, "crown": "К8", "flint": "ТФ5"})
        assert len(data["options"]) == 1
        assert data["options"][0]["crown"] == "К8"


class TestSpectral:
    def test_lines_table(self):
        data = run("catalog.spectral.lines")
        assert data["count"] == 15
        names = {ln["name"] for ln in data["lines"]}
        assert {"F", "d", "C", "e", "g"} <= names

    def test_get_by_name(self):
        data = run("catalog.spectral.get", {"name": "F"})
        assert data["wavelength_nm"] == pytest.approx(486.13)
        assert data["element"] == "H" and data["text"]
        fail("catalog.spectral.get", {"name": "Z"}, "not_found")

    def test_nearest(self):
        data = run("catalog.spectral.nearest", {"wl": 0.546})
        assert data["line"]["name"] == "e"
        assert data["distance_nm"] < 1.0

    def test_by_element(self):
        data = run("catalog.spectral.element", {"element": "Hg"})
        assert len(data["lines"]) >= 5
        fail("catalog.spectral.element", {"element": "Xx"}, "not_found")

    def test_match_system_wavelengths(self, demo_json):
        data = run("catalog.spectral.match", {"file": demo_json})
        assert len(data["rows"]) == 3
        assert all(r["matched"] for r in data["rows"])  # e/G'/C


class TestDiagramData:
    def test_data_with_highlight(self):
        data = run("diagram.data",
                   {"source": "gost", "highlight": ["К8", "ТФ1"]})
        assert data["count"] >= 25
        assert data["highlighted"] == 2
        k8 = next(g for g in data["glasses"] if g["name"] == "К8")
        assert k8["highlight"] and k8["type"] == "К" and k8["color"]

    def test_types_counts(self):
        data = run("diagram.types", {"source": "gost"})
        types = {t["type"]: t["count"] for t in data["types"]}
        assert types["К"] >= 5 and types["ТФ"] >= 2
        assert sum(types.values()) >= 25
