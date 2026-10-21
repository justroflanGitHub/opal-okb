"""
OPAL-OKB — Command Registry: адаптер ввода-вывода оптических систем.

Единственное место для команд: определение формата по расширению,
загрузка/сохранение систем, сериализация в JSON-совместимый словарь и
разрешение системы из аргументов команды (файл / имя в контексте /
текущая система контекста). Реализация — только вызовы публичных API
:mod:`fileio` (правило Волны 1: обёртки, без изменений нижних слоёв).
"""
import os
from typing import Any, Dict, List, Optional

from domain.models import OpticalSystem, Surface

from commands.base import (
    ERR_INTERNAL_ERROR,
    ERR_IO_ERROR,
    ERR_NO_SYSTEM,
    ERR_NOT_FOUND,
    ERR_UNKNOWN_FORMAT,
    ERR_UNSUPPORTED,
    CommandError,
)
from commands.context import CommandContext

# ============================================================
# Форматы
# ============================================================

FORMAT_OPJ = "opj"
FORMAT_LBO = "lbo"
FORMAT_JSON = "json"

#: Описания форматов для команды file.formats (единственный источник).
FORMATS: Dict[str, dict] = {
    FORMAT_OPJ: {
        "format": FORMAT_OPJ,
        "extensions": [".opj"],
        "read": True,
        "write": True,
        "description": "OPAL-PC native binary (standalone .OPJ)",
    },
    FORMAT_LBO: {
        "format": FORMAT_LBO,
        "extensions": [".lbo"],
        "read": True,
        "write": False,
        "description": "OPAL-PC library (коллекция .OPJ-записей)",
    },
    FORMAT_JSON: {
        "format": FORMAT_JSON,
        "extensions": [".json", ".opal.json"],
        "read": True,
        "write": True,
        "description": "OPAL-OKB JSON (.opal.json)",
    },
}


def detect_format(path: str) -> str:
    """Формат файла по расширению (регистронезависимо).

    Raises:
        CommandError: ``unknown_format``.
    """
    ext = os.path.splitext(str(path))[1].lower()
    for fmt, info in FORMATS.items():
        if ext in info["extensions"]:
            return fmt
    raise CommandError(
        ERR_UNKNOWN_FORMAT,
        f"неизвестное расширение {ext!r} файла {path!r}; "
        f"поддерживаются: "
        f"{sorted({e for i in FORMATS.values() for e in i['extensions']})}")


# ============================================================
# Загрузка
# ============================================================

def load_system(path: str, lbo_index: int = 0,
                lbo_name: Optional[str] = None) -> OpticalSystem:
    """Загрузить систему из файла по расширению.

    ``.lbo`` — библиотека многих систем: выбирается запись по
    ``lbo_name`` (имя .OPJ-записи) или по индексу ``lbo_index``.

    Raises:
        CommandError: ``io_error`` / ``not_found`` / ``unknown_format``.
    """
    fmt = detect_format(path)
    try:
        if fmt == FORMAT_JSON:
            from fileio.json_io import load_json
            return load_json(path)
        if fmt == FORMAT_OPJ:
            return _load_opj(path)
        if fmt == FORMAT_LBO:
            entries = _load_lbo_entries(path)
            entry = _pick_lbo_entry(entries, lbo_name, lbo_index, path)
            return entry["system"]
    except CommandError:
        raise
    except OSError as exc:
        raise CommandError(ERR_IO_ERROR, f"{path}: {exc}") from exc
    except Exception as exc:  # decoder internals → единый тип ошибок
        raise CommandError(
            ERR_INTERNAL_ERROR,
            f"ошибка разбора {path}: {type(exc).__name__}: {exc}") from exc
    raise CommandError(ERR_UNKNOWN_FORMAT, f"формат {fmt!r} не поддерживает чтение")  # pragma: no cover


def _load_opj(path: str) -> OpticalSystem:
    """Standalone .OPJ: строгий вход fileio/standalone_opj, при
    несоответствии раскладки — эвристический fileio/opj_io.

    Эвристика рассчитана на оригинальные файлы OPAL-PC и теряет имена
    стёкол на файлах нашего же писателя (save_opj пишет блок имён
    слева-выровненным, паттерн поиска читателя — имена после пробелов;
    раундтрип save_opj→load_opj в fileio тестами не покрыт). Адаптер
    ниже — правило Волны 1 «не менять fileio»: ремонт по строгой
    сигнатуре раскладки писателя.
    """
    from fileio.standalone_opj import StandaloneOpjError, load_standalone_opj
    try:
        return load_standalone_opj(path)[0]
    except StandaloneOpjError:
        from fileio.opj_io import load_opj
        system, _info = load_opj(path)
        if system.surfaces and not any(s.glass for s in system.surfaces):
            _repair_save_opj_glasses(path, system)
        return system


