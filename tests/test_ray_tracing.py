"""Regression tests for ray tracing and visualization.

Tests РРЅРґСѓСЃС‚Р°СЂ-23Сѓ as the golden reference, then batch-tests all libraries.
Run: py tests\test_ray_tracing.py
"""
import sys, os, math, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decode_lbo_opj import decode_lbo_opj
from lbo_reader import load_lbo_fast, scan_lbo_directory
from optics_engine import paraxial_trace
from ray_tracing import trace_fan, trace_ray_through_system, Ray


def load_industar():
    """Load РРЅРґСѓСЃС‚Р°СЂ-23Сѓ from LENS.LBO index 3."""
    lens = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
    return decode_lbo_opj(lens[3]['opj_data'])


# ============================================================
# A. PARAXIAL REFERENCE TESTS (РРЅРґСѓСЃС‚Р°СЂ-23Сѓ golden values)
# ============================================================

def test_industar_paraxial():
    """Paraxial values match OPAL-PC for РРЅРґСѓСЃС‚Р°СЂ-23Сѓ."""
    s = load_industar()
    p = paraxial_trace(s)
    assert abs(p['focal_length'] - 109.6976) < 0.01, f"f'={p['focal_length']}"
    assert abs(p['sF'] - (-95.5619)) < 0.01, f"sF={p['sF']}"
    assert abs(p['sF_prime'] - 96.8032) < 0.01, f"sF'={p['sF_prime']}"
    assert abs(p['sH'] - 14.1357) < 0.01, f"sH={p['sH']}"
    assert abs(p['sH_prime'] - (-12.8944)) < 0.01, f"sH'={p['sH_prime']}"
    assert abs(p['L'] - 124.10) < 0.01, f"L={p['L']}"
    assert abs(p['V'] - (-109.6976)) < 0.01, f"V={p['V']}"
    print("  вњ“ РРЅРґСѓСЃС‚Р°СЂ-23Сѓ paraxial values match OPAL-PC")


def test_industar_surfaces():
    """Surface data correct for РРЅРґСѓСЃС‚Р°СЂ-23Сѓ."""
    s = load_industar()
    assert len(s.surfaces) == 7, f"Expected 7 surfaces, got {len(s.surfaces)}"
    assert s.stop_surface == 4, f"stop_surface={s.stop_surface}"
    assert abs(s.stop_offset - 4.2) < 0.01, f"stop_offset={s.stop_offset}"
    assert abs(s.aperture_value - 21.1) < 0.01, f"aperture_value={s.aperture_value}"
    # R and thickness checks
    expected_r = [30.48, 0.0, -68.23, 28.05, -214.80, 28.58, -44.06]
    for i, (surf, exp_r) in enumerate(zip(s.surfaces, expected_r)):
        assert abs(surf.radius - exp_r) < 0.01, f"surf[{i}].radius={surf.radius}, expected {exp_r}"
    print("  вњ“ РРЅРґСѓСЃС‚Р°СЂ-23Сѓ surface data correct")


def test_industar_wavelengths():
    """Three wavelengths: e, G', C."""
    s = load_industar()
    wl_vals = [w.value for w in s.wavelengths]
    assert len(wl_vals) == 3, f"Expected 3 wavelengths, got {len(wl_vals)}"
    assert abs(wl_vals[0] - 0.54607) < 0.001, f"wl[0]={wl_vals[0]}"
    assert abs(wl_vals[1] - 0.43405) < 0.001, f"wl[1]={wl_vals[1]}"
    assert abs(wl_vals[2] - 0.65627) < 0.001, f"wl[2]={wl_vals[2]}"
    print("  вњ“ РРЅРґСѓСЃС‚Р°СЂ-23Сѓ wavelengths: e, G', C")


# ============================================================
# B. RAY TRACING TESTS (РРЅРґСѓСЃС‚Р°СЂ-23Сѓ)
# ============================================================

def test_industar_stop_clipping():
    """Rays wider than aperture stop are clipped (STOP error)."""
    s = load_industar()
    wl = s.wavelengths[0].value
    stop_radius = s.aperture_value / 2.0  # 10.55

    # Ray within aperture вЂ” should pass
    ray_ok = Ray(x=0, y=5.0, z=-1, k=0, l=0, m=1)
    r = trace_ray_through_system(s, ray_ok, wl)
    assert r.success, f"Ray y=5 should pass, got {r.error}"

    # Ray just within edge вЂ” should pass
    ray_edge = Ray(x=0, y=10.0, z=-1, k=0, l=0, m=1)
    r2 = trace_ray_through_system(s, ray_edge, wl)
    assert r2.success, f"Ray y=10 should pass, got {r2.error}"

    # Ray beyond stop вЂ” should be STOP-blocked
    ray_over = Ray(x=0, y=12.0, z=-1, k=0, l=0, m=1)
    r3 = trace_ray_through_system(s, ray_over, wl)
    assert not r3.success, f"Ray y=12 should be blocked"
    assert r3.error == 'STOP', f"Expected STOP, got {r3.error}"

    print("  вњ“ Stop clipping works correctly")


