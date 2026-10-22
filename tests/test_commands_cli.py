"""CLI реестра команд (subprocess): list/info/schema/run + --json.

Волна 1 Command Registry (TASK_COMMANDS_W1): tests/test_commands_cli.py.
"""
import json

import pytest

from tests._commands_proc import make_demo_system, run_cli, run_cli_json


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    """Демо-система, сгенерированная самим CLI (system.new+save)."""
    return make_demo_system(
        str(tmp_path_factory.mktemp("cli_demo") / "demo_achromat"))


class TestList:
    def test_list_json_valid(self):
        proc, payload = run_cli_json(["list"])
        assert proc.returncode == 0
        assert payload["total"] >= 30
        names = [c["name"] for c in payload["commands"]]
        assert "calc.paraxial" in names
        assert "file.open" in names
        assert "system.new" in names
        assert "analyze.psf" in names
        # каждая схема полная: категория + параметры с типами
        for cmd in payload["commands"]:
            assert cmd["category"]
            for p in cmd["params"]:
                assert p["type"] in ("str", "float", "int", "bool",
                                     "list", "dict")

    def test_list_category_filter(self):
        proc, payload = run_cli_json(["list", "--category", "calc"])
        assert proc.returncode == 0
        names = [c["name"] for c in payload["commands"]]
        assert names and all(n.startswith("calc.") for n in names)

    def test_list_unknown_category_fails(self):
        proc = run_cli(["list", "--category", "nope", "--json"])
        assert proc.returncode != 0

    def test_list_plain_text(self):
        proc = run_cli(["list"])
        assert proc.returncode == 0
        assert "calc.paraxial" in proc.stdout


class TestInfoAndSchema:
    def test_info_shows_params(self):
        proc = run_cli(["info", "calc.paraxial"])
        assert proc.returncode == 0
        assert "calc.paraxial" in proc.stdout
        assert "wl" in proc.stdout          # параметр схемы
        assert "lbo_index" in proc.stdout

    def test_info_unknown_command(self):
        proc = run_cli(["info", "no.such"])
        assert proc.returncode != 0
        assert "no.such" in proc.stderr

    def test_schema_json_all_commands(self):
        proc, payload = run_cli_json(["schema"])
        assert proc.returncode == 0
        assert payload["total"] == len(payload["commands"])
        assert "calc.beam_geometry" in payload["commands"]


class TestRun:
    def test_run_no_json_flag(self, demo_json):
        """Без --json в stdout — сам data (JSON-читаемый)."""
        proc = run_cli(["run", "calc.paraxial",
                        "--param", f"file={demo_json}"])
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert 90 < abs(data["focal_length"]) < 110

    def test_run_paraxial_json(self, demo_json):
        proc, payload = run_cli_json(
            ["run", "calc.paraxial", "--param", f"file={demo_json}"])
        assert proc.returncode == 0
        assert payload["ok"] is True
        data = payload["data"]
        assert data["focal_length"] > 0
        assert data["f_number"] > 0
        assert "sP" in data and "sP_prime" in data

    def test_run_opj_file_end_to_end(self, tmp_path, demo_json):
        """Критерий ТЗ: run calc.paraxial --param file=…opj --json → числа."""
        opj = str(tmp_path / "demo.opj")
        proc, payload = run_cli_json(
            ["run", "file.save", "--param", f"src={demo_json}",
             "--param", f"file={opj}"])
        assert proc.returncode == 0, payload
        proc, payload = run_cli_json(
            ["run", "calc.paraxial", "--param", f"file={opj}"])
        assert proc.returncode == 0
        assert payload["data"]["focal_length"] > 0

    def test_run_typed_params_parsed_by_schema(self, tmp_path, demo_json):
        """--param строки приводятся к типам: wl=float, fields=list."""
        proc, payload = run_cli_json(
            ["run", "analyze.field_aberrations",
             "--param", f"file={demo_json}",
             "--param", "fields=[0.0,3.0]",
             "--param", "num_fan_rays=7"])
        assert proc.returncode == 0, payload
        fields = payload["data"]["fields"]
        assert [f["field_y"] for f in fields] == [0.0, 3.0]

    def test_run_missing_required_param(self):
        proc, payload = run_cli_json(
            ["run", "file.open"], expect_ok=False)
        assert proc.returncode != 0
        assert payload["ok"] is False
        assert payload["error"]["code"] == "missing_param"

    def test_run_error_json_to_stderr_nonzero(self, demo_json):
        """Ошибки: ненулевой exit + JSON в stderr при --json."""
        proc, payload = run_cli_json(
            ["run", "calc.paraxial",
             "--param", f"file={demo_json}", "--param", "wl=abc"],
            expect_ok=False)
        assert proc.returncode != 0
        assert payload["error"]["code"] == "invalid_param"
        assert proc.stdout.strip() == ""  # stdout чист при ошибке

    def test_run_unknown_command(self):
        proc, payload = run_cli_json(["run", "no.such"], expect_ok=False)
        assert proc.returncode != 0
        assert payload["error"]["code"] == "unknown_command"

    def test_run_stateless_no_hidden_system(self, demo_json):
        """CLI stateless: file.save не оставляет системы другим командам."""
        proc, payload = run_cli_json(["run", "calc.paraxial"],
                                     expect_ok=False)
        assert proc.returncode != 0
        assert payload["error"]["code"] == "no_system"


class TestCliContract:
    def test_plain_error_to_stderr(self, demo_json):
        proc = run_cli(["run", "calc.paraxial",
                        "--param", f"file={demo_json}",
                        "--param", "wl=abc"])
        assert proc.returncode != 0
        assert "invalid_param" in proc.stderr
        assert proc.stdout.strip() == ""

    def test_help_lists_subcommands(self):
        proc = run_cli(["--help"])
        assert proc.returncode == 0
        for sub in ("list", "info", "schema", "run", "repl"):
            assert sub in proc.stdout

    def test_no_qt_imported(self):
        """Жёсткое правило ТЗ №1: import commands без Qt/QApplication."""
        proc = run_cli(["list", "--category", "file", "--json"])
        assert proc.returncode == 0
        assert "Qt" not in proc.stderr and "QApplication" not in proc.stderr
