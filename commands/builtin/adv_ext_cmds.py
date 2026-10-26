"""
OPAL-OKB — Пакет R500-14: расширения продвинутого анализа (adv.*).

ДОПОЛНЕНИЯ к adv.* Волны 1 (aber_cmds: adv.psf/lsf/enc/ptf/bar_image/
bar_mtf/esf/object_image) — темы, которых в реестре ещё нет:

* объёмная ФРТ через фокус — ``adv.psf.focus_stack`` (срезы-метрики на
  сетке дефокуса), ``adv.psf.waist`` (перетяжка: параболическое
  уточнение пика, осевой FWHM, асимметрия), ``adv.psf.fwhm`` (ширины
  сечений в данной плоскости), ``adv.psf.centroid`` (энергетический
  центр по полям);
* свёртка ФРТ с объектом — ``adv.slit_image`` (щель конечной ширины,
  2D-свёртка через analysis.advanced.convolve_fft),
  ``adv.convolve.profile`` (отклик на произвольный 1D-профиль —
  свёртка с ФРЛ); мира/край/точка уже закрыты ``adv.object_image``;
* миры СШАФ-1951 — ``adv.usaf.table`` (частоты групп/элементов,
  стандарт ν = 2^(G+(E−1)/6) лин/мм), ``adv.usaf.resolve``
  (разрешимый элемент по сечениям ЧКХ), ``adv.usaf.object`` (ширины
  штрихов на предмете через увеличение);
* глубина фокуса — ``adv.dof.diffraction`` (дифракционная ±2λF#²,
  критерий Рэлея λ/4 OPD), ``adv.dof.compare`` (по полям:
  дифракционная vs геометрическая из RMS пятна, режим);
* шум и сигнал — ``adv.snr.bars`` (SNR/контраст штрихов через ЧКХ при
  фотонном шуме и шуме чтения), ``adv.noise.spot`` (наложение шума
  детектора на пятно: Пуассон+Гаусс, детерминированный seed);
* пиксельное интегрирование — ``adv.pixel.matrix`` (пиксельная матрица
  пятна с подпиксельной передискретизацией), ``adv.pixel.energy``
  (доля энергии в пикселе/блоке N×N со смещением);
* спектральная свёртка — ``adv.psf.poly`` / ``adv.lsf.poly``
  (полихроматические ФРТ/ФРЛ — некогерентная взвешенная сумма по λ
  системы на общей координатной сетке);
* критерий разрешения по сечениям ЧКХ (Торнбер) —
  ``adv.resolve.thornber``: разрешение ограничено ХУДШИМ из тангенци-
  ального/сагиттального сечений + частота пересечения ветвей
  (астигматический баланс);
* энергия в кольце фотоприёмника — ``adv.energy.ring`` (ФКЭ( r₂ ) −
  ФКЭ( r₁ ));
* комплексная ОТФ — ``adv.otf.complex`` (Re/Im/фаза сечений мер/саг из
  FFT ФРТ; фазовая ЧКХ через psf_grid-маршрут, в отличие от
  ``adv.ptf`` — другой движок);
* эталон Эйри — ``adv.airy.encircled`` (аналитическая ФКЭ пятна Эйри
  1 − J0² − J1² через ряды Бесселя + сравнение с фактической ФРТ).

Ядра не дублируются: ФРТ/ЧКХ/ФКЭ/ФРЛ — analysis/psf_mtf.psf_grid и
производные, свёртка — analysis/advanced.convolve_fft, геометрическое
пятно — analysis/aberrations; перевод мм ↔ длины волн дефокуса — по
той же формуле, что analysis/advanced (константа PARAXIAL_DEFOCUS_
FACTOR). Префиксы Волны 3 (psf./diffr./zern./mtf./strehl./focus.)
не занимаются — все новые команды в adv.*.
"""
import math
import random

from commands.base import (
    ERR_INVALID_PARAM,
    CommandError,
    Param,
)
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
)
from optics_utils import (
    get_effective_aperture,
)

# Общие адаптеры Волны 3 (псевдонимы модуля psf_cmds — переиспользование
# вместо копирования): ФРТ psf_grid + λ-разрешение.
from commands.builtin.psf_cmds import (
    AIRY_FACTOR,
    _psf_of,
    _resolve_wl,
)
# Поля/λ системы и FWHM-хелпер — общий код R500-7 (sweep).
from commands.builtin.sweep_cmds import _fields_arg, _fwhm_um, _wls_arg

# Коэффициент параксиального дефокуса W = 0.5·Δz·NA²·ρ²/λ (та же
# константа, что в analysis/advanced.compute_psf — единая формула).
from analysis.advanced import PARAXIAL_DEFOCUS_FACTOR

# ============================================================
# Именованные константы пакета
# ============================================================

#: Частота СШАФ-1951 группы 0, элемента 1 (лин/мм) — база таблицы.
USAF_BASE_FREQ_LPMM = 1.0

#: Шаг частоты между элементами группы СШАФ: 2^(1/6) ≈ 1.1225.
USAF_ELEMENT_RATIO = 2.0 ** (1.0 / 6.0)

#: Элементы группы СШАФ (1..6).
USAF_ELEMENTS = (1, 2, 3, 4, 5, 6)

#: Полуширина дифракционной глубины фокуса (критерий Рэлея λ/4 OPD):
#: ±2·λ·F#² (Smith, Modern Optical Engineering; согласуется с
#: дефокусом 0.25λ на краю зрачка в формуле PARAXIAL_DEFOCUS_FACTOR).
RAYLEIGH_DOF_COEFF = 2.0

#: Порог ЧКХ по умолчанию в критериях разрешения (доли единицы).
MTF_THRESHOLD_DEFAULT = 0.1

#: Шум чтения детектора по умолчанию, электроны RMS.
READ_NOISE_E_DEFAULT = 5.0

#: Средний уровень сигнала по умолчанию, электроны на пиксель.
SIGNAL_E_DEFAULT = 10000.0

#: Порог λ, ниже которого Пуассон берётся алгоритмом Кнута, выше —
#: нормальным приближением N(λ, λ) (стандартная практика).
POISSON_NORMAL_THRESHOLD = 30.0

#: Seed генератора шума по умолчанию (детерминизм).
NOISE_SEED_DEFAULT = 0

#: Подпиксельная кратность передискретизации ФРТ по умолчанию.
PIXEL_SUBSAMPLE_DEFAULT = 4

#: Окно пиксельной матрицы по умолчанию (нечётное, пикселей на сторону).
PIXEL_MATRIX_SIZE_DEFAULT = 7

#: Лучей точечной диаграммы в геометрической ГРФ по умолчанию.
DOF_SPOT_RAYS_DEFAULT = 30

#: Точек сетки дефокуса по умолчанию (нечётное: центр в плоскости Гаусса).
FOCUS_STACK_POINTS_DEFAULT = 9

#: ±мм развёртки дефокуса по умолчанию (≈2·2λF#² демо-ахромата).
FOCUS_RANGE_MM_DEFAULT = 0.05

#: Минимальное число точек развёртки дефокуса.
FOCUS_POINTS_MIN = 3

#: Число членов рядов Бесселя J0/J1 (x ≤ ~50 сходится с запасом).
BESSEL_SERIES_TERMS = 32

#: Ориентации сечений ФРЛ (как adv.lsf Волны 1).
LSF_SECTIONS = ("tangential", "sagittal")

#: Оси щели (вдоль какой оси тянутся штрихи/щель).
SLIT_AXES = ("x", "y")

#: Радиусы-множители r₁ для таблицы ФКЭ Эйри по умолчанию.
AIRY_R_FRACTIONS_DEFAULT = (0.25, 0.5, 1.0, 1.5, 2.0)

#: Число тёмных колец Эйри в справочнике adv.airy.encircled.
AIRY_DARK_RING_COUNT = 3

#: Порог «тихой зоны» матрицы (доля от максимума) для оценки фона
#: шума: пиксели с ожидаемым сигналом ниже этого уровня считаются
#: фоном.
QUIET_FRACTION = 0.01


# ============================================================
# Хелперы (адаптер, не домен)
# ============================================================

def _odd_points(num_points: int, what: str) -> int:
    """Нечётное число точек развёртки (центр — плоскость Гаусса)."""
    if num_points < FOCUS_POINTS_MIN:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"{what}: нужно ≥ {FOCUS_POINTS_MIN} точек, получено "
            f"{num_points}")
    return num_points if num_points % 2 == 1 else num_points + 1


