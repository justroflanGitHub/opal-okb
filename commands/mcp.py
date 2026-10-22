"""
OPAL-OKB — MCP-сервер поверх реестра команд.

``py -m commands mcp`` (или ``py -m commands.mcp``): Model Context Protocol
over stdio — JSON-RPC 2.0, строка stdin = JSON-объект, строка stdout =
JSON-объект (flush после каждого ответа). Чистая stdlib (json/sys), без
новых зависимостей. Сервер — тонкий слой над ``default_registry``:
каждая команда реестра публикуется как MCP-tool.

stdout зарезервирован протоколом; все логи/ошибки сервера — только
в stderr.

Методы:
    initialize               handshake (protocolVersion/capabilities)
    notifications/initialized  уведомление — ответа нет
    ping                    → {}
    tools/list              → все команды реестра как tools
    tools/call              → выполнить команду (персистентный контекст)

Имена tools: MCP-клиенты валидируют ``[a-zA-Z0-9_-]`` — точки запрещены,
поэтому ``calc.paraxial`` → ``calc_paraxial`` (:func:`tool_name`);
каноническое имя — первым словом в description. Контекст один на процесс
(как у REPL): ``system.new`` создаёт систему, дальнейшие команды через
``system=`` её не требуют.
"""
import json
import sys
from typing import Optional, TextIO

from commands.base import (
    PARAM_BOOL,
    PARAM_DICT,
    PARAM_FLOAT,
    PARAM_INT,
    PARAM_LIST,
    PARAM_STR,
)
from commands.context import CommandContext
from commands.registry import Registry

# ============================================================
# Константы протокола/сервера
# ============================================================

#: Последняя известная версия протокола MCP (отвечаем на initialize).
PROTOCOL_VERSION_LATEST = "2025-06-18"

#: Версии, которые умеем отдавать клиенту (negotiation на initialize).
KNOWN_PROTOCOL_VERSIONS = (PROTOCOL_VERSION_LATEST, "2025-03-26",
                           "2024-11-05")

SERVER_NAME = "opal-okb"
SERVER_VERSION = "1.28.0"

#: Лимит text-контента tools/call (байт UTF-8): больше — усечённый конверт.
MAX_TOOL_RESULT_BYTES = 20000

# JSON-RPC 2.0 коды ошибок.
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602

#: Param.type → тип JSON Schema (единственное место маппинга).
JSON_SCHEMA_TYPES = {
    PARAM_STR: "string",
    PARAM_FLOAT: "number",
    PARAM_INT: "integer",
    PARAM_BOOL: "boolean",
    PARAM_LIST: "array",
    PARAM_DICT: "object",
}

TRUNCATION_HINT = (
    "результат обрезан: сохраните его в файл (например file.export.*) "
    "или запросите меньший срез (параметры limit/rows), чтобы не "
    "раздувать контекст")


