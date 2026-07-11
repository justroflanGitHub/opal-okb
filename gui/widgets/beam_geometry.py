"""Beam geometry widget — entrance pupil contours for different fields.

Widgets:

* :class:`BeamGeometryWidget` — vignetting-aware pupil outlines.
"""

from __future__ import annotations

import math

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPainterPath

from optics_engine import OpticalSystem, compute_beam_geometry
from optics_utils import get_effective_aperture

from .base import AberrationPlotWidget


class BeamGeometryWidget(AberrationPlotWidget):
    """Entrance-pupil beam contours for different field angles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.beam_data: list[dict] | None = None

    def set_data(self, sys: OpticalSystem) -> None:
        self.beam_data = compute_beam_geometry(sys)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.beam_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        aperture = 0.0
        if hasattr(self, '_sys_ref'):
            aperture = get_effective_aperture(self._sys_ref, default=10.0)
        if aperture <= 0:
            aperture = 10.0

        colors = [QColor(0, 200, 80), QColor(80, 180, 255), QColor(255, 160, 40),
                  QColor(255, 80, 80), QColor(200, 80, 255)]

        scale = min(pw, ph) / (aperture * 1.2) if aperture > 0 else 1.0
        cx = m + pw / 2
        cy = top + ph / 2

        r_pupil = aperture / 2.0
        r_px = r_pupil * scale
        painter.setPen(QPen(QColor(100, 100, 120), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - r_px), int(cy - r_px), int(2 * r_px), int(2 * r_px))

        for idx, bd in enumerate(self.beam_data):
            color = colors[idx % len(colors)]
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)

            vign_u = bd.get('vignetting_upper', 1.0)
            vign_l = bd.get('vignetting_lower', 1.0)
            Ay = bd.get('Ay', aperture / 2)

            r_upper = vign_u * Ay * scale
            r_lower = vign_l * Ay * scale
            r_sag = bd.get('Ax', Ay) * scale

            path = QPainterPath()
            n_pts = 64
            for i in range(n_pts + 1):
                angle = 2 * math.pi * i / n_pts
                sin_a = math.sin(angle)
                cos_a = math.cos(angle)
                if sin_a >= 0:
                    r_y = r_upper
                else:
                    r_y = r_lower
                px = cx + cos_a * r_sag
                py = cy - sin_a * r_y
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            painter.drawPath(path)

            painter.setPen(color)
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(cx + r_sag + 5), int(cy - idx * 14), f"{bd['field_y']:.1f}°")

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(int(cx), top, int(cx), top + ph)
        painter.drawLine(m, int(cy), m + pw, int(cy))

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Контуры входного зрачка")
        painter.drawText(m + 5, top + ph + 25, f"D = {aperture:.1f} мм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()