def _defocus_waves_per_mm(system, wl: float) -> float:
    """Дефокус на краю зрачка (волны) на мм осевого сдвига.

    W_край = PARAXIAL_DEFOCUS_FACTOR·Δz·NA²/λ (формула
    analysis/advanced.compute_psf; NA′ = D/(2f′)).
    """
    from optics_engine import paraxial_trace
    aperture = get_effective_aperture(system, default=10.0)
    efl = abs(paraxial_trace(system).get("focal_length", 0.0) or 0.0)
    if efl <= 0 or aperture <= 0 or wl <= 0:
        raise CommandError(
            ERR_INVALID_PARAM,
            "не определены апертура/f′ системы — конверсия дефокуса "
            "невозможна")
    na_img = aperture / (2.0 * efl)
    return PARAXIAL_DEFOCUS_FACTOR * na_img ** 2 / (wl * 1e-3)


def _fwhm_of(profile, axis) -> float:
    """FWHM профиля (мкм) — общий хелпер sweep._fwhm_um."""
    return _fwhm_um(profile, axis)


def _threshold_crossing(freqs, values, threshold: float):
    """Первая частота, где кривая падает ниже порога (линейная
    интерполяция; None — не упала в диапазоне)."""
    for i in range(1, len(freqs)):
        if values[i] < threshold <= values[i - 1]:
            span = values[i - 1] - values[i]
            if span <= 0:
                return float(freqs[i])
            frac = (values[i - 1] - threshold) / span
            return float(freqs[i - 1] + frac * (freqs[i] - freqs[i - 1]))
    return None


def _parabolic_vertex(y0: float, y1: float, y2: float,
                      step: float) -> float:
    """Смещение вершины параболы по трём точкам (шаг сетки)."""
    denom = y0 - 2.0 * y1 + y2
    if denom == 0:
        return 0.0
    return 0.5 * (y0 - y2) / denom * step


def _parse_number_list(values, param_name: str) -> list:
    """Список чисел (валидация как zern._parse_coeffs)."""
    if not isinstance(values, (list, tuple)) or not values:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: нужен непустой список чисел")
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError) as exc:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: все элементы — числа") from exc


def _weighted_spectrum(system, wl_list, weights):
    """Спектр (λ, вес) для полихрома: явные списки или λ системы."""
    if wl_list is not None:
        lambdas = _parse_number_list(wl_list, "wl_list")
        wls = ([float(w) for w in weights]
               if weights is not None else [1.0] * len(lambdas))
        if len(wls) != len(lambdas):
            raise CommandError(
                ERR_INVALID_PARAM,
                "weights должен совпадать по длине с wl_list")
    else:
        lambdas = _wls_arg(system)
        by_value = {float(w.value): float(w.weight)
                    for w in system.wavelengths}
        wls = [by_value.get(l, 1.0) for l in lambdas]
    total = sum(wls)
    if total <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "сумма весов спектра должна быть > 0")
    return lambdas, [w / total for w in wls]


def _resample_regular(image, src_x, src_y, dst_x, dst_y):
    """Билинейная передискретизация 2D-массива с регулярной сетки на
    другую регулярную (сепарабельно по осям через np.interp; вне
    исходной сетки — 0)."""
    import numpy as np
    src_x = np.asarray(src_x, dtype=float)
    src_y = np.asarray(src_y, dtype=float)
    tmp = np.empty((len(src_y), len(dst_x)))
    for i in range(len(src_y)):
        tmp[i] = np.interp(dst_x, src_x, image[i], left=0.0, right=0.0)
    out = np.empty((len(dst_y), len(dst_x)))
    for j in range(len(dst_x)):
        out[:, j] = np.interp(dst_y, src_y, tmp[:, j], left=0.0,
                              right=0.0)
    return out


def _pixelate(psf, x_um, y_um, pixel_um: float, size: int,
              offset_x_um: float = 0.0, offset_y_um: float = 0.0,
              subsample: int = PIXEL_SUBSAMPLE_DEFAULT):
    """Пиксельная матрица пятна: интегрирование ФРТ по пикселям.

    ФРТ (Σ = 1) передискретизируется билинейно с шагом pitch/subsample
    (подпиксельное интегрирование), отсчёты биннингуются по центрам в
    пиксели размера ``pixel_um`` со смещением центра пиксельной решётки
    (offset); возвращается окно size×size (центр — k=0).

    Returns:
        ``(matrix size×size долей энергии, доля в окне, pitch_um,
        fine_step_um)``.
    """
    import numpy as np
    if pixel_um <= 0:
        raise CommandError(ERR_INVALID_PARAM, "pixel_um должен быть > 0")
    if size < 1 or size % 2 == 0:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"size должен быть нечётным ≥ 1, получено {size}")
    if subsample < 1:
        raise CommandError(ERR_INVALID_PARAM,
                           "subsample должен быть ≥ 1")
    x_um = np.asarray(x_um, dtype=float)
    y_um = np.asarray(y_um, dtype=float)
    pitch = float(x_um[1] - x_um[0])
    fine = pitch / subsample
    # точное число точек мелкой сетки (без.endpoint-погрешности arange)
    n_fine = (len(x_um) - 1) * subsample + 1
    fine_axis = x_um[0] + np.arange(n_fine) * fine
    fine_psf = (_resample_regular(np.asarray(psf), x_um, y_um,
                                  fine_axis, fine_axis)
                if subsample > 1 else np.asarray(psf))
    # Билинейная передискретизация сохраняет Σ·шаг² лишь приближённо —
    # нормируем на фактическую сумму, чтобы доли энергии оставались
    # долями (Σ по всем пикселям = 1) при любой кратности.
    fine_total = float(fine_psf.sum())
    if fine_total <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "пустая ФРТ для пиксельного интегрирования")
    fine_psf = fine_psf / fine_total
    gx, gy = np.meshgrid(fine_axis, fine_axis)
    kx = np.rint((gx - offset_x_um) / pixel_um).astype(int)
    ky = np.rint((gy - offset_y_um) / pixel_um).astype(int)
    half = size // 2
    inside = (np.abs(kx) <= half) & (np.abs(ky) <= half)
    flat = (ky[inside] + half) * size + (kx[inside] + half)
    matrix = np.bincount(flat, weights=fine_psf[inside],
                         minlength=size * size).reshape(size, size)
    return matrix, float(matrix.sum()), pitch, fine


def _bessel_j0(x: float) -> float:
    """J0(x) рядом Тейлора (сходится для x ≲ 50 при 32 членах)."""
    term = 1.0
    total = 1.0
    half_sq = (0.5 * x) ** 2
    for k in range(1, BESSEL_SERIES_TERMS):
        term *= -half_sq / (k * k)
        total += term
    return total


def _bessel_j1(x: float) -> float:
    """J1(x) рядом Тейлора."""
    if x == 0.0:
        return 0.0
    half = 0.5 * x
    term = 0.5 * x
    total = term
    for k in range(1, BESSEL_SERIES_TERMS):
        term *= -(half * half) / (k * (k + 1.0))
        total += term
    return total


def _airy_ee(r_over_r1: float) -> float:
    """ФКЭ диска Эйри: 1 − J0²(x) − J1²(x), x = 3.8317·r/r₁."""
    x = _J1_FIRST_ZERO * r_over_r1
    return 1.0 - _bessel_j0(x) ** 2 - _bessel_j1(x) ** 2


#: Первый нуль J1 = 3.8317059702075125 (радиус диска Эйри 1.2197·λF#).
_J1_FIRST_ZERO = 3.8317059702075125


def _airy_zeros(count: int) -> list:
    """Первые нули J1 (сканирование ряда со сменой знака + бисекция)."""
    zeros = []
    x_hi = 1.0
    step = 0.05
    while len(zeros) < count and x_hi < 60.0:
        x_lo = x_hi
        x_hi += step
        f_lo, f_hi = _bessel_j1(x_lo), _bessel_j1(x_hi)
        if f_lo == 0.0:
            zeros.append(x_lo)
            continue
        if f_lo * f_hi < 0:
            a, b = x_lo, x_hi
            for _ in range(60):
                mid = 0.5 * (a + b)
                if _bessel_j1(a) * _bessel_j1(mid) <= 0:
                    b = mid
                else:
                    a = mid
            zeros.append(0.5 * (a + b))
    return zeros


