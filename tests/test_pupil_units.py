"""Регрессионные тесты пункта 16 GAP v2 — единицы зрачка (мм/дптр).

Физика (OPAL-PC Л1.4.4: «единицы измерения положения зрачков … (дптр/мм)»):
1 дптр = 1/м → положение зрачка D = 1000/sP(мм); поле дальнего типа
переводится tan-конверсией через фокусное расстояние: D = 1000·tg ω/f'.
"""
import math

import pytest

from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    paraxial_trace, PARAXIAL_WL_ROWS, PUPIL_POSITION_KEYS,
)
from optics_utils import (
    DIOPTRE_PER_M, INFINITY_TEXT,
    PUPIL_UNIT_MM, PUPIL_UNIT_DIOPTRE, PUPIL_UNIT_CHOICES,
    FIELD_UNIT_DEG, FIELD_UNIT_MM,
    get_pupil_unit, set_pupil_unit,
    add_pupil_unit_observer, remove_pupil_unit_observer, pupil_unit_is_dioptre,
    mm_to_dioptre, dioptre_to_mm,
    field_deg_to_dioptre, field_dioptre_to_deg, field_native_unit,
    field_unit_display, format_pupil_position, format_field,
    field_values_display,
)


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 — базовая тестовая система (дальний тип)."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


@pytest.fixture(autouse=True)
def _restore_pupil_unit():
    """Каждый тест завершается в исходной единице (мм)."""
    set_pupil_unit(PUPIL_UNIT_MM)
    yield
    set_pupil_unit(PUPIL_UNIT_MM)


class TestConstants:
    def test_dioptre_factor(self):
        """1 дптр = 1/м → множитель 1000 (мм → дптр)."""
        assert DIOPTRE_PER_M == 1000.0

    def test_unit_choices(self):
        assert PUPIL_UNIT_CHOICES == ('мм', 'дптр')
        assert PUPIL_UNIT_MM == 'мм'
        assert PUPIL_UNIT_DIOPTRE == 'дптр'

    def test_field_units(self):
        assert FIELD_UNIT_DEG == '°'
        assert FIELD_UNIT_MM == 'мм'

    def test_parax_rows_mark_pupil_positions(self):
        """Ключи положений зрачков входят в строки параксиальной таблицы."""
        assert PUPIL_POSITION_KEYS == ('sP', 'sP_prime')
        keys = {key for _, key, _ in PARAXIAL_WL_ROWS}
        assert set(PUPIL_POSITION_KEYS) <= keys


class TestMmDioptre:
    """Конверсия обратных длин: D = 1000/мм (положения зрачков, радиусы)."""

    @pytest.mark.parametrize("mm,dpt", [
        (500.0, 2.0),       # 0.5 м → 2 дптр
        (1000.0, 1.0),      # 1 м → 1 дптр
        (2000.0, 0.5),
        (100.0, 10.0),
        (-250.0, -4.0),     # знак сохраняется
        (-1.0, -1000.0),
    ])
    def test_known_values(self, mm, dpt):
        assert mm_to_dioptre(mm) == pytest.approx(dpt)

    @pytest.mark.parametrize("mm", [0.5, 1.0, 12.345, 100.0, -500.0, 1e6])
    def test_round_trip(self, mm):
        assert dioptre_to_mm(mm_to_dioptre(mm)) == pytest.approx(mm)
        assert mm_to_dioptre(dioptre_to_mm(mm)) == pytest.approx(mm)

    def test_zero_maps_to_infinity(self):
        """sP = 0 (зрачок «на бесконечности») → 0 дптр = ±∞."""
        assert mm_to_dioptre(0.0) == math.inf
        assert mm_to_dioptre(-0.0) == -math.inf
        assert math.copysign(1.0, mm_to_dioptre(-1e-12)) == -1.0
        assert dioptre_to_mm(0.0) == math.inf

    def test_negative_preserves_sign(self):
        assert mm_to_dioptre(-100.0) < 0
        assert mm_to_dioptre(-100.0) == pytest.approx(-10.0)
        assert dioptre_to_mm(-10.0) == pytest.approx(-100.0)

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_non_finite_rejected(self, bad):
        with pytest.raises(ValueError):
            mm_to_dioptre(bad)
        with pytest.raises(ValueError):
            dioptre_to_mm(bad)


