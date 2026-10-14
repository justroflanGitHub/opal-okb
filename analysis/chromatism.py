"""
OPAL-OKB — OPAL-режим хроматизма: парные длины волн, таблица TABAX3.

Реверс OPALA.EXE (analysis/REVERSE_TRACE.md §9): хроматизм считается
ПОВТОРНОЙ трассировкой того же луча с показателями преломления другой λ.
Выбор волны поверхностный — флаг в записи каждой поверхности
(``wl_flags[surf*2-2]``, байт, шаг записей 0x18): 0 → основная λ
(трейсер FUN_1000_f344, ``[0x50c2]=0``), иначе → второй вход того же
кода FUN_1000_f359 (``[0x50c2]=1``) + печать TABOC1/TABAX3
(FUN_1000_e920). Таблицы спектральных линий в EXE нет (§9.1) — λ только
из пользовательских данных (``system.wavelengths`` / записи).

Повторный прогон в порте — копия системы, где среды помеченных
поверхностей получают ``n_override`` на основную λ со значением
n(стекло, λ поверхности): и трейсер, и :func:`domain.calculations.paraxial_trace`
переиспользуются, а не дублируются. В разностях прогона участвуют только
помеченные поверхности (непомеченные среды одинаковы в обоих прогонах).

Формат TABAX3 (DS 0x7af): ``(f8.3, f9.2, 5f12.6)`` — 7 колонок:
λ пары, осевой отрезок sF' второй волны и 5 хроматических величин.
"""
import copy

from domain.calculations import paraxial_trace, refractive_index
from domain.models import OpticalSystem
from optics_utils import get_primary_wl, get_effective_aperture

from analysis.aberrations import (
    CODDINGTON_SD_INFLATE, _chief_image_height, _compute_ray_start,
    _exit_line, _pupil_field_ray,
)

#: Допуск совпадения длин волн (мкм) — как допуск ``n_override`` в
#: трейсере (0.002): пара (wl_main, wl) ближе этого порога не строится.
PAIR_WL_TOL = 0.002

#: Зона луча для разности углов выхода Δu': край пучка (зона 1.0) на
#: краю поля обычно виньетируется диафрагмой/кромками (STOP/EDGE), поэтому
#: разность углов берётся по лучу зоны 0.7 — стандартная проба зрачка.
ANGLE_RAY_ZONE = 0.7

#: Ширины полей TABAX3: λ f8.3, отрезок f9.2, 5×f12.6 (реверс §9.2).
TABAX3_FIELD_WIDTHS = (8, 9, 12, 12, 12, 12, 12)

#: Подписи колонок TABAX3 (ширины — :data:`TABAX3_FIELD_WIDTHS`).
TABAX3_COLUMNS = ('λ,мкм', "sF',мм", "ΔsF',мм", "Δf',мм", "Δy',мм",
                  "Δu',рад", "ΔsF',%")


def _flag_wavelength(flag, wavelengths):
    """λ (мкм) по значению флага поверхности.

    Флаг OPAL — байт записи: 0 → основная λ, иначе — λ из пользовательских
    данных. Порт принимает те же semantics извне:

    * ``0`` / ``None`` / ``False`` → ``None`` (основная λ);
    * ``int k ≥ 1`` → ``wavelengths[k-1]`` (1-основной индекс, как байт);
    * ``float > 0`` → прямое значение λ (мкм).
    """
    if flag is None or flag is False or flag == 0:
        return None
    if isinstance(flag, bool):
        raise ValueError(
            "wl-флаг bool не несёт λ: используйте int-индекс (1-основной) "
            "или float λ (мкм)")
    if isinstance(flag, int):
        if not (1 <= flag <= len(wavelengths)):
            raise ValueError(
                f"wl-флаг {flag} вне списка длин волн (1..{len(wavelengths)})")
        return float(wavelengths[flag - 1])
    lam = float(flag)
    if lam <= 0.0:
        raise ValueError(f"wl-флаг {flag!r}: λ должна быть > 0")
    return lam


def _resolve_surface_wavelengths(system: OpticalSystem,
                                 wl_flags=None) -> list:
    """λ каждой поверхности (None = основная).

    Источник флагов: аргумент ``wl_flags`` (список по поверхностям), иначе
    атрибут ``Surface.wl_flag`` (декодер OPJ сейчас его не заполняет —
    флаги принимаются извне, правило задачи). Возвращает список длиной
    ``len(system.surfaces)``.
    """
    wls = [w.value for w in system.wavelengths]
    if wl_flags is not None:
        if len(wl_flags) < len(system.surfaces):
            raise ValueError(
                f"wl_flags ({len(wl_flags)}) короче списка поверхностей "
                f"({len(system.surfaces)})")
        flags = list(wl_flags)[:len(system.surfaces)]
    else:
        flags = [getattr(s, 'wl_flag', 0) for s in system.surfaces]
    return [_flag_wavelength(f, wls) for f in flags]


