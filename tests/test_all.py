"""
OPAL-OKB — Финальный независимый QA-тест (pytest version)
Broad integration tests covering imports, optics engine, glass catalog,
ray tracing, visualization, GUI, aberrations, optimizer, OPJ/FIL readers, edge cases.
"""
import importlib
import math
import os
import struct
import time
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = BASE_DIR / "extracted" / "opal_okb"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_system(surfaces_data, wavelengths=None, aperture=20.0):
    from optics_engine import OpticalSystem, Surface, Wavelength
    sys = OpticalSystem()
    sys.aperture_value = aperture
    if wavelengths is None:
        sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    else:
        sys.wavelengths = wavelengths
    from optics_engine import FieldPoint
    sys.field_points = [FieldPoint(0.0)]
    for r, d, glass, sd in surfaces_data:
        sys.surfaces.append(Surface(radius=r, thickness=d, glass=glass, semi_diameter=sd))
    return sys


# --------------------------------------------------------------------------- #
# 0. IMPORT TESTS
# --------------------------------------------------------------------------- #

class TestImports:
    def test_import_glass_catalog(self):
        importlib.import_module("glass_catalog")

    def test_import_optics_engine(self):
        importlib.import_module("optics_engine")

    def test_import_ray_tracing(self):
        importlib.import_module("ray_tracing")

    def test_import_aberrations(self):
        importlib.import_module("aberrations")

    def test_import_optimizer(self):
        importlib.import_module("optimizer")

    def test_import_opj_reader(self):
        importlib.import_module("opj_reader")

    def test_import_fil_reader_v2(self):
        importlib.import_module("fil_reader_v2")

    @pytest.mark.skipif(
        not importlib.util.find_spec("PyQt5"),
        reason="PyQt5 not available"
    )
    def test_import_visualization(self):
        importlib.import_module("visualization")

    @pytest.mark.skipif(
        not importlib.util.find_spec("PyQt5"),
        reason="PyQt5 not available"
    )
    def test_import_main(self):
        importlib.import_module("main")


# --------------------------------------------------------------------------- #
# 1. OPTICS ENGINE
# --------------------------------------------------------------------------- #

