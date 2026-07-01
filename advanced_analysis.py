"""
OPAL-OKB — Продвинутый анализ: PSF, LSF, ENC, PTF
====================================================
Расчёт на основе FFT зрачковой функции (из diffraction_mtf.py).
"""
import math
import numpy as np
from typing import Dict, List, Tuple

from optics_engine import OpticalSystem, ObjectType, paraxial_trace
from optics_utils import get_effective_aperture
from diffraction_mtf import compute_wavefront_map


def compute_psf(system: OpticalSystem,
                wl: float = 0.58756,
                num_rays: int = 128,
                field_y: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Дифракционная PSF (Point Spread Function) через FFT зрачка.
    
    Алгоритм:
    1. Карта волнового фронта W(x,y) на зрачке
    2. Комплексная функция зрачка: P(x,y) = mask * exp(i * 2π * W(x,y))
    3. PSF = |FFT(P)|² (нормированная на единицу)
    
    Возвращает:
        psf: 2D массив PSF (нормированный на max=1.0)
        dx: 1D массив координат по x (мкм)
        dy: 1D массив координат по y (мкм)
    """
    wavefront, pupil_mask = compute_wavefront_map(system, wl, num_rays, field_y)
    
    # Комплексная функция зрачка
    pupil_complex = pupil_mask * np.exp(1j * 2 * np.pi * wavefront)
    
    # PSF = |FFT(P)|²
    ft = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(pupil_complex)))
    psf = np.abs(ft) ** 2
    
    # Нормировка
    psf_max = psf.max()
    if psf_max > 0:
        psf = psf / psf_max
    
    # Координатные оси в мкм
    aperture = get_effective_aperture(system, default=10.0)
    efl = abs(paraxial_trace(system).get('focal_length', 1))
    
    # Шаг на зрачке (мм)
    dp = aperture / num_rays
    
    # Шаг на изображении: Δx = λ * f / (N * dp_pupil)
    # dp_pupil = aperture/num_rays (мм), λ в мм
    wl_mm = wl * 1e-3
    delta_img = wl_mm * efl / aperture  # мкм: wl_mm*1e3 * efl / aperture... 
    # точнее: pixel_size = λ * EFL / D_pupil  (в мм)
    # delta_img в мм, переведём в мкм
    pixel_size_mm = wl_mm * efl / aperture
    pixel_size_um = pixel_size_mm * 1000  # → мкм
    
    center = num_rays // 2
    coords = (np.arange(num_rays) - center) * pixel_size_um
    
    return psf, coords, coords.copy()


def compute_lsf(system: OpticalSystem,
                wl: float = 0.58756,
                num_rays: int = 128,
                field_y: float = 0.0,
                direction: str = 'tangential') -> Tuple[np.ndarray, np.ndarray]:
    """
    LSF (Line Spread Function) — интеграл PSF по одному направлению.
    
    direction='tangential': интеграл PSF по y → LSF(x) (отклик на вертикальную щель)
    direction='sagittal':   интеграл PSF по x → LSF(y) (отклик на горизонтальную щель)
    
    Возвращает:
        lsf: 1D массив LSF (нормированный на max=1.0)
        axis: 1D массив координат (мкм)
    """
    psf, dx, dy = compute_psf(system, wl, num_rays, field_y)
    
    if direction == 'tangential':
        # Интеграл по y (сумма по строкам) → LSF(x)
        lsf = np.sum(psf, axis=0)
        axis = dx
    else:
        # Интеграл по x (сумма по столбцам) → LSF(y)
        lsf = np.sum(psf, axis=1)
        axis = dy
    
    # Нормировка
    lsf_max = lsf.max()
    if lsf_max > 0:
        lsf = lsf / lsf_max
    
    return lsf, axis


def compute_enc(system: OpticalSystem,
                wl: float = 0.58756,
                num_rays: int = 200,
                field_y: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Encircled Energy (ENC) — доля энергии внутри круга заданного радиуса.
    
    Геометрический расчёт через spot diagram:
    для каждого радиуса r: ENC(r) = доля лучей внутри r от центра.
    
    Возвращает:
        r_um: 1D массив радиусов (мкм)
        enc: 1D массив долей энергии [0..1]
    """
    from aberrations import compute_spot_diagram
    
    spots = compute_spot_diagram(system, wl=wl, num_rays=num_rays, field_y=field_y)
    
    if not spots:
        return np.array([0.0]), np.array([0.0])
    
    # Переводим координаты из мм в мкм
    spots_um = [(dx * 1000, dy * 1000) for dx, dy in spots]
    
    # Радиусы каждого луча от центра (мкм)
    radii = np.array([math.sqrt(x**2 + y**2) for x, y in spots_um])
    
    r_max = radii.max()
    if r_max < 1e-10:
        r_max = 1.0
    
    # 100 точек по радиусу
    num_points = 100
    r_um = np.linspace(0, r_max, num_points)
    enc = np.zeros(num_points)
    
    total = len(radii)
    sorted_radii = np.sort(radii)
    
    for i, r in enumerate(r_um):
        # Количество лучей внутри радиуса r
        count = np.searchsorted(sorted_radii, r, side='right')
        enc[i] = count / total
    
    return r_um, enc


def compute_ptf(system: OpticalSystem,
                wl: float = 0.58756,
                num_rays: int = 128,
                field_y: float = 0.0) -> Dict:
    """
    PTF (Phase Transfer Function) — фазовая ЧКХ = arg(OTF).
    
    OTF = FFT(PSF), PTF = angle(OTF) в радианах.
    
    Возвращает:
    {
        'freqs': [0, f1, f2, ...],       # лин/мм
        'ptf_tangential': [0, p1, p2, ...],  # радианы
        'ptf_sagittal': [0, p1, p2, ...],    # радианы
        'cutoff_freq': float,
    }
    """
    wavefront, pupil_mask = compute_wavefront_map(system, wl, num_rays, field_y)
    
    # Комплексная функция зрачка
    pupil_complex = pupil_mask * np.exp(1j * 2 * np.pi * wavefront)
    
    # OTF через автокорреляцию (как в diffraction_mtf.py)
    ft = np.fft.fft2(pupil_complex)
    ft_shifted = np.fft.fftshift(ft)
    power = np.abs(ft_shifted) ** 2
    
    otf = np.fft.ifft2(np.fft.ifftshift(power))
    otf = np.fft.fftshift(otf)
    
    # PTF = angle(OTF)
    ptf_2d = np.angle(otf)
    
    # Частота среза
    aperture = get_effective_aperture(system, default=10.0)
    efl = abs(paraxial_trace(system).get('focal_length', 1))
    na = aperture / (2 * efl) if efl > 0 else 0.1
    cutoff = 2 * na / (wl * 1e-3)  # лин/мм
    
    center = num_rays // 2
    delta_f = cutoff / num_rays
    
    num_points = center
    freqs = [delta_f * i for i in range(num_points)]
    
    ptf_tangential = []
    ptf_sagittal = []
    
    for i in range(num_points):
        # Сагиттальная: горизонтальное сечение (по j)
        if center + i < num_rays:
            ptf_sagittal.append(float(ptf_2d[center, center + i]))
        else:
            ptf_sagittal.append(0.0)
        
        # Меридиональная: вертикальное сечение (по i)
        if center + i < num_rays:
            ptf_tangential.append(float(ptf_2d[center + i, center]))
        else:
            ptf_tangential.append(0.0)
    
    return {
        'freqs': freqs,
        'ptf_tangential': ptf_tangential,
        'ptf_sagittal': ptf_sagittal,
        'cutoff_freq': cutoff,
    }


def compute_psf_3d(system: OpticalSystem,
                    wl: float = 0.58756,
                    grid_size: int = 64,
                    field_y: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    PSF как 3D поверхность (intensity vs x, y).
    
    Возвращает: (x_coords_um, y_coords_um, Z_intensity_2d)
    где Z_intensity_2d — нормированная 2D PSF (grid_size x grid_size).
    """
    psf, dx, dy = compute_psf(system, wl=wl, num_rays=grid_size, field_y=field_y)
    # psf уже нормирован на max=1.0
    # Берём центральную часть если нужно
    if psf.shape[0] > grid_size:
        c = psf.shape[0] // 2
        h = grid_size // 2
        psf = psf[c-h:c+h, c-h:c+h]
        dx = dx[c-h:c+h]
        dy = dy[c-h:c+h]
    return dx, dy, psf


def compute_bar_target_image(system, wl=0.58756, field_y=0.0, num_bars=5, bar_freq_lp_mm=10):
    """
    Симуляция изображения штриховой миры (bar target).

    1. Создать идеальное изображение миры (черно-белые полосы)
    2. Свернуть с PSF (свертка)
    3. Показать результат — размытые полосы

    Возвращает: (x_coords_um, ideal_profile, blurred_profile)
    """
    # Получаем LSF (используем как линию)
    lsf, axis_um = compute_lsf(system, wl=wl, num_rays=128, field_y=field_y,
                                direction='tangential')

    if axis_um is None or len(axis_um) < 2:
        return np.array([0.0]), np.array([0.0]), np.array([0.0])

    # Размер шага в мкм
    dx_um = abs(axis_um[1] - axis_um[0])

    # Период миры в мкм (из частоты лин/мм)
    period_um = 1000.0 / bar_freq_lp_mm  # мкм
    half_period_um = period_um / 2.0

    # Идеальный профиль: черно-белые полосы
    n_points = len(axis_um)
    ideal = np.zeros(n_points)
    for i in range(n_points):
        x = axis_um[i] - axis_um[n_points // 2]  # центр
        phase = x % period_um
        if phase < 0:
            phase += period_um
        if phase < half_period_um:
            ideal[i] = 1.0
        else:
            ideal[i] = 0.0

    # Свертка идеального профиля с LSF (нормированной как плотность)
    lsf_area = np.trapezoid(lsf, axis_um) if np.trapezoid(lsf, axis_um) != 0 else 1.0
    lsf_norm = lsf / lsf_area  # нормируем как PSF-подобную функцию

    blurred = np.convolve(ideal, lsf_norm * dx_um, mode='same')

    # Контраст: (Imax - Imin) / (Imax + Imin)
    return axis_um, ideal, blurred


def compute_bar_target_mtf_table(system, wl=0.58756, field_y=0.0, num_bars=5,
                                   freq_list=None):
    """
    Таблица MTF по результатам миры для разных частот.

    Возвращает список словарей:
    [{freq, contrast_ideal, contrast_real, mtf}, ...]
    """
    if freq_list is None:
        freq_list = [5, 10, 20, 30, 50, 80, 100]

    results = []
    for freq in freq_list:
        try:
            x, ideal, blurred = compute_bar_target_image(
                system, wl=wl, field_y=field_y,
                num_bars=num_bars, bar_freq_lp_mm=freq)

            if len(blurred) < 4 or blurred.max() == blurred.min():
                results.append({
                    'freq': freq,
                    'contrast_ideal': 1.0,
                    'contrast_real': 0.0,
                    'mtf': 0.0,
                })
                continue

            # Контраст идеального: всегда 1
            contrast_ideal = 1.0

            # Контраст реального (размытого) изображения
            imax = blurred.max()
            imin = blurred.min()
            contrast_real = (imax - imin) / (imax + imin) if (imax + imin) > 0 else 0.0

            # MTF = contrast_real / contrast_ideal
            mtf = contrast_real / contrast_ideal if contrast_ideal > 0 else 0.0

            results.append({
                'freq': freq,
                'contrast_ideal': contrast_ideal,
                'contrast_real': contrast_real,
                'mtf': mtf,
            })
        except Exception:
            results.append({
                'freq': freq,
                'contrast_ideal': 1.0,
                'contrast_real': 0.0,
                'mtf': 0.0,
            })

    return results


def compute_esf(system: OpticalSystem,
                wl: float = 0.58756,
                field_y: float = 0.0,
                num_points: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """
    ESF (Edge Spread Function) — отклик системы на резкий край.

    ESF(x) = ∫_{-∞}^{x} LSF(x') dx'

    Вычисляется как кумулятивная сумма от LSF (tangential).

    Возвращает:
        x_coordinates_um: 1D массив координат (мкм)
        esf_values: 1D массив значений от 0 до 1
    """
    lsf, axis = compute_lsf(system, wl=wl, num_rays=128, field_y=field_y,
                             direction='tangential')

    # Кумулятивная сумма (интеграл LSF)
    cs = np.cumsum(lsf)
    # Нормировка к [0, 1]
    cs_max = cs[-1]
    if cs_max > 0:
        esf = cs / cs_max
    else:
        esf = np.zeros_like(cs)

    return axis, esf


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    from optics_engine import create_demo_system
    
    print("=== PSF / LSF / ENC / PTF ===\n")
    sys_opt = create_demo_system()
    print(f"Система: {sys_opt.name}\n")
    
    # PSF
    print("--- PSF ---")
    psf, dx, dy = compute_psf(sys_opt, wl=0.58756, num_rays=64)
    print(f"Размер: {psf.shape}, пик: {psf.max():.6f}")
    print(f"Диапазон: x=[{dx.min():.2f}, {dx.max():.2f}] мкм, y=[{dy.min():.2f}, {dy.max():.2f}] мкм")
    
    # LSF
    print("\n--- LSF ---")
    for d in ['tangential', 'sagittal']:
        lsf, ax = compute_lsf(sys_opt, num_rays=64, direction=d)
        print(f"{d}: пик={lsf.max():.4f}, FWHM~{np.sum(lsf > 0.5) * (ax[1]-ax[0]):.2f} мкм")
    
    # ENC
    print("\n--- ENC ---")
    r_um, enc = compute_enc(sys_opt, num_rays=100)
    for pct in [0.5, 0.8, 0.9]:
        idx = np.searchsorted(enc, pct)
        if idx < len(r_um):
            print(f"  {int(pct*100)}% энергии при r ≤ {r_um[idx]:.2f} мкм")
    
    # PTF
    print("\n--- PTF ---")
    ptf = compute_ptf(sys_opt, num_rays=64)
    print(f"Частота среза: {ptf['cutoff_freq']:.1f} лин/мм")
    print(f"PTF-T[1..5]: {[f'{v:.3f}' for v in ptf['ptf_tangential'][1:6]]}")
    print(f"PTF-S[1..5]: {[f'{v:.3f}' for v in ptf['ptf_sagittal'][1:6]]}")
    
    print("\nГотово!")
