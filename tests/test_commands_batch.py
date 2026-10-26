"""Пакет R500-15: пакетные прогоны (commands/builtin/batch_cmds.py).

Три уровня проверки (как соседние R500-пакеты):
* smoke — каждая новая команда выполняется и даёт строгий JSON;
* числа — метрики пакета совпадают с одиночными прогонами тех же
  движков (batch.metric vs calc.paraxial, batch.apply → удвоение EFL);
* устойчивость — ошибки отдельных файлов (мусор/пропавший путь) не
  роняют пакет, а попадают в errors[]; пустой список / ни одного
  валидного — invalid_param (инвариант ТЗ §пакетных прогонов).

Демо-файлы генерируются самим реестром (system.new/system.achromat +
save) в tmp_path — локальных данных (extracted/) не требуется;
.lbo-хвост — отдельный класс с маркером requires_lbo.
"""
import json
import os

import pytest

from commands import CommandContext, default_registry
from tests.conftest import requires_lbo_of

#: Новые команды пакета R500-15 (категория batch).
BATCH_EXPECTED = frozenset({
    "batch.metrics", "batch.dir", "batch.names", "batch.info",
    "batch.load", "batch.run", "batch.validate", "batch.metric",
    "batch.summary", "batch.rank", "batch.stats", "batch.filter",
    "batch.check", "batch.compare", "batch.apply", "batch.changes",
    "batch.convert", "batch.dedupe", "batch.export", "batch.report",
})

#: Ожидаемое число метрик пакета (справочник batch.metrics).
BATCH_METRICS_COUNT = 21

#: EFL демо-систем (system.new achromat ≈ 100, system.achromat f=200).
ACHROMAT_EFL = 100.0
SECOND_EFL = 200.0


# --------------------------------------------------------------------------- #
# Фикстуры: пакет демо-систем, сгенерированный самим реестром
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def pkg(tmp_path_factory):
    """Пакет из 3 систем (.json) + .opj-копия + мусор + пропавший путь.

    Возвращает dict: a/b/c (.json), a_opj, garbage, missing, dir.
    """
    tmp = tmp_path_factory.mktemp("commands_r500_15")
    ctx = CommandContext()

    def _new(demo, out):
        result = default_registry.execute(
            "system.new", ctx, {"demo": demo, "save": out})
        assert result.ok, f"system.new {demo}: {result.error}"
        return out

    a = _new("achromat", str(tmp / "achromat.json"))
    b_result = default_registry.execute(
        "system.achromat", ctx,
        {"focal_length": SECOND_EFL, "out": str(tmp / "double.json")})
    assert b_result.ok, b_result.error
    b = str(tmp / "double.json")
    c = _new("mirror", str(tmp / "mirror.json"))
    a_opj = str(tmp / "achromat.opj")
    result = default_registry.execute(
        "file.save", ctx, {"src": a, "file": a_opj})
    assert result.ok, result.error
    garbage = str(tmp / "garbage.opj")
    with open(garbage, "wb") as f:
        f.write(b"\x00\x01not-an-opj-file")
    return {"a": a, "b": b, "c": c, "a_opj": a_opj,
            "garbage": garbage, "missing": str(tmp / "missing.json"),
            "dir": str(tmp), "files": [a, b, c]}


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    """Выполнить команду, ожидая ошибку с данным кодом."""
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error
    return result.error


def _strict_json(data):
    """Контракт: результат строго JSON-сериализуем (без NaN/Inf)."""
    json.dumps(data, ensure_ascii=False, allow_nan=False)


@pytest.fixture(scope="session")
def lens_lbo():
    """Путь к LENS.LBO (локальные extracted-данные; как в lbo-тестах)."""
    from catalog.library import LBO_DIR
    return os.path.join(LBO_DIR, "LENS.LBO")


# --------------------------------------------------------------------------- #
# Инвариант набора + smoke всех команд пакета
# --------------------------------------------------------------------------- #

