# -*- coding: utf-8 -*-
"""Команды Волны 3 «Трассировка и таблицы» (commands/builtin/trace_cmds.py):
trace.*/beam.*/vign.*/tables.* — smoke КАЖДОЙ команды домена + сверка с
прямыми вызовами analysis (обёртка не должна менять числа).

Демо-система — сам реестр (system.new + save, как test_commands_builtin);
виньетированные/экранированные сценарии — программы в контексте REPL
(построители как test_vignetting: дублет со срезанной S2, зеркало с
центральным экранированием).
"""
import json
import math

import pytest

from commands import CommandContext, default_registry
from optics_engine import FieldPoint, OpticalSystem, Surface, Wavelength

from analysis.beam_heights import tabeap_rows, tabesb_rows
from analysis.ray_tracing import (
    Ray,
    get_focal_spot,
    trace_grid_3d,
    trace_ray_through_system,
)
from analysis.tables import field_zones as field_zones_fn
from analysis.tables import max_field as max_field_fn
from analysis.tables import taboc1_rows, taboc2_rows
from analysis.vignetting import (
    compute_light_distribution,
    compute_vignetting,
    find_passage_zones,
    real_obscuration,
    tabbea_rows,
)


# --------------------------------------------------------------------------- #
# Фикстуры
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.json, .opj) демо-ахромат, созданный командами system.new/save."""
    tmp = tmp_path_factory.mktemp("commands_w3")
    jsn = str(tmp / "demo_achromat.json")
    opj = str(tmp / "demo_achromat.opj")
    ctx = CommandContext()
    res = default_registry.execute(
        "system.new", ctx, {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    res = default_registry.execute(
        "file.save", ctx, {"src": jsn, "file": opj})
    assert res.ok, res.error
    return jsn, opj


def build_clipped() -> OpticalSystem:
    """Дублет со срезанной второй поверхностью (semi_diameter S2 = 4 мм).

    Как ``build_clipped`` в test_vignetting: верхний край на поле 3°
    срезается поверхностью 2 → ограничение ('P', 2).
    """
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.aperture_value = 10.0
    s.field_points = [FieldPoint(0.0), FieldPoint(3.0), FieldPoint(6.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=25),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=4.0),
        Surface(radius=-200, glass='', thickness=70),
    ]
    return s


def build_mirror(obscuration: float = 0.3,
                 semi_diameter: float = 25.0) -> OpticalSystem:
    """Вогнутое зеркало D=40 с центральным экранированием."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.aperture_value = 40.0
    s.obscuration_ratio = obscuration
    s.surfaces = [Surface(radius=-400, glass='', thickness=-200,
                          is_reflective=True, semi_diameter=semi_diameter)]
    return s


@pytest.fixture
def ctx_clipped():
    """REPL-контекст с виньетированным дублетом (имя 'clipped')."""
    ctx = CommandContext()
    ctx.put_system("clipped", build_clipped())
    return ctx


@pytest.fixture
def ctx_mirror():
    """REPL-контекст с экранированным зеркалом (имя 'mirror')."""
    ctx = CommandContext()
    ctx.put_system("mirror", build_mirror())
    return ctx


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def plain(value):
    """Прямой результат analysis → JSON-норма (кортежи → списки)."""
    return json.loads(json.dumps(value, ensure_ascii=False))


def assert_points_equal(got, expected):
    """Посегментная сверка списка точек (approx не берёт вложенность)."""
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        assert g == pytest.approx(list(e))


# --------------------------------------------------------------------------- #
# Полное покрытие: каждая команда домена имеет smoke
# --------------------------------------------------------------------------- #

W3_CATEGORIES = {"trace", "beam", "vign", "tables"}


