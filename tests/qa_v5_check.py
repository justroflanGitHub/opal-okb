#!/usr/bin/env python3
"""QA v5 -- full module check"""
import sys, math, json, os, traceback
sys.stdout.reconfigure(encoding='utf-8')

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

PASS = 0
FAIL = 0

def mark(label, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok: PASS += 1
    else: FAIL += 1
    print(f"[{tag}] {label}" + (f"  {detail}" if detail else ""))

BLOCKED = "blocked by optics_engine"

# ============================================================
# 0. BLOCKER: optics_engine import
# ============================================================
print("=" * 60)
print("BLOCKER: optics_engine import")
print("=" * 60)

optics_ok = False
try:
    from optics_engine import OpticalSystem, Surface, calculate_seidel_sums, cardinal_points
    optics_ok = True
    mark("optics_engine import", True)
except Exception as e:
    mark("optics_engine import", False, "apply_vignetting() line 89 uses OpticalSystem before class def (line 188)")

# ============================================================
# 1. YADRO
# ============================================================
print("\n" + "=" * 60)
print("YADRO")
print("=" * 60)

if optics_ok:
    s = OpticalSystem()
    s.add_surface(Surface(radius=50, thickness=5, glass='K8'))
    s.add_surface(Surface(radius=-200, thickness=0, glass=''))
    S = calculate_seidel_sums(s)
    nz = all(abs(S[k]) > 1e-15 for k in ['SI','SII','SIII','SIV','SV'])
    mark("Seidel nonzero", nz, f"SI={S['SI']:.8f} SII={S['SII']:.8f} SIII={S['SIII']:.8f} SIV={S['SIV']:.8f} SV={S['SV']:.8f}")
    cp = cardinal_points(s)
    bfd_val = cp.get('bfd', cp.get('sG_prime', None))
    mark("BFD numeric, no 'n'", bfd_val is not None and isinstance(bfd_val, (int,float)), f"bfd={bfd_val} keys={list(cp.keys())}")
else:
    mark("Seidel nonzero", False, BLOCKED)
    mark("BFD numeric, no n", False, BLOCKED)

# glass_catalog
try:
    import glass_catalog as gc_mod
    cat = getattr(gc_mod, 'CATALOG', getattr(gc_mod, 'catalog', None))
    if cat is None:
        # maybe it's a function
        for fn in ['get_catalog', 'GlassCatalog']:
            obj = getattr(gc_mod, fn, None)
            if callable(obj):
                cat = obj()
                break
    if isinstance(cat, dict):
        cnt = len(cat)
    elif hasattr(cat, 'catalog'):
        cnt = len(cat.catalog)
    else:
        cnt = 0
    mark("glass_catalog fallback", cnt >= 889, f"count={cnt}")
except Exception as e:
    mark("glass_catalog", False, str(e))

# glass_catalog_full
try:
    import glass_catalog_full as gcf_mod
    cat = getattr(gcf_mod, 'CATALOG', getattr(gcf_mod, 'catalog', None))
    for fn in ['get_catalog', 'GlassCatalogFull']:
        obj = getattr(gcf_mod, fn, None)
        if callable(cat):
            cat = obj()
    if isinstance(cat, dict):
        cnt = len(cat)
    elif hasattr(cat, 'catalog'):
        cnt = len(cat.catalog)
    else:
        cnt = 0
    mark("glass_catalog_full", cnt >= 889, f"count={cnt}")
except Exception as e:
    mark("glass_catalog_full", False, str(e))

# ray_tracing
if optics_ok:
    try:
        from ray_tracing import trace_ray, Ray
        s2 = OpticalSystem()
        s2.add_surface(Surface(radius=100, thickness=5, glass='K8'))
        s2.add_surface(Surface(radius=-100, thickness=95, glass=''))
        r = trace_ray(s2, Ray(y=1.0, u=0.0))
        mark("ray_tracing", r is not None, f"result={r}")
    except Exception as e:
        mark("ray_tracing", False, str(e))
else:
    mark("ray_tracing", False, BLOCKED)

# ============================================================
# 2. ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("ANALYSIS")
print("=" * 60)

def make_sys():
    s = OpticalSystem()
    s.add_surface(Surface(radius=50, thickness=5, glass='K8'))
    s.add_surface(Surface(radius=-200, thickness=45, glass=''))
    return s

analysis_tests = [
    ("aberrations spot", "aberrations", "Aberrations", "spot_diagram"),
    ("aberrations OPL wavefront", "aberrations", "Aberrations", "opl_wavefront"),
    ("aberrations FFT MTF", "aberrations", "Aberrations", "fft_mtf"),
    ("diffraction_mtf", "diffraction_mtf", "DiffractionMTF", "calculate"),
    ("advanced_analysis PSF", "advanced_analysis", "AdvancedAnalysis", "psf"),
    ("advanced_analysis LSF", "advanced_analysis", "AdvancedAnalysis", "lsf"),
    ("advanced_analysis ENC", "advanced_analysis", "AdvancedAnalysis", "encircled_energy"),
    ("advanced_analysis PTF", "advanced_analysis", "AdvancedAnalysis", "ptf"),
]

if optics_ok:
    for label, mod, cls, method in analysis_tests:
        try:
            m = __import__(mod)
            c = getattr(m, cls)()
            s = make_sys()
            r = getattr(c, method)(s)
            mark(label, r is not None, f"type={type(r).__name__}")
        except Exception as e:
            mark(label, False, str(e))
else:
    for label, *_ in analysis_tests:
        mark(label, False, BLOCKED)

# ============================================================
# 3. NEW: polychromatic
# ============================================================
print("\n" + "=" * 60)
print("NEW: polychromatic")
print("=" * 60)

poly_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'polychromatic.py')
if not os.path.exists(poly_path):
    mark("polychromatic.py", False, "file not found on disk")
    mark("polychromatic spot", False, "module missing")
    mark("polychromatic MTF", False, "module missing")
    mark("polychromatic RMS", False, "module missing")
