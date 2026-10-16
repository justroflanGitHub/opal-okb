# -*- coding: utf-8 -*-
"""Тесты базиса Цернике OPAL — 28 членов, n ≤ 12 (TASK_ZERN).

Базис работы WA/OPAVA (REVERSE_OPAVA.md §4: таблица пар в DGROUP:0B76,
ASCII «00 20 40 … 66») — только косинусные члены m ≥ 0 до n = 12,
азимут от меридиональной плоскости, нормировка Noll; МНК-разложение и
сверка со Штрелем (analysis/strehl.py — эталон):

* состав 28 членов и марки «C xIJ» (ANALIZE.DOC §5.2);
* ортогональность базиса на единичном круге (квадратура решётки);
* W = полином k-й степени → coeffs[k] ≈ 1, остальные ≈ 0;
* безаберрационная система (дублет D = 4 мм) → все ≈ 0;
* сферическая аберрация дублета: c[сфера] доминирует;
* strehl_from_zernike ↔ strehl.py: по точкам зрачка против Марешаля,
  по решётке против точного FFT (допуск 2 %);
* интеграция psf_mtf: zernike_decomposition / формат секции протокола.
"""
import math

import numpy as np
import pytest

from optics_engine import (ApertureType, FieldPoint, OpticalSystem, Surface,
                           Wavelength)
from analysis.aberrations import trace_wavefront_hexapolar
from analysis.strehl import compute_strehl
from analysis.zernike import (ZERNIKE_MARKS_28, ZERNIKE_TERMS_28,
                              fit_zernike, fit_zernike_points,
                              strehl_from_zernike, zernike_basis,
                              zernike_reconstruct)
from analysis.psf_mtf import (format_psf_mtf_section, format_zernike_section,
                              psf_grid, zernike_decomposition)

# Решётка квадратуры ортогональности: ошибка границы круга ~1/N,
# при 384 она ~6e-3 (допуск теста 2e-2 с трёхкратным запасом).
_ORTH_GRID = 384
_RECOVER_GRID = 256


def build_doublet(aperture: float = 20.0) -> OpticalSystem:
    """Контрольный дублет К8/TF5 (как в test_strehl/test_psf_mtf).

    Апертура 4 — почти безаберрационный; 7 — умеренные аберрации
    (S ≈ 0.99); 20 — сферическая аберрация доминирует.
    """
    s = OpticalSystem(name='doublet')
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5, semi_diameter=aperture / 2 + 2),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=aperture / 2 + 2),
        Surface(radius=-200, glass='', thickness=0, semi_diameter=aperture / 2 + 2),
    ]
    s.stop_surface = 1
    s.aperture_type = ApertureType.ENTRANCE_PUPIL
    s.aperture_value = aperture
    return s


def disk_grids(n: int):
    """Координаты и маска единичного круга на решётке n×n."""
    coords = np.linspace(-1.0, 1.0, n)
    gx, gy = np.meshgrid(coords, coords)
    mask = (gx ** 2 + gy ** 2) <= 1.0
    return gx, gy, mask


class TestBasis28:
    """Состав, марки и ортогональность базиса OPAL/OPAVA."""

    def test_terms_match_opava_table(self):
        """28 пар (n, m) — точно таблица DGROUP:0B76 работы OPAVA."""
        expected = [
            (0, 0), (2, 0), (4, 0), (6, 0), (8, 0), (10, 0), (12, 0),
            (1, 1), (3, 1), (5, 1), (7, 1), (9, 1), (11, 1),
            (2, 2), (4, 2), (6, 2), (8, 2), (10, 2),
            (3, 3), (5, 3), (7, 3), (9, 3),
            (4, 4), (6, 4), (8, 4),
            (5, 5), (7, 5),
            (6, 6),
        ]
        assert ZERNIKE_TERMS_28 == expected
        assert len(ZERNIKE_TERMS_28) == 28

    def test_terms_are_valid_zernike_pairs(self):
        """Все члены: 0 ≤ m ≤ n ≤ 12, n − m чётное (косинусные m ≥ 0)."""
        for n, m in ZERNIKE_TERMS_28:
            assert 0 <= m <= n <= 12
            assert (n - m) % 2 == 0

    def test_marks_cxij(self):
        """Марки «C xIJ» (I = n, J = m, hex-цифры как в OPAVA)."""
        assert ZERNIKE_MARKS_28[0] == 'C x00'
        assert ZERNIKE_MARKS_28[1] == 'C x20'    # расфокусировка
        assert ZERNIKE_MARKS_28[7] == 'C x11'    # дисторсия
        assert ZERNIKE_MARKS_28[8] == 'C x31'    # кома
        assert ZERNIKE_MARKS_28[-1] == 'C x66'
        assert 'C xB1' in ZERNIKE_MARKS_28       # n = 11 — hex B
        assert 'C xC0' in ZERNIKE_MARKS_28       # n = 12 — hex C

    def test_orthogonality_on_unit_disk(self):
        """Грам базиса на единичном круге ≈ единичная матрица (Noll)."""
        basis = zernike_basis(_ORTH_GRID)
        _, _, mask = disk_grids(_ORTH_GRID)
        Zm = basis[:, mask]
        gram = (Zm @ Zm.T) / mask.sum()
        diag_err = np.abs(np.diag(gram) - 1.0).max()
        offdiag = np.abs(gram - np.diag(np.diag(gram))).max()
        assert diag_err < 2e-2, f'СКВ членов ≠ 1: {diag_err:.2e}'
        assert offdiag < 2e-2, f'неортогональность: {offdiag:.2e}'

    def test_basis_zero_outside_disk(self):
        """Вне единичного круга базис обнулён (ρ¹² не «взрывается»)."""
        basis = zernike_basis(129)
        _, _, mask = disk_grids(129)
        outside = basis[:, ~mask]
        assert outside.shape[1] > 0
        assert np.abs(outside).max() == 0.0


