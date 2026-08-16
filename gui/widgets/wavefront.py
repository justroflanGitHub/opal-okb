"""Wavefront map, Zernike coefficients, and RMS-vs-field widgets.

Widgets:

* :class:`WavefrontMapWidget` — 2D wavefront surface map (уровни W).
* :class:`Wavefront3DWidget` — вращаемый 3D волновой фронт (п. 10 GAP v2).
* :class:`ZernikeWidget` — Zernike polynomial coefficient bar chart.
* :class:`WfRmsFieldMplWidget` — RMS wavefront error vs field (matplotlib).
"""

from __future__ import annotations

import math

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QFont,
)

from optics_engine import OpticalSystem, ObjectType
from zernike import (
    compute_zernike_coefficients,
    compute_wavefront_map_2d,
    compute_zernike_chromatic,
)
from aberrations import compute_wavefront_rms_vs_field
from optics_utils import get_primary_wl

from .base import AberrationPlotWidget
from .mpl_widgets import (MplCanvasWidget, MplSurface3DWidget,
                          MPL_CURVE_COLOR, MPL_TEXT_COLOR)

# Единицы поля для подписи оси: дальний тип — градусы, ближний — мм предмета
FIELD_UNIT_BY_TYPE = {
    ObjectType.INFINITE: '°',
    ObjectType.FINITE: 'мм',
}


class WavefrontMapWidget(AberrationPlotWidget):
    """2D карта волнового фронта (уровни W на зрачке).

    Расходящаяся карта цветов красный–белый–синий; 3D-представление
    той же карты — :class:`Wavefront3DWidget` (п. 10 GAP v2).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wf_data = None
        self.coords = None
        self.mask = None

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

class Wavefront3DWidget(MplSurface3DWidget):
    """Вращаемый 3D волновой фронт W(x, y) на зрачке (п. 10 GAP v2).

    Та же карта W, что и в 2D-виде (:class:`WavefrontMapWidget`), —
    единый расчёт :func:`zernike.compute_wavefront_map_2d`; расходящаяся
    карта цветов (красный — W > 0), вне зрачка поверхность замаскирована.
    """

    #: расходящаяся карта цветов волнового фронта
    SURF_CMAP = 'RdBu_r'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wf_data = None
        self.coords = None
        self.mask = None

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0) -> None:
        wl = get_primary_wl(sys)
        try:
            self.wf_data, self.coords, self.mask = compute_wavefront_map_2d(
                sys, wl=wl, grid_size=48, defocus_offset=defocus_offset)
        except Exception:
            self.wf_data = None
        self.update()

    def apply_data(self, wf_data, coords, mask) -> None:
        """Применить данные фонового расчёта (фаза 2 / precomputed)."""
        self.wf_data, self.coords, self.mask = wf_data, coords, mask
        self.update()

    # -- Hooks ------------------------------------------------------------

    def _surface_data(self):
        if self.wf_data is None or self.mask is None or self.coords is None:
            return None
        return self.coords, self.coords, self.wf_data, self.mask

    def _axis_labels(self):
        return ('X зрачка (норм.)', 'Y зрачка (норм.)', 'W, λ')

    def _title(self):
        return 'Волновой фронт 3D — поверхность вращается мышью'

    def _cbar_label(self):
        return 'W, λ'


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


class WfRmsFieldMplWidget(MplCanvasWidget):
    """СКВ волновой аберрации W_RMS vs поле (matplotlib, все точки поля).

    График строится :func:`aberrations.compute_wavefront_rms_vs_field`
    на гексаполярной сетке зрачка; основная λ системы.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data = None
        self.field_unit = '°'
        self.wl_label = ''

    def set_data(self, sys: OpticalSystem) -> None:
        """Расчёт СКВ по всем точкам поля системы (основная λ)."""
        wl = get_primary_wl(sys)
        try:
            self.field_data = compute_wavefront_rms_vs_field(sys, wl=wl)
        except Exception:
            self.field_data = None
        self.field_unit = FIELD_UNIT_BY_TYPE.get(sys.object_type, '°')
        self.wl_label = f"{wl:.4f} мкм"
        self.redraw()

    def apply_data(self, field_data, field_unit: str = '°',
                   wl_label: str = '') -> None:
        """Подставить заранее рассчитанные данные (фаза 2)."""
        self.field_data = field_data
        self.field_unit = field_unit
        self.wl_label = wl_label
        self.redraw()

    def _render(self) -> None:
        if self._render_pending():
            return
        ax = self.figure.add_subplot(111)
        self._style_axes(ax)
        if not self.field_data or not self.field_data[0]:
            ax.set_xticks([]); ax.set_yticks([])
            ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                    color=MPL_TEXT_COLOR, transform=ax.transAxes)
            return
        fields, rms = self.field_data
        pts = [(f, r) for f, r in zip(fields, rms) if math.isfinite(r)]
        if pts:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, marker='o', markersize=4, linewidth=1.8,
                    color=MPL_CURVE_COLOR)
        ax.set_xlabel(f'Поле ({self.field_unit})')
        ax.set_ylabel('СКВ W (λ)')
        title = 'СКВ волновой аберрации по полю'
        if self.wl_label:
            title += f' — {self.wl_label}'
        ax.set_title(title, fontsize=9)
        ax.set_xlim(left=0.0)
        if pts:
            ax.set_ylim(bottom=0.0)
