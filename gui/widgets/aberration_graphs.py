"""Ray aberration fan graphs and field aberration widgets.

Widgets:

* :class:`AberrationGraphWidget` — transverse / longitudinal / wavefront fans.
* :class:`DistortionWidget` — distortion vs field.
* :class:`AstigmatismWidget` — astigmatism and field curvature vs field.
* :class:`ComaWidget` — coma vs field.
"""

from __future__ import annotations

import math
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from optics_engine import OpticalSystem, Wavelength
from aberrations import (
    trace_aberration_fan,
    compute_field_aberrations,
    compute_isoplanatism,
    compute_oblique_fan,
)
from optics_utils import get_primary_wl

from .base import AberrationPlotWidget


# ---------------------------------------------------------------------------
#  Wavelength colour / label helpers (used by AberrationGraphWidget)
# ---------------------------------------------------------------------------

_WL_COLORS = [
    (0.405, QColor(148, 0, 211)),    # h
    (0.436, QColor(100, 0, 255)),    # g
    (0.486, QColor(0, 80, 255)),     # F
    (0.546, QColor(220, 200, 0)),    # e
    (0.588, QColor(0, 200, 80)),     # d
    (0.656, QColor(255, 60, 60)),    # C
    (0.707, QColor(200, 0, 0)),      # r
]


def _wl_to_color(wl_um: float) -> QColor:
    """Return colour for nearest standard spectral line."""
    best = min(_WL_COLORS, key=lambda item: abs(item[0] - wl_um))
    return best[1]


_NAMED_WL = {
    404.66: 'h', 435.83: 'g', 486.13: 'F',
    546.07: 'e', 587.56: 'd', 656.27: 'C',
    706.52: 'r',
}


def _wl_label(wl_um: float) -> str:
    """Format a wavelength label, adding the spectral-line name when known."""
    nm = wl_um * 1000
    for std_nm, name in _NAMED_WL.items():
        if abs(nm - std_nm) < 1.0:
            return f"λ={std_nm:.1f} нм ({name})"
    return f"λ={nm:.1f} нм"


# ---------------------------------------------------------------------------
#  AberrationGraphWidget
# ---------------------------------------------------------------------------

