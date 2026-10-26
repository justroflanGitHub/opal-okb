# -*- coding: utf-8 -*-
"""Команды R500-16 «хвосты трассировки» (commands/builtin/trace_ext_cmds.py):
tracex.* — smoke КАЖДОЙ команды пакета + сверка чисел с прямыми вызовами
движков (analysis.ray_tracing / analysis.aberrations / domain.calculations).

Префикс ``tracex`` (не ``trace``): исчерпывающий набор Волны 3 в категориях
trace/beam/vign/tables закреплён пином ``tests/test_commands_trace.py``
(19 команд) — этот модуль держит СВОЙ набор в категории ``tracex`` и пин
Волны 3 не затрагивает.

Демо-система — файлы команд system.new/save (.json); виньетированный
дублет и зеркало — живые системы контекста REPL (``_tracex_*``, без смены
текущей; drop после теста).
"""
import json
import math

import pytest

from commands import CommandContext, default_registry
from optics_engine import FieldPoint, OpticalSystem, Surface, Wavelength

from analysis.aberrations import _compute_ray_start, _pupil_field_ray
from analysis.aberrations import compute_gauge_rays
from analysis.ray_tracing import Ray, trace_ray_through_system
from analysis.tables import field_zones as field_zones_fn
from optics_utils import get_effective_aperture