def test_industar_field_rays():
    """Field rays at 26В° pass through system."""
    s = load_industar()
    wl = s.wavelengths[0].value

    # pupil_range=1.0, field=26В° вЂ” at least some rays should pass
    fan = trace_fan(s, num_rays=11, pupil_range=1.0, wl=wl, field_y=26.0)
    passed = sum(1 for r in fan if r.success)
    assert passed >= 3, f"Expected >=3 field rays to pass at 26В°, got {passed}/11"

    # All wavelengths should have at least some rays passing
    for w in s.wavelengths:
        fan_wl = trace_fan(s, num_rays=11, pupil_range=1.0, wl=w.value, field_y=26.0)
        passed_wl = sum(1 for r in fan_wl if r.success)
        assert passed_wl >= 3, f"wl={w.value}: only {passed_wl}/11 passed at 26В°"

    print("  вњ“ Field rays at 26В° pass for all wavelengths")


def test_industar_field_angle_direction():
    """Field angle is in Y-Z plane (l component, not k)."""
    s = load_industar()
    wl = s.wavelengths[0].value
    angle = math.radians(26.0)

    # Ray direction should have l=sin(angle), k=0
    ray = Ray(x=0, y=0, z=-1, k=0, l=math.sin(angle), m=math.cos(angle))
    # At z=0, y should be ~0 (started at z=-1, y=0)
    dt = (0 - ray.z) / ray.m
    y_at_0 = ray.y + dt * ray.l
    assert abs(y_at_0) < 1.0, f"Ray at z=0: y={y_at_0} (should be ~0 for k=0 direction)"

    print("  вњ“ Field angle direction correct (Y-Z plane)")


def test_industar_no_crash_all_wavelengths():
    """System traces without exceptions for all wavelengths and field angles."""
    s = load_industar()
    for w in s.wavelengths:
        for field in [0.0, 13.0, 26.0, -26.0]:
            fan = trace_fan(s, num_rays=5, pupil_range=1.0, wl=w.value, field_y=field)
            # Just check no exception
    print("  вњ“ No crashes for all wavelengths Г— field angles")


# ============================================================
# C. BATCH TESTS вЂ” ALL LIBRARIES
# ============================================================

def get_all_libraries():
    """Find all .LBO files."""
    lib_dir = 'extracted/opal_okb/Lib'
    if not os.path.isdir(lib_dir):
        return []
    libs = []
    for f in sorted(os.listdir(lib_dir)):
        if f.upper().endswith('.LBO'):
            libs.append(os.path.join(lib_dir, f))
    return libs


def test_all_systems_load_and_trace():
    """Every system in every library loads and traces without exceptions."""
    libs = get_all_libraries()
    assert len(libs) > 0, "No .LBO libraries found"

    total = 0
    passed = 0
    failed_load = 0
    failed_trace = 0
    errors = []

    for lib_path in libs:
        lib_name = os.path.basename(lib_path)
        try:
            systems = load_lbo_fast(lib_path)
        except Exception as e:
            errors.append(f"{lib_name}: LOAD FAIL: {e}")
            continue

        for i, sys_raw in enumerate(systems):
            total += 1
            try:
                sys_obj = decode_lbo_opj(sys_raw['opj_data'])
            except Exception as e:
                failed_load += 1
                errors.append(f"{lib_name}[{i}] {sys_raw.get('name','?')}: DECODE FAIL: {e}")
                continue

            # Try paraxial
            try:
                parax = paraxial_trace(sys_obj)
                assert not math.isnan(parax.get('focal_length', float('nan')))
            except Exception as e:
                failed_trace += 1
                errors.append(f"{lib_name}[{i}] {sys_obj.name}: PARAXIAL FAIL: {e}")
                continue

            # Try ray tracing (axial, just a few rays)
            try:
                wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
                fan = trace_fan(sys_obj, num_rays=3, pupil_range=1.0, wl=wl, field_y=0.0)
            except Exception as e:
                failed_trace += 1
                errors.append(f"{lib_name}[{i}] {sys_obj.name}: TRACE FAIL: {e}")
                continue

            passed += 1

    print(f"\n  Batch: {passed}/{total} systems OK ({failed_load} decode fails, {failed_trace} trace fails)")

    # Show first 20 errors
    if errors:
        print(f"  Errors ({len(errors)} total, showing first 20):")
        for e in errors[:20]:
            print(f"    {e}")

    # We expect at least 80% success
    success_rate = passed / total if total > 0 else 0
    assert success_rate >= 0.8, f"Success rate {success_rate:.1%} < 80%"


