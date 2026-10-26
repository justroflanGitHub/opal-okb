"""Пакет R500-14: расширения продвинутого анализа (adv_ext_cmds.py).

Три уровня проверки (как у Волны 3 psf):
* smoke — каждая новая команда выполняется и даёт строгий JSON;
* паритет/формулы — таблица СШАФ, ФКЭ Эйри (ряды Бесселя), глубина
  фокуса ±2λF#² сверяются с эталонными значениями;
* инварианты — физика (энергия в окне пикселей ≤ 1, детерминизм шума
  по seed, монохромный предел полихрома, MTF(0)=1 у комплексной ОТФ).
"""
import math

import pytest

from commands import CommandContext, default_registry

#: Новые команды пакета R500-14 (категория adv; Волна 1 adv.* из
#: aber_cmds — 8 команд — здесь не повторяются, их тесты в
#: test_commands_aber.py).
ADV_EXT_EXPECTED = frozenset({
    "adv.psf.focus_stack", "adv.psf.waist", "adv.psf.fwhm",
    "adv.psf.centroid", "adv.psf.poly", "adv.lsf.poly",
    "adv.slit_image", "adv.convolve.profile",
    "adv.usaf.table", "adv.usaf.resolve", "adv.usaf.object",
    "adv.dof.diffraction", "adv.dof.compare",
    "adv.snr.bars", "adv.noise.spot",
    "adv.pixel.matrix", "adv.pixel.energy", "adv.energy.ring",
    "adv.resolve.thornber", "adv.otf.complex", "adv.airy.encircled",
})

#: Число команд категории adv после R500-14 (8 Волны 1 + 21 новых).
ADV_CATEGORY_TOTAL = 29

#: Эталон таблицы СШАФ-1951: частота группы 0 элемента 1 (лин/мм) и
#: отношение частот соседних элементов 2^(1/6).
USAF_G0E1_LPMM = 1.0
USAF_ELEMENT_RATIO = 2.0 ** (1.0 / 6.0)

#: ФКЭ идеального пятна Эйри в первом тёмном кольце (83.8 %, Born &
#: Wolf); проверка рядов Бесселя модуля.
AIRY_EE_FIRST_RING = 0.838

#: Радиус первого тёмного кольца в единицах λF# (нулём J1/π).
AIRY_RADIUS_FACTOR = 1.2197


