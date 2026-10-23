"""R500-8: допуски tol.* (commands/builtin/tol_cmds.py).

Конечноразностные чувствительности поверх реальных движков: сверка
градиента с прямыми возмущениями, обратные допуски, RSS, Монте-Карло
(детерминизм seed).
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
    path = str(tmp_path_factory.mktemp("tol") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


def _load(path):
    from fileio.json_io import load_json
    return load_json(path)


class TestSensitivity:
    def test_radius_gradient_matches_direct(self, demo_json):
        """Градиент из команды ≈ прямой разности параксиала."""
        from domain.calculations import paraxial_trace
        system = _load(demo_json)
        data = run("tol.sensitivity.radius",
                   {"file": demo_json, "delta": 0.05})
        row0 = data["rows"][0]
        # прямая центральная разность
        s_plus = _load(demo_json)
        s_plus.surfaces[0].radius += 0.05
        s_minus = _load(demo_json)
        s_minus.surfaces[0].radius -= 0.05
        direct = (paraxial_trace(s_plus)["focal_length"]
                  - paraxial_trace(s_minus)["focal_length"]) / 0.1
        assert row0["d_efl_d_r"] == pytest.approx(direct, rel=1e-9)

    def test_radius_all_and_single(self, demo_json):
        full = run("tol.sensitivity.radius", {"file": demo_json})
        assert len(full["rows"]) == 3
        single = run("tol.sensitivity.radius",
                     {"file": demo_json, "index": 1})
        assert [r["index"] for r in single["rows"]] == [1]
        assert single["rows"][0]["d_efl_d_r"] == pytest.approx(
            full["rows"][1]["d_efl_d_r"])
        fail("tol.sensitivity.radius", {"file": demo_json, "index": 99},
             "invalid_param")

    def test_thickness_and_glass(self, demo_json):
        thick = run("tol.sensitivity.thickness", {"file": demo_json})
        assert all(r["d_efl_d_d"] is not None for r in thick["rows"])
        glass = run("tol.sensitivity.glass", {"file": demo_json})
        # все 3 поверхности со стёклами (последняя — воздух: скип)
        assert [r["index"] for r in glass["rows"]] == [0, 1]
        assert all(r["d_efl_d_n"] is not None for r in glass["rows"])

    def test_seidel_sensitivity_shape(self, demo_json):
        data = run("tol.sensitivity.seidel.radius",
                   {"file": demo_json, "index": 0})
        row = data["rows"][0]
        assert {f"d{k}_d_r" for k in ("SI", "SII", "SIII", "SIV", "SV")} \
            <= set(row)

    def test_spot_and_tilt_and_decenter(self, demo_json):
        spot = run("tol.sensitivity.spot.radius",
                   {"file": demo_json, "index": 0, "num_rays": 10})
        assert spot["rows"][0]["d_rms_d_r"] is not None
        tilt = run("tol.sensitivity.tilt",
                   {"file": demo_json, "num_rays": 15})
        # boresight-чувствительность к наклону заметна (мм/град)
        assert all(abs(r["d_centroid_d_tilt"]) > 1e-4
                   for r in tilt["rows"])
        dec = run("tol.sensitivity.decenter",
                  {"file": demo_json, "num_rays": 15})
        assert all(abs(r["d_centroid_d_dec"]) > 1e-4
                   for r in dec["rows"])

    def test_bad_delta(self, demo_json):
        fail("tol.sensitivity.radius",
             {"file": demo_json, "delta": -1.0}, "invalid_param")


class TestInverseAndBudget:
    def test_contributions_ranked(self, demo_json):
        data = run("tol.contributions", {"file": demo_json})
        maxes = [r["max_g"] for r in data["rows"]]
        assert maxes == sorted(maxes, reverse=True)
        assert all("d_efl_d_r" in r and "d_efl_d_d" in r
                   for r in data["rows"])

    def test_worst_sorted(self, demo_json):
        data = run("tol.worst", {"file": demo_json, "limit": 4})
        grads = [w["abs_grad"] for w in data["worst"]]
        assert grads == sorted(grads, reverse=True)
        assert 0 < len(data["worst"]) <= 4

    def test_inverse_radius_recovers_budget(self, demo_json):
        data = run("tol.inverse.radius",
                   {"file": demo_json, "budget": 0.1})
        for row in data["rows"]:
            if row["tolerance_mm"] is not None:
                # |grad|·tol ≈ бюджет (линейная оценка)
                assert abs(row["grad"]) * row["tolerance_mm"] == \
                    pytest.approx(0.1, rel=1e-9)

    def test_inverse_bad_budget(self, demo_json):
        fail("tol.inverse.radius", {"file": demo_json, "budget": 0.0},
             "invalid_param")

    def test_budget_split_rss(self, demo_json):
        """RSS суммы вкладов на границах допусков = бюджет."""
        data = run("tol.budget.split", {"file": demo_json, "budget": 0.2})
        rss = math.sqrt(sum((r["grad"] * r["tolerance_mm"]) ** 2
                            for r in data["rows"]))
        assert rss == pytest.approx(0.2, rel=1e-9)

    def test_rss_combine(self):
        assert run("tol.rss.combine",
                   {"contributions": [3.0, 4.0]})["rss"] == \
            pytest.approx(5.0)
        fail("tol.rss.combine", {"contributions": []}, "invalid_param")


class TestPerturbationAndMC:
    def test_apply_perturbation_linear_region(self, demo_json):
        data = run("tol.apply.perturbation",
                   {"file": demo_json, "index": 0, "dr": 0.01,
                    "num_rays": 10})
        sens = run("tol.sensitivity.radius",
                   {"file": demo_json, "delta": 0.05})
        # в линейной области Δf ≈ градиент·Δr
        assert data["d_efl"] == pytest.approx(
            sens["rows"][0]["d_efl_d_r"] * 0.01, rel=0.05)

    def test_monte_carlo_deterministic(self, demo_json):
        args = {"file": demo_json, "trials": 8, "radius_tol": 0.02,
                "seed": 42}
        first = run("tol.monte_carlo", args)
        second = run("tol.monte_carlo", args)
        assert first["stats"] == second["stats"]
        assert len(first["samples_head"]) == 8
        assert first["stats"]["std"] > 0

    def test_monte_carlo_stats_sane(self, demo_json):
        data = run("tol.monte_carlo",
                   {"file": demo_json, "trials": 16, "radius_tol": 0.05,
                    "thickness_tol": 0.05})
        s = data["stats"]
        assert s["min"] <= s["median"] <= s["max"]
        assert s["min"] <= s["mean"] <= s["max"]

    def test_mc_bad_trials(self, demo_json):
        fail("tol.monte_carlo", {"file": demo_json, "trials": 1},
             "invalid_param")
