"""R500-13: интроспекция реестра и окружения (commands/builtin/meta_cmds.py).

Команды работают с реестром-замыканием (не с default_registry) —
проверяется на изолированном реестре: свежий ``Registry()`` + только
``meta_cmds.register`` видит ровно свои 12 команд и никаких чужих.
Остальные тесты — на default_registry (все builtin): сверка счётчиков
со ``registry.names()``, поиск/схемы/справка на известных командах,
снимок реестра в файл, версия проекта из CHANGELOG.md.
"""
import json
import os
import re

import pytest

from commands import CommandContext, Registry, default_registry
from commands.builtin.meta_cmds import (
    CHANGELOG_NAME,
    PROJECT_ROOT,
    register as meta_register,
)


def run(name, args=None):
    result = default_registry.execute(name, CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error


#: Число команд meta-модуля (инвариант изолированного реестра).
META_COMMANDS = 12

#: Категории, которые вводит модуль.
META_CATEGORIES = {"registry", "app", "help"}


@pytest.fixture(scope="module")
def isolated_registry():
    """Свежий реестр только с meta-командами (замыкание registry)."""
    registry = Registry()
    meta_register(registry)
    return registry


def iso_run(registry, name, args=None):
    result = registry.execute(name, CommandContext(), args or {})
    assert result.ok, f"[iso] {name}: {result.error}"
    return result.data


# --------------------------------------------------------------------------- #
# Замыкание реестра: команды видят реестр, в котором зарегистрированы
# --------------------------------------------------------------------------- #

class TestClosureRegistry:
    def test_isolated_stats_sees_only_meta(self, isolated_registry):
        data = iso_run(isolated_registry, "registry.stats")
        assert data["total"] == META_COMMANDS
        assert data["num_categories"] == len(META_CATEGORIES)
        assert set(data["categories"]) == META_CATEGORIES
        assert sum(data["categories"].values()) == META_COMMANDS

    def test_isolated_list_no_foreign_commands(self, isolated_registry):
        data = iso_run(isolated_registry, "registry.list")
        assert data["total"] == META_COMMANDS
        names = [row["name"] for row in data["rows"]]
        assert names == sorted(names)
        assert "calc.paraxial" not in names       # чужих команд нет

    def test_isolated_schema_not_found(self, isolated_registry):
        result = isolated_registry.execute(
            "registry.schema", CommandContext(), {"name": "calc.paraxial"})
        assert not result.ok
        assert result.error["code"] == "not_found"

    def test_isolated_app_info_counts(self, isolated_registry):
        data = iso_run(isolated_registry, "app.info")
        assert data["registry"]["total"] == META_COMMANDS


# --------------------------------------------------------------------------- #
# registry.stats / registry.categories
# --------------------------------------------------------------------------- #

class TestStatsCategories:
    def test_stats_matches_registry(self):
        data = run("registry.stats")
        names = default_registry.names()
        assert data["total"] == len(names)
        assert data["num_categories"] == len(default_registry.categories())
        assert sum(data["categories"].values()) == data["total"]
        assert data["categories"]["registry"] == 8
        assert data["categories"]["app"] == 3
        assert data["categories"]["help"] == 1

    def test_categories_rows_sorted_with_descriptions(self):
        data = run("registry.categories")
        rows = data["categories"]
        assert data["count"] == len(rows) >= 3
        assert [r["name"] for r in rows] == sorted(r["name"] for r in rows)
        by_name = {r["name"]: r for r in rows}
        assert by_name["registry"]["commands"] == 8
        # описание есть у всех стандартных категорий builtin
        assert by_name["calc"]["description"]
        assert by_name["registry"]["description"]

    def test_categories_counts_match_stats(self):
        stats = run("registry.stats")
        cats = run("registry.categories")
        assert {r["name"]: r["commands"] for r in cats["categories"]} == \
            stats["categories"]


# --------------------------------------------------------------------------- #
# registry.list / registry.search
# --------------------------------------------------------------------------- #

class TestListSearch:
    def test_list_all_sorted(self):
        data = run("registry.list")
        names = [r["name"] for r in data["rows"]]
        assert data["shown"] == data["total"] == len(default_registry.names())
        assert names == sorted(names)
        assert all(r["description"] for r in data["rows"])

    def test_list_by_category(self):
        data = run("registry.list", {"category": "quality"})
        assert data["shown"] > 0
        assert {r["category"] for r in data["rows"]} == {"quality"}

    def test_list_by_prefix(self):
        data = run("registry.list", {"prefix": "registry."})
        names = [r["name"] for r in data["rows"]]
        assert names == [n for n in default_registry.names()
                         if n.startswith("registry.")]
        assert len(names) == 8

    def test_list_unknown_category(self):
        fail("registry.list", {"category": "no_such_category"},
             "not_found")

    def test_search_by_name_description_category(self):
        by_name = run("registry.search", {"query": "paraxial"})
        assert "calc.paraxial" in [r["name"] for r in by_name["rows"]]
        assert all("name" in r["matched_in"] for r in by_name["rows"]
                   if r["name"] == "calc.paraxial")
        by_desc = run("registry.search", {"query": "Зейдел"})
        assert by_desc["total"] > 0
        assert all("description" in r["matched_in"] or
                   "name" in r["matched_in"] for r in by_desc["rows"])
        by_cat = run("registry.search", {"query": "zern"})
        assert all("zern" in (r["category"] + r["name"]).lower()
                   for r in by_cat["rows"])

    def test_search_case_insensitive_and_limit(self):
        data = run("registry.search", {"query": "ПАРАКСИАЛ"})
        assert data["total"] > 0
        limited = run("registry.search", {"query": "а", "limit": 3})
        assert limited["shown"] == 3 < limited["total"]

    def test_search_empty_query(self):
        fail("registry.search", {"query": "   "}, "invalid_param")


# --------------------------------------------------------------------------- #
# registry.schema / registry.category.info / registry.params
# --------------------------------------------------------------------------- #

class TestSchemaCategoryParams:
    def test_schema_known_command(self):
        data = run("registry.schema", {"name": "calc.paraxial"})
        assert data["name"] == "calc.paraxial"
        assert data["category"] == "calc"
        params = {p["name"]: p for p in data["params"]}
        assert "file" in params and "wl" in params
        assert params["wl"]["type"] == "float"
        assert not params["wl"]["required"]
        assert data["returns"]

    def test_schema_unknown_command(self):
        fail("registry.schema", {"name": "no.such_command"}, "not_found")

    def test_category_info_with_signatures(self):
        data = run("registry.category.info", {"category": "plot"})
        assert data["category"] == "plot"
        assert data["count"] == len(
            default_registry.list("plot"))
        first = data["commands"][0]
        assert first["name"].startswith("plot.")
        assert "(" in first["signature"] and ")" in first["signature"]
        assert isinstance(first["params"], list)

    def test_category_info_unknown(self):
        fail("registry.category.info", {"category": "zzz"}, "not_found")

    def test_params_common_param(self):
        data = run("registry.params", {"param": "file"})
        assert data["count"] > 10
        rows = {r["name"] for r in data["rows"]}
        assert "calc.paraxial" in rows
        assert all(r["type"] == "str" for r in data["rows"])

    def test_params_type_filter(self):
        data = run("registry.params",
                   {"param": "num_rays", "type": "int"})
        assert data["count"] > 0
        assert all(r["type"] == "int" for r in data["rows"])
        assert data["type"] == "int"

    def test_params_unknown_name_is_empty_not_error(self):
        data = run("registry.params", {"param": "no_such_param_x"})
        assert data["count"] == 0 and data["rows"] == []

    def test_params_bad_type_choice(self):
        fail("registry.params", {"param": "file", "type": "decimal"},
             "invalid_param")


# --------------------------------------------------------------------------- #
# registry.export — снимок реестра в JSON
# --------------------------------------------------------------------------- #

class TestRegistryExport:
    def test_export_snapshot_file(self, tmp_path):
        out = str(tmp_path / "registry_snapshot.json")
        data = run("registry.export", {"out": out})
        assert data["format"] == "json"
        assert data["total"] == len(default_registry.names())
        assert os.path.isfile(out)
        with open(out, encoding="utf-8") as f:
            snapshot = json.load(f)
        assert snapshot["total"] == data["total"]
        assert snapshot["commands"]["calc.paraxial"]["category"] == "calc"
        assert "params" in snapshot["commands"]["registry.schema"]

    def test_export_requires_json_extension(self, tmp_path):
        fail("registry.export",
             {"out": str(tmp_path / "snap.txt")}, "unsupported")

    def test_isolated_export_only_meta(self, isolated_registry, tmp_path):
        out = str(tmp_path / "iso_snapshot.json")
        data = iso_run(isolated_registry, "registry.export", {"out": out})
        with open(out, encoding="utf-8") as f:
            snapshot = json.load(f)
        assert snapshot["total"] == META_COMMANDS
        assert set(snapshot["commands"]) == {
            n for n in isolated_registry.names()}


# --------------------------------------------------------------------------- #
# app.info / app.env / app.paths — фактические источники, без магии
# --------------------------------------------------------------------------- #

class TestAppCommands:
    def test_info_version_from_changelog(self):
        data = run("app.info")
        assert data["project"] == "OPAL-OKB"
        assert data["version_source"] == CHANGELOG_NAME
        # версия = верхний релиз CHANGELOG.md (единственный источник)
        release = None
        with open(os.path.join(PROJECT_ROOT, CHANGELOG_NAME),
                  encoding="utf-8") as f:
            for line in f:
                match = re.match(r"^##\s*\[(\d+(?:\.\d+)+)\]", line)
                if match:
                    release = match.group(1)
                    break
        assert data["version"] == release
        assert re.fullmatch(r"\d+\.\d+(\.\d+)?", data["version"])
        assert data["python"].startswith("3.")
        assert data["platform"]
        assert data["registry"]["total"] == len(default_registry.names())

    def test_env_packages_and_encoding(self):
        data = run("app.env")
        assert data["python"].startswith("3.")
        assert data["os"]
        for package in ("numpy", "matplotlib"):
            entry = data["packages"][package]
            # в тестовой среде оба пакета обязательны (pytest-qt, Agg)
            assert entry["available"] is True, package
            assert entry["version"]
        assert data["stdout_encoding"]

    def test_paths_from_catalog_library(self):
        from catalog.library import BASE_DIR, LBO_DIR, OPJ_DIR
        data = run("app.paths")
        assert data["base_dir"] == BASE_DIR
        assert data["opj_dir"] == OPJ_DIR
        assert data["lbo_dir"] == LBO_DIR
        assert isinstance(data["opj_dir_exists"], bool)
        assert isinstance(data["lbo_dir_exists"], bool)
        assert data["num_opj_files"] >= 0 and data["num_lbo_files"] >= 0
        assert data["cwd"] == os.getcwd()

    def test_paths_counts_consistent_with_exists(self):
        data = run("app.paths")
        if not data["opj_dir_exists"]:
            assert data["num_opj_files"] == 0
        if not data["lbo_dir_exists"]:
            assert data["num_lbo_files"] == 0


# --------------------------------------------------------------------------- #
# help.command — человеческая справка
# --------------------------------------------------------------------------- #

class TestHelpCommand:
    def test_help_contents_and_example(self):
        data = run("help.command", {"name": "system.new"})
        assert data["name"] == "system.new"
        assert data["description"]
        param_names = {p["name"] for p in data["params"]}
        assert {"demo", "name", "save"} <= param_names
        assert data["example"].startswith(
            "py -m commands run system.new")
        assert "--param demo=" in data["example"]

    def test_help_example_uses_default_or_placeholder(self):
        data = run("help.command", {"name": "calc.paraxial"})
        assert "--param file=" in data["example"]     # str → заглушка
        data = run("help.command", {"name": "plot.caustic"})
        assert "--param num_rays=15" in data["example"]  # умолчание

    def test_help_unknown_command(self):
        fail("help.command", {"name": "ghost.command"}, "not_found")

    def test_help_hint_on_same_prefix(self):
        result = default_registry.execute(
            "help.command", CommandContext(), {"name": "registry.stat"})
        assert not result.ok
        assert result.error["code"] == "not_found"
        assert "registry.stats" in result.error["message"]