class TestFitRecovery:
    """W = полином k-й степени → coeffs[k] ≈ 1, остальные ≈ 0."""

    @pytest.mark.parametrize('k', range(28))
    def test_single_term_recovery(self, k):
        """Каждый из 28 членов восстанавливается в себе (машина-точность)."""
        basis = zernike_basis(_RECOVER_GRID)
        _, _, mask = disk_grids(_RECOVER_GRID)
        coeffs, residual = fit_zernike(basis[k], mask)
        assert abs(coeffs[k] - 1.0) < 1e-8
        others = np.abs(np.delete(coeffs, k)).max()
        assert others < 1e-8, f'примесь других членов: {others:.2e}'
        assert residual < 1e-8

    def test_mixed_wavefront_recovery(self):
        """Смесь членов: коэффициенты восстанавливаются, реконструкция = W."""
        basis = zernike_basis(_RECOVER_GRID)
        _, _, mask = disk_grids(_RECOVER_GRID)
        target = [0.5, -0.25, 0.125, 0.0, 0.0625] + [0.0] * 23
        target[14] = -0.3                       # астигматизм-семейство m=2
        W = zernike_reconstruct(target, _RECOVER_GRID)
        coeffs, residual = fit_zernike(W, mask)
        np.testing.assert_allclose(coeffs, target, atol=1e-8)
        assert residual < 1e-8

    def test_points_fit_matches_grid_fit(self):
        """Точечная МНК (лучи) на решётке точек = решёточной подгонке."""
        basis = zernike_basis(_RECOVER_GRID)
        _, _, mask = disk_grids(_RECOVER_GRID)
        target = [0.4, 0.0, -0.2] + [0.0] * 25
        W = zernike_reconstruct(target, _RECOVER_GRID)
        coeffs_grid, _ = fit_zernike(W, mask)
        ys, xs = np.where(mask)
        coords = np.linspace(-1.0, 1.0, _RECOVER_GRID)
        points = [(coords[x], coords[y], W[y, x]) for y, x in zip(ys, xs)]
        coeffs_pts, _ = fit_zernike_points(points)
        np.testing.assert_allclose(coeffs_pts, coeffs_grid, atol=1e-10)

    def test_too_few_points_raises(self):
        """Точек зрачка меньше 28 → ValueError (а не тихий мусор)."""
        _, _, mask = disk_grids(5)   # ~21 точка внутри круга
        assert mask.sum() < 28
        with pytest.raises(ValueError):
            fit_zernike(np.zeros(mask.shape), mask)


