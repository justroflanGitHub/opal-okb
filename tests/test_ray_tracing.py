"""Regression tests for ray tracing and visualization.

Tests Индустар-23у as the golden reference, then batch-tests all libraries.

Запуск:
    pytest tests/test_ray_tracing.py -v        # через pytest
    py tests\\test_ray_tracing.py                # напрямую (встроенный runner)
"""
import sys
import os
import math

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decode_lbo_opj import decode_lbo_opj
from lbo_reader import load_lbo_fast
from optics_engine import paraxial_trace
from ray_tracing import trace_fan, trace_ray_through_system, Ray


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #

_LIB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "extracted", "opal_okb", "Lib",
)


def _load_industar():
    """Load Индустар-23у from LENS.LBO index 3."""
    lens = load_lbo_fast(os.path.join(_LIB_DIR, "LENS.LBO"))
    return decode_lbo_opj(lens[3]['opj_data'])


def _get_all_libraries():
    """Find all .LBO files in the Lib directory."""
    if not os.path.isdir(_LIB_DIR):
        return []
    libs = []
    for f in sorted(os.listdir(_LIB_DIR)):
        if f.upper().endswith('.LBO'):
            libs.append(os.path.join(_LIB_DIR, f))
    return libs


# --------------------------------------------------------------------------- #
# Module-level cached fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def industar():
    """Декодированная система Индустар-23у — golden reference."""
    return _load_industar()


@pytest.fixture(scope="module")
def industar_parax(industar):
    """Параксиальный расчёт Индустар-23у."""
    return paraxial_trace(industar)


# =========================================================================== #
# A. PARAXIAL REFERENCE TESTS (Индустар-23у golden values)
# =========================================================================== #

class TestIndustarParaxial:
    """Paraxial values match OPAL-PC for Индустар-23у."""

    def test_focal_length(self, industar_parax):
        f = industar_parax['focal_length']
        assert f == pytest.approx(109.6976, abs=0.01), f"f'={f}"

    def test_sF(self, industar_parax):
        assert industar_parax['sF'] == pytest.approx(-95.5619, abs=0.01), \
            f"sF={industar_parax['sF']}"

    def test_sF_prime(self, industar_parax):
        assert industar_parax['sF_prime'] == pytest.approx(96.8032, abs=0.01), \
            f"sF'={industar_parax['sF_prime']}"

    def test_sH(self, industar_parax):
        assert industar_parax['sH'] == pytest.approx(14.1357, abs=0.01), \
            f"sH={industar_parax['sH']}"

    def test_sH_prime(self, industar_parax):
        assert industar_parax['sH_prime'] == pytest.approx(-12.8944, abs=0.01), \
            f"sH'={industar_parax['sH_prime']}"

    def test_L(self, industar_parax):
        assert industar_parax['L'] == pytest.approx(124.10, abs=0.01), \
            f"L={industar_parax['L']}"

    def test_V(self, industar_parax):
        assert industar_parax['V'] == pytest.approx(-109.6976, abs=0.01), \
            f"V={industar_parax['V']}"


class TestIndustarSurfaces:
    """Surface data correct for Индустар-23у."""

    def test_surface_count(self, industar):
        assert len(industar.surfaces) == 7

    def test_stop_surface(self, industar):
        assert industar.stop_surface == 4

    def test_stop_offset(self, industar):
        assert industar.stop_offset == pytest.approx(4.2, abs=0.01)

    def test_aperture_value(self, industar):
        assert industar.aperture_value == pytest.approx(21.1, abs=0.01)

    @pytest.mark.parametrize("idx,expected_r", [
        (0, 30.48),
        (1, 0.0),
        (2, -68.23),
        (3, 28.05),
        (4, -214.80),
        (5, 28.58),
        (6, -44.06),
    ])
    def test_radius(self, industar, idx, expected_r):
        actual = industar.surfaces[idx].radius
        assert actual == pytest.approx(expected_r, abs=0.01), \
            f"surf[{idx}].radius={actual}, expected {expected_r}"


