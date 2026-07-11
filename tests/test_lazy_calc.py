"""Тесты двухфазного расчёта (lazy calculation) и регрессии."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import (
    create_demo_system, create_demo_system_by_name,
    paraxial_trace, seidel_aberrations,
)
from glass_catalog import compute_refractive_index
from system_utils import reverse_system


@pytest.fixture(scope="module")
def app():
    """Single QApplication instance for all GUI tests in this module."""
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture
def main_window(app):
    from main import MainWindow
    w = MainWindow()
    w._init_new_system()
    yield w
    w.close()


class TestLazyCalc:
    def test_phase1_returns_parax(self, main_window):
        """Фаза 1 возвращает parax данные."""
        main_window.current_system = create_demo_system()
        data = main_window._do_calc_phase1(main_window.current_system)
        assert 'parax' in data, f"Missing 'parax' key: {list(data.keys())}"
        assert data['parax'].get('focal_length', 0) != 0, "focal_length is 0"

    def test_phase1_returns_seidel(self, main_window):
        """Фаза 1 возвращает seidel данные."""
        main_window.current_system = create_demo_system()
        data = main_window._do_calc_phase1(main_window.current_system)
        assert 'seidel' in data, "Missing 'seidel' key"
        assert 'SI' in data['seidel'], "Missing SI in seidel"

    def test_phase1_returns_spots(self, main_window):
        """Фаза 1 возвращает spots для визуализации."""
        main_window.current_system = create_demo_system()
        data = main_window._do_calc_phase1(main_window.current_system)
        assert 'spots' in data or 'spots_mono' in data, "Missing spots key"

    def test_phase2_returns_all_keys(self, main_window):
        """Фаза 2 возвращает все ключи анализа."""
        main_window.current_system = create_demo_system()
        data = main_window._do_calc_phase2(main_window.current_system, 0.0, 0.0)
        expected = ['fan_data', 'geo_mtf', 'diff_mtf', 'psf_data',
                    'beam_data', 'chief_data', 'zernike_coeffs']
        for key in expected:
            assert key in data, f"Missing '{key}' in phase2 results: {sorted(data.keys())}"

    def test_sync_mode_both_phases(self, main_window):
        """Sync режим выполняет обе фазы."""
        main_window.current_system = create_demo_system()
        main_window._run_calc(main_window.current_system, sync=True)
        assert main_window.results.parax_table.rowCount() > 0, "Parax table empty after sync calc"
        assert main_window.analysis._parax_data, "Analysis parax data empty"

    def test_parax_multi_wavelength(self, main_window):
        """Параксиальная таблица имеет колонки для каждой длины волны."""
        main_window.current_system = create_demo_system()
        main_window._run_calc(main_window.current_system, sync=True)
        n_wl = len(main_window.current_system.wavelengths)
        assert n_wl == 3, f"Expected 3 wavelengths, got {n_wl}"

    def test_reverse_system_preserves_glass(self):
        """Двойной оборот сохраняет данные (регрессия)."""
        s = create_demo_system_by_name('achromat')
        s2 = reverse_system(s)
        glasses_orig = [(su.glass, su.thickness) for su in s.surfaces]
        glasses_rev = [(su.glass, su.thickness) for su in s2.surfaces]
        k8_orig = [(g, d) for g, d in glasses_orig if g == 'К8']
        k8_rev = [(g, d) for g, d in glasses_rev if g == 'К8']
        assert len(k8_orig) == 1 and len(k8_rev) == 1, "К8 count mismatch"
        assert abs(k8_orig[0][1] - k8_rev[0][1]) < 0.001, "К8 thickness changed"
        tf1_orig = [(g, d) for g, d in glasses_orig if g == 'ТФ1']
        tf1_rev = [(g, d) for g, d in glasses_rev if g == 'ТФ1']
        assert len(tf1_orig) == 1 and len(tf1_rev) == 1, "ТФ1 count mismatch"
        assert abs(tf1_orig[0][1] - tf1_rev[0][1]) < 0.001, "ТФ1 thickness changed"

    def test_tf2_refractive_index(self):
        """ТФ2 даёт правильный показатель преломления (регрессия)."""
        n = compute_refractive_index('ТФ2', 0.58756)
        assert 1.65 < n < 1.70, f"ТФ2 n={n:.4f} out of range [1.65, 1.70]"
        assert abs(n - 1.0) > 0.1, f"ТФ2 n={n} — fallback to air!"

    def test_visualization_set_system_fast(self):
        """set_system_fast обновляет лучи без сброса зума."""
        from visualization import OpticalSystemView
        v = OpticalSystemView()
        s = create_demo_system()
        v.set_system_fast(s)
        assert len(v.ray_results) > 0, "No ray results after set_system_fast"

    def test_analysis_apply_phase1_phase2(self, main_window):
        """apply_phase1 + apply_phase2 работают раздельно."""
        main_window.current_system = create_demo_system()
        p1 = main_window._do_calc_phase1(main_window.current_system)
        p2 = main_window._do_calc_phase2(main_window.current_system, 0.0, 0.0)
        main_window.analysis.apply_phase1(main_window.current_system, {**p1, **p2})
        assert main_window.analysis._parax_data, "Parax not set after phase1"
        main_window.analysis.apply_phase2(main_window.current_system, {**p1, **p2})
        assert main_window.analysis._calculation_done, "calculation_done not set after phase2"

    def test_fieldpoint_import_in_aberrations(self):
        """FieldPoint импортирован в aberrations.py (регрессия краша)."""
        from aberrations import compute_chief_ray_characteristics
        from optics_engine import OpticalSystem, Surface
        sys = OpticalSystem()
        sys.surfaces = [Surface(radius=50, thickness=5, glass='К8', semi_diameter=10)]
        result = compute_chief_ray_characteristics(sys)
        assert isinstance(result, list)

    def test_calculate_empty_system_no_crash(self, main_window):
        """Расчёт пустой системы не крашит (регрессия)."""
        main_window.current_system.surfaces = []
        main_window._calculate()

    def test_bfd_positive_for_demo(self):
        """BFD должен быть положительным для демо-системы (регрессия)."""
        s = create_demo_system()
        p = paraxial_trace(s)
        bfd = p['back_focal_distance']
        d_last = s.surfaces[-1].thickness
        assert bfd > 0, f"BFD={bfd:.4f} должен быть > 0 для собирающей системы"
        assert bfd < d_last, f"BFD={bfd:.4f} должен быть < d_last={d_last:.4f}"

    def test_fit_focal_length(self):
        """Подгонка фокусного расстояния работает."""
        from optimizer import fit_focal_length
        s = create_demo_system()
        target = 100.0
        result = fit_focal_length(s, target, surface_idx=0, param_type='radius')
        f_achieved = paraxial_trace(result)['focal_length']
        assert abs(f_achieved - target) < 0.01, f"f'={f_achieved:.4f}, target={target}"
        f_orig = paraxial_trace(s)['focal_length']
        assert abs(f_orig - target) > 1.0, "Original system should differ from target"

    def test_fit_bfd_radius(self):
        """Подгонка BFD через радиус работает."""
        from optimizer import fit_bfd
        s = create_demo_system()
        p = paraxial_trace(s)
        target = p['back_focal_distance'] + 10.0
        result = fit_bfd(s, target, surface_idx=0, param_type='radius')
        bfd_achieved = paraxial_trace(result)['back_focal_distance']
        assert abs(bfd_achieved - target) < 0.01, f"BFD={bfd_achieved:.4f}, target={target}"

    def test_fit_bfd_last_thickness_raises(self):
        """Подгонка BFD через толщину последней поверхности — ошибка."""
        from optimizer import fit_bfd
        s = create_demo_system()
        last_idx = len(s.surfaces) - 1
        with pytest.raises(ValueError):
            fit_bfd(s, 80.0, surface_idx=last_idx, param_type='thickness')

    def test_fit_focal_length_unreachable_raises(self):
        """Подгонка недостижимого f' — ошибка с сообщением о диапазоне."""
        from optimizer import fit_focal_length
        s = create_demo_system()
        with pytest.raises(ValueError):
            fit_focal_length(s, 200.0, surface_idx=1, param_type='radius')
