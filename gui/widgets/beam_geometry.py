"""Beam geometry widget — entrance pupil contours for different fields.

Widgets:

* :class:`BeamGeometryWidget` — vignetting-aware pupil outlines.
"""

from __future__ import annotations

import math

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPainterPath

from optics_engine import OpticalSystem, compute_beam_geometry

from .base import AberrationPlotWidget


class BeamGeometryWidget(AberrationPlotWidget):
    """Entrance-pupil beam contours for different field angles."""

    #: Диаметр пучка, которым ограничен масштаб отрисовки (мм);
    #: из последнего расчёта габаритов (учитывает режим «реальные»).
    _DEFAULT_APERTURE_MM = 10.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.beam_data: list[dict] | None = None
        self.beam_aperture: float | None = None

    def set_data(self, sys: OpticalSystem, semi_mode: str = 'given',
                 sharp_edge: bool = True) -> None:
        """Посчитать габариты пучков и перерисовать контуры зрачка.

        ``semi_mode``/``sharp_edge`` — режим габаритов и флаг острой
        кромки (п. 15 GAP v2), см. :func:`compute_beam_geometry`.
        """
        self.apply_data(compute_beam_geometry(
            sys, semi_mode=semi_mode, sharp_edge=sharp_edge))

    def apply_data(self, beam_data: list[dict] | None) -> None:
        """Применить готовый результат (фоновый расчёт без повтора)."""
        self.beam_data = beam_data
        if beam_data:
            self.beam_aperture = 2.0 * beam_data[0].get('Ay', 0.0) or None
        else:
            self.beam_aperture = None
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

        # Диаметр пучка из последнего расчёта (режим «реальные» даёт
        # фактический габарит); раньше бралась заданная апертура системы.
        aperture = self.beam_aperture
        if not aperture or aperture <= 0:
            aperture = self._DEFAULT_APERTURE_MM

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
