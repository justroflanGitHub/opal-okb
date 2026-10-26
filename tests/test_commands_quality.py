"""R500-10: сводные метрики качества quality.* (quality_cmds.py).

Композиция движков psf/mtf/strehl/spot: сверка сводных скаляров со
своими источниками (compute_enc, compute_spot_diagram, mtf.curve),
монотонность зон энергии, согласованность пороговых проверок и
агрегата check.all, паспорт против параксиала.
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
    path = str(tmp_path_factory.mktemp("quality") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


@pytest.fixture(scope="module")
def demo2_json(tmp_path_factory):
    from domain.models import create_demo_system_by_name
    from fileio.json_io import save_json
    path = str(tmp_path_factory.mktemp("quality2") / "demo2.json")
    system = create_demo_system_by_name("achromat")
    system.surfaces[0].radius += 1.0
    save_json(system, path)
    return path


class TestEncircledEnergy:
    def test_geometric_matches_direct_compute_enc(self, demo_json):
        import numpy as np
        from analysis.advanced import compute_enc
        from fileio.json_io import load_json
        data = run("quality.ee.diameters",
                   {"file": demo_json, "fields": [0.0], "num_rays": 40})
        r_um, enc = compute_enc(load_json(demo_json), wl=data["wl"],
                                num_rays=40, field_y=0.0)
        direct = 2.0 * float(np.interp(0.5, enc, r_um))
        d50 = data["rows"][0]["diameters"][0]
        assert d50["fraction"] == 0.5
        assert d50["diameter_um"] == pytest.approx(direct, rel=1e-9)

    def test_diameters_monotonic_in_fraction(self, demo_json):
        data = run("quality.ee.diameters",
                   {"file": demo_json, "fields": [3.0], "num_rays": 40})
        diameters = [d["diameter_um"]
                     for d in data["rows"][0]["diameters"]]
        assert diameters == sorted(diameters)
        assert all(d > 0 for d in diameters)

    def test_psf_diameters_and_airy(self, demo_json):
        data = run("quality.ee.diameters.psf",
                   {"file": demo_json, "field_y": 0.0})
        diameters = [d["diameter_um"] for d in data["diameters"]]
        assert diameters == sorted(diameters)
        assert data["airy_um"] > 0
        assert diameters[0] > data["airy_um"]  # зона 50 % шире r₁ Эйри

    def test_bad_fraction(self, demo_json):
        fail("quality.ee.diameters",
             {"file": demo_json, "fractions": [1.5]}, "invalid_param")


class TestSpotAndFieldsSummary:
    def test_spot_rows_by_wl_and_poly(self, demo_json):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        from fileio.json_io import load_json
        data = run("quality.spot.summary",
                   {"file": demo_json, "num_rays": 12})
        assert [r["field_y"] for r in data["rows"]] == [0.0, 3.0, 5.0]
        axis = data["rows"][0]
        assert len(axis["by_wl"]) == 3
        direct = compute_rms_spot(
            compute_spot_diagram(load_json(demo_json), wl=axis["by_wl"][0]
                                 ["wl"], num_rays=12, field_y=0.0))
        assert axis["by_wl"][0]["rms"] == pytest.approx(direct)
        worst = max(r["rms_poly"] for r in data["rows"])
        assert data["summary"]["max_rms"] == pytest.approx(worst)
        assert data["summary"]["max_field"] in (3.0, 5.0)

    def test_fields_summary_shape_and_mtf_source(self, demo_json):
        data = run("quality.fields.summary",
                   {"file": demo_json, "num_rays": 12,
                    "freq_lpmm": 30.0})
        assert [r["field_y"] for r in data["rows"]] == [0.0, 3.0, 5.0]
        row = data["rows"][0]
        for key in ("rms_poly", "strehl_exact", "mtf_t", "mtf_s",
                    "d90_um"):
            assert row[key] is not None and row[key] >= 0, key
        # MTF-строка берётся из сестринской mtf.curve (та же λ)
        curve = run("mtf.curve", {"file": demo_json, "field_y": 0.0,
                                  "wl": data["wl"]})
        import numpy as np
        direct = float(np.interp(30.0, curve["freq_lpmm"],
                                 curve["tan"]))
        assert row["mtf_t"] == pytest.approx(direct, abs=1e-9)


class TestMtfSummaries:
    def test_matrix_shape_and_cutoff_zero(self, demo_json):
        data = run("quality.mtf.matrix",
                   {"file": demo_json, "fields": [0.0, 3.0],
                    "freqs": [20.0, 60.0, 1e6]})
        assert len(data["rows"]) == 2
        mtf = data["rows"][0]["mtf"]
        assert [m["freq_lpmm"] for m in mtf] == [20.0, 60.0, 1e6]
        assert all(0.0 <= m["mtf_t"] <= 1.0 + 1e-9 for m in mtf[:2])
        # выше частоты среза MTF = 0 по определению
        assert mtf[2]["mtf_t"] == 0.0 and mtf[2]["mtf_s"] == 0.0

    def test_poly_is_weighted_mean_of_mono(self, demo_json):
        poly = run("quality.mtf.poly",
                   {"file": demo_json, "freqs": [20.0]})
        mono_values = []
        for wl in (w["wl"] for w in poly["wls"]):
            mono = run("quality.mtf.matrix",
                       {"file": demo_json, "fields": [0.0],
                        "freqs": [20.0], "wl": wl})
            mono_values.append(mono["rows"][0]["mtf"][0]["mtf_t"])
        assert poly["rows"][0]["mtf_t"] == pytest.approx(
            sum(mono_values) / len(mono_values), abs=1e-9)

    def test_poly_needs_wavelengths(self, tmp_path):
        from domain.models import create_demo_system_by_name
        from fileio.json_io import save_json
        path = str(tmp_path / "nowl.json")
        system = create_demo_system_by_name("achromat")
        system.wavelengths = []
        save_json(system, path)
        fail("quality.mtf.poly", {"file": path}, "invalid_param")

    def test_limit_freq_bracketing(self, demo_json):
        """Частота предела высаживает MTF на порог: ниже — выше порога,
        выше — ниже."""
        data = run("quality.mtf.limit_freq",
                   {"file": demo_json, "threshold": 0.3,
                    "fields": [0.0]})
        limit = data["rows"][0]["limit_t"]
        assert limit > 0.0
        row_min = min(min(r["limit_t"], r["limit_s"]) for r in data["rows"])
        assert data["min_limit_lpmm"] == pytest.approx(row_min)
        bracket = run("quality.mtf.matrix",
                      {"file": demo_json, "fields": [0.0],
                       "freqs": [0.9 * limit, 1.1 * limit]})
        mtf = bracket["rows"][0]["mtf"]
        assert mtf[0]["mtf_t"] >= 0.3
        assert mtf[1]["mtf_t"] < 0.3

    def test_limit_freq_monotonic_in_threshold(self, demo_json):
        loose = run("quality.mtf.limit_freq",
                    {"file": demo_json, "threshold": 0.05,
                     "fields": [0.0]})
        strict = run("quality.mtf.limit_freq",
                     {"file": demo_json, "threshold": 0.5,
                      "fields": [0.0]})
        assert (loose["rows"][0]["limit_t"]
                >= strict["rows"][0]["limit_t"])
        assert strict["min_limit_lpmm"] <= loose["min_limit_lpmm"]

    def test_limit_freq_bad_threshold(self, demo_json):
        fail("quality.mtf.limit_freq",
             {"file": demo_json, "threshold": 1.5}, "invalid_param")

    def test_area_bounds(self, demo_json):
        data = run("quality.mtf.area", {"file": demo_json})
        assert 0.0 < data["ideal_area"] < 1.0
        assert 0.0 < data["area_t"] <= data["ideal_area"] + 1e-9
        assert 0.0 < data["ratio_t"] <= 1.0 + 1e-9

    def test_geo_vs_diff_ratio(self, demo_json):
        data = run("quality.mtf.geo_vs_diff",
                   {"file": demo_json, "num_rays": 25})
        # у аберрационной системы геометрический контраст ниже предела
        assert data["geo_t"] <= data["diff_t"] + 1e-9
        assert data["geo_s"] <= data["diff_s"] + 1e-9
        assert data["ratio_t"] == pytest.approx(
            data["geo_t"] / data["diff_t"])


class TestStrehlAndWavefront:
    def test_strehl_summary_aggregates(self, demo_json):
        data = run("quality.strehl.summary", {"file": demo_json})
        exact = [r["strehl_exact"] for r in data["rows"]]
        assert len(exact) == 3
        assert all(0.0 < v <= 1.0 for v in exact)
        assert data["worst"]["strehl_exact"] == pytest.approx(min(exact))
        assert data["mean_exact"] == pytest.approx(
            sum(exact) / len(exact))

    def test_wavefront_summary_max_and_marechal(self, demo_json):
        data = run("quality.wavefront.summary", {"file": demo_json})
        valid = [r["rms_wl"] for r in data["rows"]
                 if r["rms_wl"] is not None]
        assert valid
        assert data["max_rms_wl"] == pytest.approx(max(valid))
        assert data["strehl_marechal_max"] == pytest.approx(
            math.exp(-(2.0 * math.pi * data["max_rms_wl"]) ** 2))

    def test_fields_required(self, tmp_path):
        from domain.models import create_demo_system_by_name
        from fileio.json_io import save_json
        path = str(tmp_path / "nofields.json")
        system = create_demo_system_by_name("achromat")
        system.field_points = []
        save_json(system, path)
        fail("quality.strehl.summary", {"file": path}, "invalid_param")


class TestPassportAndCompare:
    def test_passport_matches_paraxial(self, demo_json):
        from domain.calculations import paraxial_trace
        from fileio.json_io import load_json
        from optics_utils import get_primary_wl
        data = run("quality.passport",
                   {"file": demo_json, "num_rays": 12})
        system = load_json(demo_json)
        parax = paraxial_trace(system, wl=get_primary_wl(system))
        assert data["efl_mm"] == pytest.approx(
            abs(parax["focal_length"]), rel=1e-12)
        assert data["f_number"] == pytest.approx(
            abs(parax["f_number"]), rel=1e-12)
        assert data["fields"] == [0.0, 3.0, 5.0]
        assert data["num_wavelengths"] == 3
        assert data["airy_diameter_um"] == pytest.approx(
            2.0 * 1.22 * get_primary_wl(system)
            * abs(parax["f_number"]))
        assert 0.0 <= data["mtf_t"] <= 1.0

    def test_compare_two_systems(self, demo_json, demo2_json):
        data = run("quality.compare",
                   {"file_a": demo_json, "file_b": demo2_json,
                    "num_rays": 12})
        rows = {r["metric"]: r for r in data["rows"]}
        assert rows["efl_mm"]["delta"] != 0.0
        assert rows["efl_mm"]["delta"] == pytest.approx(
            rows["efl_mm"]["b"] - rows["efl_mm"]["a"])
        assert rows["num_surfaces"]["a"] == rows["num_surfaces"]["b"] == 3


class TestChecks:
    def test_check_mtf_verdict_consistent(self, demo_json):
        data = run("quality.check.mtf",
                   {"file": demo_json, "threshold": 0.05,
                    "freq_lpmm": 30.0, "fields": [0.0, 5.0]})
        assert data["pass"] == all(r["pass_t"] and r["pass_s"]
                                   for r in data["rows"])
        strict = run("quality.check.mtf",
                     {"file": demo_json, "threshold": 0.99,
                      "freq_lpmm": 30.0, "fields": [0.0, 5.0]})
        assert strict["pass"] is False

    def test_check_strehl_worst_and_verdicts(self, demo_json):
        loose = run("quality.check.strehl",
                    {"file": demo_json, "threshold": 1e-6})
        assert loose["pass"] is True
        strict = run("quality.check.strehl",
                     {"file": demo_json, "threshold": 0.9})
        assert strict["pass"] is False
        exact = [r["strehl_exact"] for r in strict["rows"]]
        assert strict["worst"]["strehl_exact"] == pytest.approx(min(exact))

    def test_check_spot_thresholds(self, demo_json):
        loose = run("quality.check.spot",
                    {"file": demo_json, "threshold_um": 1e5,
                     "num_rays": 12})
        assert loose["pass"] is True
        strict = run("quality.check.spot",
                     {"file": demo_json, "threshold_um": 1e-3,
                      "num_rays": 12})
        assert strict["pass"] is False
        assert strict["worst"]["rms_um"] == pytest.approx(
            max(r["rms_um"] for r in strict["rows"]))

    def test_check_ee_worst(self, demo_json):
        data = run("quality.check.ee",
                   {"file": demo_json, "threshold_um": 1e5,
                    "num_rays": 40})
        assert data["pass"] is True
        assert data["worst"]["diameter_um"] == pytest.approx(
            max(r["diameter_um"] for r in data["rows"]))

    def test_check_all_matches_singles(self, demo_json):
        data = run("quality.check.all",
                   {"file": demo_json, "strehl_min": 0.9,
                    "fields": [0.0, 3.0]})
        assert data["num_checks"] == 1
        single = run("quality.check.strehl",
                     {"file": demo_json, "threshold": 0.9,
                      "fields": [0.0, 3.0]})
        assert data["checks"][0]["pass"] == single["pass"]
        assert data["pass"] is False

        full = run("quality.check.all",
                   {"file": demo_json, "mtf_min": 0.05,
                    "strehl_min": 1e-6, "rms_max_um": 1e5,
                    "ee_max_um": 1e5, "num_rays": 12,
                    "fields": [0.0]})
        assert full["num_checks"] == 4
        assert full["pass"] == all(c["pass"] for c in full["checks"])

    def test_check_all_requires_threshold(self, demo_json):
        fail("quality.check.all", {"file": demo_json}, "invalid_param")

    def test_bad_thresholds(self, demo_json):
        fail("quality.check.mtf",
             {"file": demo_json, "threshold": 0.0}, "invalid_param")
        fail("quality.check.strehl",
             {"file": demo_json, "threshold": 1.0}, "invalid_param")
        fail("quality.check.spot",
             {"file": demo_json, "threshold_um": -1.0}, "invalid_param")
        fail("quality.check.ee",
             {"file": demo_json, "threshold_um": 0.0}, "invalid_param")


class TestRegime:
    def test_regime_ratio_and_label(self, demo_json):
        data = run("quality.regime",
                   {"file": demo_json, "num_rays": 12})
        assert data["ratio"] == pytest.approx(
            data["rms_um"] / data["airy_radius_um"])
        assert data["regime"] in ("diffraction_limited", "comparable",
                                  "aberration_limited")
        # у демо-ахромата RMS пятна на порядки больше диска Эйри
        assert data["regime"] == "aberration_limited"
