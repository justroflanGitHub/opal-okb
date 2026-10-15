"""
OPAL-OKB — ФРТ/ФРЛ/ОПФ/ФКЭ (уровень-2 анализа, ANALIZE.DOC §9, работа DIA)

Дифракционные характеристики изображения — в порте ОТСУТСТВОВАЛИ,
реализованы по стандартной физике (сверка с OPAL-алгоритмами — реверс-волна 10):

* **ФРТ** (функция рассеяния точки, §9.2): ``|FFT(P)|²``, где зрачковая
  функция ``P = M·exp(2πi·W)`` — контур зрачка (единичный круг минус
  центральное экранирование ``system.obscuration_ratio``) и волновая
  аберрация ``W`` поля ``field_y`` от :func:`aberrations.trace_wavefront_hexapolar`
  (та же гексаполярная сетка, что у Штреля — сетка W интерполируется
  на решётку одним и тем же :func:`strehl._pupil_grid_from_points`);
* **ФРЛ** (функция рассеяния линии, §9.4): интеграл ФРТ по одной оси —
  изображение бесконечной линии; меридиональная ФРЛ — линия вдоль Y
  (профилю по X), сагиттальная — вдоль X (профиль по Y);
* **ОПФ/ЧКХ** (§9.6): ``MTF = |FFT(ФРТ)|`` нормированная; сечения:
  ``tan`` — частоты вдоль Y (меридиональная плоскость), ``sag`` — вдоль X.
  Соответствие мир (терминология пересекается, §9.5): частота в
  меридиональной плоскости измеряется штрихами вдоль X — свёртка с
  ФРЛ «по Y» (линия вдоль X);
* **ФКЭ** (функция концентрации энергии, §9.3): доля энергии ФРТ в круге
  радиуса r (у OPAL — от диаметра; диаметр = 2r) от энергетического центра;
* **Штрель**: пик ФРТ к пику идеального пятна той же маски —
  масштаб восстанавливается коэффициентом заполнения ``fill``
  (аналитический пик ``|FFT|²`` идеального зрачка), сам расчёт Штреля
  переиспользует сетку :mod:`analysis.strehl` и сверяется с ним (тесты,
  допуск 1e-3);
* **миры** (§9.5): изображение синус-миры / шпальной миры (меандр) —
  свёртка профиля с ФРЛ; контраст синус-миры на частоте ν равен MTF(ν).

Масштаб плоскости изображения (шаг решётки ФРТ, мкм)::

    δ = λ·f' / (M·Δξ),   Δξ = D/(grid−1) — шаг решётки зрачка (мм),
    M = pad·grid — решётка ФРТ после zero-padding;

координаты верны для дальнего типа (INFINITE); для ближнего типа
(FINITE) f' — параксиальная оценка. Частота среза ``ν_c = D/(λ·f')``
лин/мм; Найквист решётки ФРТ при ``pad = 4`` — ``2·ν_c``.
"""
import math
from typing import Dict, Optional, Tuple

import numpy as np

from optics_engine import OpticalSystem, paraxial_trace
from optics_utils import get_effective_aperture, get_primary_wl
from analysis.aberrations import trace_wavefront_hexapolar, WF_RMS_MIN_POINTS
from analysis.strehl import _pupil_grid_from_points, STREHL_HEXAPOLAR_RINGS

# Решётка зрачка: 128, как STREHL_GRID_SIZE — Штрель из ФРТ совпадает с
# analysis.strehl вплоть до дискретизации (тест, допуск 1e-3).
GRID = 128
# Zero-padding FFT (как STREHL_FFT_PAD): M = pad·grid = 512 → частотный
# диапазон ФРТ до 2·ν_c, ядро мир до среза не алиазит.
PSF_FFT_PAD = 4
# Кольца гексаполярной сетки зрачка — как STREHL_HEXAPOLAR_RINGS (6 → 127
# лучей): одна и та же сетка W для Штреля и ФРТ.
PSF_HEXAPOLAR_RINGS = STREHL_HEXAPOLAR_RINGS

def _empty_psf(reason: str) -> Dict:
    """Результат без ФРТ (система пуста / лучей слишком мало)."""
    return {'psf': None, 'strehl': None, 'reason': reason}


