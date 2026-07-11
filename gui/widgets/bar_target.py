"""Bar target image widget — ideal vs blurred line-pair profile.

Widgets:

* :class:`BarTargetWidget` — 1D bar-target profile (ideal + PSF-blurred).
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from optics_engine import OpticalSystem
from advanced_analysis import compute_bar_target_image, compute_bar_target_mtf_table
from optics_utils import get_primary_wl

from .base import AberrationPlotWidget


class BarTargetWidget(AberrationPlotWidget):
    """Bar target resolution chart — ideal and blurred profiles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_um = None
        self.ideal = None
        self.blurred = None
        self.mtf_table = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            self.x_um, self.ideal, self.blurred = compute_bar_target_image(
                sys, wl=wl, field_y=0.0, num_bars=5, bar_freq_lp_mm=10)
            self.mtf_table = compute_bar_target_mtf_table(
                sys, wl=wl, field_y=0.0, num_bars=5)
        except Exception:
            self.x_um = None
            self.ideal = None
            self.blurred = None
            self.mtf_table = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        half_h = h // 2

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRect(50, 10, w - 60, half_h - 20)
        painter.drawRect(50, half_h + 5, w - 60, half_h - 20)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(55, 25, "Идеальный профиль")
        painter.drawText(55, half_h + 20, "Размытый профиль (PSF)")

        if self.x_um is None or self.ideal is None or self.blurred is None:
            painter.setPen(QColor(150, 150, 170))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        x_min, x_max = self.x_um.min(), self.x_um.max()
        x_range = x_max - x_min if abs(x_max - x_min) > 1e-10 else 1.0

        m_left = 55
        plot_w = w - 65

        top_y = 30
        ph_top = half_h - 35
        painter.setPen(QPen(QColor(220, 220, 240), 2))
        prev = None
        step = max(1, len(self.x_um) // 300)
        for i in range(0, len(self.x_um), step):
            px = m_left + (self.x_um[i] - x_min) / x_range * plot_w
            py = top_y + ph_top - self.ideal[i] * ph_top
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        bot_y = half_h + 25
        ph_bot = half_h - 35
        painter.setPen(QPen(QColor(255, 160, 40), 2))
        prev = None
        for i in range(0, len(self.x_um), step):
            px = m_left + (self.x_um[i] - x_min) / x_range * plot_w
            py = bot_y + ph_bot - self.blurred[i] * ph_bot
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m_left, top_y + ph_top, m_left + plot_w, top_y + ph_top)
        painter.drawLine(m_left, bot_y + ph_bot, m_left + plot_w, bot_y + ph_bot)
        painter.setPen(QColor(160, 160, 180))
        painter.drawText(m_left + plot_w - 30, bot_y + ph_bot + 15, "мкм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()
