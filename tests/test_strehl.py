"""Тесты числа Штреля (TASK_3D, часть 1).

Марешаль ``S = exp(−(2πσ)²)`` и точный Strehl через FFT PSF:
монотонность по σ, согласие двух способов при S > 0.3, идеальный
фронт (S = 1 ± eps), полихроматическое взвешенное среднее и
форматирование для GUI.
"""
import math

import numpy as np
import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
from analysis.strehl import (
    compute_strehl,
    strehl_marechal,
    strehl_exact_from_wavefront,
    format_strehl,
    strehl_tooltip,
    _strehl_validity,
    STREHL_GOOD_MIN,
    STREHL_MARECHAL_LIMIT_MIN,
)


def build_doublet(aperture: float = 20.0,
                  wls=None) -> OpticalSystem:
    """Контрольный дублет К8/TF5 (как в test_spot_rms_xy)."""
    s = OpticalSystem(name='doublet')
    s.wavelengths = wls if wls else [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5, semi_diameter=aperture / 2 + 2),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=aperture / 2 + 2),
        Surface(radius=-200, glass='', thickness=0, semi_diameter=aperture / 2 + 2),
    ]
    s.stop_surface = 1
    s.aperture_value = aperture
    return s


def _pupil_grids(n: int = 128):
    """Единичная маска зрачка на квадратной решётке n×n."""
    xs = np.linspace(-1.0, 1.0, n)
    gx, gy = np.meshgrid(xs, xs)
    r2 = gx ** 2 + gy ** 2
    mask = (r2 <= 1.0).astype(float)
    return gx, gy, r2, mask


class TestMarechalApprox:
    def test_sigma_zero_gives_one(self):
        """Плоский фронт (σ = 0) ⇒ S = 1."""
        assert strehl_marechal(0.0) == 1.0

    def test_monotonic_decrease_in_sigma(self):
        """S монотонно убывает с ростом σ и остаётся в (0, 1]."""
        sigmas = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]
        values = [strehl_marechal(s) for s in sigmas]
        for s_m in values:
            assert 0.0 < s_m <= 1.0
        for s1, s2 in zip(values, values[1:]):
            assert s2 < s1, 'S должен убывать по σ'

    def test_aberrations_to_zero_strehl_to_one(self):
        """Аберрации → 0 ⇒ S → 1 (точный FFT на сферической аберрации)."""
        _, _, r2, mask = _pupil_grids()
        z40 = 6 * r2 ** 2 - 6 * r2 + 1  # сферическая (Цернике)
        prev = None
        for amp in (0.05, 0.01, 0.002):
            w = amp * z40 * mask
            sigma = float(w[mask > 0.5].std())
            s_exact = strehl_exact_from_wavefront(w, mask)
            # сходимость к 1 квадратичная по амплитуде аберрации
            assert s_exact > 1.0 - 100 * amp ** 2
            assert abs(s_exact - strehl_marechal(sigma)) / strehl_marechal(sigma) < 0.05
            if prev is not None:
                assert s_exact > prev, 'меньше аберраций — выше Strehl'
            prev = s_exact


class TestExactVsMarechal:
    def test_agreement_within_10pct_above_0p3(self):
        """При S > 0.3 расхождение точного и Марешаля < 10%.

        Исключение — чистая дефокусировка у самой границы (худший
        случай аппроксимации; аналитически S = [sin(2πa)/(2πa)]²):
        для неё проверяется диапазон S > 0.35. Реальные фронты
        оцениваются на лучшем фокусе, где дефокусура снята.
        """
        _, _, r2, mask = _pupil_grids()
        gx, gy = np.meshgrid(*[np.linspace(-1, 1, mask.shape[0])] * 2)
        rho = np.sqrt(r2)
        with np.errstate(invalid='ignore'):
            cos_t = np.where(rho > 0, gx / np.where(rho > 0, rho, 1), 0.0)
        modes = {
            'spherical': 6 * r2 ** 2 - 6 * r2 + 1,          # Z40
            'defocus': 2 * r2 - 1,                          # Z20
            'coma': np.sqrt(8) * (3 * rho ** 3 - 2 * rho) * cos_t,  # Z31
        }
        s_min = {'spherical': 0.3, 'coma': 0.3, 'defocus': 0.35}

        checked = 0
        for name, z in modes.items():
            for amp in (0.02, 0.05, 0.1, 0.2, 0.25, 0.3):
                w = amp * z * mask
                w = w - w[mask > 0.5].mean()
                sigma = float(w[mask > 0.5].std())
                s_m = strehl_marechal(sigma)
                if s_m <= s_min[name]:
                    continue
                s_e = strehl_exact_from_wavefront(w, mask)
                assert s_e is not None
                assert abs(s_e - s_m) / s_m < 0.10, (
                    f'{name} amp={amp}: S_m={s_m:.4f} S_e={s_e:.4f}')
                checked += 1
        assert checked >= 8, f'проверено слишком мало точек: {checked}'