def _smoke_args(demo_files):
    jsn, _ = demo_files
    return {
        "trace.ray": {"file": jsn, "y": 5.0, "z": -20.0},
        "trace.grid3d": {"file": jsn, "num_rings": 2, "num_azimuths": 4},
        "trace.focal_spot": {"file": jsn, "num_rays": 10},
        "trace.intersect.sphere": {"y": 5.0, "z": -20.0, "m": 1.0,
                                   "radius": -60.0},
        "trace.intersect.aspheric": {"y": 5.0, "z": -20.0, "m": 1.0,
                                     "radius": -60.0, "conic_k": -1.0},
        "trace.normal.sphere": {"x": 0.0, "y": 5.0, "z": -0.2,
                                "radius": -60.0},
        "trace.normal.aspheric": {"x": 0.0, "y": 5.0, "z": -0.2,
                                  "radius": -60.0, "conic_k": -1.0},
        "trace.refract": {"k": 0.0, "l": 0.3, "m": 0.95,
                          "nx": 0.0, "ny": 0.0, "nz": 1.0,
                          "n1": 1.0, "n2": 1.5},
        "beam.heights": {"file": jsn},
        "beam.screen_zones": {"file": jsn},
        "vign.compute": {"file": jsn},
        "vign.light": {"file": jsn, "grid_n": 7},
        "vign.tabbea": {"file": jsn},
        "vign.passage_zones": {"file": jsn, "grid_n": 7},
        "vign.real_obscuration": {"file": jsn},
        "tables.taboc1": {"file": jsn, "n_zones": 3},
        "tables.taboc2": {"file": jsn, "n_zones": 3, "num_rays": 10},
        "tables.field_zones": {"n_zones": 3},
        "tables.max_field": {"file": jsn},
    }


def test_every_w3_command_has_smoke(demo_files):
    """Все команды категорий trace/beam/vign/tables покрыты smoke."""
    names = {n for n in default_registry.names()
             if default_registry.get(n).category in W3_CATEGORIES}
    smoke = _smoke_args(demo_files)
    missing = names - set(smoke)
    extra = set(smoke) - names
    assert not missing, f"команды без smoke: {sorted(missing)}"
    assert not extra, f"smoke для несуществующих команд: {sorted(extra)}"
    assert len(names) == 19


def test_smoke_every_w3_command(demo_files):
    """Каждая команда домена выполняется и даёт строгий JSON."""
    smoke = _smoke_args(demo_files)
    ctx = CommandContext()
    for name, args in sorted(smoke.items()):
        result = default_registry.execute(name, ctx, args)
        assert result.ok, f"{name}: {result.error}"
        json.dumps(result.data, ensure_ascii=False, allow_nan=False)


def test_new_categories_registered():
    """Волна 3 расширяет категории реестра (видно в CLI list)."""
    categories = set(default_registry.categories())
    assert W3_CATEGORIES <= categories


# --------------------------------------------------------------------------- #
# trace.* — трассировка
# --------------------------------------------------------------------------- #

class TestTraceRay:
    def test_matches_direct_tracer(self, ctx_clipped):
        """Числа = прямой trace_ray_through_system на той же системе."""
        direct = trace_ray_through_system(
            build_clipped(), Ray(x=0, y=5, z=-25, k=0, l=0, m=1), 0.58756)
        data = run("trace.ray",
                   {"system": "clipped", "y": 5.0, "z": -25.0}, ctx_clipped)
        assert data["success"] == direct.success
        assert data["surfaces_hit"] == direct.surfaces_hit
        assert data["opl"] == pytest.approx(direct.opl)
        assert_points_equal(data["path"], direct.path)

    def test_direction_is_normalized(self, ctx_clipped):
        data = run("trace.ray",
                   {"system": "clipped", "y": 0.0, "z": -10.0,
                    "k": 0.0, "l": 0.0, "m": 7.5}, ctx_clipped)
        assert data["direction"] == pytest.approx([0.0, 0.0, 1.0])

    def test_zero_direction_is_invalid(self, ctx_clipped):
        """Нулевой вектор направления — invalid_param (после resolve)."""
        result = default_registry.execute(
            "trace.ray", ctx_clipped,
            {"system": "clipped", "k": 0, "l": 0, "m": 0})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_no_system_is_error(self):
        result = default_registry.execute(
            "trace.ray", CommandContext(), {})
        assert not result.ok
        assert result.error["code"] == "no_system"

    def test_opj_and_json_sources_agree(self, demo_files):
        jsn, opj = demo_files
        args = {"y": 5.0, "z": -20.0}
        via_json = run("trace.ray", dict(args, file=jsn))
        via_opj = run("trace.ray", dict(args, file=opj))
        assert_points_equal(via_opj["path"], via_json["path"])


