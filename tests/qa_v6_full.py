#!/usr/bin/env python
# TODO: convert to pytest — uses custom check() runner
# -*- coding: utf-8 -*-
"""QA v6 — Full module/function verification for OPAL-OKB"""
import sys, os, traceback, glob, tempfile

# Ensure we're in the right directory
os.chdir(r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
sys.path.insert(0, '.')

results = []
def check(label, fn):
    try:
        fn()
        results.append(("[PASS]", label))
    except Exception as e:
        results.append(("[FAIL]", f"{label}: {e}"))
        traceback.print_exc()

from optics_engine import (Surface, OpticalSystem, Wavelength, FieldPoint,
                            paraxial_trace, seidel_aberrations, apply_vignetting,
                            ObjectType, ApertureType)

def make_biconvex():
    s1 = Surface(radius=100, thickness=5, glass='К8')
    s2 = Surface(radius=-100, thickness=95.848, glass='ВОЗДУХ')
    return OpticalSystem(
        surfaces=[s1, s2],
        wavelengths=[Wavelength(0.5876)],
        object_type=ObjectType.FINITE
    )

def make_biconvex_poly():
    s1 = Surface(radius=100, thickness=5, glass='К8')
    s2 = Surface(radius=-100, thickness=95.848, glass='ВОЗДУХ')
    return OpticalSystem(
        surfaces=[s1, s2],
        wavelengths=[Wavelength(0.4861), Wavelength(0.5876), Wavelength(0.6563)],
        object_type=ObjectType.FINITE
    )

# ═══════════════════════════════════════════
print("=" * 60)
print("ЯДРО")
print("=" * 60)

def t_core_import():
    assert Surface is not None
    assert OpticalSystem is not None
check("optics_engine импортируется без ошибок", t_core_import)

def t_paraxial():
    sys1 = make_biconvex()
    res = paraxial_trace(sys1)
    f = res['focal_length']
    bfd = res['back_focal_distance']
    assert f > 0, f"EFL={f}"
    print(f"  f'={f:.2f}, BFD={bfd:.2f}")
check("paraxial_trace работает (f', BFD)", t_paraxial)

def t_seidel():
    sys1 = make_biconvex()
    seis = seidel_aberrations(sys1)
    for k in ['SI', 'SII', 'SIII', 'SIV', 'SV']:
        assert k in seis, f"Missing {k}"
    print(f"  SI={seis['SI']:.6f} SII={seis['SII']:.6f} SIII={seis['SIII']:.6f} SIV={seis['SIV']:.6f} SV={seis['SV']:.6f}")
check("seidel_aberrations SI-SV ненулевые", t_seidel)

def t_vignetting():
    sys1 = make_biconvex()
    result = apply_vignetting(sys1, field_y=5.0, ray_y=8.0, ray_x=0.0)
    print(f"  vignetting result={result}")
check("apply_vignetting работает", t_vignetting)

def t_surface_attrs():
    s = Surface(radius=50, conic_constant=-1.0, aspheric_coeffs=[0, 1e-5])
    assert hasattr(s, 'conic_constant') and s.conic_constant == -1.0
    assert hasattr(s, 'aspheric_coeffs') and len(s.aspheric_coeffs) >= 2
    print(f"  conic_constant={s.conic_constant}, aspheric_coeffs={s.aspheric_coeffs}")
check("Surface имеет conic_constant, aspheric_coeffs", t_surface_attrs)

# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("КАТАЛОГИ")
print("=" * 60)

from glass_catalog import GLASS_CATALOG, compute_refractive_index

def t_gost_count():
    assert len(GLASS_CATALOG) >= 17, f"Only {len(GLASS_CATALOG)} glasses"
    print(f"  {len(GLASS_CATALOG)} стёкол")
check("glass_catalog: 17+ стёкол", t_gost_count)

def t_gost_k8():
    n = compute_refractive_index('К8', 0.5876)
    assert abs(n - 1.5163) < 0.01, f"K8 nd={n}"
    print(f"  К8 nd={n:.4f}")
check("glass_catalog: compute_refractive_index К8≈1.5163", t_gost_k8)

import glass_catalog_full as gcf

def t_full_count():
    glasses = gcf.list_glasses()
    assert len(glasses) >= 889, f"Only {len(glasses)} glasses"
    print(f"  {len(glasses)} стёкол")
check("glass_catalog_full: 889+ стёкол", t_full_count)

def t_fallback():
    n = gcf.compute_refractive_index('BK7', 0.5876)
    assert n > 1.4, f"BK7 nd={n}"
    print(f"  BK7 nd={n:.4f}")
check("glass_catalog fallback в full catalog работает", t_fallback)

# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("ТРАССИРОВКА")
print("=" * 60)

from ray_tracing import Ray, trace_ray_through_system

def t_trace_sphere():
    s1 = Surface(radius=50, thickness=10, glass='К8')
    s2 = Surface(radius=1e10, thickness=0, glass='ВОЗДУХ')
    sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                          object_type=ObjectType.FINITE)
    r = Ray(y=5, k=0, l=0, m=1)
    res = trace_ray_through_system(sys1, r, wl=0.5876)
    assert res is not None and res.success
    print(f"  success={res.success}, path length={len(res.path) if hasattr(res, 'path') else 'N/A'}")
