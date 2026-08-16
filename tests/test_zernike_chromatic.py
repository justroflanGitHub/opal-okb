"""Регрессионные тесты пункта 8 GAP v2 — хроматизм разложения Цернике.

Z_nm(λ) для каждой рабочей λ + разности Z_nm(λ) − Z_nm(λ первичной);
таблица рядом с гистограммой коэффициентов (кнопка «Цернике по λ»).
"""
import math

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength
from zernike import (ZERNIKE_TERMS, compute_zernike_coefficients,
                     compute_zernike_chromatic)


def build_achromat() -> OpticalSystem:
    """Клееный дублет K8/TF5 с тремя λ: d (первичная), F, C."""
    s = OpticalSystem()
    s.wavelengths = [
        Wavelength(0.58756, 1.0, 'd'),
        Wavelength(0.48613, 1.0, 'F'),
        Wavelength(0.65627, 1.0, 'C'),
    ]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


NUM_RAYS = 16  # сетка 16×16 (~200 лучей в зрачке на каждую λ)


@pytest.fixture(scope='module')
def chromatic():
    return compute_zernike_chromatic(build_achromat(),
                                     num_rays=NUM_RAYS, max_order=4)


class TestZernikeChromatic:

    def test_per_wavelength_keys(self, chromatic):
        assert {'d', 'F', 'C'} <= set(chromatic.keys())

    def test_delta_keys_from_primary(self, chromatic):
        deltas = {k for k in chromatic if k.startswith('delta_')}
        assert deltas == {'delta_F−d', 'delta_C−d'}

    def test_all_terms_present(self, chromatic):
        expected_names = [name for _, _, name in ZERNIKE_TERMS]
        for key in ('d', 'F', 'C', 'delta_F−d', 'delta_C−d'):
            names = [n for _, n in chromatic[key]]
            assert names == expected_names

    def test_delta_is_difference(self, chromatic):
        """delta_F−d = Z_nm(F) − Z_nm(d) почленно."""
        for (df, _), (dd, _), (delta, _) in zip(chromatic['F'],
                                                chromatic['d'],
                                                chromatic['delta_F−d']):
            assert delta == pytest.approx(df - dd, abs=1e-12)

    def test_primary_column_matches_single(self, chromatic):
        """Колонка первичной λ = прямое разложение для этой λ."""
        s = build_achromat()
        single = compute_zernike_coefficients(s, wl=0.58756,
                                              num_rays=NUM_RAYS, max_order=4)
        for (c1, _), (c2, _) in zip(single, chromatic['d']):
            assert c1 == pytest.approx(c2, abs=1e-12)

    def test_dispersion_changes_defocus(self, chromatic):
        """Хроматизм: Z20 (дефокус) различается между λ."""
        def z20(coeffs):
            return next(c for c, n in coeffs if n == 'Z20 Defocus')
        assert z20(chromatic['F']) != pytest.approx(z20(chromatic['d']),
                                                    abs=1e-6)
        assert abs(z20(chromatic['delta_F−d'])) > 1e-6

    def test_single_wavelength_no_deltas(self):
        s = build_achromat()
        s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
        result = compute_zernike_chromatic(s, num_rays=NUM_RAYS)
        assert set(result.keys()) == {'d'}
        assert not any(k.startswith('delta_') for k in result)


class TestZernikeChromaticGui:
    """GUI: кнопка «Цернике по λ» + таблица Z_nm(λ) на вкладке «Цернике»."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    @pytest.fixture()
    def panel(self):
        from gui.analysis_panel import AnalysisPanel
        return AnalysisPanel()

    def test_button_present_and_toggles_widget(self, panel):
        assert not panel.zernike_w._show_chromatic
        panel.zernike_chrom_btn.setChecked(True)
        assert panel.zernike_w._show_chromatic
        panel.zernike_chrom_btn.setChecked(False)
        assert not panel.zernike_w._show_chromatic

    def test_table_chromatic_columns(self, panel):
        """Таблица: 1 + Nλ + (Nλ−1) разностей = 6 колонок для 3 λ."""
        chromatic = compute_zernike_chromatic(build_achromat(),
                                              num_rays=NUM_RAYS)
        table = panel._build_zernike_chromatic_table(chromatic['d'],
                                                     chromatic)
        assert table.columnCount() == 1 + 3 + 2
        headers = [table.horizontalHeaderItem(j).text()
                   for j in range(table.columnCount())]
        assert headers[0] == 'Полином'
        assert {'d', 'F', 'C'} <= set(headers)
        assert 'delta_F−d' in headers
        assert table.rowCount() == len(ZERNIKE_TERMS)
        # строка Z20: колонка delta_F−d = Z20(F) − Z20(d)
        row_z20 = next(i for i in range(table.rowCount())
                       if 'Z20' in table.item(i, 0).text())
        col_delta = headers.index('delta_F−d')
        cell = float(table.item(row_z20, col_delta).text())
        z20 = lambda coeffs: next(c for c, n in coeffs if n == 'Z20 Defocus')  # noqa: E731
        assert cell == pytest.approx(z20(chromatic['F']) - z20(chromatic['d']),
                                     abs=1e-6)

    def test_update_table_respects_toggle(self, panel):
        s = build_achromat()
        panel._parax_sys = s
        panel._update_zernike_table(s)
        assert panel._zernike_table.columnCount() == 2  # одна λ-колонка
        panel.zernike_chrom_btn.setChecked(True)
        assert panel._zernike_table.columnCount() == 6  # Z_nm(λ) + разности

    def test_widget_set_data_fills_chromatic(self, panel):
        panel.zernike_w.set_data(build_achromat())
        assert panel.zernike_w.coeffs
        assert panel.zernike_w.chromatic_data is not None
        assert {'d', 'F', 'C', 'delta_F−d'} <= set(
            panel.zernike_w.chromatic_data.keys())

    def test_apply_phase2_sets_chromatic_data(self, panel):
        """Фоновый путь: атрибут chromatic_data (не chromatic) заполнен."""
        panel.apply_phase2(build_achromat(), {
            'zernike_coeffs': [(0.0, name) for _, _, name in ZERNIKE_TERMS],
            'zernike_chromatic': {'d': [], 'delta_F−d': []},
        })
        assert panel.zernike_w.chromatic_data == {'d': [], 'delta_F−d': []}