class TestIndustarWavelengths:
    """Three wavelengths: e, G', C."""

    def test_three_wavelengths(self, industar):
        assert len(industar.wavelengths) == 3

    def test_e_wavelength(self, industar):
        assert industar.wavelengths[0].value == pytest.approx(0.54607, abs=0.001)

    def test_g_prime_wavelength(self, industar):
        assert industar.wavelengths[1].value == pytest.approx(0.43405, abs=0.001)

    def test_c_wavelength(self, industar):
        assert industar.wavelengths[2].value == pytest.approx(0.65627, abs=0.001)


# =========================================================================== #
# B. RAY TRACING TESTS (Индустар-23у)
# =========================================================================== #

class TestIndustarStopClipping:
    """Rays wider than aperture stop are clipped (STOP error)."""

    def test_ray_within_aperture_passes(self, industar):
        wl = industar.wavelengths[0].value
        ray = Ray(x=0, y=5.0, z=-1, k=0, l=0, m=1)
        r = trace_ray_through_system(industar, ray, wl)
        assert r.success, f"Ray y=5 should pass, got {r.error}"

    def test_ray_at_edge_passes(self, industar):
        wl = industar.wavelengths[0].value
        ray = Ray(x=0, y=10.0, z=-1, k=0, l=0, m=1)
        r = trace_ray_through_system(industar, ray, wl)
        assert r.success, f"Ray y=10 should pass, got {r.error}"

    def test_ray_beyond_stop_blocked(self, industar):
        wl = industar.wavelengths[0].value
        ray = Ray(x=0, y=12.0, z=-1, k=0, l=0, m=1)
        r = trace_ray_through_system(industar, ray, wl)
        assert not r.success, "Ray y=12 should be blocked"
        assert r.error == 'STOP', f"Expected STOP, got {r.error}"


class TestIndustarFieldRays:
    """Field rays at 26° pass through system."""

    def test_axial_and_field_pass(self, industar):
        wl = industar.wavelengths[0].value
        fan = trace_fan(industar, num_rays=11, pupil_range=1.0, wl=wl, field_y=26.0)
        passed = sum(1 for r in fan if r.success)
        assert passed >= 3, f"Expected >=3 field rays to pass at 26°, got {passed}/11"

    def test_all_wavelengths_pass(self, industar):
        for w in industar.wavelengths:
            fan = trace_fan(industar, num_rays=11, pupil_range=1.0, wl=w.value, field_y=26.0)
            passed = sum(1 for r in fan if r.success)
            assert passed >= 3, f"wl={w.value}: only {passed}/11 passed at 26°"


class TestIndustarFieldAngleDirection:
    """Field angle is in Y-Z plane (l component, not k)."""

    def test_field_angle_yz_plane(self):
        angle = math.radians(26.0)
        ray = Ray(x=0, y=0, z=-1, k=0, l=math.sin(angle), m=math.cos(angle))
        dt = (0 - ray.z) / ray.m
        y_at_0 = ray.y + dt * ray.l
        assert abs(y_at_0) < 1.0, \
            f"Ray at z=0: y={y_at_0} (should be ~0 for k=0 direction)"


class TestIndustarNoCrash:
    """System traces without exceptions for all wavelengths and field angles."""

    @pytest.mark.parametrize("field", [0.0, 13.0, 26.0, -26.0])
    def test_no_crash_all_fields(self, field, industar):
        for w in industar.wavelengths:
            # Should not raise
            trace_fan(industar, num_rays=5, pupil_range=1.0, wl=w.value, field_y=field)


# =========================================================================== #
# C. BATCH TESTS — ALL LIBRARIES
# =========================================================================== #

