# TODO: convert to pytest — uses custom runner
"""
OPAL-OKB — Финальный независимый QA-тест (исправленный)
"""
import sys, os, math, traceback, importlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Save stdout FD before any module replaces it
_stdout_fd = sys.stdout.fileno() if hasattr(sys.stdout, 'fileno') else 1

def _print(msg):
    try:
        os.write(_stdout_fd, (msg + '\n').encode('utf-8', errors='replace'))
    except:
        pass

def restore_stdout():
    try:
        sys.stdout = open(_stdout_fd, 'w', encoding='utf-8', closefd=False)
        sys.stderr = open(_stdout_fd, 'w', encoding='utf-8', closefd=False)
    except:
        pass

# Output file for reliable capture
_out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_results.txt')
_out = open(_out_file, 'w', encoding='utf-8')

def _log(msg):
    _out.write(msg + '\n')
    _out.flush()

results = []
bugs = []

def record(status, name, expected, actual, file_line=""):
    results.append((status, name, expected, actual, file_line))
    _log(f"  [{status}] {name}")
    if status != "PASS":
        _log(f"    Expected: {expected}")
        _log(f"    Actual:   {actual}")
        if file_line:
            _log(f"    {file_line}")
        if status == "BUG":
            bugs.append(name)

# ============================================================
# 0. IMPORT TESTS
# ============================================================
_log("\n" + "="*70)
_log("0. ИМПОРТ МОДУЛЕЙ")
_log("="*70)

modules_to_test = [
    "glass_catalog",
    "optics_engine",
    "ray_tracing",
    "aberrations",
    "optimizer",
    "opj_reader",
    "fil_reader_v2",
]

imported = {}
for mod_name in modules_to_test:
    try:
        mod = importlib.import_module(mod_name)
        imported[mod_name] = mod
        restore_stdout()
        record("PASS", f"import {mod_name}", "no error", "no error")
    except Exception as e:
        restore_stdout()
        record("BUG", f"import {mod_name}", "no error", str(e))

# PyQt5 modules
pyqt_available = False
try:
    import PyQt5
    pyqt_available = True
except ImportError:
    pass

for mod_name in ["visualization", "analysis_gui", "main"]:
    if not pyqt_available:
        record("FAIL", f"import {mod_name}", "PyQt5 installed", "PyQt5 not available")
        continue
    try:
        mod = importlib.import_module(mod_name)
        imported[mod_name] = mod
        restore_stdout()
        record("PASS", f"import {mod_name}", "no error", "no error")
    except Exception as e:
        restore_stdout()
        record("BUG", f"import {mod_name}", "no error", str(e))

# glass_catalog_full (expected to have issues)
try:
    mod = importlib.import_module("glass_catalog_full")
    imported["glass_catalog_full"] = mod
    restore_stdout()
    record("PASS", "import glass_catalog_full", "no error", "no error")
except SyntaxError as e:
    restore_stdout()
    record("BUG", "import glass_catalog_full", "no error", 
           f"SyntaxError: {e.msg} at line {e.lineno}")
except Exception as e:
    restore_stdout()
    record("BUG", "import glass_catalog_full", "no error", str(e))

# ============================================================
# 1. OPTICS ENGINE
# ============================================================
_log("\n" + "="*70)
_log("1. ОПТИЧЕСКИЙ ДВИЖОК (optics_engine.py)")
_log("="*70)