class TestBatchRegistry:
    def test_batch_commands_registered(self):
        assert BATCH_EXPECTED <= set(default_registry.names())
        assert all(default_registry.get(n).category == "batch"
                   for n in BATCH_EXPECTED)

    def test_smoke_all_commands_strict_json(self, pkg):
        args = {
            "batch.metrics": {},
            "batch.dir": {"path": pkg["dir"]},
            "batch.names": {"files": pkg["files"]},
            "batch.info": {"files": [pkg["a_opj"], pkg["a"]]},
            "batch.load": {"files": pkg["files"]},
            "batch.run": {"files": pkg["files"], "cmd": "calc.paraxial",
                          "include_data": True},
            "batch.validate": {"files": pkg["files"]},
            "batch.metric": {"files": pkg["files"], "metric": "efl"},
            "batch.summary": {"files": pkg["files"]},
            "batch.rank": {"files": pkg["files"], "metric": "efl"},
            "batch.stats": {"files": pkg["files"], "metric": "efl"},
            "batch.filter": {"files": pkg["files"], "metric": "efl",
                             "op": "ge", "value": 50.0},
            "batch.check": {"files": pkg["files"], "metric": "efl",
                            "threshold": 50.0},
            "batch.compare": {"ref": pkg["a"], "files": pkg["files"]},
            "batch.apply": {"files": pkg["files"][:1], "cmd": "system.scale",
                            "args": {"factor": 2.0},
                            "out_dir": os.path.join(pkg["dir"], "apply")},
            "batch.changes": {"files": pkg["files"][:1],
                              "cmd": "system.scale",
                              "args": {"factor": 2.0}},
            "batch.convert": {"files": [pkg["a_opj"]],
                              "out_dir": os.path.join(pkg["dir"], "conv")},
            "batch.dedupe": {"files": pkg["files"]},
            "batch.export": {"files": pkg["files"],
                             "out": os.path.join(pkg["dir"], "b.csv")},
            "batch.report": {"files": pkg["files"]},
        }
        assert set(args) == set(BATCH_EXPECTED)
        ctx = CommandContext()
        for name, call in sorted(args.items()):
            data = run(name, call, ctx=ctx)
            _strict_json(data)


# --------------------------------------------------------------------------- #
# batch.metrics — справочник
# --------------------------------------------------------------------------- #

class TestBatchMetrics:
    def test_catalog_contents(self):
        data = run("batch.metrics")
        assert data["count"] == BATCH_METRICS_COUNT
        by_name = {m["name"]: m for m in data["metrics"]}
        for name in ("efl", "f_number", "spot_rms", "strehl", "SI",
                     "d90_um", "cutoff_lpmm"):
            assert name in by_name
        assert by_name["strehl"]["better"] == "max"
        assert by_name["spot_rms"]["better"] == "min"
        assert by_name["efl"]["unit"] == "мм"
        assert all(m["description"] for m in data["metrics"])

    def test_catalog_matches_choices(self):
        data = run("batch.metrics")
        names = {m["name"] for m in data["metrics"]}
        schema = run("registry.schema", {"name": "batch.metric"})
        choices = set(schema["params"][1]["choices"])
        assert names == choices


# --------------------------------------------------------------------------- #
# batch.dir — скан каталога
# --------------------------------------------------------------------------- #

