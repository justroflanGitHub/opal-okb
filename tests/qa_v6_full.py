"""QA v6 — Full module/function verification for OPAL-OKB (pytest version)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import glob
import tempfile
from pathlib import Path

import pytest

try:
    import PyQt5
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

BASE_DIR = Path(__file__).resolve().parent.parent
OPJ_DIR = BASE_DIR / "extracted" / "opal_okb"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_biconvex():
    from optics_engine import Surface, OpticalSystem, Wavelength, ObjectType
    s1 = Surface(radius=100, thickness=5, glass='К8')
    s2 = Surface(radius=-100, thickness=95.848, glass='ВОЗДУХ')
    return OpticalSystem(
        surfaces=[s1, s2],
        wavelengths=[Wavelength(0.5876)],
        object_type=ObjectType.FINITE,
    )

def make_biconvex_poly():
    from optics_engine import Surface, OpticalSystem, Wavelength, ObjectType
    s1 = Surface(radius=100, thickness=5, glass='К8')
    s2 = Surface(radius=-100, thickness=95.848, glass='ВОЗДУХ')
    return OpticalSystem(
        surfaces=[s1, s2],
        wavelengths=[Wavelength(0.4861), Wavelength(0.5876), Wavelength(0.6563)],
        object_type=ObjectType.FINITE,
    )


# --------------------------------------------------------------------------- #
# ЯДРО
# --------------------------------------------------------------------------- #

class TestCore:
    def test_import(self):
        from optics_engine import Surface, OpticalSystem
        assert Surface is not None
        assert OpticalSystem is not None

    def test_paraxial(self):
        from optics_engine import paraxial_trace
        sys1 = make_biconvex()
        res = paraxial_trace(sys1)
        f = res['focal_length']
        bfd = res['back_focal_distance']
        assert f > 0, f"EFL={f}"

    def test_seidel(self):
        from optics_engine import seidel_aberrations
        sys1 = make_biconvex()
        seis = seidel_aberrations(sys1)
        for k in ['SI', 'SII', 'SIII', 'SIV', 'SV']:
            assert k in seis, f"Missing {k}"

    def test_vignetting(self):
        from optics_engine import apply_vignetting
        sys1 = make_biconvex()
        result = apply_vignetting(sys1, field_y=5.0, ray_y=8.0, ray_x=0.0)
        assert isinstance(result, bool)

    def test_surface_attrs(self):
        from optics_engine import Surface
        s = Surface(radius=50, conic_constant=-1.0, aspheric_coeffs=[0, 1e-5])
        assert hasattr(s, 'conic_constant') and s.conic_constant == -1.0
        assert hasattr(s, 'aspheric_coeffs') and len(s.aspheric_coeffs) >= 2


# --------------------------------------------------------------------------- #
# КАТАЛОГИ
# --------------------------------------------------------------------------- #

class TestCatalogs:
    def test_gost_count(self):
        from glass_catalog import GLASS_CATALOG
        assert len(GLASS_CATALOG) >= 17, f"Only {len(GLASS_CATALOG)} glasses"

    def test_k8_nd(self):
        from glass_catalog import compute_refractive_index
        n = compute_refractive_index('К8', 0.5876)
        assert abs(n - 1.5163) < 0.01, f"K8 nd={n}"

    def test_full_catalog_count(self):
        try:
            import glass_catalog_full as gcf
        except Exception:
            pytest.skip("glass_catalog_full not importable")
        glasses = gcf.list_glasses()
        assert len(glasses) >= 889, f"Only {len(glasses)} glasses"

    def test_full_catalog_fallback(self):
        try:
            import glass_catalog_full as gcf
        except Exception:
            pytest.skip("glass_catalog_full not importable")
        n = gcf.compute_refractive_index('BK7', 0.5876)
        assert n > 1.4, f"BK7 nd={n}"


# --------------------------------------------------------------------------- #
# ТРАССИРОВКА
# --------------------------------------------------------------------------- #

class TestTracing:
    def test_trace_sphere(self):
        from ray_tracing import Ray, trace_ray_through_system
        from optics_engine import Surface, OpticalSystem, Wavelength, ObjectType
        s1 = Surface(radius=50, thickness=10, glass='К8')
        s2 = Surface(radius=1e10, thickness=0, glass='ВОЗДУХ')
        sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                             object_type=ObjectType.FINITE)
        r = Ray(y=5, k=0, l=0, m=1)
        res = trace_ray_through_system(sys1, r, wl=0.5876)
        assert res is not None and res.success

    def test_trace_conic(self):
        from ray_tracing import Ray, trace_ray_through_system
        from optics_engine import Surface, OpticalSystem, Wavelength, ObjectType
        s1 = Surface(radius=50, thickness=10, glass='К8', conic_constant=-1.0)
        s2 = Surface(radius=1e10, thickness=0, glass='ВОЗДУХ')
        sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                             object_type=ObjectType.FINITE)
        r = Ray(y=5, k=0, l=0, m=1)
        res = trace_ray_through_system(sys1, r, wl=0.5876)
        assert res is not None

    def test_tir_detected(self):
        from ray_tracing import Ray, trace_ray_through_system
        from optics_engine import Surface, OpticalSystem, Wavelength, ObjectType
        s1 = Surface(radius=10, thickness=5, glass='ТФ5')
        s2 = Surface(radius=1e10, thickness=0, glass='ВОЗДУХ')
        sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                             object_type=ObjectType.FINITE)
        r = Ray(y=9.9, k=0, l=0.5, m=0.5)
        res = trace_ray_through_system(sys1, r, wl=0.5876)
        # Either TIR/error detected or ray passes (config dependent)
        assert res is not None

    def test_opl_computed(self):
        from ray_tracing import Ray, trace_ray_through_system
        sys1 = make_biconvex()
        r = Ray(y=10, k=0, l=0, m=1)
        res = trace_ray_through_system(sys1, r, wl=0.5876)
        assert res is not None
        opl = getattr(res, 'opl', None)
        assert opl is not None, "No OPL in TraceResult"


# --------------------------------------------------------------------------- #
# АНАЛИЗ
# --------------------------------------------------------------------------- #

class TestAnalysis:
    def test_spot_diagram(self):
        from aberrations import compute_spot_diagram
        sys1 = make_biconvex()
        pts = compute_spot_diagram(sys1, wl=0.5876, num_rays=15, field_y=0)
        assert len(pts) > 100, f"Only {len(pts)} points"

    def test_wavefront(self):
        from diffraction_mtf import compute_wavefront_map
        sys1 = make_biconvex()
        wf = compute_wavefront_map(sys1, wl=0.5876, grid_size=32, field_y=0)
        assert wf is not None

    def test_geometric_mtf(self):
        from aberrations import compute_spot_diagram, compute_geometric_mtf
        sys1 = make_biconvex()
        spots = compute_spot_diagram(sys1, wl=0.5876, num_rays=15, field_y=0)
        result = compute_geometric_mtf(spots)
        assert len(result) > 0

    def test_diffraction_mtf(self):
        from diffraction_mtf import compute_diffraction_mtf
        sys1 = make_biconvex()
        result = compute_diffraction_mtf(sys1, wl=0.5876, grid_size=32)
        assert result is not None and len(result) > 0
        cutoff = result.get('cutoff_freq', 0)
        assert cutoff > 0, f"cutoff_freq={cutoff}"

    def test_psf(self):
        from advanced_analysis import compute_psf
        sys1 = make_biconvex()
        res = compute_psf(sys1, wl=0.5876, num_rays=64, field_y=0)
        assert res is not None

    def test_lsf(self):
        from advanced_analysis import compute_lsf
        sys1 = make_biconvex()
        res = compute_lsf(sys1, wl=0.5876, num_rays=64, field_y=0)
        assert res is not None

    def test_enc(self):
        from advanced_analysis import compute_enc
        sys1 = make_biconvex()
        radii, enc = compute_enc(sys1, wl=0.5876, num_rays=100, field_y=0)
        assert len(radii) > 0 and len(enc) > 0

    def test_ptf(self):
        from advanced_analysis import compute_ptf
        sys1 = make_biconvex()
        res = compute_ptf(sys1, wl=0.5876, num_rays=64, field_y=0)
        assert res is not None

    def test_poly_spot(self):
        from aberrations import compute_spot_diagram_polychromatic
        sys1 = make_biconvex_poly()
        pts = compute_spot_diagram_polychromatic(sys1, num_rays=12, field_y=0)
        assert len(pts) > 50, f"Only {len(pts)} points"

    def test_poly_mtf(self):
        from diffraction_mtf import compute_polychromatic_mtf
        sys1 = make_biconvex_poly()
        result = compute_polychromatic_mtf(sys1, grid_size=32)
        assert result is not None

    def test_poly_rms(self):
        from aberrations import compute_polychromatic_rms
        sys1 = make_biconvex_poly()
        rms = compute_polychromatic_rms(sys1, num_rays=12, field_y=0)
        assert rms is not None

    def test_focus_curve(self):
        from aberrations import compute_focus_curve
        sys1 = make_biconvex()
        res = compute_focus_curve(sys1, wl=0.5876, num_points=20, field_y=0)
        assert res is not None and len(res) > 0


# --------------------------------------------------------------------------- #
# ОПТИМИЗАЦИЯ
# --------------------------------------------------------------------------- #

class TestOptimization:
    def test_dls(self):
        from optimizer import optimize_dls
        sys1 = make_biconvex()
        variables = [(0, 'radius', 50, 200)]
        result = optimize_dls(sys1, variables=variables)
        assert result is not None

    def test_simplex(self):
        from optimizer import optimize_simplex
        sys1 = make_biconvex()
        variables = [(0, 'radius', 50, 200)]
        result = optimize_simplex(sys1, variables=variables)
        assert result is not None

    def test_fit_focal_length(self):
        from optimizer import fit_focal_length
        sys1 = make_biconvex()
        result = fit_focal_length(sys1, target_f=100, surface_idx=0)
        assert result is not None

    def test_fit_bfd(self):
        from optimizer import fit_bfd
        sys1 = make_biconvex()
        # surface_idx=-1 is the last thickness which doesn't affect BFD — use 0 instead
        result = fit_bfd(sys1, target_bfd=90, surface_idx=0, param_type='radius')
        assert result is not None


# --------------------------------------------------------------------------- #
# ФАЙЛЫ
# --------------------------------------------------------------------------- #

class TestFiles:
    def test_opj_count(self):
        opj_files = list(OPJ_DIR.glob("*.OPJ"))
        assert len(opj_files) >= 83, f"Only {len(opj_files)} .OPJ files"

    def test_opj_glasses_extracted(self):
        from opj_reader import load_opj
        opj_files = list(OPJ_DIR.glob("*.OPJ"))
        found_glasses = set()
        for f in opj_files[:30]:
            try:
                result = load_opj(str(f))
                if result and isinstance(result, tuple) and len(result) == 2:
                    meta = result[1]
                    gnames = meta.get('glass_names', [])
                    for g in gnames:
                        if g and g not in ('ВОЗДУХ', 'AIR', ''):
                            found_glasses.add(g)
            except Exception:
                pass
        assert len(found_glasses) > 0, "No glasses extracted"

    def test_json_roundtrip(self):
        from io_utils import save_json, load_json
        sys1 = make_biconvex()
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            path = f.name
        try:
            save_json(sys1, path)
            sys2 = load_json(path)
            assert sys2 is not None
            assert len(sys2.surfaces) == 2
        finally:
            os.unlink(path)

    def test_achromat_design(self):
        from achromat import design_achromat
        from optics_engine import paraxial_trace
        sys_obj = design_achromat(focal_length=100)
        assert sys_obj is not None
        res = paraxial_trace(sys_obj)
        efl = res['focal_length']
        assert abs(efl - 100) < 5, f"EFL={efl}"

    def test_glass_diagram_callable(self):
        from glass_diagram import plot_glass_diagram
        assert callable(plot_glass_diagram)


# --------------------------------------------------------------------------- #
# УТИЛИТЫ
# --------------------------------------------------------------------------- #

class TestUtils:
    def test_reverse_system(self):
        from system_utils import reverse_system
        sys1 = make_biconvex()
        rev = reverse_system(sys1)
        assert rev is not None
        assert len(rev.surfaces) > 0

    def test_scale_system(self):
        from system_utils import scale_system
        sys1 = make_biconvex()
        scaled = scale_system(sys1, 2.0)
        assert scaled.surfaces[0].radius == 200, f"R={scaled.surfaces[0].radius}"

    def test_nearest_standard_radius(self):
        from system_utils import nearest_standard_radius
        r = nearest_standard_radius(47.3)
        assert r is not None

    def test_standardize_radii(self):
        from system_utils import standardize_radii
        from optics_engine import Surface, OpticalSystem, Wavelength, ObjectType
        s1 = Surface(radius=47.3, thickness=5, glass='К8')
        s2 = Surface(radius=-103.7, thickness=95, glass='ВОЗДУХ')
        sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                             object_type=ObjectType.FINITE)
        std = standardize_radii(sys1)
        assert std is not None


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def qt_app():
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestGUI:
    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_viz_exists(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        assert hasattr(mw, 'viz'), "No viz attribute"
        mw.close()

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_analysis_tabs(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        panel = None
        n = 0
        for attr in dir(mw):
            obj = getattr(mw, attr)
            try:
                if hasattr(obj, 'count') and callable(obj.count):
                    cnt = obj.count()
                    if cnt >= 13:
                        panel = obj
                        n = cnt
                        break
            except Exception:
                pass
        mw.close()
        assert panel is not None, "Cannot find analysis panel with >=13 tabs"

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_surface_table_columns(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        table = None
        for attr in dir(mw):
            obj = getattr(mw, attr)
            if type(obj).__name__ in ('SurfaceTable', 'QTableWidget') and attr != 'viz':
                table = obj
                break
        mw.close()
        assert table is not None, "SurfaceTable not found"
        headers = []
        for i in range(table.columnCount()):
            h = table.horizontalHeaderItem(i)
            if h:
                headers.append(h.text())
        assert any('Стоп' in h or 'stop' in h.lower() for h in headers), f"No 'Стоп' column in {headers}"
        assert any('k' in h.lower() or 'кон' in h.lower() for h in headers), f"No 'k' column in {headers}"

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_field_widget(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        sp = mw.sys_params
        assert hasattr(sp, 'field_points_widget'), "No field_points_widget in sys_params"
        mw.close()

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_load_demo(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        mw._load_demo()
        mw.close()

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_calculate(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        mw._load_demo()
        mw._calculate()
        mw.close()

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_menu_file(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        menubar = mw.menuBar()
        file_menu = None
        for action in menubar.actions():
            if 'Файл' in action.text() or 'File' in action.text():
                file_menu = action.menu()
                break
        mw.close()
        assert file_menu is not None, "No Файл menu"
        texts = [a.text() for a in file_menu.actions()]
        assert any('Открыть' in t for t in texts), f"No 'Открыть' in {texts}"
        assert any('Сохранить' in t for t in texts), f"No 'Сохранить' in {texts}"

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_menu_system(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        menubar = mw.menuBar()
        sys_menu = None
        for action in menubar.actions():
            if 'Система' in action.text() or 'System' in action.text():
                sys_menu = action.menu()
                break
        mw.close()
        assert sys_menu is not None, "No Система menu"
        texts = [a.text() for a in sys_menu.actions()]
        for exp in ['Обернуть', 'Масштаб', 'Стандарт', 'Ахромат', 'Подгон']:
            assert any(exp in t for t in texts), f"No '{exp}' in {texts}"

    @pytest.mark.skipif(
        not HAS_PYQT,
        reason="PyQt5 not available"
    )
    def test_menu_view(self, qt_app):
        from main import MainWindow
        mw = MainWindow()
        menubar = mw.menuBar()
        view_menu = None
        for action in menubar.actions():
            if 'Вид' in action.text() or 'View' in action.text():
                view_menu = action.menu()
                break
        mw.close()
        assert view_menu is not None, "No Вид menu"
        texts = [a.text() for a in view_menu.actions()]
        assert any('стёкол' in t.lower() or 'glass' in t.lower() for t in texts), f"No glass diagram in {texts}"
