"""Регрессионные тесты пункта 11 GAP v2 — справочник спектральных линий.

Единый источник значений λ стандартных линий (utils/spectral_lines.py);
проекции-справочники (WL_NAMES, STANDARD_WAVELENGTHS, _NAMED_WL) и
диалоги выбора λ построены на нём.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from utils.spectral_lines import (
    SPECTRAL_LINES, SpectralLine, WL_MATCH_TOL_NM,
    format_spectral_line, named_wavelengths, spectral_line_by_name,
    spectral_line_for_wavelength, wavelength_names,
)


class TestCatalog:
    """Справочник содержит все линии задания с обозначениями."""

    #: линии из задания (п. 11): обозначение → длина волны, нм
    REQUIRED = {
        'F': 486.13, 'd': 587.56, 'C': 656.27, 'e': 546.07,
        'g': 435.83, 'D': 589.30, 'h': 404.66, 'r': 706.52,
        "C'": 643.85, "A'": 768.19,
    }

    @pytest.mark.parametrize('name,nm', sorted(REQUIRED.items()))
    def test_required_line_present(self, name, nm):
        line = spectral_line_by_name(name)
        assert line is not None, f'нет линии {name}'
        assert line.wavelength_nm == pytest.approx(nm, abs=0.01)
        assert line.element, 'нет обозначения (элемент-источник)'
        assert line.color, 'нет цветового обозначения'

    def test_sorted_by_wavelength_unique_names(self):
        nms = [line.wavelength_nm for line in SPECTRAL_LINES]
        assert nms == sorted(nms), 'справочник не отсортирован по λ'
        names = [line.name for line in SPECTRAL_LINES]
        assert len(set(names)) == len(names), 'дублирование обозначений'

    def test_legacy_lines_kept(self):
        """Линии прежних справочников сохранены (файлы проектов)."""
        for name in ('i', "G'", "F'", 's', 't'):
            assert spectral_line_by_name(name) is not None


class TestLookups:
    def test_by_name_unknown(self):
        assert spectral_line_by_name('ZZ') is None

    def test_for_wavelength_near(self):
        line = spectral_line_for_wavelength(0.48613)   # F
        assert line is not None and line.name == 'F'

    def test_for_wavelength_new_A_prime(self):
        line = spectral_line_for_wavelength(0.7682)    # A' (новая линия)
        assert line is not None and line.name == "A'"

    def test_for_wavelength_far_returns_none(self):
        assert spectral_line_for_wavelength(0.550, tol_nm=WL_MATCH_TOL_NM) is None

    def test_wavelength_um_property(self):
        assert spectral_line_by_name('d').wavelength_um == pytest.approx(0.58756)

    def test_format_contains_designation(self):
        text = format_spectral_line(spectral_line_by_name('d'))
        assert '587.56 нм' in text and 'He' in text


class TestSingleSource:
    """Старые справочники — проекции нового каталога, значения согласованы."""

    def test_wl_names_projection(self):
        import optics_utils
        assert optics_utils.WL_NAMES == wavelength_names()
        assert optics_utils.WL_NAMES[0.76819] == "A'"

    def test_standard_wavelengths_projection(self):
        import fileio.json_io as json_io
        assert json_io.STANDARD_WAVELENGTHS == named_wavelengths()
        assert json_io.STANDARD_WAVELENGTHS["A'"] == pytest.approx(0.76819)

    def test_D_line_consistent(self):
        """Прежний расклад 589.29/589.30 устранён — значение одно."""
        import optics_utils
        import fileio.json_io as json_io
        d_nm = spectral_line_by_name('D').wavelength_nm
        assert json_io.STANDARD_WAVELENGTHS['D'] == pytest.approx(d_nm / 1000.0)
        assert optics_utils.WL_NAMES[d_nm / 1000.0] == 'D'

    def test_named_wl_labels_projection(self):
        import gui.widgets.aberration_graphs as ag
        catalog_nm = {line.wavelength_nm: line.name for line in SPECTRAL_LINES}
        for nm, name in ag._NAMED_WL.items():
            assert catalog_nm.get(nm) == name, 'подпись вне справочника'
        # линии задания подписываются на графиках
        for name in TestCatalog.REQUIRED:
            nm = spectral_line_by_name(name).wavelength_nm
            assert ag._NAMED_WL.get(nm) == name

    def test_no_duplicated_color_palette(self):
        """Цветовая палитра одна (base) — якоря по обозначениям линий."""
        import gui.widgets.aberration_graphs as ag
        import gui.widgets.base as base
        assert not hasattr(ag, '_WL_COLORS')
        # ближайший якорь — та же палитра, λ якорей из справочника
        assert (ag._wl_to_color(0.5).name()
                == base.wl_to_plot_color(0.5).name() == '#0050ff')


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


class TestStandardLineDialog:
    def test_lists_whole_catalog_with_designations(self, app):
        from gui.dialogs.spectral_dialog import StandardLineDialog
        dlg = StandardLineDialog()
        assert dlg.line_list.count() == len(SPECTRAL_LINES)
        texts = [dlg.line_list.item(i).text()
                 for i in range(dlg.line_list.count())]
        a_prime = [t for t in texts if "A'" in t]
        assert a_prime and '768.19 нм' in a_prime[0] and 'K' in a_prime[0]

    def test_selected_line_roundtrip(self, app):
        from gui.dialogs.spectral_dialog import StandardLineDialog
        dlg = StandardLineDialog()
        dlg.line_list.setCurrentRow(0)
        name, wl = dlg.selected_line()
        assert name == SPECTRAL_LINES[0].name
        assert wl == pytest.approx(SPECTRAL_LINES[0].wavelength_um)

    def test_selected_line_none_without_selection(self, app):
        from gui.dialogs.spectral_dialog import StandardLineDialog
        dlg = StandardLineDialog()
        assert dlg.selected_line() is None


class TestSpectralDialogUsesCatalog:
    def test_on_standard_adds_catalog_row(self, app, monkeypatch):
        """Кнопка «Стандартные...» добавляет линию из справочника."""
        import gui.dialogs.spectral_dialog as sd
        from optics_engine import OpticalSystem, Wavelength
        system = OpticalSystem()
        system.wavelengths = [Wavelength(0.54607, 1.0, 'e')]
        dlg = sd.SpectralDialog(system)
        rows_before = dlg.wl_table.rowCount()
        monkeypatch.setattr(sd, 'pick_standard_line',
                            lambda parent=None: ("A'", 0.76819))
        dlg._on_standard()
        assert dlg.wl_table.rowCount() == rows_before + 1
        r = dlg.wl_table.rowCount() - 1
        assert dlg.wl_table.item(r, 0).text() == '0.7682'
        assert dlg.wl_table.item(r, 1).text() == '1.0'
        assert dlg.wl_table.item(r, 2).text() == "A'"

    def test_on_standard_cancelled_no_row(self, app, monkeypatch):
        import gui.dialogs.spectral_dialog as sd
        from optics_engine import OpticalSystem, Wavelength
        system = OpticalSystem()
        system.wavelengths = [Wavelength(0.54607, 1.0, 'e')]
        dlg = sd.SpectralDialog(system)
        rows_before = dlg.wl_table.rowCount()
        monkeypatch.setattr(sd, 'pick_standard_line', lambda parent=None: None)
        dlg._on_standard()
        assert dlg.wl_table.rowCount() == rows_before
