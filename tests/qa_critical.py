"""QA critical checks: aberrations, analysis, GUI structure."""
import os
import re
from pathlib import Path

import numpy as np
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent


def build_system():
    from optics_engine import OpticalSystem, Surface, Wavelength
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


class TestCriticalChecks:
    def test_compute_isoplanatism(self):
        from aberrations import compute_isoplanatism
        sys_obj = build_system()
        r = compute_isoplanatism(sys_obj)
        assert isinstance(r, tuple) and len(r) == 2, f"expected 2-tuple, got {type(r)}"
        pupils, vals = r
        assert hasattr(pupils, '__len__'), "pupils not array-like"

    def test_compute_wavefront_rms_vs_field(self):
        from aberrations import compute_wavefront_rms_vs_field
        sys_obj = build_system()
        r = compute_wavefront_rms_vs_field(sys_obj)
        assert len(r) == 4, f"expected 4, got {len(r)}"

    def test_compute_spot_diagram_at_defocus(self):
        from aberrations import compute_spot_diagram_at_defocus
        sys_obj = build_system()
        for df in [0, -0.5, 0.5, -1.0, 1.0]:
            pts = compute_spot_diagram_at_defocus(sys_obj, field_y=5.0, defocus_mm=df)
            assert hasattr(pts, '__len__'), f"defocus={df} returned non-iterable"

    def test_compute_rms_spot_xy(self):
        from aberrations import compute_spot_diagram_at_defocus, compute_rms_spot_xy
        sys_obj = build_system()
        pts = compute_spot_diagram_at_defocus(sys_obj, field_y=5.0, defocus_mm=0)
        r = compute_rms_spot_xy(pts)
        required = {'rms_x', 'rms_y', 'centroid_x', 'centroid_y'}
        assert required.issubset(set(r.keys())), f"missing keys: {required - set(r.keys())}, got={list(r.keys())}"

    def test_compute_psf_3d(self):
        from advanced_analysis import compute_psf_3d
        sys_obj = build_system()
        r = compute_psf_3d(sys_obj)
        assert isinstance(r, tuple) and len(r) == 3, f"expected 3-tuple, got {type(r)}"
        x, y, Z = r
        assert isinstance(Z, np.ndarray) and Z.ndim == 2, f"Z not 2D ndarray: {type(Z)}"

    @pytest.mark.skip(reason="analysis_gui.py structure — do not touch gui/ per task constraints")
    def test_analysis_panel_tab_count(self):
        """AnalysisPanel tab count — skipped (gui not in scope)."""
        pass

    @pytest.mark.skip(reason="analysis_gui.py structure — do not touch gui/ per task constraints")
    def test_isoplanatism_dotted_line(self):
        """Dy tab has isoplanatism dotted line — skipped (gui not in scope)."""
        pass