class TestBatchDir:
    def test_default_extensions(self, pkg):
        data = run("batch.dir", {"path": pkg["dir"]})
        found = {os.path.basename(p) for p in data["files"]}
        assert {"achromat.json", "double.json", "mirror.json",
                "achromat.opj", "garbage.opj"} <= found
        assert data["count"] == len(data["files"]) == len(set(data["files"]))
        assert data["files"] == sorted(data["files"])
        assert not data["recursive"]
        assert data["skipped"] >= 0

    def test_filter_and_recursive(self, pkg, tmp_path):
        data = run("batch.dir", {"path": pkg["dir"],
                                 "extensions": ["json"]})
        assert data["files"] and all(
            p.endswith(".json") for p in data["files"])
        nested = tmp_path / "scan"
        (nested / "sub").mkdir(parents=True)
        (nested / "root.opj").write_bytes(b"")
        (nested / "sub" / "deep.opj").write_bytes(b"")
        flat = run("batch.dir", {"path": str(nested),
                                 "extensions": ["opj"]})
        deep = run("batch.dir", {"path": str(nested), "extensions": [".opj"],
                                 "recursive": True})
        assert flat["count"] == 1
        assert deep["count"] == 2

    def test_missing_dir_is_io_error(self):
        fail("batch.dir", {"path": "Z:/no/such/dir"}, "io_error")


# --------------------------------------------------------------------------- #
# batch.names / batch.info / batch.load — обзор и загрузка
# --------------------------------------------------------------------------- #

class TestBatchOverview:
    def test_names_with_errors(self, pkg):
        data = run("batch.names", {"files": pkg["files"] + [pkg["garbage"],
                                                            pkg["missing"]]})
        assert data["ok"] == 3 and len(data["errors"]) == 2
        # мусорный .opj эвристика читает в пустую систему → invalid_param,
        # пропавший путь → io_error
        assert {e["code"] for e in data["errors"]} <= {
            "invalid_param", "internal_error", "io_error"}
        names = {row["file"]: row for row in data["names"]}
        assert names[pkg["a"]]["num_surfaces"] == 3
        assert names[pkg["a"]]["stem"] == "achromat"

    def test_info_formats_and_sizes(self, pkg):
        data = run("batch.info", {"files": [pkg["a"], pkg["a_opj"],
                                            pkg["missing"]]})
        assert data["ok"] == 2 and len(data["errors"]) == 1
        rows = {row["file"]: row for row in data["rows"]}
        assert rows[pkg["a"]]["format"] == "json"
        assert rows[pkg["a_opj"]]["format"] == "opj"
        assert rows[pkg["a"]]["size_bytes"] > 0
        assert rows[pkg["a"]]["num_wavelengths"] == 3

    def test_load_into_context_no_current(self, pkg):
        ctx = CommandContext()
        data = run("batch.load", {"files": pkg["files"]}, ctx=ctx)
        assert data["count"] == 3
        assert {row["name"] for row in data["loaded"]} == {
            "achromat", "double", "mirror"}
        assert ctx.current_name is None  # текущую не трогаем
        assert all(name in ctx.systems for name in
                   ("achromat", "double", "mirror"))

    def test_load_collision_gets_suffix(self, pkg):
        ctx = CommandContext()
        data = run("batch.load", {"files": [pkg["a"], pkg["a"]]}, ctx=ctx)
        names = sorted(row["name"] for row in data["loaded"])
        assert names == ["achromat", "achromat_2"]

    def test_empty_files_invalid_param(self):
        fail("batch.names", {"files": []}, "invalid_param")
        fail("batch.info", {"files": []}, "invalid_param")

    def test_all_invalid_invalid_param(self, pkg):
        fail("batch.names", {"files": [pkg["missing"], pkg["garbage"]]},
             "invalid_param")
        fail("batch.info", {"files": [pkg["missing"]]}, "invalid_param")


# --------------------------------------------------------------------------- #
# batch.run / batch.validate — прогон команд реестра
# --------------------------------------------------------------------------- #

