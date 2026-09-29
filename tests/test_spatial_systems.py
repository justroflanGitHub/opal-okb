"""Регрессионные тесты пункта 17 GAP v2 — пространственные системы
(наклон/децентрировка поверхностей).

Физика (OPAL-PC SPACE.DOC «SRT»: произвольно расположенные в
пространстве поверхности; SBL/SRS/SBO — смещение и повороты системы
координат поверхности):

- наклонённая параллельная пластина эквивалентна призме: выходящий
  луч параллелен падающему и смещён на классическую величину
  s = t·cos θ·sin θ·(1 − cos θ/√(n² − sin² θ))  (Слюсарев);
- наклонное зеркало отклоняет луч ровно на 2θ;
- полностью децентрированная линза + сдвинутый луч дают тот же путь,
  что центрированная линза (трансляционная инвариантность);
- закон Снеллиуса в векторной форме на наклонённой/смещённой сфере:
  n₁·(d − (d·n̂)n̂) = n₂·(d′ − (d′·n̂)n̂) с нормалью, вычисленной
  вручную из глобального центра кривизны.

Все «ручные» ожидания вычисляются в тестах независимыми формулами
(без движка), золотые значения — аналитически.
"""
import math
import sys

import pytest

from domain.models import OpticalSystem, Surface, Wavelength
from domain.spatial import (
    COORD_BREAK_EPS, CoordBreak, mat_vec, mat_tvec, rotation_matrix,
    surface_has_coord_break,
)
from ray_tracing import (
    Ray, trace_ray_through_system, trace_fan,
    _apply_coord_break, _undo_coord_break, _has_coord_break,
)
from utils.optics_utils import (
    COORD_CELL_TILT_COUNT, COORD_CELL_DECENTER_COUNT,
    format_coord_cell, parse_coord_cell,
)

#: Рабочая длина волны тестов (мкм).
WL = 0.54607

#: Показатель стекла в тестах — задаётся n_override (без каталога).
TEST_N = 1.5


# --------------------------------------------------------------------------- #
# Вспомогательные построения систем и лучей
# --------------------------------------------------------------------------- #