def _poisson_draw(rng: random.Random, lam: float) -> int:
    """Пуассоновская выборка: алгоритм Кнута (λ < 30) или нормальное
    приближение N(λ, λ) для больших λ."""
    if lam <= 0.0:
        return 0
    if lam < POISSON_NORMAL_THRESHOLD:
        limit = math.exp(-lam)
        prob = 1.0
        count = 0
        while True:
            prob *= rng.random()
            if prob <= limit:
                return count
            count += 1
    return int(max(0.0, round(rng.gauss(lam, math.sqrt(lam)))))


def _edge_rise_width(profile, axis) -> float:
    """Ширина фронта 10–90 % по первому возрастающему перепаду."""
    import numpy as np
    arr = np.asarray(profile, dtype=float)
    low = float(arr.min())
    high = float(arr.max())
    span = high - low
    if span <= 0:
        raise CommandError(ERR_INVALID_PARAM,
                           "профиль вырожден (нет перепада)")
    rising = arr.argmax() > arr.argmin()
    for level in (0.1, 0.9):
        target = low + level * span
        if rising:
            idx = int(np.argmax(arr >= target))
        else:
            idx = int(np.argmax(arr[::-1] >= target))
            idx = len(arr) - 1 - idx
        if level == 0.1:
            x10 = float(axis[idx])
        else:
            x90 = float(axis[idx])
    return abs(x90 - x10)


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать команды adv.* (R500-14)."""

    # ----------------------------------------------------------
    # adv.psf.focus_stack — объёмная ФРТ: срезы-метрики через фокус
    # ----------------------------------------------------------

    @registry.command(
        "adv.psf.focus_stack", category="adv",
        description="Объёмная ФРТ через фокус: сетка дефокуса ±range, в "
                    "каждой плоскости — пик, Штрель, FWHM сечений x/y и "
                    "r₈₀ (опция — центральные срезы профилей)",
        returns="{rows: [{defocus_mm, defocus_waves, peak, strehl, "
                "fwhm_x_um, fwhm_y_um, r80_um}], meta}",
        params=system_source_params([
            Param("defocus_range_mm", type="float",
                  default=FOCUS_RANGE_MM_DEFAULT,
                  help="±мм развёртки дефокуса вокруг плоскости Гаусса"),
            Param("num_points", type="int",
                  default=FOCUS_STACK_POINTS_DEFAULT,
                  help=f"точек сетки (нечётное, ≥{FOCUS_POINTS_MIN}; "
                       f"чётное округляется +1)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("include_slices", type="bool", default=False,
                  help="включить центральные срезы ФРТ по x для каждой "
                       "плоскости"),
        ]))
    def adv_psf_focus_stack(ctx, file, system, lbo_index, lbo_name,
                            defocus_range_mm, num_points, field_y, wl,
                            include_slices):
        import numpy as np
        from analysis.psf_mtf import encircled_energy
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        if defocus_range_mm <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "defocus_range_mm должен быть > 0")
        points = _odd_points(num_points, "num_points")
        waves_per_mm = _defocus_waves_per_mm(sys_obj, wl_eff)
        rows, slices = [], []
        for i in range(points):
            dz = (2.0 * i / (points - 1) - 1.0) * defocus_range_mm
            res = _psf_of(sys_obj, field_y=field_y, wl=wl_eff,
                          defocus=dz * waves_per_mm)
            psf, x_um = res["psf"], res["x_um"]
            center = psf.shape[0] // 2
            r_um, ee = encircled_energy(psf, res["pitch_um"])
            row = {
                "defocus_mm": float(dz),
                "defocus_waves": float(dz * waves_per_mm),
                "peak": float(psf.max()),
                "strehl": float(res["strehl"]),
                "fwhm_x_um": _fwhm_of(psf[center, :], x_um),
                "fwhm_y_um": _fwhm_of(psf[:, center], x_um),
                "r80_um": float(np.interp(0.8, ee, r_um)),
            }
            rows.append(row)
            if include_slices:
                slices.append({"defocus_mm": float(dz),
                               "x_um": x_um.tolist(),
                               "profile_x": psf[center, :].tolist()})
        out = {"wl": wl_eff, "field_y": field_y,
               "defocus_range_mm": defocus_range_mm,
               "num_points": points,
               "waves_per_mm": float(waves_per_mm),
               "rows": rows}
        if include_slices:
            out["slices"] = slices
        return out

    # ----------------------------------------------------------
    # adv.psf.waist — положение перетяжки ФРТ
    # ----------------------------------------------------------

    @registry.command(
        "adv.psf.waist", category="adv",
        description="Перетяжка ФРТ вдоль оси: положение плоскости "
                    "максимального пика (параболическое уточнение), "
                    "осевой FWHM кривой пика и асимметрия полуширин",
        returns="{z_waist_mm, defocus_waves_at_waist, peak_max, "
                "peak_refined, axial_fwhm_mm, half_left_mm, "
                "half_right_mm, strehl_at_waist}",
        params=system_source_params([
            Param("defocus_range_mm", type="float",
                  default=FOCUS_RANGE_MM_DEFAULT,
                  help="±мм развёртки дефокуса"),
            Param("num_points", type="int", default=21,
                  help="точек сетки (нечётное, ≥3)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_psf_waist(ctx, file, system, lbo_index, lbo_name,
                      defocus_range_mm, num_points, field_y, wl):
        import numpy as np
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        points = _odd_points(num_points, "num_points")
        waves_per_mm = _defocus_waves_per_mm(sys_obj, wl_eff)
        z_axis = np.linspace(-defocus_range_mm, defocus_range_mm, points)
        peaks, strehls = [], []
        for dz in z_axis:
            res = _psf_of(sys_obj, field_y=field_y, wl=wl_eff,
                          defocus=dz * waves_per_mm)
            peaks.append(float(res["psf"].max()))
            strehls.append(float(res["strehl"]))
        peaks = np.asarray(peaks)
        i_max = int(np.argmax(peaks))
        peak_max = float(peaks[i_max])
        if 0 < i_max < points - 1:
            dz_step = float(z_axis[1] - z_axis[0])
            refine = _parabolic_vertex(peaks[i_max - 1], peaks[i_max],
                                       peaks[i_max + 1], dz_step)
            denom = (float(peaks[i_max - 1]) - 2.0 * peak_max
                     + float(peaks[i_max + 1]))
            chord = 0.5 * (float(peaks[i_max + 1])
                           - float(peaks[i_max - 1]))
            peak_refined = float(peak_max - chord ** 2 / (2.0 * denom)) \
                if denom != 0 else peak_max
        else:
            refine = 0.0
            peak_refined = peak_max
        z_waist = float(z_axis[i_max] + refine)
        half_level = float(peaks.min() + 0.5 * (peak_max - peaks.min()))
        above = peaks >= half_level
        left = int(np.argmax(above))
        right = len(above) - 1 - int(np.argmax(above[::-1]))
        z_left, z_right = float(z_axis[left]), float(z_axis[right])
        return {
            "wl": wl_eff, "field_y": field_y,
            "defocus_range_mm": defocus_range_mm,
            "num_points": points,
            "z_waist_mm": z_waist,
            "defocus_waves_at_waist": float(z_waist * waves_per_mm),
            "peak_max": peak_max,
            "peak_refined": peak_refined,
            "axial_fwhm_mm": z_right - z_left,
            "half_left_mm": float(z_axis[i_max]) - z_left,
            "half_right_mm": z_right - float(z_axis[i_max]),
            "strehl_at_waist": float(strehls[i_max]),
        }

    # ----------------------------------------------------------
    # adv.psf.fwhm — ширины сечений ФРТ
    # ----------------------------------------------------------

    @registry.command(
        "adv.psf.fwhm", category="adv",
        description="FWHM центральных сечений ФРТ (по x — сагиттальное, "
                    "по y — меридиональное) с сравнением с диском Эйри",
        returns="{fwhm_x_um, fwhm_y_um, airy_diameter_um, ratio_x, "
                "ratio_y}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def adv_psf_fwhm(ctx, file, system, lbo_index, lbo_name,
                     field_y, wl, defocus):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        psf, x_um = res["psf"], res["x_um"]
        center = psf.shape[0] // 2
        fwhm_x = _fwhm_of(psf[center, :], x_um)
        fwhm_y = _fwhm_of(psf[:, center], x_um)
        airy_d = 2.0 * AIRY_FACTOR * res["wl"] * (res["f_number"] or 1.0)
        return {"wl": res["wl"], "field_y": field_y,
                "defocus": defocus, "pitch_um": res["pitch_um"],
                "fwhm_x_um": fwhm_x, "fwhm_y_um": fwhm_y,
                "airy_diameter_um": float(airy_d),
                "ratio_x": float(fwhm_x / airy_d),
                "ratio_y": float(fwhm_y / airy_d)}

    # ----------------------------------------------------------
    # adv.psf.centroid — энергетический центр ФРТ по полям
    # ----------------------------------------------------------

    @registry.command(
        "adv.psf.centroid", category="adv",
        description="Энергетический центр (центроид) ФРТ по полям: "
                    "смещение от опорной оси поля (искажение-like "
                    "метрика дифракционного пятна)",
        returns="{rows: [{field, centroid_x_um, centroid_y_um, "
                "shift_um}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="поля (град); по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_psf_centroid(ctx, file, system, lbo_index, lbo_name,
                         fields, wl):
        import numpy as np
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            res = _psf_of(sys_obj, field_y=field, wl=wl_eff)
            psf = res["psf"]
            total = float(psf.sum())
            if total <= 0:
                raise CommandError(ERR_INVALID_PARAM,
                                   f"поле {field}: пустая ФРТ")
            gy, gx = np.meshgrid(res["y_um"], res["x_um"],
                                 indexing="ij")
            cx = float((psf * gx).sum() / total)
            cy = float((psf * gy).sum() / total)
            rows.append({"field": float(field),
                         "centroid_x_um": cx, "centroid_y_um": cy,
                         "shift_um": float(math.hypot(cx, cy))})
        return {"wl": wl_eff, "rows": rows}

    # ----------------------------------------------------------
    # adv.psf.poly — полихроматическая ФРТ
    # ----------------------------------------------------------

    @registry.command(
        "adv.psf.poly", category="adv",
        description="Полихроматическая ФРТ: некогерентная взвешенная "
                    "сумма монохромных ФРТ по λ системы (или явному "
                    "спектру) на общей координатной сетке",
        returns="{spectral: [{wl, weight, pitch_um}], peak, fwhm_x_um, "
                "fwhm_y_um, r50_um, r80_um (+psf при include_grid)}",
        params=system_source_params([
            Param("wl_list", type="list",
                  help="явный спектр λ, мкм (по умолчанию — λ системы)"),
            Param("weights", type="list",
                  help="веса λ (по умолчанию — веса λ системы или 1)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("include_grid", type="bool", default=False,
                  help="включить решётку psf (Σ=1) и оси"),
        ]))
    def adv_psf_poly(ctx, file, system, lbo_index, lbo_name,
                     wl_list, weights, field_y, include_grid):
        import numpy as np
        from analysis.psf_mtf import encircled_energy
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        lambdas, wls = _weighted_spectrum(sys_obj, wl_list, weights)
        combined = None
        spectral = []
        for wl_i, weight in zip(lambdas, wls):
            res = _psf_of(sys_obj, field_y=field_y, wl=wl_i)
            spectral.append({"wl": float(wl_i), "weight": float(weight),
                             "pitch_um": float(res["pitch_um"])})
            if combined is None:
                ref = res
                combined = weight * res["psf"]
            else:
                combined = combined + weight * _resample_regular(
                    res["psf"], res["x_um"], res["y_um"],
                    ref["x_um"], ref["y_um"])
        total = float(combined.sum())
        if total <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "полихромная ФРТ пуста")
        combined = combined / total
        center = combined.shape[0] // 2
        r_um, ee = encircled_energy(combined, ref["pitch_um"])
        out = {
            "field_y": field_y, "num_wavelengths": len(lambdas),
            "spectral": spectral,
            "peak": float(combined.max()),
            "fwhm_x_um": _fwhm_of(combined[center, :], ref["x_um"]),
            "fwhm_y_um": _fwhm_of(combined[:, center], ref["x_um"]),
            "r50_um": float(np.interp(0.5, ee, r_um)),
            "r80_um": float(np.interp(0.8, ee, r_um)),
        }
        if include_grid:
            out["psf"] = combined.tolist()
            out["x_um"] = ref["x_um"].tolist()
            out["y_um"] = ref["y_um"].tolist()
            out["pitch_um"] = float(ref["pitch_um"])
        return out

    # ----------------------------------------------------------
    # adv.lsf.poly — полихроматическая ФРЛ
    # ----------------------------------------------------------

    @registry.command(
        "adv.lsf.poly", category="adv",
        description="Полихроматическая ФРЛ: взвешенная сумма профилей "
                    "ФРЛ по λ на общей оси (меридиональное и "
                    "сагиттальное сечения)",
        returns="{coord_um, meridional, sagittal, spectral}",
        params=system_source_params([
            Param("wl_list", type="list",
                  help="явный спектр λ, мкм (по умолчанию — λ системы)"),
            Param("weights", type="list",
                  help="веса λ (по умолчанию — веса λ системы или 1)"),
            Param("field_y", type="float", default=0.0, help="поле"),
        ]))
    def adv_lsf_poly(ctx, file, system, lbo_index, lbo_name,
                     wl_list, weights, field_y):
        import numpy as np
        from analysis.psf_mtf import lsf_from_psf
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        lambdas, wls = _weighted_spectrum(sys_obj, wl_list, weights)
        mer = sag = None
        spectral = []
        for wl_i, weight in zip(lambdas, wls):
            res = _psf_of(sys_obj, field_y=field_y, wl=wl_i)
            lsf = lsf_from_psf(res["psf"], res["pitch_um"])
            coord = lsf["coord_um"]
            spectral.append({"wl": float(wl_i), "weight": float(weight)})
            if mer is None:
                axis = np.asarray(coord, dtype=float)
                mer = weight * np.asarray(lsf["x"], dtype=float)
                sag = weight * np.asarray(lsf["y"], dtype=float)
            else:
                mer = mer + weight * np.interp(axis, coord,
                                               lsf["x"], left=0.0,
                                               right=0.0)
                sag = sag + weight * np.interp(axis, coord,
                                               lsf["y"], left=0.0,
                                               right=0.0)
        for profile in (mer, sag):
            total = float(profile.sum())
            if total > 0:
                profile /= total
        return {"field_y": field_y, "num_wavelengths": len(lambdas),
                "spectral": spectral, "coord_um": axis.tolist(),
                "meridional": mer.tolist(), "sagittal": sag.tolist()}

    # ----------------------------------------------------------
    # adv.slit_image — изображение щели конечной ширины
    # ----------------------------------------------------------

    @registry.command(
        "adv.slit_image", category="adv",
        description="Изображение щели конечной ширины: 2D-свёртка "
                    "идеальной щели с дифракционной ФРТ (линия/край/"
                    "точка — adv.object_image; здесь — конечная щель)",
        returns="{width_um, along, contrast, edge_10_90_um, "
                "min/max профиля (+x/y/ideal/image при include_grid)}",
        params=system_source_params([
            Param("width_um", type="float", required=True,
                  help="ширина щели, мкм (> 0)"),
            Param("along", choices=list(SLIT_AXES), default="x",
                  help="ось, вдоль которой вытянута щель"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
            Param("include_grid", type="bool", default=False,
                  help="включить решётки x/y/ideal/image"),
        ]))
    def adv_slit_image(ctx, file, system, lbo_index, lbo_name,
                       width_um, along, field_y, wl, defocus,
                       include_grid):
        import numpy as np
        from analysis.advanced import convolve_fft
        if width_um <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "width_um должен быть > 0")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        psf, x_um, y_um = res["psf"], res["x_um"], res["y_um"]
        if along == "x":
            # щель вдоль X: ярко при |y| < w/2; сечение поперёк — по y
            ideal = (np.abs(y_um) < 0.5 * width_um)[:, None] \
                * np.ones((1, len(x_um)))
            profile_axis = y_um
        else:
            ideal = (np.abs(x_um) < 0.5 * width_um)[None, :] \
                * np.ones((len(y_um), 1))
            profile_axis = x_um
        kernel = psf / psf.sum()
        pad = psf.shape[0] // 2
        padded = np.pad(ideal, pad, mode="edge")
        conv = convolve_fft(padded, kernel)
        image = conv[pad:pad + psf.shape[0], pad:pad + psf.shape[0]]
        center_row = image[:, image.shape[1] // 2] if along == "x" \
            else image[image.shape[0] // 2, :]
        imax, imin = float(center_row.max()), float(center_row.min())
        contrast = ((imax - imin) / (imax + imin)
                    if (imax + imin) > 0 else 0.0)
        out = {
            "wl": res["wl"], "field_y": field_y, "defocus": defocus,
            "width_um": float(width_um), "along": along,
            "contrast": float(contrast),
            "edge_10_90_um": float(_edge_rise_width(
                center_row, profile_axis)),
            "profile_min": imin, "profile_max": imax,
        }
        if include_grid:
            out.update({"x_um": x_um.tolist(), "y_um": y_um.tolist(),
                        "ideal": ideal.tolist(),
                        "image": image.tolist()})
        return out

    # ----------------------------------------------------------
    # adv.convolve.profile — свёртка профиля объекта с ФРЛ
    # ----------------------------------------------------------

    @registry.command(
        "adv.convolve.profile", category="adv",
        description="Отклик системы на произвольный одномерный профиль "
                    "объекта: линейная свёртка с ФРЛ выбранного сечения "
                    "(моделирование отклика на произвольный объект)",
        returns="{coord_um, object, image, contrast}",
        params=system_source_params([
            Param("profile", type="list", required=True,
                  help="профиль объекта [I0, I1, ...], ≥2 значений"),
            Param("pitch_um", type="float", required=True,
                  help="шаг профиля, мкм (> 0)"),
            Param("section", choices=list(LSF_SECTIONS),
                  default="tangential",
                  help="сечения ФРЛ: tangential — LSF(x), "
                       "sagittal — LSF(y)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_convolve_profile(ctx, file, system, lbo_index, lbo_name,
                             profile, pitch_um, section, field_y, wl):
        import numpy as np
        from analysis.psf_mtf import lsf_from_psf
        values = _parse_number_list(profile, "profile")
        if len(values) < 2:
            raise CommandError(ERR_INVALID_PARAM,
                               "profile: нужно ≥2 значений")
        if pitch_um <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "pitch_um должен быть > 0")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl)
        lsf = lsf_from_psf(res["psf"], res["pitch_um"])
        key = "x" if section == "tangential" else "y"
        lsf_axis = np.asarray(lsf["coord_um"], dtype=float)
        axis = (np.arange(len(values))
                - (len(values) - 1) / 2.0) * pitch_um
        kernel = np.interp(axis, lsf_axis, lsf[key], left=0.0,
                           right=0.0)
        total = float(kernel.sum())
        if total <= 0:
            raise CommandError(
                ERR_INVALID_PARAM,
                "ФРЛ не покрывает диапазон профиля — увеличьте "
                "pitch_um или число точек")
        kernel = kernel / total
        image = pitch_um * np.convolve(values, kernel, mode="same")
        imax, imin = float(image.max()), float(image.min())
        return {"wl": res["wl"], "field_y": field_y,
                "section": section, "pitch_um": float(pitch_um),
                "coord_um": axis.tolist(),
                "object": values, "image": image.tolist(),
                "contrast": float((imax - imin) / (imax + imin))
                if (imax + imin) > 0 else 0.0}

    # ----------------------------------------------------------
    # adv.usaf.table — таблица частот СШАФ-1951
    # ----------------------------------------------------------

    @registry.command(
        "adv.usaf.table", category="adv",
        description="Таблица миры СШАФ-1951: частота элемента "
                    "ν = 2^(G+(E−1)/6) лин/мм, период и ширина штриха "
                    "(справочник, без системы)",
        returns="{rows: [{group, element, freq_lpmm, period_um, "
                "bar_width_um}], base_freq_lpmm}",
        params=[
            Param("group_from", type="int", default=0,
                  help="начальная группа (номер группы миры)"),
            Param("group_to", type="int", default=5,
                  help="конечная группа включительно"),
            Param("freq_max_lpmm", type="float",
                  help="обрезать таблицу по частоте, лин/мм"),
        ])
    def adv_usaf_table(ctx, group_from, group_to, freq_max_lpmm):
        if group_to < group_from:
            raise CommandError(
                ERR_INVALID_PARAM,
                "group_to должен быть ≥ group_from")
        rows = []
        for group in range(group_from, group_to + 1):
            for element in USAF_ELEMENTS:
                freq = USAF_BASE_FREQ_LPMM * (
                    2.0 ** (group + (element - 1) / 6.0))
                if freq_max_lpmm is not None and freq > freq_max_lpmm:
                    continue
                rows.append({
                    "group": group, "element": element,
                    "freq_lpmm": float(freq),
                    "period_um": float(1000.0 / freq),
                    "bar_width_um": float(500.0 / freq),
                })
        if not rows:
            raise CommandError(ERR_INVALID_PARAM,
                               "таблица пуста: проверьте диапазон групп "
                               "и freq_max_lpmm")
        return {"base_freq_lpmm": USAF_BASE_FREQ_LPMM,
                "element_ratio": USAF_ELEMENT_RATIO,
                "rows": rows}

    # ----------------------------------------------------------
    # adv.usaf.resolve — разрешимый элемент по ЧКХ
    # ----------------------------------------------------------

    @registry.command(
        "adv.usaf.resolve", category="adv",
        description="Разрешимый элемент миры СШАФ-1951 по сечениям ЧКХ: "
                    "наиболее мелкий элемент с ЧКХ (танг. и саг.) не "
                    "ниже порога, с учётом предела Найквиста",
        returns="{group, element, freq_lpmm, bar_width_um, mtf_tan, "
                "mtf_sag, limiting, nyquist_lpmm, cutoff_lpmm, "
                "limited_by}",
        params=system_source_params([
            Param("threshold", type="float",
                  default=MTF_THRESHOLD_DEFAULT,
                  help="порог ЧКХ (доли единицы, > 0)"),
            Param("group_from", type="int", default=0,
                  help="начальная группа поиска"),
            Param("group_to", type="int", default=7,
                  help="конечная группа поиска"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_usaf_resolve(ctx, file, system, lbo_index, lbo_name,
                         threshold, group_from, group_to, field_y, wl):
        import numpy as np
        from analysis.psf_mtf import mtf_from_psf
        if threshold <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "threshold должен быть > 0")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl)
        mtf = mtf_from_psf(res["psf"], res["pitch_um"])
        freqs = mtf["freq_lpmm"]
        best = None
        for group in range(group_from, group_to + 1):
            for element in USAF_ELEMENTS:
                freq = USAF_BASE_FREQ_LPMM * (
                    2.0 ** (group + (element - 1) / 6.0))
                if freq > float(mtf["nyquist_lpmm"]):
                    out = {
                        "wl": res["wl"], "field_y": field_y,
                        "threshold": threshold,
                        "nyquist_lpmm": float(mtf["nyquist_lpmm"]),
                        "cutoff_lpmm": float(res["cutoff_lpmm"]),
                        "limited_by": "nyquist",
                    }
                    if best is not None:
                        out.update(best)
                        out["limited_by"] = "nyquist"
                        return out
                    out.update({"group": None, "element": None,
                                "freq_lpmm": None,
                                "bar_width_um": None,
                                "mtf_tan": None, "mtf_sag": None,
                                "limiting": None})
                    return out
                mtf_t = float(np.interp(freq, freqs, mtf["tan"]))
                mtf_s = float(np.interp(freq, freqs, mtf["sag"]))
                if min(mtf_t, mtf_s) < threshold:
                    out = {
                        "wl": res["wl"], "field_y": field_y,
                        "threshold": threshold,
                        "nyquist_lpmm": float(mtf["nyquist_lpmm"]),
                        "cutoff_lpmm": float(res["cutoff_lpmm"]),
                        "limited_by": "mtf",
                    }
                    if best is not None:
                        out.update(best)
                        return out
                    out.update({"group": None, "element": None,
                                "freq_lpmm": None,
                                "bar_width_um": None,
                                "mtf_tan": None, "mtf_sag": None,
                                "limiting": None})
                    return out
                best = {
                    "group": group, "element": element,
                    "freq_lpmm": float(freq),
                    "bar_width_um": float(500.0 / freq),
                    "mtf_tan": mtf_t, "mtf_sag": mtf_s,
                    "limiting": ("tangential" if mtf_t <= mtf_s
                                 else "sagittal"),
                }
        if best is None:
            raise CommandError(
                ERR_INVALID_PARAM,
                "диапазон групп пуст: проверьте group_from/group_to")
        out = {"wl": res["wl"], "field_y": field_y,
               "threshold": threshold,
               "nyquist_lpmm": float(mtf["nyquist_lpmm"]),
               "cutoff_lpmm": float(res["cutoff_lpmm"]),
               "limited_by": "table_end"}
        out.update(best)
        return out

    # ----------------------------------------------------------
    # adv.usaf.object — ширины штрихов на предмете
    # ----------------------------------------------------------

    @registry.command(
        "adv.usaf.object", category="adv",
        description="Ширина штриха элемента миры СШАФ-1951 на плоскости "
                    "предмета: частота/ширина в изображении → через "
                    "увеличение (для INFINITE — угловой масштаб ν·f′)",
        returns="{group, element, freq_image_lpmm, bar_width_image_um, "
                "magnification, freq_object_lpmm, "
                "bar_width_object_um, angular_lp_per_mrad}",
        params=system_source_params([
            Param("group", type="int", required=True,
                  help="номер группы миры"),
            Param("element", type="int", required=True,
                  help="номер элемента в группе (1..6)"),
        ]))
    def adv_usaf_object(ctx, file, system, lbo_index, lbo_name,
                        group, element):
        from optics_engine import paraxial_trace
        if element not in USAF_ELEMENTS:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"element должен быть одним из {list(USAF_ELEMENTS)}")
        freq = USAF_BASE_FREQ_LPMM * (
            2.0 ** (group + (element - 1) / 6.0))
        bar_image_um = 500.0 / freq
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        parax = paraxial_trace(sys_obj)
        magnification = float(parax.get("magnification", 0.0) or 0.0)
        efl = abs(float(parax.get("focal_length", 0.0) or 0.0))
        out = {
            "group": group, "element": element,
            "freq_image_lpmm": float(freq),
            "bar_width_image_um": float(bar_image_um),
            "magnification": magnification,
            "efl_mm": efl,
            # угловой масштаб: ν_изобр·f′ = лин/мрад (для дальнего
            # предмета частота на предмете угловая)
            "angular_lp_per_mrad": float(freq * efl / 1000.0),
        }
        if abs(magnification) > 0:
            out["freq_object_lpmm"] = float(freq * abs(magnification))
            out["bar_width_object_um"] = float(
                bar_image_um / abs(magnification))
        else:
            out["freq_object_lpmm"] = None
            out["bar_width_object_um"] = None
        return out

    # ----------------------------------------------------------
    # adv.dof.diffraction — дифракционная глубина фокуса
    # ----------------------------------------------------------

    @registry.command(
        "adv.dof.diffraction", category="adv",
        description="Дифракционная глубина фокуса (критерий Рэлея λ/4 "
                    "OPD): ±2·λ·F#² по каждой λ системы + диск Эйри",
        returns="{f_number, rows: [{wl, dof_half_mm, dof_full_mm, "
                "airy_radius_um}]}",
        params=system_source_params([
            Param("wl_list", type="list",
                  help="явный список λ, мкм (по умолчанию — λ системы)"),
        ]))
    def adv_dof_diffraction(ctx, file, system, lbo_index, lbo_name,
                            wl_list):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        from optics_engine import paraxial_trace
        parax = paraxial_trace(sys_obj)
        efl = abs(float(parax.get("focal_length", 0.0) or 0.0))
        aperture = get_effective_aperture(sys_obj, default=10.0)
        if efl <= 0 or aperture <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "система без f′/апертуры — ГРФ не "
                               "определена")
        f_number = efl / aperture
        lambdas = (_parse_number_list(wl_list, "wl_list")
                   if wl_list is not None else _wls_arg(sys_obj))
        rows = []
        for wl_i in lambdas:
            dof_half_mm = (RAYLEIGH_DOF_COEFF * (wl_i * 1e-3)
                           * f_number ** 2)
            rows.append({
                "wl": float(wl_i),
                "dof_half_mm": float(dof_half_mm),
                "dof_full_mm": float(2.0 * dof_half_mm),
                "airy_radius_um": float(AIRY_FACTOR * wl_i * f_number),
            })
        return {"f_number": f_number, "efl_mm": efl,
                "aperture_mm": aperture, "rows": rows}

    # ----------------------------------------------------------
    # adv.dof.compare — дифракционная vs геометрическая по полям
    # ----------------------------------------------------------

    @registry.command(
        "adv.dof.compare", category="adv",
        description="Глубина фокуса по полям: дифракционная ±2λF#² vs "
                    "геометрическая (RMS пятна / NA′ — дефокус, при "
                    "котором размытие от дефокуса равно аберрационному), "
                    "доминирующий режим",
        returns="{rows: [{field, rms_spot_mm, na_image, "
                "dof_geo_half_mm, dof_diff_half_mm, ratio, regime}]}",
        params=system_source_params([
            Param("fields", type="list",
                  help="поля (град); по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("num_rays", type="int", default=DOF_SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка точечной диаграммы"),
        ]))
    def adv_dof_compare(ctx, file, system, lbo_index, lbo_name,
                        fields, wl, num_rays):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        from optics_engine import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        parax = paraxial_trace(sys_obj)
        efl = abs(float(parax.get("focal_length", 0.0) or 0.0))
        aperture = get_effective_aperture(sys_obj, default=10.0)
        if efl <= 0 or aperture <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "система без f′/апертуры")
        f_number = efl / aperture
        na_img = aperture / (2.0 * efl)
        dof_diff_half = (RAYLEIGH_DOF_COEFF * (wl_eff * 1e-3)
                         * f_number ** 2)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            spots = compute_spot_diagram(sys_obj, wl=wl_eff,
                                         num_rays=num_rays,
                                         field_y=field)
            rms_mm = compute_rms_spot(spots)
            dof_geo_half = rms_mm / na_img if na_img > 0 else None
            ratio = (dof_geo_half / dof_diff_half
                     if dof_geo_half is not None and dof_diff_half > 0
                     else None)
            rows.append({
                "field": float(field),
                "rms_spot_mm": float(rms_mm),
                "na_image": float(na_img),
                "dof_geo_half_mm": (float(dof_geo_half)
                                    if dof_geo_half is not None
                                    else None),
                "dof_diff_half_mm": float(dof_diff_half),
                "ratio_geo_over_diff": (float(ratio)
                                        if ratio is not None else None),
                "regime": ("геометрия" if ratio is not None
                           and ratio < 1.0 else "дифракция"),
            })
        return {"wl": wl_eff, "f_number": f_number,
                "dof_diff_half_mm": float(dof_diff_half), "rows": rows}

    # ----------------------------------------------------------
    # adv.snr.bars — SNR/контраст штрихов через ЧКХ
    # ----------------------------------------------------------

    @registry.command(
        "adv.snr.bars", category="adv",
        description="SNR измерения контраста штрихов через ЧКХ: "
                    "SNR = 2C·N̄/√(2(N̄+σ_r²)), C = MTF(ν) сечения "
                    "(танг./саг.), N̄ — средний сигнал на пиксель",
        returns="{freq_lpmm, mtf_tan, mtf_sag, contrast, snr_tan, "
                "snr_sag, snr_min, verdict_tan, verdict_sag}",
        params=system_source_params([
            Param("freq_lpmm", type="float", required=True,
                  help="частота штрихов, лин/мм (> 0)"),
            Param("signal_e", type="float", default=SIGNAL_E_DEFAULT,
                  help="средний сигнал, электроны на пиксель (> 0)"),
            Param("read_noise_e", type="float",
                  default=READ_NOISE_E_DEFAULT,
                  help="шум чтения, электроны RMS (≥ 0)"),
            Param("snr_min", type="float", default=3.0,
                  help="порог пригодности SNR"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_snr_bars(ctx, file, system, lbo_index, lbo_name,
                     freq_lpmm, signal_e, read_noise_e, snr_min,
                     field_y, wl):
        import numpy as np
        from analysis.psf_mtf import mtf_from_psf
        if freq_lpmm <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "freq_lpmm должен быть > 0")
        if signal_e <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "signal_e должен быть > 0")
        if read_noise_e < 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "read_noise_e должен быть ≥ 0")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl)
        mtf = mtf_from_psf(res["psf"], res["pitch_um"])
        freqs = mtf["freq_lpmm"]
        if freq_lpmm > float(freqs[-1]):
            raise CommandError(
                ERR_INVALID_PARAM,
                f"freq_lpmm={freq_lpmm} вне диапазона ЧКХ "
                f"(до {float(freqs[-1]):.1f} лин/мм)")
        mtf_t = float(np.interp(freq_lpmm, freqs, mtf["tan"]))
        mtf_s = float(np.interp(freq_lpmm, freqs, mtf["sag"]))
        noise = math.sqrt(2.0 * (signal_e + read_noise_e ** 2))

        def _snr(contrast):
            return 2.0 * contrast * signal_e / noise

        snr_t, snr_s = _snr(mtf_t), _snr(mtf_s)
        return {
            "wl": res["wl"], "field_y": field_y,
            "freq_lpmm": float(freq_lpmm),
            "signal_e": float(signal_e),
            "read_noise_e": float(read_noise_e),
            "mtf_tan": mtf_t, "mtf_sag": mtf_s,
            "contrast_used": float(min(mtf_t, mtf_s)),
            "snr_tan": float(snr_t), "snr_sag": float(snr_s),
            "snr_min": float(snr_min),
            "verdict_tan": "ok" if snr_t >= snr_min else "fail",
            "verdict_sag": "ok" if snr_s >= snr_min else "fail",
        }

    # ----------------------------------------------------------
    # adv.noise.spot — шум детектора на пятне (детерминированный seed)
    # ----------------------------------------------------------

    @registry.command(
        "adv.noise.spot", category="adv",
        description="Наложение шума детектора на пятно: пиксельная "
                    "матрица ФРТ × электроны + пуассоновский дробовой "
                    "шум + гауссов шум чтения; генератор "
                    "random.Random(seed) — результат воспроизводим",
        returns="{seed, matrix: [[e-]], peak_e, background_std_e, "
                "snr, meta}",
        params=system_source_params([
            Param("pixel_um", type="float", required=True,
                  help="шаг пиксельной решётки, мкм (> 0)"),
            Param("size", type="int", default=PIXEL_MATRIX_SIZE_DEFAULT,
                  help="окно матрицы (нечётное число пикселей)"),
            Param("peak_e", type="float", default=SIGNAL_E_DEFAULT,
                  help="электроны в центральном пикселе пятна (> 0)"),
            Param("read_noise_e", type="float",
                  default=READ_NOISE_E_DEFAULT,
                  help="шум чтения, электроны RMS (≥ 0)"),
            Param("dark_e", type="float", default=0.0,
                  help="темновой сигнал на пиксель, электроны (≥ 0)"),
            Param("seed", type="int", default=NOISE_SEED_DEFAULT,
                  help="seed генератора (детерминизм)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_noise_spot(ctx, file, system, lbo_index, lbo_name,
                       pixel_um, size, peak_e, read_noise_e, dark_e,
                       seed, field_y, wl):
        import numpy as np
        if peak_e <= 0:
            raise CommandError(ERR_INVALID_PARAM, "peak_e должен быть > 0")
        if read_noise_e < 0 or dark_e < 0:
            raise CommandError(
                ERR_INVALID_PARAM,
                "read_noise_e/dark_e должны быть ≥ 0")
        if size < 1:
            raise CommandError(ERR_INVALID_PARAM, "size должен быть ≥ 1")
        size = size if size % 2 == 1 else size + 1
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl)
        matrix, _, pitch, fine = _pixelate(
            res["psf"], res["x_um"], res["y_um"], pixel_um, size)
        rng = random.Random(seed)
        peak_fraction = float(matrix.max())
        if peak_fraction <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "пиксельная матрица пуста")
        scale_e = peak_e / peak_fraction
        expected = matrix * scale_e + dark_e
        noisy = np.empty_like(expected)
        for i in range(expected.shape[0]):
            for j in range(expected.shape[1]):
                value = _poisson_draw(rng, float(expected[i, j]))
                if read_noise_e > 0:
                    value += rng.gauss(0.0, read_noise_e)
                noisy[i, j] = value
        quiet = expected < QUIET_FRACTION * expected.max()
        background_std = float(noisy[quiet].std()) if quiet.any() \
            else float(noisy.std())
        peak_signal = float(noisy.max())
        snr = (float(peak_signal / background_std)
               if background_std > 0 else None)
        return {
            "seed": int(seed), "pixel_um": float(pixel_um),
            "size": int(size), "peak_e": float(peak_e),
            "read_noise_e": float(read_noise_e),
            "dark_e": float(dark_e),
            "wl": res["wl"], "field_y": field_y,
            "psf_pitch_um": float(pitch),
            "fine_step_um": float(fine),
            "matrix": noisy.tolist(),
            "peak_signal_e": peak_signal,
            "background_std_e": background_std,
            "snr": snr,
        }

    # ----------------------------------------------------------
    # adv.pixel.matrix — пиксельная матрица пятна
    # ----------------------------------------------------------

    @registry.command(
        "adv.pixel.matrix", category="adv",
        description="Пиксельная матрица пятна: интегрирование ФРТ по "
                    "пикселям заданного шага с подпиксельной "
                    "передискретизацией — доли энергии в пикселях окна",
        returns="{pixel_um, size, subsample, matrix [[fraction]], "
                "central_fraction, max_fraction, sum_in_window, "
                "psf_pitch_um}",
        params=system_source_params([
            Param("pixel_um", type="float", required=True,
                  help="шаг пикселя, мкм (> 0)"),
            Param("size", type="int", default=PIXEL_MATRIX_SIZE_DEFAULT,
                  help="окно матрицы, пикселей (нечётное)"),
            Param("subsample", type="int",
                  default=PIXEL_SUBSAMPLE_DEFAULT,
                  help="подпиксельная кратность передискретизации ФРТ"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def adv_pixel_matrix(ctx, file, system, lbo_index, lbo_name,
                         pixel_um, size, subsample, field_y, wl,
                         defocus):
        if size < 1:
            raise CommandError(ERR_INVALID_PARAM,
                               "size должен быть ≥ 1")
        size = size if size % 2 == 1 else size + 1
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        matrix, in_window, pitch, fine = _pixelate(
            res["psf"], res["x_um"], res["y_um"], pixel_um, size,
            subsample=subsample)
        center = size // 2
        return {
            "wl": res["wl"], "field_y": field_y, "defocus": defocus,
            "pixel_um": float(pixel_um), "size": int(size),
            "subsample": int(subsample),
            "psf_pitch_um": float(pitch),
            "fine_step_um": float(fine),
            "matrix": matrix.tolist(),
            "central_fraction": float(matrix[center, center]),
            "max_fraction": float(matrix.max()),
            "sum_in_window": float(in_window),
        }

    # ----------------------------------------------------------
    # adv.pixel.energy — энергия в пикселе/блоке
    # ----------------------------------------------------------

    @registry.command(
        "adv.pixel.energy", category="adv",
        description="Энергия фотоприёмника в пикселе: доля ФРТ в "
                    "пикселе с заданным смещением от центра пятна и в "
                    "блоке N×N вокруг него (сумма блока ≤ 1)",
        returns="{pixel_um, offset_x_um, offset_y_um, block, "
                "pixel_fraction, block_fraction}",
        params=system_source_params([
            Param("pixel_um", type="float", required=True,
                  help="шаг пикселя, мкм (> 0)"),
            Param("offset_x_um", type="float", default=0.0,
                  help="смещение центра пикселя по x, мкм"),
            Param("offset_y_um", type="float", default=0.0,
                  help="смещение центра пикселя по y, мкм"),
            Param("block", type="int", default=1,
                  help="блок block×block пикселей вокруг точки (неч.)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_pixel_energy(ctx, file, system, lbo_index, lbo_name,
                         pixel_um, offset_x_um, offset_y_um, block,
                         field_y, wl):
        import numpy as np
        if block < 1:
            raise CommandError(ERR_INVALID_PARAM, "block должен быть ≥ 1")
        block = block if block % 2 == 1 else block + 1
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl)
        # одиночный пиксель — блок 1×1 с данным смещением
        single, _, _, _ = _pixelate(
            res["psf"], res["x_um"], res["y_um"], pixel_um, 1,
            offset_x_um=offset_x_um, offset_y_um=offset_y_um)
        pixel_fraction = float(single[0, 0])
        if block == 1:
            block_fraction = pixel_fraction
        else:
            matrix, _, _, _ = _pixelate(
                res["psf"], res["x_um"], res["y_um"], pixel_um, block,
                offset_x_um=offset_x_um, offset_y_um=offset_y_um)
            block_fraction = float(matrix.sum())
        return {"wl": res["wl"], "field_y": field_y,
                "pixel_um": float(pixel_um),
                "offset_x_um": float(offset_x_um),
                "offset_y_um": float(offset_y_um),
                "block": int(block),
                "pixel_fraction": pixel_fraction,
                "block_fraction": float(block_fraction)}

    # ----------------------------------------------------------
    # adv.energy.ring — энергия в кольце фотоприёмника
    # ----------------------------------------------------------

    @registry.command(
        "adv.energy.ring", category="adv",
        description="Энергия в кольце фотоприёмника: ФКЭ(r₂) − ФКЭ(r₁) "
                    "от энергетического центра ФРТ (доля полной "
                    "энергии)",
        returns="{r_inner_um, r_outer_um, ee_inner, ee_outer, fraction}",
        params=system_source_params([
            Param("r_inner_um", type="float", required=True,
                  help="внутренний радиус кольца, мкм (≥ 0)"),
            Param("r_outer_um", type="float", required=True,
                  help="внешний радиус кольца, мкм (> внутреннего)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def adv_energy_ring(ctx, file, system, lbo_index, lbo_name,
                        r_inner_um, r_outer_um, field_y, wl, defocus):
        import numpy as np
        from analysis.psf_mtf import encircled_energy
        if r_inner_um < 0 or r_outer_um <= r_inner_um:
            raise CommandError(
                ERR_INVALID_PARAM,
                "нужно 0 ≤ r_inner_um < r_outer_um")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl,
                      defocus=defocus)
        r_um, ee = encircled_energy(res["psf"], res["pitch_um"])
        ee_in = float(np.interp(r_inner_um, r_um, ee))
        ee_out = float(np.interp(r_outer_um, r_um, ee))
        return {"wl": res["wl"], "field_y": field_y,
                "defocus": defocus,
                "r_inner_um": float(r_inner_um),
                "r_outer_um": float(r_outer_um),
                "ee_inner": ee_in, "ee_outer": ee_out,
                "fraction": float(ee_out - ee_in)}

    # ----------------------------------------------------------
    # adv.resolve.thornber — разрешение по сечениям ЧКХ
    # ----------------------------------------------------------

    @registry.command(
        "adv.resolve.thornber", category="adv",
        description="Критерий Торнбера — разрешение по сечениям ЧКХ: "
                    "частота, где ХУДШЕЕ из тангенциального/сагиттального "
                    "сечений пересекает порог; дополнительно частота "
                    "пересечения ветвей (астигматический баланс)",
        returns="{threshold, rows: [{field, freq_tan_lpmm, "
                "freq_sag_lpmm, freq_resolved_lpmm, limiting, "
                "crossover_lpmm, astig_gap}]}",
        params=system_source_params([
            Param("threshold", type="float",
                  default=MTF_THRESHOLD_DEFAULT,
                  help="порог ЧКХ (доли единицы, > 0)"),
            Param("fields", type="list",
                  help="поля (град); по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_resolve_thornber(ctx, file, system, lbo_index, lbo_name,
                             threshold, fields, wl):
        import numpy as np
        from analysis.psf_mtf import mtf_from_psf
        if threshold <= 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "threshold должен быть > 0")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _resolve_wl(sys_obj, wl)
        rows = []
        for field in _fields_arg(sys_obj, fields):
            res = _psf_of(sys_obj, field_y=field, wl=wl_eff)
            mtf = mtf_from_psf(res["psf"], res["pitch_um"])
            freqs = np.asarray(mtf["freq_lpmm"], dtype=float)
            tan = np.asarray(mtf["tan"], dtype=float)
            sag = np.asarray(mtf["sag"], dtype=float)
            freq_t = _threshold_crossing(freqs, tan, threshold)
            freq_s = _threshold_crossing(freqs, sag, threshold)
            if freq_t is None or freq_s is None:
                resolved = None
                limiting = None
            else:
                resolved = min(freq_t, freq_s)
                limiting = ("tangential" if freq_t <= freq_s
                            else "sagittal")
            gap = np.abs(tan - sag)[1:]
            rows.append({
                "field": float(field),
                "freq_tan_lpmm": freq_t, "freq_sag_lpmm": freq_s,
                "freq_resolved_lpmm": resolved,
                "bar_width_um": (float(500.0 / resolved)
                                 if resolved else None),
                "limiting": limiting,
                "crossover_lpmm": float(freqs[1:][int(np.argmin(gap))]),
                "astig_gap": float(np.mean(gap)),
                "cutoff_lpmm": float(res["cutoff_lpmm"]),
            })
        return {"wl": wl_eff, "threshold": threshold, "rows": rows}

    # ----------------------------------------------------------
    # adv.otf.complex — комплексная ОТФ (Re/Im/фаза сечений)
    # ----------------------------------------------------------

    @registry.command(
        "adv.otf.complex", category="adv",
        description="Комплексная ОТФ из FFT ФРТ (psf_grid-маршрут, с "
                    "полем и экранированием): сечения Re/Im/фаза "
                    "тангенциальное и сагиттальное (фазовая ЧКХ)",
        returns="{freq_lpmm, re_tan, im_tan, phase_tan, re_sag, "
                "im_sag, phase_sag, mtf_tan, mtf_sag, cutoff_lpmm}",
        params=system_source_params([
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def adv_otf_complex(ctx, file, system, lbo_index, lbo_name,
                        field_y, wl, defocus):
        import numpy as np
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl,
                      defocus=defocus)
        psf = np.asarray(res["psf"], dtype=float)
        n = psf.shape[0]
        otf = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(psf)))
        center = n // 2
        freqs = np.fft.fftshift(
            np.fft.fftfreq(n, d=res["pitch_um"])) * 1000.0  # лин/мм
        freq_axis = freqs[center:]
        tan = otf[center:, center]
        sag = otf[center, center:]
        return {
            "wl": res["wl"], "field_y": field_y, "defocus": defocus,
            "pitch_um": res["pitch_um"],
            "cutoff_lpmm": float(res["cutoff_lpmm"]),
            "freq_lpmm": freq_axis.tolist(),
            "re_tan": tan.real.tolist(), "im_tan": tan.imag.tolist(),
            "phase_tan": np.angle(tan).tolist(),
            "re_sag": sag.real.tolist(), "im_sag": sag.imag.tolist(),
            "phase_sag": np.angle(sag).tolist(),
            "mtf_tan": np.abs(tan).tolist(),
            "mtf_sag": np.abs(sag).tolist(),
        }

    # ----------------------------------------------------------
    # adv.airy.encircled — аналитическая ФКЭ Эйри + сравнение с ФРТ
    # ----------------------------------------------------------

    @registry.command(
        "adv.airy.encircled", category="adv",
        description="Эталон Эйри: аналитическая ФКЭ идеального пятна "
                    "1 − J0²(x) − J1²(x) (ряды Бесселя), радиусы тёмных "
                    "колец и сравнение фактической ФРТ (r₅₀/r₈₀) с "
                    "диском Эйри",
        returns="{f_number, wl, airy_radius_um, dark_rings_um, "
                "rows: [{r_um, r_over_r1, ee}], psf_r50_um, psf_r80_um, "
                "r50_over_r1, r80_over_r1}",
        params=system_source_params([
            Param("r_fractions", type="list",
                  help=f"радиусы в долях r₁ (по умолчанию "
                       f"{list(AIRY_R_FRACTIONS_DEFAULT)})"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def adv_airy_encircled(ctx, file, system, lbo_index, lbo_name,
                           r_fractions, field_y, wl):
        import numpy as np
        from analysis.psf_mtf import encircled_energy
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = _psf_of(sys_obj, field_y=field_y, wl=wl)
        f_number = res["f_number"]
        if not f_number:
            raise CommandError(ERR_INVALID_PARAM,
                               "F# не определён — эталон Эйри невозможен")
        r1_um = _J1_FIRST_ZERO / math.pi * res["wl"] * f_number
        fractions = (_parse_number_list(r_fractions, "r_fractions")
                     if r_fractions is not None
                     else list(AIRY_R_FRACTIONS_DEFAULT))
        rows = [{"r_um": float(r_over_r1 * r1_um),
                 "r_over_r1": float(r_over_r1),
                 "ee": float(_airy_ee(r_over_r1))}
                for r_over_r1 in fractions]
        dark_rings = [float(z / math.pi * res["wl"] * f_number)
                      for z in _airy_zeros(AIRY_DARK_RING_COUNT)]
        r_um, ee = encircled_energy(res["psf"], res["pitch_um"])
        r50 = float(np.interp(0.5, ee, r_um))
        r80 = float(np.interp(0.8, ee, r_um))
        return {
            "f_number": float(f_number), "wl": res["wl"],
            "field_y": field_y,
            "airy_radius_um": float(r1_um),
            "airy_diameter_um": float(2.0 * r1_um),
            "dark_rings_um": dark_rings,
            "rows": rows,
            "psf_r50_um": r50, "psf_r80_um": r80,
            "r50_over_r1": float(r50 / r1_um),
            "r80_over_r1": float(r80 / r1_um),
        }