class TestBatchRun:
    def test_run_matches_single_call(self, pkg):
        data = run("batch.run", {"files": pkg["files"],
                                 "cmd": "calc.paraxial",
                                 "include_data": True})
        assert data["command"] == "calc.paraxial"
        assert data["ok"] == data["count"] == 3 and not data["errors"]
        single = run("calc.paraxial", {"file": pkg["a"]})
        by_file = {row["file"]: row for row in data["rows"]}
        assert by_file[pkg["a"]]["data"]["focal_length"] == \
            pytest.approx(single["focal_length"], rel=1e-12)

    def test_run_without_data_compact(self, pkg):
        data = run("batch.run", {"files": pkg["files"],
                                 "cmd": "calc.seidel"})
        assert all("data" not in row for row in data["rows"])

    def test_run_per_file_errors(self, pkg):
        data = run("batch.run", {"files": [pkg["missing"], pkg["b"]],
                                 "cmd": "calc.paraxial"})
        assert data["ok"] == 1 and len(data["errors"]) == 1
        assert data["rows"][0]["ok"] is False

    def test_run_unknown_command(self, pkg):
        fail("batch.run", {"files": pkg["files"], "cmd": "ghost.cmd"},
             "unknown_command")

    def test_run_all_failed_invalid_param(self, pkg):
        fail("batch.run", {"files": [pkg["missing"]], "cmd": "calc.paraxial"},
             "invalid_param")


class TestBatchValidate:
    def test_rows_and_aggregate(self, pkg):
        data = run("batch.validate", {"files": pkg["files"]})
        assert data["count"] == 3 and not data["errors"]
        assert data["pass"] == all(r["valid"] for r in data["rows"])
        assert all("errors" in r and "warnings" in r
                   for r in data["rows"])

    def test_errors_do_not_drop_package(self, pkg):
        data = run("batch.validate", {"files": [pkg["missing"],
                                                pkg["a"]]})
        assert data["count"] == 1 and len(data["errors"]) == 1

    def test_all_failed_invalid_param(self, pkg):
        fail("batch.validate", {"files": [pkg["missing"]]},
             "invalid_param")


# --------------------------------------------------------------------------- #
# batch.metric / batch.summary — метрики
# --------------------------------------------------------------------------- #

class TestBatchMetric:
    def test_efl_matches_calc(self, pkg):
        data = run("batch.metric", {"files": pkg["files"], "metric": "efl"})
        assert data["unit"] == "мм" and data["better"] is None
        direct = run("calc.paraxial", {"file": pkg["a"]})
        by_file = {row["file"]: row for row in data["rows"]}
        assert by_file[pkg["a"]]["efl"] == pytest.approx(
            abs(direct["focal_length"]), rel=1e-9)
        assert by_file[pkg["b"]]["efl"] == pytest.approx(SECOND_EFL,
                                                         rel=0.05)

    def test_spot_metric_light_default(self, pkg):
        data = run("batch.metric", {"files": pkg["files"],
                                    "metric": "spot_rms"})
        assert all(row["spot_rms"] >= 0.0 for row in data["rows"])

    def test_seidel_metrics(self, pkg):
        for metric in ("SI", "SIV"):
            data = run("batch.metric", {"files": [pkg["a"]],
                                        "metric": metric})
            assert isinstance(data["rows"][0][metric], float)

    def test_bad_metric_choice(self, pkg):
        fail("batch.metric", {"files": pkg["files"], "metric": "nope"},
             "invalid_param")

    def test_errors_per_file(self, pkg):
        data = run("batch.metric", {"files": [pkg["a"], pkg["missing"]],
                                    "metric": "efl"})
        assert data["ok"] == 1 and len(data["errors"]) == 1


class TestBatchSummary:
    def test_default_columns_and_totals(self, pkg):
        data = run("batch.summary", {"files": pkg["files"]})
        assert set(data["metrics"]) == {"efl", "f_number", "num_surfaces",
                                        "track_length", "spot_rms"}
        efls = [row["efl"] for row in data["rows"]]
        assert data["summary"]["efl"]["min"] == pytest.approx(min(efls))
        assert data["summary"]["efl"]["max"] == pytest.approx(max(efls))
        assert data["summary"]["efl"]["mean"] == pytest.approx(
            sum(efls) / len(efls))
        assert data["summary"]["efl"]["max_file"].endswith("double.json")

    def test_explicit_metrics(self, pkg):
        data = run("batch.summary", {"files": pkg["files"],
                                     "metrics": ["num_surfaces",
                                                 "strehl"]})
        assert data["metrics"] == ["num_surfaces", "strehl"]
        assert "strehl" in data["summary"]

    def test_unknown_metric_invalid_param(self, pkg):
        fail("batch.summary", {"files": pkg["files"], "metrics": ["zz"]},
             "invalid_param")


