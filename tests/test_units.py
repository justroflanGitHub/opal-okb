# -*- coding: utf-8 -*-
"""Тесты системы единиц OPAL (analysis/units.py) + TABOC1/TABOC2
(analysis/tables.py, реверс §11+§19, волна 7 TASK_UNITS).

Эталоны: extracted/opal_okb/RT__2236.PRN (TABOC1/TABOC2 осевого пучка,
система «IR -.2X D=10 2W=72» = запись 1 USBINOCL.LBO — all-air, лучи не
проходят; сверяются структура, шапки побайтово и линейность H ЗР =
зона×Ax, §19.1.2) и RT__2250.PRN (точки меры «гр.мнсек» TABGL).
"""
import math
from pathlib import Path

import pytest

from tests.conftest import requires_prn_rt2236, requires_prn_rt2250

from optics_engine import OpticalSystem, Surface, Wavelength
from optics_utils import get_effective_aperture

from analysis.tables import (
    TABOC1_HEADER, TABOC2_HEADER, field_zones, format_taboc1,
    format_taboc2, taboc1_rows, taboc2_rows,
)
from analysis.units import (
    MM_PER_DIOPTRE, deg_to_gms, from_grminsec, grminsec,
    mm_to_dioptres, pupil_h_mm, pupil_h_out_mm, tg100,
)
from fileio.protocol import export_protocol
from optics_engine import paraxial_trace

BASE = Path(__file__).resolve().parent.parent
RT2236 = BASE / 'extracted' / 'opal_okb' / 'RT__2236.PRN'
RT2250 = BASE / 'extracted' / 'opal_okb' / 'RT__2250.PRN'


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 — базовая тестовая система (как
    test_gauge_rays; дальний тип, без точек поля — чистый осевой пучок)."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=70),
    ]
    return s


def _parse_fwo(field: str):
    """Число из поля OPAL без ведущего нуля ('.816' → 0.816)."""
    field = field.strip()
    if not field:
        return None
    if field.startswith('-.'):
        field = '-0.' + field[2:]
    elif field.startswith('.'):
        field = '0.' + field[1:]
    return float(field)


def _etalon_lines(path):
    return path.read_bytes().decode('cp866').splitlines()


# ── units.py: мм ↔ дптр ────────────────────────────────────────────────────

class TestMmToDioptres:
    """Продольные дальнего типа: D = 1000/мм (§19.2.2)."""

    def test_constant(self):
        assert MM_PER_DIOPTRE == 1000.0

    @pytest.mark.parametrize("mm,dpt", [
        (100.0, 10.0),      # ТЗ: 100 мм → 10 дптр
        (500.0, 2.0),
        (1000.0, 1.0),
        (-250.0, -4.0),     # знак сохраняется
    ])
    def test_known_values(self, mm, dpt):
        assert mm_to_dioptres(mm) == pytest.approx(dpt)

    def test_zero_returns_none(self):
        """0 мм (зрачок «на бесконечности») → пустая ячейка таблицы."""
        assert mm_to_dioptres(0.0) is None
        assert mm_to_dioptres(-0.0) is None
        assert mm_to_dioptres(1e-13) is None

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_non_finite_rejected(self, bad):
        with pytest.raises(ValueError):
            mm_to_dioptres(bad)


# ── units.py: мера «(гр.мнсек)» ───────────────────────────────────────────

