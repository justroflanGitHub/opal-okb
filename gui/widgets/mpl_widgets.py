"""Общие matplotlib-виджеты для вкладок анализа (тёмная тема).

Инфраструктура для графиков на matplotlib с панелью навигации
(зум/панорама/сохранение, для 3D — вращение). Используется:

* СКВ волновой аберрации по полю (:class:`~gui.widgets.wavefront.
  WfRmsFieldMplWidget`);
* фокусировочные диаграммы (п. 3 GAP v2);
* вращаемая 3D PSF (п. 5 GAP v2).

matplotlib импортируется лениво: без него приложение работает,
виджет показывает заглушку.
"""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

# Тёмная тема — в стиле остальных вкладок (QPainter на тёмном фоне)
MPL_BG_COLOR = '#0e0e18'      # фон фигуры
MPL_GRID_COLOR = '#3a3a52'    # сетка
MPL_TEXT_COLOR = '#b8b8cc'    # подписи осей
MPL_CURVE_COLOR = '#4a9eff'   # основная кривая
MPL_CURVE_COLORS = ('#4a9eff', '#5ce08c', '#ff5c5c', '#ffb84a', '#c07ff2')

MPL_MISSING_MSG = "matplotlib не установлен: pip install matplotlib"


class MplCanvasWidget(QWidget):
    """QWidget со встроенной matplotlib-фигурой и панелью навигации.

    Наследники переопределяют :meth:`_render` (построение графика по
    ``self.figure``) и вызывают :meth:`redraw` при изменении данных.
    Поддержан протокол ``_pending`` фазы расчёта: пока ``_pending`` —
    рисуется заглушка «⏳ Расчёт анализа...».
    """

    def __init__(self, parent=None, with_toolbar: bool = True,
                 facecolor: str = MPL_BG_COLOR):
        super().__init__(parent)
        self._pending = False
        self._mpl_ok = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        try:
            # Приложение на PyQt5 — фиксируем привязку matplotlib ДО
            # импорта бэкенда (иначе qt_compat может выбрать PySide6).
            os.environ.setdefault('QT_API', 'PyQt5')
            import matplotlib
            matplotlib.use('Qt5Agg')
            from matplotlib.backends.backend_qt5agg import (
                FigureCanvasQTAgg, NavigationToolbar2QT)
            from matplotlib.figure import Figure

            self._figure = Figure(facecolor=facecolor)
            self._canvas = FigureCanvasQTAgg(self._figure)
            if with_toolbar:
                toolbar = NavigationToolbar2QT(self._canvas, self)
                toolbar.setStyleSheet(
                    "QToolBar { background: #14141f; }"
                    "QToolButton { color: #b8b8cc; }")
                layout.addWidget(toolbar)
            layout.addWidget(self._canvas)
            self._mpl_ok = True
        except ImportError:
            placeholder = QLabel(MPL_MISSING_MSG)
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #b8b8cc;")
            layout.addWidget(placeholder)

    # -- Public API -------------------------------------------------------

    @property
    def figure(self):
        """matplotlib Figure или None, если matplotlib недоступен."""
        return self._figure if self._mpl_ok else None

    def redraw(self) -> None:
        """Перестроить фигуру: очистить и вызвать ``_render``."""
        if not self._mpl_ok:
            return
        self._figure.clear()
        self._render()
        self._canvas.draw_idle()

    def update(self) -> None:
        """Qt-update + перерисовка фигуры (например, при смене _pending)."""
        super().update()
        self.redraw()

    # -- Hooks ------------------------------------------------------------

    def _render(self) -> None:
        """Отрисовать график на ``self.figure``. Переопределяется."""
        raise NotImplementedError

    def _style_axes(self, ax) -> None:
        """Тёмная тема для осей (общая для всех matplotlib-графиков)."""
        ax.set_facecolor(MPL_BG_COLOR)
        ax.grid(True, color=MPL_GRID_COLOR, linewidth=0.6, alpha=0.8)
        ax.tick_params(colors=MPL_TEXT_COLOR, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(MPL_GRID_COLOR)
        ax.xaxis.label.set_color(MPL_TEXT_COLOR)
        ax.yaxis.label.set_color(MPL_TEXT_COLOR)
        ax.title.set_color(MPL_TEXT_COLOR)

    def _render_pending(self) -> bool:
        """Заглушка «⏳ Расчёт...», пока идёт фаза 2.

        Returns:
            True, если нарисована заглушка (рендер данных не нужен).
        """
        if not self._pending:
            return False
        ax = self._figure.add_subplot(111)
        self._style_axes(ax)
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.5, 0.5, '⏳ Расчёт анализа...', ha='center', va='center',
                color=MPL_TEXT_COLOR, fontsize=12, transform=ax.transAxes)
        return True
