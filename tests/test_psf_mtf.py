# -*- coding: utf-8 -*-
"""Тесты ФРТ/ФРЛ/ОПФ/ФКЭ (TASK_PSF, analysis/psf_mtf.py).

Физкорректность уровня-2 анализа (ANALIZE.DOC §9, работа DIA):

* Штрель из ФРТ совпадает с ``analysis.strehl`` (допуск 1e-3) и ≈ 1
  для почти дифракционно-ограниченного дублета;
* нули MTF при дефокусировке (нули Талбота): с ростом дефокуса первый
  ноль уходит вниз от среза, MTF(0.5·ν_c) монотонно падает;
* экранирование 0.3: «провал» ядра ФРТ — ФКЭ ниже в ядре, энергия в
  кольцах выше, Штрель относительно той же кольцевой апертуры ≈ 1;
* MTF(0) = 1, монотонное убывание, согласие с аналитикой круглого
  зрачка ``(2/π)(arccos s − s√(1−s²))``; tan/sag совпадают на оси и
  различаются на поле ≠ 0;
* сохранение энергии (Σ psf = 1, ФРЛ и ФКЭ нормированы);
* синус-мира: контраст изображения равен MTF(ν), шпальная мира —
  меандр с контрастом (4/π)·MTF(ν) без высших гармоник выше среза.
"""
import math

import numpy as np
import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, \
    paraxial_trace
from analysis.strehl import compute_strehl
from analysis.psf_mtf import (
    GRID, PSF_FFT_PAD, encircled_energy, format_psf_mtf_section,
    lsf_from_psf, mtf_from_psf, psf_grid, render_test_target,
    strel_from_psf,
)
from fileio.protocol import export_protocol


def build_doublet(aperture: float = 20.0) -> OpticalSystem:
    """Контрольный дублет К8/TF5 (как в test_strehl/test_spot_rms_xy).

    Апертура 4 — почти безаберрационный (S ≈ 1); 20 — аберрационный
    (S << 1); удобны оба предела.
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
    s.aperture_value = aperture
    return s


def airy_radius_um(res: dict) -> float:
    """Радиус первого нуля Эйри r₁ = 1.22·λ·F# (мкм)."""
    return 1.22 * res['wl'] * 1e-3 * res['f'] / res['D'] * 1e3


def mtf_at(mtf: dict, frac: float, key: str = 'tan') -> float:
    """MTF в сечении key на доле frac частоты среза (freq → interp)."""
    res = mtf['_cutoff']
    return float(np.interp(frac * res, mtf['freq_lpmm'], mtf[key]))


def mtf_with_cutoff(res: dict) -> dict:
    """mtf_from_psf + частота среза для интерполяции в тестах."""
    mtf = mtf_from_psf(res['psf'], res['pitch_um'])
    mtf['_cutoff'] = res['cutoff_lpmm']
    return mtf


def first_mtf_zero_frac(res: dict, threshold: float = 0.05) -> float:
    """Доля ν/ν_c первого локального минимума MTF ниже threshold."""
    mtf = mtf_with_cutoff(res)
    tan = mtf['tan']
    frac_ax = mtf['freq_lpmm'] / res['cutoff_lpmm']
    for k in range(1, len(tan) - 1):
        if tan[k] < threshold and tan[k] <= tan[k - 1] and tan[k] <= tan[k + 1]:
            return float(frac_ax[k])
    return float('inf')


