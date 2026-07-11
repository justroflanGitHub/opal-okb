"""Chief ray characteristics widget.

Widgets:

* :class:`ChiefRayWidget` — chief ray distortion, astigmatism, lateral colour.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from optics_engine import OpticalSystem
from aberrations import compute_chief_ray_characteristics

from .base import AberrationPlotWidget


class ChiefRayWidget(AberrationPlotWidget):
    """Chief ray characteristics: distortion, astigmatism, chromatism."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chief_data: list[dict] | None = None

    def set_data(self, sys: OpticalSystem) -> None:
        self.chief_data = compute_chief_ray_characteristics(sys)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.chief_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        valid = [d for d in self.chief_data if d['field_y'] != 0]
        if not valid:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Только осевое поле")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        field_max = max(abs(d['field_y']) for d in valid) or 1
        all_z = [d['Zm'] for d in valid] + [d['Zs'] for d in valid]
        z_max = max(abs(v) for v in all_z if v is not None) if all_z else 0.01
        z_max = max(z_max, 0.001)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(m, int(cy), m + pw, int(cy))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        sorted_data = sorted(valid, key=lambda x: x['field_y'])

        painter.setPen(QPen(QColor(0, 200, 80), 2))
        prev = None
        for d in sorted_data:
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['Zm'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QPen(QColor(80, 160, 255), 2))
        prev = None
        for d in sorted_data:
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['Zs'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        dist_vals = [d['distortion_rel'] for d in valid if d['distortion_rel'] is not None]
        if dist_vals:
            dist_max = max(abs(v) for v in dist_vals) or 0.01
            dist_max = max(dist_max, 0.001)
            painter.setPen(QPen(QColor(255, 160, 40), 2, Qt.DashLine))
            prev = None
            for d in sorted_data:
                if d['distortion_rel'] is not None:
                    px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
                    py = cy - (d['distortion_rel'] / dist_max) * ph / 2.0
                    if prev:
                        painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                    prev = (px, py)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Характеристики главных лучей")
        painter.setPen(QColor(0, 200, 80))
        painter.drawText(m + pw - 100, top + 15, "Z'm мерид.")
        painter.setPen(QColor(80, 160, 255))
        painter.drawText(m + pw - 100, top + 28, "Z's сагит.")
        painter.setPen(QColor(255, 160, 40))
        painter.drawText(m + pw - 100, top + 41, "Дисторсия")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 25, f"±{field_max:.1f}° / ±{z_max:.4f} мм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()