# --------------------------------------------------------------------------- #
# batch.rank / batch.stats — ранжирование и статистика
# --------------------------------------------------------------------------- #

class TestBatchRank:
    def test_rank_efl_ascending(self, pkg):
        data = run("batch.rank", {"files": pkg["files"], "metric": "efl",
                                  "order": "asc"})
        values = [row["efl"] for row in data["rows"]]
        assert values == sorted(values)
        assert [row["rank"] for row in data["rows"]] == [1, 2, 3]
        assert data["best"]["file"] != data["worst"]["file"]

    def test_rank_auto_polarity_spot(self, pkg):
        data = run("batch.rank", {"files": pkg["files"],
                                  "metric": "spot_rms"})
        assert data["order"] == "asc"  # лучше меньше — первая
        values = [row["spot_rms"] for row in data["rows"]]
        assert values == sorted(values)

    def test_rank_top_limit(self, pkg):
        data = run("batch.rank", {"files": pkg["files"], "metric": "efl",
                                  "top": 1})
        assert len(data["rows"]) == 1 and data["count"] == 3


class TestBatchStats:
    def test_stats_values(self, pkg):
        data = run("batch.stats", {"files": pkg["files"], "metric": "efl"})
        efls = [run("calc.paraxial", {"file": f})["focal_length"]
                for f in pkg["files"]]
        assert data["count"] == 3
        assert data["min"] == pytest.approx(min(abs(e) for e in efls))
        assert data["mean"] == pytest.approx(
            sum(abs(e) for e in efls) / 3)
        assert data["stdev"] >= 0.0
        assert data["min_file"] != data["max_file"]

    def test_stats_single_file_stdev_zero(self, pkg):
        data = run("batch.stats", {"files": [pkg["a"]], "metric": "efl"})
        assert data["count"] == 1 and data["stdev"] == 0.0
        assert data["min"] == data["max"] == data["median"]

    def test_stats_empty_files_invalid_param(self, pkg):
        fail("batch.stats", {"files": [], "metric": "efl"},
             "invalid_param")


# --------------------------------------------------------------------------- #
# batch.filter / batch.check — отбор и пороги
# --------------------------------------------------------------------------- #

class TestBatchFilter:
    def test_ge_on_surfaces(self, pkg):
        data = run("batch.filter", {"files": pkg["files"],
                                    "metric": "num_surfaces", "op": "ge",
                                    "value": 3})
        assert data["total"] == 3 and data["count"] >= 1
        assert all(row["num_surfaces"] >= 3 for row in data["kept"])

    def test_range_on_efl(self, pkg):
        data = run("batch.filter", {"files": pkg["files"], "metric": "efl",
                                    "op": "range", "value_min": 150.0,
                                    "value_max": 250.0})
        assert data["count"] == 1
        assert data["kept"][0]["file"].endswith("double.json")

    def test_missing_value_invalid_param(self, pkg):
        fail("batch.filter", {"files": pkg["files"], "metric": "efl",
                              "op": "gt"}, "invalid_param")
        fail("batch.filter", {"files": pkg["files"], "metric": "efl",
                              "op": "range"}, "invalid_param")

    def test_inverted_range_invalid_param(self, pkg):
        fail("batch.filter", {"files": pkg["files"], "metric": "efl",
                              "op": "range", "value_min": 10.0,
                              "value_max": 1.0}, "invalid_param")