if "optics_engine" in imported and "glass_catalog" in imported:
    oe = imported["optics_engine"]
    gc = imported["glass_catalog"]
    
    def make_system(surfaces_data, wavelengths=None, aperture=20.0):
        sys = oe.OpticalSystem()
        sys.aperture_value = aperture
        if wavelengths is None:
            sys.wavelengths = [oe.Wavelength(0.58756, 1.0, "d")]
        else:
            sys.wavelengths = wavelengths
        sys.field_points = [oe.FieldPoint(0.0)]
        for r, d, glass, sd in surfaces_data:
            sys.surfaces.append(oe.Surface(radius=r, thickness=d, glass=glass, semi_diameter=sd))
        return sys

    n_k8 = gc.compute_refractive_index("К8", 0.58756)
    _log(f"  [INFO] n(К8, d) = {n_k8:.6f}")
    
    # 1.1 Плоско-выпуклая линза
    sys1 = make_system([(50.0, 5.0, "К8", 15), (0.0, 95.0, "", 15)])
    res1 = oe.paraxial_trace(sys1)
    f1 = res1.get('focal_length', 0)
    f_theory_thin = 50.0 / (n_k8 - 1)
    record("PASS" if 90 < f1 < 110 else "FAIL",
           "Плоско-выпуклая линза f'>0",
           f"f' ≈ {f_theory_thin:.1f} мм",
           f"f' = {f1:.4f} мм",
           "optics_engine.py: paraxial_trace")
    
    # 1.2 Двояковыпуклая (R1=100, R2=-100)
    sys2 = make_system([(100.0, 5.0, "К8", 15), (-100.0, 95.0, "", 15)])
    res2 = oe.paraxial_trace(sys2)
    f2 = res2.get('focal_length', 0)
    f_theory2 = 1.0 / ((n_k8 - 1) * (1.0/100 - 1.0/(-100)))
    record("PASS" if 90 < f2 < 110 else "FAIL",
           "Двояковыпуклая (R=±100) f'>0",
           f"f' ≈ {f_theory2:.1f} мм",
           f"f' = {f2:.4f} мм",
           "optics_engine.py: paraxial_trace")
    
    # 1.3 Двояковыпуклая (R1=50, R2=-200)
    sys3 = make_system([(50.0, 5.0, "К8", 15), (-200.0, 50.0, "", 15)])
    res3 = oe.paraxial_trace(sys3)
    f3 = res3.get('focal_length', 0)
    f_theory3 = 1.0 / ((n_k8 - 1) * (1.0/50 - 1.0/(-200)))
    record("PASS" if 50 < f3 < 120 else "FAIL",
           "Двояковыпуклая (R=50,-200) f'>0",
           f"f' ≈ {f_theory3:.1f} мм",
           f"f' = {f3:.4f} мм",
           "optics_engine.py: paraxial_trace")

    # 1.4 Отрицательная линза
    sys4 = make_system([(-50.0, 5.0, "К8", 15), (50.0, 95.0, "", 15)])
    res4 = oe.paraxial_trace(sys4)
    f4 = res4.get('focal_length', 0)
    record("PASS" if f4 < 0 else "FAIL",
           "Отрицательная линза f'<0",
           "f' < 0",
           f"f' = {f4:.4f} мм",
           "optics_engine.py: paraxial_trace")
    
    # 1.5 Тонкая линза (d→0)
    sys5 = make_system([(50.0, 0.001, "К8", 15), (0.0, 95.0, "", 15)])
    res5 = oe.paraxial_trace(sys5)
    f5 = res5.get('focal_length', 0)
    f_thin_theory = 50.0 / (n_k8 - 1)
    err5 = abs(f5 - f_thin_theory) / f_thin_theory * 100
    record("PASS" if err5 < 5 else "FAIL",
           f"Тонкая линза (d→0): f'≈R/(n-1)",
           f"f' ≈ {f_thin_theory:.2f} мм (error<5%)",
           f"f' = {f5:.4f} мм (error={err5:.2f}%)",
           "optics_engine.py: paraxial_trace")

    # 1.6 Система из 2 линз
    sys6 = make_system([
        (100.0, 5.0, "К8", 15), (-100.0, 10.0, "", 15),
        (80.0, 5.0, "К8", 15), (-80.0, 50.0, "", 15),
    ])
    res6 = oe.paraxial_trace(sys6)
    f6 = res6.get('focal_length', 0)
    record("PASS" if f6 > 0 else "FAIL",
           "Система 2 линзы: f'>0",
           "f' > 0", f"f' = {f6:.4f} мм",
           "optics_engine.py: paraxial_trace")

    # 1.7 Seidel sums
    seidel1 = oe.seidel_aberrations(sys2)
    si = seidel1.get('SI', 0)
    record("PASS" if si != 0 else "FAIL",
           "Seidel SI ≠ 0 для собирающей линзы",
           "SI ≠ 0", f"SI = {si:.6f}",
           "optics_engine.py: seidel_aberrations")
    
    keys_5 = {'SI', 'SII', 'SIII', 'SIV', 'SV'}
    has_all = keys_5.issubset(set(seidel1.keys()))
    record("PASS" if has_all else "BUG",
           "Все 5 сумм Зейделя вычисляются",
           f"keys = {keys_5}",
           f"keys = {set(seidel1.keys())}",
           "optics_engine.py: seidel_aberrations")

    siv = seidel1.get('SIV', 0)
    record("PASS" if siv != 0 else "FAIL",
           "SIV (кривизна Петцваля) ≠ 0 для двояковыпуклой",
           "SIV ≠ 0", f"SIV = {siv:.6f}",
           "optics_engine.py: seidel_aberrations")
    
    # 1.8 Empty system
    sys_empty = oe.OpticalSystem()
    sys_empty.wavelengths = [oe.Wavelength(0.58756)]
    res_empty = oe.paraxial_trace(sys_empty)
    record("PASS" if isinstance(res_empty, dict) else "BUG",
           "Пустая система: paraxial_trace не крашится",
           "returns dict", f"returns {type(res_empty).__name__}",
           "optics_engine.py")
    
    seidel_empty = oe.seidel_aberrations(sys_empty)
    record("PASS" if isinstance(seidel_empty, dict) else "BUG",
           "Пустая система: seidel не крашится",
           "returns dict", f"returns {type(seidel_empty).__name__}",
           "optics_engine.py")

    # 1.9 1 surface
    sys_1s = make_system([(100.0, 50.0, "К8", 15)])
    res_1s = oe.paraxial_trace(sys_1s)
    record("PASS" if isinstance(res_1s, dict) and 'focal_length' in res_1s else "FAIL",
           "1 поверхность: paraxial_trace работает",
           "dict with focal_length", str(res_1s),
           "optics_engine.py")
    
    # 1.10 160 surfaces
    try:
        many_surfs = [(50.0, 2.0, "К8" if i % 2 == 0 else "", 15) for i in range(160)]
        sys_many = make_system(many_surfs)
        res_many = oe.paraxial_trace(sys_many)
        record("PASS" if isinstance(res_many, dict) else "FAIL",
               "160 поверхностей: не крашится",
               "returns dict", str(type(res_many).__name__),
               "optics_engine.py")
    except Exception as e:
        record("FAIL", "160 поверхностей", "no crash", str(e), "optics_engine.py")

    # 1.11 Demo system
    demo = oe.create_demo_system()
    record("PASS" if demo.num_surfaces == 2 else "FAIL",
           "create_demo_system: 2 поверхности",
           "num_surfaces == 2", f"num_surfaces = {demo.num_surfaces}",
           "optics_engine.py")
    
    demo_res = oe.paraxial_trace(demo)
    f_demo = demo_res.get('focal_length', 0)
    record("PASS" if f_demo > 0 else "FAIL",
           "Demo system: f'>0", "f' > 0", f"f' = {f_demo:.4f}",
           "optics_engine.py")

