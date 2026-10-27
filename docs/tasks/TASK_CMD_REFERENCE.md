# TASK_CMD_REFERENCE — Справочник 506 команд: автоген docs/reference

**Проект:** OPAL-OKB (реимплантация оптического САПР OPAL-PC). Ты в изолированной копии, ветка `feature/cmd-reference` (уже создана и активна, база — свежий main `de883be`).

**Контекст:** реестр — **506 команд в 40 категориях** (после r500). У каждой команды есть машина-читаемая схема (описание, параметры: имя/тип/обязательность/умолчание/choices, returns) — это источник истины (`commands/registry.py`, `help.command`). Человеческого справочника НЕТ — README упоминает только счётчик. Прецеденты экспорта: команда реестра `registry.export` (JSON-снимок всего реестра) и `export.command` (одна команда → файл).

**Цель:** `docs/reference/` — автогенерируемый справочник: `COMMANDS_INDEX.md` (оглавление по категориям, счётчики, якоря) + `commands-<category>.md` на каждую категорию (таблица: команда, описание, параметры, returns) + `registry_snapshot.json` (машино-читаемый дубль для агентов). Генератор — `scripts/gen_command_reference.py` (headless, без Qt), режим `--check` (регенерация бит-в-бит; CI-guard).

## План (пакетами, атомарные коммиты)

1. **A. Генератор-каркас**: `scripts/gen_command_reference.py` — импорт реестра (как это делают тесты `tests/test_commands_builtin.py`), шаблон страницы категории, stable-сортировка (детерминизм!). Коммит.
2. **B. Индекс + категории**: `COMMANDS_INDEX.md` + 40 файлов `commands-*.md` — сгенерированы, закоммичены. Формат: таблица команд + секция параметров с умолчаниями; длинные описания — без обрезки. Коммит.
3. **C. Snapshot + инварианты**: `registry_snapshot.json`; тест `tests/test_cmd_reference.py`: (1) счётчик команд в справочнике == счётчику реестра; (2) `--check` чист (регенерация идемпотентна); (3) каждая категория реестра имеет файл; (4) markdown-заголовки/якоря валидны. Коммит.
4. **D. Интеграция**: строка в README (ссылка на docs/reference/COMMANDS_INDEX.md); `docs/tasks/CMD_REF_REPORT.md` — формат, решения, пример страницы. Коммит.
5. **E. Финал**: полный `py -m pytest -q` зелёный; CHANGELOG `[1.34.0]`; генерация одной командой воспроизводима. Коммит.

## Жёсткие запреты

- **`commands/` — только ЧТЕНИЕ** (реестр закрыт; генератор импортирует, не правит).
- **НЕ трогать (параллельные агенты):** `gui/`, `main.py`, `visualization3d.py`, `tests/test_gui_*`, `tests/test_*3d*` (3D-агент); `scripts/corpus_*`, `tests/test_corpus*`, `docs/reports/`, `docs/tasks/CORPUS*`, `docs/tasks/TASK_CORPUS_V3.md`, `docs/tasks/G2W3_*`, `bank/`, `analysis/`, `tests/test_golden_*` (два других агента).
- Не `git push`. Коммиты только в `feature/cmd-reference`.
- Рабочая зона: `scripts/gen_command_reference.py` (НОВЫЙ файл), `docs/reference/`, `tests/test_cmd_reference.py`, README (строка), CHANGELOG.

## Окружение

- `py` вместо python; headless (без PyQt — если импорт реестра тянет Qt, изолируй импорт по образцу существующих тестов).
- Полный pytest ~6 мин после пакета C. Потерял нить → перечитай ТЗ и CMD_REF_REPORT.md.

## Критерии готовности

- `py scripts/gen_command_reference.py` регенерирует всё дерево бит-в-бит (`--check` exit 0).
- Справочник полный: 506/506 команд, 40/40 категорий, машинный snapshot.
- Тесты-инварианты зелёные; полный pytest зелёный; README/CHANGELOG обновлены.
