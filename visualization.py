"""
OPAL-OKB — Визуализация оптической системы v3
Стиль близкий к оригиналу OPAL-PC: чёрный фон, зелёные лучи, голубая линза
Зум колесиком, перемещение мышкой, полноэкранный режим
"""
import math
from PyQt5.QtWidgets import (QWidget, QSizePolicy, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QToolBar, QAction,
                              QToolButton, QMenu)
from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint, pyqtSignal
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont, 
                          QPainterPath, QLinearGradient, QWheelEvent,
                          QMouseEvent, QCursor, QTransform)

from optics_engine import OpticalSystem, Surface, ObjectType, paraxial_trace
from ray_tracing import trace_fan, TraceResult


class OpticalSystemView(QWidget):
    """Виджет для отрисовки оптической системы с лучами."""
    
    # Сигнал: масштаб изменился
    zoom_changed = pyqtSignal(float)
    
    # Оригинальные цвета OPAL-PC
    COLOR_BG = QColor(0, 0, 0)                    # Чёрный фон
    COLOR_AXIS = QColor(40, 40, 60)                # Оптическая ось
    COLOR_LENS_FILL = QColor(30, 60, 120, 140)     # Голубая заливка линзы
    COLOR_LENS_EDGE = QColor(60, 140, 220)          # Голубой контур
    COLOR_RAY = QColor(0, 200, 80, 200)             # Зелёные лучи
    COLOR_RAY_FIELD = QColor(200, 60, 60, 160)      # Красные внеосевые
    COLOR_TEXT = QColor(180, 180, 200)               # Текст
    COLOR_FOCAL = QColor(200, 200, 60)              # Жёлтый F'
    COLOR_STOP = QColor(200, 60, 60)                # Стоп (красный)
    COLOR_GRID = QColor(30, 30, 50)                 # Сетка
    
    # Цвета лучей по длине волны (нм)
    WL_COLORS = {
        # Красный (C, r)
        (0.62, float('inf')): QColor(220, 60, 60, 200),
        # Жёлто-зелёный (d, e)
        (0.55, 0.62): QColor(60, 220, 80, 200),
        # Синий (F, g)
        (0.48, 0.55): QColor(60, 120, 220, 200),
        # Фиолетовый (< 480nm)
        (0.0, 0.48): QColor(180, 60, 220, 200),
    }
    
    def _wl_color(self, wl):
        """Цвет луча по длине волны."""
        for (lo, hi), color in self.WL_COLORS.items():
            if lo <= wl < hi:
                return color
        return self.COLOR_RAY
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = None
        self.ray_results = []
        self.chromatic_rays = False  # показывать лучи для всех длин волн
        
        # Pan & Zoom
        self._zoom = 1.0          # масштаб (1.0 = автоподгонка)
        self._pan_x = 0.0         # смещение (в пикселях)
        self._pan_y = 0.0
        self._dragging = False
        self._last_mouse = None
        self._is_fullscreen = False
        
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)
        self.setCursor(QCursor(Qt.CrossCursor))
    
    def set_system(self, sys: OpticalSystem, trace_rays: bool = True):
        self.system = sys
        if trace_rays and sys and sys.surfaces:
            self._trace_all_rays()
        # Сбросить зум при новой системе
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()
    
    def set_system_fast(self, sys: OpticalSystem, spots=None):
        """Быстрое обновление: только осевой пучок для мгновенной визуализации.
        Не сбрасывает зум/pan — вызывается перед полным расчётом."""
        self.system = sys
        if sys and sys.surfaces:
            self.ray_results = []
            wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
            # Только осевой пучок, num_rays=11 — быстро (<100мс)
            axial = trace_fan(sys, num_rays=11, pupil_range=1.0, wl=wl, field_y=0.0)
            self.ray_results.append(('axial', wl, axial))
        self.update()
    
    def _trace_all_rays(self):
        self.ray_results = []
        sys = self.system
        
        wavelengths_to_trace = [sys.wavelengths[0].value] if sys.wavelengths else [0.58756]
        if getattr(self, 'chromatic_rays', False) and len(sys.wavelengths) > 1:
            wavelengths_to_trace = [wl.value for wl in sys.wavelengths]
        
        for wl in wavelengths_to_trace:
            # Осевой пучок
            axial = trace_fan(sys, num_rays=9, pupil_range=1.0, wl=wl, field_y=0.0)
            self.ray_results.append(('axial', wl, axial))
            
            # Внеосевые пучки
            if sys.field_points:
                for fp in sys.field_points:
                    if fp.y != 0:
                        fan = trace_fan(sys, num_rays=5, pupil_range=1.0, wl=wl, field_y=fp.y)
                        self.ray_results.append(('field', wl, fan))
    
    def reset_view(self):
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()
    
    def zoom_in(self):
        self._zoom = min(self._zoom * 1.3, 20.0)
        self.update()
        self.zoom_changed.emit(self._zoom)
    
    def zoom_out(self):
        self._zoom = max(self._zoom / 1.3, 0.1)
        self.update()
        self.zoom_changed.emit(self._zoom)
    
    # ===== Mouse Events =====
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        
        # Зум к позиции курсора
        mouse_pos = event.pos()
        old_zoom = self._zoom
        self._zoom = max(0.1, min(self._zoom * factor, 20.0))
        
        # Сдвигаем pan чтобы точка под курсором оставалась на месте
        scale_change = self._zoom / old_zoom
        center_x = self.width() / 2 + self._pan_x
        center_y = self.height() / 2 + self._pan_y
        
        self._pan_x = mouse_pos.x() - scale_change * (mouse_pos.x() - center_x) - self.width() / 2
        self._pan_y = mouse_pos.y() - scale_change * (mouse_pos.y() - center_y) - self.height() / 2
        
        self.update()
        self.zoom_changed.emit(self._zoom)
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._dragging = True
            self._last_mouse = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and self._last_mouse:
            dx = event.pos().x() - self._last_mouse.x()
            dy = event.pos().y() - self._last_mouse.y()
            self._pan_x += dx
            self._pan_y += dy
            self._last_mouse = event.pos()
            self.update()
            event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._dragging = False
            self._last_mouse = None
            self.setCursor(QCursor(Qt.CrossCursor))
            event.accept()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Двойной клик = полноэкранный режим"""
        if self._is_fullscreen:
            # Вернуть обратно
            self._is_fullscreen = False
            self.setParent(self._original_parent)
            self._original_layout.insertWidget(self._original_index, self)
            self.showNormal()
        else:
            # Полноэкранный
            self._is_fullscreen = True
            self._original_parent = self.parent()
            self._original_layout = self.parent().layout()
            self._original_index = self._original_layout.indexOf(self)
            self.setParent(None)
            self.setWindowFlags(Qt.Window)
            self.showFullScreen()
        event.accept()
    
    # ===== Paint =====
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        # Чёрный фон
        painter.fillRect(self.rect(), self.COLOR_BG)
        
        if not self.system or not self.system.surfaces:
            painter.setPen(QPen(self.COLOR_TEXT))
            painter.setFont(QFont("Consolas", 11))
            painter.drawText(self.rect(), Qt.AlignCenter, "Загрузите систему и нажмите «Рассчитать»")
            painter.end()
            return
        
        # ===== Координатная система =====
        z_pos = [0.0]
        for s in self.system.surfaces:
            z_pos.append(z_pos[-1] + s.thickness)
        
        margin = 40
        z_min = -max(30, z_pos[-1] * 0.25)
        # For finite object: extend z_min to show object at front focus
        from optics_engine import ObjectType, paraxial_trace
        if self.system.object_type == ObjectType.FINITE:
            parax_tmp = paraxial_trace(self.system)
            sF = parax_tmp.get('sF', 0)
            if sF and abs(sF) > 1e-6:
                z_min = -abs(sF) * 1.1
            else:
                z_min = -max(30, z_pos[-1] * 0.25)
        # z_max: find real focus from axial rays
        z_max_focus = 0
        for rtype, wl, results in self.ray_results:
            if rtype == 'axial':
                for rr in results:
                    if rr.success and len(rr.path) >= 2:
                        p1, p2 = rr.path[-2], rr.path[-1]
                        dy = p2[1] - p1[1]
                        if abs(dy) > 1e-10:
                            t = -p1[1] / dy
                            zf = p1[2] + t * (p2[2] - p1[2])
                            if 0 < zf < 1e5:
                                z_max_focus = max(z_max_focus, zf)
                break
        if z_max_focus > 0:
            z_max = z_max_focus * 1.1
        else:
            # Afocal system (image at ∞) — rays exit parallel
            z_max = z_pos[-1] + max(20, z_pos[-1] * 0.2)
        
        max_sd = max((s.semi_diameter for s in self.system.surfaces if s.semi_diameter > 0), default=15)
        aperture = self.system.aperture_value if self.system.aperture_value > 0 else 20
        y_max = max(max_sd, aperture / 2) * 1.4
        
        z_range = z_max - z_min
        y_range = y_max * 2
        draw_w = w - 2 * margin
        draw_h = h - 2 * margin
        
        base_scale = min(draw_w / z_range, draw_h / y_range)
        scale = base_scale * self._zoom
        
        cx = w / 2 + self._pan_x
        cy = h / 2 + self._pan_y
        z_center = (z_min + z_max) / 2
        
        def to_screen(z, y):
            sx = cx + (z - z_center) * scale
            sy = cy - y * scale
            return sx, sy
        
        # ===== Сетка (лёгкая) =====
        painter.setPen(QPen(self.COLOR_GRID, 1))
        # Вертикальные линии через каждые 10мм
        z_step = 10
        if self._zoom > 3: z_step = 5
        if self._zoom > 10: z_step = 1
        z = z_min - z_min % z_step
        while z <= z_max:
            sx1, sy1 = to_screen(z, y_max)
            sx2, sy2 = to_screen(z, -y_max)
            painter.drawLine(int(sx1), int(sy1), int(sx2), int(sy2))
            z += z_step
        
        # ===== Оптическая ось =====
        pen_axis = QPen(self.COLOR_AXIS, 1, Qt.DashDotLine)
        painter.setPen(pen_axis)
        ax1 = to_screen(z_min, 0)
        ax2 = to_screen(z_max, 0)
        painter.drawLine(int(ax1[0]), int(ax1[1]), int(ax2[0]), int(ax2[1]))
        
        # ===== Предмет (для конечного предмета) =====
        if self.system.object_type == ObjectType.FINITE:
            parax_obj = paraxial_trace(self.system)
            sF = parax_obj.get('sF', 0)
            if sF and abs(sF) > 1e-6:
                obj_z = -abs(sF)
                obj_h = self.system.object_height if self.system.object_height else 5.0
            # Стрелка вверх от оси
            p_base = to_screen(obj_z, 0)
            p_top = to_screen(obj_z, obj_h)
            painter.setPen(QPen(QColor(255, 200, 50), 2))
            painter.drawLine(int(p_base[0]), int(p_base[1]), int(p_top[0]), int(p_top[1]))
            # Стрелка
            arrow_size = max(3, scale * 0.02)
            painter.drawLine(int(p_top[0]), int(p_top[1]),
                             int(p_top[0] - arrow_size), int(p_top[1] + arrow_size))
            painter.drawLine(int(p_top[0]), int(p_top[1]),
                             int(p_top[0] + arrow_size), int(p_top[1] + arrow_size))
            painter.setPen(QColor(200, 200, 220))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(p_top[0]) - 15, int(p_top[1]) - 5, "Предмет")
        
        # ===== Линзы (заливка) =====
        for i, s in enumerate(self.system.surfaces):
            if s.glass and s.glass.upper() not in ('ВОЗДУХ', 'AIR', ''):
                self._draw_lens(painter, i, s, z_pos, to_screen, scale)
        
        # ===== Поверхности (контуры) =====
        for i, s in enumerate(self.system.surfaces):
            self._draw_surface_edge(painter, s, z_pos[i], to_screen, scale, i)
        
        # ===== Лучи =====
        for rtype, wl, results in self.ray_results:
            for rr in results:
                if rr.success and len(rr.path) >= 2:
                    self._draw_ray(painter, rr, to_screen, rtype, wl)
        
        # ===== Фокальная точка =====
        parax = paraxial_trace(self.system)
        efl = parax.get('focal_length', 0)
        bfd = parax.get('back_focal_distance', 0)
        if efl != 0 and len(self.system.surfaces) > 0:
            last_surf_z = z_pos[len(self.system.surfaces) - 1]
            # BFD = расстояние от последней поверхности до фокуса
            # Но z_pos[-1] уже включает толщину последней поверхности
            # Фокус на расстоянии BFD от последней поверхности
            # В нашей модели: z_pos[-1] = сумма всех толщин
            # Найдём фокус по осевому лучу
            for rtype, wl, results in self.ray_results:
                if rtype == 'axial':
                    # Найдём где лучи пересекают y=0
                    for rr in results:
                        if rr.success and len(rr.path) >= 2 and abs(rr.path[0][1]) > 1:
                            # Линейная интерполяция между последними двумя точками
                            p1 = rr.path[-2]
                            p2 = rr.path[-1]
                            if abs(p2[1] - p1[1]) > 1e-10:
                                t = -p1[1] / (p2[1] - p1[1])
                                fz = p1[2] + t * (p2[2] - p1[2])
                                fx, fy = to_screen(fz, 0)
                                painter.setPen(QPen(self.COLOR_FOCAL, 2))
                                painter.drawLine(int(fx) - 5, int(fy), int(fx) + 5, int(fy))
                                painter.drawLine(int(fx), int(fy) - 5, int(fx), int(fy) + 5)
                                painter.setFont(QFont("Consolas", 9))
                                painter.drawText(int(fx) - 5, int(fy) + 18, "F'")
                                break
                    break
        
        # ===== Экранирование =====
        obscuration = getattr(self.system, 'obscuration_ratio', 0.0)
        if obscuration > 0:
            # Закрашенный круг в центре на первой поверхности (входной зрачок)
            obs_radius_y = obscuration * y_max
            # На первой поверхности
            z0 = z_pos[0]
            center = to_screen(z0, 0)
            edge_top = to_screen(z0, obs_radius_y)
            edge_bot = to_screen(z0, -obs_radius_y)
            rx = abs(edge_top[0] - center[0])
            ry = abs(edge_top[1] - center[1])
            if rx > 2 and ry > 2:
                painter.setPen(QPen(QColor(80, 80, 80), 1))
                painter.setBrush(QBrush(QColor(60, 60, 60, 180)))
                painter.drawEllipse(QPointF(center[0], center[1]), rx, ry)
            # Also draw on all surfaces for clarity
            for si in range(len(self.system.surfaces)):
                sd = self.system.surfaces[si].semi_diameter if self.system.surfaces[si].semi_diameter > 0 else y_max
                obs_r = obscuration * sd
                c_s = to_screen(z_pos[si], 0)
                e_s = to_screen(z_pos[si], obs_r)
                rx_s = abs(e_s[0] - c_s[0])
                ry_s = abs(e_s[1] - c_s[1])
                if rx_s > 1 and ry_s > 1:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(QColor(80, 80, 80, 140)))
                    painter.drawEllipse(QPointF(c_s[0], c_s[1]), rx_s, ry_s)

        # ===== Метки поверхностей =====
        painter.setPen(QPen(self.COLOR_TEXT))
        painter.setFont(QFont("Consolas", 8))
        for i in range(len(self.system.surfaces)):
            sx, sy = to_screen(z_pos[i], -y_max * 0.9)
            painter.drawText(int(sx) - 3, int(sy), str(i + 1))
        
        # ===== Заголовок =====
        painter.setPen(QPen(QColor(200, 200, 220)))
        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        title = self.system.name if self.system.name else ""
        if efl != 0:
            title += f"   f'={efl:.2f} мм"
        painter.drawText(10, 16, title)
        
        # ===== Статус бар внизу =====
        painter.setPen(QPen(QColor(120, 120, 140)))
        painter.setFont(QFont("Consolas", 8))
        status = f"Масштаб: {self._zoom:.1f}x  |  Колёсико: зум  |  Перетаскивание: перемещение  |  Двойной клик: полный экран"
        painter.drawText(10, h - 8, status)
        
        painter.end()
    
    def _draw_lens(self, painter, idx, surf, z_pos, to_screen, scale):
        """Заливка стеклянного элемента."""
        sd = surf.semi_diameter if surf.semi_diameter > 0 else 15
        z1 = z_pos[idx]
        z2 = z1 + surf.thickness
        R1 = surf.radius if abs(surf.radius) > 1e-10 else 0
        
        n_pts = 50
        # Передняя кривая
        pts_front = []
        for j in range(n_pts + 1):
            y = -sd + 2 * sd * j / n_pts
            sag = self._sag(R1, y)
            pts_front.append(to_screen(z1 + sag, y))
        
        # Задняя кривая
        if idx + 1 < len(self.system.surfaces):
            R2 = self.system.surfaces[idx + 1].radius
            if abs(R2) < 1e-10: R2 = 0
        else:
            R2 = 0
        
        pts_back = []
        for j in range(n_pts + 1):
            y = -sd + 2 * sd * j / n_pts
            sag = self._sag(R2, y)
            pts_back.append(to_screen(z2 + sag, y))
        
        path = QPainterPath()
        path.moveTo(pts_front[0][0], pts_front[0][1])
        for p in pts_front[1:]:
            path.lineTo(p[0], p[1])
        for p in reversed(pts_back):
            path.lineTo(p[0], p[1])
        path.closeSubpath()
        
        grad = QLinearGradient(to_screen(z1, 0)[0], 0, to_screen(z2, 0)[0], 0)
        grad.setColorAt(0, QColor(30, 70, 150, 120))
        grad.setColorAt(0.5, QColor(40, 90, 180, 80))
        grad.setColorAt(1, QColor(30, 70, 150, 120))
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(path)
    
    def _draw_surface_edge(self, painter, surf, z, to_screen, scale, idx):
        """Контуры поверхностей."""
        sd = surf.semi_diameter if surf.semi_diameter > 0 else 15
        R = surf.radius if abs(surf.radius) > 1e-10 else 0
        
        has_glass = surf.glass and surf.glass.upper() not in ('ВОЗДУХ', 'AIR', '')
        pen = QPen(self.COLOR_LENS_EDGE if has_glass else QColor(80, 80, 100), 
                   2 if has_glass else 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        n_pts = 60
        path = QPainterPath()
        first = True
        for j in range(n_pts + 1):
            y = -sd + 2 * sd * j / n_pts
            sag = self._sag(R, y)
            sx, sy = to_screen(z + sag, y)
            if first:
                path.moveTo(sx, sy)
                first = False
            else:
                path.lineTo(sx, sy)
        painter.drawPath(path)
        
        # Стоп-поверхность
        if idx + 1 == self.system.stop_surface:
            painter.setPen(QPen(self.COLOR_STOP, 1, Qt.DashLine))
            s1 = to_screen(z, sd * 1.15)
            s2 = to_screen(z, -sd * 1.15)
            painter.drawLine(int(s1[0]), int(s1[1]), int(s2[0]), int(s2[1]))
    
    def _sag(self, R, y):
        if abs(R) < 1e-10: return 0.0
        if abs(y) > abs(R): return 0.0
        return R - math.copysign(math.sqrt(R**2 - y**2), R)
    
    def _draw_ray(self, painter, result, to_screen, rtype, wl=0.589):
        color = self._wl_color(wl) if self.chromatic_rays else \
                (self.COLOR_RAY if rtype == 'axial' else self.COLOR_RAY_FIELD)
        painter.setPen(QPen(color, 1.2))
        painter.setBrush(Qt.NoBrush)
        
        # Draw ray segments
        for i in range(len(result.path) - 1):
            p1 = result.path[i]
            p2 = result.path[i + 1]
            s1 = to_screen(p1[2], p1[1])
            s2 = to_screen(p2[2], p2[1])
            painter.drawLine(int(s1[0]), int(s1[1]), int(s2[0]), int(s2[1]))
        
        # Extend ray beyond last surface
        if result.success and len(result.path) >= 2:
            p_last = result.path[-1]
            p_prev = result.path[-2]
            dx = p_last[0] - p_prev[0]
            dy = p_last[1] - p_prev[1]
            dz = p_last[2] - p_prev[2]
            if abs(dz) > 1e-10:
                # Check if ray is parallel to axis (afocal system: image at ∞)
                is_parallel = abs(dy) < 1e-6 or abs(dy / dz) < 0.001
                if is_parallel:
                    # Afocal: parallel output, short extension (15% of system length)
                    sys_length = sum(s.thickness for s in self.system.surfaces)
                    z_target = p_last[2] + max(15, sys_length * 0.15)
                elif abs(dy) > 1e-10:
                    t_cross = -p_last[1] / dy
                    z_focus = p_last[2] + t_cross * dz
                    if t_cross > 0 and z_focus < 1e5:
                        # Finite focus: extend 10% past it
                        z_target = z_focus * 1.1
                    else:
                        # Diverging ray — short extension
                        sys_length = sum(s.thickness for s in self.system.surfaces)
                        z_target = p_last[2] + max(15, sys_length * 0.15)
                else:
                    z_target = p_last[2] + 20
                t = (z_target - p_last[2]) / dz
                ey = p_last[1] + dy * t
                ez = z_target
                s1 = to_screen(p_last[2], p_last[1])
                s2 = to_screen(ez, ey)
                painter.drawLine(int(s1[0]), int(s1[1]), int(s2[0]), int(s2[1]))