def _mixed_system(system: OpticalSystem, wl_main: float,
                  wl_map: dict) -> OpticalSystem:
    """Копия системы с «другой волной» у помеченных поверхностей.

    Режим B трейсера (f359, ``[0x50c2]=1``): тот же луч, но среды
    поверхностей из ``wl_map`` {индекс: λ} преломляются по показателям
    своей λ. Реализовано ``n_override[wl_main] = n(стекло, λ_i)`` —
    трейсер/paraxial_trace зовутся с wl_main и берут overridden-значения.
    n(λ) — с учётом записи (``n_override`` поверхности: RI-таблицы LBO),
    иначе дисперсионная формула каталога. Зеркала и среды без дисперсии
    (воздух) не переопределяются.
    """
    sys_b = copy.deepcopy(system)
    for i, lam in wl_map.items():
        surf = sys_b.surfaces[i]
        if surf.is_reflective or not surf.glass.strip():
            continue
        n_alt = refractive_index(surf.glass, lam, None, surf.n_override)
        override = dict(surf.n_override or {})
        override[wl_main] = n_alt
        surf.n_override = override
    return sys_b


def _fmt_field(value, width: int, spec: str) -> str:
    """Поле формата Fortran (``width`` + ``spec`` вида '.3f');
    ``None`` (луч не дошёл) — пробелы."""
    if value is None:
        return ' ' * width
    return format(value, f'{width}{spec}')


def tabax3_rows(result) -> list:
    """Строки таблицы TABAX3 по результату :func:`compute_chromatism_opal`.

    Формат OPAL (DS 0x7af): ``(f8.3, f9.2, 5f12.6)`` — строка из 7 колонок
    шириной 8+9+12·5 = 77 символов, без разделителей.
    """
    rows = []
    for row in result.get('rows', []):
        fields = (
            (row.get('wl'), '.3f'),
            (row.get('segment_mm'), '.2f'),
            (row.get('dsF_prime_mm'), '.6f'),
            (row.get('dfocal_mm'), '.6f'),
            (row.get('dy_prime_mm'), '.6f'),
            (row.get('du_prime_rad'), '.6f'),
            (row.get('dsF_prime_pct'), '.6f'),
        )
        rows.append(''.join(
            _fmt_field(v, w, s)
            for (v, s), w in zip(fields, TABAX3_FIELD_WIDTHS)))
    return rows


def format_tabax3(result) -> str:
    """Таблица TABAX3 целиком: строка подписей + строки данных."""
    header = ''.join(f'{col:>{w}}' for col, w in
                     zip(TABAX3_COLUMNS, TABAX3_FIELD_WIDTHS)).rstrip()
    return '\n'.join([header] + tabax3_rows(result))


class ChromatismResult(dict):
    """Результат :func:`compute_chromatism_opal` (dict + TABAX3-формат).

    Ключи: ``wl_main`` (основная λ пары, мкм), ``mode`` (``'per_surface'``
    | ``'fallback'``), ``field_y`` (поле главного луча), ``rows`` —
    список словарей-строк TABAX3:

    * ``wl`` — λ пары (мкм);
    * ``surface`` — индекс помеченной поверхности (0-основной; ``None``
      в fallback-режиме — переключены все поверхности);
    * ``segment_mm`` — осевой отрезок sF' второй волны пары (колонка 2);
    * ``dsF_prime_mm`` — осевой хроматизм ΔsF' (мм);
    * ``dfocal_mm`` — хроматизм фокусного расстояния Δf' (мм);
    * ``dy_prime_mm`` — поперечный хроматизм Δy' главного луча (мм);
    * ``du_prime_rad`` — разность углов выхода Δu' крайнего
      меридионального луча (рад);
    * ``dsF_prime_pct`` — относительный осевой хроматизм ΔsF'/f' (%).

    Величины ``None`` — луч в одном из прогонов не дошёл (вывод —
    пробелы).
    """

    def formatTabax3(self) -> str:
        """Таблица TABAX3 (подписи + данные), как FUN_1000_e920."""
        return format_tabax3(self)


