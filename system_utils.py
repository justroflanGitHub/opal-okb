"""Compatibility shim. Real code in utils/system_utils.py.

Re-exports all names from the new location so that
``from system_utils import scale_system`` continues to work.
"""
from utils.system_utils import *  # noqa: F401, F403
from utils.system_utils import (
    STANDARD_RADII,
    deg_to_gmms, gmms_to_deg, gmms_to_str,
    nearest_standard_radius, standardize_radii,
    get_radii_changes, reverse_system, scale_system,
)
