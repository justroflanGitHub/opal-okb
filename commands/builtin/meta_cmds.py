"""
OPAL-OKB — Пакет R500-13: интроспекция реестра и окружения (meta).

ЕДИНАЯ ТОЧКА САМОПОЗНАНИЯ РЕЕСТРА ДЛЯ АГЕНТОВ: категории, поиск, схемы
команд и снимок реестра целиком — без чтения исходников. CLI
(``py -m commands list/schema``) остаётся тонким фронтендом; команды
ниже — тот же каталог изнутри реестра (для MCP/REPL/композиции).

ВАЖНО: каждая команда работает с тем реестром, в котором
зарегистрирована (замыкание ``registry`` из :func:`register`), а не с
``default_registry`` — тесты с изолированными реестрами видят свой
набор команд.

- ``registry.stats``        — всего команд / категорий, счётчик по
  категориям;
- ``registry.categories``   — список категорий с числом команд и
  описанием;
- ``registry.list``         — перечень команд по категории/префиксу,
  с описаниями;
- ``registry.search``       — поиск по подстроке (имя/описание/
  категория, без регистра);
- ``registry.schema``       — параметры конкретной команды:
  имена/типы/обязательность/умолчания/описание + returns;
- ``registry.category.info``— команды одной категории с сигнатурами;
- ``registry.params``       — какие команды принимают параметр X
  (опционально фильтр по типу);
- ``registry.export``       — снимок реестра целиком в JSON (для
  агентов; опция ``out``, запись через exportio);
- ``app.info``              — версия проекта (CHANGELOG.md — верхний
  релиз), Python, платформа, счётчики реестра;
- ``app.env``               — окружение: Python, ОС, доступность
  numpy/matplotlib, кодировка stdout;
- ``app.paths``             — каталоги данных: LBO/OPJ/Lib из констант
  catalog.library (BASE_DIR/OPJ_DIR/LBO_DIR);
- ``help.command``          — человеческая справка по команде:
  описание + параметры + пример вызова CLI.

Никаких магических строк версий/путей: всё берётся из фактических
источников в рантайме (реестр-замыкание, CHANGELOG.md, sys/platform,
catalog.library).
"""
import json
import os
import platform as _platform
import re
import sys

from commands.base import (
    ERR_INVALID_PARAM,
    ERR_NOT_FOUND,
    PARAM_TYPES,
    CommandError,
    Param,
)
from commands.exportio import write_data
from commands.registry import Registry

#: Имя проекта (как в docstring-шапках модулей и README).
PROJECT_NAME = "OPAL-OKB"

#: Файл журнала версий в корне репозитория — единственный источник
#: версии проекта (pyproject/версионного модуля в репо нет).
CHANGELOG_NAME = "CHANGELOG.md"

#: Корень проекта: commands/builtin/meta_cmds.py → три уровня вверх.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

#: Шаблон заголовка релиза в CHANGELOG (``## [1.29.0] — дата``);
#: секции unreleased цифр в скобках не содержат и не совпадают.
_RELEASE_RE = re.compile(r"^##\s*\[(\d+(?:\.\d+)+)\]")

#: Пакеты, доступность которых проверяет app.env (numpy — расчёты,
#: matplotlib — графики plot.*).
ENV_PACKAGES = ("numpy", "matplotlib")

