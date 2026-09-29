"""PSF, LSF, ESF, ENC, PTF, and PSF 3D widgets.

Widgets:

* :class:`PSFWidget` — 2D PSF heatmap.
* :class:`LSFWidget` — Line Spread Function (tangential + sagittal).
* :class:`ENCWidget` — Encircled Energy curve.
* :class:`PTFWidget` — Phase Transfer Function.
* :class:`ESFWidget` — Edge Spread Function.
* :class:`PSF3DWidget` — вращаемая 3D PSF (matplotlib surface).
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont

from optics_engine import OpticalSystem
from advanced_analysis import (
    compute_psf, compute_lsf, compute_enc, compute_ptf, compute_esf,
    compute_psf_3d,
)
from optics_utils import get_primary_wl

from .base import AberrationPlotWidget
from .mpl_widgets import MplSurface3DWidget


class PSFWidget(AberrationPlotWidget):
    """2D PSF (Point Spread Function) heatmap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.psf_data = None
        self.dx = None
        self.dy = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            self.psf_data, self.dx, self.dy = compute_psf(sys, wl=wl, num_rays=64)
        except Exception:
            self.psf_data = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if self.psf_data is None:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        psf = self.psf_data
        ny, nx = psf.shape
        img_w = min(pw, ph)
        img_h = img_w
        ox = m + (pw - img_w) // 2
        oy = top + (ph - img_h) // 2

        psf_log = np.log10(psf + 1e-6)
        vmin, vmax = psf_log.min(), psf_log.max()
        if vmax - vmin < 1e-10:
            vmax = vmin + 1
        normalized = ((psf_log - vmin) / (vmax - vmin) * 255).astype(np.uint8)

        from PyQt5.QtGui import QImage
        img_data = np.zeros((ny, nx, 4), dtype=np.uint8)
        for i in range(ny):
            for j in range(nx):
                v = normalized[i, j]
                if v < 64:
                    r, g, b = 0, 0, v * 4
                elif v < 128:
                    r, g, b = 0, (v - 64) * 4, 255
                elif v < 192:
                    r, g, b = (v - 128) * 4, 255, 255 - (v - 128) * 4
                else:
                    r, g, b = 255, 255, (v - 192) * 4
                img_data[i, j] = [b, g, r, 255]

        qimg = QImage(img_data.data, nx, ny, nx * 4, QImage.Format_RGB32).copy()
        scaled = qimg.scaled(int(img_w), int(img_h))
        painter.drawImage(ox, oy, scaled)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRect(ox, oy, int(img_w), int(img_h))

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "PSF (Point Spread Function)")
        if self.dx is not None:
            painter.drawText(m + 5, top + ph + 25,
                             f"{self.dx.min():.1f}..{self.dx.max():.1f} мкм (log scale)")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class LSFWidget(AberrationPlotWidget):
    """LSF (Line Spread Function) — tangential + sagittal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lsf_tan = None
        self.lsf_sag = None
        self.axis = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            self.lsf_tan, ax1 = compute_lsf(sys, wl=wl, num_rays=64, direction='tangential')
            self.lsf_sag, ax2 = compute_lsf(sys, wl=wl, num_rays=64, direction='sagittal')
            self.axis = ax1
        except Exception:
            self.lsf_tan = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if self.lsf_tan is None:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)

        x_min, x_max = self.axis.min(), self.axis.max()
        x_range = x_max - x_min if x_max != x_min else 1.0

        painter.setPen(QPen(QColor(0, 200, 80), 2))
        prev = None
        for val, x in zip(self.lsf_tan, self.axis):
            px = m + (x - x_min) / x_range * pw
            py = top + ph - val * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QPen(QColor(80, 180, 255), 2))
        prev = None
        for val, x in zip(self.lsf_sag, self.axis):
            px = m + (x - x_min) / x_range * pw
            py = top + ph - val * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "LSF (Line Spread Function)")
        painter.drawText(m + pw - 60, top + ph + 25, "мкм")
        painter.drawText(m - 40, top + 5, "1.0")
        painter.drawText(m - 40, top + ph - 5, "0.0")
        painter.setPen(QPen(QColor(0, 200, 80)))
        painter.drawText(m + 5, top + ph + 25, "Мерид.")
        painter.setPen(QPen(QColor(80, 180, 255)))
        painter.drawText(m + 60, top + ph + 25, "Сагит.")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class ENCWidget(AberrationPlotWidget):
    """Encircled Energy (ENC) curve."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.r_um = None
        self.enc = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            self.r_um, self.enc = compute_enc(sys, wl=wl, num_rays=100)
        except Exception:
            self.r_um = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if self.r_um is None:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)

        r_max = self.r_um.max()
        if r_max < 1e-10:
            r_max = 1.0

        painter.setPen(QPen(QColor(255, 160, 40), 2))
        prev = None
        for r, e in zip(self.r_um, self.enc):
            px = m + r / r_max * pw
            py = top + ph - e * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        for pct, color in [(0.5, QColor(100, 100, 120)),
                            (0.8, QColor(100, 100, 120)),
                            (0.9, QColor(100, 100, 120))]:
            py = top + ph - pct * ph
            painter.setPen(QPen(color, 1, Qt.DashLine))
            painter.drawLine(m, int(py), m + pw, int(py))
            painter.setPen(QColor(120, 120, 140))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(m + pw + 2, int(py) + 4, f"{int(pct*100)}%")

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Encircled Energy (ENC)")
        painter.drawText(m + pw - 40, top + ph + 25, "мкм")
        painter.drawText(m - 40, top + 5, "1.0")
        painter.drawText(m - 40, top + ph - 5, "0.0")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class PTFWidget(AberrationPlotWidget):
    """PTF (Phase Transfer Function) graph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ptf_data = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            self.ptf_data = compute_ptf(sys, wl=wl, num_rays=64)
        except Exception:
            self.ptf_data = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if self.ptf_data is None:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        freqs = self.ptf_data['freqs']
        ptf_t = self.ptf_data['ptf_tangential']
        ptf_s = self.ptf_data['ptf_sagittal']

        if not freqs:
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        max_freq = max(freqs) if freqs else 100
        all_vals = ptf_t + ptf_s
        ptf_max = max(abs(v) for v in all_vals) if all_vals else 3.14
        ptf_max = max(ptf_max, 0.01)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)
        cy = top + ph / 2
        painter.setPen(QPen(QColor(50, 50, 70), 1, Qt.DashLine))
        painter.drawLine(m, int(cy), m + pw, int(cy))

        painter.setPen(QPen(QColor(0, 200, 80), 2))
        prev = None
        for f, v in zip(freqs, ptf_t):
            px = m + f / max(max_freq, 1) * pw
            py = cy - v / ptf_max * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QPen(QColor(80, 180, 255), 2))
        prev = None
        for f, v in zip(freqs, ptf_s):
            px = m + f / max(max_freq, 1) * pw
            py = cy - v / ptf_max * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "PTF (Phase Transfer Function)")
        painter.drawText(m + pw - 60, top + ph + 25, "лин/мм")
        painter.drawText(m - 40, top + 5, f"+{ptf_max:.2f}")
        painter.drawText(m - 40, top + ph - 5, f"-{ptf_max:.2f}")
        painter.setPen(QPen(QColor(0, 200, 80)))
        painter.drawText(m + 5, top + ph + 25, "Мерид.")
        painter.setPen(QPen(QColor(80, 180, 255)))
        painter.drawText(m + 60, top + ph + 25, "Сагит.")

        self.set_ranges(-1.0, 1.0, -max_freq, max_freq)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class ESFWidget(AberrationPlotWidget):
    """ESF (Edge Spread Function) — S-curve."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_um = None
        self.esf = None

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0) -> None:
        wl = get_primary_wl(sys)
        try:
            self.x_um, self.esf = compute_esf(sys, wl=wl, field_y=0.0)
        except Exception:
            self.x_um = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if self.x_um is None or self.esf is None:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        x_min, x_max = self.x_um.min(), self.x_um.max()
        x_range = x_max - x_min if abs(x_max - x_min) > 1e-10 else 1.0

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)

        painter.setPen(QPen(QColor(255, 160, 40), 2))
        prev = None
        step = max(1, len(self.x_um) // 200)
        for i in range(0, len(self.x_um), step):
            px = m + (self.x_um[i] - x_min) / x_range * pw
            py = top + ph - self.esf[i] * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QPen(QColor(100, 100, 120), 1, Qt.DashLine))
        py_half = top + ph - 0.5 * ph
        painter.drawLine(m, int(py_half), m + pw, int(py_half))

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "ESF (Edge Spread Function)")
        painter.drawText(m + pw - 60, top + ph + 25, "мкм")
        painter.drawText(m - 40, top + 5, "1.0")
        painter.drawText(m - 40, top + ph - 5, "0.0")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class PSF3DWidget(MplSurface3DWidget):
    """Вращаемая 3D PSF — matplotlib surface (п. 5 GAP v2).

    Истинная 3D-поверхность :meth:`~mpl_toolkits.mplot3d.axes3d.Axes3D.
    plot_surface` с панелью навигации matplotlib: вращение перетаскиванием
    мышью, зум, сохранение. Ранее — статичная псевдо-3D изометрия QPainter.
    Рендер общий с 3D волновым фронтом (:class:`MplSurface3DWidget`).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_coords = None
        self.y_coords = None
        self.Z = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            self.x_coords, self.y_coords, self.Z = compute_psf_3d(
                sys, wl=wl, grid_size=64, field_y=0.0)
        except Exception:
            self.Z = None
        self.update()

    def apply_data(self, x_coords, y_coords, Z) -> None:
        """Применить данные фонового расчёта (фаза 2 / precomputed)."""
        self.x_coords, self.y_coords, self.Z = x_coords, y_coords, Z
        self.update()

    # -- Hooks ------------------------------------------------------------

    def _surface_data(self):
        if self.Z is None or self.x_coords is None or self.y_coords is None:
            return None
        return self.x_coords, self.y_coords, self.Z

    def _axis_labels(self):
        return ('X, мкм', 'Y, мкм', 'I, отн. ед.')

    def _title(self):
        return 'PSF 3D — поверхность вращается мышью'

    def _cbar_label(self):
        return 'I, отн. ед.'