class TestBatchCheck:
    """Зеркало после .json-раундтрипа даёт efl=0 (нюанс данных движка),
    поэтому пороговые тесты — на ахромате и дублете (97.5 / 200 мм)."""

    def test_mode_min_pass(self, pkg):
        data = run("batch.check", {"files": [pkg["a"], pkg["b"]],
                                   "metric": "efl",
                                   "threshold": 50.0, "mode": "min"})
        assert data["comparison"] == "efl ≥ 50.0"
        assert data["pass"] is True and data["worst"] is None
        assert data["count"] == 2

    def test_mode_min_fail_with_worst(self, pkg):
        data = run("batch.check", {"files": [pkg["a"], pkg["b"]],
                                   "metric": "efl",
                                   "threshold": 150.0, "mode": "min"})
        assert data["pass"] is False
        assert data["worst"]["file"].endswith("achromat.json")
        assert sum(1 for r in data["rows"] if not r["pass"]) == 1

    def test_auto_mode_by_polarity(self, pkg):
        data = run("batch.check", {"files": [pkg["a"], pkg["b"]],
                                   "metric": "spot_rms",
                                   "threshold": 1e9})
        assert data["mode"] == "max"  # лучше меньше → верхняя граница
        assert data["pass"] is True

    def test_empty_files_invalid_param(self):
        fail("batch.check", {"files": [], "metric": "efl",
                             "threshold": 1.0}, "invalid_param")


# --------------------------------------------------------------------------- #
# batch.compare — сравнение с эталоном
# --------------------------------------------------------------------------- #

class TestBatchCompare:
    def test_deltas_vs_reference(self, pkg):
        data = run("batch.compare", {"ref": pkg["a"],
                                     "files": [pkg["b"], pkg["a"]]})
        assert data["count"] == 2 and not data["errors"]
        ref_efl = run("calc.paraxial", {"file": pkg["a"]})["focal_length"]
        row_b = next(r for r in data["rows"]
                     if r["file"].endswith("double.json"))
        delta_b = row_b["deltas"]["efl"]
        assert delta_b["ref"] == pytest.approx(abs(ref_efl), rel=1e-9)
        assert delta_b["delta"] > 0.0
        assert delta_b["delta_percent"] == pytest.approx(
            100.0 * delta_b["delta"] / delta_b["ref"])
        row_same = next(r for r in data["rows"]
                        if r["file"] == pkg["a"])
        assert row_same["deltas"]["efl"]["delta"] == pytest.approx(0.0)

    def test_bad_reference_invalid_param(self, pkg):
        fail("batch.compare", {"ref": pkg["missing"],
                               "files": pkg["files"]}, "invalid_param")


# --------------------------------------------------------------------------- #
# batch.apply / batch.changes — модификации
# --------------------------------------------------------------------------- #