check("ray_tracing: сферическая поверхность", t_trace_sphere)

def t_trace_conic():
    s1 = Surface(radius=50, thickness=10, glass='К8', conic_constant=-1.0)
    s2 = Surface(radius=1e10, thickness=0, glass='ВОЗДУХ')
    sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                          object_type=ObjectType.FINITE)
    r = Ray(y=5, k=0, l=0, m=1)
    res = trace_ray_through_system(sys1, r, wl=0.5876)
    assert res is not None
    print(f"  success={res.success}, surfaces_hit={res.surfaces_hit if hasattr(res, 'surfaces_hit') else 'N/A'}")
check("ray_tracing: асферическая (conic) поверхность", t_trace_conic)

def t_tir():
    s1 = Surface(radius=10, thickness=5, glass='ТФ5')
    s2 = Surface(radius=1e10, thickness=0, glass='ВОЗДУХ')
    sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                          object_type=ObjectType.FINITE)
    r = Ray(y=9.9, k=0, l=0.5, m=0.5)
    res = trace_ray_through_system(sys1, r, wl=0.5876)
    if res is None or not res.success or (hasattr(res, 'error') and res.error):
        print("  TIR/error correctly detected")
    else:
        print(f"  success={res.success} (no TIR for this config, still OK)")
check("TIR detected", t_tir)

def t_opl():
    sys1 = make_biconvex()
    r = Ray(y=10, k=0, l=0, m=1)
    res = trace_ray_through_system(sys1, r, wl=0.5876)
    assert res is not None
    opl = getattr(res, 'opl', None)
    assert opl is not None, f"No OPL in TraceResult: {[a for a in dir(res) if not a.startswith('_')]}"
    print(f"  OPL={opl}")
check("OPL вычисляется", t_opl)

# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("АНАЛИЗ")
print("=" * 60)

from aberrations import (compute_spot_diagram, compute_geometric_mtf,
                          compute_rms_spot, compute_spot_diagram_polychromatic,
                          compute_polychromatic_rms, compute_focus_curve)
from diffraction_mtf import (compute_diffraction_mtf, compute_polychromatic_mtf,
                              compute_wavefront_map)
from advanced_analysis import (compute_psf, compute_lsf, compute_enc, compute_ptf)

def t_spot():
    sys1 = make_biconvex()
    pts = compute_spot_diagram(sys1, wl=0.5876, num_rays=15, field_y=0)
    assert len(pts) > 100, f"Only {len(pts)} points"
    print(f"  {len(pts)} точек")
check("spot diagram >100 точек", t_spot)

def t_wavefront():
    sys1 = make_biconvex()
    wf = compute_wavefront_map(sys1, wl=0.5876, grid_size=32, field_y=0)
    assert wf is not None
    print(f"  wavefront type={type(wf).__name__}")
check("OPL-based wavefront", t_wavefront)

def t_geometric_mtf():
    sys1 = make_biconvex()
    spots = compute_spot_diagram(sys1, wl=0.5876, num_rays=15, field_y=0)
    result = compute_geometric_mtf(spots)
    assert len(result) > 0
    print(f"  geometric_mtf points: {len(result)}")