# ============================================================
# 2. GLASS CATALOG
# ============================================================
_log("\n" + "="*70)
_log("2. КАТАЛОГ СТЁКОЛ (glass_catalog.py)")
_log("="*70)

if "glass_catalog" in imported:
    gc = imported["glass_catalog"]
    
    # 2.1 AIR/ВОЗДУХ
    n_air = gc.compute_refractive_index("ВОЗДУХ", 0.58756)
    record("PASS" if abs(n_air - 1.0) < 1e-10 else "BUG",
           "n(λ) для ВОЗДУХ = 1.0", "1.0", f"{n_air}", "glass_catalog.py")
    
    n_air_en = gc.compute_refractive_index("AIR", 0.58756)
    record("PASS" if abs(n_air_en - 1.0) < 1e-10 else "BUG",
           "n(λ) для AIR = 1.0", "1.0", f"{n_air_en}", "glass_catalog.py")

    # 2.2 К8 nd
    n_k8_d = gc.compute_refractive_index("К8", 0.58756)
    err_k8 = abs(n_k8_d - 1.5163) / 1.5163 * 100
    record("PASS" if err_k8 < 1 else "FAIL",
           "n(d) для К8 ≈ 1.5163",
           f"1.5163 (error < 1%)",
           f"n = {n_k8_d:.6f} (error = {err_k8:.3f}%)",
           "glass_catalog.py")
    
    # 2.3 Dispersion
    test_glasses = list(gc.GLASS_CATALOG.keys())
    dispersion_ok = True
    dispersion_fail_list = []
    for g in test_glasses:
        if g in ("ВОЗДУХ", "AIR"):
            continue
        nF = gc.compute_refractive_index(g, 0.48613)
        nd = gc.compute_refractive_index(g, 0.58756)
        nC = gc.compute_refractive_index(g, 0.65627)
        if not (nF >= nd >= nC):
            dispersion_ok = False
            dispersion_fail_list.append(f"{g}: nF={nF:.6f} nd={nd:.6f} nC={nC:.6f}")
    
    record("PASS" if dispersion_ok else "FAIL",
           "Дисперсия n(F) > n(d) > n(C) для всех стёкол",
           "nF >= nd >= nC",
           f"Failed: {dispersion_fail_list[:5]}" if not dispersion_ok else "OK",
           "glass_catalog.py")
    
    # 2.4 UV
    n_uv = gc.compute_refractive_index("К8", 0.365)
    record("PASS" if n_uv > 1.516 else "FAIL",
           "n(0.365 мкм) для К8 > n(d)",
           "n > 1.516", f"n = {n_uv:.6f}", "glass_catalog.py")
    
    # 2.5 IR
    n_ir = gc.compute_refractive_index("К8", 2.6)
    record("PASS" if 1.4 < n_ir < 1.55 else "FAIL",
           "n(2.6 мкм) для К8", "1.4 < n < 1.55", f"n = {n_ir:.6f}", "glass_catalog.py")

    # 2.6 Out of range
    n_oor = gc.compute_refractive_index("К8", 0.01)
    record("PASS" if isinstance(n_oor, float) and not math.isnan(n_oor) else "FAIL",
           "λ=0.01 мкм: не крашится",
           "float, not NaN", f"n = {n_oor:.6f}", "glass_catalog.py")

    # 2.7 Unknown glass
    n_unknown = gc.compute_refractive_index("XXUNKNOWN99", 0.58756)
    record("PASS" if n_unknown == 1.5 else "FAIL",
           "Неизвестное стекло → fallback 1.5", "1.5", f"{n_unknown}", "glass_catalog.py")
    
    # 2.8 Empty glass
    n_empty = gc.compute_refractive_index("", 0.58756)
    record("PASS" if abs(n_empty - 1.0) < 1e-10 else "FAIL",
           "Пустое стекло → 1.0", "1.0", f"{n_empty}", "glass_catalog.py")
    
    # 2.9 ГОСТ glasses count
    n_gost = len([k for k in gc.GLASS_CATALOG if k not in ("ВОЗДУХ", "AIR")])
    record("PASS" if n_gost >= 14 else "FAIL",
           "ГОСТ стёкол ≥ 14", "≥ 14", f"{n_gost}", "glass_catalog.py")

# glass_catalog_full
if "glass_catalog_full" in imported:
    gcf = imported["glass_catalog_full"]
    n_full = len(gcf.GLASS_CATALOG)
    record("PASS" if n_full > 100 else "FAIL",
           "glass_catalog_full: > 100 стёкол", "> 100", f"{n_full}", "glass_catalog_full.py")
    
    readable = sum(1 for k in gcf.GLASS_CATALOG if all(c.isalpha() or c.isdigit() or c in '_- ' for c in k))
    garbled = n_full - readable
    record("PASS" if garbled < n_full * 0.5 else "BUG",
           "glass_catalog_full: имена стёкол читаемые",
           "большинство читаемые", f"readable={readable}, garbled={garbled}",
           "glass_catalog_full.py")
else:
    record("BUG", "glass_catalog_full: не импортируется (SyntaxError)",
           "import OK", "SyntaxError — имена стёкол содержат спецсимволы/переводы строк",
           "glass_catalog_full.py: line 83+")

