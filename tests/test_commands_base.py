"""Реестр команд: контракты, валидация имён, ошибки, выполнение.

Волна 1 Command Registry (TASK_COMMANDS_W1): tests/test_commands_base.py.
"""
import math

import pytest

from commands.base import (
    ERR_DUPLICATE_COMMAND,
    ERR_INTERNAL_ERROR,
    ERR_INVALID_NAME,
    ERR_INVALID_PARAM,
    ERR_MISSING_PARAM,
    ERR_NOT_SERIALIZABLE,
    ERR_UNKNOWN_COMMAND,
    ERR_UNKNOWN_PARAM,
    PARAM_BOOL,
    PARAM_FLOAT,
    PARAM_INT,
    PARAM_LIST,
    PARAM_STR,
    Command,
    CommandError,
    CommandResult,
    Param,
    coerce_value,
    sanitize_json,
)
from commands.context import CommandContext
from commands.registry import Registry, reset_registry


# --------------------------------------------------------------------------- #
# Фикстуры
# --------------------------------------------------------------------------- #

@pytest.fixture
def registry():
    """Свежий пустой реестр (без builtin) для тестов механики."""
    return Registry()


@pytest.fixture
def ctx():
    return CommandContext()


def _reg_echo(registry, name="test.echo", params=None, category="test"):
    @registry.command(name, category=category, params=params,
                      description="эхо-команда")
    def echo(ctx, **kwargs):
        return kwargs
    return echo


# --------------------------------------------------------------------------- #
# Валидация имён
# --------------------------------------------------------------------------- #

class TestNameValidation:
    @pytest.mark.parametrize("name", [
        "calc.paraxial",                     # 2 сегмента
        "analyze.tables.tabgl",              # 3 сегмента
        "file.open", "system.surface.set",
        "a.b",                               # короткие сегменты
        "calc2.multi_wl",                    # цифры и подчёркивания
        "sys9.a_1.b",                        # несколько сегментов
    ])
    def test_valid_names_accepted(self, registry, name):
        cmd = Command(name=name, category="t", description="",
                      handler=lambda ctx: None)
        assert registry.register(cmd) is cmd
        assert registry.has(name)

    @pytest.mark.parametrize("name", [
        "calc",                              # один сегмент
        "Calc.paraxial",                     # верхний регистр
        "calc.Paraxial",
        ".calc.paraxial",                    # ведущая точка
        "calc..paraxial",                    # пустой сегмент
        "calc.paraxial.",                    # хвостовая точка
        "calc.par!",                         # недопустимый символ
        "calc.пар axial",                    # не ASCII / пробел
        "",                                  # пусто
        "calc.-paraxial",                    # дефис
    ])
    def test_invalid_names_rejected(self, registry, name):
        cmd = Command(name=name, category="t", description="",
                      handler=lambda ctx: None)
        with pytest.raises(CommandError) as ei:
            registry.register(cmd)
        assert ei.value.code == ERR_INVALID_NAME

    def test_duplicate_rejected(self, registry):
        _reg_echo(registry, "test.echo")
        with pytest.raises(CommandError) as ei:
            _reg_echo(registry, "test.echo")
        assert ei.value.code == ERR_DUPLICATE_COMMAND


# --------------------------------------------------------------------------- #
# Param / типы
# --------------------------------------------------------------------------- #

class TestParam:
    def test_unknown_type_rejected(self):
        with pytest.raises(ValueError):
            Param("x", type="decimal")

    def test_param_types_tuple_complete(self):
        # константы типов — единый источник (не строки по коду)
        from commands.base import PARAM_TYPES
        assert set(PARAM_TYPES) == {"str", "float", "int", "bool",
                                    "list", "dict"}

    def test_to_dict_shape(self):
        p = Param("wl", type=PARAM_FLOAT, default=0.546,
                  help="длина волны")
        d = p.to_dict()
        assert d["name"] == "wl"
        assert d["type"] == PARAM_FLOAT
        assert d["required"] is False
        assert d["default"] == 0.546
        assert d["choices"] is None


# --------------------------------------------------------------------------- #
# coerce_value — единый разбор значений
# --------------------------------------------------------------------------- #