#: Человекочитаемые описания категорий реестра (единственный источник;
#: для категорий, которых нет в карте — null, честно).
CATEGORY_DESCRIPTIONS = {
    "file": "открытие/сохранение/конвертация файлов систем (OPJ/LBO/JSON)",
    "system": "структура оптической системы: поверхности, поля, λ, контекст",
    "calc": "параксиальные характеристики и расчётные формулы",
    "catalog": "каталог стёкол и библиотека систем",
    "analyze": "базовый анализ: веера, пятна, ФРТ, таблицы",
    "trace": "трассировка лучей (пучки, сетки, главные лучи)",
    "aber": "аберрации: веера, суммы, таблицы остаточных аберраций",
    "psf": "функция рассеяния точки и дифракционные расчёты",
    "adv": "продвинутый анализ (ФРЛ, ФКЭ, свёртки)",
    "opt": "оптимизация и headless-графики (PNG, Agg)",
    "export": "выгрузка таблиц и данных (CSV/JSON/TXT)",
    "lbo": "LBO-библиотеки: чтение записей и метаданных",
    "library": "библиотека систем: категории, поиск, пакетные прогоны",
    "units": "единицы и координатные преобразования",
    "spatial": "пространственные преобразования (матрицы, наклоны)",
    "sweep": "развёртки по полям/λ/дефокусу/зонам поверх движков",
    "seidel": "суммы Зейделя 3-го порядка",
    "seidel3": "производные величины из сумм Зейделя",
    "tol": "допуски: чувствительность и Monte-Carlo",
    "quality": "сводные метрики качества изображения",
    "report": "текстовые отчёты для печати",
    "plot": "headless-графики (PNG, matplotlib Agg)",
    "tables": "таблицы-выгрузки порта OPAL",
    "chrom": "хроматизм (OPAL-режим TABAX3)",
    "diagram": "диаграммы по данным каталога",
    "vign": "виньетирование и апертурные характеристики",
    "beam": "световые высоты пучков",
    "mtf": "частотно-контрастная характеристика",
    "diffr": "дифракционная ЧКХ",
    "strehl": "число Штреля",
    "focus": "фокусировка: критерии и положение плоскости",
    "zern": "разложение волнового фронта по Цернике",
    "spectral": "справочник спектральных линий",
    "panel": "команды панели анализа",
    "registry": "интроспекция реестра команд (этот модуль)",
    "app": "сведения о приложении и окружении",
    "help": "справка по командам",
}

#: Заглушки значений параметров в примере вызова help.command (по типу).
_EXAMPLE_VALUES = {
    "str": "abc",
    "float": "1.0",
    "int": "1",
    "bool": "true",
    "list": "[1,2]",
    "dict": '{"k": 1}',
}


# ============================================================
# Хелперы
# ============================================================

def _project_version() -> dict:
    """Версия проекта из CHANGELOG.md (верхний релиз).

    Returns:
        ``{"version", "source"}``; при недоступном файле —
        ``version=None``, источник всё равно указываем.
    """
    path = os.path.join(PROJECT_ROOT, CHANGELOG_NAME)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                match = _RELEASE_RE.match(line)
                if match:
                    return {"version": match.group(1),
                            "source": CHANGELOG_NAME}
    except OSError:
        pass
    return {"version": None, "source": CHANGELOG_NAME}


def _category_counts(registry: Registry) -> "dict[str, int]":
    """Счётчик команд по категориям (отсортированный dict)."""
    counts: dict = {}
    for name in registry.names():
        category = registry.get(name).category
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _common_prefix_len(a: str, b: str) -> int:
    """Длина общего префикса двух строк."""
    length = min(len(a), len(b))
    index = 0
    while index < length and a[index] == b[index]:
        index += 1
    return index


def _require_command(registry: Registry, name: str):
    """Команда по имени; ``not_found`` с подсказкой ближайших имён.

    Подсказка — до PREFIX_HINT_MAX команд той же категории,
    ранжированных по длине общего префикса с запрошенным именем
    (опечатка в последнем сегменте даёт нужную команду первой).
    """
    if registry.has(name):
        return registry.get(name)
    segment = name.split(".")[0] + "."
    siblings = [n for n in registry.names() if n.startswith(segment)]
    siblings.sort(key=lambda n: (-_common_prefix_len(name, n), n))
    hint = (f"; близкие: {siblings[:PREFIX_HINT_MAX]}"
            if siblings else "")
    raise CommandError(
        ERR_NOT_FOUND,
        f"команда {name!r} не найдена в реестре{hint}; "
        f"см. registry.search / registry.list")


def _require_category(registry: Registry, category: str) -> list:
    """Команды категории; ``not_found`` со списком доступных категорий."""
    cmds = registry.list(category)
    if not cmds:
        raise CommandError(
            ERR_NOT_FOUND,
            f"категория {category!r} не найдена; доступны: "
            f"{registry.categories()}")
    return cmds