class TestBatchApplyChanges:
    def test_apply_scales_copies(self, pkg, tmp_path):
        out_dir = str(tmp_path / "applied")
        data = run("batch.apply", {
            "files": pkg["files"], "cmd": "system.scale",
            "args": {"factor": 2.0}, "out_dir": out_dir})
        assert data["ok"] == 3 and not data["errors"]
        assert data["suffix"] == "_applied" and data["ext"] == "json"
        for row in data["applied"]:
            assert os.path.isfile(row["out"])
            before = run("calc.paraxial", {"file": row["file"]})
            after = run("calc.paraxial", {"file": row["out"]})
            assert after["focal_length"] == pytest.approx(
                2.0 * before["focal_length"], rel=1e-6)
        # исходники на месте, копии — только в out_dir
        assert sorted(os.listdir(out_dir)) == [
            "achromat_applied.json", "double_applied.json",
            "mirror_applied.json"]

    def test_apply_opj_format_and_suffix(self, pkg, tmp_path):
        out_dir = str(tmp_path / "opj_out")
        data = run("batch.apply", {
            "files": [pkg["a"]], "cmd": "system.reverse",
            "out_dir": out_dir, "suffix": "_rev", "ext": "opj"})
        assert data["applied"][0]["out"].endswith("achromat_rev.opj")
        assert os.path.isfile(data["applied"][0]["out"])

    def test_apply_unknown_command(self, pkg, tmp_path):
        fail("batch.apply", {"files": pkg["files"], "cmd": "ghost.mod",
                             "out_dir": str(tmp_path)}, "unknown_command")

    def test_apply_all_failed_invalid_param(self, pkg, tmp_path):
        fail("batch.apply", {"files": [pkg["missing"]], "cmd": "system.scale",
                             "args": {"factor": 2.0},
                             "out_dir": str(tmp_path / "x")},
             "invalid_param")

    def test_changes_before_after_delta(self, pkg):
        data = run("batch.changes", {
            "files": pkg["files"], "cmd": "system.scale",
            "args": {"factor": 2.0}})
        assert data["metrics"] == ["efl", "f_number", "spot_rms"]
        assert data["count"] == 3 and not data["errors"]
        for row in data["rows"]:
            before, delta = row["before"]["efl"], row["delta"]["efl"]
            assert delta == pytest.approx(before, rel=1e-6)  # ×2 − x = x
            assert row["delta"]["f_number"] is not None
            # исходник остался прежним: after считается по временной копии
            assert run("calc.paraxial",
                       {"file": row["file"]})["focal_length"] == \
                pytest.approx(before, rel=1e-9)

    def test_changes_errors_per_file(self, pkg):
        data = run("batch.changes", {
            "files": [pkg["missing"], pkg["a"]], "cmd": "system.scale",
            "args": {"factor": 2.0}})
        assert data["count"] == 1 and len(data["errors"]) == 1


# --------------------------------------------------------------------------- #
# batch.convert — пакетная конвертация
# --------------------------------------------------------------------------- #

class TestBatchConvert:
    def test_opj_to_json(self, pkg, tmp_path):
        out_dir = str(tmp_path / "conv")
        data = run("batch.convert", {"files": [pkg["a_opj"]],
                                     "out_dir": out_dir})
        assert data["ok"] == 1
        dst = data["converted"][0]["dst"]
        assert dst.endswith("achromat.json") and os.path.isfile(dst)
        system = run("calc.paraxial", {"file": dst})
        assert system["focal_length"] == pytest.approx(
            run("calc.paraxial", {"file": pkg["a"]})["focal_length"])

    def test_same_path_guard(self, pkg):
        # конвертация в каталог источника с тем же форматом → dst==src
        # → ошибка элемента; ни одной конвертации → invalid_param
        fail("batch.convert", {"files": [pkg["a"]], "out_dir": pkg["dir"]},
             "invalid_param")

    def test_no_silent_overwrite(self, pkg, tmp_path):
        out_dir = str(tmp_path / "twice")
        first = run("batch.convert", {"files": [pkg["a"]],
                                      "out_dir": out_dir})
        with open(first["converted"][0]["dst"], encoding="utf-8") as f:
            original = f.read()
        second = run("batch.convert", {"files": [pkg["a"]],
                                       "out_dir": out_dir})
        dst2 = second["converted"][0]["dst"]
        assert dst2.endswith("achromat_2.json")
        with open(first["converted"][0]["dst"], encoding="utf-8") as f:
            assert f.read() == original  # первая копия нетронута

    def test_all_failed_invalid_param(self, pkg, tmp_path):
        fail("batch.convert", {"files": [pkg["missing"]],
                               "out_dir": str(tmp_path)}, "invalid_param")


# --------------------------------------------------------------------------- #
# batch.dedupe — дубликаты по контрольной сумме
# --------------------------------------------------------------------------- #

