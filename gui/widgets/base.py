"""Shared base classes, mixins, and helper utilities for analysis widgets.

This module provides:

* :class:`InteractivePlot` — mouse-tracking / zoom / pan mixin.
* :class:`AberrationPlotWidget` — concrete base widget with grid rendering.
* :func:`make_table` — factory for styled ``QTableWidget`` instances.
* :func:`clear_layout` — recursively clear a ``QLayout``.
* :func:`wl_to_plot_color` — map a wavelength (µm) to a display colour.

All widget modules in :mod:`gui.widgets` import from here.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QAction,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QTransform,
)

from optics_utils import copy_table_selection


# ---------------------------------------------------------------------------
#  Table helpers
# ---------------------------------------------------------------------------

def make_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    col_widths: Optional[Sequence[int]] = None,
) -> QTableWidget:
    """Create a styled ``QTableWidget`` with copy support.

    Args:
        headers: Column header labels.
        rows: Iterable of row value lists.
        col_widths: Optional explicit column widths in pixels.

    Returns:
        A configured, read-only ``QTableWidget``.
    """
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setRowCount(len(rows))
    table.setHorizontalHeaderLabels(list(headers))
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    table.setFocusPolicy(Qt.StrongFocus)
    table.verticalHeader().setVisible(False)
    table.setFont(QFont("Courier", 9))

    header_font = QFont("Courier", 9)
    header_font.setBold(True)
    table.horizontalHeader().setFont(header_font)

    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if i % 2 == 1:
                item.setBackground(QColor(240, 240, 245))
            table.setItem(i, j, item)

    if col_widths:
        for j, w in enumerate(col_widths):
            table.setColumnWidth(j, w)
    else:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    # Context-menu copy action
    table.setContextMenuPolicy(Qt.ActionsContextMenu)
    copy_action = QAction("Копировать (Ctrl+C)", table)
    copy_action.setShortcut("Ctrl+C")
    copy_action.triggered.connect(lambda checked=False, t=table: copy_table_selection(t))
    table.addAction(copy_action)

    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.setSizePolicy(table.sizePolicy().Expanding, table.sizePolicy().Expanding)
    return table


def clear_layout(layout) -> None:
    """Recursively remove all items from a ``QLayout``."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        sub = item.layout()
        if sub:
            clear_layout(sub)


# ---------------------------------------------------------------------------
#  Wavelength → colour mapping
# ---------------------------------------------------------------------------

_WL_PLOT_COLORS = [
    (0.405, QColor(148, 0, 211)),    # h
    (0.436, QColor(100, 0, 255)),    # g
    (0.486, QColor(0, 80, 255)),     # F — blue
    (0.546, QColor(220, 200, 0)),    # e
    (0.588, QColor(0, 200, 80)),     # d — green
    (0.656, QColor(255, 60, 60)),    # C — red
    (0.707, QColor(200, 0, 0)),      # r
]


def wl_to_plot_color(wl_um: float) -> QColor:
    """Return the display colour for the nearest standard spectral line.

    Args:
        wl_um: Wavelength in micrometres.

    Returns:
        Matching ``QColor``.
    """
    best = min(_WL_PLOT_COLORS, key=lambda item: abs(item[0] - wl_um))
    return best[1]


# ---------------------------------------------------------------------------
#  InteractivePlot mixin
# ---------------------------------------------------------------------------

