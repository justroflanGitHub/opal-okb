"""Тесты критериев оптимального фокуса OPAL (analysis/focus_criteria).

Проверяются требования TASK_FOCUS (B4):
1. min RMS(W) и max Штрель — близкие плоскости (±5 %);
2. min RMS пятна — другая плоскость (физика сферической);
3. зеркальность критериев по знаку дефокуса (на синтетике);
4. EQF конечен и лежит между min RMS(W) и зональным балансом.
"""
import math

import numpy as np
import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
from analysis import focus_criteria as fc
from analysis.aberrations import _hexapolar_points

WL_D = 0.58756


def build_doublet(aperture=16.0):
    """Склейка К8/TF5 с остаточной сферической (как в test_strehl)."""
    s = OpticalSystem(name='doublet')
    s.wavelengths = [Wavelength(WL_D, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5,
                semi_diameter=aperture / 2 + 2),
        Surface(radius=-60, glass='TF5', thickness=3,
                semi_diameter=aperture / 2 + 2),
        Surface(radius=-200, glass='', thickness=0,
                semi_diameter=aperture / 2 + 2),
    ]
    s.stop_surface = 1
    s.aperture_value = aperture
    return s


@pytest.fixture(scope='module')
def res16():
    """Сводка критериев: апертура 16 — умеренная сферическая (S ≈ 0.65)."""
    return fc.all_focus_criteria(build_doublet(16.0))


@pytest.fixture(scope='module')
def res20():
    """Сводка критериев: апертура 20 — сильная сферическая (W_edge ≈ −3λ)."""
    return fc.all_focus_criteria(build_doublet(20.0))


def test_min_rms_vs_max_strehl_close(res16):
    """Тест 1 ТЗ: min RMS(W) и max Штрель дают близкие плоскости (±5%).

    Ведём расчёт в режиме умеренной сферической (апертура 16,
    W_edge ≈ −1.3λ, S ≈ 0.65): здесь максимумы Штреля и минимум СКВ
    обязаны совпадать. При |W| ≳ 2λ (апертура 20) плоскости физически
    расходятся (~30 %) — многолепестковое PSF; см. докстринг модуля.
    """
    a = res16['min_rms_wavefront_mm']
    b = res16['max_strehl_mm']
    assert abs(a) > 1e-6
    assert abs(b - a) / abs(a) < 0.05


def test_min_spot_rms_differs_from_min_rms(res16):
    """Тест 2 ТЗ: min RMS пятна — иная плоскость, чем min RMS(W).

    Для недоисправленной сферической круг наименьшего рассеяния лежит
    между плоскостью min RMS(W) и зональным балансом 0.7.
    """
    a = res16['min_rms_wavefront_mm']
    s = res16['min_spot_rms_mm']
    z = res16['zone_best_mm']
    assert abs(s - a) / abs(a) > 0.05
    lo, hi = sorted((a, z))
    assert lo < s < hi


@pytest.fixture(scope='module')
def synthetic():
    """Синтетический волновой фронт b·ρ⁴ и его сдвиг на ±δ·ρ²."""
    pts = _hexapolar_points(30)
    rho2 = np.array([px * px + py * py for px, py in pts])
    w0 = 0.8 * rho2 ** 2
    delta = 0.37
    return pts, rho2, w0, delta


def test_defocus_symmetry(synthetic):
    """Тест 3 ТЗ: зеркальность по знаку дефокуса.

    Добавка ±δ·ρ² к волновому фронту сдвигает оптимум каждого критерия
    ровно на ∓δ (в волнах на краю зрачка): d*(W ± δρ²) = d*(W) ∓ δ.
    В миллиметрах это зеркально: Δz* сдвигается на ±8·F#²·λ·δ.
    """
    pts, rho2, w0, delta = synthetic

    def with_W(w):
        return [(px, py, wi) for (px, py), wi in zip(pts, w)]

    def optimum(w):
        p = with_W(w)
        d_rms = fc._defocus_min_rms(rho2, w)
        d_zone = fc._defocus_zone_balance(p, 30)
        d_strehl = fc._defocus_max_strehl(rho2, w, d_rms)[0]
        d_eqf = fc._eqf_defocus(p, 30, d_rms)['d']
        return {'min_rms': d_rms, 'zone': d_zone,
                'strehl': d_strehl, 'eqf': d_eqf}

    base = optimum(w0)
    for shift, sign in ((w0 + delta * rho2, -1.0), (w0 - delta * rho2, +1.0)):
        moved = optimum(shift)
        for key, tol in (('min_rms', 1e-9), ('zone', 1e-9),
                         ('strehl', 1e-3), ('eqf', 1e-6)):
            assert abs((moved[key] - base[key]) - sign * delta) < tol, \
                f'{key}: сдвиг {moved[key] - base[key]:+.6f} вместо {sign * delta:+.2f}'


def test_eqf_between_min_rms_and_zone(res20):
    """Тест 4 ТЗ: EQF конечен и лежит между min RMS(W) и зональным."""
    e = res20['eqf']
    assert e['converged']
    assert math.isfinite(e['dz_mm'])
    lo, hi = sorted((res20['min_rms_wavefront_mm'],
                     res20['zone_best_mm']))
    assert lo <= e['dz_mm'] <= hi
    # паритет зон достигнут: СКВ внутренней и внешней зоны равны
    assert abs(e['rms_in'] - e['rms_out']) < 1e-9
    # гипотеза задокументирована (код OPALO не разобран)
    assert 'REVERSE_OPALO' in e['hypothesis']


def test_all_summary_structure(res16, res20):
    """Сводка: полнота ключей, плоскость OPAL = EQF, метаданные масштаба."""
    for res in (res16, res20):
        for key in ('min_rms_wavefront_mm', 'max_strehl_mm', 'min_spot_rms_mm',
                    'zone_best_mm', 'eqf_mm', 'best_opal_mm'):
            assert math.isfinite(res[key])
        assert res['best_opal_mm'] == res['eqf_mm']
        assert res['best_opal_source'] == 'eqf'
        m = res['meta']
        assert m['f_number'] > 0
        assert m['num_rings'] == fc.FOCUS_RINGS
        # 1 + 3·N·(N+1) точек гексаполярной сетки
        assert m['num_points'] == 1 + 3 * fc.FOCUS_RINGS * (fc.FOCUS_RINGS + 1)
        assert m['mm_per_edge_wave'] > 0
    # согласованный масштаб: одна волна на краю = 8·F#²·λ
    m = res20['meta']
    assert m['mm_per_edge_wave'] == pytest.approx(
        8 * m['f_number'] ** 2 * m['wl_um'] * 1e-3, rel=1e-9)


def test_system_level_single_criteria(res16):
    """Отдельные функции согласованы со сводкой (одна конвенция Δz, мм)."""
    s = build_doublet(16.0)
    assert fc.focus_min_rms_wavefront(s, 0.0, WL_D) == \
        pytest.approx(res16['min_rms_wavefront_mm'], abs=1e-9)
    assert fc.focus_zone_best(s, 0.0, WL_D) == \
        pytest.approx(res16['zone_best_mm'], abs=1e-9)
    dz_eqf = fc.eqf(s, 0.0, WL_D)['dz_mm']
    assert dz_eqf == pytest.approx(res16['eqf_mm'], abs=1e-9)
    assert fc.focus_max_strehl(s, 0.0, WL_D) == \
        pytest.approx(res16['max_strehl_mm'], abs=1e-7)
    assert fc.focus_min_spot_rms(s, 0.0, WL_D) == \
        pytest.approx(res16['min_spot_rms_mm'], abs=1e-6)
