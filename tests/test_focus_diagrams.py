"""Регрессионные тесты пункта 3 GAP v2 — фокусировочные диаграммы.

5 точечных диаграмм при defocus = 0, ±ΔS', ±2ΔS'; ΔS' — шаг фокусировки
из настроек анализа (по умолчанию 0.1 мм); отрисовка matplotlib 1×5
с общим масштабом.
"""
import pytest

from optics_engine import OpticalSystem, Surface, Wavelength
from aberrations import (compute_focus_diagrams, DEFAULT_FOCUS_STEP_MM,
                         FOCUS_DIAGRAM_DEFOCI)

FOCUS_LABELS = [label for label, _ in FOCUS_DIAGRAM_DEFOCI]


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 — базовая тестовая система."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


class TestComputeFocusDiagrams:
    def test_default_step_constant(self):
        """ΔS' по умолчанию — 0.1 мм (вынесен в настройки анализа)."""
        assert DEFAULT_FOCUS_STEP_MM == 0.1

    def test_five_positions_with_expected_defocus(self):
        diagrams, max_range = compute_focus_diagrams(build_doublet(),
                                                     focus_step_mm=0.3)
        assert list(diagrams.keys()) == FOCUS_LABELS
        expected = {"номинал": 0.0, "+DS'": 0.3, "-DS'": -0.3,
                    "+2DS'": 0.6, "-2DS'": -0.6}
        for label, df in expected.items():
            spots, rms_info, actual = diagrams[label]
            assert actual == pytest.approx(df, abs=1e-12)
            assert spots, f"{label}: пустая диаграмма"
            assert {'rms_x', 'rms_y', 'rms_total'} <= set(rms_info)

    def test_default_step_used_when_not_given(self):
        diagrams, _ = compute_focus_diagrams(build_doublet())
        assert diagrams["+DS'"][2] == pytest.approx(0.1)
        assert diagrams["+2DS'"][2] == pytest.approx(0.2)

    def test_max_range_positive_and_shared(self):
        """Общий масштаб: max_range — максимальный радиус по всем позициям."""
        s = build_doublet()
        diagrams, max_range = compute_focus_diagrams(s)
        import math
        worst = max(math.sqrt(dx * dx + dy * dy)
                    for spots, _, _ in diagrams.values()
                    for dx, dy in spots)
        assert max_range == pytest.approx(worst)
        assert max_range > 0

    def test_nominal_matches_zero_defocus_spot(self):
        """«номинал» = spot-диаграмма без смещения плоскости."""
        from aberrations import compute_spot_diagram_at_defocus
        s = build_doublet()
        diagrams, _ = compute_focus_diagrams(s, focus_step_mm=0.2)
        ref = compute_spot_diagram_at_defocus(s, wl=0.58756, num_rays=60,
                                              field_y=0.0, defocus_mm=0.0)
        assert diagrams["номинал"][0] == pytest.approx(ref, abs=1e-12)


class TestFocusDiagramGui:
    """GUI: matplotlib 1×5, общий масштаб, ΔS' из настроек."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def test_widget_is_mpl_with_five_axes(self):
        from gui.widgets import FocusDiagramWidget, MplCanvasWidget
        w = FocusDiagramWidget()
        assert isinstance(w, MplCanvasWidget)
        w.set_data(build_doublet(), focus_step_mm=0.2)
        assert len(w.figure.axes) == 5
        assert set(w.spots_by_defocus) == set(FOCUS_LABELS)

    def test_common_scale(self):
        """Все 5 сабплотов имеют одинаковые пределы осей (общий масштаб)."""
        from gui.widgets import FocusDiagramWidget
        w = FocusDiagramWidget()
        w.set_data(build_doublet(), focus_step_mm=0.2)
        xlims = {tuple(ax.get_xlim()) for ax in w.figure.axes}
        ylims = {tuple(ax.get_ylim()) for ax in w.figure.axes}
        assert len(xlims) == 1 and len(ylims) == 1

    def test_apply_data_roundtrip(self):
        from gui.widgets import FocusDiagramWidget
        w = FocusDiagramWidget()
        diagrams, max_r = compute_focus_diagrams(build_doublet())
        w.apply_data(diagrams, max_r)
        assert w.spots_by_defocus is diagrams
        assert w.max_range == max_r

    def test_panel_settings_and_tab_placement(self):
        """ΔS' в настройках анализа (default 0.1); вкладка «Фокус.диагр.»
        рядом с точечной диаграммой."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        assert panel.get_focus_step() == pytest.approx(0.1)
        panel.focus_step_spin.setValue(0.5)
        assert panel.get_focus_step() == pytest.approx(0.5)
        titles = [panel.tabText(i) for i in range(panel.count())]
        assert titles.index('Фокус.диагр.') == titles.index('Точечная диагр.') + 1

    def test_controller_accepts_focus_step(self):
        """do_calc_phase2 использует шаг ΔS' (иначе — настройка игнорируется)."""
        from gui.controllers.calculation_controller import CalculationController
        import inspect
        sig = inspect.signature(CalculationController.do_calc_phase2)
        assert 'focus_step' in sig.parameters
