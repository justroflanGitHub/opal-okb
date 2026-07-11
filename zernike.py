"""Compatibility shim. Real code in analysis/zernike.py.

Re-exports everything so that existing imports like
``from zernike import compute_zernike_coefficients`` continue to work.
"""
from analysis.zernike import *  # noqa: F401, F403
from analysis.zernike import (
    ZERNIKE_TERMS,
    _zernike_poly, _compute_opl_for_ray,
    compute_zernike_coefficients, compute_wavefront_map_2d,
    compute_zernike_chromatic,
)
