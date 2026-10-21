# TASK_COMMANDS_W1.md — Волна 1: Command Registry + CLI + JSON-канал

**Ветка:** `feature/command-registry` (от `feature/native-core`)
**Цель:** единый реестр команд поверх domain/analysis/fileio/catalog — без Qt, headless.
UI НЕ трогаем в этой волне.

## Архитектурные образцы (лучшие практики)
- VS Code Commands (`vscode.commands.registerCommand`): `id → handler`, единый каталог, всё через него.
- Blender Operators: имя домена (`object.transform`), параметры с типами, вызов из UI/CLI/скриптов одинаков.
- FreeCAD Commands: реестр + thin UI-обвязка.

Принцип: **single source of truth** — реестр один, команды регистрируются декоратором, CLI/JSON — тонкие фронтенды над реестром.

## Структура (новый пакет `commands/`)
```
commands/
  __init__.py        # register_all() (идемпотентно), default_registry
  base.py            # Command, CommandResult, CommandError, Param
  registry.py        # Registry: register/get/has/list/search/categories/schema
  cli.py             # argparse CLI: list|info|schema|run  (+ --json)
  jsonrepl.py        # JSONL REPL: stdin {"id","cmd","args"} → stdout {"id","ok","data|error"}
  builtin/
    __init__.py      # регистрирует все модули ниже
    file_cmds.py     # file.*
    system_cmds.py   # system.*
    calc_cmds.py     # calc.*      (domain/calculations.py)
    catalog_cmds.py  # catalog.*   (catalog/)
    analyze_cmds.py  # analyze.*   (analysis/__init__.py, главные точки входа)
```

## Контракты

### base.py
- `CommandError(code, message)` — единственный тип ошибок команд.
- `CommandResult`: `ok: bool`, `data: Any` (JSON-сериализуемое), `error: Optional[dict]`; `to_dict()`.
- `Param`: `name`, `type` (`"str"|"float"|"int"|"bool"|"list"|"dict"`), `required`, `default`, `choices`, `help`.
- `Command`: `name`, `category`, `description`, `params: list[Param]`, `returns: str` (описание результата), `handler: Callable[..., Any]`.
- Константы типов параметров — в base.py, не разбросаны строками.

### registry.py
- `Registry`: `register(cmd)` (+ декоратор `@command(name, category, ...)`), `get(name)`, `has(name)`, `names()`, `list(category=None)`, `search(query)`, `categories()`, `schema(name)`, `schema_all()`.
- `default_registry` — модуль-уровень; `reset_registry()` для тестов.
- Имена валидируются: `^[a-z0-9_]+(\.[a-z0-9_]+)+$` (минимум 2 сегмента).

### cli.py
Запуск: `py -m commands <subcommand>`:
- `list [--category X] [--json]` — имена+описания
- `info <cmd>` — полное описание, параметры
- `schema [--json]` — схема всех команд
- `run <cmd> [--param key=value ...] [--json]` — выполнить
Парсинг значений: float/int/bool/list[...] по schema типа параметра. Ошибки — nonzero exit + JSON в stderr при --json. argparse — единый builder-модуль, без дублирования.

### jsonrepl.py
- `py -m commands repl` (или `py -m commands.jsonrepl`): читает JSONL со stdin, пишет JSONL в stdout.
- Запрос: `{"id": 1, "cmd": "calc.paraxial", "args": {...}}` → ответ: `{"id": 1, "ok": true, "data": {...}}` или `{"id": 1, "ok": false, "error": {"code": "...", "message": "..."}}`.
- Одна команда — одна строка, flush после каждой. Ctrl+D/EOF → выход 0.

## Команды Волны 1 (~30 шт)

**file.*** (fileio/): `file.open` (opj/lbo/json по расширению → сериализованная система), `file.save`, `file.info` (формат, число поверхностей, стёкла), `file.convert` (opj→json и обратно), `file.formats`.
**system.*** (domain/models.py): `system.new` (пустая/демо), `system.info`, `system.surfaces.list`, `system.surface.add`, `system.surface.set`, `system.surface.remove`, `system.fields.list/add`, `system.wavelengths.list/add`.
Системы между вызовами в CLI не живут (stateless): команды принимают путь к файлу или JSON-описание системы. Исключение — REPL: там держим `state.system` (команды `system.load`, `system.current`) — реализовать через опциональный context-объект в handler(ctx, **args), CLI передаёт fresh ctx, REPL — персистентный.
**calc.*** (domain/calculations.py): `calc.paraxial`, `calc.paraxial.multi_wl`, `calc.aperture.real`, `calc.beam_geometry`, `calc.seidel`.
**catalog.*** (catalog/): `catalog.info`, `catalog.glass.get`, `catalog.glass.search`, `catalog.library.list`.
**analyze.*** (analysis/): обернуть ГЛАВНЫЕ точки входа, которые уже покрыты тестами и не требуют Qt: ray fan / aberrations / psf_mtf / tables — посмотреть фактические сигнатуры в analysis/__init__.py и обернуть 4–6 функций.

Точные сигнатуры смотреть в коде. Если функция принимает OpticalSystem — команда принимает путь к файлу или имя загруженной в ctx системы и строит её через существующие fileio.

## Жёсткие правила
1. НИКАКОГО Qt/import GUI в commands/ (проверить: `py -c "import commands"` без QApplication).
2. Не менять domain/analysis/fileio/catalog — только обёртки. Если чего-то не хватает — адаптер внутри commands/.
3. Никаких дублей: парсинг значений, сериализация системы, загрузка по расширению — по одному хелперу в одном месте.
4. Production grade: type hints, docstrings, константы вместо магических строк.
5. Regression-тесты обязательны: tests/test_commands_base.py (реестр, валидация имён, ошибки), tests/test_commands_cli.py (list/info/run через subprocess), tests/test_commands_repl.py, tests/test_commands_builtin.py — smoke КАЖДОЙ команды (demo-данные из tests/ или сгенерированные system.new+save).
6. Полный прогон: `py -m pytest -x -q` — существующие 1161+ тестов зелёные + новые.
7. CHANGELOG.md — запись. README трогать не надо (этап ещё не закрыт).
8. Коммит(ы) осмысленные в новой ветке feature/command-registry. НЕ пушить.

## Критерий готовности
- `py -m commands list --json` → валидный JSON со всеми командами Волны 1.
- `py -m commands run calc.paraxial --param file=tests/... .opj --json` → числа параксиального расчёта.
- REPL-скрипт на Python: load → calc → результат совпадает с вызовом через CLI.
- Все тесты зелёные.
