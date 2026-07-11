"""Compatibility shim. Real code in catalog/glass_agf.py.

Re-exports everything so that
``from glass_agf import compute_n`` continues to work.
"""
from catalog.glass_agf import *  # noqa: F401, F403
from catalog.glass_agf import (
    AGFGlass,
    _parse_agf, _ensure_loaded,
    get_glass_list, get_glass, compute_n, get_nd_vd,
    _agf_to_russian, _rus_to_latin,
)
