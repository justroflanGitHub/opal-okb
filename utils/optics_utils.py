"""
optics_utils.py — shared utility functions for OPAL-OKB.

Created by refactoring/dedup-v2.
Each function here was extracted from duplicated inline code.
See REFACTORING.md for details.
"""

import inspect
import math
import weakref
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optics_engine import OpticalSystem


# ============================================================
# NUMERICAL CONSTANTS
# ============================================================

EPSILON = 1e-10       # general "near zero" for float comparisons
TINY = 1e-15          # very small, for division guards
UNLIMITED_SD = 1e6    # placeholder for unlimited semi-diameter
DEFAULT_RAY_Z = -50.0  # default ray start z (should be overridden by entrance pupil)


# ============================================================
# PUPIL UNITS: мм / дптр (п. 16 GAP v2)
# ============================================================

#: 1 дптр = 1/м → перевод мм-величины (положение зрачка, радиус) в дптр:
#: D = 1000/мм. Физика по OPAL-PC Л1.4.4: «единицы измерения положения
#: зрачков … (дптр/мм)» — диоптрия есть величина, обратная расстоянию в м.
DIOPTRE_PER_M = 1000.0

PUPIL_UNIT_MM = 'мм'
PUPIL_UNIT_DIOPTRE = 'дптр'
#: единственное место со списком единиц зрачка (комбобоксы, тесты)
PUPIL_UNIT_CHOICES = (PUPIL_UNIT_MM, PUPIL_UNIT_DIOPTRE)

#: единица поля системы: дальний тип (INFINITE) — градусы,
#: ближний тип (FINITE) — мм предмета
FIELD_UNIT_DEG = '°'
FIELD_UNIT_MM = PUPIL_UNIT_MM

#: подпись бесконечного значения (зрачок в «бесконечности» → 0 дптр)
INFINITY_TEXT = '∞'

# Выбранная единица зрачков — единственное состояние (single source of
# truth, п. 16): комбобоксы панели анализа и панели результатов только
# синхронизируются с ним через наблюдателей.
_pupil_unit = PUPIL_UNIT_MM
_pupil_unit_observers: list = []


def get_pupil_unit() -> str:
    """Текущая единица зрачков: ``PUPIL_UNIT_MM`` или ``PUPIL_UNIT_DIOPTRE``."""
    return _pupil_unit


def set_pupil_unit(unit: str) -> None:
    """Установить единицу зрачков и оповестить наблюдателей.

    Наблюдатели (комбобоксы панелей) синхронизируются с состоянием и
    перерисовывают зависимые таблицы/графики. Повторная установка той же
    единицы — no-op (нет циклов оповещения).

    Raises:
        ValueError: ``unit`` не входит в ``PUPIL_UNIT_CHOICES``.
    """
    global _pupil_unit
    if unit not in PUPIL_UNIT_CHOICES:
        raise ValueError(
            f"неизвестная единица зрачков {unit!r}; "
            f"допустимо: {', '.join(PUPIL_UNIT_CHOICES)}")
    if unit == _pupil_unit:
        return
    _pupil_unit = unit
    for ref in list(_pupil_unit_observers):
        callback = _resolve_pupil_unit_observer(ref)
        if callback is None:
            _pupil_unit_observers.remove(ref)
            continue
        try:
            callback(unit)
        except RuntimeError:
            # C++-объект Qt-виджета уже удалён (Python-обёртка жива) —
            # мёртвый наблюдатель выбываем из реестра, а не роняет смену
            _pupil_unit_observers.remove(ref)


def _observer_ref(callback):
    """Ссылка на наблюдателя: слабая для методов, сильная для функций.

    Слабая ссылка на метод не удерживает владельца (панель): собранный
    GC виджет исчезает из реестра сам, подписку не нужно снимать явно.
    """
    if inspect.ismethod(callback):
        return weakref.WeakMethod(callback)
    return callback


def _resolve_pupil_unit_observer(ref):
    """Живой вызываемый наблюдатель или ``None`` (ссылка мертва)."""
    if isinstance(ref, weakref.WeakMethod):
        return ref()
    return ref


def add_pupil_unit_observer(callback) -> None:
    """Подписать ``callback(unit)`` на смену единицы зрачков."""
    ref = _observer_ref(callback)
    if ref not in _pupil_unit_observers:
        _pupil_unit_observers.append(ref)


def remove_pupil_unit_observer(callback) -> None:
    """Отписать наблюдателя (обратимо к :func:`add_pupil_unit_observer`)."""
    ref = _observer_ref(callback)
    while ref in _pupil_unit_observers:
        _pupil_unit_observers.remove(ref)


