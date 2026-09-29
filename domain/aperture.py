"""Способы задания апертуры осевого пучка и пересчёт между ними (п. 12 GAP v2).

Три способа задания (плюс прежние — диаметр зрачка, F/#, NA):

* передняя апертура — полуугол предметного луча *u* (°);
* задняя апертура — полуугол в пространстве изображений *u'* (°) или
  числовая апертура NA' = n'·sin u';
* высота луча на апертурной диафрагме (полувысота, мм).

Каноническое представление — диаметр входного зрачка D_вх: именно им
пользуются трассировка лучей и расчёт пучков. Пересчёты опираются на
параксиальные характеристики (:func:`domain.calculations.paraxial_trace`):
f', sF', положение зрачков sP/sP' и увеличения изображения диафрагмы
(луч через центр диафрагмы + инвариант Лагранжа):

* полуугол → полувысота: h = tan(u)·L (L — путь луча до плоскости);
* диафрагма → зрачок: h_зрачок = h_диафр · m (m — увеличение
  изображения диафрагмы соответствующего зрачка).
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Union

from domain.models import ApertureType, ObjectType

#: допуск «нуля» знаменателей пересчёта, мм
APERTURE_EPS = 1e-9
#: ограничение полуугла при пересчёте NA' (sin u' < 1)
MAX_REAR_NA = 0.999999

ApertureSpec = Union[float, Optional[float]]


def _parax_or_trace(system, parax: Optional[Dict]):
    """Готовые параксиальные характеристики или трассировка системы."""
    if parax is not None:
        return parax
    from domain.calculations import paraxial_trace  # отложенно: без цикла
    return paraxial_trace(system)


def object_to_pupil_distance(system, parax: Optional[Dict] = None) -> Optional[float]:
    """Путь осевого предметного луча от плоскости предмета до входного зрачка.

    Только для предмета на конечном расстоянии (для предмета в ∞ луч
    параллелен — передняя апертура вырождается).

    Returns:
        Расстояние (мм) или ``None``, если предмет в бесконечности /
        зрачок не определён.
    """
    if system.object_type != ObjectType.FINITE:
        return None
    parax = _parax_or_trace(system, parax)
    if not system.surfaces:
        return None
    d_obj = abs(system.surfaces[0].thickness)  # предмет перед 1-й поверхностью
    s_pupil = parax.get('entrance_pupil', parax.get('sP', 0.0)) if parax else 0.0
    dist = d_obj + s_pupil
    if dist <= APERTURE_EPS:
        return None
    return dist


def aperture_to_epd(system, value: float,
                    ap_type: ApertureType,
                    parax: Optional[Dict] = None) -> Optional[float]:
    """Привести любой способ задания апертуры к диаметру входного зрачка.

    Args:
        system: Оптическая система (объект/поверхности/диафрагма).
        value: Значение апертуры в единицах способа.
        ap_type: Способ задания (:class:`ApertureType`).
        parax: Готовые параксиальные характеристики (или ``None`` —
            посчитать).

    Returns:
        Диаметр входного зрачка (мм) или ``None``, если способ неприменим
        (предмет в ∞ для переднего угла, вырожденные параксиальные
        характеристики, значение ≤ 0).
    """
    if value is None or value <= APERTURE_EPS:
        return None
    if ap_type == ApertureType.ENTRANCE_PUPIL:
        return float(value)

    parax = _parax_or_trace(system, parax)
    efl = abs(parax.get('focal_length', 0.0)) if parax else 0.0

    if ap_type == ApertureType.F_NUMBER:
        return efl / value if value > APERTURE_EPS and efl > APERTURE_EPS else None
    if ap_type == ApertureType.NUMERICAL_APERTURE:
        # прежняя семантика приложения: D = 2·f'·NA
        return 2.0 * efl * value if efl > APERTURE_EPS else None

    if ap_type == ApertureType.FRONT_ANGLE:
        dist = object_to_pupil_distance(system, parax)
        if dist is None:
            return None
        return 2.0 * math.tan(math.radians(value)) * dist

    if ap_type == ApertureType.REAR_ANGLE:
        return _rear_angle_to_epd(system, math.radians(value), parax)

    if ap_type == ApertureType.REAR_NA:
        na = min(value, MAX_REAR_NA)
        return _rear_angle_to_epd(system, math.asin(na), parax)

    if ap_type == ApertureType.STOP_HEIGHT:
        m_entrance = (parax or {}).get('entrance_pupil_magnification')
        if not m_entrance or abs(m_entrance) <= APERTURE_EPS:
            return None
        return 2.0 * value * abs(m_entrance)

    return None


def _rear_angle_to_epd(system, u_prime_rad: float, parax: Dict) -> Optional[float]:
    """Полуугол в пространстве изображений → диаметр входного зрачка.

    Осевой крайний луч проходит через край выходного зрачка под углом
    u' к оси и пересекает ось в параксиальном фокусе: полувысота
    выходного зрачка h' = tan(u')·|sF' − sP'|, далее через увеличение
    зрачков D_вх = 2·h'/|m_p|.
    """
    s_fprime = parax.get('sF_prime', parax.get('back_focal_distance', 0.0))
    s_xpupil = parax.get('exit_pupil', parax.get('sP_prime', 0.0))
    m_pupil = parax.get('pupil_magnification')
    lever = abs(s_fprime - s_xpupil)
    if m_pupil is None or abs(m_pupil) <= APERTURE_EPS or lever <= APERTURE_EPS:
        return None
    h_exit = math.tan(u_prime_rad) * lever
    return 2.0 * h_exit / abs(m_pupil)


def epd_to_apertures(system, epd: float,
                     parax: Optional[Dict] = None) -> Dict[ApertureType, Optional[float]]:
    """Все представления одного осевого пучка, заданного диаметром зрачка.

    Args:
        system: Оптическая система.
        epd: Диаметр входного зрачка (мм).
        parax: Готовые параксиальные характеристики (или ``None``).

    Returns:
        Словарь «способ → значение» для всех способов задания; неприменимые
        (например, передний угол при предмете в ∞) — ``None``.
    """
    out: Dict[ApertureType, Optional[float]] = {}
    if epd is None or epd <= APERTURE_EPS:
        return {t: None for t in ApertureType}
    semi = epd / 2.0

    out[ApertureType.ENTRANCE_PUPIL] = epd
    parax = _parax_or_trace(system, parax)
    efl = abs(parax.get('focal_length', 0.0)) if parax else 0.0
    out[ApertureType.F_NUMBER] = efl / epd if efl > APERTURE_EPS else None
    out[ApertureType.NUMERICAL_APERTURE] = epd / (2.0 * efl) if efl > APERTURE_EPS else None

    dist = object_to_pupil_distance(system, parax)
    out[ApertureType.FRONT_ANGLE] = (
        math.degrees(math.atan(semi / dist)) if dist else None)

    s_fprime = parax.get('sF_prime', parax.get('back_focal_distance', 0.0))
    s_xpupil = parax.get('exit_pupil', parax.get('sP_prime', 0.0))
    m_pupil = parax.get('pupil_magnification')
    lever = abs(s_fprime - s_xpupil)
    if m_pupil and abs(m_pupil) > APERTURE_EPS and lever > APERTURE_EPS:
        u_prime = math.atan(semi * abs(m_pupil) / lever)
        out[ApertureType.REAR_ANGLE] = math.degrees(u_prime)
        out[ApertureType.REAR_NA] = math.sin(u_prime)
    else:
        out[ApertureType.REAR_ANGLE] = None
        out[ApertureType.REAR_NA] = None

    m_entrance = (parax or {}).get('entrance_pupil_magnification')
    out[ApertureType.STOP_HEIGHT] = (
        semi / abs(m_entrance) if m_entrance and abs(m_entrance) > APERTURE_EPS else None)
    return out


def convert_aperture(system, value: float, from_type: ApertureType,
                     parax: Optional[Dict] = None) -> Dict[str, Optional[float]]:
    """Пересчёт апертуры, заданной любым способом, во все представления.

    Args:
        system: Оптическая система.
        value: Значение апертуры в единицах способа *from_type*.
        from_type: Исходный способ задания.
        parax: Готовые параксиальные характеристики (или ``None``).

    Returns:
        Словарь с ключом ``'epd'`` (канонический диаметр входного
        зрачка, мм) и по ключу-имени каждого способа задания.
    """
    epd = aperture_to_epd(system, value, from_type, parax=parax)
    result: Dict[str, Optional[float]] = {'epd': epd}
    if epd is None:
        return result
    by_type = epd_to_apertures(system, epd, parax=parax)
    for ap_type, val in by_type.items():
        result[ap_type.name.lower()] = val
    return result
