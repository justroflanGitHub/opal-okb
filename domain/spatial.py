"""
OPAL-OKB — Пространственные системы: координатные преобразования поверхностей

Единственное место (single source of truth) преобразований
«глобальная СК ↔ локальная СК поверхности» для наклона и
децентрировки поверхностей (п. 17 GAP v2; OPAL-PC SPACE.DOC:
SBL/SRS/SBO — смещение и повороты системы координат поверхности).

Локальная система координат (СК) поверхности — правая, вершина
поверхности в начале координат, оптическая ось поверхности вдоль +Z.
Положение поверхности в глобальной СК:

1. **Децентрировка** ``decenter_x``/``decenter_y`` (мм) — смещение
   вершины от оси; координата Z вершины задаётся толщинами (d).
2. **Наклон** ``tilt_x``/``tilt_y``/``tilt_z`` (градусы) — поворот
   локальных осей вокруг вершины; порядок поворотов X, затем Y,
   затем Z: ``R = Rz·Ry·Rx`` (правые повороты, положительный угол —
   против часовой стрелки при взгляде с конца оси).

Преобразование луча в локальную СК (точка ``p`` и направление ``d``)::

    p_local = Rᵀ · (p − V),      d_local = Rᵀ · d
    p_global = V + R · p_local,  d_global = R · d_local

где ``V = (decenter_x, decenter_y, z_vertex)`` — вершина поверхности
в глобальной СК (поворот выполняется вокруг вершины).  Закон
Снеллиуса и формула отражения инвариантны к повороту, поэтому
пересечение с поверхностью и преломление выполняются в локальной СК
стандартными процедурами (сфера — аналитически, асферика — Ньютон).

Между поверхностями луч всегда возвращается в глобальную СК:
наклон/децентрировка каждой поверхности задаётся относительно
глобальной СК (самовозвратный координатный излом, как у децентрированной
поверхности, а не у наклонённой системы координат).

Модуль работает с чистыми кортежами и не зависит от других пакетов
проекта; связка с :class:`~analysis.ray_tracing.Ray` — в analysis.
"""
import math
from typing import Optional, Tuple

#: Порог (градусы/мм), ниже которого наклон/децентрировка считаются
#: нулевыми (тождественное преобразование, быстрый путь трассировки).
COORD_BREAK_EPS = 1e-12

#: 3-вектор — точка или направление (x, y, z) / (k, l, m).
Vec3 = Tuple[float, float, float]

#: Матрица поворота 3×3, строка за строкой (m00, m01, m02, m10, ...).
Matrix3 = Tuple[float, float, float,
                float, float, float,
                float, float, float]


def rotation_matrix(tilt_x_deg: float, tilt_y_deg: float,
                    tilt_z_deg: float) -> Optional[Matrix3]:
    """Матрица поворота локальной СК поверхности R = Rz·Ry·Rx.

    Правые повороты вокруг осей X, Y, Z глобальной СК (градусы),
    применяются в порядке X → Y → Z.  Возвращает ``None``, если все
    углы ниже :data:`COORD_BREAK_EPS` — тождественное преобразование
    (быстрый путь без матрицы).
    """
    if (abs(tilt_x_deg) <= COORD_BREAK_EPS and
            abs(tilt_y_deg) <= COORD_BREAK_EPS and
            abs(tilt_z_deg) <= COORD_BREAK_EPS):
        return None

    a = math.radians(tilt_x_deg)
    b = math.radians(tilt_y_deg)
    c = math.radians(tilt_z_deg)
    ca, sa = math.cos(a), math.sin(a)
    cb, sb = math.cos(b), math.sin(b)
    cc, sc = math.cos(c), math.sin(c)

    # R = Rz(c) · Ry(b) · Rx(a)
    return (
        cc * cb, cc * sb * sa - sc * ca, cc * sb * ca + sc * sa,
        sc * cb, sc * sb * sa + cc * ca, sc * sb * ca - cc * sa,
        -sb,     cb * sa,                cb * ca,
    )


def mat_vec(m: Matrix3, v: Vec3) -> Vec3:
    """Умножение матрицы на вектор: m · v."""
    return (
        m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
        m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
        m[6] * v[0] + m[7] * v[1] + m[8] * v[2],
    )