#: Раскладка fileio.opj_io.save_opj: заголовок 0x58 байт, N пар (R,d),
#: M λ-double, затем (N+1) имён стёкол по 8 байт cp866 (слева).
_SAVE_OPJ_HEADER_SIZE = 0x58
_SAVE_OPJ_AIR_NAMES = ("ВОЗДУХ", "AIR")


def _repair_save_opj_glasses(path: str, system: OpticalSystem) -> None:
    """Восстановить имена стёкол после эвристической загрузки.

    Применяется только при точном совпадении сигнатуры save_opj
    (длина файла = заголовок + поверхности + λ + имена; первый запись
    блока имён — ВОЗДУХ/AIR) — оригинальные раскладки OPAL под неё не
    попадают. Молча пропускается при любом несовпадении.
    """
    import struct
    try:
        with open(path, "rb") as f:
            data = f.read()
        num_surf = struct.unpack_from("<h", data, 0x34)[0]
        num_wl = struct.unpack_from("<h", data, 0x38)[0]
        if not (0 < num_surf <= 160) or not (0 <= num_wl <= 10):
            return
        expected = (_SAVE_OPJ_HEADER_SIZE + num_surf * 16 + num_wl * 8
                    + (num_surf + 1) * 8)
        if len(data) != expected or num_surf != system.num_surfaces:
            return
        block = _SAVE_OPJ_HEADER_SIZE + num_surf * 16 + num_wl * 8
        names = []
        for i in range(num_surf + 1):
            raw = data[block + i * 8:block + (i + 1) * 8]
            name = raw.decode("cp866", errors="replace").strip()
            names.append("" if name in _SAVE_OPJ_AIR_NAMES else name)
        if not names or (names[0] != "" and names[0] not in _SAVE_OPJ_AIR_NAMES):
            return  # первый записи нет воздуха → это не раскладка писателя
        for i, surface in enumerate(system.surfaces):
            if i + 1 < len(names):
                surface.glass = names[i + 1]
    except (OSError, struct.error):
        return


def _load_lbo_entries(path: str) -> List[dict]:
    """Записи .LBO через fileio.lbo_io (полный разбор OPJ-данных)."""
    from fileio.lbo_io import load_lbo
    return load_lbo(path)


def _pick_lbo_entry(entries: List[dict], lbo_name: Optional[str],
                    lbo_index: int, path: str) -> dict:
    """Выбрать запись LBO по имени файла записи или индексу."""
    if not entries:
        raise CommandError(ERR_NOT_FOUND, f"{path}: записей не найдено")
    if lbo_name:
        wanted = lbo_name.upper()
        for entry in entries:
            if entry.get("filename", "").upper() == wanted:
                return _require_lbo_system(entry, path)
        names = [e.get("filename", "") for e in entries]
        raise CommandError(
            ERR_NOT_FOUND,
            f"запись {lbo_name!r} не найдена в {path}; "
            f"доступны (первые 10): {names[:10]}")
    if not (0 <= int(lbo_index) < len(entries)):
        raise CommandError(
            ERR_NOT_FOUND,
            f"lbo_index={lbo_index} вне диапазона 0..{len(entries) - 1} "
            f"({path})")
    return _require_lbo_system(entries[lbo_index], path)


def _require_lbo_system(entry: dict, path: str) -> dict:
    system = entry.get("system")
    if system is None or not getattr(system, "surfaces", None):
        warnings = entry.get("warnings") or ["OPJ-запись не разобрана"]
        raise CommandError(
            ERR_INTERNAL_ERROR,
            f"{path}: запись {entry.get('filename', '?')} не разобрана: "
            f"{'; '.join(str(w) for w in warnings)}")
    return entry


def lbo_entry_info(entry: dict) -> dict:
    """Метаданные записи LBO для JSON-ответа (без бинарных данных)."""
    system = entry.get("system")
    return {
        "filename": entry.get("filename", ""),
        "name": entry.get("name", ""),
        "description": entry.get("description", ""),
        "num_surfaces": (len(system.surfaces)
                         if system is not None and getattr(system, "surfaces", None) else 0),
        "warnings": entry.get("warnings") or [],
    }


# ============================================================
# Сохранение
# ============================================================

def save_system(system: OpticalSystem, path: str) -> str:
    """Сохранить систему по расширению целевого пути.

    Raises:
        CommandError: ``unsupported`` (``.lbo`` нельзя записать),
            ``io_error``.
    """
    fmt = detect_format(path)
    if not FORMATS[fmt]["write"]:
        raise CommandError(
            ERR_UNSUPPORTED,
            f"запись формата {fmt!r} не поддерживается")
    try:
        if fmt == FORMAT_JSON:
            from fileio.json_io import save_json
            save_json(system, path)
        else:  # FORMAT_OPJ
            from fileio.opj_io import save_opj
            save_opj(system, path)
    except OSError as exc:
        raise CommandError(ERR_IO_ERROR, f"{path}: {exc}") from exc
    return path


