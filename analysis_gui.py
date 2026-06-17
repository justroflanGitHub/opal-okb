"""
OPAL-OKB — Панель аберраций и графиков для GUI
Виджеты: точечная диаграмма, графики аберраций, ЧКХ
"""
import math
from PyQt5.QtWidgets import (QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QGroupBox, QFormLayout, QSplitter,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QAbstractItemView, QDoubleSpinBox, QComboBox,
                              QGridLayout, QSizePolicy, QPushButton, QAction,
                              QStackedWidget, QApplication)
from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                          QPainterPath, QLinearGradient, QFontMetrics,
                          QTransform)

import numpy as np
from optics_engine import OpticalSystem, Wavelength, paraxial_trace, seidel_aberrations, compute_beam_geometry
from aberrations import (trace_aberration_fan, compute_spot_diagram,
                          compute_spot_diagram_polychromatic, compute_polychromatic_rms,
                          compute_rms_spot, compute_rms_spot_xy, compute_geometric_mtf,
                          compute_field_aberrations, compute_focus_curve,
                          compute_spot_heatmap,
                          compute_spot_diagram_at_defocus,
                          compute_chief_ray_characteristics,
                          compute_isoplanatism, compute_wavefront_rms_vs_field,
                          compute_oblique_fan, compute_ray_coordinates)
from advanced_analysis import compute_psf, compute_lsf, compute_enc, compute_ptf, compute_esf, compute_psf_3d, compute_bar_target_image, compute_bar_target_mtf_table
from zernike import compute_zernike_coefficients, compute_wavefront_map_2d, compute_zernike_chromatic


def _copy_table_selection(table):
    """Копирует выделенные ячейки таблицы в буфер обмена (tab-separated)."""
    selection = table.selectedRanges()
    if not selection:
        return
    lines = []
    for rng in selection:
        for row in range(rng.topRow(), rng.bottomRow() + 1):
            cells = []
            for col in range(rng.leftColumn(), rng.rightColumn() + 1):
                item = table.item(row, col)
                cells.append(item.text() if item else "")
            lines.append("\t".join(cells))
    text = "\n".join(lines)
    QApplication.clipboard().setText(text)


def compute_all_analysis(sys, defocus=0.0, azimuth=0.0):
    """Compute all analysis data. Thread-safe (no GUI operations).
    Returns dict with all precomputed results for widgets and tables.
    """
    import traceback as _tb
    d = {}
    wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
    wl_list = [w.value for w in sys.wavelengths] if sys.wavelengths else [0.58756]
    d['wl'] = wl
    d['wl_list'] = wl_list

    def _safe(key, fn, *args, **kwargs):
        try:
            d[key] = fn(*args, **kwargs)
        except Exception:
            pass

    # Spot diagram
    _safe('spot_mono', compute_spot_diagram, sys, wl=wl, num_rays=40, field_y=0.0)
    if 'spot_mono' not in d:
        d['spot_mono'] = []
    _safe('spot_rms', compute_rms_spot, d['spot_mono'])
    _safe('spot_rms_xy', compute_rms_spot_xy, d['spot_mono'])
    d.setdefault('spot_rms', 0)
    d.setdefault('spot_rms_xy', {'rms_x': 0, 'rms_y': 0, 'rms_total': 0, 'centroid_x': 0, 'centroid_y': 0})

    if len(wl_list) > 1:
        _safe('spot_poly', compute_spot_diagram_polychromatic, sys, num_rays=40, field_y=0.0)
        _safe('poly_rms', compute_polychromatic_rms, sys, num_rays=40, field_y=0.0)
        d.setdefault('spot_poly', [])
        d.setdefault('poly_rms', 0)
        if d.get('spot_poly'):
            _safe('poly_rms_xy', compute_rms_spot_xy, [(dx, dy) for dx, dy, _ in d['spot_poly']])
        d.setdefault('poly_rms_xy', {'rms_x': 0, 'rms_y': 0, 'rms_total': 0, 'centroid_x': 0, 'centroid_y': 0})
    else:
        d['spot_poly'] = [(dx, dy, 0) for dx, dy in d['spot_mono']]
        d['poly_rms'] = d.get('spot_rms', 0)
        d['poly_rms_xy'] = d.get('spot_rms_xy', {})

    # Aberration fans
    d['fan_data'] = {}
    d['isoplanatism_data'] = {}
    d['oblique_data'] = None

    if abs(azimuth) > 0.1:
        _safe('oblique_data', compute_oblique_fan, sys, wl=wl, num_rays=20,
              field_y=0.0, azimuth_deg=azimuth)
    else:
        wavelengths = sys.wavelengths if sys.wavelengths else [Wavelength(0.58756)]
        for wl_obj in wavelengths:
            _safe_fan = trace_aberration_fan(sys, wl_obj.value, num_rays=30)
            d['fan_data'][wl_obj.value] = _safe_fan if _safe_fan else []
            try:
                d['isoplanatism_data'][wl_obj.value] = compute_isoplanatism(
                    sys, wl=wl_obj.value, num_rays=30)
            except Exception:
                d['isoplanatism_data'][wl_obj.value] = ([], [])

    # MTF
    _safe('geo_mtf', compute_geometric_mtf, d['spot_mono'], max_freq=100, num_freqs=20)
    d['diff_mtf'] = None
    d['diff_limited_mtf'] = None
    d['poly_mtf'] = None
    try:
        from diffraction_mtf import compute_diffraction_mtf_quick
        d['diff_mtf'] = compute_diffraction_mtf_quick(sys, wl=wl)
    except Exception:
        pass
    try:
        from diffraction_mtf import compute_diffraction_limited_mtf
        d['diff_limited_mtf'] = compute_diffraction_limited_mtf(sys, wl=wl)
    except Exception:
        pass
    if len(wl_list) > 1:
        try:
            from diffraction_mtf import compute_polychromatic_mtf
            d['poly_mtf'] = compute_polychromatic_mtf(sys, grid_size=32)
        except Exception:
            pass

    # Field aberrations
    _safe('field_data', compute_field_aberrations, sys, wl=wl)
    d.setdefault('field_data', [])

    # Focus curve
    _safe('focus_curve', compute_focus_curve, sys, wl=wl, num_points=40,
          defocus_range=2.0, freq_lpmm=50.0, num_rays=25, field_y=0.0)

    # PSF
    d['psf_data'] = None; d['psf_dx'] = None; d['psf_dy'] = None
    try:
        d['psf_data'], d['psf_dx'], d['psf_dy'] = compute_psf(sys, wl=wl, num_rays=64)
    except Exception:
        pass

    # LSF
    d['lsf_tan'] = None; d['lsf_sag'] = None; d['lsf_ax'] = None
    try:
        d['lsf_tan'], d['lsf_ax'] = compute_lsf(sys, wl=wl, num_rays=64, direction='tangential')
        d['lsf_sag'], _ = compute_lsf(sys, wl=wl, num_rays=64, direction='sagittal')
    except Exception:
        pass

    # ESF
    d['esf_x'] = None; d['esf_y'] = None
    try:
        d['esf_x'], d['esf_y'] = compute_esf(sys, wl=wl, field_y=0.0)
    except Exception:
        pass

    # ENC
    d['enc_r'] = None; d['enc_e'] = None
    try:
        d['enc_r'], d['enc_e'] = compute_enc(sys, wl=wl, num_rays=100)
    except Exception:
        pass

    # PTF
    d['ptf_data'] = None
    try:
        d['ptf_data'] = compute_ptf(sys, wl=wl, num_rays=64)
    except Exception:
        pass

    # Heatmap
    d['heatmap'] = None
    d['heatmap_x_range'] = (0, 0); d['heatmap_y_range'] = (0, 0)
    d['heatmap_centroid_x'] = 0; d['heatmap_centroid_y'] = 0
    d['heatmap_max_density'] = 0; d['heatmap_num_points'] = 0
    try:
        hm, xr, yr = compute_spot_heatmap(sys, wl=wl, num_rays=500, field_y=0.0, grid_size=100)
        d['heatmap'] = hm; d['heatmap_x_range'] = xr; d['heatmap_y_range'] = yr
        if hm is not None and hm.size > 0:
            gs = 100
            total = hm.sum()
            if total > 0:
                ys = np.linspace(yr[0], yr[1], gs)
                xs = np.linspace(xr[0], xr[1], gs)
                yy, xx = np.meshgrid(ys, xs, indexing='ij')
                d['heatmap_centroid_x'] = float(np.sum(xx * hm) / total)
                d['heatmap_centroid_y'] = float(np.sum(yy * hm) / total)
            d['heatmap_max_density'] = float(hm.max())
            d['heatmap_num_points'] = int(np.sum(hm > 0))
    except Exception:
        pass

    # Beam geometry
    _safe('beam_data', compute_beam_geometry, sys)
    d.setdefault('beam_data', [])

    # Chief ray
    _safe('chief_data', compute_chief_ray_characteristics, sys)
    d.setdefault('chief_data', [])

    # Zernike
    d['zernike_coeffs'] = []
    d['zernike_chromatic'] = None
    try:
        d['zernike_coeffs'] = compute_zernike_coefficients(
            sys, wl=wl, num_rays=32, max_order=4, defocus_offset=defocus)
    except Exception:
        pass
    if len(wl_list) > 1:
        try:
            d['zernike_chromatic'] = compute_zernike_chromatic(sys, num_rays=32, max_order=4)
        except Exception:
            pass

    # Wavefront map
    d['wf_data'] = None; d['wf_coords'] = None; d['wf_mask'] = None
    try:
        d['wf_data'], d['wf_coords'], d['wf_mask'] = compute_wavefront_map_2d(
            sys, wl=wl, grid_size=48, defocus_offset=defocus)
    except Exception:
        pass

    # WF RMS vs field
    d['wf_rms_field'] = None
    try:
        d['wf_rms_field'] = compute_wavefront_rms_vs_field(sys, wl=wl)
    except Exception:
        pass

    # Focus diagrams
    d['focus_diag_data'] = {}
    d['focus_diag_max_range'] = 0.001
    try:
        parax = paraxial_trace(sys)
        bfd = parax.get('back_focal_distance', 0)
        if abs(bfd) < 1e-6:
            efl = parax.get('focal_length', 50)
            bfd = abs(efl) * 0.5
        ds = abs(bfd) * 0.01
        all_spots = []
        for label, df in [("\u043d\u043e\u043c\u0438\u043d\u0430\u043b", 0.0),
                          ("+DS'", +ds), ("-DS'", -ds),
                          ("+2DS'", +2*ds), ("-2DS'", -2*ds)]:
            spots = compute_spot_diagram_at_defocus(
                sys, wl=wl, num_rays=60, field_y=0.0, defocus_mm=df)
            rms_info = compute_rms_spot_xy(spots)
            d['focus_diag_data'][label] = (spots, rms_info, df)
            all_spots.extend(spots)
        if all_spots:
            d['focus_diag_max_range'] = max(
                math.sqrt(dx**2 + dy**2) for dx, dy in all_spots)
            d['focus_diag_max_range'] = max(d['focus_diag_max_range'], 1e-6)
    except Exception:
        pass

    # PSF 3D
    d['psf3d_x'] = None; d['psf3d_y'] = None; d['psf3d_Z'] = None
    try:
        d['psf3d_x'], d['psf3d_y'], d['psf3d_Z'] = compute_psf_3d(
            sys, wl=wl, grid_size=64, field_y=0.0)
    except Exception:
        pass

    # Bar target
    d['bar_x'] = None; d['bar_ideal'] = None; d['bar_blurred'] = None
    d['bar_mtf_table'] = None
    try:
        d['bar_x'], d['bar_ideal'], d['bar_blurred'] = compute_bar_target_image(
            sys, wl=wl, field_y=0.0, num_bars=5, bar_freq_lp_mm=10)
        d['bar_mtf_table'] = compute_bar_target_mtf_table(
            sys, wl=wl, field_y=0.0, num_bars=5)
    except Exception:
        pass

    return d


def _make_table(headers, rows, col_widths=None):
    """Создаёт стилизованную QTableWidget с поддержкой копирования.
    
    Args:
        headers: список заголовков
        rows: список списков значений (строки)
        col_widths: список ширин колонок (опционально)
    Returns:
        QTableWidget
    """
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setRowCount(len(rows))
    table.setHorizontalHeaderLabels(headers)
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
            # Чередуем цвета
            if i % 2 == 1:
                item.setBackground(QColor(240, 240, 245))
            table.setItem(i, j, item)
    
    # Ширина колонок
    if col_widths:
        for j, w in enumerate(col_widths):
            table.setColumnWidth(j, w)
    else:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    # Контекстное меню для копирования
    table.setContextMenuPolicy(Qt.ActionsContextMenu)
    copy_action = QAction("Копировать (Ctrl+C)", table)
    copy_action.setShortcut("Ctrl+C")
    copy_action.triggered.connect(lambda checked=False, t=table: _copy_table_selection(t))
    table.addAction(copy_action)

    # No fixed width constraints — let table expand to fill available space
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.setSizePolicy(table.sizePolicy().Expanding, table.sizePolicy().Expanding)
    
    return table


def _clear_layout(layout):
    """Удаляет все элементы из layout."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        sub = item.layout()
        if sub:
            _clear_layout(sub)


class InteractivePlot:
    """Mixin для виджетов графиков: перекрёстие, зум, панорамирование."""

    def _init_interactive(self):
        """Вызвать в __init__ после super().__init__()."""
        self.setMouseTracking(True)
        self._mouse_pos = None
        self._x_range = (0, 1)
        self._y_range = (0, 1)
        self._plot_rect = QRectF(50, 20, 500, 300)
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self._dragging = False
        self._drag_start = None
        self._drag_start_offset = None
        self._inverse_transform = QTransform()

    def set_ranges(self, x_min, x_max, y_min, y_max):
        self._x_range = (x_min, x_max)
        self._y_range = (y_min, y_max)

    def pixel_to_data(self, px, py):
        """Convert pixel coords to data coords, accounting for zoom/pan."""
        r = self._plot_rect
        # Forward transform: data_pixel → screen_pixel = (dp - cx) * z + cx
        # where cx = r.center.x - pan.x, cy = r.center.y - pan.y  (note: pan is negated)
        cx = r.center().x() - self._pan_offset.x()
        cy = r.center().y() - self._pan_offset.y()
        # Inverse: data_pixel = (screen_pixel - cx) / z + cx
        unzoomed_x = (px - cx) / self._zoom_factor + cx
        unzoomed_y = (py - cy) / self._zoom_factor + cy
        # Now convert from unzoomed plot rect to data coords
        x = self._x_range[0] + (unzoomed_x - r.left()) / r.width() * (self._x_range[1] - self._x_range[0])
        y = self._y_range[1] - (unzoomed_y - r.top()) / r.height() * (self._y_range[1] - self._y_range[0])
        return x, y

    def _interactive_mouseMoveEvent(self, event):
        """Pan by drag — drag right = content moves right."""
        if self._dragging and self._drag_start:
            dx = event.pos().x() - self._drag_start.x()
            dy = event.pos().y() - self._drag_start.y()
            self._pan_offset = QPointF(
                self._drag_start_offset.x() + dx,
                self._drag_start_offset.y() + dy
            )
        self._mouse_pos = event.pos()
        self.update()

    def _interactive_leaveEvent(self, event):
        self._mouse_pos = None
        self.update()

    def _interactive_wheelEvent(self, event):
        """Zoom with mouse wheel."""
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        self._zoom_factor *= factor
        self._zoom_factor = max(0.1, min(self._zoom_factor, 100.0))
        self.update()

    def _interactive_mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            self._dragging = True
            self._drag_start = event.pos()
            self._drag_start_offset = QPointF(self._pan_offset)
            self.setCursor(Qt.ClosedHandCursor)

    def _interactive_mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)

    def _interactive_mouseDoubleClickEvent(self, event):
        """Reset zoom/pan."""
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self.update()

    def draw_crosshair(self, painter, rect):
        """Draw crosshair + coordinate label at mouse position."""
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

    def paint_finalize(self, painter, rect):
        """Restore painter from zoom, then draw crosshair in screen coords."""
        painter.restore()  # Undo zoom/pan so crosshair/text are not scaled
        self.draw_crosshair(painter, rect)

    def apply_zoom_pan(self, painter, rect):
        """Apply zoom/pan to painter. Saves state so paint_finalize can restore."""
        painter.save()  # Save un-zoomed state
        if self._zoom_factor != 1.0 or self._pan_offset.x() != 0 or self._pan_offset.y() != 0:
            cx = rect.center().x() + self._pan_offset.x()
            cy = rect.center().y() + self._pan_offset.y()
            painter.translate(cx, cy)
            painter.scale(self._zoom_factor, self._zoom_factor)
            painter.translate(-cx, -cy)
        # Save the transform for pixel_to_data inversion
        self._painter_transform = painter.transform()
        inv, ok = self._painter_transform.inverted()
        self._inverse_transform = inv if ok else QTransform()


class AberrationPlotWidget(QWidget, InteractivePlot):
    """Базовый виджет для рисования графиков."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 200)
        self.data = None
        self._init_interactive()

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
    
    def paint_grid(self, painter, w, h, margin=40):
        """Рисует координатную сетку. Возвращает (m, top, pw, ph)."""
        # Фон
        painter.fillRect(self.rect(), QColor(10, 10, 25))
        
        # Рамка
        painter.setPen(QPen(QColor(60, 60, 80), 1))
        rect_top = 10
        pw = w - margin - 10
        ph = h - margin - 10
        painter.drawRect(margin, rect_top, pw, ph)

        # Сохраняем область графика для перекрестья
        self._plot_rect = QRectF(margin, rect_top, pw, ph)

        # Применяем зум/пан
        self.apply_zoom_pan(painter, self._plot_rect)
        
        return margin, rect_top, pw, ph


