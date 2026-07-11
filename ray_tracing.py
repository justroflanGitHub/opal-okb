"""Compatibility shim. Real code in analysis/ray_tracing.py.

Re-exports everything so that existing imports like
``from ray_tracing import Ray, trace_ray_through_system`` continue to work.
"""
from analysis.ray_tracing import *  # noqa: F401, F403
from analysis.ray_tracing import (
    Ray, TraceResult,
    intersect_aspheric, surface_normal_aspheric,
    intersect_sphere, refract, surface_normal,
    _compute_semi_diameter, _check_aperture_stop,
    _has_coord_break, _apply_coord_break, _undo_coord_break,
    trace_ray_through_system, trace_fan, trace_grid_3d,
    get_focal_spot,
)