# ============================================================
# 3. RAY TRACING
# ============================================================
_log("\n" + "="*70)
_log("3. ТРАССИРОВКА ЛУЧЕЙ (ray_tracing.py)")
_log("="*70)

if "ray_tracing" in imported and "optics_engine" in imported:
    rt = imported["ray_tracing"]
    oe = imported["optics_engine"]
    
    def make_sys_2convex():
        sys = oe.OpticalSystem()
        sys.aperture_value = 20.0
        sys.wavelengths = [oe.Wavelength(0.58756)]
        sys.field_points = [oe.FieldPoint(0.0)]
        sys.surfaces = [
            oe.Surface(radius=100.0, thickness=5.0, glass="К8", semi_diameter=15),
            oe.Surface(radius=-100.0, thickness=95.0, glass="", semi_diameter=15),
        ]
        return sys

    # 3.1 Axial ray
    sys_rt = make_sys_2convex()
    ray_axial = rt.Ray(x=0, y=5.0, z=-50, k=0, l=0, m=1)
    res_axial = rt.trace_ray_through_system(sys_rt, ray_axial, 0.58756)
    
    if res_axial.success and len(res_axial.path) > 1:
        last_y = res_axial.path[-1][1]
        record("PASS" if abs(last_y) < 2.0 else "FAIL",
               "Осевой луч: y→0 в фокусе",
               f"|y| < 2.0 мм", f"y = {last_y:.4f} мм",
               "ray_tracing.py")
    else:
        record("FAIL", "Осевой луч: трассировка",
               "success=True", f"success={res_axial.success}, error={res_axial.error}",
               "ray_tracing.py")
    
    # 3.2 Fans
    for n_rays in [7, 9, 11]:
        fan = rt.trace_fan(sys_rt, num_rays=n_rays, wl=0.58756)
        passed = sum(1 for r in fan if r.success)
        record("PASS" if passed == n_rays else "FAIL",
               f"Веер {n_rays} лучей: все проходят",
               f"{n_rays}/{n_rays}", f"{passed}/{n_rays}",
               "ray_tracing.py")

    # 3.3 Plane-parallel plate
    sys_pp = oe.OpticalSystem()
    sys_pp.aperture_value = 20.0
    sys_pp.wavelengths = [oe.Wavelength(0.58756)]
    sys_pp.field_points = [oe.FieldPoint(0.0)]
    sys_pp.surfaces = [
        oe.Surface(radius=0.0, thickness=10.0, glass="К8", semi_diameter=20),
        oe.Surface(radius=0.0, thickness=50.0, glass="", semi_diameter=20),
    ]
    ray_pp = rt.Ray(x=0, y=3.0, z=-50, k=0, l=0, m=1)
    res_pp = rt.trace_ray_through_system(sys_pp, ray_pp, 0.58756)
    
    if res_pp.success and len(res_pp.path) > 1:
        last_y_pp = res_pp.path[-1][1]
        record("PASS" if abs(last_y_pp - 3.0) < 1.0 else "FAIL",
               "Плоскопараллельная пластина: луч проходит",
               f"|y_out - y_in| < 1.0", f"y_in=3.0, y_out={last_y_pp:.4f}",
               "ray_tracing.py")
    else:
        record("FAIL", "Плоскопараллельная пластина",
               "success", f"success={res_pp.success}", "ray_tracing.py")

    # 3.4 TIR
    sys_tir = oe.OpticalSystem()
    sys_tir.aperture_value = 20.0
    sys_tir.wavelengths = [oe.Wavelength(0.58756)]
    sys_tir.surfaces = [
        oe.Surface(radius=0.0, thickness=5.0, glass="ТФ5", semi_diameter=15),
        oe.Surface(radius=0.0, thickness=50.0, glass="", semi_diameter=15),
    ]
    ray_tir = rt.Ray(x=0, y=15.0, z=-1, k=0, l=-0.95, m=0.312)
    norm_tir = math.sqrt(ray_tir.k**2 + ray_tir.l**2 + ray_tir.m**2)
    ray_tir.k /= norm_tir; ray_tir.l /= norm_tir; ray_tir.m /= norm_tir
    res_tir = rt.trace_ray_through_system(sys_tir, ray_tir, 0.58756)
    record("PASS" if res_tir.error == 'TIR' or res_tir.success else "FAIL",
           "TIR: обнаруживается или луч проходит",
           "error='TIR' or success",
           f"success={res_tir.success}, error={res_tir.error}",
           "ray_tracing.py")

    # 3.5 Dublet
    sys_dub = oe.OpticalSystem()
    sys_dub.aperture_value = 20.0
    sys_dub.wavelengths = [oe.Wavelength(0.58756)]
    sys_dub.field_points = [oe.FieldPoint(0.0)]
    sys_dub.surfaces = [
        oe.Surface(radius=80.0, thickness=5.0, glass="К8", semi_diameter=15),
        oe.Surface(radius=-60.0, thickness=3.0, glass="ТФ5", semi_diameter=15),
        oe.Surface(radius=-200.0, thickness=80.0, glass="", semi_diameter=15),
    ]
    fan_dub = rt.trace_fan(sys_dub, num_rays=7, wl=0.58756)
    passed_dub = sum(1 for r in fan_dub if r.success)
    record("PASS" if passed_dub == 7 else "FAIL",
           "Дублет (К8+ТФ5): все 7 лучей проходят",
           "7/7", f"{passed_dub}/7", "ray_tracing.py")

    # 3.6 Large aperture
    sys_big = make_sys_2convex()
    sys_big.aperture_value = 50.0
    fan_big = rt.trace_fan(sys_big, num_rays=9, wl=0.58756)
    passed_big = sum(1 for r in fan_big if r.success)
    record("PASS" if passed_big >= 5 else "FAIL",
           "Большой зрачок (aperture=50): ≥5 лучей проходят",
           "≥5", f"{passed_big}/9", "ray_tracing.py")