class TestPsfGrid:
    """Базовые свойства решётки ФРТ (тест 5: энергия сохраняется)."""

    def test_result_keys_and_shape(self):
        res = psf_grid(build_doublet(aperture=4.0))
        for key in ('psf', 'y_um', 'x_um', 'pitch_um', 'fill', 'strehl',
                    'cutoff_lpmm', 'nyquist_lpmm', 'wavefront', 'pupil_mask',
                    'obscuration', 'wl', 'field_y', 'defocus'):
            assert key in res
        m = PSF_FFT_PAD * GRID
        assert res['psf'].shape == (m, m)
        assert res['M'] == m and res['grid'] == GRID

    def test_energy_conserved(self):
        """Σ psf = 1 (нормировка на полную энергию), интенсивность ≥ 0."""
        res = psf_grid(build_doublet(aperture=4.0))
        assert res['psf'].sum() == pytest.approx(1.0, abs=1e-9)
        assert res['psf'].min() >= 0.0

    def test_intensity_peak_in_center(self):
        """W измерена до опорной сферы поля — пятно в центре решётки."""
        res = psf_grid(build_doublet(aperture=4.0))
        cy, cx = np.unravel_index(np.argmax(res['psf']), res['psf'].shape)
        half = res['M'] // 2
        assert abs(cy - half) <= 2 and abs(cx - half) <= 2

    def test_scale_consistent_with_airy(self):
        """Шаг решётки и оси согласованы: Найквист = (pad/2)·ν_c·grid/(grid−1)."""
        res = psf_grid(build_doublet(aperture=4.0))
        assert res['x_um'][1] - res['x_um'][0] == pytest.approx(res['pitch_um'])
        # zero-padding ×4: частотный диапазон 2·ν_c (умножен на grid/(grid−1)
        # из-за полуоткрытых концов linspace-решётки зрачка)
        assert res['nyquist_lpmm'] == pytest.approx(
            res['cutoff_lpmm'] * (PSF_FFT_PAD / 2) * GRID / (GRID - 1),
            rel=1e-9)

    def test_empty_system(self):
        res = psf_grid(OpticalSystem())
        assert res['psf'] is None and res['reason']


class TestStrehlCrossCheck:
    """Тест 1: Штрель из ФРТ == strehl.py (допуск 1e-3)."""

    @pytest.mark.parametrize('aperture', [4.0, 20.0])
    def test_matches_strehl_exact(self, aperture):
        """Та же сетка W/решётка, что у strehl.py — совпадение точное."""
        s = build_doublet(aperture)
        res = psf_grid(s)
        ref = compute_strehl(s)
        assert res['strehl'] == pytest.approx(ref['strehl_exact'], abs=1e-3)
        assert strel_from_psf(res['psf'], res['fill']) == pytest.approx(
            res['strehl'], abs=1e-12)

    def test_aberration_free_lens_strehl_near_one(self):
        """Малая апертура (W ≈ 0): Штрель ≈ 1 обоими способами."""
        s = build_doublet(aperture=4.0)
        res = psf_grid(s)
        assert res['strehl'] == pytest.approx(1.0, abs=5e-3)
        assert compute_strehl(s)['strehl_exact'] == pytest.approx(1.0, abs=5e-3)

    def test_defocus_reduces_strehl(self):
        """Чистая дефокусировка монотонно снижает пик ФРТ."""
        s = build_doublet(aperture=4.0)
        strehls = [psf_grid(s, defocus=d)['strehl']
                   for d in (0.0, 0.25, 0.5, 1.0)]
        assert strehls == sorted(strehls, reverse=True)
        assert strehls[0] > 0.99 and strehls[-1] < 0.2

    def test_strel_from_psf_bad_peak(self):
        res = psf_grid(build_doublet(aperture=4.0))
        assert math.isnan(strel_from_psf(res['psf'], 0.0))


class TestDefocusMtfNulls:
    """Тест 2: нули MTF при дефокусировке (порядок нулей Талбота)."""

    def test_mtf_at_half_cutoff_monotone_in_defocus(self):
        """MTF(0.5·ν_c) падает с дефокусом: ~0.39 → 0.29 → 0.09 → 0.02."""
        s = build_doublet(aperture=4.0)
        values = [mtf_at(mtf_with_cutoff(psf_grid(s, defocus=d)), 0.5)
                  for d in (0.0, 0.25, 0.5, 1.0)]
        assert values == sorted(values, reverse=True)
        assert values[0] == pytest.approx(0.39, abs=0.02)  # круглая апертура
        assert values[-1] < 0.05

    def test_first_null_moves_down_with_defocus(self):
        """Первый ноль MTF: 1λ — в ядре (~0.2·ν_c), 0.25/0.5λ — у среза."""
        s = build_doublet(aperture=4.0)
        null_025 = first_mtf_zero_frac(psf_grid(s, defocus=0.25))
        null_050 = first_mtf_zero_frac(psf_grid(s, defocus=0.5))
        null_100 = first_mtf_zero_frac(psf_grid(s, defocus=1.0))
        # 1λ PV: ноль на ~0.2·ν_c (известный порядок нулей Талбота),
        # заведомо ниже половины среза
        assert 0.12 < null_100 < 0.28 < null_050
        # слабые дефокусы ядро MTF держат: ноль только у самого среза
        assert null_025 > 0.9 and null_050 > 0.9

    def test_defocus_is_extra_wavefront_term(self):
        """defocus — дополнительный член поверх трассированной W (карта
        ``wavefront`` в результате дефокус не включает)."""
        s = build_doublet(aperture=4.0)
        r0 = psf_grid(s, defocus=0.0)
        r1 = psf_grid(s, defocus=1.0)
        assert np.array_equal(r1['wavefront'], r0['wavefront'])
        assert np.array_equal(r1['pupil_mask'], r0['pupil_mask'])
        assert not np.allclose(r1['psf'], r0['psf'])

    def test_defocus_broadens_psf(self):
        """Чистая дефокусировка расширяет пятно: ФКЭ в r₁ Эйри падает."""
        s = build_doublet(aperture=4.0)
        ee_at_airy = []
        for d in (0.0, 0.25, 0.5):
            res = psf_grid(s, defocus=d)
            r_um, ee = encircled_energy(res['psf'], res['pitch_um'])
            ee_at_airy.append(float(np.interp(airy_radius_um(res), r_um, ee)))
        assert ee_at_airy == sorted(ee_at_airy, reverse=True)


