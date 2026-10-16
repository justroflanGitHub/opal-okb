# -*- coding: utf-8 -*-
"""Прототип физики psf_mtf: проверка констант для тестов (временный скрипт)."""
import sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')

import numpy as np
from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint, paraxial_trace
from optics_utils import get_effective_aperture, get_primary_wl
from analysis.strehl import compute_strehl, _pupil_grid_from_points
from analysis.aberrations import trace_wavefront_hexapolar

GRID = 128
PAD = 4


def build_doublet(aperture=4.0):
    s = OpticalSystem(name='doublet')
    s.wavelengths = [Wavelength(0.58756, 1.0, 'd')]
    s.field_points = [FieldPoint(y=0.0)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5, semi_diameter=aperture / 2 + 2),
        Surface(radius=-60, glass='TF5', thickness=3, semi_diameter=aperture / 2 + 2),
        Surface(radius=-200, glass='', thickness=0, semi_diameter=aperture / 2 + 2),
    ]
    s.stop_surface = 1
    s.aperture_value = aperture
    return s


def psf_grid(system, field_y=0.0, wl=None, defocus=0.0, grid=GRID, pad=PAD,
             obscuration=None):
    if wl is None:
        wl = get_primary_wl(system)
    pts = trace_wavefront_hexapolar(system, wl=wl, field_y=field_y, num_rings=6)
    wavefront, mask = _pupil_grid_from_points(pts, grid_size=grid)
    xs = np.linspace(-1.0, 1.0, grid)
    gx, gy = np.meshgrid(xs, xs)
    rho2 = gx ** 2 + gy ** 2
    eps = system.obscuration_ratio if obscuration is None else obscuration
    if eps > 0:
        mask = mask * (rho2 >= eps ** 2)
    W = wavefront + defocus * rho2
    pupil = mask * np.exp(2j * np.pi * W)
    M = pad * grid
    padded = np.zeros((M, M), dtype=complex)
    off = (M - grid) // 2
    padded[off:off + grid, off:off + grid] = pupil
    amp = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))
    psf = np.abs(amp) ** 2
    total = psf.sum()
    psf = psf / total
    D = get_effective_aperture(system, default=10.0)
    f = abs(paraxial_trace(system).get('focal_length', 1))
    delta_mm = (wl * 1e-3) * f / (M * (D / (grid - 1)))
    fill = mask.sum() / (M * M)
    return {'psf': psf, 'pitch_um': delta_mm * 1e3, 'fill': fill,
            'cutoff_lpmm': D / (wl * 1e-3) / f, 'wavefront': W, 'mask': mask,
            'wl': wl, 'M': M, 'D': D, 'f': f}


def strel(res):
    return float(res['psf'].max()) / res['fill']


def mtf_from_psf(psf, pitch_um):
    M = psf.shape[0]
    otf = np.fft.fft2(psf)
    mtf2d = np.fft.fftshift(np.abs(otf))
    f = np.fft.fftshift(np.fft.fftfreq(M, d=pitch_um)) * 1000.0
    half = M // 2
    return {'freq': f[half:], 'tan': mtf2d[half:, half], 'sag': mtf2d[half, half:],
            'nyq': f[-1]}


def ee(psf, pitch_um):
    M = psf.shape[0]
    tot = psf.sum()
    cy, cx = np.unravel_index(np.argmax(psf), psf.shape)
    ii, jj = np.meshgrid(np.arange(M) - cy, np.arange(M) - cx, indexing='ij')
    r_px = np.sqrt(ii ** 2 + jj ** 2)
    nb = int(np.ceil(r_px.max()))
    binc = np.bincount(r_px.astype(int).ravel(), weights=psf.ravel(),
                       minlength=nb + 1)
    cum = np.cumsum(binc) / tot
    r_um = np.arange(nb + 1) * pitch_um
    return r_um, cum


print('=== 1. Штрель: psf vs strehl.py ===')
for ap in (4.0, 20.0):
    s = build_doublet(ap)
    res = psf_grid(s)
    ref = compute_strehl(s)
    print(f'ap={ap}: S_psf={strel(res):.6f}  S_strehl_exact={ref["strehl_exact"]:.6f}  '
          f'diff={abs(strel(res) - ref["strehl_exact"]):.2e}  S_marechal={ref["strehl_marechal"]:.4f}')

