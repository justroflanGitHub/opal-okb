"""
OPAL-OKB — Command Registry (Волна 1, Built for agents).

Единый реестр команд поверх domain/analysis/fileio/catalog — headless,
без Qt. Фронтенды: CLI (:mod:`commands.cli`), JSONL-REPL
(:mod:`commands.jsonrepl`); UI/MCP — следующие волны.

    py -m commands list --json
    py -m commands run calc.paraxial --param file=demo.opj --json
    py -m commands repl

Single source of truth: команды регистрируются декоратором в
:data:`commands.registry.default_registry`; фронтенды тонкие.
"""
from commands.base import (  # noqa: F401
    BOOL_FALSE_STRINGS,
    BOOL_TRUE_STRINGS,
    Command,
    CommandError,
    CommandResult,
    Param,
    PARAM_BOOL,
    PARAM_DICT,
    PARAM_FLOAT,
    PARAM_INT,
    PARAM_LIST,
    PARAM_STR,
    PARAM_TYPES,
    coerce_value,
    sanitize_json,
    validate_jsonable,
)
from commands.context import CommandContext  # noqa: F401
from commands.registry import (  # noqa: F401
    NAME_PATTERN,
    Registry,
    reset_registry,
)


def __getattr__(name):
    """``commands.default_registry`` всегда ссылается на текущий реестр
    (reset_registry() заменяет объект в commands.registry)."""
    if name == "default_registry":
        from commands import registry as _registry
        return _registry.default_registry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

#: Команда-маркер: её наличие = builtin-команды уже зарегистрированы.
_REGISTERED_MARK = "file.formats"


def register_all(registry: Registry = None) -> Registry:
    """Зарегистрировать все builtin-команды (идемпотентно).

    Args:
        registry: целевой реестр (по умолчанию ``default_registry``).

    Returns:
        Реестр с зарегистрированными командами.
    """
    from commands import registry as registry_module
    reg = (registry if registry is not None
           else registry_module.default_registry)
    if reg.has(_REGISTERED_MARK):
        return reg  # повторный вызов — no-op
    from commands.builtin import register_builtin
    register_builtin(reg)
    return reg


# Регистрация при импорте пакета: `import commands` → реестр готов.
register_all()

__all__ = [
    "Command",
    "CommandContext",
    "CommandError",
    "CommandResult",
    "NAME_PATTERN",
    "Param",
    "PARAM_BOOL",
    "PARAM_DICT",
    "PARAM_FLOAT",
    "PARAM_INT",
    "PARAM_LIST",
    "PARAM_STR",
    "PARAM_TYPES",
    "Registry",
    "coerce_value",
    "default_registry",
    "register_all",
    "reset_registry",
    "sanitize_json",
    "validate_jsonable",
]
