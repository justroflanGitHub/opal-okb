"""Thread-safe analysis computation pipeline.

The :func:`compute_all_analysis` function performs all heavy optical analysis
in a background thread and returns a dictionary of results that
:class:`~gui.analysis_panel.AnalysisPanel` applies to its widgets.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from optics_engine import (
    OpticalSystem,
    Wavelength,
    paraxial_trace,
    seidel_aberrations,
    compute_beam_geometry,
)
from aberrations import (
    trace_aberration_fan,
    compute_spot_diagram,
    compute_spot_diagram_polychromatic,
    compute_polychromatic_rms,
    compute_rms_spot,
    compute_rms_spot_xy,
    compute_geometric_mtf,
    compute_field_aberrations,
    compute_focus_curve,
    compute_spot_heatmap,
    compute_spot_diagram_at_defocus,
    compute_chief_ray_characteristics,
    compute_isoplanatism,
    compute_wavefront_rms_vs_field,
    compute_oblique_fan,
    compute_ray_coordinates,
)
from advanced_analysis import (
    compute_psf,
    compute_lsf,
    compute_enc,
    compute_ptf,
    compute_esf,
    compute_psf_3d,
    compute_bar_target_image,
    compute_bar_target_mtf_table,
)
from zernike import (
    compute_zernike_coefficients,
    compute_wavefront_map_2d,
    compute_zernike_chromatic,
)
from optics_utils import get_primary_wl


def compute_all_analysis(
    sys: OpticalSystem,
    defocus: float = 0.0,
    azimuth: float = 0.0,
) -> dict[str, Any]:
    """Compute all analysis data.  Thread-safe (no GUI operations).

    Args:
        sys: The optical system to analyse.
        defocus: Defocus offset in millimetres.
        azimuth: Azimuthal angle in degrees (0 = meridional, 90 = sagittal).

    Returns:
        Dictionary with all precomputed results for widgets and tables.
    """
    d: dict[str, Any] = {}
    wl = get_primary_wl(sys)
    wl_list = [w.value for w in sys.wavelengths] if sys.wavelengths else [0.58756]
    d['wl'] = wl
    d['wl_list'] = wl_list

    def _safe(key: str, fn, *args, **kwargs) -> None:
        try:
            d[key] = fn(*args, **kwargs)
        except Exception:
            pass

    # Spot diagram
    _safe('spot_mono', compute_spot_diagram, sys, wl=wl, num_rays=40, field_y=0.0)
    if 'spot_mono' not in d:
        d['spot_mono'] = []
    _safe('spot_rms', compute_rms_spot, d['spot_mono'])
    _safe('spot_rms_xy', compute_rms_spot_xy, d['spot_mono'])
    d.setdefault('spot_rms', 0)
    d.setdefault('spot_rms_xy', {'rms_x': 0, 'rms_y': 0, 'rms_total': 0, 'centroid_x': 0, 'centroid_y': 0})

    if len(wl_list) > 1:
        _safe('spot_poly', compute_spot_diagram_polychromatic, sys, num_rays=40, field_y=0.0)
        _safe('poly_rms', compute_polychromatic_rms, sys, num_rays=40, field_y=0.0)
        d.setdefault('spot_poly', [])
        d.setdefault('poly_rms', 0)
        if d.get('spot_poly'):
            _safe('poly_rms_xy', compute_rms_spot_xy, [(dx, dy) for dx, dy, _ in d['spot_poly']])
        d.setdefault('poly_rms_xy', {'rms_x': 0, 'rms_y': 0, 'rms_total': 0, 'centroid_x': 0, 'centroid_y': 0})
    else:
        d['spot_poly'] = [(dx, dy, 0) for dx, dy in d['spot_mono']]
        d['poly_rms'] = d.get('spot_rms', 0)
        d['poly_rms_xy'] = d.get('spot_rms_xy', {})

    # Aberration fans
    d['fan_data'] = {}
    d['isoplanatism_data'] = {}
    d['oblique_data'] = None

    if abs(azimuth) > 0.1:
        _safe('oblique_data', compute_oblique_fan, sys, wl=wl, num_rays=20,
              field_y=0.0, azimuth_deg=azimuth)
    else:
        wavelengths = sys.wavelengths if sys.wavelengths else [Wavelength(0.58756)]
        for wl_obj in wavelengths:
            _safe_fan = trace_aberration_fan(sys, wl_obj.value, num_rays=30)
            d['fan_data'][wl_obj.value] = _safe_fan if _safe_fan else []
            try:
                d['isoplanatism_data'][wl_obj.value] = compute_isoplanatism(
                    sys, wl=wl_obj.value, num_rays=30)
            except Exception:
                d['isoplanatism_data'][wl_obj.value] = ([], [])

    # MTF
    _safe('geo_mtf', compute_geometric_mtf, d['spot_mono'], max_freq=100, num_freqs=20)
    d['diff_mtf'] = None
    d['diff_limited_mtf'] = None
    d['poly_mtf'] = None
    try:
        from diffraction_mtf import compute_diffraction_mtf_quick
        d['diff_mtf'] = compute_diffraction_mtf_quick(sys, wl=wl)
    except Exception:
        pass
    try:
        from diffraction_mtf import compute_diffraction_limited_mtf
        d['diff_limited_mtf'] = compute_diffraction_limited_mtf(sys, wl=wl)
    except Exception:
        pass
    if len(wl_list) > 1:
        try:
            from diffraction_mtf import compute_polychromatic_mtf
            d['poly_mtf'] = compute_polychromatic_mtf(sys, grid_size=32)
        except Exception:
            pass

    # Field aberrations
    _safe('field_data', compute_field_aberrations, sys, wl=wl)
    d.setdefault('field_data', [])

    # Focus curve
    _safe('focus_curve', compute_focus_curve, sys, wl=wl, num_points=40,
          defocus_range=2.0, freq_lpmm=50.0, num_rays=25, field_y=0.0)

    # PSF
    d['psf_data'] = None; d['psf_dx'] = None; d['psf_dy'] = None
    try:
        d['psf_data'], d['psf_dx'], d['psf_dy'] = compute_psf(sys, wl=wl, num_rays=64)
    except Exception:
        pass

    # LSF
    d['lsf_tan'] = None; d['lsf_sag'] = None; d['lsf_ax'] = None
    try:
        d['lsf_tan'], d['lsf_ax'] = compute_lsf(sys, wl=wl, num_rays=64, direction='tangential')
        d['lsf_sag'], _ = compute_lsf(sys, wl=wl, num_rays=64, direction='sagittal')
    except Exception:
        pass

    # ESF
    d['esf_x'] = None; d['esf_y'] = None
    try:
        d['esf_x'], d['esf_y'] = compute_esf(sys, wl=wl, field_y=0.0)
    except Exception:
        pass

    # ENC
    d['enc_r'] = None; d['enc_e'] = None
    try:
        d['enc_r'], d['enc_e'] = compute_enc(sys, wl=wl, num_rays=100)
    except Exception:
        pass

    # PTF
    d['ptf_data'] = None
    try:
        d['ptf_data'] = compute_ptf(sys, wl=wl, num_rays=64)
    except Exception:
        pass

    # Heatmap
    d['heatmap'] = None
    d['heatmap_x_range'] = (0, 0); d['heatmap_y_range'] = (0, 0)
    d['heatmap_centroid_x'] = 0; d['heatmap_centroid_y'] = 0
    d['heatmap_max_density'] = 0; d['heatmap_num_points'] = 0
    try:
        hm, xr, yr = compute_spot_heatmap(sys, wl=wl, num_rays=500, field_y=0.0, grid_size=100)
        d['heatmap'] = hm; d['heatmap_x_range'] = xr; d['heatmap_y_range'] = yr
        if hm is not None and hm.size > 0:
            gs = 100
            total = hm.sum()
            if total > 0:
                ys = np.linspace(yr[0], yr[1], gs)
                xs = np.linspace(xr[0], xr[1], gs)
                yy, xx = np.meshgrid(ys, xs, indexing='ij')
                d['heatmap_centroid_x'] = float(np.sum(xx * hm) / total)
                d['heatmap_centroid_y'] = float(np.sum(yy * hm) / total)
            d['heatmap_max_density'] = float(hm.max())
            d['heatmap_num_points'] = int(np.sum(hm > 0))
    except Exception:
        pass

    # Beam geometry
    _safe('beam_data', compute_beam_geometry, sys)
    d.setdefault('beam_data', [])

    # Chief ray
    _safe('chief_data', compute_chief_ray_characteristics, sys)
    d.setdefault('chief_data', [])

    # Zernike
    d['zernike_coeffs'] = []
    d['zernike_chromatic'] = None
    try:
        d['zernike_coeffs'] = compute_zernike_coefficients(
            sys, wl=wl, num_rays=32, max_order=4, defocus_offset=defocus)
    except Exception:
        pass
    if len(wl_list) > 1:
        try:
            d['zernike_chromatic'] = compute_zernike_chromatic(sys, num_rays=32, max_order=4)
        except Exception:
            pass

    # Wavefront map
    d['wf_data'] = None; d['wf_coords'] = None; d['wf_mask'] = None
    try:
        d['wf_data'], d['wf_coords'], d['wf_mask'] = compute_wavefront_map_2d(
            sys, wl=wl, grid_size=48, defocus_offset=defocus)
    except Exception:
        pass

    # WF RMS vs field
    d['wf_rms_field'] = None
    try:
        d['wf_rms_field'] = compute_wavefront_rms_vs_field(sys, wl=wl)
    except Exception:
        pass

    # Focus diagrams
    d['focus_diag_data'] = {}
    d['focus_diag_max_range'] = 0.001
    try:
        parax = paraxial_trace(sys)
        bfd = parax.get('back_focal_distance', 0)
        if abs(bfd) < 1e-6:
            efl = parax.get('focal_length', 50)
            bfd = abs(efl) * 0.5
        ds = abs(bfd) * 0.01
        all_spots = []
        for label, df in [("\u043d\u043e\u043c\u0438\u043d\u0430\u043b", 0.0),
                          ("+DS'", +ds), ("-DS'", -ds),
                          ("+2DS'", +2*ds), ("-2DS'", -2*ds)]:
            spots = compute_spot_diagram_at_defocus(
                sys, wl=wl, num_rays=60, field_y=0.0, defocus_mm=df)
            rms_info = compute_rms_spot_xy(spots)
            d['focus_diag_data'][label] = (spots, rms_info, df)
            all_spots.extend(spots)
        if all_spots:
            d['focus_diag_max_range'] = max(
                math.sqrt(dx**2 + dy**2) for dx, dy in all_spots)
            d['focus_diag_max_range'] = max(d['focus_diag_max_range'], 1e-6)
    except Exception:
        pass

    # PSF 3D
    d['psf3d_x'] = None; d['psf3d_y'] = None; d['psf3d_Z'] = None
    try:
        d['psf3d_x'], d['psf3d_y'], d['psf3d_Z'] = compute_psf_3d(
            sys, wl=wl, grid_size=64, field_y=0.0)
    except Exception:
        pass

    # Bar target
    d['bar_x'] = None; d['bar_ideal'] = None; d['bar_blurred'] = None
    d['bar_mtf_table'] = None
    try:
        d['bar_x'], d['bar_ideal'], d['bar_blurred'] = compute_bar_target_image(
            sys, wl=wl, field_y=0.0, num_bars=5, bar_freq_lp_mm=10)
        d['bar_mtf_table'] = compute_bar_target_mtf_table(
            sys, wl=wl, field_y=0.0, num_bars=5)
    except Exception:
        pass

    return d