print()
print('=== 2. Дефокус: нули MTF (Талбот) ===')
s = build_doublet(4.0)
for df in (0.25, 0.5, 1.0):
    res = psf_grid(s, defocus=df)
    m = mtf_from_psf(res['psf'], res['pitch_um'])
    nu = m['freq'] / res['cutoff_lpmm']
    t = m['tan']
    # первый минимум ниже порога
    first_zero = None
    for k in range(1, len(t) - 1):
        if t[k] < 0.05 and t[k] <= t[k - 1] and t[k] <= t[k + 1]:
            first_zero = nu[k]
            break
    print(f'defocus={df}λ: S={strel(res):.4f}, min MTF={t.min():.4f}, '
          f'первый ноль при ν/νc = {first_zero}, MTF(0.5νc)={np.interp(0.5, nu, t):.4f}')

print()
print('=== 3. Экранирование 0.3 ===')
r0 = psf_grid(s, obscuration=0.0)
r3 = psf_grid(s, obscuration=0.3)
airy_r = 1.22 * r0['wl'] * 1e-3 * r0['f'] / r0['D'] * 1e3  # мкм
print(f'pitch={r0["pitch_um"]:.4f} мкм, Airy r1={airy_r:.4f} мкм = {airy_r / r0["pitch_um"]:.2f} отсчётов')
print(f'пик: clear={r0["psf"].max():.6f}, obsc={r3["psf"].max():.6f} '
      f'(отношение {r3["psf"].max() / r0["psf"].max():.4f})')
rr0, e0 = ee(r0['psf'], r0['pitch_um'])
rr3, e3 = ee(r3['psf'], r3['pitch_um'])
for frac in (0.5, 0.8, 1.0, 1.5, 3.0):
    r_ = frac * airy_r
    v0 = np.interp(r_, rr0, e0)
    v3 = np.interp(r_, rr3, e3)
    print(f'  r={frac}·r1: EE clear={v0:.4f}, obsc={v3:.4f}, ниже: {v3 < v0}')
# энергия в кольце 1..2 r1
ring0 = np.interp(2 * airy_r, rr0, e0) - np.interp(1.05 * airy_r, rr0, e0)
ring3 = np.interp(2 * airy_r, rr3, e3) - np.interp(1.05 * airy_r, rr3, e3)
print(f'  кольцо (1..2)r1: clear={ring0:.4f}, obsc={ring3:.4f} (выше: {ring3 > ring0})')

print()
print('=== 4. MTF(0)=1, монотонность, tan/sag ===')
m0 = mtf_from_psf(r0['psf'], r0['pitch_um'])
print(f'MTF(0): tan={m0["tan"][0]:.8f}, sag={m0["sag"][0]:.8f}')
mono = np.diff(m0['tan'])
print(f'монотонность: max прирост={mono.max():.2e}, min MTF у среза={np.interp(1.0, m0["freq"] / r0["cutoff_lpmm"], m0["tan"]):.4f}')
print(f'осевая tan-sag: max|Δ|={np.abs(m0["tan"] - m0["sag"]).max():.2e}')
s20 = build_doublet(20.0)
rf = psf_grid(s20, field_y=5.0)
mf = mtf_from_psf(rf['psf'], rf['pitch_um'])
print(f'поле 5°, ап.20: max|tan-sag|={np.abs(mf["tan"] - mf["sag"]).max():.4f}')

print()
print('=== 5. Синус-мира: контраст vs MTF ===')
res = r0
M = res['M']
y_um = (np.arange(M) - M // 2) * res['pitch_um']
x_um = y_um.copy()
for nu_frac in (0.2, 0.3, 0.5):
    nu = nu_frac * res['cutoff_lpmm']  # лин/мм
    period_um = 1000.0 / nu
    Y, X = np.meshgrid(y_um, x_um, indexing='ij')
    obj = 0.5 + 0.5 * np.sin(2 * np.pi * Y / period_um)
    kernel = res['psf']
    padn = M // 2
    padded = np.pad(obj, padn, mode='edge')
    full = (padn * 2 + M, padn * 2 + M)
    conv = np.fft.irfft2(np.fft.rfft2(padded, full) * np.fft.rfft2(kernel, full), full)
    img = conv[padn:padn + M, padn:padn + M]
    col = img[:, M // 2]          # синус меняется вдоль Y — срез по столбцу
    mid = col[M // 4: 3 * M // 4]
    contrast = (mid.max() - mid.min()) / (mid.max() + mid.min())
    m = mtf_from_psf(res['psf'], res['pitch_um'])
    mtf_at = np.interp(nu, m['freq'], m['tan'])
    print(f'ν={nu:.1f} лин/мм ({nu_frac}νc), период={period_um:.2f} мкм '
          f'({period_um / res["pitch_um"]:.1f} отсч.): контраст={contrast:.4f}, '
          f'MTF_tan(ν)={mtf_at:.4f}, rel={abs(contrast - mtf_at) / max(mtf_at, 1e-9):.3f}')
