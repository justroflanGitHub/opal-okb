# -*- coding: utf-8 -*-
"""A4 (TASK_SEIDEL): реальное экранирование — зоны прохождения по всем
поверхностям + эллипс экранирования (ANALIZE.DOC §2.2.4.3, §4.4).

Система-зеркалка — Кассегрен со складкой (знаки толщин порта: после
отражения луч идёт к −z, вторичное зеркало между вершиной главного и
его фокусом): главное R=−400 (фокус 200), вторичное выпуклое R=−140 на
z=−150 (увеличение 3.5, efl=700, финальный фокус за вершиной главного
z=+25). k=0.3 моделирует «загораживание» (вторичное зеркало + отверстие).
"""
import pytest

from analysis.vignetting import find_passage_zones, real_obscuration
from domain.models import (ApertureType, FieldPoint, ObjectType,
                           OpticalSystem, Surface, Wavelength)


def _cass():
    """Кассегрен: k=0.3, апертура 18, вторичное sd=5 срезает поле 1.5°."""
    sysm = OpticalSystem(name='cass', object_type=ObjectType.INFINITE,
                         object_height=1.0)
    sysm.wavelengths = [Wavelength(0.54607)]
    sysm.field_points = [FieldPoint(0.0)]
    sysm.aperture_type = ApertureType.ENTRANCE_PUPIL
    sysm.aperture_value = 18.0
    sysm.obscuration_ratio = 0.3
    sysm.surfaces = [
        Surface(radius=-400.0, thickness=-150.0, glass='',
                semi_diameter=40.0, is_reflective=True),
        Surface(radius=-140.0, thickness=175.0, glass='',
                semi_diameter=5.0, is_reflective=True),
        Surface(radius=0.0, thickness=25.0, glass='', semi_diameter=25.0),
    ]
    sysm.stop_surface = 1
    return sysm


def _vig_lenses():
    """Линзовая система со стопом НЕ на первой поверхности (S3): первая
    линза (sd=5.6) срезает внеосевой пучок поля 3°, осевой проходит."""
    sysm = OpticalSystem(name='vig', object_type=ObjectType.INFINITE,
                         object_height=1.0)
    sysm.wavelengths = [Wavelength(0.54607)]
    sysm.field_points = [FieldPoint(0.0)]
    sysm.aperture_type = ApertureType.ENTRANCE_PUPIL
    sysm.aperture_value = 10.0
    sysm.surfaces = [
        Surface(radius=60.0, thickness=4.0, glass='К8', semi_diameter=5.6),
        Surface(radius=-35.0, thickness=15.0, glass='', semi_diameter=5.6),
        Surface(radius=0.0, thickness=25.0, glass='', semi_diameter=5.0),
        Surface(radius=50.0, thickness=4.0, glass='К8', semi_diameter=8.0),
        Surface(radius=-50.0, thickness=60.0, glass='', semi_diameter=8.0),
    ]
    sysm.stop_surface = 3
    return sysm


# ── тест 1: зеркальная система (obscuration 0.3) ────────────────────────────

def test_axial_zones_are_annuli_with_k_edge():
    """Осевой пучок: зоны — кольца, внутренний край = k (загораживание)."""
    zones = find_passage_zones(_cass(), 0.0)
    assert zones['n_blocked_launch'] > 0        # правило запуска |ρ| ≥ k
    assert zones['n_passed'] == zones['n_traced']
    s1, s2 = zones['surfaces'][0], zones['surfaces'][1]
    assert s1['outer'] == pytest.approx(9.0, abs=1e-6)      # полная апертура
    assert s1['inner'] == pytest.approx(2.7, abs=1e-6)      # k·радиус
    assert s1['center'] == pytest.approx(0.0, abs=1e-9)
    # вторичное зеркало: проекция кольца (линейное уменьшение 0.25)
    assert s2['outer'] == pytest.approx(2.25, abs=0.01)
    assert s2['inner'] == pytest.approx(0.675, abs=0.01)