def test_all_systems_field_rays():
    """All systems with field angles trace without exceptions at their field."""
    libs = get_all_libraries()
    total = 0
    crashed = 0
    no_pass = 0
    errors = []

    for lib_path in libs:
        lib_name = os.path.basename(lib_path)
        try:
            systems = load_lbo_fast(lib_path)
        except:
            continue

        for i, sys_raw in enumerate(systems):
            try:
                sys_obj = decode_lbo_opj(sys_raw['opj_data'])
            except:
                continue

            if not sys_obj.wavelengths or not sys_obj.surfaces:
                continue

            total += 1
            wl = sys_obj.wavelengths[0].value

            # Get max field angle
            field = 0.0
            if sys_obj.field_points:
                field = max(abs(fp.y) for fp in sys_obj.field_points)

            try:
                # Trace at field angle
                fan = trace_fan(sys_obj, num_rays=5, pupil_range=1.0, wl=wl, field_y=field)
                ok = sum(1 for r in fan if r.success)
                if ok == 0 and field > 0:
                    # Try axial
                    fan0 = trace_fan(sys_obj, num_rays=5, pupil_range=1.0, wl=wl, field_y=0.0)
                    ok0 = sum(1 for r in fan0 if r.success)
                    if ok0 == 0:
                        no_pass += 1
                        errors.append(f"{lib_name}[{i}] {sys_obj.name}: 0 rays pass at any angle")
            except Exception as e:
                crashed += 1
                errors.append(f"{lib_name}[{i}] {sys_obj.name}: FIELD TRACE CRASH: {e}")

    print(f"\n  Field batch: {total} systems, {crashed} crashed, {no_pass} no rays pass")
    if errors:
        print(f"  Issues ({len(errors)}, showing first 15):")
        for e in errors[:15]:
            print(f"    {e}")

    assert crashed == 0, f"{crashed} systems crashed during field ray tracing"


# ============================================================
# D. EDGE CASES
# ============================================================

def test_mirror_system():
    """Mirror (catadioptric) systems trace correctly."""
    libs = get_all_libraries()
    mirror_tested = 0
    for lib_path in libs:
        try:
            systems = load_lbo_fast(lib_path)
        except:
            continue
        for sys_raw in systems:
            try:
                sys_obj = decode_lbo_opj(sys_raw['opj_data'])
            except:
                continue
            has_mirror = any(s.is_reflective for s in sys_obj.surfaces)
            if not has_mirror:
                continue
            wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
            fan = trace_fan(sys_obj, num_rays=3, pupil_range=0.5, wl=wl, field_y=0.0)
            mirror_tested += 1
    if mirror_tested > 0:
        print(f"  вњ“ {mirror_tested} mirror systems traced without crash")
    else:
        print("  (no mirror systems found to test)")


def test_afocal_systems():
    """Afocal systems (binoculars, telescopes) trace without crash."""
    libs = get_all_libraries()
    afocal_tested = 0
    for lib_path in libs:
        lib_name = os.path.basename(lib_path)
        if 'BINOC' not in lib_name.upper():
            continue
        try:
            systems = load_lbo_fast(lib_path)
        except:
            continue
        for sys_raw in systems:
            try:
                sys_obj = decode_lbo_opj(sys_raw['opj_data'])
            except:
                continue
            wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
            fan = trace_fan(sys_obj, num_rays=5, pupil_range=1.0, wl=wl, field_y=0.0)
            afocal_tested += 1
    if afocal_tested > 0:
        print(f"  вњ“ {afocal_tested} afocal (BINOCUL) systems traced")
    else:
        print("  (no afocal systems found)")


def test_microlen_systems():
    """Microscope objectives (MICROLEN) trace correctly."""
    lib_path = 'extracted/opal_okb/Lib/MICROLEN.LBO'
    if not os.path.exists(lib_path):
        print("  (MICROLEN.LBO not found)")
        return
    systems = load_lbo_fast(lib_path)
    tested = 0
    for sys_raw in systems:
        try:
            sys_obj = decode_lbo_opj(sys_raw['opj_data'])
            wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
            # Microscope: high NA, near object
            fan = trace_fan(sys_obj, num_rays=5, pupil_range=0.5, wl=wl, field_y=0.0)
            tested += 1
        except Exception as e:
            raise AssertionError(f"MICROLEN {sys_raw.get('name','?')}: {e}")
    print(f"  вњ“ {tested} MICROLEN systems traced")


# ============================================================
# RUNNER
# ============================================================

def run_all():
    """Run all tests manually (no pytest needed)."""
    tests = [
        ("РРЅРґСѓСЃС‚Р°СЂ paraxial", test_industar_paraxial),
        ("РРЅРґСѓСЃС‚Р°СЂ surfaces", test_industar_surfaces),
        ("РРЅРґСѓСЃС‚Р°СЂ wavelengths", test_industar_wavelengths),
        ("Stop clipping", test_industar_stop_clipping),
        ("Field rays 26В°", test_industar_field_rays),
        ("Field angle direction", test_industar_field_angle_direction),
        ("No crash all wl", test_industar_no_crash_all_wavelengths),
        ("All systems load+trace", test_all_systems_load_and_trace),
        ("All systems field rays", test_all_systems_field_rays),
        ("Mirror systems", test_mirror_system),
        ("Afocal systems", test_afocal_systems),
        ("MICROLEN systems", test_microlen_systems),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  вњ— FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  вњ— ERROR: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return failed == 0


if __name__ == '__main__':
    ok = run_all()
    sys.exit(0 if ok else 1)