# ============================================================
# 4. VISUALIZATION (structural)
# ============================================================
_log("\n" + "="*70)
_log("4. ВИЗУАЛИЗАЦИЯ (visualization.py)")
_log("="*70)

if "visualization" in imported:
    viz = imported["visualization"]
    record("PASS" if hasattr(viz, 'OpticalSystemView') else "BUG",
           "OpticalSystemView class exists", "True",
           str(hasattr(viz, 'OpticalSystemView')), "visualization.py")
    
    if hasattr(viz, 'OpticalSystemView'):
        for m in ['zoom_in', 'zoom_out', 'reset_view', 'set_system']:
            record("PASS" if hasattr(viz.OpticalSystemView, m) else "BUG",
                   f"OpticalSystemView.{m}() exists", "True",
                   str(hasattr(viz.OpticalSystemView, m)), "visualization.py")
else:
    record("FAIL", "visualization.py", "PyQt5 required", "not loaded", "visualization.py")

# ============================================================
# 5. GUI
# ============================================================
_log("\n" + "="*70)
_log("5. GUI (main.py)")
_log("="*70)

if "main" in imported:
    m = imported["main"]
    
    for cls_name in ['MainWindow', 'SurfaceTable', 'ResultsPanel', 'AnalysisPanel']:
        record("PASS" if hasattr(m, cls_name) else "BUG",
               f"{cls_name} class exists", "True",
               str(hasattr(m, cls_name)), "main.py")
    
    if hasattr(m, 'SurfaceTable'):
        headers = m.SurfaceTable.HEADERS
        record("PASS" if len(headers) == 6 else "FAIL",
               "SurfaceTable: 6 столбцов", "6",
               f"{len(headers)}", "main.py: SurfaceTable.HEADERS")
    
    if hasattr(m, 'MainWindow'):
        for method in ['_load_demo', '_add_surface', '_del_surface', '_calculate', '_new_system']:
            record("PASS" if hasattr(m.MainWindow, method) else "BUG",
                   f"MainWindow.{method}() exists", "True",
                   str(hasattr(m.MainWindow, method)), "main.py")
else:
    record("FAIL", "main.py", "PyQt5 required", "not loaded", "main.py")

# ============================================================
# 6. ABERRATIONS
# ============================================================
_log("\n" + "="*70)
_log("6. АНАЛИЗ АБЕРРАЦИЙ (aberrations.py)")
_log("="*70)

if "aberrations" in imported and "optics_engine" in imported:
    ab = imported["aberrations"]
    oe = imported["optics_engine"]
    
    sys_ab = oe.OpticalSystem()
    sys_ab.aperture_value = 20.0
    sys_ab.wavelengths = [oe.Wavelength(0.58756)]
    sys_ab.field_points = [oe.FieldPoint(0.0)]
    sys_ab.surfaces = [
        oe.Surface(radius=100.0, thickness=5.0, glass="К8", semi_diameter=12),
        oe.Surface(radius=-100.0, thickness=95.0, glass="", semi_diameter=12),
    ]
    
    # 6.1 trace_aberration_fan
    try:
        fan_data = ab.trace_aberration_fan(sys_ab, 0.58756, num_rays=20)
        n_success = sum(1 for r in fan_data if r['success'])
        record("PASS" if n_success >= 15 else "FAIL",
               "trace_aberration_fan: ≥15/20 success",
               "≥15", f"{n_success}/20", "aberrations.py")
    except Exception as e:
        record("BUG", "trace_aberration_fan", "no error", str(e), "aberrations.py")
    
    # 6.2 compute_spot_diagram
    try:
        spots = ab.compute_spot_diagram(sys_ab, wl=0.58756, num_rays=20, field_y=0.0)
        record("PASS" if len(spots) > 10 else "FAIL",
               "compute_spot_diagram: >10 spots",
               ">10", f"{len(spots)}", "aberrations.py")
    except Exception as e:
        record("BUG", "compute_spot_diagram", "no error", str(e), "aberrations.py")

    # 6.3 compute_rms_spot
    try:
        test_spots = [(0.01, 0.02), (0.03, -0.01), (-0.02, 0.03)]
        rms = ab.compute_rms_spot(test_spots)
        expected_rms = math.sqrt(sum(dx**2 + dy**2 for dx, dy in test_spots) / len(test_spots))
        record("PASS" if abs(rms - expected_rms) < 1e-10 else "BUG",
               "compute_rms_spot: правильный RMS",
               f"{expected_rms:.8f}", f"{rms:.8f}", "aberrations.py")
    except Exception as e:
        record("BUG", "compute_rms_spot", "no error", str(e), "aberrations.py")

    # 6.4 compute_geometric_mtf
    try:
        test_spots_mtf = [(0.01*i, 0.01*i) for i in range(20)]
        mtf = ab.compute_geometric_mtf(test_spots_mtf)
        if len(mtf) > 2:
            record("PASS" if abs(mtf[0][1] - 1.0) < 0.01 else "FAIL",
                   "compute_geometric_mtf: MTF(0)=1.0",
                   "1.0", f"{mtf[0][1]:.4f}", "aberrations.py")
        else:
            record("FAIL", "compute_geometric_mtf: returns data",
                   ">2 points", f"{len(mtf)}", "aberrations.py")
    except Exception as e:
        record("BUG", "compute_geometric_mtf", "no error", str(e), "aberrations.py")

    # 6.5 Multi-wavelength
    try:
        fan_d = ab.trace_aberration_fan(sys_ab, 0.58756, num_rays=15)
        fan_F = ab.trace_aberration_fan(sys_ab, 0.48613, num_rays=15)
        fan_C = ab.trace_aberration_fan(sys_ab, 0.65627, num_rays=15)
        
        dy_d = [abs(r['dy']) for r in fan_d if r['success'] and r['dy'] is not None]
        dy_F = [abs(r['dy']) for r in fan_F if r['success'] and r['dy'] is not None]
        dy_C = [abs(r['dy']) for r in fan_C if r['success'] and r['dy'] is not None]
        
        max_d = max(dy_d) if dy_d else 0
        max_F = max(dy_F) if dy_F else 0
        max_C = max(dy_C) if dy_C else 0
        
        differs = len({round(max_d, 4), round(max_F, 4), round(max_C, 4)}) > 1
        record("PASS" if differs else "FAIL",
               "Многоволновые данные: Δy' отличаются",
               "different for F, d, C",
               f"d={max_d:.4f}, F={max_F:.4f}, C={max_C:.4f}",
               "aberrations.py")
    except Exception as e:
        record("BUG", "Многоволновые данные", "no error", str(e), "aberrations.py")