class TestFieldDegDioptre:
    """Поле дальнего типа: D = 1000·tg ω / f' (tan-конверсия через f')."""

    def test_known_value(self):
        """f' = 100 мм, ω = 45° → tg = 1 → 1000/100 = 10 дптр."""
        assert field_deg_to_dioptre(45.0, 100.0) == pytest.approx(10.0)

    def test_zero_field(self):
        assert field_deg_to_dioptre(0.0, 100.0) == 0.0

    def test_small_angle_linear(self):
        """Малые углы: D ≈ 1000·ω[рад]/f'."""
        for deg in (0.5, 1.0, 2.0):
            linear = 1000.0 * math.radians(deg) / 100.0
            assert field_deg_to_dioptre(deg, 100.0) == pytest.approx(
                linear, rel=1e-3)

    def test_sign_and_symmetry(self):
        assert field_deg_to_dioptre(-10.0, 100.0) == pytest.approx(
            -field_deg_to_dioptre(10.0, 100.0))

    @pytest.mark.parametrize("deg", [0.0, 1.5, 7.0, 30.0, -12.0])
    def test_round_trip(self, deg):
        dpt = field_deg_to_dioptre(deg, 100.0)
        assert field_dioptre_to_deg(dpt, 100.0) == pytest.approx(deg)

    @pytest.mark.parametrize("focal", [0.0, -0.0, 1e-12])
    def test_zero_focal_rejected(self, focal):
        with pytest.raises(ValueError):
            field_deg_to_dioptre(5.0, focal)
        with pytest.raises(ValueError):
            field_dioptre_to_deg(5.0, focal)

    def test_native_unit_by_object_type(self):
        assert field_native_unit(build_doublet()) == FIELD_UNIT_DEG
        finite = build_doublet()
        from optics_engine import ObjectType
        finite.object_type = ObjectType.FINITE
        assert field_native_unit(finite) == FIELD_UNIT_MM


class TestUnitState:
    """Состояние единиц — в одном месте (utils), с наблюдателями."""

    def test_default_is_mm(self):
        assert get_pupil_unit() == PUPIL_UNIT_MM
        assert pupil_unit_is_dioptre() is False

    def test_set_and_back(self):
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        assert get_pupil_unit() == PUPIL_UNIT_DIOPTRE
        assert pupil_unit_is_dioptre() is True
        set_pupil_unit(PUPIL_UNIT_MM)
        assert get_pupil_unit() == PUPIL_UNIT_MM

    def test_invalid_unit_rejected(self):
        with pytest.raises(ValueError):
            set_pupil_unit('m-1')

    def test_same_unit_is_noop_no_notify(self):
        calls = []
        add_pupil_unit_observer(calls.append)
        set_pupil_unit(PUPIL_UNIT_MM)  # уже мм — наблюдателей нет
        assert calls == []
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        assert calls == [PUPIL_UNIT_DIOPTRE]
        remove_pupil_unit_observer(calls.append)
        set_pupil_unit(PUPIL_UNIT_MM)
        assert calls == [PUPIL_UNIT_DIOPTRE]  # отписан — не вызывается