# --------------------------------------------------------------------------- #
# Фикстуры
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.json, .opj) демо-ахромат, созданный командами system.new/save."""
    tmp = tmp_path_factory.mktemp("commands_r500_16")
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

    Как ``build_clipped`` в test_commands_trace: на поле 6° лучи срезаются
    кромкой S2 (EDGE) — материал для vignetted.rays/apertures.fill.
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


@pytest.fixture
def ctx_clipped():
    """REPL-контекст с виньетированным дублетом (имя '_tracex_clipped')."""
    ctx = CommandContext()
    ctx.put_system("_tracex_clipped", build_clipped(), make_current=False)
    yield ctx
    ctx.drop_system("_tracex_clipped")


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def assert_points_equal(got, expected):
    """Посегментная сверка списка точек (approx не берёт вложенность)."""
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        assert g == pytest.approx(list(e))


# --------------------------------------------------------------------------- #
# Полное покрытие: каждая команда пакета имеет smoke
# --------------------------------------------------------------------------- #

TRACEX_CATEGORY = "tracex"


def _smoke_args(demo_files):
    jsn, opj = demo_files
    ray = {"x": 0.0, "y": 5.0, "z": -20.0, "k": 0.0, "l": 0.0, "m": 1.0}
    return {
        "tracex.ray.surfaces": {"file": jsn, **ray},
        "tracex.ray.angles": {"file": jsn, **ray},
        "tracex.ray.pupil": {"file": jsn, "field_y": 3.0, "rho_y": 0.7},
        "tracex.ray.multi_wl": {"file": jsn, "rho_y": 0.5},
        "tracex.stop.clearance": {"file": jsn, "rho_y": 0.9},
        "tracex.tir.critical": {"file": jsn},
        "tracex.meridional.table": {"file": jsn, "field_y": 3.0},
        "tracex.opl.table": {"file": jsn},
        "tracex.opl.summary": {"file": jsn, "field_y": 3.0},
        "tracex.apertures.fill": {"file": jsn},
        "tracex.pupils.surfaces": {"file": jsn, "field_y": 3.0},
        "tracex.exit.cone": {"file": jsn},
        "tracex.surface.vertices": {"file": jsn},
        "tracex.surface.glasses": {"file": jsn},
        "tracex.fan.zones": {"file": jsn, "n_zones": 2},
        "tracex.grid.stats": {"file": jsn, "num_rings": 2,
                              "num_azimuths": 4},
        "tracex.vignetted.rays": {"file": jsn, "num_rings": 2,
                                  "num_azimuths": 4},
        "tracex.ynu.table": {"file": jsn},
        "tracex.paraxial.ray": {"file": jsn, "y0": 10.0, "u0": 0.02},
        "tracex.paraxial.matrices": {"file": jsn},
        "tracex.paraxial.invariants": {"file": jsn},
        "tracex.paraxial.gaps": {"file": jsn},
    }


def test_every_tracex_command_has_smoke(demo_files):
    """Все команды категории tracex покрыты smoke (свой набор пакета)."""
    names = {n for n in default_registry.names()
             if default_registry.get(n).category == TRACEX_CATEGORY}
    smoke = _smoke_args(demo_files)
    missing = names - set(smoke)
    extra = set(smoke) - names
    assert not missing, f"команды без smoke: {sorted(missing)}"
    assert not extra, f"smoke для несуществующих команд: {sorted(extra)}"
    assert len(names) == 22


def test_smoke_every_tracex_command(demo_files):
    """Каждая команда пакета выполняется и даёт строгий JSON."""
    smoke = _smoke_args(demo_files)
    ctx = CommandContext()
    for name, args in sorted(smoke.items()):
        result = default_registry.execute(name, ctx, args)
        assert result.ok, f"{name}: {result.error}"
        json.dumps(result.data, ensure_ascii=False, allow_nan=False)


def test_tracex_does_not_touch_w3_pin():
    """Категория tracex не расширяет пин Волны 3 (trace/beam/vign/tables
    остаются ровно 19 — tests/test_commands_trace.py)."""
    w3 = {"trace", "beam", "vign", "tables"}
    names = [n for n in default_registry.names()
             if default_registry.get(n).category in w3]
    assert len(names) == 19


# --------------------------------------------------------------------------- #
# Луч по поверхностям
# --------------------------------------------------------------------------- #

class TestRaySurfaces:
    def test_matches_direct_tracer(self, demo_files):
        """Координаты строк = точкам пути точного трейсера; ОПС в конце —
        opl трейсера (в пределах терминального допуска)."""
        jsn, _ = demo_files
        data = run("tracex.ray.surfaces",
                   {"file": jsn, "y": 5.0, "z": -20.0})
        system = _load_json_system(jsn)
        ray = Ray(x=0, y=5, z=-20, k=0, l=0, m=1)
        direct = trace_ray_through_system(system, ray, 0.54607)
        assert data["success"] == direct.success is True
        assert data["surfaces_hit"] == direct.surfaces_hit == 3
        # точки поверхностей 1..3 = path[1..3] (точек диафрагмы нет)
        for i in range(3):
            assert [data["rows"][i]["x"], data["rows"][i]["y"],
                    data["rows"][i]["z"]] == pytest.approx(
                list(direct.path[i + 1]))
        # ОПС нарастающим итогом: строка последней поверхности — до неё;
        # сегмент до изображения — диагональный (воздух, n=1)
        last_seg = math.dist(direct.path[-2], direct.path[-1])
        assert data["rows"][-1]["opl_cum_mm"] == pytest.approx(
            direct.opl - last_seg, abs=1e-3)
        assert data["opl_total_mm"] == pytest.approx(direct.opl, abs=1e-3)
        assert data["image"] == pytest.approx(list(direct.path[-1]))

    def test_edge_clipped_marks_row(self, ctx_clipped):
        data = run("tracex.ray.surfaces",
                   {"system": "_tracex_clipped", "y": 5.0, "z": -10.0},
                   ctx_clipped)
        assert data["success"] is False
        assert data["error"] == "EDGE"
        assert data["rows"][0].get("clipped") is not True  # S1 пройдена
        assert data["rows"][1].get("clipped") is True      # срезана S2

    def test_zero_direction_is_invalid(self, demo_files):
        jsn, _ = demo_files
        result = default_registry.execute(
            "tracex.ray.surfaces", CommandContext(),
            {"file": jsn, "k": 0, "l": 0, "m": 0})
        assert not result.ok
        assert result.error["code"] == "invalid_param"


class TestRayAngles:
    def test_snell_at_first_surface(self, demo_files):
        """Снеллиус на S1: sin I / sin I' = n1/n2 (воздух → К8)."""
        jsn, _ = demo_files
        data = run("tracex.ray.angles",
                   {"file": jsn, "y": 5.0, "z": -20.0})
        first = data["rows"][0]
        n1, n2 = first["n_before"], first["n_after"]
        assert n1 == pytest.approx(1.0)
        assert n2 == pytest.approx(
            _refr("К8", 0.54607), rel=1e-3)
        ratio = math.sin(math.radians(first["i_deg"])) / \
            math.sin(math.radians(first["t_deg"]))
        assert ratio == pytest.approx(n2 / n1, rel=1e-6)
        # cos I согласован с углом
        assert first["cos_i"] == pytest.approx(
            math.cos(math.radians(first["i_deg"])))
        assert not first["reflective"]

    def test_axial_ray_normal_incidence(self, demo_files):
        """Осевой луч падает нормально на плоскости → I = 0."""
        jsn, _ = demo_files
        data = run("tracex.ray.angles", {"file": jsn, "y": 0.0, "z": -20.0})
        for row in data["rows"]:
            assert row["i_deg"] == pytest.approx(0.0, abs=1e-6)
            assert row["t_deg"] == pytest.approx(0.0, abs=1e-6)


