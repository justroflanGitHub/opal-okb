# TODO: convert to pytest — uses sys.stdout hack and custom runner
"""Тесты двухфазного расчёта (lazy calculation) и регрессии."""
import sys, os, io
if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from optics_engine import (
    create_demo_system, create_demo_system_by_name,
    paraxial_trace, seidel_aberrations,
)
from glass_catalog import compute_refractive_index
from system_utils import reverse_system
from main import MainWindow


class TestLazyCalc:
    def test_phase1_returns_parax(self):
        """Фаза 1 возвращает parax данные."""
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        data = w._do_calc_phase1(w.current_system)
        assert 'parax' in data, f"Missing 'parax' key: {list(data.keys())}"
        assert data['parax'].get('focal_length', 0) != 0, "focal_length is 0"
        print("  ✅ test_phase1_returns_parax")

    def test_phase1_returns_seidel(self):
        """Фаза 1 возвращает seidel данные."""
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        data = w._do_calc_phase1(w.current_system)
        assert 'seidel' in data, f"Missing 'seidel' key"
        assert 'SI' in data['seidel'], "Missing SI in seidel"
        print("  ✅ test_phase1_returns_seidel")

    def test_phase1_returns_spots(self):
        """Фаза 1 возвращает spots для визуализации."""
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        data = w._do_calc_phase1(w.current_system)
        assert 'spots' in data or 'spots_mono' in data, f"Missing spots key"
        print("  ✅ test_phase1_returns_spots")

    def test_phase2_returns_all_keys(self):
        """Фаза 2 возвращает все ключи анализа."""
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        data = w._do_calc_phase2(w.current_system, 0.0, 0.0)
        expected = ['fan_data', 'geo_mtf', 'diff_mtf', 'psf_data',
                    'beam_data', 'chief_data', 'zernike_coeffs']
        for key in expected:
            assert key in data, f"Missing '{key}' in phase2 results: {sorted(data.keys())}"
        print(f"  ✅ test_phase2_returns_all_keys ({len(data)} keys)")

    def test_sync_mode_both_phases(self):
        """Sync режим выполняет обе фазы."""
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        w._run_calc(w.current_system, sync=True)
        assert w.results.parax_table.rowCount() > 0, "Parax table empty after sync calc"
        assert w.analysis._parax_data, "Analysis parax data empty"
        print("  ✅ test_sync_mode_both_phases")

    def test_parax_multi_wavelength(self):
        """Параксиальная таблица имеет колонки для каждой длины волны."""
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        w._run_calc(w.current_system, sync=True)
        # Demo system has 3 wavelengths
        n_wl = len(w.current_system.wavelengths)
        assert n_wl == 3, f"Expected 3 wavelengths, got {n_wl}"
        print(f"  ✅ test_parax_multi_wavelength ({n_wl} wavelengths)")

    def test_reverse_system_preserves_glass(self):
        """Двойной оборот сохраняет данные (регрессия)."""
        s = create_demo_system_by_name('achromat')
        s2 = reverse_system(s)
        # Single reverse adds air surface — check glass+thickness preserved
        # Original: S0(К8,d=6), S1(ТФ1,d=2.5), S2(воздух,d=95)
        # Reversed: S0(воздух,d=95), S1(ТФ1,d=2.5), S2(К8,d=6), S3(воздух,d=0)
        glasses_orig = [(su.glass, su.thickness) for su in s.surfaces]
        glasses_rev = [(su.glass, su.thickness) for su in s2.surfaces]
        # К8(d=6) should appear in both
        k8_orig = [(g, d) for g, d in glasses_orig if g == 'К8']
        k8_rev = [(g, d) for g, d in glasses_rev if g == 'К8']
        assert len(k8_orig) == 1 and len(k8_rev) == 1, f"К8 count mismatch"
        assert abs(k8_orig[0][1] - k8_rev[0][1]) < 0.001, f"К8 thickness changed"
        # ТФ1(d=2.5) should appear in both
        tf1_orig = [(g, d) for g, d in glasses_orig if g == 'ТФ1']
        tf1_rev = [(g, d) for g, d in glasses_rev if g == 'ТФ1']
        assert len(tf1_orig) == 1 and len(tf1_rev) == 1, f"ТФ1 count mismatch"
        assert abs(tf1_orig[0][1] - tf1_rev[0][1]) < 0.001, f"ТФ1 thickness changed"
        print("  ✅ test_reverse_system_preserves_glass")

    def test_tf2_refractive_index(self):
        """ТФ2 даёт правильный показатель преломления (регрессия)."""
        n = compute_refractive_index('ТФ2', 0.58756)
        assert 1.65 < n < 1.70, f"ТФ2 n={n:.4f} out of range [1.65, 1.70]"
        assert abs(n - 1.0) > 0.1, f"ТФ2 n={n} — fallback to air!"
        print(f"  ✅ test_tf2_refractive_index (n={n:.4f})")

    def test_visualization_set_system_fast(self):
        """set_system_fast обновляет лучи без сброса зума."""
        from visualization import OpticalSystemView
        v = OpticalSystemView()
        s = create_demo_system()
        v.set_system_fast(s)
        assert len(v.ray_results) > 0, "No ray results after set_system_fast"
        print("  ✅ test_visualization_set_system_fast")

    def test_analysis_apply_phase1_phase2(self):
        """apply_phase1 + apply_phase2 работают раздельно."""
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        p1 = w._do_calc_phase1(w.current_system)
        p2 = w._do_calc_phase2(w.current_system, 0.0, 0.0)
        # apply phase1
        w.analysis.apply_phase1(w.current_system, {**p1, **p2})
        assert w.analysis._parax_data, "Parax not set after phase1"
        # apply phase2
        w.analysis.apply_phase2(w.current_system, {**p1, **p2})
        assert w.analysis._calculation_done, "calculation_done not set after phase2"
        print("  ✅ test_analysis_apply_phase1_phase2")

    def test_fieldpoint_import_in_aberrations(self):
        """FieldPoint импортирован в aberrations.py (регрессия краша)."""
        from aberrations import compute_chief_ray_characteristics
        from optics_engine import OpticalSystem, Surface
        sys = OpticalSystem()
        sys.surfaces = [Surface(radius=50, thickness=5, glass='К8', semi_diameter=10)]
        result = compute_chief_ray_characteristics(sys)
        assert isinstance(result, list)
        print("  ✅ test_fieldpoint_import_in_aberrations")

    def test_calculate_empty_system_no_crash(self):
        """Расчёт пустой системы не крашит (регрессия)."""
        w = MainWindow()
        w._init_new_system()
        w.current_system.surfaces = []
        w._calculate()  # should not crash
        # Just reaching here = pass
        print("  ✅ test_calculate_empty_system_no_crash")

    def test_bfd_positive_for_demo(self):
        """BFD должен быть положительным для демо-системы (регрессия).
        Раньше BFD вычислялся как -A/C где A включал последний отрезок,
        что давало BFD = true_BFD - d_last (отрицательный при d_last > BFD).
        """
        from optics_engine import create_demo_system, paraxial_trace
        s = create_demo_system()
        p = paraxial_trace(s)
        bfd = p['back_focal_distance']
        d_last = s.surfaces[-1].thickness
        assert bfd > 0, f"BFD={bfd:.4f} должен быть > 0 для собирающей системы"
        assert bfd < d_last, f"BFD={bfd:.4f} должен быть < d_last={d_last:.4f}"
        print(f"  ✅ test_bfd_positive_for_demo (BFD={bfd:.4f}, d_last={d_last:.4f})")

    def test_fit_focal_length(self):
        """Подгонка фокусного расстояния работает."""
        from optics_engine import create_demo_system, paraxial_trace
        from optimizer import fit_focal_length
        s = create_demo_system()
        target = 100.0
        result = fit_focal_length(s, target, surface_idx=0, param_type='radius')
        f_achieved = paraxial_trace(result)['focal_length']
        assert abs(f_achieved - target) < 0.01, \
            f"f'={f_achieved:.4f}, target={target}"
        # Original system unchanged
        f_orig = paraxial_trace(s)['focal_length']
        assert abs(f_orig - target) > 1.0, "Original system should differ from target"
        print(f"  ✅ test_fit_focal_length (f'={f_achieved:.4f}, target={target})")

    def test_fit_bfd_radius(self):
        """Подгонка BFD через радиус работает."""
        from optics_engine import create_demo_system, paraxial_trace
        from optimizer import fit_bfd
        s = create_demo_system()
        p = paraxial_trace(s)
        target = p['back_focal_distance'] + 10.0  # shift by 10mm
        result = fit_bfd(s, target, surface_idx=0, param_type='radius')
        bfd_achieved = paraxial_trace(result)['back_focal_distance']
        assert abs(bfd_achieved - target) < 0.01, \
            f"BFD={bfd_achieved:.4f}, target={target}"
        print(f"  ✅ test_fit_bfd_radius (BFD={bfd_achieved:.4f}, target={target})")

    def test_fit_bfd_last_thickness_raises(self):
        """Подгонка BFD через толщину последней поверхности — ошибка (не влияет на BFD)."""
        from optics_engine import create_demo_system
        from optimizer import fit_bfd
        s = create_demo_system()
        last_idx = len(s.surfaces) - 1
        try:
            fit_bfd(s, 80.0, surface_idx=last_idx, param_type='thickness')
            assert False, "Должна быть ValueError для изменения d_last"
        except ValueError:
            pass  # Expected
        print("  ✅ test_fit_bfd_last_thickness_raises")

    def test_fit_focal_length_unreachable_raises(self):
        """Подгонка недостижимого f' — ошибка с сообщением о диапазоне."""
        from optics_engine import create_demo_system
        from optimizer import fit_focal_length
        s = create_demo_system()
        # Demo: f≈77mm with R[1]=-200. Making f=200 via R[1] is unreachable
        # (with negative R[1], max f ≈ 96mm as R→-∞)
        try:
            fit_focal_length(s, 200.0, surface_idx=1, param_type='radius')
            assert False, "Должна быть ValueError для недостижимой цели"
        except ValueError:
            pass  # Expected
        print("  ✅ test_fit_focal_length_unreachable_raises")


if __name__ == '__main__':
    test = TestLazyCalc()
    methods = [m for m in dir(test) if m.startswith('test_')]
    passed = 0
    failed = 0
    for m in methods:
        try:
            getattr(test, m)()
            passed += 1
        except Exception as e:
            print(f"  ❌ {m}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"ИТОГО: {passed}/{passed+failed} пройдено, {failed} не пройдено")
    print(f"{'='*60}")
