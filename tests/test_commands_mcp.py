"""MCP-сервер реестра команд (Волна 5): handshake, tools/list, tools/call,
имена tools, усечение вывода, протокольные ошибки, subprocess-смоук.

Волна 5 Command Registry (TASK_COMMANDS_W5): tests/test_commands_mcp.py.
In-process — handle_request/run_loop напрямую; смоук — subprocess
(критерий ТЗ: initialize + initialized + tools/list + tools/call).
"""
import io
import json
import re

import pytest

from commands import register_all
from commands.base import PARAM_INT, Param
from commands.context import CommandContext
from commands.mcp import (
    JSON_SCHEMA_TYPES,
    MAX_TOOL_RESULT_BYTES,
    PROTOCOL_VERSION_LATEST,
    SERVER_NAME,
    format_data,
    handle_request,
    input_schema,
    run_loop,
    tool_name,
)
from commands.registry import Registry
from tests._commands_proc import run_mcp

#: MCP-клиенты валидируют имена tools этим паттерном (точки запрещены).
VALID_TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

#: Допустимые типы JSON Schema в inputSchema.
JSON_SCHEMA_TYPE_VALUES = set(JSON_SCHEMA_TYPES.values())


@pytest.fixture()
def reg():
    """Текущий default_registry с зарегистрированными builtin-командами."""
    from commands import registry as registry_module
    register_all(registry_module.default_registry)
    return registry_module.default_registry


@pytest.fixture()
def ctx():
    return CommandContext()


def rpc(method, params=None, req_id=1):
    """Собрать JSON-RPC запрос (id обязательный — это не уведомление)."""
    request = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        request["params"] = params
    return request


def call(reg, ctx, name, arguments=None, req_id=1):
    """tools/call через handle_request (in-process)."""
    return handle_request(
        rpc("tools/call", {"name": name,
                           "arguments": arguments or {}}, req_id),
        reg, ctx)


def tools_list(reg, ctx):
    """tools/list → список дескрипторов tools."""
    resp = handle_request(rpc("tools/list"), reg, ctx)
    assert resp is not None and "result" in resp
    return resp["result"]["tools"]


class TestInitialize:
    def test_handshake_shape(self, reg, ctx):
        resp = handle_request(rpc("initialize", {"protocolVersion":
                                                 PROTOCOL_VERSION_LATEST}),
                              reg, ctx)
        assert resp["jsonrpc"] == "2.0" and resp["id"] == 1
        result = resp["result"]
        assert result["protocolVersion"] == PROTOCOL_VERSION_LATEST
        assert result["capabilities"] == {"tools": {}}
        assert result["serverInfo"]["name"] == SERVER_NAME
        assert re.match(r"^\d+\.\d+\.\d+$",
                        result["serverInfo"]["version"])

    def test_version_negotiation(self, reg, ctx):
        """Клиентскую версию из известных — отзеркалим, неизвестную — своя."""
        for known in ("2024-11-05", "2025-03-26"):
            resp = handle_request(
                rpc("initialize", {"protocolVersion": known}), reg, ctx)
            assert resp["result"]["protocolVersion"] == known
        resp = handle_request(
            rpc("initialize", {"protocolVersion": "1999-01-01"}), reg, ctx)
        assert resp["result"]["protocolVersion"] == PROTOCOL_VERSION_LATEST

    def test_ping(self, reg, ctx):
        resp = handle_request(rpc("ping", {}), reg, ctx)
        assert resp["result"] == {}

    def test_initialized_notification_no_response(self, reg, ctx):
        assert handle_request(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            reg, ctx) is None

    def test_string_id_echoed(self, reg, ctx):
        resp = handle_request(rpc("ping", {}, "alpha"), reg, ctx)
        assert resp["id"] == "alpha"


class TestToolNames:
    def test_valid_unique_no_collisions(self, reg, ctx):
        """После замены '.'→'_' имена валидны и не коллидируют."""
        cmds = reg.list()
        mapped = [tool_name(c.name) for c in cmds]
        assert len(mapped) == len(set(mapped)), "коллизия имён tools"
        for name in mapped:
            assert VALID_TOOL_NAME.match(name), name

    def test_reverse_mapping_roundtrip(self, reg, ctx):
        from commands.mcp import resolve_tool_name
        for c in reg.list():
            assert resolve_tool_name(tool_name(c.name), reg) == c.name


