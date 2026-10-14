"""Тесты следа Коддингтона и радиусов каустик (TASK_CODDINGTON).

Проверяемое — реверс OPAL §7-8 (analysis/REVERSE_TRACE.md):

- Z'm/Z's из дифференциального следа (FUN_1000_93f3/9897,
  0x193F3/0x19897; выход h/u — 0x1971D/0x197BA, отсчёт от опорной
  плоскости — 0x19976) ↔ :func:`aberrations.coddington_trace`;
- радиусы каустики 2-го порядка (0x19739-0x197F7, 0x19C39-0x19CB1;
  нормировка [0x3A10] ≈ 100/f′) ↔ :func:`aberrations.caustic_radii`.

Системы: каталога ``tests/fixtures`` в проекте нет — используются
встроенные системы (как в остальных тестах анализа) и золотая
эталонная фикстура «Индустар-23у» из ``conftest.py`` (LENS.LBO,
сферическая оптика), т.е. все доступные фикстуры со сферической
оптикой.
"""
import copy
import math

import pytest

from optics_engine import (OpticalSystem, Surface, Wavelength, FieldPoint,
                           paraxial_trace)
from optics_utils import compute_z_positions, get_effective_aperture
from aberrations import coddington_trace, caustic_radii, \
    compute_field_aberrations

# Сужение веера для сравнения с дифференциальным следом: 20% апертуры
# (сферическая аберрация веера ∝ h², при сужении веер сходится к следу)
FAN_NARROW_FRAC = 0.2
# Допуски из задания: z_m/z_s — 5%, астигматизм — 10% + знак
TOL_Z_REL = 0.05
TOL_AST_REL = 0.10


def build_biconvex() -> OpticalSystem:
    """Одиночная положительная линза K8 (сильные аберрации)."""
    s = OpticalSystem()
    s.name = 'biconvex'
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=5.0)]
    s.aperture_value = 20.0
    s.surfaces = [
        Surface(radius=100, glass='K8', thickness=6, semi_diameter=12),
        Surface(radius=-100, glass='', thickness=90, semi_diameter=12),
    ]
    return s


def build_achromat() -> OpticalSystem:
    """Дублет K8/TF5 (хроматически скорректированная сферика)."""
    s = OpticalSystem()
    s.name = 'achromat'
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=5.0)]
    s.aperture_value = 20.0
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5, semi_diameter=12),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=12),
        Surface(radius=-200, glass='', thickness=90, semi_diameter=12),
    ]
    return s


BUILDERS = {'biconvex': build_biconvex, 'achromat': build_achromat}


def narrowed(system: OpticalSystem, frac: float) -> OpticalSystem:
    """Копия системы с суженной апертурой (сужение веера)."""
    s = copy.deepcopy(system)
    eff = get_effective_aperture(system, default=10.0)
    s.aperture_value = eff * frac
    return s


class TestCoddingtonFanConvergence:
    """Сходимость следа Коддингтона с веером compute_field_aberrations."""

    @pytest.mark.parametrize('name', ['biconvex', 'achromat'])
    def test_inline_systems(self, name):
        system = BUILDERS[name]()
        self._check_convergence(system, field_y=5.0)

    def test_industar_half_field(self, industar23u):
        """Индустар-23у на половине поля (26°/2): крайнее поле
        завиньетировано для суженного сагиттального веера."""
        self._check_convergence(industar23u,
                                field_y=max(abs(fp.y) for fp in
                                            industar23u.field_points) / 2.0)

    @staticmethod
    def _check_convergence(system, field_y):
        cod = coddington_trace(system, field_y=field_y)
        assert cod['z_m'] is not None and cod['z_s'] is not None

        for frac in (1.0, FAN_NARROW_FRAC):
            fan = compute_field_aberrations(
                narrowed(system, frac), field_points=[(field_y,)])[0]
            assert fan['z_m'] is not None, f'веер x{frac} не прошёл'
            img_z = compute_z_positions(system)[-1]
            z_fan_m = img_z + fan['z_m']
            z_fan_s = img_z + fan['z_s']
            # фокусы: 5% при любой ширине веера
            assert abs(cod['z_m'] - z_fan_m) < TOL_Z_REL * abs(z_fan_m), \
                f'z_m x{frac}: коддингтон {cod["z_m"]:.4f} vs веер {z_fan_m:.4f}'
            assert abs(cod['z_s'] - z_fan_s) < TOL_Z_REL * abs(z_fan_s), \
                f'z_s x{frac}: коддингтон {cod["z_s"]:.4f} vs веер {z_fan_s:.4f}'
            if frac == FAN_NARROW_FRAC:
                # астигматизм: знак + величина в пределах 10% на суженном веере
                ast_fan = fan['astigmatism']
                assert ast_fan * cod['astigmatism'] > 0, 'знак астигматизма'
                assert abs(cod['astigmatism'] - ast_fan) \
                    < TOL_AST_REL * abs(ast_fan), \
                    (f'астигматизм: коддингтон {cod["astigmatism"]:.4f} '
                     f'vs веер {ast_fan:.4f}')