class TestPortSystems:
    """Разложение реальных трассировок порта."""

    def test_unaberrated_system_all_zero(self):
        """Малая апертура (D = 4 мм) — аберрации ≈ 0, все 28 членов ≈ 0."""
        system = build_doublet(4.0)
        pts = trace_wavefront_hexapolar(system, wl=0.58756, field_y=0.0,
                                        num_rings=6)
        coeffs, _ = fit_zernike_points(pts)
        worst = float(np.abs(coeffs).max())
        assert worst < 0.01, f'безаберрационная система: |c|max = {worst:.4f}'

    def test_doublet_spherical_dominates(self):
        """Дублет D = 20 мм: сферическая C x40 доминирует над аберрациями.

        Дефокус (C x20) — плоскость установки, а не аберрация (OPAVA
        оптимизирует её отдельно, пункт меню BFP/ПНУ).
        """
        system = build_doublet(20.0)
        pts = trace_wavefront_hexapolar(system, wl=0.58756, field_y=0.0,
                                        num_rings=6)
        coeffs, residual = fit_zernike_points(pts)
        assert residual < 0.05, 'гладкий фронт дублета — малый остаток'
        idx = {t: i for i, t in enumerate(ZERNIKE_TERMS_28)}
        c_sphere = coeffs[idx[(4, 0)]]
        aberrations = [abs(c) for t, c in zip(ZERNIKE_TERMS_28, coeffs)
                       if t not in ((0, 0), (2, 0), (4, 0))]
        assert abs(c_sphere) > 0.05, 'сферическая аберрация ощутима'
        assert abs(c_sphere) > 2.0 * max(aberrations), \
            'сферическая должна доминировать с запасом'

    def test_strehl_vs_strehl_marechal(self):
        """strehl_from_zernike ↔ Марешаль strehl.py по точкам (допуск 2 %)."""
        system = build_doublet(7.0)
        st = compute_strehl(system, wl=0.58756, field_y=0.0)
        assert st['strehl_marechal'] is not None
        pts = trace_wavefront_hexapolar(system, wl=0.58756, field_y=0.0,
                                        num_rings=6)
        coeffs, _ = fit_zernike_points(pts)
        s_zern = strehl_from_zernike(coeffs)
        s_ref = st['strehl_marechal']
        assert abs(s_zern - s_ref) / s_ref < 0.02

    def test_strehl_vs_strehl_exact_fft(self):
        """Штрель из коэффициентов ↔ точный FFT strehl.py (та же решётка)."""
        system = build_doublet(7.0)
        st = compute_strehl(system, wl=0.58756, field_y=0.0)
        res = psf_grid(system, field_y=0.0, wl=0.58756)
        assert res['psf'] is not None
        coeffs, _ = fit_zernike(res['wavefront'], res['pupil_mask'])
        s_zern = strehl_from_zernike(coeffs)
        s_ref = st['strehl_exact']
        assert s_ref is not None
        assert abs(s_zern - s_ref) / s_ref < 0.02

    def test_strehl_pure_defocus_formula(self):
        """Чистый дефокус c = 0.1λ: S = exp(−(2π·0.1)²) точно."""
        coeffs = np.zeros(28)
        coeffs[1] = 0.1                      # C x20 — расфокусировка
        expected = math.exp(-((2.0 * math.pi * 0.1) ** 2))
        assert strehl_from_zernike(coeffs) == pytest.approx(expected, rel=1e-12)
        # пистон на Штрель не влияет
        coeffs[0] = 12.5
        assert strehl_from_zernike(coeffs) == pytest.approx(expected, rel=1e-12)


class TestPsfMtfIntegration:
    """Опция разложения в psf_mtf (печать коэффициентов как OPAVA WGLB)."""

    def test_decomposition_dict(self):
        """zernike_decomposition: 28 коэффициентов, марки, вклады ≈ 100 %."""
        dec = zernike_decomposition(build_doublet(7.0), field_y=0.0)
        assert dec['coeffs'] is not None
        assert len(dec['coeffs']) == 28
        assert dec['marks'][0] == 'C x00'
        assert 'Сферическая' in dec['names']
        assert dec['names'][0] == 'Пистон'
        shares = [s for s in dec['contributions_pct'] if s is not None]
        assert sum(shares) == pytest.approx(100.0, abs=0.5)
        assert dec['num_points'] > 0
        assert dec['sigma_w'] > 0.0

    def test_format_section(self):
        """Секция протокола: марки C xIJ, СКВ, Штрель — как OPAVA."""
        text = format_zernike_section(build_doublet(7.0), field_y=0.0)
        assert 'РАЗЛОЖЕНИЕ ЦЕРНИКЕ' in text
        assert 'C x40' in text and 'C x66' in text
        assert 'СКВ' in text and 'Штрель' in text
        assert 'C x20' in text          # дефокус печатается тоже

    def test_psf_section_option(self):
        """format_psf_mtf_section: опция zernike=True добавляет секцию."""
        system = build_doublet(7.0)
        plain = format_psf_mtf_section(system, field_y=0.0)
        with_zern = format_psf_mtf_section(system, field_y=0.0, zernike=True)
        assert 'ЦЕРНИКЕ' not in plain
        assert 'ЦЕРНИКЕ' in with_zern
        assert 'C x40' in with_zern
        assert with_zern.startswith(plain)   # ФРТ-часть не изменилась

    def test_empty_system(self):
        """Пустая система: coeffs = None, секции пустые."""
        dec = zernike_decomposition(OpticalSystem())
        assert dec['coeffs'] is None
        assert dec['reason']
        assert format_zernike_section(OpticalSystem()) == ''
