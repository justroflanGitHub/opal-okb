"""R500-5: команды units/spatial (commands/builtin/units_cmds.py).

Паритеты с analysis/units.py и domain/spatial.py, раундтрипы
Г.ММСС↔градусы и мм↔диоптрии.
"""
import math

import pytest

from commands import CommandContext, default_registry


def run(name, args=None):
    result = default_registry.execute(name, CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    from domain.models import create_demo_system_by_name
    from fileio.json_io import save_json
    path = str(tmp_path_factory.mktemp("units_cmds") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


class TestUnitsAngles:
    def test_gms_roundtrip(self):
        for angle in (0.0, 1.5, 12.3456, -7.25):
            gms = run("units.grminsec", {"angle_deg": angle})["gms_value"]
            back = run("units.gms_to_deg", {"value": gms})["angle_deg"]
            assert back == pytest.approx(angle, abs=1e-9)

    def test_deg_to_gms_parity(self):
        from analysis.units import deg_to_gms, grminsec
        data = run("units.deg_to_gms", {"angle_deg": 5.25})
        assert data["gms"] == deg_to_gms(5.25)
        assert data["gms"].strip().startswith("5.1")  # 0.25°=15'
        assert run("units.grminsec",
                   {"angle_deg": 5.25})["gms_value"] == grminsec(5.25)

    def test_tg100(self):
        data = run("units.tg100", {"angle_deg": 2.0})
        assert data["tg100"] == pytest.approx(
            math.tan(math.radians(2.0)) * 100.0)

    def test_angle_convert(self):
        data = run("units.angle.convert",
                   {"value": 180.0, "from_unit": "deg", "to_unit": "rad"})
        assert data["result"] == pytest.approx(math.pi)
        data = run("units.angle.convert",
                   {"value": 30.0, "from_unit": "arcmin", "to_unit": "deg"})
        assert data["result"] == pytest.approx(0.5)

    def test_wl_convert(self):
        data = run("units.wl.convert",
                   {"value": 0.54607, "from_unit": "um", "to_unit": "nm"})
        assert data["result"] == pytest.approx(546.07)
        back = run("units.wl.convert",
                   {"value": 546.07, "from_unit": "nm", "to_unit": "um"})
        assert back["result"] == pytest.approx(0.54607)


class TestUnitsOptical:
    def test_mm_dioptres_roundtrip(self):
        dpt = run("units.mm_to_dioptres", {"mm": 100.0})
        assert dpt["dioptres"] == pytest.approx(10.0)
        back = run("units.dioptres_to_mm", {"dioptres": dpt["dioptres"]})
        assert back["mm"] == pytest.approx(100.0)

    def test_mm_zero_invalid(self):
        fail("units.mm_to_dioptres", {"mm": 0.0}, "invalid_param")
        fail("units.dioptres_to_mm", {"dioptres": 0.0}, "invalid_param")

    def test_pupil_heights(self):
        assert run("units.pupil_h_mm",
                   {"rel": 0.7, "ax_mm": 20.0})["h_mm"] == pytest.approx(14.0)
        assert run("units.pupil_h_out_mm",
                   {"rel": 1.0, "ax_out_mm": 8.0})["h_mm"] == pytest.approx(8.0)


class TestSpatialMatrices:
    def test_identity_when_no_tilt(self):
        data = run("spatial.rotation_matrix", {})
        assert data["identity"] is True and data["matrix"] is None

    def test_rotation_x_90(self):
        data = run("spatial.rotation_matrix", {"tilt_x": 90.0})
        m = data["matrix"]
        assert data["identity"] is False
        # Rx(90°): [[1,0,0],[0,cos,−sin],[0,sin,cos]]
        assert m[0] == pytest.approx(1.0)
        assert m[4] == pytest.approx(math.cos(math.radians(90)), abs=1e-9)
        assert m[5] == pytest.approx(-1.0, abs=1e-9)
        assert m[7] == pytest.approx(1.0, abs=1e-9)

    def test_rotate_vector_parity(self):
        from domain.spatial import mat_vec, rotation_matrix
        m = rotation_matrix(10.0, -5.0, 3.0)
        v = (0.1, -0.2, 0.97)
        direct = mat_vec(m, v)
        data = run("spatial.rotate_vector",
                   {"tilt_x": 10.0, "tilt_y": -5.0, "tilt_z": 3.0,
                    "v": list(v)})
        assert data["result"] == pytest.approx(list(direct))

    def test_rotate_transpose_is_inverse(self):
        args = {"tilt_x": 10.0, "tilt_y": -5.0, "v": [0.3, 0.4, 0.86]}
        forward = run("spatial.rotate_vector", dict(args, transpose=False))
        back = run("spatial.rotate_vector",
                   dict(args, v=forward["result"], transpose=True))
        assert back["result"] == pytest.approx(args["v"], abs=1e-12)

    def test_mat_vec_and_tvec(self):
        ident = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        data = run("spatial.mat_vec", {"matrix": ident, "v": [1, 2, 3]})
        assert data["result"] == [1.0, 2.0, 3.0]
        swap = [0, -1, 0, 1, 0, 0, 0, 0, 1]  # поворот на +90° вокруг Z
        data = run("spatial.mat_tvec", {"matrix": swap, "v": [1, 0, 0]})
        assert data["result"][0] == pytest.approx(0.0)
        assert data["result"][1] == pytest.approx(-1.0)

    def test_bad_shapes(self):
        fail("spatial.mat_vec", {"matrix": [1, 2], "v": [1, 2, 3]},
             "invalid_param")
        fail("spatial.rotate_vector", {"v": [1, 2]}, "invalid_param")

    def test_ray_rotate_normalized(self):
        data = run("spatial.ray_rotate",
                   {"tilt_y": 5.0, "k": 0.0, "l": 0.0, "m": 2.0})
        norm = math.sqrt(data["k"] ** 2 + data["l"] ** 2 + data["m"] ** 2)
        assert norm == pytest.approx(1.0)
        assert data["k"] == pytest.approx(math.sin(math.radians(5.0)),
                                          abs=1e-12)

    def test_ray_rotate_zero_vector(self):
        fail("spatial.ray_rotate",
             {"k": 0.0, "l": 0.0, "m": 0.0}, "invalid_param")


class TestSpatialSystem:
    def test_coord_breaks_all_false(self, demo_json):
        data = run("spatial.coord_breaks", {"file": demo_json})
        assert data["count"] == 3 and data["with_break"] == 0

    def test_coord_breaks_after_tilt(self, demo_json):
        from commands import CommandContext
        ctx = CommandContext()
        assert default_registry.execute(
            "system.load", ctx, {"file": demo_json}).ok
        assert default_registry.execute(
            "system.surface.set", ctx,
            {"index": 1, "tilt_x": 2.0}).ok
        result = default_registry.execute(
            "spatial.coord_breaks", ctx, {})
        assert result.ok
        assert result.data["with_break"] == 1

    def test_vertices_z_cumulative(self, demo_json):
        data = run("spatial.vertices", {"file": demo_json})
        zs = [v["z"] for v in data["vertices"]]
        assert zs[0] == 0.0
        assert all(zs[i + 1] > zs[i] for i in range(len(zs) - 1))
        assert data["z_image"] == pytest.approx(sum(
            s.thickness for s in _load(demo_json).surfaces))

    def test_surface_frames_identity(self, demo_json):
        data = run("spatial.surface_frames", {"file": demo_json})
        assert data["count"] == 3
        assert all(f["identity"] for f in data["frames"])


def _load(path):
    from fileio.json_io import load_json
    return load_json(path)