def test_field_obscuration_ellipse_on_secondary():
    """Поле 1.5°: зона на вторичном зеркале — эксцентричное кольцо,
    срезанное кромкой (код 'M'), эллипс экранирования смещён."""
    zones = find_passage_zones(_cass(), 1.5)
    assert zones['n_passed'] < zones['n_traced']
    s2 = zones['surfaces'][1]
    assert s2['blocked_here'] > 0
    assert s2['limit'] == ('M', 2)              # зеркало-экран №2
    assert s2['inner'] > 1.0                    # кольцо: ось не проходит
    assert s2['center'] == pytest.approx(3.29, abs=0.3)     # смещён
    assert s2['crossed'][1] > s2['passed'][1] + 0.5         # верх срезан


def test_real_obscuration_ellipse_and_cutters():
    """Эллипс на входном зрачке: осевой — круг k; поле — эллипс со
    смещением, срезающая поверхность ('M', 2)."""
    axial = real_obscuration(_cass(), 0.0)
    assert axial['outer_semi_y'] == pytest.approx(9.0, abs=1e-6)
    assert axial['outer_semi_x'] == pytest.approx(9.0, abs=1e-6)
    assert axial['inner_semi_y'] == pytest.approx(2.7, abs=1e-6)
    assert axial['obscuration_fraction'] == pytest.approx(0.09, abs=1e-4)
    assert axial['cutters'] == []
    assert axial['minimal_obscuration'] == pytest.approx(0.3, abs=0.01)

    field = real_obscuration(_cass(), 1.5)
    assert field['outer_semi_y'] < field['outer_semi_x'] - 1.0   # эллипс
    assert abs(field['outer_shift_y']) > 1.0                     # смещён
    assert ('M', 2) in field['cutters']


# ── тест 3: «полные габариты» vs «габариты экранов» ─────────────────────────

def test_full_dimensions_vs_screen_dimensions():
    """Полные габариты (TABBEA) — весь зрачок 18; габариты экранов
    (TABEAP) — центральный экран k=0.3 → 5.4; у линз без экрана — 0."""
    r = real_obscuration(_cass(), 0.0)
    assert r['full_diameter_y'] == pytest.approx(18.0, abs=1e-6)
    assert r['screen_diameter_y'] == pytest.approx(5.4, abs=1e-6)
    assert r['screen_diameter_y'] < 0.5 * r['full_diameter_y']

    r2 = real_obscuration(_vig_lenses(), 0.0)     # k=0: экрана нет
    assert r2['screen_diameter_y'] == 0.0
    assert r2['minimal_obscuration'] == 0.0
    assert r2['full_diameter_y'] == pytest.approx(10.0, abs=0.1)


# ── тест 2: внеосевой пучок уже осевого на первой линзе ─────────────────────

def test_field_zones_narrower_on_first_lens():
    """Поле 3°: зона прохождения на первой линзе уже осевой (виньетирование
    кромкой, код 'P'); осевой пучок не срезан."""
    system = _vig_lenses()
    axial = find_passage_zones(system, 0.0)
    field = find_passage_zones(system, 3.0)
    s1a, s1f = axial['surfaces'][0], field['surfaces'][0]
    width_axial = s1a['passed'][1] - s1a['passed'][0]
    width_field = s1f['passed'][1] - s1f['passed'][0]
    assert width_axial == pytest.approx(10.0, abs=0.1)
    assert width_field < width_axial - 0.5
    assert s1a['blocked_here'] == 0
    assert s1f['blocked_here'] > 0
    assert s1f['limit'] == ('P', 1)


def test_passage_zones_empty_system():
    """Пустая система — пустые зоны без трассировки."""
    zones = find_passage_zones(OpticalSystem(name='empty'), 0.0)
    assert zones['surfaces'] == []
    assert zones['n_traced'] == 0
    assert real_obscuration(OpticalSystem(name='empty'), 0.0)[
        'full_diameter_y'] == 0.0
