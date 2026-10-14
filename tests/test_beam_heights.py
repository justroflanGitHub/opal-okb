# -*- coding: utf-8 -*-
"""Тесты OPAL-таблиц TABESB/TABEAP (analysis/beam_heights.py, реверс §14.1).

Эталонного вывода TABESB/TABEAP в PRN-корпусе нет (в RT__2236/2250 —
TABOC2/TABGL) — проверка по форматам DS 0xdb9/0xece, словарю величин
ANALIZE.DOC:731–753/488–516 и физике демо-систем/Индустара-23у.
"""
import copy

import pytest

from domain.models import create_demo_system_by_name
from analysis.beam_heights import (
    TABEAP_FIELD_SPECS, TABESB_FIELD_SPECS, TABESB_KEYS, format_tabeap,
    format_tabesb, tabeap_rows, tabesb_rows,
)

#: Ширина строки данных TABESB: 1X + i3 + f11.3 + 2×f12.3 + 4×f10.3.
TABESB_LINE_WIDTH = 1 + 3 + sum(w for w, _d in TABESB_FIELD_SPECS)   # 79

#: То же TABEAP: 1X + i3 + 7 чисел + 2×(1x,1a,1x,i3).
TABEAP_LINE_WIDTH = 1 + 3 + sum(w for w, _d in TABEAP_FIELD_SPECS) + 2 * 6  # 77


@pytest.fixture(scope='module')
def plano():
    return create_demo_system_by_name('plano_convex')


@pytest.fixture(scope='module')
def mirror():
    return create_demo_system_by_name('mirror')


class TestTabesbPlanoConvex:
    """Плосковыпуклая линза: осевой пучок сходится к фокусу."""

    def test_axial_decreases_to_focus(self, plano):
        """Высоты осевого луча монотонно убывают от Ay к фокусу.

        S0 — ApertureD/2 = 10.0 (луч поле 0 параллелен оси до S0);
        замыкающая строка — плоскость изображения (демо-системы её
        поверхностью не задают): -.207 — крайний луч пересёк ось до
        параксиального фокуса (недоисправленная сферическая).
        """
        rows = tabesb_rows(plano)
        assert [r['n'] for r in rows] == [1, 2, 3]
        axial = [r['axial_y'] for r in rows]
        assert axial[0] == pytest.approx(10.0, abs=1e-9)   # Ay = D/2
        assert all(a > b for a, b in zip(axial, axial[1:]))
        assert rows[-1]['axial_y'] < 0 < rows[0]['axial_y']

    def test_apertures_are_semi_diameters(self, plano):
        """Верхн.отв/нижн.отв = ±semi_diameter заданных поверхностей."""
        rows = tabesb_rows(plano)
        for row, s in zip(rows, plano.surfaces):
            assert row['aperture_upper'] == pytest.approx(s.semi_diameter)
            assert row['aperture_lower'] == pytest.approx(-s.semi_diameter)
        # на замыкающей плоскости изображения отверстий нет
        assert rows[-1]['aperture_upper'] is None

    def test_axial_field_beams_symmetric(self, plano):
        """Поле 0: предельные/рабочие зеркальны осевому (±Ay)."""
        rows = tabesb_rows(plano, field_y=0.0)
        for row in rows:
            assert row['upper_y'] == pytest.approx(row['axial_y'])
            assert row['lower_y'] == pytest.approx(-row['axial_y'])
            assert row['work_upper_y'] == pytest.approx(row['axial_y'])
            assert row['work_lower_y'] == pytest.approx(-row['axial_y'])