class JsonRpcError(Exception):
    """Ошибка уровня протокола → JSON-RPC error (не tool-ошибка)."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ============================================================
# JSON-RPC обвязка: одна пара (успех/ошибка) + один вывод
# ============================================================

def ok_response(req_id, result: dict) -> dict:
    """JSON-RPC response с result."""
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def error_response(req_id, code: int, message: str) -> dict:
    """JSON-RPC response с error (id None — для parse error)."""
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message}}


def _send(stdout: TextIO, payload: dict) -> None:
    """Одна строка JSON в stdout, flush сразу (клиент ждёт ответа)."""
    print(json.dumps(payload, ensure_ascii=False), file=stdout, flush=True)


# ============================================================
# Имена tools: '.' запрещена → '_'
# ============================================================

def tool_name(cmd_name: str) -> str:
    """Имя MCP-tool из имени команды: ``calc.paraxial`` → ``calc_paraxial``."""
    return cmd_name.replace(".", "_")


def resolve_tool_name(tool: str, registry: Registry) -> Optional[str]:
    """Обратный маппинг: имя tool → каноническое имя команды (или None)."""
    for name in registry.names():
        if tool_name(name) == tool:
            return name
    return None


# ============================================================
# inputSchema из Param (JSON Schema)
# ============================================================

def input_schema(cmd) -> dict:
    """JSON Schema (object) параметров команды.

    Типы — :data:`JSON_SCHEMA_TYPES`; ``required`` — обязательные
    параметры; ``default``/``enum``/``description`` — из Param.
    """
    properties = {}
    required = []
    for p in cmd.params:
        prop = {"type": JSON_SCHEMA_TYPES[p.type]}
        if p.help:
            prop["description"] = p.help
        if p.default is not None:
            prop["default"] = p.default
        if p.choices is not None:
            prop["enum"] = list(p.choices)
        properties[p.name] = prop
        if p.required:
            required.append(p.name)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def tool_descriptor(cmd) -> dict:
    """MCP-tool дескриптор: имя без точек, каноническое имя первым словом."""
    return {
        "name": tool_name(cmd.name),
        "description": f"{cmd.name} [{cmd.category}] — {cmd.description}",
        "inputSchema": input_schema(cmd),
    }


# ============================================================
# Форматирование результата tools/call
# ============================================================

def format_data(data) -> str:
    """JSON-текст результата; сверх лимита — усечённый конверт.

    Конверт: ``{"truncated": true, "size_bytes", "limit_bytes",
    "preview", "hint"}`` — чтобы не раздувать контекст агента.
    """
    text = json.dumps(data, ensure_ascii=False, indent=2)
    raw = text.encode("utf-8")
    if len(raw) <= MAX_TOOL_RESULT_BYTES:
        return text
    preview = raw[:MAX_TOOL_RESULT_BYTES].decode("utf-8", errors="ignore")
    envelope = {
        "truncated": True,
        "size_bytes": len(raw),
        "limit_bytes": MAX_TOOL_RESULT_BYTES,
        "preview": preview + "\n…",
        "hint": TRUNCATION_HINT,
    }
    return json.dumps(envelope, ensure_ascii=False, indent=2)


# ============================================================
# Методы MCP
# ============================================================

def _initialize(params: dict) -> dict:
    """Handshake: версию клиента поддерживаем, иначе последнюю свою."""
    requested = params.get("protocolVersion")
    version = (requested if requested in KNOWN_PROTOCOL_VERSIONS
               else PROTOCOL_VERSION_LATEST)
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def _call_tool(params: dict, registry: Registry,
               ctx: CommandContext) -> dict:
    """tools/call → MCP result (content + isError).

    Raises:
        JsonRpcError: ``-32602`` — нет name / аргументы не объект /
            неизвестный tool.
    """
    name = params.get("name")
    if not isinstance(name, str) or not name:
        raise JsonRpcError(
            JSONRPC_INVALID_PARAMS, "tools/call: 'name' обязателен")
    arguments = params.get("arguments")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise JsonRpcError(
            JSONRPC_INVALID_PARAMS, "'arguments' должен быть объектом")
    canonical = resolve_tool_name(name, registry)
    if canonical is None:
        raise JsonRpcError(
            JSONRPC_INVALID_PARAMS,
            f"неизвестный tool {name!r}; см. tools/list")
    result = registry.execute(canonical, ctx, arguments)
    if result.ok:
        return {"content": [{"type": "text", "text": format_data(result.data)}],
                "isError": False}
    return {"content": [{"type": "text", "text": json.dumps(
        {"ok": False, "error": result.error}, ensure_ascii=False)}],
        "isError": True}


def handle_request(request, registry: Registry,
                   ctx: CommandContext) -> Optional[dict]:
    """Обработать один JSON-RPC объект → response или None (уведомление).

    Протокольные ошибки (нет method, неизвестный метод, битые params)
    — JSON-RPC error; ошибки самой команды — isError в tools/call.
    """
    if not isinstance(request, dict):
        return error_response(None, JSONRPC_INVALID_REQUEST,
                              "запрос должен быть JSON-объектом")
    is_notification = "id" not in request
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params")
    if params is None:
        params = {}

    if not isinstance(method, str) or not method:
        return None if is_notification else error_response(
            req_id, JSONRPC_INVALID_REQUEST,
            "в запросе нет строки 'method'")
    if not isinstance(params, dict):
        return None if is_notification else error_response(
            req_id, JSONRPC_INVALID_PARAMS, "'params' должен быть объектом")

    try:
        if method == "initialize":
            result = _initialize(params)
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [tool_descriptor(c) for c in registry.list()]}
        elif method == "tools/call":
            result = _call_tool(params, registry, ctx)
        else:
            return None if is_notification else error_response(
                req_id, JSONRPC_METHOD_NOT_FOUND,
                f"Method not found: {method}")
    except JsonRpcError as exc:
        return None if is_notification else error_response(
            req_id, exc.code, exc.message)
    return None if is_notification else ok_response(req_id, result)


# ============================================================
# Цикл сервера
# ============================================================

def run_loop(stdin: TextIO, stdout: TextIO,
             registry: Optional[Registry] = None) -> int:
    """Основной цикл: JSONL stdin → JSONL stdout. EOF → выход 0.

    Контекст персистентен на процесс (как у REPL): stateful-сессия
    поверх реестра без изменения контрактов команд.
    """
    if registry is None:
        from commands import registry as registry_module
        registry = registry_module.default_registry
    ctx = CommandContext()
    for line in stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            request = json.loads(stripped)
        except json.JSONDecodeError as exc:
            _send(stdout, error_response(
                None, JSONRPC_PARSE_ERROR, f"битый JSON: {exc}"))
            continue
        response = handle_request(request, registry, ctx)
        if response is not None:
            _send(stdout, response)
    return 0


def main() -> int:
    """Точка входа ``py -m commands mcp`` (и ``py -m commands.mcp``)."""
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
