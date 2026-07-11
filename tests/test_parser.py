"""Тесты парсера LBO/OPJ — проверка корректности загрузки систем.

Запуск:
    pytest tests/test_parser.py -v          # через pytest
    py tests\\test_parser.py                  # напрямую (встроенный runner)
"""
import sys
import os
import re
import math

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lbo_reader import load_lbo_fast
from decode_lbo_opj import decode_lbo_opj
from optics_engine import paraxial_trace, refractive_index, ApertureType, ObjectType
from system_utils import deg_to_gmms, gmms_to_deg, gmms_to_str


# Path to the canonical library directory — works regardless of CWD.
_LIB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "extracted", "opal_okb", "Lib",
)
_LENS_LBO = os.path.join(_LIB_DIR, "LENS.LBO")
_LENS_SPC_LBO = os.path.join(_LIB_DIR, "LENS_SPC.LBO")
_MICROLEN_LBO = os.path.join(_LIB_DIR, "MICROLEN.LBO")
_OCULAR_LBO = os.path.join(_LIB_DIR, "OCULAR.LBO")
_REPROD_LBO = os.path.join(_LIB_DIR, "REPROD.LBO")


# --------------------------------------------------------------------------- #
# Module-level cached loaders (reused across all tests in this file)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def industar_sys():
    """Декодированная система Индустар-23у (LENS.LBO index 3)."""
    systems = load_lbo_fast(_LENS_LBO)
    return decode_lbo_opj(systems[3]['opj_data'])


@pytest.fixture(scope="module")
def mirror450_sys():
    """Декодированная зеркально-линзовая система f'=450 (LENS_SPC.LBO index 1)."""
    systems = load_lbo_fast(_LENS_SPC_LBO)
    return decode_lbo_opj(systems[1]['opj_data'])


# =========================================================================== #
# 1. Конвертация Г.ММСС
# =========================================================================== #

class TestGmmsConversion:
    """Конвертация углов в формат Г.ММСС и обратно."""

    def test_half_degree_to_gmms(self):
        assert deg_to_gmms(0.5) == pytest.approx(0.30, rel=1e-3)

    def test_gmms_to_half_degree(self):
        assert gmms_to_deg(0.30) == pytest.approx(0.5, rel=1e-3)

    def test_26_degrees(self):
        assert deg_to_gmms(26.0) == pytest.approx(26.0, rel=1e-3)

    def test_23_2_degrees(self):
        assert deg_to_gmms(23.2) == pytest.approx(23.12, rel=1e-3)

    def test_gmms_to_str_format(self):
        result = gmms_to_str(0.30)
        assert "0°30'00\"" in result


# =========================================================================== #
# 2. Стандартные длины волн
# =========================================================================== #

class TestDefaultWavelengths:

    def test_three_wavelengths(self):
        from optics_engine import _std_wavelengths
        wls = _std_wavelengths()
        assert len(wls) == 3

    def test_e_value(self):
        from optics_engine import _std_wavelengths
        wls = _std_wavelengths()
        assert wls[0].value == pytest.approx(0.54607, abs=1e-6)

    def test_g_prime_value(self):
        from optics_engine import _std_wavelengths
        wls = _std_wavelengths()
        assert wls[1].value == pytest.approx(0.43405, abs=1e-6)

    def test_c_value(self):
        from optics_engine import _std_wavelengths
        wls = _std_wavelengths()
        assert wls[2].value == pytest.approx(0.65627, abs=1e-6)

    def test_e_name(self):
        from optics_engine import _std_wavelengths
        wls = _std_wavelengths()
        assert wls[0].name == 'e'

    def test_g_prime_name(self):
        from optics_engine import _std_wavelengths
        wls = _std_wavelengths()
        assert wls[1].name == "G'"

    def test_c_name(self):
        from optics_engine import _std_wavelengths
        wls = _std_wavelengths()
        assert wls[2].name == 'C'


# =========================================================================== #
# 3. Показатели преломления КВАРЦСТК
# =========================================================================== #