class TestBatchDedupe:
    def test_duplicate_group_found(self, pkg):
        data = run("batch.dedupe", {"files": [pkg["a"], pkg["a"],
                                              pkg["b"], pkg["missing"]]})
        assert data["algo"] == "md5"
        assert data["total"] == 4 and data["unique"] == 2
        assert len(data["groups"]) == 1
        group = data["groups"][0]
        assert group["count"] == 2 and len(group["files"]) == 2
        assert data["num_duplicate_files"] == 2
        assert len(data["errors"]) == 1  # только missing

    def test_other_algo(self, pkg):
        data = run("batch.dedupe", {"files": [pkg["a"], pkg["a"]],
                                    "algo": "sha1"})
        assert data["algo"] == "sha1" and len(data["groups"]) == 1

    def test_bad_algo_choice(self, pkg):
        fail("batch.dedupe", {"files": pkg["files"], "algo": "crc32"},
             "invalid_param")

    def test_nothing_readable(self, pkg):
        fail("batch.dedupe", {"files": [pkg["missing"]]},
             "invalid_param")


# --------------------------------------------------------------------------- #
# batch.export / batch.report — выгрузка и свод
# --------------------------------------------------------------------------- #

class TestBatchExportReport:
    def test_export_csv(self, pkg, tmp_path):
        out = str(tmp_path / "summary.csv")
        data = run("batch.export", {"files": pkg["files"], "out": out})
        assert data["format"] == "csv" and data["rows"] == 3
        assert os.path.isfile(out)
        with open(out, encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        assert {"file", "name", "efl", "f_number"} <= set(header)

    def test_export_json(self, pkg, tmp_path):
        out = str(tmp_path / "summary.json")
        data = run("batch.export", {"files": pkg["files"], "out": out,
                                    "metrics": ["efl", "num_surfaces"]})
        assert data["format"] == "json"
        with open(out, encoding="utf-8") as f:
            rows = json.load(f)
        assert len(rows) == 3 and "efl" in rows[0]

    def test_export_unsupported_ext(self, pkg, tmp_path):
        fail("batch.export", {"files": pkg["files"],
                              "out": str(tmp_path / "x.txt")},
             "unsupported")

    def test_report_text(self, pkg):
        data = run("batch.report", {"files": pkg["files"] + [pkg["missing"]],
                                    "metrics": ["efl"]})
        text = data["text"]
        assert "Пакетный отчёт OPAL-OKB" in text
        assert "achromat.json" in text and "double.json" in text
        assert "Итоги:" in text and "efl [мм]" in text
        assert "Ошибки загрузки:" in text
        assert data["count"] == 3 and len(data["errors"]) == 1

    def test_report_writes_txt(self, pkg, tmp_path):
        out = str(tmp_path / "report.txt")
        data = run("batch.report", {"files": pkg["files"], "out": out})
        assert os.path.isfile(out)
        with open(out, encoding="utf-8") as f:
            assert "Пакетный отчёт" in f.read()
        assert data["out"].endswith("report.txt")
        assert data["size_bytes"] > 0

    def test_report_bad_out_ext(self, pkg, tmp_path):
        fail("batch.report", {"files": pkg["files"],
                              "out": str(tmp_path / "r.csv")},
             "unsupported")


# --------------------------------------------------------------------------- #
# .lbo-хвост: файлы пакета могут быть библиотеками (запись 0)
# --------------------------------------------------------------------------- #

@requires_lbo_of("LENS")
class TestBatchLboTail:
    """batch.* поверх .lbo (load_system выбирает запись 0) — только при
    локальных extracted-данных (конвенция conftest)."""

    def test_names_on_lbo(self, lens_lbo):
        data = run("batch.names", {"files": [lens_lbo]})
        assert data["ok"] == 1
        assert data["names"][0]["num_surfaces"] >= 1

    def test_metric_on_lbo(self, lens_lbo):
        data = run("batch.metric", {"files": [lens_lbo],
                                    "metric": "num_surfaces"})
        assert data["rows"][0]["num_surfaces"] >= 1
