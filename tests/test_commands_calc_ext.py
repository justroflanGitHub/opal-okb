"""R500-6: расширенные calc.* (commands/builtin/calc_ext_cmds.py).

Паритеты с domain/calculations.py, физические формулы (сагитта, силы,
Эйри, ГРИП, ОПС, сопряжённые отрезки), параксиальные своды.
"""
import math

import pytest

from commands import CommandContext, default_registry


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
    path = str(tmp_path_factory.mktemp("calc_ext") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


class TestEngineWrappers:
    def test_n_known_and_unknown(self):
        data = run("calc.n", {"glass": "К8", "wl": 0.58756})
        assert 1.51 < data["n"] < 1.53 and data["source"] == "gost"
        fail("calc.n", {"glass": "НЕТ_СТЕКЛА"}, "not_found")

    def test_goe_radius_and_table(self, demo_json):
        from domain.models import Surface
        single = run("calc.goe.radius", {"file": demo_json, "index": 0})
        assert single["radius"] == pytest.approx(62.0)
        table = run("calc.goe.table", {"file": demo_json})
        assert len(table["rows"]) == 3
        assert table["rows"][0]["radius"] == single["radius"]
        fail("calc.goe.radius", {"file": demo_json, "index": 99},
             "invalid_param")

    def test_semi_effective(self):
        sharp = run("calc.semi_effective",
                    {"semi_diameter": 10.0, "sharp_edge": True})
        soft = run("calc.semi_effective",
                   {"semi_diameter": 10.0, "sharp_edge": False})
        assert sharp["effective"] >= soft["effective"]

    def test_vignetting_pass_fail(self, demo_json):
        # движок: True = луч завиньетирован; ray_* — мм на 1-й поверхности
        axis = run("calc.vignetting.apply",
                   {"file": demo_json, "field_y": 0.0, "ray_y": 5.0})
        assert axis["vignetted"] is False and axis["passes"] is True
        blocked = run("calc.vignetting.apply",
                      {"file": demo_json, "field_y": 0.0, "ray_y": 50.0})
        assert blocked["vignetted"] is True and blocked["passes"] is False


class TestParaxialSummaries:
    def test_cardinals_consistent(self, demo_json):
        data = run("calc.cardinals", {"file": demo_json})
        assert data["f_prime"] == pytest.approx(97.4678, abs=0.01)
        assert data["f"] == -data["f_prime"]
        assert data["sH_prime"] < 0  # H′ левее последней поверхности
        assert data["back_focal_distance"] > 0

    def test_pupils(self, demo_json):
        data = run("calc.pupils", {"file": demo_json})
        assert data["entrance_diameter"] == pytest.approx(20.0)
        assert data["pupil_magnification"] == pytest.approx(1.0156, abs=1e-3)

    def test_magnification(self, demo_json):
        data = run("calc.magnification", {"file": demo_json})
        assert data["V"] == pytest.approx(-97.4678, abs=0.01)

    def test_lagrange_formula(self, demo_json):
        data = run("calc.lagrange", {"file": demo_json})
        expected = 0.5 * 20.0 * math.tan(math.radians(data["max_field"]))
        assert data["H"] == pytest.approx(expected)

    def test_aperture_na(self, demo_json):
        data = run("calc.aperture.na", {"file": demo_json})
        assert data["na_image"] == pytest.approx(
            20.0 / (2 * 97.4678), abs=1e-4)
        assert 0 < data["na_image"] < 1


class TestGeometryFormulas:
    def test_sagitta_sphere(self):
        data = run("calc.sagitta", {"radius": 100.0, "height": 10.0})
        expected = 1.0 / (1.0 + math.sqrt(1 - 0.01))
        assert data["sag"] == pytest.approx(expected)
        flat = run("calc.sagitta", {"radius": 0.0, "height": 10.0})
        assert flat["sag"] == 0.0

    def test_sagitta_over_aperture_fails(self):
        fail("calc.sagitta", {"radius": 10.0, "height": 20.0},
             "invalid_param")

    def test_sagitta_table(self, demo_json):
        data = run("calc.sagitta.table",
                   {"file": demo_json, "heights": [5.0]})
        assert len(data["rows"]) == 3  # по строке на поверхность

    def test_power_surface(self):
        data = run("calc.power.surface",
                   {"n1": 1.0, "n2": 1.5163, "radius": 62.0})
        assert data["power_dpt"] == pytest.approx(0.5163 / 62.0 * 1000.0)

    def test_thin_lens_equiconvex(self):
        data = run("calc.power.thin_lens",
                   {"n": 1.5163, "r1": 96.84, "r2": -96.84})
        assert data["f_prime"] == pytest.approx(
            1.0 / (0.5163 * (2.0 / 96.84)))
        fail("calc.power.thin_lens",
             {"n": 1.0, "r1": 100.0, "r2": 100.0}, "invalid_param")

    def test_power_table_sum(self, demo_json):
        data = run("calc.power.table", {"file": demo_json})
        assert len(data["rows"]) == 3
        assert data["rows"][0]["n_before"] == pytest.approx(1.0)
        assert data["rows"][0]["n_after"] > 1.5  # К8
        assert data["rows"][2]["n_after"] == pytest.approx(1.0)  # воздух
        total = sum(r["power_dpt"] for r in data["rows"])
        assert data["total_thin_dpt"] == pytest.approx(total)

    def test_airy_and_cutoff(self):
        airy = run("calc.airy", {"f_number": 4.87, "wl": 0.54607})
        assert airy["diameter_um"] == pytest.approx(
            2 * 1.22 * 0.54607 * 4.87)
        cutoff = run("calc.diffraction.cutoff",
                     {"f_number": 4.87, "wl": 0.54607})
        assert cutoff["cutoff_lpmm"] == pytest.approx(
            1.0 / (0.54607e-3 * 4.87))

    def test_depth_of_field(self):
        data = run("calc.depth_of_field",
                   {"f_number": 4.87, "coc_um": 20.0})
        assert data["total_mm"] == pytest.approx(2 * 0.02 * 4.87)

    def test_opl(self):
        data = run("calc.opl", {"segments": [{"n": 1.5, "length": 5.0},
                                             {"n": 1.0, "length": 90.0}]})
        assert data["total_opl_mm"] == pytest.approx(97.5)
        fail("calc.opl", {"segments": []}, "invalid_param")
        fail("calc.opl", {"segments": [{"n": 1.5}]}, "invalid_param")


class TestConjugate:
    def test_solve_from_s(self, demo_json):
        data = run("calc.conjugate.solve",
                   {"file": demo_json, "s": -200.0})
        assert data["s_prime"] == pytest.approx(
            1.0 / (1.0 / 97.4678 + 1.0 / -200.0), abs=1e-2)
        assert data["V"] == pytest.approx(data["s_prime"] / -200.0)

    def test_solve_from_v_roundtrip(self, demo_json):
        target = -0.5
        data = run("calc.conjugate.solve",
                   {"file": demo_json, "V_target": target})
        assert data["V"] == pytest.approx(target)
        back = run("calc.conjugate.solve",
                   {"file": demo_json, "s": data["s"]})
        assert back["s_prime"] == pytest.approx(data["s_prime"], rel=1e-9)

    def test_requires_exactly_one(self, demo_json):
        fail("calc.conjugate.solve", {}, "invalid_param")
        fail("calc.conjugate.solve",
             {"f_override": 100.0, "s": -100.0, "V_target": -1.0},
             "invalid_param")

    def test_override_f(self):
        data = run("calc.conjugate.solve",
                   {"f_override": 100.0, "s": -300.0})
        assert data["s_prime"] == pytest.approx(150.0)
        assert data["V"] == pytest.approx(-0.5)

    def test_object_at_focal_plane_infinite_image(self):
        fail("calc.conjugate.solve",
             {"f_override": 100.0, "s": -100.0}, "invalid_param")