def mat_tvec(m: Matrix3, v: Vec3) -> Vec3:
    """Умножение транспонированной матрицы на вектор: mᵀ · v (обратный поворот)."""
    return (
        m[0] * v[0] + m[3] * v[1] + m[6] * v[2],
        m[1] * v[0] + m[4] * v[1] + m[7] * v[2],
        m[2] * v[0] + m[5] * v[1] + m[8] * v[2],
    )


def surface_has_coord_break(surface) -> bool:
    """True, если у поверхности задан наклон или децентрировка.

    Работает с любым объектом, у которого есть поля ``tilt_x`` /
    ``tilt_y`` / ``tilt_z`` / ``decenter_x`` / ``decenter_y``
    (:class:`domain.models.Surface`); отсутствующие поля считаются нулём.
    """
    return (abs(getattr(surface, 'tilt_x', 0.0)) > COORD_BREAK_EPS or
            abs(getattr(surface, 'tilt_y', 0.0)) > COORD_BREAK_EPS or
            abs(getattr(surface, 'tilt_z', 0.0)) > COORD_BREAK_EPS or
            abs(getattr(surface, 'decenter_x', 0.0)) > COORD_BREAK_EPS or
            abs(getattr(surface, 'decenter_y', 0.0)) > COORD_BREAK_EPS)


class CoordBreak:
    """Локальная система координат поверхности (наклон + децентрировка).

    Атрибуты:
        decenter_x, decenter_y: смещение вершины от оси (мм).
        z_vertex: Z-координата вершины в глобальной СК (мм) —
            получается накоплением толщин d.
        matrix: матрица поворота R (локальная → глобальная СК) или
            ``None`` для тождественного преобразования.

    Точки преобразуются с переносом вершины (поворот вокруг вершины),
    направления — только поворотом.
    """

    __slots__ = ('decenter_x', 'decenter_y', 'z_vertex', 'matrix')

    def __init__(self, tilt_x: float = 0.0, tilt_y: float = 0.0,
                 tilt_z: float = 0.0, decenter_x: float = 0.0,
                 decenter_y: float = 0.0, z_vertex: float = 0.0) -> None:
        self.decenter_x = decenter_x
        self.decenter_y = decenter_y
        self.z_vertex = z_vertex
        self.matrix = rotation_matrix(tilt_x, tilt_y, tilt_z)

    @classmethod
    def from_surface(cls, surface, z_vertex: float) -> 'CoordBreak':
        """Построить излом СК из поверхности (поля tilt_*/decenter_*)."""
        return cls(
            tilt_x=getattr(surface, 'tilt_x', 0.0),
            tilt_y=getattr(surface, 'tilt_y', 0.0),
            tilt_z=getattr(surface, 'tilt_z', 0.0),
            decenter_x=getattr(surface, 'decenter_x', 0.0),
            decenter_y=getattr(surface, 'decenter_y', 0.0),
            z_vertex=z_vertex,
        )

    @property
    def is_identity(self) -> bool:
        """True, если преобразование тождественно (нет наклона и децентрировки)."""
        return (self.matrix is None and
                abs(self.decenter_x) <= COORD_BREAK_EPS and
                abs(self.decenter_y) <= COORD_BREAK_EPS)

    # -- точки ----------------------------------------------------------

    def point_to_local(self, p: Vec3) -> Vec3:
        """Точку из глобальной СК — в локальную (вершина → начало координат).

        Смещение на вершину ``V`` выполняется всегда (и при децентрировке
        без наклона), поэтому вершина поверхности — в начале локальной СК.
        """
        shifted = (p[0] - self.decenter_x, p[1] - self.decenter_y,
                   p[2] - self.z_vertex)
        if self.matrix is None:
            return shifted
        return mat_tvec(self.matrix, shifted)

    def point_to_global(self, p: Vec3) -> Vec3:
        """Точку из локальной СК — в глобальную (начало координат → вершина)."""
        rotated = mat_vec(self.matrix, p) if self.matrix is not None else p
        return (rotated[0] + self.decenter_x, rotated[1] + self.decenter_y,
                rotated[2] + self.z_vertex)

    # -- направления ------------------------------------------------------

    def dir_to_local(self, d: Vec3) -> Vec3:
        """Направление луча из глобальной СК — в локальную (только поворот)."""
        if self.matrix is None:
            return d
        return mat_tvec(self.matrix, d)

    def dir_to_global(self, d: Vec3) -> Vec3:
        """Направление луча из локальной СК — в глобальную (только поворот)."""
        if self.matrix is None:
            return d
        return mat_vec(self.matrix, d)
