"""Регресс-тест бага зеркальной опорной сферы (волна 10, 2026-10-16).

Баг: _reference_sphere строила центр сферы сравнения как last+bfd без учёта
обратного хода после нечётного числа отражений — для зеркала фокус
оказывался в +z (зеркально-неверном) полупространстве, W на оси у
идеального параболоида давала сатурацию ~-0.25 мм на rho=1 (дефокусная
парабола -k*rho^2), штрели/Цернике/PSF зеркальных систем были мусором.

Фикс: нечётное число отражений → cz = last - bfd (конвенция трейсера).
"""
import math

import pytest

from domain.models import OpticalSystem, Surface, Wavelength
from analysis.aberrations import trace_wavefront_hexapolar
from analysis.strehl import compute_strehl


def _parabola_system():
    """Идеальный параболоид F=100, D=20 (вогнутое зеркало, R<0, k=-1)."""
    s = Surface(radius=-200.0, thickness=-100.0, semi_diameter=10.0,
                conic_constant=-1.0, is_reflective=True)
    sysm = OpticalSystem(name='parab-regress', surfaces=[s])
    sysm.wavelengths = [Wavelength(0.5876)]
    return sysm


def test_parabola_wavefront_zero_on_axis():
    """W идеального параболоида на оси == 0 во всех кольцах (≤0.01λ)."""
    pts = trace_wavefront_hexapolar(_parabola_system(), num_rings=4)
    assert len(pts) >= 60
    for px, py, w in pts:
        assert abs(w) < 0.01, f'W={w}λ при зрачке ({px},{py}) — дефокус сферы вернулся'


def test_parabola_wavefront_monotone_free_of_saturation():
    """Нет сатурации W (равные средние соседних колец от ветвления сферы)."""
    pts = trace_wavefront_hexapolar(_parabola_system(), num_rings=4)
    import collections
    by_rho = collections.defaultdict(list)
    for px, py, w in pts:
        by_rho[round(math.hypot(px, py), 2)].append(w)
    rhos = sorted(by_rho)
    assert len(rhos) >= 4
    means = [sum(by_rho[r]) / len(by_rho[r]) for r in rhos]
    # все ≈ 0 → разброс мал
    assert max(abs(m) for m in means) < 0.01


def test_parabola_strehl_near_one():
    """Штрель идеального параболоида ≈ 1 (раньше — мусор из-за сферы)."""
    res = compute_strehl(_parabola_system())
    st = res.get('strehl_exact', res.get('strehl_marechal', 0)) if isinstance(res, dict) else res
    assert st > 0.95, f'Штрель {st} — сфера сравнения всё ещё неверна'


def test_cassegrain_wavefront_finite_sane():
    """Кассегрен (чётное число зеркал): W конечен и без дефокус-параболы."""
    sysm = OpticalSystem(name='cass-regress', surfaces=[
        Surface(radius=-400.0, thickness=-150.0, semi_diameter=40.0,
                is_reflective=True),
        Surface(radius=-140.0, thickness=175.0, semi_diameter=5.0,
                is_reflective=True),
        Surface(radius=0.0, thickness=25.0, semi_diameter=25.0),
    ])
    sysm.wavelengths = [Wavelength(0.54607)]
    pts = trace_wavefront_hexapolar(sysm, num_rings=3)
    assert pts, 'нет точек W'
    for px, py, w in pts:
        assert math.isfinite(w), f'W={w} не конечен'


def test_cassegrain_wrong_thickness_diagnosed_not_silent():
    """Инвертированная толщина зеркала — диагностика MISS, не молчаливый пропуск.

    Баг: при недостижимой поверхности за спиной луча трейсер делал
    continue (success=True, err=None) и «терял» вторичное зеркало
    Кассегрена без каких-либо признаков ошибки.
    """
    from analysis.ray_tracing import trace_ray_through_system, Ray
    sysm = OpticalSystem(name='cass-badthick', surfaces=[
        Surface(radius=-400.0, thickness=150.0, semi_diameter=40.0,
                is_reflective=True),   # +150 вместо -150
        Surface(radius=-140.0, thickness=175.0, semi_diameter=5.0,
                is_reflective=True),
        Surface(radius=0.0, thickness=25.0, semi_diameter=25.0),
    ])
    sysm.wavelengths = [Wavelength(0.54607)]
    ray = Ray(x=0.0, y=5.0, z=-1000.0, k=0.0, l=0.0, m=1.0)
    res = trace_ray_through_system(sysm, ray, wl=0.54607)
    assert not res.success, 'ошибочная геометрия помечена успехом'
    assert res.error == 'MISS'
    assert res.surfaces_hit < 3


def test_virtual_reference_plane_still_skipped():
    """Легитимные виртуальные reference-плоскости (R=0, без стекла) — по-прежнему
    пропускаются без ошибки (регресс на регресс: не сломать лазерные системы)."""
    from analysis.ray_tracing import trace_ray_through_system, Ray
    sysm = OpticalSystem(name='virt-ref', surfaces=[
        Surface(radius=-200.0, thickness=-100.0, semi_diameter=10.0,
                conic_constant=-1.0, is_reflective=True),
        Surface(radius=0.0, thickness=-50.0, semi_diameter=8.0),  # виртуальная пл.
    ])
    sysm.wavelengths = [Wavelength(0.5876)]
    ray = Ray(x=0.0, y=3.0, z=-500.0, k=0.0, l=0.0, m=1.0)
    res = trace_ray_through_system(sysm, ray, wl=0.5876)
    assert res.success and res.error is None, \
        f'виртуальная плоскость перестала пропускаться: {res.error}'
