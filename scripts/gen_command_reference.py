# -*- coding: utf-8 -*-
"""Генератор справочника команд OPAL-OKB (docs/reference/).

Headless-скрипт (без Qt): источник истины — реестр команд
``commands.default_registry`` (``import commands`` автоматически
регистрирует все builtin-команды). Собирает и пишет ровно 42 файла:

1. ``COMMANDS_INDEX.md`` — оглавление по категориям со счётчиками;
2. ``commands-<category>.md`` — страница на каждую категорию
   (таблица команд + раздел «Параметры и результаты»);
3. ``registry_snapshot.json`` — машиночитаемый снимок реестра.

CLI:
    py scripts/gen_command_reference.py [--out DIR] [--check] [--json]

Без опций — генерация всего дерева в ``docs/reference`` (путь
резолвится от корня репозитория, не от cwd). ``--out DIR`` —
альтернативный каталог вывода. ``--check`` — НЕ писать файлы:
сгенерировать всё в память и побайтово сравнить с целевым каталогом.
``--json`` — краткий итог в stdout в формате JSON.

Детерминизм (регенерация бит-в-бит, CI-guard ``--check``):
сортировки явные и stable (категории/команды — sorted, параметры —
в порядке объявления схемы), в выводе нет временных меток и версий,
файлы пишутся в UTF-8 с принудительным ``\\n``.

Коды возврата: 0 — генерация выполнена или ``--check`` чист;
1 — ``--check`` нашёл расхождения; 2 — ошибка аргументов CLI.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Консоль Windows (cp1251): русский вывод без падений
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

# Корень проекта (родитель scripts/) — импорт реестра из любого cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import commands  # noqa: E402  (импорт пакета регистрирует builtin-команды)

#: Имя файла оглавления
INDEX_NAME = "COMMANDS_INDEX.md"
#: Имя файла машиночитаемого снимка
SNAPSHOT_NAME = "registry_snapshot.json"
#: Подпись генератора в snapshot (стабильная, без путей и меток времени)
GENERATOR_LABEL = "scripts/gen_command_reference.py"
#: Прочерк для пустых ячеек таблиц
DASH = "—"


# ============================================================
# Форматирование: экранирование, слаги, русские формы
# ============================================================

def _slug(text: str) -> str:
    """Якорь в стиле GitHub: lowercase; удалить символы, не являющиеся
    unicode-буквами/цифрами/пробелом/дефисом/подчёркиванием; пробелы
    → дефисы. Примеры: ``calc.paraxial`` → ``calcparaxial``,
    ``Категория aber`` → ``категория-aber``."""
    kept = [ch for ch in text.lower()
            if ch.isalnum() or ch in (" ", "-", "_")]
    return "".join(kept).replace(" ", "-")


def _cell(text: str) -> str:
    """Экранировать текст для ячейки markdown-таблицы: переводы строк
    → пробел, ``|`` → ``\\|`` (иначе таблица разъедется)."""
    return (text or "").replace("\r", " ").replace("\n", " ").replace(
        "|", "\\|")


def _code(text: str) -> str:
    """Завернуть текст в inline-code с экранированием ячейки."""
    return "`" + _cell(text) + "`"


def _json_inline(value) -> str:
    """Значение умолчания/choices одной строкой (детерминированно)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _plural_commands(n: int) -> str:
    """«N команда/команды/команд.» — русская форма множественного числа."""
    if n % 10 == 1 and n % 100 != 11:
        word = "команда"
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = "команды"
    else:
        word = "команд"
    return f"{n} {word}."


# ============================================================
# Рендер страниц
# ============================================================

