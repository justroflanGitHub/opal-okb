"""Spot diagram and related heatmap / focus-diagram widgets.

Widgets:

* :class:`SpotDiagramWidget` — полихроматическая точечная диаграмма
  с переключателем 2D/3D (кнопка в виджете, состояние сохраняется).
* :class:`SpotDiagram2DWidget` — 2D-вид пятна (QPainter, окружности Эри).
* :class:`SpotDiagram3DWidget` — 3D-вид пятна (matplotlib scatter,
  проекция ``'3d'``): X, Y — координаты пятна, Z — плотность лучей,
  цвет — длина волны (полихром.) или плотность.
* :class:`HeatmapWidget` — scatter density heatmap.
* :class:`FocusDiagramWidget` — five spot diagrams at different defocus
  positions (matplotlib, общий масштаб, шаг ΔS' из настроек анализа).
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
)

from optics_engine import OpticalSystem, paraxial_trace
from aberrations import (
    compute_spot_diagram,
    compute_spot_diagram_polychromatic,
    compute_polychromatic_rms,
    compute_rms_spot,
    compute_rms_spot_xy,
    compute_spot_heatmap,
    compute_spot_diagram_at_defocus,
    compute_focus_diagrams,
    DEFAULT_FOCUS_STEP_MM,
    FOCUS_DIAGRAM_DEFOCI,
)
from optics_utils import get_primary_wl

from .base import (
    AberrationPlotWidget,
    InteractivePlot,
    wl_to_plot_color,
)
from .mpl_widgets import (
    MplCanvasWidget, MPL_CURVE_COLOR, MPL_TEXT_COLOR, MPL_BG_COLOR,
    MPL_3D_ELEV, MPL_3D_AZIM, style_3d_axes,
)


class SpotDiagram2DWidget(AberrationPlotWidget):
    """2D-вид полихроматической точечной диаграммы (Л1.6.1, QPainter)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spots_mono: list[tuple[float, float]] = []
        self.spots_poly: list[tuple[float, float, int]] = []
        self.rms: float = 0.0
        self.rms_xy: Dict = {}
        self.poly_rms: float = 0.0
        self.poly_rms_xy: Dict = {}
        self.polychromatic: bool = True

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        self.spots_mono = compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=0.0)
        self.rms = compute_rms_spot(self.spots_mono)
        self.rms_xy = compute_rms_spot_xy(self.spots_mono)
        self._wl_cache = [w.value for w in sys.wavelengths]
        if len(sys.wavelengths) > 1:
            self.spots_poly = compute_spot_diagram_polychromatic(sys, num_rays=40, field_y=0.0)
            self.poly_rms = compute_polychromatic_rms(sys, num_rays=40, field_y=0.0)
            self.poly_rms_xy = compute_rms_spot_xy([(dx, dy) for dx, dy, _ in self.spots_poly])
        else:
            self.spots_poly = [(dx, dy, 0) for dx, dy in self.spots_mono]
            self.poly_rms = self.rms
            self.poly_rms_xy = self.rms_xy
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        spots = self.spots_poly if (self.polychromatic and self.spots_poly) else \
                [(dx, dy, 0) for dx, dy in self.spots_mono] if self.spots_mono else []

        if not spots:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        max_r = max(math.sqrt(dx**2 + dy**2) for dx, dy, _ in spots) if spots else 1
        max_r = max(max_r, 0.001)
        scale = min(pw, ph) / (2.2 * max_r)
        cx = m + pw / 2
        cy = top + ph / 2

        # Airy diffraction circles
        painter.setPen(QPen(QColor(40, 80, 40), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        for r_mm in [max_r * 0.25, max_r * 0.5, max_r * 0.75, max_r]:
            r_px = r_mm * scale
            painter.drawEllipse(int(cx - r_px), int(cy - r_px), int(2 * r_px), int(2 * r_px))

        # Coloured spot points
        painter.setPen(Qt.NoPen)
        for dx, dy, wl_idx in spots:
            if self.polychromatic and wl_idx < 100:
                wl_um = 0.588
                if wl_idx < len(self._get_wavelengths()):
                    wl_um = self._get_wavelengths()[wl_idx]
                color = wl_to_plot_color(wl_um)
                color.setAlpha(180)
            else:
                color = QColor(0, 255, 120, 180)
            painter.setBrush(QBrush(color))
            px = cx + dx * scale
            py = cy - dy * scale
            painter.drawEllipse(int(px) - 1, int(py) - 1, 3, 3)

        # Axes
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(int(cx), top, int(cx), top + ph)
        painter.drawLine(m, int(cy), m + pw, int(cy))

        # RMS readout
        cur_rms = self.poly_rms if self.polychromatic else self.rms
        cur_xy = self.poly_rms_xy if self.polychromatic else self.rms_xy
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + ph + 25,
                         self._rms_label(cur_rms, cur_xy, len(spots)))
        title = "Точечная диаграмма (полихром.)" if self.polychromatic else "Точечная диаграмма"
        painter.drawText(m + 5, top + 15, title)

        self.set_ranges(-max_r, max_r, -max_r, max_r)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()

    def _get_wavelengths(self) -> list[float]:
        """Return cached wavelength list (lazy)."""
        if not hasattr(self, '_wl_cache'):
            return [0.588]
        return self._wl_cache

    @staticmethod
    def _rms_label(rms: float, rms_xy: Dict, num_rays: int) -> str:
        """Подпись RMS под графиком пятна: общий RMS, раздельные X/Y,
        энергетический центр Y (Yцэ) и число лучей."""
        return (f"RMS: {rms:.4f} мм | "
                f"RMS_X: {rms_xy.get('rms_x', 0.0):.4f} | "
                f"RMS_Y: {rms_xy.get('rms_y', 0.0):.4f} | "
                f"Yцэ: {rms_xy.get('centroid_y', 0.0):.4f} мм | "
                f"{num_rays} лучей")


class SpotDiagram3DWidget(MplCanvasWidget):
    """3D-вид точечной диаграммы (matplotlib, проекция ``'3d'``).

    X, Y — координаты пятна (мм); Z — локальная плотность лучей
    (число точек пятна в ячейке гистограммы); цвет точек — по длине
    волны в полихроматическом режиме, иначе по плотности (viridis).
    """

    #: ячеек гистограммы плотности по каждой оси
    DENSITY_BINS = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spots_mono: list[tuple[float, float]] = []
        self.spots_poly: list[tuple[float, float, int]] = []
        self.rms: float = 0.0
        self.rms_xy: Dict = {}
        self.poly_rms: float = 0.0
        self.poly_rms_xy: Dict = {}
        self.polychromatic: bool = True
        self._wl_cache: list[float] = [0.588]
        #: контент ещё не отрисован / данные изменились — 3D перерисуется
        #: при следующем показе (ленивый рендер)
        self._needs_redraw = True

    def _get_wavelengths(self) -> list[float]:
        """Кэш длин волн (как в 2D-виде)."""
        return self._wl_cache if self._wl_cache else [0.588]

    def _render(self) -> None:
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

        self._needs_redraw = False
        if self._render_pending():
            return

        spots = self.spots_poly if (self.polychromatic and self.spots_poly) else \
                [(dx, dy, 0) for dx, dy in self.spots_mono] if self.spots_mono else []
        if not spots:
            self._render_no_data()
            return

        xs = np.asarray([dx for dx, _, _ in spots], dtype=float)
        ys = np.asarray([dy for _, dy, _ in spots], dtype=float)

        # Плотность: Z точки — населенность ячейки гистограммы, где она лежит
        bins = self.DENSITY_BINS
        span_x = max(xs.max() - xs.min(), 1e-9)
        span_y = max(ys.max() - ys.min(), 1e-9)
        hist, _, _ = np.histogram2d(xs, ys, bins=bins)
        ix = np.clip(((xs - xs.min()) / span_x * bins).astype(int), 0, bins - 1)
        iy = np.clip(((ys - ys.min()) / span_y * bins).astype(int), 0, bins - 1)
        zs = hist[ix, iy]

        # Цвет: по λ (полихром.) либо по плотности
        wls = self._get_wavelengths()
        use_wl_color = self.polychromatic and len(wls) > 1
        if use_wl_color:
            colors = []
            for _, _, wl_idx in spots:
                if wl_idx < 100 and wl_idx < len(wls):
                    colors.append(wl_to_plot_color(wls[wl_idx]).name())
                else:
                    colors.append('#00ff78')
            cmap = None
        else:
            colors = zs / max(float(zs.max()), 1.0)
            cmap = 'viridis'

        ax = self._figure.add_subplot(projection='3d')
        style_3d_axes(ax)
        ax.scatter(xs, ys, zs, c=colors, cmap=cmap, s=8,
                   depthshade=True, linewidths=0)
        ax.view_init(elev=MPL_3D_ELEV, azim=MPL_3D_AZIM)
        try:
            ax.set_box_aspect((1.0, 1.0, 0.35))
        except AttributeError:
            pass  # старые matplotlib без set_box_aspect
        ax.set_xlabel('X, мм')
        ax.set_ylabel('Y, мм')
        ax.set_zlabel('Плотность, лучей/ячейку')
        cur_rms = self.poly_rms if self.polychromatic else self.rms
        mode = ' (цвет — λ)' if use_wl_color else ' (цвет — плотность)'
        ax.set_title(f'Точечная диаграмма 3D{mode} | RMS: {cur_rms:.4f} мм')

    def _render_no_data(self) -> None:
        """Заглушка «Нет данных» до первого расчёта."""
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(MPL_BG_COLOR)
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                color=MPL_TEXT_COLOR, fontsize=12, transform=ax.transAxes)


