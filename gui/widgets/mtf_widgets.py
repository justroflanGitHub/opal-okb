"""MTF (Modulation Transfer Function) widget.

Widgets:

* :class:`MTFWidget` — geometric + diffraction + diffraction-limited + polychromatic MTF.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from optics_engine import OpticalSystem
from aberrations import compute_spot_diagram, compute_geometric_mtf
from optics_utils import get_primary_wl

from .base import AberrationPlotWidget


class MTFWidget(AberrationPlotWidget):
    """MTF / ЧКХ — geometric, diffraction, diffraction-limited, polychromatic."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.geo_mtf = None
        self.diff_mtf = None
        self.poly_mtf = None
        self.diff_limited_mtf = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        spots = compute_spot_diagram(sys, wl=wl, num_rays=40)
        self.geo_mtf = compute_geometric_mtf(spots, max_freq=100, num_freqs=20)
        try:
            from diffraction_mtf import compute_diffraction_mtf_quick
            self.diff_mtf = compute_diffraction_mtf_quick(sys, wl=wl)
        except Exception:
            self.diff_mtf = None
        try:
            from diffraction_mtf import compute_diffraction_limited_mtf
            self.diff_limited_mtf = compute_diffraction_limited_mtf(sys, wl=wl)
        except Exception:
            self.diff_limited_mtf = None
        if len(sys.wavelengths) > 1:
            try:
                from diffraction_mtf import compute_polychromatic_mtf
                self.poly_mtf = compute_polychromatic_mtf(sys, grid_size=32)
            except Exception:
                self.poly_mtf = None
        else:
            self.poly_mtf = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.geo_mtf and not self.diff_mtf and not self.poly_mtf:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        max_freq = 100.0
        if self.diff_mtf and self.diff_mtf['freqs']:
            max_freq = max(max_freq, max(self.diff_mtf['freqs']))
        if self.poly_mtf and self.poly_mtf['freqs']:
            max_freq = max(max_freq, max(self.poly_mtf['freqs']))

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)

        # Geometric MTF (green)
        if self.geo_mtf:
            geo_max = max(f for f, _, _ in self.geo_mtf)
            painter.setPen(QPen(QColor(0, 200, 80), 2))
            prev = None
            for freq, mtf_t, mtf_s in self.geo_mtf:
                px = m + freq / max(geo_max, 1) * pw
                py = top + ph - mtf_t * ph
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)

        # Diffraction MTF (cyan)
        if self.diff_mtf:
            freqs = self.diff_mtf['freqs']
            mt = self.diff_mtf['mtf_tangential']
            diff_max = max(freqs) if freqs else 100
            painter.setPen(QPen(QColor(80, 180, 255), 2))
            prev = None
            for i, f in enumerate(freqs):
                px = m + f / max(diff_max, 1) * pw
                py = top + ph - mt[i] * ph
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)

        # Polychromatic MTF (orange)
        if self.poly_mtf and self.poly_mtf['freqs']:
            freqs = self.poly_mtf['freqs']
            mt = self.poly_mtf['mtf_tangential']
            poly_max = max(freqs) if freqs else 100
            painter.setPen(QPen(QColor(255, 160, 40), 2))
            prev = None
            for i, f in enumerate(freqs):
                px = m + f / max(poly_max, 1) * pw
                py = top + ph - mt[i] * ph
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)

        # Diffraction-limited MTF (white dashed)
        if self.diff_limited_mtf and self.diff_limited_mtf['freqs']:
            freqs = self.diff_limited_mtf['freqs']
            mt = self.diff_limited_mtf['mtf']
            dl_max = max(freqs) if freqs else 100
            painter.setPen(QPen(QColor(255, 255, 255), 2, Qt.DashLine))
            prev = None
            for i, f in enumerate(freqs):
                px = m + f / max(dl_max, 1) * pw
                py = top + ph - mt[i] * ph
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)

        # Labels
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "ЧКХ (MTF)")
        painter.drawText(m + pw - 80, top + ph + 25, "лин/мм")
        painter.drawText(m - 40, top + 5, "1.0")
        painter.drawText(m - 40, top + ph - 5, "0.0")

        legend_x = m + 5
        legend_y = top + ph + 25
        painter.setPen(QPen(QColor(0, 200, 80)))
        painter.drawText(legend_x, legend_y, "Геом.")
        if self.diff_mtf:
            painter.setPen(QPen(QColor(80, 180, 255)))
            painter.drawText(legend_x + 45, legend_y, "Дифр.")
        if self.poly_mtf:
            painter.setPen(QPen(QColor(255, 160, 40)))
            painter.drawText(legend_x + 85, legend_y, "Полихр.")
        if self.diff_limited_mtf:
            painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
            painter.drawText(legend_x + 140, legend_y, "Безаберр.")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()
