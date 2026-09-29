"""Регрессионные тесты пункта 5 GAP v2 — вращаемая 3D PSF.

Истинная 3D-поверхность (matplotlib ``plot_surface``) с вращением мышью
через панель навигации; вкладка «PSF 3D» рядом с 2D PSF (heatmap).
Ранее — статичная псевдо-3D изометрия QPainter без взаимодействия.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength


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


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture
def widget(app):
    from gui.widgets import PSF3DWidget
    w = PSF3DWidget()
    w.set_data(build_doublet())
    return w


class TestPsf3dSurface:
    def test_widget_is_mpl_canvas(self, widget):
        """3D PSF — matplotlib-виджет (не QPainter изометрия)."""
        from gui.widgets import MplCanvasWidget
        assert isinstance(widget, MplCanvasWidget)

    def test_true_3d_axes_with_surface(self, widget):
        """Фигура содержит 3D-оси с поверхностью Poly3DCollection."""
        assert widget.figure.axes, 'нет осей'
        ax = widget.figure.axes[0]
        assert ax.name == '3d'
        surfaces = [c for c in ax.get_children()
                    if type(c).__name__ == 'Poly3DCollection']
        assert surfaces, 'нет Poly3DCollection (plot_surface)'

    def test_axis_labels_and_title(self, widget):
        ax = widget.figure.axes[0]
        assert ax.get_xlabel() == 'X, мкм'
        assert ax.get_ylabel() == 'Y, мкм'
        assert 'PSF 3D' in ax.get_title()

    def test_surface_data_matches_Z(self, widget):
        """Поверхность строится из полного Z (64×64 сетка PSF)."""
        assert widget.Z is not None
        assert widget.Z.shape == (64, 64)
        assert widget.Z.max() == pytest.approx(1.0)  # нормированная PSF

    def test_rotation_toolbar_present(self, widget):
        """Панель навигации matplotlib (вращение/зум) встроена в виджет."""
        from PyQt5.QtWidgets import QToolBar
        toolbars = widget.findChildren(QToolBar)
        assert toolbars, 'нет NavigationToolbar2QT'

    def test_apply_data_roundtrip(self, widget, app):
        """Данные фонового расчёта применяются и перерисовываются."""
        from advanced_analysis import compute_psf_3d
        x, y, Z = compute_psf_3d(build_doublet(), wl=0.58756,
                                 grid_size=64, field_y=0.0)
        widget.apply_data(x, y, Z)
        assert widget.Z is Z
        assert widget.figure.axes[0].name == '3d'

    def test_pending_placeholder(self, widget):
        """Пока идёт фаза 2 — заглушка «⏳ Расчёт», не 3D-поверхность."""
        widget._pending = True
        widget.redraw()
        assert widget.figure.axes[0].name == 'rectilinear'
        texts = [t.get_text() for t in widget.figure.axes[0].texts]
        assert any('Расчёт' in t for t in texts)

    def test_no_data_placeholder(self, widget):
        widget.apply_data(None, None, None)
        texts = [t.get_text() for t in widget.figure.axes[0].texts]
        assert 'Нет данных' in texts


class TestPsf3dPanel:
    def test_tab_next_to_psf_heatmap(self, app):
        """Вкладка «PSF 3D» — сразу после 2D PSF (heatmap)."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        titles = [panel.tabText(i) for i in range(panel.count())]
        assert titles.index('PSF 3D') == titles.index('PSF') + 1

    def test_psf3d_table_reads_widget(self, widget, app):
        """Таблица PSF 3D (макс/размер/поле) читает данные виджета."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel.psf_3d_w.x_coords = widget.x_coords
        panel.psf_3d_w.y_coords = widget.y_coords
        panel.psf_3d_w.Z = widget.Z
        panel._update_psf3d_table(build_doublet())
        table = panel._table_containers['psf3d'].layout().itemAt(0).widget()
        rows = {table.item(r, 0).text(): table.item(r, 1).text()
                for r in range(table.rowCount())}
        assert 'Макс.' in rows
        assert rows['Размер'] == '64×64'