def _render_category(cat: str, schemas: list) -> str:
    """Страница одной категории: таблица команд + секции параметров.

    ``schemas`` — схемы команд (``registry.schema(name)``), уже
    отсортированные по имени. Инвариант: h3 в файле используется
    ТОЛЬКО для команд (на этом строится тест подсчёта секций).
    """
    lines = [
        f"# Категория {cat}",
        "",
        _plural_commands(len(schemas)),
        "",
        "| Команда | Описание | Параметры | Returns |",
        "| --- | --- | --- | --- |",
    ]
    for sch in schemas:
        anchor = _slug(sch["name"])
        params = (", ".join(_code(p["name"]) for p in sch["params"])
                  if sch["params"] else DASH)
        returns = _cell(sch["returns"]) or DASH
        lines.append(
            f"| [`{sch['name']}`](#{anchor}) "
            f"| {_cell(sch['description'])} "
            f"| {params} | {returns} |")
    lines += ["", "## Параметры и результаты", ""]
    for sch in schemas:
        lines += [
            f"### {sch['name']}",
            "",
            _cell(sch["description"]),
            "",
            f"**Returns:** {_cell(sch['returns']) or DASH}",
        ]
        if sch["params"]:
            lines += [
                "",
                "| Имя | Тип | Обяз. | Умолчание | Choices | Описание |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for p in sch["params"]:
                lines.append(
                    f"| {_code(p['name'])} | {_code(p['type'])} "
                    f"| {'да' if p['required'] else DASH} "
                    f"| {_code(_json_inline(p['default']))} "
                    f"| {_fmt_choices(p)} "
                    f"| {_cell(p['help'])} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def _fmt_choices(param: dict) -> str:
    """Choices параметра ячейкой таблицы: JSON-массив или прочерк."""
    choices = param.get("choices")
    if choices is None:
        return DASH
    return _code(_json_inline(list(choices)))


def _render_index(categories: list, counts: dict, total: int) -> str:
    """Оглавление: шапка-автоген, счётчики, таблица категорий."""
    lines = [
        "# Справочник команд OPAL-OKB",
        "",
        "Автогенерируется из реестра команд (commands/registry.py) "
        "скриптом scripts/gen_command_reference.py — не редактировать "
        "вручную; регенерация: `py scripts/gen_command_reference.py`, "
        "проверка целостности: `py scripts/gen_command_reference.py "
        "--check`.",
        "",
        f"- Команд: {total}",
        f"- Категорий: {len(categories)}",
        "",
        "| Категория | Команд | Файл |",
        "| --- | --- | --- |",
    ]
    for cat in categories:
        fname = f"commands-{cat}.md"
        anchor = _slug(f"Категория {cat}")
        lines.append(
            f"| {cat} | {counts[cat]} | [{fname}]({fname}#{anchor}) |")
    return "\n".join(lines) + "\n"


def _render_snapshot(categories: list, counts: dict, names: list,
                     registry) -> str:
    """Машиночитаемый снимок реестра (JSON, sort_keys, без меток времени)."""
    doc = {
        "meta": {
            "generator": GENERATOR_LABEL,
            "command_count": len(names),
            "category_count": len(categories),
            "categories": counts,
        },
        "commands": [registry.schema(name) for name in names],
    }
    return json.dumps(doc, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"


def build_pages(registry) -> dict:
    """Собрать справочник целиком в память: ``{имя файла: текст}``.

    Ровно 42 файла: 1 индекс + страница на каждую категорию +
    registry_snapshot.json. Сортировки явные: категории и команды —
    sorted, параметры — в порядке объявления схемы.
    """
    categories = sorted(registry.categories())
    names = sorted(registry.names())
    counts = {cat: len(registry.list(cat)) for cat in categories}
    pages = {}
    for cat in categories:
        schemas = sorted(
            (cmd.schema() for cmd in registry.list(cat)),
            key=lambda s: s["name"])
        pages[f"commands-{cat}.md"] = _render_category(cat, schemas)
    pages[INDEX_NAME] = _render_index(categories, counts, len(names))
    pages[SNAPSHOT_NAME] = _render_snapshot(categories, counts, names,
                                            registry)
    return pages


# ============================================================
# Запись и проверка
# ============================================================

def write_pages(target: Path, pages: dict) -> None:
    """Записать страницы в UTF-8 с принудительным ``\\n`` (без CRLF)."""
    target.mkdir(parents=True, exist_ok=True)
    for name in sorted(pages):
        with open(target / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(pages[name])


def check_pages(target: Path, pages: dict) -> list:
    """Побайтово сравнить страницы с целевым каталогом.

    Returns:
        Список расхождений (пустой = идентично): отсутствующие,
        лишние и изменённые файлы.
    """
    diffs = []
    if not target.is_dir():
        return [f"ОТСУТСТВУЕТ КАТАЛОГ: {target} "
                f"(ожидалось файлов: {len(pages)})"]
    actual = sorted(p.name for p in target.iterdir() if p.is_file())
    expected = sorted(pages)
    for name in expected:
        if name not in actual:
            diffs.append(f"ОТСУТСТВУЕТ: {name}")
        elif (target / name).read_bytes() != pages[name].encode("utf-8"):
            diffs.append(f"ИЗМЕНЁН: {name}")
    for name in actual:
        if name not in expected:
            diffs.append(f"ЛИШНИЙ: {name}")
    return diffs


# ============================================================
# CLI
# ============================================================

def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Генератор справочника команд OPAL-OKB "
                    "(docs/reference/) из реестра commands.")
    parser.add_argument(
        "--out", metavar="DIR",
        help="каталог вывода (по умолчанию docs/reference от корня репо)")
    parser.add_argument(
        "--check", action="store_true",
        help="не писать файлы: побайтово сравнить генерацию с каталогом; "
             "exit 1 при расхождениях")
    parser.add_argument(
        "--json", action="store_true",
        help="краткий итог в stdout в формате JSON (counts)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    registry = commands.default_registry
    categories = sorted(registry.categories())
    names = sorted(registry.names())
    pages = build_pages(registry)

    root = Path(__file__).resolve().parents[1]
    target = (Path(args.out) if args.out
              else root / "docs" / "reference")

    if args.check:
        diffs = check_pages(target, pages)
        if args.json:
            print(json.dumps({
                "commands": len(names),
                "categories": len(categories),
                "files_expected": len(pages),
                "check": "ok" if not diffs else "fail",
                "missing": sum(d.startswith("ОТСУТСТВУЕТ") for d in diffs),
                "extra": sum(d.startswith("ЛИШНИЙ") for d in diffs),
                "changed": sum(d.startswith("ИЗМЕНЁН") for d in diffs),
            }, ensure_ascii=False))
        if diffs:
            print(f"--check: расхождений {len(diffs)}:", file=sys.stderr)
            for d in diffs:
                print(f"  {d}", file=sys.stderr)
            return 1
        print(f"--check: OK — {len(pages)} файлов идентичны "
              f"({target})", file=sys.stderr)
        return 0

    write_pages(target, pages)
    if args.json:
        print(json.dumps({
            "commands": len(names),
            "categories": len(categories),
            "files_written": len(pages),
            "out": str(target),
        }, ensure_ascii=False))
    else:
        print(f"Справочник команд: {len(names)} команд, "
              f"{len(categories)} категорий → {len(pages)} файлов "
              f"в {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