elif optics_ok:
    for label, cls in [("polychromatic spot","PolychromaticSpot"),("polychromatic MTF","PolychromaticMTF"),("polychromatic RMS","PolychromaticRMS")]:
        try:
            m = __import__('polychromatic')
            c = getattr(m, cls)()
            s = make_sys()
            r = c.calculate(s, wavelengths=[0.486, 0.588, 0.656])
            mark(label, r is not None)
        except Exception as e:
            mark(label, False, str(e))
else:
    mark("polychromatic spot", False, BLOCKED)
    mark("polychromatic MTF", False, BLOCKED)
    mark("polychromatic RMS", False, BLOCKED)

# ============================================================
# 4. FILES
# ============================================================
print("\n" + "=" * 60)
print("FILES")
print("=" * 60)

if optics_ok:
    # opj_reader
    try:
        from opj_reader import OPJReader
        reader = OPJReader()
        opj_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'opj_files')
        opj_files = [f for f in os.listdir(opj_dir) if f.upper().endswith('.OPJ')] if os.path.isdir(opj_dir) else []
        mark("opj_reader 83/83 files", len(opj_files) >= 83, f"count={len(opj_files)}")
        if opj_files:
            data = reader.read(os.path.join(opj_dir, opj_files[0]))
            mark("opj_reader read", data is not None, f"file={opj_files[0]}")
            has_glass = False
            if isinstance(data, dict):
                for surf in data.get('surfaces', []):
                    g = surf.get('glass', '')
                    if g and g not in ('', 'VOZDUH', 'AIR'):
                        has_glass = True; break
            mark("opj_reader glasses", has_glass, "non-air glass found")
    except Exception as e:
        mark("opj_reader", False, str(e))

    # io_utils
    try:
        from io_utils import IOUtils
        io = IOUtils()
        s = make_sys()
        j = io.to_json(s)
        mark("io_utils to_json", len(j) > 10, f"len={len(j)}")
        r = io.from_json(j)
        mark("io_utils JSON roundtrip", r is not None, f"type={type(r).__name__}")
    except Exception as e:
        mark("io_utils", False, str(e))

    # achromat
    try:
        from achromat import AchromatDesigner
        ad = AchromatDesigner()
        result = ad.design(f_target=100, glass1='K8', glass2='TF5')
        fp = result.get('f_prime', result.get('f', 0))
        mark("achromat f approx 100", abs(fp - 100) < 5, f"f'={fp:.2f}")
    except Exception as e:
        mark("achromat", False, str(e))
else:
    for l in ["opj_reader 83/83","opj_reader read","opj_reader glasses","io_utils to_json","io_utils roundtrip","achromat f approx 100"]:
        mark(l, False, BLOCKED)

# ============================================================
# 5. UTILS
# ============================================================
print("\n" + "=" * 60)
print("UTILS")
print("=" * 60)

if optics_ok:
    try:
        from system_utils import SystemUtils
        su = SystemUtils()
        s = make_sys()
        rev = su.reverse(s)
        mark("system_utils reverse", rev is not None, f"type={type(rev).__name__}")
        sc = su.scale(s, factor=2.0)
        mark("system_utils scale", sc is not None, f"type={type(sc).__name__}")
        gost = su.gost_r(s)
        mark("system_utils GOST R", gost is not None, f"type={type(gost).__name__}")
    except Exception as e:
        mark("system_utils", False, str(e))
else:
    for l in ["system_utils reverse","system_utils scale","system_utils GOST R"]:
        mark(l, False, BLOCKED)

# ============================================================
# 6. GUI
# ============================================================
print("\n" + "=" * 60)
print("GUI")
print("=" * 60)

if optics_ok:
    try:
        from main import MainWindow
        mark("MainWindow import", True)
    except Exception as e:
        mark("MainWindow import", False, str(e))
    try:
        from analysis_gui import AnalysisPanel
        mark("AnalysisPanel import", True)
    except Exception as e:
        mark("AnalysisPanel import", False, str(e))
else:
    mark("MainWindow import", False, BLOCKED)
    mark("AnalysisPanel import", False, BLOCKED)

# Source checks (no import)
try:
    with open('analysis_gui.py', 'r', encoding='utf-8') as f:
        src = f.read()
    tc = src.count('addTab') + src.count('insertTab')
    mark("AnalysisPanel >= 13 tabs", tc >= 13, f"addTab count={tc}")
except Exception as e:
    mark("AnalysisPanel tabs", False, str(e))

try:
    with open('main.py', 'r', encoding='utf-8') as f:
        src = f.read()
    mark("MainWindow.viz ref", 'viz' in src.lower() or 'visualization' in src.lower())
except Exception as e:
    mark("MainWindow.viz", False, str(e))

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"SUMMARY: {PASS}/{total} PASS, {FAIL} FAIL")
if not optics_ok:
    print("CRITICAL BUG: optics_engine.py line 89 -- apply_vignetting() references OpticalSystem before class definition (line 188)")
    print("FIX: add 'from __future__ import annotations' at top of optics_engine.py")
print("=" * 60)