class TestAllSystemsLoadAndTrace:
    """Every system in every library loads and traces without exceptions."""

    def test_all_systems_success_rate(self):
        libs = _get_all_libraries()
        assert len(libs) > 0, "No .LBO libraries found"

        total = 0
        passed = 0
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
                    errors.append(f"{lib_name}[{i}] {sys_raw.get('name', '?')}: DECODE FAIL: {e}")
                    continue

                try:
                    parax = paraxial_trace(sys_obj)
                    assert not math.isnan(parax.get('focal_length', float('nan')))
                except Exception as e:
                    errors.append(f"{lib_name}[{i}] {sys_obj.name}: PARAXIAL FAIL: {e}")
                    continue

                try:
                    wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
                    trace_fan(sys_obj, num_rays=3, pupil_range=1.0, wl=wl, field_y=0.0)
                except Exception as e:
                    errors.append(f"{lib_name}[{i}] {sys_obj.name}: TRACE FAIL: {e}")
                    continue

                passed += 1

        success_rate = passed / total if total > 0 else 0
        if errors:
            for e in errors[:20]:
                print(f"  {e}")

        assert success_rate >= 0.8, \
            f"Success rate {success_rate:.1%} < 80% ({passed}/{total})"


class TestAllSystemsFieldRays:
    """All systems with field angles trace without exceptions at their field."""

    def test_no_crashes_during_field_tracing(self):
        libs = _get_all_libraries()
        total = 0
        crashed = 0
        errors = []

        for lib_path in libs:
            lib_name = os.path.basename(lib_path)
            try:
                systems = load_lbo_fast(lib_path)
            except Exception:
                continue

            for i, sys_raw in enumerate(systems):
                try:
                    sys_obj = decode_lbo_opj(sys_raw['opj_data'])
                except Exception:
                    continue

                if not sys_obj.wavelengths or not sys_obj.surfaces:
                    continue

                total += 1
                wl = sys_obj.wavelengths[0].value

                field = 0.0
                if sys_obj.field_points:
                    field = max(abs(fp.y) for fp in sys_obj.field_points)

                try:
                    trace_fan(sys_obj, num_rays=5, pupil_range=1.0, wl=wl, field_y=field)
                except Exception as e:
                    crashed += 1
                    errors.append(f"{lib_name}[{i}] {sys_obj.name}: FIELD TRACE CRASH: {e}")

        if errors:
            for e in errors[:15]:
                print(f"  {e}")

        assert crashed == 0, f"{crashed} systems crashed during field ray tracing"


# =========================================================================== #
# D. EDGE CASES
# =========================================================================== #

class TestMirrorSystems:
    """Mirror (catadioptric) systems trace correctly."""

    def test_mirror_systems_no_crash(self):
        libs = _get_all_libraries()
        mirror_tested = 0
        for lib_path in libs:
            try:
                systems = load_lbo_fast(lib_path)
            except Exception:
                continue
            for sys_raw in systems:
                try:
                    sys_obj = decode_lbo_opj(sys_raw['opj_data'])
                except Exception:
                    continue
                has_mirror = any(s.is_reflective for s in sys_obj.surfaces)
                if not has_mirror:
                    continue
                wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
                trace_fan(sys_obj, num_rays=3, pupil_range=0.5, wl=wl, field_y=0.0)
                mirror_tested += 1

        if mirror_tested > 0:
            print(f"  ✓ {mirror_tested} mirror systems traced without crash")
        else:
            print("  (no mirror systems found to test)")


class TestAfocalSystems:
    """Afocal systems (binoculars, telescopes) trace without crash."""

    def test_binoc_systems_no_crash(self):
        libs = _get_all_libraries()
        afocal_tested = 0
        for lib_path in libs:
            lib_name = os.path.basename(lib_path)
            if 'BINOC' not in lib_name.upper():
                continue
            try:
                systems = load_lbo_fast(lib_path)
            except Exception:
                continue
            for sys_raw in systems:
                try:
                    sys_obj = decode_lbo_opj(sys_raw['opj_data'])
                except Exception:
                    continue
                wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
                trace_fan(sys_obj, num_rays=5, pupil_range=1.0, wl=wl, field_y=0.0)
                afocal_tested += 1

        if afocal_tested > 0:
            print(f"  ✓ {afocal_tested} afocal (BINOCUL) systems traced")
        else:
            print("  (no afocal systems found)")


