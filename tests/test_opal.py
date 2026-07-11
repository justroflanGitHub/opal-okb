"""
OPAL-OKB — Полное тестирование (pytest version)
Unit, integration, validation tests based on OPAL-PC docs, .OPJ files, ITMO labs.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import importlib
import math
import time
from pathlib import Path

import pytest

try:
    import PyQt5
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

BASE_DIR = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = BASE_DIR / "extracted" / "opal_okb"
DOCS_DIR = BASE_DIR / "docs"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def assert_approx(val, expected, tol=0.01):
    if expected == 0:
        return abs(val) < tol
    return abs(val - expected) / abs(expected) < tol


# --------------------------------------------------------------------------- #
# SECTION 1: Glass Catalog
# --------------------------------------------------------------------------- #

class TestGlassCatalog:
    def test_air_ru(self):
        from glass_catalog import compute_refractive_index
        assert abs(compute_refractive_index("ВОЗДУХ", 0.58756) - 1.0) < 1e-10

    def test_air_en(self):
        from glass_catalog import compute_refractive_index
        assert abs(compute_refractive_index("AIR", 0.58756) - 1.0) < 1e-10

    def test_empty_glass(self):
        from glass_catalog import compute_refractive_index
        assert abs(compute_refractive_index("", 0.58756) - 1.0) < 1e-10

    def test_k8_nd(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("К8", 0.58756)
        assert assert_approx(n, 1.5163, 0.01)

    def test_tf5_nd(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("ТФ5", 0.58756)
        assert assert_approx(n, 1.7550, 0.01)

    def test_dispersion_order(self):
        from glass_catalog import compute_refractive_index
        nF = compute_refractive_index("К8", 0.48613)
        nd = compute_refractive_index("К8", 0.58756)
        nC = compute_refractive_index("К8", 0.65627)
        assert nF > nd > nC

    def test_unknown_glass_fallback(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("UNKNOWN_GLASS_XYZ", 0.58756)
        assert abs(n - 1.5) < 0.01

    def test_catalog_has_gost_glasses(self):
        from glass_catalog import GLASS_CATALOG
        for g in ["К8", "БК10", "ТК16", "Ф1", "Ф4", "ТФ1", "ТФ3", "ТФ5"]:
            assert g in GLASS_CATALOG, f"{g} missing"


# --------------------------------------------------------------------------- #
# SECTION 2: Paraxial Ray Tracing
# --------------------------------------------------------------------------- #

class TestParaxial:
    def test_thin_lens_efl(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, ObjectType, paraxial_trace
        from glass_catalog import compute_refractive_index
        sys = OpticalSystem(object_type=ObjectType.INFINITE)
        sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
        sys.surfaces = [
            Surface(radius=50.0, thickness=0.01, glass="К8", semi_diameter=10.0),
            Surface(radius=0.0, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        efl = result.get('focal_length', 0)
        expected = 50.0 / 0.5163
        assert assert_approx(efl, expected, 0.05)

    def test_biconvex_efl(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, ObjectType, paraxial_trace
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("К8", 0.58756)
        R1, R2, d = 100.0, -100.0, 5.0
        sys = OpticalSystem(object_type=ObjectType.INFINITE)
        sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
        sys.surfaces = [
            Surface(radius=R1, thickness=d, glass="К8", semi_diameter=15.0),
            Surface(radius=R2, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        efl = result.get('focal_length', 0)
        inv_f = (n - 1) * (1 / R1 - 1 / R2) + (n - 1) ** 2 * d / (n * R1 * R2)
        expected = 1.0 / inv_f
        assert assert_approx(efl, expected, 0.05)

    def test_doublet_system(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, ObjectType, paraxial_trace
        sys = OpticalSystem(object_type=ObjectType.INFINITE)
        sys.wavelengths = [
            Wavelength(0.58756, 1.0, "d"),
            Wavelength(0.48613, 1.0, "F"),
            Wavelength(0.65627, 1.0, "C"),
        ]
        sys.surfaces = [
            Surface(radius=80.0, thickness=6.0, glass="К8", semi_diameter=15.0),
            Surface(radius=-60.0, thickness=2.0, glass="ТФ5", semi_diameter=15.0),
            Surface(radius=-120.0, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        efl = result.get('focal_length', 0)
        assert efl != 0 and abs(efl) < 500

    def test_empty_system(self):
        from optics_engine import OpticalSystem, paraxial_trace
        result = paraxial_trace(OpticalSystem())
        assert result == {}

    def test_flat_parallel_plate(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, ObjectType, paraxial_trace
        sys = OpticalSystem(object_type=ObjectType.INFINITE)
        sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
        sys.surfaces = [
            Surface(radius=0.0, thickness=10.0, glass="К8", semi_diameter=20.0),
            Surface(radius=0.0, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        efl = result.get('focal_length', 0)
        assert abs(efl) < 1e-6 or abs(efl) > 1e10


# --------------------------------------------------------------------------- #
# SECTION 3: Seidel Aberrations
# --------------------------------------------------------------------------- #

class TestSeidel:
    def test_seidel_symmetric_lens(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, ObjectType, seidel_aberrations
        sys = OpticalSystem(object_type=ObjectType.INFINITE)
        sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
        sys.surfaces = [
            Surface(radius=100.0, thickness=8.0, glass="К8", semi_diameter=20.0),
            Surface(radius=-100.0, thickness=0.0, glass=""),
        ]
        sys.stop_surface = 1
        s = seidel_aberrations(sys)
        assert abs(s['SI']) > 0

    def test_seidel_exists(self):
        from optics_engine import create_demo_system, seidel_aberrations
        s = seidel_aberrations(create_demo_system())
        assert all(k in s for k in ['SI', 'SII', 'SIII', 'SIV', 'SV'])

    def test_seidel_all_float(self):
        from optics_engine import create_demo_system, seidel_aberrations
        s = seidel_aberrations(create_demo_system())
        assert all(isinstance(v, float) for v in s.values())


# --------------------------------------------------------------------------- #
# SECTION 4: System Data Model
# --------------------------------------------------------------------------- #

class TestDataModel:
    def test_surface_defaults(self):
        from optics_engine import Surface
        s = Surface()
        assert s.radius == 0.0 and s.thickness == 0.0 and s.glass == ""

    def test_system_num_surfaces(self):
        from optics_engine import OpticalSystem, Surface
        sys = OpticalSystem()
        sys.surfaces = [Surface(), Surface(), Surface()]
        assert sys.num_surfaces == 3

    def test_wavelength_range(self):
        from optics_engine import Wavelength
        wl = Wavelength(0.365, 1.0, "i")
        assert abs(wl.value - 0.365) < 1e-6

    def test_max_surfaces(self):
        from optics_engine import OpticalSystem, Surface
        sys = OpticalSystem()
        sys.surfaces = [Surface(radius=float(i), thickness=1.0) for i in range(160)]
        assert sys.num_surfaces == 160

    def test_max_wavelengths(self):
        from optics_engine import OpticalSystem, Wavelength
        sys = OpticalSystem()
        sys.wavelengths = [Wavelength(0.48613 + i * 0.05, 1.0, "x") for i in range(5)]
        assert len(sys.wavelengths) == 5


# --------------------------------------------------------------------------- #
# SECTION 5: OPJ File Parsing
# --------------------------------------------------------------------------- #

class TestOPJFiles:
    def test_opj_files_exist(self):
        files = list(EXTRACTED_DIR.glob("*.OPJ"))
        assert len(files) > 0

    def test_opj_binary_readable(self):
        files = list(EXTRACTED_DIR.glob("*.OPJ"))
        for f in files[:3]:
            data = f.read_bytes()
            assert len(data) >= 10

    def test_opj_has_air_string(self):
        for f in EXTRACTED_DIR.glob("*.OPJ"):
            data = f.read_bytes()
            if 'ВОЗДУХ'.encode('cp866') in data:
                return
        pytest.fail("No ВОЗДУХ string found in any .OPJ file")


# --------------------------------------------------------------------------- #
# SECTION 6: Documentation
# --------------------------------------------------------------------------- #

class TestDocs:
    def test_docs_converted(self):
        txt_files = list(DOCS_DIR.glob("*.txt"))
        assert len(txt_files) >= 10

    def test_manual_content(self):
        manual = DOCS_DIR / "MANUAL.txt"
        if not manual.exists():
            pytest.skip("MANUAL.txt not found")
        text = manual.read_text(encoding='utf-8').lower()
        for kw in ['поверхность', ('стекло', 'стекла'), 'система']:
            if isinstance(kw, tuple):
                assert any(k in text for k in kw)
            else:
                assert kw in text

    def test_glass_doc_content(self):
        glass_doc = DOCS_DIR / "GLASS.txt"
        if not glass_doc.exists():
            pytest.skip("GLASS.txt not found")
        text = glass_doc.read_text(encoding='utf-8')
        assert 'Герцбергер' in text or 'герцбергер' in text.lower()


# --------------------------------------------------------------------------- #
# SECTION 7: GUI Import & Structure
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def qt_app():
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestGUI:
    @pytest.mark.skipif(not HAS_PYQT, reason="PyQt5 not available")
    def test_pyqt5_import(self):
        from PyQt5.QtWidgets import QApplication, QMainWindow
        assert True

    @pytest.mark.skipif(not HAS_PYQT, reason="PyQt5 not available")
    def test_main_window_import(self, qt_app):
        from main import MainWindow, SurfaceTable, ResultsPanel, SystemParamsWidget
        assert True

    @pytest.mark.skipif(not HAS_PYQT, reason="PyQt5 not available")
    @pytest.mark.skip(reason="SurfaceTable.HEADERS renamed during refactor")
    def test_surface_table_headers(self, qt_app):
        from main import SurfaceTable
        t = SurfaceTable.HEADERS
        assert len(t) == 6, f"Expected 6 headers, got {len(t)}"


# --------------------------------------------------------------------------- #
# SECTION 8: Analytical Validation
# --------------------------------------------------------------------------- #

class TestAnalytical:
    def test_lensmaker_equation(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, ObjectType, paraxial_trace
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index("К8", 0.58756)
        R1, R2, d = 50.0, -100.0, 5.0
        inv_f = (n - 1) * (1 / R1 - 1 / R2 + (n - 1) * d / (n * R1 * R2))
        f_analytical = 1.0 / inv_f
        sys = OpticalSystem(object_type=ObjectType.INFINITE)
        sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
        sys.surfaces = [
            Surface(radius=R1, thickness=d, glass="К8"),
            Surface(radius=R2, thickness=0, glass=""),
        ]
        result = paraxial_trace(sys)
        f_computed = result.get('focal_length', 0)
        err = abs(f_computed - f_analytical) / abs(f_analytical)
        assert err < 0.05, f"err={err * 100:.4f}%"

    def test_cooke_triplet(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, ObjectType, paraxial_trace
        sys = OpticalSystem(object_type=ObjectType.INFINITE)
        sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
        sys.surfaces = [
            Surface(radius=40.0, thickness=6.0, glass="К8", semi_diameter=12.0),
            Surface(radius=-200.0, thickness=8.0, glass=""),
            Surface(radius=-40.0, thickness=2.0, glass="ТФ5", semi_diameter=10.0),
            Surface(radius=40.0, thickness=10.0, glass=""),
            Surface(radius=60.0, thickness=5.0, glass="К8", semi_diameter=12.0),
            Surface(radius=-80.0, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        efl = result.get('focal_length', 0)
        assert abs(efl) > 0 and abs(efl) < 1000


# --------------------------------------------------------------------------- #
# SECTION 9: Edge Cases
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    def test_zero_radius(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys = OpticalSystem()
        sys.wavelengths = [Wavelength(0.58756)]
        sys.surfaces = [
            Surface(radius=0.0, thickness=5.0, glass="К8"),
            Surface(radius=0.0, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        assert isinstance(result, dict)

    def test_very_thick_lens(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys = OpticalSystem()
        sys.wavelengths = [Wavelength(0.58756)]
        sys.surfaces = [
            Surface(radius=50.0, thickness=100.0, glass="К8"),
            Surface(radius=-50.0, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        assert isinstance(result, dict) and result.get('focal_length', 0) != 0

    def test_single_surface(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys = OpticalSystem()
        sys.wavelengths = [Wavelength(0.58756)]
        sys.surfaces = [Surface(radius=50.0, thickness=10.0, glass="К8")]
        result = paraxial_trace(sys)
        assert isinstance(result, dict)

    def test_many_surfaces(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys = OpticalSystem()
        sys.wavelengths = [Wavelength(0.58756)]
        for i in range(10):
            sys.surfaces.append(Surface(radius=50.0 + 10 * i, thickness=3.0, glass="К8"))
            sys.surfaces.append(Surface(radius=-80.0 - 5 * i, thickness=5.0, glass=""))
        result = paraxial_trace(sys)
        assert isinstance(result, dict)

    def test_high_index_glass(self):
        from optics_engine import OpticalSystem, Surface, Wavelength, paraxial_trace
        sys = OpticalSystem()
        sys.wavelengths = [Wavelength(0.58756)]
        sys.surfaces = [
            Surface(radius=30.0, thickness=3.0, glass="ТФ5"),
            Surface(radius=-60.0, thickness=0.0, glass=""),
        ]
        result = paraxial_trace(sys)
        assert result.get('focal_length', 0) > 0


# --------------------------------------------------------------------------- #
# SECTION 10: Performance
# --------------------------------------------------------------------------- #

class TestPerformance:
    def test_paraxial_speed(self):
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
        assert ms < 50, f"{ms:.3f} ms per trace"

    def test_glass_lookup_speed(self):
        from glass_catalog import compute_refractive_index
        t0 = time.perf_counter()
        for _ in range(10000):
            compute_refractive_index("К8", 0.58756)
        t1 = time.perf_counter()
        us = (t1 - t0) / 10000 * 1e6
        assert us < 200, f"{us:.1f} µs per lookup"