class TestDegToGms:
    """«гр.мнсек» = градусы + минуты/100 (проверка гипотез ТЗ).

    ТЗ допускало «десятичные градусы» (−36.000000 при 2W=72) и
    «град×3600»; нецелые углы эталона RT__2250 разводят гипотезы:
    ω' = 9.09104° напечатано «9.054624» = 9°05.4624'.
    """

    def test_etalon_whole_degree(self):
        """Поле зоны 1.000 эталона RT__2250 (2W=72 → −36°) — точно."""
        assert deg_to_gms(-36.0) == '-36.000000'.rjust(12)

    def test_etalon_fractional_degree(self):
        """ω' = 9.09104° → «9.054624» (RT__2250, побайтово, волна 5)."""
        assert deg_to_gms(9.09104) == '9.054624'.rjust(12)

    def test_hypothesis_deg_times_3600_refuted(self):
        """«град×3600»: −36° дало бы «-129600.000000» — эталон пишет
        «-36.000000» (RT__2250)."""
        text = deg_to_gms(-36.0)
        assert '129600' not in text
        assert _parse_fwo(text) == pytest.approx(-36.0)

    def test_hypothesis_decimal_degrees_refuted(self):
        """«десятичные градусы»: 9.09104° дало бы «9.091040» — эталон
        печатает «9.054624» (минуты/100, не доли градуса)."""
        assert deg_to_gms(9.09104) != '9.091040'.rjust(12)
        assert _parse_fwo(deg_to_gms(9.09104)) == pytest.approx(
            9.054624, abs=1e-6)

    def test_no_leading_zero(self):
        """«-.535640»-стиль: ведущий нуль мантиссы не печатается
        (дисторсия RT__2250: −0.89273° → −0°53.5638')."""
        assert deg_to_gms(-0.89273) == '-.535638'.rjust(12)
        assert deg_to_gms(0.5) == '.300000'.rjust(12)   # 0°30.0000'

    @requires_prn_rt2250
    def test_etalon_tabgl_field_cell(self):
        """Ячейка «(гр.мнсек)» предмета зоны 1.000 в TABGL эталона
        RT__2250 совпадает с deg_to_gms(−36°) символ в символ."""
        lines = _etalon_lines(RT2250)
        start = next(i for i, ln in enumerate(lines)
                     if 'Характеристики главных лучей' in ln)
        row = lines[start + 4]                 # первая строка данных (N=1)
        cell = row[4 + 7:4 + 7 + 12].strip()   # поле f12.6 предмета
        assert cell == '-36.000000'
        assert deg_to_gms(-36.0).strip() == cell

    @pytest.mark.parametrize("deg", [-36.0, 9.09104, -0.89273, 0.0,
                                     30.657124, -7.5, 179.999])
    def test_width_and_round_trip(self, deg):
        text = deg_to_gms(deg)
        assert len(text) == 12
        back = from_grminsec(_parse_fwo(text))
        assert back == pytest.approx(deg, abs=2e-5)  # 4 знака минут

    def test_grminsec_exact_points(self):
        assert grminsec(9.09104) == pytest.approx(9.054624)
        assert grminsec(-36.0) == -36.0
        assert grminsec(0.5) == pytest.approx(0.3)


# ── units.py: зрачковые координаты ─────────────────────────────────────────

class TestPupilCoordinates:
    """tg×100 и H ЗР/H' ЗР — четвёрка юнитов пула 0x44500 (§19.1.1)."""

    def test_tg100(self):
        assert tg100(45.0) == pytest.approx(100.0)
        assert tg100(0.0) == 0.0
        assert tg100(-30.0) == pytest.approx(-100 * math.tan(
            math.radians(30.0)))

    def test_pupil_h_mm(self):
        """ТЗ: зона 0.7, Ax = 5 → H ЗР = 3.5 (§19.1: H ЗР = отн.зр × Ax)."""
        assert pupil_h_mm(0.7, 5.0) == pytest.approx(3.5)
        assert pupil_h_mm(1.0, 5.0) == pytest.approx(5.0)
        assert pupil_h_mm(0.0, 5.0) == 0.0

    def test_pupil_h_out_mm(self):
        """H' ЗР — тот же закон в пространстве изображений (штрих)."""
        assert pupil_h_out_mm(math.sqrt(3) / 2, 3.0) == pytest.approx(
            2.598076, abs=1e-6)
        assert pupil_h_out_mm(0.5, 8.0) == pytest.approx(4.0)


# ── TABOC2: золотая сверка структуры с RT__2236 ────────────────────────────

def _etalon_taboc2_lines():
    """3 строки шапки + 5 строк данных TABOC2 эталона RT__2236."""
    lines = _etalon_lines(RT2236)
    start = next(i for i, ln in enumerate(lines)
                 if ln.lstrip().startswith("─Tg'*100"))
    return lines[start - 1:]