class TestToolsList:
    def test_all_commands_exposed(self, reg, ctx):
        """Каждая команда реестра — ровно один tool."""
        tools = tools_list(reg, ctx)
        assert len(tools) == len(reg.names())
        assert {t["name"] for t in tools} == \
            {tool_name(n) for n in reg.names()}

    def test_input_schema_is_valid_json_schema(self, reg, ctx):
        """type object + properties + required ⊆ properties + типы схемы."""
        for tool in tools_list(reg, ctx):
            schema = tool["inputSchema"]
            assert schema["type"] == "object"
            props = schema["properties"]
            assert isinstance(props, dict)
            for prop in props.values():
                assert prop["type"] in JSON_SCHEMA_TYPE_VALUES, prop
                if "enum" in prop:
                    assert isinstance(prop["enum"], list) \
                        and prop["enum"]
                if "default" in prop:
                    json.dumps(prop["default"])  # сериализуем
            for req in schema.get("required", []):
                assert req in props, (tool["name"], req)

    def test_description_starts_with_canonical_name(self, reg, ctx):
        for tool in tools_list(reg, ctx):
            canonical = tool["description"].split()[0]
            assert tool_name(canonical) == tool["name"], tool["name"]

    def test_concrete_schema_paraxial(self, reg, ctx):
        """calc_paraxial: file/system — string, wl — number, lbo_index —
        integer c default."""
        schema = input_schema(reg.get("calc.paraxial"))
        props = schema["properties"]
        assert props["file"]["type"] == "string"
        assert props["system"]["type"] == "string"
        assert props["wl"]["type"] == "number"
        assert props["lbo_index"]["type"] == "integer"
        assert props["lbo_index"]["default"] == 0

    def test_enum_from_choices(self, reg, ctx):
        schema = input_schema(reg.get("system.new"))
        assert schema["properties"]["demo"]["enum"] == \
            reg.get("system.new").params[0].choices


class TestToolsCall:
    def test_stateful_session_new_then_paraxial(self, reg, ctx):
        """system_new кладёт систему — calc_paraxial без аргументов берёт
        её из персистентного контекста сервера."""
        resp = call(reg, ctx, "system_new",
                    {"demo": "achromat", "name": "ach"})
        assert resp["result"]["isError"] is False
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["name"] == "ach"

        resp = call(reg, ctx, "calc_paraxial")
        assert resp["result"]["isError"] is False
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["focal_length"] > 0

    def test_fresh_context_has_no_system(self, reg, ctx):
        """Состояние живёт в контексте, а не в реестре: новый ctx пуст."""
        call(reg, ctx, "system_new", {"demo": "achromat", "name": "ach"})
        resp = handle_request(
            rpc("tools/call", {"name": "calc_paraxial", "arguments": {}}),
            reg, CommandContext())
        assert resp["result"]["isError"] is True

    def test_command_error_is_error_true(self, reg, ctx):
        """Ошибка команды (нет системы) — isError true + код в тексте."""
        resp = call(reg, ctx, "calc_paraxial")
        result = resp["result"]
        assert result["isError"] is True
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        payload = json.loads(result["content"][0]["text"])
        assert payload["ok"] is False
        assert payload["error"]["code"] == "no_system"

    def test_invalid_param_is_error_true(self, reg, ctx):
        resp = call(reg, ctx, "system_new", {"demo": "no_such_demo"})
        payload = json.loads(resp["result"]["content"][0]["text"])
        assert resp["result"]["isError"] is True
        assert payload["error"]["code"] == "invalid_param"

    def test_unknown_tool_jsonrpc_error(self, reg, ctx):
        resp = call(reg, ctx, "no_such_tool")
        assert "error" in resp and "result" not in resp
        assert resp["error"]["code"] == -32602

    def test_missing_name_invalid_params(self, reg, ctx):
        resp = handle_request(rpc("tools/call", {"arguments": {}}), reg, ctx)
        assert resp["error"]["code"] == -32602

    def test_arguments_not_object_invalid_params(self, reg, ctx):
        resp = handle_request(
            rpc("tools/call", {"name": "ping", "arguments": [1, 2]}),
            reg, ctx)
        assert resp["error"]["code"] == -32602


