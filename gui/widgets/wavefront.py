"""Wavefront map, Zernike coefficients, and RMS-vs-field widgets.

Widgets:

* :class:`WavefrontMapWidget` — 2D / 3D wavefront surface map.
* :class:`ZernikeWidget` — Zernike polynomial coefficient bar chart.
* :class:`WavefrontRmsVsFieldWidget` — RMS wavefront error vs field.
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
)

from optics_engine import OpticalSystem
from zernike import (
    compute_zernike_coefficients,
    compute_wavefront_map_2d,
    compute_zernike_chromatic,
)
from aberrations import compute_wavefront_rms_vs_field
from optics_utils import get_primary_wl

from .base import AberrationPlotWidget


class WavefrontMapWidget(AberrationPlotWidget):
    """2D / 3D wavefront map with Red-White-Blue diverging colormap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wf_data = None
        self.coords = None
        self.mask = None
        self._mode_3d = False

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0) -> None:
        wl = get_primary_wl(sys)
        try:
            self.wf_data, self.coords, self.mask = compute_wavefront_map_2d(
                sys, wl=wl, grid_size=48, defocus_offset=defocus_offset)
        except Exception:
            self.wf_data = None
        self.update()

    @staticmethod
    def _rdylbu_colormap(v: float) -> tuple[int, int, int]:
        """Red-White-Blue diverging colormap. *v* in [-1, 1]."""
        if v < -1:
            v = -1
        if v > 1:
            v = 1
        if v < 0:
            t = 1 + v
            return (int(255 * t), int(255 * t), 255)
        else:
            t = 1 - v
            return (255, int(255 * t), int(255 * t))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if self.wf_data is None or self.mask is None:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        if self._mode_3d:
            self._paint_3d(painter, m, top, pw, ph)
        else:
            self._paint_2d(painter, m, top, pw, ph, w, h)

        self.paint_finalize(painter, self._plot_rect)
        painter.end()

    def _paint_2d(self, painter, m, top, pw, ph, w, h):
        gs = self.wf_data.shape[0]
        img_w = min(pw, ph)
        img_h = img_w
        ox = m + (pw - img_w) // 2
        oy = top + (ph - img_h) // 2

        valid = self.wf_data[self.mask > 0]
        if valid.size == 0:
            return
        w_max = max(abs(valid.max()), abs(valid.min()), 1e-6)

        from PyQt5.QtGui import QImage
        img_data = np.zeros((gs, gs, 4), dtype=np.uint8)
        for iy in range(gs):
            for ix in range(gs):
                if self.mask[iy, ix] > 0:
                    v = self.wf_data[iy, ix] / w_max
                    r, g, b = self._rdylbu_colormap(v)
                else:
                    r, g, b = 10, 10, 25
                img_data[iy, ix] = [b, g, r, 255]

        qimg = QImage(img_data.data, gs, gs, gs * 4, QImage.Format_RGB32).copy()
        scaled = qimg.scaled(int(img_w), int(img_h))
        painter.drawImage(ox, oy, scaled)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRect(ox, oy, int(img_w), int(img_h))

        bar_x = ox + int(img_w) + 8
        bar_w = 12
        bar_y = oy
        bar_h = int(img_h)
        if bar_x + bar_w + 40 < w:
            for iy in range(bar_h):
                v = 1.0 - 2.0 * iy / max(bar_h - 1, 1)
                r, g, b = self._rdylbu_colormap(v)
                painter.setPen(QPen(QColor(r, g, b), 1))
                painter.drawLine(bar_x, bar_y + iy, bar_x + bar_w, bar_y + iy)
            painter.setPen(QPen(QColor(80, 80, 100), 1))
            painter.drawRect(bar_x, bar_y, bar_w, bar_h)
            painter.setPen(QColor(180, 180, 200))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(bar_x + bar_w + 2, bar_y + 8, f"+{w_max:.2f}λ")
            painter.drawText(bar_x + bar_w + 2, bar_y + bar_h // 2 + 4, "0")
            painter.drawText(bar_x + bar_w + 2, bar_y + bar_h, f"-{w_max:.2f}λ")

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Карта волнового фронта (λ) [2D]")

    def _paint_3d(self, painter, m, top, pw, ph):
        gs = self.wf_data.shape[0]
        valid = self.wf_data[self.mask > 0]
        if valid.size == 0:
            return
        w_max = max(abs(valid.max()), abs(valid.min()), 1e-6)

        step = max(1, gs // 30)
        Zs = self.wf_data[::step, ::step]
        Ms = self.mask[::step, ::step]
        ny_s, nx_s = Zs.shape

        scale_xy = min(pw, ph) * 0.35 / max(nx_s, ny_s)
        scale_z = ph * 0.35

        def project(ix, iy, zv):
            px = (ix - nx_s / 2) * scale_xy * 0.7 - (iy - ny_s / 2) * scale_xy * 0.7
            py = (ix - nx_s / 2) * scale_xy * 0.35 + (iy - ny_s / 2) * scale_xy * 0.35 - zv * scale_z
            return (m + pw / 2 + px, top + ph * 0.65 + py)

        for iy in range(ny_s - 1, -1, -1):
            for ix in range(nx_s - 1, -1, -1):
                if Ms[iy, ix] < 0.5:
                    continue
                z0 = Zs[iy, ix] / w_max
                r, g, b = self._rdylbu_colormap(z0)
                shade = 0.5 + 0.5 * (1.0 - iy / max(ny_s - 1, 1))
                r = min(255, int(r * shade))
                g = min(255, int(g * shade))
                b = min(255, int(b * shade))

                x0, y0 = project(ix, iy, z0)
                x_base, y_base = project(ix, iy, 0)

                if abs(z0) > 0.01:
                    painter.setPen(QPen(QColor(r // 2, g // 2, b // 2, 80), 1))
                    painter.drawLine(int(x0), int(y0), int(x_base), int(y_base))

                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(r, g, b)))
                sz = max(2, int(3 * shade))
                painter.drawEllipse(int(x0) - sz // 2, int(y0) - sz // 2, sz, sz)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Карта волнового фронта (λ) [3D]")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 25, f"PV={valid.max()-valid.min():.3f}λ | RMS={np.sqrt(np.mean(valid**2)):.3f}λ")


class ZernikeWidget(AberrationPlotWidget):
    """Zernike polynomial coefficient bar chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.coeffs: list = []
        self.chromatic_data = None
        self._show_chromatic = False

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0) -> None:
        wl = get_primary_wl(sys)
        try:
            self.coeffs = compute_zernike_coefficients(sys, wl=wl, num_rays=32,
                                                        max_order=4,
                                                        defocus_offset=defocus_offset)
        except Exception:
            self.coeffs = []
        if len(sys.wavelengths) > 1:
            try:
                self.chromatic_data = compute_zernike_chromatic(sys, num_rays=32, max_order=4)
            except Exception:
                self.chromatic_data = None
        else:
            self.chromatic_data = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.coeffs and not self.chromatic_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        if self._show_chromatic and self.chromatic_data:
            self._paint_chromatic(painter, m, top, pw, ph)
        else:
            self._paint_single(painter, m, top, pw, ph)

        self.paint_finalize(painter, self._plot_rect)
        painter.end()

    def _paint_single(self, painter, m, top, pw, ph):
        data = [(c, n) for c, n in self.coeffs if 'Piston' not in n]
        if not data:
            return
        vals = [abs(c) for c, _ in data]
        val_max = max(vals) if vals else 1.0
        val_max = max(val_max, 1e-6)
        n_bars = len(data)
        bar_w = pw / (n_bars * 1.5)
        gap = bar_w * 0.25
        cy = top + ph / 2
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, int(cy), m + pw, int(cy))
        for i, (coeff, name) in enumerate(data):
            color = QColor(80, 160, 255) if coeff >= 0 else QColor(255, 80, 80)
            x = m + gap + i * (bar_w + gap)
            bar_h = abs(coeff) / val_max * (ph / 2.0)
            if coeff >= 0:
                painter.fillRect(int(x), int(cy - bar_h), int(bar_w), int(bar_h), color)
            else:
                painter.fillRect(int(x), int(cy), int(bar_w), int(bar_h), color)
            painter.setPen(QColor(180, 180, 200))
            painter.setFont(QFont("Consolas", 7))
            painter.save()
            painter.translate(int(x + bar_w / 2), int(top + ph + 5))
            painter.rotate(-45)
            short = name.split()[-1] if ' ' in name else name
            painter.drawText(0, 0, short)
            painter.restore()
            painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Коэффициенты Цернике (λ)")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 35, f"Шкала: ±{val_max:.3f} λ")

    def _paint_chromatic(self, painter, m, top, pw, ph):
        datasets = {}
        for key, coeffs in self.chromatic_data.items():
            if not key.startswith('delta_'):
                datasets[key] = coeffs
        if not datasets:
            return

        first_key = list(datasets.keys())[0]
        data = [(c, n) for c, n in datasets[first_key] if 'Piston' not in n]
        if not data:
            return

        all_vals = []
        for key, coeffs in datasets.items():
            for c, n in coeffs:
                if 'Piston' not in n:
                    all_vals.append(abs(c))
        val_max = max(all_vals) if all_vals else 1.0
        val_max = max(val_max, 1e-6)

        n_bars = len(data)
        n_sets = len(datasets)
        group_w = pw / (n_bars * 1.2)
        bar_w = group_w / (n_sets + 0.5)
        gap = (group_w - bar_w * n_sets) / 2
        cy = top + ph / 2

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, int(cy), m + pw, int(cy))

        colors = [QColor(80, 160, 255), QColor(255, 80, 80), QColor(0, 200, 80),
                  QColor(255, 160, 40), QColor(200, 80, 255)]

        for bar_idx, (_, name) in enumerate(data):
            x_start = m + bar_idx * group_w + gap
            for set_idx, (key, coeffs) in enumerate(datasets.items()):
                coeff = 0.0
                for c, n in coeffs:
                    if n == name:
                        coeff = c
                        break
                color = colors[set_idx % len(colors)]
                x = x_start + set_idx * bar_w
                bar_h = abs(coeff) / val_max * (ph / 2.0)
                if coeff >= 0:
                    painter.fillRect(int(x), int(cy - bar_h), int(bar_w), int(bar_h), color)
                else:
                    painter.fillRect(int(x), int(cy), int(bar_w), int(bar_h), color)

            painter.setPen(QColor(180, 180, 200))
            painter.setFont(QFont("Consolas", 7))
            painter.save()
            painter.translate(int(x_start + group_w / 2 - gap), int(top + ph + 5))
            painter.rotate(-45)
            short = name.split()[-1] if ' ' in name else name
            painter.drawText(0, 0, short)
            painter.restore()
            painter.setPen(QPen(QColor(80, 80, 100), 1))

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Цернике: хроматизм")

        legend_x = m + pw - 100
        legend_y_start = top + 25
        painter.fillRect(int(legend_x - 4), int(legend_y_start - 10),
                         104, n_sets * 16 + 6, QColor(15, 15, 30, 200))
        for idx, key in enumerate(datasets.keys()):
            ly = legend_y_start + idx * 16
            painter.setPen(QPen(colors[idx % len(colors)], 3))
            painter.drawLine(int(legend_x), int(ly), int(legend_x + 18), int(ly))
            painter.setPen(QColor(200, 200, 220))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(legend_x + 22), int(ly + 4), key)

        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 35, f"Шкала: ±{val_max:.3f} λ")


class WavefrontRmsVsFieldWidget(AberrationPlotWidget):
    """RMS wavefront error vs field angle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        self.field_data = compute_wavefront_rms_vs_field(sys, wl=wl)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.field_data or not self.field_data[0]:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        field_vals, rms_full, rms_no_def, rms_no_tilt = self.field_data

        all_vals = [v for v in rms_full + rms_no_def + rms_no_tilt
                    if not (v != v)]
        if not all_vals:
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        val_max = max(abs(v) for v in all_vals)
        val_max = max(val_max, 1e-6)
        field_max = max(abs(f) for f in field_vals) if field_vals else 1.0
        field_max = max(field_max, 1e-6)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top, m, top + ph)
        painter.drawLine(m, top + ph, m + pw, top + ph)

        curves = [
            (rms_full, QColor(60, 130, 255), "Полное СКВ", 2.0, Qt.SolidLine),
            (rms_no_def, QColor(60, 220, 100), "За вычетом дефокуса", 2.0, Qt.SolidLine),
            (rms_no_tilt, QColor(255, 80, 80), "За вычетом наклона", 2.0, Qt.SolidLine),
        ]

        for data, color, label, width, style in curves:
            painter.setPen(QPen(color, width, style))
            prev = None
            for i, (f, v) in enumerate(zip(field_vals, data)):
                if v != v:
                    prev = None
                    continue
                px = m + f / field_max * pw
                py = top + ph - v / val_max * ph
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "СКВ волновой аберрации по полю")

        legend_x = m + pw - 180
        legend_y = top + 25
        painter.fillRect(int(legend_x - 4), int(legend_y - 14),
                         184, 52, QColor(15, 15, 30, 200))
        painter.setPen(QPen(QColor(60, 60, 80), 1))
        painter.drawRect(int(legend_x - 4), int(legend_y - 14), 184, 52)
        for idx, (_, color, label, _, _) in enumerate(curves):
            ly = legend_y + idx * 16
            painter.setPen(QPen(color, 3))
            painter.drawLine(int(legend_x), int(ly), int(legend_x + 18), int(ly))
            painter.setPen(QColor(200, 200, 220))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(legend_x + 22), int(ly + 4), label)

        painter.setPen(QColor(120, 120, 140))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + pw + 3, top + 5, f"{val_max:.4f} λ")
        painter.drawText(m + pw + 3, top + ph, "0")
        painter.drawText(m, top + ph + 20, "0")
        painter.drawText(m + pw - 20, top + ph + 20, f"{field_max:.1f}°")

        self.set_ranges(-1.0, 1.0, -val_max, val_max)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()
