# -*- coding: utf-8 -*-
"""Команды R500-17 «хвосты анализа аберраций»
(commands/builtin/aberr_ext_cmds.py): aberx.* — smoke КАЖДОЙ команды
пакета + сверка чисел с прямыми вызовами движков
(analysis.aberrations / domain.calculations / analysis.seidel_check).

Префикс ``aberx`` (не ``aber``): состав домена «АБЕРРАЦИИ» Волны 3
закреплён пином ``tests/test_commands_aber.py`` (``DOMAIN_COMMANDS``,
31 команда с категориями aber/chrom/seidel/adv) — этот модуль держит
СВОЙ набор в категории ``aberx`` и пин Волны 3 не затрагивает (как
``tracex`` в П16).

Демо-система — файлы команд system.new/save (.json; ОПJ-раундтрип
теряет field_points, поэтому все поле-зависимые тесты на .json);
виньетированный дублет — живая система контекста REPL
(``_aberx_clipped``, без смены текущей; drop после теста).
"""
import json
import math

import pytest

from commands import CommandContext, default_registry
from optics_engine import FieldPoint, OpticalSystem, Surface, Wavelength

from analysis.aberrations import compute_field_aberrations
from analysis.aberrations import compute_oblique_fan
from analysis.aberrations import compute_rms_spot_xy
from analysis.aberrations import compute_spot_diagram
from analysis.aberrations import compute_wavefront_rms_vs_field
from fileio.json_io import load_json
from optics_utils import get_primary_wl