class TestRayPupil:
    def test_matches_direct_builder(self, demo_files):
        """Числа = прямой трассировке построителя _pupil_field_ray."""
        jsn, _ = demo_files
        system = _load_json_system(jsn)
        aperture = get_effective_aperture(system, default=10.0)
        from optics_engine import paraxial_trace
        z_start, z_pupil = _compute_ray_start(system, paraxial_trace(system))
        direct = trace_ray_through_system(
            system,
            _pupil_field_ray(system, 0.0, 0.7 * aperture / 2, 3.0,
                             z_start, z_pupil),
            0.54607)
        data = run("tracex.ray.pupil",
                   {"file": jsn, "field_y": 3.0, "rho_y": 0.7})
        assert data["success"] == direct.success is True
        assert data["opl"] == pytest.approx(direct.opl)
        assert_points_equal(data["path"], direct.path)


class TestRayMultiWl:
    def test_row_per_system_wavelength(self, demo_files):
        jsn, _ = demo_files
        system = _load_json_system(jsn)
        data = run("tracex.ray.multi_wl", {"file": jsn, "rho_y": 0.5})
        assert [r["wl"] for r in data["rows"]] == pytest.approx(
            [float(w.value) for w in system.wavelengths])
        assert all(r["success"] for r in data["rows"])


# --------------------------------------------------------------------------- #
# Диафрагма / ПВО
# --------------------------------------------------------------------------- #

class TestStopClearance:
    def test_pass_and_clip(self, demo_files):
        jsn, _ = demo_files
        ok = run("tracex.stop.clearance", {"file": jsn, "rho_y": 0.9})
        assert ok["r_at_stop"] == pytest.approx(9.0, abs=0.1)
        assert ok["passed"] is True
        assert ok["clearance_mm"] == pytest.approx(
            ok["stop_radius_mm"] - ok["r_at_stop"])
        bad = run("tracex.stop.clearance", {"file": jsn, "rho_y": 1.5})
        assert bad["passed"] is False
        assert bad["clearance_mm"] < 0

    def test_no_stop_is_invalid(self, ctx_clipped):
        """stop_surface вне системы — клиренс не определён."""
        system = build_clipped()
        system.stop_surface = 0
        ctx = CommandContext()
        ctx.put_system("_tracex_nostop", system, make_current=False)
        try:
            result = default_registry.execute(
                "tracex.stop.clearance", ctx, {"system": "_tracex_nostop"})
            assert not result.ok
            assert result.error["code"] == "invalid_param"
        finally:
            ctx.drop_system("_tracex_nostop")