class TestCoerceValue:
    def test_str(self):
        assert coerce_value("abc", PARAM_STR, "p") == "abc"
        assert coerce_value(5, PARAM_STR, "p") == "5"

    def test_float(self):
        assert coerce_value("3.5", PARAM_FLOAT, "p") == 3.5
        assert coerce_value(2, PARAM_FLOAT, "p") == 2.0
        with pytest.raises(CommandError) as ei:
            coerce_value("abc", PARAM_FLOAT, "p")
        assert ei.value.code == ERR_INVALID_PARAM

    def test_int(self):
        assert coerce_value("42", PARAM_INT, "p") == 42
        assert coerce_value(3.0, PARAM_INT, "p") == 3  # целый float
        with pytest.raises(CommandError):
            coerce_value("3.5", PARAM_INT, "p")

    @pytest.mark.parametrize("raw,expected", [
        ("true", True), ("TRUE", True), ("1", True), ("yes", True),
        ("false", False), ("0", False), ("no", False), ("", False),
    ])
    def test_bool_strings(self, raw, expected):
        assert coerce_value(raw, PARAM_BOOL, "p") is expected

    def test_bool_passthrough_and_error(self):
        assert coerce_value(True, PARAM_BOOL, "p") is True
        with pytest.raises(CommandError):
            coerce_value("maybe", PARAM_BOOL, "p")

    def test_list_json_and_csv(self):
        assert coerce_value("[1,2,3]", PARAM_LIST, "p") == [1, 2, 3]
        assert coerce_value("a, b,c", PARAM_LIST, "p") == ["a", "b", "c"]
        assert coerce_value((1, 2), PARAM_LIST, "p") == [1, 2]

    def test_dict(self):
        assert coerce_value('{"a": 1}', "dict", "p") == {"a": 1}


# --------------------------------------------------------------------------- #
# Поиск и схемы
# --------------------------------------------------------------------------- #

class TestRegistryQuery:
    def test_get_missing_raises(self, registry):
        with pytest.raises(CommandError) as ei:
            registry.get("no.such")
        assert ei.value.code == ERR_UNKNOWN_COMMAND

    def test_list_and_categories(self, registry):
        _reg_echo(registry, "a.one", category="alpha")
        _reg_echo(registry, "a.two", category="alpha")
        _reg_echo(registry, "b.one", category="beta")
        assert registry.names() == ["a.one", "a.two", "b.one"]
        assert registry.categories() == ["alpha", "beta"]
        assert [c.name for c in registry.list(category="alpha")] == \
            ["a.one", "a.two"]

    def test_search_by_name_category_description(self, registry):
        _reg_echo(registry, "calc.paraxial", category="calc",
                  params=None)
        registry.get("calc.paraxial").description = "параксиальный расчёт"
        assert [c.name for c in registry.search("PARAX")] == ["calc.paraxial"]
        assert [c.name for c in registry.search("calc")] == ["calc.paraxial"]
        assert [c.name for c in registry.search("расчёт")] == ["calc.paraxial"]
        assert registry.search("") == []
        assert registry.search("zzz") == []

    def test_schema_shape(self, registry):
        _reg_echo(registry, "test.echo", params=[
            Param("file", required=True),
            Param("wl", type=PARAM_FLOAT, default=0.546),
        ], category="test")
        schema = registry.schema("test.echo")
        assert schema["name"] == "test.echo"
        assert schema["category"] == "test"
        assert [p["name"] for p in schema["params"]] == ["file", "wl"]
        assert schema["params"][0]["required"] is True
        assert "test.echo" in registry.schema_all()
        assert registry.schema_all()["test.echo"] == schema


# --------------------------------------------------------------------------- #
# execute: валидация и ошибки
# --------------------------------------------------------------------------- #