# --------------------------------------------------------------------------- #
# Фикстуры и хелперы
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.json, .opj) демо-ахромат, созданный командами Волны 1."""
    tmp = tmp_path_factory.mktemp("commands_r500_17")
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


@pytest.fixture(scope="module")
def system(demo_files):
    """OpticalSystem напрямую из fileio (для паритета с движками)."""
    return load_json(demo_files[0])


def build_clipped() -> OpticalSystem:
    """Дублет с узкой второй поверхностью (semi_diameter S2 = 4 мм).

    Как ``build_clipped`` в test_commands_trace_ext: крайние лучи
    срезаются кромкой S2 — материал для None-строк карт аберраций.
    """
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.aperture_value = 10.0
    s.field_points = [FieldPoint(0.0), FieldPoint(3.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=25),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=4.0),
        Surface(radius=-200, glass='', thickness=70),
    ]
    return s


@pytest.fixture
def ctx_clipped():
    """REPL-контекст с виньетированным дублетом (имя '_aberx_clipped')."""
    ctx = CommandContext()
    ctx.put_system("_aberx_clipped", build_clipped(), make_current=False)
    yield ctx
    ctx.drop_system("_aberx_clipped")


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    # контракт: результат строго JSON-сериализуем
    json.dumps(result.data, ensure_ascii=False, allow_nan=False)
    return result.data


def fail(name, args, code):
    """Выполнить команду, ожидая ошибку с данным кодом."""
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error
    return result.error


# --------------------------------------------------------------------------- #
# Полное покрытие: каждая команда пакета имеет smoke
# --------------------------------------------------------------------------- #

ABERX_CATEGORY = "aberx"


def _smoke_args(demo_files):
    jsn, opj = demo_files
    return {
        "aberx.map.grid": {"file": jsn, "num_rays": 5},
        "aberx.wf.rho": {"file": jsn, "num_rays": 5},
        "aberx.rms.grid": {"file": jsn, "num_rings": 2},
        "aberx.wf.pv": {"file": jsn, "num_rings": 2},
        "aberx.distortion.curve": {"file": jsn, "fit_degree": 3},
        "aberx.astig.curve": {"file": jsn},
        "aberx.petzval.check": {"file": jsn},
        # .opj-раундтрип теряет field_points — в smoke только
        # поле-НЕзависимая команда (параксиал по λ)
        "aberx.chrom.focus_shift": {"file": opj},
        "aberx.chrom.magnification": {"file": jsn},
        "aberx.wf.chrom": {"file": jsn, "field_y": 3.0, "num_rings": 2},
        "aberx.fan.chrom": {"file": jsn, "field_y": 3.0, "num_rays": 5},
        "aberx.spot.grid": {"file": jsn, "num_rays": 9},
        "aberx.centroid.fields": {"file": jsn, "num_rays": 9},
        "aberx.bestfocus.fields": {
            "file": jsn, "num_rays": 9, "num_points": 5,
            "defocus_range": 1.0},
        "aberx.coma.fan": {"file": jsn, "field_y": 3.0, "num_rays": 7},
        "aberx.coma.fields": {"file": jsn, "num_rays": 5},
        "aberx.spherical.zones": {"file": jsn, "num_rays": 9},
        "aberx.aperture.aberrations": {
            "file": jsn, "apertures": [10.0, 20.0], "num_rays": 9},
        "aberx.transverse.zones": {"file": jsn, "field_y": 3.0,
                                   "n_zones": 2},
        "aberx.focal.zonal": {"file": jsn, "field_y": 3.0,
                              "zones": [0.5, 1.0]},
        "aberx.longitudinal.fields": {"file": jsn},
        "aberx.seidel.shares": {"file": jsn},
    }


def test_every_aberx_command_has_smoke(demo_files):
    """Полный набор aberx.* покрыт smoke-аргументами (не больше и не
    меньше), категория всех команд пакета — ``aberx``."""
    names = [n for n in default_registry.names()
             if n.split(".")[0] == ABERX_CATEGORY]
    assert len(names) == 22
    assert all(default_registry.get(n).category == ABERX_CATEGORY
               for n in names)
    smoke = _smoke_args(demo_files)
    assert set(smoke) == set(names)


def test_smoke_every_command(demo_files):
    """Каждая команда пакета выполняется на демо-данных (строгий JSON)."""
    for name, args in sorted(_smoke_args(demo_files).items()):
        run(name, args)


# --------------------------------------------------------------------------- #
# Паритет с движками (обёртка не меняет числа)
# --------------------------------------------------------------------------- #

class TestParity:
    def test_map_grid_matches_oblique_fan(self, demo_files, system):
        """Карта поле×зона == прямые вызовы compute_oblique_fan."""
        jsn, _ = demo_files
        wl = get_primary_wl(system)
        data = run("aberx.map.grid", {"file": jsn, "num_rays": 5})
        rho_ref, dy_mer_ref, _ = compute_oblique_fan(
            system, wl=wl, num_rays=5, field_y=3.0, azimuth_deg=0.0)
        _, _, dy_sag_ref = compute_oblique_fan(
            system, wl=wl, num_rays=5, field_y=3.0, azimuth_deg=90.0)
        rows = [r for r in data["rows"] if r["field_y"] == 3.0]
        assert len(rows) == len(rho_ref)
        for row, r_ref, m_ref, s_ref in zip(rows, rho_ref, dy_mer_ref,
                                            dy_sag_ref):
            assert row["rho"] == pytest.approx(r_ref)
            assert row["dy_mer_um"] == pytest.approx(m_ref)
            assert row["dy_sag_um"] == pytest.approx(s_ref)

    def test_transverse_zones_matches_oblique_fan(self, demo_files,
                                                  system):
        """Таблица зон = oblique_fan мер/саг в тех же точках ρ."""
        jsn, _ = demo_files
        wl = get_primary_wl(system)
        data = run("aberx.transverse.zones", {
            "file": jsn, "field_y": 3.0,
            "zones": [-1.0, -0.5, 0.0, 0.5, 1.0]})
        rho_ref, dy_mer_ref, _ = compute_oblique_fan(
            system, wl=wl, num_rays=5, field_y=3.0, azimuth_deg=0.0)
        _, _, dy_sag_ref = compute_oblique_fan(
            system, wl=wl, num_rays=5, field_y=3.0, azimuth_deg=90.0)
        assert len(data["rows"]) == 5
        for row, r_ref, m_ref, s_ref in zip(data["rows"], rho_ref,
                                            dy_mer_ref, dy_sag_ref):
            assert row["rho"] == pytest.approx(r_ref)
            assert row["dy_mer_um"] == pytest.approx(m_ref, abs=1e-6)
            assert row["dy_sag_um"] == pytest.approx(s_ref, abs=1e-6)

    def test_astig_curve_matches_field_aberrations(self, demo_files,
                                                   system):
        """Z'm−Z's Коддингтона ≈ астигматизм compute_field_aberrations
        (методы разные — след Коддингтона против вееров; допуск 2 %)."""
        jsn, _ = demo_files
        wl = get_primary_wl(system)
        data = run("aberx.astig.curve", {"file": jsn})
        ref = compute_field_aberrations(
            system, wl=wl, field_points=[0.0, 3.0, 5.0], num_fan_rays=15)
        for row, ref_row in zip(data["rows"][1:], ref[1:]):
            assert row["field_y"] == pytest.approx(ref_row["field_y"])
            assert row["astigmatism"] == pytest.approx(
                ref_row["astigmatism"], rel=0.02, abs=1e-3)

    def test_distortion_curve_matches_field_aberrations(
            self, demo_files, system):
        """Дисторсия главного луча == compute_field_aberrations
        (формула y_parax та же — совпадение до машинной точности)."""
        jsn, _ = demo_files
        wl = get_primary_wl(system)
        data = run("aberx.distortion.curve", {"file": jsn})
        ref = compute_field_aberrations(
            system, wl=wl, field_points=[0.0, 3.0, 5.0], num_fan_rays=9)
        for row, ref_row in zip(data["rows"][1:], ref[1:]):
            assert row["dist_pct"] == pytest.approx(ref_row["distortion"],
                                                    rel=1e-9)

    def test_seidel_shares_totals_match_engine(self, demo_files):
        """Сумма пер-поверхностных вкладов == итоги seidel_sums,
        флаг parity_ok поднят."""
        from analysis.seidel_check import seidel_sums
        jsn, _ = demo_files
        data = run("aberx.seidel.shares", {"file": jsn})
        assert data["parity_ok"] is True
        totals = seidel_sums(load_json(jsn))
        for key in ("SI", "SII", "SIII", "SIV", "SV", "SIxp", "SIIxp"):
            got = sum(r[key] for r in data["rows"])
            assert got == pytest.approx(totals[key], abs=1e-12), key
            # доли сходятся в 100 % (по алгебраической сумме)
            shares = [r[f"{key}_share_pct"] for r in data["rows"]
                      if r[f"{key}_share_pct"] is not None]
            assert sum(shares) == pytest.approx(100.0, abs=1e-6), key

    def test_rms_grid_matches_wavefront_rms_vs_field(self, demo_files,
                                                     system):
        """Столбец основной λ == compute_wavefront_rms_vs_field."""
        jsn, _ = demo_files
        wl = get_primary_wl(system)
        data = run("aberx.rms.grid", {"file": jsn, "num_rings": 3})
        fields_ref, rms_ref = compute_wavefront_rms_vs_field(
            system, wl=wl, num_rings=3)
        rows = [r for r in data["rows"] if r["wl"] == pytest.approx(wl)]
        assert len(rows) == len(fields_ref)
        for row, f_ref, v_ref in zip(rows, fields_ref, rms_ref):
            assert row["field_y"] == pytest.approx(f_ref)
            if math.isfinite(v_ref):
                assert row["rms_wl"] == pytest.approx(v_ref)

    def test_spot_grid_matches_rms_spot_xy(self, demo_files, system):
        """RMS-столбцы == прямые вызовы compute_spot_diagram+xy."""
        jsn, _ = demo_files
        wl = get_primary_wl(system)
        data = run("aberx.spot.grid", {"file": jsn, "num_rays": 11})
        spots = compute_spot_diagram(system, wl=wl, num_rays=11,
                                     field_y=3.0)
        xy = compute_rms_spot_xy(spots)
        row = next(r for r in data["rows"]
                   if r["field_y"] == 3.0 and r["wl"] == pytest.approx(wl))
        assert row["rms_total_mm"] == pytest.approx(xy["rms_total"])
        assert row["rms_x_mm"] == pytest.approx(xy["rms_x"])
        assert row["rms_y_mm"] == pytest.approx(xy["rms_y"])

    def test_chrom_focus_shift_matches_paraxial(self, demo_files,
                                                system):
        """BFD строки == domain.paraxial_trace(wl=λ)."""
        from domain.calculations import paraxial_trace
        jsn, _ = demo_files
        data = run("aberx.chrom.focus_shift", {"file": jsn})
        assert data["wl_ref"] == pytest.approx(get_primary_wl(system))
        for row in data["rows"]:
            ref = paraxial_trace(system, wl=row["wl"])
            assert row["bfd_mm"] == pytest.approx(
                ref["back_focal_distance"])
            assert row["efl_mm"] == pytest.approx(ref["focal_length"])
        # основная λ: сдвиги нулевые
        first = data["rows"][0]
        assert first["d_bfd_mm"] == pytest.approx(0.0, abs=1e-12)

    def test_wf_chrom_zero_at_reference(self, demo_files):
        """dW на основной λ тождественно нуль (та же сетка)."""
        jsn, _ = demo_files
        data = run("aberx.wf.chrom", {"file": jsn, "field_y": 3.0,
                                      "num_rings": 2})
        ref_row = next(r for r in data["rows"]
                       if r["wl"] == pytest.approx(data["wl_ref"]))
        assert ref_row["dW_rms"] == pytest.approx(0.0, abs=1e-12)
        assert ref_row["dW_pv"] == pytest.approx(0.0, abs=1e-12)

    def test_coma_fields_edges_consistent(self, demo_files, system):
        """T-кома кривой полей == краевая асимметрия veera (та же
        величина из другого вызова)."""
        jsn, _ = demo_files
        wl = get_primary_wl(system)
        data = run("aberx.coma.fields", {"file": jsn, "num_rays": 7})
        rho, dy_mer, _ = compute_oblique_fan(
            system, wl=wl, num_rays=7, field_y=3.0, azimuth_deg=0.0)
        row = next(r for r in data["rows"] if r["field_y"] == 3.0)
        assert row["t_coma_um"] == pytest.approx(dy_mer[0] + dy_mer[-1])


# --------------------------------------------------------------------------- #
# Инварианты физики
# --------------------------------------------------------------------------- #

class TestPhysics:
    def test_axial_symmetry_map(self, demo_files):
        """Осевое поле: мер. и саг. сечения зеркальны (симметрия)."""
        jsn, _ = demo_files
        data = run("aberx.map.grid", {"file": jsn, "num_rays": 5})
        axial = next(b for b in data["by_field"] if b["field_y"] == 0.0)
        assert axial["rms_dy_mer_um"] == pytest.approx(
            axial["rms_dy_sag_um"], rel=1e-9)
        assert axial["failed_mer"] == 0 and axial["failed_sag"] == 0

    def test_axial_coma_zero(self, demo_files):
        """Осевое поле: кома тождественно нуль (симметрия)."""
        jsn, _ = demo_files
        data = run("aberx.coma.fields", {"file": jsn, "num_rays": 5})
        axial = next(r for r in data["rows"] if r["field_y"] == 0.0)
        assert axial["t_coma_um"] == pytest.approx(0.0, abs=1e-6)

    def test_spherical_zones_symmetric(self, demo_files):
        """Осевой веер: dy нечётна по ρ (dy(−ρ) = −dy(ρ))."""
        jsn, _ = demo_files
        data = run("aberx.spherical.zones", {"file": jsn, "num_rays": 9})
        rows = data["rows"]
        for i in range(len(rows) // 2):
            assert rows[i]["dy_um"] == pytest.approx(
                -rows[-1 - i]["dy_um"], rel=1e-6, abs=1e-6)
        # фазиты: c2 доминирует над c4 у слабо corrig. системы
        fit = data["fit"]
        assert fit is not None and len(fit["coeffs"]) == 3

    def test_petzval_agrees_third_order(self, demo_files):
        """Эмпирический R Петцваля из хода против −1/SIV: третьий
        порядок — расхождение демо-ахромата в единицы %."""
        jsn, _ = demo_files
        data = run("aberx.petzval.check", {"file": jsn})
        assert data["petzval_radius_empirical_mm"] is not None
        assert data["deviation_pct"] == pytest.approx(2.96, rel=0.2)

    def test_bestfocus_rms_leq_zero_plane(self, demo_files):
        """Минимум RMS по дефокусу ≤ RMS в нулевой плоскости."""
        jsn, _ = demo_files
        data = run("aberx.bestfocus.fields", {
            "file": jsn, "num_rays": 9, "num_points": 7,
            "defocus_range": 3.0})
        for row in data["rows"]:
            assert row["min_rms_mm"] <= row["rms_at_zero_mm"] + 1e-12

    def test_focal_zonal_sagittal_symmetric(self, demo_files):
        """Сагиттальные зонные фокусы симметричны: z_s+ = z_s−."""
        jsn, _ = demo_files
        data = run("aberx.focal.zonal", {"file": jsn, "field_y": 3.0,
                                         "zones": [0.5, 1.0]})
        for row in data["rows"]:
            assert row["z_s_plus"] == pytest.approx(row["z_s_minus"],
                                                    abs=1e-6)

    def test_chrom_magnification_monotone_wl(self, demo_files):
        """Хроматизм увеличения растёт с полем (linear color ∝ y)."""
        jsn, _ = demo_files
        data = run("aberx.chrom.magnification", {"file": jsn})
        values = [b["lateral_color_mm"] for b in data["by_field"][1:]]
        assert values == sorted(values)

    def test_wide_aperture_rays_clipped(self, ctx_clipped):
        """Зрачок шире полудиаметров: краевые лучи не доходят —
        None-строки и флаги success=False (контракт краёв)."""
        data = run("aberx.map.grid",
                   {"system": "_aberx_clipped", "num_rays": 5,
                    "fields": [3.0]}, ctx=ctx_clipped)
        axial = data["by_field"][0]
        assert axial["failed_mer"] > 0
        assert any(r["dy_mer_um"] is None for r in data["rows"])


# --------------------------------------------------------------------------- #
# Живые системы контекста и контракты ошибок
# --------------------------------------------------------------------------- #

class TestContextAndErrors:
    def test_live_system_without_file(self, ctx_clipped):
        """Система из контекста REPL (имя, без смены текущей)."""
        run("aberx.astig.curve", {"system": "_aberx_clipped"},
            ctx=ctx_clipped)

    def test_opj_loses_fields_but_explicit_ok(self, demo_files):
        """OPJ-раундтрип теряет field_points: явные fields спасают
        (поле-зависимая команда на .opj с fields)."""
        _, opj = demo_files
        data = run("aberx.astig.curve", {"file": opj,
                                         "fields": [0.0, 3.0]})
        assert [r["field_y"] for r in data["rows"]] == [0.0, 3.0]

    def test_no_fields_error(self, demo_files):
        """Система без точек поля и без fields → invalid_param."""
        _, opj = demo_files
        fail("aberx.astig.curve", {"file": opj}, "invalid_param")

    def test_apertures_empty_error(self, demo_files):
        jsn, _ = demo_files
        fail("aberx.aperture.aberrations",
             {"file": jsn, "apertures": []}, "invalid_param")

    def test_fan_rays_too_few_error(self, demo_files):
        jsn, _ = demo_files
        fail("aberx.coma.fan",
             {"file": jsn, "field_y": 3.0, "num_rays": 2},
             "invalid_param")

    def test_focal_zonal_bad_zones_error(self, demo_files):
        jsn, _ = demo_files
        fail("aberx.focal.zonal",
             {"file": jsn, "field_y": 3.0, "zones": [2.0, -1.0]},
             "invalid_param")
