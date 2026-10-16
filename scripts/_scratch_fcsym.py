"""Проба 11: EQF-корень синтетики и сдвиг оптимумов при +δρ²."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

from analysis.aberrations import _hexapolar_points
from analysis import focus_criteria as fc

pts = _hexapolar_points(30)
rho2 = np.array([px * px + py * py for px, py in pts])
W0 = 0.8 * rho2 ** 2

root0 = fc._eqf_defocus([(math.sqrt(x), 0.0, w) for x, w in zip(rho2, W0)], 30,
                        fc._defocus_min_rms(rho2, W0))
print(f"b=0.8: eqf d={root0['d']:.6f} conv={root0['converged']} res={root0['residual']:.3e}")

# сдвиг оптимумов: W' = W + δ·ρ²  =>  d* сдвигается ровно на −δ
delta = 0.37
W1 = W0 + delta * rho2
pts1 = [(math.sqrt(x), 0.0, w) for x, w in zip(rho2, W1)]

for name, f0, f1 in [
    ('min_rms', fc._defocus_min_rms(rho2, W0), fc._defocus_min_rms(rho2, W1)),
    ('zone', fc._defocus_zone_balance([(math.sqrt(x), 0.0, w) for x, w in zip(rho2, W0)], 30),
               fc._defocus_zone_balance(pts1, 30)),
    ('strehl', fc._defocus_max_strehl(rho2, W0, fc._defocus_min_rms(rho2, W0))[0],
                fc._defocus_max_strehl(rho2, W1, fc._defocus_min_rms(rho2, W1))[0]),
    ('eqf', root0['d'], fc._eqf_defocus(pts1, 30, fc._defocus_min_rms(rho2, W1))['d']),
]:
    print(f"  {name:7s}: d0={f0:+.6f}  d1={f1:+.6f}  сдвиг={f1 - f0:+.6f} (−δ = −0.37)")
