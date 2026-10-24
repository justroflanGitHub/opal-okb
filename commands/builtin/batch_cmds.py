"""
OPAL-OKB — Пакет R500-15: пакетные прогоны команд по спискам систем (batch).

ПАКЕТНАЯ ОБРАБОТКА СПИСКОВ ФАЙЛОВ (.opj/.json/.lbo): единый вход ``files``
(список путей, например результат ``batch.dir``), ошибки отдельных файлов
НЕ роняют пакет — попадают в ``errors[]`` по каждому элементу; если не
загрузился ни один файл (или список пуст) — ``invalid_param``.

Отличие от ``library.batch`` (R500-3, прогоны по одной .LBO-библиотеке):
здесь список произвольный (файлы любых форматов + директория через
``batch.dir``), а прогон — ЛЮВАЯ команда реестра (``batch.run``) или
готовая метрика качества.

- ``batch.metrics``  — справочник метрик пакета (имя/описание/единица/
  полярность «лучше больше/меньше»);
- ``batch.dir``      — скан каталога по расширениям (без прописных
  путей: параметр path; рекурсия опциональна);
- ``batch.names``   — имена систем пакета (файл → имя системы);
- ``batch.info``    — обзор пакета: формат/размер/поверхности/λ/поля;
- ``batch.load``    — загрузить все системы пакета в контекст REPL
  (без смены текущей);
- ``batch.run``     — выполнить произвольную команду реестра над каждым
  файлом (композиция через registry.execute, ``file=<путь>``);
- ``batch.validate``— санити ``system.validate`` по всем файлам пакета;
- ``batch.metric``  — одна метрика по всем системам (efl, F/#, RMS
  пятна, Штрель, суммы Зейделя, ...);
- ``batch.summary`` — таблица нескольких метрик + итоги min/max/mean;
- ``batch.rank``    — ранжирование систем по метрике (best/worst);
- ``batch.stats``   — статистика метрики: min/max/mean/median/σ;
- ``batch.filter``  — отбор систем по условию на метрику (>, <, range);
- ``batch.check``   — пороговая проверка по всем системам (pass/fail);
- ``batch.compare`` — сравнение каждой системы с эталонным файлом;
- ``batch.apply``   — применить команду-модификацию к копиям систем
  (через ``out``-параметр сестринской команды);
- ``batch.changes`` — метрики до/после модификации (что изменилось);
- ``batch.convert`` — пакетная конвертация формата (.opj ↔ .json);
- ``batch.dedupe``  — дубликаты по контрольной сумме файла;
- ``batch.export``  — выгрузка метрик пакета в .csv/.json (exportio);
- ``batch.report``  — текстовый свод по пакету (опция записи .txt).

Движки не дублируются: параксиал/Зейдель — domain.calculations, пятно —
analysis.aberrations, Штрель — analysis.strehl, ФКЭ-диаметры — хелпер
quality_cmds (analysis.advanced.compute_enc), загрузка/сохранение —
commands.systemio, запись выгрузок — commands.exportio, алгоритмы хешей
— CHECKSUM_ALGOS из lbo_cmds. Тяжёлые метрики по умолчанию считаются
лёгким вариантом (малое число лучей), полный — параметром ``num_rays``.
"""
import hashlib
import math
import os
import statistics
from typing import Any, Dict, List, Optional, Tuple

from commands.base import (
    ERR_INVALID_PARAM,
    ERR_IO_ERROR,
    ERR_UNSUPPORTED,
    Param,
    CommandError,
)
from commands.registry import Registry
from commands.systemio import (
    detect_format,
    load_system,
    save_system,
)

# Переиспользование общего кода соседних пакетов (правило №1: не копировать).
from commands.builtin.lbo_cmds import CHECKSUM_ALGOS
from commands.builtin.quality_cmds import (
    AIRY_FIRST_ZERO,
    EE_FRACTION_DEFAULT,
    _ee_diameters_geometric,
)
from optics_utils import get_primary_wl

# ============================================================
# Именованные константы пакета
# ============================================================

#: Лучей сетки зрачка в геометрических метриках по умолчанию (лёгкий
#: вариант; полный — параметром num_rays).
BATCH_SPOT_RAYS_DEFAULT = 20

#: Поле (y, градусы) метрик по умолчанию (осевое).
BATCH_FIELD_DEFAULT = 0.0

#: Метрики сводной таблицы batch.summary / report / export по умолчанию.
SUMMARY_METRICS_DEFAULT = ("efl", "f_number", "num_surfaces",
                           "track_length", "spot_rms")

#: Метрики batch.changes по умолчанию (лёгкий набор «что изменилось»).
CHANGES_METRICS_DEFAULT = ("efl", "f_number", "spot_rms")

#: Расширения batch.dir по умолчанию (.lbo — библиотека многих систем,
#: её пакеты — домен library.batch; здесь — файлы «одна система»).
DIR_EXTENSIONS_DEFAULT = (".opj", ".json")

#: Суффикс имени копий в batch.apply (защита от перезаписи исходников).
APPLY_SUFFIX_DEFAULT = "_applied"

#: Формат копий batch.apply / batch.convert по умолчанию (.opj-раундтрип
#: теряет точки поля — .json сохраняет всё).
BATCH_FORMAT_DEFAULT = "json"

#: Алгоритм контрольной суммы batch.dedupe по умолчанию.
DEDUPE_ALGO_DEFAULT = "md5"

#: Операции отбора batch.filter.
FILTER_OPS = ("gt", "ge", "lt", "le", "eq", "ne", "range")

#: Направления ранжирования batch.rank (auto — по полярности метрики).
RANK_ORDERS = ("auto", "asc", "desc")

#: Режимы порога batch.check: min — «не ниже», max — «не выше»
#: (auto — по полярности метрики).
CHECK_MODES = ("auto", "min", "max")

#: Формат чисел в текстовом отчёте batch.report.
REPORT_VALUE_FMT = "{:.6g}"

#: Разделитель колонок текстового отчёта.
REPORT_COL_GAP = "  "

#: Ошибок загрузки в тексте batch.report (сверху; остальные — итогом).
BATCH_REPORT_ERROR_LIMIT = 10

#: мм в одном мкм — множитель среза ЧКХ (формула calc.diffraction.cutoff).
WL_UM_PER_MM = 1e-3

#: Служебный префикс имён batch.load в контексте REPL не используется:
#: системы кладутся под имя файла (stem), без смены текущей.


# ============================================================
# Метрики пакета (движки — существующие; лёгкий вариант по умолчанию)
# ============================================================

