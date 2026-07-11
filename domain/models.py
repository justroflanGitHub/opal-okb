"""
OPAL-OKB — Domain Models

Core data structures for optical system representation.

Extracted from optics_engine.py during package restructuring.
All types, dataclasses, and demo-system factories live here.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class SurfaceType(Enum):
    SPHERE = 0        # Сферическая
    CONIC = 1         # Коническая (параболоид, эллипсоид, гиперболоид)
    ASPHERIC = 2      # Асферическая (полином)
    HOLOGRAM = 3      # ГОЭ (голограммный оптический элемент)
    GRATING = 4       # Дифракционная решётка
    TOROIDAL = 5      # Торическая


class ObjectType(Enum):
    FINITE = 1         # Предмет на конечном расстоянии (OB=1)
    INFINITE = 0       # Предмет в бесконечности (OB=0)


class ApertureType(Enum):
    ENTRANCE_PUPIL = 0    # Входной зрачок (диаметр)
    NUMERICAL_APERTURE = 1  # Числовая апертура
    F_NUMBER = 2          # Относительное отверстие (F/#)


@dataclass
class Surface:
    """Одна оптическая поверхность."""
    radius: float = 0.0          # Радиус кривизны (мм), 0 = плоскость
    thickness: float = 0.0       # Расстояние до следующей поверхности (мм)
    glass: str = ""              # Марка стекла или код среды
    semi_diameter: float = 0.0   # Полудиаметр (мм)
    surface_type: SurfaceType = SurfaceType.SPHERE
    conic_constant: float = 0.0  # Коническая постоянная (для CONIC)
    aspheric_coeffs: List[float] = field(default_factory=list)  # Асферические коэфф.
    is_reflective: bool = False   # Зеркальная поверхность?
    # Деформация (для SPTDEF)
    deformation_coeffs: List[float] = field(default_factory=list)
    # ГОЭ параметры
    hologram_order: float = 1.0
    hologram_wavelength: float = 0.6328  # мкм
    hologram_coeffs: List[float] = field(default_factory=list)
    # Override refractive index (if set, used instead of glass_catalog)
    n_override: dict = field(default_factory=dict)  # {wl_value: n}
    # Coordinate break / tilt / decenter
    tilt_x: float = 0.0       # tilt around X axis (degrees)
    tilt_y: float = 0.0       # tilt around Y axis (degrees)
    decenter_x: float = 0.0   # lateral shift in X (mm)
    decenter_y: float = 0.0   # lateral shift in Y (mm)


@dataclass
class Wavelength:
    """Длина волны."""
    value: float          # мкм
    weight: float = 1.0   # Вес при оптимизации
    name: str = ""


@dataclass
class FieldPoint:
    """Точка поля (внеосевой пучок)."""
    y: float = 0.0       # Угловое поле (градусы) или высота (мм)
    x: float = 0.0       # Для 2D поля
    weight: float = 1.0
    # Параметры зрачка
    pupil_y: float = 1.0
    pupil_x: float = 0.0


@dataclass
class GlassCatalogEntry:
    """Запись в каталоге стёкол."""
    name: str
    nd: float           # Показатель преломления для d-линии (0.58756 мкм)
    ne: float           # Показатель преломления для e-линии (0.54607 мкм)
    vd: float           # Коэффициент дисперсии (Abbe) для d
    ve: float           # Коэффициент дисперсии для e
    # Коэффициенты дисперсионной формулы (Sellmeier / Herzberger)
    coeffs: List[float] = field(default_factory=list)
    # Ограничения
    transmission: dict = field(default_factory=dict)  # wavelength -> %


@dataclass
class OpticalSystem:
    """Полная оптическая система."""
    name: str = ""
    # Предмет
    object_type: ObjectType = ObjectType.INFINITE
    image_type: ObjectType = ObjectType.FINITE   # TODO: wire into UI — Тип изображения: INFINITE=дальний, FINITE=ближний
    object_height: float = 0.0     # мм (для FINITE) или градусы (для INFINITE)
    object_distance: float = 0.0   # мм — расстояние от предмета до первой поверхности (для FINITE)
    # Поверхности
    surfaces: List[Surface] = field(default_factory=list)
    # Апертура
    aperture_type: ApertureType = ApertureType.ENTRANCE_PUPIL
    aperture_value: float = 0.0
    # Длины волн (до 5)
    wavelengths: List[Wavelength] = field(default_factory=list)
    # Точки поля (до 5)
    field_points: List[FieldPoint] = field(default_factory=list)
    # Стоп-поверхность (апертурная диафрагма)
    stop_surface: int = 1
    stop_offset: float = 0.0  # мм — смещение диафрагмы от stop_surface вправо
    stop_type: str = 'd'  # Тип диафрагмы: 'd' (диафрагма), 'z' (зрачок-z), 'p' (зрачок)
    # Экранирование
    obscuration_ratio: float = 0.0  # 0 = нет экранирования, 0.3 = 30% центральное
    # Режимы расчёта габаритов (#15)
    beam_mode: str = "real"  # "real" | "given"
    sharp_edge: bool = True
    # Примечания
    comment: str = ""

    @property
    def num_surfaces(self) -> int:
        return len(self.surfaces)

    @property
    def image_index(self) -> int:
        return len(self.surfaces) - 1


# ============================================================
# Standard wavelengths & fields
# ============================================================

def _std_wavelengths():
    """Стандартный набор длин волн: e, G', C."""
    return [
        Wavelength(0.54607, 1.0, "e"),
        Wavelength(0.43405, 1.0, "G'"),
        Wavelength(0.65627, 1.0, "C"),
    ]