class TestTraceGrid3d:
    def test_matches_direct_structure(self, ctx_clipped):
        direct = trace_grid_3d(build_clipped(), num_rings=2,
                               num_azimuths=4, wl=0.58756, field_y=0.0)
        data = run("trace.grid3d",
                   {"system": "clipped", "num_rings": 2,
                    "num_azimuths": 4}, ctx_clipped)
        assert len(data["rings"]) == len(direct) == 2
        # кольцо 0 — центральный луч, кольцо 1 — 4 азимутальных
        assert len(data["rings"][0]) == 1
        assert len(data["rings"][1]) == 4
        assert data["rings"][0][0]["rho"] == pytest.approx(0.0)
        assert data["rings"][1][0]["rho"] == pytest.approx(1.0)
        assert data["rings"][1][1]["phi_deg"] == pytest.approx(90.0)
        for cmd_ray, dir_ray in zip(data["rings"][1], direct[1]):
            assert cmd_ray["success"] == dir_ray.success
            assert cmd_ray["opl"] == pytest.approx(dir_ray.opl)
        # путей нет по умолчанию (компактный ответ), last_point есть
        assert "path" not in data["rings"][1][0]
        assert data["rings"][1][0]["last_point"] == pytest.approx(
            list(direct[1][0].path[-1]))

    def test_include_path(self, ctx_clipped):
        data = run("trace.grid3d",
                   {"system": "clipped", "num_rings": 2,
                    "num_azimuths": 4, "include_path": True}, ctx_clipped)
        assert len(data["rings"][1][0]["path"]) >= 2


class TestTraceFocalSpot:
    def test_matches_direct(self, ctx_clipped):
        direct = get_focal_spot(build_clipped(), wl=0.58756, num_rays=10)
        data = run("trace.focal_spot",
                   {"system": "clipped", "num_rays": 10}, ctx_clipped)
        assert_points_equal(data["spots"], direct)
        assert data["num_points"] == len(direct)