class InteractivePlot:
    """Mixin providing crosshair, zoom, and pan functionality for plot widgets.

    Call :meth:`_init_interactive` in ``__init__`` after ``super().__init__()``.
    """

    def _init_interactive(self) -> None:
        """Initialise interactive state. Call after ``super().__init__()``."""
        self.setMouseTracking(True)
        self._mouse_pos: Optional[QPoint] = None
        self._x_range = (0, 1)
        self._y_range = (0, 1)
        self._plot_rect = QRectF(50, 20, 500, 300)
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self._dragging = False
        self._drag_start: Optional[QPoint] = None
        self._drag_start_offset = QPointF(0, 0)
        self._inverse_transform = QTransform()

    def set_ranges(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        """Set data-coordinate ranges used for crosshair readout."""
        self._x_range = (x_min, x_max)
        self._y_range = (y_min, y_max)

    def pixel_to_data(self, px: float, py: float) -> tuple[float, float]:
        """Convert pixel coordinates to data coordinates (accounting for zoom/pan)."""
        r = self._plot_rect
        rcx = r.center().x()
        rcy = r.center().y()
        unzoomed_x = (px - self._pan_offset.x() - rcx) / self._zoom_factor + rcx
        unzoomed_y = (py - self._pan_offset.y() - rcy) / self._zoom_factor + rcy
        x = self._x_range[0] + (unzoomed_x - r.left()) / r.width() * (self._x_range[1] - self._x_range[0])
        y = self._y_range[1] - (unzoomed_y - r.top()) / r.height() * (self._y_range[1] - self._y_range[0])
        return x, y

    # -- mouse event handlers (call from subclass overrides) --

    def _interactive_mouseMoveEvent(self, event) -> None:
        if self._dragging and self._drag_start:
            dx = event.pos().x() - self._drag_start.x()
            dy = event.pos().y() - self._drag_start.y()
            self._pan_offset = QPointF(
                self._drag_start_offset.x() + dx,
                self._drag_start_offset.y() + dy,
            )
        self._mouse_pos = event.pos()
        self.update()

    def _interactive_leaveEvent(self, event) -> None:
        self._mouse_pos = None
        self.update()

    def _interactive_wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        self._zoom_factor *= factor
        self._zoom_factor = max(0.1, min(self._zoom_factor, 100.0))
        self.update()

    def _interactive_mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            self._dragging = True
            self._drag_start = event.pos()
            self._drag_start_offset = QPointF(self._pan_offset)
            self.setCursor(Qt.ClosedHandCursor)

    def _interactive_mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)

    def _interactive_mouseDoubleClickEvent(self, event) -> None:
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self.update()

    # -- painting helpers --

    def draw_crosshair(self, painter: QPainter, rect: QRectF) -> None:
        """Draw crosshair lines and a coordinate label at the mouse position."""
        if self._mouse_pos is None:
            return
        mx, my = self._mouse_pos.x(), self._mouse_pos.y()
        if not rect.contains(QPoint(mx, my)):
            return

        pen = QPen(QColor(255, 255, 255, 128), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(int(mx), int(rect.top()), int(mx), int(rect.bottom()))
        painter.drawLine(int(rect.left()), int(my), int(rect.right()), int(my))

        data_x, data_y = self.pixel_to_data(mx, my)
        label = f"X: {data_x:.4g}  Y: {data_y:.4g}"

        font = QFont("Courier", 9)
        painter.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(label) + 8
        th = fm.height() + 4

        tx = mx + 15
        ty = my - 15
        if tx + tw > self.width():
            tx = mx - tw - 5
        if ty < 0:
            ty = my + 20

        painter.fillRect(int(tx), int(ty), int(tw), int(th), QColor(0, 0, 0, 200))
        painter.setPen(QColor(255, 255, 0))
        painter.drawText(int(tx + 4), int(ty + th - 4), label)

    def paint_finalize(self, painter: QPainter, rect: QRectF) -> None:
        """Restore painter from zoom and draw crosshair / pending overlay."""
        painter.restore()
        if getattr(self, '_pending', False):
            painter.fillRect(self.rect(), QColor(10, 10, 25))
            painter.setPen(QColor(200, 180, 80))
            painter.setFont(QFont("Consolas", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "⏳ Расчёт анализа...")
            return
        self.draw_crosshair(painter, rect)

    def apply_zoom_pan(self, painter: QPainter, rect: QRectF) -> None:
        """Apply current zoom/pan to *painter*.

        Saves painter state so :meth:`paint_finalize` can restore it.
        """
        painter.save()
        if self._zoom_factor != 1.0 or self._pan_offset.x() != 0 or self._pan_offset.y() != 0:
            painter.translate(self._pan_offset.x(), self._pan_offset.y())
            cx = rect.center().x()
            cy = rect.center().y()
            painter.translate(cx, cy)
            painter.scale(self._zoom_factor, self._zoom_factor)
            painter.translate(-cx, -cy)
        self._painter_transform = painter.transform()
        inv, ok = self._painter_transform.inverted()
        self._inverse_transform = inv if ok else QTransform()


# ---------------------------------------------------------------------------
#  AberrationPlotWidget
# ---------------------------------------------------------------------------

class AberrationPlotWidget(QWidget, InteractivePlot):
    """Base widget for custom-painted analysis graphs.

    Provides grid rendering, zoom/pan/crosshair via :class:`InteractivePlot`,
    and a ``_pending`` flag for deferred-computation feedback.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 200)
        self.data = None
        self._pending = False
        self._init_interactive()

    # Delegate Qt events to InteractivePlot handlers
    def mouseMoveEvent(self, event):
        self._interactive_mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._interactive_leaveEvent(event)

    def wheelEvent(self, event):
        self._interactive_wheelEvent(event)

    def mousePressEvent(self, event):
        self._interactive_mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._interactive_mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._interactive_mouseDoubleClickEvent(event)

    def paint_grid(self, painter: QPainter, w: int, h: int, margin: int = 40) -> tuple[int, int, int, int]:
        """Paint the standard dark-background coordinate grid.

        Returns:
            ``(margin, top, plot_width, plot_height)`` for the drawable area.
        """
        painter.fillRect(self.rect(), QColor(10, 10, 25))

        painter.setPen(QPen(QColor(60, 60, 80), 1))
        rect_top = 10
        pw = w - margin - 10
        ph = h - margin - 10
        painter.drawRect(margin, rect_top, pw, ph)

        self._plot_rect = QRectF(margin, rect_top, pw, ph)
        self.apply_zoom_pan(painter, self._plot_rect)
        return margin, rect_top, pw, ph