def _std_fields(*angles):
    return [FieldPoint(a) for a in angles]


# ============================================================
# Demo system factories
# ============================================================

def create_demo_system() -> OpticalSystem:
    """Создать демо-систему: тонкая линза f'≈77мм"""
    sys = OpticalSystem(
        name="Демо: Тонкая линза",
        object_type=ObjectType.INFINITE,
        object_height=5.0,
    )
    sys.wavelengths = _std_wavelengths()
    sys.field_points = [FieldPoint(0.0), FieldPoint(3.0), FieldPoint(5.0)]
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=50.0, thickness=5.0, glass="К8", semi_diameter=12.0),
        Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0),
    ]
    sys.stop_surface = 1
    return sys


def create_demo_system_by_name(name: str) -> OpticalSystem:
    """Создать демо-систему по имени."""
    systems = {
        "achromat": _demo_achromat,
        "cook_doublet": _demo_cook_doublet,
        "telephoto": _demo_telephoto,
        "petzval": _demo_petzval,
        "mirror": _demo_mirror,
        "meniscus": _demo_meniscus,
        "plano_convex": _demo_plano_convex,
    }
    fn = systems.get(name, create_demo_system)
    return fn()


def _demo_achromat() -> OpticalSystem:
    """Ахроматический дублет f'≈100мм, К8+ТФ1."""
    sys = OpticalSystem(name="Ахромат К8+ТФ1", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0, 5.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=62.0, thickness=6.0, glass="К8", semi_diameter=12.0),
        Surface(radius=-44.0, thickness=2.5, glass="ТФ1", semi_diameter=11.5),
        Surface(radius=-130.0, thickness=95.0, glass="", semi_diameter=12.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_cook_doublet() -> OpticalSystem:
    """Дублет Кука — классический ахромат f/5 f'≈100."""
    sys = OpticalSystem(name="Дублет Кука f/5", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 2.5, 5.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=55.0, thickness=8.0, glass="К8", semi_diameter=11.0),
        Surface(radius=-38.0, thickness=3.0, glass="ТФ2", semi_diameter=10.5),
        Surface(radius=-120.0, thickness=92.0, glass="", semi_diameter=11.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_telephoto() -> OpticalSystem:
    """Телеобъектив — 4 поверхности, отрицательный задний компонент."""
    sys = OpticalSystem(name="Телеобъектив", object_type=ObjectType.INFINITE, object_height=3.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 1.5, 3.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 15.0
    sys.surfaces = [
        Surface(radius=40.0, thickness=6.0, glass="К8", semi_diameter=10.0),
        Surface(radius=-60.0, thickness=25.0, glass="", semi_diameter=9.5),
        Surface(radius=-30.0, thickness=3.0, glass="ТФ1", semi_diameter=7.0),
        Surface(radius=45.0, thickness=40.0, glass="", semi_diameter=7.5),
    ]
    sys.stop_surface = 1
    return sys


def _demo_petzval() -> OpticalSystem:
    """Объектив Петцваля — 2 склеенных дублета, светосильный."""
    sys = OpticalSystem(name="Объектив Петцваля", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 25.0
    sys.surfaces = [
        Surface(radius=75.0, thickness=10.0, glass="К8", semi_diameter=16.0),
        Surface(radius=-55.0, thickness=3.0, glass="ТФ2", semi_diameter=15.5),
        Surface(radius=-200.0, thickness=40.0, glass="", semi_diameter=15.0),
        Surface(radius=50.0, thickness=5.0, glass="К8", semi_diameter=10.0),
        Surface(radius=-45.0, thickness=2.0, glass="ТФ1", semi_diameter=9.5),
        Surface(radius=80.0, thickness=35.0, glass="", semi_diameter=10.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_mirror() -> OpticalSystem:
    """Вогнутое сферическое зеркало f'≈200мм."""
    sys = OpticalSystem(name="Вогнутое зеркало", object_type=ObjectType.INFINITE, object_height=1.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 0.5, 1.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 40.0
    sys.surfaces = [
        Surface(radius=-400.0, thickness=-200.0, glass="", semi_diameter=22.0, is_reflective=True),
        Surface(radius=0.0, thickness=0.0, glass="", semi_diameter=5.0),  # плоскость изображения
    ]
    sys.stop_surface = 1
    return sys


def _demo_meniscus() -> OpticalSystem:
    """Менисковая линза (Росс) — обе поверхности выпуклые."""
    sys = OpticalSystem(name="Мениск Росса", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=45.0, thickness=10.0, glass="К8", semi_diameter=14.0),
        Surface(radius=55.0, thickness=80.0, glass="", semi_diameter=14.0),
    ]
    sys.stop_surface = 1
    return sys


def _demo_plano_convex() -> OpticalSystem:
    """Плоско-выпуклая линза — минимальная сферическая аберрация при правильной ориентации."""
    sys = OpticalSystem(name="Плоско-выпуклая линза", object_type=ObjectType.INFINITE, object_height=5.0)
    sys.wavelengths = _std_wavelengths()
    sys.field_points = _std_fields(0.0, 3.0, 5.0)
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = 20.0
    sys.surfaces = [
        Surface(radius=50.0, thickness=5.0, glass="К8", semi_diameter=12.0),
        Surface(radius=0.0, thickness=93.0, glass="", semi_diameter=12.0),  # плоская
    ]
    sys.stop_surface = 1
    return sys
