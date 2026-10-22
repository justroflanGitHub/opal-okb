# TASK_COMMANDS_W5.md — Волна 5: MCP-сервер поверх реестра команд

**База:** ветка `feature/command-registry` (140 команд, мост UI, 1511 тестов).
**Цель:** OPAL-OKB как MCP-сервер (Model Context Protocol) over stdio — чтобы ИИ-агенты (OpenClaw, Claude и др.) могли выполнять команды реестра как tools.

## Архитектура
MCP = JSON-RPC 2.0 по stdin/stdout (строка = JSON-объект). Реализовать на чистой stdlib (json, sys) — БЕЗ новых зависимостей (pip недоступен офлайн). Сервер — тонкий слой над `default_registry` (никакой бизнес-логики).

## Что сделать

### 1. `commands/mcp.py` — сервер
- Точка входа через CLI: `py -m commands mcp` (добавить subcommand в существующий `commands/cli.py`, не дублируя builder).
- Цикл: читать JSONL со stdin, писать JSONL в stdout (flush после каждого ответа). Логи/ошибки — ТОЛЬКО в stderr (stdout зарезервирован протоколом).
- Методы:
  - `initialize` → ответ: protocolVersion (последняя известная, например "2025-06-18"), capabilities: {tools: {}}, serverInfo: {name: "opal-okb", version: из пакета/константы}.
  - `notifications/initialized` — уведомление, ответа нет.
  - `ping` → {}.
  - `tools/list` → все команды реестра: {name, description, inputSchema}.
  - `tools/call` (params: {name, arguments}) → {content: [{type: "text", text: JSON-результат}], isError: false} или isError: true с текстом ошибки.
  - Неизвестный метод → JSON-RPC error -32601 Method not found.
- **Имена tools:** MCP-клиенты валидируют имена `[a-zA-Z0-9_-]` — точки запрещены. Маппинг: `calc.paraxial` → `calc_paraxial` (замена '.' на '_'), в description первым словом каноническое имя `calc.paraxial`. В tools/call обратный маппинг. Коллизии проверить тестом (после замены имена уникальны).
- **inputSchema** из Param (JSON Schema): type mapping `str→string, float→number, int→integer, bool→boolean, list→array, dict→object`; required-массив; default; enum из choices; description из help. Константы маппинга — в одном месте.
- **Контекст сессии:** один персистентный `CommandContext` на процесс сервера (как у REPL): `system.load` кладёт систему, дальнейшие команды через `system=` не требуют. Параметр `__ctx__`/system-параметры работают как в REPL.
- Ограничение вывода: если data > N байт (константа, например 20000), возвращать усечённо с пометкой `"truncated": true` и подсказкой (сохранить в файл / запросить меньший срез) — чтобы не раздувать контекст агента.

### 2. Тесты `tests/test_commands_mcp.py`
- initialize handshake (protocolVersion, capabilities).
- tools/list: все 140 команд, имена валидны `^[A-Za-z0-9_-]+$`, уникальны, inputSchema — валидный JSON Schema (required/типы).
- tools/call smoke: system.new → calc.paraxial через stateful-контекст; ошибочная команда → isError true; unknown tool → код ошибки.
- unknown method → -32601.
- Смоук через subprocess: запустить `py -m commands mcp`, скормить initialize + initialized + tools/list + tools/call по stdin, разобрать stdout.

### 3. Докуменация
- README.md (и README_RU.md): короткий раздел про MCP — как подключить (command: py, args: [-m, commands, mcp], cwd: путь к opal_okb), что умеет.
- CHANGELOG.md: запись 1.28.0.

## Правила
- Не менять контракты команд/реестра/моста. Никакого Qt.
- Никаких дублей: JSON-RPC обвязка (чтение/запись/ошибка) — одна пара функций.
- Полный прогон `py -m pytest -q` зелёный (база 1511 passed, 8 skipped).
- Коммиты в feature/command-registry. Не пушить.
- В конце отчёт: сколько tools, как проверено.

## Критерий готовности
- `echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | py -m commands mcp` (после initialize) отдаёт список всех команд валидного MCP-формата.
- tests/test_commands_mcp.py зелёный, полный прогон зелёный.
