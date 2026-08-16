"""Регрессионные тесты пункта 14 GAP v2 — тест-объекты.

Симуляция изображения тест-объекта через систему: FFT-свёртка идеала
с дифракционной PSF (compute_test_object_image). Объекты: шпальная
мира (штрихи убывающей толщины), край, точка, синусоидальная мишень.
Дефокус — квадратичный фазовый член на зрачке (compute_psf).
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, \
    create_demo_system
from advanced_analysis import (
    TEST_OBJECT_KINDS, MIRA_DEFAULT_GROUPS,
    make_test_object, convolve_fft, compute_test_object_image, compute_psf,
)


def singlet() -> OpticalSystem:
    """Синглет К8 f'≈100 мм — хорошо осветвлённая, быстрая трассировка."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(0.0)]
    s.surfaces = [
        Surface(radius=100.0, glass='К8', thickness=5.0),
        Surface(radius=-100.0, glass='', thickness=0.0),
    ]
    return s


GRID = 64  # сетка PSF/объекта в тестах (как в GUI)


@pytest.fixture(scope='module')
def sim_singlet():
    return compute_test_object_image(singlet(), kind='mira', num_rays=GRID)


# --------------------------------------------------------------------------- #
# Генераторы объектов
# --------------------------------------------------------------------------- #

