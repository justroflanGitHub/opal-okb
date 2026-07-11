"""Compatibility shim. Real code in catalog/glass_catalog_full.py.

Re-exports everything so that
``from glass_catalog_full import compute_refractive_index`` continues to work.
"""
from catalog.glass_catalog_full import *  # noqa: F401, F403
from catalog.glass_catalog_full import (
    LAMBDA0_VISIBLE,
    _load_catalog, _get_catalog,
    compute_refractive_index, list_glasses,
)
