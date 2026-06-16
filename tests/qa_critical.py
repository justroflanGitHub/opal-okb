"""QA critical checks #1-5 + tab count + isoplanatism line"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optics_engine import OpticalSystem, Surface, Wavelength
from aberrations import (compute_isoplanatism, compute_wavefront_rms_vs_field,
                         compute_spot_diagram_at_defocus, compute_rms_spot_xy)
from advanced_analysis import compute_psf_3d
import numpy as np

def build_system():
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s

def main():
    sys_obj = build_system()
    results = []

    # 1. compute_isoplanatism
    try:
        r = compute_isoplanatism(sys_obj)
        assert isinstance(r, tuple) and len(r) == 2, f'expected 2-tuple, got {type(r)}'
        pupils, vals = r
        assert hasattr(pupils, '__len__'), 'pupils not array-like'
        results.append(('1. compute_isoplanatism()', 'PASS'))
    except Exception as e:
        results.append(('1. compute_isoplanatism()', f'FAIL: {e}'))

    # 2. compute_wavefront_rms_vs_field
    try:
        r = compute_wavefront_rms_vs_field(sys_obj)
        assert len(r) == 4, f'expected 4, got {len(r)}'
        results.append(('2. compute_wavefront_rms_vs_field()', 'PASS'))
    except Exception as e:
        results.append(('2. compute_wavefront_rms_vs_field()', f'FAIL: {e}'))

    # 3. compute_spot_diagram_at_defocus — 5 positions
    try:
        for df in [0, -0.5, 0.5, -1.0, 1.0]:
            pts = compute_spot_diagram_at_defocus(sys_obj, field_y=5.0, defocus_mm=df)
            assert hasattr(pts, '__len__'), f'defocus={df} returned non-iterable'
        results.append(('3. compute_spot_diagram_at_defocus() x5', 'PASS'))
    except Exception as e:
        results.append(('3. compute_spot_diagram_at_defocus()', f'FAIL: {e}'))

    # 4. compute_rms_spot_xy — rms_x, rms_y, centroid_x, centroid_y (+ rms_total ok)
    try:
        pts = compute_spot_diagram_at_defocus(sys_obj, field_y=5.0, defocus_mm=0)
        r = compute_rms_spot_xy(pts)
        required = {'rms_x', 'rms_y', 'centroid_x', 'centroid_y'}
        assert required.issubset(set(r.keys())), f'missing keys: {required - set(r.keys())}, got={list(r.keys())}'
        results.append(('4. compute_rms_spot_xy()', 'PASS'))
    except Exception as e:
        results.append(('4. compute_rms_spot_xy()', f'FAIL: {e}'))

    # 5. compute_psf_3d — returns (x, y, Z_2d)
    try:
        r = compute_psf_3d(sys_obj)
        assert isinstance(r, tuple) and len(r) == 3, f'expected 3-tuple, got {type(r)}'
        x, y, Z = r
        assert isinstance(Z, np.ndarray) and Z.ndim == 2, f'Z not 2D ndarray: {type(Z)}'
        results.append(('5. compute_psf_3d()', 'PASS'))
    except Exception as e:
        results.append(('5. compute_psf_3d()', f'FAIL: {e}'))

    # 6. AnalysisPanel tab count
    try:
        gui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'analysis_gui.py')
        with open(gui_path, encoding='utf-8') as f:
            src = f.read()
        m = re.search(r'tabs\s*=\s*\[(.*?)\]', src, re.DOTALL)
        assert m, 'tabs list not found'
        tab_entries = re.findall(r'\("[^"]+",\s*\w+', m.group(1))
        count = len(tab_entries)
        assert 21 <= count <= 22, f'tab count={count}'
        results.append((f'6. AnalysisPanel tabs: {count}', 'PASS'))
    except Exception as e:
        results.append(('6. AnalysisPanel tabs', f'FAIL: {e}'))

    # 7. Isoplanatism dotted line on transverse tab
    try:
        assert 'isoplanatism_data' in src, 'no isoplanatism_data'
        assert "self.mode == 'transverse'" in src, 'no transverse mode check'
        results.append(("7. Dy tab has isoplanatism dotted line", 'PASS'))
    except Exception as e:
        results.append(("7. Dy isoplanatism line", f'FAIL: {e}'))

    print("=" * 60)
    print("QA CRITICAL CHECKS")
    print("=" * 60)
    all_pass = True
    for name, res in results:
        if res == 'PASS':
            print(f'  [PASS] {name}')
        else:
            all_pass = False
            print(f'  [FAIL] {name}')
            print(f'         {res}')
    print("=" * 60)
    passed = sum(1 for _, r in results if r == 'PASS')
    print(f'  {passed}/{len(results)} passed')
    print("=" * 60)
    return 0 if all_pass else 1

if __name__ == '__main__':
    sys.exit(main())
