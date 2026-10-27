"""GUI-тесты строки Strehl (TASK_3D_VIZ, пакет B).

Строка «Strehl: 0.847 (σ=0.052λ, Марешаль)» в панели результатов +
tooltip (Марешаль vs точный FFT, σ_w, применимость, разбивка по λ) и
проводка ``MainWindow._refresh_ui`` → ``bridge.execute("strehl.calc")``
→ ``ResultsPanel.update_strehl``. Движок (analysis/strehl.py) уже
покрыт tests/test_strehl.py — здесь проверяется только GUI-слой на
демо-ахромате ``domain.models.create_demo_system_by_name('achromat')``.

Зафиксированный факт (осознанное решение): демо-ахромат на полной
апертуре 20 мм сильно аберрирован (σ_w ≈ 1.86λ, S(Марешаль) ≈ 0.0007,
validity='invalid') — там аппроксимация Марешаля физически не обязана
сходиться с точным FFT (расхождение ~2 порядка). Поэтому проверка
«Марешаль ≈ точный» выполняется на стоп-дауне той же системы
(апертура 3 мм, S ≈ 0.89 > 0.3) с допуском 10% — как в
tests/test_strehl.py::TestExactVsMarechal.

Smoke-тест MainWindow — прецедент tests/qa_v6_full.py::TestGUI
(MainWindow поднимается offscreen без проблем).
"""
import math
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from domain.models import create_demo_system_by_name
from analysis.strehl import compute_strehl


def build_achromat(aperture: float = 20.0):
    """Демо-ахромат К8+ТФ1 (domain/models.py) с заданной апертурой."""
    sys = create_demo_system_by_name('achromat')
    sys.aperture_value = aperture
    return sys


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture(scope='module')
def achromat_sys():
    """Демо-ахромат, полная апертура (как в GUI по умолчанию)."""
    return build_achromat()


@pytest.fixture(scope='module')
def achromat_poly_result(achromat_sys):
    """Полихроматический Strehl полного ахромата (σ≈1.86λ → invalid)."""
    return compute_strehl(achromat_sys)


@pytest.fixture(scope='module')
def achromat_good_result():
    """Стоп-даун ахромата (3 мм): S ≈ 0.89, Марешаль надёжен."""
    return compute_strehl(build_achromat(aperture=3.0))


@pytest.fixture(scope='module')
def panel(app, achromat_poly_result):
    """ResultsPanel с уже поданным полихром-результатом ахромата."""
    from main import ResultsPanel
    p = ResultsPanel()
    p.update_strehl(achromat_poly_result)
    return p


class TestStrehlRowFormat:
    """Строка и tooltip через ResultsPanel.update_strehl."""

    def test_label_text_valid_poly(self, panel, achromat_sys):
        """Валидный полихром-результат: «Strehl: …(σ=…λ, Марешаль, полихром.)»."""
        text = panel.strehl_label.text()
        assert text.startswith('Strehl: ')
        assert '(σ=' in text
        assert 'Марешаль' in text
        # у ахромата 3 длины волны → суффикс полихроматического расчёта
        assert len(achromat_sys.wavelengths) > 1
        assert 'полихром.' in text
        assert '—' not in text

    def test_label_value_in_bounds(self, panel, achromat_poly_result):
        """Число после «Strehl: » — само S(Марешаль), 0 < S ≤ 1."""
        s = float(panel.strehl_label.text().split('Strehl: ')[1].split(' ')[0])
        assert 0.0 < s <= 1.0
        assert s == pytest.approx(achromat_poly_result['strehl_marechal'], abs=1e-3)

    def test_tooltip_breakdown(self, panel, achromat_sys):
        """Tooltip: формулы, точный FFT, σ_w, применимость, все λ системы."""
        tip = panel.strehl_label.toolTip()
        assert tip, 'tooltip пуст'
        assert 'Марешаль' in tip
        assert 'S(точный FFT)' in tip
        assert 'σ_w =' in tip
        assert 'Применимость' in tip
        assert 'По длинам волн:' in tip
        for w in achromat_sys.wavelengths:
            assert f'λ={w.value:.5f}' in tip, f'нет λ={w.value} в tooltip'

    def test_update_strehl_empty(self, app, panel):
        """Пустой результат → заглушка «Strehl: —» и «нет данных» в tooltip."""
        panel.update_strehl({})
        assert panel.strehl_label.text() == 'Strehl: —'
        assert 'нет данных' in panel.strehl_label.toolTip()
        panel.update_strehl(None)
        assert panel.strehl_label.text() == 'Strehl: —'