class TestObscuration:
    """Тест 3: экранирование 0.3 — «провал» ядра, энергия в кольцах."""

    def test_pupil_mask_has_central_hole(self):
        s = build_doublet(aperture=4.0)
        s.obscuration_ratio = 0.3
        res = psf_grid(s)
        xs = np.linspace(-1.0, 1.0, res['grid'])
        rho = np.sqrt(np.add.outer(xs * xs, xs * xs))
        assert res['pupil_mask'][rho < 0.2].max() == 0.0   # центр закрыт
        assert res['pupil_mask'][(rho > 0.5) & (rho < 0.9)].min() == 1.0
        assert res['obscuration'] == 0.3

    def test_fill_ratio_annular(self):
        """Площадь зрачка падает до 1−ε² ≈ 0.91 от чистой."""
        s = build_doublet(aperture=4.0)
        clear = psf_grid(s)
        s.obscuration_ratio = 0.3
        obsc = psf_grid(s)
        assert obsc['fill'] / clear['fill'] == pytest.approx(1 - 0.3 ** 2,
                                                             rel=0.02)

    def test_encircled_energy_lower_in_core(self):
        """ФКЭ в ядре (0.5..1.5 r₁) ниже с экраном; в далёких кольцах
        энергия выше (яркое кольцо Эйри)."""
        s = build_doublet(aperture=4.0)
        clear = psf_grid(s)
        s.obscuration_ratio = 0.3
        obsc = psf_grid(s)
        r1 = airy_radius_um(clear)
        rc, ec = encircled_energy(clear['psf'], clear['pitch_um'])
        ro, eo = encircled_energy(obsc['psf'], obsc['pitch_um'])
        for frac in (0.5, 1.0, 1.5):
            assert np.interp(frac * r1, ro, eo) < np.interp(frac * r1, rc, ec)
        # кольцо (1..2)r₁: энергия заметно выше, чем без экрана
        ring_clear = np.interp(2 * r1, rc, ec) - np.interp(1.05 * r1, rc, ec)
        ring_obsc = np.interp(2 * r1, ro, eo) - np.interp(1.05 * r1, ro, eo)
        assert ring_obsc > 2.0 * ring_clear

    def test_strehl_relative_to_annular_ideal(self):
        """Штрель считается от идеала той же кольцевой апертуры: ≈ 1."""
        s = build_doublet(aperture=4.0)
        s.obscuration_ratio = 0.3
        res = psf_grid(s)
        assert res['strehl'] == pytest.approx(1.0, abs=5e-3)


