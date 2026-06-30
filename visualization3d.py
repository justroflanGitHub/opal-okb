"""
OPAL-OKB - 3D Visualization with OpenGL
QOpenGLWidget-based 3D viewer for optical systems and ray tracing.
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QOpenGLWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QSurfaceFormat

from PyQt5 import QtCore

try:
    from OpenGL.GL import (
        glBegin, glEnd, glVertex3f, glColor4f, glLineWidth, glPointSize,
        glEnable, glDisable, glClear, glClearColor, glMatrixMode, glLoadIdentity,
        glTranslatef, glRotatef, glScalef, glViewport, glOrtho,
        GL_PROJECTION, GL_MODELVIEW, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
        GL_DEPTH_TEST, GL_BLEND, GL_LINE_SMOOTH, GL_POINTS, GL_LINES,
        GL_LINE_STRIP, GL_LINE_LOOP, GL_TRIANGLES, GL_TRIANGLE_FAN, GL_QUADS,
        glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
        glPushMatrix, glPopMatrix, glGetFloatv, glGetIntegerv,
        GL_LINE_WIDTH, GL_POINT_SIZE,
        glHint, GL_LINE_SMOOTH_HINT, GL_NICEST,
        glPolygonMode, GL_FRONT_AND_BACK, GL_LINE, GL_FILL,
        glFlush,
    )
    from OpenGL.GLU import gluPerspective, gluLookAt
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False

from optics_engine import OpticalSystem, Surface, ObjectType, paraxial_trace
from ray_tracing import trace_ray_through_system, trace_grid_3d, Ray, TraceResult


class Visualization3D(QWidget):
    """
    3D optical system visualization widget.
    Renders lens surfaces, aperture stop, and rays in 3D using OpenGL.
    """

    # Wavelength colors (R, G, B) for common spectral lines
    WL_COLORS = {
        0.65627: (0.9, 0.2, 0.2),   # C (red)
        0.58756: (0.9, 0.9, 0.3),   # d (yellow)
        0.54607: (0.2, 0.9, 0.3),   # e (green)
        0.48613: (0.2, 0.5, 0.9),   # F (blue-cyan)
        0.43405: (0.6, 0.2, 0.9),   # G' (violet)
    }

    def _wl_color(self, wl):
        """Get RGB color for a wavelength, with interpolation fallback."""
        if wl in self.WL_COLORS:
            return self.WL_COLORS[wl]
        # Find nearest
        closest = min(self.WL_COLORS.keys(), key=lambda k: abs(k - wl))
        return self.WL_COLORS[closest]

    def __init__(self, parent=None):
        super().__init__(parent)

        if not HAS_OPENGL:
            # Fallback: show a label
            layout = QVBoxLayout(self)
            from PyQt5.QtWidgets import QLabel
            lbl = QLabel("PyOpenGL not available.\nInstall: pip install PyOpenGL")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)
            self.gl_widget = None
            self.system = None
            self.ray_data_3d = []
            return

        self.system = None
        self.ray_data_3d = []  # List of (wl, field_y, results_from_trace_grid_3d)

        # State
        self._show_rays = True
        self._show_wireframe = False
        self._show_solid = True

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)

        self.btn_reset = QPushButton("Reset View")
        self.btn_reset.setMaximumWidth(90)
        self.btn_reset.clicked.connect(self._reset_view)

        self.btn_toggle_rays = QPushButton("Rays: ON")
        self.btn_toggle_rays.setMaximumWidth(90)
        self.btn_toggle_rays.setCheckable(True)
        self.btn_toggle_rays.setChecked(True)
        self.btn_toggle_rays.clicked.connect(self._toggle_rays)

        self.btn_toggle_wire = QPushButton("Wireframe")
        self.btn_toggle_wire.setMaximumWidth(90)
        self.btn_toggle_wire.setCheckable(True)
        self.btn_toggle_wire.clicked.connect(self._toggle_wireframe)

        self.btn_trace = QPushButton("Trace 3D Rays")
        self.btn_trace.setMaximumWidth(110)
        self.btn_trace.clicked.connect(self._trace_rays)

        toolbar.addWidget(self.btn_reset)
        toolbar.addWidget(self.btn_toggle_rays)
        toolbar.addWidget(self.btn_toggle_wire)
        toolbar.addWidget(self.btn_trace)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # OpenGL widget
        self.gl_widget = _GLWidget(self)
        layout.addWidget(self.gl_widget, 1)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_system(self, sys):
        """Load an optical system and auto-trace rays."""
        self.system = sys
        if sys and sys.surfaces:
            self._trace_rays()
        if self.gl_widget:
            self.gl_widget.update()

    def _reset_view(self):
        if self.gl_widget:
            self.gl_widget.reset_view()

    def _toggle_rays(self):
        self._show_rays = self.btn_toggle_rays.isChecked()
        self.btn_toggle_rays.setText("Rays: ON" if self._show_rays else "Rays: OFF")
        if self.gl_widget:
            self.gl_widget.update()

    def _toggle_wireframe(self):
        self._show_wireframe = self.btn_toggle_wire.isChecked()
        if self.gl_widget:
            self.gl_widget.update()

    def _trace_rays(self):
        """Trace rays for all wavelengths and field points."""
        if not self.system or not self.system.surfaces:
            return

        sys = self.system
        self.ray_data_3d = []

        # Determine field angles to trace
        field_angles = [0.0]
        if sys.field_points:
            max_field = max(abs(fp.y) for fp in sys.field_points if fp.y != 0)
            if max_field > 0:
                field_angles = [0.0, max_field]

        # Determine wavelengths
        wavelengths = [sys.wavelengths[0].value] if sys.wavelengths else [0.54607]
        # For 3D, limit to primary + maybe 2 more for chromatic effect
        if len(sys.wavelengths) > 1:
            wavelengths = [w.value for w in sys.wavelengths[:3]]

        for wl in wavelengths:
            for fa in field_angles:
                try:
                    results = trace_grid_3d(sys, num_rings=3, num_azimuths=8,
                                           wl=wl, field_y=fa)
                    if results and any(ring for ring in results):
                        self.ray_data_3d.append((wl, fa, results))
                except Exception:
                    pass

        if self.gl_widget:
            self.gl_widget.update()

    def get_scene_info(self):
        """Return info string about the current scene."""
        if not self.system:
            return "No system loaded"
        total_rays = sum(
            sum(len(ring) for ring in results)
            for _, _, results in self.ray_data_3d
        )
        ok_rays = sum(
            sum(1 for ring in results for r in ring if r.success)
            for _, _, results in self.ray_data_3d
        )
        return f"Rays: {ok_rays}/{total_rays} passed"


class _GLWidget(QOpenGLWidget):
    """Internal OpenGL rendering widget."""

    def __init__(self, parent3d):
        super().__init__()
        self.parent3d = parent3d

        # Camera state
        self._rot_x = -20.0   # pitch (tilt down to see system from above)
        self._rot_y = 0.0     # yaw
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0

        # Mouse tracking
        self._last_pos = None
        self._dragging = False

        # Display lists cache
        self._cached_surfaces = None

        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def reset_view(self):
        self._rot_x = -20.0
        self._rot_y = 0.0
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()

    def initializeGL(self):
        if not HAS_OPENGL:
            return
        glClearColor(0.05, 0.05, 0.08, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, w, h):
        if not HAS_OPENGL:
            return
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h if h > 0 else 1.0
        gluPerspective(45.0, aspect, 0.1, 5000.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if not HAS_OPENGL:
            return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Camera setup
        # We look at the origin from a distance, rotated
        cam_dist = 200.0 / self._zoom if self._zoom > 0 else 200.0

        gluLookAt(
            self._pan_x, self._pan_y, cam_dist,   # eye
            self._pan_x, self._pan_y, 0.0,         # center
            0.0, 1.0, 0.0                           # up
        )

        sys = self.parent3d.system
        if not sys or not sys.surfaces:
            return

        # Compute z-positions
        z_pos = [0.0]
        for s in sys.surfaces:
            z_pos.append(z_pos[-1] + s.thickness)

        # Center the system around z=0 BEFORE rotation
        # so rotation pivot is at the center of the optical system
        z_center = (z_pos[0] + z_pos[-1]) / 2.0
        glTranslatef(0.0, 0.0, -z_center)

        # Apply rotation around the center
        glRotatef(self._rot_x, 1.0, 0.0, 0.0)
        glRotatef(self._rot_y, 0.0, 1.0, 0.0)

        # Determine scale factor
        total_z = z_pos[-1] - z_pos[0]
        max_sd = max((s.semi_diameter for s in sys.surfaces if s.semi_diameter > 0), default=15.0)
        aperture = sys.aperture_value if sys.aperture_value > 0 else 20.0
        if aperture < 1.0:
            real_sd = [s2.semi_diameter for s2 in sys.surfaces if s2.semi_diameter > aperture / 10.0]
            if real_sd:
                aperture = max(real_sd) * 2.0
        max_dim = max(total_z, max_sd, aperture / 2.0)
        scale = 50.0 / max_dim if max_dim > 0 else 1.0
        glScalef(scale, scale, scale)

        # ===== Draw optical axis =====
        self._draw_axis(z_pos, scale)

        # ===== Draw lens surfaces =====
        for i, s in enumerate(sys.surfaces):
            self._draw_surface(s, z_pos[i], i, sys)

        # ===== Draw aperture stop =====
        self._draw_aperture_stop(sys, z_pos)

        # ===== Draw rays =====
        if self.parent3d._show_rays:
            self._draw_rays()

        glFlush()

    def _draw_axis(self, z_pos, scale):
        """Draw the optical axis as a thin gray line."""
        z_min = z_pos[0] - 20.0
        z_max = z_pos[-1] + 20.0
        glColor4f(0.3, 0.3, 0.4, 0.5)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, 0.0, z_min)
        glVertex3f(0.0, 0.0, z_max)
        glEnd()

    def _draw_surface(self, surf, z, idx, sys):
        """Draw a lens surface as a 3D ring/disc."""
        sd = abs(surf.semi_diameter) if surf.semi_diameter > 0 else 15.0
        
        # Detect bogus semi_diameter
        aperture = sys.aperture_value if sys.aperture_value > 0 else 20.0
        if aperture < 1.0:
            real_sd_list = [s2.semi_diameter for s2 in sys.surfaces if s2.semi_diameter > aperture / 10.0]
            if real_sd_list:
                aperture = max(real_sd_list) * 2.0
        if 0 < sd < aperture / 10.0:
            sd = aperture / 2.0 * 0.9  # Use aperture radius instead

        R = surf.radius if abs(surf.radius) > 1e-10 else 0.0
        n_segments = 48

        if surf.is_reflective:
            # Mirror: golden ring
            color = (0.85, 0.7, 0.2, 0.8)
            self._draw_surface_ring(sd, R, z, color, n_segments, is_mirror=True)
        elif surf.glass and surf.glass.upper().strip() not in ('', 'AIR', 'ВОЗДУХ'):
            # Glass surface: blue-ish
            color = (0.3, 0.5, 0.9, 0.3)
            self._draw_surface_ring(sd, R, z, color, n_segments, is_mirror=False)
            
            # Draw glass volume between this surface and the next (if next is also glass or same element)
            if idx + 1 < len(sys.surfaces):
                next_s = sys.surfaces[idx + 1]
                next_z = z + surf.thickness
                if surf.thickness > 0 and surf.thickness < 100:  # reasonable glass thickness
                    self._draw_glass_volume(surf, next_s, z, next_z, sd, n_segments)
        else:
            # Air surface: faint gray ring
            color = (0.4, 0.4, 0.45, 0.25)
            self._draw_surface_ring(sd, R, z, color, n_segments, is_mirror=False)

    def _draw_surface_ring(self, sd, R, z, color, n_segments, is_mirror=False):
        """Draw a surface as a filled ring (disc) with optional curvature."""

        # Draw the surface as a disc with sag
        if self.parent3d._show_wireframe:
            # Wireframe mode: just the outline
            glColor4f(color[0], color[1], color[2], color[3] * 2)
            glLineWidth(1.5)
            glBegin(GL_LINE_LOOP)
            for i in range(n_segments):
                a = 2 * math.pi * i / n_segments
                x = sd * math.cos(a)
                y = sd * math.sin(a)
                sag = self._sag(R, math.sqrt(x*x + y*y))
                glVertex3f(x, y, z + sag)
            glEnd()
        else:
            # Solid: filled disc
            if is_mirror:
                # Mirror: draw front and back arcs
                glColor4f(color[0], color[1], color[2], color[3])
                glLineWidth(3.0)
                glBegin(GL_LINE_LOOP)
                for i in range(n_segments):
                    a = 2 * math.pi * i / n_segments
                    x = sd * math.cos(a)
                    y = sd * math.sin(a)
                    sag = self._sag(R, math.sqrt(x*x + y*y))
                    glVertex3f(x, y, z + sag)
                glEnd()
                # Draw radial hash marks to indicate mirror
                glColor4f(0.7, 0.55, 0.15, 0.6)
                glLineWidth(1.0)
                n_hash = 12
                for i in range(n_hash):
                    a = 2 * math.pi * i / n_hash
                    x1 = sd * 0.85 * math.cos(a)
                    y1 = sd * 0.85 * math.sin(a)
                    x2 = sd * 1.05 * math.cos(a)
                    y2 = sd * 1.05 * math.sin(a)
                    sag1 = self._sag(R, math.sqrt(x1*x1 + y1*y1))
                    sag2 = self._sag(R, math.sqrt(x2*x2 + y2*y2))
                    glBegin(GL_LINES)
                    glVertex3f(x1, y1, z + sag1)
                    glVertex3f(x2, y2, z + sag2)
                    glEnd()
            else:
                # Glass/air surface: translucent disc
                # Center fan
                glColor4f(color[0], color[1], color[2], color[3])
                glBegin(GL_TRIANGLE_FAN)
                sag_center = self._sag(R, 0.0)
                glVertex3f(0.0, 0.0, z + sag_center)
                for i in range(n_segments + 1):
                    a = 2 * math.pi * i / n_segments
                    x = sd * math.cos(a)
                    y = sd * math.sin(a)
                    sag = self._sag(R, math.sqrt(x*x + y*y))
                    glVertex3f(x, y, z + sag)
                glEnd()

                # Outline ring
                glColor4f(color[0] * 1.5, color[1] * 1.5, color[2] * 1.5, min(1.0, color[3] * 3))
                glLineWidth(1.5)
                glBegin(GL_LINE_LOOP)
                for i in range(n_segments):
                    a = 2 * math.pi * i / n_segments
                    x = sd * math.cos(a)
                    y = sd * math.sin(a)
                    sag = self._sag(R, math.sqrt(x*x + y*y))
                    glVertex3f(x, y, z + sag)
                glEnd()

    def _draw_glass_volume(self, s1, s2, z1, z2, sd, n_segments):
        """Draw a semi-transparent volume between two surfaces."""
        R1 = s1.radius if abs(s1.radius) > 1e-10 else 0.0
        R2 = s2.radius if abs(s2.radius) > 1e-10 else 0.0

        glColor4f(0.2, 0.4, 0.8, 0.08)
        glBegin(GL_QUADS)
        for i in range(n_segments):
            a1 = 2 * math.pi * i / n_segments
            a2 = 2 * math.pi * (i + 1) / n_segments

            # Points on surface 1
            x1a = sd * math.cos(a1)
            y1a = sd * math.sin(a1)
            x1b = sd * math.cos(a2)
            y1b = sd * math.sin(a2)
            sag1a = self._sag(R1, sd)
            sag1b = self._sag(R1, sd)

            # Points on surface 2
            x2a = x1a
            y2a = y1a
            x2b = x1b
            y2b = y1b
            sag2a = self._sag(R2, sd)
            sag2b = self._sag(R2, sd)

            # Side quad
            glVertex3f(x1a, y1a, z1 + sag1a)
            glVertex3f(x1b, y1b, z1 + sag1b)
            glVertex3f(x2b, y2b, z2 + sag2b)
            glVertex3f(x2a, y2a, z2 + sag2a)
        glEnd()

    def _draw_aperture_stop(self, sys, z_pos):
        """Draw the aperture stop as a distinctive ring."""
        stop_idx = getattr(sys, 'stop_surface', 1)
        stop_off = getattr(sys, 'stop_offset', 0.0)

        if stop_idx < 0 or stop_idx >= len(z_pos):
            return

        z_stop = z_pos[stop_idx] + stop_off

        aperture = sys.aperture_value if sys.aperture_value > 0 else 20.0
        if aperture < 1.0:
            real_sd = [s2.semi_diameter for s2 in sys.surfaces if s2.semi_diameter > aperture / 10.0]
            if real_sd:
                aperture = max(real_sd) * 2.0
        stop_r = aperture / 2.0

        # Draw stop as a bright red ring
        n_segments = 48
        glColor4f(0.9, 0.3, 0.3, 0.9)
        glLineWidth(2.5)
        glBegin(GL_LINE_LOOP)
        for i in range(n_segments):
            a = 2 * math.pi * i / n_segments
            x = stop_r * math.cos(a)
            y = stop_r * math.sin(a)
            glVertex3f(x, y, z_stop)
        glEnd()

        # Draw small ticks at cardinals
        glColor4f(0.9, 0.3, 0.3, 0.7)
        glLineWidth(1.5)
        tick_r1 = stop_r * 1.1
        tick_r2 = stop_r * 1.2
        for angle_deg in [0, 90, 180, 270]:
            a = math.radians(angle_deg)
            glBegin(GL_LINES)
            glVertex3f(tick_r1 * math.cos(a), tick_r1 * math.sin(a), z_stop)
            glVertex3f(tick_r2 * math.cos(a), tick_r2 * math.sin(a), z_stop)
            glEnd()

    def _draw_rays(self):
        """Draw all traced rays as 3D polylines."""
        for wl, field_y, grid_results in self.parent3d.ray_data_3d:
            color = self.parent3d._wl_color(wl)
            r_col, g_col, b_col = color

            for ring_results in grid_results:
                for tr in ring_results:
                    if len(tr.path) < 2:
                        continue

                    if tr.success:
                        # Bright colored ray
                        alpha = 0.85
                        cr, cg, cb = r_col, g_col, b_col
                        lw = 1.5
                    else:
                        # Dimmed/blocked ray
                        alpha = 0.2
                        cr, cg, cb = 0.5, 0.5, 0.5
                        lw = 0.8

                    glColor4f(cr, cg, cb, alpha)
                    glLineWidth(lw)
                    glBegin(GL_LINE_STRIP)
                    for px, py, pz in tr.path:
                        glVertex3f(px, py, pz)
                    glEnd()

    def _sag(self, R, r):
        """Compute sag of a spherical surface at radial distance r."""
        if abs(R) < 1e-10:
            return 0.0
        if abs(r) > abs(R):
            r = abs(R) * 0.999
        return R - math.copysign(math.sqrt(R * R - r * r), R)

    # ===== Mouse Events =====
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_pos = event.pos()
        elif event.button() == Qt.MiddleButton:
            self._dragging = True
            self._last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if not self._dragging or not self._last_pos:
            return

        dx = event.x() - self._last_pos.x()
        dy = event.y() - self._last_pos.y()

        if event.modifiers() & Qt.ShiftModifier or event.buttons() & Qt.MiddleButton:
            # Pan
            self._pan_x -= dx * 0.5 / self._zoom
            self._pan_y += dy * 0.5 / self._zoom
        else:
            # Rotate
            self._rot_y += dx * 0.5
            self._rot_x -= dy * 0.5
            # Clamp pitch
            self._rot_x = max(-90.0, min(90.0, self._rot_x))

        self._last_pos = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._dragging = False
            self._last_pos = None

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self._zoom = max(0.05, min(self._zoom * factor, 50.0))
        self.update()
