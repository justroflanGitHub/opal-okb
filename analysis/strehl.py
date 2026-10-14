"""
OPAL-OKB — Число Штреля (Strehl ratio)

Два способа (Л1.7, качество изображения):

* **Марешаль** — аппроксимация ``S = exp(−(2π·σ_w)²)``, где σ_w — СКВ
  волновой аберрации в длинах волн. Точна при S ≳ 0.8 (σ ≲ 0.07λ);
* **точный (FFT PSF)** — отношение пика интенсивности PSF аберрированной
  системы к пику дифракционно-ограниченного пятна той же апертуры:
  функция зрачка ``P = M·exp(2πi·W)``, PSF = |FFT(P)|², пик берётся по
  всей частотной плоскости (пик может смещаться, например комой).

σ_w считается по гексаполярной сетке зрачка
(:func:`aberrations.trace_wavefront_hexapolar` — та же сетка, что у СКВ
волновой аберрации по полю); для FFT сетка W интерполируется на
квадратную решётку (обратно-взвешенная интерполяция по расстоянию).

Полихроматический случай — Strehl на каждой длине волны системы +
взвешенное среднее по весам λ.
"""
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from optics_engine import OpticalSystem
from aberrations import (
    trace_wavefront_hexapolar,
    WF_RMS_MIN_POINTS,
)


# Пороги применимости аппроксимации Марешаля (по S_Марешаль):
# выше STREHL_GOOD_MIN аппроксимация надёжна, между порогами —
# «на границе применимости», ниже — неприменима (большие аберрации).
STREHL_GOOD_MIN = 0.1
STREHL_MARECHAL_LIMIT_MIN = 0.05

# Сетка зрачка: кольца гексаполярной выборки и размер решётки FFT.
STREHL_HEXAPOLAR_RINGS = 6       # 127 узлов (часть может теряться виньетированием)
STREHL_GRID_SIZE = 128           # решётка зрачка до zero-padding
STREHL_FFT_PAD = 4               # zero-padding FFT (точный захват пика)


def strehl_marechal(sigma_w: float) -> float:
    """Аппроксимация Марешаля: ``S = exp(−(2π·σ_w)²)``.

    Args:
        sigma_w: СКВ волновой аберрации (длины волн).

    Returns:
        Число Штреля в (0, 1]; σ = 0 → S = 1.
    """
    return math.exp(-((2.0 * math.pi * sigma_w) ** 2))


def strehl_exact_from_wavefront(wavefront_grid: np.ndarray,
                                pupil_mask: np.ndarray) -> Optional[float]:
    """Точный Strehl через FFT PSF.

    Пик |FFT(P)|² с аберрациями (пистон вычтен — на пик он не влияет)
    делится на пик дифракционно-ограниченного пятна той же апертуры
    (``W = 0``, та же маска зрачка). Псевдо-zero-padding сеткой ×4
    (:data:`STREHL_FFT_PAD`), чтобы дискретизация не «промахивалась»
    мимо истинного пика PSF.

    Args:
        wavefront_grid: W (длины волн) на квадратной решётке зрачка.
        pupil_mask: маска зрачка (≥ 0.5 — внутри зрачка), той же формы.

    Returns:
        Отношение пиков в (0, 1+eps] или ``None``, если зрачок пуст.
    """
    mask = np.asarray(pupil_mask) >= 0.5
    if not mask.any():
        return None
    wavefront_grid = np.asarray(wavefront_grid, dtype=float)

    n_pad = STREHL_FFT_PAD * max(mask.shape)
    padded = np.zeros((n_pad, n_pad), dtype=complex)
    m_pad = np.zeros((n_pad, n_pad), dtype=float)

    w = wavefront_grid[mask] - wavefront_grid[mask].mean()  # без пистона
    padded[:mask.shape[0], :mask.shape[1]][mask] = np.exp(2j * np.pi * w)
    m_pad[:mask.shape[0], :mask.shape[1]][mask] = 1.0

    peak_ab = float((np.abs(np.fft.fft2(padded)) ** 2).max())
    peak_ideal = float((np.abs(np.fft.fft2(m_pad)) ** 2).max())
    if peak_ideal < 1e-300:
        return None
    return peak_ab / peak_ideal