def psf_grid(system: OpticalSystem, field_y: float = 0.0,
             wl: Optional[float] = None, defocus: float = 0.0,
             grid: int = GRID, pad: int = PSF_FFT_PAD,
             num_rings: int = PSF_HEXAPOLAR_RINGS) -> Dict:
    """ФРТ на решётке: зрачок (W + дефокус) → ``|FFT|²`` → psf[i, j].

    Строки ``psf`` — координата Y (меридиональная), столбцы — X; ФРТ
    нормирована на единичную полную энергию (``Σ psf = 1``). Центр
    решётки — опорная ось поля (W измерена до опорной сферы поля, так
    что пятно стоит в центре и на поле ≠ 0).

    Args:
        system: Оптическая система (экранирование — из
            ``system.obscuration_ratio``).
        field_y: Угол поля (град) для INFINITE / высота предмета (мм)
            для FINITE.
        wl: Длина волны (мкм); None → основная λ системы.
        defocus: Добавляемая дефокусировка в длинах волн (W += defocus·ρ²,
            ρ — нормированный радиус зрачка; defocus = 0.25 — «0.25λ
            на краю зрачка»).
        grid: Решётка зрачка (до zero-padding).
        pad: Кратность zero-padding FFT (M = pad·grid).
        num_rings: Кольца гексаполярной сетки зрачка для W.

    Returns:
        Словарь; ``psf = None`` и ``reason`` — если расчёт невозможен::

            psf           — ФРТ M×M, Σ = 1 (строки — Y, мкм ось y_um)
            y_um, x_um    — координатные оси плоскости изображения (мкм)
            pitch_um      — шаг решётки ФРТ (мкм)
            fill          — коэффициент заполнения зрачка (аналитический
                            пик идеального пятна в нормировке Σ=1)
            strehl        — пик ФРТ / пик идеала (см. strel_from_psf)
            cutoff_lpmm   — частота среза ν_c = D/(λ·f') (лин/мм)
            nyquist_lpmm  — Найквист решётки ФРТ (лин/мм)
            wavefront     — карта W (длины волн, grid×grid, без дефокуса)
            pupil_mask    — амплитуда зрачка grid×grid (0/1, с экраниров.)
            obscuration   — центральное экранирование (доли D)
            wl, field_y, defocus, D, f, f_number, grid, pad, M,
            num_points    — параметры расчёта (D — апертура, мм; f — f')
    """
    if not system.surfaces:
        return _empty_psf('система без поверхностей')
    if wl is None:
        wl = get_primary_wl(system)

    pupil_w = trace_wavefront_hexapolar(system, wl=wl, field_y=field_y,
                                        num_rings=num_rings)
    if len(pupil_w) < WF_RMS_MIN_POINTS:
        return _empty_psf('трассировка зрачка не удалась')

    wavefront, mask = _pupil_grid_from_points(pupil_w, grid_size=grid)

    # Амплитуда = чистая апертура: единичный круг минус центральное
    # экранирование (зеркальные системы, TASK_PSF).
    obscuration = abs(getattr(system, 'obscuration_ratio', 0.0) or 0.0)
    xs = np.linspace(-1.0, 1.0, grid)
    gx, gy = np.meshgrid(xs, xs)
    rho2 = gx ** 2 + gy ** 2
    if obscuration > 0.0:
        mask = mask * (rho2 >= obscuration ** 2)

    pupil = mask * np.exp(2j * math.pi * (wavefront + defocus * rho2))

    # FFT с zero-padding: центр решётки → начало координат → обратно,
    # чтобы пик ФРТ попал в центр массива.
    m = pad * grid
    padded = np.zeros((m, m), dtype=complex)
    off = (m - grid) // 2
    padded[off:off + grid, off:off + grid] = pupil
    amp = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))
    psf = np.abs(amp) ** 2
    total = float(psf.sum())
    if total <= 0.0:
        return _empty_psf('пустой зрачок')
    psf = psf / total

    # Масштаб плоскости изображения: шаг решётки зрачка Δξ = D/(grid−1) мм
    # (нормированный шаг 2/(grid−1) × полудиаметр D/2), δ = λf'/(M·Δξ).
    D = get_effective_aperture(system, default=10.0)
    efl = abs(paraxial_trace(system).get('focal_length', 0.0) or 0.0)
    if efl < 1e-9:
        return _empty_psf('система без фокусного расстояния')
    pitch_mm = (wl * 1e-3) * efl / (m * (D / (grid - 1)))
    pitch_um = pitch_mm * 1e3

    fill = float(mask.sum()) / (m * m)
    coord_um = (np.arange(m) - m // 2) * pitch_um
    return {
        'psf': psf,
        'y_um': coord_um.copy(),
        'x_um': coord_um.copy(),
        'pitch_um': pitch_um,
        'fill': fill,
        'strehl': float(psf.max()) / fill,
        'cutoff_lpmm': D / (wl * 1e-3) / efl,
        'nyquist_lpmm': 500.0 / pitch_um,
        'wavefront': wavefront,
        'pupil_mask': mask,
        'obscuration': obscuration,
        'wl': wl,
        'field_y': field_y,
        'defocus': defocus,
        'D': D,
        'f': efl,
        'f_number': efl / D if D > 0 else None,
        'grid': grid,
        'pad': pad,
        'M': m,
        'num_points': len(pupil_w),
    }


def lsf_from_psf(psf: np.ndarray,
                 pitch_um: Optional[float] = None) -> Dict:
    """ФРЛ — изображение бесконечной линии (ANALIZE.DOC §9.4).

    Интеграл ФРТ по оси, вдоль которой идёт линия: линия вдоль Y
    («меридиональная ФРЛ») даёт профиль по X, линия вдоль X
    («сагиттальная ФРЛ») — профиль по Y. Каждый профиль нормирован на
    единицу (полная энергия); термины OPAL и физические оси пересекаются
    (частота в меридиональной плоскости измеряется мирой, штрихи которой
    вдоль X, — свёртка с профилем «по Y», см. :func:`render_test_target`).

    Args:
        psf: ФРТ из :func:`psf_grid` (или любая Σ=1).
        pitch_um: Шаг решётки (мкм) для оси координат; None — ось в
            отсчётах (пикселях).

    Returns:
        ``{'x': профиль по X (линия вдоль Y, меридиональная ФРЛ),
        'y': профиль по Y (линия вдоль X, сагиттальная ФРЛ),
        'meridional': то же, что 'x', 'sagittal': то же, что 'y',
        'coord_um' | 'coord_px': ось координат профилей}``.
    """
    psf = np.asarray(psf, dtype=float)
    lsf_x = psf.sum(axis=0)  # Σ по Y → профиль по X (строки = Y)
    lsf_y = psf.sum(axis=1)  # Σ по X → профиль по Y
    n = psf.shape[0]
    step = pitch_um if pitch_um is not None else 1.0
    coord = (np.arange(n) - n // 2) * step
    key = 'coord_um' if pitch_um is not None else 'coord_px'
    return {'x': lsf_x, 'y': lsf_y,
            'meridional': lsf_x, 'sagittal': lsf_y,
            key: coord}


def mtf_from_psf(psf: np.ndarray, pitch_um: float) -> Dict:
    """ОПФ (§9.6): ``MTF = |FFT(ФРТ)|`` нормированная; сечения tan/sag.

    Тангенциальное сечение — частоты вдоль Y (меридиональная плоскость,
    в которой лежит поле), сагиттальное — вдоль X; на оси (и для
    осесимметричной системы) совпадают.

    Args:
        psf: ФРТ, нормированная на единицу (``Σ psf = 1``).
        pitch_um: Шаг решётки ФРТ (мкм).

    Returns:
        ``{'freq_lpmm': частоты 0..Найквист (лин/мм),
        'tan': MTF по ν_y, 'sag': MTF по ν_x,
        'nyquist_lpmm': Найквист, 'df_lpmm': шаг по частоте,
        'mtf_2d': полная 2D MTF (fftshift, центр = нулевая частота)}``.
    """
    psf = np.asarray(psf, dtype=float)
    n = psf.shape[0]
    otf = np.fft.fft2(psf)
    mtf2d = np.fft.fftshift(np.abs(otf))
    dc = mtf2d[n // 2, n // 2]
    if dc > 0.0:
        mtf2d = mtf2d / dc  # MTF(0) = 1 по определению
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=pitch_um)) * 1000.0  # лин/мм
    half = n // 2
    return {'freq_lpmm': freq[half:],
            'tan': mtf2d[half:, half],   # ν вдоль Y — меридиональная плоскость
            'sag': mtf2d[half, half:],   # ν вдоль X — сагиттальное направление
            # истинный Найквист 0.5/pitch (freq[-1] отстаёт от него на df)
            'nyquist_lpmm': 500.0 / pitch_um,
            'df_lpmm': float(freq[1] - freq[0]),
            'mtf_2d': mtf2d}


def encircled_energy(psf: np.ndarray,
                     pitch_um: float) -> Tuple[np.ndarray, np.ndarray]:
    """ФКЭ — доля энергии ФРТ в круге радиуса r (ANALIZE.DOC §9.3).

    Центр кружков — энергетический центр ФРТ (центроид); радиус
    округляется до целого числа отсчётов (гистограммная биннинг-схема,
    точность ~шага решётки). OPAL откладывает ФКЭ от диаметра
    (D = 2r); возвращаем радиус — так удобнее сравнивать с радиусом
    Эйри r₁ = 1.22·λ·F#.

    Args:
        psf: ФРТ, нормированная на единицу.
        pitch_um: Шаг решётки ФРТ (мкм).

    Returns:
        ``(r_um, ee)`` — радиусы кружков (мкм, от 0) и кумулятивная доля
        энергии в них; ``ee`` монотонна, ``ee[-1] ≈ 1``.
    """
    psf = np.asarray(psf, dtype=float)
    n = psf.shape[0]
    tot = float(psf.sum())
    rows = np.arange(n)
    cy = float((psf.sum(axis=1) * rows).sum() / tot)
    cx = float((psf.sum(axis=0) * rows).sum() / tot)
    dy = rows - cy
    dx = rows - cx
    r_px = np.sqrt(dy[:, None] ** 2 + dx[None, :] ** 2)
    nb = int(np.ceil(r_px.max()))
    binned = np.bincount(r_px.astype(int).ravel(), weights=psf.ravel(),
                         minlength=nb + 1)
    r_um = np.arange(nb + 1) * pitch_um
    return r_um, np.cumsum(binned) / tot


def strel_from_psf(psf: np.ndarray, ideal_peak: float) -> float:
    """Штрель из ФРТ: пик ФРТ к пику идеального пятна той же апертуры.

    ФРТ нормирована на ``Σ = 1``, поэтому абсолютный масштаб пика
    утерян; он восстанавливается коэффициентом заполнения зрачка
    ``ideal_peak = fill`` из :func:`psf_grid` (аналитический пик
    ``|FFT|²`` идеального — безаберрационного — зрачка с той же маской:
    ``(ΣP)²/(M²·Σ|P|²) = N_зрачка/M²``). При ``grid``, ``pad`` и сетке W
    как у :mod:`analysis.strehl` совпадает с ``strehl_exact`` (тест,
    допуск 1e-3) — переиспользование, а не дублирование Штреля.

    Args:
        psf: ФРТ, нормированная на единицу.
        ideal_peak: Пик идеального пятна в той же нормировке (``fill``).

    Returns:
        Отношение пиков; ``nan`` при пустом зрачке.
    """
    if ideal_peak is None or ideal_peak <= 0.0:
        return float('nan')
    return float(np.asarray(psf).max()) / float(ideal_peak)


# Ориентации миры: ключ → (направление частоты, профиль ФРЛ, сечение MTF)
# Частота в меридиональной плоскости (tangential, вдоль Y) измеряется
# штрихами вдоль X — свёртка с профилем ФРЛ по Y (ANALIZE.DOC §9.4-9.6).
_TARGET_ORIENTATIONS = {
    'tangential': ('y', 'tan'),
    'sagittal': ('x', 'sag'),
}


def render_test_target(psf: np.ndarray, pitch_um: float, freq_lpmm: float,
                       orientation: str = 'tangential',
                       kind: str = 'sine') -> Dict:
    """Изображение миры (ANALIZE.DOC §9.5): свёртка с ФРЛ.

    Мира бесконечна вдоль штрихов, поэтому изображение её центрального
    среза (поперёк штрихов, посередине штриха — как у OPAL) — линейная
    свёртка одномерного профиля миры с ФРЛ соответствующего направления:
    синус-мира частоты ν даёт контраст, равный MTF(ν).

    Args:
        psf: ФРТ, нормированная на единицу.
        pitch_um: Шаг решётки ФРТ (мкм).
        freq_lpmm: Частота миры (лин/мм).
        orientation: ``'tangential'`` — штрихи вдоль X, яркость меняется
            вдоль Y (частота в меридиональной плоскости); ``'sagittal'``
            — наоборот.
        kind: ``'sine'`` — синус-мира ``0.5 + 0.5·sin``; ``'bar'`` —
            шпальная мира (меандр 0/1, «шпалы» шириной полпериода).

    Returns:
        ``{'coord_um': ось поперёк штрихов (центральное окно),
        'object': идеальный профиль миры, 'image': изображение (свёртка),
        'contrast': контраст Михельсона изображения в центральном окне,
        'freq_lpmm', 'period_um', 'orientation', 'kind'}``.
    """
    if orientation not in _TARGET_ORIENTATIONS:
        raise ValueError(f'ориентация миры: {orientation!r} — нужна '
                         f'одна из {sorted(_TARGET_ORIENTATIONS)}')
    if kind not in ('sine', 'bar'):
        raise ValueError(f"тип миры: {kind!r} — нужен 'sine' или 'bar'")
    if freq_lpmm <= 0.0:
        raise ValueError('частота миры должна быть > 0')

    axis, _ = _TARGET_ORIENTATIONS[orientation]
    lsf = lsf_from_psf(psf, pitch_um)
    profile = np.asarray(lsf[axis], dtype=float)

    n = profile.shape[0]
    period_um = 1000.0 / freq_lpmm
    # Мира строится аналитически на удвоенной решётке (свёртка линейная,
    # без шва), центральное окно — половина решётки ФРТ.
    n_ext = 2 * n
    u_ext = (np.arange(n_ext) - n_ext // 2) * pitch_um
    phase = 2.0 * math.pi * u_ext / period_um
    if kind == 'sine':
        obj = 0.5 + 0.5 * np.sin(phase)
    else:  # bar — шпальная мира: меандр, ширина шпалы = период/2
        obj = (np.sin(phase) >= 0.0).astype(float)

    img_ext = np.convolve(obj, profile, mode='same')

    half_out = n // 4  # центральное окно: ±n/4 от центра
    c = n_ext // 2
    lo, hi = c - half_out, c + half_out
    obj_c = obj[lo:hi]
    img_c = img_ext[lo:hi]
    contrast = float((img_c.max() - img_c.min())
                     / (img_c.max() + img_c.min()))
    return {'coord_um': u_ext[lo:hi],
            'object': obj_c,
            'image': img_c,
            'contrast': contrast,
            'freq_lpmm': freq_lpmm,
            'period_um': period_um,
            'orientation': orientation,
            'kind': kind}


def format_psf_mtf_section(system: OpticalSystem,
                           field_y: float = 0.0) -> str:
    """Краткая секция «ФРТ/ОПФ» для протокола расчёта (fileio/protocol).

    Штрель (FFT), частота среза и ЧКХ осевого пучка по сечениям
    меридиональному/сагиттальному на частотах 0.2..1.0·ν_c.
    Возвращает пустую строку, если расчёт невозможен.
    """
    res = psf_grid(system, field_y=field_y)
    if res.get('psf') is None:
        return ''
    mtf = mtf_from_psf(res['psf'], res['pitch_um'])
    nu = res['cutoff_lpmm']
    freqs, tan, sag = mtf['freq_lpmm'], mtf['tan'], mtf['sag']

    fracs = [f for f in (0.2, 0.4, 0.6, 0.8, 1.0) if f * nu <= freqs[-1]]
    lines = ['─' * 40,
             '  ФРТ / ОПФ (ДИФРАКЦИОННЫЙ АНАЛИЗ, УРОВЕНЬ-2)',
             '─' * 40,
             f"  λ = {res['wl']:.5f} мкм   поле = {field_y:.2f}"
             f"   F# = {res['f_number']:.1f}"
             f"   экр. = {res['obscuration'] * 100:.0f}%",
             f"  Штрель (FFT) = {res['strehl']:.4f}"
             f"   ν_c = {nu:.1f} лин/мм",
             '  ν/νc  ' + ''.join(f"{f:>8.2f}" for f in fracs)]
    for label, key in (('мер', 'tan'), ('саг', 'sag')):
        values = ''.join(
            f"{float(np.interp(f * nu, freqs, mtf[key])):>8.3f}"
            for f in fracs)
        lines.append(f"  {label}   {values}")
    return '\n'.join(lines)
