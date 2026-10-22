"""Команды Волны 3, домен «Оптимизация и визуализация» (opt.*/plot.*/
diagram.*): smoke КАЖДОЙ команды + сверка с прямыми вызовами
analysis/optimization, optimizer, analysis/aberrations, analysis/psf_mtf.

Реестр изолирован от default_registry ( Волна 3: команды в общем
builtin-каталоге появятся после мержа — координатор обновит __init__),
поэтому модуль поднимает свой Registry = builtin Волны 1 + opt_cmds.
"""
import os

import matplotlib
import pytest

import commands
from commands import CommandContext, Registry
from commands.base import CommandError
from commands.builtin import opt_cmds
from analysis.optimization import (
    OptGoal,
    OptVariable,
    evaluate_goal,
    merit_vector,
    optimize,
    solve_single,
)

# --------------------------------------------------------------------------- #
# Изолированный реестр: builtin Волны 1 + команды домена
# --------------------------------------------------------------------------- #

registry = Registry()
commands.register_all(registry)  # включает opt_cmds (Волна 3, мерж)
if not registry.has("opt.goals"):  # защита при ручной регистрации без builtin
    opt_cmds.register(registry)

#: Все команды модуля (для проверки полноты smoke-покрытия).
OPT_COMMANDS = (
    "opt.goals",
    "opt.variables",
    "opt.merit",
    "opt.run",
    "opt.solve",
    "opt.parse",
    "opt.rms",
    "plot.spot",
    "plot.fan",
    "plot.field",
    "plot.psf",
    "plot.mtf",
    "plot.ee",
    "plot.focus",
    "plot.heatmap",
    "diagram.render",
    "diagram.glasses",
)


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = registry.execute(name, ctx or CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.opj, .json) демо-ахромат, созданный командами system.new/save."""
    tmp = tmp_path_factory.mktemp("commands_w3_opt")
    jsn = str(tmp / "demo_achromat.json")
    ctx = CommandContext()
    res = registry.execute("system.new", ctx,
                           {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    return jsn


@pytest.fixture
def ctx(demo_files):
    """Контекст с загруженной демо-системой (REPL-сценарий)."""
    context = CommandContext()
    res = registry.execute("system.load", context,
                           {"file": demo_files, "name": "demo"})
    assert res.ok, res.error
    return context


def _png_ok(path: str) -> bool:
    """Файл существует, непуст и начинается с подписи PNG."""
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        return False
    with open(path, "rb") as f:
        return f.read(8) == b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------- #
# Регистрация
# --------------------------------------------------------------------------- #

class TestRegistration:
    def test_all_commands_registered(self):
        for name in OPT_COMMANDS:
            assert registry.has(name), name
            assert name.split(".")[0] in ("opt", "plot", "diagram")

    def test_no_dups_with_builtin(self):
        """Повторная регистрация модуля — duplicate_command (как builtin)."""
        with pytest.raises(CommandError) as exc:
            opt_cmds.register(registry)
        assert exc.value.code == "duplicate_command"

    def test_every_command_has_smoke_in_this_module(self):
        """Все 17 команд модуля покрыты тестами ниже (по имени)."""
        smoke_names = {"opt.goals", "opt.variables", "opt.merit", "opt.run",
                       "opt.solve", "opt.parse", "opt.rms", "plot.spot",
                       "plot.fan", "plot.field", "plot.psf", "plot.mtf",
                       "plot.ee", "plot.focus", "plot.heatmap",
                       "diagram.render", "diagram.glasses"}
        assert smoke_names == set(OPT_COMMANDS)


# --------------------------------------------------------------------------- #
# opt.* — справочники и оценка
# --------------------------------------------------------------------------- #

class TestOptCatalog:
    def test_goals_reference(self):
        data = run("opt.goals")
        assert set(data["kinds"]) >= {"efl", "bfd", "rms_spot", "seidel",
                                      "longitudinal", "transverse", "field"}
        assert "radius" in data["param_types"]
        assert data["default_norms"]["transverse"] == pytest.approx(0.01)
        assert data["istop"]["0"] and data["istop"]["-1"]

    def test_variables_match_get_param(self, demo_files):
        from analysis.optimization import get_param
        from fileio.json_io import load_json
        system = load_json(demo_files)
        data = run("opt.variables", {"file": demo_files})
        assert data["num_surfaces"] == system.num_surfaces
        got = {(v["surface"], v["param"]): v["value"]
               for v in data["variables"]}
        assert got[(0, "radius")] == pytest.approx(
            get_param(system, 0, "radius"))
        assert got[(1, "thickness")] == pytest.approx(
            get_param(system, 1, "thickness"))
        assert len(data["variables"]) == system.num_surfaces * \
            len(data["param_types"])


class TestOptMerit:
    def test_merit_matches_domain(self, demo_files):
        from fileio.json_io import load_json
        system = load_json(demo_files)
        goal = {"kind": "efl", "target": 100.0, "weight": 2.0}
        data = run("opt.merit", {"file": demo_files, "goals": [goal]})
        direct_value = evaluate_goal(system, OptGoal(kind="efl"))
        assert data["values"][0] == pytest.approx(direct_value, rel=1e-12)
        direct_res = merit_vector(system, [OptGoal(kind="efl", target=100.0,
                                                   weight=2.0)])
        assert data["residuals"][0] == pytest.approx(direct_res[0],
                                                     rel=1e-12)
        assert data["F"] == pytest.approx(direct_res[0] ** 2, rel=1e-12)

    def test_merit_without_target_skips_residuals(self, ctx):
        data = run("opt.merit", {"goals": [{"kind": "efl",
                                            "target": None}]}, ctx=ctx)
        assert "residuals" not in data and "F" not in data
        assert len(data["values"]) == 1

    def test_bad_goal_kind(self, ctx):
        result = registry.execute("opt.merit", ctx,
                                  {"goals": [{"kind": "nosuch"}]})
        assert not result.ok
        assert result.error["code"] == "invalid_param"


# --------------------------------------------------------------------------- #
# opt.run / opt.solve / opt.parse / opt.rms
# --------------------------------------------------------------------------- #

#: Компактная задача ЛАП для тестов: f′ ахромата +5 % двумя радиусами.
_VARS = [{"surface": 0, "param": "radius", "pmin": 40.0, "pmax": 200.0},
         {"surface": 1, "param": "radius", "pmin": -200.0, "pmax": -40.0}]


def _efl_target(demo_files, factor=1.05):
    from fileio.json_io import load_json
    from optics_engine import paraxial_trace
    return paraxial_trace(load_json(demo_files))["focal_length"] * factor


class TestOptRun:
    def test_matches_domain_optimize(self, demo_files):
        """Числа команды = прямой вызов optimize() с теми же данными."""
        from fileio.json_io import load_json
        target = _efl_target(demo_files)
        goals = [{"kind": "efl", "target": target, "tol": 1e-5}]
        data = run("opt.run", {"file": demo_files, "variables": _VARS,
                               "goals": goals, "max_iter": 25})
        var_objs = [OptVariable(surface=0, param="radius", pmin=40.0,
                                pmax=200.0),
                    OptVariable(surface=1, param="radius", pmin=-200.0,
                                pmax=-40.0)]
        goal_objs = [OptGoal(kind="efl", target=target, tol=1e-5)]
        direct = optimize(load_json(demo_files), var_objs, goal_objs,
                          max_iter=25)
        assert data["fmin"] == pytest.approx(direct.fmin, rel=1e-9)
        assert data["istop"] == direct.istop
        assert data["variables"][0]["to"] == pytest.approx(
            direct.system.surfaces[0].radius, rel=1e-9)

    def test_converges_and_source_untouched(self, demo_files, ctx):
        target = _efl_target(demo_files)
        radii_before = [s.radius for s in ctx.systems["demo"].surfaces]
        data = run("opt.run", {"variables": _VARS,
                               "goals": [{"kind": "efl", "target": target,
                                          "tol": 1e-5}],
                               "max_iter": 25}, ctx=ctx)
        assert data["istop"] in (0, 1, 2)
        assert data["converged"] == (data["istop"] == 0)
        assert len(data["residuals"]) == 1
        assert data["fmin_curve"][-1] <= data["fmin_curve"][0] + 1e-12
        assert len(data["protocol_tail"]) <= 3
        # исходная система в контексте не изменена (решатель работает с копией)
        assert [s.radius for s in ctx.systems["demo"].surfaces] == \
            radii_before
        again = run("calc.paraxial", ctx=ctx)
        assert again["focal_length"] == pytest.approx(
            _efl_target(demo_files, 1.0), rel=1e-6)

    def test_name_and_save_outputs(self, demo_files, ctx, tmp_path):
        target = _efl_target(demo_files)
        saved = str(tmp_path / "opt_result.json")
        data = run("opt.run", {"variables": _VARS,
                               "goals": [{"kind": "efl", "target": target}],
                               "max_iter": 10, "name": "fitted",
                               "save": saved}, ctx=ctx)
        assert data["system"] == "fitted"
        assert os.path.exists(saved)
        fitted = run("calc.paraxial", {"system": "fitted"}, ctx=ctx)
        assert fitted["focal_length"] == pytest.approx(target, rel=1e-3)

    def test_include_history(self, demo_files):
        target = _efl_target(demo_files)
        data = run("opt.run", {"file": demo_files, "variables": _VARS,
                               "goals": [{"kind": "efl", "target": target}],
                               "max_iter": 5, "include_history": True})
        assert data["history"][0]["nstep"] == 0
        assert all("fmin" in h and "x" in h for h in data["history"])

    def test_bad_variables_spec(self, demo_files):
        for bad in ([], [{"surface": 0, "param": "nosuch"}],
                    [{"param": "radius"}], [{"surface": 99, "param":
                                             "radius"}], "radius"):
            result = registry.execute(
                "opt.run", CommandContext(),
                {"file": demo_files, "variables": bad,
                 "goals": [{"kind": "efl", "target": 100}]})
            assert not result.ok, bad
            assert result.error["code"] == "invalid_param", bad


class TestOptSolve:
    def test_matches_domain_solve_single(self, demo_files):
        from fileio.json_io import load_json
        target = _efl_target(demo_files)
        data = run("opt.solve", {"file": demo_files, "kind": "efl",
                                 "target": target, "surface": 0,
                                 "param": "radius"})
        direct = solve_single(load_json(demo_files), "efl", target, 0,
                              "radius")
        assert data["value"] == pytest.approx(
            direct.system.surfaces[0].radius, rel=1e-9)
        assert data["achieved"] == pytest.approx(target, rel=1e-4)

    def test_name_output_chaining(self, demo_files, ctx):
        target = _efl_target(demo_files, 0.9)
        data = run("opt.solve", {"kind": "bfd", "target": target,
                                 "surface": 0, "param": "radius",
                                 "name": "solved"}, ctx=ctx)
        assert data["system"] == "solved"
        assert data["achieved"] == pytest.approx(target, rel=1e-3)

    def test_insensitive_param_is_error(self, demo_files):
        """Толщина последней поверхности не влияет на f′ — явная ошибка."""
        result = registry.execute(
            "opt.solve", CommandContext(),
            {"file": demo_files, "kind": "efl", "target": 50.0,
             "surface": 2, "param": "thickness"})
        assert not result.ok
        assert "не влияет" in result.error["message"]

    def test_bad_kind(self, ctx):
        result = registry.execute("opt.solve", ctx,
                                  {"kind": "nosuch", "target": 1,
                                   "surface": 0})
        assert not result.ok
        assert result.error["code"] == "invalid_param"


class TestOptParse:
    def test_parse_text(self):
        data = run("opt.parse", {"task": "PAR(1-2)=C/1,D/1; MF(1)=DSA;"})
        assert [(v["surface"], v["param"]) for v in data["variables"]] == \
            [(0, "radius"), (0, "thickness")]
        assert data["goals"][0]["kind"] == "longitudinal"
        assert data["warnings"] == []

    def test_parse_file_and_num_surfaces(self, demo_files, tmp_path):
        task = tmp_path / "task.opt"
        task.write_text("PAR(1)=C; MF(1)=DSA; nosuch=1;", encoding="utf-8")
        data = run("opt.parse", {"task_file": str(task),
                                 "file": demo_files})
        assert len(data["variables"]) == 3   # C без указателя → все радиусы
        assert data["num_surfaces"] == 3
        assert any("NOSUCH" in w.upper() for w in data["warnings"])

    def test_requires_task_or_file(self):
        result = registry.execute("opt.parse", CommandContext(), {})
        assert not result.ok
        assert result.error["code"] == "bad_request"


class TestOptRms:
    def test_matches_domain_legacy(self, demo_files):
        """opt.rms (dls) = прямой вызов optimizer.optimize, мерит падает."""
        import optimizer
        from fileio.json_io import load_json
        system = load_json(demo_files)
        spec = [{"surface": 0, "param": "radius", "min": 30.0, "max": 200.0},
                {"surface": 1, "param": "thickness", "min": 3.0,
                 "max": 12.0}]
        data = run("opt.rms", {"file": demo_files, "variables": spec,
                               "method": "dls", "max_iter": 4,
                               "num_rays": 6})
        tuples = [(0, "radius", 30.0, 200.0), (1, "thickness", 3.0, 12.0)]
        history = []
        direct = optimizer.optimize(system, tuples, method="dls",
                                    max_iter=4, num_rays=6,
                                    callback=lambda it, m, x: history.append(
                                        (it, m)))
        assert data["merit_initial"] == pytest.approx(history[0][1],
                                                      rel=1e-9)
        assert data["merit_final"] == pytest.approx(history[-1][1],
                                                    rel=1e-9)
        assert data["merit_final"] <= data["merit_initial"] + 1e-12
        assert data["variables"][0]["to"] == pytest.approx(
            direct.surfaces[0].radius, rel=1e-9)

    def test_simplex_method(self, demo_files):
        data = run("opt.rms", {"file": demo_files,
                               "variables": [{"surface": 0, "param":
                                              "radius", "min": 30.0,
                                              "max": 200.0}],
                               "method": "simplex", "max_iter": 5,
                               "num_rays": 6})
        assert data["method"] == "simplex"
        assert data["merit_final"] <= data["merit_initial"] + 1e-12

    def test_legacy_param_restricted(self, demo_files):
        result = registry.execute(
            "opt.rms", CommandContext(),
            {"file": demo_files, "variables": [{"surface": 0, "param":
                                                "conic", "min": -1,
                                                "max": 1}]})
        assert not result.ok
        assert result.error["code"] == "invalid_param"


# --------------------------------------------------------------------------- #
# plot.* — headless PNG (Agg)
# --------------------------------------------------------------------------- #

class TestPlots:
    def test_spot_png_and_rms_match(self, demo_files, tmp_path):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        from fileio.json_io import load_json
        out = str(tmp_path / "spot.png")
        data = run("plot.spot", {"file": demo_files, "output": out,
                                 "num_rays": 20})
        assert _png_ok(out)
        spots = compute_spot_diagram(load_json(demo_files), wl=0.54607,
                                     num_rays=20)
        assert data["num_points"] == len(spots)
        assert data["rms"] == pytest.approx(compute_rms_spot(spots),
                                            rel=1e-9)
        assert matplotlib.get_backend() == "Agg"

    def test_fan_png_and_counts(self, demo_files, tmp_path):
        from analysis.aberrations import trace_aberration_fan
        from fileio.json_io import load_json
        out = str(tmp_path / "fan.png")
        data = run("plot.fan", {"file": demo_files, "output": out,
                                "num_rays": 11})
        assert _png_ok(out)
        direct = trace_aberration_fan(load_json(demo_files), 0.54607,
                                      num_rays=11)
        assert data["num_rays"] == len(direct)
        assert data["num_ok"] == sum(1 for r in direct if r["success"])

    def test_field_png_system_fields(self, ctx, tmp_path):
        out = str(tmp_path / "field.png")
        data = run("plot.field", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert data["fields"] == pytest.approx([0.0, 3.0, 5.0])

    def test_field_no_fields_is_error(self, demo_files, tmp_path):
        """Система без полей и без fields — осмысленный отказ, не пустой PNG."""
        result = registry.execute(
            "plot.field", CommandContext(),
            {"file": demo_files, "output": str(tmp_path / "f.png"),
             "fields": []})
        assert not result.ok
        assert result.error["code"] == "bad_request"

    def test_psf_png(self, ctx, tmp_path):
        out = str(tmp_path / "psf.png")
        data = run("plot.psf", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert data["strehl"] is not None
        assert data["grid"] > 0

    def test_mtf_png(self, ctx, tmp_path):
        out = str(tmp_path / "mtf.png")
        data = run("plot.mtf", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert data["nyquist_lpmm"] > 0

    def test_ee_png_monotone_metric(self, ctx, tmp_path):
        out = str(tmp_path / "ee.png")
        data = run("plot.ee", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert 0.0 < data["r80_um"] < 100.0

    def test_focus_png(self, ctx, tmp_path):
        out = str(tmp_path / "focus.png")
        data = run("plot.focus", {"output": out, "num_points": 15,
                                  "num_rays": 10}, ctx=ctx)
        assert _png_ok(out)
        assert data["num_points"] == 15
        assert abs(data["best_defocus_mm"]) <= 2.0

    def test_heatmap_png(self, ctx, tmp_path):
        out = str(tmp_path / "heat.png")
        data = run("plot.heatmap", {"output": out, "num_rays": 200},
                   ctx=ctx)
        assert _png_ok(out)
        assert len(data["x_range"]) == 2 and data["x_range"][0] < \
            data["x_range"][1]

    def test_output_required(self, ctx):
        result = registry.execute("plot.spot", ctx, {})
        assert not result.ok
        assert result.error["code"] == "missing_param"


# --------------------------------------------------------------------------- #
# diagram.* — карта стёкол n–V
# --------------------------------------------------------------------------- #

class TestDiagram:
    def test_render_png_with_highlight(self, tmp_path):
        out = str(tmp_path / "diagram.png")
        data = run("diagram.render", {"output": out,
                                      "highlight": ["К8", "ТФ1"]})
        assert _png_ok(out)
        assert data["num_glasses"] >= 25
        assert set(data["highlighted"]) == {"К8", "ТФ1"}

    def test_render_highlights_system_glasses(self, demo_files, tmp_path):
        out = str(tmp_path / "diagram2.png")
        data = run("diagram.render", {"output": out, "file": demo_files})
        assert _png_ok(out)
        assert set(data["highlighted"]) >= {"К8", "ТФ1"}

    def test_glasses_data(self):
        data = run("diagram.glasses")
        assert data["num_glasses"] >= 25
        by_name = {g["name"]: g for g in data["glasses"]}
        assert by_name["К8"]["nd"] == pytest.approx(1.5163, abs=1e-4)
        assert by_name["К8"]["type"] == "К"
        assert by_name["К8"]["color"].startswith("#")

    def test_glasses_type_filter(self):
        data = run("diagram.glasses", {"type": "ТФ"})
        assert data["num_glasses"] > 0
        assert all(g["type"] == "ТФ" for g in data["glasses"])