class TestTabesbTessar:
    """Тессар Индустар-23у (LENS.LBO #3): внеосевой пучок на главном поле."""

    def test_upper_axial_lower_on_s0(self, industar23u):
        """|верхний Y| > |осевой Y| > |нижний Y| на S0 (поле со знаком OPAL).

        Поле отрицательное (знак OPAL — как tables._zone_field): главный
        луч на S0 смещён вверх, верхний крайний вырастает над осевым
        (+16.6 против +10.55), нижний сжимается (−2.1).
        """
        field = -max(fp.y for fp in industar23u.field_points)
        rows = tabesb_rows(industar23u, field_y=field)
        row0 = rows[0]
        assert abs(row0['upper_y']) > abs(row0['axial_y']) > abs(row0['lower_y'])
        assert row0['axial_y'] == pytest.approx(
            industar23u.aperture_value / 2, rel=1e-3)

    def test_working_zone_narrower(self, industar23u):
        """Рабочие высоты — внутри предельных: пучок винетируется.

        Верхний предельный срезается кромкой S0 (16.6 > 12.35 → дальше
        пробелы), рабочая зона проходит всю систему; на S0 верхняя
        рабочая прижата к отверстию (виньетирование кромкой S0).
        """
        field = -max(fp.y for fp in industar23u.field_points)
        rows = tabesb_rows(industar23u, field_y=field)
        assert rows[1]['upper_y'] is None            # EDGE на S0
        assert all(r['work_upper_y'] is not None for r in rows)
        assert rows[0]['work_upper_y'] < rows[0]['upper_y']

    def test_meta_wavelength_index(self, industar23u):
        rows = tabesb_rows(industar23u)
        assert rows[0]['wl'] == pytest.approx(0.54607, abs=1e-6)
        assert rows[0]['wl_index'] == 1
        rows_c = tabesb_rows(industar23u, wl=0.65627)
        assert rows_c[0]['wl_index'] == 3


class TestTabesbMirror:
    """Вогнутое зеркало: отражение и смена знака высоты."""

    def test_sign_change_after_mirror(self, mirror):
        """Осевой Y убывает и меняет знак: +20 на зеркале → −.025.

        Крайний луч пересекает ось чуть ДО параксиальной плоскости
        изображения (сферическая аберрация зеркала) — на плоскости
        (последняя поверхность демо-системы) высота отрицательна.
        """
        rows = tabesb_rows(mirror)
        axial = [r['axial_y'] for r in rows]
        assert axial[0] == pytest.approx(20.0, abs=1e-9)
        assert axial[0] > 0 > axial[-1]
        assert abs(axial[-1]) < 1e-1
        assert all(a > b for a, b in zip(axial, axial[1:]))

    def test_oblique_beam_shifted(self, mirror):
        """Поле −0.5°: высоты пучка на зеркале сдвинуты (20.00/−20.00)."""
        rows = tabesb_rows(mirror, field_y=-0.5)
        assert rows[0]['upper_y'] > rows[0]['axial_y'] > rows[0]['lower_y']


def _parse_field(field: str):
    """Число из поля OPAL без ведущего нуля ('.207' → 0.207; '' → None)."""
    field = field.strip()
    if not field:
        return None
    if field.startswith('-.'):
        field = '-0.' + field[2:]
    elif field.startswith('.'):
        field = '0.' + field[1:]
    return float(field)


class TestFormatTabesb:
    """Формат (1X,i3,f11.3,2f12.3,4f10.3) — ширины и позиции полей."""

    def test_line_widths_and_field_positions(self, plano):
        """Строка данных 79 знаков; поля читаются обратно в значения строк."""
        rows = tabesb_rows(plano)
        lines = format_tabesb(rows).splitlines()
        assert lines[0].strip() == 'Световые высоты'
        assert lines[1] == '─ Длина волны - 1'
        data = lines[4]
        assert len(data) == TABESB_LINE_WIDTH == 79
        assert data[1:4] == '  1'                       # 1X,i3
        pos = 4
        for (width, _dec), key in zip(TABESB_FIELD_SPECS, TABESB_KEYS):
            value = _parse_field(data[pos:pos + width])
            assert value == pytest.approx(rows[0][key], abs=5e-4)
            pos += width
        assert pos == len(data)                         # поля без зазоров

    def test_failed_ray_blank_column(self, industar23u):
        """Недошедший луч — пробелы в колонке (не 0/NaN/None)."""
        field = -max(fp.y for fp in industar23u.field_points)
        text = format_tabesb(tabesb_rows(industar23u, field_y=field))
        assert 'nan' not in text and 'None' not in text
        # строка S2: предельный верхний срезан кромкой S0 → поле пустое
        data = text.splitlines()[5]
        assert data[15:27].strip() == ''


