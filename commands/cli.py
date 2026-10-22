"""
OPAL-OKB — CLI поверх реестра команд.

``py -m commands <subcommand>``:
    list   [—category X] [--json]   имена+описания
    info   <cmd>                    полное описание, параметры
    schema [--json]                 схема всех команд
    run    <cmd> [--param k=v …]    выполнить команду
    repl                             JSONL-REPL (роутинг в jsonrepl)
    mcp                              MCP-сервер over stdio (роутинг в mcp)

Ошибки: ненулевой код выхода; при ``--json`` — JSON-ответ в stderr.
"""
import argparse
import json
import sys
from typing import List, Optional

from commands.base import (
    ERR_INTERNAL_ERROR,
    ERR_INVALID_PARAM,
    CommandError,
    CommandResult,
    coerce_value,
)
from commands.context import CommandContext
from commands.registry import default_registry

PROG = "py -m commands"

#: Разделитель ключ=значение в --param (первое вхождение).
PARAM_SEPARATOR = "="


def build_parser() -> argparse.ArgumentParser:
    """Единый builder argparse (без дублирования подкоманд)."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Command Registry OPAL-OKB — headless-управление "
                    "оптическими расчётами")
    sub = parser.add_subparsers(dest="subcommand", metavar="subcommand")
    sub.required = True

    p_list = sub.add_parser(
        "list", help="список команд (имена + описания)")
    p_list.add_argument("--category", help="фильтр по категории")
    p_list.add_argument("--json", action="store_true",
                        help="вывод в JSON")

    p_info = sub.add_parser("info", help="описание команды и параметры")
    p_info.add_argument("cmd", help="имя команды (например calc.paraxial)")

    p_schema = sub.add_parser("schema", help="схемы всех команд")
    p_schema.add_argument("--json", action="store_true",
                          help="вывод в JSON")

    p_run = sub.add_parser("run", help="выполнить команду")
    p_run.add_argument("cmd", help="имя команды")
    p_run.add_argument(
        "--param", action="append", default=[], metavar="KEY=VALUE",
        help="аргумент команды (тип — по схеме); можно повторять")
    p_run.add_argument("--json", action="store_true",
                       help="вывод результата в JSON")

    sub.add_parser("repl", help="JSONL-REPL: запросы со stdin")
    sub.add_parser("mcp", help="MCP-сервер over stdio: команды реестра "
                               "как tools (JSON-RPC 2.0)")

    return parser


def _print_json(payload: dict) -> None:
    """JSON в stdout (UTF-8, без экранирования не-ASCII)."""
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_data_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def parse_params(pairs: List[str], cmd) -> dict:
    """Разобрать ``--param key=value`` по схеме команды.

    Типы значений (float/int/bool/list) — из схемы; разбор строк —
    единый :func:`commands.base.coerce_value`.
    """
    params_spec = {p.name: p for p in cmd.params}
    args = {}
    for pair in pairs:
        try:
            if PARAM_SEPARATOR not in pair:
                raise ValueError(
                    f"--param {pair!r}: ожидается формат KEY=VALUE")
            key, _, raw = pair.partition(PARAM_SEPARATOR)
            key = key.strip()
            if key not in params_spec:
                raise ValueError(
                    f"--param {key!r}: неизвестный параметр команды "
                    f"{cmd.name!r} (допустимы {sorted(params_spec)})")
            args[key] = coerce_value(raw, params_spec[key].type, key)
        except CommandError as exc:
            raise ValueError(str(exc)) from exc
    return args


# ----------------------------------------------------------
# Подкоманды (каждая возвращает код выхода)
# ----------------------------------------------------------

def _cmd_list(args) -> int:
    registry = default_registry
    if args.category and args.category not in registry.categories():
        print(f"категория {args.category!r} не найдена; "
              f"доступны: {registry.categories()}", file=sys.stderr)
        return 2
    cmds = registry.list(category=args.category)
    if args.json:
        _print_json({
            "commands": [c.schema() for c in cmds],
            "total": len(cmds),
        })
    else:
        for c in cmds:
            print(f"{c.name:<28} {c.description}")
        print(f"— всего: {len(cmds)}")
    return 0


def _cmd_info(args) -> int:
    schema = default_registry.schema(args.cmd)
    params = schema["params"]
    print(f"{schema['name']}  [{schema['category']}]")
    print(f"  {schema['description']}")
    if params:
        print("  Параметры:")
        for p in params:
            req = "обязателен" if p["required"] else "опционален"
            meta = [f"type={p['type']}", req]
            if p["default"] is not None:
                meta.append(f"default={p['default']!r}")
            if p["choices"]:
                meta.append(f"choices={p['choices']}")
            print(f"    {p['name']:<16} {', '.join(meta)}")
            if p["help"]:
                print(f"{'':<22}{p['help']}")
    else:
        print("  Параметры: нет")
    if schema["returns"]:
        print(f"  Возвращает: {schema['returns']}")
    return 0


def _cmd_schema(args) -> int:
    schemas = default_registry.schema_all()
    if args.json:
        _print_json({"commands": schemas, "total": len(schemas)})
    else:
        for name in sorted(schemas):
            print(f"{name:<28} "
                  f"{schemas[name]['description']}")
    return 0


def _cmd_run(args) -> int:
    registry = default_registry
    try:
        cmd = registry.get(args.cmd)
    except Exception as exc:
        err = (exc if isinstance(exc, CommandError)
               else CommandError(ERR_INTERNAL_ERROR, str(exc)))
        return _emit_result(CommandResult.failure(err), args.json)
    try:
        cmd_args = parse_params(args.param, cmd)
    except ValueError as exc:
        # Разбор --param вне схемы — ошибка вызова CLI (код 2)
        result = CommandResult.failure(
            CommandError(ERR_INVALID_PARAM, str(exc)))
        return _emit_result(result, args.json, exit_code=2)
    ctx = CommandContext()
    result = registry.execute(args.cmd, ctx, cmd_args)
    return _emit_result(result, args.json)


def _emit_result(result: CommandResult, as_json: bool,
                 exit_code: Optional[int] = None) -> int:
    """Вывести результат: успех — stdout; ошибка — stderr + код ≠ 0."""
    if result.ok:
        if as_json:
            _print_json(result.to_dict())
        else:
            _print_data_json(result.data)
        return 0
    code = exit_code if exit_code is not None else 1
    if as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
              file=sys.stderr)
    else:
        err = result.error or {}
        print(f"ошибка [{err.get('code', '?')}]: {err.get('message', '')}",
              file=sys.stderr)
    return code


def main(argv: Optional[List[str]] = None) -> int:
    """Точка входа CLI; возвращает код выхода процесса."""
    _force_utf8_streams()
    from commands import register_all
    register_all()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "repl":
        from commands.jsonrepl import main as repl_main
        return repl_main()

    if args.subcommand == "mcp":
        from commands.mcp import main as mcp_main
        return mcp_main()

    if args.subcommand == "list":
        return _cmd_list(args)
    if args.subcommand == "info":
        try:
            return _cmd_info(args)
        except Exception as exc:
            print(f"ошибка: {exc}", file=sys.stderr)
            return 1
    if args.subcommand == "schema":
        return _cmd_schema(args)
    if args.subcommand == "run":
        return _cmd_run(args)
    parser.error(f"неизвестная подкоманда {args.subcommand!r}")
    return 2  # pragma: no cover


def _force_utf8_streams() -> None:
    """UTF-8 для stdout/stderr (Windows-консоль по умолчанию cp1251/cp866)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


if __name__ == "__main__":
    sys.exit(main())