class TestStrehlOnDemoAchromat:
    """Физика числа на демо-ахромате (create_demo_system_by_name)."""

    def test_bounds(self, achromat_poly_result):
        """0 < S(Марешаль) ≤ 1 на полном демо-ахромате."""
        s = achromat_poly_result['strehl_marechal']
        assert s is not None
        assert 0.0 < s <= 1.0

    def test_validity_invalid_full_aperture(self, achromat_poly_result):
        """Полная апертура: σ_w ≈ 1.9λ ⇒ S < 0.05 ⇒ validity='invalid'.

        Зафиксированный факт: осевой ахромат f/5 на 20 мм зрачка далёк
        от дифракционного предела — категория 'invalid' честная
        (пороги см. analysis/strehl.py::STREHL_MARECHAL_LIMIT_MIN).
        """
        assert achromat_poly_result['sigma_w'] > 0.5
        assert achromat_poly_result['validity'] == 'invalid'

    def test_marechal_formula_consistency(self, achromat_poly_result):
        """S(Марешаль) воспроизводится из σ_w на каждой λ: S = exp(−(2πσ)²).

        На уровне полихром-агрегата формула не обязана выполняться
        (агрегат — взвешенное среднее per-λ S, а exp нелинеен), поэтому
        проверяется каждая монохроматическая составляющая per_wl.
        """
        for p in achromat_poly_result['per_wl']:
            assert p['strehl_marechal'] == pytest.approx(
                math.exp(-((2.0 * math.pi * p['sigma_w']) ** 2)), rel=1e-12)

    def test_polychromatic_ge_mono_min(self, achromat_poly_result):
        """Полихром ≥ моно-минимума: взвешенное среднее между min и max per-λ.

        Веса всех λ ахромата равны (см. _std_wavelengths), поэтому
        среднее обязано лежать в [min, max] монохроматических S
        (равенство границам — вырожденный, но допустимый случай).
        """
        res = achromat_poly_result
        per = [p['strehl_marechal'] for p in res['per_wl']
               if p['strehl_marechal'] is not None]
        assert len(per) == len(achromat := res['per_wl']) > 1
        poly = res['strehl_marechal']
        assert min(per) <= poly <= max(per), (
            f'полихром {poly:.6f} вне [{min(per):.6f}, {max(per):.6f}]')
        assert poly >= min(per)

    def test_exact_leq_one_all_wl(self, achromat_poly_result):
        """Точный FFT-результат в (0, 1] на каждой λ и в среднем."""
        res = achromat_poly_result
        assert 0.0 < res['strehl_exact'] <= 1.0 + 1e-12
        for p in res['per_wl']:
            assert 0.0 < p['strehl_exact'] <= 1.0 + 1e-12

    def test_marechal_matches_exact_when_valid(self, achromat_good_result):
        """Марешаль ≈ точный при S > 0.3 (стоп-даун 3 мм): расхождение < 10%.

        Допуск — как в tests/test_strehl.py::TestExactVsMarechal
        (10% относительных при S > 0.3). На полной апертуре проверка
        невозможна физически (см. докстринг модуля и
        test_validity_invalid_full_aperture).
        """
        res = achromat_good_result
        s_m = res['strehl_marechal']
        s_e = res['strehl_exact']
        assert s_m > 0.3, f'ожидался стоп-даун с S>0.3, получено {s_m:.4f}'
        assert s_e is not None
        assert abs(s_e - s_m) / s_m < 0.10, (
            f'S_m={s_m:.4f} S_e={s_e:.4f} — расхождение ≥ 10%')
        assert res['validity'] == 'good'


class TestStrehlWiring:
    """Проводка: ResultsPanel.update_strehl и мост strehl.calc."""

    def test_panel_nonempty_result(self, app, achromat_poly_result):
        """update_strehl(compute_strehl(ахромат)) → непустые текст и tooltip."""
        from main import ResultsPanel
        p = ResultsPanel()
        p.update_strehl(achromat_poly_result)
        text = p.strehl_label.text()
        assert text.startswith('Strehl: ') and '—' not in text
        tip = p.strehl_label.toolTip()
        assert tip and 'нет данных' not in tip

    def test_bridge_strehl_calc(self, app, achromat_good_result):
        """bridge.set_current(ахромат) → bridge.execute('strehl.calc') → ok, S в (0,1].

        Тот же протокол, что в MainWindow._refresh_ui
        (main.py: _refresh_ui) — мост синглтонный, система подаётся
        set_current перед вызовом команды.
        """
        from gui.cmdbridge import bridge
        sys = build_achromat(aperture=3.0)
        bridge.set_current(sys)
        r = bridge.execute('strehl.calc')
        assert r.ok, f'strehl.calc не выполнился: {r.error}'
        assert 0.0 < r.data['strehl_marechal'] <= 1.0
        assert r.data['validity'] == 'good'

    def test_bridge_result_feeds_panel(self, app, achromat_good_result):
        """Результат моста рендерится панелью (путь _refresh_ui целиком)."""
        from gui.cmdbridge import bridge
        from main import ResultsPanel
        bridge.set_current(build_achromat(aperture=3.0))
        r = bridge.execute('strehl.calc')
        p = ResultsPanel()
        p.update_strehl(r.data if r.ok else {})
        assert p.strehl_label.text().startswith('Strehl: ')
        assert '—' not in p.strehl_label.text()


class TestMainWindowStrehl:
    """Smoke: MainWindow offscreen (прецедент tests/qa_v6_full.py::TestGUI)."""

    def test_refresh_ui_empty_system(self, app):
        """_refresh_ui на пустой системе не падает; строка — заглушка."""
        from main import MainWindow
        mw = MainWindow()
        try:
            mw._refresh_ui()  # пустая система → strehl.calc → no_data
            text = mw.results.strehl_label.text()
            assert text.startswith('Strehl: ')
            assert '—' in text
        finally:
            mw.close()

    def test_refresh_ui_with_achromat(self, app, achromat_good_result):
        """_refresh_ui с ахроматом: проводка мост → панель даёт S в (0,1].

        Строка обязана содержать фактическое значение (не заглушку):
        стоп-даун 3 мм даёт S ≈ 0.89 с validity='good' (совпадает с
        achromat_good_result — тот же детерминированный расчёт).
        """
        from main import MainWindow
        mw = MainWindow()
        try:
            mw.current_system = build_achromat(aperture=3.0)
            mw._refresh_ui()
            text = mw.results.strehl_label.text()
            assert text.startswith('Strehl: ')
            assert 'Марешаль' in text
            s = float(text.split('Strehl: ')[1].split(' ')[0])
            assert 0.0 < s <= 1.0
            assert s == pytest.approx(
                achromat_good_result['strehl_marechal'], abs=2e-3)
            assert 'нет данных' not in mw.results.strehl_label.toolTip()
        finally:
            mw.close()