class TestExecute:
    def test_ok_path(self, registry, ctx):
        _reg_echo(registry, params=[Param("x", type=PARAM_INT,
                                          default=0)])
        result = registry.execute("test.echo", ctx, {"x": "7"})
        assert result.ok
        assert result.data == {"x": 7}
        assert result.to_dict() == {"ok": True, "data": {"x": 7}}

    def test_missing_required(self, registry, ctx):
        _reg_echo(registry, params=[Param("file", required=True)])
        result = registry.execute("test.echo", ctx, {})
        assert not result.ok
        assert result.error["code"] == ERR_MISSING_PARAM

    def test_unknown_param(self, registry, ctx):
        _reg_echo(registry)
        result = registry.execute("test.echo", ctx, {"junk": 1})
        assert result.error["code"] == ERR_UNKNOWN_PARAM

    def test_unknown_command(self, registry, ctx):
        result = registry.execute("no.such", ctx, {})
        assert result.error["code"] == ERR_UNKNOWN_COMMAND

    def test_choices_violation(self, registry, ctx):
        _reg_echo(registry, params=[
            Param("mode", choices=["given", "real"])])
        result = registry.execute("test.echo", ctx, {"mode": "other"})
        assert result.error["code"] == ERR_INVALID_PARAM

    def test_bad_type(self, registry, ctx):
        _reg_echo(registry, params=[Param("wl", type=PARAM_FLOAT)])
        result = registry.execute("test.echo", ctx, {"wl": "abc"})
        assert result.error["code"] == ERR_INVALID_PARAM

    def test_default_applied(self, registry, ctx):
        _reg_echo(registry, params=[Param("wl", type=PARAM_FLOAT,
                                          default=0.546)])
        result = registry.execute("test.echo", ctx, {})
        assert result.data == {"wl": 0.546}

    def test_command_error_from_handler(self, registry, ctx):
        @registry.command("test.fail", category="test")
        def fail(ctx):
            raise CommandError("custom_code", "детали")
        result = registry.execute("test.fail", ctx, {})
        assert result.error == {"code": "custom_code", "message": "детали"}

    def test_unexpected_exception_wrapped(self, registry, ctx):
        @registry.command("test.boom", category="test")
        def boom(ctx):
            raise ValueError("surprise")
        result = registry.execute("test.boom", ctx, {})
        assert result.error["code"] == ERR_INTERNAL_ERROR
        assert "ValueError" in result.error["message"]

    def test_non_serializable_data(self, registry, ctx):
        @registry.command("test.obj", category="test")
        def obj(ctx):
            return object()
        result = registry.execute("test.obj", ctx, {})
        assert result.error["code"] == ERR_NOT_SERIALIZABLE

    def test_nan_sanitized_to_none(self, registry, ctx):
        @registry.command("test.nan", category="test")
        def nan(ctx):
            return {"f": float("nan"), "g": math.inf,
                    "ok": 1.5, "nested": [float("nan")]}
        result = registry.execute("test.nan", ctx, {})
        assert result.ok
        assert result.data == {"f": None, "g": None, "ok": 1.5,
                               "nested": [None]}

    def test_args_not_dict(self, registry, ctx):
        _reg_echo(registry)
        result = registry.execute("test.echo", ctx, [1, 2])
        assert result.error["code"] == "bad_request"


# --------------------------------------------------------------------------- #
# CommandResult / sanitize_json
# --------------------------------------------------------------------------- #

class TestResultContracts:
    def test_failure_shape(self):
        res = CommandResult.failure(CommandError("x", "y"))
        assert res.to_dict() == {"ok": False,
                                 "error": {"code": "x", "message": "y"}}

    def test_sanitize_nested(self):
        data = {"a": [1.0, float("nan")], "b": (float("inf"),),
                "c": "text"}
        assert sanitize_json(data) == {"a": [1.0, None],
                                       "b": [None], "c": "text"}


# --------------------------------------------------------------------------- #
# default_registry / reset
# --------------------------------------------------------------------------- #

class TestDefaultRegistry:
    def test_builtin_registered_on_import(self):
        import commands
        names = commands.default_registry.names()
        assert "calc.paraxial" in names
        assert "file.open" in names
        assert "system.new" in names
        assert len(names) >= 30  # ~32 команды Волны 1

    def test_register_all_idempotent(self):
        import commands
        before = commands.default_registry.names()
        commands.register_all()
        commands.register_all()
        assert commands.default_registry.names() == before

    def test_reset_registry_returns_fresh_with_builtins(self):
        import commands
        old = commands.default_registry
        fresh = reset_registry()
        assert fresh is not old
        assert commands.default_registry is fresh
        assert "calc.paraxial" in fresh.names()
        # старый реестр не тронут
        assert "calc.paraxial" in old.names()

    def test_context_system_lifecycle(self):
        from domain.models import create_demo_system
        ctx = CommandContext()
        assert ctx.current is None
        ctx.put_system("demo", create_demo_system())
        assert ctx.current is not None
        assert ctx.get_system("demo") is ctx.current
        assert ctx.get_system() is ctx.current  # None → текущая
        ctx.drop_system("demo")
        assert ctx.current is None
        with pytest.raises(CommandError):
            ctx.get_system("demo")