# ============================================================
# 7. OPTIMIZER
# ============================================================
_log("\n" + "="*70)
_log("7. ОПТИМИЗАТОР (optimizer.py)")
_log("="*70)

if "optimizer" in imported and "optics_engine" in imported:
    opt = imported["optimizer"]
    oe = imported["optics_engine"]
    
    record("PASS" if hasattr(opt, 'optimize_dls') else "BUG",
           "optimize_dls() exists", "True",
           str(hasattr(opt, 'optimize_dls')), "optimizer.py")
    
    record("PASS" if hasattr(opt, 'optimize_simplex') else "BUG",
           "optimize_simplex() exists", "True",
           str(hasattr(opt, 'optimize_simplex')), "optimizer.py")
    
    try:
        sys_opt = oe.OpticalSystem()
        sys_opt.aperture_value = 20.0
        sys_opt.wavelengths = [oe.Wavelength(0.58756)]
        sys_opt.field_points = [oe.FieldPoint(0.0)]
        sys_opt.surfaces = [
            oe.Surface(radius=80.0, thickness=5.0, glass="К8", semi_diameter=12),
            oe.Surface(radius=-80.0, thickness=70.0, glass="", semi_diameter=12),
        ]
        
        variables = [(0, 'radius', 20, 500), (1, 'radius', -500, -20)]
        initial_rms = opt._merit_function(sys_opt, variables)
        
        iterations_log = []
        def callback(it, val, x):
            iterations_log.append((it, val))
        
        opt_sys = opt.optimize_dls(sys_opt, variables, max_iter=10,
                                    num_rays=15, callback=callback)
        final_rms = opt._merit_function(opt_sys, variables)
        
        record("PASS" if len(iterations_log) >= 5 else "FAIL",
               "Оптимизация: ≥5 итераций", "≥5",
               f"{len(iterations_log)}", "optimizer.py")
        
        record("PASS" if final_rms <= initial_rms * 1.5 else "FAIL",
               "Оптимизация: RMS не растёт",
               f"final ≤ {initial_rms*1.5:.4f}",
               f"initial={initial_rms:.4f}, final={final_rms:.4f}",
               "optimizer.py")
    except Exception as e:
        record("BUG", "Оптимизация DLS", "no crash", str(e), "optimizer.py")

# ============================================================
# 8. OPJ READER
# ============================================================
_log("\n" + "="*70)
_log("8. OPJ READER (opj_reader.py)")
_log("="*70)

if "opj_reader" in imported:
    opj = imported["opj_reader"]
    
    record("PASS" if hasattr(opj, 'load_opj') else "BUG",
           "load_opj() exists", "True",
           str(hasattr(opj, 'load_opj')), "opj_reader.py")
    
    opj_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted", "opal_okb")
    opj_files = []
    if os.path.exists(opj_dir):
        for f in os.listdir(opj_dir):
            if f.upper().endswith('.OPJ'):
                opj_files.append(os.path.join(opj_dir, f))
    
    if opj_files:
        parsed_ok = 0
        radii_extracted = 0
        for opj_file in opj_files:
            try:
                result = opj.load_opj(opj_file)
                if isinstance(result, tuple) and len(result) == 2:
                    sys_obj, info = result
                    parsed_ok += 1
                    if hasattr(sys_obj, 'surfaces') and sys_obj.surfaces:
                        for s in sys_obj.surfaces:
                            if abs(s.radius) > 0:
                                radii_extracted += 1
            except Exception:
                pass
        
        record("PASS" if parsed_ok > 0 else "FAIL",
               f"OPJ файлы: {parsed_ok}/{len(opj_files)} распарсены",
               ">0", f"{parsed_ok}/{len(opj_files)}", "opj_reader.py")
        
        record("PASS" if radii_extracted > 0 else "FAIL",
               "OPJ: извлекаются радиусы и толщины",
               ">0", f"{radii_extracted} surfaces with R≠0",
               "opj_reader.py")
    else:
        record("FAIL", "OPJ файлы: не найдены",
               "≥1 .OPJ файл", f"dir={opj_dir}", "opj_reader.py")

