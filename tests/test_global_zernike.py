"""Регрессионные тесты пункта 9 GAP v2 — глобальное разложение Цернике.

Z_nm для каждой комбинации (точка поля × λ): пучок на гексаполярной
сетке зрачка (пункт 2) + МНК-подгонка Цернике (общая с пунктом 8).
"""
import math

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
import zernike as zk
from zernike import (ZERNIKE_TERMS, fit_zernike_coefficients,
                     compute_global_zernike, format_global_zernike_text,
                     compute_zernike_coefficients)
from aberrations import trace_wavefront_hexapolar, _hexapolar_points


def build_achromat() -> OpticalSystem:
    """Клееный дублет K8/TF5 с полем и двумя λ."""
    s = OpticalSystem()
    s.wavelengths = [
        Wavelength(0.58756, 1.0, 'd'),
        Wavelength(0.48613, 1.0, 'F'),
    ]
    s.field_points = [FieldPoint(y=0.0), FieldPoint(y=7.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


class TestFitZernike:
    def test_recovers_synthetic_coefficients(self):
        """МНК по точкам гексаполярной сетки восстанавливает заданные
        коэффициенты разложения (W = 0.5·Z20 + 0.3·Z11 + 0.2·Z1-1)."""
        target = {'Z20 Defocus': 0.5, 'Z11 Tilt X': 0.3, 'Z1-1 Tilt Y': 0.2}
        points = []
        for px, py in _hexapolar_points(num_rings=4):
            rho = math.hypot(px, py)
            theta = math.atan2(py, px)
            w = 0.0
            for (n, m, name), coeff in [
                    ((2, 0, 'Z20 Defocus'), 0.5),
                    ((1, 1, 'Z11 Tilt X'), 0.3),
                    ((1, -1, 'Z1-1 Tilt Y'), 0.2)]:
                w += coeff * zk._zernike_poly_noll(n, m, rho, theta)
            points.append((px, py, w))
        fitted = {n: c for c, n in fit_zernike_coefficients(points)}
        for name, expected in target.items():
            assert fitted[name] == pytest.approx(expected, abs=1e-9)
        # остальные члены ≈ 0
        piston = fitted['Z00 Piston']
        assert piston == pytest.approx(0.0, abs=1e-9)

    def test_too_few_points_returns_zeros(self):
        fitted = fit_zernike_coefficients([(0.0, 0.0, 1.0)])
        assert len(fitted) == len([t for t in ZERNIKE_TERMS if t[0] <= 4])
        assert all(c == 0.0 for c, _ in fitted)

    def test_compute_zernike_uses_shared_fit(self, monkeypatch):
        """compute_zernike_coefficients строится на общем fit."""
        import analysis.zernike as azk
        calls = []
        real_fit = azk.fit_zernike_coefficients

        def spy(points, max_order=4):
            calls.append(points)
            return real_fit(points, max_order=max_order)

        monkeypatch.setattr(azk, 'fit_zernike_coefficients', spy)
        compute_zernike_coefficients(build_achromat(), num_rays=10)
        assert calls, "fit_zernike_coefficients не вызван"


class TestGlobalZernike:
    @pytest.fixture(scope='module')
    def result(self):
        return compute_global_zernike(build_achromat())

    def test_combinations_field_times_wl(self, result):
        """Все комбинации поле × λ: 2 поля × 2 λ = 4."""
        assert result['fields'] == [0.0, 7.0]
        assert result['wavelengths'] == [0.58756, 0.48613]
        assert set(result['coeffs'].keys()) == {
            (0.0, 0.58756), (0.0, 0.48613),
            (7.0, 0.58756), (7.0, 0.48613)}

    def test_each_combination_full_terms(self, result):
        expected_names = [name for _, _, name in ZERNIKE_TERMS]
        for coeffs in result['coeffs'].values():
            assert [n for _, n in coeffs] == expected_names

    def test_axial_matches_square_grid(self, result):
        """Гексаполярная сетка ≈ квадратурная сетка: коэффициенты осевого
        пучка совпадают с compute_zernike_coefficients в пределах допуска."""
        s = build_achromat()
        single = {n: c for c, n in compute_zernike_coefficients(
            s, wl=0.58756, num_rays=24, max_order=4)}
        global_axial = {n: c for c, n in result['coeffs'][(0.0, 0.58756)]}
        for name in ('Z20 Defocus', 'Z40 Spherical'):
            assert global_axial[name] == pytest.approx(single[name], abs=0.05)

    def test_coma_grows_off_axis(self, result):
        """Внеосевой пучок: кома Z3-1 заметно больше осевой."""
        axial = {n: c for c, n in result['coeffs'][(0.0, 0.58756)]}
        off = {n: c for c, n in result['coeffs'][(7.0, 0.58756)]}
        assert abs(off['Z3-1 Coma Y']) > abs(axial['Z3-1 Coma Y']) + 1e-3

    def test_hexapolar_reuse(self, monkeypatch):
        """Глобальное разложение переиспользует trace_wavefront_hexapolar."""
        import aberrations
        calls = []
        real = aberrations.trace_wavefront_hexapolar

        def spy(system, wl=None, field_y=0.0, num_rings=4):
            calls.append((field_y, wl))
            return real(system, wl=wl, field_y=field_y, num_rings=num_rings)

        monkeypatch.setattr(aberrations, 'trace_wavefront_hexapolar', spy)
        compute_global_zernike(build_achromat())
        assert len(calls) == 4  # 2 поля × 2 λ


class TestFormatText:
    def test_contains_labels_and_terms(self):
        result = compute_global_zernike(build_achromat())
        text = format_global_zernike_text(
            result, wl_names={0.58756: 'd', 0.48613: 'F'})
        assert 'Глобальное разложение Цернике' in text
        assert 'Z20' in text and 'Z40' in text
        assert 'd 0.588' in text and 'F 0.486' in text
        assert '7.000' in text and '0.000' in text
        # 4 строки данных
        data_lines = [ln for ln in text.splitlines()
                      if ln.strip() and ln.strip()[0].isdigit()]
        assert len(data_lines) == 4

    def test_empty_result(self):
        assert format_global_zernike_text({}) == 'Нет данных'
        assert format_global_zernike_text(None) == 'Нет данных'


class TestGlobalZernikeGui:
    """GUI: вкладка «Цернике (глоб.)» с текстом и экспортом."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def test_tab_present(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        titles = [panel.tabText(i) for i in range(panel.count())]
        assert 'Цернике (глоб.)' in titles

    def test_update_fills_text(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel._update_zernike_global(build_achromat())
        text = panel.zernike_global_text.toPlainText()
        assert 'Глобальное разложение Цернике' in text
        assert 'Z20' in text

    def test_export_writes_file(self, tmp_path):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel._update_zernike_global(build_achromat())
        target = tmp_path / 'zernike_global.txt'
        # подменяем диалоги выбора файла и сообщений (без нативных окон)
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        orig_fd = QFileDialog.getSaveFileName
        orig_mb = QMessageBox.information
        QFileDialog.getSaveFileName = (
            lambda *a, **k: (str(target), 'Текст (*.txt)'))
        QMessageBox.information = lambda *a, **k: None
        try:
            panel._export_zernike_global()
        finally:
            QFileDialog.getSaveFileName = orig_fd
            QMessageBox.information = orig_mb
        content = target.read_text(encoding='utf-8')
        assert 'Глобальное разложение Цернике' in content

    def test_precomputed_uses_pipeline_data(self):
        """apply_precomputed берёт разложение из данных пайплайна."""
        from gui.analysis_panel import AnalysisPanel
        from gui.analysis_pipeline import compute_all_analysis
        panel = AnalysisPanel()
        d = compute_all_analysis(build_achromat())
        assert d.get('zernike_global')
        panel.apply_precomputed(build_achromat(), d)
        assert 'Глобальное разложение Цернике' in \
            panel.zernike_global_text.toPlainText()
