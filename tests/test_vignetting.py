# -*- coding: utf-8 -*-
"""Тесты виньетирования/светораспределения/TABBEA (analysis/vignetting.py).

Реверс §14.1 (колонки «Виньетир.│Светораспред.│Ограничения» TABBEA,
формат DS 0xc56) + §17.6 (вычислительный пробел №1 порта: машина
ограничений [0x39D0] и Σ-накопитель веера 0x10FB8+). Определения —
словарь терминов §19.3.1 (ANALIZE.DOC:549–558): виньетирование — доля
срезаемой части пучка (верх/низ отдельно), светораспределение — доля
площади зрачка пучка от площади зрачка осевого пучка основной λ.
"""
import pytest

from optics_engine import (FieldPoint, OpticalSystem, Surface, Wavelength,
                           paraxial_trace)

from analysis.vignetting import (
    TABBEA_FIELD_SPECS, TABBEA_HEADER, compute_light_distribution,
    compute_vignetting, format_tabbea, tabbea_rows,
)


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 (марки — каталог стёкол) — без виньетирования.

    aperture_value не задан (как ``build_doublet`` в test_gauge_rays):
    полудиаметры поверхностей не заданы → неограничены, радиус
    диафрагмы-«стоп» нулевой → край зрачка (rel_y = ±1) проходит
    свободно, пучок ограничен только диафрагмой.
    """
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=70),
    ]
    return s


def build_clipped() -> OpticalSystem:
    """Дублет со срезанной второй поверхностью (semi_diameter S2 = 4 мм).

    Первый интервал увеличен (25 мм): смещение главного луча с полем
    велико, верхний край срезается сильнее нижнего, светораспределение
    монотонно падает с полем.
    """
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.aperture_value = 10.0
    s.field_points = [FieldPoint(0.0), FieldPoint(3.0), FieldPoint(6.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=25),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=4.0),
        Surface(radius=-200, glass='', thickness=70),
    ]
    return s


def build_mirror(obscuration: float = 0.3,
                 semi_diameter: float = 25.0) -> OpticalSystem:
    """Вогнутое зеркало D=40 с центральным экранированием."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.aperture_value = 40.0
    s.obscuration_ratio = obscuration
    s.surfaces = [Surface(radius=-400, glass='', thickness=-200,
                          is_reflective=True, semi_diameter=semi_diameter)]
    return s


class TestComputeVignetting:
    """compute_vignetting: срезание краёв зрачка + ограничивающие элементы."""

    def test_doublet_unvignetted(self):
        """1. Дублет без виньетирования: 0 %, ограничение — диафрагма."""
        s = build_doublet()
        for field in (0.0, 3.0):
            v = compute_vignetting(s, field)
            assert v['vignet_up'] == pytest.approx(0.0)
            assert v['vignet_down'] == pytest.approx(0.0)
            assert not v['obscured']
            assert v['limit_up'] == ('D', s.stop_surface)
            assert v['limit_down'] == ('D', s.stop_surface)

    def test_upper_edge_clipped_by_surface(self):
        """2. S2 уменьшен → верхний луч срезан, ограничение ('P', 2)."""
        v = compute_vignetting(build_clipped(), 3.0)
        assert v['vignet_up'] > 0
        assert v['limit_up'] == ('P', 2)
        # нижний край на этом поле свободен — ограничение остаётся диафрагмой
        assert v['vignet_down'] == pytest.approx(0.0)
        assert v['limit_down'] == ('D', 1)

    def test_axial_symmetric_clip(self):
        """Осевое поле: верх/низ срезаны одинаково той же поверхностью."""
        v = compute_vignetting(build_clipped(), 0.0)
        assert v['vignet_up'] == pytest.approx(v['vignet_down'], rel=1e-6)
        assert v['limit_up'] == v['limit_down'] == ('P', 2)

    def test_mirror_edge_clipped_m_letter(self):
        """Срезающая поверхность отражает → код 'M' (зеркало-экран)."""
        v = compute_vignetting(build_mirror(semi_diameter=19.0), 0.0)
        assert v['vignet_up'] == pytest.approx(5.0, abs=0.1)   # 1 − 19/20
        assert v['limit_up'] == ('M', 1)
        assert v['limit_down'] == ('M', 1)

    def test_obscuration_flag_only(self):
        """Центральное экранирование: только флаг obscured, края целы."""
        v = compute_vignetting(build_mirror(), 0.5)
        assert v['obscured']
        assert v['vignet_up'] == pytest.approx(0.0)
        assert v['vignet_down'] == pytest.approx(0.0)


