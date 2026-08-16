"""Общие matplotlib-виджеты для вкладок анализа (тёмная тема).

Инфраструктура для графиков на matplotlib с панелью навигации
(зум/панорама/сохранение, для 3D — вращение). Используется:

* СКВ волновой аберрации по полю (:class:`~gui.widgets.wavefront.
  WfRmsFieldMplWidget`);
* фокусировочные диаграммы (п. 3 GAP v2);
* вращаемые 3D-поверхности (:class:`MplSurface3DWidget`) — PSF 3D
  (п. 5 GAP v2) и волновой фронт 3D (п. 10 GAP v2).

matplotlib импортируется лениво: без него приложение работает,
виджет показывает заглушку.
"""

from __future__ import annotations

import os

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

# Тёмная тема — в стиле остальных вкладок (QPainter на тёмном фоне)
MPL_BG_COLOR = '#0e0e18'      # фон фигуры
MPL_GRID_COLOR = '#3a3a52'    # сетка
MPL_TEXT_COLOR = '#b8b8cc'    # подписи осей
MPL_CURVE_COLOR = '#4a9eff'   # основная кривая
MPL_CURVE_COLORS = ('#4a9eff', '#5ce08c', '#ff5c5c', '#ffb84a', '#c07ff2')

# 3D-поверхности: стартовая ориентация камеры (высота/азимут, градусы)
# и максимум сегментов сетки по каждой оси (быстрый рендер)
MPL_3D_ELEV = 28
MPL_3D_AZIM = -60
MPL_3D_MAX_RES = 64

MPL_MISSING_MSG = "matplotlib не установлен: pip install matplotlib"


def style_3d_axes(ax) -> None:
    """Тёмная тема для 3D-осей: панели, сетка, подписи, тики.

    Единственная реализация для всех 3D-графиков (PSF 3D, волновой
    фронт 3D); приватное API сетки mplot3d не критично.
    """
    import matplotlib.colors

    pane = matplotlib.colors.to_rgba(MPL_BG_COLOR)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        try:
            axis.set_pane_color(pane)
            axis._axinfo['grid'].update(color=MPL_GRID_COLOR,
                                        linewidth=0.6)
        except (AttributeError, KeyError):
            pass  # приватное API сетки — не критично
        axis.label.set_color(MPL_TEXT_COLOR)
        for tick in axis.get_ticklabels():
            tick.set_color(MPL_TEXT_COLOR)
    ax.set_facecolor(MPL_BG_COLOR)
    ax.title.set_color(MPL_TEXT_COLOR)


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


class MplSurface3DWidget(MplCanvasWidget):
    """Вращаемая 3D-поверхность — общий базовый класс (matplotlib
    ``plot_surface`` с панелью навигации: вращение мышью, зум).

    Наследники — PSF 3D (п. 5 GAP v2) и волновой фронт 3D (п. 10
    GAP v2); они задают карту цветов, подписи и данные через хуки.
    Заглушки «⏳ Расчёт» / «Нет данных», прореживание сетки, тёмная
    тема и colorbar — общие.
    """

    #: цветовая карта поверхности
    SURF_CMAP = 'viridis'
    #: стартовая ориентация камеры и предел сетки (:data:`MPL_3D_*`)
    SURF_ELEV = MPL_3D_ELEV
    SURF_AZIM = MPL_3D_AZIM
    SURF_MAX_RES = MPL_3D_MAX_RES

    # -- Rendering --------------------------------------------------------

    def _render(self) -> None:
        # Регистрирует проекцию '3d' (для старых matplotlib)
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

        if self._render_pending():
            return
        data = self._surface_data()
        if data is None:
            self._render_no_data()
            return

        x, y, Z = data[0], data[1], data[2]
        mask = data[3] if len(data) > 3 else None
        step = max(1, max(Z.shape) // self.SURF_MAX_RES)
        X, Y = np.meshgrid(x[::step], y[::step])
        Zs = Z[::step, ::step]
        if mask is not None:
            # вне зрачка поверхность не рисуется
            Zs = np.ma.masked_array(Zs, mask[::step, ::step] < 0.5)

        ax = self._figure.add_subplot(projection='3d')
        style_3d_axes(ax)
        surf = ax.plot_surface(X, Y, Zs, cmap=self.SURF_CMAP,
                               linewidth=0, antialiased=True)
        ax.view_init(elev=self.SURF_ELEV, azim=self.SURF_AZIM)
        xlabel, ylabel, zlabel = self._axis_labels()
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_zlabel(zlabel)
        ax.set_title(self._title())

        cb = self._figure.colorbar(surf, ax=ax, shrink=0.55, pad=0.08)
        cb.ax.tick_params(colors=MPL_TEXT_COLOR, labelsize=8)
        cb.set_label(self._cbar_label(), color=MPL_TEXT_COLOR, fontsize=8)

    def _render_no_data(self) -> None:
        """Заглушка «Нет данных» до первого расчёта."""
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(MPL_BG_COLOR)
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                color=MPL_TEXT_COLOR, fontsize=12, transform=ax.transAxes)

    # -- Hooks ------------------------------------------------------------

    def _surface_data(self):
        """Данные поверхности: ``(x, y, Z)`` или ``(x, y, Z, mask)``
        (mask ≥ 0.5 — точка внутри зрачка); ``None`` — нет данных.
        Переопределяется.
        """
        raise NotImplementedError

    def _axis_labels(self) -> tuple:
        """Подписи ``(xlabel, ylabel, zlabel)``. Переопределяется."""
        raise NotImplementedError

    def _title(self) -> str:
        """Заголовок графика. Переопределяется."""
        raise NotImplementedError

    def _cbar_label(self) -> str:
        """Подпись шкалы colorbar. Переопределяется."""
        raise NotImplementedError