class TestTirCritical:
    def test_glass_to_air_has_critical(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.tir.critical", {"file": jsn})
        first, last = data["rows"][0], data["rows"][-1]
        assert first["n_before"] == pytest.approx(1.0)
        assert first["tir_possible"] is False
        assert first["critical_deg"] is None
        # выход из стекла в воздух: предельный угол ≈ arcsin(1/n)
        assert last["n_before"] > 1.0
        assert last["tir_possible"] is True
        assert last["critical_deg"] == pytest.approx(
            math.degrees(math.asin(last["n_after"] / last["n_before"])),
            rel=1e-9)


# --------------------------------------------------------------------------- #
# Габаритные лучи: таблицы пучка
# --------------------------------------------------------------------------- #

class TestMeridionalTable:
    def test_heights_match_gauge_rays(self, demo_files):
        """Высоты = прямым compute_gauge_rays (разбор пути)."""
        jsn, _ = demo_files
        system = _load_json_system(jsn)
        direct = {r["key"]: r for r in
                  compute_gauge_rays(system, wl=0.54607, field_y=3.0)}
        data = run("tracex.meridional.table",
                   {"file": jsn, "field_y": 3.0})
        first = data["rows"][0]
        assert first["y_upper"] == pytest.approx(
            direct["upper"]["points"][1][1])
        assert first["y_chief"] == pytest.approx(
            direct["chief"]["points"][1][1])
        # высоты есть, углы конечны, полувысота осевого пучка на S1 = D/2
        axial = run("tracex.meridional.table", {"file": jsn})
        semi_s1 = axial["rows"][0]["semi_height"]
        epd = get_effective_aperture(system, default=10.0)
        assert semi_s1 == pytest.approx(epd / 2, abs=0.2)

    def test_image_row_chief(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.meridional.table",
                   {"file": jsn, "field_y": 3.0})
        assert data["image_row"]["y_chief"] == pytest.approx(5.1, abs=0.4)


class TestOplTables:
    def test_opl_table_monotonic_and_total(self, demo_files):
        jsn, _ = demo_files
        system = _load_json_system(jsn)
        data = run("tracex.opl.table", {"file": jsn})
        chief_col = [r["opl_chief"] for r in data["rows"]]
        assert chief_col == sorted(chief_col)       # нарастающий итог
        direct = {r["key"]: r for r in
                  compute_gauge_rays(system, wl=0.54607, field_y=0.0)}
        # строка последней поверхности — ОПС ДО неё; сегмент до
        # изображения — диагональный (воздух, n=1) — сверх
        chief_pts = direct["chief"]["points"]
        last_seg = math.dist(chief_pts[-2], chief_pts[-1])
        assert chief_col[-1] + last_seg == pytest.approx(
            direct["chief"]["opl"], abs=1e-3)
        assert data["keys"] == ["upper", "lower", "chief",
                                "sag_plus", "sag_minus"]

    def test_opl_summary_chief_zero(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.opl.summary", {"file": jsn, "field_y": 3.0})
        chief = next(r for r in data["rays"] if r["key"] == "chief")
        assert chief["d_opl_mm"] == pytest.approx(0.0)
        assert chief["d_opl_waves"] == pytest.approx(0.0)
        assert data["opd_spread_mm"] > 0


class TestAperturesFill:
    def test_violation_on_clipped(self, ctx_clipped):
        """На поле 6° кромка S2 (sd=4) срезает пучок — заполнение > 1."""
        data = run("tracex.apertures.fill",
                   {"system": "_tracex_clipped", "field_y": 6.0},
                   ctx_clipped)
        row2 = data["rows"][1]
        assert row2["semi_diameter"] == pytest.approx(4.0)
        assert row2["violation"] is True
        assert row2["fill_fraction"] > 1.0

    def test_axial_fits(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.apertures.fill", {"file": jsn})
        assert all(not r["violation"] for r in data["rows"])


class TestPupilsSurfaces:
    def test_stop_at_first_surface(self, demo_files):
        """Диафрагма на S1: dz_to_entrance у S1 = 0 (sP = 0), центр
        зрачка на S1 = высота главного луча."""
        jsn, _ = demo_files
        data = run("tracex.pupils.surfaces",
                   {"file": jsn, "field_y": 3.0})
        first = data["rows"][0]
        assert first["dz_to_entrance"] == pytest.approx(
            -data["entrance_pupil_z"])
        assert first["pupil_center_y"] == pytest.approx(
            first["semi_height_up"] + first["semi_height_low"], abs=0.6)
        assert data["epd_mm"] == pytest.approx(20.0)


class TestExitCone:
    def test_f_number_close_to_paraxial(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.exit.cone", {"file": jsn})
        assert data["half_angle_deg"] > 0
        assert data["f_number_real"] == pytest.approx(
            data["f_number_paraxial"], rel=0.05)
        assert data["na_prime"] == pytest.approx(
            math.sin(math.radians(data["half_angle_deg"])), rel=1e-9)


# --------------------------------------------------------------------------- #
# Поверхности / среды
# --------------------------------------------------------------------------- #

class TestSurfaceTables:
    def test_vertices_cumulative(self, demo_files):
        jsn, _ = demo_files
        system = _load_json_system(jsn)
        data = run("tracex.surface.vertices", {"file": jsn})
        zs = [r["z_vertex"] for r in data["rows"]]
        assert zs[0] == pytest.approx(0.0)
        assert data["total_track_mm"] == pytest.approx(
            sum(s.thickness for s in system.surfaces))
        assert data["rows"][0]["dz_to_next"] == pytest.approx(
            system.surfaces[0].thickness)
        assert data["rows"][0]["glass"] == "К8"

    def test_glasses_refraction_media(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.surface.glasses", {"file": jsn})
        rows = data["rows"]
        assert rows[0]["n_before"] == pytest.approx(1.0)
        assert rows[0]["n_after"] == pytest.approx(
            _refr("К8", 0.54607), rel=1e-3)
        assert rows[-1]["n_after"] == pytest.approx(1.0)   # воздух
        assert data["image_space_n"] == pytest.approx(1.0)
        assert rows[0]["dn"] == pytest.approx(rows[0]["n_after"] - 1.0)


# --------------------------------------------------------------------------- #
# Сетки и веера
# --------------------------------------------------------------------------- #

class TestFanZones:
    def test_default_zones_equal_area(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.fan.zones", {"file": jsn, "n_zones": 2})
        expected = sorted({0.0} | set(field_zones_fn(2)))
        assert [r["rho"] for r in data["zones"]] == pytest.approx(expected)
        assert data["zones"][0]["dy_vs_chief"] == pytest.approx(0.0,
                                                                abs=1e-9)

    def test_explicit_zones(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.fan.zones",
                   {"file": jsn, "zones": [0, 0.5, -1.0]})
        assert [r["rho"] for r in data["zones"]] == pytest.approx(
            [-1.0, 0.0, 0.5])


class TestGridStats:
    def test_counts_total_rays(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.grid.stats",
                   {"file": jsn, "num_rings": 2, "num_azimuths": 4})
        # центральный + (num_rings−1)×num_azimuths
        assert data["total"] == 1 + 1 * 4
        assert data["success"] == data["total"]
        assert data["failed"] == 0
        assert data["opl_min"] <= data["opl_mean"] <= data["opl_max"]

    def test_clipped_field_fails(self, ctx_clipped):
        data = run("tracex.grid.stats",
                   {"system": "_tracex_clipped", "field_y": 6.0,
                    "num_rings": 2, "num_azimuths": 4}, ctx_clipped)
        assert data["failed"] > 0
        assert data["by_error"]


class TestVignettedRays:
    def test_clipped_lists_edge_rays(self, ctx_clipped):
        data = run("tracex.vignetted.rays",
                   {"system": "_tracex_clipped", "field_y": 6.0,
                    "num_rings": 2, "num_azimuths": 4}, ctx_clipped)
        assert data["failed"] > 0
        assert all(r["error"] for r in data["rays"])
        assert all(r["rho"] > 0 for r in data["rays"])  # центр прошёл


# --------------------------------------------------------------------------- #
# Параксиальные хвосты
# --------------------------------------------------------------------------- #

class TestYnuTable:
    def test_marginal_nu_gives_efl(self, demo_files):
        """C = (nu)_кр после последней поверхности → efl = −1/C (как
        paraxial_trace)."""
        jsn, _ = demo_files
        data = run("tracex.ynu.table", {"file": jsn})
        nu_last = data["rows"][-1]["nu_marginal"]
        assert -1.0 / nu_last == pytest.approx(data["efl"], rel=1e-9)
        assert len(data["rows"]) == 3
        assert data["rows"][0]["y_marginal"] == pytest.approx(1.0)

    def test_opj_and_json_agree(self, demo_files):
        jsn, opj = demo_files
        via_json = run("tracex.ynu.table", {"file": jsn})
        via_opj = run("tracex.ynu.table", {"file": opj})
        assert via_json["rows"] == pytest.approx(via_opj["rows"])


class TestParaxialRay:
    def test_axial_ray_stays_on_axis(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.paraxial.ray",
                   {"file": jsn, "y0": 0.0, "u0": 0.0})
        assert all(r["y"] == pytest.approx(0.0) for r in data["rows"])
        assert data["image_y"] == pytest.approx(0.0)

    def test_matches_ynu_marginal_basis(self, demo_files):
        """y0=1, u0=0 — ровно крайевой базисный луч ynu-таблицы."""
        jsn, _ = demo_files
        ynu = run("tracex.ynu.table", {"file": jsn})
        ray = run("tracex.paraxial.ray", {"file": jsn})
        for r_ynu, r_ray in zip(ynu["rows"], ray["rows"]):
            assert r_ray["y"] == pytest.approx(r_ynu["y_marginal"])
            assert r_ray["nu_after"] == pytest.approx(r_ynu["nu_marginal"])


class TestParaxialMatrices:
    def test_det_and_efl(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.paraxial.matrices", {"file": jsn})
        (a, b), (c, d) = data["system_ABCD"]
        assert a * d - b * c == pytest.approx(1.0)
        assert data["det"] == pytest.approx(1.0)
        assert data["efl_from_matrix"] == pytest.approx(
            data["efl_paraxial"], rel=1e-9)
        # матрицы поверхностей/промежутков согласованы по числу
        assert len(data["surfaces"]) == 3
        assert data["surfaces"][0]["M"] == [[1.0, 0.0],
                                            [-data["surfaces"][0]["phi"],
                                             1.0]]

    def test_mirror_system(self, ctx_clipped):
        """Зеркало не даёт промежутка с изменением знака det."""
        system = OpticalSystem()
        system.wavelengths = [Wavelength(value=0.58756)]
        system.aperture_value = 40.0
        system.surfaces = [Surface(radius=-400, glass='', thickness=-200,
                                   is_reflective=True,
                                   semi_diameter=25.0)]
        ctx = CommandContext()
        ctx.put_system("_tracex_mirror", system, make_current=False)
        try:
            data = run("tracex.paraxial.matrices",
                       {"system": "_tracex_mirror"}, ctx)
            assert data["surfaces"][0]["kind"] == "reflect"
            assert data["det"] == pytest.approx(1.0)
            assert data["efl_from_matrix"] == pytest.approx(
                data["efl_paraxial"], rel=1e-9)
        finally:
            ctx.drop_system("_tracex_mirror")


class TestParaxialInvariants:
    def test_h_is_constant(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.paraxial.invariants", {"file": jsn})
        assert len(data["rows"]) == 4            # промежутки 0..ns
        assert data["drift"] == pytest.approx(0.0, abs=1e-9)
        # базис (y=1,nu=0)/(y=0,nu=1): H = 0·0 − 1·1 = −1
        assert data["H_min"] == pytest.approx(-1.0)


class TestParaxialGaps:
    def test_scaled_to_real_pupil(self, demo_files):
        jsn, _ = demo_files
        data = run("tracex.paraxial.gaps", {"file": jsn})
        # диафрагма на S1: базисный луч y=1 в её плоскости → масштаб =
        # epd/2 = 10 мм; полувысота на S1 = 10
        assert data["scale_mm"] == pytest.approx(10.0)
        first = data["rows"][0]
        assert first["y_start"] == pytest.approx(10.0)
        assert len(data["rows"]) == 3


# --------------------------------------------------------------------------- #
# REPL-сценарий: текущая система контекста без явного источника
# --------------------------------------------------------------------------- #

class TestReplCurrentSystem:
    def test_current_system_used_without_file(self, demo_files):
        jsn, _ = demo_files
        ctx = CommandContext()
        assert default_registry.execute(
            "system.load", ctx, {"file": jsn}).ok
        data = run("tracex.ray.pupil", {"rho_y": 0.5}, ctx=ctx)
        assert data["success"] and len(data["path"]) >= 2
        assert run("tracex.ynu.table", ctx=ctx)["rows"]


# --------------------------------------------------------------------------- #
# Хелперы прямых вызовов
# --------------------------------------------------------------------------- #

def _load_json_system(path):
    """Загрузка системы напрямую (fileio) — для сверок с движками."""
    from fileio.json_io import load_json
    return load_json(path)


def _refr(glass: str, wl: float) -> float:
    """n стекла напрямую (domain.calculations.refractive_index)."""
    from domain.calculations import refractive_index
    return refractive_index(glass, wl)
