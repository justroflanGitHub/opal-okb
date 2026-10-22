"""
OPAL-OKB — JSONL-REPL поверх реестра команд.

``py -m commands repl`` (или ``py -m commands.jsonrepl``): читает
JSON-запросы построчно со stdin, пишет JSON-ответы в stdout (flush после
каждой строки). Ctrl+D/EOF — выход с кодом 0.

Протокол:
    запрос:  {"id": 1, "cmd": "calc.paraxial", "args": {"file": "d.opj"}}
    ответ:   {"id": 1, "ok": true, "data": {...}}
             {"id": 1, "ok": false, "error": {"code", "message"}}

Контекст персистентен на сессию: ``system.load`` загружает систему,
последующие команды без ``file``/``system`` работают с текущей.
"""
import json
import sys
from typing import Optional, TextIO

from commands.context import CommandContext
from commands.registry import Registry, default_registry


def make_response(req_id, result) -> dict:
    """Ответ протокола: id из запроса + результат команды (без 'ok'-дубля)."""
    resp = {"id": req_id}
    if result.ok:
        resp["ok"] = True
        resp["data"] = result.data
    else:
        resp["ok"] = False
        resp["error"] = result.error
    return resp


def process_line(line: str, registry: Registry,
                 ctx: CommandContext) -> dict:
    """Разобрать одну строку-запрос и выполнить команду.

    Ошибки протокола (битый JSON, нет cmd) возвращаются как ответ с
    ``ok=false`` и соответствующим кодом — REPL не падает.
    """
    from commands.base import ERR_BAD_REQUEST, CommandError
    try:
        request = json.loads(line)
    except json.JSONDecodeError as exc:
        return {"id": None, "ok": False,
                "error": CommandError(
                    ERR_BAD_REQUEST, f"битый JSON: {exc}").to_dict()}
    if not isinstance(request, dict):
        return {"id": None, "ok": False,
                "error": CommandError(
                    ERR_BAD_REQUEST,
                    "запрос должен быть JSON-объектом").to_dict()}

    req_id = request.get("id")
    cmd = request.get("cmd")
    args = request.get("args", {})
    if not cmd or not isinstance(cmd, str):
        return make_response(
            req_id,
            _failure(ERR_BAD_REQUEST, "в запросе нет строки 'cmd'"))
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return make_response(
            req_id,
            _failure(ERR_BAD_REQUEST, "'args' должен быть объектом"))
    result = registry.execute(cmd, ctx, args)
    return make_response(req_id, result)


def _failure(code: str, message: str):
    """CommandResult-failure без циклического импорта base→repl."""
    from commands.base import CommandError, CommandResult
    return CommandResult.failure(CommandError(code, message))


def run_loop(stdin: TextIO, stdout: TextIO,
             registry: Optional[Registry] = None) -> int:
    """Основной цикл: строки-запросы → строки-ответы. EOF → выход 0."""
    reg = registry or default_registry
    ctx = CommandContext()
    for line in stdin:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue  # пустые строки и комментарии — протокол молчит
        response = process_line(stripped, reg, ctx)
        print(json.dumps(response, ensure_ascii=False), file=stdout,
              flush=True)
    return 0


def main() -> int:
    """Точка входа ``py -m commands.jsonrepl``."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    from commands import register_all
    register_all()
    return run_loop(sys.stdin, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
