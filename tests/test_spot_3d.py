"""Тесты 3D-режима точечной диаграммы (TASK_3D, часть 2).

Переключатель «2D/3D» в самом виджете: 2D — QPainter (поведение не
меняется), 3D — matplotlib scatter (проекция '3d'): X, Y — координаты
пятна, Z — плотность, цвет — λ (полихром.) или плотность. Состояние
переключателя хранится в виджете; делегирование данных не ломает
протокол фаз расчёта панели анализа.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint


def build_doublet(wls=None) -> OpticalSystem:
    """Контрольный дублет К8/TF5 (как в test_spot_rms_xy)."""
    s = OpticalSystem(name='doublet')
    s.wavelengths = wls if wls else [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5, semi_diameter=14),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=14),
        Surface(radius=-200, glass='', thickness=0, semi_diameter=14),
    ]
    s.stop_surface = 1
    s.aperture_value = 20.0
    return s


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture
def widget(app):
    from gui.widgets.spot_diagram import SpotDiagramWidget
    w = SpotDiagramWidget()
    w.set_data(build_doublet())
    return w


@pytest.fixture
def poly_widget(app):
    from gui.widgets.spot_diagram import SpotDiagramWidget
    w = SpotDiagramWidget()
    w.set_data(build_doublet(wls=[Wavelength(0.54607, 1.0, 'e'),
                                  Wavelength(0.65627, 1.0, 'C'),
                                  Wavelength(0.48613, 1.0, 'F')]))
    return w


class TestSpot3DWidget:
    def test_data_not_empty(self, widget):
        """После set_data данные пятна не пусты (моно и полихром.)."""
        assert len(widget.spots_mono) > 0
        assert len(widget.spots_poly) > 0
        assert widget.rms > 0

    def test_widget_creates_3d_axes(self, widget):
        """Виджет создаётся; 3D-режим строит scatter в проекции '3d'."""
        widget.set_3d_enabled(True)
        assert widget.spot_3d_enabled is True
        figure = widget._view3d.figure
        assert figure.axes, 'нет осей'
        ax = figure.axes[0]
        assert ax.name == '3d'
        assert ax.collections, 'нет scatter-коллекции'
        n_shown = len(ax.collections[0].get_offsets())
        spots = widget.spots_poly if widget.spots_poly else widget.spots_mono
        assert n_shown == len(spots)

    def test_default_is_2d_and_toggle_back(self, widget):
        """По умолчанию 2D; переключение туда-обратно мгновенное."""
        assert widget.spot_3d_enabled is False
        assert widget._stack.currentIndex() == 0
        widget.set_3d_enabled(True)
        assert widget._stack.currentIndex() == 1
        widget.set_3d_enabled(False)
        assert widget.spot_3d_enabled is False
        # 2D-вид на месте и с данными
        assert len(widget._view2d.spots_mono) == len(widget.spots_mono)

    def test_state_persists_after_set_data(self, widget):
        """Состояние 3D сохраняется при обновлении данных."""
        widget.set_3d_enabled(True)
        widget.set_data(build_doublet())
        assert widget.spot_3d_enabled is True

    def test_mono_color_by_density(self, widget):
        """Одна λ: цвет по плотности (viridis), Z — плотность лучей."""
        widget.set_3d_enabled(True)
        ax = widget._view3d.figure.axes[0]
        assert 'цвет — плотность' in ax.get_title()
        assert 'Плотность' in ax.get_zlabel()

    def test_poly_color_by_wavelength(self, poly_widget):
        """Несколько λ: цвет точек — по длине волны."""
        poly_widget.set_3d_enabled(True)
        ax = poly_widget._view3d.figure.axes[0]
        assert 'цвет — λ' in ax.get_title()
        scatter = ax.collections[0]
        # разные λ → разные цвета точек (более одного уникального)
        rgba = scatter.get_facecolor()
        assert len({tuple(c) for c in rgba}) > 1

    def test_no_data_placeholder(self, app):
        """Свежий виджет без данных: 3D-режим показывает заглушку."""
        from gui.widgets.spot_diagram import SpotDiagramWidget
        w = SpotDiagramWidget()
        w.set_3d_enabled(True)
        ax = w._view3d.figure.axes[0]
        assert ax.name != '3d'  # заглушка — обычные оси
        assert ax.texts[0].get_text() == 'Нет данных'

    def test_pending_placeholder_propagates(self, widget):
        """Протокол фазы расчёта: _pending показывает «⏳ Расчёт...» в 3D."""
        widget.set_3d_enabled(True)
        widget._pending = True
        widget.update()
        ax = widget._view3d.figure.axes[0]
        assert 'Расчёт' in ax.texts[0].get_text()
        assert widget._view2d._pending is True

    def test_lazy_render_when_hidden(self, widget):
        """Скрытый 3D не перерисовывается; при показе — перерисовывается."""
        widget.set_3d_enabled(True)
        widget.set_3d_enabled(False)
        widget.set_data(build_doublet())
        assert widget._view3d._needs_redraw is True
        widget.set_3d_enabled(True)
        assert widget._view3d._needs_redraw is False

    def test_external_attr_delegation(self, widget):
        """Внешние присваивания (apply_phase2) видны обоим вложенным видам."""
        spots = [(0.001, 0.002), (0.003, -0.001)]
        widget.spots_mono = spots
        widget.rms = 0.42
        widget._wl_cache = [0.55]
        assert widget._view2d.spots_mono == spots
        assert widget._view3d.spots_mono == spots
        assert widget._view3d.rms == 0.42
        assert widget.rms == 0.42          # чтение — из 2D-вида
        assert widget._wl_cache == [0.55]

    def test_rms_label_static_through_container(self):
        """Статическая подпись RMS доступна через контейнер (контракт)."""
        from gui.widgets.spot_diagram import SpotDiagramWidget
        label = SpotDiagramWidget._rms_label(
            0.5, {'rms_x': 0.2, 'rms_y': 0.4, 'centroid_y': 0.05}, 40)
        assert 'RMS: 0.5000' in label
        assert '40 лучей' in label


class TestPanelIntegration:
    def test_panel_spot_tab_keeps_api(self, app):
        """Панель анализа: вкладка «Точечная диагр.» — новый контейнер,
        внешний API (set_data/атрибуты/ rms_xy) не изменился."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        assert hasattr(panel, 'spot_diagram')
        panel.spot_diagram.set_data(build_doublet())
        assert {'rms_x', 'rms_y', 'centroid_y'} <= set(panel.spot_diagram.rms_xy)
        assert len(panel.spot_diagram.spots_mono) > 0
