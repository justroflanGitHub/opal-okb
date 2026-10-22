"""Команды Волны 3, домен «АБЕРРАЦИИ»: aber.* / chrom.* / seidel.* / adv.*

Демо-система — системными командами реестра (system.new achromat + save),
как в tests/test_commands_builtin.py. Реестр — изолированный экземпляр
(builtin Волны 1 + aber_cmds), чтобы не менять ``default_registry``:
``commands/builtin/__init__.py`` собирает координатор после мержа веток.

Сверка команд с прямыми вызовами analysis/* — обёртка не меняет числа.
"""
import json
import math
from pathlib import Path

import pytest

from commands import CommandContext
from commands.registry import Registry
from commands.builtin import register_builtin
from commands.builtin import aber_cmds
from fileio.json_io import load_json
from optics_utils import get_primary_wl


# --------------------------------------------------------------------------- #
# Реестр: builtin Волны 1 + команды домена (без default_registry)
# --------------------------------------------------------------------------- #

#: Все команды домена (имя → категория). 31 команда Волны 3.
DOMAIN_COMMANDS = {
    # aber.* — analysis/aberrations.py
    "aber.fan": "aber",
    "aber.chief": "aber",
    "aber.focus_curve": "aber",
    "aber.spot_poly": "aber",
    "aber.rms_poly": "aber",
    "aber.spot_heatmap": "aber",
    "aber.mtf_geo": "aber",
    "aber.spot_defocus": "aber",
    "aber.focus_diagrams": "aber",
    "aber.isoplanatism": "aber",
    "aber.oblique_fan": "aber",
    "aber.gauge_rays": "aber",
    "aber.ray_coordinates": "aber",
    "aber.fields": "aber",
    "aber.wavefront": "aber",
    "aber.wavefront_rms": "aber",
    "aber.coddington": "aber",
    "aber.caustic": "aber",
    # chrom.* — analysis/chromatism.py
    "chrom.opal": "chrom",
    # seidel.* — analysis/seidel_check.py
    "seidel.sums": "seidel",
    "seidel.check_tracing": "seidel",
    "seidel.vs_golden": "seidel",
    "seidel.parse_prn": "seidel",
    # adv.* — analysis/advanced.py
    "adv.psf": "adv",
    "adv.lsf": "adv",
    "adv.enc": "adv",
    "adv.ptf": "adv",
    "adv.bar_image": "adv",
    "adv.bar_mtf": "adv",
    "adv.esf": "adv",
    "adv.object_image": "adv",
}

#: Команда-маркер домена (регистрация aber_cmds уже выполнена).
_DOMAIN_MARK = "aber.fan"


@pytest.fixture(scope="module")
def registry():
    """Изолированный реестр: builtin Волны 1 + aber_cmds (без мержа)."""
    reg = Registry()
    register_builtin(reg)
    if not reg.has(_DOMAIN_MARK):
        aber_cmds.register(reg)
    return reg


