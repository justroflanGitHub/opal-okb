"""Записывающий GL-стаб + программный растеризатор для тестов 3D-визуализации.

Окружение без GPU (TASK_3DMIRRORS): offscreen-платформа Qt не создаёт
GL-контекст для QOpenGLWidget (grabFramebuffer → 0×0), нативная платформа
падает в драйвере. Стаб подменяет импортированные в ``visualization3d``
функции OpenGL, записывает поток примитивов из настоящего ``paintGL()``
и растеризует его в QImage — перспектива gluPerspective/gluLookAt,
depth-test и alpha-blend повторяют конвейер фиксированного OpenGL.

Используется тестами (test_viz3d_mirrors) и скриптом скриншотов
(scripts/render_viz3d_mirrors.py) — без дисплея и без драйвера.
"""
import contextlib
import math

import numpy as np

# Константы режимов glBegin (значения — как в gl.h)
GL_POINTS = 0x0000
GL_LINES = 0x0001
GL_LINE_LOOP = 0x0002
GL_LINE_STRIP = 0x0003
GL_TRIANGLES = 0x0004
GL_TRIANGLE_FAN = 0x0006
GL_QUADS = 0x0007

GL_PROJECTION = 0x1701
GL_MODELVIEW = 0x1700


# ---------------------------------------------------------------------------
# Матричная арифметика (row-major 4x4, v' = M · v)
# ---------------------------------------------------------------------------

def _identity():
    return np.eye(4, dtype=np.float64)


def _translate(tx, ty, tz):
    m = _identity()
    m[0, 3], m[1, 3], m[2, 3] = tx, ty, tz
    return m


def _scale(sx, sy, sz):
    m = _identity()
    m[0, 0], m[1, 1], m[2, 2] = sx, sy, sz
    return m


def _rotate(deg, x, y, z):
    """glRotatef: поворот вокруг нормализованной оси (deg), v' = R·v."""
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-12:
        return _identity()
    x, y, z = x / n, y / n, z / n
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    t = 1.0 - c
    return np.array([
        [t * x * x + c,     t * x * y - s * z, t * x * z + s * y, 0.0],
        [t * x * y + s * z, t * y * y + c,     t * y * z - s * x, 0.0],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c,     0.0],
        [0.0,               0.0,               0.0,               1.0],
    ], dtype=np.float64)


def _perspective(fovy_deg, aspect, near, far):
    """gluPerspective: клип w = −z_eye (OpenGL man page)."""
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4), dtype=np.float64)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2.0 * far * near / (near - far)
    m[3, 2] = -1.0
    return m


def _look_at(eye, center, up):
    """gluLookAt: s = f×up, u = s×f, затем перенос на −eye."""
    ex, ey, ez = eye
    cx, cy, cz = center
    ux, uy, uz = up
    f = np.array([cx - ex, cy - ey, cz - ez], dtype=np.float64)
    fn = np.linalg.norm(f)
    if fn < 1e-12:
        return _identity()
    f /= fn
    upv = np.array([ux, uy, uz], dtype=np.float64)
    s = np.cross(f, upv)
    sn = np.linalg.norm(s)
    if sn < 1e-12:
        return _identity()
    s /= sn
    u = np.cross(s, f)
    m = _identity()
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    return m @ _translate(-ex, -ey, -ez)


# ---------------------------------------------------------------------------
# GL-стаб: записывает примитивы из paintGL
# ---------------------------------------------------------------------------