@requires_prn_rt2236
class TestTaboc2GoldenRT2236:
    """Эталон RT__2236: шапки побайтово, H ЗР = зона × Ax точно."""

    def test_header_byte_exact(self):
        """Шапка осевого варианта — строки эталона символ в символ."""
        etalon = _etalon_taboc2_lines()
        assert list(TABOC2_HEADER) == etalon[:3]

    def test_h_zr_is_zone_times_ax(self):
        """§19.1.2: Н ЗР линеен по зоне точно до 4-го знака (Ax = 5 мм,
        «D=10» шапки) — номинальная входная координата, не трассировка."""
        rows = _etalon_taboc2_lines()[3:]
        zones = field_zones(4) + [0.0]
        assert len(rows) == len(zones) == 5
        for zone, line in zip(zones, rows):
            tokens = line.split()
            h_printed = _parse_fwo(tokens[-1])       # колонка «Н ЗР (мм)»
            assert h_printed == pytest.approx(
                pupil_h_mm(zone, 5.0), abs=5e-5)     # печать — 4 знака

    def test_zone_scheme(self):
        """Зоны зрачка равной площади: 1/.866/.707/.5 + осевая (§19.1.2).

        Колонка «Отн.зр koop.» — первая таблица эталона (TABOC1).
        """
        lines = _etalon_lines(RT2236)
        start = next(i for i, ln in enumerate(lines)
                     if 'koop.' in ln)
        zones = [_parse_fwo(ln.split()[0]) for ln in lines[start + 1:start + 5]]
        assert zones == pytest.approx(field_zones(4), abs=2e-3)


# ── TABOC1/TABOC2 на дублете ───────────────────────────────────────────────

class TestTaboc1Rows:
    def test_rows_structure(self):
        rows = taboc1_rows(build_doublet())
        assert [r['zone'] for r in rows] == pytest.approx(
            field_zones(4) + [0.0])
        for row in rows[:-1]:
            assert row['longitudinal_mm'] is not None
            assert row['transverse_mer_mm'] is not None
            # осевой меридиональный веер: сагиттальная компонента ≡ 0
            assert row['transverse_sag_mm'] == 0.0

    def test_axial_row_zero(self):
        row = taboc1_rows(build_doublet())[-1]
        assert row['zone'] == 0.0
        assert all(v == 0 for k, v in row.items() if k != 'zone')

    def test_empty_system_single_row(self):
        rows = taboc1_rows(OpticalSystem())
        assert len(rows) == 1 and rows[0]['zone'] == 0.0
        assert 'koop.' in format_taboc1(rows)


class TestTaboc2Rows:
    """ТЗ: W монотонен по зоне, H ЗР = зона×Ax, Z'm/C's конечны."""

    def test_wave_monotonic_over_zones(self):
        rows = taboc2_rows(build_doublet())[:-1]   # зоны от края к центру
        waves = [abs(r['wave']) for r in rows]
        assert all(a >= b for a, b in zip(waves, waves[1:]))  # |W| спадает
        assert waves[0] > waves[-1]                            # к центру

    def test_h_zr_equals_zone_times_ax(self):
        """H ЗР = зона × Ax, Ax = D/2 — тот же радиус, которым веер
        строится (get_effective_aperture; D — entrance_pupil_diameter
        для aperture_type=ENTRANCE_PUPIL)."""
        s = build_doublet()
        ax = get_effective_aperture(s, default=10.0) / 2.0
        for row in taboc2_rows(s)[:-1]:
            assert row['h_zr_mm'] == pytest.approx(row['zone'] * ax)

    def test_zm_cs_finite(self):
        rows = taboc2_rows(build_doublet())
        for row in rows[:-1]:
            assert row['z_m'] is not None and math.isfinite(row['z_m'])
            assert row['c_s'] is not None and math.isfinite(row['c_s'])

    def test_tg_prime100_negative_converging(self):
        """Сходящийся выход дублета: верхние зоны — наклоны к оси,
        Tg'*100 < 0 (ср. эталон −20.684 на краю)."""
        for row in taboc2_rows(build_doublet())[:-1]:
            assert row['tg_prime100'] < 0

    def test_iso_pct_finite(self):
        for row in taboc2_rows(build_doublet())[:-1]:
            assert row['iso_pct'] is not None
            assert math.isfinite(row['iso_pct'])

    def test_axial_row_zero(self):
        row = taboc2_rows(build_doublet())[-1]
        assert row['zone'] == 0.0
        assert all(v == 0 for k, v in row.items() if k != 'zone')

    def test_empty_system_single_row(self):
        rows = taboc2_rows(OpticalSystem())
        assert len(rows) == 1 and all(
            v == 0 for k, v in rows[0].items() if k != 'zone')