class AberrationGraphWidget(AberrationPlotWidget):
    """Transverse / longitudinal / wavefront aberration fan graphs."""

    def __init__(self, mode: str = 'transverse', parent=None):
        super().__init__(parent)
        self.mode = mode  # 'transverse', 'longitudinal', 'wavefront'
        self.fan_data: dict[float, list] = {}
        self.isoplanatism_data: dict[float, tuple] = {}
        self.oblique_data: Any = None
        self._azimuth_deg = 0.0

    def set_azimuth(self, azimuth_deg: float) -> None:
        self._azimuth_deg = azimuth_deg

    def set_data(self, sys: OpticalSystem, azimuth_deg: float | None = None) -> None:
        if azimuth_deg is not None:
            self._azimuth_deg = azimuth_deg
        wavelengths = sys.wavelengths if sys.wavelengths else [Wavelength(0.58756)]
        self.fan_data = {}
        self.isoplanatism_data = {}
        if abs(self._azimuth_deg) > 0.1:
            wl = wavelengths[0].value
            self.oblique_data = compute_oblique_fan(sys, wl=wl, num_rays=20,
                                                      field_y=0.0,
                                                      azimuth_deg=self._azimuth_deg)
        else:
            self.oblique_data = None
            for wl in wavelengths:
                self.fan_data[wl.value] = trace_aberration_fan(sys, wl.value, num_rays=30)
                if self.mode == 'transverse':
                    self.isoplanatism_data[wl.value] = compute_isoplanatism(
                        sys, wl=wl.value, num_rays=30)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.fan_data and not self.oblique_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        all_vals: list[float] = []

        if self.oblique_data:
            pupils, dy_mer, dy_sag = self.oblique_data
            for v in dy_mer + dy_sag:
                if v is not None:
                    if self.mode == 'transverse':
                        all_vals.append(v / 1000.0)
                    else:
                        all_vals.append(v)
        else:
            for wl, fan in self.fan_data.items():
                for r in fan:
                    if r['success']:
                        if self.mode == 'transverse':
                            all_vals.append(r['dy'])
                        elif self.mode == 'longitudinal':
                            all_vals.append(r['ds'])
                        else:
                            all_vals.append(r['wave'])

        if not all_vals:
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        val_max = max(abs(v) for v in all_vals) if all_vals else 1
        val_max = max(val_max, 1e-6)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(int(cx), top, int(cx), top + ph)
        painter.drawLine(m, int(cy), m + pw, int(cy))

        if self.oblique_data:
            pupils, dy_mer, dy_sag = self.oblique_data
            painter.setPen(QPen(QColor(0, 200, 80), 2))
            prev = None
            for hgt, v in zip(pupils, dy_mer):
                if v is None:
                    prev = None; continue
                px = cx + hgt * pw / 2.0
                py = cy - (v / 1000.0) / val_max * ph / 2.0
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)
            painter.setPen(QPen(QColor(80, 180, 255), 2))
            prev = None
            for hgt, v in zip(pupils, dy_sag):
                if v is None:
                    prev = None; continue
                px = cx + hgt * pw / 2.0
                py = cy - (v / 1000.0) / val_max * ph / 2.0
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)
        else:
            for wl, fan in self.fan_data.items():
                color = _wl_to_color(wl)
                painter.setPen(QPen(color, 2))
                prev_point = None
                for r in fan:
                    if not r['success']:
                        prev_point = None
                        continue
                    pupil = r['pupil_y']
                    if self.mode == 'transverse':
                        val = r['dy']
                    elif self.mode == 'longitudinal':
                        val = r['ds']
                    else:
                        val = r['wave']
                    px = cx + pupil * pw / 2.0
                    py = cy - val / val_max * ph / 2.0
                    if prev_point:
                        painter.drawLine(int(prev_point[0]), int(prev_point[1]), int(px), int(py))
                    prev_point = (px, py)

            if self.mode == 'transverse' and self.isoplanatism_data:
                iso_max = 0.0
                for wl, (pupils_iso, iso_vals) in self.isoplanatism_data.items():
                    if iso_vals:
                        iso_max = max(iso_max, max(abs(v) for v in iso_vals))
                if iso_max < 1e-12:
                    iso_max = 1.0
                for wl, (pupils_iso, iso_vals) in self.isoplanatism_data.items():
                    if not pupils_iso:
                        continue
                    color = _wl_to_color(wl)
                    dot_color = QColor(min(255, color.red() + 80),
                                       min(255, color.green() + 80),
                                       min(255, color.blue() + 80))
                    painter.setPen(QPen(dot_color, 1.5, Qt.DotLine))
                    prev_iso = None
                    for pupil_h, iso_um in zip(pupils_iso, iso_vals):
                        val_mm = iso_um / 1000.0
                        ipx = cx + pupil_h * pw / 2.0
                        ipy = cy - val_mm / val_max * ph / 2.0
                        if prev_iso:
                            painter.drawLine(int(prev_iso[0]), int(prev_iso[1]), int(ipx), int(ipy))
                        prev_iso = (ipx, ipy)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        titles = {
            'transverse': 'Поперечные аберрации Δy\' (мм)',
            'longitudinal': 'Продольные аберрации Δs\' (мм)',
            'wavefront': 'Волновая аберрация W (λ)',
        }
        title = titles.get(self.mode, '')
        if self.oblique_data:
            title += f' [Азимут={self._azimuth_deg:.1f}°]'
        elif self.mode == 'transverse' and self.isoplanatism_data:
            title += ' + Неизопланатизм (пунктир)'
        painter.drawText(m + 5, top + 15, title)

        # Legend
        if self.oblique_data:
            legend_x = m + pw - 100
            legend_y_start = top + 12
            painter.fillRect(int(legend_x - 4), int(legend_y_start - 10),
                             104, 38, QColor(15, 15, 30, 200))
            painter.setPen(QPen(QColor(60, 60, 80), 1))
            painter.drawRect(int(legend_x - 4), int(legend_y_start - 10), 104, 38)
            painter.setPen(QPen(QColor(0, 200, 80), 3))
            painter.drawLine(int(legend_x), int(legend_y_start), int(legend_x + 18), int(legend_y_start))
            painter.setPen(QColor(200, 200, 220))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(legend_x + 22), int(legend_y_start + 4), "Мерид.")
            painter.setPen(QPen(QColor(80, 180, 255), 3))
            painter.drawLine(int(legend_x), int(legend_y_start + 16), int(legend_x + 18), int(legend_y_start + 16))
            painter.setPen(QColor(200, 200, 220))
            painter.drawText(int(legend_x + 22), int(legend_y_start + 20), "Сагит.")
        elif self.fan_data:
            legend_x = m + pw - 120
            legend_y_start = top + 12
            num_wl = len(self.fan_data)
            legend_h = num_wl * 16 + 6
            painter.fillRect(int(legend_x - 4), int(legend_y_start - 10),
                             124, int(legend_h), QColor(15, 15, 30, 200))
            painter.setPen(QPen(QColor(60, 60, 80), 1))
            painter.drawRect(int(legend_x - 4), int(legend_y_start - 10),
                             124, int(legend_h))
            for idx, wl in enumerate(sorted(self.fan_data.keys())):
                color = _wl_to_color(wl)
                label = _wl_label(wl)
                ly = legend_y_start + idx * 16
                painter.setPen(QPen(color, 3))
                painter.drawLine(int(legend_x), int(ly), int(legend_x + 18), int(ly))
                painter.setPen(QColor(200, 200, 220))
                painter.setFont(QFont("Consolas", 8))
                painter.drawText(int(legend_x + 22), int(ly + 4), label)

        painter.setPen(QColor(120, 120, 140))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + ph + 25, f"±{val_max:.4f}")

        self.set_ranges(-1.0, 1.0, -val_max, val_max)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()