class GLStub:
    """Минимальный записывающий двойник фиксированного конвейера OpenGL.

    Понимает только то, что реально использует visualization3d.paintGL:
    матрицы/стек, glBegin/glVertex3f/glEnd, glColor4f, glLineWidth.
    """

    def __init__(self, width=900, height=600):
        self.width, self.height = width, height
        self.reset()

    def reset(self):
        self.matrices = {GL_PROJECTION: _identity(), GL_MODELVIEW: _identity()}
        self.stacks = {GL_PROJECTION: [], GL_MODELVIEW: []}
        self._mode = None
        self._verts = None
        self._color = (1.0, 1.0, 1.0, 1.0)
        self._line_width = 1.0
        #: список примитивов: (mode, color, line_width, [(x,y,z), ...])
        self.primitives = []

    # -- состояние ----------------------------------------------------------
    def glViewport(self, x, y, w, h):
        self.width, self.height = w, h

    def glMatrixMode(self, mode):
        self._matrix_mode = mode

    def glLoadIdentity(self):
        self.matrices[self._matrix_mode] = _identity()

    def glPushMatrix(self):
        self.stacks[self._matrix_mode].append(
            self.matrices[self._matrix_mode].copy())

    def glPopMatrix(self):
        if self.stacks[self._matrix_mode]:
            self.matrices[self._matrix_mode] = \
                self.stacks[self._matrix_mode].pop()

    def _compose(self, m):
        cur = self.matrices[self._matrix_mode]
        self.matrices[self._matrix_mode] = cur @ m

    def glTranslatef(self, tx, ty, tz):
        self._compose(_translate(tx, ty, tz))

    def glRotatef(self, deg, x, y, z):
        self._compose(_rotate(deg, x, y, z))

    def glScalef(self, sx, sy, sz):
        self._compose(_scale(sx, sy, sz))

    def glOrtho(self, *args):
        pass  # visualization3d не использует в paintGL

    def gluPerspective(self, fovy, aspect, near, far):
        self._compose(_perspective(fovy, aspect, near, far))

    def gluLookAt(self, *args):
        self._compose(_look_at(args[0:3], args[3:6], args[6:9]))

    # -- рисование ----------------------------------------------------------
    def glColor4f(self, r, g, b, a):
        self._color = (r, g, b, min(1.0, max(0.0, a)))

    def glLineWidth(self, w):
        self._line_width = max(0.5, float(w))

    def glPointSize(self, s):
        pass

    def glBegin(self, mode):
        self._mode = mode
        self._verts = []

    def glVertex3f(self, x, y, z):
        self._verts.append((float(x), float(y), float(z)))

    def glEnd(self):
        if self._mode is not None and self._verts:
            self.primitives.append(
                (self._mode, self._color, self._line_width, self._verts))
        self._mode = None
        self._verts = None

    # -- заглушки без эффекта ----------------------------------------------
    def glEnable(self, *a):
        pass

    def glDisable(self, *a):
        pass

    def glClear(self, *a):
        pass

    def glClearColor(self, *a):
        pass

    def glBlendFunc(self, *a):
        pass

    def glHint(self, *a):
        pass

    def glPolygonMode(self, *a):
        pass

    def glFlush(self):
        pass


#: имена GL-функций, которые visualization3d импортирует и вызывает в paintGL
GL_FUNCS = (
    'glBegin', 'glEnd', 'glVertex3f', 'glColor4f', 'glLineWidth', 'glPointSize',
    'glEnable', 'glDisable', 'glClear', 'glClearColor', 'glMatrixMode',
    'glLoadIdentity', 'glTranslatef', 'glRotatef', 'glScalef', 'glViewport',
    'glOrtho', 'gluPerspective', 'gluLookAt', 'glBlendFunc', 'glPushMatrix',
    'glPopMatrix', 'glHint', 'glPolygonMode', 'glFlush',
)


@contextlib.contextmanager
def gl_stubbed(width=900, height=600):
    """Подменить GL-функции модуля visualization3d на GLStub (контекст-менеджер).

    Yields стаб; после выхода исходные функции восстанавливаются.
    """
    import visualization3d
    stub = GLStub(width, height)
    saved = {name: getattr(visualization3d, name) for name in GL_FUNCS}
    try:
        for name in GL_FUNCS:
            setattr(visualization3d, name, getattr(stub, name))
        yield stub
    finally:
        for name, fn in saved.items():
            setattr(visualization3d, name, fn)


# ---------------------------------------------------------------------------
# Программный растеризатор записанного потока
# ---------------------------------------------------------------------------

