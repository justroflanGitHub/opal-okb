"""Волна 3, домен «Дифракция и волновой фронт»: команды psf/mtf/diffr/
strehl/zern/focus (commands/builtin/psf_cmds.py).

Три уровня проверки:
* smoke — каждая команда выполняется и даёт строгий JSON;
* паритет — числа команд совпадают с прямыми вызовами analysis/
  (обёртка не должна менять результаты);
* инварианты — физика (MTF(0)=1, контраст синус-миры = MTF(ν), СКВ
  Noll-члена = 1, ФКЭ монотонна) и контракт ошибок.
"""
import json
import math

import pytest

from commands import CommandContext, default_registry
from fileio.json_io import load_json
from tests._commands_proc import run_cli_json

#: Рабочая λ тестов (d-линия) — явная, чтобы паритет не зависел от
#: выбора основной λ системы.
WL = 0.58756

#: Префиксы домена Волны 3 → ожидаемое число команд.
WAVE3_EXPECTED = {
    "psf": 4, "mtf": 1, "diffr": 5, "strehl": 2, "zern": 11, "focus": 6,
}


# --------------------------------------------------------------------------- #
# Фикстуры и хелперы
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.opj, .json) демо-ахромат, созданный командами Волны 1."""
    tmp = tmp_path_factory.mktemp("commands_w3_psf")
    jsn = str(tmp / "demo_achromat.json")
    opj = str(tmp / "demo_achromat.opj")
    ctx = CommandContext()
    res = default_registry.execute(
        "system.new", ctx, {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    res = default_registry.execute(
        "file.save", ctx, {"src": jsn, "file": opj})
    assert res.ok, res.error
    return opj, jsn


@pytest.fixture(scope="module")
def system(demo_files):
    """OpticalSystem напрямую из fileio (для паритета с доменом)."""
    return load_json(demo_files[1])


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    """Выполнить команду, ожидая ошибку с данным кодом."""
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error
    return result.error


def _defocus_points(num, amplitude):
    """Детерминированные точки зрачка с W = a·(2ρ²−1) (чистый дефокус).

    Золотая спираль (равномерна по площади, без симметрии) — точная
    представимость W одним членом базиса от симметрии не зависит.
    """
    points = []
    for i in range(num):
        r = math.sqrt((i + 0.5) / num)
        phi = i * 2.399963229728653  # золотой угол
        px, py = r * math.cos(phi), r * math.sin(phi)
        w = amplitude * (2.0 * (px * px + py * py) - 1.0)
        points.append([px, py, w])
    return points


# --------------------------------------------------------------------------- #
# Реестр: состав и smoke домена
# --------------------------------------------------------------------------- #

class TestWave3Registry:
    def test_all_prefixes_registered(self):
        names = default_registry.names()
        for prefix, count in WAVE3_EXPECTED.items():
            owned = [n for n in names if n.split(".")[0] == prefix]
            assert len(owned) == count, (prefix, owned)
            assert all(default_registry.get(n).category == prefix
                       for n in owned)

    def test_wave3_total(self):
        wave3 = [n for n in default_registry.names()
                 if n.split(".")[0] in WAVE3_EXPECTED]
        assert len(wave3) == 29

    def test_target_schema_requires_freq(self):
        params = {p["name"]: p for p in default_registry
                  .schema("psf.target")["params"]}
        assert params["freq_lpmm"]["required"]
        assert params["orientation"]["choices"] == ["tangential",
                                                    "sagittal"]
        # системные команды несут общий хвост источников системы
        assert {"file", "system", "lbo_index", "lbo_name"} <= set(params)

    def test_smoke_all_wave3_json_strict(self, demo_files):
        opj, _ = demo_files
        points16 = _defocus_points(16, 0.3)
        points28 = _defocus_points(28, 0.3)
        smoke = {
            "psf.lsf": {"file": opj},
            "psf.encircled": {"file": opj},
            "psf.target": {"file": opj, "freq_lpmm": 50.0},
            "psf.section": {"file": opj, "zernike": True},
            "mtf.curve": {"file": opj},
            "diffr.wavefront": {"file": opj, "grid_size": 32},
            "diffr.mtf": {"file": opj, "grid_size": 32},
            "diffr.mtf.quick": {"file": opj},
            "diffr.mtf.poly": {"file": opj, "grid_size": 32},
            "diffr.mtf.limited": {"file": opj},
            "strehl.marechal": {"sigma_w": 0.05},
            "strehl.calc": {"file": opj, "wl": WL},
            "zern.terms": {},
            "zern.coeffs": {"file": opj, "num_rays": 16},
            "zern.coeffs.fit": {"points": points16},
            "zern.wavefront": {"file": opj, "grid_size": 32},
            "zern.chromatic": {"file": opj, "num_rays": 16},
            "zern.global": {"file": opj, "num_rings": 3,
                            "num_fields": 3},
            "zern.fit_points": {"points": points28},
            "zern.reconstruct": {"coeffs": [0.1, 0.0, -0.2, 0.05],
                                 "grid": 16},
            "zern.strehl": {"coeffs": [0.1, 0.02, -0.05]},
            "zern.decompose": {"file": opj},
            "zern.protocol": {"file": opj},
            "focus.min_rms": {"file": opj},
            "focus.max_strehl": {"file": opj},
            "focus.zone_best": {"file": opj},
            "focus.min_spot": {"file": opj},
            "focus.eqf": {"file": opj},
            "focus.all": {"file": opj},
        }
        assert set(smoke) == {
            n for n in default_registry.names()
            if n.split(".")[0] in WAVE3_EXPECTED}
        for name, args in sorted(smoke.items()):
            data = run(name, args)
            json.dumps(data, ensure_ascii=False, allow_nan=False)


# --------------------------------------------------------------------------- #
# psf.* — ФРЛ, ФКЭ, миры, протокол
# --------------------------------------------------------------------------- #

class TestPsfCommands:
    def test_lsf_profiles_normalized(self, demo_files):
        data = run("psf.lsf", {"file": demo_files[1], "wl": WL})
        for key in ("meridional", "sagittal"):
            assert len(data[key]) == len(data["coord_um"])
            assert sum(data[key]) == pytest.approx(1.0, abs=1e-9)
        assert data["pitch_um"] > 0

    def test_lsf_matches_domain(self, demo_files, system):
        from analysis.psf_mtf import lsf_from_psf, psf_grid
        res = psf_grid(system, wl=WL)
        lsf = lsf_from_psf(res["psf"], res["pitch_um"])
        data = run("psf.lsf", {"file": demo_files[1], "wl": WL})
        assert data["meridional"] == pytest.approx(
            lsf["meridional"].tolist(), abs=1e-12)
        assert data["coord_um"] == pytest.approx(
            lsf["coord_um"].tolist(), abs=1e-9)

    def test_encircled_energy_curve(self, demo_files):
        data = run("psf.encircled", {"file": demo_files[1], "wl": WL})
        ee = data["ee"]
        assert ee[0] >= 0.0
        assert ee[-1] == pytest.approx(1.0, abs=1e-6)
        assert all(b >= a - 1e-12 for a, b in zip(ee, ee[1:]))  # монотонна
        assert 0.0 < data["r50_um"] < data["r80_um"]
        assert data["airy_um"] > 0

    def test_target_sine_contrast_equals_mtf(self, demo_files):
        """Физика §9.5: контраст синус-миры на ν равен MTF(ν)."""
        freq = 50.0
        mtf = run("mtf.curve", {"file": demo_files[1], "wl": WL})
        mtf_at = float(np_interp(freq, mtf["freq_lpmm"], mtf["tan"]))
        target = run("psf.target", {"file": demo_files[1], "wl": WL,
                                    "freq_lpmm": freq})
        assert target["period_um"] == pytest.approx(1000.0 / freq)
        assert target["contrast"] == pytest.approx(mtf_at, rel=0.05)
        assert target["coord_um"][0] < 0 < target["coord_um"][-1]

    def test_target_bar_and_orientation(self, demo_files):
        sine = run("psf.target", {"file": demo_files[1], "wl": WL,
                                  "freq_lpmm": 50.0})
        bar = run("psf.target", {"file": demo_files[1], "wl": WL,
                                 "freq_lpmm": 50.0, "kind": "bar"})
        assert bar["kind"] == "bar"
        assert bar["contrast"] >= sine["contrast"]  # меандр ≥ синуса
        sag = run("psf.target", {"file": demo_files[1], "wl": WL,
                                 "freq_lpmm": 50.0,
                                 "orientation": "sagittal"})
        assert sag["orientation"] == "sagittal"
        # осевой пучок осесимметричен: сечения совпадают (допуск —
        # асимметрия IDW-интерполяции гексасетки на решётку)
        assert sag["contrast"] == pytest.approx(sine["contrast"],
                                                rel=0.02)

    def test_section_text(self, demo_files):
        data = run("psf.section", {"file": demo_files[1]})
        assert "ФРТ / ОПФ" in data["text"]
        assert "Штрель" in data["text"]
        with_zern = run("psf.section", {"file": demo_files[1],
                                        "zernike": True})
        assert "ЦЕРНИКЕ" in with_zern["text"]


def np_interp(x, xs, ys):
    """np.interp без numpy в импортах теста (линейная интерполяция)."""
    if x <= xs[0]:
        return ys[0]
    for x0, x1, y0, y1 in zip(xs, xs[1:], ys, ys[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]


# --------------------------------------------------------------------------- #
# mtf.* — ОПФ из ФРТ
# --------------------------------------------------------------------------- #

class TestMtfCommands:
    def test_mtf_curve_shape_and_dc(self, demo_files):
        data = run("mtf.curve", {"file": demo_files[1], "wl": WL})
        assert data["tan"][0] == pytest.approx(1.0, abs=1e-9)  # MTF(0)=1
        assert data["sag"][0] == pytest.approx(1.0, abs=1e-9)
        assert data["cutoff_lpmm"] > 0
        # pad=4: Найквист решётки ФРТ = ν_c·M/(2·(grid−1)) — частотный
        # диапазон чуть выше 2·ν_c из-за шага решётки зрачка (grid−1)
        from analysis.psf_mtf import GRID, PSF_FFT_PAD
        expected = data["cutoff_lpmm"] * (PSF_FFT_PAD * GRID) / (
            2.0 * (GRID - 1))
        assert data["nyquist_lpmm"] == pytest.approx(expected, rel=1e-9)
        assert data["freq_lpmm"] == sorted(data["freq_lpmm"])

    def test_mtf_matches_domain(self, demo_files, system):
        from analysis.psf_mtf import mtf_from_psf, psf_grid
        res = psf_grid(system, wl=WL)
        mtf = mtf_from_psf(res["psf"], res["pitch_um"])
        data = run("mtf.curve", {"file": demo_files[1], "wl": WL})
        assert data["tan"] == pytest.approx(mtf["tan"].tolist(),
                                            abs=1e-12)
        assert data["cutoff_lpmm"] == pytest.approx(res["cutoff_lpmm"])


# --------------------------------------------------------------------------- #
# diffr.* — дифракционная ЧКХ и волновой фронт
# --------------------------------------------------------------------------- #

class TestDiffrCommands:
    def test_wavefront_stats_and_grid(self, demo_files):
        data = run("diffr.wavefront",
                   {"file": demo_files[1], "wl": WL, "grid_size": 32})
        # точное число узлов решётки в единичном круге (сетка −1+2k/31)
        expected_points = sum(
            1 for i in range(32) for j in range(32)
            if (-1 + 2 * j / 31) ** 2 + (-1 + 2 * i / 31) ** 2 <= 1.0)
        assert data["num_points"] == expected_points
        assert data["pv"] >= data["rms"] > 0
        full = run("diffr.wavefront",
                   {"file": demo_files[1], "wl": WL, "grid_size": 32,
                    "include_grid": True})
        assert len(full["wavefront"]) == 32
        assert full["pupil_mask"][16][16] == 1.0
        assert sum(sum(row) for row in full["pupil_mask"]) == \
            full["num_points"]

    def test_mtf_matches_domain(self, demo_files, system):
        from analysis.diffraction import compute_diffraction_mtf
        direct = compute_diffraction_mtf(system, wl=WL, grid_size=32)
        data = run("diffr.mtf",
                   {"file": demo_files[1], "wl": WL, "grid_size": 32})
        assert data["mtf_tangential"] == pytest.approx(
            direct["mtf_tangential"], abs=1e-12)
        assert data["cutoff_freq"] == pytest.approx(direct["cutoff_freq"])
        assert data["mtf_tangential"][0] == pytest.approx(1.0, abs=1e-9)

    def test_mtf_quick_is_grid32(self, demo_files):
        quick = run("diffr.mtf.quick", {"file": demo_files[1], "wl": WL})
        full32 = run("diffr.mtf",
                     {"file": demo_files[1], "wl": WL, "grid_size": 32})
        assert quick["mtf_sagittal"] == full32["mtf_sagittal"]

    def test_mtf_poly_weights_all_wavelengths(self, demo_files, system):
        data = run("diffr.mtf.poly",
                   {"file": demo_files[1], "grid_size": 32})
        assert len(data["freqs"]) == 16  # grid 32 → 16 точек до среза/2
        # MTF(0) = 1 независимо от взвешивания λ
        assert data["mtf_tangential"][0] == 1.0
        assert data["mtf_sagittal"][0] == 1.0

    def test_mtf_limited_is_ideal(self, demo_files):
        data = run("diffr.mtf.limited", {"file": demo_files[1], "wl": WL})
        assert data["mtf"][0] == 1.0
        diffs = [b - a for a, b in zip(data["mtf"], data["mtf"][1:])]
        assert all(d <= 1e-12 for d in diffs)  # монотонно убывает
        assert data["mtf"][-1] < data["mtf"][0]
        # аналитика круглого зрачка на узловой частоте ν = 0.25·νc:
        # MTF = (2/π)(arccos ν̃ − ν̃·√(1−ν̃²)) ≈ 0.685
        quarter = data["mtf"][8]
        assert data["freqs"][8] == pytest.approx(
            0.25 * data["cutoff_freq"], rel=1e-9)
        expected = (2 / math.pi) * (math.acos(0.25)
                                    - 0.25 * math.sqrt(1 - 0.25 ** 2))
        assert quarter == pytest.approx(expected, abs=1e-9)


# --------------------------------------------------------------------------- #
# strehl.* — Марешаль и точный FFT
# --------------------------------------------------------------------------- #

class TestStrehlCommands:
    def test_marechal_formula(self):
        assert run("strehl.marechal", {"sigma_w": 0.0})["strehl"] == 1.0
        data = run("strehl.marechal", {"sigma_w": 0.05})
        assert data["strehl"] == pytest.approx(
            math.exp(-((2 * math.pi * 0.05) ** 2)), rel=1e-12)

    def test_calc_matches_domain(self, demo_files, system):
        from analysis.strehl import compute_strehl
        direct = compute_strehl(system, wl=WL)
        data = run("strehl.calc", {"file": demo_files[1], "wl": WL})
        assert data["strehl_marechal"] == pytest.approx(
            direct["strehl_marechal"], abs=1e-12)
        assert data["strehl_exact"] == pytest.approx(
            direct["strehl_exact"], abs=1e-12)
        assert 0.0 < data["strehl_marechal"] <= 1.0
        assert data["validity"] in ("good", "marechal_limit", "invalid")

    def test_calc_polychromatic_and_text(self, demo_files, system):
        data = run("strehl.calc", {"file": demo_files[1],
                                   "include_text": True})
        assert len(data["per_wl"]) == len(system.wavelengths)
        assert data["wl"] is None  # полихроматический режим
        assert data["text"].startswith("Strehl:")
        assert "σ" in data["tooltip"]


# --------------------------------------------------------------------------- #
# zern.* — базисы, коэффициенты, реконструкция
# --------------------------------------------------------------------------- #

class TestZernCommands:
    def test_terms_tables(self):
        data = run("zern.terms")
        assert len(data["classic"]) == 15
        assert len(data["opal"]) == 28
        assert data["classic"][0]["name"] == "Z00 Piston"
        assert data["opal"][0]["mark"] == "C x00"
        assert data["opal"][-1]["mark"] == "C x66"
        names = [t["name"] for t in data["opal"]]
        assert "Кома" in " ".join(names)

    def test_coeffs_matches_domain(self, demo_files, system):
        from analysis.zernike import compute_zernike_coefficients
        direct = compute_zernike_coefficients(system, wl=WL, num_rays=16)
        data = run("zern.coeffs",
                   {"file": demo_files[1], "wl": WL, "num_rays": 16})
        assert [c["coeff"] for c in data["coeffs"]] == pytest.approx(
            [c for c, _ in direct], abs=1e-12)
        assert len(data["coeffs"]) == 15
        by_term = {(c["n"], c["m"]): c["coeff"] for c in data["coeffs"]}
        assert set(by_term) == {(n, m) for n, m, _
                                in _classic_terms_reference()}

    def test_coeffs_max_order_2(self, demo_files):
        data = run("zern.coeffs",
                   {"file": demo_files[1], "wl": WL, "num_rays": 16,
                    "max_order": 2})
        assert len(data["coeffs"]) == 6  # члены n≤2 классического базиса

    def test_coeffs_fit_pure_defocus(self):
        """W = a·(2ρ²−1): только Z20 ≠ 0, коэффициент a/√3 (Noll)."""
        amplitude = 0.3
        data = run("zern.coeffs.fit",
                   {"points": _defocus_points(40, amplitude)})
        by_term = {(c["n"], c["m"]): c["coeff"] for c in data["coeffs"]}
        assert by_term[(2, 0)] == pytest.approx(
            amplitude / math.sqrt(3), abs=1e-8)
        others = [v for k, v in by_term.items() if k != (2, 0)]
        assert max(abs(v) for v in others) < 1e-8

    def test_wavefront_matches_domain(self, demo_files, system):
        from analysis.zernike import compute_wavefront_map_2d
        _wf, _coords, mask = compute_wavefront_map_2d(system, wl=WL,
                                                      grid_size=32)
        data = run("zern.wavefront",
                   {"file": demo_files[1], "wl": WL, "grid_size": 32,
                    "include_grid": True})
        inside = [w for w, m in zip(
            (v for row in data["wavefront"] for v in row),
            (v for row in data["pupil_mask"] for v in row)) if m > 0]
        # rms с пистоном — как в _wavefront_stats (sqrt(mean(W²)))
        rms = math.sqrt(sum(w * w for w in inside) / len(inside))
        assert rms == pytest.approx(data["rms"], rel=1e-6)
        assert data["num_points"] == int(sum(
            v for row in mask.tolist() for v in row))

    def test_chromatic_matches_domain(self, demo_files, system):
        from analysis.zernike import compute_zernike_chromatic
        direct = compute_zernike_chromatic(system, num_rays=16)
        data = run("zern.chromatic",
                   {"file": demo_files[1], "num_rays": 16})
        assert set(data["by_wavelength"]) == set(direct)
        # значения — пары [коэффициент, имя] по каждой λ
        key = sorted(direct)[0]
        assert [c for c, _name in data["by_wavelength"][key]] == \
            pytest.approx([c for c, _name in direct[key]], abs=1e-12)

    def test_global_matches_domain(self, demo_files, system):
        from analysis.zernike import compute_global_zernike
        direct = compute_global_zernike(system, num_rings=3,
                                        num_fields=3)
        data = run("zern.global", {"file": demo_files[1], "num_rings": 3,
                                   "num_fields": 3})
        assert len(data["combos"]) == len(direct["coeffs"])
        combo = data["combos"][0]
        key = (combo["field"], combo["wl"])
        assert [c["coeff"] for c in combo["coeffs"]] == pytest.approx(
            [c for c, _ in direct["coeffs"][key]], abs=1e-12)
        assert data["text"].strip()

    def test_fit_points_opal_basis(self):
        """OPAL-28: чистый дефокус → coeff[1] (член (2,0)) = a/√3."""
        amplitude = 0.25
        data = run("zern.fit_points",
                   {"points": _defocus_points(40, amplitude)})
        assert len(data["coeffs"]) == 28
        assert data["coeffs"][1] == pytest.approx(
            amplitude / math.sqrt(3), abs=1e-8)
        assert data["strehl_zernike"] == pytest.approx(
            math.exp(-((2 * math.pi * amplitude / math.sqrt(3)) ** 2)),
            rel=1e-6)

    def test_reconstruct_unit_rms(self):
        """Noll-нормировка: коэффициент c даёт СКВ |c| по зрачку
        (допуск — дискретизация решётки, ~2 % на N=32)."""
        data = run("zern.reconstruct",
                   {"coeffs": [0.0, 0.25], "grid": 32})  # только Z20
        assert data["rms"] == pytest.approx(0.25, abs=0.01)
        assert data["pv"] == pytest.approx(0.5 * math.sqrt(3), abs=0.02)

    def test_reconstruct_matches_domain(self):
        from analysis.zernike import zernike_reconstruct
        coeffs = [0.1, -0.05, 0.02, 0.01, 0.005]
        wf = zernike_reconstruct(coeffs, 16)
        data = run("zern.reconstruct",
                   {"coeffs": coeffs, "grid": 16, "include_grid": True})
        flat = [v for row in data["wavefront"] for v in row]
        direct = [float(v) for v in wf.ravel()]
        assert flat == pytest.approx(direct, abs=1e-12)

    def test_strehl_from_coeffs(self):
        from analysis.zernike import strehl_from_zernike
        coeffs = [0.1, 0.05, 0.0, -0.02]
        data = run("zern.strehl", {"coeffs": coeffs})
        assert data["strehl"] == pytest.approx(
            strehl_from_zernike(coeffs), rel=1e-12)
        assert data["sigma_w"] == pytest.approx(
            math.sqrt(0.05 ** 2 + 0.02 ** 2), rel=1e-12)

    def test_decompose_shape_and_domain(self, demo_files, system):
        from analysis.psf_mtf import zernike_decomposition
        direct = zernike_decomposition(system, wl=WL)
        data = run("zern.decompose", {"file": demo_files[1], "wl": WL})
        assert data["coeffs"] == pytest.approx(
            direct["coeffs"].tolist(), abs=1e-12)
        assert len(data["marks"]) == 28
        assert data["contributions_pct"][0] is None  # пистон — не аберрация
        shares = [s for s in data["contributions_pct"]
                  if s is not None]
        assert sum(shares) == pytest.approx(100.0, abs=1e-6)
        assert 0.0 < data["strehl_zernike"] <= 1.0

    def test_protocol_text(self, demo_files):
        data = run("zern.protocol", {"file": demo_files[1]})
        assert "РАЗЛОЖЕНИЕ ЦЕРНИКЕ" in data["text"]
        assert "C x20" in data["text"]


def _classic_terms_reference():
    from analysis.zernike import ZERNIKE_TERMS
    return ZERNIKE_TERMS


# --------------------------------------------------------------------------- #
# focus.* — критерии оптимального фокуса
# --------------------------------------------------------------------------- #

class TestFocusCommands:
    def test_min_rms_matches_domain(self, demo_files, system):
        from analysis.focus_criteria import focus_min_rms_wavefront
        direct = focus_min_rms_wavefront(system, field=0.0, wl=WL)
        data = run("focus.min_rms", {"file": demo_files[1], "wl": WL})
        assert data["dz_mm"] == pytest.approx(direct, abs=1e-12)

    def test_all_criteria_close_for_mild_aberrations(self, demo_files):
        """Демо-ахромат: волновые критерии согласны в доли мм."""
        values = {
            key: run(f"focus.{key}", {"file": demo_files[1], "wl": WL})["dz_mm"]
            for key in ("min_rms", "max_strehl", "zone_best")}
        assert all(abs(v) < 5.0 for v in values.values())
        wave = [values["min_rms"], values["max_strehl"],
                values["zone_best"]]
        assert max(wave) - min(wave) < 0.5

    def test_min_spot_matches_domain(self, demo_files, system):
        from analysis.focus_criteria import focus_min_spot_rms
        direct = focus_min_spot_rms(system, field=0.0, wl=WL)
        data = run("focus.min_spot", {"file": demo_files[1], "wl": WL})
        assert data["dz_mm"] == pytest.approx(direct, abs=1e-12)

    def test_eqf_contract(self, demo_files):
        data = run("focus.eqf", {"file": demo_files[1], "wl": WL})
        assert data["converged"] in (True, False)
        assert "hypothesis" in data and data["hypothesis"]
        if data["converged"]:
            assert data["rms_in"] == pytest.approx(data["rms_out"],
                                                   rel=0.01)
            assert data["residual"] == pytest.approx(0.0, abs=1e-6)

    def test_all_summary(self, demo_files, system):
        from analysis.focus_criteria import all_focus_criteria
        direct = all_focus_criteria(system, field=0.0, wl=WL)
        data = run("focus.all", {"file": demo_files[1], "wl": WL})
        for key in ("min_rms_wavefront_mm", "max_strehl_mm",
                    "min_spot_rms_mm", "zone_best_mm", "eqf_mm",
                    "best_opal_mm"):
            assert data[key] == pytest.approx(direct[key], abs=1e-12)
        assert data["meta"]["f_number"] > 0
        assert data["best_opal_source"] in ("eqf", "min_rms_wavefront")


# --------------------------------------------------------------------------- #
# Контракт ошибок
# --------------------------------------------------------------------------- #

class TestErrors:
    def test_no_system_source(self):
        fail("focus.min_rms", {}, "no_system")

    def test_target_missing_freq(self, demo_files):
        fail("psf.target", {"file": demo_files[1]}, "missing_param")

    def test_target_bad_orientation(self, demo_files):
        fail("psf.target", {"file": demo_files[1], "freq_lpmm": 50.0,
                            "orientation": "diag"}, "invalid_param")

    def test_marechal_bad_sigma(self):
        fail("strehl.marechal", {"sigma_w": "abc"}, "invalid_param")

    def test_marechal_missing_sigma(self):
        fail("strehl.marechal", {}, "missing_param")

    def test_fit_points_too_few(self):
        fail("zern.fit_points",
             {"points": _defocus_points(5, 0.1)}, "invalid_param")

    def test_coeffs_fit_bad_point(self):
        fail("zern.coeffs.fit", {"points": [[1.0, 2.0]]},
             "invalid_param")

    def test_strehl_bad_coeffs(self):
        fail("zern.strehl", {"coeffs": ["a", "b"]}, "invalid_param")

    def test_reconstruct_empty_coeffs(self):
        fail("zern.reconstruct", {"coeffs": []}, "invalid_param")

    def test_unknown_param(self, demo_files):
        fail("zern.decompose", {"file": demo_files[1],
                                "no_such": 1}, "unknown_param")


# --------------------------------------------------------------------------- #
# CLI (subprocess): домен виден из командной строки
# --------------------------------------------------------------------------- #

class TestCli:
    def test_run_strehl_marechal(self):
        proc, payload = run_cli_json(
            ["run", "strehl.marechal", "--param", "sigma_w=0.05"])
        assert proc.returncode == 0
        assert payload["ok"] is True
        assert payload["data"]["strehl"] == pytest.approx(
            math.exp(-((2 * math.pi * 0.05) ** 2)), rel=1e-9)

    def test_list_category_focus(self):
        proc, payload = run_cli_json(["list", "--category", "focus"])
        assert proc.returncode == 0
        names = [c["name"] for c in payload["commands"]]
        assert len(names) == 6
        assert names[0] == "focus.all"
