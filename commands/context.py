"""
OPAL-OKB — Command Registry: контекст выполнения.

Контекст — способ передать состояние между командами. CLI создаёт
свежий контекст на каждый вызов (команды stateless: система задаётся
путём к файлу), REPL держит один персистентный контекст на сессию
(``system.load`` → ``calc.paraxial`` без повторной загрузки).
"""
from typing import Dict, Optional

from domain.models import OpticalSystem

from commands.base import ERR_NOT_FOUND, CommandError


class CommandContext:
    """Состояние сессии: именованные оптические системы + текущая.

    Атрибуты:
        systems: словарь ``имя → OpticalSystem``.
        current_name: имя текущей системы (цель команд без явного
            указания системы) или ``None``.
    """

    def __init__(self):
        self.systems: Dict[str, OpticalSystem] = {}
        self.current_name: Optional[str] = None

    # ----------------------------------------------------------

    def put_system(self, name: str, system: OpticalSystem,
                   make_current: bool = True) -> None:
        """Сохранить систему под именем (перезапись допустима)."""
        if not name or not isinstance(name, str):
            raise CommandError(ERR_NOT_FOUND, "имя системы пустое")
        self.systems[name] = system
        if make_current:
            self.current_name = name

    def get_system(self, name: Optional[str] = None) -> OpticalSystem:
        """Система по имени; ``None`` — текущая.

        Raises:
            CommandError: ``not_found`` — имени нет в контексте или
                текущая система не выбрана.
        """
        key = name if name is not None else self.current_name
        if key is None:
            raise CommandError(
                ERR_NOT_FOUND,
                "в контексте нет текущей системы: загрузите её "
                "(system.load) или укажите параметр file/system")
        try:
            return self.systems[key]
        except KeyError:
            hint = (f"доступны: {sorted(self.systems)}"
                    if self.systems else "контекст пуст")
            raise CommandError(
                ERR_NOT_FOUND,
                f"система {key!r} не загружена в контекст ({hint})") from None

    @property
    def current(self) -> Optional[OpticalSystem]:
        """Текущая система или ``None`` (без исключения)."""
        if self.current_name is None:
            return None
        return self.systems.get(self.current_name)

    def drop_system(self, name: str) -> None:
        """Удалить систему из контекста; текущая — сбросить, если она."""
        self.systems.pop(name, None)
        if self.current_name == name:
            self.current_name = None