# Цвета для стандартных спектральных линий
_WL_PLOT_COLORS = [
    (0.405, QColor(148, 0, 211)),    # h
    (0.436, QColor(100, 0, 255)),    # g
    (0.486, QColor(0, 80, 255)),     # F — синий
    (0.546, QColor(220, 200, 0)),    # e
    (0.588, QColor(0, 200, 80)),     # d — зелёный
    (0.656, QColor(255, 60, 60)),    # C — красный
    (0.707, QColor(200, 0, 0)),      # r
]


def _wl_to_plot_color(wl_um: float) -> QColor:
    """Цвет точки по длине волны."""
    best = min(_WL_PLOT_COLORS, key=lambda item: abs(item[0] - wl_um))
    return best[1]


class SpotDiagramWidget(AberrationPlotWidget):
    """Точечная диаграмма (Л1.6.1), полихроматическая."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spots_mono = []       # [(dx, dy), ...]
        self.spots_poly = []       # [(dx, dy, wl_idx), ...]
        self.rms = 0.0
        self.poly_rms = 0.0
        self.polychromatic = True
    
    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        self.spots_mono = compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=0.0)
        self.rms = compute_rms_spot(self.spots_mono)
        self._wl_cache = [w.value for w in sys.wavelengths]
        if len(sys.wavelengths) > 1:
            self.spots_poly = compute_spot_diagram_polychromatic(sys, num_rays=40, field_y=0.0)
            self.poly_rms = compute_polychromatic_rms(sys, num_rays=40, field_y=0.0)
        else:
            self.spots_poly = [(dx, dy, 0) for dx, dy in self.spots_mono]
            self.poly_rms = self.rms
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)
        
        spots = self.spots_poly if (self.polychromatic and self.spots_poly) else \
                [(dx, dy, 0) for dx, dy in self.spots_mono] if self.spots_mono else []
        
        if not spots:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return
        
        # Масштаб
        max_r = max(math.sqrt(dx**2 + dy**2) for dx, dy, _ in spots) if spots else 1
        max_r = max(max_r, 0.001)
        scale = min(pw, ph) / (2.2 * max_r)
        cx = m + pw / 2
        cy = top + ph / 2
        
        # Круги Airy (дифракционный предел)
        painter.setPen(QPen(QColor(40, 80, 40), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        for r_mm in [max_r * 0.25, max_r * 0.5, max_r * 0.75, max_r]:
            r_px = r_mm * scale
            painter.drawEllipse(int(cx - r_px), int(cy - r_px), int(2*r_px), int(2*r_px))
        
        # Точки с цветом по λ
        painter.setPen(Qt.NoPen)
        for dx, dy, wl_idx in spots:
            if self.polychromatic and wl_idx < 100:
                # Получаем цвет из длины волны
                wl_um = 0.588  # default
                if wl_idx < len(self._get_wavelengths()):
                    wl_um = self._get_wavelengths()[wl_idx]
                color = _wl_to_plot_color(wl_um)
                color.setAlpha(180)
            else:
                color = QColor(0, 255, 120, 180)
            painter.setBrush(QBrush(color))
            px = cx + dx * scale
            py = cy - dy * scale
            painter.drawEllipse(int(px) - 1, int(py) - 1, 3, 3)
        
        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(int(cx), top, int(cx), top + ph)
        painter.drawLine(m, int(cy), m + pw, int(cy))
        
        # RMS
        cur_rms = self.poly_rms if self.polychromatic else self.rms
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + ph + 25, f"RMS: {cur_rms:.4f} мм | {len(spots)} лучей")
        title = "Точечная диаграмма (полихром.)" if self.polychromatic else "Точечная диаграмма"
        painter.drawText(m + 5, top + 15, title)

        self.set_ranges(-max_r, max_r, -max_r, max_r)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()
    
    def _get_wavelengths(self):
        """Получить список длин волн из текущей системы (ленивый кэш)."""
        if not hasattr(self, '_wl_cache'):
            return [0.588]
        return self._wl_cache


class AberrationGraphWidget(AberrationPlotWidget):
    """Графики поперечных/продольных/волновых аберраций."""

    # Цветовая схема по длине волны (мкм)
    _WL_COLORS = [
        (0.405, QColor(148, 0, 211)),    # h — фиолетовый
        (0.436, QColor(100, 0, 255)),    # g — сине-фиолетовый
        (0.486, QColor(0, 80, 255)),     # F — синий
        (0.546, QColor(220, 200, 0)),    # e — жёлтый
        (0.588, QColor(0, 200, 80)),     # d — зелёный
        (0.656, QColor(255, 60, 60)),    # C — красный
        (0.707, QColor(200, 0, 0)),      # r — тёмно-красный
    ]

    @staticmethod
    def _wl_to_color(wl_um: float) -> QColor:
        """Подбирает цвет по ближайшей стандартной линии."""
        best = min(AberrationGraphWidget._WL_COLORS,
                   key=lambda item: abs(item[0] - wl_um))
        return best[1]

    @staticmethod
    def _wl_label(wl_um: float) -> str:
        """Формирует подпись: 'λ=486 нм (F)' для стандартных линий."""
        nm = wl_um * 1000
        named = {
            404.66: 'h', 435.83: 'g', 486.13: 'F',
            546.07: 'e', 587.56: 'd', 656.27: 'C',
            706.52: 'r',
        }
        for std_nm, name in named.items():
            if abs(nm - std_nm) < 1.0:
                return f"λ={std_nm:.1f} нм ({name})"
        return f"λ={nm:.1f} нм"

    def __init__(self, mode='transverse', parent=None):
        super().__init__(parent)
        self.mode = mode  # 'transverse', 'longitudinal', 'wavefront'
        self.fan_data = {}
        self.isoplanatism_data = {}  # {wl: (pupils, iso_vals_um)}
        self.oblique_data = None  # (pupil_heights, dy_mer_um, dy_sag_um)
        self._azimuth_deg = 0.0  # азимутальный угол для косого сечения
    
    def set_azimuth(self, azimuth_deg: float):
        self._azimuth_deg = azimuth_deg
    
    def set_data(self, sys: OpticalSystem, azimuth_deg: float = None):
        if azimuth_deg is not None:
            self._azimuth_deg = azimuth_deg
        wavelengths = sys.wavelengths if sys.wavelengths else [Wavelength(0.58756)]
        self.fan_data = {}
        self.isoplanatism_data = {}
        # Косое сечение — только если азимут != 0
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
        
        # Определяем диапазон
        all_vals = []
        
        if self.oblique_data:
            pupils, dy_mer, dy_sag = self.oblique_data
            for v in dy_mer + dy_sag:
                if v is not None:
                    if self.mode == 'transverse':
                        all_vals.append(v / 1000.0)  # мкм -> мм
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
        
        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(int(cx), top, int(cx), top + ph)  # Y axis
        painter.drawLine(m, int(cy), m + pw, int(cy))       # X axis
        
        # Косое сечение
        if self.oblique_data:
            pupils, dy_mer, dy_sag = self.oblique_data
            # Меридиональная компонента (зелёная)
            painter.setPen(QPen(QColor(0, 200, 80), 2))
            prev = None
            for h, v in zip(pupils, dy_mer):
                if v is None:
                    prev = None; continue
                px = cx + h * pw / 2.0
                py = cy - (v / 1000.0) / val_max * ph / 2.0
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)
            # Сагиттальная компонента (голубая)
            painter.setPen(QPen(QColor(80, 180, 255), 2))
            prev = None
            for h, v in zip(pupils, dy_sag):
                if v is None:
                    prev = None; continue
                px = cx + h * pw / 2.0
                py = cy - (v / 1000.0) / val_max * ph / 2.0
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)
        else:
            # Обычные графики для каждой длины волны
            for wl, fan in self.fan_data.items():
                color = self._wl_to_color(wl)
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
            
            # Неизопланатизм
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
                    color = self._wl_to_color(wl)
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
        
        # Метки
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
        
        # Легенда
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
                color = self._wl_to_color(wl)
                label = self._wl_label(wl)
                ly = legend_y_start + idx * 16
                painter.setPen(QPen(color, 3))
                painter.drawLine(int(legend_x), int(ly), int(legend_x + 18), int(ly))
                painter.setPen(QColor(200, 200, 220))
                painter.setFont(QFont("Consolas", 8))
                painter.drawText(int(legend_x + 22), int(ly + 4), label)
        
        # Масштаб
        painter.setPen(QColor(120, 120, 140))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + ph + 25, f"±{val_max:.4f}")

        self.set_ranges(-1.0, 1.0, -val_max, val_max)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class MTFWidget(AberrationPlotWidget):
    """ЧКХ/MTF — геометрическая + дифракционная + безаберрационная + полихроматическая (Л1.7)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.geo_mtf = None
        self.diff_mtf = None
        self.poly_mtf = None
        self.diff_limited_mtf = None
    
    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        spots = compute_spot_diagram(sys, wl=wl, num_rays=40)
        self.geo_mtf = compute_geometric_mtf(spots, max_freq=100, num_freqs=20)
        try:
            from diffraction_mtf import compute_diffraction_mtf_quick
            self.diff_mtf = compute_diffraction_mtf_quick(sys, wl=wl)
        except Exception:
            self.diff_mtf = None
        # Безаберрационная MTF
        try:
            from diffraction_mtf import compute_diffraction_limited_mtf
            self.diff_limited_mtf = compute_diffraction_limited_mtf(sys, wl=wl)
        except Exception:
            self.diff_limited_mtf = None
        # Полихроматическая MTF
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
        
        # Определяем максимальную частоту для шкалы
        max_freq = 100.0
        if self.diff_mtf and self.diff_mtf['freqs']:
            max_freq = max(max_freq, max(self.diff_mtf['freqs']))
        if self.poly_mtf and self.poly_mtf['freqs']:
            max_freq = max(max_freq, max(self.poly_mtf['freqs']))
        
        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)  # X
        painter.drawLine(m, top, m, top + ph)              # Y
        
        # Геометрическая MTF (зелёная)
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
        
        # Дифракционная MTF (голубая)
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
        
        # Полихроматическая MTF (оранжевая)
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
        
        # Безаберрационная MTF (белая пунктирная)
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
        
        # Legend
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