class TestProtocolErrors:
    def test_unknown_method(self, reg, ctx):
        resp = handle_request(rpc("bogus/method"), reg, ctx)
        assert resp["error"]["code"] == -32601
        assert "bogus/method" in resp["error"]["message"]
        assert resp["id"] == 1

    def test_unknown_method_notification_silent(self, reg, ctx):
        assert handle_request(
            {"jsonrpc": "2.0", "method": "bogus/method"}, reg, ctx) is None

    def test_non_object_request(self, reg, ctx):
        resp = handle_request([1, 2, 3], reg, ctx)
        assert resp["error"]["code"] == -32600
        assert resp["id"] is None

    def test_no_method(self, reg, ctx):
        resp = handle_request({"jsonrpc": "2.0", "id": 5}, reg, ctx)
        assert resp["error"]["code"] == -32600

    def test_run_loop_bad_json_then_ping(self, reg):
        """Битая строка → -32700 (id null), сессия жива, ping — ок."""
        out = io.StringIO()
        code = run_loop(io.StringIO('{"broken\n'
                                    + json.dumps(rpc("ping")) + "\n"),
                        out, registry=reg)
        assert code == 0
        lines = [json.loads(x) for x in out.getvalue().splitlines()]
        assert lines[0]["error"]["code"] == -32700
        assert lines[0]["id"] is None
        assert lines[1]["result"] == {}

    def test_run_loop_empty_lines_skipped(self, reg):
        out = io.StringIO()
        code = run_loop(io.StringIO("\n\n"), out, registry=reg)
        assert code == 0 and out.getvalue() == ""


class TestTruncation:
    def test_small_data_passthrough(self):
        text = format_data({"focal_length": 97.5})
        assert json.loads(text) == {"focal_length": 97.5}

    def test_big_data_truncated_envelope(self):
        text = format_data({"blob": "x" * (MAX_TOOL_RESULT_BYTES * 3)})
        envelope = json.loads(text)
        assert envelope["truncated"] is True
        assert envelope["size_bytes"] > MAX_TOOL_RESULT_BYTES
        assert envelope["limit_bytes"] == MAX_TOOL_RESULT_BYTES
        assert len(envelope["preview"].encode("utf-8")) \
            <= MAX_TOOL_RESULT_BYTES + 8  # хвост '\n…'
        assert "файл" in envelope["hint"]  # подсказка про сохранение

    def test_tools_call_big_result_truncated(self, ctx):
        """tools/call команды с огромным результатом — усечённый конверт
        (изолированный реестр, default_registry не трогаем)."""
        big_reg = Registry()

        @big_reg.command("demo.big", category="demo",
                         description="большой результат для теста усечения",
                         params=[Param("size", type=PARAM_INT,
                                       default=MAX_TOOL_RESULT_BYTES * 3)])
        def _big(ctx, size=MAX_TOOL_RESULT_BYTES * 3):
            return {"blob": "x" * size}

        resp = call(big_reg, ctx, "demo_big")
        assert resp["result"]["isError"] is False
        envelope = json.loads(resp["result"]["content"][0]["text"])
        assert envelope["truncated"] is True


class TestSubprocessSmoke:
    """Критерий ТЗ: initialize + initialized + tools/list + tools/call
    одним процессом ``py -m commands mcp``; stdout — только протокол."""

    def test_full_session(self):
        proc, responses = run_mcp([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": PROTOCOL_VERSION_LATEST}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "system_new",
                        "arguments": {"demo": "achromat", "name": "ach"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "calc_paraxial", "arguments": {}}},
        ])
        assert proc.returncode == 0
        assert proc.stderr.strip() == ""  # stdout/stderr не перепутаны
        assert [r["id"] for r in responses] == [1, 2, 3, 4]  # уведомление молчит
        assert all(r["jsonrpc"] == "2.0" for r in responses)

        init = responses[0]["result"]
        assert init["protocolVersion"] == PROTOCOL_VERSION_LATEST
        assert init["capabilities"] == {"tools": {}}

        tools = responses[1]["result"]["tools"]
        assert len(tools) == 140  # весь реестр волны 5
        assert all(VALID_TOOL_NAME.match(t["name"]) for t in tools)

        new = responses[2]["result"]
        assert new["isError"] is False
        paraxial = responses[3]["result"]
        assert paraxial["isError"] is False
        data = json.loads(paraxial["content"][0]["text"])
        assert data["focal_length"] > 0  # stateful: система из запроса 3

    def test_tools_list_without_initialize(self, reg, ctx):
        """Критерий ТЗ: tools/list отвечает и до initialize."""
        proc, responses = run_mcp(
            [{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
        assert proc.returncode == 0
        assert len(responses) == 1
        assert len(responses[0]["result"]["tools"]) == len(reg.names())

    def test_error_paths_in_subprocess(self):
        proc, responses = run_mcp([
            {"jsonrpc": "2.0", "id": 1, "method": "no.such.method"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "no_such_tool", "arguments": {}}},
        ])
        assert proc.returncode == 0
        assert responses[0]["error"]["code"] == -32601
        assert responses[1]["error"]["code"] == -32602
