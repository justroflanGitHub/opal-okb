"""Compatibility shim. Real code in analysis/diffraction.py.

Re-exports everything so that existing imports like
``from diffraction_mtf import compute_diffraction_mtf`` continue to work.
"""
from analysis.diffraction import *  # noqa: F401, F403
from analysis.diffraction import (
    compute_wavefront_map, compute_diffraction_mtf,
    compute_diffraction_mtf_quick, compute_polychromatic_mtf,
    compute_diffraction_limited_mtf,
)