def _project(verts, mv, proj, w, h):
    """Мировые вершины → экранные (x_px, y_px, depth) и клип-w."""
    v = np.array([(x, y, z, 1.0) for x, y, z in verts], dtype=np.float64).T
    clip = proj @ (mv @ v)
    wc = clip[3]
    # за глазом (w<=0) — вершина отсекается
    if np.any(wc <= 1e-9):
        return None
    ndc = clip[:3] / wc
    sx = (ndc[0] * 0.5 + 0.5) * w
    sy = (1.0 - (ndc[1] * 0.5 + 0.5)) * h
    depth = ndc[2] * 0.5 + 0.5
    return np.stack([sx, sy, depth])


def rasterize(stub, bg=(0.05, 0.05, 0.08)):
    """Растеризовать записанные примитивы → float-массив (H, W, 4) RGBA.

    Повторяет фиксированный конвейер: depth-test (LESS) и blend
    (SRC_ALPHA, ONE_MINUS_SRC_ALPHA). Возвращает изображение в float 0..1.
    """
    w, h = int(stub.width), int(stub.height)
    mv = stub.matrices[GL_MODELVIEW]
    proj = stub.matrices[GL_PROJECTION]

    color_buf = np.zeros((h, w, 4), dtype=np.float64)
    color_buf[..., 0:3] = bg
    color_buf[..., 3] = 1.0
    depth_buf = np.full((h, w), 1e30, dtype=np.float64)

    def _blend_pixel(xs, ys, depths, rgba):
        r, g, b, a = rgba
        xs = np.clip(xs, 0, w - 1).astype(int)
        ys = np.clip(ys, 0, h - 1).astype(int)
        d = depths
        ok = d < depth_buf[ys, xs]
        if not np.any(ok):
            return
        xs, ys, d = xs[ok], ys[ok], d[ok]
        # ближний к камере пиксель побеждает — сортируем по z по возрастанию
        order = np.argsort(d)
        xs, ys, d = xs[order], ys[order], d[order]
        seen = {}
        for x, y, z in zip(xs, ys, d):
            key = (int(y), int(x))
            if key not in seen:
                seen[key] = z
        for (y, x), z in seen.items():
            if z < depth_buf[y, x]:
                depth_buf[y, x] = z
                dst = color_buf[y, x]
                color_buf[y, x] = (
                    r * a + dst[0] * (1 - a),
                    g * a + dst[1] * (1 - a),
                    b * a + dst[2] * (1 - a),
                    a + dst[3] * (1 - a),
                )

    def _draw_line(p0, p1, rgba, width):
        """Отрезок в экранных координатах: сэмплирование ~0.5 px + толщина."""
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        length = math.hypot(x1 - x0, y1 - y0)
        if length < 1e-9:
            return
        n = max(2, int(length * 2))
        t = np.linspace(0.0, 1.0, n)
        xs = x0 + (x1 - x0) * t
        ys = y0 + (y1 - y0) * t
        zs = z0 + (z1 - z0) * t
        rad = max(0.0, (width - 1.0) / 2.0)
        if rad < 0.25:
            _blend_pixel(xs, ys, zs, rgba)
        else:
            for dx in np.arange(-rad, rad + 0.5, 1.0):
                for dy in np.arange(-rad, rad + 0.5, 1.0):
                    _blend_pixel(xs + dx, ys + dy, zs, rgba)

    def _draw_triangle(p0, p1, p2, rgba):
        """Заливка треугольника edge-функциями (numpy, по bbox)."""
        xs = np.array([p0[0], p1[0], p2[0]])
        ys = np.array([p0[1], p1[1], p2[1]])
        zs = np.array([p0[2], p1[2], p2[2]])
        x_min = max(0, int(np.floor(xs.min())))
        x_max = min(w - 1, int(np.ceil(xs.max())))
        y_min = max(0, int(np.floor(ys.min())))
        y_max = min(h - 1, int(np.ceil(ys.max())))
        if x_max < x_min or y_max < y_min:
            return
        gx, gy = np.meshgrid(np.arange(x_min, x_max + 1),
                             np.arange(y_min, y_max + 1))
        e1 = ((xs[1] - xs[0]) * (gy - ys[0]) - (ys[1] - ys[0]) * (gx - xs[0]))
        e2 = ((xs[2] - xs[1]) * (gy - ys[1]) - (ys[2] - ys[1]) * (gx - xs[1]))
        e3 = ((xs[0] - xs[2]) * (gy - ys[2]) - (ys[0] - ys[2]) * (gx - xs[2]))
        inside = ((e1 >= 0) & (e2 >= 0) & (e3 >= 0)) | \
                 ((e1 <= 0) & (e2 <= 0) & (e3 <= 0))
        if not np.any(inside):
            return
        # барицентрическая интерполяция z (λ0 ∝ e2, λ1 ∝ e3, λ2 ∝ e1)
        area = e1.astype(np.float64) + e2 + e3
        with np.errstate(divide='ignore', invalid='ignore'):
            l0 = np.where(area != 0, e2 / area, 0.0)
            l1 = np.where(area != 0, e3 / area, 0.0)
            l2 = np.where(area != 0, e1 / area, 0.0)
        z = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
        _blend_pixel(gx[inside], gy[inside], z[inside], rgba)

    for mode, rgba, line_width, verts in stub.primitives:
        pts = _project(verts, mv, proj, w, h)
        if pts is None:
            continue  # примитив частично за глазом — отсекается целиком

        if mode == GL_POINTS:
            for i in range(pts.shape[1]):
                _blend_pixel(_np.array([pts[0, i]]), _np.array([pts[1, i]]),
                             _np.array([pts[2, i]]), rgba)
        elif mode == GL_LINES:
            for i in range(0, pts.shape[1] - 1, 2):
                _draw_line(pts[:, i], pts[:, i + 1], rgba, line_width)
        elif mode in (GL_LINE_STRIP, GL_LINE_LOOP):
            n = pts.shape[1]
            for i in range(n - 1):
                _draw_line(pts[:, i], pts[:, i + 1], rgba, line_width)
            if mode == GL_LINE_LOOP and n > 2:
                _draw_line(pts[:, n - 1], pts[:, 0], rgba, line_width)
        elif mode == GL_TRIANGLES:
            for i in range(0, pts.shape[1] - 2, 3):
                _draw_triangle(pts[:, i], pts[:, i + 1], pts[:, i + 2], rgba)
        elif mode == GL_TRIANGLE_FAN:
            for i in range(1, pts.shape[1] - 1):
                _draw_triangle(pts[:, 0], pts[:, i], pts[:, i + 1], rgba)
        elif mode == GL_QUADS:
            for i in range(0, pts.shape[1] - 3, 4):
                _draw_triangle(pts[:, i], pts[:, i + 1], pts[:, i + 2], rgba)
                _draw_triangle(pts[:, i], pts[:, i + 2], pts[:, i + 3], rgba)

    return color_buf


def render_framebuffer(gl_widget, width=900, height=600):
    """Прогнать настоящий paintGL через GLStub и растеризовать кадр.

    Returns:
        ``(QImage кадр, GLStub стаб)`` — кадр отрисован программно из того же
        потока примитивов, который paintGL отправил бы в OpenGL.
    """
    from PyQt5.QtGui import QImage
    with gl_stubbed(width, height) as stub:
        gl_widget.resizeGL(width, height)  # перспектива gluPerspective
        gl_widget.paintGL()
        buf = rasterize(stub)
    h, w = buf.shape[:2]
    rgb = (np.clip(buf, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    # QImage Format_ARGB32 на little-endian: байты B, G, R, A
    bgra = np.ascontiguousarray(rgb[:, :, [2, 1, 0, 3]])
    img = QImage(bgra.data, w, h, w * 4, QImage.Format_ARGB32)
    return img.copy(), stub  # copy: отвязаться от numpy-буфера
