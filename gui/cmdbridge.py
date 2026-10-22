"""
OPAL-OKB — мост UI ↔ реестр команд (Волна 4, TASK_COMMANDS_W4.md).

Единая точка вызова команд из GUI: обработчики меню/кнопок собирают
параметры из диалогов и состояния окна, выполняют команду через
:meth:`CommandBridge.execute` и рендерят результат прежними виджетами.
Кнопка не считает сама — считает команда (принцип VS Code).

Мост НЕ содержит бизнес-логики: только вызов ``default_registry``,
персистентный контекст сессии (как у JSON-REPL) и адаптеры формы
результата (правило 4 ТЗ: несоответствие формы решается здесь, а не
в контрактах команд Волн 1+3).

Модуль общий для агентов Волны 4: создаёт агент src=main; агент
src=panel только импортирует его (не дублирует).
"""
from typing import Any, Optional, Tuple

from commands.base import CommandResult
from commands.context import CommandContext
from commands.registry import Registry, default_registry

#: Ключ текущей системы UI-сессии в контексте моста.
CURRENT_KEY = "ui.current"

#: Первая команда Волны 4 (src=main) — маркер ленивой регистрации.
_W4_MAIN_SENTINEL = "system.append"


def ensure_w4_registered(registry: Optional[Registry] = None) -> None:
    """Зарегистрировать команды Волны 4 в реестре, если их ещё нет.

    ``commands/builtin/__init__.py`` не трогается (правило 5 ТЗ —
    координатор добавит регистрацию после мержа); мост регистрирует
    свои модули лениво и идемпотентно.
    """
    reg = registry if registry is not None else default_registry
    if reg.has(_W4_MAIN_SENTINEL):
        return
    from commands.builtin import w4_main_cmds
    w4_main_cmds.register(reg)


class CommandBridge:
    """Персистентный контекст UI-сессии + вызовы реестра команд.

    Обработчик начинает с :meth:`set_current` (состояние GUI →
    контекст) и вызывает команды без явного источника системы — они
    работают с текущей системой контекста (REPL-семантика
    ``resolve_system``).
    """

    def __init__(self, registry: Optional[Registry] = None):
        self._registry = registry if registry is not None else default_registry
        self._ctx = CommandContext()
        ensure_w4_registered(self._registry)

    # ----------------------------------------------------------
    # Выполнение
    # ----------------------------------------------------------

    @property
    def context(self) -> CommandContext:
        """Контекст сессии (именованные системы + текущая)."""
        return self._ctx

    def execute(self, cmd: str, ctx: Optional[CommandContext] = None,
                **kwargs) -> CommandResult:
        """Выполнить команду через реестр (обёртка execute реестра).

        Args:
            cmd: имя команды (например ``calc.paraxial``).
            ctx: контекст выполнения; по умолчанию — контекст моста.
            **kwargs: аргументы команды (приводятся к типам схемы;
                первый параметр назван ``cmd``, а не ``name`` — чтобы
                не конфликтовать с одноимённым параметром самих
                команд: ``execute("system.new", name=…)``).

        Returns:
            :class:`CommandResult` — ошибка никогда не исключением.
        """
        return self._registry.execute(cmd, ctx or self._ctx, kwargs)

    # ----------------------------------------------------------
    # Синхронизация состояния GUI ↔ контекст
    # ----------------------------------------------------------

    def set_current(self, system: Any) -> None:
        """Текущая система окна → контекст моста (перед командой)."""
        if system is not None:
            self._ctx.put_system(CURRENT_KEY, system)

    def current_system(self) -> Any:
        """Живой объект текущей системы контекста (``None``, если пусто)."""
        return self._ctx.current

    # ----------------------------------------------------------
    # Адаптеры формы результата (правило 4 ТЗ)
    # ----------------------------------------------------------

    def load_file(self, path: str, lbo_index: int = 0,
                  lbo_name: Optional[str] = None
                  ) -> Tuple[Any, Optional[CommandResult]]:
        """Загрузка системы из файла: ``system.load`` + живой объект.

        ``system.load`` (контракт Волны 1) кладёт систему в контекст и
        делает текущей — живой объект для окна берётся из контекста,
        без повторной загрузки и без десериализации ответа.

        Returns:
            ``(OpticalSystem | None, CommandResult)`` — система ``None``
            при ошибке.
        """
        res = self.execute("system.load", file=path, lbo_index=lbo_index,
                           lbo_name=lbo_name)
        if not res.ok:
            return None, res
        return self.current_system(), res

    def create_demo(self, demo: str = "default"
                    ) -> Tuple[Any, Optional[CommandResult]]:
        """Демо-система: ``system.new`` + живой объект в контексте.

        ``system.new`` (контракт Волны 1) кладёт систему в контекст
        только при явном ``name`` (который заодно переименовывает).
        Мост передаёт фабричное имя из первого ответа: генераторы
        ``domain/models.py`` детерминированы, повторный вызов дешевле
        десериализации и не создаёт параллельный конструктор систем.
        """
        res = self.execute("system.new", demo=demo)
        if not res.ok:
            return None, res
        factory_name = res.data.get("name") or CURRENT_KEY
        res = self.execute("system.new", demo=demo, name=factory_name)
        if not res.ok:
            return None, res
        return self.current_system(), res

    def create_empty(self, name: str = "Новая система",
                     field_zero: bool = True
                     ) -> Tuple[Any, Optional[CommandResult]]:
        """Пустая система: ``system.new`` (demo=empty) + точка поля 0.

        Воспроизводит стартовое состояние окна: имя «Новая система»,
        одна осевая точка поля (стандартные длины волн подставляет
        ``_refresh_ui`` при загрузке в таблицы).
        """
        res = self.execute("system.new", demo="empty", name=name)
        if not res.ok:
            return None, res
        if field_zero:
            res = self.execute("system.fields.add", y=0.0, x=0.0,
                               weight=1.0)
            if not res.ok:
                return None, res
        return self.current_system(), res


#: Мост главного окна (единый экземпляр UI-сессии).
bridge = CommandBridge()


def report_error(parent, result: CommandResult,
                 cmd: Optional[str] = None) -> None:
    """Единый показ ошибки команды (QMessageBox с кодом).

    Args:
        parent: родительский виджет для диалога.
        result: неудачный :class:`CommandResult`.
        cmd: имя команды для заголовка (если известен вызывающему).
    """
    from PyQt5.QtWidgets import QMessageBox  # лениво: модуль моста не тянет Qt

    error = result.error or {}
    code = error.get("code", "error")
    message = error.get("message", "")
    title = f"Ошибка команды {cmd}" if cmd else "Ошибка команды"
    QMessageBox.critical(parent, title, f"[{code}] {message}")