class DistortionWidget(AberrationPlotWidget):
    """График дисторсии vs поле."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data = None

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(m, int(cy), m + pw, int(cy))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        # Кривая
        painter.setPen(QPen(QColor(255, 120, 40), 2))
        prev = None
        for d in sorted(valid, key=lambda x: x['field_y']):
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['distortion'] / dist_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Дисторсия (%)")
        painter.drawText(m + 5, top + ph + 25, f"±{field_max:.1f}° / ±{dist_max:.3f}%")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class AstigmatismWidget(AberrationPlotWidget):
    """Кривизна поля и астигматизм: Z'm, Z's vs поле."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data = None

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(m, int(cy), m + pw, int(cy))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        sorted_data = sorted(valid, key=lambda x: x['field_y'])

        # Z'm — меридиональный (зелёный)
        painter.setPen(QPen(QColor(0, 200, 80), 2))
        prev = None
        for d in sorted_data:
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['z_m'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Z's — сагиттальный (голубой)
        painter.setPen(QPen(QColor(80, 160, 255), 2))
        prev = None
        for d in sorted_data:
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['z_s'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Метки
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
    """График комы vs поле."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data = None

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(m, int(cy), m + pw, int(cy))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        # Кривая
        painter.setPen(QPen(QColor(200, 80, 255), 2))
        prev = None
        for d in sorted(valid, key=lambda x: x['field_y']):
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['coma'] / coma_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Кома (мм)")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 25, f"±{field_max:.1f}° / ±{coma_max:.5f} мм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class FocusCurveWidget(AberrationPlotWidget):
    """Фокусировочная кривая: MTF vs смещение (Л1.7.4)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.curve_data = None
        self.best_defocus = 0.0
        self.best_mtf = 0.0

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        self.curve_data = compute_focus_curve(sys, wl=wl, num_points=40,
                                               defocus_range=2.0, freq_lpmm=50.0,
                                               num_rays=25, field_y=0.0)
        if self.curve_data:
            best = max(self.curve_data, key=lambda p: p[1])
            self.best_defocus = best[0]
            self.best_mtf = best[1]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.curve_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        # Диапазоны
        defocus_vals = [p[0] for p in self.curve_data]
        mtf_vals = [p[1] for p in self.curve_data]
        d_min, d_max = min(defocus_vals), max(defocus_vals)
        d_range = d_max - d_min if d_max != d_min else 1.0

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        # X: defocus, Y: MTF (0..1)
        # Горизонтальная ось (MTF=0)
        y0 = top + ph
        # Горизонтальная ось (MTF=1)
        y1 = top
        # Вертикальная ось (defocus=0)
        cx = m + pw * (-d_min) / d_range if d_range > 0 else m + pw / 2

        painter.drawLine(m, y0, m + pw, y0)  # X axis
        painter.drawLine(m, y0, m, y1)         # Y axis
        # Линия defocus=0
        painter.setPen(QPen(QColor(50, 50, 70), 1, Qt.DashLine))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        # Кривая MTF
        painter.setPen(QPen(QColor(255, 180, 40), 2))
        prev = None
        for defocus, mtf in self.curve_data:
            px = m + (defocus - d_min) / d_range * pw
            py = top + ph - mtf * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Маркер максимума
        if self.best_mtf > 0:
            bx = m + (self.best_defocus - d_min) / d_range * pw
            by = top + ph - self.best_mtf * ph
            # Крестик
            painter.setPen(QPen(QColor(255, 60, 60), 2))
            painter.drawLine(int(bx) - 6, int(by) - 6, int(bx) + 6, int(by) + 6)
            painter.drawLine(int(bx) - 6, int(by) + 6, int(bx) + 6, int(by) - 6)
            # Вертикальная пунктирная линия от маркера к оси X
            painter.setPen(QPen(QColor(255, 60, 60, 120), 1, Qt.DashLine))
            painter.drawLine(int(bx), int(by), int(bx), top + ph)

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Фокусировочная кривая (MTF vs defocus)")
        painter.drawText(m + pw - 80, top + ph + 25, "Δz (мм)")
        painter.drawText(m - 45, top + 5, "1.0")
        painter.drawText(m - 45, top + ph - 5, "0.0")

        # Диапазон по X
        painter.drawText(m, top + ph + 25, f"{d_min:.1f}")
        painter.drawText(m + pw - 30, top + ph + 25, f"{d_max:.1f}")

        # Info line
        painter.setPen(QColor(255, 180, 40))
        painter.drawText(m + 5, top + ph + 40,
                         f"Лучший фокус: Δz={self.best_defocus:+.3f} мм  MTF={self.best_mtf:.4f}")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class PSFWidget(AberrationPlotWidget):
    """PSF (Point Spread Function) — 2D тепловая карта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.psf_data = None
        self.dx = None
        self.dy = None

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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
        # Рисуем PSF как тепловую карту (QImage)
        img_w = min(pw, ph)
        img_h = img_w
        ox = m + (pw - img_w) // 2
        oy = top + (ph - img_h) // 2

        # Логарифмическая шкала для видимости деталей
        psf_log = np.log10(psf + 1e-6)
        vmin, vmax = psf_log.min(), psf_log.max()
        if vmax - vmin < 1e-10:
            vmax = vmin + 1
        normalized = ((psf_log - vmin) / (vmax - vmin) * 255).astype(np.uint8)

        # Создаём QImage
        from PyQt5.QtGui import QImage
        # Upscale to widget size
        img_data = np.zeros((ny, nx, 4), dtype=np.uint8)
        # Цветовая карта: тёмно-синий → голубой → зелёный → жёлтый → белый
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
                img_data[i, j] = [b, g, r, 255]  # BGRA

        qimg = QImage(img_data.data, nx, ny, nx * 4,
                      QImage.Format_RGB32).copy()
        scaled = qimg.scaled(int(img_w), int(img_h))
        painter.drawImage(ox, oy, scaled)

        # Рамка
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRect(ox, oy, int(img_w), int(img_h))

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "PSF (Point Spread Function)")
        if self.dx is not None:
            painter.drawText(m + 5, top + ph + 25,
                             f"{self.dx.min():.1f}..{self.dx.max():.1f} мкм (log scale)")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class LSFWidget(AberrationPlotWidget):
    """LSF (Line Spread Function) — 1D график."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lsf_tan = None
        self.lsf_sag = None
        self.axis = None

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)

        x_min, x_max = self.axis.min(), self.axis.max()
        x_range = x_max - x_min if x_max != x_min else 1.0

        # Tangential (зелёный)
        painter.setPen(QPen(QColor(0, 200, 80), 2))
        prev = None
        for i, (val, x) in enumerate(zip(self.lsf_tan, self.axis)):
            px = m + (x - x_min) / x_range * pw
            py = top + ph - val * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Sagittal (голубой)
        painter.setPen(QPen(QColor(80, 180, 255), 2))
        prev = None
        for i, (val, x) in enumerate(zip(self.lsf_sag, self.axis)):
            px = m + (x - x_min) / x_range * pw
            py = top + ph - val * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "LSF (Line Spread Function)")
        painter.drawText(m + pw - 60, top + ph + 25, "мкм")
        painter.drawText(m - 40, top + 5, "1.0")
        painter.drawText(m - 40, top + ph - 5, "0.0")
        # Легенда
        painter.setPen(QPen(QColor(0, 200, 80)))
        painter.drawText(m + 5, top + ph + 25, "Мерид.")
        painter.setPen(QPen(QColor(80, 180, 255)))
        painter.drawText(m + 60, top + ph + 25, "Сагит.")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class ENCWidget(AberrationPlotWidget):
    """Encircled Energy — график."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.r_um = None
        self.enc = None

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)

        r_max = self.r_um.max()
        if r_max < 1e-10:
            r_max = 1.0

        # Кривая
        painter.setPen(QPen(QColor(255, 160, 40), 2))
        prev = None
        for r, e in zip(self.r_um, self.enc):
            px = m + r / r_max * pw
            py = top + ph - e * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Пунктирные линии 50%, 80%, 90%
        for pct, color in [(0.5, QColor(100, 100, 120)),
                            (0.8, QColor(100, 100, 120)),
                            (0.9, QColor(100, 100, 120))]:
            py = top + ph - pct * ph
            painter.setPen(QPen(color, 1, Qt.DashLine))
            painter.drawLine(m, int(py), m + pw, int(py))
            painter.setPen(QColor(120, 120, 140))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(m + pw + 2, int(py) + 4, f"{int(pct*100)}%")

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Encircled Energy (ENC)")
        painter.drawText(m + pw - 40, top + ph + 25, "мкм")
        painter.drawText(m - 40, top + 5, "1.0")
        painter.drawText(m - 40, top + ph - 5, "0.0")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class PTFWidget(AberrationPlotWidget):
    """PTF (Phase Transfer Function) — график."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ptf_data = None

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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
        # Диапазон PTF
        all_vals = ptf_t + ptf_s
        ptf_max = max(abs(v) for v in all_vals) if all_vals else 3.14
        ptf_max = max(ptf_max, 0.01)

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)
        painter.drawLine(m, top, m, top + ph)
        # Нулевая линия
        cy = top + ph / 2
        painter.setPen(QPen(QColor(50, 50, 70), 1, Qt.DashLine))
        painter.drawLine(m, int(cy), m + pw, int(cy))

        # Tangential (зелёный)
        painter.setPen(QPen(QColor(0, 200, 80), 2))
        prev = None
        for f, v in zip(freqs, ptf_t):
            px = m + f / max(max_freq, 1) * pw
            py = cy - v / ptf_max * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Sagittal (голубой)
        painter.setPen(QPen(QColor(80, 180, 255), 2))
        prev = None
        for f, v in zip(freqs, ptf_s):
            px = m + f / max(max_freq, 1) * pw
            py = cy - v / ptf_max * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "PTF (Phase Transfer Function)")
        painter.drawText(m + pw - 60, top + ph + 25, "лин/мм")
        painter.drawText(m - 40, top + 5, f"+{ptf_max:.2f}")
        painter.drawText(m - 40, top + ph - 5, f"-{ptf_max:.2f}")
        # Легенда
        painter.setPen(QPen(QColor(0, 200, 80)))
        painter.drawText(m + 5, top + ph + 25, "Мерид.")
        painter.setPen(QPen(QColor(80, 180, 255)))
        painter.drawText(m + 60, top + ph + 25, "Сагит.")

        self.set_ranges(-1.0, 1.0, -max_freq, max_freq)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class HeatmapWidget(AberrationPlotWidget):
    """Топограмма пятна рассеяния (Heatmap) — тепловая карта плотности."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.heatmap = None
        self.x_range = (0, 0)
        self.y_range = (0, 0)
        self.grid_size = 100
        self.num_points = 0
        self.centroid_x = 0.0
        self.centroid_y = 0.0
        self.max_density = 0.0
        # Zoom state
        self._zoom = False
        self._zoom_rect = None
    
    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            self.heatmap, self.x_range, self.y_range = compute_spot_heatmap(
                sys, wl=wl, num_rays=500, field_y=0.0, grid_size=self.grid_size)
            self.num_points = int(np.sum(self.heatmap > 0))
            # Centroid
            if self.heatmap is not None and self.heatmap.size > 0:
                ys = np.linspace(self.y_range[0], self.y_range[1], self.grid_size)
                xs = np.linspace(self.x_range[0], self.x_range[1], self.grid_size)
                total = self.heatmap.sum()
                if total > 0:
                    yy, xx = np.meshgrid(ys, xs, indexing='ij')
                    self.centroid_x = float(np.sum(xx * self.heatmap) / total)
                    self.centroid_y = float(np.sum(yy * self.heatmap) / total)
                self.max_density = float(self.heatmap.max())
        except Exception:
            self.heatmap = None
        self.update()
    
    @staticmethod
    def _hot_colormap(v):
        """Hot colormap: чёрный → красный → жёлтый → белый. v in [0,1]."""
        if v < 0.33:
            t = v / 0.33
            return (int(255 * t), 0, 0)
        elif v < 0.67:
            t = (v - 0.33) / 0.34
            return (255, int(255 * t), 0)
        else:
            t = (v - 0.67) / 0.33
            return (255, 255, int(255 * t))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)
        
        if self.heatmap is None or self.heatmap.size == 0:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return
        
        # Draw heatmap as QImage
        gs = self.grid_size
        img_w = min(pw, ph)
        img_h = img_w
        ox = m + (pw - img_w) // 2
        oy = top + (ph - img_h) // 2
        
        # Build BGRA image data
        img_data = np.zeros((gs, gs, 4), dtype=np.uint8)
        for iy in range(gs):
            for ix in range(gs):
                v = self.heatmap[iy, ix]
                r, g, b = self._hot_colormap(min(1.0, max(0.0, v)))
                img_data[iy, ix] = [b, g, r, 255]  # BGRA
        
        from PyQt5.QtGui import QImage
        qimg = QImage(img_data.data, gs, gs, gs * 4, QImage.Format_RGB32).copy()
        scaled = qimg.scaled(int(img_w), int(img_h))
        painter.drawImage(ox, oy, scaled)
        
        # Frame
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRect(ox, oy, int(img_w), int(img_h))
        
        # Coordinate labels on frame
        painter.setPen(QColor(180, 180, 200))
        painter.setFont(QFont("Consolas", 8))
        # X axis labels
        x_min_s = f"{self.x_range[0]*1000:.2f}"
        x_max_s = f"{self.x_range[1]*1000:.2f}"
        y_min_s = f"{self.y_range[0]*1000:.2f}"
        y_max_s = f"{self.y_range[1]*1000:.2f}"
        painter.drawText(ox, oy + int(img_h) + 12, x_min_s)
        painter.drawText(ox + int(img_w) - 40, oy + int(img_h) + 12, x_max_s + " мкм")
        painter.drawText(ox - 45, oy + 10, y_max_s)
        painter.drawText(ox - 45, oy + int(img_h), y_min_s)
        
        # Title
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Топограмма пятна рассеяния")
        
        # Info
        painter.setPen(QColor(150, 150, 170))
        painter.drawText(m + 5, top + ph + 25,
                         f"{gs}×{gs} | макс={self.max_density:.3f} | "
                         f"центр=({self.centroid_x*1000:.2f}, {self.centroid_y*1000:.2f}) мкм")
        
        # Colorbar (small gradient bar on the right)
        bar_x = ox + int(img_w) + 8
        bar_w = 12
        bar_y = oy
        bar_h = int(img_h)
        if bar_x + bar_w + 5 < w:
            for iy in range(bar_h):
                v = 1.0 - iy / max(bar_h - 1, 1)
                r, g, b = self._hot_colormap(v)
                painter.setPen(QPen(QColor(r, g, b), 1))
                painter.drawLine(bar_x, bar_y + iy, bar_x + bar_w, bar_y + iy)
            painter.setPen(QPen(QColor(80, 80, 100), 1))
            painter.drawRect(bar_x, bar_y, bar_w, bar_h)
            painter.setPen(QColor(180, 180, 200))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(bar_x + bar_w + 2, bar_y + 8, "1.0")
            painter.drawText(bar_x + bar_w + 2, bar_y + bar_h, "0.0")
        
        self.paint_finalize(painter, self._plot_rect)
        painter.end()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._zoom = not self._zoom
            self.update()
        super().keyPressEvent(event)


class BeamGeometryWidget(AberrationPlotWidget):
    """Габариты пучков: контур входного зрачка для разных полей."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.beam_data = None

    def set_data(self, sys: OpticalSystem):
        self.beam_data = compute_beam_geometry(sys)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.beam_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        aperture = 0.0
        if hasattr(self, '_sys_ref'):
            aperture = self._sys_ref.aperture_value if self._sys_ref.aperture_value > 0 else 10.0
        if aperture <= 0:
            aperture = 10.0

        # Рисуем контур входного зрачка для каждого поля
        colors = [QColor(0, 200, 80), QColor(80, 180, 255), QColor(255, 160, 40),
                  QColor(255, 80, 80), QColor(200, 80, 255)]

        scale = min(pw, ph) / (aperture * 1.2) if aperture > 0 else 1.0
        cx = m + pw / 2
        cy = top + ph / 2

        # Нулевой (круговой) зрачок
        r_pupil = aperture / 2.0
        r_px = r_pupil * scale
        painter.setPen(QPen(QColor(100, 100, 120), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - r_px), int(cy - r_px), int(2 * r_px), int(2 * r_px))

        # Контуры для каждого поля
        for idx, bd in enumerate(self.beam_data):
            color = colors[idx % len(colors)]
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)

            vign_u = bd.get('vignetting_upper', 1.0)
            vign_l = bd.get('vignetting_lower', 1.0)
            Ay = bd.get('Ay', aperture / 2)

            # Контур: эллипс с верхним и нижним виньетированием
            r_upper = vign_u * Ay * scale
            r_lower = vign_l * Ay * scale
            r_sag = bd.get('Ax', Ay) * scale

            # Рисуем как деформированный эллипс
            path = QPainterPath()
            n_pts = 64
            for i in range(n_pts + 1):
                angle = 2 * math.pi * i / n_pts
                # Модифицируем радиус: верхний (sin>0) и нижний (sin<0)
                sin_a = math.sin(angle)
                cos_a = math.cos(angle)
                if sin_a >= 0:
                    r_y = r_upper
                else:
                    r_y = r_lower
                px = cx + cos_a * r_sag
                py = cy - sin_a * r_y
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            painter.drawPath(path)

            # Метка поля
            painter.setPen(color)
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(cx + r_sag + 5), int(cy - idx * 14), f"{bd['field_y']:.1f}°")

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(int(cx), top, int(cx), top + ph)
        painter.drawLine(m, int(cy), m + pw, int(cy))

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Контуры входного зрачка")
        painter.drawText(m + 5, top + ph + 25, f"D = {aperture:.1f} мм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class ChiefRayWidget(AberrationPlotWidget):
    """Характеристики главных лучей: дисторсия, астигматизм, хроматизм."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chief_data = None

    def set_data(self, sys: OpticalSystem):
        self.chief_data = compute_chief_ray_characteristics(sys)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)

        if not self.chief_data:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        valid = [d for d in self.chief_data if d['field_y'] != 0]
        if not valid:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Только осевое поле")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        field_max = max(abs(d['field_y']) for d in valid) or 1

        # Графики: Z'm (меридиональный), Z's (сагиттальный)
        all_z = [d['Zm'] for d in valid] + [d['Zs'] for d in valid]
        z_max = max(abs(v) for v in all_z if v is not None) if all_z else 0.01
        z_max = max(z_max, 0.001)

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        cx = m + pw / 2
        cy = top + ph / 2
        painter.drawLine(m, int(cy), m + pw, int(cy))
        painter.drawLine(int(cx), top, int(cx), top + ph)

        sorted_data = sorted(valid, key=lambda x: x['field_y'])

        # Z'm меридиональный (зелёный)
        painter.setPen(QPen(QColor(0, 200, 80), 2))
        prev = None
        for d in sorted_data:
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['Zm'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Z's сагиттальный (голубой)
        painter.setPen(QPen(QColor(80, 160, 255), 2))
        prev = None
        for d in sorted_data:
            px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
            py = cy - (d['Zs'] / z_max) * ph / 2.0
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Дисторсия (оранжевый пунктир)
        dist_vals = [d['distortion_rel'] for d in valid if d['distortion_rel'] is not None]
        if dist_vals:
            dist_max = max(abs(v) for v in dist_vals) or 0.01
            dist_max = max(dist_max, 0.001)
            painter.setPen(QPen(QColor(255, 160, 40), 2, Qt.DashLine))
            prev = None
            for d in sorted_data:
                if d['distortion_rel'] is not None:
                    px = m + (d['field_y'] / field_max) * pw / 2.0 + pw / 2
                    py = cy - (d['distortion_rel'] / dist_max) * ph / 2.0
                    if prev:
                        painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                    prev = (px, py)

        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Характеристики главных лучей")
        # Легенда
        painter.setPen(QColor(0, 200, 80))
        painter.drawText(m + pw - 100, top + 15, "Z'm мерид.")
        painter.setPen(QColor(80, 160, 255))
        painter.drawText(m + pw - 100, top + 28, "Z's сагит.")
        painter.setPen(QColor(255, 160, 40))
        painter.drawText(m + pw - 100, top + 41, "Дисторсия")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 25, f"±{field_max:.1f}° / ±{z_max:.4f} мм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class ZernikeWidget(AberrationPlotWidget):
    """Гистограмма коэффициентов Цернике."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.coeffs = []
        self.chromatic_data = None  # {wl_name: [(coeff, name)], ...}
        self._show_chromatic = False

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            self.coeffs = compute_zernike_coefficients(sys, wl=wl, num_rays=32,
                                                        max_order=4,
                                                        defocus_offset=defocus_offset)
        except Exception:
            self.coeffs = []
        # Хроматический Цернике
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
        """Обычная гистограмма Цернике."""
        # Skip piston
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
        """Хроматический Цернике: несколько наборов."""
        # Собираем все наборы (исключаем delta)
        datasets = {}
        for key, coeffs in self.chromatic_data.items():
            if not key.startswith('delta_'):
                datasets[key] = coeffs
            
        if not datasets:
            return
        
        # Берём имена полиномов из первого набора
        first_key = list(datasets.keys())[0]
        data = [(c, n) for c, n in datasets[first_key] if 'Piston' not in n]
        if not data:
            return
        
        # Все значения для масштаба
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
                # Находим коэфф. для данного полинома
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
        
        # Легенда
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


class WavefrontMapWidget(AberrationPlotWidget):
    """2D/3D карта волнового фронта (цветовая/изометрия)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wf_data = None
        self.coords = None
        self.mask = None
        self._mode_3d = False  # Переключатель 2D/3D

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            self.wf_data, self.coords, self.mask = compute_wavefront_map_2d(
                sys, wl=wl, grid_size=48, defocus_offset=defocus_offset)
        except Exception:
            self.wf_data = None
        self.update()

    @staticmethod
    def _rdylbu_colormap(v):
        """Red-White-Blue diverging colormap. v in [-1, 1]."""
        if v < -1: v = -1
        if v > 1: v = 1
        if v < 0:
            # Blue to White
            t = 1 + v  # 0..1
            return (int(255 * t), int(255 * t), 255)
        else:
            # White to Red
            t = 1 - v  # 1..0
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
        """Стандартная 2D карта."""
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

        # Colorbar
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
        """3D изометрическая поверхность волнового фронта."""
        gs = self.wf_data.shape[0]
        valid = self.wf_data[self.mask > 0]
        if valid.size == 0:
            return
        w_max = max(abs(valid.max()), abs(valid.min()), 1e-6)

        # Subsample для скорости
        step = max(1, gs // 30)
        Zs = self.wf_data[::step, ::step]
        Ms = self.mask[::step, ::step]
        ny_s, nx_s = Zs.shape

        scale_xy = min(pw, ph) * 0.35 / max(nx_s, ny_s)
        scale_z = ph * 0.35

        def project(ix, iy, zv):
            px = (ix - nx_s/2) * scale_xy * 0.7 - (iy - ny_s/2) * scale_xy * 0.7
            py = (ix - nx_s/2) * scale_xy * 0.35 + (iy - ny_s/2) * scale_xy * 0.35 - zv * scale_z
            return (m + pw/2 + px, top + ph * 0.65 + py)

        # Рисуем сзади наперёд
        for iy in range(ny_s - 1, -1, -1):
            for ix in range(nx_s - 1, -1, -1):
                if Ms[iy, ix] < 0.5:
                    continue
                z0 = Zs[iy, ix] / w_max  # нормированное значение

                # Цвет по значению
                r, g, b = self._rdylbu_colormap(z0)
                # Освещение
                shade = 0.5 + 0.5 * (1.0 - iy / max(ny_s - 1, 1))
                r = min(255, int(r * shade))
                g = min(255, int(g * shade))
                b = min(255, int(b * shade))

                x0, y0 = project(ix, iy, z0)
                x_base, y_base = project(ix, iy, 0)

                # Вертикальная линия до основания
                if abs(z0) > 0.01:
                    painter.setPen(QPen(QColor(r//2, g//2, b//2, 80), 1))
                    painter.drawLine(int(x0), int(y0), int(x_base), int(y_base))

                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(r, g, b)))
                sz = max(2, int(3 * shade))
                painter.drawEllipse(int(x0) - sz//2, int(y0) - sz//2, sz, sz)

        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "Карта волнового фронта (λ) [3D]")
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(m + 5, top + ph + 25, f"PV={valid.max()-valid.min():.3f}λ | RMS={np.sqrt(np.mean(valid**2)):.3f}λ")


class ESFWidget(AberrationPlotWidget):
    """Edge Spread Function — S-кривая."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_um = None
        self.esf = None

    def set_data(self, sys: OpticalSystem, defocus_offset: float = 0.0):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Axes
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top + ph, m + pw, top + ph)  # X
        painter.drawLine(m, top, m, top + ph)              # Y

        # ESF curve (orange)
        painter.setPen(QPen(QColor(255, 160, 40), 2))
        prev = None
        step = max(1, len(self.x_um) // 200)
        for i in range(0, len(self.x_um), step):
            px = m + (self.x_um[i] - x_min) / x_range * pw
            py = top + ph - self.esf[i] * ph
            if prev:
                painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
            prev = (px, py)

        # Dashed 0.5 line
        painter.setPen(QPen(QColor(100, 100, 120), 1, Qt.DashLine))
        py_half = top + ph - 0.5 * ph
        painter.drawLine(m, int(py_half), m + pw, int(py_half))

        # Labels
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "ESF (Edge Spread Function)")
        painter.drawText(m + pw - 60, top + ph + 25, "мкм")
        painter.drawText(m - 40, top + 5, "1.0")
        painter.drawText(m - 40, top + ph - 5, "0.0")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class BarTargetWidget(AberrationPlotWidget):
    """Штриховая мира — 1D профиль (идеал + размытый)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_um = None
        self.ideal = None
        self.blurred = None
        self.mtf_table = None  # list of dicts

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Разделяем на две половины: верх (идеал), низ (размытый)
        half_h = h // 2

        # Рамки
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRect(50, 10, w - 60, half_h - 20)
        painter.drawRect(50, half_h + 5, w - 60, half_h - 20)

        # Заголовки
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

        # Верх: идеальный профиль (белый)
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

        # Низ: размытый профиль (оранжевый)
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

        # Ось X
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m_left, top_y + ph_top, m_left + plot_w, top_y + ph_top)
        painter.drawLine(m_left, bot_y + ph_bot, m_left + plot_w, bot_y + ph_bot)
        painter.setPen(QColor(160, 160, 180))
        painter.drawText(m_left + plot_w - 30, bot_y + ph_bot + 15, "мкм")

        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class FocusDiagramWidget(QWidget, InteractivePlot):
    """Фокусировочные диаграммы — 5 spot diagrams для разных позиций плоскости изображения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 300)
        self.spots_by_defocus = {}  # label -> (spots, rms_info)
        self.max_range = 0.001
        self._init_interactive()

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
    
    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        parax = paraxial_trace(sys)
        bfd = parax.get('back_focal_distance', 0)
        # DS' = BFD * 0.01 (настраиваемый)
        if abs(bfd) < 1e-6:
            efl = parax.get('focal_length', 50)
            bfd = abs(efl) * 0.5
        ds = abs(bfd) * 0.01
        
        defoci = [
            ("номинал", 0.0),
            ("+DS'", +ds),
            ("-DS'", -ds),
            ("+2DS'", +2*ds),
            ("-2DS'", -2*ds),
        ]
        
        self.spots_by_defocus = {}
        all_spots = []
        for label, df in defoci:
            spots = compute_spot_diagram_at_defocus(sys, wl=wl, num_rays=60,
                                                     field_y=0.0, defocus_mm=df)
            rms_info = compute_rms_spot_xy(spots)
            self.spots_by_defocus[label] = (spots, rms_info, df)
            all_spots.extend(spots)
        
        if all_spots:
            self.max_range = max(math.sqrt(dx**2 + dy**2) for dx, dy in all_spots)
            self.max_range = max(self.max_range, 1e-6)
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor(10, 10, 25))
        
        if not self.spots_by_defocus:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return
        
        labels_order = ["номинал", "+DS'", "-DS'", "+2DS'", "-2DS'"]
        n = len(labels_order)
        margin = 10
        top_margin = 25
        bot_margin = 35
        cell_w = (w - 2 * margin) / n
        cell_h = h - top_margin - bot_margin
        
        for idx, label in enumerate(labels_order):
            if label not in self.spots_by_defocus:
                continue
            spots, rms_info, df = self.spots_by_defocus[label]
            
            ox = margin + idx * cell_w
            oy = top_margin
            cw = cell_w - 4
            ch = cell_h
            
            # Рамка
            painter.setPen(QPen(QColor(60, 60, 80), 1))
            painter.drawRect(int(ox), int(oy), int(cw), int(ch))
            
            cx = ox + cw / 2
            cy = oy + ch / 2
            scale = min(cw, ch) / (2.2 * self.max_range)
            
            # Оси
            painter.setPen(QPen(QColor(50, 50, 70), 1))
            painter.drawLine(int(cx), int(oy), int(cx), int(oy + ch))
            painter.drawLine(int(ox), int(cy), int(ox + cw), int(cy))
            
            # Точки
            painter.setPen(Qt.NoPen)
            color = QColor(0, 255, 120, 160)
            painter.setBrush(QBrush(color))
            for dx, dy in spots:
                px = cx + dx * scale
                py = cy - dy * scale
                painter.drawEllipse(int(px) - 1, int(py) - 1, 2, 2)
            
            # Подпись
            painter.setPen(QColor(200, 200, 220))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(ox), int(oy - 2), int(cw), 20,
                             Qt.AlignCenter, label)
            
            # RMS
            painter.setPen(QColor(150, 200, 150))
            painter.setFont(QFont("Consolas", 7))
            rms_val = rms_info['rms_total']
            painter.drawText(int(ox), int(oy + ch + 2), int(cw), 15,
                             Qt.AlignCenter, f"RMS={rms_val:.4f}")
            
            # Defocus
            painter.setPen(QColor(120, 120, 150))
            painter.drawText(int(ox), int(oy + ch + 14), int(cw), 15,
                             Qt.AlignCenter, f"Δz={df:+.3f}")
        
        # Заголовок
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 10))
        painter.drawText(margin, 15, "Фокусировочные диаграммы (5 позиций)")
        
        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class PSF3DWidget(AberrationPlotWidget):
    """PSF как псевдо-3D изометрическая проекция через QPainter."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_coords = None
        self.y_coords = None
        self.Z = None
    
    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            self.x_coords, self.y_coords, self.Z = compute_psf_3d(
                sys, wl=wl, grid_size=64, field_y=0.0)
        except Exception:
            self.Z = None
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m, top, pw, ph = self.paint_grid(painter, w, h, margin=50)
        
        if self.Z is None or self.x_coords is None:
            painter.setPen(QColor(150, 150, 170))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return
        
        Z = self.Z
        ny, nx = Z.shape
        
        # Subsample для скорости
        step = max(1, max(ny, nx) // 40)
        Zs = Z[::step, ::step]
        ny_s, nx_s = Zs.shape
        
        # Изометрические коэффициенты
        # X вправо-вниз, Y влево-вниз, Z вверх
        scale_xy = min(pw, ph) * 0.35 / max(nx_s, ny_s)
        scale_z = ph * 0.4
        angle_x = 0.7  # наклон по X
        angle_y = 0.7  # наклон по Y
        
        def project(ix, iy, zv):
            # Изометрическая проекция
            px = (ix - nx_s/2) * scale_xy * angle_x - (iy - ny_s/2) * scale_xy * angle_y
            py = (ix - nx_s/2) * scale_xy * 0.4 + (iy - ny_s/2) * scale_xy * 0.4 - zv * scale_z
            return (m + pw/2 + px, top + ph * 0.7 + py)
        
        # Рисуем сетку с заполнением (painter's algorithm: сзади наперёд)
        for iy in range(ny_s - 1, -1, -1):
            for ix in range(nx_s - 1, -1, -1):
                z0 = Zs[iy, ix]
                
                # Цвет по высоте
                intensity = min(1.0, max(0.0, z0))
                r = int(20 + 235 * intensity)
                g = int(20 + 80 * intensity)
                b = int(80 + 175 * intensity)
                
                # Освещение: по позиции
                shade = 0.6 + 0.4 * (1.0 - iy / max(ny_s - 1, 1))
                r = min(255, int(r * shade))
                g = min(255, int(g * shade))
                b = min(255, int(b * shade))
                
                x0, y0 = project(ix, iy, z0)
                
                # Рисуем столбик (вертикальная линия до основания)
                x_base, y_base = project(ix, iy, 0)
                if z0 > 0.01:
                    painter.setPen(QPen(QColor(r // 2, g // 2, b // 2, 100), 1))
                    painter.drawLine(int(x0), int(y0), int(x_base), int(y_base))
                
                # Точка поверхности
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(r, g, b)))
                sz = max(2, int(3 * shade))
                painter.drawEllipse(int(x0) - sz//2, int(y0) - sz//2, sz, sz)
        
        # Метки
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "PSF (3D изометрия)")
        if self.x_coords is not None and len(self.x_coords) > 0:
            x_span = (self.x_coords.max() - self.x_coords.min())
            painter.drawText(m + 5, top + ph + 25,
                             f"{x_span:.1f} мкм | max={Z.max():.4f}")
        
        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class WavefrontRmsVsFieldWidget(AberrationPlotWidget):
    """СКВ волновой аберрации по полю."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field_data = None  # (field_y_values, rms_full, rms_no_def, rms_no_tilt)

    def set_data(self, sys: OpticalSystem):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
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

        # Определяем диапазон
        all_vals = [v for v in rms_full + rms_no_def + rms_no_tilt
                    if not (v != v)]  # skip NaN
        if not all_vals:
            self.paint_finalize(painter, self._plot_rect)
            painter.end()
            return

        val_max = max(abs(v) for v in all_vals)
        val_max = max(val_max, 1e-6)
        field_max = max(abs(f) for f in field_vals) if field_vals else 1.0
        field_max = max(field_max, 1e-6)

        # Оси
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawLine(m, top, m, top + ph)  # Y axis
        painter.drawLine(m, top + ph, m + pw, top + ph)  # X axis

        curves = [
            (rms_full, QColor(60, 130, 255), "Полное СКВ", 2.0, Qt.SolidLine),
            (rms_no_def, QColor(60, 220, 100), "За вычетом дефокуса", 2.0, Qt.SolidLine),
            (rms_no_tilt, QColor(255, 80, 80), "За вычетом наклона", 2.0, Qt.SolidLine),
        ]

        for data, color, label, width, style in curves:
            painter.setPen(QPen(color, width, style))
            prev = None
            for i, (f, v) in enumerate(zip(field_vals, data)):
                if v != v:  # NaN
                    prev = None
                    continue
                px = m + f / field_max * pw
                py = top + ph - v / val_max * ph
                if prev:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
                prev = (px, py)

        # Title
        painter.setPen(QColor(200, 200, 220))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + 5, top + 15, "СКВ волновой аберрации по полю")

        # Legend
        legend_x = m + pw - 180
        legend_y = top + 25
        painter.fillRect(int(legend_x - 4), int(legend_y - 14),
                         184, 52, QColor(15, 15, 30, 200))
        painter.setPen(QPen(QColor(60, 60, 80), 1))
        painter.drawRect(int(legend_x - 4), int(legend_y - 14),
                         184, 52)
        for idx, (_, color, label, _, _) in enumerate(curves):
            ly = legend_y + idx * 16
            painter.setPen(QPen(color, 3))
            painter.drawLine(int(legend_x), int(ly), int(legend_x + 18), int(ly))
            painter.setPen(QColor(200, 200, 220))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(legend_x + 22), int(ly + 4), label)

        # Scale labels
        painter.setPen(QColor(120, 120, 140))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(m + pw + 3, top + 5, f"{val_max:.4f} λ")
        painter.drawText(m + pw + 3, top + ph, "0")
        painter.drawText(m, top + ph + 20, "0")
        painter.drawText(m + pw - 20, top + ph + 20, f"{field_max:.1f}°")

        self.set_ranges(-1.0, 1.0, -val_max, val_max)
        self.paint_finalize(painter, self._plot_rect)
        painter.end()