# ── Форматтеры ─────────────────────────────────────────────────────────────

class TestFormatTaboc:
    def test_taboc1_widths(self):
        """Строка данных = 1x + f6.3 + f12.5 + 2×f11.5 = 41 позиция."""
        text = format_taboc1(taboc1_rows(build_doublet()))
        lines = text.splitlines()
        assert len(lines) == 2 + 5
        for line in lines[2:]:
            assert len(line) == 41

    def test_taboc2_widths(self):
        """Строка данных = 1x + F7.3 + 3×F10.4 = 38 позиций; шапка —
        ширины эталона (57/57/59)."""
        text = format_taboc2(taboc2_rows(build_doublet()))
        lines = text.splitlines()
        assert [len(ln) for ln in lines[:3]] == [57, 57, 59]
        for line in lines[3:]:
            assert len(line) == 38

    @requires_prn_rt2236
    def test_taboc1_header_alignment(self):
        """│ шапки (мм-вариант формы 0x50619) стоят над ┴ оси графика —
        ось совпадает с эталоном RT__2236 побайтово."""
        names, axis = TABOC1_HEADER
        assert [i for i, ch in enumerate(names) if ch == '│'] == \
            [i for i, ch in enumerate(axis) if ch == '┴']
        etalon_axis = _etalon_lines(RT2236)[3]
        assert axis == etalon_axis

    @requires_prn_rt2236
    def test_default_header_matches_etalon(self):
        text = format_taboc2(taboc2_rows(build_doublet()))
        assert text.splitlines()[:3] == _etalon_taboc2_lines()[:3]

    def test_selector_variant_columns(self):
        """Селектор [0x34b8]: 3 величины из 5 — вариант с Z'm/C's."""
        text = format_taboc2(taboc2_rows(build_doublet()),
                             columns=('z_m', 'c_s', 'h_zr'))
        assert "Z'm" in text and "C's" in text
        for line in text.splitlines()[3:]:
            assert len(line) == 38

    def test_selector_rejects_unknown(self):
        rows = taboc2_rows(build_doublet())
        with pytest.raises(ValueError):
            format_taboc2(rows, columns=('wave', 'iso', 'nope'))
        with pytest.raises(ValueError):
            format_taboc2(rows, columns=('wave', 'iso'))   # нужно 3

    def test_none_values_blank(self):
        """Луч не дошёл (all-air IR-запись) — пробелы, не падение."""
        rows = [{'zone': 1.0, 'tg_prime100': None, 'wave': None,
                 'iso_pct': None, 'h_zr_mm': 5.0, 'z_m': None, 'c_s': None}]
        lines = format_taboc2(rows).splitlines()
        assert lines[3].endswith('5.0000')
        assert len(lines[3]) == 38


# ── Протокол: секции TABOC для осевого пучка ──────────────────────────────

class TestProtocolTabocSections:
    def test_sections_present_without_field(self):
        """Осевые секции не требуют поля (в отличие от TABGL/TABPR2)."""
        s = build_doublet()
        assert not s.field_points
        lines = []
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'proto.txt'
            export_protocol(s, paraxial_trace(s), {}, str(path))
            text = path.read_text(encoding='utf-8')
        assert 'Продольные аберрации (мм)' in text
        assert 'Волновые аберрации' in text
        assert 'Н ЗР' in text
        assert 'Конец протокола' in text

    def test_sections_absent_without_surfaces(self):
        s = OpticalSystem()
        s.name = 'пустая'
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'proto_empty.txt'
            export_protocol(s, paraxial_trace(s), {}, str(path))
            text = path.read_text(encoding='utf-8')
        assert 'Продольные аберрации' not in text
        assert 'Конец протокола' in text