class TestMakeTestObject:

    def setup_method(self):
        self.axis = np.linspace(-50.0, 50.0, GRID)

    def test_all_kinds_shapes_and_range(self):
        for kind, _ in TEST_OBJECT_KINDS:
            obj = make_test_object(kind, self.axis, self.axis)
            assert obj.shape == (GRID, GRID), kind
            assert obj.min() >= 0.0 and obj.max() <= 1.0, kind

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError):
            make_test_object('nope', self.axis, self.axis)

    def test_point_is_single_delta(self):
        obj = make_test_object('point', self.axis, self.axis)
        assert obj.sum() == 1.0
        i0 = int(np.argmin(np.abs(self.axis)))  # ближайший к 0 отсчёт
        assert obj[i0, i0] == 1.0

    def test_edge_is_step_along_y(self):
        obj = make_test_object('edge', self.axis, self.axis)
        first = int(np.argmax(self.axis >= 0))  # первый y ≥ 0
        assert obj[:first].max() == 0.0   # y < 0 — тёмное поле
        assert obj[first:].min() == 1.0   # y ≥ 0 — светлое
        assert np.all(obj == obj[:, :1])  # край постоянен вдоль X

    def test_sine_frequency_and_contrast(self):
        freq = 25.0  # период 40 мкм на кадре 100 мкм — 2.5 периода
        obj = make_test_object('sine', self.axis, self.axis,
                               freq_lp_mm=freq)
        col = obj[:, GRID // 2]
        assert col.max() == pytest.approx(1.0, abs=1e-9)
        assert col.min() == pytest.approx(0.0, abs=1e-9)
        assert col.mean() == pytest.approx(0.5, abs=1e-9)
        # число переходов через 0.5 ≈ 2·число периодов
        crossings = int(np.sum(np.diff(np.sign(col - 0.5)) != 0))
        n_periods = (self.axis[-1] - self.axis[0]) * freq / 1000.0
        assert crossings == pytest.approx(2 * n_periods, abs=1)

    def test_mira_bar_widths_halve(self):
        """Шпальная мира: ширины штрихов вдоль Y убывают вдвое.

        Ширины меряются по координатам границ полос (в мкм), поэтому
        допуск — шаг сетки (квантование на пиксели).
        """
        n = 129
        axis = np.linspace(-60.0, 60.0, n)
        freq = 80.0  # w0 = 12.5 мкм: границы 12.5, 25, 31.25, 37.5, 40.625
        obj = make_test_object('mira', axis, axis, freq_lp_mm=freq,
                               num_bars=3)
        col = obj[:, n // 2]
        step = axis[1] - axis[0]
        # границы полос — смена значения; от центра наружу
        boundaries = [axis[i] for i in range(1, n)
                      if col[i] != col[i - 1] and axis[i] > 0]
        widths = [b - a for a, b in zip([0.0] + boundaries, boundaries)]
        assert len(widths) >= 5  # три группы помещаются в кадр
        # пары «штрих + пробел» одной группы равны; каждая группа вдвое тоньше
        assert widths[0] == pytest.approx(1000.0 / freq, abs=2 * step)
        assert widths[1] == pytest.approx(widths[0], abs=2 * step)
        assert widths[2] == pytest.approx(widths[0] / 2, abs=2 * step)
        assert widths[3] == pytest.approx(widths[0] / 2, abs=2 * step)
        assert widths[4] == pytest.approx(widths[0] / 4, abs=2 * step)

    def test_mira_symmetric_about_center(self):
        obj = make_test_object('mira', self.axis, self.axis,
                               freq_lp_mm=40.0, num_bars=3)
        half = GRID // 2  # центр между строками half-1 и half
        assert np.allclose(obj[half - 1::-1], obj[half:])


# --------------------------------------------------------------------------- #
# FFT-свёртка
# --------------------------------------------------------------------------- #

class TestConvolveFft:

    def test_delta_kernel_identity(self):
        n = 16
        img = np.random.default_rng(0).random((n, n))
        delta = np.zeros((n, n))
        delta[n // 2, n // 2] = 1.0
        assert np.allclose(convolve_fft(img, delta), img)

    def test_shift_invariance_no_wrap(self):
        """Сдвиг объекта = сдвиг изображения (нет заворота периода)."""
        n = 32
        delta = np.zeros((n, n))
        delta[2, 5] = 1.0
        ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
        c = n // 2
        kernel = np.exp(-((ii - c) ** 2 + (jj - c) ** 2) / 8.0)  # пик в центре
        out = convolve_fft(delta, kernel)
        # максимум туда, куда сдвинут объект (2, 5), а не завернулся
        assert np.unravel_index(out.argmax(), out.shape) == (2, 5)
        # «хвост» не перетёк на противоположный край
        assert out[-3:, -3:].sum() < out.max() * 1e-6

    def test_energy_preserved(self):
        rng = np.random.default_rng(1)
        n = 32
        img = np.zeros((n, n))
        img[10:22, 10:22] = rng.random((12, 12))
        kernel = np.zeros((n, n))
        kernel[14:18, 14:18] = 1.0
        kernel /= kernel.sum()
        out = convolve_fft(img, kernel)
        assert out.sum() == pytest.approx(img.sum(), rel=1e-9)


# --------------------------------------------------------------------------- #
# Симуляция изображения
# --------------------------------------------------------------------------- #

class TestSimulation:

    def test_result_structure(self, sim_singlet):
        res = sim_singlet
        assert res['kind'] == 'mira'
        assert set(res) >= {'kind', 'x', 'y', 'ideal', 'image', 'psf',
                            'defocus_mm', 'freq_lp_mm', 'num_bars'}
        assert res['image'].shape == res['ideal'].shape == (GRID, GRID)
        assert res['psf'].sum() == pytest.approx(1.0)  # ядро — плотность
        assert res['num_bars'] == MIRA_DEFAULT_GROUPS

    def test_point_image_is_psf(self):
        """Точка: свёртка дельты с PSF = сама PSF (нормированная)."""
        res = compute_test_object_image(singlet(), kind='point',
                                        num_rays=GRID)
        assert np.allclose(res['image'], res['psf'])
        assert res['image'].max() == pytest.approx(res['psf'].max())

    def test_edge_profile_monotone_in_center(self):
        """Край: в центре кадра профиль — монотонная S-кривая (ESF);
        у краёв кадра — краевые эффекты конечной сетки."""
        res = compute_test_object_image(singlet(), kind='edge',
                                        num_rays=GRID)
        mid = GRID // 2
        margin = GRID // 8
        prof = res['image'][margin:GRID - margin, mid]
        assert np.all(np.diff(prof) > -1e-12)
        assert prof[0] < 0.2 and prof[-1] > 0.8  # 0 → 1

    def test_sine_contrast_falls_with_frequency(self):
        """Синусоидальная мишень: контраст изображения = ЧКХ(ν),
        убывает с частотой."""
        def contrast(freq):
            res = compute_test_object_image(singlet(), kind='sine',
                                            num_rays=GRID, freq_lp_mm=freq)
            col = res['image'][GRID // 4:3 * GRID // 4, GRID // 2]
            return (col.max() - col.min()) / (col.max() + col.min())

        c_low, c_high = contrast(10.0), contrast(60.0)
        assert c_low > c_high
        assert c_high > 0.0  # но не ноль (частота ниже среза)

    def test_mira_image_smoothed(self):
        """Шпальная мира: изображение — размытый идеал (полная
        вариация профиля падает; частотный спад — см. sine-тест)."""
        res = compute_test_object_image(singlet(), kind='mira',
                                        num_rays=GRID, freq_lp_mm=40.0)
        mid = GRID // 2
        tv_ideal = np.abs(np.diff(res['ideal'][1:-1, mid])).sum()
        tv_image = np.abs(np.diff(res['image'][1:-1, mid])).sum()
        assert tv_image < tv_ideal
        # резкие ступени идеала 0/1 в изображении сглажены
        assert res['image'][:, mid].min() > res['ideal'][:, mid].min()
        assert res['image'][:, mid].max() < res['ideal'][:, mid].max()

    def test_defocus_blurs_more(self):
        """Смещение плоскости установки размывает изображение сильнее.

        Сравниваются далёкие от фокуса Δz: малый дефокус частично
        компенсирует сферическую аберрацию синглета (сдвиг к кругу
        наименьшего рассеяния) и может «заострить» край; вдали от
        оптимума размытие растёт с |Δz|.
        """
        s = singlet()
        res0 = compute_test_object_image(s, kind='edge', num_rays=GRID,
                                         defocus_mm=0.5)
        res1 = compute_test_object_image(s, kind='edge', num_rays=GRID,
                                         defocus_mm=1.0)
        mid, margin = GRID // 2, GRID // 8

        def edge_width(res):
            # ширина края через максимальный градиент (робастно к
            # аберрациям, размывающим край сильнее кадра)
            prof = res['image'][margin:GRID - margin, mid]
            step = abs(res['y'][1] - res['y'][0])
            return 0.8 / max(np.abs(np.diff(prof)) / step)

        assert edge_width(res1) > edge_width(res0)
        # и результат вообще другой
        assert not np.allclose(res0['image'], res1['image'], atol=1e-6)

    def test_field_shifts_and_blurs(self):
        """Внеосевое поле: изображение тоже считается (кома/астигматизм)."""
        res = compute_test_object_image(singlet(), kind='sine',
                                        num_rays=GRID, field_y=2.0)
        assert np.isfinite(res['image']).all()
        assert res['image'].max() > 0.0


# --------------------------------------------------------------------------- #
# Дефокус PSF
# --------------------------------------------------------------------------- #

class TestPsfDefocus:

    def test_defocus_spreads_energy(self):
        s = create_demo_system()
        p0, _, _ = compute_psf(s, num_rays=GRID)
        p1, _, _ = compute_psf(s, num_rays=GRID, defocus_mm=0.2)

        def central_fraction(p):
            d = p / p.sum()
            c = GRID // 2
            return d[c - 1:c + 2, c - 1:c + 2].sum()

        assert central_fraction(p1) < central_fraction(p0)

    def test_zero_defocus_is_previous_behavior(self):
        s = create_demo_system()
        p_def, _, _ = compute_psf(s, num_rays=32, defocus_mm=0.0)
        p_old, _, _ = compute_psf(s, num_rays=32)
        assert np.allclose(p_def, p_old)

    def test_symmetric_defocus_same_spread(self):
        """±Δz дают одинаковое размытие (квадратичный член).

        При ненулевых аберрациях PSF_+ и PSF_− не совпадают поэлементно
        (комплексно-сопряжённый зрачок — это зеркало интенсивности),
        но ширина распределения энергии одинакова.
        """
        s = singlet()

        def spread(dz):
            p, _, _ = compute_psf(s, num_rays=GRID, defocus_mm=dz)
            d = p / p.sum()
            c = GRID // 2
            ii, jj = np.meshgrid(np.arange(GRID) - c, np.arange(GRID) - c,
                                 indexing='ij')
            return (d * (ii ** 2 + jj ** 2)).sum()

        assert spread(0.15) == pytest.approx(spread(-0.15), rel=0.05)


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #

class TestTestObjectGui:

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import sys
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    @pytest.fixture()
    def panel(self):
        from gui.analysis_panel import AnalysisPanel
        return AnalysisPanel()

    def test_widget_next_to_esf(self, panel):
        """Вкладка «Изображение» рядом с ESF; в панели есть виджет."""
        assert panel.test_object_w is not None
        titles = [panel.tabText(i) for i in range(panel.count())]
        assert abs(titles.index('ESF') - titles.index('Изображение')) == 1

    def test_combo_lists_all_kinds(self, panel):
        combo = panel.test_object_w.kind_combo
        assert combo.count() == len(TEST_OBJECT_KINDS)
        assert [combo.itemData(i) for i in range(combo.count())] \
            == [k for k, _ in TEST_OBJECT_KINDS]

    def test_set_data_simulates(self, panel):
        panel.test_object_w.set_data(singlet(), defocus_offset=0.0)
        res = panel.test_object_w.result
        assert res is not None
        assert res['kind'] == 'mira'  # выбранный по умолчанию объект
        assert panel.test_object_w.defocus_spin.value() == 0.0

    def test_button_resimulates_with_params(self, panel):
        w = panel.test_object_w
        w.set_data(singlet())
        w.kind_combo.setCurrentIndex(2)  # точка
        w.freq_spin.setValue(50.0)
        w.defocus_spin.setValue(0.05)
        w.sim_btn.click()
        assert w.result['kind'] == 'point'
        assert w.result['freq_lp_mm'] == pytest.approx(50.0)
        assert w.result['defocus_mm'] == pytest.approx(0.05)

    def test_no_system_renders_placeholder(self, panel):
        w = panel.test_object_w
        w._system = None
        w.simulate()
        assert w.result is None