class TestTraceGeometry:
    """Примитивы Снеллиуса — чистая геометрия, без системы."""

    def test_intersect_plane(self):
        data = run("trace.intersect.sphere", {"z": 0.0, "m": 1.0,
                                              "radius": 0.0, "z_surf": 10.0})
        assert data["hit"] == pytest.approx([0.0, 0.0, 10.0])
        assert data["t"] == pytest.approx(10.0)

    def test_intersect_sphere_known_point(self):
        # сфера R=-60: луч y=5 из z=-20 вдоль +z → z ≈ -60+√(60²-5²)
        z_expected = -60.0 + math.sqrt(60.0 ** 2 - 5.0 ** 2)
        data = run("trace.intersect.sphere",
                   {"y": 5.0, "z": -20.0, "m": 1.0,
                    "radius": -60.0, "z_surf": 0.0})
        assert data["hit"] == pytest.approx([0.0, 5.0, z_expected])

    def test_intersect_parallel_to_plane_is_miss(self):
        data = run("trace.intersect.sphere",
                   {"y": 5.0, "z": -20.0, "l": 1.0, "m": 0.0,
                    "radius": 0.0, "z_surf": 10.0})
        assert data["hit"] is None and data["t"] is None

    def test_intersect_aspheric_reduces_to_sphere(self):
        """k=0 без коэффициентов — та же точка, что у сферы."""
        args = {"y": 5.0, "z": -20.0, "m": 1.0, "radius": -60.0,
                "z_surf": 0.0}
        sphere = run("trace.intersect.sphere", args)
        asphere = run("trace.intersect.aspheric", dict(args, conic_k=0.0))
        assert asphere["hit"] == pytest.approx(sphere["hit"])

    def test_intersect_aspheric_coeffs_as_csv(self):
        """CLI-csv список коэффициентов («0,0,-1e-5») приводится к float."""
        data = run("trace.intersect.aspheric",
                   {"y": 5.0, "z": -20.0, "m": 1.0, "radius": -60.0,
                    "z_surf": 0.0, "aspheric_coeffs": "0,0,-0.000001"})
        assert data["hit"] is not None

    def test_normal_vertex_and_unit(self):
        data = run("trace.normal.sphere",
                   {"x": 0.0, "y": 0.0, "z": 0.0, "radius": -60.0})
        assert data["normal"] == pytest.approx([0.0, 0.0, 1.0])
        off = run("trace.normal.sphere",
                  {"x": 0.0, "y": 5.0, "z": -0.2, "radius": -60.0})
        nx, ny, nz = off["normal"]
        assert nx * nx + ny * ny + nz * nz == pytest.approx(1.0)

    def test_normal_aspheric_matches_sphere_when_plain(self):
        args = {"x": 0.0, "y": 5.0, "z": -0.2, "radius": -60.0}
        assert run("trace.normal.aspheric", dict(args, conic_k=0.0))[
            "normal"] == pytest.approx(
            run("trace.normal.sphere", args)["normal"])

    def test_refract_normal_incidence_unchanged(self):
        data = run("trace.refract",
                   {"k": 0.0, "l": 0.0, "m": 1.0,
                    "nx": 0.0, "ny": 0.0, "nz": 1.0,
                    "n1": 1.0, "n2": 1.5163})
        assert data["refracted"] == pytest.approx([0.0, 0.0, 1.0])
        assert not data["tir"]

    def test_refract_tir_from_dense_medium(self):
        """Стекло→воздух за предельным углом — TIR (refracted null)."""
        data = run("trace.refract",
                   {"k": 0.0, "l": 0.8, "m": 0.6,
                    "nx": 0.0, "ny": 0.0, "nz": 1.0,
                    "n1": 1.5, "n2": 1.0})
        assert data["tir"] and data["refracted"] is None


# --------------------------------------------------------------------------- #
# beam.* — TABESB / TABEAP
# --------------------------------------------------------------------------- #

class TestBeamCommands:
    def test_heights_matches_direct(self, ctx_clipped):
        direct = tabesb_rows(build_clipped(), field_y=3.0)
        data = run("beam.heights", {"system": "clipped", "field_y": 3.0},
                   ctx_clipped)
        assert data["rows"] == plain(direct)
        assert data["text"].splitlines()[0].strip() == "Световые высоты"

    def test_heights_row_keys_and_numbers(self, ctx_clipped):
        data = run("beam.heights", {"system": "clipped"}, ctx_clipped)
        first = data["rows"][0]
        assert first["n"] == 1
        for key in ("axial_y", "upper_y", "lower_y", "work_upper_y",
                    "work_lower_y", "aperture_upper", "aperture_lower"):
            assert key in first
        # осевой пучок на 1-й поверхности — высота ≈ половина апертуры D=10
        assert first["axial_y"] == pytest.approx(5.0, abs=0.1)

    def test_screen_zones_matches_direct(self, ctx_clipped):
        direct = tabeap_rows(build_clipped())
        data = run("beam.screen_zones", {"system": "clipped"}, ctx_clipped)
        assert data["rows"] == plain(direct)
        # по строке на поле системы (3 точки поля дублета)
        assert len(data["rows"]) == 3
        assert data["text"].splitlines()[0].strip() == \
            "Экранные зоны (экранирование пучков)"


# --------------------------------------------------------------------------- #
# vign.* — виньетирование / светораспределение / TABBEA
# --------------------------------------------------------------------------- #