class TestFormatting:
    def test_pupil_position_mm(self):
        assert format_pupil_position(12.3456, PUPIL_UNIT_MM) == '12.3456'

    def test_pupil_position_dioptre(self):
        assert format_pupil_position(500.0, PUPIL_UNIT_DIOPTRE) == '2.0000'

    def test_pupil_position_infinity(self):
        assert format_pupil_position(0.0, PUPIL_UNIT_DIOPTRE) == INFINITY_TEXT
        assert format_pupil_position(-1e-12, PUPIL_UNIT_DIOPTRE) == INFINITY_TEXT

    def test_field_format_native_deg(self):
        assert format_field(5.0, 100.0, FIELD_UNIT_DEG) == '5.0000'
        assert format_field(5.0, 0.0, FIELD_UNIT_DEG, 1, with_unit=True) == '5.0°'

    def test_field_format_dioptre(self):
        """ω = 45°, f' = 100 мм → 10 дптр."""
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        assert format_field(45.0, 100.0, FIELD_UNIT_DEG) == '10.0000'
        assert format_field(45.0, 100.0, FIELD_UNIT_DEG,
                            with_unit=True) == '10.0000 дптр'

    def test_field_format_mm_field_stays_mm(self):
        """Поле ближнего типа (мм предмета) в диоптрии не переводится."""
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        assert format_field(7.5, 100.0, FIELD_UNIT_MM) == '7.5000'

    def test_field_unit_display_requires_efl(self):
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        assert field_unit_display(FIELD_UNIT_DEG, 100.0) == PUPIL_UNIT_DIOPTRE
        assert field_unit_display(FIELD_UNIT_DEG, 0.0) == FIELD_UNIT_DEG
        assert field_unit_display(FIELD_UNIT_MM, 100.0) == FIELD_UNIT_MM
        set_pupil_unit(PUPIL_UNIT_MM)
        assert field_unit_display(FIELD_UNIT_DEG, 100.0) == FIELD_UNIT_DEG

    def test_field_values_display(self):
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        vals, unit = field_values_display([0.0, 5.0, 45.0], 100.0,
                                          FIELD_UNIT_DEG)
        assert unit == PUPIL_UNIT_DIOPTRE
        assert vals[0] == pytest.approx(0.0)
        assert vals[1] == pytest.approx(1000.0 * math.tan(math.radians(5.0))
                                        / 100.0)
        assert vals[2] == pytest.approx(10.0)
        # монотонность сохраняется (ось остаётся упорядоченной)
        assert vals == sorted(vals)


