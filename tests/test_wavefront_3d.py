"""Регрессионные тесты пункта 10 GAP v2 — 3D волновой фронт.

Вращаемая 3D-поверхность W(x, y) на зрачке (matplotlib surface) рядом
с 2D-картой уровней на вкладке «Волн. фронт»; общий рендер 3D-виджетов
с PSF 3D — базовый класс MplSurface3DWidget (без дублирования).
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint


def build_achromat() -> OpticalSystem:
    s = OpticalSystem()
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=2.0),
    ]
    return s


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture
def widget(app):
    from gui.widgets import Wavefront3DWidget
    w = Wavefront3DWidget()
    w.set_data(build_achromat())
    return w


class TestSharedBase:
    def test_psf_and_wf_share_base(self):
        """PSF 3D (п. 5) и волновой фронт 3D (п. 10) — общий базовый
        рендер MplSurface3DWidget, своего _render у них нет."""
        from gui.widgets import PSF3DWidget, Wavefront3DWidget
        from gui.widgets.mpl_widgets import MplSurface3DWidget
        assert issubclass(PSF3DWidget, MplSurface3DWidget)
        assert issubclass(Wavefront3DWidget, MplSurface3DWidget)
        assert '_render' not in PSF3DWidget.__dict__
        assert '_render' not in Wavefront3DWidget.__dict__

    def test_style_3d_axes_single_definition(self):
        """Тёмная тема 3D-осей определена один раз (mpl_widgets)."""
        from gui.widgets import PSF3DWidget, Wavefront3DWidget
        import gui.widgets.mpl_widgets as mplw
        assert hasattr(mplw, 'style_3d_axes')
        assert '_style_3d_axes' not in PSF3DWidget.__dict__


class TestWavefront3dWidget:
    def test_true_3d_axes_with_surface(self, widget):
        assert widget.figure.axes, 'нет осей'
        ax = widget.figure.axes[0]
        assert ax.name == '3d'
        surfaces = [c for c in ax.get_children()
                    if type(c).__name__ == 'Poly3DCollection']
        assert surfaces, 'нет Poly3DCollection (plot_surface)'

    def test_masked_outside_pupil(self, widget):
        """Вне зрачка поверхность маскируется (в 2D-карте — тёмный фон)."""
        import numpy as np
        assert widget.mask is not None
        assert widget.mask[0, 0] == 0      # угол сетки — вне зрачка
        assert widget.mask[:, widget.mask.shape[1] // 2].any()
        surf = widget.figure.axes[0].collections[0]
        n_quads = (widget.wf_data.shape[0] - 1) ** 2
        n_drawn = len(np.asarray(surf.get_facecolors()))
        # masked-квадраты matplotlib не рисует: нарисовано меньше полной сетки
        assert 0 < n_drawn < n_quads

    def test_labels_and_title(self, widget):
        ax = widget.figure.axes[0]
        assert ax.get_zlabel() == 'W, λ'
        assert 'Волновой фронт 3D' in ax.get_title()

    def test_diverging_colormap(self, widget):
        """Расходящаяся карта цветов (как в 2D-виде красный–синий)."""
        assert widget.SURF_CMAP == 'RdBu_r'

    def test_rotation_toolbar_present(self, widget):
        from PyQt5.QtWidgets import QToolBar
        assert widget.findChildren(QToolBar)

    def test_apply_data_roundtrip(self, widget):
        wf, coords, mask = (widget.wf_data, widget.coords, widget.mask)
        widget.apply_data(wf, coords, mask)
        assert widget.wf_data is wf
        assert widget.figure.axes[0].name == '3d'

    def test_pending_placeholder(self, widget):
        widget._pending = True
        widget.redraw()
        assert widget.figure.axes[0].name == 'rectilinear'
        texts = [t.get_text() for t in widget.figure.axes[0].texts]
        assert any('Расчёт' in t for t in texts)

    def test_no_data_placeholder(self, widget):
        widget.apply_data(None, None, None)
        texts = [t.get_text() for t in widget.figure.axes[0].texts]
        assert 'Нет данных' in texts


class TestPanelWfmap:
    def test_tab_is_2d_3d_stack(self, app):
        """Вкладка «Волн. фронт» — QStackedWidget: 2D-карта + 3D."""
        from PyQt5.QtWidgets import QStackedWidget
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        for i in range(panel.count()):
            if panel.tabText(i) == 'Волн. фронт':
                page = panel.widget(i)
                break
        else:
            raise AssertionError('нет вкладки «Волн. фронт»')
        stacks = page.findChildren(QStackedWidget)
        assert any(s is panel.wavefront_stack for s in stacks)
        assert panel.wavefront_stack.count() == 2
        assert panel.wavefront_stack.widget(0) is panel.wavefront_map_w
        assert panel.wavefront_stack.widget(1) is panel.wavefront_3d_w

    def test_set_wavefront_3d_switches(self, app):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        assert not panel.wavefront_3d_enabled
        panel.set_wavefront_3d(True)
        assert panel.wavefront_3d_enabled
        assert panel.wavefront_stack.currentWidget() is panel.wavefront_3d_w
        panel.set_wavefront_3d(False)
        assert panel.wavefront_stack.currentWidget() is panel.wavefront_map_w

    def test_phase2_pending_protocol(self, app):
        """3D-виджет участвует в протоколе _pending фазы 2."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        assert 'wavefront_3d_w' in panel._PHASE2_WIDGETS

    def test_precomputed_feeds_both_views(self, app):
        """Данные пайплайна подставляются и в 2D, и в 3D вид."""
        from gui.analysis_panel import AnalysisPanel
        from gui.analysis_pipeline import compute_all_analysis
        panel = AnalysisPanel()
        d = compute_all_analysis(build_achromat())
        panel.apply_precomputed(build_achromat(), d)
        assert panel.wavefront_3d_w.wf_data is panel.wavefront_map_w.wf_data
        assert panel.wavefront_3d_w.wf_data is d['wf_data']

    def test_analyze_reuses_map_for_3d(self, app, monkeypatch):
        """Живой расчёт считает карту W один раз: 3D-вид получает те же
        данные, set_data 3D-виджета не вызывается (нет повторного
        расчёта)."""
        from gui.analysis_panel import AnalysisPanel
        from gui.widgets import Wavefront3DWidget
        panel = AnalysisPanel()
        called = []
        monkeypatch.setattr(
            Wavefront3DWidget, 'set_data',
            lambda self, *a, **k: called.append(a))
        panel.analyze(build_achromat())
        assert not called, '3D-виджет пересчитывает карту W'
        assert panel.wavefront_3d_w.wf_data is panel.wavefront_map_w.wf_data
        assert panel.wavefront_3d_w.wf_data is not None

    def test_wfmap_table_reuses_widget_data(self, app, monkeypatch):
        """Таблица «Волн. фронт» переиспользует данные виджета."""
        import gui.analysis_panel as ap
        panel = ap.AnalysisPanel()
        wf, coords, mask = panel.wavefront_map_w.wf_data, \
            panel.wavefront_map_w.coords, panel.wavefront_map_w.mask
        # подставляем данные виджета напрямую (как после apply_phase2)
        from zernike import compute_wavefront_map_2d
        wf, coords, mask = compute_wavefront_map_2d(
            build_achromat(), wl=0.58756, grid_size=16)
        panel.wavefront_map_w.wf_data = wf
        panel.wavefront_map_w.coords = coords
        panel.wavefront_map_w.mask = mask
        calls = []
        real = ap.compute_wavefront_map_2d

        def spy(*a, **k):
            calls.append(a)
            return real(*a, **k)

        monkeypatch.setattr(ap, 'compute_wavefront_map_2d', spy)
        panel._update_wfmap_table(build_achromat())
        assert not calls, 'таблица пересчитывает уже готовую карту W'
        table = panel._table_containers['wfmap'].layout().itemAt(0).widget()
        rows = {table.item(r, 0).text(): table.item(r, 1).text()
                for r in range(table.rowCount())}
        assert 'PV' in rows