class TestVignCompute:
    def test_matches_direct_clipped(self, ctx_clipped):
        direct = compute_vignetting(build_clipped(), 3.0)
        data = run("vign.compute", {"system": "clipped", "field_y": 3.0},
                   ctx_clipped)
        assert data["vignet_up"] == pytest.approx(direct["vignet_up"])
        assert data["vignet_down"] == pytest.approx(direct["vignet_down"])
        assert data["limit_up"] == list(direct["limit_up"]) == ["P", 2]
        assert data["wl"] == pytest.approx(0.58756)

    def test_axial_symmetric_clip(self, ctx_clipped):
        data = run("vign.compute", {"system": "clipped"}, ctx_clipped)
        assert data["vignet_up"] == pytest.approx(data["vignet_down"],
                                                  rel=1e-6)
        assert data["limit_up"] == ["P", 2]


class TestVignLight:
    def test_default_fields_from_system(self, ctx_clipped):
        """Без fields — поля системы (у дублета 3 точки поля)."""
        direct = compute_light_distribution(
            build_clipped(), [0.0, 3.0, 6.0], grid_n=7)
        data = run("vign.light", {"system": "clipped", "grid_n": 7},
                   ctx_clipped)
        assert len(data["fields"]) == 3
        assert data["fields"] == plain(direct)

    def test_obscured_mirror_total(self, ctx_mirror):
        """Экранирование ε=0.3 → светораспределение ≈ 1 − ε².

        Сетка по умолчанию 15 (LIGHT_GRID_N): дискретизация круга даёт
        1−ε² с точностью ~0.01 (как test_vignetting).
        """
        data = run("vign.light", {"system": "mirror"}, ctx_mirror)
        row = data["fields"][0]
        assert row["field_y"] == pytest.approx(0.0)
        assert row["light_total"] == pytest.approx(1 - 0.09, abs=0.01)

    def test_explicit_fields_override(self, ctx_clipped):
        data = run("vign.light",
                   {"system": "clipped", "fields": [0.0, 6.0], "grid_n": 7},
                   ctx_clipped)
        assert [f["field_y"] for f in data["fields"]] == [0.0, 6.0]


class TestVignTabbea:
    def test_matches_direct_rows_and_text(self, ctx_clipped):
        direct = tabbea_rows(build_clipped())
        data = run("vign.tabbea", {"system": "clipped"}, ctx_clipped)
        assert data["rows"] == plain(direct)
        assert "Апертурные" in data["text"]
        # виньетирование строки 2 (поле 3°) срезано поверхностью 2
        assert data["rows"][1]["limit_up"] == ["P", 2]

    def test_fields_param(self, ctx_clipped):
        data = run("vign.tabbea",
                   {"system": "clipped", "fields": [0.0]}, ctx_clipped)
        assert len(data["rows"]) == 1


class TestVignPassageZones:
    def test_matches_direct(self, ctx_clipped):
        direct = find_passage_zones(build_clipped(), 3.0, grid_n=7)
        data = run("vign.passage_zones",
                   {"system": "clipped", "field_y": 3.0, "grid_n": 7},
                   ctx_clipped)
        assert data == plain(direct)
        assert data["n_traced"] > 0
        assert data["surfaces"], "ни одна поверхность не достигнута"

    def test_blocked_here_counts_cutter(self, ctx_clipped):
        """Срезанные кромкой лучи приписаны срезавшей поверхности."""
        data = run("vign.passage_zones",
                   {"system": "clipped", "field_y": 6.0, "grid_n": 9},
                   ctx_clipped)
        by_n = {sf["n"]: sf for sf in data["surfaces"]}
        assert by_n[2]["blocked_here"] > 0
        assert data["vignetted"]


