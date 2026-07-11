"""Spot diagram and related heatmap / focus-diagram widgets.

Widgets:

* :class:`SpotDiagramWidget` — polychromatic spot diagram.
* :class:`HeatmapWidget` — scatter density heatmap.
* :class:`FocusDiagramWidget` — five spot diagrams at different defocus positions.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
)
from PyQt5.QtWidgets import QWidget

from optics_engine import OpticalSystem, paraxial_trace
from aberrations import (
    compute_spot_diagram,
    compute_spot_diagram_polychromatic,
    compute_polychromatic_rms,
    compute_rms_spot,
    compute_rms_spot_xy,
    compute_spot_heatmap,
    compute_spot_diagram_at_defocus,
)
from optics_utils import get_primary_wl

from .base import (
    AberrationPlotWidget,
    InteractivePlot,
    wl_to_plot_color,
)


class SpotDiagramWidget(AberrationPlotWidget):
    """Polychromatic spot diagram (Л1.6.1)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spots_mono: list[tuple[float, float]] = []
        self.spots_poly: list[tuple[float, float, int]] = []
        self.rms: float = 0.0
        self.poly_rms: float = 0.0
        self.polychromatic: bool = True

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        self.spots_mono = compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=0.0)
        self.rms = compute_rms_spot(self.spots_mono)
        self._wl_cache = [w.value for w in sys.wavelengths]
        if len(sys.wavelengths) > 1:
            self.spots_poly = compute_spot_diagram_polychromatic(sys, num_rays=40, field_y=0.0)
            self.poly_rms = compute_polychromatic_rms(sys, num_rays=40, field_y=0.0)
        else:
            self.spots_poly = [(dx, dy, 0) for dx, dy in self.spots_mono]
            self.poly_rms = self.rms
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
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + ph + 25, f"RMS: {cur_rms:.4f} мм | {len(spots)} лучей")
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


class FocusDiagramWidget(QWidget, InteractivePlot):
    """Five spot diagrams at different image-plane positions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 300)
        self.spots_by_defocus: dict[str, tuple] = {}
        self.max_range = 0.001
        self._pending = False
        self._init_interactive()

    def mouseMoveEvent(self, event):
        self._interactive_mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._interactive_leaveEvent(event)

    def wheelEvent(self, event):
        self._interactive_wheelEvent(event)

    def mousePressEvent(self, event):
        self._interactive_mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._interactive_mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._interactive_mouseDoubleClickEvent(event)

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        parax = paraxial_trace(sys)
        bfd = parax.get('back_focal_distance', 0)
        if abs(bfd) < 1e-6:
            efl = parax.get('focal_length', 50)
            bfd = abs(efl) * 0.5
        ds = abs(bfd) * 0.01

        defoci = [
            ("номинал", 0.0),
            ("+DS'", +ds),
            ("-DS'", -ds),
            ("+2DS'", +2*ds),
            ("-2DS'", -2*ds),
        ]

        self.spots_by_defocus = {}
        all_spots = []
        for label, df in defoci:
            spots = compute_spot_diagram_at_defocus(sys, wl=wl, num_rays=60,
                                                     field_y=0.0, defocus_mm=df)
            rms_info = compute_rms_spot_xy(spots)
            self.spots_by_defocus[label] = (spots, rms_info, df)
            all_spots.extend(spots)

        if all_spots:
            self.max_range = max(math.sqrt(dx**2 + dy**2) for dx, dy in all_spots)
            self.max_range = max(self.max_range, 1e-6)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor(10, 10, 25))

        if not self.spots_by_defocus:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        labels_order = ["номинал", "+DS'", "-DS'", "+2DS'", "-2DS'"]
        n = len(labels_order)
        margin = 10
        top_margin = 25
        bot_margin = 35
        cell_w = (w - 2 * margin) / n
        cell_h = h - top_margin - bot_margin

        for idx, label in enumerate(labels_order):
            if label not in self.spots_by_defocus:
                continue
            spots, rms_info, df = self.spots_by_defocus[label]

            ox = margin + idx * cell_w
            oy = top_margin
            cw = cell_w - 4
            ch = cell_h

            painter.setPen(QPen(QColor(60, 60, 80), 1))
            painter.drawRect(int(ox), int(oy), int(cw), int(ch))

            cx = ox + cw / 2
            cy = oy + ch / 2
            scale = min(cw, ch) / (2.2 * self.max_range)

            painter.setPen(QPen(QColor(50, 50, 70), 1))
            painter.drawLine(int(cx), int(oy), int(cx), int(oy + ch))
            painter.drawLine(int(ox), int(cy), int(ox + cw), int(cy))

            painter.setPen(Qt.NoPen)
            color = QColor(0, 255, 120, 160)
            painter.setBrush(QBrush(color))
            for dx, dy in spots:
                px = cx + dx * scale
                py = cy - dy * scale
                painter.drawEllipse(int(px) - 1, int(py) - 1, 2, 2)

            painter.setPen(QColor(200, 200, 220))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(ox), int(oy - 2), int(cw), 20,
                             Qt.AlignCenter, label)

            painter.setPen(QColor(150, 200, 150))
            painter.setFont(QFont("Consolas", 7))
            rms_val = rms_info['rms_total']
            painter.drawText(int(ox), int(oy + ch + 2), int(cw), 15,
                             Qt.AlignCenter, f"RMS={rms_val:.4f}")

            painter.setPen(QColor(120, 120, 150))
            painter.drawText(int(ox), int(oy + ch + 14), int(cw), 15,
                             Qt.AlignCenter, f"Δz={df:+.3f}")

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 10))
        painter.drawText(margin, 15, "Фокусировочные диаграммы (5 позиций)")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()
