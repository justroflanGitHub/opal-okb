# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
import numpy as np
import importlib.util
spec = importlib.util.spec_from_file_location(
    'proto', r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts\_scratch_psf_proto.py')
# выполнить только определения: отбросить печатную часть
src = open(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts\_scratch_psf_proto.py',
           encoding='utf-8').read().split("print('=== 1")[0]
ns = {}
exec(compile(src.replace('sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=\'utf-8\')', ''),
             'proto', 'exec'), ns)
psf_grid, mtf_from_psf, build_doublet = ns['psf_grid'], ns['mtf_from_psf'], ns['build_doublet']

sys.stdout.reconfigure(encoding='utf-8')

s = build_doublet(4.0)
res = psf_grid(s)
M = res['M']
psf = res['psf']
m = mtf_from_psf(psf, res['pitch_um'])
nu = m['freq'] / res['cutoff_lpmm']
for k in range(60, 68):
    print(f'bin {k}: nu/nu_c={nu[k]:.4f}, tan={m["tan"][k]:.4f}, sag={m["sag"][k]:.4f}')
print('nu_step =', round(nu[1] - nu[0], 5))
print()
y_um = (np.arange(M) - M // 2) * res['pitch_um']
for nu_frac in (0.2, 0.3, 0.5):
    nuv = nu_frac * res['cutoff_lpmm']
    P = 1000.0 / nuv
    obj = 0.5 + 0.5 * np.sin(2 * np.pi * y_um / P)
    col_kernel = psf[:, M // 2]
    img1d = np.convolve(obj, col_kernel)[M // 2: M // 2 + M]
    mid = img1d[M // 4: 3 * M // 4]
    c = (mid.max() - mid.min()) / (mid.max() + mid.min())
    print(f'nu={nu_frac}nu_c 1D: contrast={c:.4f}, mtf_tan={np.interp(nuv, m["freq"], m["tan"]):.4f}')