class TestMicrolenSystems:
    """Microscope objectives (MICROLEN) trace correctly."""

    def test_microlen_no_crash(self):
        lib_path = os.path.join(_LIB_DIR, "MICROLEN.LBO")
        if not os.path.exists(lib_path):
            pytest.skip("MICROLEN.LBO not found")

        systems = load_lbo_fast(lib_path)
        tested = 0
        for sys_raw in systems:
            sys_obj = decode_lbo_opj(sys_raw['opj_data'])
            wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
            trace_fan(sys_obj, num_rays=5, pupil_range=0.5, wl=wl, field_y=0.0)
            tested += 1

        assert tested > 0, "No MICROLEN systems tested"


# =========================================================================== #
# E. TILT / DECENTER (COORDINATE BREAKS)
# =========================================================================== #

class TestTiltDecenter:
    """Tests for surface tilt/decenter (coordinate break support)."""

    def test_no_tilt_no_change(self):
        """Surface with zero tilt/decenter behaves identically to before."""
        from domain.models import OpticalSystem, Surface, ObjectType, Wavelength, FieldPoint, ApertureType

        # Simple thin lens
        sys = OpticalSystem(
            name="Test lens",
            object_type=ObjectType.INFINITE,
            object_height=5.0,
        )
        sys.wavelengths = [Wavelength(0.54607, 1.0, "e")]
        sys.field_points = [FieldPoint(0.0)]
        sys.aperture_type = ApertureType.ENTRANCE_PUPIL
        sys.aperture_value = 20.0
        sys.surfaces = [
            Surface(radius=50.0, thickness=5.0, glass="\u041a8", semi_diameter=12.0,
                    tilt_x=0.0, tilt_y=0.0, decenter_x=0.0, decenter_y=0.0),
            Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0,
                    tilt_x=0.0, tilt_y=0.0, decenter_x=0.0, decenter_y=0.0),
        ]
        sys.stop_surface = 1

        ray = Ray(x=0, y=5.0, z=-1, k=0, l=0, m=1)
        result = trace_ray_through_system(sys, ray, 0.54607)

        # Must succeed and hit both surfaces
        assert result.success, f"Ray failed: {result.error}"
        assert result.surfaces_hit == 2

        # Compare with a system that doesn't have tilt/decenter fields at all
        sys2 = OpticalSystem(
            name="Test lens no cb",
            object_type=ObjectType.INFINITE,
            object_height=5.0,
        )
        sys2.wavelengths = [Wavelength(0.54607, 1.0, "e")]
        sys2.field_points = [FieldPoint(0.0)]
        sys2.aperture_type = ApertureType.ENTRANCE_PUPIL
        sys2.aperture_value = 20.0
        sys2.surfaces = [
            Surface(radius=50.0, thickness=5.0, glass="\u041a8", semi_diameter=12.0),
            Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0),
        ]
        sys2.stop_surface = 1

        result2 = trace_ray_through_system(sys2, ray, 0.54607)
        assert result2.success

        # Path must be identical
        assert len(result.path) == len(result2.path), \
            f"Path lengths differ: {len(result.path)} vs {len(result2.path)}"
        for p1, p2 in zip(result.path, result2.path):
            assert p1[0] == pytest.approx(p2[0], abs=1e-10), f"x mismatch: {p1[0]} vs {p2[0]}"
            assert p1[1] == pytest.approx(p2[1], abs=1e-10), f"y mismatch: {p1[1]} vs {p2[1]}"
            assert p1[2] == pytest.approx(p2[2], abs=1e-10), f"z mismatch: {p1[2]} vs {p2[2]}"

    def test_decenter_shifts_image(self):
        """A decentered lens shifts the image position laterally."""
        from domain.models import OpticalSystem, Surface, ObjectType, Wavelength, FieldPoint, ApertureType

        # Reference system (no decenter)
        sys_ref = OpticalSystem(
            name="Reference",
            object_type=ObjectType.INFINITE,
        )
        sys_ref.wavelengths = [Wavelength(0.54607)]
        sys_ref.field_points = [FieldPoint(0.0)]
        sys_ref.aperture_type = ApertureType.ENTRANCE_PUPIL
        sys_ref.aperture_value = 20.0
        sys_ref.surfaces = [
            Surface(radius=50.0, thickness=5.0, glass="\u041a8", semi_diameter=12.0),
            Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0),
        ]
        sys_ref.stop_surface = 1

        # Decentered system: first surface decentered by 2mm in Y
        dec_y = 2.0
        sys_dec = OpticalSystem(
            name="Decentered",
            object_type=ObjectType.INFINITE,
        )
        sys_dec.wavelengths = [Wavelength(0.54607)]
        sys_dec.field_points = [FieldPoint(0.0)]
        sys_dec.aperture_type = ApertureType.ENTRANCE_PUPIL
        sys_dec.aperture_value = 20.0
        sys_dec.surfaces = [
            Surface(radius=50.0, thickness=5.0, glass="\u041a8", semi_diameter=12.0,
                    decenter_y=dec_y),
            Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0),
        ]
        sys_dec.stop_surface = 1

        ray = Ray(x=0, y=0.0, z=-1, k=0, l=0, m=1)
        r_ref = trace_ray_through_system(sys_ref, ray, 0.54607)
        r_dec = trace_ray_through_system(sys_dec, ray, 0.54607)

        assert r_ref.success and r_dec.success

        # The final image point should differ in Y by approximately dec_y
        # (decenter shifts the ray's effective position on the surface)
        final_ref = r_ref.path[-1]
        final_dec = r_dec.path[-1]

        # The decenter should cause a lateral shift in the image
        y_shift = abs(final_dec[1] - final_ref[1])
        assert y_shift > 0.01, \
            f"Decenter should shift image: y_shift={y_shift:.6f}, " \
            f"ref_y={final_ref[1]:.4f}, dec_y={final_dec[1]:.4f}"

    def test_tilt_rotates_image(self):
        """A tilted surface changes the ray direction and shifts the image."""
        from domain.models import OpticalSystem, Surface, ObjectType, Wavelength, FieldPoint, ApertureType

        # Reference system (no tilt)
        sys_ref = OpticalSystem(
            name="Reference",
            object_type=ObjectType.INFINITE,
        )
        sys_ref.wavelengths = [Wavelength(0.54607)]
        sys_ref.field_points = [FieldPoint(0.0)]
        sys_ref.aperture_type = ApertureType.ENTRANCE_PUPIL
        sys_ref.aperture_value = 20.0
        sys_ref.surfaces = [
            Surface(radius=50.0, thickness=5.0, glass="\u041a8", semi_diameter=12.0),
            Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0),
        ]
        sys_ref.stop_surface = 1

        # Tilted system: first surface tilted by 5 degrees around X
        tilt_angle = 5.0
        sys_tilt = OpticalSystem(
            name="Tilted",
            object_type=ObjectType.INFINITE,
        )
        sys_tilt.wavelengths = [Wavelength(0.54607)]
        sys_tilt.field_points = [FieldPoint(0.0)]
        sys_tilt.aperture_type = ApertureType.ENTRANCE_PUPIL
        sys_tilt.aperture_value = 20.0
        sys_tilt.surfaces = [
            Surface(radius=50.0, thickness=5.0, glass="\u041a8", semi_diameter=12.0,
                    tilt_x=tilt_angle),
            Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0),
        ]
        sys_tilt.stop_surface = 1

        ray = Ray(x=0, y=0.0, z=-1, k=0, l=0, m=1)
        r_ref = trace_ray_through_system(sys_ref, ray, 0.54607)
        r_tilt = trace_ray_through_system(sys_tilt, ray, 0.54607)

        assert r_ref.success, f"Reference failed: {r_ref.error}"
        assert r_tilt.success, f"Tilted trace failed: {r_tilt.error}"

        # The tilt should change where the ray ends up
        final_ref = r_ref.path[-1]
        final_tilt = r_tilt.path[-1]

        # For an on-axis ray through a tilted surface, the image should shift
        # in Y (tilt around X causes Y-shift)
        y_shift = abs(final_tilt[1] - final_ref[1])
        assert y_shift > 0.1, \
            f"Tilt should shift image in Y: y_shift={y_shift:.6f}, " \
            f"ref_y={final_ref[1]:.4f}, tilt_y={final_tilt[1]:.4f}"

    def test_tilt_and_decenter_no_crash(self):
        """System with both tilt and decenter traces without exceptions."""
        from domain.models import OpticalSystem, Surface, ObjectType, Wavelength, FieldPoint, ApertureType

        sys = OpticalSystem(
            name="Tilt+Decenter",
            object_type=ObjectType.INFINITE,
        )
        sys.wavelengths = [Wavelength(0.54607)]
        sys.field_points = [FieldPoint(0.0)]
        sys.aperture_type = ApertureType.ENTRANCE_PUPIL
        sys.aperture_value = 20.0
        sys.surfaces = [
            Surface(radius=50.0, thickness=5.0, glass="\u041a8", semi_diameter=12.0,
                    tilt_x=3.0, tilt_y=-2.0, decenter_x=1.0, decenter_y=-0.5),
            Surface(radius=-200.0, thickness=90.0, glass="", semi_diameter=12.0,
                    tilt_x=-1.0, decenter_y=0.5),
        ]
        sys.stop_surface = 1

        # Should not crash for axial rays
        for y_start in [0.0, 3.0, -3.0, 8.0, -8.0]:
            ray = Ray(x=0, y=y_start, z=-1, k=0, l=0, m=1)
            result = trace_ray_through_system(sys, ray, 0.54607)
            # It's OK if some rays fail (EDGE, TIR) but shouldn't crash
            assert isinstance(result.success, bool)
            assert isinstance(result.path, list)

    def test_coord_break_undo_roundtrip(self):
        """Apply + undo coord break returns ray to original direction."""
        from ray_tracing import _apply_coord_break, _undo_coord_break

        original = Ray(x=1.0, y=2.0, z=10.0, k=0.0, l=0.1, m=0.995)

        # Apply then undo
        tilted = _apply_coord_break(original, 10.0, -5.0, 2.0, -1.0)
        restored = _undo_coord_break(tilted, 10.0, -5.0, 2.0, -1.0)

        assert restored.x == pytest.approx(original.x, abs=1e-10)
        assert restored.y == pytest.approx(original.y, abs=1e-10)
        assert restored.z == pytest.approx(original.z, abs=1e-10)
        assert restored.k == pytest.approx(original.k, abs=1e-10)
        assert restored.l == pytest.approx(original.l, abs=1e-10)
        assert restored.m == pytest.approx(original.m, abs=1e-10)

    def test_zero_coord_break_identity(self):
        """Applying and undoing zero coord break is identity."""
        from ray_tracing import _apply_coord_break, _undo_coord_break, _has_coord_break
        from domain.models import Surface

        s = Surface()  # all defaults
        assert not _has_coord_break(s)

        original = Ray(x=3.0, y=-1.0, z=50.0, k=0.0, l=0.2, m=0.98)

        forward = _apply_coord_break(original, 0.0, 0.0, 0.0, 0.0)
        assert forward.x == pytest.approx(original.x)
        assert forward.y == pytest.approx(original.y)
        assert forward.k == pytest.approx(original.k)
        assert forward.l == pytest.approx(original.l)
        assert forward.m == pytest.approx(original.m)

        backward = _undo_coord_break(forward, 0.0, 0.0, 0.0, 0.0)
        assert backward.x == pytest.approx(original.x)
        assert backward.y == pytest.approx(original.y)
        assert backward.k == pytest.approx(original.k)
        assert backward.l == pytest.approx(original.l)
        assert backward.m == pytest.approx(original.m)


# =========================================================================== #
# Manual runner — preserves `py tests\test_ray_tracing.py` execution
# =========================================================================== #

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