def _signature(cmd) -> str:
    """Сигнатура обработки: ``name(p1: float = 1.0, p2: str)``."""
    parts = []
    for p in cmd.params:
        chunk = f"{p.name}: {p.type}"
        if not p.required and p.default is not None:
            chunk += f" = {p.default!r}"
        parts.append(chunk)
    return f"{cmd.name}({', '.join(parts)})"


def _example_value(p: Param) -> str:
    """Значение параметра для примера вызова: умолчание или заглушка
    по типу (для choices — первое допустимое значение)."""
    if p.choices:
        return str(p.choices[0])
    if p.default is not None:
        if isinstance(p.default, (dict, list)):
            return json.dumps(p.default, ensure_ascii=False)
        return str(p.default)
    return _EXAMPLE_VALUES.get(p.type, "value")


#: Максимум команд в подсказке «близкие имена».
PREFIX_HINT_MAX = 5


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать команды интроспекции (R500-13)."""

    # ----------------------------------------------------------
    # registry.stats — счётчики реестра
    # ----------------------------------------------------------

    @registry.command(
        "registry.stats", category="registry",
        description="Статистика реестра: всего команд, число категорий, "
                    "счётчик команд по каждой категории",
        returns="{total, num_categories, categories: {имя: число}}",
    )
    def registry_stats(ctx):
        counts = _category_counts(registry)
        return {"total": sum(counts.values()),
                "num_categories": len(counts),
                "categories": counts}

    # ----------------------------------------------------------
    # registry.categories — категории с описаниями
    # ----------------------------------------------------------

    @registry.command(
        "registry.categories", category="registry",
        description="Категории реестра с числом команд и описанием "
                    "(описание — карта модуля, для неизвестных категорий "
                    "null)",
        returns="{count, categories: [{name, commands, description}]}",
    )
    def registry_categories(ctx):
        counts = _category_counts(registry)
        return {"count": len(counts),
                "categories": [
                    {"name": name, "commands": count,
                     "description": CATEGORY_DESCRIPTIONS.get(name)}
                    for name, count in counts.items()]}

    # ----------------------------------------------------------
    # registry.list — перечень команд по категории/префиксу
    # ----------------------------------------------------------

    @registry.command(
        "registry.list", category="registry",
        description="Перечень команд реестра (по имени, с категорией и "
                    "описанием); фильтры — одна категория и/или префикс "
                    "имени, без фильтров — все команды",
        returns="{total, shown, rows: [{name, category, description}]}",
        params=[
            Param("category",
                  help="категория (например 'calc'; см. "
                       "registry.categories)"),
            Param("prefix", help="префикс имени (например 'file.lbo.')"),
        ])
    def registry_list(ctx, category, prefix):
        cmds = _require_category(registry, category) if category \
            else registry.list()
        if prefix:
            cmds = [c for c in cmds if c.name.startswith(prefix)]
        return {"total": len(registry.names()), "shown": len(cmds),
                "rows": [{"name": c.name, "category": c.category,
                          "description": c.description} for c in cmds]}

    # ----------------------------------------------------------
    # registry.search — поиск по подстроке
    # ----------------------------------------------------------

    @registry.command(
        "registry.search", category="registry",
        description="Поиск команд по подстроке без регистра: имя, "
                    "описание или категория; в каждой находке — где "
                    "совпало",
        returns="{query, total, shown, rows: [{name, category, "
                "description, matched_in}]}",
        params=[
            Param("query", required=True,
                  help="подстрока поиска (непустая)"),
            Param("limit", type="int",
                  help="максимум находок в ответе (по умолчанию — все)"),
        ])
    def registry_search(ctx, query, limit):
        q = (query or "").strip().lower()
        if not q:
            raise CommandError(ERR_INVALID_PARAM,
                               "query должен быть непустой строкой")
        rows = []
        for cmd in registry.list():
            matched = [field for field, value in (
                ("name", cmd.name),
                ("category", cmd.category),
                ("description", cmd.description)) if q in value.lower()]
            if matched:
                rows.append({"name": cmd.name,
                             "category": cmd.category,
                             "description": cmd.description,
                             "matched_in": matched})
        shown = rows[:limit] if limit is not None else rows
        return {"query": query, "total": len(rows), "shown": len(shown),
                "rows": shown}

    # ----------------------------------------------------------
    # registry.schema — параметры конкретной команды
    # ----------------------------------------------------------

    @registry.command(
        "registry.schema", category="registry",
        description="Схема команды: имя, категория, описание, параметры "
                    "(имя/тип/обязательность/умолчание/choices/подсказка) "
                    "и описание результата",
        returns="{name, category, description, params: [{name, type, "
                "required, default, choices, help}], returns}",
        params=[
            Param("name", required=True,
                  help="имя команды (например 'calc.paraxial')"),
        ])
    def registry_schema(ctx, name):
        return _require_command(registry, name).schema()

    # ----------------------------------------------------------
    # registry.category.info — команды категории с сигнатурами
    # ----------------------------------------------------------

    @registry.command(
        "registry.category.info", category="registry",
        description="Команды одной категории: описание, сигнатура "
                    "параметров и returns каждой команды",
        returns="{category, description, count, commands: [{name, "
                "description, signature, params, returns}]}",
        params=[
            Param("category", required=True,
                  help="имя категории (например 'plot')"),
        ])
    def registry_category_info(ctx, category):
        cmds = _require_category(registry, category)
        return {"category": category,
                "description": CATEGORY_DESCRIPTIONS.get(category),
                "count": len(cmds),
                "commands": [
                    {"name": c.name, "description": c.description,
                     "signature": _signature(c),
                     "params": [p.to_dict() for p in c.params],
                     "returns": c.returns} for c in cmds]}

    # ----------------------------------------------------------
    # registry.params — какие команды принимают параметр X
    # ----------------------------------------------------------

    @registry.command(
        "registry.params", category="registry",
        description="Команды, принимающие параметр с данным именем "
                    "(например 'file' или 'num_rays'); опциональный "
                    "фильтр по типу параметра",
        returns="{param, type, count, rows: [{name, category, type, "
                "required, default, help}]}",
        params=[
            Param("param", required=True,
                  help="имя параметра (например 'wl')"),
            Param("type", choices=list(PARAM_TYPES),
                  help="только параметры этого типа (str/float/int/"
                       "bool/list/dict)"),
        ])
    def registry_params(ctx, param, type):
        rows = []
        for cmd in registry.list():
            for p in cmd.params:
                if p.name == param and (type is None or p.type == type):
                    rows.append({"name": cmd.name,
                                 "category": cmd.category,
                                 "type": p.type, "required": p.required,
                                 "default": p.default, "help": p.help})
        return {"param": param, "type": type, "count": len(rows),
                "rows": rows}

    # ----------------------------------------------------------
    # registry.export — снимок реестра в JSON
    # ----------------------------------------------------------

    @registry.command(
        "registry.export", category="registry",
        description="Снимок реестра целиком в JSON-файл (для агентов): "
                    "счётчики, категории и схемы всех команд; запись — "
                    "exportio (.json)",
        returns="{out, format, size_bytes, preview, total, "
                "num_categories}",
        params=[
            Param("out", required=True,
                  help="путь к .json-файлу снимка"),
        ])
    def registry_export(ctx, out):
        counts = _category_counts(registry)
        snapshot = {"project": PROJECT_NAME,
                    "total": sum(counts.values()),
                    "num_categories": len(counts),
                    "categories": counts,
                    "commands": registry.schema_all()}
        result = write_data(snapshot, out)
        result.update({"total": snapshot["total"],
                       "num_categories": snapshot["num_categories"]})
        return result

    # ----------------------------------------------------------
    # app.info — версия проекта, Python, платформа, реестр
    # ----------------------------------------------------------

    @registry.command(
        "app.info", category="app",
        description="Сведения о приложении: имя и версия проекта "
                    "(верхний релиз CHANGELOG.md), Python, платформа, "
                    "счётчики этого реестра",
        returns="{project, version, version_source, python, "
                "platform, registry: {total, num_categories}}",
    )
    def app_info(ctx):
        version = _project_version()
        counts = _category_counts(registry)
        return {"project": PROJECT_NAME, "version": version["version"],
                "version_source": version["source"],
                "python": _platform.python_version(),
                "platform": _platform.platform(),
                "registry": {"total": sum(counts.values()),
                             "num_categories": len(counts)}}

    # ----------------------------------------------------------
    # app.env — окружение исполнения
    # ----------------------------------------------------------

    @registry.command(
        "app.env", category="app",
        description="Окружение исполнения: версия/реализация Python, ОС, "
                    "кодировка stdout, доступность и версии расчётных "
                    "пакетов (numpy, matplotlib)",
        returns="{python, python_implementation, executable, os, "
                "os_release, machine, stdout_encoding, "
                "filesystem_encoding, packages: {имя: {available, "
                "version}}}",
    )
    def app_env(ctx):
        import importlib.metadata
        import importlib.util
        packages = {}
        for package in ENV_PACKAGES:
            available = importlib.util.find_spec(package) is not None
            try:
                version = (importlib.metadata.version(package)
                           if available else None)
            except importlib.metadata.PackageNotFoundError:
                version = None
            packages[package] = {"available": available,
                                 "version": version}
        return {
            "python": _platform.python_version(),
            "python_implementation": _platform.python_implementation(),
            "executable": sys.executable or None,
            "os": _platform.system(),
            "os_release": _platform.release(),
            "machine": _platform.machine(),
            "stdout_encoding": getattr(sys.stdout, "encoding", None),
            "filesystem_encoding": sys.getfilesystemencoding(),
            "packages": packages,
        }

    # ----------------------------------------------------------
    # app.paths — каталоги данных проекта
    # ----------------------------------------------------------

    @registry.command(
        "app.paths", category="app",
        description="Каталоги данных проекта (из констант catalog."
                    "library): корень, OPJ-системы, LBO-библиотеки; "
                    "наличие каталогов и число файлов в них",
        returns="{project_root, base_dir, opj_dir, lbo_dir, "
                "opj_dir_exists, lbo_dir_exists, num_opj_files, "
                "num_lbo_files, cwd}",
    )
    def app_paths(ctx):
        import glob
        from catalog.library import BASE_DIR, LBO_DIR, OPJ_DIR
        opj_files = sorted(
            glob.glob(os.path.join(OPJ_DIR, "*.opj"))
            + glob.glob(os.path.join(OPJ_DIR, "*.OPJ")))
        lbo_files = sorted(
            glob.glob(os.path.join(LBO_DIR, "*.lbo"))
            + glob.glob(os.path.join(LBO_DIR, "*.LBO")))
        return {
            "project_root": PROJECT_ROOT,
            "base_dir": BASE_DIR,
            "opj_dir": OPJ_DIR,
            "lbo_dir": LBO_DIR,
            "opj_dir_exists": os.path.isdir(OPJ_DIR),
            "lbo_dir_exists": os.path.isdir(LBO_DIR),
            "num_opj_files": len(opj_files),
            "num_lbo_files": len(lbo_files),
            "cwd": os.getcwd(),
        }

    # ----------------------------------------------------------
    # help.command — человеческая справка по команде
    # ----------------------------------------------------------

    @registry.command(
        "help.command", category="help",
        description="Справка по команде: описание, параметры с типами и "
                    "умолчаниями, описание результата и пример вызова "
                    "CLI (py -m commands run)",
        returns="{name, category, description, params, returns, "
                "example}",
        params=[
            Param("name", required=True,
                  help="имя команды (например 'system.new')"),
        ])
    def help_command(ctx, name):
        cmd = _require_command(registry, name)
        pairs = [f"--param {p.name}={_example_value(p)}"
                 for p in cmd.params]
        example = "py -m commands run " + cmd.name
        if pairs:
            example += " " + " ".join(pairs)
        return {"name": cmd.name, "category": cmd.category,
                "description": cmd.description,
                "params": [p.to_dict() for p in cmd.params],
                "returns": cmd.returns,
                "example": example}
