# -*- coding: utf-8 -*-
"""Тесты OPAL-таблиц TABGL/TABPR2 (analysis/tables.py, реверс §15).

Эталоны: extracted/opal_okb/RT__2250.PRN (TABGL, система «IR -.2X» =
запись 1 USBINOCL.LBO; запись без данных стёкол → численная свёрка
возможна по предметным колонкам, остальное — структура/знаки/порядки
на Индустаре-23у).
"""
import copy
import math
from pathlib import Path

import pytest

from tests.conftest import REASON_NO_LBO, has_lbo, requires_prn_rt2250

from lbo_reader import load_lbo_fast
from fileio.decode_lbo import decode_lbo_opj
from fileio.protocol import export_protocol
from optics_engine import paraxial_trace

from analysis.tables import (
    TABGL_FIELD_SPECS, WL_C, WL_D, _fwo, field_zones, format_tabgl,
    format_tabpr2, max_field, tabgl_rows, tabpr2_rows,
)

BASE = Path(__file__).resolve().parent.parent
RT2250 = BASE / 'extracted' / 'opal_okb' / 'RT__2250.PRN'
USBINOCL = BASE / 'extracted' / 'opal_okb' / 'Lib' / 'USBINOCL.LBO'


# ── Эталон RT__2250: разбор и golden-сверка ────────────────────────────────

def _etalon_tabgl_lines():
    """8 строк эталона TABGL: титул + 3 шапки + 4 данных (CP866)."""
    lines = RT2250.read_bytes().decode('cp866').splitlines()
    start = next(i for i, ln in enumerate(lines)
                 if 'Характеристики главных лучей' in ln)
    return lines[start:start + 8]


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


_ETALON_KEYS = ('obj_rel', 'obj_grminsec', 'img_rel', 'img_grminsec',
                'distortion_pct', 'distortion_grminsec',
                'z_m', 'z_s', 'c_m', 'c_s')


def _etalon_rows():
    rows = []
    for line in _etalon_tabgl_lines()[4:]:
        pos, values = 4, []
        for width, _ in TABGL_FIELD_SPECS:
            values.append(_parse_fwo(line[pos:pos + width]))
            pos += width
        row = dict(zip(_ETALON_KEYS, values))
        row['n'] = int(line[2:4])
        row['zone'] = row['obj_rel']
        rows.append(row)
    return rows


@pytest.fixture(scope='module')
def ir_system():
    """Эталонная система RT__2250 — запись 1 USBINOCL.LBO.

    Запись хранит поле 36° (2W=72 шапки), но БЕЗ блока стёкол
    (all-air) — главные лучи не проходят, численная golden-сверка
    только по предметным колонкам (зависят от поля, не от сред).
    """
    if not has_lbo("USBINOCL"):
        pytest.skip(REASON_NO_LBO)
    entries = load_lbo_fast(str(USBINOCL))
    return decode_lbo_opj(entries[1]['opj_data'])


@requires_prn_rt2250
class TestGoldenRT2250:
    """Golden против эталона RT__2250.PRN."""

    def test_format_byte_exact(self):
        """Форматтер с числами эталона воспроизводит его байт-в-байт."""
        lines = _etalon_tabgl_lines()
        rows = _etalon_rows()
        assert format_tabgl(rows).splitlines() == lines

    def test_computed_object_columns(self, ir_system):
        """Рассчитанные предметные колонки — в пределах ±0.5% от эталона.

        Зоны √(k/n) и углы ω = atan(zone·tan(ω_max)) не зависят от сред —
        сверяются даже на all-air записи.
        """
        rows = tabgl_rows(ir_system)
        etalon = _etalon_rows()
        assert [r['n'] for r in rows] == [1, 2, 3, 0]
        for row, ref in zip(rows[:3], etalon[:3]):
            assert row['obj_rel'] == pytest.approx(ref['obj_rel'], rel=1e-3)
            assert row['obj_grminsec'] == pytest.approx(
                ref['obj_grminsec'], rel=5e-3)   # ±0.5% по ТЗ

    def test_etalon_zone_scheme(self):
        """Зоны эталона N=3: 1, √(2/3), √(1/3) (равные площади поля)."""
        assert field_zones(3) == pytest.approx(
            [1.0, math.sqrt(2.0 / 3.0), math.sqrt(1.0 / 3.0)])
        for row, zone in zip(_etalon_rows()[:3], field_zones(3)):
            assert row['obj_rel'] == pytest.approx(zone, abs=2e-3)


