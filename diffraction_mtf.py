"""
OPAL-OKB — Дифракционная ЧКХ (MTF) через FFT
Основано на: Л1.7.1 Частотно-контрастная характеристика
"""
import math
import numpy as np
from typing import Dict, List, Tuple

from optics_engine import OpticalSystem, ObjectType, Wavelength, paraxial_trace
from ray_tracing import Ray, trace_ray_through_system
from glass_catalog import compute_refractive_index
from optics_utils import compute_z_positions, get_primary_wl, get_effective_aperture
from aberrations import _compute_ray_start, _aim_at_pupil


def compute_wavefront_map(system: OpticalSystem, 
                           wl: float = 0.58756,
                           grid_size: int = 64,
                           field_y: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute wavefront map on pupil.

    Returns:
    - wavefront: 2D array W(x,y) in wavelengths
    - pupil_mask: 2D array (1 inside pupil, 0 outside)
    """
    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    efl = parax.get('focal_length', 0)
    z_start, z_pupil = _compute_ray_start(system, parax)

    # Chief ray (for reference)
    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_y) if field_y != 0 else 0.0
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        cx_s, cy_s = _aim_at_pupil(0, 0, z_start, z_pupil, sin_a, cos_a)
        chief_ray = Ray(x=cx_s, y=cy_s, z=z_start, k=0, l=math.sin(angle), m=math.cos(angle))
    else:
        obj_z = -system.surfaces[0].thickness if system.surfaces else -50
        chief_ray = Ray(x=0, y=field_y, z=obj_z, k=0, l=0, m=1)

    chief_result = trace_ray_through_system(system, chief_ray, wl)

    # Use result.opl from trace engine (handles mirrors correctly)
    chief_opl = chief_result.opl if chief_result.success else 0.0

    # Wavefront map
    wavefront = np.zeros((grid_size, grid_size))
    pupil_mask = np.zeros((grid_size, grid_size))

    for i in range(grid_size):
        for j in range(grid_size):
            px = -1.0 + 2.0 * j / (grid_size - 1)
            py = -1.0 + 2.0 * i / (grid_size - 1)

            r2 = px**2 + py**2
            if r2 > 1.0:
                continue

            pupil_mask[i, j] = 1.0

            y_start = py * aperture / 2
            x_start = px * aperture / 2

            if system.object_type == ObjectType.INFINITE:
                angle = math.radians(field_y) if field_y != 0 else 0.0
                sin_a, cos_a = math.sin(angle), math.cos(angle)
                rx_s, ry_s = _aim_at_pupil(x_start, y_start, z_start, z_pupil, sin_a, cos_a)
                ray = Ray(x=rx_s, y=ry_s, z=z_start,
                         k=0, l=math.sin(angle), m=math.cos(angle))
            else:
                obj_z = -system.surfaces[0].thickness if system.surfaces else -50
                d = abs(obj_z)
                ray = Ray(x=x_start, y=field_y, z=obj_z,
                         k=x_start/d, l=(y_start-field_y)/d, m=1)
                norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
                ray.k /= norm; ray.l /= norm; ray.m /= norm

            result = trace_ray_through_system(system, ray, wl)

            if result.success and len(result.path) >= 2:
                # Use result.opl from trace engine
                opl = result.opl
                opd = opl - chief_opl
                wavefront[i, j] = opd / (wl * 1e-3)

    return wavefront, pupil_mask


def compute_diffraction_mtf(system: OpticalSystem,
                            wl: float = 0.58756,
                            grid_size: int = 64,
                            max_freq_lpmm: float = None) -> Dict:
    """
    Дифракционная ЧКХ через FFT автокорреляции зрачка.
    
    Алгоритм:
    1. P(x,y) = exp(i * 2π * W(x,y)) * mask  — функция зрачка
    2. OTF = IFFT(|FFT(P)|²) / нормировка
    3. MTF = |OTF|
    
    Возвращает:
    {
        'freqs': [0, f1, f2, ...],  # лин/мм
        'mtf_tangential': [1.0, m1, m2, ...],
        'mtf_sagittal': [1.0, m1, m2, ...],
        'cutoff_freq': float,
    }
    """
    # Вычисляем волновой фронт
    wavefront, pupil_mask = compute_wavefront_map(system, wl, grid_size)
    
    # Функция зрачка
    pupil_complex = pupil_mask * np.exp(1j * 2 * np.pi * wavefront)
    
    # FFT автокорреляция
    ft = np.fft.fft2(pupil_complex)
    ft_shifted = np.fft.fftshift(ft)
    power = np.abs(ft_shifted)**2
    
    # OTF = IFFT(power)
    otf = np.fft.ifft2(np.fft.ifftshift(power))
    otf = np.fft.fftshift(otf)
    
    # MTF = |OTF| нормированный
    mtf_2d = np.abs(otf)
    mtf_max = mtf_2d[grid_size//2, grid_size//2]
    if mtf_max > 0:
        mtf_2d = mtf_2d / mtf_max
    
    # Envelope: ensure non-negative (diffraction MTF should be >= 0)
    mtf_2d = np.maximum(mtf_2d, 0)
    
    # Частота среза
    aperture = get_effective_aperture(system, default=10.0)
    efl = abs(paraxial_trace(system).get('focal_length', 1))
    na = aperture / (2 * efl) if efl > 0 else 0.1
    cutoff = 2 * na / (wl * 1e-3)  # лин/мм (λ в мм)
    
    if max_freq_lpmm is None:
        max_freq_lpmm = cutoff
    
    # Извлечь меридиональное и сагиттальное сечения
    center = grid_size // 2
    
    # Частотная шкала
    delta_f = cutoff / grid_size  # лин/мм на пиксель
    
    num_points = center
    freqs = [delta_f * i for i in range(num_points)]
    
    mtf_tangential = []
    mtf_sagittal = []
    
    for i in range(num_points):
        # Сагиттальная: горизонтальное сечение (по j)
        if center + i < grid_size:
            mtf_sagittal.append(float(mtf_2d[center, center + i]))
        else:
            mtf_sagittal.append(0.0)
        
        # Меридиональная: вертикальное сечение (по i)  
        if center + i < grid_size:
            mtf_tangential.append(float(mtf_2d[center + i, center]))
        else:
            mtf_tangential.append(0.0)
    
    return {
        'freqs': freqs,
        'mtf_tangential': mtf_tangential,
        'mtf_sagittal': mtf_sagittal,
        'cutoff_freq': cutoff,
        'wavefront_rms': float(np.sqrt(np.mean(wavefront[pupil_mask > 0]**2))),
        'wavefront_pv': float(np.ptp(wavefront[pupil_mask > 0])) if np.any(pupil_mask > 0) else 0,
    }


def compute_diffraction_mtf_quick(system: OpticalSystem,
                                   wl: float = 0.58756) -> Dict:
    """Быстрая дифракционная ЧКХ (grid=32)."""
    return compute_diffraction_mtf(system, wl, grid_size=32)


def compute_polychromatic_mtf(system: OpticalSystem,
                                grid_size: int = 64,
                                max_freq_lpmm: float = None) -> Dict:
    """
    Полихроматическая дифракционная ЧКХ.
    MTF(ν) = Σ(wl_weight_i * MTF_i(ν)) / Σ(wl_weight_i)
    
    Взвешенная сумма MTF по длинам волн.
    """
    wavelengths = system.wavelengths if system.wavelengths else [Wavelength(0.58756)]
    
    # Собираем MTF для каждой длины волны
    all_mtf = []
    total_weight = 0.0
    
    for wl in wavelengths:
        mtf_result = compute_diffraction_mtf(system, wl=wl.value,
                                              grid_size=grid_size,
                                              max_freq_lpmm=max_freq_lpmm)
        all_mtf.append((mtf_result, wl.weight))
        total_weight += wl.weight
    
    if total_weight == 0 or not all_mtf:
        # Fallback: вернуть пустой результат
        return {
            'freqs': [],
            'mtf_tangential': [],
            'mtf_sagittal': [],
            'cutoff_freq': 0,
        }
    
    # Все частотные шкалы должны быть одинаковые (grid_size совпадает)
    ref = all_mtf[0][0]
    num_pts = len(ref['freqs'])
    
    mtf_t = [0.0] * num_pts
    mtf_s = [0.0] * num_pts
    
    for mtf_result, w in all_mtf:
        for i in range(min(num_pts, len(mtf_result['freqs']))):
            mtf_t[i] += w * mtf_result['mtf_tangential'][i]
            mtf_s[i] += w * mtf_result['mtf_sagittal'][i]
    
    for i in range(num_pts):
        mtf_t[i] /= total_weight
        mtf_s[i] /= total_weight
    
    return {
        'freqs': ref['freqs'],
        'mtf_tangential': mtf_t,
        'mtf_sagittal': mtf_s,
        'cutoff_freq': ref['cutoff_freq'],
    }


def compute_diffraction_limited_mtf(system: OpticalSystem,
                                       wl: float = None) -> Dict:
    """
    Безаберрационная дифракционная ЧКХ.
    Это MTF для идеальной системы (W=0) с той же апертурой.
    
    Для круглого зрачка: MTF(ν) = (2/π) * [arccos(ν/ν_c) - (ν/ν_c)*√(1-(ν/ν_c)²)]
    где ν_c = 2·NA/λ = D/(λ·f') — частота обрезания
    
    Возвращает:
    {
        'freqs': [0, f1, f2, ...],  # лин/мм
        'mtf': [1.0, m1, m2, ...],  # MTF (одинаково для мер/саг для круглого зрачка)
        'cutoff_freq': float,
    }
    """
    if wl is None:
        wl = get_primary_wl(system)
    
    # Вычисляем NA и частоту обрезания
    aperture = get_effective_aperture(system, default=10.0)
    efl = abs(paraxial_trace(system).get('focal_length', 1))
    na = aperture / (2 * efl) if efl > 0 else 0.1
    
    wl_mm = wl * 1e-3  # мкм -> мм
    cutoff = 2 * na / wl_mm  # лин/мм
    
    # Генерируем частоты (как у compute_diffraction_mtf_quick: grid_size=32)
    grid_size = 32
    num_points = grid_size // 2
    delta_f = cutoff / grid_size
    freqs = [delta_f * i for i in range(num_points)]
    
    mtf_vals = []
    for f in freqs:
        if f == 0:
            mtf_vals.append(1.0)
            continue
        nu_norm = f / cutoff  # ν/ν_c
        if nu_norm >= 1.0:
            mtf_vals.append(0.0)
            continue
        # Аналитическая формула для круглого зрачка
        mtf = (2.0 / math.pi) * (math.acos(nu_norm) - nu_norm * math.sqrt(1 - nu_norm**2))
        mtf_vals.append(max(0.0, mtf))
    
    return {
        'freqs': freqs,
        'mtf': mtf_vals,
        'cutoff_freq': cutoff,
    }


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from optics_engine import create_demo_system
    
    print("=== Дифракционная ЧКХ ===")
    sys_opt = create_demo_system()
    
    print(f"Система: {sys_opt.name}")
    print(f"Поверхности: {sys_opt.num_surfaces}")
    print()
    
    result = compute_diffraction_mtf_quick(sys_opt, wl=0.58756)
    
    print(f"Частота среза: {result['cutoff_freq']:.1f} лин/мм")
    print(f"RMS волнового фронта: {result['wavefront_rms']:.4f} λ")
    print(f"PV волнового фронта: {result['wavefront_pv']:.4f} λ")
    print()
    print(f"{'Частота':>10} {'MTF-T':>8} {'MTF-S':>8}")
    print("-" * 30)
    for i in range(0, len(result['freqs']), max(1, len(result['freqs'])//15)):
        f = result['freqs'][i]
        mt = result['mtf_tangential'][i]
        ms = result['mtf_sagittal'][i]
        print(f"{f:10.1f} {mt:8.4f} {ms:8.4f}")
    
    print("\nГотово!")