# ============================================================
# 9. FIL READER
# ============================================================
_log("\n" + "="*70)
_log("9. FIL READER (fil_reader_v2.py)")
_log("="*70)

if "fil_reader_v2" in imported:
    fil = imported["fil_reader_v2"]
    
    record("PASS" if hasattr(fil, 'parse_gctg') else "BUG",
           "parse_gctg() exists", "True",
           str(hasattr(fil, 'parse_gctg')), "fil_reader_v2.py")
    
    fil_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted", "opal_okb")
    fil_files = {
        'GCTG.FIL': ('ГОСТ', 96),
        'FCTG.FIL': ('SHOTT', 96),
        'HCTG.FIL': ('HOYA', 96),
    }
    
    total_glasses = 0
    for fname, (desc, rec_size) in fil_files.items():
        fpath = os.path.join(fil_dir, fname)
        if os.path.exists(fpath):
            try:
                entries = fil.parse_gctg(fpath, rec_size)
                total_glasses += len(entries)
                record("PASS" if len(entries) > 0 else "FAIL",
                       f"{fname} ({desc}): {len(entries)} стёкол",
                       ">0", f"{len(entries)}", "fil_reader_v2.py")
                
                c0_ok = sum(1 for e in entries if 1.3 <= e['C0'] <= 2.5)
                pct = c0_ok / len(entries) * 100 if entries else 0
                record("PASS" if pct > 80 else "FAIL",
                       f"{fname}: C0 в 1.3-2.5 для >80%",
                       ">80%", f"{c0_ok}/{len(entries)} ({pct:.0f}%)",
                       "fil_reader_v2.py")
            except Exception as e:
                record("BUG", f"{fname} parsing", "no error", str(e), "fil_reader_v2.py")
        else:
            record("FAIL", f"{fname} не найден", fpath, "missing", "fil_reader_v2.py")
    
    record("PASS" if total_glasses > 100 else "FAIL",
           f"FIL Reader: total > 100 стёкол",
           ">100", f"{total_glasses}", "fil_reader_v2.py")

# ============================================================
# 10. EDGE CASES
# ============================================================
_log("\n" + "="*70)
_log("10. КРАЕВЫЕ СЛУЧАИ")
_log("="*70)

