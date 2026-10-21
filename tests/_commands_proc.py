"""Общий хелпер subprocess-тестов Command Registry (CLI/REPL)."""
import json
import os
import subprocess
import sys
from pathlib import Path

#: Корень репо (для cwd subprocess — импорты пакетов из корня).
REPO_ROOT = Path(__file__).resolve().parent.parent


def run_cli(args, expect_ok=True, timeout=180):
    """``py -m commands <args>`` → CompletedProcess (UTF-8, cwd=репо)."""
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "commands", *args],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(REPO_ROOT), timeout=timeout,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return proc


def run_cli_json(args, **kwargs):
    """CLI с --json: stdout (или stderr при ошибке) → распарсенный JSON."""
    proc = run_cli([*args, "--json"], **kwargs)
    payload = json.loads(proc.stdout if proc.returncode == 0
                         else proc.stderr)
    return proc, payload


def run_repl(requests, timeout=180):
    """REPL: список запросов → список ответов (один subprocess)."""
    lines = [json.dumps(r, ensure_ascii=False) for r in requests]
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "commands", "repl"],
        input="\n".join(lines), capture_output=True, text=True,
        encoding="utf-8", cwd=str(REPO_ROOT), timeout=timeout,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    responses = [json.loads(line)
                 for line in proc.stdout.strip().splitlines() if line]
    return proc, responses


def make_demo_system(path_stem):
    """Демо-система через сам реестр: system.new+save (критерий ТЗ).

    Returns:
        Путь к .json-файлу демо-ахромата.
    """
    json_path = f"{path_stem}.json"
    proc, payload = run_cli_json(
        ["run", "system.new",
         "--param", "demo=achromat",
         "--param", f"save={json_path}"])
    assert proc.returncode == 0, payload
    return json_path
