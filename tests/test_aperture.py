"""Регрессионные тесты пункта 12 GAP v2 — способы задания апертуры.

Три способа (передняя апертура — угол; задняя — угол/NA'; высота луча
на диафрагме) плюс прежние (D, F/#, NA); пересчёт между ними — через
параксиальные характеристики (f', зрачки, увеличения изображения
диафрагмы). Каноническая величина — диаметр входного зрачка.
"""
import math
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint, ObjectType,
    paraxial_trace,
)
from domain.models import ApertureType
from domain.aperture import (
    APERTURE_EPS, aperture_to_epd, epd_to_apertures, convert_aperture,
    object_to_pupil_distance,
)


def singlet(object_type: ObjectType = ObjectType.INFINITE,
            first_thickness: float = 5.0) -> OpticalSystem:
    """Синглет f'≈100 мм, диафрагма на 1-й поверхности (входной зрачок
    совпадает с ней, m входного зрачка = 1)."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.object_type = object_type
    s.surfaces = [
        Surface(radius=100.0, glass='K8', thickness=first_thickness),
        Surface(radius=-100.0, glass='', thickness=95.0),
    ]
    s.aperture_type = ApertureType.ENTRANCE_PUPIL
    s.aperture_value = 20.0
    return s


class TestPupilMagnifications:
    def test_stop_at_first_surface_m_entrance_one(self):
        parax = paraxial_trace(singlet())
        assert parax['entrance_pupil_magnification'] == pytest.approx(1.0)

    def test_pupil_magnification_present(self):
        parax = paraxial_trace(singlet())
        assert parax.get('pupil_magnification')
        assert parax.get('exit_pupil_magnification')


class TestStopHeight:
    def test_stop_at_first_surface_is_epd(self):
        """Диафрагма на 1-й поверхности: полувысота h → D = 2h."""
        s = singlet()
        parax = paraxial_trace(s)
        assert aperture_to_epd(s, 10.0, ApertureType.STOP_HEIGHT,
                               parax=parax) == pytest.approx(20.0)

    def test_roundtrip(self):
        s = singlet()
        parax = paraxial_trace(s)
        ap = epd_to_apertures(s, 20.0, parax=parax)
        h = ap[ApertureType.STOP_HEIGHT]
        assert h is not None
        assert aperture_to_epd(s, h, ApertureType.STOP_HEIGHT,
                               parax=parax) == pytest.approx(20.0)

    def test_paraxial_trace_uses_stop_height(self):
        """Параксиальный расчёт приводит высоту на диафрагме к D зрачка."""
        s = singlet()
        s.aperture_type = ApertureType.STOP_HEIGHT
        s.aperture_value = 7.5
        assert paraxial_trace(s)['entrance_pupil_diameter'] == pytest.approx(15.0)


class TestRearAperture:
    def test_rear_angle_formula(self):
        """u' от края выходного зрачка до фокуса: h' = tan(u')·|sF'−sP'|,
        D_вх = 2h'/|m_p| (независимая проверка геометрией)."""
        s = singlet()
        parax = paraxial_trace(s)
        m_p = parax['pupil_magnification']
        lever = abs(parax['sF_prime'] - parax['exit_pupil'])
        u = math.atan(10.0 * abs(m_p) / lever)
        assert aperture_to_epd(s, math.degrees(u), ApertureType.REAR_ANGLE,
                               parax=parax) == pytest.approx(20.0)

    def test_rear_angle_roundtrip(self):
        s = singlet()
        parax = paraxial_trace(s)
        ap = epd_to_apertures(s, 20.0, parax=parax)
        assert aperture_to_epd(s, ap[ApertureType.REAR_ANGLE],
                               ApertureType.REAR_ANGLE,
                               parax=parax) == pytest.approx(20.0)

    def test_rear_na_is_sin_of_rear_angle(self):
        s = singlet()
        parax = paraxial_trace(s)
        ap = epd_to_apertures(s, 20.0, parax=parax)
        assert ap[ApertureType.REAR_NA] == pytest.approx(
            math.sin(math.radians(ap[ApertureType.REAR_ANGLE])))
        assert aperture_to_epd(s, ap[ApertureType.REAR_NA],
                               ApertureType.REAR_NA,
                               parax=parax) == pytest.approx(20.0)


class TestFrontAperture:
    def test_infinite_object_none(self):
        """Предмет в ∞: осевой пучок параллелен, передний угол не определён."""
        s = singlet()
        parax = paraxial_trace(s)
        assert object_to_pupil_distance(s, parax) is None
        assert aperture_to_epd(s, 2.0, ApertureType.FRONT_ANGLE,
                               parax=parax) is None
        assert epd_to_apertures(s, 20.0, parax=parax)[
            ApertureType.FRONT_ANGLE] is None

    def test_finite_object_geometry(self):
        """Предмет на 200 мм перед зрачком: u = atan(h/200)."""
        s = singlet(object_type=ObjectType.FINITE, first_thickness=200.0)
        parax = paraxial_trace(s)
        assert object_to_pupil_distance(s, parax) == pytest.approx(200.0)
        expected = math.degrees(math.atan(10.0 / 200.0))
        ap = epd_to_apertures(s, 20.0, parax=parax)
        assert ap[ApertureType.FRONT_ANGLE] == pytest.approx(expected)
        assert aperture_to_epd(s, expected, ApertureType.FRONT_ANGLE,
                               parax=parax) == pytest.approx(20.0)


class TestLegacyTypes:
    """Прежние способы (D, F/#, NA) — прежняя семантика, один источник."""

    def test_entrance_pupil_passthrough(self):
        s = singlet()
        assert aperture_to_epd(s, 20.0, ApertureType.ENTRANCE_PUPIL) == 20.0

    def test_f_number(self):
        s = singlet()
        parax = paraxial_trace(s)
        efl = abs(parax['focal_length'])
        assert aperture_to_epd(s, 8.0, ApertureType.F_NUMBER,
                               parax=parax) == pytest.approx(efl / 8.0)

    def test_na(self):
        s = singlet()
        parax = paraxial_trace(s)
        efl = abs(parax['focal_length'])
        assert aperture_to_epd(s, 0.05, ApertureType.NUMERICAL_APERTURE,
                               parax=parax) == pytest.approx(2.0 * efl * 0.05)

    @pytest.mark.parametrize('value', [0.0, -3.0])
    def test_nonpositive_value_none(self, value):
        s = singlet()
        assert aperture_to_epd(s, value, ApertureType.ENTRANCE_PUPIL) is None


class TestConvertAperture:
    def test_all_representations_same_beam(self):
        """Все представления описывают один пучок: обратный пересчёт
        любого из них даёт тот же диаметр зрачка."""
        s = singlet()
        parax = paraxial_trace(s)
        conv = convert_aperture(s, 2.0, ApertureType.REAR_ANGLE, parax=parax)
        assert conv['epd'] == pytest.approx(
            aperture_to_epd(s, 2.0, ApertureType.REAR_ANGLE, parax=parax))
        for name in ('entrance_pupil', 'f_number', 'numerical_aperture',
                     'rear_angle', 'rear_na', 'stop_height'):
            assert name in conv
        # замыкание через каждый способ
        assert aperture_to_epd(s, conv['f_number'], ApertureType.F_NUMBER,
                               parax=parax) == pytest.approx(conv['epd'])
        assert aperture_to_epd(s, conv['stop_height'], ApertureType.STOP_HEIGHT,
                               parax=parax) == pytest.approx(conv['epd'])

    def test_invalid_input_epd_none(self):
        conv = convert_aperture(singlet(), 0.0, ApertureType.STOP_HEIGHT)
        assert conv['epd'] is None and 'f_number' not in conv


class TestEffectiveAperture:
    def test_any_spec_converts_to_diameter(self):
        """get_effective_aperture возвращает диаметр, а не «сырое» значение
        способа (F/# или угол не попадают в трассировку как мм)."""
        from optics_utils import get_effective_aperture
        s = singlet()
        efl = abs(paraxial_trace(s)['focal_length'])
        s.aperture_type = ApertureType.F_NUMBER
        s.aperture_value = 8.0
        assert get_effective_aperture(s, default=10.0) == pytest.approx(efl / 8.0)
        s.aperture_type = ApertureType.STOP_HEIGHT
        s.aperture_value = 7.5
        assert get_effective_aperture(s, default=10.0) == pytest.approx(15.0)

    def test_diameter_passthrough_and_default(self):
        from optics_utils import get_effective_aperture
        s = singlet()
        assert get_effective_aperture(s, default=10.0) == 20.0
        s.aperture_value = 0.0
        assert get_effective_aperture(s, default=10.0) == 10.0


class TestApertureUi:
    @pytest.fixture
    def sp(self):
        """SystemParamsWidget с живым QApplication (ссылка удерживается)."""
        import sys
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        import main as m
        yield m.SystemParamsWidget()

    def test_method_combo_has_three_new_ways(self, sp):
        """Переключатель способов: передний угол, задний угол/NA',
        высота на диафрагме (+ прежние D, F/#, NA)."""
        import main as m
        types = [t for _, t in m.APERTURE_METHODS]
        for t in (ApertureType.FRONT_ANGLE, ApertureType.REAR_ANGLE,
                  ApertureType.REAR_NA, ApertureType.STOP_HEIGHT):
            assert t in types
        assert sp.ap_method_combo.count() == len(m.APERTURE_METHODS)

    def test_aperture_from_ui_single_source(self, sp):
        sp.set_aperture(ApertureType.REAR_NA, 0.25)
        assert sp.aperture_from_ui() == (ApertureType.REAR_NA, 0.25)
        sp.set_aperture(ApertureType.ENTRANCE_PUPIL, 30.0)
        assert sp.aperture_from_ui() == (ApertureType.ENTRANCE_PUPIL, 30.0)

    def test_controllers_share_widget_method(self):
        """Оба контроллера собирают апертуру одним вызовом (без дублирования)."""
        import inspect
        src_cc = inspect.getsource(
            __import__('gui.controllers.calculation_controller',
                       fromlist=['x']))
        src_sc = inspect.getsource(
            __import__('gui.controllers.system_controller', fromlist=['x']))
        for src in (src_cc, src_sc):
            assert 'aperture_from_ui()' in src
            assert 'front_ap_combo' not in src


class TestJsonRoundTrip:
    def test_new_types_serialize(self, tmp_path):
        import fileio.json_io as json_io
        s = singlet()
        s.aperture_type = ApertureType.FRONT_ANGLE
        s.aperture_value = 2.5
        p = tmp_path / 'ap.json'
        json_io.save_json(s, str(p))
        loaded = json_io.load_json(str(p))
        assert loaded.aperture_type == ApertureType.FRONT_ANGLE
        assert loaded.aperture_value == pytest.approx(2.5)