class TestMtf:
    """Тест 4: MTF(0)=1, монотонность, tan/sag, аналитика круглого зрачка."""

    def test_mtf_at_zero_is_one(self):
        res = psf_grid(build_doublet(aperture=4.0))
        mtf = mtf_from_psf(res['psf'], res['pitch_um'])
        assert mtf['tan'][0] == pytest.approx(1.0, abs=1e-9)
        assert mtf['sag'][0] == pytest.approx(1.0, abs=1e-9)

    def test_monotonic_decrease(self):
        """Осевая MTF не возрастает (вплоть до числовой точности)."""
        res = psf_grid(build_doublet(aperture=4.0))
        mtf = mtf_from_psf(res['psf'], res['pitch_um'])
        for curve in (mtf['tan'], mtf['sag']):
            assert np.diff(curve).max() <= 1e-6

    @pytest.mark.parametrize('frac', [0.25, 0.5, 0.75])
    def test_matches_analytic_circular_pupil(self, frac):
        """Дифракционный предел: MTF(s) = (2/π)(arccos s − s√(1−s²))."""
        res = psf_grid(build_doublet(aperture=4.0))
        got = mtf_at(mtf_with_cutoff(res), frac)
        analytic = (2 / math.pi) * (math.acos(frac)
                                    - frac * math.sqrt(1 - frac ** 2))
        assert got == pytest.approx(analytic, rel=0.01)

    def test_tan_sag_equal_on_axis(self):
        """Осевая (осесимметричная) система: сечения совпадают."""
        res = psf_grid(build_doublet(aperture=4.0))
        mtf = mtf_from_psf(res['psf'], res['pitch_um'])
        assert np.abs(mtf['tan'] - mtf['sag']).max() < 1e-5

    def test_tan_sag_differ_off_axis(self):
        """Внеосевая кома/астигматизм: меридиональное и сагиттальное
        сечения ЧКХ различимы (поле в меридиональной плоскости Y)."""
        res = psf_grid(build_doublet(aperture=4.0), field_y=5.0)
        mtf = mtf_from_psf(res['psf'], res['pitch_um'])
        assert np.abs(mtf['tan'] - mtf['sag']).max() > 0.01

    def test_frequency_axis_units(self):
        """Ось частот — лин/мм: среза достигает при ν_c = D/(λf')."""
        res = psf_grid(build_doublet(aperture=4.0))
        mtf = mtf_from_psf(res['psf'], res['pitch_um'])
        assert mtf['freq_lpmm'][0] == pytest.approx(0.0, abs=1e-9)
        assert mtf['nyquist_lpmm'] == pytest.approx(res['nyquist_lpmm'],
                                                    rel=1e-9)


class TestLsf:
    """ФРЛ — интегралы ФРТ (§9.4), нормировка и терминология OPAL."""

    def test_profiles_normalized_and_symmetric_on_axis(self):
        res = psf_grid(build_doublet(aperture=4.0))
        lsf = lsf_from_psf(res['psf'], res['pitch_um'])
        for key in ('x', 'y', 'meridional', 'sagittal'):
            assert lsf[key].sum() == pytest.approx(1.0, abs=1e-9)
        # осевая симметрия: оба профиля совпадают и пики в центре
        # (расхождение — порядок суммирования, ~1e-8)
        assert np.abs(lsf['x'] - lsf['y']).max() < 1e-6
        assert np.argmax(lsf['x']) == lsf['x'].shape[0] // 2
        assert 'coord_um' in lsf

    def test_coord_px_without_pitch(self):
        res = psf_grid(build_doublet(aperture=4.0))
        lsf = lsf_from_psf(res['psf'])
        assert 'coord_px' in lsf and 'coord_um' not in lsf

    def test_opal_naming_aliases(self):
        """меридиональная ФРЛ — линия вдоль Y (профиль по X) и наоборот."""
        res = psf_grid(build_doublet(aperture=20.0), field_y=5.0)
        lsf = lsf_from_psf(res['psf'], res['pitch_um'])
        assert np.array_equal(lsf['meridional'], lsf['x'])
        assert np.array_equal(lsf['sagittal'], lsf['y'])


class TestEncircledEnergy:
    """ФКЭ — монотонная кумулятивная кривая от энергетического центра."""

    def test_monotonic_and_complete(self):
        res = psf_grid(build_doublet(aperture=4.0))
        r_um, ee = encircled_energy(res['psf'], res['pitch_um'])
        assert np.diff(ee).min() >= 0.0
        assert ee[0] > 0.0
        assert ee[-1] == pytest.approx(1.0, abs=1e-9)
        assert r_um[0] == 0.0 and r_um[1] == pytest.approx(res['pitch_um'])

    def test_airy_core_contains_most_energy(self):
        """Безаберрационная линза: в r₁ Эйри ≈ 84% энергии (ядро Эйри)."""
        res = psf_grid(build_doublet(aperture=4.0))
        r_um, ee = encircled_energy(res['psf'], res['pitch_um'])
        assert np.interp(airy_radius_um(res), r_um, ee) == pytest.approx(
            0.84, abs=0.03)