def _paraxial_metric(key: str, absolute: bool = False):
    """Метрика из параксиального расчёта (domain.calculations)."""
    def compute(system, opts: dict):
        from domain.calculations import paraxial_trace
        value = paraxial_trace(system).get(key)
        if value is None:
            raise CommandError(ERR_INVALID_PARAM,
                               f"параксиальный расчёт не дал {key!r}")
        return abs(value) if absolute else value
    return compute


def _seidel_metric(key: str):
    """Сумма Зейделя SI..SV (domain.calculations)."""
    def compute(system, opts: dict):
        from domain.calculations import seidel_aberrations
        return seidel_aberrations(system).get(key)
    return compute


def _strehl_metric(key: str):
    """Поле результата compute_strehl (strehl_exact / sigma_w)."""
    def compute(system, opts: dict):
        from analysis.strehl import compute_strehl
        return compute_strehl(system, field_y=opts["field_y"]).get(key)
    return compute


def _c_spot_rms(system, opts: dict) -> float:
    """RMS кружка рассеяния (мм), лёгкая сетка по умолчанию."""
    from analysis.aberrations import compute_rms_spot, compute_spot_diagram
    spots = compute_spot_diagram(system, num_rays=opts["num_rays"],
                                 field_y=opts["field_y"])
    return float(compute_rms_spot(spots))


def _c_spot_rms_poly(system, opts: dict) -> float:
    """Полихроматический RMS пятна (мм) по рабочим λ системы."""
    from analysis.aberrations import compute_polychromatic_rms
    return float(compute_polychromatic_rms(
        system, num_rays=opts["num_rays"], field_y=opts["field_y"]))


def _c_track_length(system, opts: dict) -> float:
    """Длина хода: сумма толщин поверхностей (мм)."""
    return float(sum(s.thickness for s in system.surfaces))


def _c_airy_diameter(system, opts: dict) -> float:
    """Диаметр диска Эйри 2·1.22·λ·F/# (мкм) — дифракционный предел."""
    from domain.calculations import paraxial_trace
    f_number = abs(paraxial_trace(system).get("f_number") or 0.0)
    if f_number <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "F/# ≤ 0: апертура системы не задана")
    return 2.0 * AIRY_FIRST_ZERO * get_primary_wl(system) * f_number


def _c_cutoff_lpmm(system, opts: dict) -> float:
    """Дифракционный срез ЧКХ 1/(λ·F/#), лин/мм (calc.diffraction.cutoff)."""
    from domain.calculations import paraxial_trace
    f_number = abs(paraxial_trace(system).get("f_number") or 0.0)
    if f_number <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "F/# ≤ 0: апертура системы не задана")
    return 1.0 / (get_primary_wl(system) * WL_UM_PER_MM * f_number)


def _c_d90_um(system, opts: dict) -> float:
    """Диаметр зоны 90 % энергии (мкм), геометрическая ФКЭ (quality)."""
    return float(_ee_diameters_geometric(
        system, [EE_FRACTION_DEFAULT], opts["field_y"],
        get_primary_wl(system), opts["num_rays"])[0]["diameter_um"])


#: Реестр метрик: имя → {description, unit, better, compute}.
#: ``better`` — полярность («max» — чем больше тем лучше, «min» — чем
#: меньше тем лучше, None — целезависимая).
_METRICS: Dict[str, dict] = {
    "num_surfaces": {
        "description": "число поверхностей",
        "unit": "шт", "better": None,
        "compute": lambda s, o: s.num_surfaces},
    "track_length": {
        "description": "длина хода (сумма толщин)",
        "unit": "мм", "better": None,
        "compute": _c_track_length},
    "num_wavelengths": {
        "description": "число рабочих λ",
        "unit": "шт", "better": None,
        "compute": lambda s, o: len(s.wavelengths)},
    "num_fields": {
        "description": "число точек поля",
        "unit": "шт", "better": None,
        "compute": lambda s, o: len(s.field_points)},
    "efl": {
        "description": "фокусное расстояние |f'|",
        "unit": "мм", "better": None,
        "compute": _paraxial_metric("focal_length", absolute=True)},
    "f_number": {
        "description": "диафрагменное число |F/#|",
        "unit": "-", "better": None,
        "compute": _paraxial_metric("f_number", absolute=True)},
    "epd": {
        "description": "диаметр входного зрачка",
        "unit": "мм", "better": None,
        "compute": _paraxial_metric("entrance_pupil_diameter",
                                    absolute=True)},
    "bfd": {
        "description": "задний фокальный отрезок |BFD|",
        "unit": "мм", "better": None,
        "compute": _paraxial_metric("back_focal_distance",
                                    absolute=True)},
    "magnification": {
        "description": "параксиальное увеличение",
        "unit": "-", "better": None,
        "compute": _paraxial_metric("magnification")},
    "spot_rms": {
        "description": "RMS кружка рассеяния (монохром, основная λ)",
        "unit": "мм", "better": "min", "compute": _c_spot_rms},
    "spot_rms_poly": {
        "description": "полихроматический RMS пятна (по рабочим λ)",
        "unit": "мм", "better": "min", "compute": _c_spot_rms_poly},
    "strehl": {
        "description": "число Штреля (точное, FFT ФРТ)",
        "unit": "-", "better": "max",
        "compute": _strehl_metric("strehl_exact")},
    "sigma_w": {
        "description": "СКВ волнового фронта",
        "unit": "λ", "better": "min",
        "compute": _strehl_metric("sigma_w")},
    "airy_um": {
        "description": "диаметр диска Эйри 2·1.22·λ·F/#",
        "unit": "мкм", "better": "min", "compute": _c_airy_diameter},
    "cutoff_lpmm": {
        "description": "дифракционный срез ЧКХ 1/(λ·F/#)",
        "unit": "лин/мм", "better": "max", "compute": _c_cutoff_lpmm},
    "d90_um": {
        "description": "диаметр зоны 90 % энергии (геометрическая ФКЭ)",
        "unit": "мкм", "better": "min", "compute": _c_d90_um},
    "SI": {"description": "сумма Зейделя SI (сферическая)",
           "unit": "-", "better": None,
           "compute": _seidel_metric("SI")},
    "SII": {"description": "сумма Зейделя SII (кома)",
            "unit": "-", "better": None,
            "compute": _seidel_metric("SII")},
    "SIII": {"description": "сумма Зейделя SIII (астигматизм)",
             "unit": "-", "better": None,
             "compute": _seidel_metric("SIII")},
    "SIV": {"description": "сумма Зейделя SIV (Петцваль)",
            "unit": "-", "better": None,
            "compute": _seidel_metric("SIV")},
    "SV": {"description": "сумма Зейделя SV (дисторсия)",
           "unit": "-", "better": None,
           "compute": _seidel_metric("SV")},
}