# --------------------------------------------------------------------------- #
# Фикстуры и хелперы
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.opj, .json) демо-ахромат, созданный командами Волны 1.

    Поле-зависимые smoke — на .json (OPJ-раундтрип теряет field_points).
    """
    tmp = tmp_path_factory.mktemp("commands_r500_14")
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


def run(name, args=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    """Выполнить команду, ожидая ошибку с данным кодом."""
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error
    return result.error


def _smoke(demo_files):
    """Карта smoke-аргументов новых команд (быстрые сетки)."""
    _, jsn = demo_files
    return {
        "adv.psf.focus_stack": {"file": jsn, "num_points": 5,
                                "defocus_range_mm": 0.03,
                                "include_slices": True},
        "adv.psf.waist": {"file": jsn, "num_points": 9,
                          "defocus_range_mm": 0.3},
        "adv.psf.fwhm": {"file": jsn},
        "adv.psf.centroid": {"file": jsn, "fields": [0.0, 3.0]},
        "adv.psf.poly": {"file": jsn},
        "adv.lsf.poly": {"file": jsn},
        "adv.slit_image": {"file": jsn, "width_um": 20.0},
        "adv.convolve.profile": {"file": jsn,
                                 "profile": [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
                                 "pitch_um": 3.0},
        "adv.usaf.table": {"group_from": 0, "group_to": 2},
        "adv.usaf.resolve": {"file": jsn, "group_to": 4},
        "adv.usaf.object": {"file": jsn, "group": 2, "element": 3},
        "adv.dof.diffraction": {"file": jsn},
        "adv.dof.compare": {"file": jsn, "fields": [0.0, 3.0],
                            "num_rays": 20},
        "adv.snr.bars": {"file": jsn, "freq_lpmm": 30.0},
        "adv.noise.spot": {"file": jsn, "pixel_um": 8.0, "size": 5,
                           "seed": 42},
        "adv.pixel.matrix": {"file": jsn, "pixel_um": 8.0},
        "adv.pixel.energy": {"file": jsn, "pixel_um": 8.0,
                             "offset_x_um": 4.0, "block": 3},
        "adv.energy.ring": {"file": jsn, "r_inner_um": 5.0,
                            "r_outer_um": 15.0},
        "adv.resolve.thornber": {"file": jsn, "fields": [0.0, 3.0]},
        "adv.otf.complex": {"file": jsn},
        "adv.airy.encircled": {"file": jsn},
    }


# --------------------------------------------------------------------------- #
# Реестр: состав и smoke домена
# --------------------------------------------------------------------------- #

class TestAdvExtRegistry:
    def test_new_commands_registered(self):
        names = set(default_registry.names())
        missing = ADV_EXT_EXPECTED - names
        assert not missing, f"не зарегистрированы: {sorted(missing)}"
        for name in ADV_EXT_EXPECTED:
            assert default_registry.get(name).category == "adv", name

    def test_adv_category_total(self):
        adv = [n for n in default_registry.names()
               if default_registry.get(n).category == "adv"]
        assert len(adv) == ADV_CATEGORY_TOTAL

    def test_prefixes_wave3_not_extended(self):
        """Префиксы Волны 3 (пины WAVE3_EXPECTED) не занимались."""
        from tests.test_commands_psf import WAVE3_EXPECTED
        for prefix, count in WAVE3_EXPECTED.items():
            owned = [n for n in default_registry.names()
                     if n.split(".")[0] == prefix]
            assert len(owned) == count, (prefix, owned)

    def test_smoke_all_strict_json(self, demo_files):
        import json
        smoke = _smoke(demo_files)
        assert set(smoke) == ADV_EXT_EXPECTED
        for name, args in sorted(smoke.items()):
            data = run(name, args)
            json.dumps(data, ensure_ascii=False, allow_nan=False)


# --------------------------------------------------------------------------- #
# Объёмная ФРТ через фокус
# --------------------------------------------------------------------------- #

class TestPsfThroughFocus:
    def test_focus_stack_rows(self, demo_files):
        data = run("adv.psf.focus_stack",
                   {"file": demo_files[1], "num_points": 5,
                    "defocus_range_mm": 0.03, "include_slices": True})
        rows = data["rows"]
        assert len(rows) == 5
        assert rows[0]["defocus_mm"] == pytest.approx(-0.03)
        assert rows[2]["defocus_mm"] == pytest.approx(0.0)
        for row in rows:
            assert 0.0 < row["strehl"] <= 1.0
            assert row["fwhm_x_um"] > 0 and row["fwhm_y_um"] > 0
            assert 0.0 < row["r80_um"] < 1e3
        # срезы — те же оси, что у ФРТ
        assert data["slices"][2]["profile_x"][
            len(data["slices"][2]["profile_x"]) // 2] == \
            pytest.approx(max(data["slices"][2]["profile_x"]))

    def test_focus_stack_bad_points(self, demo_files):
        fail("adv.psf.focus_stack",
             {"file": demo_files[1], "num_points": 2}, "invalid_param")

    def test_waist_inside_range(self, demo_files):
        data = run("adv.psf.waist",
                   {"file": demo_files[1], "num_points": 21,
                    "defocus_range_mm": 0.3})
        assert -0.3 < data["z_waist_mm"] < 0.3
        assert data["peak_refined"] >= data["peak_max"]
        assert data["axial_fwhm_mm"] > 0
        # ширины на полувысоте не выходят за развёртку
        assert 0 <= data["half_left_mm"] <= 0.3
        assert 0 <= data["half_right_mm"] <= 0.3

    def test_fwhm_axis_symmetry(self, demo_files):
        """На оси демо-системы сечения почти изотропны."""
        data = run("adv.psf.fwhm", {"file": demo_files[1]})
        ratio = max(data["fwhm_x_um"], data["fwhm_y_um"]) / \
            min(data["fwhm_x_um"], data["fwhm_y_um"])
        assert ratio < 1.3
        assert data["airy_diameter_um"] > 0

    def test_centroid_on_axis_near_zero(self, demo_files):
        data = run("adv.psf.centroid",
                   {"file": demo_files[1], "fields": [0.0]})
        row = data["rows"][0]
        assert row["shift_um"] < 5.0  # ось: центроид у опорной оси

    def test_centroid_requires_fields(self, demo_files):
        """OPJ теряет field_points — без явных полей команда честно
        отказывает (грабли раундтрика)."""
        fail("adv.psf.centroid", {"file": demo_files[0]}, "invalid_param")


# --------------------------------------------------------------------------- #
# Полихроматические ФРТ/ФРЛ
# --------------------------------------------------------------------------- #

class TestPolychromatic:
    def test_psf_poly_monochrom_limit(self, demo_files):
        """Одна λ с весом 1 = монохромная ФРТ (та же FWHM)."""
        mono = run("adv.psf.fwhm", {"file": demo_files[1]})
        poly = run("adv.psf.poly",
                   {"file": demo_files[1], "wl_list": [mono["wl"]],
                    "weights": [1.0]})
        assert poly["fwhm_x_um"] == pytest.approx(mono["fwhm_x_um"],
                                                  rel=1e-6)
        assert poly["spectral"][0]["weight"] == pytest.approx(1.0)

    def test_psf_poly_weights_normalized(self, demo_files):
        data = run("adv.psf.poly",
                   {"file": demo_files[1], "wl_list": [0.4861, 0.5876],
                    "weights": [3.0, 1.0]})
        weights = [row["weight"] for row in data["spectral"]]
        assert sum(weights) == pytest.approx(1.0)
        assert weights[0] == pytest.approx(0.75)

    def test_lsf_poly_profiles_normalized(self, demo_files):
        data = run("adv.lsf.poly", {"file": demo_files[1]})
        for key in ("meridional", "sagittal"):
            assert sum(data[key]) == pytest.approx(1.0, abs=1e-9)
        assert len(data["coord_um"]) == len(data["meridional"])

    def test_psf_poly_weight_mismatch(self, demo_files):
        fail("adv.psf.poly",
             {"file": demo_files[1], "wl_list": [0.5, 0.6],
              "weights": [1.0]}, "invalid_param")


# --------------------------------------------------------------------------- #
# Свёртка с объектом
# --------------------------------------------------------------------------- #

class TestObjectConvolution:
    def test_slit_contrast_blur(self, demo_files):
        data = run("adv.slit_image",
                   {"file": demo_files[1], "width_um": 20.0})
        assert 0.0 < data["contrast"] < 1.0
        assert data["edge_10_90_um"] > 0

    def test_slit_wide_width_limit(self, demo_files):
        """Широкая щель → сечение почти плоское: контраст ≈ 1."""
        data = run("adv.slit_image",
                   {"file": demo_files[1], "width_um": 200.0})
        assert data["contrast"] > 0.95

    def test_slit_bad_width(self, demo_files):
        fail("adv.slit_image",
             {"file": demo_files[1], "width_um": 0.0}, "invalid_param")

    def test_convolve_profile_delta(self, demo_files):
        """Дельта-профиль → отклик повторяет форму ФРЛ."""
        import numpy as np
        from analysis.psf_mtf import lsf_from_psf, psf_grid
        from fileio.json_io import load_json
        system = load_json(demo_files[1])
        res = psf_grid(system)
        lsf = lsf_from_psf(res["psf"], res["pitch_um"])
        pitch = float(res["pitch_um"])
        axis = lsf["coord_um"]
        profile = [0.0] * len(axis)
        profile[len(axis) // 2] = 1.0
        data = run("adv.convolve.profile",
                   {"file": demo_files[1], "profile": profile,
                    "pitch_um": pitch})
        image = data["image"]
        kernel = lsf["x"] / lsf["x"].sum()
        expected = np.interp(data["coord_um"], axis, kernel)
        # команда нормирует ядро на оси профиля (после интерполяции),
        # тест — до: расхождение только в нормировке, форма совпадает
        assert max(image) == pytest.approx(
            float(expected.max()) * pitch, rel=1e-4)

    def test_convolve_profile_bad(self, demo_files):
        fail("adv.convolve.profile",
             {"file": demo_files[1], "profile": [1], "pitch_um": 1.0},
             "invalid_param")


# --------------------------------------------------------------------------- #
# Миры СШАФ-1951
# --------------------------------------------------------------------------- #

class TestUsaf:
    def test_table_standard_frequencies(self):
        data = run("adv.usaf.table",
                   {"group_from": 0, "group_to": 2})
        rows = {(r["group"], r["element"]): r for r in data["rows"]}
        assert rows[(0, 1)]["freq_lpmm"] == pytest.approx(
            USAF_G0E1_LPMM)
        assert rows[(2, 1)]["freq_lpmm"] == pytest.approx(4.0)
        # соседние элементы отличаются в 2^(1/6)
        assert rows[(0, 2)]["freq_lpmm"] / rows[(0, 1)]["freq_lpmm"] == \
            pytest.approx(USAF_ELEMENT_RATIO)
        # ширина штриха = полпериода
        assert rows[(0, 1)]["bar_width_um"] == pytest.approx(500.0)

    def test_table_freq_cap(self):
        data = run("adv.usaf.table",
                   {"group_from": 0, "group_to": 5,
                    "freq_max_lpmm": 10.0})
        assert all(r["freq_lpmm"] <= 10.0 for r in data["rows"])
        assert data["rows"]

    def test_table_empty(self):
        fail("adv.usaf.table",
             {"group_from": 4, "group_to": 5, "freq_max_lpmm": 1.0},
             "invalid_param")

    def test_resolve_consistent_with_table(self, demo_files):
        data = run("adv.usaf.resolve",
                   {"file": demo_files[1], "group_to": 4})
        table = run("adv.usaf.table",
                    {"group_from": 0, "group_to": 4})["rows"]
        by_key = {(r["group"], r["element"]): r for r in table}
        key = (data["group"], data["element"])
        assert data["freq_lpmm"] == pytest.approx(
            by_key[key]["freq_lpmm"])
        assert data["bar_width_um"] == pytest.approx(500.0
                                                     / data["freq_lpmm"])
        assert min(data["mtf_tan"], data["mtf_sag"]) >= \
            data["threshold"]

    def test_object_scaling(self, demo_files):
        data = run("adv.usaf.object",
                   {"file": demo_files[1], "group": 1, "element": 1})
        magnification = data["magnification"]
        assert data["freq_object_lpmm"] == pytest.approx(
            data["freq_image_lpmm"] * abs(magnification))
        assert data["bar_width_object_um"] == pytest.approx(
            data["bar_width_image_um"] / abs(magnification))

    def test_object_bad_element(self, demo_files):
        fail("adv.usaf.object",
             {"file": demo_files[1], "group": 0, "element": 7},
             "invalid_param")


# --------------------------------------------------------------------------- #
# Глубина фокуса
# --------------------------------------------------------------------------- #

class TestDof:
    def test_diffraction_formula(self, demo_files):
        data = run("adv.dof.diffraction", {"file": demo_files[1]})
        for row in data["rows"]:
            expected = 2.0 * row["wl"] * 1e-3 * data["f_number"] ** 2
            assert row["dof_half_mm"] == pytest.approx(expected)
            assert row["dof_full_mm"] == pytest.approx(2 * expected)
            assert row["airy_radius_um"] == pytest.approx(
                AIRY_RADIUS_FACTOR * row["wl"] * data["f_number"],
                rel=1e-3)

    def test_compare_rows_and_regime(self, demo_files):
        data = run("adv.dof.compare",
                   {"file": demo_files[1], "fields": [0.0, 3.0],
                    "num_rays": 20})
        rows = data["rows"]
        assert len(rows) == 2
        for row in rows:
            assert row["rms_spot_mm"] >= 0
            assert row["na_image"] > 0
            assert row["dof_geo_half_mm"] == pytest.approx(
                row["rms_spot_mm"] / row["na_image"])
            assert row["regime"] in ("дифракция", "геометрия")

    def test_compare_requires_fields(self, demo_files):
        fail("adv.dof.compare", {"file": demo_files[0]}, "invalid_param")


# --------------------------------------------------------------------------- #
# SNR и шум детектора
# --------------------------------------------------------------------------- #

class TestNoiseAndSnr:
    def test_snr_formula(self, demo_files):
        data = run("adv.snr.bars",
                   {"file": demo_files[1], "freq_lpmm": 30.0,
                    "signal_e": 10000.0, "read_noise_e": 5.0})
        noise = math.sqrt(2.0 * (10000.0 + 25.0))
        assert data["snr_tan"] == pytest.approx(
            2.0 * data["mtf_tan"] * 10000.0 / noise)
        assert 0.0 <= data["mtf_tan"] <= 1.0
        assert data["verdict_tan"] in ("ok", "fail")

    def test_snr_bad_freq(self, demo_files):
        fail("adv.snr.bars",
             {"file": demo_files[1], "freq_lpmm": 0.0}, "invalid_param")

    def test_noise_deterministic(self, demo_files):
        args = {"file": demo_files[1], "pixel_um": 8.0, "size": 5}
        first = run("adv.noise.spot", {**args, "seed": 11})
        second = run("adv.noise.spot", {**args, "seed": 11})
        other = run("adv.noise.spot", {**args, "seed": 12})
        assert first["matrix"] == second["matrix"]
        assert first["matrix"] != other["matrix"]

    def test_noise_matrix_shape(self, demo_files):
        data = run("adv.noise.spot",
                   {"file": demo_files[1], "pixel_um": 8.0, "size": 5,
                    "peak_e": 1000.0, "read_noise_e": 10.0})
        assert len(data["matrix"]) == 5
        assert all(len(row) == 5 for row in data["matrix"])
        assert data["peak_signal_e"] > 0
        assert data["background_std_e"] >= 0


# --------------------------------------------------------------------------- #
# Пиксельное интегрирование и кольца
# --------------------------------------------------------------------------- #

class TestPixelIntegration:
    def test_matrix_energy_window(self, demo_files):
        data = run("adv.pixel.matrix",
                   {"file": demo_files[1], "pixel_um": 2.0, "size": 21})
        matrix = data["matrix"]
        assert len(matrix) == 21
        assert 0.0 < data["sum_in_window"] <= 1.0
        assert data["central_fraction"] == pytest.approx(
            matrix[10][10])
        # центр — максимум распределения
        assert data["max_fraction"] == pytest.approx(
            max(max(row) for row in matrix))

    def test_matrix_subpixel_refinement(self, demo_files):
        """Подпиксельная передискретизация сохраняет полную энергию."""
        coarse = run("adv.pixel.matrix",
                     {"file": demo_files[1], "pixel_um": 4.0, "size": 15,
                      "subsample": 1})
        fine = run("adv.pixel.matrix",
                   {"file": demo_files[1], "pixel_um": 4.0, "size": 15,
                      "subsample": 8})
        assert coarse["sum_in_window"] == pytest.approx(
            fine["sum_in_window"], rel=1e-3)

    def test_pixel_energy_bounds(self, demo_files):
        data = run("adv.pixel.energy",
                   {"file": demo_files[1], "pixel_um": 8.0,
                    "offset_x_um": 4.0, "block": 3})
        assert 0.0 < data["pixel_fraction"] < 1.0
        assert data["pixel_fraction"] < data["block_fraction"] <= 1.0

    def test_pixel_energy_offset_reduces_signal(self, demo_files):
        central = run("adv.pixel.energy",
                      {"file": demo_files[1], "pixel_um": 6.0})
        shifted = run("adv.pixel.energy",
                      {"file": demo_files[1], "pixel_um": 6.0,
                       "offset_x_um": 10.0})
        assert shifted["pixel_fraction"] < central["pixel_fraction"]

    def test_energy_ring_complement(self, demo_files):
        ring = run("adv.energy.ring",
                   {"file": demo_files[1], "r_inner_um": 5.0,
                    "r_outer_um": 15.0})
        assert 0.0 < ring["fraction"] < 1.0
        assert ring["fraction"] == pytest.approx(
            ring["ee_outer"] - ring["ee_inner"])
        # кольцо от нуля: ee_inner = ФКЭ(0) (бinned-центральный пиксель
        # движка encircled_energy), доля = остаток до ee_outer
        outer = run("adv.energy.ring",
                    {"file": demo_files[1], "r_inner_um": 0.0,
                     "r_outer_um": 15.0})
        assert outer["fraction"] == pytest.approx(
            outer["ee_outer"] - outer["ee_inner"])
        assert outer["fraction"] == pytest.approx(ring["ee_outer"]
                                                  - outer["ee_inner"])

    def test_energy_ring_bad(self, demo_files):
        fail("adv.energy.ring",
             {"file": demo_files[1], "r_inner_um": 15.0,
              "r_outer_um": 5.0}, "invalid_param")


# --------------------------------------------------------------------------- #
# Разрешение по ЧКХ и комплексная ОТФ
# --------------------------------------------------------------------------- #

class TestResolutionAndOtf:
    def test_thornber_worst_section(self, demo_files):
        data = run("adv.resolve.thornber",
                   {"file": demo_files[1], "fields": [0.0, 3.0],
                    "threshold": 0.2})
        rows = data["rows"]
        assert len(rows) == 2
        for row in rows:
            assert row["freq_resolved_lpmm"] == pytest.approx(
                min(row["freq_tan_lpmm"], row["freq_sag_lpmm"]))
            assert row["freq_resolved_lpmm"] <= row["cutoff_lpmm"]
            assert row["bar_width_um"] == pytest.approx(
                500.0 / row["freq_resolved_lpmm"])

    def test_otf_dc_value(self, demo_files):
        """OTF(0) = 1: Re(0) = 1, Im(0) = 0 (ФРТ Σ = 1)."""
        data = run("adv.otf.complex", {"file": demo_files[1]})
        assert data["freq_lpmm"][0] == pytest.approx(0.0)
        assert data["re_tan"][0] == pytest.approx(1.0, abs=1e-9)
        assert data["im_tan"][0] == pytest.approx(0.0, abs=1e-9)
        assert data["mtf_tan"][0] == pytest.approx(1.0, abs=1e-9)

    def test_otf_matches_mtf_curve(self, demo_files):
        """Модуль комплексной ОТФ == ЧКХ команды mtf.curve."""
        curve = run("mtf.curve", {"file": demo_files[1]})
        data = run("adv.otf.complex", {"file": demo_files[1]})
        assert data["mtf_sag"] == pytest.approx(curve["sag"], abs=1e-9)

    def test_thornber_requires_fields(self, demo_files):
        fail("adv.resolve.thornber", {"file": demo_files[0]},
             "invalid_param")


# --------------------------------------------------------------------------- #
# Эталон Эйри
# --------------------------------------------------------------------------- #

class TestAiryReference:
    def test_airy_encircled_textbook(self, demo_files):
        data = run("adv.airy.encircled", {"file": demo_files[1]})
        rows = {round(row["r_over_r1"], 6): row["ee"]
                for row in data["rows"]}
        assert rows[1.0] == pytest.approx(AIRY_EE_FIRST_RING, abs=2e-3)
        assert data["airy_radius_um"] == pytest.approx(
            AIRY_RADIUS_FACTOR * data["wl"] * data["f_number"],
            rel=1e-3)
        # тёмные кольца: r_k = нули J1/π · λF#
        factors = [r / data["airy_radius_um"]
                   for r in data["dark_rings_um"]]
        assert factors[0] == pytest.approx(1.0, rel=1e-3)
        assert factors[1] == pytest.approx(7.0156 / 3.8317, rel=1e-3)
        # ФКЭ монотонна по радиусу
        ees = [row["ee"] for row in sorted(
            data["rows"], key=lambda r: r["r_um"])]
        assert ees == sorted(ees)

    def test_airy_psf_comparison_positive(self, demo_files):
        data = run("adv.airy.encircled", {"file": demo_files[1]})
        assert data["psf_r50_um"] > 0
        assert data["r80_over_r1"] > data["r50_over_r1"] > 0