class TestCoddingtonAxial:
    """Осевой случай: след Коддингтона = параксиальный расчёт.

    На оси i = r = 0 на каждой поверхности, уравнения вырождаются в
    параксиальную рекурренность: t_m = t_s = задний фокальный отрезок
    (фокусное расстояние от последней поверхности для предмета в ∞),
    астигматизм нулевой.
    """

    AXIAL_REL_TOL = 1e-6

    @pytest.mark.parametrize('name', ['biconvex', 'achromat'])
    def test_inline_systems(self, name):
        self._check_axial(BUILDERS[name]())

    def test_industar(self, industar23u):
        self._check_axial(industar23u)

    @staticmethod
    def _check_axial(system):
        parax = paraxial_trace(system)
        bfd = parax['back_focal_distance']
        assert abs(bfd) > 1.0

        cod = coddington_trace(system, field_y=0.0)
        assert cod['t_m'] is not None and cod['t_s'] is not None
        # t_m == t_s == фокусный отрезок (до 1e-6 отн.)
        assert cod['t_m'] == pytest.approx(cod['t_s'], rel=1e-9)
        assert cod['t_m'] == pytest.approx(bfd, rel=1e-6), \
            f't_m={cod["t_m"]:.6f} vs BFD={bfd:.6f}'
        # астигматизм на оси нулевой, отсчёт от плоскости изображения
        assert cod['astigmatism'] == pytest.approx(0.0, abs=1e-9)
        assert cod['delta_zm'] == pytest.approx(cod['z_m'] - compute_z_positions(system)[-1])


class TestCausticRadii:
    """Радиусы каустик: знаки, симметрия, поведение при диафрагмировании."""

    def test_positive_lens_positive_radius(self):
        """Положительная линза: R > 0, центр кривизны за фокусом."""
        r = caustic_radii(build_biconvex(), field_y=0.0)
        assert r['method'] == 'coddington'
        assert r['r_m'] > 0.0
        assert r['r_s'] > 0.0
        # осевой пучок: меридиональная и сагиттальная каустики совпадают
        assert r['r_m'] == pytest.approx(r['r_s'], rel=1e-6)

    def test_normalization_percent(self):
        """r_rel = r/f'·100 — нормировка OPAL [0x3A10] ≈ 100/f′."""
        system = build_biconvex()
        r = caustic_radii(system, field_y=0.0)
        efl = paraxial_trace(system)['focal_length']
        assert r['r_m_rel'] == pytest.approx(r['r_m'] / efl * 100.0)
        assert r['r_s_rel'] == pytest.approx(r['r_s'] / efl * 100.0)

    def test_symmetry_z_plus_minus(self):
        """Осевой пучок: z(δ) = z(−δ) точно (зеркальная симметрия)."""
        r = caustic_radii(build_biconvex(), field_y=0.0)
        scale = 1.0 + abs(r['z_m0'])
        assert abs(r['z_m_plus'] - r['z_m_minus']) < 1e-6 * scale
        assert abs(r['z_s_plus'] - r['z_s_minus']) < 1e-6 * scale
        # сагиттальное сечение симметрично и для косого пучка
        r_field = caustic_radii(build_biconvex(), field_y=5.0)
        assert abs(r_field['z_s_plus'] - r_field['z_s_minus']) \
            < 1e-6 * (1.0 + abs(r_field['z_s0']))

    def test_radius_grows_when_stopping_down(self):
        """Диафрагмирование: R растёт, каустика сплющивается.

        Лучи на краю закрытого зрачка попадают в параксиальную зону:
        R(δ = 0.5·r_зрачка) монотонно растёт к пределу R(δ→0).
        """
        system = build_biconvex()
        pupil_r = get_effective_aperture(system, default=10.0) / 2.0
        radii = []
        for frac in (1.0, 0.5, 0.25):
            stopped = narrowed(system, frac)
            r = caustic_radii(stopped, field_y=0.0,
                              ray_halfheight=0.5 * pupil_r * frac)
            assert r['r_m'] is not None
            radii.append(r['r_m'])
        assert radii[1] > radii[0], 'R должен расти при закрытии зрачка'
        assert radii[2] > radii[1]
        # предел — параксиальная каустика (δ = 1% зрачка)
        limit = caustic_radii(system, field_y=0.0)['r_m']
        assert radii[2] < limit or radii[2] == pytest.approx(limit, rel=1e-3)

    def test_explicit_halfheight_matches_default_scale(self):
        """Явный ray_halfheight эквивалентен умолчанию (1% зрачка)."""
        system = build_biconvex()
        r_default = caustic_radii(system, field_y=0.0)
        r_explicit = caustic_radii(
            system, field_y=0.0,
            ray_halfheight=0.01 * get_effective_aperture(system) / 2.0)
        assert r_explicit['r_m'] == pytest.approx(r_default['r_m'])

    def test_industar_axial(self, industar23u):
        r = caustic_radii(industar23u, field_y=0.0)
        assert r['method'] == 'coddington'
        assert r['r_m'] > 0.0
        assert r['r_s'] > 0.0
