"""Регрессионные тесты пункта 13 GAP v2 — параксиальные по λ.

paraxial_trace(sys, wl=...) считает кардинальные отрезки с показателями
преломления заданной λ без копии системы; paraxial_trace_all_wavelengths
прогоняет расчёт для каждой рабочей λ. Таблица «Параксиалы» показывает
полный набор характеристик на каждую λ (PARAXIAL_WL_ROWS).
"""
import copy
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    paraxial_trace, paraxial_trace_all_wavelengths, PARAXIAL_WL_ROWS,
)


def build_achromat() -> OpticalSystem:
    """Клееный дублет К8/ТФ5 с тремя λ: d (первичная), F, C."""
    s = OpticalSystem()
    s.wavelengths = [
        Wavelength(0.58756, 1.0, 'd'),
        Wavelength(0.48613, 1.0, 'F'),
        Wavelength(0.65627, 1.0, 'C'),
    ]
    s.field_points = [FieldPoint(0.0)]
    s.surfaces = [
        Surface(radius=80, glass='К8', thickness=5),
        Surface(radius=-60, glass='ТФ5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


def build_singlet() -> OpticalSystem:
    """Синглет К8 — нормальная дисперсия без компенсации."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.surfaces = [
        Surface(radius=100, glass='К8', thickness=5),
        Surface(radius=-100, glass='', thickness=0),
    ]
    return s


class TestParaxialTraceWl:

    def test_wl_none_is_primary(self):
        """wl=None (прежний вызов) — основная λ, поведение не меняется."""
        s = build_achromat()
        r_default = paraxial_trace(s)
        r_primary = paraxial_trace(s, wl=0.58756)
        assert r_default['wl'] == pytest.approx(0.58756)
        for key in ('focal_length', 'sF_prime', 'sH_prime', 'sP', 'V'):
            assert r_default[key] == pytest.approx(r_primary[key])

    def test_wl_stored_in_result(self):
        r = paraxial_trace(build_achromat(), wl=0.48613)
        assert r['wl'] == pytest.approx(0.48613)

    def test_matches_primary_replacement(self):
        """Прежний приём (копия системы с другой основной λ) даёт те же
        числа, что и прямой параметр wl."""
        s = build_achromat()
        for wl_val in (0.48613, 0.65627):
            s_copy = copy.deepcopy(s)
            s_copy.wavelengths = [Wavelength(wl_val, 1.0, 'x')]
            r_copy = paraxial_trace(s_copy)
            r_param = paraxial_trace(s, wl=wl_val)
            for key in ('focal_length', 'sF_prime', 'sH_prime',
                        'sP', 'sP_prime', 'V'):
                assert r_param[key] == pytest.approx(r_copy[key]), key

    def test_system_not_mutated(self):
        s = build_achromat()
        before = [(w.value, w.name) for w in s.wavelengths]
        paraxial_trace(s, wl=0.48613)
        paraxial_trace_all_wavelengths(s)
        assert [(w.value, w.name) for w in s.wavelengths] == before

    def test_normal_dispersion_shortens_efl(self):
        """Синглет, нормальная дисперсия: n(F) > n(d) > n(C) →
        f'(F) < f'(d) < f'(C)."""
        s = build_singlet()
        fF = paraxial_trace(s, wl=0.48613)['focal_length']
        fd = paraxial_trace(s, wl=0.58756)['focal_length']
        fC = paraxial_trace(s, wl=0.65627)['focal_length']
        assert fF < fd < fC

    def test_chromatic_difference_exists(self):
        """Дублет: кардинальные отрезки различаются между λ (хроматизм)."""
        s = build_achromat()
        fF = paraxial_trace(s, wl=0.48613)
        fC = paraxial_trace(s, wl=0.65627)
        for key in ('focal_length', 'sF_prime', 'sH_prime'):
            assert fF[key] != pytest.approx(fC[key]), key


class TestAllWavelengths:

    def test_one_result_per_wavelength(self):
        s = build_achromat()
        results = paraxial_trace_all_wavelengths(s)
        assert len(results) == 3
        assert [r['wl'] for r in results] == pytest.approx(
            [0.58756, 0.48613, 0.65627])
        # первая λ — основная
        assert results[0]['focal_length'] == pytest.approx(
            paraxial_trace(s)['focal_length'])

    def test_no_wavelengths_falls_back_to_primary(self):
        s = build_achromat()
        s.wavelengths = []
        results = paraxial_trace_all_wavelengths(s)
        assert len(results) == 1
        assert results[0]['wl'] == pytest.approx(0.58756)  # fallback d

    def test_all_table_rows_available(self):
        """Каждый ключ PARAXIAL_WL_ROWS присутствует в результате расчёта."""
        for r in paraxial_trace_all_wavelengths(build_achromat()):
            for _, key, _ in PARAXIAL_WL_ROWS:
                assert key in r, key

    def test_rows_cover_task_set(self):
        """Набор строк — характеристики задания: f', кардинальные отрезки,
        длина, зрачки, V."""
        labels = ' '.join(name for name, _, _ in PARAXIAL_WL_ROWS)
        for token in ("f'", 'sF', 'sH', 'L', 'sP', 'V'):
            assert token in labels


class TestAchromatReport:
    def test_report_does_not_touch_wavelengths(self):
        """achromat_report считает f'_F/f'_C через параметр wl и больше
        не подменяет sys.wavelengths."""
        from achromat import design_achromat, achromat_report
        s = design_achromat(100.0)
        s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
        before = [(w.value, w.name) for w in s.wavelengths]
        report = achromat_report(s)
        assert [(w.value, w.name) for w in s.wavelengths] == before
        assert 'Δf' in report or 'f\'' in report


class TestParaxialWlGui:
    """GUI: таблица параксиалов — колонка на каждую рабочую λ."""

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

    @staticmethod
    def _fill(panel, s):
        from optics_engine import paraxial_trace as pt
        parax = pt(s)
        efl = parax.get('focal_length', 0)
        epd = parax.get('entrance_pupil_diameter', 0)
        fno = efl / epd if epd > 0 else 0
        panel.update_parax(parax, fno, epd, sys=s)

    def test_column_per_wavelength(self, panel):
        self._fill(panel, build_achromat())
        table = panel._parax_wl_table
        assert table.columnCount() == 1 + 3
        headers = [table.horizontalHeaderItem(j).text()
                   for j in range(table.columnCount())]
        assert headers[0] == 'Характеристика'
        assert {'d', 'F', 'C'} <= set(headers)
        assert table.rowCount() == len(PARAXIAL_WL_ROWS)

    def test_chromatic_values_in_table(self, panel):
        """f' и sF' в колонках F и C различаются (вторичный спектр)."""
        self._fill(panel, build_achromat())
        table = panel._parax_wl_table
        headers = [table.horizontalHeaderItem(j).text()
                   for j in range(table.columnCount())]
        row_f = next(i for i in range(table.rowCount())
                     if table.item(i, 0).text().startswith("f'"))
        val = lambda col: float(table.item(row_f, headers.index(col)).text())  # noqa: E731
        assert val('F') != pytest.approx(val('C'))

    def test_single_wavelength_two_columns(self, panel):
        s = build_achromat()
        s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
        self._fill(panel, s)
        table = panel._parax_wl_table
        assert table.columnCount() == 2
        assert table.horizontalHeaderItem(1).text() == 'd'

    def test_unnamed_wavelength_labelled_from_catalog(self, panel):
        """λ без имени подписывается обозначением линии из справочника."""
        s = build_achromat()
        s.wavelengths = [Wavelength(0.58756, 1.0, ''),
                         Wavelength(0.54607, 1.0, '')]
        self._fill(panel, s)
        headers = [panel._parax_wl_table.horizontalHeaderItem(j).text()
                   for j in range(panel._parax_wl_table.columnCount())]
        assert {'d', 'e'} <= set(headers)
