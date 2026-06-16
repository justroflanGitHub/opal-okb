import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')

from diffraction_mtf import compute_diffraction_mtf_quick
from optics_engine import create_demo_system

s = create_demo_system()
r = compute_diffraction_mtf_quick(s, wl=0.58756)

co = r['cutoff_freq']
rms = r['wavefront_rms']
pv = r['wavefront_pv']
nf = len(r['freqs'])
mt0 = r['mtf_tangential'][0]

print(f'Cutoff: {co:.1f} lp/mm')
print(f'RMS WF: {rms:.4f} lambda')
print(f'PV WF: {pv:.4f} lambda')
print(f'Points: {nf}')
print(f'MTF@0: {mt0:.4f}')
print()

for i in range(0, nf, max(1, nf // 12)):
    f = r['freqs'][i]
    mt = r['mtf_tangential'][i]
    ms = r['mtf_sagittal'][i]
    print(f'  f={f:8.1f}  T={mt:.4f}  S={ms:.4f}')