@pytest.fixture(scope="module")
def demo_files(registry, tmp_path_factory):
    """(.opj, .json) демо-ахромат, созданный командами system.new/save."""
    tmp = tmp_path_factory.mktemp("commands_w3_aber")
    opj = str(tmp / "demo_achromat.opj")
    jsn = str(tmp / "demo_achromat.json")
    ctx = CommandContext()
    res = registry.execute("system.new", ctx,
                           {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    res = registry.execute("file.save", ctx, {"src": jsn, "file": opj})
    assert res.ok, res.error
    return opj, jsn


@pytest.fixture(scope="module")
def prn_empty(tmp_path_factory):
    """.PRN без секции сумм Зейделя (все эталоны репозитория такие)."""
    path = tmp_path_factory.mktemp("commands_w3_aber") / "empty.PRN"
    path.write_bytes("ОТЧЁТ OPAL-PC\n     (секции sumsed нет)\n".encode("cp866"))
    return str(path)


@pytest.fixture
def ctx(registry, demo_files):
    """Контекст REPL с загруженной демо-системой (текущая)."""
    opj, _ = demo_files
    context = CommandContext()
    res = registry.execute("system.load", context,
                           {"file": opj, "name": "demo"})
    assert res.ok, res.error
    return context


def run(registry, name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = registry.execute(name, ctx or CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    # контракт: результат строго JSON-сериализуем
    json.dumps(result.data, ensure_ascii=False, allow_nan=False)
    return result.data


def _write_prn(path, rows):
    """Fabricated .PRN со строками sumsed: ' ' + I3 + 5×F11.5 + 2×F10.5."""
    lines = ["ОТЧЁТ OPAL-PC (секция сумм Зейделя)"]
    for n, vals in rows:
        line = (f" {n:>3d}"
                + "".join(f"{v:>11.5f}" for v in vals[:5])
                + "".join(f"{v:>10.5f}" for v in vals[5:7]))
        assert len(line) >= 69
        lines.append(line)
    Path(path).write_bytes("\n".join(lines).encode("cp866"))


# --------------------------------------------------------------------------- #
# Реестр и smoke-покрытие
# --------------------------------------------------------------------------- #

def test_domain_commands_registered(registry):
    """Все 31 команда домена зарегистрированы, категории верные,
    имена Wave 1 не тронуты (32 builtin + 31 = 63)."""
    for name, category in DOMAIN_COMMANDS.items():
        assert registry.has(name), name
        assert registry.get(name).category == category, name
    assert len(registry.names()) == 32 + len(DOMAIN_COMMANDS)


def test_default_registry_untouched(registry):
    """Изолированная регистрация: default_registry без команд домена
    (до мержа; тесты Волны 1 не должны видеть aber.*)."""
    from commands import default_registry
    assert not default_registry.has(_DOMAIN_MARK)


def _smoke_args(demo_files, prn_empty):
    _, jsn = demo_files
    return {
        "aber.fan": {"file": jsn, "num_rays": 5},
        "aber.chief": {"file": jsn},
        "aber.focus_curve": {"file": jsn, "num_points": 7, "num_rays": 10},
        "aber.spot_poly": {"file": jsn, "num_rays": 10},
        "aber.rms_poly": {"file": jsn, "num_rays": 10},
        "aber.spot_heatmap": {"file": jsn, "num_rays": 200, "grid_size": 25},
        "aber.mtf_geo": {"file": jsn, "num_freqs": 5},
        "aber.spot_defocus": {"file": jsn, "num_rays": 20,
                              "defocus_mm": -0.2},
        "aber.focus_diagrams": {"file": jsn, "num_rays": 20},
        "aber.isoplanatism": {"file": jsn, "num_rays": 9},
        "aber.oblique_fan": {"file": jsn, "num_rays": 7},
        "aber.gauge_rays": {"file": jsn, "field_y": 3.0},
        "aber.ray_coordinates": {"file": jsn, "field_y": 3.0},
        "aber.fields": {"file": jsn},
        "aber.wavefront": {"file": jsn, "num_rings": 2},
        "aber.wavefront_rms": {"file": jsn, "num_rings": 2},
        "aber.coddington": {"file": jsn, "field_y": 3.0},
        "aber.caustic": {"file": jsn, "field_y": 3.0},
        "chrom.opal": {"file": jsn},
        "seidel.sums": {"file": jsn},
        "seidel.check_tracing": {"file": jsn, "field_y": 3.0},
        "seidel.vs_golden": {"file": jsn, "prn": prn_empty},
        "seidel.parse_prn": {"prn": prn_empty},
        "adv.psf": {"file": jsn, "num_rays": 32},
        "adv.lsf": {"file": jsn, "num_rays": 32},
        "adv.enc": {"file": jsn, "num_rays": 40},
        "adv.ptf": {"file": jsn, "num_rays": 32},
        "adv.bar_image": {"file": jsn},
        "adv.bar_mtf": {"file": jsn, "freq_list": [10]},
        "adv.esf": {"file": jsn},
        "adv.object_image": {"file": jsn, "num_rays": 32},
    }


def test_smoke_every_command(registry, demo_files, prn_empty):
    """Каждая команда домена выполняется на демо-данных без ошибки."""
    smoke = _smoke_args(demo_files, prn_empty)
    assert set(smoke) == set(DOMAIN_COMMANDS)
    for name, args in sorted(smoke.items()):
        run(registry, name, args)


# --------------------------------------------------------------------------- #
# aber.* — сверки с прямыми вызовами analysis/aberrations.py
# --------------------------------------------------------------------------- #

class TestAberCommands:
    def test_fan_matches_direct(self, registry, demo_files):
        from analysis.aberrations import trace_aberration_fan
        _, jsn = demo_files
        system = load_json(jsn)
        direct = trace_aberration_fan(system, wl=get_primary_wl(system),
                                      num_rays=9, field_y=3.0)
        data = run(registry, "aber.fan",
                   {"file": jsn, "num_rays": 9, "field_y": 3.0})
        assert data["rays"] == direct
        assert data["wl"] == pytest.approx(get_primary_wl(system))
        ok_rows = [r for r in data["rays"] if r["success"]]
        assert ok_rows, "все лучи веера упали"

    def test_fan_from_opj_same_as_json(self, registry, demo_files):
        opj, jsn = demo_files
        via_opj = run(registry, "aber.fan", {"file": opj, "num_rays": 5})
        via_json = run(registry, "aber.fan", {"file": jsn, "num_rays": 5})
        assert via_opj["rays"] == pytest.approx(via_json["rays"])

    def test_chief_rows_by_fields(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.chief", {"file": jsn})
        assert [r["field_y"] for r in data["rows"]] == [0.0, 3.0, 5.0]
        assert data["rows"][0]["distortion_rel"] == 0.0
        assert data["rows"][2]["distortion_abs"] != 0.0

    def test_focus_curve_shape(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.focus_curve",
                   {"file": jsn, "num_points": 7, "num_rays": 10})
        assert len(data["curve"]) == 7
        assert all(0.0 <= m <= 1.0 for _, m in data["curve"])
        assert data["curve"][0][0] == pytest.approx(-data["defocus_range"])

    def test_spot_poly_wavelength_indices(self, registry, demo_files):
        _, jsn = demo_files
        system = load_json(jsn)
        data = run(registry, "aber.spot_poly",
                   {"file": jsn, "num_rays": 10})
        assert data["wavelengths"] == pytest.approx(
            [w.value for w in system.wavelengths])
        assert {p[2] for p in data["spots"]} <= set(range(len(data["wavelengths"])))

    def test_rms_poly_matches_direct(self, registry, demo_files):
        from analysis.aberrations import compute_polychromatic_rms
        _, jsn = demo_files
        direct = compute_polychromatic_rms(load_json(jsn), num_rays=10)
        data = run(registry, "aber.rms_poly",
                   {"file": jsn, "num_rays": 10})
        assert data["rms"] == pytest.approx(direct)
        assert data["rms"] > 0.0

    def test_spot_heatmap_scalars_and_grid(self, registry, demo_files):
        _, jsn = demo_files
        scalars = run(registry, "aber.spot_heatmap",
                      {"file": jsn, "num_rays": 200, "grid_size": 25})
        assert "heatmap" not in scalars  # решётка по умолчанию выключена
        assert 0.0 < scalars["fill"] <= 1.0
        assert scalars["x_range"][0] < scalars["x_range"][1]
        grid = run(registry, "aber.spot_heatmap",
                   {"file": jsn, "num_rays": 200, "grid_size": 25,
                    "include_grid": True})
        assert len(grid["heatmap"]) == 25
        assert max(max(row) for row in grid["heatmap"]) == pytest.approx(1.0)
        assert grid["filled_cells"] == sum(
            1 for row in grid["heatmap"] for v in row if v > 0)

    def test_mtf_geo_shape(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.mtf_geo",
                   {"file": jsn, "num_freqs": 5, "max_freq": 50})
        assert data["mtf"][0] == pytest.approx([0.0, 1.0, 1.0])
        assert len(data["mtf"]) == 6
        assert all(0.0 <= t <= 1.0 and 0.0 <= s <= 1.0
                   for _, t, s in data["mtf"])

    def test_spot_defocus_matches_direct(self, registry, demo_files):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram_at_defocus,
        )
        _, jsn = demo_files
        direct = compute_spot_diagram_at_defocus(
            load_json(jsn), wl=get_primary_wl(load_json(jsn)),
            num_rays=20, field_y=3.0, defocus_mm=-0.2)
        data = run(registry, "aber.spot_defocus",
                   {"file": jsn, "num_rays": 20, "field_y": 3.0,
                    "defocus_mm": -0.2})
        assert data["spots"] == [list(p) for p in direct]
        assert data["rms"] == pytest.approx(compute_rms_spot(direct))

    def test_focus_diagrams_labels_and_rms(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.focus_diagrams",
                   {"file": jsn, "num_rays": 20})
        assert set(data["diagrams"]) == {"номинал", "+DS'", "-DS'",
                                         "+2DS'", "-2DS'"}
        assert all("spots" not in d for d in data["diagrams"].values())
        assert data["diagrams"]["номинал"]["defocus_mm"] == 0.0
        with_spots = run(registry, "aber.focus_diagrams",
                         {"file": jsn, "num_rays": 20, "include_spots": True})
        assert with_spots["diagrams"]["+DS'"]["spots"]

    def test_isoplanatism_lists(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.isoplanatism",
                   {"file": jsn, "num_rays": 9})
        assert len(data["pupil"]) == len(data["eta"]) == 9
        assert data["eta"][len(data["eta"]) // 2] == pytest.approx(
            0.0, abs=1e-6)  # центр зрачка — ноль по построению

    def test_oblique_fan_azimuth(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.oblique_fan",
                   {"file": jsn, "num_rays": 7, "azimuth_deg": 405.0})
        assert data["azimuth_deg"] == pytest.approx(45.0)  # 405 → 45
        assert len(data["pupil"]) == 7

    def test_gauge_rays_keys(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.gauge_rays",
                   {"file": jsn, "field_y": 3.0})
        assert [r["key"] for r in data["rays"]] == [
            "upper", "lower", "chief", "sag_plus", "sag_minus"]
        upper = data["rays"][0]
        assert upper["success"]
        assert len(upper["points"]) == len(upper["segment_lengths"]) + 1
        assert upper["path_length"] == pytest.approx(
            sum(upper["segment_lengths"]))

    def test_ray_coordinates_rows(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.ray_coordinates",
                   {"file": jsn, "field_y": 3.0})
        # 3 поверхности + плоскость изображения (+ старт у трейсера)
        assert len(data["rows"]) >= 4
        assert data["rows"][1]["y_upper"] is not None

    def test_fields_sampling(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "aber.fields", {"file": jsn})
        assert data["fields"] == [0.0, 3.0, 5.0]

    def test_wavefront_hexapolar(self, registry, demo_files):
        from analysis.aberrations import trace_wavefront_hexapolar
        _, jsn = demo_files
        system = load_json(jsn)
        direct = trace_wavefront_hexapolar(system, field_y=3.0, num_rings=2)
        data = run(registry, "aber.wavefront",
                   {"file": jsn, "field_y": 3.0, "num_rings": 2})
        assert data["points"] == [list(p) for p in direct]
        assert len(data["points"]) == 1 + 6 * (1 + 2)  # 2 кольца → 19

    def test_wavefront_rms_matches_direct(self, registry, demo_files):
        from analysis.aberrations import compute_wavefront_rms_vs_field
        _, jsn = demo_files
        fields, rms = compute_wavefront_rms_vs_field(load_json(jsn),
                                                     num_rings=2)
        data = run(registry, "aber.wavefront_rms",
                   {"file": jsn, "num_rings": 2})
        assert data["fields"] == pytest.approx(list(fields))
        assert data["rms"] == pytest.approx(list(rms))

    def test_coddington_matches_direct(self, registry, demo_files):
        from analysis.aberrations import coddington_trace
        _, jsn = demo_files
        direct = coddington_trace(load_json(jsn), field_y=3.0)
        data = run(registry, "aber.coddington",
                   {"file": jsn, "field_y": 3.0})
        for key in ("z_m", "z_s", "delta_zm", "delta_zs", "astigmatism"):
            assert data[key] == pytest.approx(direct[key]), key

    def test_caustic_radii(self, registry, demo_files):
        from analysis.aberrations import caustic_radii
        _, jsn = demo_files
        direct = caustic_radii(load_json(jsn), field_y=3.0)
        data = run(registry, "aber.caustic",
                   {"file": jsn, "field_y": 3.0})
        assert data["r_m"] == pytest.approx(direct["r_m"])
        assert data["method"] == direct["method"]
        assert data["r_m_rel"] is not None

    def test_fan_no_system_error(self, registry):
        result = registry.execute("aber.fan", CommandContext(), {})
        assert not result.ok
        assert result.error["code"] == "no_system"


# --------------------------------------------------------------------------- #
# chrom.* — analysis/chromatism.py
# --------------------------------------------------------------------------- #

class TestChromCommands:
    def test_opal_fallback_matches_direct(self, registry, demo_files):
        from analysis.chromatism import compute_chromatism_opal, format_tabax3
        _, jsn = demo_files
        direct = compute_chromatism_opal(load_json(jsn))
        data = run(registry, "chrom.opal", {"file": jsn})
        assert data["mode"] == "fallback" == direct["mode"]
        assert data["rows"] == direct["rows"]
        assert data["text"] == format_tabax3(direct)
        assert data["wl_main"] == pytest.approx(direct["wl_main"])

    def test_opal_per_surface_flags(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "chrom.opal",
                   {"file": jsn, "wl_flags": [0, 0.65627, 0]})
        assert data["mode"] == "per_surface"
        assert data["rows"][0]["surface"] == 1
        assert data["rows"][0]["wl"] == pytest.approx(0.65627)

    def test_opal_flags_from_cli_strings(self, registry, demo_files):
        """CLI передаёт list строкой: '0,0.65627,0' — нормализация в обёртке."""
        _, jsn = demo_files
        via_str = run(registry, "chrom.opal",
                      {"file": jsn, "wl_flags": "0,0.65627,0"})
        via_list = run(registry, "chrom.opal",
                       {"file": jsn, "wl_flags": [0, 0.65627, 0]})
        assert via_str["rows"] == via_list["rows"]

    def test_opal_repl_current_system(self, registry, ctx):
        data = run(registry, "chrom.opal", {}, ctx=ctx)
        assert data["mode"] == "fallback"
        assert len(data["rows"]) == 2  # F'/C' пары к основной λ


# --------------------------------------------------------------------------- #
# seidel.* — analysis/seidel_check.py
# --------------------------------------------------------------------------- #

class TestSeidelCommands:
    def test_sums_matches_direct_and_domain_parity(self, registry, demo_files):
        from analysis.seidel_check import seidel_sums
        from domain.calculations import seidel_aberrations
        _, jsn = demo_files
        system = load_json(jsn)
        data = run(registry, "seidel.sums", {"file": jsn})
        direct = seidel_sums(system)
        assert data == pytest.approx(direct)
        # паритет SI..SV с calc.seidel Волны 1 (независимая реализация)
        wave1 = registry.execute("calc.seidel", CommandContext(),
                                 {"file": jsn})
        assert wave1.ok
        for key, value in wave1.data.items():
            assert data[key] == pytest.approx(value), key
        # хроматические суммы — только здесь (в domain их нет)
        assert data["chromatic"] is True
        assert set(data) >= {"SIxp", "SIIxp", "wl_lo", "wl_hi"}

    def test_check_tracing_keys(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "seidel.check_tracing",
                   {"file": jsn, "field_y": 3.0})
        for key in ("sums", "axial", "field", "chromatic", "signs",
                    "orders"):
            assert key in data
        assert set(data["signs"]) == {"SI_c3", "SII_a2", "SIII_astig",
                                      "SV_a0", "SIxp_df"}

    def test_check_tracing_field_required(self, registry, demo_files):
        _, jsn = demo_files
        result = registry.execute("seidel.check_tracing", CommandContext(),
                                  {"file": jsn})
        assert not result.ok
        assert result.error["code"] == "missing_param"

    def test_vs_golden_skipped_without_section(self, registry, demo_files,
                                               prn_empty):
        _, jsn = demo_files
        data = run(registry, "seidel.vs_golden",
                   {"file": jsn, "prn": prn_empty})
        assert data["status"] == "skipped"
        assert "sumsed" in data["reason"]

    def test_vs_golden_matched(self, registry, demo_files, tmp_path):
        """Golden = суммы порта ×10 (инвариант отношений) → matched."""
        from analysis.seidel_check import seidel_sums
        _, jsn = demo_files
        sums = seidel_sums(load_json(jsn))
        keys = ("SI", "SII", "SIII", "SIV", "SV", "SIxp", "SIIxp")
        prn = str(tmp_path / "golden.PRN")
        _write_prn(prn, [(0, [10.0 * sums[k] for k in keys])])
        data = run(registry, "seidel.vs_golden", {"file": jsn, "prn": prn})
        assert data["status"] == "matched"
        assert all(data["signs"].values())
        # печать F11.5 квантует golden — отношения совпадают до кванта
        assert all(r["rel_dev"] < data["tol"]
                   and not r["low_precision"]
                   for r in data["ratios"].values())

    def test_parse_prn_rows(self, registry, tmp_path):
        prn = str(tmp_path / "sumsed.PRN")
        vals = (-0.00065, -0.09966, -0.43641, 0.07355, -387.95831,
                0.00103, 0.00370)
        _write_prn(prn, [(0, vals), (1, [v / 3 for v in vals])])
        data = run(registry, "seidel.parse_prn", {"prn": prn})
        assert data["num_rows"] == 2
        row = data["rows"][0]
        assert row["n"] == 0
        assert row["S1"] == pytest.approx(vals[0])
        assert row["S5"] == pytest.approx(vals[4])

    def test_parse_prn_empty(self, registry, prn_empty):
        data = run(registry, "seidel.parse_prn", {"prn": prn_empty})
        assert data["rows"] == [] and data["num_rows"] == 0


# --------------------------------------------------------------------------- #
# adv.* — analysis/advanced.py
# --------------------------------------------------------------------------- #

class TestAdvCommands:
    def test_psf_scalars_and_grid(self, registry, demo_files):
        from analysis.advanced import compute_psf
        _, jsn = demo_files
        system = load_json(jsn)
        scalars = run(registry, "adv.psf", {"file": jsn, "num_rays": 32})
        assert "psf" not in scalars  # решётки по умолчанию выключены
        assert scalars["pixel_um"] > 0
        psf, dx, dy = compute_psf(system, wl=get_primary_wl(system),
                                  num_rays=32)
        grid = run(registry, "adv.psf",
                   {"file": jsn, "num_rays": 32, "include_grid": True})
        assert grid["x_um"] == pytest.approx(dx.tolist())
        assert grid["y_um"] == pytest.approx(dy.tolist())
        assert grid["psf"][16][16] == pytest.approx(float(psf[16, 16]))
        assert max(max(r) for r in grid["psf"]) == pytest.approx(1.0)

    def test_lsf_matches_direct(self, registry, demo_files):
        from analysis.advanced import compute_lsf
        _, jsn = demo_files
        system = load_json(jsn)
        for direction in ("tangential", "sagittal"):
            lsf, axis = compute_lsf(system, wl=get_primary_wl(system),
                                    num_rays=32, direction=direction)
            data = run(registry, "adv.lsf",
                       {"file": jsn, "num_rays": 32, "direction": direction})
            assert data["lsf"] == pytest.approx(lsf.tolist()), direction
            assert data["x_um"] == pytest.approx(axis.tolist())
            assert max(data["lsf"]) == pytest.approx(1.0)

    def test_lsf_bad_direction(self, registry, demo_files):
        _, jsn = demo_files
        result = registry.execute("adv.lsf", CommandContext(),
                                  {"file": jsn, "direction": "diagonal"})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_enc_monotonic(self, registry, demo_files):
        from analysis.advanced import compute_enc
        _, jsn = demo_files
        system = load_json(jsn)
        r_direct, enc_direct = compute_enc(system, wl=get_primary_wl(system),
                                           num_rays=40)
        data = run(registry, "adv.enc", {"file": jsn, "num_rays": 40})
        assert data["r_um"] == pytest.approx(r_direct.tolist())
        assert data["enc"] == pytest.approx(enc_direct.tolist())
        assert data["enc"][0] < 0.05  # r=0 — почти пустой круг
        assert data["enc"][-1] == pytest.approx(1.0)
        assert all(b >= a - 1e-12 for a, b in zip(data["enc"],
                                                  data["enc"][1:]))

    def test_ptf_shape(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "adv.ptf", {"file": jsn, "num_rays": 32})
        assert data["freqs"][0] == 0.0
        assert data["cutoff_freq"] > 0
        assert len(data["ptf_tangential"]) == len(data["freqs"])
        assert len(data["ptf_sagittal"]) == len(data["freqs"])
        assert all(-math.pi <= v <= math.pi
                   for v in data["ptf_tangential"])

    def test_bar_image_profiles(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "adv.bar_image",
                   {"file": jsn, "bar_freq_lp_mm": 10.0})
        assert set(data["ideal"]) <= {0.0, 1.0}
        assert min(data["blurred"]) >= 0.0
        assert max(data["blurred"]) <= 1.1  # лёгкий звон у краёв допустим
        assert len(data["x_um"]) == len(data["ideal"]) == len(data["blurred"])

    def test_bar_mtf_table(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "adv.bar_mtf",
                   {"file": jsn, "freq_list": [10, 30]})
        assert [r["freq"] for r in data["rows"]] == [10.0, 30.0]
        assert all(0.0 <= r["mtf"] <= 1.0 for r in data["rows"])
        assert all(r["mtf"] > 0.5 for r in data["rows"])  # ахромат f/5

    def test_esf_bounds(self, registry, demo_files):
        _, jsn = demo_files
        data = run(registry, "adv.esf", {"file": jsn})
        assert 0.0 <= data["esf"][0] < 0.5
        assert data["esf"][-1] == pytest.approx(1.0)
        assert all(b >= a - 1e-12 for a, b in zip(data["esf"],
                                                  data["esf"][1:]))

    def test_object_image_kinds(self, registry, demo_files):
        _, jsn = demo_files
        for kind in ("mira", "edge", "point", "sine"):
            data = run(registry, "adv.object_image",
                       {"file": jsn, "kind": kind, "num_rays": 32})
            assert data["kind"] == kind
            assert data["image_peak"] > 0.0
            assert "image" not in data  # решётки по умолчанию выключены
            if kind != "point":  # у точки image = ядро ФРТ (пик « 1)
                assert data["image_peak"] > 0.9
        grid = run(registry, "adv.object_image",
                   {"file": jsn, "kind": "edge", "num_rays": 32,
                    "include_grid": True})
        assert len(grid["image"]) == 32
        assert sum(sum(row) for row in grid["image"]) > 0

    def test_object_image_bad_kind(self, registry, demo_files):
        _, jsn = demo_files
        result = registry.execute("adv.object_image", CommandContext(),
                                  {"file": jsn, "kind": "zone_plate"})
        assert not result.ok
        assert result.error["code"] == "invalid_param"