class TestVignRealObscuration:
    def test_matches_direct(self, ctx_mirror):
        # прямая мера: wl=None (модуль кладёт wl как есть); команда
        # передаёт разрешённую основную λ — сверка с подменой этого поля
        direct = real_obscuration(build_mirror(), 0.0, wl=0.58756)
        data = run("vign.real_obscuration",
                   {"system": "mirror"}, ctx_mirror)
        assert data == plain(direct)

    def test_mirror_full_vs_screen_diameters(self, ctx_mirror):
        """D=40, ε=0.3: полный габарит 40, экран ≈ 12, доля ≈ 0.09."""
        data = run("vign.real_obscuration", {"system": "mirror"},
                   ctx_mirror)
        assert data["full_diameter_y"] == pytest.approx(40.0, abs=0.5)
        assert data["screen_diameter_y"] == pytest.approx(12.0, abs=0.5)
        assert data["obscuration_fraction"] == pytest.approx(0.09, abs=0.01)
        assert data["minimal_obscuration"] == pytest.approx(0.3, abs=0.02)


# --------------------------------------------------------------------------- #
# tables.* — TABOC1 / TABOC2 + зоны поля
# --------------------------------------------------------------------------- #

class TestTablesTaboc:
    def test_taboc1_matches_direct(self, ctx_clipped):
        direct = taboc1_rows(build_clipped(), n_zones=3)
        data = run("tables.taboc1",
                   {"system": "clipped", "n_zones": 3}, ctx_clipped)
        assert data["rows"] == plain(direct)
        # n_zones строк + замыкающая осевая из нулей
        assert len(data["rows"]) == 4
        assert data["rows"][-1] == {"zone": 0.0, "longitudinal_mm": 0.0,
                                    "transverse_mer_mm": 0.0,
                                    "transverse_sag_mm": 0.0}
        assert "Продольные аберрации" in data["text"]

    def test_taboc2_matches_direct_and_columns(self, ctx_clipped):
        direct = taboc2_rows(build_clipped(), n_zones=3, num_rays=10)
        data = run("tables.taboc2",
                   {"system": "clipped", "n_zones": 3, "num_rays": 10},
                   ctx_clipped)
        assert data["rows"] == plain(direct)
        assert data["columns"] == ["wave", "iso", "h_zr"]
        assert "Волновые" in data["text"]
        assert data["rows"][-1]["wave"] == pytest.approx(0.0)

    def test_taboc2_custom_columns(self, ctx_clipped):
        data = run("tables.taboc2",
                   {"system": "clipped", "n_zones": 2,
                    "columns": ["z_m", "c_s", "wave"]}, ctx_clipped)
        assert data["columns"] == ["z_m", "c_s", "wave"]
        assert "Z'm" in data["text"] and "C's" in data["text"]

    def test_taboc2_bad_columns(self, ctx_clipped):
        for bad in (["wave", "iso"], ["wave", "iso", "nope"], []):
            result = default_registry.execute(
                "tables.taboc2", ctx_clipped, {"columns": bad})
            assert not result.ok, bad
            assert result.error["code"] == "invalid_param"


class TestTablesHelpers:
    def test_field_zones_sqrt_scheme(self):
        data = run("tables.field_zones", {"n_zones": 3})
        assert data["zones"] == pytest.approx(
            [1.0, math.sqrt(2 / 3), math.sqrt(1 / 3)])
        assert data["zones"] == pytest.approx(field_zones_fn(3))

    def test_max_field_matches_direct(self, ctx_clipped):
        data = run("tables.max_field", {"system": "clipped"}, ctx_clipped)
        assert data["max_field"] == pytest.approx(
            max_field_fn(build_clipped()))


# --------------------------------------------------------------------------- #
# REPL-сценарий: текущая система контекста без явного источника
# --------------------------------------------------------------------------- #

class TestReplCurrentSystem:
    def test_current_system_used_without_file(self, demo_files):
        jsn, _ = demo_files
        ctx = CommandContext()
        assert default_registry.execute(
            "system.load", ctx, {"file": jsn}).ok
        data = run("trace.ray", {"y": 5.0, "z": -20.0}, ctx=ctx)
        assert data["success"] and len(data["path"]) >= 2
        tabbea = run("vign.tabbea", ctx=ctx)
        assert tabbea["rows"]
