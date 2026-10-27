# -*- coding: utf-8 -*-
"""Инварианты автогенерированного справочника команд (docs/reference/).

Источник истины — реестр ``commands.default_registry`` (506 команд в
40 категориях); справочник регенерируется скриптом
``scripts/gen_command_reference.py`` (пакет C ТЗ TASK_CMD_REFERENCE).
Проверяются 4 инварианта:

1. полнота: h3-секции страниц категорий и snapshot покрывают реестр;
2. ``--check`` чист — регенерация бит-в-бит (CI-guard);
3. каждой категории реестра соответствует страница и строка индекса;
4. markdown-заголовки и якоря валидны (слаги в стиле GitHub).

Тесты headless (без Qt), только чтение docs/reference; единственный
subprocess — ``--check`` (сам ничего не пишет).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import commands  # импорт пакета регистрирует все builtin-команды

REPO = Path(__file__).resolve().parents[1]
REF = REPO / "docs" / "reference"
SCRIPT = REPO / "scripts" / "gen_command_reference.py"

#: Слаг заголовка в стиле GitHub: удалить символы, не являющиеся
#: unicode-буквой/цифрой/пробелом/дефисом/подчёркиванием.
_NOT_SLUG = re.compile(r"[^\w\-\s]", re.UNICODE)


def _slug(text: str) -> str:
    """Слаг заголовка в стиле GitHub — реализован НЕЗАВИСИМО от
    генератора: тест должен ловить рассинхрон алгоритмов. Алгоритм:
    lower(); удалить символы кроме unicode-букв/цифр/пробела/дефиса/
    подчёркивания; пробелы → дефисы. Пример: ``Категория aber`` →
    ``категория-aber``, ``aber.focus_curve`` → ``aberfocus_curve``."""
    return _NOT_SLUG.sub("", text.lower()).replace(" ", "-")


def _read(name: str) -> str:
    """Текст файла справочника (только чтение)."""
    return (REF / name).read_text(encoding="utf-8")


def _headings(text: str) -> list:
    """Все заголовки h1–h3 файла: ``[(уровень, текст), ...]`` (ATX-стиль)."""
    heads = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,3}) (.+)$", line)
        if m:
            heads.append((len(m.group(1)), m.group(2)))
    return heads


# --------------------------------------------------------------------------- #
# Инвариант 1: справочник полон относительно реестра
# --------------------------------------------------------------------------- #

def test_reference_is_complete():
    """Счётчики справочника == счётчикам реестра: h3-секции страниц,
    registry_snapshot.json и строки счётчиков COMMANDS_INDEX.md."""
    names = set(commands.default_registry.names())
    assert len(names) == 506, f"в реестре {len(names)} команд, ожидалось 506"

    # h3 используется ТОЛЬКО для секций команд (инвариант генератора)
    sections = set()
    for page in sorted(REF.glob("commands-*.md")):
        for line in page.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^### (.+)$", line)
            if m:
                sections.add(m.group(1))
    assert len(sections) == 506, (
        f"h3-секций в справочнике {len(sections)}, ожидалось 506; "
        f"расхождение: {sorted(sections ^ names)[:10]}")
    assert sections == names, (
        f"справочник/реестр различаются: "
        f"нет в справочнике {sorted(names - sections)[:10]}, "
        f"лишние в справочнике {sorted(sections - names)[:10]}")

    snapshot = json.loads(_read("registry_snapshot.json"))
    meta = snapshot["meta"]
    assert meta["command_count"] == len(names)
    assert meta["category_count"] == len(meta["categories"])
    assert len(snapshot["commands"]) == 506
    assert {cmd["name"] for cmd in snapshot["commands"]} == names

    index = _read("COMMANDS_INDEX.md")
    assert "Команд: 506" in index
    assert "Категорий: 40" in index


# --------------------------------------------------------------------------- #
# Инвариант 2: --check чист (регенерация бит-в-бит)
# --------------------------------------------------------------------------- #

def test_check_mode_is_clean():
    """``--check`` генератора: дерево docs/reference побайтово совпадает
    с регенерацией (exit 0); при расхождении — stdout/stderr в assert."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=str(REPO), capture_output=True, timeout=180)
    assert proc.returncode == 0, (
        f"--check exit {proc.returncode} (ожидался 0)\n"
        f"stdout:\n{proc.stdout.decode('utf-8', errors='replace')}\n"
        f"stderr:\n{proc.stderr.decode('utf-8', errors='replace')}")


# --------------------------------------------------------------------------- #
# Инвариант 3: у каждой категории есть страница и строка в индексе
# --------------------------------------------------------------------------- #

def test_every_category_has_file():
    """Для каждой категории реестра существует commands-<cat>.md с h1
    «# Категория <cat>» и упоминание файла в COMMANDS_INDEX.md."""
    index = _read("COMMANDS_INDEX.md")
    for cat in sorted(commands.default_registry.categories()):
        page = REF / f"commands-{cat}.md"
        assert page.is_file(), f"нет страницы категории: {page.name}"
        first = page.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith(f"# Категория {cat}"), (
            f"{page.name}: h1 = {first!r}, ожидалось начало "
            f"'# Категория {cat}'")
        assert f"commands-{cat}.md" in index, (
            f"COMMANDS_INDEX.md не упоминает {page.name}")


# --------------------------------------------------------------------------- #
# Инвариант 4: заголовки и якоря валидны
# --------------------------------------------------------------------------- #

def test_markdown_headers_and_anchors_are_valid():
    """(a) в каждой commands-*.md ровно один h1 и один h2 «Параметры и
    результаты»; (b) слаги заголовков h1–h3 уникальны в файле; (c) каждая
    внутренняя ссылка ``(#frag)`` ведёт на слаг заголовка этого файла;
    (d) каждая ссылка индекса ``commands-<cat>.md#<frag>`` указывает на
    существующий файл, frag == слаг его h1."""
    h1_slugs = {}
    for page in sorted(REF.glob("commands-*.md")):
        text = page.read_text(encoding="utf-8")
        heads = _headings(text)

        h1 = [t for lvl, t in heads if lvl == 1]
        h2 = [t for lvl, t in heads if lvl == 2]
        assert len(h1) == 1, f"{page.name}: h1 {len(h1)} шт., ожидается 1"
        assert h2 == ["Параметры и результаты"], (
            f"{page.name}: h2 {h2!r}, ожидается ['Параметры и результаты']")

        slugs = [_slug(t) for _, t in heads]
        dupes = sorted({s for s in slugs if slugs.count(s) > 1})
        assert not dupes, f"{page.name}: дубликаты якорей {dupes}"

        frags = {m.group(1) for m in
                 re.finditer(r"\[[^\]]*\]\(#([^)]+)\)", text)}
        broken = sorted(frags - set(slugs))
        assert not broken, (
            f"{page.name}: ссылки на несуществующие якоря {broken}")

        m = re.match(r"^(#{1}) (.+)$", text.splitlines()[0])
        h1_slugs[page.name] = _slug(m.group(2))

    index = _read("COMMANDS_INDEX.md")
    for m in re.finditer(
            r"\]\((commands-[^)#]+)\.md#([^)]+)\)", index):
        fname, frag = f"{m.group(1)}.md", m.group(2)
        assert fname in h1_slugs, f"COMMANDS_INDEX.md: нет файла {fname}"
        assert frag == h1_slugs[fname], (
            f"COMMANDS_INDEX.md: якорь {fname}#{frag}, "
            f"ожидался #{h1_slugs[fname]}")
