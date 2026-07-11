"""Compatibility shim. Real code in utils/optics_utils.py.

Re-exports all names from the new location so that
``from optics_utils import compute_z_positions`` continues to work.
"""
from utils.optics_utils import *  # noqa: F401, F403
from utils.optics_utils import (
    EPSILON, TINY, UNLIMITED_SD, DEFAULT_RAY_Z,
    compute_z_positions, get_primary_wl, get_effective_aperture,
    WL_NAMES, wl_name,
    copy_table_selection, fmt_val, make_field_ray,
)