class TestLightDistribution:
    """compute_light_distribution: зоны прохождения + Σ-центроид (§17.6)."""

    def test_obscured_mirror_less_than_unit(self):
        """3. Экранирование ε = 0.3 → светораспределение ≈ 1 − ε² < 1."""
        light = compute_light_distribution(build_mirror(), [0.0])[0]
        assert light['light_total'] < 1.0
        assert light['light_total'] == pytest.approx(1 - 0.3 ** 2, abs=0.01)
        assert light['light_up'] == pytest.approx(light['light_down'],
                                                  abs=0.01)

    def test_monotonic_decrease_with_field(self):
        """4. Светораспределение монотонно падает с полем."""
        lights = compute_light_distribution(build_clipped(), [0.0, 3.0, 6.0])
        totals = [l['light_total'] for l in lights]
        assert totals[0] > totals[1] > totals[2]
        # верх (сторона среза) падает сильнее низа
        assert lights[2]['light_up'] < lights[2]['light_down']

    def test_unvignetted_full(self):
        """Невиньетированный дублет: весь зрачок проходит (доля 1)."""
        light = compute_light_distribution(build_doublet(), [0.0])[0]
        assert light['light_total'] == pytest.approx(1.0)
        assert light['light_up'] == pytest.approx(1.0)
        assert light['light_down'] == pytest.approx(1.0)

    def test_centroid_accumulator(self):
        """Σ-накопитель §17.6: центроид осевого пучка на оси, с полем уходит."""
        lights = compute_light_distribution(build_clipped(), [0.0, 6.0])
        assert lights[0]['centroid_y'] == pytest.approx(0.0, abs=1e-6)
        assert lights[1]['centroid_y'] > 0


class TestTabbeaRows:
    """tabbea_rows: по строке на поле, зрачки из параксиали, поля не роняются."""

    def test_rows_structure(self):
        s = build_clipped()
        rows = tabbea_rows(s)
        assert [r['n'] for r in rows] == [1, 2, 3]
        assert [r['field_y'] for r in rows] == [0.0, 3.0, 6.0]
        parax = paraxial_trace(s)
        assert rows[0]['Sp'] == pytest.approx(parax['sP'])
        assert rows[0]['Sp_prime'] == pytest.approx(parax['sP_prime'])
        assert rows[0]['Ax'] == pytest.approx(5.0)      # D/2 = 10/2
        # осевая строка: срез симметричен, пределы одинаковые
        assert rows[0]['vignet_up'] == pytest.approx(rows[0]['vignet_down'],
                                                     rel=1e-6)
        assert rows[0]['limit_up'] == rows[0]['limit_down'] == ('P', 2)
        # подмена field_points (габариты по одному полю) восстановлена
        assert [fp.y for fp in s.field_points] == [0.0, 3.0, 6.0]

    def test_fields_argument(self):
        rows = tabbea_rows(build_doublet(), fields=[2.0])
        assert len(rows) == 1 and rows[0]['field_y'] == 2.0
        assert rows[0]['light_up'] == pytest.approx(1.0)

    def test_default_fields_from_system(self):
        rows = tabbea_rows(build_clipped())
        assert [r['field_y'] for r in rows] == [0.0, 3.0, 6.0]

    def test_empty_system_no_crash(self):
        """Пустая система — нулевая строка без падения (диафрагма N=0)."""
        rows = tabbea_rows(OpticalSystem())
        assert len(rows) == 1
        assert rows[0]['Ax'] == 0.0 and rows[0]['light_up'] is None
        assert rows[0]['limit_up'] == ('D', 0)


class TestFormatTabbea:
    """5. format_tabbea: ширины колонок по формату DS 0xc56."""

    def test_data_line_width(self):
        """Строка данных = 1x + i2 + 32 + 20 + 12 + 12 + 12 + пробел
        печатальщика = 92 символа (как ``format_tabgl`` — 1x сверх формата)."""
        text = format_tabbea(tabbea_rows(build_clipped()))
        lines = text.splitlines()
        assert lines[:len(TABBEA_HEADER)] == list(TABBEA_HEADER)
        data = lines[len(TABBEA_HEADER):]
        assert len(data) == 3
        for line in data:
            assert len(line) == 92

    def test_column_offsets(self):
        """Позиции формата: N [2:4], Ax c [4], Sp с [36], виньетир. с [56],
        светораспр. с [68], ограничения [80:86] и [86:92] — 1x,1a,1x,i3."""
        rows = tabbea_rows(build_clipped())
        line = format_tabbea(rows).splitlines()[len(TABBEA_HEADER)]
        row = rows[0]
        assert line[2:4] == '%2d' % row['n']
        assert line[4:12].endswith('5.00000')            # Ax = D/2
        assert line[36:46].strip().startswith('.')       # Sp ≈ 0 (Fw.d OPAL)
        vign = float(line[56:62])                        # виньетир. верх, f6.3
        light = float(line[68:74])                       # светораспр. верх, f6.1
        assert vign == pytest.approx(row['vignet_up'], abs=5e-4)
        assert light == pytest.approx(row['light_up'] * 100.0, abs=5e-2)
        assert line[80:86] == ' P   2'
        assert line[86:92] == ' P   2'

    def test_field_specs_match_format(self):
        """Набор полей = 4×f8.5 + 2×f10.3 + 2×f6.3 + 2×f6.1 (DS 0xc56)."""
        assert TABBEA_FIELD_SPECS == ((8, 5), (8, 5), (8, 5), (8, 5),
                                      (10, 3), (10, 3),
                                      (6, 3), (6, 3),
                                      (6, 1), (6, 1))

    def test_empty_system_blank_light(self):
        """None (лучи не шли) — пробелы поля; стоп вне списка → ('D', 0)."""
        rows = tabbea_rows(OpticalSystem())
        line = format_tabbea(rows).splitlines()[len(TABBEA_HEADER)]
        assert len(line) == 92
        assert line[68:80] == ' ' * 12                   # светораспр. — пусто
        assert line[80:86] == ' D   0'
