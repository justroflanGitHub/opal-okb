"""Builtin-команды реестра: файлы, системы, расчёты, каталог, анализ,
трассировка и таблицы (Волна 3).

Каждый модуль экспортирует ``register(registry)``; регистрация всех —
:func:`register_builtin` (вызывается ``commands.register_all``).
"""
from commands.registry import Registry

#: Модули builtin-команд (порядок = порядок категорий в list).
_BUILTIN_MODULES = (
    "commands.builtin.file_cmds",
    "commands.builtin.system_cmds",
    "commands.builtin.calc_cmds",
    "commands.builtin.catalog_cmds",
    "commands.builtin.analyze_cmds",
    "commands.builtin.trace_cmds",
    "commands.builtin.aber_cmds",
    "commands.builtin.psf_cmds",
    "commands.builtin.opt_cmds",
    "commands.builtin.w4_main_cmds",
    "commands.builtin.w4_panel_cmds",
)


def register_builtin(registry: Registry) -> Registry:
    """Зарегистрировать все builtin-команды в реестр (идемпотентно
    на уровне commands.register_all; повторный вызов напрямую поднимет
    duplicate_command — это защита от двойной регистрации)."""
    import importlib
    for module_name in _BUILTIN_MODULES:
        module = importlib.import_module(module_name)
        module.register(registry)
    return registry