class TestFormatFwo:
    """Эмуляция FORTRAN Fw.d в стиле печати OPAL."""

    def test_no_leading_zero(self):
        assert _fwo(0.816, 7, 3) == '.816'.rjust(7)
        assert _fwo(-0.535640, 12, 6) == '-.535640'.rjust(12)
        assert _fwo(-36.0, 12, 6) == '-36.000000'.rjust(12)

    def test_negative_zero_positive(self):
        # строка N=0 эталона: все нули положительны
        assert _fwo(-1e-9, 9, 4) == '    .0000'
        assert _fwo(0.0, 9, 4) == '    .0000'

    def test_none_blank(self):
        assert _fwo(None, 9, 4) == ' ' * 9

    def test_width_preserved(self):
        for value, width, dec in ((0.5, 7, 3), (-123.4567, 11, 6),
                                  (9.9, 8, 4), (-0.0001, 12, 6)):
            assert len(_fwo(value, width, dec)) == width

    def test_overflow_asterisks(self):
        """Переполнение Fw.d — звёздочки, как FORTRAN."""
        assert _fwo(1234.5, 8, 4) == '*' * 8
        assert _fwo(202.9300, 8, 4) == '202.9300'   # ровно 8 — помещается

    def test_rounding_half_up(self):
        """Округление HALF_UP по десятичному разложению (RTL 0x2E73,
        REVERSE_FMT.md §4), а не half-even f-строки Python."""
        # 0.0625 при d=3: Python «.062», OPAL «.063» (связь вверх по модулю)
        assert _fwo(0.0625, 8, 3) == '    .063'
        assert _fwo(-0.0625, 8, 3) == '   -.063'
        assert _fwo(0.1875, 8, 3) == '    .188'   # не связь — одинаково
        assert _fwo(2.5, 4, 0) == '   3'
        assert _fwo(0.5, 4, 0) == '   1'
        # не-связи не меняются относительно прежнего half-even
        assert _fwo(0.00005, 8, 4) == '   .0001'
        # double -0.00015 = -0.0001499999...98 — ниже связи → вниз
        assert _fwo(-0.00015, 9, 4) == '   -.0001'

    def test_data_line_width(self, industar23u):
        """Строки данных ≤ 96 символов (формат + пробел печатальщика)."""
        lines = format_tabgl(tabgl_rows(industar23u)).splitlines()
        for line in lines[4:7]:
            assert len(line) <= 96
        # зона 1: C's занимает поле целиком → ровно 96
        assert len(lines[4]) == 96


class TestTabglStructure:
    """Структура/знаки/порядки TABGL на Индустаре-23у (поле 26°)."""

    ROW_KEYS = _ETALON_KEYS

    def test_rows_structure(self, industar23u):
        rows = tabgl_rows(industar23u)
        assert [r['n'] for r in rows] == [1, 2, 3, 0]
        zones = [r['zone'] for r in rows[:3]]
        assert zones == pytest.approx([1.0, math.sqrt(2 / 3), math.sqrt(1 / 3)])

    def test_distortion_signs_orders(self, industar23u):
        """Дисторсия — проценты, отрицательная (бочка), растёт к центру."""
        dist = [r['distortion_pct'] for r in tabgl_rows(industar23u)[:3]]
        assert all(d is not None and -10 < d < 0 for d in dist)
        assert abs(dist[2]) < abs(dist[0])

    def test_image_relative_close_to_zone(self, industar23u):
        """«Изображ. относ.» ≈ зона (дисторсия мала, tan-пропорция)."""
        for row in tabgl_rows(industar23u)[:3]:
            assert abs(row['img_rel'] - row['zone']) < 0.05

    def test_caustics_coddington_positive_orders(self, industar23u):
        rows = tabgl_rows(industar23u)
        for row in rows[:3]:
            assert row['c_m'] > 0 and row['c_s'] > 0   # мм-радиусы
            assert row['z_m'] is not None and row['z_s'] is not None

    def test_axial_row_zero(self, industar23u):
        row = tabgl_rows(industar23u)[-1]
        assert row['n'] == 0
        assert all(v == 0 for v in row.values())

    def test_zero_field_single_axial_row(self, industar23u):
        system = copy.deepcopy(industar23u)
        system.field_points = []
        system.object_height = 0
        assert max_field(system) == 0
        rows = tabgl_rows(system)
        assert len(rows) == 1 and rows[0]['n'] == 0
        assert format_tabgl(rows).count('\n') == 4   # шапка + 1 строка