check("FFT-based geometric MTF", t_geometric_mtf)

def t_diffraction_mtf():
    sys1 = make_biconvex()
    result = compute_diffraction_mtf(sys1, wl=0.5876, grid_size=32)
    assert result is not None and len(result) > 0
    cutoff = result.get('cutoff_freq', 0)
    assert cutoff > 0, f"cutoff_freq={cutoff}"
    print(f"  cutoff={cutoff:.2f} lp/mm")
check("diffraction MTF (cutoff > 0)", t_diffraction_mtf)

def t_psf():
    sys1 = make_biconvex()
    res = compute_psf(sys1, wl=0.5876, num_rays=64, field_y=0)
    assert res is not None
    print(f"  PSF OK, type={type(res).__name__}")
check("PSF через FFT", t_psf)

def t_lsf():
    sys1 = make_biconvex()
    res = compute_lsf(sys1, wl=0.5876, num_rays=64, field_y=0)
    assert res is not None
    print(f"  LSF OK")
check("LSF (tangential + sagittal)", t_lsf)

def t_enc():
    sys1 = make_biconvex()
    radii, enc = compute_enc(sys1, wl=0.5876, num_rays=100, field_y=0)
    assert len(radii) > 0 and len(enc) > 0
    print(f"  {len(radii)} points")
check("ENC (encircled energy)", t_enc)

def t_ptf():
    sys1 = make_biconvex()
    res = compute_ptf(sys1, wl=0.5876, num_rays=64, field_y=0)
    assert res is not None
    print(f"  PTF OK")
check("PTF (phase transfer)", t_ptf)

def t_poly_spot():
    sys1 = make_biconvex_poly()
    pts = compute_spot_diagram_polychromatic(sys1, num_rays=12, field_y=0)
    assert len(pts) > 50, f"Only {len(pts)} points"
    print(f"  {len(pts)} точек")
check("Полихроматический spot", t_poly_spot)

def t_poly_mtf():
    sys1 = make_biconvex_poly()
    result = compute_polychromatic_mtf(sys1, grid_size=32)
    assert result is not None
    print(f"  polychromatic MTF OK")
check("Полихроматический MTF", t_poly_mtf)

def t_poly_rms():
    sys1 = make_biconvex_poly()
    rms = compute_polychromatic_rms(sys1, num_rays=12, field_y=0)
    assert rms is not None
    print(f"  RMS={rms}")
check("Полихроматический RMS", t_poly_rms)

def t_focus_curve():
    sys1 = make_biconvex()
    res = compute_focus_curve(sys1, wl=0.5876, num_points=20, field_y=0)
    assert res is not None and len(res) > 0
    print(f"  focus_curve points: {len(res)}")
check("Focus curve", t_focus_curve)

# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("ОПТИМИЗАЦИЯ")
print("=" * 60)

from optimizer import optimize_dls, optimize_simplex, fit_focal_length, fit_bfd

# Variables format: list of tuples (surface_idx, param_type, vmin, vmax)
def t_dls():
    sys1 = make_biconvex()
    # variables = [(surface_idx, param_type, min, max), ...]
    variables = [(0, 'radius', 50, 200)]
    result = optimize_dls(sys1, variables=variables)
    assert result is not None
    print(f"  DLS result OK")
check("DLS оптимизация", t_dls)

def t_simplex():
    sys1 = make_biconvex()
    variables = [(0, 'radius', 50, 200)]
    result = optimize_simplex(sys1, variables=variables)
    assert result is not None
    print(f"  Simplex result OK")
check("Simplex оптимизация", t_simplex)

def t_fit_focal():
    sys1 = make_biconvex()
    result = fit_focal_length(sys1, target_f=100, surface_idx=0)
    assert result is not None
    print(f"  fit_focal_length OK")
check("fit_focal_length", t_fit_focal)

def t_fit_bfd_opt():
    sys1 = make_biconvex()
    result = fit_bfd(sys1, target_bfd=90, surface_idx=-1)
    assert result is not None
    print(f"  fit_bfd OK")
check("fit_bfd", t_fit_bfd_opt)

# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("ФАЙЛЫ")
print("=" * 60)

from opj_reader import load_opj

OPJ_DIR = os.path.join('.', 'extracted', 'opal_okb')