class SpotDiagramWidget(QWidget):
    """Точечная диаграмма с переключателем 2D/3D.

    Обёртка: кнопка «2D/3D» + стек из 2D-вида (:class:`SpotDiagram2DWidget`,
    QPainter) и 3D-вида (:class:`SpotDiagram3DWidget`, matplotlib scatter).
    Переключение мгновенное, состояние хранится в виджете; 3D перерисовывается
    лениво — только когда показан. Данные и протокол фаз расчёта
    (``spots_mono``…``poly_rms_xy``, ``_wl_cache``, ``_pending``, ``update``)
    делегируются обоим видам, поэтому внешнее API (панель анализа, тесты)
    не меняется.
    """

    #: атрибуты данных, перенаправляемые обоим вложенным видам
    _DATA_ATTRS = ('spots_mono', 'spots_poly', 'rms', 'rms_xy',
                   'poly_rms', 'poly_rms_xy', 'polychromatic',
                   '_wl_cache', '_pending')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view2d = SpotDiagram2DWidget()
        self._view3d = SpotDiagram3DWidget()
        self._stack = QStackedWidget()
        self._stack.addWidget(self._view2d)   # индекс 0 — 2D (QPainter)
        self._stack.addWidget(self._view3d)   # индекс 1 — 3D (matplotlib)

        self._btn_3d = QPushButton("2D/3D")
        self._btn_3d.setMaximumWidth(55)
        self._btn_3d.setCheckable(True)
        self._btn_3d.setToolTip(
            "Переключить 2D/3D вид точечной диаграммы:\n"
            "3D — высота и цвет по плотности пятна\n"
            "(цвет по длине волны в полихром. режиме)")
        self._btn_3d.toggled.connect(self.set_3d_enabled)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addWidget(self._btn_3d)
        btn_row.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(btn_row)
        layout.addWidget(self._stack)

    # -- Делегирование данных вложенным видам ----------------------------
    def __setattr__(self, name, value):
        if name in SpotDiagramWidget._DATA_ATTRS and '_view2d' in self.__dict__:
            setattr(self._view2d, name, value)
            setattr(self._view3d, name, value)
            self._view3d._needs_redraw = True
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        # вызывается только если атрибут не найден обычным путём
        if name in SpotDiagramWidget._DATA_ATTRS and '_view2d' in self.__dict__:
            return getattr(self._view2d, name)
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}")

    # -- Public API -------------------------------------------------------
    @property
    def spot_3d_enabled(self) -> bool:
        """Включён ли 3D-режим (состояние переключателя)."""
        return self._stack.currentIndex() == 1

    def set_3d_enabled(self, enabled: bool) -> None:
        """Переключить 2D/3D-режим (мгновенно, без пересчёта данных)."""
        self._btn_3d.blockSignals(True)
        self._btn_3d.setChecked(bool(enabled))
        self._btn_3d.blockSignals(False)
        self._stack.setCurrentIndex(1 if enabled else 0)
        if enabled and self._view3d._needs_redraw:
            self._view3d.update()   # ленивая перерисовка при показе 3D

    def set_data(self, sys: OpticalSystem) -> None:
        """Пересчитать пятно (моно + полихром.) и обновить оба вида."""
        self._view2d.set_data(sys)
        for name in ('spots_mono', 'spots_poly', 'rms', 'poly_rms',
                     'polychromatic', '_wl_cache'):
            setattr(self._view3d, name, getattr(self._view2d, name))
        self._view3d._needs_redraw = True
        if self.spot_3d_enabled:
            self._view3d.update()

    def update(self) -> None:
        """Qt-update контейнера и вложенных видов (протокол ``_pending``)."""
        super().update()
        self._view2d.update()
        if self.spot_3d_enabled:
            self._view3d.update()

    @staticmethod
    def _rms_label(rms: float, rms_xy: Dict, num_rays: int) -> str:
        """Подпись RMS (делегируется 2D-виду)."""
        return SpotDiagram2DWidget._rms_label(rms, rms_xy, num_rays)


