"""R500-2: расширенные команды system.* (commands/builtin/system_ext_cmds.py).

Контексты REPL, скалярные поля, пересчёты апертуры (domain/aperture.py),
точечные операции с поверхностями, поля/λ, стёкла, санити-проверки.
"""
import pytest

from commands import CommandContext, default_registry


@pytest.fixture
def ctx(tmp_path):
    """Контекст с демо-ахроматом под именем 'demo'."""
    context = CommandContext()
    res = default_registry.execute(
        "system.new", context, {"demo": "achromat", "name": "demo"})
    assert res.ok, res.error
    return context


def run(name, args=None, ctx=None):
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code, ctx=None):
    result = default_registry.execute(name, ctx or CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error
    return result.error


# --------------------------------------------------------------------------- #
# Контекст REPL
# --------------------------------------------------------------------------- #

class TestContext:
    def test_list_select_drop(self, ctx):
        default_registry.execute(
            "system.new", ctx, {"demo": "mirror", "name": "mir"})
        data = run("system.list", ctx=ctx)
        assert data["count"] == 2
        assert {s["name"] for s in data["systems"]} == {"demo", "mir"}
        assert data["current"] == "mir"
        run("system.select", {"name": "demo"}, ctx=ctx)
        assert run("system.list", ctx=ctx)["current"] == "demo"
        run("system.drop", {"name": "mir"}, ctx=ctx)
        data = run("system.list", ctx=ctx)
        assert data["count"] == 1 and "mir" not in {
            s["name"] for s in data["systems"]}

    def test_drop_current_resets(self, ctx):
        run("system.drop", {"name": "demo"}, ctx=ctx)
        result = default_registry.execute(
            "system.current", ctx, {})
        assert not result.ok  # текущей больше нет

    def test_drop_missing_is_noop(self, ctx):
        data = run("system.drop", {"name": "ghost"}, ctx=ctx)
        assert data["dropped"] is False

    def test_select_unknown(self, ctx):
        fail("system.select", {"name": "ghost"}, "not_found", ctx=ctx)

    def test_clone_deep_copy(self, ctx):
        run("system.clone", {"name": "copy"}, ctx=ctx)
        # правка копии (она стала текущей) не трогает оригинал
        run("system.surface.set", {"index": 0, "radius": 33.0}, ctx=ctx)
        run("system.select", {"name": "demo"}, ctx=ctx)
        original = run("system.surfaces.list", ctx=ctx)
        assert original["surfaces"][0]["radius"] != 33.0

    def test_rename_moves_ctx_key(self, ctx):
        data = run("system.rename", {"name": "renamed"}, ctx=ctx)
        assert data["old_name"] == "demo" and data["name"] == "renamed"
        names = run("system.list", ctx=ctx)
        assert names["current"] == "renamed"
        assert "demo" not in {s["name"] for s in names["systems"]}


# --------------------------------------------------------------------------- #
# Скалярные поля
# --------------------------------------------------------------------------- #

class TestScalarFields:
    def test_name_and_comment(self, ctx):
        assert run("system.name.set", {"name": "x"}, ctx=ctx)["name"] == "x"
        assert run("system.comment.set", {"comment": "тест"},
                   ctx=ctx)["comment"] == "тест"

    def test_object_and_image(self, ctx):
        data = run("system.object.set",
                   {"object_type": "FINITE", "object_distance": 500.0,
                    "object_height": 12.0}, ctx=ctx)
        assert data["object_type"] == "FINITE"
        assert data["object_distance"] == 500.0
        assert run("system.image.set", {"image_type": "INFINITE"},
                   ctx=ctx)["image_type"] == "INFINITE"

    def test_object_set_requires_field(self, ctx):
        fail("system.object.set", {}, "invalid_param", ctx=ctx)

    def test_stop_obscuration_beam(self, ctx):
        data = run("system.stop.set",
                   {"stop_surface": 0, "stop_offset": 1.5, "stop_type": "z"},
                   ctx=ctx)
        assert data["stop_surface"] == 0
        assert data["stop_type"] == "z"
        assert run("system.obscuration.set", {"obscuration_ratio": 0.3},
                   ctx=ctx)["obscuration_ratio"] == 0.3
        data = run("system.beam.set", {"beam_mode": "given",
                                       "sharp_edge": False}, ctx=ctx)
        assert data["beam_mode"] == "given" and data["sharp_edge"] is False

    def test_stop_out_of_range(self, ctx):
        fail("system.stop.set", {"stop_surface": 99}, "invalid_param",
             ctx=ctx)

    def test_obscuration_bounds(self, ctx):
        fail("system.obscuration.set", {"obscuration_ratio": 1.5},
             "invalid_param", ctx=ctx)

    def test_aperture_set(self, ctx):
        data = run("system.aperture.set",
                   {"aperture_type": "F_NUMBER", "aperture_value": 4.0},
                   ctx=ctx)
        assert data["aperture_type"] == "F_NUMBER"
        assert data["aperture_value"] == 4.0
        fail("system.aperture.set", {"aperture_type": "F_NUMBER",
                                     "aperture_value": -1.0},
             "invalid_param", ctx=ctx)


# --------------------------------------------------------------------------- #
# Пересчёты апертуры (domain/aperture.py)
# --------------------------------------------------------------------------- #

class TestApertureConversions:
    def test_f_number_roundtrip(self, ctx):
        data = run("system.aperture.convert",
                   {"value": 5.0, "from_type": "F_NUMBER"}, ctx=ctx)
        assert data["epd"] == pytest.approx(
            run("calc.paraxial", ctx=ctx)["focal_length"] / 5.0,
            rel=1e-9)
        assert data["f_number"] == pytest.approx(5.0, rel=1e-9)

    def test_epd_of_current_system(self, ctx):
        data = run("system.aperture.epd", ctx=ctx)
        assert data["aperture_type"] == "ENTRANCE_PUPIL"
        assert data["epd"] == pytest.approx(data["aperture_value"])

    def test_from_epd_all_types(self, ctx):
        data = run("system.aperture.from_epd", {"epd": 20.0}, ctx=ctx)
        assert data["entrance_pupil"] == 20.0
        assert data["f_number"] > 0 and data["numerical_aperture"] > 0

    def test_pupil_distance_infinite_none(self, ctx):
        data = run("system.aperture.pupil_distance", ctx=ctx)
        assert data["object_type"] == "INFINITE"
        assert data["distance"] is None

    def test_epd_value_parity_with_domain(self, ctx):
        from domain.aperture import aperture_to_epd
        from domain.models import ApertureType
        from optics_utils import get_primary_wl  # noqa: F401  (демо-система)
        system = ctx.get_system("demo")
        direct = aperture_to_epd(system, 8.0, ApertureType.F_NUMBER)
        data = run("system.aperture.convert",
                   {"value": 8.0, "from_type": "F_NUMBER"}, ctx=ctx)
        assert data["epd"] == pytest.approx(direct, rel=1e-12)


# --------------------------------------------------------------------------- #
# Поверхности
# --------------------------------------------------------------------------- #

class TestSurfaces:
    def test_get_returns_full_dict(self, ctx):
        data = run("system.surface.get", {"index": 0}, ctx=ctx)
        assert data["index"] == 0 and data["radius"] > 0
        assert "aspheric_coeffs" in data

    def test_get_bad_index(self, ctx):
        fail("system.surface.get", {"index": 99}, "invalid_param", ctx=ctx)

    def test_duplicate(self, ctx):
        before = run("system.surfaces.list", ctx=ctx)["num_surfaces"]
        data = run("system.surface.duplicate", {"index": 1, "count": 2},
                   ctx=ctx)
        assert data["num_surfaces"] == before + 2
        assert data["surfaces"][1]["radius"] == data["surfaces"][2]["radius"]

    def test_move(self, ctx):
        radii = [s["radius"] for s in
                 run("system.surfaces.list", ctx=ctx)["surfaces"]]
        data = run("system.surface.move", {"index": 2, "to": 0}, ctx=ctx)
        moved = [s["radius"] for s in data["surfaces"]]
        assert moved == [radii[2], radii[0], radii[1]]

    def test_aspheric_and_n_override(self, ctx):
        data = run("system.surface.aspheric.set",
                   {"index": 0, "coeffs": [1e-6, -2e-9]}, ctx=ctx)
        assert data["surfaces"][0]["aspheric_coeffs"] == [1e-6, -2e-9]
        assert data["surfaces"][0]["surface_type"] == "ASPHERIC"
        run("system.surface.n.set",
            {"index": 0, "n_override": {"0.58756": 1.7}}, ctx=ctx)
        # n_override не входит в сериализацию поверхности — смотрим объект
        assert ctx.get_system("demo").surfaces[0].n_override == {
            0.58756: 1.7}

    def test_duplicate_bad_count(self, ctx):
        fail("system.surface.duplicate", {"index": 0, "count": 0},
             "invalid_param", ctx=ctx)


# --------------------------------------------------------------------------- #
# Поля и длины волн
# --------------------------------------------------------------------------- #

class TestFieldsAndWavelengths:
    def test_remove_and_clear_fields(self, ctx):
        before = run("system.fields.list", ctx=ctx)["num_fields"]
        assert before >= 2
        run("system.fields.remove", {"index": 1}, ctx=ctx)
        assert run("system.fields.list",
                   ctx=ctx)["num_fields"] == before - 1
        run("system.fields.clear", ctx=ctx)
        assert run("system.fields.list", ctx=ctx)["num_fields"] == 0

    def test_fields_auto(self, ctx):
        from analysis.aberrations import analysis_field_points
        data = run("system.fields.auto", {"num_fields": 4}, ctx=ctx)
        assert data["field_values"] == analysis_field_points(
            ctx.get_system("demo"), num_fields=4)
        assert len(data["field_points"]) == len(data["field_values"])
        assert data["field_points"][0]["y"] == pytest.approx(0.0)

    def test_weights(self, ctx):
        data = run("system.fields.weight.set",
                   {"index": 0, "weight": 2.5}, ctx=ctx)
        assert data["field_points"][0]["weight"] == 2.5
        data = run("system.wavelengths.weight.set",
                   {"index": 0, "weight": 0.25}, ctx=ctx)
        assert data["wavelengths"][0]["weight"] == 0.25

    def test_wavelengths_remove_clear_primary(self, ctx):
        run("system.wavelengths.remove", {"index": 2}, ctx=ctx)
        assert run("system.wavelengths.list",
                   ctx=ctx)["num_wavelengths"] == 2
        primary = run("system.wavelengths.primary", ctx=ctx)
        assert primary["value"] == pytest.approx(0.54607, abs=1e-6)
        run("system.wavelengths.clear", ctx=ctx)
        fail("system.wavelengths.primary", {}, "invalid_param", ctx=ctx)

    def test_remove_bad_index(self, ctx):
        fail("system.wavelengths.remove", {"index": 99},
             "invalid_param", ctx=ctx)


# --------------------------------------------------------------------------- #
# Стёкла и валидация
# --------------------------------------------------------------------------- #

class TestGlassesAndValidate:
    def test_glasses_list(self, ctx):
        data = run("system.glasses.list", ctx=ctx)
        names = {g["glass"] for g in data["glasses"]}
        assert names == {"К8", "ТФ1"}
        by_glass = {g["glass"]: g["surfaces"] for g in data["glasses"]}
        assert by_glass["К8"] == [0]

    def test_glasses_replace(self, ctx):
        data = run("system.glasses.replace",
                   {"old": "ТФ1", "new": "ТФ5"}, ctx=ctx)
        assert data["changed_surfaces"] == 1
        names = {g["glass"] for g in
                 run("system.glasses.list", ctx=ctx)["glasses"]}
        assert names == {"К8", "ТФ5"}

    def test_validate_ok(self, ctx):
        data = run("system.validate", ctx=ctx)
        assert data["valid"] is True
        assert data["errors"] == []
        assert data["checks"]["surfaces"] == 3

    def test_validate_reports_errors(self, ctx):
        # сломаем систему напрямую: апертура 0 + пустые λ
        system = ctx.get_system("demo")
        system.aperture_value = 0.0
        system.wavelengths.clear()
        data = run("system.validate", ctx=ctx)
        assert data["valid"] is False
        assert any("aperture_value" in e for e in data["errors"])
        assert any("длин волн" in e for e in data["errors"])

    def test_validate_unknown_glass_warning(self, ctx):
        system = ctx.get_system("demo")
        system.surfaces[0].glass = "НЕТ_ТАКОГО_СТЕКЛА"
        data = run("system.validate", ctx=ctx)
        assert data["valid"] is True  # предупреждение, не ошибка
        assert any("вне каталогов" in w for w in data["warnings"])