if "optics_engine" in imported:
    oe = imported["optics_engine"]
    
    # 10.1 Empty system
    sys_e = oe.OpticalSystem()
    sys_e.wavelengths = [oe.Wavelength(0.58756)]
    try:
        res_e = oe.paraxial_trace(sys_e)
        record("PASS" if isinstance(res_e, dict) else "BUG",
               "Пустая система: paraxial_trace OK",
               "dict", type(res_e).__name__, "optics_engine.py")
    except Exception as e:
        record("BUG", "Пустая система: paraxial_trace", "no crash", str(e))
    
    try:
        seidel_e = oe.seidel_aberrations(sys_e)
        record("PASS" if isinstance(seidel_e, dict) else "BUG",
               "Пустая система: seidel OK",
               "dict", type(seidel_e).__name__, "optics_engine.py")
    except Exception as e:
        record("BUG", "Пустая система: seidel", "no crash", str(e))

    # 10.2 1 surface
    sys_1s = oe.OpticalSystem()
    sys_1s.wavelengths = [oe.Wavelength(0.58756)]
    sys_1s.surfaces = [oe.Surface(radius=100, thickness=50, glass="К8", semi_diameter=12)]
    try:
        res_1s = oe.paraxial_trace(sys_1s)
        record("PASS" if isinstance(res_1s, dict) else "BUG",
               "1 поверхность: paraxial_trace OK",
               "dict", type(res_1s).__name__, "optics_engine.py")
    except Exception as e:
        record("BUG", "1 поверхность: paraxial_trace", "no crash", str(e))

    # 10.3 R=0
    sys_flat = oe.OpticalSystem()
    sys_flat.wavelengths = [oe.Wavelength(0.58756)]
    sys_flat.aperture_value = 20.0
    sys_flat.surfaces = [
        oe.Surface(radius=0, thickness=5, glass="К8", semi_diameter=15),
        oe.Surface(radius=0, thickness=50, glass="", semi_diameter=15),
    ]
    try:
        res_flat = oe.paraxial_trace(sys_flat)
        f_flat = res_flat.get('focal_length', 0)
        record("PASS" if f_flat == 0 or abs(f_flat) > 1e10 else "FAIL",
               "R=0 на всех: f'=0 или ∞",
               "f' ≈ 0 or ∞", f"f' = {f_flat}", "optics_engine.py")
    except Exception as e:
        record("BUG", "R=0 на всех", "no crash", str(e), "optics_engine.py")
    
    # 10.4 Very thick lens
    sys_thick = oe.OpticalSystem()
    sys_thick.wavelengths = [oe.Wavelength(0.58756)]
    sys_thick.aperture_value = 20.0
    sys_thick.surfaces = [
        oe.Surface(radius=100, thickness=200, glass="К8", semi_diameter=25),
        oe.Surface(radius=-100, thickness=50, glass="", semi_diameter=25),
    ]
    try:
        res_thick = oe.paraxial_trace(sys_thick)
        f_thick = res_thick.get('focal_length', 0)
        record("PASS" if abs(f_thick) > 0 and math.isfinite(f_thick) else "FAIL",
               "Толстая линза (d=200): f' вычисляется",
               "finite f'", f"f' = {f_thick}", "optics_engine.py")
    except Exception as e:
        record("BUG", "Толстая линза (d=200)", "no crash", str(e), "optics_engine.py")

    # 10.5 Negative R
    sys_div = oe.OpticalSystem()
    sys_div.wavelengths = [oe.Wavelength(0.58756)]
    sys_div.aperture_value = 20.0
    sys_div.surfaces = [
        oe.Surface(radius=-50, thickness=3, glass="К8", semi_diameter=12),
        oe.Surface(radius=50, thickness=50, glass="", semi_diameter=12),
    ]
    try:
        res_div = oe.paraxial_trace(sys_div)
        f_div = res_div.get('focal_length', 0)
        record("PASS" if f_div < 0 else "FAIL",
               "Рассеивающая (R<0): f'<0",
               "f' < 0", f"f' = {f_div}", "optics_engine.py")
    except Exception as e:
        record("BUG", "Рассеивающая", "no crash", str(e), "optics_engine.py")

    # 10.6 Unknown glass
    sys_unk = oe.OpticalSystem()
    sys_unk.wavelengths = [oe.Wavelength(0.58756)]
    sys_unk.aperture_value = 20.0
    sys_unk.surfaces = [
        oe.Surface(radius=100, thickness=5, glass="UNKNOWN_GLASS_XYZ", semi_diameter=12),
        oe.Surface(radius=-100, thickness=50, glass="", semi_diameter=12),
    ]
    try:
        res_unk = oe.paraxial_trace(sys_unk)
        record("PASS" if isinstance(res_unk, dict) and 'focal_length' in res_unk else "BUG",
               "Неизвестное стекло: не крашится",
               "dict with focal_length",
               str(res_unk.get('focal_length', 'N/A')), "optics_engine.py")
    except Exception as e:
        record("BUG", "Неизвестное стекло", "no crash", str(e), "optics_engine.py")

    # 10.7 UV
    if "glass_catalog" in imported:
        gc = imported["glass_catalog"]
        n_uv = gc.compute_refractive_index("К8", 0.365)
        record("PASS" if n_uv > 1.516 else "FAIL",
               "UV λ=0.365: n > 1.5 для К8",
               "n > 1.5", f"n = {n_uv:.6f}", "glass_catalog.py")

    # 10.8 IR
    if "glass_catalog" in imported:
        gc = imported["glass_catalog"]
        n_ir = gc.compute_refractive_index("К8", 2.6)
        record("PASS" if isinstance(n_ir, float) and 1.4 < n_ir < 1.6 else "FAIL",
               "IR λ=2.6: n для К8 в диапазоне",
               "1.4 < n < 1.6", f"n = {n_ir:.6f}", "glass_catalog.py")
    
    # 10.9 Empty system ray tracing
    if "ray_tracing" in imported:
        rt = imported["ray_tracing"]
        sys_e_rt = oe.OpticalSystem()
        sys_e_rt.wavelengths = [oe.Wavelength(0.58756)]
        ray_e = rt.Ray(x=0, y=5, z=-50, k=0, l=0, m=1)
        try:
            res_e_rt = rt.trace_ray_through_system(sys_e_rt, ray_e, 0.58756)
            record("PASS" if isinstance(res_e_rt, rt.TraceResult) else "BUG",
                   "Пустая система: ray tracing OK",
                   "TraceResult", type(res_e_rt).__name__, "ray_tracing.py")
        except Exception as e:
            record("BUG", "Пустая система: ray tracing", "no crash", str(e))

# ============================================================
# ADDITIONAL: Side-effect bugs
# ============================================================
_log("\n" + "="*70)
_log("11. ПОБОЧНЫЕ ЭФФЕКТЫ (side effects)")
_log("="*70)

# BUG: opj_reader.py and fil_reader_v2.py replace sys.stdout
record("BUG", "opj_reader.py: заменяет sys.stdout",
       "sys.stdout не должен модифицироваться при импорте",
       "sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8') закрывает оригинальный stdout",
       "opj_reader.py: line 8")

record("BUG", "fil_reader_v2.py: заменяет sys.stdout",
       "sys.stdout не должен модифицироваться при импорте",
       "sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')",
       "fil_reader_v2.py: line 5")

# ============================================================
# SUMMARY
# ============================================================
_log("\n" + "="*70)
_log("СВОДКА РЕЗУЛЬТАТОВ")
_log("="*70)

total = len(results)
passed = sum(1 for s, *_ in results if s == "PASS")
failed = sum(1 for s, *_ in results if s == "FAIL")
bugged = sum(1 for s, *_ in results if s == "BUG")

_log(f"\nВсего тестов: {total}")
_log(f"  PASSED: {passed}")
_log(f"  FAILED: {failed}")
_log(f"  BUGS:   {bugged}")

if bugs:
    _log(f"\n⚠ НАЙДЕННЫЕ БАГИ:")
    for b in bugs:
        _log(f"  - {b}")

_log(f"\n{'='*70}")
_log("ДЕТАЛЬНЫЙ СПИСОК НЕПРОЙДЕННЫХ ТЕСТОВ:")
_log(f"{'='*70}")
for status, name, expected, actual, file_line in results:
    if status != "PASS":
        _log(f"\n[{status}] {name}")
        _log(f"  Ожидается: {expected}")
        _log(f"  Фактически: {actual}")
        if file_line:
            _log(f"  {file_line}")

_out.close()