def _pupil_grid_from_points(points: List[Tuple[float, float, float]],
                             grid_size: int = STREHL_GRID_SIZE
                             ) -> Tuple[np.ndarray, np.ndarray]:
    """Интерполяция W с гексаполярной сетки на квадратную решётку зрачка.

    Обратно-взвешенная по квадрату расстояния интерполяция (сглаживание
    радиуса — шаг решётки): в точках выборки воспроизводит W точно.

    Args:
        points: Список ``(px, py, W)`` — нормированные координаты зрачка
            (−1..1) и волновая аберрация (длины волн).
        grid_size: Размер квадратной решётки.

    Returns:
        ``(wavefront_grid, pupil_mask)``: W на решётке и маска (1.0
        внутри единичного круга, 0.0 вне).
    """
    xs = np.linspace(-1.0, 1.0, grid_size)
    gx, gy = np.meshgrid(xs, xs)
    grid_pts = np.stack([gx.ravel(), gy.ravel()], axis=1)  # (N², 2)
    sample = np.asarray([(px, py) for px, py, _ in points])  # (M, 2)
    values = np.asarray([w for _, _, w in points])            # (M,)

    soft = (2.0 / max(grid_size - 1, 1)) ** 2  # сглаживание ~ шаг решётки
    weights = np.zeros((grid_pts.shape[0], sample.shape[0]))
    for j in range(sample.shape[0]):
        d2 = ((grid_pts - sample[j]) ** 2).sum(axis=1)
        weights[:, j] = 1.0 / (d2 + soft)
    w_sum = weights.sum(axis=1)
    w_grid = (weights * values).sum(axis=1) / w_sum

    wavefront = w_grid.reshape(grid_size, grid_size)
    mask = ((gx ** 2 + gy ** 2) <= 1.0).astype(float)
    return wavefront, mask


def _wavefront_sigma(points: List[Tuple[float, float, float]]) -> float:
    """СКВ волновой аберрации по зрачку (λ) с вычитанием пистона."""
    ws = [w for _, _, w in points]
    mean_w = sum(ws) / len(ws)
    return math.sqrt(sum((w - mean_w) ** 2 for w in ws) / len(ws))


def _strehl_validity(strehl_marechal_value: Optional[float]) -> str:
    """Категория применимости аппроксимации Марешаля."""
    if strehl_marechal_value is None:
        return 'no_data'
    if strehl_marechal_value > STREHL_GOOD_MIN:
        return 'good'
    if strehl_marechal_value > STREHL_MARECHAL_LIMIT_MIN:
        return 'marechal_limit'
    return 'invalid'


def _strehl_single_wl(system: OpticalSystem, wl: float, field_y: float,
                      num_rings: int, grid_size: int) -> Dict:
    """Strehl на одной длине волны (гексаполярная сетка зрачка → FFT)."""
    result = {'wl': wl, 'strehl_marechal': None, 'strehl_exact': None,
              'sigma_w': None}
    try:
        pupil_w = trace_wavefront_hexapolar(system, wl=wl, field_y=field_y,
                                             num_rings=num_rings)
    except Exception:
        return result
    if len(pupil_w) < WF_RMS_MIN_POINTS:
        return result

    sigma = _wavefront_sigma(pupil_w)
    result['sigma_w'] = sigma
    result['strehl_marechal'] = strehl_marechal(sigma)
    wavefront, mask = _pupil_grid_from_points(pupil_w, grid_size=grid_size)
    result['strehl_exact'] = strehl_exact_from_wavefront(wavefront, mask)
    return result


def compute_strehl(system: OpticalSystem, wl: Optional[float] = None,
                   field_y: float = 0.0,
                   num_rings: int = STREHL_HEXAPOLAR_RINGS,
                   grid_size: int = STREHL_GRID_SIZE) -> Dict:
    """Число Штреля двумя способами (Марешаль + точный FFT PSF).

    σ_w берётся по гексаполярной сетке зрачка (как у СКВ волновой
    аберрации по полю :func:`aberrations.compute_wavefront_rms_vs_field`);
    точный Strehl — по FFT PSF от интерполированной на решётку карты W.

    Args:
        system: Оптическая система.
        wl: Длина волны (мкм); None → полихроматически по всем λ системы
            (взвешенное среднее по весам λ).
        field_y: Угол поля (град) для INFINITE / высота предмета (мм)
            для FINITE.
        num_rings: Кольца гексаполярной сетки зрачка (6 → 127 лучей).
        grid_size: Решётка зрачка для FFT.

    Returns:
        Словарь::

            strehl_marechal — S = exp(−(2πσ)²) (взв. среднее по λ)
            strehl_exact    — пик PSF / пик идеала (взв. среднее по λ)
            sigma_w         — СКВ волновой аберрации, λ (взв. среднее)
            validity        — 'good' (S>0.1) | 'marechal_limit'
                              (0.05<S<0.1) | 'invalid' (S<0.05,
                              Марешаль неприменим) | 'no_data'
            wl              — λ (мкм) или None для полихроматического
            field_y         — поле расчёта
            per_wl          — [{'wl', 'strehl_marechal', 'strehl_exact',
                               'sigma_w'}, …] по каждой λ
    """
    result: Dict = {'strehl_marechal': None, 'strehl_exact': None,
                    'sigma_w': None, 'validity': 'no_data', 'wl': wl,
                    'field_y': field_y, 'per_wl': []}
    if not system.surfaces:
        return result

    if wl is not None:
        per_wl = [_strehl_single_wl(system, wl, field_y,
                                     num_rings, grid_size)]
        result['wl'] = wl
        weights = [1.0]
    else:
        wavelengths = system.wavelengths or []
        per_wl = [_strehl_single_wl(system, w.value, field_y,
                                     num_rings, grid_size)
                  for w in wavelengths]
        result['wl'] = None
        weights = [w.weight for w in wavelengths]
    result['per_wl'] = per_wl

    # Взвешенное среднее по λ с весами (λ без данных пропускается)
    pairs = [(res, weight) for res, weight in zip(per_wl, weights)
             if res['strehl_marechal'] is not None and weight > 0]
    if not pairs:
        return result
    total_w = sum(weight for _, weight in pairs)
    result['strehl_marechal'] = sum(
        res['strehl_marechal'] * weight for res, weight in pairs) / total_w
    sigma_pairs = [(res, weight) for res, weight in pairs
                   if res['sigma_w'] is not None]
    if sigma_pairs:
        sw = sum(weight for _, weight in sigma_pairs)
        result['sigma_w'] = sum(
            res['sigma_w'] * weight for res, weight in sigma_pairs) / sw
    exact_pairs = [(res, weight) for res, weight in pairs
                   if res['strehl_exact'] is not None]
    if exact_pairs:
        ew = sum(weight for _, weight in exact_pairs)
        result['strehl_exact'] = sum(
            res['strehl_exact'] * weight for res, weight in exact_pairs) / ew

    result['validity'] = _strehl_validity(result['strehl_marechal'])
    return result