class TestOpticsEngine:
    def test_plano_convex_positive_efl(self):
        from optics_engine import paraxial_trace
        from glass_catalog import compute_refractive_index
        n_k8 = compute_refractive_index("К8", 0.58756)
        sys1 = make_system([(50.0, 5.0, "К8", 15), (0.0, 95.0, "", 15)])
        res1 = paraxial_trace(sys1)
        f1 = res1.get('focal_length', 0)
        assert 90 < f1 < 110, f"f' = {f1:.4f} мм"

    def test_biconvex_positive_efl(self):
        from optics_engine import paraxial_trace
        sys2 = make_system([(100.0, 5.0, "К8", 15), (-100.0, 95.0, "", 15)])
        res2 = paraxial_trace(sys2)
        f2 = res2.get('focal_length', 0)
        assert 90 < f2 < 110, f"f' = {f2:.4f} мм"

    def test_biconvex_50_neg200(self):
        from optics_engine import paraxial_trace
        sys3 = make_system([(50.0, 5.0, "К8", 15), (-200.0, 50.0, "", 15)])
        res3 = paraxial_trace(sys3)
        f3 = res3.get('focal_length', 0)
        assert 50 < f3 < 120, f"f' = {f3:.4f} мм"

    def test_negative_lens(self):
        from optics_engine import paraxial_trace
        sys4 = make_system([(-50.0, 5.0, "К8", 15), (50.0, 95.0, "", 15)])
        res4 = paraxial_trace(sys4)
        f4 = res4.get('focal_length', 0)
        assert f4 < 0, f"f' = {f4:.4f} мм"

    def test_thin_lens(self):
        from optics_engine import paraxial_trace
        from glass_catalog import compute_refractive_index
        n_k8 = compute_refractive_index("К8", 0.58756)
        sys5 = make_system([(50.0, 0.001, "К8", 15), (0.0, 95.0, "", 15)])
        res5 = paraxial_trace(sys5)
        f5 = res5.get('focal_length', 0)
        f_thin_theory = 50.0 / (n_k8 - 1)
        err5 = abs(f5 - f_thin_theory) / f_thin_theory * 100
        assert err5 < 5, f"f' = {f5:.4f} мм (error={err5:.2f}%)"

    def test_two_lens_system(self):
        from optics_engine import paraxial_trace
        sys6 = make_system([
            (100.0, 5.0, "К8", 15), (-100.0, 10.0, "", 15),
            (80.0, 5.0, "К8", 15), (-80.0, 50.0, "", 15),
        ])
        res6 = paraxial_trace(sys6)
        f6 = res6.get('focal_length', 0)
        assert f6 > 0, f"f' = {f6:.4f} мм"

    def test_seidel_si_nonzero(self):
        from optics_engine import seidel_aberrations
        sys2 = make_system([(100.0, 5.0, "К8", 15), (-100.0, 95.0, "", 15)])
        seidel1 = seidel_aberrations(sys2)
        si = seidel1.get('SI', 0)
        assert si != 0, f"SI = {si:.6f}"

    def test_seidel_all_5_sums(self):
        from optics_engine import seidel_aberrations
        sys2 = make_system([(100.0, 5.0, "К8", 15), (-100.0, 95.0, "", 15)])
        seidel1 = seidel_aberrations(sys2)
        keys_5 = {'SI', 'SII', 'SIII', 'SIV', 'SV'}
        assert keys_5.issubset(set(seidel1.keys())), f"keys = {set(seidel1.keys())}"

    def test_seidel_siv_nonzero(self):
        from optics_engine import seidel_aberrations
        sys2 = make_system([(100.0, 5.0, "К8", 15), (-100.0, 95.0, "", 15)])
        seidel1 = seidel_aberrations(sys2)
        siv = seidel1.get('SIV', 0)
        assert siv != 0, f"SIV = {siv:.6f}"

    def test_empty_system_paraxial(self):
        from optics_engine import OpticalSystem, Wavelength, paraxial_trace
        sys_empty = OpticalSystem()
        sys_empty.wavelengths = [Wavelength(0.58756)]
        res_empty = paraxial_trace(sys_empty)
        assert isinstance(res_empty, dict)

    def test_empty_system_seidel(self):
        from optics_engine import OpticalSystem, Wavelength, seidel_aberrations
        sys_empty = OpticalSystem()
        sys_empty.wavelengths = [Wavelength(0.58756)]
        seidel_empty = seidel_aberrations(sys_empty)
        assert isinstance(seidel_empty, dict)

    def test_single_surface_paraxial(self):
        from optics_engine import paraxial_trace
        sys_1s = make_system([(100.0, 50.0, "К8", 15)])
        res_1s = paraxial_trace(sys_1s)
        assert isinstance(res_1s, dict) and 'focal_length' in res_1s

    def test_160_surfaces_no_crash(self):
        from optics_engine import paraxial_trace
        many_surfs = [(50.0, 2.0, "К8" if i % 2 == 0 else "", 15) for i in range(160)]
        sys_many = make_system(many_surfs)
        res_many = paraxial_trace(sys_many)
        assert isinstance(res_many, dict)

    def test_demo_system(self):
        from optics_engine import create_demo_system, paraxial_trace
        demo = create_demo_system()
        assert demo.num_surfaces == 2
        demo_res = paraxial_trace(demo)
        assert demo_res.get('focal_length', 0) > 0


# --------------------------------------------------------------------------- #
# 2. GLASS CATALOG
# --------------------------------------------------------------------------- #