def pupil_unit_is_dioptre() -> bool:
    """``True``, если выбраны диоптрии."""
    return _pupil_unit == PUPIL_UNIT_DIOPTRE


# ------------------------------------------------------------
# Конверсия мм ↔ дптр (обратные длины: положения зрачков, радиусы)
# ------------------------------------------------------------

def mm_to_dioptre(value_mm: float) -> float:
    """Перевести мм-величину в диоптрии: ``D = 1000 / мм``.

    Применимо к обратным длинам — положению зрачка (sP), радиусу
    кривизны и т.п. Ноль переводится в ±∞ с сохранением знака
    (зрачок «на бесконечности» — 0 дптр).

    Raises:
        ValueError: ``value_mm`` — NaN или ±∞.
    """
    if not math.isfinite(value_mm):
        raise ValueError(f"ожидалось конечное значение, получено {value_mm!r}")
    if abs(value_mm) < EPSILON:
        return math.copysign(math.inf, value_mm)
    return DIOPTRE_PER_M / value_mm


def dioptre_to_mm(value_dpt: float) -> float:
    """Перевести диоптрии в мм: ``мм = 1000 / D`` (обратное к
    :func:`mm_to_dioptre`; 0 дптр → ±∞)."""
    if not math.isfinite(value_dpt):
        raise ValueError(f"ожидалось конечное значение, получено {value_dpt!r}")
    if abs(value_dpt) < EPSILON:
        return math.copysign(math.inf, value_dpt)
    return DIOPTRE_PER_M / value_dpt


# ------------------------------------------------------------
# Конверсия поля: градусы ↔ дптр (tan-конверсия через f')
# ------------------------------------------------------------

def field_deg_to_dioptre(field_deg: float, focal_length_mm: float) -> float:
    """Перевести угол поля (градусы) в диоптрии: ``D = 1000·tan θ / f'``.

    tan-конверсия через фокусное расстояние: величина изображения
    y' = f'·tan θ, отнесённая к f' в диоптриях (OPAL-PC: поле дальнего
    типа задаётся в дптр от выходного зрачка).

    Raises:
        ValueError: ``focal_length_mm`` ≈ 0 (конверсия не определена).
    """
    if abs(focal_length_mm) < EPSILON:
        raise ValueError("tan-конверсия поля определена только при f' ≠ 0")
    return (DIOPTRE_PER_M * math.tan(math.radians(field_deg))
            / focal_length_mm)


def field_dioptre_to_deg(value_dpt: float, focal_length_mm: float) -> float:
    """Перевести поле в диоптриях в градусы (обратное к
    :func:`field_deg_to_dioptre`)."""
    if abs(focal_length_mm) < EPSILON:
        raise ValueError("tan-конверсия поля определена только при f' ≠ 0")
    return math.degrees(
        math.atan(value_dpt * focal_length_mm / DIOPTRE_PER_M))


def field_native_unit(system) -> str:
    """Единица поля системы без учёта переключателя: ``FIELD_UNIT_DEG``
    для дальнего типа (INFINITE), ``FIELD_UNIT_MM`` — для ближнего."""
    from optics_engine import ObjectType  # отложенно: без цикла импортов
    if getattr(system, 'object_type', ObjectType.INFINITE) == ObjectType.INFINITE:
        return FIELD_UNIT_DEG
    return FIELD_UNIT_MM


# ------------------------------------------------------------
# Отображение: значения, подписи осей и заголовки таблиц
# ------------------------------------------------------------

def field_unit_display(native_unit: str, efl_mm: float) -> str:
    """Единица поля для отображения по текущему переключателю зрачков.

    Градусы переводятся в дптры (tan-конверсия), когда выбраны диоптрии
    и известно f' ≠ 0; поле ближнего типа (мм) и неизвестное f'
    остаются в родных единицах.
    """
    if (pupil_unit_is_dioptre() and native_unit == FIELD_UNIT_DEG
            and efl_mm and abs(efl_mm) > EPSILON):
        return PUPIL_UNIT_DIOPTRE
    return native_unit


def format_pupil_position(value_mm: float, unit: str, ndigits: int = 4) -> str:
    """Положение зрачка в выбранных единицах: ``'12.3456'`` (мм),
    ``'81.3008'`` (дптр) или ``INFINITY_TEXT`` для нуля в дптрах."""
    value = mm_to_dioptre(value_mm) if unit == PUPIL_UNIT_DIOPTRE else value_mm
    if not math.isfinite(value):
        return INFINITY_TEXT
    return f"{value:.{ndigits}f}"