METRIC_CHOICES = sorted(_METRICS)


# ============================================================
# Общие хелперы пакета
# ============================================================

def _files_arg(files) -> List[str]:
    """Непустой список путей пакета (``invalid_param`` если пусто)."""
    if not files:
        raise CommandError(
            ERR_INVALID_PARAM,
            "files: передан пустой список — пакету нужен хотя бы один "
            "файл (.opj/.json/.lbo) или результат batch.dir")
    return [str(f) for f in files]


def _load_rows(files: List[str]):
    """Загрузить системы пакета: ([(файл, имя, система)], errors[]).

    Ошибки отдельных файлов не роняют пакет (ТЗ §пакетных прогонов).
    """
    rows, errors = [], []
    for path in files:
        try:
            system = load_system(path)
        except CommandError as exc:
            errors.append({"file": path, **exc.to_dict()})
            continue
        except Exception as exc:  # мусорные файлы не роняют пакет
            errors.append({"file": path, "code": "internal_error",
                           "message": f"{type(exc).__name__}: {exc}"})
            continue
        if not getattr(system, "surfaces", None):
            errors.append({"file": path, "code": "invalid_param",
                           "message": "система без поверхностей"})
            continue
        name = (getattr(system, "name", None)
                or os.path.splitext(os.path.basename(path))[0])
        rows.append((path, name, system))
    return rows, errors


def _require_loaded(rows: List[tuple], errors: List[dict],
                    files: List[str]) -> None:
    """Инвариант ТЗ: ни одного валидного файла → invalid_param."""
    if not rows:
        first = (f"; первая: {errors[0]['file']}: "
                 f"{errors[0].get('code')}: {errors[0].get('message')}"
                 if errors else "")
        raise CommandError(
            ERR_INVALID_PARAM,
            f"ни один из {len(files)} файлов не загрузился как оптическая "
            f"система{first}")


def _metric_opts(num_rays, field_y) -> dict:
    """Параметры вычисления метрик (лёгкий вариант по умолчанию)."""
    return {"num_rays": (num_rays if num_rays
                         else BATCH_SPOT_RAYS_DEFAULT),
            "field_y": (field_y if field_y is not None
                        else BATCH_FIELD_DEFAULT)}


def _metrics_arg(metrics, default) -> List[str]:
    """Список метрик: явный (валидация имён) или умолчание пакета."""
    names = [str(m) for m in metrics] if metrics else list(default)
    unknown = [m for m in names if m not in _METRICS]
    if unknown:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"неизвестные метрики {unknown!r}; допустимы: {METRIC_CHOICES}")
    if not names:
        raise CommandError(ERR_INVALID_PARAM, "список метрик пуст")
    return names


def _metric_value(system, metric: str, opts: dict) -> Tuple[Any, Optional[str]]:
    """Одна метрика системы: (значение | None, ошибка | None).

    Вычислительные сбои и non-finite значения не роняют пакет.
    """
    try:
        value = _METRICS[metric]["compute"](system, opts)
    except CommandError as exc:
        return None, exc.message
    except Exception as exc:  # noqa: BLE001 — по элементу, не по пакету
        return None, f"{type(exc).__name__}: {exc}"
    if isinstance(value, float) and not math.isfinite(value):
        return None, "не-конечное значение"
    return value, None


def _metric_rows(files: List[str], metrics: List[str], opts: dict):
    """Метрики по всем системам: (rows, errors); row = {file, name, ...}.

    Значения — плоские поля по имени метрики; сбой конкретной метрики
    оставляет значение None (в rows['metric_errors'] — причина).
    """
    loaded, errors = _load_rows(files)
    _require_loaded(loaded, errors, files)
    rows = []
    for path, name, system in loaded:
        row = {"file": path, "name": name, "ok": True}
        failed = {}
        for metric in metrics:
            value, err = _metric_value(system, metric, opts)
            row[metric] = value
            if err:
                failed[metric] = err
        if failed:
            row["metric_errors"] = failed
        rows.append(row)
    return rows, errors


def _numeric_pairs(rows: List[dict], metric: str) -> List[Tuple[dict, float]]:
    """(row, значение) валидных строк по метрике."""
    pairs = []
    for row in rows:
        value = row.get(metric)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            pairs.append((row, float(value)))
    return pairs


def _fmt_value(value) -> str:
    """Число/строка для текстового отчёта (None → прочерк)."""
    if value is None:
        return "-"
    if isinstance(value, float):
        return REPORT_VALUE_FMT.format(value)
    return str(value)


