"""
OPAL-OKB — Command Registry: адаптер записи результатов в файлы.

Единственное место для экспортных команд: определение формата выгрузки
по расширению, запись строк (CSV), структур (JSON) и текста (TXT),
единый контракт ответа (``out/format/rows/preview``). Реализация —
стандартная библиотека (csv/json), без нижних слоёв проекта.
"""
import csv
import io
import json
import os
from typing import Any, Dict, List, Optional

from commands.base import (
    ERR_IO_ERROR,
    ERR_UNKNOWN_FORMAT,
    ERR_UNSUPPORTED,
    CommandError,
    sanitize_json,
)

# ============================================================
# Форматы выгрузки
# ============================================================

FORMAT_CSV = "csv"
FORMAT_JSON = "json"
FORMAT_TXT = "txt"

#: Описания форматов выгрузки (единственный источник, как FORMATS в systemio).
EXPORT_FORMATS: Dict[str, dict] = {
    FORMAT_CSV: {
        "format": FORMAT_CSV,
        "extensions": [".csv"],
        "description": "таблица: строки-словари, колонки — по порядку ключей",
    },
    FORMAT_JSON: {
        "format": FORMAT_JSON,
        "extensions": [".json"],
        "description": "структура (dict/list) как есть, indent=2",
    },
    FORMAT_TXT: {
        "format": FORMAT_TXT,
        "extensions": [".txt"],
        "description": "готовый текст (протоколы/отчёты OPAL)",
    },
}

#: Строк превью в ответе экспортных команд.
PREVIEW_ROWS = 5

#: Символов превью текстовых выгрузок.
PREVIEW_CHARS = 200


def detect_export_format(path: str) -> str:
    """Формат выгрузки по расширению (регистронезависимо).

    Raises:
        CommandError: ``unknown_format``.
    """
    ext = os.path.splitext(str(path))[1].lower()
    for fmt, info in EXPORT_FORMATS.items():
        if ext in info["extensions"]:
            return fmt
    raise CommandError(
        ERR_UNKNOWN_FORMAT,
        f"неизвестное расширение выгрузки {ext!r} у {path!r}; "
        f"поддерживаются: "
        f"{sorted({e for i in EXPORT_FORMATS.values() for e in i['extensions']})}")


# ============================================================
# Запись
# ============================================================

def _cell(value: Any) -> str:
    """Значение ячейки CSV: скаляры как есть, структуры — компактный JSON."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _columns_of(rows: List[dict], columns: Optional[List[str]]) -> List[str]:
    """Колонки CSV: явный список или объединение ключей по порядку."""
    if columns:
        return list(columns)
    seen: Dict[str, None] = {}
    for row in rows:
        for key in row:
            seen.setdefault(key, None)
    return list(seen)


def write_rows(rows: List[dict], path: str,
               columns: Optional[List[str]] = None) -> dict:
    """Записать строки-словари в CSV (или JSON, если расширение .json).

    Returns:
        ``{"out", "format", "rows", "columns", "preview"}`` — контракт
        экспортных команд.
    Raises:
        CommandError: ``unknown_format`` / ``unsupported`` / ``io_error``.
    """
    fmt = detect_export_format(path)
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise CommandError(
            ERR_UNSUPPORTED,
            "rows должен быть списком словарей (строками таблицы)")
    cols = _columns_of(rows, columns)
    try:
        if fmt == FORMAT_JSON:
            payload = json.dumps(sanitize_json(rows), ensure_ascii=False,
                                 allow_nan=False, indent=2)
        else:
            buf = io.StringIO()
            writer = csv.writer(buf, lineterminator="\n")
            writer.writerow(cols)
            for row in rows:
                writer.writerow([_cell(row.get(c)) for c in cols])
            payload = buf.getvalue()
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
    except OSError as exc:
        raise CommandError(ERR_IO_ERROR, f"{path}: {exc}") from exc
    return {"out": os.path.abspath(path), "format": fmt,
            "rows": len(rows), "columns": cols,
            "preview": rows[:PREVIEW_ROWS]}


def write_data(data: Any, path: str) -> dict:
    """Записать структуру (dict/list) в JSON-файл.

    Raises:
        CommandError: ``unknown_format`` / ``io_error`` /
            ``not_serializable``.
    """
    fmt = detect_export_format(path)
    if fmt != FORMAT_JSON:
        raise CommandError(
            ERR_UNSUPPORTED,
            f"структуры выгружаются только в .json (получено {fmt!r}); "
            f"строки — export.rows, текст — export.text")
    try:
        payload = json.dumps(sanitize_json(data), ensure_ascii=False,
                             allow_nan=False, indent=2)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
    except OSError as exc:
        raise CommandError(ERR_IO_ERROR, f"{path}: {exc}") from exc
    return _text_result(path, payload)


def write_text(text: str, path: str) -> dict:
    """Записать текст в .txt-файл.

    Raises:
        CommandError: ``unknown_format`` / ``io_error``.
    """
    fmt = detect_export_format(path)
    if fmt != FORMAT_TXT:
        raise CommandError(
            ERR_UNSUPPORTED,
            f"текст выгружается только в .txt (получено {fmt!r}); "
            f"структуры — export.data")
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    except OSError as exc:
        raise CommandError(ERR_IO_ERROR, f"{path}: {exc}") from exc
    return _text_result(path, text)


def _text_result(path: str, payload: str) -> dict:
    """Общий ответ текстовых выгрузок: файл + размер + превью."""
    return {"out": os.path.abspath(path),
            "format": detect_export_format(path),
            "size_bytes": len(payload.encode("utf-8")),
            "preview": payload[:PREVIEW_CHARS]}