def _base_system(surfaces) -> OpticalSystem:
    """Система с одной длиной волны и апертурой 20 мм."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=WL)]
    s.aperture_value = 20.0
    s.surfaces = list(surfaces)
    s.stop_surface = 1
    return s


def _axial_ray(z_start: float = -10.0, y: float = 0.0) -> Ray:
    """Луч вдоль оси Z (входит параллельно оптической оси)."""
    return Ray(x=0.0, y=y, z=z_start, k=0.0, l=0.0, m=1.0)


def _lens(dy: float = 0.0) -> list:
    """Двухповерхностная линза (R=50/-200, d=5), полностью децентрированная на dy."""
    return [
        Surface(radius=50.0, thickness=5.0, glass='К8', semi_diameter=12.0,
                decenter_y=dy),
        Surface(radius=-200.0, thickness=90.0, glass='', semi_diameter=12.0,
                decenter_y=dy),
    ]


def _dir_between(p0, p1) -> tuple:
    """Единичное направление из p0 в p1 (направление сегмента пути)."""
    d = [p1[i] - p0[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in d))
    return tuple(v / n for v in d)


# --------------------------------------------------------------------------- #
# A. Матрицы поворота и CoordBreak (domain/spatial.py)
# --------------------------------------------------------------------------- #

class TestRotationMatrix:
    def test_identity_returns_none(self):
        """Все углы ~0 → тождественное преобразование (без матрицы)."""
        assert rotation_matrix(0.0, 0.0, 0.0) is None
        assert rotation_matrix(1e-14, -1e-14, 1e-14) is None

    def test_rotation_x_90(self):
        """Rx(90°): x→x, y→z, z→−y (правый поворот)."""
        m = rotation_matrix(90.0, 0.0, 0.0)
        assert mat_vec(m, (1, 0, 0)) == pytest.approx((1, 0, 0))
        assert mat_vec(m, (0, 1, 0)) == pytest.approx((0, 0, 1))
        assert mat_vec(m, (0, 0, 1)) == pytest.approx((0, -1, 0))

    def test_rotation_y_90(self):
        """Ry(90°): y→y, z→x, x→−z (правый поворот)."""
        m = rotation_matrix(0.0, 90.0, 0.0)
        assert mat_vec(m, (0, 1, 0)) == pytest.approx((0, 1, 0))
        assert mat_vec(m, (0, 0, 1)) == pytest.approx((1, 0, 0))
        assert mat_vec(m, (1, 0, 0)) == pytest.approx((0, 0, -1))

    def test_rotation_z_90(self):
        """Rz(90°): z→z, x→y, y→−x (правый поворот)."""
        m = rotation_matrix(0.0, 0.0, 90.0)
        assert mat_vec(m, (0, 0, 1)) == pytest.approx((0, 0, 1))
        assert mat_vec(m, (1, 0, 0)) == pytest.approx((0, 1, 0))
        assert mat_vec(m, (0, 1, 0)) == pytest.approx((-1, 0, 0))

    def test_composition_order_rz_ry_rx(self):
        """R = Rz·Ry·Rx (сначала X, затем Y, затем Z) — сверка с явным умножением."""
        tx, ty, tz = 30.0, 40.0, 50.0
        m = rotation_matrix(tx, ty, tz)

        def _rx(a):
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            return ((1, 0, 0), (0, c, -s), (0, s, c))

        def _ry(a):
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            return ((c, 0, s), (0, 1, 0), (-s, 0, c))

        def _rz(a):
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            return ((c, -s, 0), (s, c, 0), (0, 0, 1))

        def _mul(a, b):
            return tuple(
                tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
                for i in range(3))

        def _flat(mm):
            return tuple(v for row in mm for v in row)

        expected = _flat(_mul(_rz(tz), _mul(_ry(ty), _rx(tx))))
        assert m == pytest.approx(expected)

    def test_orthonormal_det_plus_one(self):
        m = rotation_matrix(11.0, -23.0, 47.0)
        # R·Rᵀ = I
        for i in range(3):
            for j in range(3):
                dot = sum(m[i * 3 + k] * m[j * 3 + k] for k in range(3))
                assert dot == pytest.approx(1.0 if i == j else 0.0)
        det = (m[0] * (m[4] * m[8] - m[5] * m[7])
               - m[1] * (m[3] * m[8] - m[5] * m[6])
               + m[2] * (m[3] * m[7] - m[4] * m[6]))
        assert det == pytest.approx(1.0)


class TestCoordBreak:
    def test_identity_passthrough(self):
        """Тождественный излом не меняет ни точку, ни направление."""
        cb = CoordBreak()
        assert cb.is_identity
        p, d = (1.0, -2.0, 30.0), (0.1, 0.2, 0.97)
        assert cb.point_to_local(p) == p
        assert cb.point_to_global(p) == p
        assert cb.dir_to_local(d) == d
        assert cb.dir_to_global(d) == d

    def test_decenter_only_translation(self):
        """Децентрировка без наклона — чистый сдвиг на вершину (включая Z)."""
        cb = CoordBreak(decenter_x=2.0, decenter_y=-1.0, z_vertex=13.0)
        assert not cb.is_identity
        p = (5.0, 4.0, 20.0)
        assert cb.point_to_local(p) == (3.0, 5.0, 7.0)
        assert cb.point_to_global((3.0, 5.0, 7.0)) == p

    def test_vertex_maps_to_local_origin(self):
        """Вершина поверхности — начало локальной СК (пивот поворота)."""
        cb = CoordBreak(tilt_x=10.0, tilt_y=-6.0, tilt_z=3.0,
                        decenter_x=1.5, decenter_y=-0.5, z_vertex=42.0)
        v = (1.5, -0.5, 42.0)
        assert cb.point_to_local(v) == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)

    def test_directions_only_rotated(self):
        """Направление не зависит от смещения вершины (только поворот)."""
        cb1 = CoordBreak(tilt_x=8.0, decenter_x=3.0, z_vertex=10.0)
        cb2 = CoordBreak(tilt_x=8.0)
        d = (0.0, 0.3, 0.95)
        assert cb1.dir_to_local(d) == pytest.approx(cb2.dir_to_local(d))

    def test_roundtrip_point_and_dir(self):
        """Туда-обратно — исходные точка и направление (точные инверсии)."""
        cb = CoordBreak(tilt_x=25.0, tilt_y=-14.0, tilt_z=61.0,
                        decenter_x=2.0, decenter_y=-3.0, z_vertex=17.0)
        p, d = (0.7, -1.3, 44.0), (0.2, -0.1, 0.97)
        assert cb.point_to_global(cb.point_to_local(p)) == pytest.approx(p)
        assert cb.dir_to_global(cb.dir_to_local(d)) == pytest.approx(d)

    def test_surface_has_coord_break(self):
        assert not surface_has_coord_break(Surface())
        assert surface_has_coord_break(Surface(tilt_x=1e-9))
        assert surface_has_coord_break(Surface(tilt_z=0.01))
        assert surface_has_coord_break(Surface(decenter_y=-1e-6))
        # обёртка трассировки делегирует той же реализации
        assert _has_coord_break(Surface(tilt_z=0.01))


class TestCoordBreakRayWrappers:
    """_apply/_undo_coord_break (analysis) — обёртки над domain.spatial."""

    def test_roundtrip_with_pivot_and_tilt_z(self):
        ray = Ray(x=1.0, y=2.0, z=10.0, k=0.0, l=0.1, m=0.995)
        tilted = _apply_coord_break(ray, 10.0, -5.0, 2.0, -1.0,
                                    tilt_z_deg=33.0, z_vertex=7.0)
        restored = _undo_coord_break(tilted, 10.0, -5.0, 2.0, -1.0,
                                     tilt_z_deg=33.0, z_vertex=7.0)
        assert (restored.x, restored.y, restored.z) == pytest.approx(
            (ray.x, ray.y, ray.z))
        assert (restored.k, restored.l, restored.m) == pytest.approx(
            (ray.k, ray.l, ray.m))

    def test_pivot_vertex_to_origin(self):
        """Луч из вершины поверхности попадает в локальное начало координат."""
        ray = Ray(x=1.5, y=-0.5, z=42.0, k=0.0, l=0.2, m=0.98)
        local = _apply_coord_break(ray, 12.0, -7.0, 1.5, -0.5, z_vertex=42.0)
        assert (local.x, local.y, local.z) == pytest.approx((0.0, 0.0, 0.0))


# --------------------------------------------------------------------------- #
# B. Золотой тест: наклонённая пластина = призма (Слюсарев)
# --------------------------------------------------------------------------- #

def _plate_system(theta_deg: float, t: float = 8.0, img: float = 40.0,
                  n: float = TEST_N) -> OpticalSystem:
    """Плоскопараллельная пластина, наклонённая на theta_deg вокруг X.

    Обе поверхности с одинаковым наклоном; показатель n задан точно
    через n_override (без каталога стёкол).
    """
    return _base_system([
        Surface(radius=0.0, thickness=t, glass='', semi_diameter=25.0,
                tilt_x=theta_deg, n_override={WL: n}),
        Surface(radius=0.0, thickness=img, glass='', semi_diameter=25.0,
                tilt_x=theta_deg),
    ])


def _manual_plate_exit(theta_deg: float, t: float, n: float) -> tuple:
    """Ручной расчёт точки выхода из наклонённой пластины.

    Пластина: вершина 1-й поверхности в (0,0,0), 2-й — в (0,0,t)
    (t вдоль глобальной оси Z); нормаль пластин повёрнута на θ вокруг X.
    Внутренний луч: a = sin θ/n, b = √(1−a²); путь в стекле
    L = t·cos θ/b; выход — L·d₂, d₂ = R_x(θ)·(0, a, b).
    """
    th = math.radians(theta_deg)
    st, ct = math.sin(th), math.cos(th)
    a = st / n
    b = math.sqrt(1.0 - a * a)
    length = t * ct / b
    y = length * (a * ct - b * st)
    z = length * (a * st + b * ct)
    return y, z


class TestTiltedPlatePrism:
    @pytest.mark.parametrize("theta_deg", [-25.0, -10.0, 5.0, 10.0, 30.0])
    @pytest.mark.parametrize("n,t", [(1.5, 8.0), (1.7, 5.0), (1.5, 12.0)])
    def test_exit_matches_manual_snell(self, theta_deg, n, t):
        """Точка выхода и направление луча в стекле — ручной расчёт Снеллиуса."""
        img = 40.0
        s = _plate_system(theta_deg, t=t, img=img, n=n)
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success, f"error={r.error}"

        y_exp, z_exp = _manual_plate_exit(theta_deg, t, n)
        entry, exit_p, final = r.path[1], r.path[2], r.path[3]
        assert (exit_p[0], exit_p[1], exit_p[2]) == pytest.approx(
            (0.0, y_exp, z_exp), rel=1e-9)

        # внутри стекла: глобальное направление = R_x(θ)·(0, a, b)
        th = math.radians(theta_deg)
        a = math.sin(th) / n
        b = math.sqrt(1.0 - a * a)
        d_in = _dir_between(entry, exit_p)
        assert d_in == pytest.approx(
            (0.0, a * math.cos(th) - b * math.sin(th),
             a * math.sin(th) + b * math.cos(th)), rel=1e-9)

        # после пластины луч параллелен падающему и идёт вдоль Z до плоскости
        # изображения: y на изображении = y выхода
        assert _dir_between(exit_p, final) == pytest.approx((0.0, 0.0, 1.0))
        assert final == pytest.approx((0.0, y_exp, t + img), rel=1e-9)

    @pytest.mark.parametrize("theta_deg", [5.0, 10.0, 20.0, 35.0])
    def test_classic_slyusarev_displacement(self, theta_deg):
        """Модуль смещения — классическая формула параллельной пластины."""
        t, n = 8.0, TEST_N
        s = _plate_system(theta_deg, t=t, n=n)
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success

        th = math.radians(theta_deg)
        expected = t * math.cos(th) * math.sin(th) * (
            1.0 - math.cos(th) / math.sqrt(n * n - math.sin(th) ** 2))
        y_exit = r.path[2][1]
        assert abs(y_exit) == pytest.approx(expected, rel=1e-9)

    def test_exit_direction_parallel_to_incident(self):
        """Выходящий из призмы луч параллелен падающему (плоскопараллельность)."""
        s = _plate_system(15.0)
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success
        d = _dir_between(r.path[2], r.path[3])
        assert d == pytest.approx((0.0, 0.0, 1.0), abs=1e-12)

    def test_opl_positive(self):
        """OPL через пластину больше геометрического пути (n > 1)."""
        s = _plate_system(12.0, t=10.0)
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success
        geom = sum(
            math.dist(r.path[i], r.path[i + 1]) for i in range(3))
        assert r.opl > geom


# --------------------------------------------------------------------------- #
# C. Золотой тест: наклонное зеркало — отклонение 2θ
# --------------------------------------------------------------------------- #

class TestTiltedMirror:
    @pytest.mark.parametrize("theta_deg", [-15.0, 7.5, 30.0])
    def test_reflection_deviation_2theta(self, theta_deg):
        """Плоское зеркало, наклонённое на θ, отклоняет луч ровно на 2θ."""
        back = 20.0
        s = _base_system([
            Surface(radius=0.0, thickness=-back, glass='', semi_diameter=25.0,
                    is_reflective=True, tilt_x=theta_deg),
            # при 2θ=60° луч уходит на y = 20·tan60° ≈ 34.6 — нужен запас D/2
            Surface(radius=0.0, thickness=0.0, glass='', semi_diameter=60.0),
        ])
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success, f"error={r.error}"

        two_theta = math.radians(2.0 * theta_deg)
        expected = (0.0, math.sin(two_theta), -math.cos(two_theta))
        assert _dir_between(r.path[-2], r.path[-1]) == pytest.approx(
            expected, abs=1e-12)
        # точка падения на плоскость изображения: y = back·tan 2θ
        assert r.path[-1][1] == pytest.approx(back * math.tan(two_theta),
                                              rel=1e-9)
        assert r.path[-1][2] == pytest.approx(-back, abs=1e-9)

    def test_tilt_z_rotates_reflected_azimuth(self):
        """tilt_z поворачивает азимут отражённого луча: R = Rz(φ)·Rx(θ).

        Осьевой луч, зеркало с наклоном θ вокруг X и φ вокруг Z:
        отражённое направление Rz(φ)·(0, sin 2θ, −cos 2θ).
        """
        theta, phi = 20.0, 45.0
        s = _base_system([
            Surface(radius=0.0, thickness=-20.0, glass='', semi_diameter=25.0,
                    is_reflective=True, tilt_x=theta, tilt_z=phi),
            Surface(radius=0.0, thickness=0.0, glass='', semi_diameter=25.0),
        ])
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success

        two_theta = math.radians(2.0 * theta)
        p = math.radians(phi)
        expected = (-math.sin(p) * math.sin(two_theta),
                    math.cos(p) * math.sin(two_theta),
                    -math.cos(two_theta))
        assert _dir_between(r.path[-2], r.path[-1]) == pytest.approx(
            expected, abs=1e-12)

    def test_tilt_z_only_mirror_axis_invariant(self):
        """Поворот зеркала вокруг Z не меняет отражение осевого луча."""
        for phi in (0.0, 33.0, 90.0):
            s = _base_system([
                Surface(radius=0.0, thickness=-20.0, glass='',
                        semi_diameter=25.0, is_reflective=True, tilt_z=phi),
                Surface(radius=0.0, thickness=0.0, glass='', semi_diameter=25.0),
            ])
            r = trace_ray_through_system(s, _axial_ray(), WL)
            assert r.success
            assert _dir_between(r.path[-2], r.path[-1]) == pytest.approx(
                (0.0, 0.0, -1.0), abs=1e-12)


# --------------------------------------------------------------------------- #
# D. Золотой тест: децентрировка линзы — сдвиг изображения
# --------------------------------------------------------------------------- #

class TestDecenteredLens:
    def test_translation_invariance_axial(self):
        """Полностью децентрированная линза + сдвинутый луч = тот же путь.

        Физика трансляционно инвариантна: путь луча (0, dy, z) через
        линзу, децентрированную на dy, совпадает с путём осевого луча
        через центрированную линзу, сдвинутым на +dy (точно).
        """
        dy = 2.0
        r0 = trace_ray_through_system(_base_system(_lens(0.0)), _axial_ray(), WL)
        r1 = trace_ray_through_system(_base_system(_lens(dy)),
                                      _axial_ray(y=dy), WL)
        assert r0.success and r1.success
        assert len(r0.path) == len(r1.path)
        for p0, p1 in zip(r0.path, r1.path):
            assert p1[0] == pytest.approx(p0[0], abs=1e-9)
            assert p1[1] == pytest.approx(p0[1] + dy, abs=1e-9)
            assert p1[2] == pytest.approx(p0[2], abs=1e-9)

    def test_translation_invariance_off_axis(self):
        """То же для внеосевого (по высоте) луча — h = 3 мм."""
        dy, h = 2.0, 3.0
        r0 = trace_ray_through_system(_base_system(_lens(0.0)),
                                      _axial_ray(y=h), WL)
        r1 = trace_ray_through_system(_base_system(_lens(dy)),
                                      _axial_ray(y=h + dy), WL)
        assert r0.success and r1.success
        for p0, p1 in zip(r0.path, r1.path):
            assert p1[1] == pytest.approx(p0[1] + dy, abs=1e-9)

    def test_full_decenter_shifts_image_by_dy(self):
        """Полная децентрировка линзы смещает изображение ровно на dy
        (сравнение с центрированной системой на том же луче)."""
        dy = 2.0
        r0 = trace_ray_through_system(_base_system(_lens(0.0)),
                                      _axial_ray(y=3.0), WL)
        r1 = trace_ray_through_system(_base_system(_lens(dy)),
                                      _axial_ray(y=3.0 + dy), WL)
        assert r1.path[-1][1] - r0.path[-1][1] == pytest.approx(dy, abs=1e-9)

    def test_partial_decenter_changes_image(self):
        """Децентрировка только первой поверхности меняет изображение
        (луч видит другую зону линзы — кома/сдвиг)."""
        dy = 1.5
        surfaces = [
            Surface(radius=50.0, thickness=5.0, glass='К8',
                    semi_diameter=12.0, decenter_y=dy),
            Surface(radius=-200.0, thickness=90.0, glass='',
                    semi_diameter=12.0),
        ]
        r0 = trace_ray_through_system(_base_system(_lens(0.0)),
                                      _axial_ray(y=2.0), WL)
        r1 = trace_ray_through_system(_base_system(surfaces),
                                      _axial_ray(y=2.0), WL)
        assert r0.success and r1.success
        assert abs(r1.path[-1][1] - r0.path[-1][1]) > 1e-3


# --------------------------------------------------------------------------- #
# E. Снеллиус на наклонённой/смещённой сфере (векторная инварианта)
# --------------------------------------------------------------------------- #

class TestSnellOnTiltedSphere:
    def test_vector_snell_invariant(self):
        """n₁·d_t = n₂·d'_t на сфере с tilt_x/tilt_y/tilt_z и децентром.

        Нормаль вычисляется вручную: центр кривизны в глобальной СК —
        C = V + R·r(θ)·(0,0,1); путь луча — в глобальной СК.
        """
        n_glass = 1.6
        tilt = (8.0, -5.0, 17.0)
        dec = (0.6, -0.4)
        s = _base_system([
            Surface(radius=-80.0, thickness=50.0, glass='',
                    semi_diameter=25.0,
                    tilt_x=tilt[0], tilt_y=tilt[1], tilt_z=tilt[2],
                    decenter_x=dec[0], decenter_y=dec[1],
                    n_override={WL: n_glass}),
            Surface(radius=0.0, thickness=30.0, glass='', semi_diameter=25.0),
        ])
        d0 = (0.05, 0.12, 1.0)
        norm = math.sqrt(sum(v * v for v in d0))
        ray = Ray(x=0.0, y=0.0, z=-30.0,
                  k=d0[0] / norm, l=d0[1] / norm, m=d0[2] / norm)
        r = trace_ray_through_system(s, ray, WL)
        assert r.success, f"error={r.error}"

        hit = r.path[1]
        d_in = _dir_between(r.path[0], hit)
        d_out = _dir_between(hit, r.path[2])

        # центр кривизны: вершина V + R_surf · (матрица поворота · z)
        m = rotation_matrix(*tilt)
        axis = mat_vec(m, (0.0, 0.0, 1.0))
        vertex = (dec[0], dec[1], 0.0)
        center = tuple(vertex[i] + (-80.0) * axis[i] for i in range(3))
        nv = tuple(hit[i] - center[i] for i in range(3))
        nlen = math.sqrt(sum(v * v for v in nv))
        nhat = tuple(v / nlen for v in nv)

        def tangential(d, nn):
            dot = sum(d[i] * nn[i] for i in range(3))
            return tuple(1.0 * d[i] - dot * nn[i] for i in range(3))

        t_in = tangential(d_in, nhat)
        t_out = tangential(d_out, nhat)
        for i in range(3):
            assert 1.0 * t_in[i] == pytest.approx(n_glass * t_out[i], rel=1e-9)

    def test_hit_point_on_tilted_sphere_surface(self):
        """Точка попадания лежит на сфере (|hit − C| = |R| в глобальной СК)."""
        tilt = (12.0, -7.0, 0.0)
        dec = (0.8, 0.3)
        s = _base_system([
            Surface(radius=120.0, thickness=60.0, glass='',
                    semi_diameter=25.0,
                    tilt_x=tilt[0], tilt_y=tilt[1],
                    decenter_x=dec[0], decenter_y=dec[1]),
            Surface(radius=0.0, thickness=20.0, glass='', semi_diameter=25.0),
        ])
        r = trace_ray_through_system(s, _axial_ray(y=4.0), WL)
        assert r.success
        hit = r.path[1]
        m = rotation_matrix(*tilt)
        axis = mat_vec(m, (0.0, 0.0, 1.0))
        vertex = (dec[0], dec[1], 0.0)
        center = tuple(vertex[i] + 120.0 * axis[i] for i in range(3))
        dist = math.sqrt(sum((hit[i] - center[i]) ** 2 for i in range(3)))
        assert dist == pytest.approx(120.0, rel=1e-9)


# --------------------------------------------------------------------------- #
# F. Две поверхности с наклоном против ручного расчёта (одиночная призма)
# --------------------------------------------------------------------------- #

class TestSingleTiltedRefractingPlane:
    def test_direction_matches_manual(self):
        """Один наклонённый преломляющий торец: направление — Снеллиус вручную.

        Осевой луч, плоскость с tilt_x=θ, воздух→стекло n: локальное
        направление после преломления (0, sin θ/n, √(1−(sin θ/n)²)),
        глобальное — R_x(θ)·(0, a, b).
        """
        theta_deg, n = 18.0, TEST_N
        s = _base_system([
            Surface(radius=0.0, thickness=25.0, glass='', semi_diameter=25.0,
                    tilt_x=theta_deg, n_override={WL: n}),
            Surface(radius=0.0, thickness=20.0, glass='', semi_diameter=25.0),
        ])
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success

        th = math.radians(theta_deg)
        a = math.sin(th) / n
        b = math.sqrt(1.0 - a * a)
        expected = (0.0, a * math.cos(th) - b * math.sin(th),
                    a * math.sin(th) + b * math.cos(th))
        d = _dir_between(r.path[1], r.path[2])
        assert d == pytest.approx(expected, rel=1e-9)


# --------------------------------------------------------------------------- #
# G. NaN-безопасность: луч мимо поверхности — маркер «пропал», без крэша
# --------------------------------------------------------------------------- #

class TestMissSafety:
    def test_ray_missing_tilted_surface_marks_miss(self):
        """Луч мимо наклонённой сферы → success=False, error='MISS'."""
        s = _base_system([
            Surface(radius=5.0, thickness=50.0, glass='К8',
                    semi_diameter=4.0, tilt_x=35.0),
            Surface(radius=0.0, thickness=20.0, glass='', semi_diameter=25.0),
        ])
        # далёкий от вершины луч — пересечения со сферой R=5 нет
        r = trace_ray_through_system(s, _axial_ray(y=9.0), WL)
        assert r.success is False
        assert r.error == 'MISS'
        for p in r.path:
            assert all(math.isfinite(v) for v in p)

    def test_edge_clip_marks_edge(self):
        """Попадание за полудиаметром → 'EDGE', точка конечна."""
        s = _base_system([
            Surface(radius=0.0, thickness=50.0, glass='', semi_diameter=3.0),
            Surface(radius=0.0, thickness=20.0, glass='', semi_diameter=25.0),
        ])
        r = trace_ray_through_system(s, _axial_ray(y=5.0), WL)
        assert r.success is False
        assert r.error == 'EDGE'
        for p in r.path:
            assert all(math.isfinite(v) for v in p)

    def test_fan_tilted_system_no_crash(self):
        """trace_fan по системе с наклонами не падает; ошибки — только маркеры."""
        s = _base_system([
            Surface(radius=50.0, thickness=5.0, glass='К8',
                    semi_diameter=12.0, tilt_x=3.0, tilt_y=-2.0,
                    decenter_x=1.0, decenter_y=-0.5),
            Surface(radius=-200.0, thickness=90.0, glass='',
                    semi_diameter=12.0, tilt_x=-1.0, decenter_y=0.5),
        ])
        results = trace_fan(s, num_rays=9, pupil_range=1.0, wl=WL)
        assert len(results) == 9
        for res in results:
            assert isinstance(res.success, bool)
            for p in res.path:
                assert all(math.isfinite(v) for v in p)

    def test_tir_marks_tir(self):
        """Полное внутреннее отражение → 'TIR', без исключения.

        Вход в стекло по нормали (наклон 0), вторая грань наклонена на
        50° > arcsin(1/1.5) ≈ 41.8° → ПВО.
        """
        s = _base_system([
            Surface(radius=0.0, thickness=5.0, glass='', semi_diameter=25.0,
                    n_override={WL: 1.5}),
            Surface(radius=0.0, thickness=10.0, glass='', semi_diameter=25.0,
                    tilt_x=50.0),
        ])
        r = trace_ray_through_system(s, _axial_ray(), WL)
        assert r.success is False
        assert r.error == 'TIR'


# --------------------------------------------------------------------------- #
# H. Обратная совместимость: нули = прежнее поведение
# --------------------------------------------------------------------------- #

class TestBackwardCompatibility:
    def test_zero_fields_same_as_no_break(self):
        """Явные нули tilt/decenter дают тот же путь, что их отсутствие
        (быстрый путь тождественного излома)."""
        def build(with_zeros: bool) -> OpticalSystem:
            extra = dict(tilt_x=0.0, tilt_y=0.0, tilt_z=0.0,
                         decenter_x=0.0, decenter_y=0.0) if with_zeros else {}
            return _base_system([
                Surface(radius=50.0, thickness=5.0, glass='К8',
                        semi_diameter=12.0, **extra),
                Surface(radius=-200.0, thickness=90.0, glass='',
                        semi_diameter=12.0, **extra),
            ])

        r0 = trace_ray_through_system(build(False), _axial_ray(y=4.0), WL)
        r1 = trace_ray_through_system(build(True), _axial_ray(y=4.0), WL)
        assert r0.success and r1.success
        assert r0.path == r1.path
        assert r0.opl == r1.opl

    def test_demo_systems_still_trace(self):
        """Демо-системы (центрированные) трассируются успешно."""
        from domain.models import create_demo_system_by_name
        for name in ('achromat', 'cook_doublet', 'plano_convex', 'meniscus'):
            s = create_demo_system_by_name(name)
            r = trace_ray_through_system(s, _axial_ray(y=2.0), WL)
            assert r.success, f"{name}: {r.error}"
            for p in r.path:
                assert all(math.isfinite(v) for v in p)

    def test_default_surface_has_zero_spatial_params(self):
        """Surface() по умолчанию — нули (обратная совместимость модели)."""
        s = Surface()
        assert (s.tilt_x, s.tilt_y, s.tilt_z,
                s.decenter_x, s.decenter_y) == (0.0, 0.0, 0.0, 0.0, 0.0)
        assert not _has_coord_break(s)


# --------------------------------------------------------------------------- #
# I. Ячейки таблицы «наклон/децентр» (utils/optics_utils.py)
# --------------------------------------------------------------------------- #

class TestCoordCells:
    def test_format_zero(self):
        assert format_coord_cell((0.0, 0.0, 0.0)) == '0'
        assert format_coord_cell((0.0, 0.0)) == '0'

    def test_format_values(self):
        assert format_coord_cell((5.0, -2.0, 0.5)) == '5,-2,0.5'
        assert format_coord_cell((1.25, 0.0)) == '1.25,0'
        assert format_coord_cell((0.123456, 0.0, 0.0)) == '0.1235,0,0'

    def test_parse_basic(self):
        assert parse_coord_cell('5, -2, 0', 3) == (5.0, -2.0, 0.0)
        assert parse_coord_cell('0', 3) == (0.0, 0.0, 0.0)
        assert parse_coord_cell('', 3) == (0.0, 0.0, 0.0)

    def test_parse_semicolon_and_missing(self):
        assert parse_coord_cell('5;-2;0', 3) == (5.0, -2.0, 0.0)
        assert parse_coord_cell('1.5', 2) == (1.5, 0.0)
        assert parse_coord_cell('1,2,3,4', 3) == (1.0, 2.0, 3.0)

    def test_parse_garbage_raises(self):
        with pytest.raises(ValueError):
            parse_coord_cell('abc', 3)
        with pytest.raises(ValueError):
            parse_coord_cell('5,x', 2)

    def test_roundtrip(self):
        for vals in [(0.0, 0.0, 0.0), (5.0, -2.0, 0.5), (0.1, 0.0, 0.0)]:
            assert parse_coord_cell(format_coord_cell(vals), 3) == vals


# --------------------------------------------------------------------------- #
# J. JSON round-trip
# --------------------------------------------------------------------------- #

class TestJsonRoundTrip:
    def test_tilt_decenter_roundtrip(self, tmp_path):
        from fileio.json_io import save_json, load_json
        s = _base_system([
            Surface(radius=50.0, thickness=5.0, glass='К8',
                    tilt_x=5.0, tilt_y=-2.0, tilt_z=1.5,
                    decenter_x=1.0, decenter_y=-0.5),
            Surface(radius=0.0, thickness=90.0),
        ])
        path = tmp_path / "spatial.opal.json"
        save_json(s, str(path))
        loaded = load_json(str(path))
        a, b = s.surfaces[0], loaded.surfaces[0]
        assert (b.tilt_x, b.tilt_y, b.tilt_z) == (5.0, -2.0, 1.5)
        assert (b.decenter_x, b.decenter_y) == (1.0, -0.5)
        assert a.thickness == b.thickness

    def test_legacy_file_without_fields_defaults_zero(self, tmp_path):
        import json
        from fileio.json_io import load_json
        data = {
            "name": "legacy", "surfaces": [
                {"radius": 50.0, "thickness": 5.0, "glass": "",
                 "surface_type": "SPHERE"},
            ],
        }
        path = tmp_path / "legacy.opal.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        surf = load_json(str(path)).surfaces[0]
        assert (surf.tilt_x, surf.tilt_y, surf.tilt_z,
                surf.decenter_x, surf.decenter_y) == (0.0,) * 5


# --------------------------------------------------------------------------- #
# K. UI: колонки «Наклон X,Y,Z (°)» / «Децентр X,Y (мм)»
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestSurfaceTableSpatialColumns:
    def test_headers_present(self, qapp):
        from main import SurfaceTable
        t = SurfaceTable()
        headers = [t.horizontalHeaderItem(c).text()
                   for c in range(t.columnCount())]
        assert any("Наклон" in h for h in headers)
        assert any("Децентр" in h for h in headers)
        assert "Стоп" in headers[-1]  # стоп остался последней колонкой

    def test_load_and_read_back(self, qapp):
        from main import SurfaceTable
        from gui.controllers.system_controller import read_surface_table
        s = _base_system([
            Surface(radius=50.0, thickness=5.0, glass='К8',
                    semi_diameter=12.0, tilt_x=5.0, tilt_y=-2.5, tilt_z=1.0,
                    decenter_x=1.5, decenter_y=-0.75),
            Surface(radius=0.0, thickness=90.0, glass='', semi_diameter=12.0),
        ])
        t = SurfaceTable()
        t.load_system(s)
        cols = t._col_indices()
        assert t.item(0, cols['tilt']).text() == '5,-2.5,1'
        assert t.item(0, cols['dec']).text() == '1.5,-0.75'
        assert t.item(1, cols['tilt']).text() == '0'

        read_surface_table(t, s.surfaces)
        a = s.surfaces[0]
        assert (a.tilt_x, a.tilt_y, a.tilt_z) == (5.0, -2.5, 1.0)
        assert (a.decenter_x, a.decenter_y) == (1.5, -0.75)

    def test_edit_and_garbage_keeps_old(self, qapp):
        from main import SurfaceTable
        from gui.controllers.system_controller import read_surface_table
        s = _base_system(_lens())
        t = SurfaceTable()
        t.load_system(s)
        cols = t._col_indices()
        t.item(0, cols['tilt']).setText('3, 2')
        t.item(0, cols['dec']).setText('-1')
        read_surface_table(t, s.surfaces)
        assert (s.surfaces[0].tilt_x, s.surfaces[0].tilt_y,
                s.surfaces[0].tilt_z) == (3.0, 2.0, 0.0)
        assert (s.surfaces[0].decenter_x,
                s.surfaces[0].decenter_y) == (-1.0, 0.0)

        t.item(0, cols['tilt']).setText('abc')
        read_surface_table(t, s.surfaces)
        assert s.surfaces[0].tilt_x == 3.0  # мусор не меняет значение

    def test_radius_glass_still_read(self, qapp):
        """Общий читатель не сломал прежние колонки (R, d, стекло, D/2, k)."""
        from main import SurfaceTable
        from gui.controllers.system_controller import read_surface_table
        s = _base_system([
            Surface(radius=50.0, thickness=5.0, glass='К8',
                    semi_diameter=12.0, conic_constant=-1.0),
        ])
        t = SurfaceTable()
        t.load_system(s)
        read_surface_table(t, s.surfaces)
        a = s.surfaces[0]
        assert (a.radius, a.thickness, a.glass, a.semi_diameter) == \
            (50.0, 5.0, 'К8', 12.0)
        assert a.conic_constant == -1.0
        assert a.surface_type.name == 'CONIC'