_VALIDITY_TEXT = {
    'good': 'аппроксимация Марешаля надёжна (S > 0.1)',
    'marechal_limit': 'на границе применимости Марешаля (0.05 < S < 0.1)',
    'invalid': 'большие аберрации: Марешаль неприменим (S < 0.05), '
               'показан точный FFT-результат',
    'no_data': 'нет данных (трассировка не удалась)',
}


def strehl_tooltip(strehl: Dict) -> str:
    """Многострочная расшифровка результата для tooltip GUI.

    Args:
        strehl: Результат :func:`compute_strehl`.

    Returns:
        Формула, точное значение, σ_w, категория применимости и разбивка
        по длинам волн (для полихроматического расчёта).
    """
    if not strehl or strehl.get('strehl_marechal') is None:
        return "Число Штреля: нет данных (волновой фронт не построен)"
    lines = [
        "Число Штреля — отношение пика интенсивности PSF системы "
        "к пику дифракционно-ограниченного пятна:",
        "",
        "Марешаль: S = exp(−(2π·σ)²), σ — СКВ волновой аберрации (λ)",
    ]
    s_m = strehl.get('strehl_marechal')
    s_e = strehl.get('strehl_exact')
    sigma = strehl.get('sigma_w')
    lines.append(f"  S(Марешаль) = {s_m:.4f}")
    if s_e is not None:
        lines.append(f"  S(точный FFT) = {s_e:.4f}")
    if sigma is not None:
        lines.append(f"  σ_w = {sigma:.4f} λ")
    validity = strehl.get('validity', 'no_data')
    lines.append(f"  Применимость: {_VALIDITY_TEXT.get(validity, validity)}")
    per_wl = strehl.get('per_wl') or []
    if len(per_wl) > 1:
        lines.append("")
        lines.append("По длинам волн:")
        for item in per_wl:
            wl = item.get('wl')
            sm = item.get('strehl_marechal')
            sw = item.get('sigma_w')
            if sm is None:
                lines.append(f"  λ={wl:.5f} мкм — нет данных")
                continue
            line = f"  λ={wl:.5f} мкм: S={sm:.4f}"
            if sw is not None:
                line += f", σ={sw:.4f}λ"
            lines.append(line)
    return "\n".join(lines)


def format_strehl(strehl: Dict) -> str:
    """Строка «Strehl: 0.847 (σ=0.052λ, Марешаль)» для GUI/лога.

    Args:
        strehl: Результат :func:`compute_strehl`.

    Returns:
        Однострочное представление; «Strehl: —» при отсутствии данных.
    """
    if not strehl or strehl.get('strehl_marechal') is None:
        return "Strehl: —"
    s = strehl['strehl_marechal']
    sigma = strehl.get('sigma_w')
    poly = strehl.get('wl') is None and len(strehl.get('per_wl', [])) > 1
    text = f"Strehl: {s:.3f}"
    if sigma is not None:
        text += f" (σ={sigma:.3f}λ, Марешаль"
        if poly:
            text += ", полихром."
        text += ")"
    return text
