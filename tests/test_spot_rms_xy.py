"""Регрессионные тесты пункта 4 GAP v2 — СКВ пятна раздельно X/Y + центроид.

RMS_X / RMS_Y — раздельные СКВ пятна по осям (сагиттальная / меридиональная),
Yцэ — энергетический центр (центроид) по Y. Данные — в таблице СКВ пятна
и в подписи под графиком точечной диаграммы.
"""
import math
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, create_demo_system
from aberrations import compute_rms_spot_xy

# Детерминированный набор точек: центроид (2/3, 4/3),
# rms_x = sqrt(8/9), rms_y = sqrt(32/9), rms_total = sqrt(40/9).
SPOT_TRIAD = [(0.0, 0.0), (2.0, 0.0), (0.0, 4.0)]
CENTROID_X_EXPECTED = 2.0 / 3.0
CENTROID_Y_EXPECTED = 4.0 / 3.0
RMS_X_EXPECTED = math.sqrt(8.0 / 9.0)
RMS_Y_EXPECTED = math.sqrt(32.0 / 9.0)
RMS_TOTAL_EXPECTED = math.sqrt(40.0 / 9.0)


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 (монохром) для GUI-тестов."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


class TestComputeRmsSpotXy:
    def test_deterministic_values(self):
        """Раздельные СКВ и центроид на известном наборе точек."""
        r = compute_rms_spot_xy(SPOT_TRIAD)
        assert r['centroid_x'] == pytest.approx(CENTROID_X_EXPECTED)
        assert r['centroid_y'] == pytest.approx(CENTROID_Y_EXPECTED)
        assert r['rms_x'] == pytest.approx(RMS_X_EXPECTED)
        assert r['rms_y'] == pytest.approx(RMS_Y_EXPECTED)
        assert r['rms_total'] == pytest.approx(RMS_TOTAL_EXPECTED)

    def test_empty_spots(self):
        assert compute_rms_spot_xy([]) == {
            'rms_x': 0.0, 'rms_y': 0.0, 'centroid_x': 0.0,
            'centroid_y': 0.0, 'rms_total': 0.0}

    def test_piston_shift_invariance(self):
        """Сдвиг всех точек меняет центроид, но не раздельные СКВ."""
        shifted = [(dx + 3.0, dy - 1.5) for dx, dy in SPOT_TRIAD]
        r = compute_rms_spot_xy(shifted)
        assert r['rms_x'] == pytest.approx(RMS_X_EXPECTED)
        assert r['rms_y'] == pytest.approx(RMS_Y_EXPECTED)
        assert r['centroid_y'] == pytest.approx(CENTROID_Y_EXPECTED - 1.5)

    def test_pythagoras(self):
        """rms_total² = rms_x² + rms_y²."""
        r = compute_rms_spot_xy(SPOT_TRIAD)
        assert r['rms_x'] ** 2 + r['rms_y'] ** 2 == pytest.approx(r['rms_total'] ** 2)


class TestSpotRmsGui:
    """GUI: подпись графика пятна + таблица СКВ пятна."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import sys
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def test_rms_label_contents(self):
        """Подпись: общий RMS, RMS_X, RMS_Y, Yцэ, число лучей."""
        from gui.widgets.spot_diagram import SpotDiagramWidget
        label = SpotDiagramWidget._rms_label(
            0.5, {'rms_x': 0.2, 'rms_y': 0.4, 'centroid_y': 0.05}, 40)
        assert 'RMS: 0.5000' in label
        assert 'RMS_X: 0.2000' in label
        assert 'RMS_Y: 0.4000' in label
        assert 'Yцэ: 0.0500' in label
        assert '40 лучей' in label

    def test_rms_label_defaults_on_missing(self):
        """Пустое rms_xy не ломает подпись (нули)."""
        from gui.widgets.spot_diagram import SpotDiagramWidget
        label = SpotDiagramWidget._rms_label(0.1, {}, 10)
        assert 'RMS_X: 0.0000' in label
        assert 'Yцэ: 0.0000' in label

    def test_set_data_populates_rms_xy(self):
        """set_data считает rms_xy (моно) и poly_rms_xy."""
        from gui.widgets.spot_diagram import SpotDiagramWidget
        w = SpotDiagramWidget()
        w.set_data(build_doublet())
        assert {'rms_x', 'rms_y', 'centroid_y', 'rms_total'} <= set(w.rms_xy)
        assert set(w.poly_rms_xy) == set(w.rms_xy)  # одна λ → poly = mono
        ref = compute_rms_spot_xy(w.spots_mono)
        assert w.rms_xy['rms_y'] == pytest.approx(ref['rms_y'])
        assert w.rms_xy['centroid_y'] == pytest.approx(ref['centroid_y'])

    def test_polychromatic_rms_xy_separate(self):
        """При нескольких λ poly_rms_xy считается по полихроматическому пятну."""
        s = build_doublet()
        s.wavelengths = [Wavelength(value=0.58756), Wavelength(value=0.65627)]
        from gui.widgets.spot_diagram import SpotDiagramWidget
        w = SpotDiagramWidget()
        w.set_data(s)
        ref = compute_rms_spot_xy([(dx, dy) for dx, dy, _ in w.spots_poly])
        assert w.poly_rms_xy['rms_x'] == pytest.approx(ref['rms_x'])
        assert w.poly_rms_xy['centroid_y'] == pytest.approx(ref['centroid_y'])

    def test_spot_table_has_xy_columns(self):
        """Таблица СКВ пятна: колонки RMS_X, RMS_Y, Yцэ (с единицами)."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel._update_spot_table(build_doublet())
        table = panel._table_containers['spot'].layout().itemAt(0).widget()
        headers = [table.horizontalHeaderItem(c).text()
                   for c in range(table.columnCount())]
        for col in ('RMS, мм', 'RMS_X, мм', 'RMS_Y, мм', 'Yцэ, мм'):
            assert col in headers, f"Нет колонки {col}: {headers}"
        # Числовая строка: 8 колонок, RMS_X ≠ 0 у аберрирующего дублета
        row = [table.item(0, c).text() for c in range(table.columnCount())]
        assert len(row) == 8
        assert float(row[headers.index('RMS_X, мм')]) > 0

    def test_phase2_results_carry_rms_xy(self):
        """do_calc_phase2 возвращает rms_xy и poly_rms_xy для apply_phase2."""
        from gui.controllers.calculation_controller import CalculationController
        cc = CalculationController.__new__(CalculationController)
        data = cc.do_calc_phase2(build_doublet(), 0.0, 0.0)
        for key in ('rms_xy', 'poly_rms_xy'):
            assert {'rms_x', 'rms_y', 'centroid_y', 'rms_total'} <= set(data[key])
        ref = compute_rms_spot_xy(data['spots_mono'])
        assert data['rms_xy']['rms_y'] == pytest.approx(ref['rms_y'])
        assert data['poly_rms_xy'] == data['rms_xy']  # одна λ

    def test_apply_precomputed_sets_widget_rms_xy(self):
        """apply_precomputed прокидывает spot_rms_xy/poly_rms_xy в виджет."""
        from gui.analysis_pipeline import compute_all_analysis
        from gui.analysis_panel import AnalysisPanel
        s = build_doublet()
        panel = AnalysisPanel()
        panel.apply_precomputed(s, compute_all_analysis(s))
        assert {'rms_x', 'rms_y', 'centroid_y'} <= set(panel.spot_diagram.rms_xy)
        assert set(panel.spot_diagram.poly_rms_xy) == set(panel.spot_diagram.rms_xy)
        assert panel.spot_diagram.poly_rms_xy == panel.spot_diagram.rms_xy