class TestTabeap:
    """TABEAP: экранные зоны центрального экранирования."""

    def test_no_obscuration_zeros(self, plano):
        """Без экранирования размеры/смещение — нули (пучки есть)."""
        rows = tabeap_rows(plano)
        assert len(rows) == len(plano.field_points)
        for row in rows:
            assert row['obsc_in_x'] == row['obsc_in_y'] == 0.0
            assert row['obsc_out_x'] == row['obsc_out_y'] == 0.0
            assert row['screen_shift'] == 0.0

    def test_obscuration_03_sizes_positive(self, mirror):
        """obscuration_ratio=0.3 → относительные размеры 0.3 (>0),
        смещение на экране растёт с полем, осевой пучок — без смещения."""
        system = copy.deepcopy(mirror)
        system.obscuration_ratio = 0.3
        rows = tabeap_rows(system)
        for row in rows:
            for key in ('obsc_in_x', 'obsc_in_y',
                        'obsc_out_x', 'obsc_out_y'):
                assert row[key] == pytest.approx(0.3)
        assert rows[0]['screen_shift'] == pytest.approx(0.0)
        assert abs(rows[1]['screen_shift']) > 0
        assert abs(rows[2]['screen_shift']) > abs(rows[1]['screen_shift'])

    def test_limits_and_vignetting_structure(self, mirror):
        """Ограничения — (буква, N); виньетирование в [0, 1].

        Буквы — LIMIT_LETTERS (единые с TABBEA): D диафрагма /
        P поверхность / M зеркало-экран; N — номер поверхности
        (1-based, 0 — диафрагма вне списка). Виньетирование — доля
        срезанного края зрачка (DOC:549–551), не зона прохождения.
        """
        system = copy.deepcopy(mirror)
        system.obscuration_ratio = 0.3
        for row in tabeap_rows(system):
            for key in ('limit_upper', 'limit_lower'):
                pair = row[key]
                assert pair is not None
                letter, num = pair
                assert letter in ('D', 'P', 'M')
                assert 0 <= num <= len(mirror.surfaces)
            for key in ('vignetting_upper', 'vignetting_lower'):
                assert 0.0 <= row[key] <= 1.0

    def test_format_widths(self, mirror):
        """Формат (1X,i3,4f9.5,f9.4,2f8.3,2(1x,1a,1x,i3)) — ширина 77."""
        system = copy.deepcopy(mirror)
        system.obscuration_ratio = 0.3
        lines = format_tabeap(tabeap_rows(system)).splitlines()
        assert 'Экранирующая поверхность' in lines[1]
        data = lines[5]                    # титул + экран + 3 строки шапки
        assert len(data) == TABEAP_LINE_WIDTH == 77
        # хвост — пары «буква + i3»: буквы на позициях 66 и 72
        assert data[66] in ('D', 'P', 'M')
        assert data[72] in ('D', 'P', 'M')

    def test_catadioptric_system(self, mirror_lens_450):
        """Зеркально-линзовая f'=450 (LENS_SPC.LBO): не падает, структура.

        Осевой пучок срезан кромкой S3 (полудиаметры LBO впритык),
        косой — сильнее: доля срезанного края растёт с полем.
        """
        system = copy.deepcopy(mirror_lens_450)
        system.obscuration_ratio = 0.3
        rows = tabeap_rows(system)
        assert [r['n'] for r in rows] == [1, 2]
        assert 0.0 < rows[0]['vignetting_upper'] < 1.0   # осевой срезан S3
        assert rows[1]['vignetting_upper'] > rows[0]['vignetting_upper']