class _QtOffscreen:
    """Общий фиксатор: offscreen Qt + приложение."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app


class TestParaxTableUnits(_QtOffscreen):
    """Таблица «Параксиальные»: строки sP/sP' в выбранных единицах."""

    def _panel_with_parax(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        s = build_doublet()
        parax = paraxial_trace(s)
        efl = parax.get('focal_length', 0)
        epd = parax.get('entrance_pupil_diameter', 0) or 10.0
        panel.update_parax(parax, efl / epd, epd, sys=s)
        return panel, parax

    def _sp_row(self, panel, row_idx):
        table = panel._parax_wl_table
        return table.item(row_idx, 0).text(), table.item(row_idx, 1).text()

    def test_mm_headers_and_values(self):
        panel, parax = self._panel_with_parax()
        # строки PARAXIAL_WL_ROWS: sP — индекс 6, sP' — 7
        title, val = self._sp_row(panel, 6)
        assert title == 'sP (мм)'
        # численно совпадает с расчётом (у дублета sP ≈ -1e-15 — шум
        # округления, панель показывает его как «0.0000»)
        assert float(val) == pytest.approx(parax['sP'], abs=1e-4)

    def test_dioptre_headers_and_values(self):
        panel, parax = self._panel_with_parax()
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        panel._update_parax_table()
        title, val = self._sp_row(panel, 6)
        assert title == 'sP (дптр)'
        assert val == format_pupil_position(parax['sP'], PUPIL_UNIT_DIOPTRE)
        title_p, val_p = self._sp_row(panel, 7)
        assert title_p == 'sP\' (дптр)'
        assert val_p == format_pupil_position(parax['sP_prime'],
                                              PUPIL_UNIT_DIOPTRE)

    def test_results_panel_sp_rows(self):
        """Панель результатов (main.py): sP/sP' через общий хелпер."""
        from main import ResultsPanel
        rp = ResultsPanel()
        rp._parax_result = {'focal_length': 100.0, 'sP': 500.0,
                            'sP_prime': 200.0}
        rp._fno = 10.0
        rp._epd = 10.0
        rp._update_parax_display()
        texts = [rp.parax_table.item(i, 1).text()
                 for i in range(rp.parax_table.rowCount())]
        assert '500.0000 мм' in texts
        assert '200.0000 мм' in texts
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        rp._update_parax_display()
        texts = [rp.parax_table.item(i, 1).text()
                 for i in range(rp.parax_table.rowCount())]
        assert '2.0000 дптр' in texts
        assert '5.0000 дптр' in texts

    def test_results_panel_infinity(self):
        """sP = 0 → ∞ без единицы (зрачок «на бесконечности»)."""
        from main import ResultsPanel
        rp = ResultsPanel()
        rp._parax_result = {'focal_length': 100.0, 'sP': 0.0,
                            'sP_prime': 0.0}
        rp._fno = 10.0
        rp._epd = 10.0
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        rp._update_parax_display()
        texts = [rp.parax_table.item(i, 1).text()
                 for i in range(rp.parax_table.rowCount())]
        assert '∞' in texts


class TestFieldTablesAndAxes(_QtOffscreen):
    """Оси поля и заголовки таблиц в единицах отображения (п. 16)."""

    def _field_system(self) -> OpticalSystem:
        s = build_doublet()
        s.field_points = [FieldPoint(y=0.0), FieldPoint(y=5.0)]
        return s

    def test_distortion_table_header_and_values(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        s = self._field_system()
        parax = paraxial_trace(s)
        panel.update_parax(parax, 10.0, 10.0, sys=s)
        panel._update_distortion_table(s)

        def field_col():
            table = panel._table_containers['distortion'].layout().itemAt(0).widget()
            header = table.horizontalHeaderItem(0).text()
            first = table.item(0, 0).text()
            return header, first

        header, _ = field_col()
        assert header == 'Поле Y (°)'   # родная единица — градусы
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        panel._update_distortion_table(s)
        header, first = field_col()
        assert header == 'Поле Y (дптр)'
        assert first == format_field(0.0, parax['focal_length'], FIELD_UNIT_DEG)

    def test_beam_table_header(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        s = build_doublet()
        parax = paraxial_trace(s)
        panel.update_parax(parax, 10.0, 10.0, sys=s)
        fake_beam = [{'field_y': 5.0, 'Ay': 4.0, 'Ay_prime': 4.0,
                      'vignetting_upper': 1.0, 'vignetting_lower': 1.0,
                      'relative_illumination': 1.0}]
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        panel._update_beam_table(s, beam_data=fake_beam)
        table = panel._table_containers['beam'].layout().itemAt(0).widget()
        assert table.horizontalHeaderItem(0).text() == 'Поле (дптр)'
        assert table.item(0, 0).text() == format_field(
            5.0, parax['focal_length'], FIELD_UNIT_DEG)

    def test_fan_tables_keep_normalized_pupil(self):
        """Высоты лучей — нормированные зрачковые координаты (как в OPAL-PC
        Л1.4.6); переключатель единиц их не меняет."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        s = build_doublet()
        parax = paraxial_trace(s)
        panel.update_parax(parax, 10.0, 10.0, sys=s)
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        panel._update_transverse_table(s)
        table = panel._table_containers['transverse'].layout().itemAt(0).widget()
        assert table.horizontalHeaderItem(0).text() == 'Высота луча'

    def test_field_scale_label(self):
        """Подпись масштаба оси поля: «±5.0°» / «±0.9 дптр» (f'=100)."""
        from gui.widgets.aberration_graphs import DistortionWidget
        w = DistortionWidget()
        w.efl_mm = 100.0
        w.field_native_unit = FIELD_UNIT_DEG
        assert w.field_scale_label(5.0) == '±5.0°'
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        assert w.field_scale_label(5.0) == '±0.9 дптр'

    def test_field_axis_conversion(self):
        from gui.widgets.aberration_graphs import ComaWidget
        w = ComaWidget()
        w.efl_mm = 100.0
        w.field_native_unit = FIELD_UNIT_DEG
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        vals, unit = w.field_axis([0.0, 45.0])
        assert unit == PUPIL_UNIT_DIOPTRE
        assert vals[0] == pytest.approx(0.0)
        assert vals[1] == pytest.approx(10.0)

    def test_wf_rms_axis_label(self):
        """График СКВ по полю (вкладка «Цернике»): подпись оси — единица
        отображения; данные пересчитываются tan-конверсией."""
        from gui.widgets import WfRmsFieldMplWidget
        w = WfRmsFieldMplWidget()
        w.set_data(self._field_system())
        ax = w.figure.axes[0]
        assert ax.get_xlabel() == 'Поле (°)'
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        w.redraw()
        ax = w.figure.axes[0]
        assert ax.get_xlabel() == 'Поле (дптр)'
        # нулевая точка поля остаётся нулевой в любых единицах
        assert ax.lines[0].get_xdata()[0] == pytest.approx(0.0)

    def test_wf_rms_table_row_units(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        s = self._field_system()
        parax = paraxial_trace(s)
        panel.update_parax(parax, 10.0, 10.0, sys=s)
        panel.wf_rms_field_w.set_data(s)
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        panel._update_wf_rms_field_table(s)
        table = panel._wf_rms_table
        texts = [table.item(i, 0).text() for i in range(table.rowCount())]
        assert any(t.endswith(' дптр') for t in texts)


class TestPupilUnitSwitch(_QtOffscreen):
    """UI-переключатель: комбобоксы обеих панелей — одно состояние."""

    def test_combo_items_and_accessor(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        assert [panel.pupil_unit_combo.itemText(i)
                for i in range(panel.pupil_unit_combo.count())] == ['мм', 'дптр']
        assert panel.get_pupil_unit() == PUPIL_UNIT_MM

    def test_combo_changes_shared_state(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel.pupil_unit_combo.setCurrentText('дптр')
        assert get_pupil_unit() == PUPIL_UNIT_DIOPTRE
        panel.pupil_unit_combo.setCurrentText('мм')
        assert get_pupil_unit() == PUPIL_UNIT_MM

    def test_state_change_syncs_combo_and_refreshes(self):
        """Смена состояния извне: комбобокс синхронизируется, параксиальная
        таблица перестраивается без повторного расчёта."""
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        s = build_doublet()
        parax = paraxial_trace(s)
        panel.update_parax(parax, 10.0, 10.0, sys=s)
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)   # как с другой панели
        assert panel.pupil_unit_combo.currentText() == 'дптр'
        title = panel._parax_wl_table.item(6, 0).text()
        assert title == 'sP (дптр)'

    def test_results_combo_shares_state(self):
        from gui.analysis_panel import AnalysisPanel
        from main import ResultsPanel
        analysis = AnalysisPanel()
        results = ResultsPanel()
        results.pupil_unit_combo.setCurrentText('дптр')
        assert get_pupil_unit() == PUPIL_UNIT_DIOPTRE
        assert analysis.pupil_unit_combo.currentText() == 'дптр'
        set_pupil_unit(PUPIL_UNIT_MM)
        assert results.pupil_unit_combo.currentText() == 'мм'
        assert analysis.pupil_unit_combo.currentText() == 'мм'

    def test_observer_does_not_keep_panel_alive(self):
        """Слабая подписка: реестр не удерживает панели — собранная GC
        панель не получает оповещений (нет утечки и межтестовых сбоев)."""
        import gc
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)   # живая панель синхронизируется
        assert panel.pupil_unit_combo.currentText() == 'дптр'
        set_pupil_unit(PUPIL_UNIT_MM)
        del panel
        gc.collect()
        # после сборки панели смена единиц не касается мёртвых наблюдателей
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        set_pupil_unit(PUPIL_UNIT_MM)

    def test_observer_survives_deleted_qt_object(self):
        """C++-объект панели удалён, Python-обёртка жива: наблюдатель
        выбывает из реестра, смена единиц не падает (RuntimeError гасится)."""
        from gui.analysis_panel import AnalysisPanel
        from PyQt5 import sip
        panel = AnalysisPanel()
        sip.delete(panel)
        set_pupil_unit(PUPIL_UNIT_DIOPTRE)
        set_pupil_unit(PUPIL_UNIT_MM)
