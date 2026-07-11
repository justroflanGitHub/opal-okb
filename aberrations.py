"""Compatibility shim. Real code in analysis/aberrations.py.

Re-exports everything so that existing imports like
``from aberrations import compute_spot_diagram`` continue to work.
"""
from analysis.aberrations import *  # noqa: F401, F403
from analysis.aberrations import (
    _compute_ray_start, _aim_at_pupil,
    trace_aberration_fan, compute_spot_diagram, compute_rms_spot,
    compute_rms_spot_xy, compute_field_aberrations,
    compute_chief_ray_characteristics, compute_focus_curve,
    compute_spot_diagram_polychromatic, compute_polychromatic_rms,
    compute_spot_heatmap, compute_geometric_mtf,
    compute_spot_diagram_at_defocus,
    compute_isoplanatism, compute_oblique_fan,
    compute_ray_coordinates, compute_wavefront_rms_vs_field,
)
