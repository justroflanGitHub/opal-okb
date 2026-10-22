"""
OPAL-OKB — Command Registry: базовые контракты.

Единый источник типов параметров, ошибок и результатов команд.
Фронтенды (CLI/JSON-REPL, будущие UI/MCP) работают только с этими
контрактами — сам реестр в :mod:`commands.registry`.
"""
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

# ============================================================
# Типы параметров — константы, не строки по коду
# ============================================================

PARAM_STR = "str"
PARAM_FLOAT = "float"
PARAM_INT = "int"
PARAM_BOOL = "bool"
PARAM_LIST = "list"
PARAM_DICT = "dict"

#: Допустимые значения Param.type.
PARAM_TYPES = (PARAM_STR, PARAM_FLOAT, PARAM_INT, PARAM_BOOL,
               PARAM_LIST, PARAM_DICT)

# ============================================================
# Коды ошибок команд
# ============================================================

ERR_UNKNOWN_COMMAND = "unknown_command"
ERR_UNKNOWN_PARAM = "unknown_param"
ERR_MISSING_PARAM = "missing_param"
ERR_INVALID_PARAM = "invalid_param"
ERR_INVALID_NAME = "invalid_name"
ERR_DUPLICATE_COMMAND = "duplicate_command"
ERR_NOT_FOUND = "not_found"
ERR_NO_SYSTEM = "no_system"
ERR_UNKNOWN_FORMAT = "unknown_format"
ERR_UNSUPPORTED = "unsupported"
ERR_BAD_REQUEST = "bad_request"
ERR_IO_ERROR = "io_error"
ERR_NOT_SERIALIZABLE = "not_serializable"
ERR_INTERNAL_ERROR = "internal_error"

#: Строковые значения bool (регистронезависимо): CLI/JSON в одну сторону.
BOOL_TRUE_STRINGS = frozenset({"true", "1", "yes", "on", "да"})
BOOL_FALSE_STRINGS = frozenset({"false", "0", "no", "off", "нет", ""})


class CommandError(Exception):
    """Единственный тип ошибок команд.

    ``code`` — машинный идентификатор (константы ``ERR_*``),
    ``message`` — человекочитаемое описание.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


@dataclass
class CommandResult:
    """Результат выполнения команды.

    ``data`` — JSON-сериализуемое значение (проверяется при выполнении,
    не-finite float заменяются на ``None`` — см. :func:`sanitize_json`).
    ``error`` — ``{"code": ..., "message": ...}`` при ``ok=False``.
    """
    ok: bool = True
    data: Any = None
    error: Optional[dict] = None

    @classmethod
    def success(cls, data: Any = None) -> "CommandResult":
        return cls(ok=True, data=data)

    @classmethod
    def failure(cls, error: CommandError) -> "CommandResult":
        return cls(ok=False, error=error.to_dict())

    def to_dict(self) -> dict:
        if self.ok:
            return {"ok": True, "data": self.data}
        return {"ok": False, "error": self.error}


@dataclass
class Param:
    """Описание одного параметра команды.

    ``type`` — одна из констант ``PARAM_*``; ``choices`` — допустимые
    значения (для str); ``default`` используется, если параметр не
    передан (тогда параметр не считается обязательным).
    """
    name: str
    type: str = PARAM_STR
    required: bool = False
    default: Any = None
    choices: Optional[List[str]] = None
    help: str = ""

    def __post_init__(self):
        if self.type not in PARAM_TYPES:
            raise ValueError(
                f"параметр {self.name!r}: неизвестный тип {self.type!r} "
                f"(допустимо {list(PARAM_TYPES)})")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "choices": self.choices,
            "help": self.help,
        }


@dataclass
class Command:
    """Команда реестра: метаданные + обработчик.

    Обработчик вызывается как ``handler(ctx, **args)``: первый
    аргумент — контекст (:class:`commands.context.CommandContext`;
    CLI передаёт свежий, REPL — персистентный), далее — провалидированные
    параметры по схеме.
    """
    name: str
    category: str
    description: str
    params: List[Param] = field(default_factory=list)
    returns: str = ""
    handler: Callable[..., Any] = None

    def schema(self) -> dict:
        """JSON-сериализуемое описание команды (для CLI schema / агентов)."""
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "params": [p.to_dict() for p in self.params],
            "returns": self.returns,
        }


# ============================================================
# Разбор значений — единственное место (CLI и REPL)
# ============================================================

def coerce_value(value: Any, ptype: str, param_name: str) -> Any:
    """Привести значение к типу параметра.

    Строки разбираются по типу (``"3.5"`` → float, ``"true"`` → bool,
    ``"[1,2]"`` или ``"a,b"`` → list); значения уже нужного типа
    проходят с проверкой. Ошибка разбора — :class:`CommandError` с кодом
    ``invalid_param``.
    """
    try:
        if ptype == PARAM_STR:
            return value if isinstance(value, str) else str(value)
        if ptype == PARAM_FLOAT:
            return float(value)
        if ptype == PARAM_INT:
            if isinstance(value, float) and value.is_integer():
                return int(value)
            if isinstance(value, str) and "." in value:
                f = float(value)
                if not f.is_integer():
                    raise ValueError(value)
                return int(f)
            return int(value)
        if ptype == PARAM_BOOL:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)) and value in (0, 1):
                return bool(value)
            s = str(value).strip().lower()
            if s in BOOL_TRUE_STRINGS:
                return True
            if s in BOOL_FALSE_STRINGS:
                return False
            raise ValueError(value)
        if ptype == PARAM_LIST:
            if isinstance(value, (list, tuple)):
                return list(value)
            s = str(value).strip()
            if s.startswith("["):
                parsed = json.loads(s)
                if not isinstance(parsed, list):
                    raise ValueError("не список")
                return parsed
            return [item.strip() for item in s.split(",")] if s else []
        if ptype == PARAM_DICT:
            if isinstance(value, dict):
                return value
            parsed = json.loads(str(value))
            if not isinstance(parsed, dict):
                raise ValueError("не словарь")
            return parsed
    except CommandError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: не удалось привести "
            f"{value!r} к типу {ptype} ({exc})") from exc
    raise CommandError(ERR_INVALID_PARAM,
                       f"параметр {param_name!r}: неизвестный тип {ptype!r}")


# ============================================================
# JSON-санитайзер результата
# ============================================================

def sanitize_json(value: Any) -> Any:
    """Рекурсивно заменить non-finite float (NaN/±inf) на ``None``.

    Стандарт JSON не допускает NaN/Infinity; молча выбрасывать их в
    канал нельзя, а терять весь результат из-за одного вырожденного
    числа — тоже. Возвращает ту же структуру с заменой на ``None``.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: sanitize_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_json(v) for v in value]
    return value


def validate_jsonable(data: Any) -> None:
    """Проверить, что ``data`` сериализуется в строгий JSON.

    Raises:
        CommandError: ``not_serializable`` — если ``json.dumps``
            не справляется (обработчик вернул живой объект).
    """
    try:
        json.dumps(data, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CommandError(
            ERR_NOT_SERIALIZABLE,
            f"результат команды не JSON-сериализуем: {exc}") from exc
