"""Focus curve widget — MTF vs defocus position.

Widgets:

* :class:`FocusCurveWidget` — focus curve showing best-focus position.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from optics_engine import OpticalSystem
from aberrations import compute_focus_curve
from optics_utils import get_primary_wl

from .base import AberrationPlotWidget


class FocusCurveWidget(AberrationPlotWidget):
    """Focus curve: MTF vs defocus (Л1.7.4)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.curve_data = None
        self.best_defocus = 0.0
        self.best_mtf = 0.0

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        self.curve_data = compute_focus_curve(sys, wl=wl, num_points=40,
                                               defocus_range=2.0, freq_lpmm=50.0,
                                               num_rays=25, field_y=0.0)
        if self.curve_data:
            best = max(self.curve_data, key=lambda p: p[1])
            self.best_defocus = best[0]
            self.best_mtf = best[1]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.curve_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        defocus_vals = [p[0] for p in self.curve_data]
        mtf_vals = [p[1] for p in self.curve_data]
        d_min, d_max = min(defocus_vals), max(defocus_vals)
        d_range = d_max - d_min if d_max != d_min else 1.0

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        y0 = top + ph
        y1 = top
        cx = m + pw * (-d_min) / d_range if d_range > 0 else m + pw / 2

        painter.drawLine(m, y0, m + pw, y0)
        painter.drawLine(m, y0, m, y1)
        painter.setPen(QPen(QColor(50, 50, 70), 1, Qt.DashLine))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        painter.setPen(QPen(QColor(255, 180, 40), 2))
        prev = None
        for defocus, mtf in self.curve_data:
            px = m + (defocus - d_min) / d_range * pw
            py = top + ph - mtf * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        if self.best_mtf > 0:
            bx = m + (self.best_defocus - d_min) / d_range * pw
            by = top + ph - self.best_mtf * ph
            painter.setPen(QPen(QColor(255, 60, 60), 2))
            painter.drawLine(int(bx) - 6, int(by) - 6, int(bx) + 6, int(by) + 6)
            painter.drawLine(int(bx) - 6, int(by) + 6, int(bx) + 6, int(by) - 6)
            painter.setPen(QPen(QColor(255, 60, 60, 120), 1, Qt.DashLine))
            painter.drawLine(int(bx), int(by), int(bx), top + ph)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Фокусировочная кривая (MTF vs defocus)")
        painter.drawText(m + pw - 80, top + ph + 25, "Δz (мм)")
        painter.drawText(m - 45, top + 5, "1.0")
        painter.drawText(m - 45, top + ph - 5, "0.0")

        painter.drawText(m, top + ph + 25, f"{d_min:.1f}")
        painter.drawText(m + pw - 30, top + ph + 25, f"{d_max:.1f}")

        painter.setPen(QColor(255, 180, 40))
        painter.drawText(m + 5, top + ph + 40,
                         f"Лучший фокус: Δz={self.best_defocus:+.3f} мм  MTF={self.best_mtf:.4f}")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()
