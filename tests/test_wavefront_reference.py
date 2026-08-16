"""Регрессионные тесты опорной сферы волновой аберрации.

Общая логика замыкания лучей на опорную сферу
(``_reference_sphere`` / ``_air_exit_direction`` /
``_opl_to_reference_sphere``) используется веером аберраций,
гексаполярной сеткой зрачка и разложением Цернике. Тесты проверяют:

- геометрию замыкания (точка на сфере / до сферы / промах);
- направление выхода луча в воздух при нулевом отрезке до плоскости
  изображения (преломление на последней поверхности);
- независимую проверку масштаба W: OPD до фокуса по Ферма́ту против
  W на опорной сфере (порядок долей λ, а не сотен λ и не 10⁻³ λ);
- согласованность веера и гексаполярной сетки (одна и та же физика).
"""
import math

import pytest

from optics_engine import (OpticalSystem, Surface, Wavelength, FieldPoint,
                           paraxial_trace)
from ray_tracing import Ray, trace_ray_through_system
from optics_utils import compute_z_positions, get_effective_aperture, make_field_ray
import aberrations as ab
from aberrations import trace_aberration_fan, trace_wavefront_hexapolar


def build_achromat(last_thickness: float = 0.0) -> OpticalSystem:
    """Дублет с нулевым (по умолчанию) отрезком до плоскости изображения."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=last_thickness),
    ]
    return s


def _focus_z(s: OpticalSystem) -> float:
    parax = paraxial_trace(s)
    z_pos = compute_z_positions(s)
    return z_pos[-2] + parax['back_focal_distance']


class TestOplToReferenceSphere:
    """Геометрия замыкания на опорную сферу вдоль луча."""

    CENTER = (0.0, 0.0, 100.0)
    R = 100.0

    def test_point_on_sphere_no_addition(self):
        # точка ровно на сфере, луч вдоль оси к центру — L = 0
        assert ab._opl_to_reference_sphere(
            5.0, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), self.CENTER, self.R) == 5.0

    def test_point_before_sphere(self):
        # точка на оси за 20 мм до сферы, луч к центру — прибавляется 20
        assert ab._opl_to_reference_sphere(
            5.0, (0.0, 0.0, -20.0), (0.0, 0.0, 1.0),
            self.CENTER, self.R) == pytest.approx(25.0)

    def test_point_inside_sphere_backtracks(self):
        # точка внутри сферы — ближняя сторона сферы позади, L < 0
        opl = ab._opl_to_reference_sphere(
            5.0, (0.0, 0.0, 50.0), (0.0, 0.0, 1.0), self.CENTER, self.R)
        assert opl == pytest.approx(-45.0)  # 5 + (50 − 100)

    def test_miss_returns_none(self):
        # параллельный оси луч на высоте > R не пересекает сферу
        assert ab._opl_to_reference_sphere(
            5.0, (0.0, 150.0, -50.0), (0.0, 0.0, 1.0),
            self.CENTER, self.R) is None


class TestAirExitDirection:
    def test_image_plane_segment_is_air(self):
        """Ненулевой отрезок до плоскости изображения: направление —
        последний сегмент пути (воздух)."""
        s = build_achromat(last_thickness=2.0)
        ray = Ray(x=0, y=5.0, z=-15.0, k=0, l=0, m=1)
        res = trace_ray_through_system(s, ray, 0.58756)
        d = ab._air_exit_direction(s, res, 0.58756)
        p0, p1 = res.path[-2], res.path[-1]
        norm = math.dist(p0, p1)
        expected = ((p1[0] - p0[0]) / norm, (p1[1] - p0[1]) / norm,
                    (p1[2] - p0[2]) / norm)
        assert d == pytest.approx(expected)

    def test_zero_thickness_refracts_to_focus(self):
        """Нулевой отрезок до плоскости изображения: направление
        преломляется на последней поверхности — луч пересекает ось
        вблизи параксиального фокуса (продольная сферическая
        аберрация мала), а не вдвое дальше (непреломлённый ход)."""
        s = build_achromat(last_thickness=0.0)
        focus = _focus_z(s)
        ray = Ray(x=0, y=5.0, z=-15.0, k=0, l=0, m=1)
        res = trace_ray_through_system(s, ray, 0.58756)
        k, l, m = ab._air_exit_direction(s, res, 0.58756)
        # пересечение с осью
        assert l < 0
        t = -res.path[-1][1] / l
        z_cross = res.path[-1][2] + t * m
        assert abs(z_cross - focus) < 0.5


class TestWavefrontScale:
    """Масштаб W: согласование с независимой OPD до фокуса (Ферма)."""

    def _fermant_w(self, s: OpticalSystem, wl: float, px: float,
                   py: float) -> float:
        """W по Ферма́ту: OPL вдоль луча до плоскости параксиального
        фокуса минус OPL главного луча (независимое замыкание —
        проекция на направление луча, без опорной сферы)."""
        parax = paraxial_trace(s)
        z_start, z_pupil = ab._compute_ray_start(s, parax)
        aperture = get_effective_aperture(s, default=10.0)
        focus = _focus_z(s)

        def opl_to_focus_plane(pupil_x: float, pupil_y: float) -> float:
            ray = make_field_ray(s, pupil_x, pupil_y, 0.0, z_start, z_pupil)
            res = trace_ray_through_system(s, ray, wl)
            k, l, m = ab._air_exit_direction(s, res, wl)
            p = res.path[-1]
            return res.opl + (focus - p[2]) / m

        chief = opl_to_focus_plane(0.0, 0.0)
        return (opl_to_focus_plane(px * aperture / 2, py * aperture / 2)
                - chief) / (wl * 1e-3)

    @pytest.mark.parametrize('last_thickness', [0.0, 2.0])
    def test_hexapolar_matches_fermat(self, last_thickness):
        """W на опорной сфере ≈ OPD до фокуса по Ферма́ту: различие —
        конструктивная поправка сферы/плоскости, доли λ. Ловит и
        ошибку масштаба (×10⁻³), и промах замыкания (сотни λ)."""
        s = build_achromat(last_thickness=last_thickness)
        wl = 0.58756
        points = trace_wavefront_hexapolar(s, wl=wl, field_y=0.0,
                                           num_rings=4)
        assert points
        rim = [(px, py, w) for px, py, w in points
               if abs(math.hypot(px, py) - 1.0) < 1e-9]
        assert rim
        for px, py, w in rim:
            w_fermat = self._fermant_w(s, wl, px, py)
            # порядок величины — скорректированная система
            assert abs(w_fermat) < 5.0
            assert abs(w) < 5.0
            assert abs(w - w_fermat) < 1.0


class TestFanHexapolarConsistency:
    def test_axial_fan_matches_hexapolar(self):
        """Веер (меридиональное сечение) и гексаполярная сетка — одна
        физика: W совпадает в общих меридиональных точках зрачка
        (px = 0)."""
        s = build_achromat()
        wl = 0.58756
        fan = {round(r['pupil_y'], 9): r['wave']
               for r in trace_aberration_fan(s, wl, num_rays=9, field_y=0.0)}
        hexa = {(round(px, 9), round(py, 9)): w for px, py, w
                in trace_wavefront_hexapolar(s, wl=wl, field_y=0.0,
                                             num_rings=2)}
        # кольцо 2 гексаполярной сетки содержит меридиональные точки
        # (0, ±1); веер с num_rays=9 — те же pupil_y = ±1
        common = [(px, py) for (px, py) in hexa if px == 0.0 and py in fan]
        assert common
        for px, py in common:
            assert hexa[(px, py)] == pytest.approx(fan[py], abs=1e-9)
