"""Тест-объекты: симуляция изображения (п. 14 GAP v2).

Widgets:

* :class:`TestObjectWidget` — выбор тест-объекта (шпальная мира, край,
  точка, синусоидальная мишень) и его изображение через систему:
  слева идеал, справа свёртка с PSF (matplotlib imshow).
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton,
)

from optics_engine import OpticalSystem
from advanced_analysis import (
    TEST_OBJECT_KINDS, compute_test_object_image,
)
from optics_utils import get_primary_wl

from .mpl_widgets import MplCanvasWidget

# Диапазоны параметров объекта
FREQ_MIN_LP_MM = 0.5
FREQ_MAX_LP_MM = 500.0
DEFOCUS_MIN_MM = -10.0
DEFOCUS_MAX_MM = 10.0
DEFOCUS_STEP_MM = 0.01
PSF_GRID = 64  # та же сетка PSF, что в PSFWidget


class TestObjectWidget(MplCanvasWidget):
    """Изображение тест-объекта через оптическую систему.

    Параметры (вид объекта, частота, смещение плоскости) и кнопка
    «Симулировать изображение»; рендер — два imshow (идеал / image)
    на общей координатной сетке (мкм).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self._system = None

        bar = QHBoxLayout()
        bar.setContentsMargins(4, 1, 4, 1)
        bar.addWidget(QLabel("Объект:"))
        self.kind_combo = QComboBox()
        for key, label in TEST_OBJECT_KINDS:
            self.kind_combo.addItem(label, key)
        bar.addWidget(self.kind_combo)
        bar.addWidget(QLabel("Частота:"))
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(FREQ_MIN_LP_MM, FREQ_MAX_LP_MM)
        self.freq_spin.setDecimals(1)
        self.freq_spin.setSingleStep(1.0)
        self.freq_spin.setValue(10.0)
        self.freq_spin.setSuffix(" лин/мм")
        self.freq_spin.setToolTip("Частота первой группы миры / синусоиды")
        bar.addWidget(self.freq_spin)
        bar.addWidget(QLabel("Смещ. плоскости:"))
        self.defocus_spin = QDoubleSpinBox()
        self.defocus_spin.setRange(DEFOCUS_MIN_MM, DEFOCUS_MAX_MM)
        self.defocus_spin.setDecimals(3)
        self.defocus_spin.setSingleStep(DEFOCUS_STEP_MM)
        self.defocus_spin.setValue(0.0)
        self.defocus_spin.setSuffix(" мм")
        self.defocus_spin.setToolTip(
            "Смещение плоскости установки (дефокус) при симуляции")
        bar.addWidget(self.defocus_spin)
        self.sim_btn = QPushButton("Симулировать изображение")
        self.sim_btn.clicked.connect(self.simulate)
        bar.addWidget(self.sim_btn)
        bar.addStretch()
        # панель параметров — над toolbar'ом matplotlib
        self.layout().insertLayout(0, bar)

    # -- Public API -------------------------------------------------------

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0) -> None:
        """Запомнить систему и посчитать изображение текущего объекта.

        ``defocus_offset`` — глобальное смещение плоскости установки
        (спин «Смещение плоскости» панели анализа); 0 — Гаусс.
        """
        self._system = sys
        self.defocus_spin.setValue(defocus_offset)
        self.simulate()

    def simulate(self) -> None:
        """Пересчитать изображение с текущими параметрами (кнопка)."""
        if self._system is None:
            self.result = None
            self.redraw()
            return
        kind = self.kind_combo.currentData()
        try:
            self.result = compute_test_object_image(
                self._system, kind=kind, wl=get_primary_wl(self._system),
                defocus_mm=self.defocus_spin.value(),
                num_rays=PSF_GRID, freq_lp_mm=self.freq_spin.value())
        except Exception:
            self.result = None
        self.redraw()

    # -- Rendering --------------------------------------------------------

    def _render_no_data(self) -> None:
        """Заглушка «Нет данных» (до первого расчёта / ошибка)."""
        ax = self._figure.add_subplot(111)
        ax.set_facecolor('#0e0e18')
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                color='#b8b8cc', fontsize=12, transform=ax.transAxes)

    def _render(self) -> None:
        if self._render_pending():
            return
        if self.result is None:
            self._render_no_data()
            return

        res = self.result
        extent = [float(res['x'][0]), float(res['x'][-1]),
                  float(res['y'][0]), float(res['y'][-1])]
        kind_label = dict(TEST_OBJECT_KINDS).get(res['kind'], res['kind'])

        ax_ideal, ax_img = self._figure.subplots(1, 2)
        for ax, data, title in (
                (ax_ideal, res['ideal'], f'Идеал — {kind_label}'),
                (ax_img, res['image'], 'Изображение (свёртка с PSF)')):
            im = ax.imshow(data, origin='lower', extent=extent,
                           cmap='gray', aspect='equal')
            ax.set_title(title, fontsize=9)
            ax.set_xlabel('X, мкм')
            ax.set_ylabel('Y, мкм')
            self._style_axes(ax)
            ax.grid(False)
            cb = self._figure.colorbar(im, ax=ax, shrink=0.85)
            cb.ax.tick_params(labelsize=7)