class AnalysisPanel(QTabWidget):
    """Панель анализа: все графики в табах."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Global settings bar ──
        self._settings_widget = QWidget()
        settings_layout = QHBoxLayout(self._settings_widget)
        settings_layout.setContentsMargins(4, 2, 4, 2)

        settings_layout.addWidget(QLabel("Смещение плоскости (мм):"))
        self.defocus_spin = QDoubleSpinBox()
        self.defocus_spin.setRange(-100.0, 100.0)
        self.defocus_spin.setSingleStep(0.01)
        self.defocus_spin.setDecimals(4)
        self.defocus_spin.setValue(0.0)
        self.defocus_spin.setToolTip("Смещение плоскости изображения для всех вкладок")
        settings_layout.addWidget(self.defocus_spin)
        settings_layout.addStretch()

        # Азимутальный угол (#6)
        settings_layout.addWidget(QLabel("Азимут (°):"))
        self.azimuth_spin = QDoubleSpinBox()
        self.azimuth_spin.setRange(0.0, 90.0)
        self.azimuth_spin.setSingleStep(5.0)
        self.azimuth_spin.setDecimals(1)
        self.azimuth_spin.setValue(0.0)
        self.azimuth_spin.setToolTip("Азимутальный угол сечения: 0=меридиональное, 90=сагиттальное")
        settings_layout.addWidget(self.azimuth_spin)
        settings_layout.addStretch()

        settings_layout.addWidget(QLabel("Хроматизм:"))
        self.chromatic_combo = QComboBox()
        self.chromatic_combo.addItems(["Абсолютный", "Разностный", "Спектр"])
        self.chromatic_combo.setToolTip("Режим отображения хроматизма в таблицах")
        settings_layout.addWidget(self.chromatic_combo)
        settings_layout.addStretch()

        # Create plot widgets
        self.spot_diagram = SpotDiagramWidget()
        self.transverse = AberrationGraphWidget('transverse')
        self.longitudinal = AberrationGraphWidget('longitudinal')
        self.wavefront = AberrationGraphWidget('wavefront')
        self.mtf = MTFWidget()
        self.distortion = DistortionWidget()
        self.astigmatism = AstigmatismWidget()
        self.coma = ComaWidget()
        self.focus_curve = FocusCurveWidget()
        self.psf_w = PSFWidget()
        self.lsf_w = LSFWidget()
        self.enc_w = ENCWidget()
        self.ptf_w = PTFWidget()
        self.heatmap_w = HeatmapWidget()
        self.beam_geom = BeamGeometryWidget()
        self.chief_ray = ChiefRayWidget()
        self.zernike_w = ZernikeWidget()
        self.wavefront_map_w = WavefrontMapWidget()
        self.esf_w = ESFWidget()
        self.wf_rms_field_w = WavefrontRmsVsFieldWidget()
        self.focus_diagrams = FocusDiagramWidget()
        self.psf_3d_w = PSF3DWidget()
        self.bar_target_w = BarTargetWidget()

        # Create splitters: plot | table
        self._table_containers = {}  # key -> QWidget with VBoxLayout for table

        # Parax/Seidel data storage
        self._parax_data = {}
        self._seidel_data = {}
        self._fno = 0
        self._epd = 0

        # Placeholder widgets for table-only tabs (no plot)
        parax_placeholder = QWidget()
        seidel_placeholder = QWidget()

        tabs = [
            ("Параксиальные", parax_placeholder, 'parax'),
            ("Точечная диагр.", self.spot_diagram, 'spot'),
            ("Поперечные Δy'", self.transverse, 'transverse'),
            ("Продольные Δs'", self.longitudinal, 'longitudinal'),
            ("Волновые W", self.wavefront, 'wavefront'),
            ("ЧКХ (MTF)", self.mtf, 'mtf'),
            ("Дисторсия", self.distortion, 'distortion'),
            ("Астигматизм", self.astigmatism, 'astigmatism'),
            ("Кома", self.coma, 'coma'),
            ("Фокусировка", self.focus_curve, 'focus'),
            ("PSF", self.psf_w, 'psf'),
            ("PSF 3D", self.psf_3d_w, 'psf3d'),
            ("LSF", self.lsf_w, 'lsf'),
            ("ESF", self.esf_w, 'esf'),
            ("ENC", self.enc_w, 'enc'),
            ("PTF", self.ptf_w, 'ptf'),
            ("Топограмма", self.heatmap_w, 'heatmap'),
            ("Фокус.диагр.", self.focus_diagrams, 'focus_diag'),
            ("Габариты", self.beam_geom, 'beam'),
            ("Гл. лучи", self.chief_ray, 'chief'),
            ("Цернике", self.zernike_w, 'zernike'),
            ("Волн. фронт", self.wavefront_map_w, 'wfmap'),
            ("СКВ по полю", self.wf_rms_field_w, 'wf_rms_field'),
            ("Мира", self.bar_target_w, 'bar_target'),
            ("Зейдель", seidel_placeholder, 'seidel'),
        ]

        self._table_mode = False  # Global: False=graph, True=table
        self._toggle_btns = []  # All toggle buttons

        for title, plot_widget, key in tabs:
            # Table-only tabs (parax, seidel) — no toggle, just table
            if key in ('parax', 'seidel'):
                container = QWidget()
                container.setLayout(QVBoxLayout(container))
                container.layout().setContentsMargins(0, 0, 0, 0)
                self._table_containers[key] = container
                self.addTab(container, title)
                continue

            # Toggle button: graph/table mode
            toggle_btn = QPushButton("📊 График")
            toggle_btn.setCheckable(True)
            toggle_btn.setChecked(False)
            toggle_btn.setFixedWidth(90)
            toggle_btn.setToolTip("Переключить: график / таблица")
            toggle_btn.setStyleSheet("""
                QPushButton { font-size: 10px; padding: 2px 4px; }
                QPushButton:checked { background-color: #505080; }
            """)

            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(plot_widget)
            # Table container
            container = QWidget()
            container.setLayout(QVBoxLayout(container))
            container.layout().setContentsMargins(0, 0, 0, 0)
            container.setMinimumWidth(0)  # No minimum — let splitter decide
            splitter.addWidget(container)
            splitter.setStretchFactor(0, 1)  # Plot takes all by default
            splitter.setStretchFactor(1, 0)
            container.hide()  # Start in plot mode
            self._table_containers[key] = container

            # Tab page with toggle button in corner
            tab_page = QWidget()
            tab_page_layout = QVBoxLayout(tab_page)
            tab_page_layout.setContentsMargins(0, 0, 0, 0)
            tab_page_layout.setSpacing(0)

            # Top bar with toggle
            top_bar = QHBoxLayout()
            top_bar.setContentsMargins(4, 1, 4, 1)
            top_bar.addWidget(toggle_btn)
            top_bar.addStretch()
            tab_page_layout.addLayout(top_bar)
            tab_page_layout.addWidget(splitter)

            # Store references for toggle
            toggle_btn._splitter = splitter
            toggle_btn._plot_widget = plot_widget
            toggle_btn._table_container = container
            self._toggle_btns.append(toggle_btn)
            toggle_btn.toggled.connect(
                lambda checked, btn=toggle_btn: self._on_mode_toggle(btn, checked))

            self.addTab(tab_page, title)
    
    def _on_mode_toggle(self, btn, checked):
        """Переключение: checked=таблица, unchecked=график. Глобально для всех вкладок."""
        self._table_mode = checked
        for b in self._toggle_btns:
            b.blockSignals(True)
            b.setChecked(checked)
            b.blockSignals(False)
            if checked:
                b.setText("📋 Таблица")
            else:
                b.setText("📊 График")
            container = b._table_container
            plot = b._plot_widget
            splitter = b._splitter
            if checked:
                plot.hide()
                container.show()
                splitter.setStretchFactor(0, 0)
                splitter.setStretchFactor(1, 1)
            else:
                plot.show()
                container.hide()
                splitter.setStretchFactor(0, 1)
                splitter.setStretchFactor(1, 0)

    def _set_table(self, key, table):
        """Replace the table in a container."""
        container = self._table_containers[key]
        layout = container.layout()
        _clear_layout(layout)
        if table:
            layout.addWidget(table)
    
    def update_parax(self, parax_dict, fno, epd, sys=None):
        """Update paraxial table. sys needed for multi-wavelength computation."""
        self._parax_data = parax_dict or {}
        self._fno = fno
        self._epd = epd
        self._parax_sys = sys
        self._update_parax_table()

    def update_seidel(self, seidel_dict):
        """Update Seidel sums table."""
        self._seidel_data = seidel_dict or {}
        self._update_seidel_table()

    def _update_parax_table(self):
        """Build paraxial table — multi-wavelength columns for s, s', s'G, V, sP, sP'."""
        import copy
        from optics_engine import paraxial_trace
        parax = self._parax_data
        if not parax:
            self._set_table('parax', _make_table(
                ["Параметр", "Значение"], [["—", "Нет данных"]], [120, 120]))
            return

        sys = getattr(self, '_parax_sys', None)
        # Compute paraxial for each wavelength
        wl_labels = []
        parax_by_wl = {}
        if sys and sys.wavelengths:
            for wl in sys.wavelengths:
                label = wl.name if wl.name else f"{wl.value:.4f}"
                try:
                    sys_wl = copy.deepcopy(sys)
                    sys_wl.wavelengths = [type(wl)(wl.value, 1.0, wl.name)]
                    parax_by_wl[label] = paraxial_trace(sys_wl)
                    wl_labels.append(label)
                except Exception:
                    pass
        if not wl_labels:
            wl_labels = ['d']
            parax_by_wl['d'] = parax
        n_wl = len(wl_labels)

        # Table 1: Cardinal params (same for all λ) — 2 columns
        common_rows = [
            ["f'", f"{parax.get('focal_length', 0):.4f}"],
            ["FFD", f"{parax.get('front_focal_distance', 0):.4f}"],
            ["sF", f"{parax.get('sF', 0):.4f}"],
            ["sF'", f"{parax.get('sF_prime', 0):.4f}"],
            ["sH", f"{parax.get('sH', 0):.4f}"],
            ["sH'", f"{parax.get('sH_prime', 0):.4f}"],
            ["L", f"{parax.get('L', 0):.4f}"],
            ["f/#", f"{self._fno:.2f}"],
            ["D вх.зрачка", f"{self._epd:.4f}"],
        ]
        table1 = _make_table(["Кардинальные", "Значение"], common_rows, [90, 80])
        table1.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Table 2: Per-wavelength params — columns = wavelengths
        per_wl_keys = [
            ("s' (мм)", 'back_focal_distance'),
            ("s' (дптр)", 'back_focal_distance'),  # will convert to diopters
            ("s'G (мм)", 'back_focal_distance'),
            ("V", 'V'),
            ("sP (мм)", 'sP'),
            ("sP' (мм)", 'sP_prime'),
        ]
        wl_headers = ["Параметр"] + wl_labels
        wl_rows = []
        for name, key in per_wl_keys:
            vals = []
            for wl in wl_labels:
                p = parax_by_wl.get(wl, {})
                v = p.get(key, 0)
                if 'дптр' in name and v:
                    v = 1000.0 / v if abs(v) > 1e-10 else 0
                vals.append(f"{v:.4f}" if v is not None else "—")
            wl_rows.append([name] + vals)
        table2 = _make_table(wl_headers, wl_rows, [60] + [55] * n_wl)
        table2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Combine in horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(table1)
        splitter.addWidget(table2)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self._set_table('parax', splitter)

    def _update_seidel_table(self):
        """Build Seidel sums table from cached data."""
        seidel = self._seidel_data
        if not seidel:
            self._set_table('seidel', _make_table(
                ["Сумма", "Значение"], [["—", "Нет данных"]], [120, 120]))
            return
        rows = [
            ("SI — сферическая", f"{seidel.get('SI', 0):.6e}"),
            ("SII — кома", f"{seidel.get('SII', 0):.6e}"),
            ("SIII — астигматизм", f"{seidel.get('SIII', 0):.6e}"),
            ("SIV — кривизна", f"{seidel.get('SIV', 0):.6e}"),
            ("SV — дисторсия", f"{seidel.get('SV', 0):.6e}"),
        ]
        table = _make_table(["Сумма", "Значение"], rows, [130, 100])
        self._set_table('seidel', table)

    def get_defocus_offset(self) -> float:
        """Get current defocus offset from settings widget."""
        return self.defocus_spin.value() if hasattr(self, 'defocus_spin') else 0.0

    def get_azimuth(self) -> float:
        """Get current azimuth angle from settings."""
        return self.azimuth_spin.value() if hasattr(self, 'azimuth_spin') else 0.0

    def apply_precomputed(self, sys, data):
        """Apply precomputed analysis data to all widgets. GUI thread only."""
        d = data

        # ── Set widget data attributes ──
        # Spot diagram
        self.spot_diagram.spots_mono = d.get('spot_mono', [])
        self.spot_diagram.rms = d.get('spot_rms', 0)
        self.spot_diagram._wl_cache = d.get('wl_list', [0.588])
        self.spot_diagram.spots_poly = d.get('spot_poly', [])
        self.spot_diagram.poly_rms = d.get('poly_rms', 0)
        self.spot_diagram.update()

        # Aberration graphs
        for widget in [self.transverse, self.longitudinal, self.wavefront]:
            widget.fan_data = d.get('fan_data', {})
            widget.isoplanatism_data = d.get('isoplanatism_data', {})
            widget.oblique_data = d.get('oblique_data')
            widget.update()

        # MTF
        self.mtf.geo_mtf = d.get('geo_mtf')
        self.mtf.diff_mtf = d.get('diff_mtf')
        self.mtf.poly_mtf = d.get('poly_mtf')
        self.mtf.diff_limited_mtf = d.get('diff_limited_mtf')
        self.mtf.update()

        # Field aberration widgets
        fd = d.get('field_data')
        self.distortion.field_data = fd
        self.distortion.update()
        self.astigmatism.field_data = fd
        self.astigmatism.update()
        self.coma.field_data = fd
        self.coma.update()

        # Focus curve
        curve = d.get('focus_curve')
        self.focus_curve.curve_data = curve
        if curve:
            best = max(curve, key=lambda p: p[1])
            self.focus_curve.best_defocus = best[0]
            self.focus_curve.best_mtf = best[1]
        self.focus_curve.update()

        # PSF
        self.psf_w.psf_data = d.get('psf_data')
        self.psf_w.dx = d.get('psf_dx')
        self.psf_w.dy = d.get('psf_dy')
        self.psf_w.update()

        # LSF
        self.lsf_w.lsf_tan = d.get('lsf_tan')
        self.lsf_w.lsf_sag = d.get('lsf_sag')
        self.lsf_w.axis = d.get('lsf_ax')
        self.lsf_w.update()

        # ESF
        self.esf_w.x_um = d.get('esf_x')
        self.esf_w.esf = d.get('esf_y')
        self.esf_w.update()

        # ENC
        self.enc_w.r_um = d.get('enc_r')
        self.enc_w.enc = d.get('enc_e')
        self.enc_w.update()

        # PTF
        self.ptf_w.ptf_data = d.get('ptf_data')
        self.ptf_w.update()

        # Heatmap
        self.heatmap_w.heatmap = d.get('heatmap')
        self.heatmap_w.x_range = d.get('heatmap_x_range', (0, 0))
        self.heatmap_w.y_range = d.get('heatmap_y_range', (0, 0))
        self.heatmap_w.centroid_x = d.get('heatmap_centroid_x', 0)
        self.heatmap_w.centroid_y = d.get('heatmap_centroid_y', 0)
        self.heatmap_w.max_density = d.get('heatmap_max_density', 0)
        self.heatmap_w.num_points = d.get('heatmap_num_points', 0)
        self.heatmap_w.update()

        # Beam geometry
        self.beam_geom.beam_data = d.get('beam_data')
        self.beam_geom.update()

        # Chief ray
        self.chief_ray.chief_data = d.get('chief_data')
        self.chief_ray.update()

        # Zernike
        self.zernike_w.coeffs = d.get('zernike_coeffs', [])
        self.zernike_w.chromatic_data = d.get('zernike_chromatic')
        self.zernike_w.update()

        # Wavefront map
        self.wavefront_map_w.wf_data = d.get('wf_data')
        self.wavefront_map_w.coords = d.get('wf_coords')
        self.wavefront_map_w.mask = d.get('wf_mask')
        self.wavefront_map_w.update()

        # WF RMS vs field
        self.wf_rms_field_w.field_data = d.get('wf_rms_field')
        self.wf_rms_field_w.update()

        # Focus diagrams
        self.focus_diagrams.spots_by_defocus = d.get('focus_diag_data', {})
        self.focus_diagrams.max_range = d.get('focus_diag_max_range', 0.001)
        self.focus_diagrams.update()

        # PSF 3D
        self.psf_3d_w.x_coords = d.get('psf3d_x')
        self.psf_3d_w.y_coords = d.get('psf3d_y')
        self.psf_3d_w.Z = d.get('psf3d_Z')
        self.psf_3d_w.update()

        # Bar target
        self.bar_target_w.x_um = d.get('bar_x')
        self.bar_target_w.ideal = d.get('bar_ideal')
        self.bar_target_w.blurred = d.get('bar_blurred')
        self.bar_target_w.mtf_table = d.get('bar_mtf_table')
        self.bar_target_w.update()

        # ── Build tables from precomputed data ──
        self._build_tables_precomputed(sys, d)

    def _build_tables_precomputed(self, sys, d):
        """Build all tables from precomputed data. GUI thread only."""
        wl = d.get('wl', 0.58756)
        wl_list = d.get('wl_list', [0.58756])

        # ── Spot table ──
        rows = []
        spots_mono = d.get('spot_mono', [])
        rms = d.get('spot_rms', 0)
        rms_xy = d.get('spot_rms_xy', {})
        max_r = max((math.sqrt(dx**2 + dy**2) for dx, dy in spots_mono), default=0)
        rows.append(["0.0", f"{wl:.4f}", str(len(spots_mono)),
                     f"{rms:.4f}", f"{rms_xy.get('rms_x', 0):.4f}",
                     f"{rms_xy.get('rms_y', 0):.4f}",
                     f"{rms_xy.get('centroid_y', 0):.4f}", f"{max_r:.4f}"])
        if len(wl_list) > 1:
            poly_spots = d.get('spot_poly', [])
            poly_rms = d.get('poly_rms', 0)
            poly_rms_xy = d.get('poly_rms_xy', {})
            poly_max = max((math.sqrt(dx**2 + dy**2) for dx, dy, _ in poly_spots), default=0)
            rows.append(["0.0", "\u043f\u043e\u043b\u0438\u0445\u0440.", str(len(poly_spots)),
                         f"{poly_rms:.4f}", f"{poly_rms_xy.get('rms_x', 0):.4f}",
                         f"{poly_rms_xy.get('rms_y', 0):.4f}",
                         f"{poly_rms_xy.get('centroid_y', 0):.4f}", f"{poly_max:.4f}"])
        self._set_table('spot', _make_table(
            ["\u041f\u043e\u043b\u0435", "\u03bb, \u043c\u043a\u043c", "\u041b\u0443\u0447\u0435\u0439", "RMS, \u043c\u043c",
             "RMS_X", "RMS_Y", "Y\u0446\u044d", "\u041c\u0430\u043a\u0441 R, \u043c\u043c"],
            rows, [35, 55, 40, 60, 60, 60, 60, 60]))

        # ── Transverse / Longitudinal / Wavefront tables ──
        fan_primary = d.get('fan_data', {}).get(wl, [])
        for key, val_key in [('transverse', 'dy'), ('longitudinal', 'ds'), ('wavefront', 'wave')]:
            rows_fan = []
            step = max(1, len(fan_primary) // 13)
            for i in range(0, len(fan_primary), step):
                r = fan_primary[i]
                if r['success']:
                    if val_key == 'dy':
                        rows_fan.append([f"{r['pupil_y']:.4f}", f"{r['dy']*1000:.5f}"])
                    elif val_key == 'ds':
                        rows_fan.append([f"{r['pupil_y']:.4f}", f"{r['ds']:.5f}"])
                    else:
                        rows_fan.append([f"{r['pupil_y']:.4f}", f"{r['wave']:.5f}"])
            if val_key == 'dy':
                self._set_table(key, _make_table(
                    ["\u0412\u044b\u0441\u043e\u0442\u0430 \u043b\u0443\u0447\u0430", "\u0394y' (\u043c\u043a\u043c)"],
                    rows_fan, [100, 100]))
            elif val_key == 'ds':
                self._set_table(key, _make_table(
                    ["\u0412\u044b\u0441\u043e\u0442\u0430 \u043b\u0443\u0447\u0430", "\u0394s' (\u043c\u043c)"],
                    rows_fan, [100, 100]))
            else:
                self._set_table(key, _make_table(
                    ["\u0412\u044b\u0441\u043e\u0442\u0430 \u043b\u0443\u0447\u0430", "W (\u03bb)"],
                    rows_fan, [100, 100]))

        # ── MTF table ──
        geo_mtf = d.get('geo_mtf')
        diff_mtf = d.get('diff_mtf')
        diff_ltd = d.get('diff_limited_mtf')
        rows_mtf = []
        if geo_mtf:
            for i, (freq, mtf_t, mtf_s) in enumerate(geo_mtf):
                dt = ds = dl = ""
                if diff_mtf and i < len(diff_mtf['freqs']):
                    dt = f"{diff_mtf['mtf_tangential'][i]:.4f}"
                    ds = f"{diff_mtf['mtf_sagittal'][i]:.4f}" if i < len(diff_mtf.get('mtf_sagittal', [])) else ""
                if diff_ltd and i < len(diff_ltd['freqs']):
                    dl = f"{diff_ltd['mtf'][i]:.4f}"
                rows_mtf.append([f"{freq:.2f}", f"{mtf_t:.4f}", f"{mtf_s:.4f}", dt, ds, dl, ""])
        self._set_table('mtf', _make_table(
            ["\u0427\u0430\u0441\u0442\u043e\u0442\u0430", "\u0413.\u043c\u0435\u0440.", "\u0413.\u0441\u0430\u0433.",
             "\u0414.\u043c\u0435\u0440.", "\u0414.\u0441\u0430\u0433.", "\u0411\u0435\u0437\u0430\u0431.", "\u041f\u043e\u043b\u0438\u0445\u0440."],
            rows_mtf, [45, 48, 48, 48, 48, 48, 45]))

        # ── Distortion / Astigmatism / Coma tables ──
        field_data = d.get('field_data', [])
        rows_dist = []
        rows_astig = []
        rows_coma = []
        for dd in field_data:
            fy = dd['field_y']
            if dd.get('distortion') is not None:
                dist_pct = dd['distortion']
                dist_mm = fy * dist_pct / 100.0 if abs(fy) > 1e-10 else 0.0
                rows_dist.append([f"{fy:.4f}", f"{dist_pct:.5f}", f"{dist_mm:.5f}"])
            if dd.get('z_m') is not None:
                dz = dd['z_m'] - dd['z_s']
                rows_astig.append([f"{fy:.4f}", f"{dd['z_m']:.5f}",
                                   f"{dd['z_s']:.5f}", f"{dz:.5f}"])
            if dd.get('coma') is not None:
                coma_y = dd['coma'] * 1000
                rows_coma.append([f"{fy:.4f}", "0.0000", f"{coma_y:.5f}"])
        self._set_table('distortion', _make_table(
            ["\u041f\u043e\u043b\u0435 Y (\u043c\u043c)", "\u0414\u0438\u0441\u0442. %", "\u0414\u0438\u0441\u0442. (\u043c\u043c)"],
            rows_dist, [75, 70, 75]))
        self._set_table('astigmatism', _make_table(
            ["\u041f\u043e\u043b\u0435 Y (\u043c\u043c)", "Z'm (\u043c\u043c)", "Z's (\u043c\u043c)", "\u0394Z (\u043c\u043c)"],
            rows_astig, [70, 65, 65, 65]))
        self._set_table('coma', _make_table(
            ["\u041f\u043e\u043b\u0435 Y (\u043c\u043c)", "\u041a\u043e\u043c\u0430 X (\u043c\u043a\u043c)", "\u041a\u043e\u043c\u0430 Y (\u043c\u043a\u043c)"],
            rows_coma, [75, 75, 75]))

        # ── Focus table ──
        curve = d.get('focus_curve')
        if curve:
            best_defocus = max(curve, key=lambda p: p[1])[0]
            rows_fc = []
            step = max(1, len(curve) // 15)
            for i in range(0, len(curve), step):
                dd_f, mt = curve[i][0], curve[i][1]
                ms = curve[i][2] if len(curve[i]) > 2 else 0.0
                rows_fc.append([f"{dd_f:+.4f}", f"{mt:.4f}", f"{ms:.4f}"])
            table = _make_table(
                ["\u0394defocus (\u043c\u043c)", "MTF \u043c\u0435\u0440.", "MTF \u0441\u0430\u0433."],
                rows_fc, [80, 70, 70])
            for i, rd in enumerate(rows_fc):
                if abs(float(rd[0]) - best_defocus) < 0.001:
                    font = QFont("Courier", 9)
                    font.setBold(True)
                    for j in range(table.columnCount()):
                        item = table.item(i, j)
                        if item:
                            item.setFont(font)
                    break
            self._set_table('focus', table)
        else:
            self._set_table('focus', None)

        # ── PSF table ──
        rows_psf = [["\u03bb \u043f\u0435\u0440\u0432.", f"{wl:.4f} \u043c\u043a\u043c"]]
        psf_data = d.get('psf_data')
        psf_dx = d.get('psf_dx')
        psf_dy = d.get('psf_dy')
        if psf_data is not None and psf_dx is not None:
            pix_size = (psf_dx.max() - psf_dx.min()) / len(psf_dx) if len(psf_dx) > 1 else 0
            max_intens = psf_data.max()
            cy, cx = np.unravel_index(np.argmax(psf_data), psf_data.shape)
            center_x = psf_dx[cx] if cx < len(psf_dx) else 0
            center_y = psf_dy[cy] if cy < len(psf_dy) else 0
            row_c = psf_data[cy, :]
            col_c = psf_data[:, cx]
            half_max = max_intens / 2
            try:
                w_mer = (psf_dx.max() - psf_dx.min()) / len(psf_dx) * np.sum(row_c > half_max)
                w_sag = (psf_dy.max() - psf_dy.min()) / len(psf_dy) * np.sum(col_c > half_max)
            except Exception:
                w_mer = w_sag = 0
            rows_psf.append(["\u0420\u0430\u0437\u043c. \u043f\u0438\u043a\u0441.", f"{pix_size:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u041c\u0430\u043a\u0441. \u0438\u043d\u0442\u0435\u043d\u0441.", f"{max_intens:.5f}"])
            rows_psf.append(["\u0426\u0435\u043d\u0442\u0440 X", f"{center_x:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u0426\u0435\u043d\u0442\u0440 Y", f"{center_y:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u0428\u0438\u0440. \u043c\u0435\u0440.", f"{w_mer:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u0428\u0438\u0440. \u0441\u0430\u0433.", f"{w_sag:.4f} \u043c\u043a\u043c"])
        else:
            rows_psf.append(["\u041e\u0448\u0438\u0431\u043a\u0430", "\u2014"])
        self._set_table('psf', _make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_psf, [100, 120]))

        # ── LSF table ──
        lsf_tan = d.get('lsf_tan')
        lsf_ax = d.get('lsf_ax')
        lsf_sag = d.get('lsf_sag')
        if lsf_tan is not None and lsf_ax is not None:
            rows_lsf = []
            n = len(lsf_ax)
            step = max(1, n // 15)
            for i in range(0, n, step):
                rows_lsf.append([f"{lsf_ax[i]:.4f}", f"{lsf_tan[i]:.5f}", f"{lsf_sag[i]:.5f}"])
            self._set_table('lsf', _make_table(
                ["\u041a\u043e\u043e\u0440\u0434. (\u043c\u043a\u043c)", "\u041c\u0435\u0440\u0438\u0434. LSF", "\u0421\u0430\u0433\u0438\u0442. LSF"],
                rows_lsf, [75, 75, 75]))
        else:
            self._set_table('lsf', None)

        # ── ESF table ──
        esf_x = d.get('esf_x')
        esf_y = d.get('esf_y')
        if esf_x is not None:
            rows_esf = []
            n = len(esf_x)
            step = max(1, n // 15)
            for i in range(0, n, step):
                rows_esf.append([f"{esf_x[i]:.4f}", f"{esf_y[i]:.5f}"])
            self._set_table('esf', _make_table(
                ["\u041a\u043e\u043e\u0440\u0434. (\u043c\u043a\u043c)", "ESF"], rows_esf, [90, 90]))
        else:
            self._set_table('esf', None)

        # ── ENC table ──
        enc_r = d.get('enc_r')
        enc_e = d.get('enc_e')
        if enc_r is not None:
            rows_enc = []
            n = len(enc_r)
            step = max(1, n // 13)
            for i in range(0, n, step):
                rows_enc.append([f"{enc_r[i]*2:.4f}", f"{enc_e[i]*100:.2f}"])
            for pct in [0.5, 0.8, 0.9]:
                idx = np.searchsorted(enc_e, pct)
                if idx < len(enc_r):
                    dd_enc = enc_r[idx] * 2
                    rows_enc.append([f"D@{int(pct*100)}%={dd_enc:.4f}", f"{pct*100:.2f}%"])
            self._set_table('enc', _make_table(
                ["D \u043a\u0440\u0443\u0433\u0430 (\u043c\u043a\u043c)", "\u041f\u043e\u043b\u0438\u0445\u0440. %"],
                rows_enc, [110, 80]))
        else:
            self._set_table('enc', None)

        # ── PTF table ──
        ptf_data = d.get('ptf_data')
        if ptf_data is not None:
            freqs = ptf_data['freqs']
            ptf_t = ptf_data['ptf_tangential']
            ptf_s = ptf_data['ptf_sagittal']
            rows_ptf = []
            step = max(1, len(freqs) // 15)
            for i in range(0, len(freqs), step):
                rows_ptf.append([f"{freqs[i]:.2f}", f"{ptf_t[i]:.5f}", f"{ptf_s[i]:.5f}"])
            self._set_table('ptf', _make_table(
                ["\u0427\u0430\u0441\u0442\u043e\u0442\u0430 (\u043b/\u043c\u043c)", "PTF \u043c\u0435\u0440. (\u0440\u0430\u0434)", "PTF \u0441\u0430\u0433. (\u0440\u0430\u0434)"],
                rows_ptf, [75, 80, 80]))
        else:
            self._set_table('ptf', None)

        # ── Heatmap table ──
        rows_hm = [["\u0414\u043b\u0438\u043d\u0430 \u0432\u043e\u043b\u043d\u044b", f"{wl:.4f} \u043c\u043a\u043c"],
                   ["\u0421\u0435\u0442\u043a\u0430", f"100\u00d7100"]]
        if d.get('heatmap') is not None:
            xr = d['heatmap_x_range']
            yr = d['heatmap_y_range']
            x_span = (xr[1] - xr[0]) * 1000
            y_span = (yr[1] - yr[0]) * 1000
            rows_hm.append(["\u0420\u0430\u0437\u043c\u0435\u0440 \u043f\u043e\u043b\u044f", f"{x_span:.4f}\u00d7{y_span:.4f} \u043c\u043a\u043c"])
            rows_hm.append(["\u041f\u0438\u043a\u0441\u0435\u043b\u0435\u0439 \u0441 \u0434\u0430\u043d\u043d\u044b\u043c\u0438", str(d.get('heatmap_num_points', 0))])
            rows_hm.append(["\u041c\u0430\u043a\u0441. \u043f\u043b\u043e\u0442\u043d\u043e\u0441\u0442\u044c", f"{d.get('heatmap_max_density', 0):.4f}"])
            rows_hm.append(["\u0426\u0435\u043d\u0442\u0440\u043e\u0438\u0434 X", f"{d.get('heatmap_centroid_x', 0)*1000:.4f} \u043c\u043a\u043c"])
            rows_hm.append(["\u0426\u0435\u043d\u0442\u0440\u043e\u0438\u0434 Y", f"{d.get('heatmap_centroid_y', 0)*1000:.4f} \u043c\u043a\u043c"])
        else:
            rows_hm.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        self._set_table('heatmap', _make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_hm, [130, 130]))

        # ── Beam table ──
        beam_data = d.get('beam_data', [])
        rows_beam = []
        for bd in beam_data:
            rows_beam.append([f"{bd['field_y']:.4f}", f"{bd['Ay']:.4f}", f"{bd['Ay_prime']:.4f}",
                              f"{bd['vignetting_upper']:.4f}", f"{bd['vignetting_lower']:.4f}",
                              f"{bd['relative_illumination']:.4f}"])
        self._set_table('beam', _make_table(
            ["\u041f\u043e\u043b\u0435", "Ay", "Ay'", "\u0412\u0438\u043d\u044c\u0435\u0442.\u2191",
             "\u0412\u0438\u043d\u044c\u0435\u0442.\u2193", "\u0421\u0432\u0435\u0442\u043e\u0440\u0430\u0441\u043f\u0440."],
            rows_beam, [45, 50, 50, 55, 55, 60]))

        # ── Chief ray table ──
        chief_data = d.get('chief_data', [])
        rows_chief = []
        for cd in chief_data:
            rows_chief.append([f"{cd['field_y']:.4f}", f"{cd['distortion_abs']:.6f}",
                               f"{cd['distortion_rel']:.6f}", f"{cd['Zm']:.6f}",
                               f"{cd['Zs']:.6f}", f"{cd['lateral_color']:.6f}"])
        self._set_table('chief', _make_table(
            ["\u041f\u043e\u043b\u0435", "\u0414\u0438\u0441\u0442.\u0430\u0431\u0441", "\u0414\u0438\u0441\u0442.%",
             "Z'm", "Z's", "\u0425\u0440.\u0443\u0432\u0435\u043b."],
            rows_chief, [45, 60, 55, 60, 60, 60]))

        # ── Zernike table ──
        zernike_coeffs = d.get('zernike_coeffs', [])
        zernike_chromatic = d.get('zernike_chromatic')
        if zernike_chromatic and self.zernike_w._show_chromatic:
            wl_keys = [k for k in zernike_chromatic if not k.startswith('delta_')]
            if wl_keys:
                headers = ["\u041f\u043e\u043b\u0438\u043d\u043e\u043c"] + wl_keys
                rows_zk = []
                for idx, (val, name) in enumerate(zernike_coeffs):
                    row = [name]
                    for key in wl_keys:
                        if key in zernike_chromatic:
                            for c, n in zernike_chromatic[key]:
                                if n == name:
                                    row.append(f"{c:+.6f}")
                                    break
                            else:
                                row.append("\u2014")
                        else:
                            row.append("\u2014")
                    rows_zk.append(row)
                delta_headers = [k for k in ['delta_F-d', 'delta_C-d'] if k in zernike_chromatic]
                for delta_key in delta_headers:
                    for idx, (val, name) in enumerate(zernike_chromatic[delta_key]):
                        if idx < len(rows_zk):
                            rows_zk[idx].append(f"{val:+.6f}")
                headers.extend(delta_headers)
                self._set_table('zernike', _make_table(
                    headers, rows_zk, [80] + [70] * (len(headers) - 1)))
                return  # early return for chromatic path
        # Normal Zernike
        rows_z = []
        for val, name in zernike_coeffs:
            rows_z.append([name, f"{val:+.6f}"])
        self._set_table('zernike', _make_table(
            ["\u041f\u043e\u043b\u0438\u043d\u043e\u043c", "\u041a\u043e\u044d\u0444\u0444. (\u03bb)"],
            rows_z, [120, 90]))

        # ── Wavefront map table ──
        wf_data = d.get('wf_data')
        wf_mask = d.get('wf_mask')
        rows_wf = [["\u03bb \u043f\u0435\u0440\u0432.", f"{wl:.4f} \u043c\u043a\u043c"]]
        if wf_data is not None and wf_mask is not None:
            valid = wf_data[wf_mask > 0]
            if valid.size > 0:
                rows_wf.append(["PV", f"{valid.max()-valid.min():.5f} \u03bb"])
                rows_wf.append(["RMS", f"{np.sqrt(np.mean(valid**2)):.5f} \u03bb"])
                rows_wf.append(["\u041c\u0438\u043d", f"{valid.min():.5f} \u03bb"])
                rows_wf.append(["\u041c\u0430\u043a\u0441", f"{valid.max():.5f} \u03bb"])
                rows_wf.append(["\u0421\u0435\u0442\u043a\u0430", f"{wf_data.shape[0]}\u00d7{wf_data.shape[1]}"])
            else:
                rows_wf.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        else:
            rows_wf.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        self._set_table('wfmap', _make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_wf, [100, 120]))

        # ── Focus diagrams table ──
        fd_data = d.get('focus_diag_data', {})
        if fd_data:
            rows_fd = []
            for label in ["\u043d\u043e\u043c\u0438\u043d\u0430\u043b", "+DS'", "-DS'", "+2DS'", "-2DS'"]:
                if label in fd_data:
                    spots, rms_info, df = fd_data[label]
                    rows_fd.append([label, f"{df:+.4f}", str(len(spots)),
                                    f"{rms_info['rms_total']:.5f}",
                                    f"{rms_info['rms_x']:.4f}",
                                    f"{rms_info['rms_y']:.4f}"])
            self._set_table('focus_diag', _make_table(
                ["\u041f\u043e\u0437.", "\u0394z (\u043c\u043c)", "\u041b\u0443\u0447\u0435\u0439", "RMS", "RMS_X", "RMS_Y"],
                rows_fd, [55, 65, 40, 65, 65, 65]))
        else:
            self._set_table('focus_diag', None)

        # ── PSF 3D table ──
        rows_p3 = [["\u03bb \u043f\u0435\u0440\u0432.", f"{wl:.4f} \u043c\u043a\u043c"]]
        psf3d_Z = d.get('psf3d_Z')
        psf3d_x = d.get('psf3d_x')
        if psf3d_Z is not None:
            rows_p3.append(["\u041c\u0430\u043a\u0441.", f"{psf3d_Z.max():.5f}"])
            rows_p3.append(["\u0420\u0430\u0437\u043c\u0435\u0440", f"{psf3d_Z.shape[0]}\u00d7{psf3d_Z.shape[1]}"])
            if psf3d_x is not None:
                x_span = psf3d_x.max() - psf3d_x.min()
                rows_p3.append(["\u041f\u043e\u043b\u0435 X", f"{x_span:.4f} \u043c\u043a\u043c"])
        else:
            rows_p3.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        self._set_table('psf3d', _make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_p3, [100, 120]))

        # ── WF RMS vs field table ──
        wf_rms = d.get('wf_rms_field')
        if wf_rms and wf_rms[0]:
            field_vals, rms_full, rms_no_def, rms_no_tilt = wf_rms
            rows_wr = []
            def _fmt(v):
                return f"{v:.5f}" if v == v else "\u2014"
            for f, r_f, r_d, r_t in zip(field_vals, rms_full, rms_no_def, rms_no_tilt):
                rows_wr.append([f"{f:.2f}\u00b0", _fmt(r_f), _fmt(r_d), _fmt(r_t)])
            self._set_table('wf_rms_field', _make_table(
                ["\u041f\u043e\u043b\u0435", "\u0421\u041a\u0412 (\u03bb)", "\u0421\u041a\u0412-\u0434\u0435\u0444", "\u0421\u041a\u0412-\u0442\u0438\u043b\u044c\u0442"],
                rows_wr, [55, 75, 75, 75]))
        else:
            self._set_table('wf_rms_field', _make_table(
                ["\u041f\u043e\u043b\u0435", "\u0421\u041a\u0412 (\u03bb)"],
                [["\u2014", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"]], [60, 100]))

        # ── Bar target table ──
        bar_mtf = d.get('bar_mtf_table')
        if bar_mtf:
            rows_bt = []
            for entry in bar_mtf:
                rows_bt.append([f"{entry['freq']}", f"{entry['contrast_ideal']:.4f}",
                                f"{entry['contrast_real']:.4f}", f"{entry['mtf']:.4f}"])
            self._set_table('bar_target', _make_table(
                ["\u0427\u0430\u0441\u0442\u043e\u0442\u0430 (\u043b/\u043c\u043c)", "\u041a\u043e\u043d\u0442\u0440. \u0438\u0434\u0435\u0430\u043b",
                 "\u041a\u043e\u043d\u0442\u0440. \u0440\u0435\u0430\u043b.", "MTF"],
                rows_bt, [80, 80, 80, 80]))
        else:
            self._set_table('bar_target', None)

    def apply_results(self, sys, data):
        """Apply pre-computed results from background thread. GUI thread only."""
        if not data:
            self.analyze(sys)
            return

        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756

        # Parax/Seidel
        if 'parax' in data:
            parax = data['parax']
            fno = parax.get('f_number', 0)
            epd = parax.get('entrance_pupil_diameter', 0)
            if fno == 0:
                efl = parax.get('focal_length', 0)
                epd = sys.aperture_value if sys.aperture_value > 0 else efl / 4.0
                fno = efl / epd if epd > 0 else 0
            self.update_parax(parax, fno, epd, sys=sys)
        if 'seidel' in data:
            self.update_seidel(data['seidel'])

        # Spot
        if 'spots_mono' in data:
            self.spot_diagram.spots_mono = data['spots_mono']
            self.spot_diagram.rms = data['rms']
            self.spot_diagram._wl_cache = [w.value for w in sys.wavelengths]
            self.spot_diagram.spots_poly = data.get('spots_poly', [])
            self.spot_diagram.poly_rms = data.get('poly_rms', data['rms'])
            self.spot_diagram.update()

        # Aberration fans — all wavelengths
        if 'fan_data' in data:
            all_fans = data['fan_data']  # {wl: [fan_results]}
            wl_keys = list(all_fans.keys())
            isoplanatism = data.get('isoplanatism', {})
            for key, widget in [('transverse', self.transverse), ('longitudinal', self.longitudinal), ('wavefront', self.wavefront)]:
                widget.fan_data = all_fans  # All wavelengths
                widget._wl_cache = wl_keys
                if key == 'transverse' and isoplanatism:
                    widget.isoplanatism_data = isoplanatism
                if key == 'transverse':
                    widget.val_key = 'dy'
                    widget.scale = 1000
                elif key == 'longitudinal':
                    widget.val_key = 'ds'
                    widget.scale = 1
                else:
                    widget.val_key = 'wave'
                    widget.scale = 1
                widget.update()

        # MTF
        if 'geo_mtf' in data:
            self.mtf.geo_mtf = data['geo_mtf']
            self.mtf.diff_mtf = data.get('diff_mtf')
            self.mtf.diff_limited_mtf = data.get('diff_ltd')
            self.mtf.update()

        # Field aberrations -> distortion, astigmatism, coma
        if 'field_aberr' in data:
            fa = data['field_aberr']
            self.distortion.field_data = fa
            self.distortion.update()
            self.astigmatism.field_data = fa
            self.astigmatism.update()
            self.coma.field_data = fa
            self.coma.update()

        # Focus curve
        if 'focus_curve' in data:
            self.focus_curve.curve_data = data['focus_curve']
            self.focus_curve.update()

        # PSF
        if data.get('psf_data') is not None:
            self.psf_w.psf_data, self.psf_w.dx, self.psf_w.dy = data['psf_data']
            self.psf_w.update()

        # LSF
        if data.get('lsf_t') is not None:
            self.lsf_w.lsf_tan = data['lsf_t']
            self.lsf_w.axis = data['lsf_ax1']
            self.lsf_w.lsf_sag = data['lsf_s']
            self.lsf_w.update()

        # ESF
        if data.get('esf_x') is not None:
            self.esf_w.x_um = data['esf_x']
            self.esf_w.esf = data['esf_y']
            self.esf_w.update()

        # ENC
        if data.get('enc_r') is not None:
            self.enc_w.r_um = data['enc_r']
            self.enc_w.enc = data['enc_e']
            self.enc_w.update()

        # PTF
        if data.get('ptf_data') is not None:
            self.ptf_w.ptf_data = data['ptf_data']
            self.ptf_w.update()

        # Beam & Chief
        if 'beam_data' in data:
            self.beam_geom.beam_data = data['beam_data']
            self.beam_geom.update()
        if 'chief_data' in data:
            self.chief_ray.chief_data = data['chief_data']
            self.chief_ray.update()

        # Zernike
        if 'zernike_coeffs' in data:
            self.zernike_w.coeffs = data['zernike_coeffs']
            self.zernike_w.chromatic = data.get('zernike_chromatic')
            self.zernike_w.update()

        # Wavefront map
        if data.get('wfmap') is not None:
            wf, coords, mask = data['wfmap']
            self.wavefront_map_w.wf_data = wf
            self.wavefront_map_w.coords = coords
            self.wavefront_map_w.mask = mask
            self.wavefront_map_w.update()

        # Focus diagrams
        if data.get('focus_diagrams'):
            self.focus_diagrams.spots_by_defocus = data['focus_diagrams']
            self.focus_diagrams.max_range = data.get('focus_diag_max', 1e-6)
            self.focus_diagrams.update()

        # Bar target
        if data.get('bar_x') is not None:
            self.bar_target_w.x_um = data['bar_x']
            self.bar_target_w.ideal = data['bar_ideal']
            self.bar_target_w.blurred = data['bar_blurred']
            self.bar_target_w.mtf_table = data.get('bar_mtf_table')
            self.bar_target_w.update()

        # Heatmap & PSF 3D & WF RMS field — still compute in GUI (lightweight or needs widget state)
        self.heatmap_w.set_data(sys)
        self.wf_rms_field_w.set_data(sys)
        self.psf_3d_w.set_data(sys)

        # Update tables
        self._update_spot_table(sys)
        self._update_transverse_table(sys)
        self._update_longitudinal_table(sys)
        self._update_wavefront_table(sys)
        self._update_mtf_table(sys)
        self._update_distortion_table(sys)
        self._update_astigmatism_table(sys)
        self._update_coma_table(sys)
        self._update_focus_table(sys)
        self._update_psf_table(sys)
        self._update_lsf_table(sys)
        self._update_esf_table(sys)
        self._update_enc_table(sys)
        self._update_ptf_table(sys)
        self._update_heatmap_table(sys)
        self._update_beam_table(sys)
        self._update_chief_table(sys)
        self._update_zernike_table(sys)
        self._update_wfmap_table(sys)
        self._update_wf_rms_field_table(sys)
        self._update_focus_diag_table(sys)
        self._update_psf3d_table(sys)
        self._update_bar_target_table(sys)

    def analyze(self, sys: OpticalSystem):
        defocus = self.get_defocus_offset()
        azimuth = self.get_azimuth()

        # Update parax/seidel from sys
        from optics_engine import paraxial_trace, seidel_aberrations
        parax = paraxial_trace(sys)
        efl = parax.get('focal_length', 0)
        epd = sys.aperture_value if sys.aperture_value > 0 else efl / 4.0
        fno = efl / epd if epd > 0 else 0
        self.update_parax(parax, fno, epd, sys=sys)
        self.update_seidel(seidel_aberrations(sys))

        self.spot_diagram.set_data(sys)
        self.transverse.set_data(sys, azimuth_deg=azimuth)
        self.longitudinal.set_data(sys, azimuth_deg=azimuth)
        self.wavefront.set_data(sys, azimuth_deg=azimuth)
        self.mtf.set_data(sys)
        self.distortion.set_data(sys)
        self.astigmatism.set_data(sys)
        self.coma.set_data(sys)
        self.focus_curve.set_data(sys)
        self.psf_w.set_data(sys)
        self.lsf_w.set_data(sys)
        self.esf_w.set_data(sys, defocus_offset=defocus)
        self.enc_w.set_data(sys)
        self.ptf_w.set_data(sys)
        self.heatmap_w.set_data(sys)
        self.beam_geom.set_data(sys)
        self.chief_ray.set_data(sys)
        self.zernike_w.set_data(sys, defocus_offset=defocus)
        self.wavefront_map_w.set_data(sys, defocus_offset=defocus)
        self.wf_rms_field_w.set_data(sys)
        self.focus_diagrams.set_data(sys)
        self.psf_3d_w.set_data(sys)
        self.bar_target_w.set_data(sys)

        # Update tables
        self._update_spot_table(sys)
        self._update_transverse_table(sys)
        self._update_longitudinal_table(sys)
        self._update_wavefront_table(sys)
        self._update_mtf_table(sys)
        self._update_distortion_table(sys)
        self._update_astigmatism_table(sys)
        self._update_coma_table(sys)
        self._update_focus_table(sys)
        self._update_psf_table(sys)
        self._update_lsf_table(sys)
        self._update_esf_table(sys)
        self._update_enc_table(sys)
        self._update_ptf_table(sys)
        self._update_heatmap_table(sys)
        self._update_beam_table(sys)
        self._update_chief_table(sys)
        self._update_zernike_table(sys)
        self._update_wfmap_table(sys)
        self._update_wf_rms_field_table(sys)
        self._update_focus_diag_table(sys)
        self._update_psf3d_table(sys)
        self._update_bar_target_table(sys)

        # Parax/Seidel tables (data must be set externally via update_parax/update_seidel)
        self._update_parax_table()
        self._update_seidel_table()
    
    # ===== Table builders =====
    
    def _update_spot_table(self, sys):
        wl_list = [w.value for w in sys.wavelengths] if sys.wavelengths else [0.58756]
        rows = []
        for field_y in [0.0]:  # On-axis
            for wl in wl_list:
                spots = compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=field_y)
                rms = compute_rms_spot(spots)
                rms_xy = compute_rms_spot_xy(spots)
                max_r = max((math.sqrt(dx**2+dy**2) for dx,dy in spots), default=0)
                rows.append([f"{field_y:.1f}", f"{wl:.4f}", str(len(spots)),
                             f"{rms:.4f}", f"{rms_xy['rms_x']:.4f}",
                             f"{rms_xy['rms_y']:.4f}", f"{rms_xy['centroid_y']:.4f}",
                             f"{max_r:.4f}"])
        # Полихроматическая
        if len(wl_list) > 1:
            poly_spots = compute_spot_diagram_polychromatic(sys, num_rays=40, field_y=0.0)
            poly_rms = compute_polychromatic_rms(sys, num_rays=40, field_y=0.0)
            poly_rms_xy = compute_rms_spot_xy([(dx, dy) for dx, dy, _ in poly_spots])
            poly_max = max((math.sqrt(dx**2+dy**2) for dx,dy,_ in poly_spots), default=0)
            rows.append(["0.0", "полихр.", str(len(poly_spots)),
                         f"{poly_rms:.4f}", f"{poly_rms_xy['rms_x']:.4f}",
                         f"{poly_rms_xy['rms_y']:.4f}", f"{poly_rms_xy['centroid_y']:.4f}",
                         f"{poly_max:.4f}"])
        self._set_table('spot', _make_table(
            ["Поле", "λ, мкм", "Лучей", "RMS, мм", "RMS_X", "RMS_Y", "Yцэ", "Макс R, мм"],
            rows, [35, 55, 40, 60, 60, 60, 60, 60]))
    
    def _update_transverse_table(self, sys):
        rows = []
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        fan = trace_aberration_fan(sys, wl, num_rays=30)
        # Sample 13 points evenly
        step = max(1, len(fan) // 13)
        for i in range(0, len(fan), step):
            r = fan[i]
            if r['success']:
                rows.append([f"{r['pupil_y']:.4f}", f"{r['dy']*1000:.5f}"])
        self._set_table('transverse', _make_table(
            ["Высота луча", "Δy' (мкм)"], rows, [100, 100]))
    
    def _update_longitudinal_table(self, sys):
        rows = []
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        fan = trace_aberration_fan(sys, wl, num_rays=30)
        step = max(1, len(fan) // 13)
        for i in range(0, len(fan), step):
            r = fan[i]
            if r['success']:
                rows.append([f"{r['pupil_y']:.4f}", f"{r['ds']:.5f}"])
        self._set_table('longitudinal', _make_table(
            ["Высота луча", "Δs' (мм)"], rows, [100, 100]))
    
    def _update_wavefront_table(self, sys):
        rows = []
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        fan = trace_aberration_fan(sys, wl, num_rays=30)
        step = max(1, len(fan) // 13)
        for i in range(0, len(fan), step):
            r = fan[i]
            if r['success']:
                rows.append([f"{r['pupil_y']:.4f}", f"{r['wave']:.5f}"])
        self._set_table('wavefront', _make_table(
            ["Высота луча", "W (λ)"], rows, [100, 100]))
    
    def _update_mtf_table(self, sys):
        rows = []
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        # Геометрическая MTF
        spots = compute_spot_diagram(sys, wl=wl, num_rays=40)
        geo_mtf = compute_geometric_mtf(spots, max_freq=100, num_freqs=20)
        
        diff_mtf = None
        try:
            from diffraction_mtf import compute_diffraction_mtf_quick
            diff_mtf = compute_diffraction_mtf_quick(sys, wl=wl)
        except Exception:
            pass
        
        diff_limited_mtf = None
        try:
            from diffraction_mtf import compute_diffraction_limited_mtf
            diff_limited_mtf = compute_diffraction_limited_mtf(sys, wl=wl)
        except Exception:
            pass
        
        for i, (freq, mtf_t, mtf_s) in enumerate(geo_mtf):
            d_t = ""
            d_s = ""
            dl = ""
            poly = ""
            if diff_mtf and i < len(diff_mtf['freqs']):
                d_t = f"{diff_mtf['mtf_tangential'][i]:.4f}"
                d_s = f"{diff_mtf['mtf_sagittal'][i]:.4f}" if i < len(diff_mtf.get('mtf_sagittal', [])) else ""
            if diff_limited_mtf and i < len(diff_limited_mtf['freqs']):
                dl = f"{diff_limited_mtf['mtf'][i]:.4f}"
            rows.append([f"{freq:.2f}", f"{mtf_t:.4f}", f"{mtf_s:.4f}", d_t, d_s, dl, poly])
        
        self._set_table('mtf', _make_table(
            ["Частота", "Г.мер.", "Г.саг.", "Д.мер.", "Д.саг.", "Безаб.", "Полихр."],
            rows, [45, 48, 48, 48, 48, 48, 45]))
    
    def _update_distortion_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        data = compute_field_aberrations(sys, wl=wl)
        rows = []
        for d in data:
            if d['distortion'] is not None:
                fy = d['field_y']
                dist_pct = d['distortion']
                dist_mm = fy * dist_pct / 100.0 if abs(fy) > 1e-10 else 0.0
                rows.append([f"{fy:.4f}", f"{dist_pct:.5f}", f"{dist_mm:.5f}"])
        self._set_table('distortion', _make_table(
            ["Поле Y (мм)", "Дист. %", "Дист. (мм)"], rows, [75, 70, 75]))
    
    def _update_astigmatism_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        data = compute_field_aberrations(sys, wl=wl)
        rows = []
        for d in data:
            if d['z_m'] is not None:
                dz = d['z_m'] - d['z_s']
                rows.append([f"{d['field_y']:.4f}", f"{d['z_m']:.5f}",
                             f"{d['z_s']:.5f}", f"{dz:.5f}"])
        self._set_table('astigmatism', _make_table(
            ["Поле Y (мм)", "Z'm (мм)", "Z's (мм)", "ΔZ (мм)"], rows, [70, 65, 65, 65]))
    
    def _update_coma_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        data = compute_field_aberrations(sys, wl=wl)
        rows = []
        for d in data:
            if d['coma'] is not None:
                coma_y = d['coma'] * 1000  # мм -> мкм
                rows.append([f"{d['field_y']:.4f}", "0.0000", f"{coma_y:.5f}"])
        self._set_table('coma', _make_table(
            ["Поле Y (мм)", "Кома X (мкм)", "Кома Y (мкм)"], rows, [75, 75, 75]))
    
    def _update_focus_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        curve = compute_focus_curve(sys, wl=wl, num_points=40,
                                    defocus_range=2.0, freq_lpmm=50.0,
                                    num_rays=25, field_y=0.0)
        if not curve:
            self._set_table('focus', None)
            return
        best_defocus = max(curve, key=lambda p: p[1])[0]
        rows = []
        step = max(1, len(curve) // 15)
        for i in range(0, len(curve), step):
            d, mt = curve[i][0], curve[i][1]
            ms = curve[i][2] if len(curve[i]) > 2 else 0.0
            rows.append([f"{d:+.4f}", f"{mt:.4f}", f"{ms:.4f}"])
        table = _make_table(
            ["Δdefocus (мм)", "MTF мер.", "MTF саг."], rows, [80, 70, 70])
        # Highlight best defocus row
        for i, row_data in enumerate(rows):
            if abs(float(row_data[0]) - best_defocus) < 0.001:
                font = QFont("Courier", 9)
                font.setBold(True)
                for j in range(table.columnCount()):
                    item = table.item(i, j)
                    if item:
                        item.setFont(font)
                break
        self._set_table('focus', table)
    
    def _update_psf_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        rows = [["λ перв.", f"{wl:.4f} мкм"]]
        try:
            psf_data, dx, dy = compute_psf(sys, wl=wl, num_rays=64)
            if psf_data is not None:
                pix_size = (dx.max() - dx.min()) / len(dx) if len(dx) > 1 else 0
                max_intens = psf_data.max()
                cy, cx = np.unravel_index(np.argmax(psf_data), psf_data.shape)
                center_x = dx[cx] if cx < len(dx) else 0
                center_y = dy[cy] if cy < len(dy) else 0
                # Width estimates (FWHM approx)
                row_center = psf_data[cy, :]
                col_center = psf_data[:, cx]
                half_max = max_intens / 2
                try:
                    w_mer = (dx.max() - dx.min()) / len(dx) * np.sum(row_center > half_max)
                    w_sag = (dy.max() - dy.min()) / len(dy) * np.sum(col_center > half_max)
                except Exception:
                    w_mer = w_sag = 0
                rows.append(["Разм. пикс.", f"{pix_size:.4f} мкм"])
                rows.append(["Макс. интенс.", f"{max_intens:.5f}"])
                rows.append(["Центр X", f"{center_x:.4f} мкм"])
                rows.append(["Центр Y", f"{center_y:.4f} мкм"])
                rows.append(["Шир. мер.", f"{w_mer:.4f} мкм"])
                rows.append(["Шир. саг.", f"{w_sag:.4f} мкм"])
        except Exception:
            rows.append(["Ошибка", "—"])
        self._set_table('psf', _make_table(
            ["Параметр", "Значение"], rows, [100, 120]))
    
    def _update_lsf_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            lsf_t, ax1 = compute_lsf(sys, wl=wl, num_rays=64, direction='tangential')
            lsf_s, ax2 = compute_lsf(sys, wl=wl, num_rays=64, direction='sagittal')
            rows = []
            n = len(ax1)
            step = max(1, n // 15)
            for i in range(0, n, step):
                rows.append([f"{ax1[i]:.4f}", f"{lsf_t[i]:.5f}", f"{lsf_s[i]:.5f}"])
            self._set_table('lsf', _make_table(
                ["Коорд. (мкм)", "Мерид. LSF", "Сагит. LSF"], rows, [75, 75, 75]))
        except Exception:
            self._set_table('lsf', None)
    
    def _update_enc_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            r_um, enc = compute_enc(sys, wl=wl, num_rays=100)
            rows = []
            n = len(r_um)
            step = max(1, n // 13)
            for i in range(0, n, step):
                rows.append([f"{r_um[i]*2:.4f}", f"{enc[i]*100:.2f}"])
            # Add key percentages
            for pct in [0.5, 0.8, 0.9]:
                idx = np.searchsorted(enc, pct)
                if idx < len(r_um):
                    d = r_um[idx] * 2  # diameter = 2*radius
                    rows.append([f"D@{int(pct*100)}%={d:.4f}", f"{pct*100:.2f}%"])
            self._set_table('enc', _make_table(
                ["D круга (мкм)", "Полихр. %"], rows, [110, 80]))
        except Exception:
            self._set_table('enc', None)
    
    def _update_ptf_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            ptf = compute_ptf(sys, wl=wl, num_rays=64)
            if ptf is None:
                self._set_table('ptf', None)
                return
            freqs = ptf['freqs']
            ptf_t = ptf['ptf_tangential']
            ptf_s = ptf['ptf_sagittal']
            rows = []
            n = len(freqs)
            step = max(1, n // 15)
            for i in range(0, n, step):
                rows.append([f"{freqs[i]:.2f}", f"{ptf_t[i]:.5f}", f"{ptf_s[i]:.5f}"])
            self._set_table('ptf', _make_table(
                ["Частота (л/мм)", "PTF мер. (рад)", "PTF саг. (рад)"], rows, [75, 80, 80]))
        except Exception:
            self._set_table('ptf', None)
    
    def _update_heatmap_table(self, sys):
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        rows = []
        rows.append(["Длина волны", f"{wl:.4f} мкм"])
        rows.append(["Сетка", f"{self.heatmap_w.grid_size}×{self.heatmap_w.grid_size}"])
        if self.heatmap_w.heatmap is not None and self.heatmap_w.heatmap.size > 0:
            x_span = (self.heatmap_w.x_range[1] - self.heatmap_w.x_range[0]) * 1000
            y_span = (self.heatmap_w.y_range[1] - self.heatmap_w.y_range[0]) * 1000
            rows.append(["Размер поля", f"{x_span:.4f}×{y_span:.4f} мкм"])
            rows.append(["Пикселей с данными", str(self.heatmap_w.num_points)])
            rows.append(["Макс. плотность", f"{self.heatmap_w.max_density:.4f}"])
            rows.append(["Центроид X", f"{self.heatmap_w.centroid_x*1000:.4f} мкм"])
            rows.append(["Центроид Y", f"{self.heatmap_w.centroid_y*1000:.4f} мкм"])
        else:
            rows.append(["Статус", "Нет данных"])
        self._set_table('heatmap', _make_table(
            ["Параметр", "Значение"], rows, [130, 130]))

    def _update_beam_table(self, sys):
        """Таблица габаритов пучков."""
        beam_data = compute_beam_geometry(sys)
        rows = []
        for bd in beam_data:
            rows.append([
                f"{bd['field_y']:.4f}",
                f"{bd['Ay']:.4f}",
                f"{bd['Ay_prime']:.4f}",
                f"{bd['vignetting_upper']:.4f}",
                f"{bd['vignetting_lower']:.4f}",
                f"{bd['relative_illumination']:.4f}",
            ])
        self._set_table('beam', _make_table(
            ["Поле", "Ay", "Ay'", "Виньет.↑", "Виньет.↓", "Светораспр."],
            rows, [45, 50, 50, 55, 55, 60]))

    def _update_chief_table(self, sys):
        """Таблица характеристик главных лучей."""
        chief_data = compute_chief_ray_characteristics(sys)
        rows = []
        for cd in chief_data:
            rows.append([
                f"{cd['field_y']:.4f}",
                f"{cd['distortion_abs']:.6f}",
                f"{cd['distortion_rel']:.6f}",
                f"{cd['Zm']:.6f}",
                f"{cd['Zs']:.6f}",
                f"{cd['lateral_color']:.6f}",
            ])
        self._set_table('chief', _make_table(
            ["Поле", "Дист.абс", "Дист.%", "Z'm", "Z's", "Хр.увел."],
            rows, [45, 60, 55, 60, 60, 60]))

    def _update_zernike_table(self, sys):
        """Таблица коэффициентов Цернике."""
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        defocus = self.get_defocus_offset()
        try:
            coeffs = compute_zernike_coefficients(sys, wl=wl, num_rays=32,
                                                    max_order=4,
                                                    defocus_offset=defocus)
            # Хроматический Цернике
            chromatic = None
            if len(sys.wavelengths) > 1:
                try:
                    chromatic = compute_zernike_chromatic(sys, num_rays=32, max_order=4)
                except Exception:
                    pass
            
            if chromatic and self.zernike_w._show_chromatic:
                # Показываем хроматический: колонки для каждой длины волны
                wl_keys = [k for k in chromatic if not k.startswith('delta_')]
                if wl_keys:
                    headers = ["Полином"] + wl_keys
                    rows = []
                    for idx, (val, name) in enumerate(coeffs):
                        row = [name]
                        for key in wl_keys:
                            if key in chromatic:
                                for c, n in chromatic[key]:
                                    if n == name:
                                        row.append(f"{c:+.6f}")
                                        break
                                else:
                                    row.append("—")
                            else:
                                row.append("—")
                        rows.append(row)
                    # Разности
                    for delta_key in ['delta_F-d', 'delta_C-d']:
                        if delta_key in chromatic:
                            for idx, (val, name) in enumerate(chromatic[delta_key]):
                                if idx < len(rows):
                                    rows[idx].append(f"{val:+.6f}")
                    if any(k in chromatic for k in ['delta_F-d', 'delta_C-d']):
                        delta_headers = [k for k in ['delta_F-d', 'delta_C-d'] if k in chromatic]
                        headers.extend(delta_headers)
                    self._set_table('zernike', _make_table(headers, rows,
                        [80] + [70] * (len(headers) - 1)))
                    return
            
            # Обычный режим
            rows = []
            for val, name in coeffs:
                rows.append([name, f"{val:+.6f}"])
            self._set_table('zernike', _make_table(
                ["Полином", "Коэфф. (λ)"], rows, [120, 90]))
        except Exception:
            self._set_table('zernike', None)

    def _update_wfmap_table(self, sys):
        """Таблица параметров волнового фронта."""
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        rows = [["λ перв.", f"{wl:.4f} мкм"]]
        try:
            wf, coords, mask = compute_wavefront_map_2d(sys, wl=wl, grid_size=48,
                                                          defocus_offset=self.get_defocus_offset())
            if wf is not None and mask is not None:
                valid = wf[mask > 0]
                valid = valid[np.isfinite(valid)]  # Remove NaN/inf
                if valid.size > 0:
                    rows.append(["PV", f"{valid.max()-valid.min():.5f} λ"])
                    rows.append(["RMS", f"{np.sqrt(np.mean(valid**2)):.5f} λ"])
                    rows.append(["Мин", f"{valid.min():.5f} λ"])
                    rows.append(["Макс", f"{valid.max():.5f} λ"])
                    rows.append(["Сетка", f"{wf.shape[0]}×{wf.shape[1]}"])
                else:
                    rows.append(["Статус", "Нет данных"])
            else:
                rows.append(["Статус", "Нет данных"])
        except Exception:
            rows.append(["Ошибка", "—"])
        self._set_table('wfmap', _make_table(
            ["Параметр", "Значение"], rows, [100, 120]))

    def _update_esf_table(self, sys):
        """Таблица ESF."""
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            x_um, esf = compute_esf(sys, wl=wl)
            if x_um is None:
                self._set_table('esf', None)
                return
            rows = []
            n = len(x_um)
            step = max(1, n // 15)
            for i in range(0, n, step):
                rows.append([f"{x_um[i]:.4f}", f"{esf[i]:.5f}"])
            self._set_table('esf', _make_table(
                ["Коорд. (мкм)", "ESF"], rows, [90, 90]))
        except Exception:
            self._set_table('esf', None)
    
    def _update_focus_diag_table(self, sys):
        """Таблица для фокусировочных диаграмм."""
        if not self.focus_diagrams.spots_by_defocus:
            self._set_table('focus_diag', None)
            return
        rows = []
        for label in ["номинал", "+DS'", "-DS'", "+2DS'", "-2DS'"]:
            if label not in self.focus_diagrams.spots_by_defocus:
                continue
            spots, rms_info, df = self.focus_diagrams.spots_by_defocus[label]
            rows.append([
                label,
                f"{df:+.4f}",
                str(len(spots)),
                f"{rms_info['rms_total']:.5f}",
                f"{rms_info['rms_x']:.5f}",
                f"{rms_info['rms_y']:.5f}",
            ])
        self._set_table('focus_diag', _make_table(
            ["Поз.", "Δz (мм)", "Лучей", "RMS", "RMS_X", "RMS_Y"],
            rows, [55, 65, 40, 65, 65, 65]))
    
    def _update_psf3d_table(self, sys):
        """Таблица для PSF 3D."""
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        rows = [["λ перв.", f"{wl:.4f} мкм"]]
        if self.psf_3d_w.Z is not None:
            Z = self.psf_3d_w.Z
            rows.append(["Макс.", f"{Z.max():.5f}"])
            rows.append(["Размер", f"{Z.shape[0]}×{Z.shape[1]}"])
            if self.psf_3d_w.x_coords is not None:
                x_span = self.psf_3d_w.x_coords.max() - self.psf_3d_w.x_coords.min()
                rows.append(["Поле X", f"{x_span:.5f} мкм"])
        else:
            rows.append(["Статус", "Нет данных"])
        self._set_table('psf3d', _make_table(
            ["Параметр", "Значение"], rows, [100, 120]))

    def _update_wf_rms_field_table(self, sys):
        """Таблица СКВ волновой аберрации по полю."""
        data = self.wf_rms_field_w.field_data
        if not data or not data[0]:
            self._set_table('wf_rms_field', _make_table(
                ["Поле", "СКВ (λ)"], [["—", "Нет данных"]], [60, 100]))
            return
        field_vals, rms_full, rms_no_def, rms_no_tilt = data
        rows = []
        for f, r_full, r_def, r_tilt in zip(field_vals, rms_full, rms_no_def, rms_no_tilt):
            def _fmt(v):
                return f"{v:.5f}" if v == v else "—"  # NaN check
            rows.append([f"{f:.2f}°", _fmt(r_full), _fmt(r_def), _fmt(r_tilt)])
        self._set_table('wf_rms_field', _make_table(
            ["Поле", "СКВ (λ)", "СКВ-деф", "СКВ-тильт"], rows, [55, 75, 75, 75]))

    def _update_bar_target_table(self, sys):
        """Таблица миры: частота | контраст идеал | контраст реальный | MTF."""
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            mtf_data = self.bar_target_w.mtf_table
            if not mtf_data:
                mtf_data = compute_bar_target_mtf_table(sys, wl=wl)
            rows = []
            for entry in mtf_data:
                rows.append([
                    f"{entry['freq']}",
                    f"{entry['contrast_ideal']:.4f}",
                    f"{entry['contrast_real']:.4f}",
                    f"{entry['mtf']:.4f}",
                ])
            self._set_table('bar_target', _make_table(
                ["Частота (л/мм)", "Контр. идеал", "Контр. реал.", "MTF"],
                rows, [80, 80, 80, 80]))
        except Exception:
            self._set_table('bar_target', None)