# ============================================================
# Сериализация системы
# ============================================================

def surface_to_dict(index: int, s: Surface) -> dict:
    """Поверхность → JSON-совместимый словарь (полный набор полей)."""
    return {
        "index": index,
        "radius": s.radius,
        "thickness": s.thickness,
        "glass": s.glass,
        "semi_diameter": s.semi_diameter,
        "surface_type": s.surface_type.name,
        "conic_constant": s.conic_constant,
        "is_reflective": s.is_reflective,
        "aspheric_coeffs": list(s.aspheric_coeffs),
        "tilt_x": s.tilt_x,
        "tilt_y": s.tilt_y,
        "tilt_z": s.tilt_z,
        "decenter_x": s.decenter_x,
        "decenter_y": s.decenter_y,
    }


def system_to_dict(system: OpticalSystem) -> dict:
    """OpticalSystem → JSON-совместимый словарь (единственный сериализатор)."""
    return {
        "name": system.name,
        "object_type": system.object_type.name,
        "image_type": system.image_type.name,
        "object_height": system.object_height,
        "object_distance": system.object_distance,
        "aperture_type": system.aperture_type.name,
        "aperture_value": system.aperture_value,
        "stop_surface": system.stop_surface,
        "stop_offset": system.stop_offset,
        "stop_type": system.stop_type,
        "obscuration_ratio": system.obscuration_ratio,
        "beam_mode": system.beam_mode,
        "sharp_edge": system.sharp_edge,
        "comment": system.comment,
        "num_surfaces": system.num_surfaces,
        "track_length": sum(s.thickness for s in system.surfaces),
        "wavelengths": [
            {"value": wl.value, "weight": wl.weight, "name": wl.name}
            for wl in system.wavelengths
        ],
        "field_points": [
            {"y": fp.y, "x": fp.x, "weight": fp.weight}
            for fp in system.field_points
        ],
        "surfaces": [surface_to_dict(i, s)
                     for i, s in enumerate(system.surfaces)],
        "glasses": [s.glass for s in system.surfaces if s.glass],
    }


def system_summary(system: OpticalSystem) -> dict:
    """Краткая сводка о системе (file.info / system.info)."""
    d = system_to_dict(system)
    return {
        "name": d["name"],
        "object_type": d["object_type"],
        "object_height": d["object_height"],
        "aperture_type": d["aperture_type"],
        "aperture_value": d["aperture_value"],
        "stop_surface": d["stop_surface"],
        "num_surfaces": d["num_surfaces"],
        "num_wavelengths": len(d["wavelengths"]),
        "num_field_points": len(d["field_points"]),
        "glasses": d["glasses"],
        "track_length": d["track_length"],
        "wavelengths": d["wavelengths"],
        "field_points": d["field_points"],
    }


# ============================================================
# Разрешение системы из аргументов команды
# ============================================================

def resolve_system(ctx: CommandContext,
                   file: Optional[str] = None,
                   system: Optional[str] = None,
                   lbo_index: int = 0,
                   lbo_name: Optional[str] = None) -> OpticalSystem:
    """Система для команды: путь к файлу → имя в контексте → текущая.

    Порядок: ``file`` (загрузка по расширению; для REPL — без записи в
    контекст) важнее ``system`` (имя в контексте); если ничего не задано
    — текущая система контекста (REPL-сценарий ``system.load`` → расчёт).

    Raises:
        CommandError: ``no_system`` — источник не указан и контекст пуст.
    """
    if file:
        return load_system(file, lbo_index=lbo_index, lbo_name=lbo_name)
    if system:
        return ctx.get_system(system)
    current = ctx.current
    if current is not None:
        return current
    raise CommandError(
        ERR_NO_SYSTEM,
        "не указана система: передайте параметр file (путь к "
        ".opj/.lbo/.json) или system (имя в контексте REPL), либо "
        "загрузите систему командой system.load")


#: Аргументы команд, работающих с системой (общий хвост для схем).
SYSTEM_SOURCE_PARAMS = [
    ("file", "str", False, None, None,
     "путь к файлу системы (.opj/.lbo/.json)"),
    ("system", "str", False, None, None,
     "имя системы в контексте REPL"),
    ("lbo_index", "int", False, 0, None,
     "индекс записи в .lbo (если file указывает на библиотеку)"),
    ("lbo_name", "str", False, None, None,
     "имя .OPJ-записи в .lbo (приоритетнее lbo_index)"),
]


def system_source_params(extra: List[Any] = None) -> list:
    """Собрать параметры-источники системы (+ дополнительные) для схемы."""
    from commands.base import Param
    params = [Param(name=nm, type=ptype, required=req, default=deft,
                    choices=ch, help=hp)
              for nm, ptype, req, deft, ch, hp in SYSTEM_SOURCE_PARAMS]
    if extra:
        params.extend(extra)
    return params
