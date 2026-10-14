"""Compatibility shim. Real code in analysis/strehl.py.

Re-exports everything so that existing imports such as
``from strehl import compute_strehl`` continue to work.
"""
from analysis.strehl import *  # noqa: F401,F403
from analysis.strehl import (  # noqa: F401
    compute_strehl, strehl_marechal, strehl_exact_from_wavefront,
    format_strehl, strehl_tooltip,
    STREHL_GOOD_MIN, STREHL_MARECHAL_LIMIT_MIN,
    STREHL_HEXAPOLAR_RINGS, STREHL_GRID_SIZE, STREHL_FFT_PAD,
)