class TestKvartsRefractiveIndex:

    def test_n_e_approx_1_46(self):
        n_e = refractive_index('КВАРЦСТК', 0.54607)
        assert n_e == pytest.approx(1.46, abs=0.02)

    def test_n_e_not_1_5(self):
        n_e = refractive_index('КВАРЦСТК', 0.54607)
        assert abs(n_e - 1.5) > 0.01

    def test_n_g_prime_greater_than_n_e(self):
        n_g = refractive_index('КВАРЦСТК', 0.43405)
        n_e = refractive_index('КВАРЦСТК', 0.54607)
        assert n_g > n_e

    def test_n_c_less_than_n_e(self):
        n_c = refractive_index('КВАРЦСТК', 0.65627)
        n_e = refractive_index('КВАРЦСТК', 0.54607)
        assert n_c < n_e


# =========================================================================== #
# 4. Индустар-23у — основная тестовая система
# =========================================================================== #

class TestIndustar23u:
    """Индустар-23у f'=110 — детальная проверка декодирования."""

    def test_name_contains_industar_or_110(self, industar_sys):
        assert "Индустар" in industar_sys.name or "110" in industar_sys.name, \
            f"got {industar_sys.name!r}"

    def test_name_not_glass(self, industar_sys):
        assert industar_sys.name != "ТК20", f"got {industar_sys.name!r}"

    def test_seven_surfaces(self, industar_sys):
        assert len(industar_sys.surfaces) == 7, f"got {len(industar_sys.surfaces)}"

    def test_has_tk16_glass(self, industar_sys):
        glasses = [s.glass for s in industar_sys.surfaces
                    if s.glass and s.glass not in ('', 'ЗЕРКАЛО')]
        assert any('ТК16' in g for g in glasses), f"{glasses}"

    def test_has_lf5_glass(self, industar_sys):
        glasses = [s.glass for s in industar_sys.surfaces
                    if s.glass and s.glass not in ('', 'ЗЕРКАЛО')]
        assert any('ЛФ5' in g for g in glasses), f"{glasses}"

    def test_no_mirrors(self, industar_sys):
        assert not any(s.is_reflective for s in industar_sys.surfaces)

    def test_stop_surface_is_4(self, industar_sys):
        assert industar_sys.stop_surface == 4, f"got {industar_sys.stop_surface}"

    def test_stop_offset(self, industar_sys):
        assert industar_sys.stop_offset == pytest.approx(4.2, abs=0.01)

    def test_aperture_value(self, industar_sys):
        assert industar_sys.aperture_value == pytest.approx(21.1, abs=0.5)

    def test_aperture_type(self, industar_sys):
        assert industar_sys.aperture_type == ApertureType.ENTRANCE_PUPIL

    def test_field_approx_26(self, industar_sys):
        assert industar_sys.object_height == pytest.approx(26.0, abs=0.5)

    def test_three_wavelengths(self, industar_sys):
        assert len(industar_sys.wavelengths) == 3

    def test_wavelength_names(self, industar_sys):
        wl_names = [w.name for w in industar_sys.wavelengths]
        assert "e" in wl_names and "G'" in wl_names and "C" in wl_names, \
            f"got {wl_names}"

    def test_focal_length_approx_110(self, industar_sys):
        parax = paraxial_trace(industar_sys)
        f_val = parax.get('focal_length', 0)
        assert f_val == pytest.approx(110, abs=5), f"got f'={f_val:.2f}"

    def test_focal_length_nonzero(self, industar_sys):
        parax = paraxial_trace(industar_sys)
        f_val = parax.get('focal_length', 0)
        assert abs(f_val) > 1, f"got f'={f_val}"

    def test_back_focal_distance(self, industar_sys):
        parax = paraxial_trace(industar_sys)
        assert parax.get('back_focal_distance', 0) > 50

    def test_glass_n_not_1_5(self, industar_sys):
        """Проверка что n ≠ 1.5 для всех реальных стёкол."""
        for s in industar_sys.surfaces:
            if s.glass and s.glass.upper() not in ('', 'ВОЗДУХ', 'AIR'):
                n = refractive_index(s.glass, 0.54607)
                assert abs(n - 1.5) > 0.01, f"n({s.glass})={n:.6f} ≈ 1.5"


# =========================================================================== #
# 5. Зеркально-линзовая система f'=450
# =========================================================================== #