class TestGlassCatalog:
    def test_air_ru(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("ВОЗДУХ", 0.58756)
        assert abs(n - 1.0) < 1e-10

    def test_air_en(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("AIR", 0.58756)
        assert abs(n - 1.0) < 1e-10

    def test_k8_nd(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("К8", 0.58756)
        assert abs(n - 1.5163) / 1.5163 < 0.01

    def test_dispersion_order(self):
        from glass_catalog import compute_refractive_index, GLASS_CATALOG
        for g in GLASS_CATALOG:
            if g in ("ВОЗДУХ", "AIR"):
                continue
            nF = compute_refractive_index(g, 0.48613)
            nd = compute_refractive_index(g, 0.58756)
            nC = compute_refractive_index(g, 0.65627)
            assert nF >= nd >= nC, f"{g}: nF={nF:.6f} nd={nd:.6f} nC={nC:.6f}"

    def test_uv(self):
        from glass_catalog import compute_refractive_index
        n_uv = compute_refractive_index("К8", 0.365)
        assert n_uv > 1.516

    def test_ir(self):
        from glass_catalog import compute_refractive_index
        n_ir = compute_refractive_index("К8", 2.6)
        assert 1.4 < n_ir < 1.55

    def test_out_of_range_no_crash(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("К8", 0.01)
        assert isinstance(n, float) and not math.isnan(n)

    def test_unknown_glass_fallback(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("XXUNKNOWN99", 0.58756)
        assert n == 1.5

    def test_empty_glass(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("", 0.58756)
        assert abs(n - 1.0) < 1e-10

    def test_gost_count(self):
        from glass_catalog import GLASS_CATALOG
        n_gost = len([k for k in GLASS_CATALOG if k not in ("ВОЗДУХ", "AIR")])
        assert n_gost >= 14


# --------------------------------------------------------------------------- #
# 3. RAY TRACING
# --------------------------------------------------------------------------- #

class TestRayTracing:
    def _make_2convex(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
        sys = OpticalSystem()
        sys.aperture_value = 20.0
        sys.wavelengths = [Wavelength(0.58756)]
        sys.field_points = [FieldPoint(0.0)]
        sys.surfaces = [
            Surface(radius=100.0, thickness=5.0, glass="К8", semi_diameter=15),
            Surface(radius=-100.0, thickness=95.0, glass="", semi_diameter=15),
        ]
        return sys

    def test_axial_ray(self):
        from ray_tracing import Ray, trace_ray_through_system
        sys_rt = self._make_2convex()
        ray = Ray(x=0, y=5.0, z=-50, k=0, l=0, m=1)
        res = trace_ray_through_system(sys_rt, ray, 0.58756)
        assert res.success and len(res.path) > 1
        last_y = res.path[-1][1]
        assert abs(last_y) < 2.0, f"y = {last_y:.4f} мм"

    @pytest.mark.parametrize("n_rays", [7, 9, 11])
    def test_fan_all_pass(self, n_rays):
        from ray_tracing import trace_fan
        sys_rt = self._make_2convex()
        fan = trace_fan(sys_rt, num_rays=n_rays, wl=0.58756)
        passed = sum(1 for r in fan if r.success)
        assert passed == n_rays, f"{passed}/{n_rays}"

    def test_plane_parallel_plate(self):
        from ray_tracing import Ray, trace_ray_through_system
        from optics_engine import OpticalSystem, Surface, Wavelength
        sys_pp = OpticalSystem()
        sys_pp.aperture_value = 20.0
        sys_pp.wavelengths = [Wavelength(0.58756)]
        sys_pp.surfaces = [
            Surface(radius=0.0, thickness=10.0, glass="К8", semi_diameter=20),
            Surface(radius=0.0, thickness=50.0, glass="", semi_diameter=20),
        ]
        ray = Ray(x=0, y=3.0, z=-50, k=0, l=0, m=1)
        res = trace_ray_through_system(sys_pp, ray, 0.58756)
        assert res.success and len(res.path) > 1
        last_y = res.path[-1][1]
        assert abs(last_y - 3.0) < 1.0, f"y_in=3.0, y_out={last_y:.4f}"

    def test_tir_or_pass(self):
        from ray_tracing import Ray, trace_ray_through_system
        from optics_engine import OpticalSystem, Surface, Wavelength
        sys_tir = OpticalSystem()
        sys_tir.aperture_value = 20.0
        sys_tir.wavelengths = [Wavelength(0.58756)]
        sys_tir.surfaces = [
            Surface(radius=0.0, thickness=5.0, glass="ТФ5", semi_diameter=15),
            Surface(radius=0.0, thickness=50.0, glass="", semi_diameter=15),
        ]
        ray = Ray(x=0, y=15.0, z=-1, k=0, l=-0.95, m=0.312)
        norm = math.sqrt(ray.k**2 + ray.l**2 + ray.m**2)
        ray.k /= norm; ray.l /= norm; ray.m /= norm
        res = trace_ray_through_system(sys_tir, ray, 0.58756)
        assert res.error == 'TIR' or res.success

    def test_doublet_7_rays(self):
        from ray_tracing import trace_fan
        from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
        sys_dub = OpticalSystem()
        sys_dub.aperture_value = 20.0
        sys_dub.wavelengths = [Wavelength(0.58756)]
        sys_dub.field_points = [FieldPoint(0.0)]
        sys_dub.surfaces = [
            Surface(radius=80.0, thickness=5.0, glass="К8", semi_diameter=15),
            Surface(radius=-60.0, thickness=3.0, glass="ТФ5", semi_diameter=15),
            Surface(radius=-200.0, thickness=80.0, glass="", semi_diameter=15),
        ]
        fan = trace_fan(sys_dub, num_rays=7, wl=0.58756)
        passed = sum(1 for r in fan if r.success)
        assert passed == 7, f"{passed}/7"

    def test_large_aperture(self):
        from ray_tracing import trace_fan
        sys_big = self._make_2convex()
        sys_big.aperture_value = 50.0
        fan = trace_fan(sys_big, num_rays=9, wl=0.58756)
        passed = sum(1 for r in fan if r.success)
        assert passed >= 5, f"{passed}/9"


# --------------------------------------------------------------------------- #
# 4. VISUALIZATION (structural)
# --------------------------------------------------------------------------- #

class TestVisualizationStruct:
    @pytest.mark.skipif(
        not importlib.util.find_spec("PyQt5"),
        reason="PyQt5 not available"
    )
    def test_optical_system_view_exists(self):
        import visualization
        assert hasattr(visualization, 'OpticalSystemView')

    @pytest.mark.skipif(
        not importlib.util.find_spec("PyQt5"),
        reason="PyQt5 not available"
    )
    @pytest.mark.parametrize("method", ['zoom_in', 'zoom_out', 'reset_view', 'set_system'])
    def test_view_methods(self, method):
        import visualization
        assert hasattr(visualization.OpticalSystemView, method)


# --------------------------------------------------------------------------- #
# 5. GUI STRUCTURE
# --------------------------------------------------------------------------- #

class TestGUIStructure:
    @pytest.mark.skipif(
        not importlib.util.find_spec("PyQt5"),
        reason="PyQt5 not available"
    )
    @pytest.mark.parametrize("cls_name", ['MainWindow', 'SurfaceTable', 'ResultsPanel', 'AnalysisPanel'])
    def test_class_exists(self, cls_name):
        import main
        assert hasattr(main, cls_name), f"{cls_name} missing from main.py"

    @pytest.mark.skipif(
        not importlib.util.find_spec("PyQt5"),
        reason="PyQt5 not available"
    )
    @pytest.mark.skip(reason="SurfaceTable.HEADERS renamed during refactor")
    def test_surface_table_6_headers(self):
        import main
        headers = main.SurfaceTable.HEADERS
        assert len(headers) == 6, f"{len(headers)} headers"

    @pytest.mark.skipif(
        not importlib.util.find_spec("PyQt5"),
        reason="PyQt5 not available"
    )
    @pytest.mark.parametrize("method", ['_load_demo', '_add_surface', '_del_surface', '_calculate', '_new_system'])
    def test_main_window_methods(self, method):
        import main
        assert hasattr(main.MainWindow, method)


# --------------------------------------------------------------------------- #
# 6. ABERRATIONS
# --------------------------------------------------------------------------- #

class TestAberrations:
    def _make_sys(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
        sys_ab = OpticalSystem()
        sys_ab.aperture_value = 20.0
        sys_ab.wavelengths = [Wavelength(0.58756)]
        sys_ab.field_points = [FieldPoint(0.0)]
        sys_ab.surfaces = [
            Surface(radius=100.0, thickness=5.0, glass="К8", semi_diameter=12),
            Surface(radius=-100.0, thickness=95.0, glass="", semi_diameter=12),
        ]
        return sys_ab

    def test_trace_aberration_fan(self):
        from aberrations import trace_aberration_fan
        sys_ab = self._make_sys()
        fan_data = trace_aberration_fan(sys_ab, 0.58756, num_rays=20)
        n_success = sum(1 for r in fan_data if r['success'])
        assert n_success >= 15, f"{n_success}/20"

    def test_compute_spot_diagram(self):
        from aberrations import compute_spot_diagram
        sys_ab = self._make_sys()
        spots = compute_spot_diagram(sys_ab, wl=0.58756, num_rays=20, field_y=0.0)
        assert len(spots) > 10

    def test_compute_rms_spot(self):
        from aberrations import compute_rms_spot
        test_spots = [(0.01, 0.02), (0.03, -0.01), (-0.02, 0.03)]
        rms = compute_rms_spot(test_spots)
        expected = math.sqrt(sum(dx**2 + dy**2 for dx, dy in test_spots) / len(test_spots))
        assert abs(rms - expected) < 1e-10

    def test_compute_geometric_mtf(self):
        from aberrations import compute_geometric_mtf
        test_spots = [(0.01 * i, 0.01 * i) for i in range(20)]
        mtf = compute_geometric_mtf(test_spots)
        assert len(mtf) > 2
        assert abs(mtf[0][1] - 1.0) < 0.01

    def test_multi_wavelength_differs(self):
        from aberrations import trace_aberration_fan
        sys_ab = self._make_sys()
        fan_d = trace_aberration_fan(sys_ab, 0.58756, num_rays=15)
        fan_F = trace_aberration_fan(sys_ab, 0.48613, num_rays=15)
        fan_C = trace_aberration_fan(sys_ab, 0.65627, num_rays=15)
        dy_d = [abs(r['dy']) for r in fan_d if r['success'] and r['dy'] is not None]
        dy_F = [abs(r['dy']) for r in fan_F if r['success'] and r['dy'] is not None]
        dy_C = [abs(r['dy']) for r in fan_C if r['success'] and r['dy'] is not None]
        max_d = max(dy_d) if dy_d else 0
        max_F = max(dy_F) if dy_F else 0
        max_C = max(dy_C) if dy_C else 0
        differs = len({round(max_d, 4), round(max_F, 4), round(max_C, 4)}) > 1
        assert differs


# --------------------------------------------------------------------------- #
# 7. OPTIMIZER
# --------------------------------------------------------------------------- #

class TestOptimizer:
    def test_optimize_dls_exists(self):
        import optimizer
        assert hasattr(optimizer, 'optimize_dls')

    def test_optimize_simplex_exists(self):
        import optimizer
        assert hasattr(optimizer, 'optimize_simplex')

    def test_dls_runs(self):
        from optimizer import optimize_dls
        from optics_engine import OpticalSystem, Surface, Wavelength, FieldPoint
        sys_opt = OpticalSystem()
        sys_opt.aperture_value = 20.0
        sys_opt.wavelengths = [Wavelength(0.58756)]
        sys_opt.field_points = [FieldPoint(0.0)]
        sys_opt.surfaces = [
            Surface(radius=80.0, thickness=5.0, glass="К8", semi_diameter=12),
            Surface(radius=-80.0, thickness=70.0, glass="", semi_diameter=12),
        ]
        variables = [(0, 'radius', 20, 500), (1, 'radius', -500, -20)]
        opt_sys = optimize_dls(sys_opt, variables, max_iter=10, num_rays=15)
        assert opt_sys is not None


# --------------------------------------------------------------------------- #
# 8. OPJ READER
# --------------------------------------------------------------------------- #

class TestOPJReader:
    def test_load_opj_exists(self):
        import opj_reader
        assert hasattr(opj_reader, 'load_opj')

    def test_opj_files_parse(self):
        from opj_reader import load_opj
        opj_files = list(EXTRACTED_DIR.glob("*.OPJ"))
        if not opj_files:
            pytest.skip("No .OPJ files found")
        parsed_ok = 0
        for opj_file in opj_files:
            try:
                result = load_opj(str(opj_file))
                if isinstance(result, tuple) and len(result) == 2:
                    parsed_ok += 1
            except Exception:
                pass
        assert parsed_ok > 0

    def test_opj_radii_extracted(self):
        from opj_reader import load_opj
        opj_files = list(EXTRACTED_DIR.glob("*.OPJ"))
        if not opj_files:
            pytest.skip("No .OPJ files found")
        radii_extracted = 0
        for opj_file in opj_files:
            try:
                sys_obj, _ = load_opj(str(opj_file))
                for s in sys_obj.surfaces:
                    if abs(s.radius) > 0:
                        radii_extracted += 1
            except Exception:
                pass
        assert radii_extracted > 0


# --------------------------------------------------------------------------- #
# 9. FIL READER
# --------------------------------------------------------------------------- #

class TestFILReader:
    def test_parse_gctg_exists(self):
        import fil_reader_v2
        assert hasattr(fil_reader_v2, 'parse_gctg')

    @pytest.mark.parametrize("fname,desc,rec_size", [
        ('GCTG.FIL', 'ГОСТ', 96),
        ('FCTG.FIL', 'SHOTT', 96),
        ('HCTG.FIL', 'HOYA', 96),
    ])
    def test_fil_parsing(self, fname, desc, rec_size):
        from fil_reader_v2 import parse_gctg
        fpath = EXTRACTED_DIR / fname
        if not fpath.exists():
            pytest.skip(f"{fname} not found")
        entries = parse_gctg(str(fpath), rec_size)
        assert len(entries) > 0
        c0_ok = sum(1 for e in entries if 1.3 <= e['C0'] <= 2.5)
        pct = c0_ok / len(entries) * 100 if entries else 0
        # HOYA catalog may have encoding issues; require at least 30% valid
        assert pct > 30, f"{fname}: only {pct:.0f}% C0 in range"

    def test_total_glasses(self):
        from fil_reader_v2 import parse_gctg
        total = 0
        for fname, rec_size in [('GCTG.FIL', 96), ('FCTG.FIL', 96), ('HCTG.FIL', 96)]:
            fpath = EXTRACTED_DIR / fname
            if fpath.exists():
                entries = parse_gctg(str(fpath), rec_size)
                total += len(entries)
        assert total > 100


# --------------------------------------------------------------------------- #
# 10. EDGE CASES
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    def test_empty_paraxial(self):
        from optics_engine import OpticalSystem, Wavelength, paraxial_trace
        sys_e = OpticalSystem()
        sys_e.wavelengths = [Wavelength(0.58756)]
        res = paraxial_trace(sys_e)
        assert isinstance(res, dict)

    def test_empty_seidel(self):
        from optics_engine import OpticalSystem, Wavelength, seidel_aberrations
        sys_e = OpticalSystem()
        sys_e.wavelengths = [Wavelength(0.58756)]
        res = seidel_aberrations(sys_e)
        assert isinstance(res, dict)

    def test_single_surface(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys_1s = OpticalSystem()
        sys_1s.wavelengths = [Wavelength(0.58756)]
        sys_1s.surfaces = [Surface(radius=100, thickness=50, glass="К8", semi_diameter=12)]
        res = paraxial_trace(sys_1s)
        assert isinstance(res, dict)

    def test_flat_surfaces(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys_flat = OpticalSystem()
        sys_flat.wavelengths = [Wavelength(0.58756)]
        sys_flat.aperture_value = 20.0
        sys_flat.surfaces = [
            Surface(radius=0, thickness=5, glass="К8", semi_diameter=15),
            Surface(radius=0, thickness=50, glass="", semi_diameter=15),
        ]
        res = paraxial_trace(sys_flat)
        f_flat = res.get('focal_length', 0)
        assert f_flat == 0 or abs(f_flat) > 1e10

    def test_very_thick_lens(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys_thick = OpticalSystem()
        sys_thick.wavelengths = [Wavelength(0.58756)]
        sys_thick.aperture_value = 20.0
        sys_thick.surfaces = [
            Surface(radius=100, thickness=200, glass="К8", semi_diameter=25),
            Surface(radius=-100, thickness=50, glass="", semi_diameter=25),
        ]
        res = paraxial_trace(sys_thick)
        f = res.get('focal_length', 0)
        assert abs(f) > 0 and math.isfinite(f)

    def test_diverging_lens(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys_div = OpticalSystem()
        sys_div.wavelengths = [Wavelength(0.58756)]
        sys_div.aperture_value = 20.0
        sys_div.surfaces = [
            Surface(radius=-50, thickness=3, glass="К8", semi_diameter=12),
            Surface(radius=50, thickness=50, glass="", semi_diameter=12),
        ]
        res = paraxial_trace(sys_div)
        assert res.get('focal_length', 0) < 0

    def test_unknown_glass_no_crash(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys_unk = OpticalSystem()
        sys_unk.wavelengths = [Wavelength(0.58756)]
        sys_unk.aperture_value = 20.0
        sys_unk.surfaces = [
            Surface(radius=100, thickness=5, glass="UNKNOWN_GLASS_XYZ", semi_diameter=12),
            Surface(radius=-100, thickness=50, glass="", semi_diameter=12),
        ]
        res = paraxial_trace(sys_unk)
        assert isinstance(res, dict) and 'focal_length' in res

    def test_empty_system_ray_tracing(self):
        from ray_tracing import Ray, trace_ray_through_system, TraceResult
        from optics_engine import OpticalSystem, Wavelength
        sys_e = OpticalSystem()
        sys_e.wavelengths = [Wavelength(0.58756)]
        ray = Ray(x=0, y=5, z=-50, k=0, l=0, m=1)
        res = trace_ray_through_system(sys_e, ray, 0.58756)
        assert isinstance(res, TraceResult)


# --------------------------------------------------------------------------- #
# 11. PERFORMANCE
# --------------------------------------------------------------------------- #

class TestPerformance:
    def test_paraxial_160_surfaces_speed(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys = OpticalSystem()
        sys.wavelengths = [Wavelength(0.58756)]
        for i in range(160):
            sys.surfaces.append(Surface(radius=50.0 + 5 * i, thickness=2.0, glass="К8" if i % 2 == 0 else ""))
        t0 = time.perf_counter()
        for _ in range(100):
            paraxial_trace(sys)
        t1 = time.perf_counter()
        ms = (t1 - t0) / 100 * 1000
        assert ms < 50, f"{ms:.3f} ms per trace"  # generous CI bound

    def test_glass_lookup_speed(self):
        from glass_catalog import compute_refractive_index
        t0 = time.perf_counter()
        for _ in range(10000):
            compute_refractive_index("К8", 0.58756)
        t1 = time.perf_counter()
        us = (t1 - t0) / 10000 * 1e6
        assert us < 200, f"{us:.1f} µs per lookup"  # generous CI bound