class TestIdealSystem:
    def test_flat_wavefront_exact_is_one(self):
        """Идеальная система (плоская волновой фронт): S = 1.0 ± eps."""
        _, _, _, mask = _pupil_grids(96)
        w = np.zeros_like(mask)
        assert strehl_exact_from_wavefront(w, mask) == pytest.approx(1.0, abs=1e-9)

    def test_real_system_near_diffraction_limit(self):
        """Реальная система с малой апертурой: S ≈ 1 (σ → 0)."""
        res = compute_strehl(build_doublet(aperture=4.0))
        assert res['sigma_w'] is not None and res['sigma_w'] < 0.01
        assert res['strehl_marechal'] == pytest.approx(1.0, abs=5e-3)
        assert res['strehl_exact'] == pytest.approx(1.0, abs=5e-3)

    def test_empty_mask_returns_none(self):
        w = np.zeros((8, 8))
        assert strehl_exact_from_wavefront(w, np.zeros((8, 8))) is None


class TestComputeStrehl:
    def test_result_structure(self):
        """Ключи результата и категория применимости."""
        res = compute_strehl(build_doublet(aperture=4.0))
        for key in ('strehl_marechal', 'strehl_exact', 'sigma_w',
                    'validity', 'wl', 'field_y', 'per_wl'):
            assert key in res
        assert res['validity'] == 'good'

    def test_large_aberrations_invalid(self):
        """Полная апертура контрольного дублета: S << 1 ⇒ 'invalid'."""
        res = compute_strehl(build_doublet(aperture=20.0))
        assert res['strehl_marechal'] < STREHL_MARECHAL_LIMIT_MIN
        assert res['validity'] == 'invalid'

    def test_validity_thresholds(self):
        assert _strehl_validity(None) == 'no_data'
        assert _strehl_validity(0.5) == 'good'
        assert _strehl_validity(STREHL_GOOD_MIN) == 'marechal_limit'  # 0.1
        assert _strehl_validity(0.07) == 'marechal_limit'
        assert _strehl_validity(STREHL_MARECHAL_LIMIT_MIN) == 'invalid'  # 0.05
        assert _strehl_validity(0.01) == 'invalid'

    def test_single_wl_mode(self):
        res = compute_strehl(build_doublet(aperture=4.0), wl=0.58756)
        assert res['wl'] == 0.58756
        assert len(res['per_wl']) == 1
        assert res['per_wl'][0]['wl'] == 0.58756

    def test_polychromatic_weighted_mean(self):
        """wl=None: per-λ Strehl + взвешенное среднее по весам λ."""
        wls = [Wavelength(0.54607, 1.0, 'e'),
               Wavelength(0.65627, 2.0, 'C'),
               Wavelength(0.48613, 1.0, 'F')]
        s = build_doublet(aperture=4.0, wls=wls)
        res = compute_strehl(s)
        assert res['wl'] is None
        assert len(res['per_wl']) == 3
        # среднее воспроизводится из per_wl и весов системы
        total = sum(w.weight for w in wls)
        expected_m = sum(p['strehl_marechal'] * w.weight
                         for p, w in zip(res['per_wl'], wls)) / total
        assert res['strehl_marechal'] == pytest.approx(expected_m, rel=1e-12)
        expected_sigma = sum(p['sigma_w'] * w.weight
                             for p, w in zip(res['per_wl'], wls)) / total
        assert res['sigma_w'] == pytest.approx(expected_sigma, rel=1e-12)
        # значения слегка хроматические (не все одинаковые) — проверка не вырождена
        assert len({round(p['sigma_w'], 6) for p in res['per_wl']}) > 1

    def test_no_surfaces_no_data(self):
        res = compute_strehl(OpticalSystem())
        assert res['strehl_marechal'] is None
        assert res['validity'] == 'no_data'


class TestFormatting:
    def test_format_strehl_line(self):
        text = format_strehl({'strehl_marechal': 0.847, 'sigma_w': 0.052,
                              'wl': 0.58756, 'per_wl': [{}]})
        assert text == "Strehl: 0.847 (σ=0.052λ, Марешаль)"

    def test_format_strehl_poly(self):
        text = format_strehl({'strehl_marechal': 0.9, 'sigma_w': 0.04,
                              'wl': None, 'per_wl': [{}, {}, {}]})
        assert 'полихром.' in text

    def test_format_strehl_no_data(self):
        assert format_strehl({}) == "Strehl: —"
        assert format_strehl(None) == "Strehl: —"

    def test_tooltip_contains_breakdown(self):
        res = compute_strehl(build_doublet(
            aperture=4.0,
            wls=[Wavelength(0.54607, 1.0, 'e'), Wavelength(0.65627, 1.0, 'C')]))
        tip = strehl_tooltip(res)
        assert 'Марешаль' in tip
        assert 'σ_w' in tip
        assert 'По длинам волн' in tip
        assert 'λ=0.54607' in tip

    def test_tooltip_no_data(self):
        assert 'нет данных' in strehl_tooltip({})
