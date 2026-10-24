"""
OPAL-OKB — общие приватные хелперы пакетов R500 (правило №1).

Одна и та же логика не живёт в нескольких модулях: разрешение аргументов
«явный список или системные значения» (поля/λ), проверка конечности,
запуск сестринской команды с живой системой в контексте — единые
реализации здесь. Модули пакетов импортируют их под локальными именами
(``_fields_arg`` и т.п.), сохраняя совместимость межмодульных импортов
(например, adv_ext ← sweep).
"""
from typing import Optional

import math

from commands.base import ERR_INVALID_PARAM, CommandError
from commands.registry import Registry
from optics_utils import get_primary_wl

#: Абсолютный эпсилон сравнения с нулём (мм/λ/безразмерные нормы).
TINY = 1e-12


def fields_arg(system, fields) -> list:
    """Список полей: явный или точки поля системы.

    Raises:
        CommandError: ``invalid_param`` — у системы нет точек поля.
    """
    if fields:
        return [float(f) for f in fields]
    values = [fp.y for fp in system.field_points]
    if not values:
        raise CommandError(
            ERR_INVALID_PARAM,
            "у системы нет точек поля; передайте fields или добавьте "
            "поля системе (system.fields.add)")
    return values


def system_wls(system) -> list:
    """Рабочие λ системы (или основная, если список пуст)."""
    return [w.value for w in system.wavelengths] or [
        get_primary_wl(system)]


def wls_arg(system, wls) -> list:
    """Список λ: явный или рабочие λ системы (fallback — основная)."""
    if wls:
        return [float(w) for w in wls]
    return system_wls(system)


def finite(value: float, param: str) -> float:
    """Конечное число или ``invalid_param``."""
    if not math.isfinite(value):
        raise CommandError(ERR_INVALID_PARAM,
                           f"параметр {param!r} должен быть конечным")
    return float(value)


def run_sibling(registry: Registry, ctx, system, key: str, name: str,
                args: Optional[dict] = None) -> dict:
    """Выполнить сестринскую команду с живой системой в контексте.

    Система кладётся под служебным именем ``key`` (префикс + тег —
    забота вызывающего) и удаляется после вызова; ошибка сестры →
    :class:`CommandError`.
    """
    ctx.put_system(key, system, make_current=False)
    try:
        result = registry.execute(name, ctx, {"system": key, **(args or {})})
    finally:
        ctx.drop_system(key)
    if not result.ok:
        raise CommandError(result.error["code"], result.error["message"])
    return result.data
