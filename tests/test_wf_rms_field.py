"""Регрессионные тесты пункта 2 GAP v2 — СКВ волновой аберрации по полю.

Физика: для каждой точки поля пучок трассируется на гексаполярной сетке
зрачка, W = разность OPL до опорной сферы; СКВ = среднеквадратическое
отклонение W от среднего по зрачку.
"""
import math

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
import aberrations
from aberrations import (compute_wavefront_rms_vs_field,
                         trace_wavefront_hexapolar)


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


class TestWavefrontHexapolar:
    def test_hexapolar_grid_size(self):
        """num_rings=4 → 1 + 3·4·5 = 61 точка зрачка."""
        pts = trace_wavefront_hexapolar(build_doublet(), field_y=0.0)
        assert len(pts) == 61

    def test_center_is_chief_ray(self):
        """Луч через центр зрачка — главный: W = 0 (ноль отсчёта)."""
        pts = trace_wavefront_hexapolar(build_doublet(), field_y=0.0)
        assert pts[0][0] == pytest.approx(0.0)
        assert pts[0][1] == pytest.approx(0.0)
        assert pts[0][2] == pytest.approx(0.0, abs=1e-9)

    def test_matches_meridional_fan(self):
        """Осевой пучок осесимметричен: W на кольце ρ=1 совпадает с
        ``wave`` крайнего луча меридионального веера."""
        s = build_doublet()
        pts = trace_wavefront_hexapolar(s, wl=0.58756, field_y=0.0,
                                        num_rings=1)
        ring = [w for px, py, w in pts[1:]]  # 6 точек кольца ρ=1
        fan = aberrations.trace_aberration_fan(s, 0.58756, num_rays=3)
        rim = [r['wave'] for r in fan
               if r['success'] and abs(abs(r['pupil_y']) - 1.0) < 1e-9]
        assert rim, "крайние лучи веера не прошли"
        assert all(w == pytest.approx(rim[0], abs=1e-9) for w in ring)


class TestRmsVsField:
    def test_all_field_points_present(self):
        """Поля = все точки поля системы (поле 0 добавляется)."""
        s = build_doublet()
        s.field_points = [FieldPoint(y=0.0), FieldPoint(y=7.0),
                          FieldPoint(y=14.0)]
        fields, rms = compute_wavefront_rms_vs_field(s)
        assert fields == [0.0, 7.0, 14.0]
        assert len(rms) == 3
        assert all(math.isfinite(r) and r >= 0 for r in rms)

    def test_fallback_linspace_without_field_points(self):
        s = build_doublet()
        fields, rms = compute_wavefront_rms_vs_field(s, num_fields=5)
        assert fields == [0.0, 1.25, 2.5, 3.75, 5.0]
        assert len(rms) == 5

    def test_rms_is_deviation_from_mean(self, monkeypatch):
        """СКВ — отклонение от среднего (пистон не влияет)."""
        # 12 точек зрачка (≥ WF_RMS_MIN_POINTS): W чередуется 10/12/14
        fake = [(float(i % 3) - 1, float(i % 2), float((10, 12, 14)[i % 3]))
                for i in range(12)]
        monkeypatch.setitem(compute_wavefront_rms_vs_field.__globals__,
                            'trace_wavefront_hexapolar', lambda *a, **k: fake)
        s = build_doublet()
        s.field_points = [FieldPoint(y=5.0)]
        fields, rms = compute_wavefront_rms_vs_field(s)
        # mean = 12 → СКВ = sqrt(mean((W−12)²)) = sqrt(8/3)
        assert rms[0] == pytest.approx(math.sqrt(8.0 / 3.0))

    def test_piston_invariance(self, monkeypatch):
        """Добавка постоянного пистона не меняет СКВ."""
        coords = [(float(i % 3) - 1, float(i % 2)) for i in range(12)]
        base = [(px, py, 3.0 * px + 1.0) for px, py in coords]
        shifted = [(px, py, w + 25.0) for px, py, w in base]
        calls = iter([base, shifted])
        monkeypatch.setitem(compute_wavefront_rms_vs_field.__globals__,
                            'trace_wavefront_hexapolar',
                            lambda *a, **k: next(calls))
        s = build_doublet()
        s.field_points = [FieldPoint(y=5.0)]
        _, rms = compute_wavefront_rms_vs_field(s)
        assert rms[0] == pytest.approx(rms[1])

    def test_grows_off_axis_for_aberrated_system(self):
        """Кома/астигматизм: СКВ на краю поля больше осевого."""
        s = build_doublet()
        s.field_points = [FieldPoint(y=0.0), FieldPoint(y=14.0)]
        fields, rms = compute_wavefront_rms_vs_field(s)
        assert rms[1] > rms[0]

    def test_seidel_consistency_axial(self):
        """Аберрационная система: осевое СКВ > 0 (сферическая аберрация)."""
        s = build_doublet()
        s.field_points = [FieldPoint(y=0.0)]
        _, rms = compute_wavefront_rms_vs_field(s)
        assert rms[0] > 0


class TestWfRmsGui:
    """GUI: matplotlib-график СКВ по полю на вкладке «Цернике»."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def test_widget_renders_line(self):
        from gui.widgets import WfRmsFieldMplWidget
        w = WfRmsFieldMplWidget()
        assert w.figure is not None, "matplotlib не доступен"
        w.set_data(build_doublet())
        assert w.field_data and w.field_data[0]
        assert w.figure.axes, "оси не созданы"
        assert len(w.figure.axes[0].lines) == 1
        assert 'СКВ' in w.figure.axes[0].get_title()

    def test_widget_pending_placeholder(self):
        from gui.widgets import WfRmsFieldMplWidget
        w = WfRmsFieldMplWidget()
        w._pending = True
        w.update()
        texts = [t.get_text() for t in w.figure.axes[0].texts]
        assert any('Расчёт' in t for t in texts)

    def test_zernike_tab_contains_graph(self):
        """Вкладка «Цернике»: гистограммы + СКВ по полю; отдельной вкладки
        СКВ по полю больше нет (элемент определён один раз)."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        titles = [panel.tabText(i) for i in range(panel.count())]
        assert 'Цернике' in titles
        assert 'СКВ по полю' not in titles
        page = panel.zernike_page
        assert panel.zernike_w.parent() is page
        assert panel.wf_rms_field_w.parent() is page

    def test_zernike_tab_tables_stacked(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel._update_wf_rms_field_table(build_doublet())
        assert panel._wf_rms_table is not None
        container = panel._table_containers['zernike']
        assert container.layout().count() == 1  # один stacked-виджет