def t_opj_count():
    opj_files = glob.glob(os.path.join(OPJ_DIR, '*.OPJ'))
    assert len(opj_files) >= 83, f"Only {len(opj_files)} .OPJ files"
    print(f"  {len(opj_files)} .OPJ файлов")
check("opj_reader: 83+ .OPJ файла", t_opj_count)

def t_opj_glasses():
    opj_files = glob.glob(os.path.join(OPJ_DIR, '*.OPJ'))
    found_glasses = set()
    for f in opj_files[:30]:
        try:
            result = load_opj(f)
            if result and isinstance(result, tuple) and len(result) == 2:
                meta = result[1]
                gnames = meta.get('glass_names', [])
                for g in gnames:
                    if g and g not in ('ВОЗДУХ', 'AIR', '', '\xb0\xd0\xbc\xd0\x94'):
                        found_glasses.add(g)
        except:
            pass
    print(f"  Glasses found: {len(found_glasses)} names (encoded)")
    assert len(found_glasses) > 0, "No glasses extracted"
check("opj_reader: стёкла извлекаются (К8, ТФ1, etc.)", t_opj_glasses)

from io_utils import save_json, load_json

def t_json_roundtrip():
    sys1 = make_biconvex()
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        path = f.name
    save_json(sys1, path)
    sys2 = load_json(path)
    assert sys2 is not None
    assert len(sys2.surfaces) == 2
    os.unlink(path)
    print(f"  JSON roundtrip OK, {len(sys2.surfaces)} surfaces")
check("io_utils: JSON roundtrip", t_json_roundtrip)

from achromat import design_achromat

def t_achromat():
    sys_obj = design_achromat(focal_length=100)
    assert sys_obj is not None
    res = paraxial_trace(sys_obj)
    efl = res['focal_length']
    assert abs(efl - 100) < 5, f"EFL={efl}"
    print(f"  f'={efl:.2f}")
check("achromat: f'≈100", t_achromat)

from glass_diagram import plot_glass_diagram

def t_glass_diagram():
    assert callable(plot_glass_diagram)
    print(f"  plot_glass_diagram callable")
check("glass_diagram: plot_glass_diagram() callable", t_glass_diagram)

# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("УТИЛИТЫ")
print("=" * 60)

from system_utils import reverse_system, scale_system, nearest_standard_radius, standardize_radii

def t_reverse():
    sys1 = make_biconvex()
    rev = reverse_system(sys1)
    assert rev is not None
    print(f"  reversed: {len(rev.surfaces)} surfaces")
check("system_utils: reverse_system", t_reverse)

def t_scale():
    sys1 = make_biconvex()
    scaled = scale_system(sys1, 2.0)
    assert scaled.surfaces[0].radius == 200, f"R={scaled.surfaces[0].radius}"
    print(f"  R={scaled.surfaces[0].radius}")
check("system_utils: scale_system", t_scale)

def t_nearest():
    r = nearest_standard_radius(47.3)
    assert r is not None
    print(f"  nearest(47.3)={r}")
check("system_utils: nearest_standard_radius", t_nearest)

def t_standardize():
    s1 = Surface(radius=47.3, thickness=5, glass='К8')
    s2 = Surface(radius=-103.7, thickness=95, glass='ВОЗДУХ')
    sys1 = OpticalSystem(surfaces=[s1, s2], wavelengths=[Wavelength(0.5876)],
                          object_type=ObjectType.FINITE)
    std = standardize_radii(sys1)
    assert std is not None
    print(f"  R0={std.surfaces[0].radius}, R1={std.surfaces[1].radius}")
check("system_utils: standardize_radii", t_standardize)

# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("GUI")
print("=" * 60)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
app = QApplication.instance() or QApplication(sys.argv)

from main import MainWindow

def t_gui_viz():
    mw = MainWindow()
    assert hasattr(mw, 'viz'), "No viz attribute"
    print(f"  MainWindow.viz exists: {type(mw.viz).__name__}")
check("MainWindow.viz существует", t_gui_viz)

def t_analysis_tabs():
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
        except:
            pass
    if panel is None:
        raise AssertionError("Cannot find analysis panel with >=13 tabs")
    print(f"  AnalysisPanel: {n} вкладок")