def compute_chromatism_opal(system: OpticalSystem, wl_main: float = None,
                            wl_flags=None, field_y: float = None
                            ) -> ChromatismResult:
    """OPAL-режим хроматизма: повторная трассировка с другой λ (§9).

    Для каждой помеченной поверхности (``wl_flags`` / ``Surface.wl_flag``)
    строится пара прогонов: «основная λ» → «λ поверхности» — та же
    трассировка, но среды помеченных поверхностей преломляются по своей λ
    (:func:`_mixed_system`). Разности на изображении — осевые/поперечные
    хроматические величины. Если wl-флагов нет (современные системы) —
    fallback: пары (wl_main, wl) для всех λ из ``system.wavelengths``
    (сравнимо со старым polychromatic-поведением).

    Осевые величины (ΔsF', Δf') — параксиальные разности прогона B и
    прогона A (:func:`domain.calculations.paraxial_trace`, не дублируется);
    в fallback-режиме прогон B эквивалентен ``paraxial_trace(system, wl)``
    в точности (те же n на среду), что и проверяется сверковочным тестом.

    Args:
        system: Оптическая система (не изменяется).
        wl_main: Основная λ пары (мкм); None → основная λ системы.
        wl_flags: Флаги волн по поверхностям (см. :func:`_flag_wavelength`);
            None → читать ``Surface.wl_flag``, при отсутствии — fallback.
        field_y: Поле главного луча (град/мм); None → максимальное поле.

    Returns:
        :class:`ChromatismResult` со строками ``rows`` и методом
        ``formatTabax3()``.
    """
    empty = ChromatismResult(
        wl_main=float(wl_main) if wl_main is not None else get_primary_wl(system),
        mode='fallback', field_y=field_y or 0.0, rows=[])
    if not system.surfaces:
        return empty

    wl_main = float(wl_main) if wl_main is not None else get_primary_wl(system)
    lam_surf = _resolve_surface_wavelengths(system, wl_flags)
    flagged = {i: lam for i, lam in enumerate(lam_surf)
               if lam is not None and abs(lam - wl_main) >= PAIR_WL_TOL}

    # Пары (поверхность, λ): per-surface изоляция вклада каждой помеченной
    # поверхности либо fallback по всем λ системы
    if flagged:
        mode = 'per_surface'
        pairs = sorted(flagged.items())
    else:
        mode = 'fallback'
        pairs, seen = [], []
        for w in system.wavelengths:
            wl = float(w.value)
            if abs(wl - wl_main) < PAIR_WL_TOL \
                    or any(abs(wl - s) < PAIR_WL_TOL for s in seen):
                continue
            seen.append(wl)
            pairs.append((None, wl))
        if not pairs:
            return ChromatismResult(wl_main=wl_main, mode=mode,
                                    field_y=field_y or 0.0, rows=[])

    if field_y is None:
        fields = [abs(fp.y) for fp in (system.field_points or [])]
        field_y = max(fields) if fields else 0.0

    # Прогон A (основная λ) — общий для всех пар; лучи одни и те же,
    # меняются только показатели преломления сред (режим B)
    parax_main = paraxial_trace(system, wl=wl_main)
    sF_main = parax_main.get('sF_prime', 0.0)
    f_main = parax_main.get('focal_length', 0.0)
    z_start, z_pupil = _compute_ray_start(system, parax_main)
    aperture = get_effective_aperture(system, default=10.0)
    upper_ray = _pupil_field_ray(system, 0.0, ANGLE_RAY_ZONE * aperture / 2.0,
                                 field_y, z_start, z_pupil)

    # Запас полудиаметров для прохода лучей поля (приём
    # compute_field_aberrations); копии наследуют увеличенные значения
    _orig_sds = [s.semi_diameter for s in system.surfaces]
    for s in system.surfaces:
        if s.semi_diameter > 0:
            s.semi_diameter = abs(s.semi_diameter) * CODDINGTON_SD_INFLATE
    try:
        y_chief_a = _chief_image_height(system, wl_main, field_y, parax_main)
        line_a = _exit_line(system, upper_ray, wl_main)
        slope_a = line_a[4] if line_a is not None else None

        rows = []
        for surf_idx, wl_value in pairs:
            wl_map = ({surf_idx: wl_value} if surf_idx is not None
                      else {i: wl_value for i in range(len(system.surfaces))})
            sys_b = _mixed_system(system, wl_main, wl_map)
            parax_b = paraxial_trace(sys_b, wl=wl_main)
            y_chief_b = _chief_image_height(sys_b, wl_main, field_y, parax_b)
            line_b = _exit_line(sys_b, upper_ray, wl_main)
            slope_b = line_b[4] if line_b is not None else None

            dsF = parax_b.get('sF_prime', 0.0) - sF_main
            rows.append({
                'wl': wl_value,
                'surface': surf_idx,
                'segment_mm': parax_b.get('sF_prime', 0.0),
                'dsF_prime_mm': dsF,
                'dfocal_mm': parax_b.get('focal_length', 0.0) - f_main,
                'dy_prime_mm': (y_chief_b - y_chief_a)
                if y_chief_b is not None and y_chief_a is not None else None,
                'du_prime_rad': (slope_b - slope_a)
                if slope_b is not None and slope_a is not None else None,
                'dsF_prime_pct': dsF / f_main * 100.0 if f_main else None,
            })
    finally:
        for i, s in enumerate(system.surfaces):
            s.semi_diameter = _orig_sds[i]

    return ChromatismResult(wl_main=wl_main, mode=mode, field_y=field_y,
                            rows=rows)