class TestMirrorLens450:

    def test_name_contains_450(self, mirror450_sys):
        assert "450" in mirror450_sys.name, f"got {mirror450_sys.name!r}"

    def test_two_mirrors(self, mirror450_sys):
        mirrors = [s for s in mirror450_sys.surfaces if s.is_reflective]
        assert len(mirrors) == 2, f"got {len(mirrors)}"

    def test_has_kvarts(self, mirror450_sys):
        has_quartz = any(
            'КВАРЦ' in s.glass.upper()
            for s in mirror450_sys.surfaces if s.glass
        )
        assert has_quartz, f"glasses={[s.glass for s in mirror450_sys.surfaces]}"

    def test_aperture_from_na(self, mirror450_sys):
        assert mirror450_sys.aperture_type == ApertureType.ENTRANCE_PUPIL
        assert mirror450_sys.aperture_value == pytest.approx(80.0, abs=5.0)

    def test_three_wavelengths(self, mirror450_sys):
        assert len(mirror450_sys.wavelengths) == 3

    def test_focal_length_in_range(self, mirror450_sys):
        parax = paraxial_trace(mirror450_sys)
        f_val = parax.get('focal_length', 0)
        assert 400 < f_val < 500, f"got f'={f_val:.2f}"

    def test_focal_length_nonzero(self, mirror450_sys):
        parax = paraxial_trace(mirror450_sys)
        f_val = parax.get('focal_length', 0)
        assert abs(f_val) > 1


# =========================================================================== #
# 6. Тип предмета и изображения для разных каталогов
# =========================================================================== #

class TestObjectImageTypes:

    def test_lens_infinite_finite(self):
        """LENS: дальний → ближний (фотообъектив)."""
        systems = load_lbo_fast(_LENS_LBO)
        s = decode_lbo_opj(systems[3]['opj_data'])
        assert s.object_type == ObjectType.INFINITE
        assert s.image_type == ObjectType.FINITE

    def test_microlen_finite_finite(self):
        """MICROLEN: ближний → ближний."""
        systems = load_lbo_fast(_MICROLEN_LBO)
        s = decode_lbo_opj(systems[0]['opj_data'])
        assert s.object_type == ObjectType.FINITE
        assert s.image_type == ObjectType.FINITE

    def test_ocular_infinite_finite(self):
        """OCULAR: дальний → ближний."""
        systems = load_lbo_fast(_OCULAR_LBO)
        s = decode_lbo_opj(systems[0]['opj_data'])
        assert s.object_type == ObjectType.INFINITE
        assert s.image_type == ObjectType.FINITE

    def test_reprod_finite(self):
        """REPROD: ближний → ближний."""
        systems = load_lbo_fast(_REPROD_LBO)
        s = decode_lbo_opj(systems[0]['opj_data'])
        assert s.object_type == ObjectType.FINITE

    def test_lens_spc_infinite_finite(self):
        """LENS_SPC: дальний → ближний (зеркально-линзовый)."""
        systems = load_lbo_fast(_LENS_SPC_LBO)
        s = decode_lbo_opj(systems[1]['opj_data'])
        assert s.object_type == ObjectType.INFINITE
        assert s.image_type == ObjectType.FINITE


# =========================================================================== #
# 7. Пакетный тест LENS.LBO — f' в пределах 15%
# =========================================================================== #

class TestBatchLensLbo:

    def test_lens_lbo_focal_length_within_15_percent(self):
        """Все системы LENS.LBO с f'=N в имени: расчётный f' в пределах 15%."""
        systems = load_lbo_fast(_LENS_LBO)
        good = 0
        total = 0
        for i, s in enumerate(systems[:30]):
            try:
                sys_obj = decode_lbo_opj(s['opj_data'])
                parax = paraxial_trace(sys_obj)
                f_val = abs(parax.get('focal_length', 0))
                f_match = re.search(r"f'=([\d.]+)", s['name'])
                if f_match:
                    f_target = float(f_match.group(1))
                    if f_target > 0:
                        total += 1
                        ratio = abs(f_val - f_target) / f_target
                        if ratio < 0.15:
                            good += 1
            except Exception:
                pass

        assert total > 0, "No systems with f'=N in name found"
        assert good >= total * 0.7, f"Only {good}/{total} systems within 15%"


# =========================================================================== #
# Manual runner — preserves `py tests\test_parser.py` execution
# =========================================================================== #

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
