"""JSONL-REPL реестра команд (subprocess): протокол, состояние, паритет с CLI.

Волна 1 Command Registry (TASK_COMMANDS_W1): tests/test_commands_repl.py.
"""
import json
import subprocess
import sys

import pytest

from tests._commands_proc import (
    REPO_ROOT,
    make_demo_system,
    run_cli_json,
    run_repl,
)


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    return make_demo_system(
        str(tmp_path_factory.mktemp("repl_demo") / "demo_achromat"))


class TestProtocol:
    def test_id_echo_and_ok_shape(self, demo_json):
        proc, responses = run_repl([
            {"id": 1, "cmd": "calc.paraxial",
             "args": {"file": demo_json}},
            {"id": "alpha", "cmd": "file.formats", "args": {}},
        ])
        assert proc.returncode == 0
        assert len(responses) == 2
        assert responses[0]["id"] == 1 and responses[0]["ok"] is True
        assert "data" in responses[0] and "error" not in responses[0]
        assert responses[1]["id"] == "alpha"   # id любого JSON-типа

    def test_one_line_per_request_flushed(self, demo_json):
        proc, responses = run_repl([
            {"id": i, "cmd": "file.formats", "args": {}}
            for i in range(5)])
        assert len(proc.stdout.strip().splitlines()) == 5
        assert [r["id"] for r in responses] == list(range(5))

    def test_error_response_shape(self):
        proc, responses = run_repl([
            {"id": 1, "cmd": "no.such.command", "args": {}}])
        assert proc.returncode == 0  # ошибка команды ≠ падение REPL
        assert responses[0] == {
            "id": 1, "ok": False,
            "error": {"code": "unknown_command",
                      "message": responses[0]["error"]["message"]}}

    def test_bad_json_line_does_not_kill_repl(self, demo_json):
        """Битая строка → bad_request, сессия жива, EOF → exit 0."""
        lines = "{broken json"
        payload = json.dumps({"cmd": "file.formats"})
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "commands", "repl"],
            input=f"{lines}\n{payload}\n",
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT), timeout=180)
        assert proc.returncode == 0
        out = [json.loads(x) for x in proc.stdout.strip().splitlines()]
        assert out[0]["ok"] is False
        assert out[0]["error"]["code"] == "bad_request"
        assert out[1]["ok"] is True

    def test_missing_cmd_field(self):
        proc, responses = run_repl([{"id": 7, "args": {}}])
        assert responses[0]["error"]["code"] == "bad_request"

    def test_comments_and_empty_lines_skipped(self):
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "commands", "repl"],
            input="\n# comment\n\n",
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT), timeout=180)
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""


class TestStatefulSession:
    def test_load_then_calc_without_file(self, demo_json):
        proc, responses = run_repl([
            {"id": 1, "cmd": "system.load",
             "args": {"file": demo_json}},
            {"id": 2, "cmd": "calc.paraxial", "args": {}},
        ])
        assert all(r["ok"] for r in responses)
        assert responses[1]["data"]["focal_length"] > 0

    def test_mutation_persists_across_requests(self, demo_json):
        """system.surface.set меняет текущую систему для последующих команд."""
        proc, responses = run_repl([
            {"id": 1, "cmd": "system.load",
             "args": {"file": demo_json}},
            {"id": 2, "cmd": "calc.paraxial", "args": {}},
            {"id": 3, "cmd": "system.surface.set",
             "args": {"index": 0, "radius": 40.0}},
            {"id": 4, "cmd": "calc.paraxial", "args": {}},
        ])
        assert all(r["ok"] for r in responses), responses
        f_before = responses[1]["data"]["focal_length"]
        f_after = responses[3]["data"]["focal_length"]
        assert f_before != f_after

    def test_named_systems_coexist(self, demo_json):
        proc, responses = run_repl([
            {"id": 1, "cmd": "system.load",
             "args": {"file": demo_json, "name": "achromat"}},
            {"id": 2, "cmd": "system.new",
             "args": {"demo": "mirror", "name": "mirror"}},
            {"id": 3, "cmd": "system.surfaces.list",
             "args": {"system": "achromat"}},
            {"id": 4, "cmd": "system.current", "args": {}},
        ])
        assert all(r["ok"] for r in responses), responses
        assert responses[2]["data"]["num_surfaces"] == 3
        assert responses[3]["data"]["num_surfaces"] == 2
        assert responses[3]["data"]["name_in_context"] == "mirror"

    def test_current_without_load(self):
        proc, responses = run_repl([
            {"id": 1, "cmd": "system.current", "args": {}}])
        assert responses[0]["ok"] is False
        assert responses[0]["error"]["code"] == "not_found"


class TestParityWithCli:
    def test_repl_result_equals_cli_result(self, demo_json):
        """Критерий ТЗ: load → calc в REPL = вызов той же команды через CLI."""
        proc, responses = run_repl([
            {"id": 1, "cmd": "system.load",
             "args": {"file": demo_json}},
            {"id": 2, "cmd": "calc.paraxial", "args": {}},
        ])
        cli_proc, cli_payload = run_cli_json(
            ["run", "calc.paraxial", "--param", f"file={demo_json}"])
        assert cli_proc.returncode == 0
        repl_data = responses[1]["data"]
        cli_data = cli_payload["data"]
        assert repl_data["focal_length"] == cli_data["focal_length"]
        assert repl_data["back_focal_distance"] == \
            cli_data["back_focal_distance"]
        assert repl_data["entrance_pupil_diameter"] == \
            cli_data["entrance_pupil_diameter"]

    def test_repl_utf8_payload(self, demo_json):
        """Русские имена систем/стёкол проходят канал без потерь."""
        proc, responses = run_repl([
            {"id": 1, "cmd": "system.load",
             "args": {"file": demo_json}},
            {"id": 2, "cmd": "catalog.glass.get",
             "args": {"name": "К8"}},
        ])
        assert responses[1]["ok"]
        assert responses[1]["data"]["name"] == "К8"
        assert responses[0]["data"]["system"]["glasses"][0] == "К8"