def format_field(value: float, efl_mm: float, native_unit: str,
                 ndigits: int = 4, with_unit: bool = False) -> str:
    """Значение поля в единицах отображения (см. :func:`field_unit_display`).

    ``with_unit=True`` дописывает единицу: ``'5.00°'`` / ``'50.00 дптр'``.
    """
    unit = field_unit_display(native_unit, efl_mm)
    if unit == PUPIL_UNIT_DIOPTRE:
        value = field_deg_to_dioptre(value, efl_mm)
    text = f"{value:.{ndigits}f}"
    if with_unit:
        text += unit if unit == FIELD_UNIT_DEG else f" {unit}"
    return text


def field_values_display(values, efl_mm: float,
                         native_unit: str) -> tuple[list, str]:
    """Список значений поля в единицах отображения + единица (оси графиков)."""
    unit = field_unit_display(native_unit, efl_mm)
    if unit == PUPIL_UNIT_DIOPTRE:
        return [field_deg_to_dioptre(v, efl_mm) for v in values], unit
    return list(values), unit


# ============================================================
# Z-POSITIONS: cumulative vertex positions from thicknesses
# ============================================================

def compute_z_positions(system):
    """
    Compute cumulative z-position of each surface vertex.
    Returns list of len(surfaces)+1 values (z[0]=0, z[i]=z[i-1]+thickness[i-1]).
    """
    z_pos = [0.0]
    for s in system.surfaces:
        z_pos.append(z_pos[-1] + s.thickness)
    return z_pos


# ============================================================
# PRIMARY WAVELENGTH
# ============================================================

def get_primary_wl(system):
    """
    Return the primary (first) wavelength value in micrometers.
    Falls back to 0.58756 (d-line) if no wavelengths defined.
    """
    return system.wavelengths[0].value if system.wavelengths else 0.58756


# ============================================================
# EFFECTIVE APERTURE
# ============================================================

def get_effective_aperture(system, default=20.0):
    """
    Return aperture diameter (D in mm).

    Любой способ задания апертуры (п. 12 GAP v2: передний/задний угол,
    NA', высота на диафрагме, F/#, NA) приводится к диаметру входного
    зрачка через параксиальные характеристики; falls back to `default`
    if aperture_value <= 0 or the conversion is not applicable.

    Callers should pass the same default they used before refactoring:
    - aberrations.py, advanced_analysis.py, diffraction_mtf.py, zernike.py: default=10.0
    - visualization.py, visualization3d.py, ray_tracing.py: default=20.0
    - optics_engine.py: uses its own efl/4.0 logic (not this function)
    """
    ap = system.aperture_value
    if not ap or ap <= 0:
        return default
    from domain.models import ApertureType  # отложенно: без цикла импортов
    if getattr(system, 'aperture_type', ApertureType.ENTRANCE_PUPIL) \
            == ApertureType.ENTRANCE_PUPIL:
        return ap
    from domain.aperture import aperture_to_epd
    epd = aperture_to_epd(system, ap, system.aperture_type)
    return epd if epd and epd > 0 else default


# ============================================================
# WAVELENGTH NAME LOOKUP
# ============================================================

# Full mapping: wavelength (μm) → spectral line name.
# Проекция справочника стандартных линий (п. 11 GAP v2) — см.
# utils/spectral_lines.py; здесь определяется только проекция.
from .spectral_lines import wavelength_names  # noqa: E402  (раздел ниже)

WL_NAMES = wavelength_names()


def wl_name(wl, tol=0.0002):
    """
    Look up spectral line name for a wavelength (μm).
    Returns name if within `tol` of a known line, else formatted string.
    """
    for wlv, name in WL_NAMES.items():
        if abs(wl - wlv) < tol:
            return name
    return f"{wl:.5f}"


# ============================================================
# TABLE CLIPBOARD COPY
# ============================================================

def copy_table_selection(table_widget):
    """
    Copy selected cells from a QTableWidget to clipboard as TSV.
    Works with any QTableWidget instance.
    """
    from PyQt5.QtWidgets import QApplication
    selection = table_widget.selectedRanges()
    if not selection:
        return
    lines = []
    for rng in selection:
        for row in range(rng.topRow(), rng.bottomRow() + 1):
            cells = []
            for col in range(rng.leftColumn(), rng.rightColumn() + 1):
                item = table_widget.item(row, col)
                cells.append(item.text() if item else '')
            lines.append('\t'.join(cells))
    QApplication.clipboard().setText('\n'.join(lines))


# ============================================================
# VALUE FORMATTING
# ============================================================

def fmt_val(v, ndigits=5):
    """
    Format a numeric value with fixed decimals.
    Returns em-dash for NaN.
    """
    if v != v:  # NaN check
        return '—'
    return f"{v:.{ndigits}f}"


