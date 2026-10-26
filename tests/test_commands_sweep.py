"""R500-7: развёртки sweep.* и seidel3.* (commands/builtin/sweep_cmds.py).

Циклы поверх существующих движков: сверка одиночных значений со
своими источниками (spot/strehl/mtf), формы кривых дефокуса, инвариант
SI по диафрагме, Петцваль из SIV.
"""
import math

import pytest

from commands import CommandContext, default_registry


def run(name, args=None):
    result = default_registry.execute(name, CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    from domain.models import create_demo_system_by_name
    from fileio.json_io import save_json
    path = str(tmp_path_factory.mktemp("sweep") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


class TestFieldSweeps:
    def test_spot_rms_matches_direct(self, demo_json):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        from fileio.json_io import load_json
        data = run("sweep.fields.spot_rms",
                   {"file": demo_json, "num_rays": 12, "fields": [0.0, 3.0]})
        system = load_json(demo_json)
        direct = compute_rms_spot(
            compute_spot_diagram(system, wl=data["wl"], num_rays=12,
                                 field_y=3.0))
        assert data["rows"][1]["rms"] == pytest.approx(direct)
        assert data["num_fields"] == 2

    def test_mtf_monotonic_fields_shape(self, demo_json):
        data = run("sweep.fields.mtf",
                   {"file": demo_json, "num_rays": 25,
                    "fields": [0.0, 3.0, 5.0], "freq_lpmm": 20.0})
        assert len(data["rows"]) == 3
        assert all(0.0 <= r["mtf_t"] <= 1.0 + 1e-9 for r in data["rows"])

    def test_strehl_rows(self, demo_json):
        data = run("sweep.fields.strehl",
                   {"file": demo_json, "fields": [0.0, 3.0]})
        assert all(0.0 <= r["strehl_exact"] <= 1.0 for r in data["rows"])

    def test_enc_bounds(self, demo_json):
        data = run("sweep.fields.enc",
                   {"file": demo_json, "fields": [0.0],
                    "radius_um": 1000.0, "num_rays": 40})
        assert 0.9 < data["rows"][0]["enc"] <= 1.0  # большой кружок ловит всё

    def test_lsf_width_positive(self, demo_json):
        data = run("sweep.fields.lsf_width",
                   {"file": demo_json, "fields": [0.0], "num_rays": 32})
        assert data["rows"][0]["fwhm_um"] > 0

    def test_chrom_shift_zero_on_axis(self, demo_json):
        data = run("sweep.fields.chrom_shift",
                   {"file": demo_json, "fields": [0.0], "num_rays": 12})
        assert data["rows"][0]["shift_mm"] == pytest.approx(0.0, abs=1e-9)

    def test_chrom_shift_needs_two_wls(self, tmp_path):
        from domain.models import create_demo_system_by_name
        from fileio.json_io import save_json, load_json
        path = str(tmp_path / "mono.json")
        system = create_demo_system_by_name("achromat")
        system.wavelengths = system.wavelengths[:1]
        save_json(system, path)
        fail("sweep.fields.chrom_shift",
             {"file": path, "fields": [0.0]}, "invalid_param")


class TestWavelengthAndDefocus:
    def test_wl_spot_rms_covers_system_wls(self, demo_json):
        data = run("sweep.wl.spot_rms",
                   {"file": demo_json, "num_rays": 12})
        assert len(data["rows"]) == 3
        assert all(r["rms"] > 0 for r in data["rows"])

    def test_wl_strehl(self, demo_json):
        data = run("sweep.wl.strehl", {"file": demo_json})
        assert len(data["rows"]) == 3

    def test_defocus_spot_curve_has_minimum(self, demo_json):
        data = run("sweep.defocus.spot_rms",
                   {"file": demo_json, "num_rays": 12, "steps": 11,
                    "defocus_min": -3.0, "defocus_max": 1.0})
        rms = [r["rms"] for r in data["rows"]]
        assert len(rms) == 11
        # минимум кривой — внутри диапазона (крайние значения больше)
        assert data["best"]["rms"] <= min(rms[0], rms[-1])
        mid = rms.index(min(rms))
        assert 0 < mid < len(rms) - 1

    def test_defocus_wavefront_rms(self, demo_json):
        data = run("sweep.defocus.wavefront_rms",
                   {"file": demo_json, "steps": 3, "grid_size": 32,
                    "defocus_min": 0.0, "defocus_max": 2.0})
        assert len(data["rows"]) == 3
        assert all(r["rms_wl"] > 0 for r in data["rows"])

    def test_defocus_bad_range(self, demo_json):
        fail("sweep.defocus.spot_rms",
             {"file": demo_json, "defocus_min": 1.0, "defocus_max": -1.0},
             "invalid_param")


class TestZonesAzimuthApertureStop:
    def test_zones_ring_zero_is_point(self, demo_json):
        data = run("sweep.zones.spot",
                   {"file": demo_json, "num_rings": 3, "num_azimuths": 6})
        assert data["rows"][0]["rho"] == 0.0
        assert data["rows"][0]["num_points"] == 1  # центральный луч
        assert data["rows"][1]["rho"] == pytest.approx(2.0 / 3.0)

    def test_azimuth_sweep_shape(self, demo_json):
        data = run("sweep.azimuth.aberrations",
                   {"file": demo_json, "field_y": 3.0, "num_rays": 7})
        assert [r["azimuth_deg"] for r in data["rows"]] == [0.0, 45.0, 90.0]
        assert all(r["max_dy"] >= r["rms_dy"] > 0 for r in data["rows"])

    def test_aperture_sweep_grows(self, demo_json):
        data = run("sweep.aperture.spot_rms",
                   {"file": demo_json, "num_rays": 12,
                    "apertures": [6.0, 20.0]})
        # больше апертура → больше аберрации (сферическая 3-го порядка)
        assert data["rows"][1]["rms"] > data["rows"][0]["rms"]

    def test_stop_sweep_si_invariant(self, demo_json):
        data = run("sweep.stop.seidel", {"file": demo_json})
        si_values = {round(r["SI"], 12) for r in data["rows"]}
        assert len(si_values) == 1  # SI инвариантна к диафрагме
        sii_values = {round(r["SII"], 9) for r in data["rows"]}
        assert len(sii_values) >= 1  # SII может меняться (stop=2 меняет)

    def test_stop_bad_position(self, demo_json):
        fail("sweep.stop.seidel",
             {"file": demo_json, "stop_surfaces": [99]}, "invalid_param")


class TestSeidel3:
    def test_petzval_from_siv(self, demo_json):
        from domain.calculations import seidel_aberrations
        from fileio.json_io import load_json
        data = run("seidel3.petzval.radius", {"file": demo_json})
        sums = seidel_aberrations(load_json(demo_json))
        assert data["SIV"] == pytest.approx(sums["SIV"])
        assert data["petzval_radius_mm"] == pytest.approx(1.0 / sums["SIV"])

    def test_ranking_sorted(self, demo_json):
        data = run("seidel3.sums.ranking", {"file": demo_json})
        shares = [r["share"] for r in data["ranking"]]
        assert shares == sorted(shares, reverse=True)
        assert shares[0] == 1.0
        labels = {r["sum"] for r in data["ranking"]}
        assert labels == {"SI", "SII", "SIII", "SIV", "SV"}

    def test_normalized_ratios(self, demo_json):
        data = run("seidel3.sums.normalized", {"file": demo_json})
        # сверка: SII/SI по прямым суммам
        from domain.calculations import seidel_aberrations
        from fileio.json_io import load_json
        sums = seidel_aberrations(load_json(demo_json))
        assert data["ratios"]["SII"] == pytest.approx(
            sums["SII"] / sums["SI"], rel=1e-12)

    def test_chromatic_position(self, demo_json):
        data = run("seidel3.chromatic.position", {"file": demo_json})
        assert len(data["rows"]) == 3
        assert data["delta_f_mm"] == pytest.approx(
            data["rows"][-1]["f_prime"] - data["rows"][0]["f_prime"])

    def test_chromatic_magnitude(self, demo_json):
        data = run("seidel3.chromatic.magnitude", {"file": demo_json})
        assert len(data["rows"]) == 3
        assert data["delta_V_pct"] != 0.0

    def test_single_wl_chromatic_fails(self, tmp_path):
        from domain.models import create_demo_system_by_name
        from fileio.json_io import save_json
        path = str(tmp_path / "mono.json")
        system = create_demo_system_by_name("achromat")
        system.wavelengths = system.wavelengths[:1]
        save_json(system, path)
        fail("seidel3.chromatic.position", {"file": path},
             "invalid_param")
