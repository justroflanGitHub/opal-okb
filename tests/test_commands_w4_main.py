"""Команды Волны 4 (src=main, w4_main_cmds): smoke КАЖДОЙ команды +
сверка с прямыми вызовами utils/system_utils, achromat,
catalog/library, fileio/protocol + REPL-семантика замены текущей
системы контекста.

Реестр изолирован от default_registry (Волна 4: команды появятся в
общем builtin-каталоге после мержа — координатор обновит __init__),
поэтому модуль поднимает свой Registry = builtin + w4_main_cmds
(правило 5 ТЗ Волны 4: регистрация вручную + guard has()).
"""
import os

import pytest

import commands
from commands import CommandContext, Registry
from commands.builtin import w4_main_cmds

# --------------------------------------------------------------------------- #
# Изолированный реестр: builtin Волны 1+3 + команды Волны 4 (src=main)
# --------------------------------------------------------------------------- #

registry = Registry()
commands.register_all(registry)  # Волны 1+3 (128 команд после мержа)
if not registry.has("system.append"):  # guard правила 5 ТЗ Волны 4
    w4_main_cmds.register(registry)

#: Все команды модуля (полнота smoke-покрытия).
W4_MAIN_COMMANDS = (
    "system.reverse",
    "system.scale",
    "system.radii.changes",
    "system.radii.standardize",
    "system.append",
    "system.achromat",
    "catalog.library.create",
    "system.fields.set",
    "system.wavelengths.set",
    "file.export.protocol",
)


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = registry.execute(name, ctx or CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def demo_ctx(demo="achromat"):
    """Контекст REPL с демо-системой (system.load-сценарий через put)."""
    from domain.models import create_demo_system_by_name
    ctx = CommandContext()
    ctx.put_system("demo", create_demo_system_by_name(demo))
    return ctx


# --------------------------------------------------------------------------- #
# Полнота регистрации
# --------------------------------------------------------------------------- #

def test_all_w4_main_commands_registered():
    for name in W4_MAIN_COMMANDS:
        assert registry.has(name), name


# --------------------------------------------------------------------------- #
# system.reverse / system.scale
# --------------------------------------------------------------------------- #

class TestReverseScale:
    def test_reverse_matches_direct_call(self):
        from utils.system_utils import reverse_system
        from domain.models import create_demo_system_by_name
        data = run("system.reverse", {}, ctx=demo_ctx())  # REPL-текущая
        direct = reverse_system(create_demo_system_by_name("achromat"))
        assert [s["radius"] for s in data["surfaces"]] == \
            [s.radius for s in direct.surfaces]
        assert data["replaced_current"] is True

    def test_reverse_stateless_from_file(self, tmp_path):
        """CLI-режим (file=): исходный файл не трогается, замены нет."""
        src = str(tmp_path / "demo.opal.json")
        run("system.new", {"demo": "telephoto", "save": src})
        data = run("system.reverse", {"file": src})
        assert data["replaced_current"] is False
        # файл не перезаписан
        data2 = run("system.info", {"file": src})
        assert data2["num_surfaces"] == 4

    def test_scale_matches_direct_call(self):
        from utils.system_utils import scale_system
        from domain.models import create_demo_system_by_name
        factor = 2.5
        data = run("system.scale", {"factor": factor}, ctx=demo_ctx())
        direct = scale_system(create_demo_system_by_name("achromat"),
                              factor)
        assert data["aperture_value"] == pytest.approx(
            direct.aperture_value)
        assert [s["radius"] for s in data["surfaces"]] == \
            [s.radius for s in direct.surfaces]

    def test_scale_zero_factor_rejected(self):
        result = registry.execute(
            "system.scale", demo_ctx(), {"factor": 0.0})
        assert not result.ok
        assert "factor" in result.error["message"]

    def test_scale_save_out(self, tmp_path):
        out = str(tmp_path / "scaled.opal.json")
        run("system.scale", {"factor": 0.5, "out": out}, ctx=demo_ctx())
        assert os.path.exists(out)
        data = run("system.info", {"file": out})
        assert data["num_surfaces"] > 0


# --------------------------------------------------------------------------- #
# system.radii.* (ГОСТ 1807-75)
# --------------------------------------------------------------------------- #

class TestRadiiGost:
    @pytest.fixture
    def nonstandard_ctx(self):
        """Система с заведомо нестандартным радиусом."""
        ctx = demo_ctx()
        ctx.current.surfaces[0].radius = 61.93  # не по ГОСТ
        return ctx

    def test_changes_lists_nonstandard(self, nonstandard_ctx):
        from utils.system_utils import get_radii_changes
        data = run("system.radii.changes", {}, ctx=nonstandard_ctx)
        direct = get_radii_changes(nonstandard_ctx.current)
        assert data["num_changes"] == len(direct)
        assert data["num_changes"] >= 1
        first = data["changes"][0]
        assert first["old_radius"] == pytest.approx(61.93)
        assert "delta_percent" in first

    def test_standardize_matches_direct(self, nonstandard_ctx):
        from utils.system_utils import standardize_radii
        from domain.models import create_demo_system_by_name
        data = run("system.radii.standardize", {}, ctx=nonstandard_ctx)
        direct = standardize_radii(
            create_demo_system_by_name("achromat"))
        direct.surfaces[0].radius = 61.93
        direct = standardize_radii(direct)
        assert [s["radius"] for s in data["surfaces"]] == \
            [s.radius for s in direct.surfaces]
        # REPL: текущая система контекста заменена
        assert nonstandard_ctx.current.surfaces[0].radius == \
            pytest.approx(data["surfaces"][0]["radius"])


# --------------------------------------------------------------------------- #
# system.append
# --------------------------------------------------------------------------- #

class TestAppend:
    def test_append_concatenates(self, tmp_path):
        extra = str(tmp_path / "meniscus.opal.json")
        run("system.new", {"demo": "meniscus", "save": extra})
        n_extra = run("system.info", {"file": extra})["num_surfaces"]
        ctx = demo_ctx("achromat")
        n_before = len(ctx.current.surfaces)
        data = run("system.append", {"append": extra}, ctx=ctx)
        assert data["num_surfaces"] == n_before + n_extra
        assert "+" in data["name"]
        # REPL-замена: текущая система — объединённая
        assert len(ctx.current.surfaces) == data["num_surfaces"]

    def test_append_requires_path(self):
        result = registry.execute("system.append", demo_ctx(), {})
        assert not result.ok  # обязательный параметр append


# --------------------------------------------------------------------------- #
# system.achromat
# --------------------------------------------------------------------------- #

class TestAchromat:
    def test_matches_design_achromat(self):
        from achromat import design_achromat
        data = run("system.achromat",
                   {"focal_length": 150.0, "crown": "К8",
                    "flint": "ТФ5", "aperture": 25.0})
        direct = design_achromat(150.0, "К8", "ТФ5", 25.0)
        assert [s["radius"] for s in data["surfaces"]] == \
            [s.radius for s in direct.surfaces]
        assert data["name"] == direct.name

    def test_result_into_context(self):
        ctx = CommandContext()
        run("system.achromat", {"focal_length": 100.0, "name": "ach"},
            ctx=ctx)
        assert ctx.current_name == "ach"
        assert ctx.current.num_surfaces >= 2


# --------------------------------------------------------------------------- #
# catalog.library.create
# --------------------------------------------------------------------------- #

class TestLibraryCreate:
    def test_generator_entry(self):
        from catalog.library import create_system_from_entry
        data = run("catalog.library.create",
                   {"generator": "achromat_100"})
        direct = create_system_from_entry({"generator": "achromat_100"})
        assert [s["radius"] for s in data["surfaces"]] == \
            [s.radius for s in direct.surfaces]

    def test_requires_source(self):
        result = registry.execute("catalog.library.create",
                                  CommandContext(), {})
        assert not result.ok
        assert "generator" in result.error["message"]


# --------------------------------------------------------------------------- #
# system.fields.set / system.wavelengths.set
# --------------------------------------------------------------------------- #

class TestSets:
    def test_fields_set_replaces_all(self):
        ctx = demo_ctx()
        fields = [{"y": 0.0, "x": 0.0, "weight": 1.0},
                  {"y": 3.5, "x": 1.0, "weight": 0.5},
                  {"y": -2.0}]
        data = run("system.fields.set", {"fields": fields}, ctx=ctx)
        assert data["num_surfaces"] == ctx.current.num_surfaces  # ok
        assert len(ctx.current.field_points) == 3
        assert ctx.current.field_points[1].y == pytest.approx(3.5)
        assert ctx.current.field_points[1].weight == pytest.approx(0.5)
        # y без x/weight — дефолты 0/1
        assert ctx.current.field_points[2].weight == pytest.approx(1.0)

    def test_fields_set_rejects_missing_y(self):
        result = registry.execute(
            "system.fields.set", demo_ctx(),
            {"fields": [{"x": 1.0}]})
        assert not result.ok
        assert "y" in result.error["message"]

    def test_wavelengths_set_keeps_line_names(self):
        ctx = demo_ctx()
        wavelengths = [{"value": 0.54607, "name": "e", "weight": 2.0},
                       {"value": 0.65627, "name": "C"}]
        run("system.wavelengths.set", {"wavelengths": wavelengths},
            ctx=ctx)
        wls = ctx.current.wavelengths
        assert len(wls) == 2
        assert wls[0].name == "e"
        assert wls[0].weight == pytest.approx(2.0)
        assert wls[1].name == "C"
        assert wls[1].weight == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# file.export.protocol
# --------------------------------------------------------------------------- #

class TestExportProtocol:
    def test_txt_protocol_written(self, tmp_path):
        from domain.calculations import paraxial_trace
        out = str(tmp_path / "protocol.txt")
        ctx = demo_ctx()
        data = run("file.export.protocol", {"out": out}, ctx=ctx)
        assert os.path.exists(out)
        text = open(out, encoding="utf-8").read()
        assert "ПРОТОКОЛ" in text
        f_direct = paraxial_trace(ctx.current)["focal_length"]
        assert data["focal_length"] == pytest.approx(f_direct)