# ---------------------------------------------------------------------------
#  Field aberration widgets
# ---------------------------------------------------------------------------

class DistortionWidget(AberrationPlotWidget):
    """Distortion vs field graph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data: list[dict] | None = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        self.field_data = compute_field_aberrations(sys, wl=wl)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.field_data or all(d['distortion'] is None for d in self.field_data):
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        valid = [d for d in self.field_data if d['distortion'] is not None]
        if not valid:
            painter.end(); return

        field_max = max(abs(d['field_y']) for d in valid) or 1
        dist_max = max(abs(d['distortion']) for d in valid) or 0.01
        dist_max = max(dist_max, 0.001)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(m, int(cy), m + pw, int(cy))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        painter.setPen(QPen(QColor(255, 120, 40), 2))
        prev = None
        for d in sorted(valid, key=lambda x: x['field_y']):
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['distortion'] / dist_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Дисторсия (%)")
        painter.drawText(m + 5, top + ph + 25, f"±{field_max:.1f}° / ±{dist_max:.3f}%")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class AstigmatismWidget(AberrationPlotWidget):
    """Field curvature and astigmatism: Z'm, Z's vs field."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data: list[dict] | None = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        self.field_data = compute_field_aberrations(sys, wl=wl)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.field_data or all(d['z_m'] is None for d in self.field_data):
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        valid = [d for d in self.field_data if d['z_m'] is not None]
        if not valid:
            painter.end(); return

        field_max = max(abs(d['field_y']) for d in valid) or 1
        all_z = [d['z_m'] for d in valid] + [d['z_s'] for d in valid]
        z_max = max(abs(v) for v in all_z) or 0.01
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
            py = cy - (d['z_m'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QPen(QColor(80, 160, 255), 2))
        prev = None
        for d in sorted_data:
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['z_s'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Астигматизм и кривизна поля (мм)")
        painter.setPen(QColor(0, 200, 80))
        painter.drawText(m + pw - 100, top + 15, "Z'm мерид.")
        painter.setPen(QColor(80, 160, 255))
        painter.drawText(m + pw - 100, top + 28, "Z's сагит.")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 25, f"±{field_max:.1f}° / ±{z_max:.4f} мм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class ComaWidget(AberrationPlotWidget):
    """Coma vs field graph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data: list[dict] | None = None

    def set_data(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        self.field_data = compute_field_aberrations(sys, wl=wl)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.field_data or all(d['coma'] is None for d in self.field_data):
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        valid = [d for d in self.field_data if d['coma'] is not None]
        if not valid:
            painter.end(); return

        field_max = max(abs(d['field_y']) for d in valid) or 1
        coma_max = max(abs(d['coma']) for d in valid) or 0.001
        coma_max = max(coma_max, 1e-5)

        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(m, int(cy), m + pw, int(cy))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        painter.setPen(QPen(QColor(200, 80, 255), 2))
        prev = None
        for d in sorted(valid, key=lambda x: x['field_y']):
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['coma'] / coma_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Кома (мм)")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 25, f"±{field_max:.1f}° / ±{coma_max:.5f} мм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()