# ============================================================
# COORD-BREAK TABLE CELLS: наклон/децентрировка (п. 17 GAP v2)
# ============================================================

#: Разделитель значений в ячейках «Наклон αx,αy,αz (°)» и «Децентр x,y (мм)»
#: таблицы конструктивных параметров (запятая; пробелы вокруг игнорируются).
COORD_CELL_SEPARATOR = ','

#: Количество значений в ячейке наклона (αx, αy, αz) и децентра (x, y).
COORD_CELL_TILT_COUNT = 3
COORD_CELL_DECENTER_COUNT = 2


def format_coord_cell(values) -> str:
    """Ячейка «наклон/децентр»: компактный список через запятую.

    Все значения ~0 → ``'0'`` (как колонка k); иначе значения через
    :data:`COORD_CELL_SEPARATOR` без хвостовых нулей (5, -2, 0.5).

    Parameters
    ----------
    values: iterable of float — углы (°) или смещения (мм).
    """
    vals = [float(v) for v in values]
    if all(abs(v) <= EPSILON for v in vals):
        return '0'
    return COORD_CELL_SEPARATOR.join(
        f"{v:.4f}".rstrip('0').rstrip('.') or '0' for v in vals)


def parse_coord_cell(text: str, count: int) -> tuple:
    """Разобрать ячейку «наклон/децентр» в кортеж из ``count`` чисел.

    Понятны форматы ``'5, -2, 0'``, ``'5;-2;0'``, ``'5'`` (недостающие
    значения — нули); лишние значения игнорируются.  ``'0'`` → все нули.

    Raises:
        ValueError: в тексте есть нечисловое значение.
    """
    parts = [p for p in text.replace(';', COORD_CELL_SEPARATOR)
             .split(COORD_CELL_SEPARATOR) if p.strip()]
    if not parts:
        return (0.0,) * count
    values = tuple(float(p.strip()) for p in parts[:count])
    return values + (0.0,) * (count - len(values))


# ============================================================
# RAY FACTORY
# ============================================================

def make_field_ray(system: 'OpticalSystem',
                    pupil_x: float,
                    pupil_y: float,
                    field_angle_deg: float,
                    z_start: float,
                    z_pupil: float = 0.0):
    """
    Create a field ray aimed through entrance pupil coordinates.

    For **INFINITE** objects: the ray starts at *z_start*, tilted by
    *field_angle_deg* (degrees), and passes through *(pupil_x, pupil_y)*
    at *z_pupil*.  Back-projection from the pupil plane to the start
    plane is handled automatically.

    For **FINITE** objects: *field_angle_deg* is interpreted as the
    object-side field height (mm).  The ray originates from
    (pupil_x, field_angle_deg) at the object plane and is aimed at
    *(pupil_x, pupil_y)* near the first surface.

    Parameters
    ----------
    system : OpticalSystem
        The optical system (provides ``object_type`` and ``surfaces``).
    pupil_x, pupil_y : float
        Physical coordinates (mm) at the entrance-pupil / first-surface
        plane that the ray must pass through.
    field_angle_deg : float
        Field angle (degrees) for INFINITE objects, or field height (mm)
        for FINITE objects.
    z_start : float
        Z-position where the ray originates.
    z_pupil : float
        Z-position of the entrance pupil (used for back-projection in
        the INFINITE case).  Default 0.0.

    Returns
    -------
    Ray
        A ready-to-trace ray (see :class:`ray_tracing.Ray`).
    """
    from ray_tracing import Ray          # avoid circular at module level
    from optics_engine import ObjectType

    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_angle_deg) if field_angle_deg != 0 else 0.0
        sin_a, cos_a = math.sin(angle), math.cos(angle)

        # Back-project pupil coords to z_start plane
        dz = z_pupil - z_start
        x_start = pupil_x
        if cos_a > EPSILON:
            y_start = pupil_y - dz * sin_a / cos_a
        else:
            y_start = pupil_y

        return Ray(x=x_start, y=y_start, z=z_start, k=0.0, l=sin_a, m=cos_a)
    else:
        # FINITE object — field_angle_deg is field height in mm
        obj_z = -system.surfaces[0].thickness if system.surfaces else DEFAULT_RAY_Z
        d = abs(obj_z)
        if d < EPSILON:
            d = abs(DEFAULT_RAY_Z)
        k = pupil_x / d
        l = (pupil_y - field_angle_deg) / d
        m = 1.0
        norm = math.sqrt(k * k + l * l + m * m)
        return Ray(x=pupil_x, y=field_angle_deg, z=obj_z,
                   k=k / norm, l=l / norm, m=m / norm)