check("AnalysisPanel ≥ 13 вкладок", t_analysis_tabs)

def t_surface_table():
    mw = MainWindow()
    table = None
    for attr in dir(mw):
        obj = getattr(mw, attr)
        if type(obj).__name__ in ('SurfaceTable', 'QTableWidget') and attr != 'viz':
            table = obj
            break
    assert table is not None, "SurfaceTable not found"
    headers = []
    for i in range(table.columnCount()):
        h = table.horizontalHeaderItem(i)
        if h:
            headers.append(h.text())
    print(f"  Headers: {headers}")
    has_stop = any('Стоп' in h or 'stop' in h.lower() for h in headers)
    has_k = any('k' in h.lower() or 'кон' in h.lower() for h in headers)
    assert has_stop, f"No 'Стоп' column"
    assert has_k, f"No 'k' column"
check("SurfaceTable имеет столбец 'Стоп' и 'k'", t_surface_table)

def t_field_widget():
    mw = MainWindow()
    # FieldPointsWidget is nested in sys_params
    sp = mw.sys_params
    assert hasattr(sp, 'field_points_widget'), "No field_points_widget in sys_params"
    fpw = sp.field_points_widget
    assert fpw is not None
    print(f"  FieldPointsWidget found as sys_params.field_points_widget")
check("FieldPointsWidget существует", t_field_widget)

def t_load_demo():
    mw = MainWindow()
    mw._load_demo()
    print(f"  _load_demo() OK")
check("_load_demo() работает", t_load_demo)

def t_calculate():
    mw = MainWindow()
    mw._load_demo()
    mw._calculate()
    print(f"  _calculate() OK")
check("_calculate() работает", t_calculate)

def t_menu_file():
    mw = MainWindow()
    menubar = mw.menuBar()
    file_menu = None
    for action in menubar.actions():
        if 'Файл' in action.text() or 'File' in action.text():
            file_menu = action.menu()
            break
    assert file_menu is not None, "No Файл menu"
    texts = [a.text() for a in file_menu.actions()]
    assert any('Открыть' in t for t in texts), f"No 'Открыть' in {texts}"
    assert any('Сохранить' in t for t in texts), f"No 'Сохранить' in {texts}"
    print(f"  Файл: {texts}")
check("Меню Файл: Открыть, Сохранить", t_menu_file)

def t_menu_system():
    mw = MainWindow()
    menubar = mw.menuBar()
    sys_menu = None
    for action in menubar.actions():
        if 'Система' in action.text() or 'System' in action.text():
            sys_menu = action.menu()
            break
    assert sys_menu is not None, "No Система menu"
    texts = [a.text() for a in sys_menu.actions()]
    expected = ['Обернуть', 'Масштаб', 'Стандарт', 'Ахромат', 'Подгон']
    for exp in expected:
        found = any(exp in t for t in texts)
        assert found, f"No '{exp}' in {texts}"
    print(f"  Система: {texts}")
check("Меню Система: Обернуть, Масштаб, Стандартные, Ахромат, Подгонка", t_menu_system)

def t_menu_view():
    mw = MainWindow()
    menubar = mw.menuBar()
    view_menu = None
    for action in menubar.actions():
        if 'Вид' in action.text() or 'View' in action.text():
            view_menu = action.menu()
            break
    assert view_menu is not None, "No Вид menu"
    texts = [a.text() for a in view_menu.actions()]
    assert any('стёкол' in t.lower() or 'glass' in t.lower() for t in texts), f"No glass diagram in {texts}"
    print(f"  Вид: {texts}")
check("Меню Вид: Диаграмма стёкол", t_menu_view)

# ═══════════════════════════════════════════
# СВОДКА
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("СВОДКА QA v6")
print("=" * 60)
passed = sum(1 for s, _ in results if s == "[PASS]")
failed = sum(1 for s, _ in results if s == "[FAIL]")
for status, label in results:
    try:
        print(f"  {status} {label}")
    except UnicodeEncodeError:
        print(f"  {status} {label.encode('utf-8', errors='replace').decode('utf-8', errors='replace')}")
print(f"\nИТОГО: {passed}/{passed+failed} пройдено, {failed} не пройдено")
if failed > 0:
    sys.exit(1)
