"""Справочник стандартных спектральных линий — единственный источник (п. 11 GAP v2).

Все длины волн стандартных линий приложения берутся отсюда:

* диалоги выбора λ — главное окно и :class:`gui.dialogs.spectral_dialog.SpectralDialog`;
* имена линий ``optics_utils.WL_NAMES`` (подписи, чтение файлов проектов);
* ``fileio.json_io.STANDARD_WAVELENGTHS`` (набор по умолчанию для JSON);
* подписи «λ=… нм (имя)» на графиках аберраций;
* якоря цветовой палитры длин волн ``gui.widgets.base.wl_to_plot_color``.

Точные значения — линии характеристических спектров элементов:
F/d/C (H, He), e/g/h (Hg), D (Na), C' (Cd), A' (K) и линии прежних
справочников (i, G', F', s, t) — сохранены, чтобы файлы проектов и
подписи не меняли поведение.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: допуск сопоставления введённой λ со стандартной линией, нм
WL_MATCH_TOL_NM = 1.0


@dataclass(frozen=True)
class SpectralLine:
    """Стандартная спектральная линия.

    Attributes:
        name: обозначение линии ('F', 'd', "C'", 'A', …).
        wavelength_nm: длина волны линии, нм.
        element: элемент — источник линии (Hg, H, He, Na, Cd, K, Cs).
        color: цвет линии («синяя», …; для УФ/ИК — «УФ»/«ИК»).
    """

    name: str
    wavelength_nm: float
    element: str
    color: str

    @property
    def wavelength_um(self) -> float:
        """Длина волны, мкм (единица хранения системы)."""
        return self.wavelength_nm / 1000.0


#: Справочник, отсортирован по длине волны. Единственное определение
#: значений λ стандартных линий в проекте.
SPECTRAL_LINES: tuple[SpectralLine, ...] = (
    SpectralLine('i', 365.01, 'Hg', 'УФ'),
    SpectralLine('h', 404.66, 'Hg', 'фиолетовая'),
    SpectralLine("G'", 434.05, 'Hg', 'синяя'),
    SpectralLine('g', 435.83, 'Hg', 'синяя'),
    SpectralLine("F'", 479.99, 'Cd', 'синяя'),
    SpectralLine('F', 486.13, 'H', 'синяя'),
    SpectralLine('e', 546.07, 'Hg', 'зелёная'),
    SpectralLine('d', 587.56, 'He', 'жёлтая'),
    SpectralLine('D', 589.30, 'Na', 'жёлтая'),
    SpectralLine("C'", 643.85, 'Cd', 'красная'),
    SpectralLine('C', 656.27, 'H', 'красная'),
    SpectralLine('r', 706.52, 'He', 'красная'),
    SpectralLine("A'", 768.19, 'K', 'красная'),
    SpectralLine('s', 852.11, 'Cs', 'ИК'),
    SpectralLine('t', 1013.98, 'Hg', 'ИК'),
)

_SPECTRAL_LINE_BY_NAME: dict[str, SpectralLine] = {
    line.name: line for line in SPECTRAL_LINES
}


def spectral_line_by_name(name: str) -> Optional[SpectralLine]:
    """Найти линию справочника по обозначению.

    Args:
        name: обозначение линии ('d', "C'", …).

    Returns:
        :class:`SpectralLine` или ``None``, если обозначения нет.
    """
    return _SPECTRAL_LINE_BY_NAME.get(name)


def spectral_line_for_wavelength(
        wl_um: float, tol_nm: float = WL_MATCH_TOL_NM) -> Optional[SpectralLine]:
    """Найти стандартную линию, ближайшую к заданной λ.

    Args:
        wl_um: длина волны, мкм.
        tol_nm: допуск совпадения, нм.

    Returns:
        :class:`SpectralLine`, если |λ − λ_линии| ≤ tol_nm, иначе ``None``.
    """
    nm = wl_um * 1000.0
    best = min(SPECTRAL_LINES, key=lambda line: abs(line.wavelength_nm - nm))
    if abs(best.wavelength_nm - nm) <= tol_nm:
        return best
    return None


def named_wavelengths() -> dict[str, float]:
    """Проекция справочника: обозначение → λ (мкм)."""
    return {line.name: line.wavelength_um for line in SPECTRAL_LINES}


def wavelength_names() -> dict[float, str]:
    """Проекция справочника: λ (мкм) → обозначение."""
    return {line.wavelength_um: line.name for line in SPECTRAL_LINES}


def format_spectral_line(line: SpectralLine) -> str:
    """Строка справочника для UI: «d — 587.56 нм (He, жёлтая)»."""
    return (f"{line.name} — {line.wavelength_nm:.2f} нм "
            f"({line.element}, {line.color})")