def _unique_path(used: set, path: str) -> str:
    """Путь, не занятый в этом прогоне и на диске (коллизии stem →
    _2, _3, ...; существующие файлы не перезаписываются молча)."""
    if path not in used and not os.path.exists(path):
        used.add(path)
        return path
    stem, ext = os.path.splitext(path)
    index = 2
    while True:
        candidate = f"{stem}_{index}{ext}"
        if candidate not in used and not os.path.exists(candidate):
            used.add(candidate)
            return candidate
        index += 1


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать пакетные команды (R500-15)."""

    # ----------------------------------------------------------
    # batch.metrics — справочник метрик пакета
    # ----------------------------------------------------------

    @registry.command(
        "batch.metrics", category="batch",
        description="Справочник метрик пакета: имя, описание, единица, "
                    "полярность («лучше больше/меньше» — для batch.rank/"
                    "check auto-режимов)",
        returns="{count, metrics: [{name, description, unit, better}]}",
        params=[])
    def batch_metrics(ctx):
        return {"count": len(_METRICS),
                "metrics": [{"name": name, **{k: spec[k] for k in
                                              ("description", "unit",
                                               "better")}}
                            for name, spec in sorted(_METRICS.items())]}

    # ----------------------------------------------------------
    # batch.dir — скан каталога по расширениям
    # ----------------------------------------------------------

    @registry.command(
        "batch.dir", category="batch",
        description="Собрать список файлов систем в каталоге по "
                    "расширениям (для параметра files остальных batch.*)",
        returns="{dir, extensions, recursive, count, files: [...], skipped}",
        params=[
            Param("path", required=True,
                  help="каталог для скана (путь задаётся явно)"),
            Param("extensions", type="list",
                  help=f"расширения; по умолчанию "
                       f"{list(DIR_EXTENSIONS_DEFAULT)}"),
            Param("recursive", type="bool",
                  help="обход подкаталогов (по умолчанию false)"),
        ])
    def batch_dir(ctx, path, extensions, recursive):
        if not os.path.isdir(path):
            raise CommandError(ERR_IO_ERROR,
                               f"каталог {path!r} не найден")
        exts = set()
        for ext in (extensions or DIR_EXTENSIONS_DEFAULT):
            item = str(ext).strip().lower()
            if not item:
                continue
            exts.add(item if item.startswith(".") else "." + item)
        files, skipped = [], 0
        if recursive:
            for root, _dirs, names in os.walk(path):
                for nm in names:
                    if os.path.splitext(nm)[1].lower() in exts:
                        files.append(os.path.join(root, nm))
                    else:
                        skipped += 1
        else:
            for nm in os.listdir(path):
                full = os.path.join(path, nm)
                if not os.path.isfile(full):
                    continue
                if os.path.splitext(nm)[1].lower() in exts:
                    files.append(full)
                else:
                    skipped += 1
        return {"dir": os.path.abspath(path),
                "extensions": sorted(exts),
                "recursive": bool(recursive),
                "count": len(files), "files": sorted(files),
                "skipped": skipped}

    # ----------------------------------------------------------
    # batch.names — имена систем пакета
    # ----------------------------------------------------------

    @registry.command(
        "batch.names", category="batch",
        description="Имена систем пакета: файл → имя системы из файла "
                    "(fallback — база имени файла)",
        returns="{count, ok, names: [{file, stem, name, num_surfaces}], "
                "errors: [...]}",
        params=[Param("files", type="list", required=True,
                      help="список путей (.opj/.json/.lbo)")])
    def batch_names(ctx, files):
        paths = _files_arg(files)
        loaded, errors = _load_rows(paths)
        _require_loaded(loaded, errors, paths)
        names = [{"file": path, "stem": os.path.splitext(
                      os.path.basename(path))[0], "name": name,
                  "num_surfaces": system.num_surfaces}
                 for path, name, system in loaded]
        return {"count": len(names), "ok": len(names),
                "names": names, "errors": errors}

    # ----------------------------------------------------------
    # batch.info — обзор пакета
    # ----------------------------------------------------------

    @registry.command(
        "batch.info", category="batch",
        description="Обзор пакета: по каждому файлу формат, размер, "
                    "поверхности, λ, поля, стёкла, длина хода",
        returns="{count, ok, rows: [{file, format, size_bytes, "
                "num_surfaces, ...}], errors: [...]}",
        params=[Param("files", type="list", required=True,
                      help="список путей (.opj/.json/.lbo)")])
    def batch_info(ctx, files):
        paths = _files_arg(files)
        rows, errors = [], []
        for path in paths:
            try:
                size = os.path.getsize(path)
                fmt = detect_format(path)
                system = load_system(path)
            except CommandError as exc:
                errors.append({"file": path, **exc.to_dict()})
                continue
            except OSError as exc:
                errors.append({"file": path, "code": "io_error",
                               "message": str(exc)})
                continue
            rows.append({
                "file": path, "format": fmt, "size_bytes": size,
                "num_surfaces": system.num_surfaces,
                "num_wavelengths": len(system.wavelengths),
                "num_fields": len(system.field_points),
                "glasses": sorted({s.glass for s in system.surfaces
                                   if s.glass}),
                "track_length": float(sum(s.thickness
                                          for s in system.surfaces)),
            })
        if not rows:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"ни один из {len(paths)} файлов не читается"
                + (f"; первая ошибка: {errors[0]['file']}: "
                   f"{errors[0].get('message')}" if errors else ""))
        return {"count": len(rows), "ok": len(rows), "rows": rows,
                "errors": errors}

    # ----------------------------------------------------------
    # batch.load — пакет в контекст REPL
    # ----------------------------------------------------------

    @registry.command(
        "batch.load", category="batch",
        description="Загрузить все системы пакета в контекст REPL под "
                    "именами-базами файлов (текущая система не меняется; "
                    "коллизии имён — суффиксы _2, _3, ...)",
        returns="{count, loaded: [{file, name, num_surfaces}], errors}",
        params=[Param("files", type="list", required=True,
                      help="список путей (.opj/.json/.lbo)")])
    def batch_load(ctx, files):
        paths = _files_arg(files)
        loaded, errors = _load_rows(paths)
        _require_loaded(loaded, errors, paths)
        used = set(ctx.systems)
        rows = []
        for path, _name, system in loaded:
            key = _unique_path(used, os.path.splitext(
                os.path.basename(path))[0])
            ctx.put_system(key, system, make_current=False)
            rows.append({"file": path, "name": key,
                         "num_surfaces": system.num_surfaces})
        return {"count": len(rows), "loaded": rows, "errors": errors}

    # ----------------------------------------------------------
    # batch.run — произвольная команда над каждым файлом
    # ----------------------------------------------------------

    @registry.command(
        "batch.run", category="batch",
        description="Выполнить команду реестра над каждым файлом пакета "
                    "(команда получает file=<путь>; данные ответа — "
                    "параметром include_data)",
        returns="{command, count, ok, rows: [{file, ok, error?, data?}], "
                "errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("cmd", required=True,
                  help="имя команды (например 'calc.paraxial')"),
            Param("args", type="dict",
                  help="доп. параметры команды (кроме file)"),
            Param("include_data", type="bool",
                  help="включить данные ответа каждой команды "
                       "(по умолчанию false)"),
        ])
    def batch_run(ctx, files, cmd, args, include_data):
        paths = _files_arg(files)
        registry.get(cmd)  # unknown_command, если команды нет
        extra = dict(args or {})
        rows, errors = [], []
        for path in paths:
            result = registry.execute(cmd, ctx, {"file": path, **extra})
            if result.ok:
                row = {"file": path, "ok": True}
                if include_data:
                    row["data"] = result.data
                rows.append(row)
            else:
                error = result.error or {}
                errors.append({"file": path, **error})
                rows.append({"file": path, "ok": False,
                             "error": error.get("message")})
        if not rows or not any(r["ok"] for r in rows):
            first = errors[0] if errors else {}
            raise CommandError(
                ERR_INVALID_PARAM,
                f"команда {cmd!r} не выполнилась ни на одном из "
                f"{len(paths)} файлов"
                + (f"; первая ошибка: {first.get('code')}: "
                   f"{first.get('message')}" if first else ""))
        return {"command": cmd, "count": len(rows),
                "ok": sum(1 for r in rows if r["ok"]), "rows": rows,
                "errors": errors}

    # ----------------------------------------------------------
    # batch.validate — санити по всем файлам
    # ----------------------------------------------------------

    @registry.command(
        "batch.validate", category="batch",
        description="Санити-проверки system.validate по всем файлам "
                    "пакета (структура/апертура/λ/стёкла) с общим "
                    "вердиктом",
        returns="{count, pass, rows: [{file, valid, errors, warnings}], "
                "errors: [...]}",
        params=[Param("files", type="list", required=True,
                      help="список путей (.opj/.json/.lbo)")])
    def batch_validate(ctx, files):
        paths = _files_arg(files)
        rows, errors = [], []
        for path in paths:
            result = registry.execute("system.validate", ctx,
                                      {"file": path})
            if not result.ok:
                error = result.error or {}
                errors.append({"file": path, **error})
                continue
            data = result.data
            rows.append({"file": path, "valid": bool(data["valid"]),
                         "errors": data["errors"],
                         "warnings": data["warnings"]})
        if not rows:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"system.validate не прошёл ни по одному из {len(paths)} "
                f"файлов")
        return {"count": len(rows),
                "pass": all(r["valid"] for r in rows),
                "rows": rows, "errors": errors}

    # ----------------------------------------------------------
    # batch.metric — одна метрика по всем системам
    # ----------------------------------------------------------

    @registry.command(
        "batch.metric", category="batch",
        description="Одна метрика качества по всем системам пакета "
                    "(efl, F/#, RMS пятна, Штрель, Зейдель, ФКЭ, ...; "
                    "справочник — batch.metrics)",
        returns="{metric, description, unit, better, count, ok, rows: "
                "[{file, name, <метрика>}], errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("metric", required=True, choices=METRIC_CHOICES,
                  help="имя метрики (см. batch.metrics)"),
            Param("num_rays", type="int",
                  help=f"лучей сетки зрачка (по умолчанию "
                       f"{BATCH_SPOT_RAYS_DEFAULT} — лёгкий вариант)"),
            Param("field_y", type="float",
                  help=f"поле, градусы (по умолчанию {BATCH_FIELD_DEFAULT})"),
        ])
    def batch_metric(ctx, files, metric, num_rays, field_y):
        paths = _files_arg(files)
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, [metric], opts)
        spec = _METRICS[metric]
        return {"metric": metric, "description": spec["description"],
                "unit": spec["unit"], "better": spec["better"],
                "count": len(rows), "ok": len(rows),
                "rows": rows, "errors": errors}

    # ----------------------------------------------------------
    # batch.summary — таблица нескольких метрик
    # ----------------------------------------------------------

    @registry.command(
        "batch.summary", category="batch",
        description="Сводная таблица по нескольким метрикам сразу + итоги "
                    "min/max/mean по каждой метрике",
        returns="{metrics, count, ok, rows: [{file, name, <метрики>...}], "
                "summary: {метрика: {min, max, mean, min_file, max_file}}, "
                "errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("metrics", type="list",
                  help=f"метрики (по умолчанию "
                       f"{list(SUMMARY_METRICS_DEFAULT)})"),
            Param("num_rays", type="int",
                  help=f"лучей сетки зрачка (по умолчанию "
                       f"{BATCH_SPOT_RAYS_DEFAULT})"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_summary(ctx, files, metrics, num_rays, field_y):
        paths = _files_arg(files)
        names = _metrics_arg(metrics, SUMMARY_METRICS_DEFAULT)
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, names, opts)
        summary = {}
        for metric in names:
            pairs = _numeric_pairs(rows, metric)
            if not pairs:
                continue
            values = [v for _r, v in pairs]
            summary[metric] = {
                "min": min(values), "max": max(values),
                "mean": sum(values) / len(values),
                "min_file": min(pairs, key=lambda p: p[1])[0]["file"],
                "max_file": max(pairs, key=lambda p: p[1])[0]["file"],
            }
        return {"metrics": names, "count": len(rows), "ok": len(rows),
                "rows": rows, "summary": summary, "errors": errors}

    # ----------------------------------------------------------
    # batch.rank — ранжирование по метрике
    # ----------------------------------------------------------

    @registry.command(
        "batch.rank", category="batch",
        description="Ранжирование систем по метрике (auto — лучшая "
                    "система первой: RMS растёт, Штрель падает) + best/"
                    "worst",
        returns="{metric, order, count, rows: [{rank, file, name, "
                "<метрика>}], best, worst, errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("metric", required=True, choices=METRIC_CHOICES,
                  help="имя метрики (см. batch.metrics)"),
            Param("order", choices=list(RANK_ORDERS),
                  help="asc/desc/auto (по умолчанию auto — по полярности)"),
            Param("top", type="int",
                  help="показать первые N строк (по умолчанию все)"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_rank(ctx, files, metric, order, top, num_rays, field_y):
        paths = _files_arg(files)
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, [metric], opts)
        pairs = _numeric_pairs(rows, metric)
        if not pairs:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"метрика {metric!r} не посчитана ни на одной системе")
        better = _METRICS[metric]["better"]
        if not order or order == "auto":
            order = "desc" if better == "max" else "asc"
        pairs.sort(key=lambda p: p[1], reverse=(order == "desc"))
        ranked = [{"rank": i + 1, "file": row["file"], "name": row["name"],
                   metric: value}
                  for i, (row, value) in enumerate(pairs)]
        shown = ranked[:max(0, top)] if top is not None else ranked
        return {"metric": metric, "order": order, "count": len(ranked),
                "rows": shown, "best": ranked[0], "worst": ranked[-1],
                "errors": errors}

    # ----------------------------------------------------------
    # batch.stats — статистика метрики
    # ----------------------------------------------------------

    @registry.command(
        "batch.stats", category="batch",
        description="Статистика метрики по пакету: count/min/max/mean/"
                    "median/СКО + файлы-экстремумы",
        returns="{metric, unit, count, min, max, mean, median, stdev, "
                "min_file, max_file, errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("metric", required=True, choices=METRIC_CHOICES,
                  help="имя метрики (см. batch.metrics)"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_stats(ctx, files, metric, num_rays, field_y):
        paths = _files_arg(files)
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, [metric], opts)
        pairs = _numeric_pairs(rows, metric)
        if not pairs:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"метрика {metric!r} не посчитана ни на одной системе")
        values = [v for _r, v in pairs]
        stdev = (statistics.stdev(values) if len(values) >= 2 else 0.0)
        return {"metric": metric, "unit": _METRICS[metric]["unit"],
                "count": len(values),
                "min": min(values), "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "stdev": stdev,
                "min_file": min(pairs, key=lambda p: p[1])[0]["file"],
                "max_file": max(pairs, key=lambda p: p[1])[0]["file"],
                "errors": errors}

    # ----------------------------------------------------------
    # batch.filter — отбор по условию на метрику
    # ----------------------------------------------------------

    @registry.command(
        "batch.filter", category="batch",
        description="Отобрать системы пакета по условию на метрику "
                    "(gt/ge/lt/le/eq/ne/range)",
        returns="{metric, op, count, total, kept: [{file, name, "
                "<метрика>}], errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("metric", required=True, choices=METRIC_CHOICES,
                  help="имя метрики (см. batch.metrics)"),
            Param("op", required=True, choices=list(FILTER_OPS),
                  help="операция сравнения"),
            Param("value", type="float",
                  help="порог (для gt/ge/lt/le/eq/ne)"),
            Param("value_min", type="float",
                  help="нижняя граница (для op=range)"),
            Param("value_max", type="float",
                  help="верхняя граница (для op=range)"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_filter(ctx, files, metric, op, value, value_min, value_max,
                     num_rays, field_y):
        paths = _files_arg(files)
        if op == "range":
            if value_min is None or value_max is None:
                raise CommandError(
                    ERR_INVALID_PARAM,
                    "op=range требует value_min и value_max")
            lo, hi = float(value_min), float(value_max)
            if lo > hi:
                raise CommandError(ERR_INVALID_PARAM,
                                   f"value_min={lo} > value_max={hi}")
        elif value is None:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"op={op!r} требует параметр value")
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, [metric], opts)
        kept = []
        for row in rows:
            v = row.get(metric)
            if v is None:
                continue
            take = {
                "gt": lambda: v > value, "ge": lambda: v >= value,
                "lt": lambda: v < value, "le": lambda: v <= value,
                "eq": lambda: v == value, "ne": lambda: v != value,
                "range": lambda: lo <= v <= hi,
            }[op]()
            if take:
                kept.append({"file": row["file"], "name": row["name"],
                             metric: v})
        return {"metric": metric, "op": op, "count": len(kept),
                "total": len(rows), "kept": kept, "errors": errors}

    # ----------------------------------------------------------
    # batch.check — пороговая проверка по всем системам
    # ----------------------------------------------------------

    @registry.command(
        "batch.check", category="batch",
        description="Пороговая проверка метрики по всем системам пакета: "
                    "min — «не ниже порога», max — «не выше» (auto — по "
                    "полярности метрики)",
        returns="{metric, mode, comparison, threshold, pass, count, rows: "
                "[{file, name, <метрика>, pass}], worst, errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("metric", required=True, choices=METRIC_CHOICES,
                  help="имя метрики (см. batch.metrics)"),
            Param("threshold", type="float", required=True,
                  help="порог метрики"),
            Param("mode", choices=list(CHECK_MODES),
                  help="min/max/auto (по умолчанию auto — по полярности)"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_check(ctx, files, metric, threshold, mode, num_rays, field_y):
        paths = _files_arg(files)
        better = _METRICS[metric]["better"]
        if not mode or mode == "auto":
            mode = "min" if better == "max" else "max"
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, [metric], opts)
        checked = []
        for row in rows:
            value = row.get(metric)
            if value is None:
                continue
            passed = (value >= threshold if mode == "min"
                      else value <= threshold)
            checked.append({"file": row["file"], "name": row["name"],
                            metric: value, "pass": bool(passed)})
        if not checked:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"метрика {metric!r} не посчитана ни на одной системе")
        comparison = "≥" if mode == "min" else "≤"
        failed = [r for r in checked if not r["pass"]]
        return {"metric": metric, "mode": mode,
                "comparison": f"{metric} {comparison} {threshold}",
                "threshold": threshold,
                "pass": not failed, "count": len(checked),
                "rows": checked,
                "worst": (max(failed, key=lambda r: r[metric])
                          if mode == "min" and failed
                          else min(failed, key=lambda r: r[metric])
                          if failed else None),
                "errors": errors}

    # ----------------------------------------------------------
    # batch.compare — сравнение с эталонным файлом
    # ----------------------------------------------------------

    @registry.command(
        "batch.compare", category="batch",
        description="Сравнение каждой системы пакета с эталонным файлом "
                    "по метрикам (Δ и Δ%)",
        returns="{ref, metrics, count, rows: [{file, name, deltas: "
                "{метрика: {ref, value, delta, delta_percent}}}], errors}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей для сравнения"),
            Param("ref", required=True,
                  help="эталонный файл системы (.opj/.json/.lbo)"),
            Param("metrics", type="list",
                  help=f"метрики (по умолчанию "
                       f"{list(SUMMARY_METRICS_DEFAULT)})"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_compare(ctx, files, ref, metrics, num_rays, field_y):
        paths = _files_arg(files)
        names = _metrics_arg(metrics, SUMMARY_METRICS_DEFAULT)
        opts = _metric_opts(num_rays, field_y)
        try:
            ref_system = load_system(ref)
        except CommandError as exc:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"эталон {ref!r} не загрузился: {exc.message}") from exc
        ref_values = {}
        for metric in names:
            ref_values[metric], _err = _metric_value(ref_system, metric,
                                                     opts)
        rows, errors = _metric_rows(paths, names, opts)
        out_rows = []
        for row in rows:
            deltas = {}
            for metric in names:
                ref_v = ref_values.get(metric)
                value = row.get(metric)
                delta = (value - ref_v
                         if isinstance(value, (int, float))
                         and isinstance(ref_v, (int, float)) else None)
                delta_pct = (100.0 * delta / ref_v
                             if delta is not None and ref_v else None)
                deltas[metric] = {"ref": ref_v, "value": value,
                                  "delta": delta,
                                  "delta_percent": delta_pct}
            out_rows.append({"file": row["file"], "name": row["name"],
                             "deltas": deltas})
        return {"ref": ref, "metrics": names, "count": len(out_rows),
                "rows": out_rows, "errors": errors}

    # ----------------------------------------------------------
    # batch.apply — команда-модификация к копиям систем
    # ----------------------------------------------------------

    @registry.command(
        "batch.apply", category="batch",
        description="Применить команду-модификацию (system.scale, "
                    "system.reverse, ...) к копиям всех систем пакета: "
                    "команда выполняется с file=<путь> и out=<копия> в "
                    "out_dir",
        returns="{command, out_dir, suffix, ext, count, ok, applied: "
                "[{file, out}], errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("cmd", required=True,
                  help="команда-модификация (должна принимать out)"),
            Param("args", type="dict",
                  help="доп. параметры команды (кроме file/out)"),
            Param("out_dir", required=True,
                  help="каталог для модифицированных копий"),
            Param("suffix", default=APPLY_SUFFIX_DEFAULT,
                  help=f"суффикс имён копий (по умолчанию "
                       f"{APPLY_SUFFIX_DEFAULT!r})"),
            Param("ext", choices=["opj", "json"],
                  default=BATCH_FORMAT_DEFAULT,
                  help="формат копий (по умолчанию json — .opj-раундтрип "
                       "теряет точки поля)"),
        ])
    def batch_apply(ctx, files, cmd, args, out_dir, suffix, ext):
        paths = _files_arg(files)
        registry.get(cmd)  # unknown_command, если команды нет
        os.makedirs(out_dir, exist_ok=True)
        extra = dict(args or {})
        used: set = set()
        applied, errors = [], []
        for path in paths:
            stem = os.path.splitext(os.path.basename(path))[0]
            dst = _unique_path(used, os.path.join(
                out_dir, f"{stem}{suffix}.{ext}"))
            result = registry.execute(cmd, ctx,
                                      {"file": path, "out": dst, **extra})
            if result.ok:
                applied.append({"file": path, "out": os.path.abspath(dst)})
            else:
                error = result.error or {}
                errors.append({"file": path, **error})
        if not applied:
            first = errors[0] if errors else {}
            raise CommandError(
                ERR_INVALID_PARAM,
                f"команда {cmd!r} не применилась ни к одному из "
                f"{len(paths)} файлов"
                + (f"; первая ошибка: {first.get('code')}: "
                   f"{first.get('message')}" if first else ""))
        return {"command": cmd, "out_dir": os.path.abspath(out_dir),
                "suffix": suffix, "ext": ext, "count": len(applied),
                "ok": len(applied), "applied": applied, "errors": errors}

    # ----------------------------------------------------------
    # batch.changes — до/после модификации
    # ----------------------------------------------------------

    @registry.command(
        "batch.changes", category="batch",
        description="Как каждая система изменилась после команды-"
                    "модификации: метрики до → после → Δ (модификация — "
                    "во временном файле, исходники не трогаются)",
        returns="{command, metrics, count, rows: [{file, name, before, "
                "after, delta}], errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("cmd", required=True,
                  help="команда-модификация (должна принимать out)"),
            Param("args", type="dict",
                  help="доп. параметры команды (кроме file/out)"),
            Param("metrics", type="list",
                  help=f"метрики (по умолчанию "
                       f"{list(CHANGES_METRICS_DEFAULT)})"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_changes(ctx, files, cmd, args, metrics, num_rays, field_y):
        import tempfile
        paths = _files_arg(files)
        registry.get(cmd)  # unknown_command, если команды нет
        names = _metrics_arg(metrics, CHANGES_METRICS_DEFAULT)
        opts = _metric_opts(num_rays, field_y)
        extra = dict(args or {})

        def _values(system) -> dict:
            out = {}
            for metric in names:
                out[metric], _err = _metric_value(system, metric, opts)
            return out

        rows, errors = [], []
        with tempfile.TemporaryDirectory(prefix="batch_changes_") as tmp:
            used: set = set()
            for path in paths:
                try:
                    before_system = load_system(path)
                except CommandError as exc:
                    errors.append({"file": path, **exc.to_dict()})
                    continue
                before = _values(before_system)
                stem = os.path.splitext(os.path.basename(path))[0]
                tmp_out = _unique_path(
                    used, os.path.join(tmp, f"{stem}.json"))
                result = registry.execute(cmd, ctx,
                                          {"file": path, "out": tmp_out,
                                           **extra})
                if not result.ok:
                    error = result.error or {}
                    errors.append({"file": path, **error})
                    continue
                after = _values(load_system(tmp_out))
                delta = {}
                for metric in names:
                    b, a = before.get(metric), after.get(metric)
                    delta[metric] = (a - b
                                     if isinstance(a, (int, float))
                                     and isinstance(b, (int, float))
                                     else None)
                rows.append({"file": path,
                             "name": (getattr(before_system, "name", None)
                                      or stem),
                             "before": before, "after": after,
                             "delta": delta})
        if not rows:
            first = errors[0] if errors else {}
            raise CommandError(
                ERR_INVALID_PARAM,
                f"модификация {cmd!r} не прошла ни по одному из "
                f"{len(paths)} файлов"
                + (f"; первая ошибка: {first.get('code')}: "
                   f"{first.get('message')}" if first else ""))
        return {"command": cmd, "metrics": names, "count": len(rows),
                "rows": rows, "errors": errors}

    # ----------------------------------------------------------
    # batch.convert — пакетная конвертация формата
    # ----------------------------------------------------------

    @registry.command(
        "batch.convert", category="batch",
        description="Пакетная конвертация систем в другой формат "
                    "(.opj ↔ .json; .json сохраняет точки поля, "
                    ".opj-раундтрип их теряет)",
        returns="{ext, out_dir, count, ok, converted: [{src, dst}], "
                "errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("out_dir", required=True, help="каталог назначения"),
            Param("ext", choices=["opj", "json"],
                  default=BATCH_FORMAT_DEFAULT,
                  help="целевой формат (по умолчанию json)"),
        ])
    def batch_convert(ctx, files, out_dir, ext):
        paths = _files_arg(files)
        os.makedirs(out_dir, exist_ok=True)
        converted, errors = [], []
        used: set = set()
        for path in paths:
            try:
                system = load_system(path)
            except CommandError as exc:
                errors.append({"file": path, **exc.to_dict()})
                continue
            stem = os.path.splitext(os.path.basename(path))[0]
            dst = os.path.join(out_dir, f"{stem}.{ext}")
            if os.path.abspath(dst) == os.path.abspath(path):
                errors.append({"file": path, "code": "invalid_param",
                               "message": "источник и назначение "
                                          "совпадают"})
                continue
            dst = _unique_path(used, dst)
            try:
                save_system(system, dst)
            except CommandError as exc:
                errors.append({"file": path, **exc.to_dict()})
                continue
            converted.append({"src": path, "dst": os.path.abspath(dst)})
        if not converted:
            first = errors[0] if errors else {}
            raise CommandError(
                ERR_INVALID_PARAM,
                f"ни одна из {len(paths)} систем не конвертирована"
                + (f"; первая ошибка: {first.get('code')}: "
                   f"{first.get('message')}" if first else ""))
        return {"ext": ext, "out_dir": os.path.abspath(out_dir),
                "count": len(converted), "ok": len(converted),
                "converted": converted, "errors": errors}

    # ----------------------------------------------------------
    # batch.dedupe — дубликаты по контрольной сумме
    # ----------------------------------------------------------

    @registry.command(
        "batch.dedupe", category="batch",
        description="Одинаковые файлы пакета по контрольной сумме "
                    "(md5/sha1/sha256; бит-в-бит), группы дубликатов",
        returns="{algo, total, unique, num_duplicate_files, groups: "
                "[{hex, count, files}], errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (любые файлы)"),
            Param("algo", choices=list(CHECKSUM_ALGOS),
                  default=DEDUPE_ALGO_DEFAULT,
                  help="алгоритм хеша"),
        ])
    def batch_dedupe(ctx, files, algo):
        paths = _files_arg(files)
        by_hash: Dict[str, List[str]] = {}
        errors = []
        for path in paths:
            try:
                with open(path, "rb") as f:
                    digest = hashlib.new(algo, f.read()).hexdigest()
            except OSError as exc:
                errors.append({"file": path, "code": "io_error",
                               "message": str(exc)})
                continue
            by_hash.setdefault(digest, []).append(path)
        if not by_hash:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"ни один из {len(paths)} файлов не читается")
        dup_groups = [{"hex": digest, "count": len(group), "files": group}
                      for digest, group in sorted(by_hash.items())
                      if len(group) > 1]
        return {"algo": algo, "total": len(paths), "unique": len(by_hash),
                "num_duplicate_files": sum(g["count"] for g in dup_groups),
                "groups": dup_groups, "errors": errors}

    # ----------------------------------------------------------
    # batch.export — выгрузка метрик пакета (.csv/.json)
    # ----------------------------------------------------------

    @registry.command(
        "batch.export", category="batch",
        description="Выгрузить сводные метрики пакета в файл .csv/.json "
                    "(exportio: строки-системы × колонки-метрики)",
        returns="{out, format, rows, columns, preview, ok, errors: [...]}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("out", required=True,
                  help="путь выгрузки (.csv или .json)"),
            Param("metrics", type="list",
                  help=f"метрики (по умолчанию "
                       f"{list(SUMMARY_METRICS_DEFAULT)})"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
        ])
    def batch_export(ctx, files, out, metrics, num_rays, field_y):
        from commands.exportio import write_rows
        ext = os.path.splitext(str(out))[1].lower()
        if ext not in (".csv", ".json"):
            raise CommandError(
                ERR_UNSUPPORTED,
                f"batch.export выгружает только в .csv/.json (получено "
                f"{ext!r}); текст — batch.report c out=.txt")
        paths = _files_arg(files)
        names = _metrics_arg(metrics, SUMMARY_METRICS_DEFAULT)
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, names, opts)
        table = [{"file": row["file"], "name": row["name"],
                  **{metric: row.get(metric) for metric in names}}
                 for row in rows]
        result = write_rows(table, out)
        result.update({"ok": len(table), "errors": errors})
        return result

    # ----------------------------------------------------------
    # batch.report — текстовый свод по пакету
    # ----------------------------------------------------------

    @registry.command(
        "batch.report", category="batch",
        description="Текстовый свод по пакету: таблица метрик по системам "
                    "+ итоги min/max/mean (опция записи .txt)",
        returns="{text, count, ok, errors: [...], out?}",
        params=[
            Param("files", type="list", required=True,
                  help="список путей (.opj/.json/.lbo)"),
            Param("metrics", type="list",
                  help=f"метрики (по умолчанию "
                       f"{list(SUMMARY_METRICS_DEFAULT)})"),
            Param("num_rays", type="int", help="лучей сетки зрачка"),
            Param("field_y", type="float", help="поле, градусы"),
            Param("out", help="записать отчёт в .txt (exportio)"),
        ])
    def batch_report(ctx, files, metrics, num_rays, field_y, out):
        paths = _files_arg(files)
        names = _metrics_arg(metrics, SUMMARY_METRICS_DEFAULT)
        opts = _metric_opts(num_rays, field_y)
        rows, errors = _metric_rows(paths, names, opts)

        header_cells = ["файл", "имя"] + [
            f"{m} [{_METRICS[m]['unit']}]" for m in names]
        table = [[os.path.basename(row["file"]), row["name"]]
                 + [_fmt_value(row.get(m)) for m in names]
                 for row in rows]
        widths = [max(len(header_cells[i]),
                      *(len(row[i]) for row in table))
                  for i in range(len(header_cells))] if table else \
                 [len(h) for h in header_cells]

        def _line(cells) -> str:
            return REPORT_COL_GAP.join(cell.ljust(widths[i])
                                       for i, cell in enumerate(cells))

        lines = ["Пакетный отчёт OPAL-OKB",
                 f"Файлов: {len(paths)}, загружено: {len(rows)}, "
                 f"ошибок: {len(errors)}",
                 "" if rows else "нет загруженных систем", _line(header_cells)]
        for row in table:
            lines.append(_line(row))
        lines.append("")
        lines.append("Итоги:")
        for metric in names:
            pairs = _numeric_pairs(rows, metric)
            if not pairs:
                lines.append(f"  {metric}: не посчитана")
                continue
            values = [v for _r, v in pairs]
            unit = _METRICS[metric]["unit"]
            fmt = REPORT_VALUE_FMT
            mean = fmt.format(sum(values) / len(values))
            lines.append(f"  {metric} [{unit}]: "
                         f"min={fmt.format(min(values))}, "
                         f"mean={mean}, "
                         f"max={fmt.format(max(values))}")
        if errors:
            lines.append("Ошибки загрузки:")
            shown = errors[:BATCH_REPORT_ERROR_LIMIT]
            for error in shown:
                lines.append(f"  {os.path.basename(error['file'])}: "
                             f"{error.get('code')}: "
                             f"{error.get('message')}")
            rest = len(errors) - len(shown)
            if rest > 0:
                lines.append(f"  ... и ещё {rest}")
        text = "\n".join(lines) + "\n"
        result = {"text": text, "count": len(rows), "ok": len(rows),
                  "errors": errors}
        if out:
            from commands.exportio import write_text
            written = write_text(text, out)
            result.update({"out": written["out"],
                           "size_bytes": written["size_bytes"]})
        return result
