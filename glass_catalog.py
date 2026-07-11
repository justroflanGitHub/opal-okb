"""Compatibility shim. Real code in catalog/glass_catalog.py.

Re-exports everything so that
``from glass_catalog import compute_refractive_index`` continues to work.
"""
from catalog.glass_catalog import *  # noqa: F401, F403
from catalog.glass_catalog import (
    LAMBDA0_VISIBLE, GLASS_CATALOG,
    compute_refractive_index,
)
