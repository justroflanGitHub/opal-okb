"""
OPAL-OKB — Command Registry: реестр команд.

Единый каталог ``name → Command`` (single source of truth). Регистрация —
через :meth:`Registry.register` или декоратор-фабрику
:meth:`Registry.command`. CLI (:mod:`commands.cli`) и JSON-REPL
(:mod:`commands.jsonrepl`) — тонкие фронтенды над реестром.
"""
import re
from typing import Dict, List, Optional

from commands.base import (
    Command,
    CommandError,
    CommandResult,
    Param,
    ERR_DUPLICATE_COMMAND,
    ERR_INVALID_NAME,
    ERR_MISSING_PARAM,
    ERR_UNKNOWN_COMMAND,
    ERR_UNKNOWN_PARAM,
    ERR_INVALID_PARAM,
    ERR_BAD_REQUEST,
    ERR_INTERNAL_ERROR,
    coerce_value,
    sanitize_json,
    validate_jsonable,
)

#: Имя команды: минимум два сегмента ``[a-z0-9_]+`` через точку
#: (``calc.paraxial``, ``analyze.tables.tabgl``).
NAME_PATTERN = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")


class Registry:
    """Каталог команд: регистрация, поиск, схемы, выполнение.

    Поток выполнения (:meth:`execute`): валидация имени → валидация
    параметров по схеме (неизвестный/отсутствующий/неверный тип/choices)
    → вызов ``handler(ctx, **args)`` → санитайз и проверка JSON-ответа.
    Любое исключение обработчика, кроме :class:`CommandError`,
    превращается в ``internal_error`` — наружу всегда CommandResult.
    """

    def __init__(self):
        self._commands: Dict[str, Command] = {}

    # ----------------------------------------------------------
    # Регистрация
    # ----------------------------------------------------------

    def register(self, cmd: Command) -> Command:
        """Зарегистрировать команду; вернуть её же (для декоратора).

        Raises:
            CommandError: ``invalid_name`` — имя не проходит
                :data:`NAME_PATTERN`; ``duplicate_command`` — имя занято.
        """
        if not NAME_PATTERN.match(cmd.name or ""):
            raise CommandError(
                ERR_INVALID_NAME,
                f"недопустимое имя команды {cmd.name!r}: нужно "
                f"минимум два сегмента [a-z0-9_]+ через точку "
                f"(например 'calc.paraxial')")
        if cmd.name in self._commands:
            raise CommandError(
                ERR_DUPLICATE_COMMAND,
                f"команда {cmd.name!r} уже зарегистрирована")
        self._commands[cmd.name] = cmd
        return cmd

    def command(self, name: str, category: str, description: str = "",
                params: Optional[List[Param]] = None,
                returns: str = "") -> callable:
        """Декоратор-фабрика: обёртка функции в Command + регистрация.

        >>> @registry.command("demo.hello", category="demo",
        ...                   params=[Param("who", default="мир")])
        ... def hello(ctx, who="мир"):
        ...     return {"hello": who}
        """
        def decorator(func: callable) -> callable:
            self.register(Command(
                name=name, category=category, description=description,
                params=list(params or []), returns=returns, handler=func))
            return func
        return decorator

    # ----------------------------------------------------------
    # Доступ и поиск
    # ----------------------------------------------------------

    def get(self, name: str) -> Command:
        """Получить команду по имени.

        Raises:
            CommandError: ``unknown_command``.
        """
        try:
            return self._commands[name]
        except KeyError:
            raise CommandError(
                ERR_UNKNOWN_COMMAND,
                f"неизвестная команда {name!r}; "
                f"см. 'py -m commands list'") from None

    def has(self, name: str) -> bool:
        return name in self._commands

    def names(self) -> List[str]:
        """Все имена команд (отсортированы)."""
        return sorted(self._commands)

    def list(self, category: Optional[str] = None) -> List[Command]:
        """Команды (по имени), опционально одной категории."""
        cmds = [c for c in self._commands.values()
                if category is None or c.category == category]
        return sorted(cmds, key=lambda c: c.name)

    def search(self, query: str) -> List[Command]:
        """Подстрочный поиск по имени/категории/описанию (без регистра)."""
        q = (query or "").strip().lower()
        if not q:
            return []
        found = [c for c in self._commands.values()
                 if q in c.name.lower()
                 or q in c.category.lower()
                 or q in c.description.lower()]
        return sorted(found, key=lambda c: c.name)

    def categories(self) -> List[str]:
        """Отсортированный список категорий."""
        return sorted({c.category for c in self._commands.values()})

    # ----------------------------------------------------------
    # Схемы
    # ----------------------------------------------------------

    def schema(self, name: str) -> dict:
        """Схема одной команды (:meth:`Command.schema`)."""
        return self.get(name).schema()

    def schema_all(self) -> Dict[str, dict]:
        """Схемы всех команд: ``{name: schema}``."""
        return {name: self._commands[name].schema()
                for name in self.names()}

    # ----------------------------------------------------------
    # Выполнение
    # ----------------------------------------------------------

    def execute(self, name: str, ctx, args: Optional[dict] = None
                ) -> CommandResult:
        """Выполнить команду с валидацией параметров.

        Args:
            name: имя команды.
            ctx: контекст выполнения (см. :mod:`commands.context`).
            args: словарь аргументов (CLI-строки приводятся к типам
                схемы автоматически).

        Returns:
            :class:`CommandResult` — ошибка выполнения никогда не
            поднимается исключением наружу.
        """
        try:
            cmd = self.get(name)
        except CommandError as exc:
            return CommandResult.failure(exc)

        if args is None:
            args = {}
        if not isinstance(args, dict):
            return CommandResult.failure(CommandError(
                ERR_BAD_REQUEST, "args должен быть объектом (dict)"))

        try:
            kwargs = self._validate_args(cmd, args)
            data = cmd.handler(ctx, **kwargs)
            data = sanitize_json(data)
            validate_jsonable(data)
            return CommandResult.success(data)
        except CommandError as exc:
            return CommandResult.failure(exc)
        except Exception as exc:  # noqa: BLE001 — наружу только JSON
            return CommandResult.failure(CommandError(
                ERR_INTERNAL_ERROR,
                f"{type(exc).__name__}: {exc}"))

    def _validate_args(self, cmd: Command, args: dict) -> dict:
        """Проверить args по схеме команды; вернуть готовые kwargs."""
        known = {p.name: p for p in cmd.params}
        unknown = [k for k in args if k not in known]
        if unknown:
            raise CommandError(
                ERR_UNKNOWN_PARAM,
                f"неизвестные параметры {unknown!r} для {cmd.name!r}; "
                f"допустимы {sorted(known)}")
        kwargs = {}
        for p in cmd.params:
            if p.name in args and args[p.name] is not None:
                value = coerce_value(args[p.name], p.type, p.name)
                if p.choices is not None and value not in p.choices:
                    raise CommandError(
                        ERR_INVALID_PARAM,
                        f"параметр {p.name!r}={value!r}: допустимо "
                        f"{p.choices}")
                kwargs[p.name] = value
            elif p.required:
                raise CommandError(
                    ERR_MISSING_PARAM,
                    f"параметр {p.name!r} обязателен для {cmd.name!r}")
            else:
                kwargs[p.name] = p.default
        return kwargs


# ============================================================
# Реестр по умолчанию
# ============================================================

#: Реестр модуль-уровня — единственный для приложения.
default_registry = Registry()


def reset_registry() -> Registry:
    """Свежий реестр с builtin-командами (для тестов).

    Заменяет :data:`default_registry` новым экземпляром и повторно
    регистрирует все builtin-команды (включая команды, добавленные
    тестами поверх builtin — они теряются, это ожидаемо).
    """
    global default_registry
    default_registry = Registry()
    from commands.builtin import register_builtin
    register_builtin(default_registry)
    return default_registry
