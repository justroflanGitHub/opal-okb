"""OPAL-OKB — Bridge: единая точка вызова команд реестра из UI (Волна 4).

Тонкая обвязка над ``commands.registry.default_registry`` (спецификация
``docs/tasks/TASK_COMMANDS_W4.md``, п. 2):

* :func:`execute` — выполнить команду (валидация параметров, JSON-контракт
  и превращение исключений в ``CommandResult`` остаются на стороне реестра);
* :func:`report_error` — единый показ ошибок команды (QMessageBox,
  текст с кодом команды).

Модуль НЕ содержит бизнес-логики: только вызов реестра и показ ошибки.
Контексты выполнения создаёт вызывающая сторона (панель/главное окно
кладёт в контекст живую систему GUI), здесь состояния не хранится.
"""
from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import QMessageBox

from commands.base import CommandResult
from commands.registry import default_registry

#: Заголовок окна единого показа ошибок команд.
_ERROR_TITLE = "Команда"


def execute(name: str, ctx, **kwargs: Any) -> CommandResult:
    """Выполнить команду реестра для контекста ``ctx``.

    Args:
        name: имя команды (например ``calc.paraxial``).
        ctx: контекст выполнения с текущей системой GUI
            (:class:`commands.context.CommandContext`).
        **kwargs: параметры команды по схеме реестра.

    Returns:
        :class:`CommandResult` — исключения наружу не поднимаются
        (контракт реестра); ошибку показывает :func:`report_error`.
    """
    return default_registry.execute(name, ctx, kwargs)


def report_error(parent, result: CommandResult) -> bool:
    """Показать ошибку выполнения команды (единый формат для UI).

    Для успешного результата ничего не делает. Возвращает ``True``,
    если ошибка была показана.
    """
    if result is None or result.ok:
        return False
    error = result.error or {}
    code = error.get("code", "error")
    message = error.get("message", "")
    QMessageBox.warning(
        parent, _ERROR_TITLE,
        f"Команда не выполнена (код: {code}).\n{message}")
    return True