class HeatmapWidget(AberrationPlotWidget):
    """Scatter-density heatmap of the spot diagram."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.heatmap: Any = None
        self.x_range = (0, 0)
        self.y_range = (0, 0)
        self.grid_size = 100
        self.num_points = 0
        self.centroid_x = 0.0
        self.centroid_y = 0.0
        self.max_density = 0.0
        self._zoom = False
        self._zoom_rect = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            self.heatmap, self.x_range, self.y_range = compute_spot_heatmap(
                sys, wl=wl, num_rays=500, field_y=0.0, grid_size=self.grid_size)
            self.num_points = int(np.sum(self.heatmap > 0))
            if self.heatmap is not None and self.heatmap.size > 0:
                ys = np.linspace(self.y_range[0], self.y_range[1], self.grid_size)
                xs = np.linspace(self.x_range[0], self.x_range[1], self.grid_size)
                total = self.heatmap.sum()
                if total > 0:
                    yy, xx = np.meshgrid(ys, xs, indexing='ij')
                    self.centroid_x = float(np.sum(xx * self.heatmap) / total)
                    self.centroid_y = float(np.sum(yy * self.heatmap) / total)
                self.max_density = float(self.heatmap.max())
        except Exception:
            self.heatmap = None
        self.update()

    @staticmethod
    def _hot_colormap(v: float) -> tuple[int, int, int]:
        """Hot colormap: black → red → yellow → white. *v* in [0, 1]."""
        if v < 0.33:
            t = v / 0.33
            return (int(255 * t), 0, 0)
        elif v < 0.67:
            t = (v - 0.33) / 0.34
            return (255, int(255 * t), 0)
        else:
            t = (v - 0.67) / 0.33
            return (255, 255, int(255 * t))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if self.heatmap is None or self.heatmap.size == 0:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        gs = self.grid_size
        img_w = min(pw, ph)
        img_h = img_w
        ox = m + (pw - img_w) // 2
        oy = top + (ph - img_h) // 2

        from PyQt5.QtGui import QImage
        img_data = np.zeros((gs, gs, 4), dtype=np.uint8)
        for iy in range(gs):
            for ix in range(gs):
                v = self.heatmap[iy, ix]
                r, g, b = self._hot_colormap(min(1.0, max(0.0, v)))
                img_data[iy, ix] = [b, g, r, 255]

        qimg = QImage(img_data.data, gs, gs, gs * 4, QImage.Format_RGB32).copy()
        scaled = qimg.scaled(int(img_w), int(img_h))
        painter.drawImage(ox, oy, scaled)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRect(ox, oy, int(img_w), int(img_h))

        painter.setPen(QColor(180, 180, 200))
        painter.setFont(QFont("Consolas", 8))
        x_min_s = f"{self.x_range[0]*1000:.2f}"
        x_max_s = f"{self.x_range[1]*1000:.2f}"
        y_min_s = f"{self.y_range[0]*1000:.2f}"
        y_max_s = f"{self.y_range[1]*1000:.2f}"
        painter.drawText(ox, oy + int(img_h) + 12, x_min_s)
        painter.drawText(ox + int(img_w) - 40, oy + int(img_h) + 12, x_max_s + " мкм")
        painter.drawText(ox - 45, oy + 10, y_max_s)
        painter.drawText(ox - 45, oy + int(img_h), y_min_s)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Топограмма пятна рассеяния")

        painter.setPen(QColor(150, 150, 170))
        painter.drawText(m + 5, top + ph + 25,
                         f"{gs}×{gs} | макс={self.max_density:.3f} | "
                         f"центр=({self.centroid_x*1000:.2f}, {self.centroid_y*1000:.2f}) мкм")

        # Colour bar
        bar_x = ox + int(img_w) + 8
        bar_w = 12
        bar_y = oy
        bar_h = int(img_h)
        if bar_x + bar_w + 5 < w:
            for iy in range(bar_h):
                v = 1.0 - iy / max(bar_h - 1, 1)
                r, g, b = self._hot_colormap(v)
                painter.setPen(QPen(QColor(r, g, b), 1))
                painter.drawLine(bar_x, bar_y + iy, bar_x + bar_w, bar_y + iy)
            painter.setPen(QPen(QColor(80, 80, 100), 1))
            painter.drawRect(bar_x, bar_y, bar_w, bar_h)
            painter.setPen(QColor(180, 180, 200))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(bar_x + bar_w + 2, bar_y + 8, "1.0")
            painter.drawText(bar_x + bar_w + 2, bar_y + bar_h, "0.0")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._zoom = not self._zoom
            self.update()
        super().keyPressEvent(event)


class FocusDiagramWidget(MplCanvasWidget):
    """Фокусировочные диаграммы: 5 spot-диаграмм при defocus = 0, ±ΔS', ±2ΔS'.

    matplotlib 1×5 subplots с общим масштабом (одинаковые пределы осей,
    equal aspect); ΔS' — шаг фокусировки из настроек анализа панели
    (по умолчанию DEFAULT_FOCUS_STEP_MM = 0.1 мм).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spots_by_defocus: dict[str, tuple] = {}
        self.max_range: float = 1e-6
        self.focus_step_mm: float = DEFAULT_FOCUS_STEP_MM

    def set_data(self, sys: OpticalSystem,
                 focus_step_mm: float = None) -> None:
        """Расчёт 5 позиций фокуса (шаг ΔS' из настроек, мм)."""
        if focus_step_mm is not None:
            self.focus_step_mm = abs(focus_step_mm)
        try:
            self.spots_by_defocus, self.max_range = compute_focus_diagrams(
                sys, focus_step_mm=self.focus_step_mm)
        except Exception:
            self.spots_by_defocus, self.max_range = {}, 1e-6
        self.redraw()

    def apply_data(self, diagrams: dict, max_range: float = None) -> None:
        """Подставить заранее рассчитанные данные (фаза 2)."""
        self.spots_by_defocus = diagrams or {}
        self.max_range = max_range if max_range else 1e-6
        self.redraw()

    def _render(self) -> None:
        if self._render_pending():
            return
        labels = [label for label, _ in FOCUS_DIAGRAM_DEFOCI
                  if label in self.spots_by_defocus]
        if not labels:
            ax = self.figure.add_subplot(111)
            self._style_axes(ax)
            ax.set_xticks([]); ax.set_yticks([])
            ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                    color=MPL_TEXT_COLOR, transform=ax.transAxes)
            return

        axes = self.figure.subplots(1, len(labels), sharex=True, sharey=True)
        if len(labels) == 1:
            axes = [axes]
        for ax, label in zip(axes, labels):
            spots, rms_info, df = self.spots_by_defocus[label]
            self._style_axes(ax)
            if spots:
                xs = [dx for dx, _ in spots]
                ys = [dy for _, dy in spots]
                ax.scatter(xs, ys, s=4, color=MPL_CURVE_COLOR, alpha=0.8,
                           linewidths=0)
            ax.set_title(f"{label}  Δz={df:+.3f} мм", fontsize=8)
            ax.set_xlabel(f"RMS={rms_info['rms_total']:.4f} мм",
                          fontsize=8)
            r = 1.1 * self.max_range
            ax.set_xlim(-r, r)
            ax.set_ylim(-r, r)
            ax.set_aspect('equal')
        axes[0].set_ylabel('Y, мм', fontsize=8)
        for ax in axes:
            ax.label_outer()
        self.figure.suptitle(
            f"Фокусировочные диаграммы (ΔS'={self.focus_step_mm:.3f} мм)",
            color=MPL_TEXT_COLOR, fontsize=10)
        self.figure.tight_layout()