class TestTestTarget:
    """Тест-миры (§9.5): контраст синус-миры = MTF(ν)."""

    @pytest.mark.parametrize('frac', [0.2, 0.3])
    def test_sine_contrast_equals_mtf(self, frac):
        """Контраст синус-миры на ν = frac·ν_c равен MTF_tan(ν)."""
        res = psf_grid(build_doublet(aperture=4.0))
        mtf = mtf_with_cutoff(res)
        nu = frac * res['cutoff_lpmm']
        target = render_test_target(res['psf'], res['pitch_um'], nu,
                                    orientation='tangential', kind='sine')
        expected = mtf_at(mtf, frac)
        assert target['contrast'] == pytest.approx(expected, rel=0.02)

    def test_sine_sagittal_orientation(self):
        """Штрихи вдоль Y (сагиттальная частота): контраст = MTF_sag(ν);
        на оси совпадает с тангенциальной."""
        res = psf_grid(build_doublet(aperture=4.0))
        mtf = mtf_with_cutoff(res)
        nu = 0.3 * res['cutoff_lpmm']
        target = render_test_target(res['psf'], res['pitch_um'], nu,
                                    orientation='sagittal', kind='sine')
        assert target['contrast'] == pytest.approx(mtf_at(mtf, 0.3, 'sag'),
                                                   rel=0.02)

    def test_bar_target_bounds_and_fundamental(self):
        """Шпальная мира: изображение в (0, 1); вблизи 0.3·ν_c высшие
        гармоники подавлены — контраст ≈ (4/π)·MTF(ν)."""
        res = psf_grid(build_doublet(aperture=4.0))
        mtf = mtf_with_cutoff(res)
        nu = 0.3 * res['cutoff_lpmm']
        bar = render_test_target(res['psf'], res['pitch_um'], nu,
                                 orientation='tangential', kind='bar')
        assert 0.0 < bar['image'].min() < bar['image'].max() < 1.0
        assert bar['contrast'] == pytest.approx(
            (4 / math.pi) * mtf_at(mtf, 0.3), rel=0.05)

    def test_object_profiles_in_range(self):
        res = psf_grid(build_doublet(aperture=4.0))
        nu = 0.2 * res['cutoff_lpmm']
        target = render_test_target(res['psf'], res['pitch_um'], nu)
        # окно попадает между экстремумами синуса — допускаем 0/1 ± 1%
        assert 0.0 <= target['object'].min() <= 0.01
        assert 0.99 <= target['object'].max() <= 1.0
        assert target['image'].min() > 0.0
        assert target['period_um'] == pytest.approx(1000.0 / nu)

    def test_invalid_args_raise(self):
        res = psf_grid(build_doublet(aperture=4.0))
        with pytest.raises(ValueError):
            render_test_target(res['psf'], res['pitch_um'], 10.0,
                               orientation='diagonal')
        with pytest.raises(ValueError):
            render_test_target(res['psf'], res['pitch_um'], 10.0,
                               kind='triangle')
        with pytest.raises(ValueError):
            render_test_target(res['psf'], res['pitch_um'], -1.0)


class TestProtocolSection:
    """Секция «ФРТ/ОПФ» в протоколе расчёта (краткая)."""

    def test_format_section_contents(self):
        text = format_psf_mtf_section(build_doublet(aperture=4.0))
        assert 'Штрель' in text and 'ν_c' in text
        assert 'мер' in text and 'саг' in text
        assert '1.00' in text  # частоты 0.2..1.0 · ν_c

    def test_export_protocol_contains_section(self, tmp_path):
        s = build_doublet(aperture=4.0)
        path = tmp_path / 'proto_psf.txt'
        export_protocol(s, paraxial_trace(s), {}, str(path))
        text = path.read_text(encoding='utf-8')
        assert 'ФРТ / ОПФ' in text
        assert 'Штрель (FFT)' in text
        assert 'Конец протокола' in text

    def test_export_protocol_no_crash_on_empty(self, tmp_path):
        path = tmp_path / 'proto_empty.txt'
        export_protocol(OpticalSystem(), paraxial_trace(OpticalSystem()),
                        {}, str(path))
        text = path.read_text(encoding='utf-8')
        assert 'ФРТ / ОПФ' not in text
