"""Builtin-команды реестра: smoke КАЖДОЙ команды (Волна 1 + Волна 3 psf).

Демо-данные генерируются самим реестром (system.new + save) — как в
TASK_COMMANDS_W1 §5. Дополнительно — сверка calc.* с прямыми вызовами
domain (обёртка не должна менять числа). Инвариант: у каждой команды
реестра есть smoke-набор здесь (волны добавляют свои записи в карту).
"""
import os

import pytest

from tests.conftest import requires_fil
from commands import CommandContext, default_registry
from commands.base import CommandError
from domain.calculations import (
    compute_beam_geometry,
    paraxial_trace,
    seidel_aberrations,
)
from domain.models import create_demo_system
from fileio.json_io import load_json

# Волна 4 (src=main): команды регистрируются лениво (gui.cmdbridge при
# импорте main) — здесь регистрируем явно, чтобы smoke-инвариант был
# детерминирован и в изолированном прогоне модуля (guard-правило 5 ТЗ).
from commands.builtin import w4_main_cmds
if not default_registry.has("system.append"):
    w4_main_cmds.register(default_registry)


# --------------------------------------------------------------------------- #
# Фикстуры: демо-система, сгенерированная самим реестром (system.new+save)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.opj, .json) демо-ахромат, созданный командами system.new/save."""
    tmp = tmp_path_factory.mktemp("commands_w1")
    opj = str(tmp / "demo_achromat.opj")
    jsn = str(tmp / "demo_achromat.json")
    ctx = CommandContext()
    res = default_registry.execute(
        "system.new", ctx,
        {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    res = default_registry.execute(
        "file.save", ctx, {"src": jsn, "file": opj})
    assert res.ok, res.error
    return opj, jsn


@pytest.fixture
def ctx(demo_files):
    """Контекст с загруженной демо-системой (REPL-сценарий)."""
    opj, _ = demo_files
    context = CommandContext()
    res = default_registry.execute(
        "system.load", context, {"file": opj, "name": "demo"})
    assert res.ok, res.error
    return context


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


# --------------------------------------------------------------------------- #
# Полное покрытие: каждая команда реестра имеет smoke
# --------------------------------------------------------------------------- #

#: Категории Волны 1 — этот smoke-набор покрывает только их; команды
#: более поздних волн (trace/beam/vign/tables, psf/..., ...) держат
#: собственные исчерпывающие наборы в своих тест-модулях.
W1_CATEGORIES = {"file", "system", "calc", "catalog", "analyze"}

#: Синтетические точки зрачка (px, py, W) для команд разложения Цернике:
#: 16 точек ≥ 15 членов классического базиса n≤4,
#: 28 точек ≥ 28 членов базиса OPAL (zern.fit_points).
_SMOKE_POINTS_16 = [
    [0.0, 0.0, 0.10], [0.5, 0.0, 0.20], [0.0, 0.5, -0.10],
    [0.7, 0.7, 0.05], [-0.3, 0.6, 0.02], [0.9, -0.2, -0.30],
    [0.1, -0.8, 0.15], [-0.5, -0.5, 0.0], [0.3, 0.3, 0.01],
    [-0.9, 0.1, 0.20], [0.2, 0.9, -0.05], [-0.1, -0.9, 0.30],
    [0.6, -0.6, -0.02], [-0.7, 0.4, 0.04], [0.8, 0.5, 0.03],
    [0.0, 0.3, 0.0],
]
_SMOKE_POINTS_28 = _SMOKE_POINTS_16 + [
    [0.4, -0.4, 0.0], [-0.2, 0.8, 0.10], [0.55, 0.55, 0.20],
    [0.95, 0.0, -0.10], [0.0, 0.95, 0.25], [-0.95, -0.05, 0.0],
    [0.25, -0.95, -0.20], [0.33, 0.66, 0.05], [-0.66, 0.33, -0.05],
    [0.66, -0.33, 0.10], [0.1, 0.1, 0.0], [-0.1, 0.1, 0.05],
    [0.2, -0.2, -0.05],
]


def _smoke_args(demo_files):
    opj, jsn = demo_files
    return {
        "file.convert": {"src": opj, "dst": opj + ".converted.json"},
        "file.export.protocol": {"file": opj, "out": opj + ".protocol.txt"},
        "file.info": {"file": opj},
        "file.open": {"file": opj},
        "file.save": {"src": opj, "file": opj + ".saved.opj"},
        "file.formats": {},
        "system.current": {"__ctx__": True},
        "system.achromat": {"focal_length": 100.0},
        "system.append": {"file": opj, "append": jsn},
        "system.fields.add": {"file": opj, "y": 7.0},
        "system.fields.list": {"file": opj},
        "system.fields.set": {"file": opj,
                              "fields": [{"y": 0.0}, {"y": 5.0, "x": 1.0,
                                                      "weight": 0.5}]},
        "system.info": {"file": opj},
        "system.load": {"file": opj},
        "system.new": {},
        "system.radii.changes": {"file": opj},
        "system.radii.standardize": {"file": opj},
        "system.reverse": {"file": opj},
        "system.scale": {"file": opj, "factor": 2.0},
        "system.surface.add": {"file": opj, "radius": -60.0},
        "system.surface.remove": {"file": opj, "index": 2},
        "system.surface.set": {"file": opj, "index": 0, "radius": 55.0},
        "system.surfaces.list": {"file": opj},
        "system.wavelengths.add": {"file": opj, "value": 0.48613},
        "system.wavelengths.list": {"file": opj},
        "system.wavelengths.set": {"file": opj,
                                   "wavelengths": [{"value": 0.58756,
                                                    "name": "d"}]},
        "calc.aperture.real": {"file": opj},
        "calc.beam_geometry": {"file": opj},
        "calc.paraxial": {"file": opj},
        "calc.paraxial.multi_wl": {"file": opj},
        "calc.seidel": {"file": opj},
        "catalog.glass.get": {"name": "К8", "wl": 0.54607},
        "catalog.glass.search": {"query": "ТФ"},
        "catalog.info": {},
        "catalog.library.create": {"generator": "achromat_100"},
        "catalog.library.list": {},
        "analyze.field_aberrations": {"file": opj},
        "analyze.psf": {"file": opj},
        "analyze.ray_fan": {"file": opj, "num_rays": 5},
        "analyze.spot": {"file": opj, "num_rays": 10},
        "analyze.tables.tabgl": {"file": opj},
        "analyze.tables.tabpr2": {"file": opj},
        # Волна 3, домен «Дифракция и волновой фронт» (psf_cmds.py);
        # тяжёлые решётки уменьшены, покрываем контракт, не точность.
        "diffr.mtf": {"file": opj, "grid_size": 32},
        "diffr.mtf.limited": {"file": opj},
        "diffr.mtf.poly": {"file": opj, "grid_size": 32},
        "diffr.mtf.quick": {"file": opj},
        "diffr.wavefront": {"file": opj, "grid_size": 32},
        "focus.all": {"file": opj},
        "focus.eqf": {"file": opj},
        "focus.max_strehl": {"file": opj},
        "focus.min_rms": {"file": opj},
        "focus.min_spot": {"file": opj},
        "focus.zone_best": {"file": opj},
        "mtf.curve": {"file": opj},
        "psf.encircled": {"file": opj},
        "psf.lsf": {"file": opj},
        "psf.section": {"file": opj},
        "psf.target": {"file": opj, "freq_lpmm": 50.0},
        "strehl.calc": {"file": opj, "wl": 0.58756},
        "strehl.marechal": {"sigma_w": 0.05},
        "zern.chromatic": {"file": opj, "num_rays": 16},
        "zern.coeffs": {"file": opj, "num_rays": 16},
        "zern.coeffs.fit": {"points": _SMOKE_POINTS_16},
        "zern.decompose": {"file": opj},
        "zern.fit_points": {"points": _SMOKE_POINTS_28},
        "zern.global": {"file": opj, "num_rings": 3, "num_fields": 3},
        "zern.protocol": {"file": opj},
        "zern.reconstruct": {"coeffs": [0.1, 0.0, -0.2, 0.05],
                             "grid": 16},
        "zern.strehl": {"coeffs": [0.1, 0.02, -0.05]},
        "zern.terms": {},
        "zern.wavefront": {"file": opj, "grid_size": 32},
        # R500-1: экспорт таблиц/данных (категория export; выгрузки пишутся
        # рядом с демо-системой в tmp-каталог модуля).
        "export.rows": {"rows": [{"a": 1}], "out": opj + ".rows.csv"},
        "export.data": {"data": {"a": [1]}, "out": opj + ".data.json"},
        "export.text": {"text": "ok", "out": opj + ".text.txt"},
        "export.command": {"cmd": "catalog.info", "out": opj + ".cmd.json"},
        "tables.taboc1.export": {"file": opj, "out": opj + ".taboc1.csv"},
        "tables.taboc2.export": {"file": opj, "out": opj + ".taboc2.csv"},
        "tables.tabgl.export": {"file": opj, "out": opj + ".tabgl.csv"},
        "tables.tabpr2.export": {"file": opj, "out": opj + ".tabpr2.csv"},
        "tables.tabax3.export": {"file": opj, "out": opj + ".tabax3.csv"},
        "tables.tabbea.export": {"file": opj, "out": opj + ".tabbea.csv"},
        "tables.tabeap.export": {"file": opj, "out": opj + ".tabeap.csv"},
        "tables.tabesb.export": {"file": opj, "out": opj + ".tabesb.csv"},
        "tables.field_zones.export": {"out": opj + ".zones.csv"},
        "analyze.spot.export": {"file": opj, "num_rays": 8,
                                "out": opj + ".spot.csv"},
        "analyze.ray_fan.export": {"file": opj, "num_rays": 5,
                                   "out": opj + ".rayfan.csv"},
        "analyze.field_aberrations.export": {"file": opj,
                                             "out": opj + ".fieldab.csv"},
        "aber.fan.export": {"file": opj, "num_rays": 10,
                            "out": opj + ".fan.csv"},
        "aber.mtf_geo.export": {"file": opj, "num_rays": 20,
                                "out": opj + ".mtfgeo.csv"},
        "zern.coeffs.export": {"file": opj, "num_rays": 16,
                               "out": opj + ".zern.csv"},
        "psf.encircled.export": {"file": opj, "out": opj + ".ee.csv"},
        "diffr.mtf.export": {"file": opj, "grid_size": 32,
                             "out": opj + ".mtf.csv"},
        "adv.lsf.export": {"file": opj, "out": opj + ".lsf.csv"},
        "adv.enc.export": {"file": opj, "num_rays": 50,
                           "out": opj + ".enc.csv"},
        "seidel.sums.export": {"file": opj, "out": opj + ".sums.csv"},
        "trace.ray_bundle.export": {"file": opj, "out": opj + ".bundle.csv"},
        "calc.paraxial.export": {"file": opj, "out": opj + ".parax.json"},
        "calc.seidel.export": {"file": opj, "out": opj + ".seidel.json"},
    }


def test_every_registered_command_has_smoke(demo_files):
    """Реестр Волн 1+3(psf) покрыт smoke-набором; trace/aber/opt держат
    свои исчерпывающие наборы в собственных тест-модулях."""
    covered = W1_CATEGORIES | {"psf", "mtf", "diffr", "strehl", "zern",
                               "focus", "export"}
    names = {n for n in default_registry.names()
             if default_registry.get(n).category in covered}
    smoke = _smoke_args(demo_files)
    missing = names - set(smoke)
    extra = set(smoke) - names
    assert not missing, f"команды без smoke: {sorted(missing)}"
    assert not extra, f"smoke для несуществующих команд: {sorted(extra)}"
    assert len(names) >= 30


#: R500: инвариант общего числа команд реестра (обновляется каждым пакетом;
#: 140 (Волны 1-5) + 27 (R500-1 export) = 167).
REGISTRY_TOTAL_COMMANDS = 167


def test_registry_total_count():
    """R500: счётчик реестра == ожидаемому (обновлять в пакетах)."""
    import commands
    commands.register_all()
    assert len(commands.default_registry.names()) == REGISTRY_TOTAL_COMMANDS


def test_smoke_every_command(demo_files, tmp_path):
    """Каждая команда реестра выполняется без ошибки на демо-данных."""
    smoke = _smoke_args(demo_files)
    loaded_ctx = CommandContext()
    assert default_registry.execute(
        "system.load", loaded_ctx, {"file": demo_files[0]}).ok
    for name, args in sorted(smoke.items()):
        call_args = {k: v for k, v in args.items() if k != "__ctx__"}
        result = default_registry.execute(name, loaded_ctx, call_args)
        assert result.ok, f"{name}: {result.error}"
        # контракт: результат строго JSON-сериализуем
        import json
        json.dumps(result.data, ensure_ascii=False, allow_nan=False)


# --------------------------------------------------------------------------- #
# file.*
# --------------------------------------------------------------------------- #

class TestFileCommands:
    def test_formats_shape(self):
        data = run("file.formats")
        fmts = {f["format"]: f for f in data["formats"]}
        assert set(fmts) == {"opj", "lbo", "json"}
        assert fmts["opj"]["write"] and fmts["lbo"]["read"]
        assert not fmts["lbo"]["write"]

    def test_open_json_and_opj_give_same_optics(self, demo_files):
        opj, jsn = demo_files
        from_opj = run("calc.paraxial", {"file": opj})
        from_json = run("calc.paraxial", {"file": jsn})
        assert from_opj["focal_length"] == pytest.approx(
            from_json["focal_length"], abs=1e-6)

    def test_open_unknown_extension(self):
        result = default_registry.execute(
            "file.open", CommandContext(), {"file": "system.txt"})
        assert not result.ok
        assert result.error["code"] == "unknown_format"

    def test_info_counts(self, demo_files):
        data = run("file.info", {"file": demo_files[0]})
        assert data["format"] == "opj"
        assert data["num_surfaces"] == 3
        assert "К8" in data["glasses"] and "ТФ1" in data["glasses"]
        assert data["num_wavelengths"] == 3

    def test_convert_opj_to_json_roundtrip(self, demo_files, tmp_path):
        opj, _ = demo_files
        dst = str(tmp_path / "converted.json")
        data = run("file.convert", {"src": opj, "dst": dst})
        assert data["src_format"] == "opj" and data["dst_format"] == "json"
        system = load_json(dst)
        assert system.num_surfaces == 3
        assert any(s.glass == "К8" for s in system.surfaces)

    def test_save_unsupported_lbo(self, demo_files):
        result = default_registry.execute(
            "file.save", CommandContext(),
            {"src": demo_files[0], "file": "out.lbo"})
        assert not result.ok
        assert result.error["code"] == "unsupported"


# --------------------------------------------------------------------------- #
# system.*
# --------------------------------------------------------------------------- #

class TestSystemCommands:
    def test_new_empty_and_demos(self):
        empty = run("system.new", {"demo": "empty"})
        assert empty["num_surfaces"] == 0
        for demo in ("default", "achromat", "petzval", "mirror"):
            data = run("system.new", {"demo": demo})
            assert data["num_surfaces"] >= 2, demo

    def test_new_bad_demo_choice(self):
        result = default_registry.execute(
            "system.new", CommandContext(), {"demo": "nosuch"})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_load_sets_current(self, demo_files, ctx):
        assert ctx.current is not None
        data = run("system.current", ctx=ctx)
        assert data["name_in_context"] == "demo"
        assert "demo" in data["context_names"]

    def test_current_without_load_is_error(self):
        result = default_registry.execute(
            "system.current", CommandContext(), {})
        assert not result.ok
        assert result.error["code"] == "not_found"

    def test_mutations_visible_in_ctx(self, demo_files, ctx):
        """REPL-сценарий: правка текущей системы меняет её параксиал."""
        before = run("calc.paraxial", ctx=ctx)["focal_length"]
        changed = run("system.surface.set",
                      {"index": 0, "radius": 40.0}, ctx=ctx)
        assert changed["changed"] == ["radius"]
        assert changed["surfaces"][0]["radius"] == 40.0
        after = run("calc.paraxial", ctx=ctx)["focal_length"]
        assert after != pytest.approx(before)

    def test_surface_add_index_and_append(self, ctx):
        inserted = run("system.surface.add",
                       {"radius": -33.0, "index": 0}, ctx=ctx)
        assert inserted["surfaces"][0]["radius"] == -33.0
        appended = run("system.surface.add",
                       {"radius": -44.0}, ctx=ctx)
        assert appended["surfaces"][-1]["radius"] == -44.0

    def test_surface_remove_bad_index(self, ctx):
        result = default_registry.execute(
            "system.surface.remove", ctx, {"index": 99})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_surface_set_requires_fields(self, ctx):
        result = default_registry.execute(
            "system.surface.set", ctx, {"index": 0})
        assert not result.ok

    def test_wavelengths_and_fields_add(self, ctx):
        wls = run("system.wavelengths.add",
                  {"value": 0.48613, "name": "F"}, ctx=ctx)
        assert wls["wavelengths"][-1] == {"value": 0.48613, "weight": 1.0,
                                          "name": "F"}
        flds = run("system.fields.add", {"y": 7.0}, ctx=ctx)
        assert flds["field_points"][-1]["y"] == 7.0

    def test_no_system_source_error(self):
        result = default_registry.execute(
            "calc.paraxial", CommandContext(), {})
        assert not result.ok
        assert result.error["code"] == "no_system"


# --------------------------------------------------------------------------- #
# calc.* — числа совпадают с прямыми вызовами domain
# --------------------------------------------------------------------------- #

class TestCalcCommands:
    def test_paraxial_matches_domain(self, demo_files):
        opj, _ = demo_files
        direct = paraxial_trace(load_json(demo_files[1]))
        data = run("calc.paraxial", {"file": opj})
        assert data["focal_length"] == pytest.approx(
            direct["focal_length"], rel=1e-12)
        assert data["f_number"] == pytest.approx(direct["f_number"],
                                                 rel=1e-12)
        assert 90.0 < abs(data["focal_length"]) < 110.0  # ахромат f'≈100

    def test_paraxial_wl_override(self, demo_files):
        _, jsn = demo_files
        blue = run("calc.paraxial", {"file": jsn, "wl": 0.43405})
        red = run("calc.paraxial", {"file": jsn, "wl": 0.65627})
        assert blue["wl"] == 0.43405 and red["wl"] == 0.65627
        assert blue["focal_length"] != pytest.approx(red["focal_length"])

    def test_multi_wl_covers_system_wavelengths(self, demo_files):
        _, jsn = demo_files
        system = load_json(jsn)
        data = run("calc.paraxial.multi_wl", {"file": jsn})
        assert data["num_wavelengths"] == len(system.wavelengths)
        wls = [r["wl"] for r in data["results"]]
        assert wls == pytest.approx([w.value for w in system.wavelengths])

    def test_seidel_matches_domain(self, demo_files):
        _, jsn = demo_files
        direct = seidel_aberrations(load_json(jsn))
        data = run("calc.seidel", {"file": jsn})
        assert data == pytest.approx(direct)

    def test_beam_geometry_matches_domain(self, demo_files):
        _, jsn = demo_files
        direct = compute_beam_geometry(load_json(jsn))
        data = run("calc.beam_geometry", {"file": jsn})
        assert len(data["fields"]) == len(direct)
        assert data["fields"][0]["Ax"] == pytest.approx(direct[0]["Ax"])

    def test_aperture_real_returns_diameter(self, demo_files):
        _, jsn = demo_files
        data = run("calc.aperture.real", {"file": jsn})
        assert data["diameter"] > 0


# --------------------------------------------------------------------------- #
# catalog.*
# --------------------------------------------------------------------------- #

class TestCatalogCommands:
    @requires_fil
    def test_info_counts(self):
        data = run("catalog.info")
        assert data["glasses"]["gost"] >= 25
        assert data["glasses"]["fil"] > 100
        assert "library" in data

    def test_glass_get_known_and_unknown(self):
        data = run("catalog.glass.get", {"name": "К8", "wl": 0.54607})
        assert data["source"] == "gost"
        assert data["nd"] == pytest.approx(1.5163, abs=1e-4)
        assert 1.5 < data["n"] < 1.6
        result = default_registry.execute(
            "catalog.glass.get", CommandContext(),
            {"name": "NO_SUCH_GLASS_XYZ"})
        assert not result.ok
        assert result.error["code"] == "not_found"

    def test_glass_search_finds_and_limits(self):
        data = run("catalog.glass.search", {"query": "ТФ", "limit": 5})
        assert 0 < len(data["matches"]) <= 5
        assert data["total"] >= len(data["matches"])
        sources = {m["source"] for m in data["matches"]}
        assert "gost" in sources

    def test_library_list_categories(self):
        data = run("catalog.library.list")
        names = [c["name"] for c in data["categories"]]
        assert any("OPAL" in n or "LBO" in n for n in names)


# --------------------------------------------------------------------------- #
# analyze.*
# --------------------------------------------------------------------------- #

class TestAnalyzeCommands:
    def test_ray_fan_shape(self, demo_files):
        data = run("analyze.ray_fan",
                   {"file": demo_files[1], "num_rays": 5})
        assert len(data["rays"]) == 5
        assert data["rays"][0]["pupil_y"] == pytest.approx(-1.0)
        assert data["rays"][2]["pupil_y"] == pytest.approx(0.0)
        ok_rays = [r for r in data["rays"] if r["success"]]
        assert ok_rays, "все лучи веера упали"
        assert all(len(r["path"]) >= 2 for r in ok_rays)

    def test_field_aberrations_rows(self, demo_files):
        data = run("analyze.field_aberrations",
                   {"file": demo_files[1], "fields": [0.0, 3.0]})
        assert [f["field_y"] for f in data["fields"]] == [0.0, 3.0]

    def test_spot_metrics(self, demo_files):
        data = run("analyze.spot",
                   {"file": demo_files[1], "num_rays": 10})
        assert data["num_points"] > 0
        assert data["rms"] >= 0.0
        assert data["rms_xy"]["rms_total"] >= 0.0

    def test_psf_scalars_and_grid(self, demo_files):
        scalars = run("analyze.psf", {"file": demo_files[1]})
        assert "strehl" in scalars and "cutoff_lpmm" in scalars
        assert "psf" not in scalars  # решётки по умолчанию выключены
        grid = run("analyze.psf",
                   {"file": demo_files[1], "include_grid": True})
        assert len(grid["psf"]) == len(grid["y_um"])
        assert abs(sum(sum(row) for row in grid["psf"]) - 1.0) < 1e-3

    def test_tables_tabgl_and_tabpr2(self, demo_files):
        tabgl = run("analyze.tables.tabgl", {"file": demo_files[1]})
        assert tabgl["rows"][-1]["n"] == 0  # осевая строка-эталон (замыкает)
        assert "TABGL" in tabgl["text"].upper() or tabgl["text"].strip()
        tabpr2 = run("analyze.tables.tabpr2", {"file": demo_files[1]})
        assert len(tabpr2["rows"]) == len(tabgl["rows"])
        assert tabpr2["text"].strip()


# --------------------------------------------------------------------------- #
# Источники системы: файл vs контекст vs текущая
# --------------------------------------------------------------------------- #

class TestSystemResolution:
    def test_ctx_name_beats_current(self, demo_files):
        _, jsn = demo_files
        ctx = CommandContext()
        assert default_registry.execute(
            "system.load", ctx, {"file": jsn, "name": "a"}).ok
        # подменим текущую: первая загруженная остаётся доступной по имени
        assert default_registry.execute(
            "system.new", ctx, {"demo": "mirror", "name": "b"}).ok
        via_name = run("system.surfaces.list", {"system": "a"}, ctx=ctx)
        via_current = run("system.surfaces.list", {}, ctx=ctx)
        assert via_name["num_surfaces"] == 3      # ахромат 'a'
        assert via_current["num_surfaces"] == 2   # зеркало 'b' текущее

    def test_file_beats_ctx(self, demo_files):
        opj, jsn = demo_files
        ctx = CommandContext()
        assert default_registry.execute(
            "system.load", ctx, {"file": jsn}).ok
        data = run("system.info", {"file": opj}, ctx=ctx)
        assert data["num_surfaces"] == 3

    def test_unknown_ctx_name(self, demo_files):
        result = default_registry.execute(
            "system.info", CommandContext(), {"system": "ghost"})
        assert not result.ok
        assert result.error["code"] == "not_found"