class TestTabpr2:
    """TABPR2: механизм второй λ, fallback, структура."""

    def test_rows_structure(self, industar23u):
        rows = tabpr2_rows(industar23u)
        assert [r['n'] for r in rows] == [1, 2, 3, 0]
        for row in rows[:3]:
            # хроматизм увеличения у ахроматизованного объектива — мал
            assert abs(row['mag_abs_mm']) < 0.5
            assert abs(row['mag_rel_pct']) < 1.0
            assert row['dy_prime_mm'] is not None
            assert row['z_m'] is not None

    def test_second_wavelength_preferred(self, industar23u):
        # вторая λ системы (0.43405) предпочтительнее fallback-пары d→C
        rows = tabpr2_rows(industar23u)
        assert rows[-1]['wl_alt'] == pytest.approx(0.43405, abs=1e-5)

    def test_mono_fallback_d_to_c(self, industar23u):
        """Монохромная система → пара d→C (λ₂ = линия C)."""
        mono = copy.deepcopy(industar23u)
        mono.wavelengths = [industar23u.wavelengths[0]]
        rows = tabpr2_rows(mono)
        assert rows[-1]['wl_main'] == pytest.approx(0.54607, abs=1e-5)
        assert rows[-1]['wl_alt'] == pytest.approx(WL_C)
        # системная λ сама = C → альтернатива разворачивается на d
        mono_c = copy.deepcopy(industar23u)
        mono_c.wavelengths = [industar23u.wavelengths[2]]   # 0.65627 = C
        rows_c = tabpr2_rows(mono_c)
        assert rows_c[-1]['wl_main'] == pytest.approx(WL_C)
        assert rows_c[-1]['wl_alt'] == pytest.approx(WL_D)

    def test_explicit_wl_alt(self, industar23u):
        mono = copy.deepcopy(industar23u)
        mono.wavelengths = [industar23u.wavelengths[0]]
        rows = tabpr2_rows(mono, wl_alt=0.55)
        assert rows[-1]['wl_alt'] == pytest.approx(0.55)

    def test_zero_field_axial_only(self, industar23u):
        system = copy.deepcopy(industar23u)
        system.field_points = []
        system.object_height = 0
        rows = tabpr2_rows(system)
        assert len(rows) == 1 and rows[0]['n'] == 0
        assert all(v == 0 for k, v in rows[0].items()
                   if k not in ('wl_main', 'wl_alt'))
        assert format_tabpr2(rows).count('\n') == 4

    def test_axial_row_zero(self, industar23u):
        row = tabpr2_rows(industar23u)[-1]
        assert row['n'] == 0
        assert all(v == 0 for k, v in row.items()
                   if k not in ('wl_main', 'wl_alt'))

    def test_ir_system_no_crash(self, ir_system):
        """All-air запись: лучи не проходят → пустые колонки, без падения."""
        rows = tabpr2_rows(ir_system)
        assert len(rows) == 4
        for row in rows[:3]:
            assert row['mag_abs_mm'] is None


class TestProtocolSections:
    """Секции TABGL/TABPR2 в экспортируемом протоколе (поле > 0)."""

    def test_sections_present(self, industar23u, tmp_path):
        path = tmp_path / 'proto_field.txt'
        export_protocol(industar23u, paraxial_trace(industar23u), {}, str(path))
        text = path.read_text(encoding='utf-8')
        assert 'Характеристики главных лучей' in text
        assert 'Хроматизм увеличения' in text
        assert 'Конец протокола' in text

    def test_sections_absent_without_field(self, industar23u, tmp_path):
        system = copy.deepcopy(industar23u)
        system.field_points = []
        system.object_height = 0
        path = tmp_path / 'proto_zero.txt'
        export_protocol(system, paraxial_trace(system), {}, str(path))
        text = path.read_text(encoding='utf-8')
        assert 'Характеристики главных лучей' not in text
        assert 'Хроматизм увеличения' not in text
        assert 'Конец протокола' in text
