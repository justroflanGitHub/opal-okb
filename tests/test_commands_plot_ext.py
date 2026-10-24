"""Команды R500-12: расширенные headless-графики ``plot.*``
(commands/builtin/plot_ext_cmds.py) — smoke КАЖДОЙ команды + сверка
чисел с прямыми вызовами движков (analysis/aberrations, analysis/
ray_tracing, analysis/zernike, analysis/seidel_check, domain/
calculations) и сестринских команд (seidel.sums, trace.grid3d,
diagram.glasses).

Реестр поднимается как builtin целиком (композиция plot.* вызывает
сестёр по имени); модуль хранит свой исчерпывающий набор, категория
``plot`` в smoke-инвариант tests/test_commands_builtin.py добавлена
этим же пакетом.
"""
import os

import matplotlib
import pytest

import commands
from commands import CommandContext, Registry
from commands.builtin import plot_ext_cmds

# --------------------------------------------------------------------------- #
# Реестр: builtin (композиция требует сестёр) + защита от ручной регистрации
# --------------------------------------------------------------------------- #

registry = Registry()
commands.register_all(registry)          # включает plot_ext_cmds (R500-12)
if not registry.has("plot.layout"):
    plot_ext_cmds.register(registry)

#: Все команды модуля (полнота smoke-покрытия).
PLOT_EXT_COMMANDS = (
    "plot.layout",
    "plot.caustic",
    "plot.vignetting",
    "plot.chromatism",
    "plot.wavefront",
    "plot.glassmap",
    "plot.seidel",
    "plot.fields",
    "plot.mtf.family",
    "plot.ee.family",
    "plot.spot.grid",
    "plot.fan.fields",
    "plot.dof",
    "plot.pupil.vign",
    "plot.psf.slice",
)

#: Рабочая λ демо-ахромата (e-линия, основная λ системы).
WL = 0.54607


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = registry.execute(name, ctx or CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.json) демо-ахромат, созданный командами system.new/save.

    Только .json: OPJ-раундтрип теряет field_points, а графики пакета
    по умолчанию берут поля системы.
    """
    tmp = tmp_path_factory.mktemp("commands_r500_plot_ext")
    jsn = str(tmp / "demo_achromat.json")
    ctx = CommandContext()
    res = registry.execute("system.new", ctx,
                           {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    return jsn


@pytest.fixture
def ctx(demo_files):
    """Контекст с загруженной демо-системой (REPL-сценарий)."""
    context = CommandContext()
    res = registry.execute("system.load", context,
                           {"file": demo_files, "name": "demo"})
    assert res.ok, res.error
    return context


def _png_ok(path: str) -> bool:
    """Файл существует, непуст и начинается с подписи PNG."""
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        return False
    with open(path, "rb") as f:
        return f.read(8) == b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------- #
# Регистрация
# --------------------------------------------------------------------------- #

class TestRegistration:
    def test_all_commands_registered(self):
        for name in PLOT_EXT_COMMANDS:
            assert registry.has(name), name
            assert registry.get(name).category == "plot"

    def test_no_dups_with_builtin(self):
        """Повторная регистрация модуля — duplicate_command (как builtin)."""
        from commands.base import CommandError
        with pytest.raises(CommandError) as exc:
            plot_ext_cmds.register(registry)
        assert exc.value.code == "duplicate_command"

    def test_every_command_has_smoke_in_this_module(self):
        """Все 15 команд модуля покрыты тестами ниже (по имени)."""
        smoke_names = {
            "plot.layout", "plot.caustic", "plot.vignetting",
            "plot.chromatism", "plot.wavefront", "plot.glassmap",
            "plot.seidel", "plot.fields", "plot.mtf.family",
            "plot.ee.family", "plot.spot.grid", "plot.fan.fields",
            "plot.dof", "plot.pupil.vign", "plot.psf.slice"}
        assert smoke_names == set(PLOT_EXT_COMMANDS)
        assert len(PLOT_EXT_COMMANDS) == 15

    def test_no_reserved_prefixes(self):
        """Новые имена не начинаются с psf/diffr/zern/mtf/strehl/focus
        (пины Волны 3, tests/test_commands_psf.py)."""
        reserved = ("psf", "diffr", "zern", "mtf", "strehl", "focus")
        for name in PLOT_EXT_COMMANDS:
            assert name.split(".")[0] == "plot", name
            assert name.split(".")[0] not in reserved, name

    def test_composition_leaves_no_probe_systems(self, ctx, tmp_path):
        """plot.seidel/plot.pupil.vign убирают служебные системы из ctx."""
        run("plot.seidel", {"output": str(tmp_path / "s.png")}, ctx=ctx)
        run("plot.pupil.vign", {"output": str(tmp_path / "p.png")}, ctx=ctx)
        assert not [n for n in ctx.systems if n.startswith("_plotx_")]

    def test_figures_closed_after_run(self, ctx, tmp_path):
        """Фигуры закрываются после сохранения (нет утечки в длинных прогонах)."""
        run("plot.spot.grid", {"num_rays": 10,
                               "output": str(tmp_path / "sg.png")}, ctx=ctx)
        run("plot.mtf.family", {"fields": [0.0, 3.0],
                                "output": str(tmp_path / "mf.png")}, ctx=ctx)
        assert matplotlib.get_backend() == "Agg"
        assert len(matplotlib.pyplot.get_fignums()) == 0


# --------------------------------------------------------------------------- #
# Схема системы и каустика
# --------------------------------------------------------------------------- #

class TestLayoutCaustic:
    def test_layout_png_and_focus(self, ctx, demo_files, tmp_path):
        from fileio.json_io import load_json
        from optics_utils import compute_z_positions
        from domain.calculations import paraxial_trace
        out = str(tmp_path / "layout.png")
        data = run("plot.layout", {"output": out, "num_rays": 7}, ctx=ctx)
        assert _png_ok(out)
        system = load_json(demo_files)
        z_pos = compute_z_positions(system)
        sfp = paraxial_trace(system)["sF_prime"]
        assert data["focal_z_mm"] == pytest.approx(z_pos[-2] + sfp,
                                                   rel=1e-9)
        assert data["num_ok"] > 0
        assert data["num_surfaces"] == 3
        assert data["fields"] == [0.0, 5.0]   # 0 + максимальное поле

    def test_layout_explicit_fields(self, ctx, tmp_path):
        out = str(tmp_path / "layout2.png")
        data = run("plot.layout", {"output": out, "fields": [0.0, 3.0],
                                   "num_rays": 5}, ctx=ctx)
        assert _png_ok(out)
        assert data["fields"] == [0.0, 3.0]

    def test_layout_mirror_system(self, tmp_path):
        """Зеркальная система: дуги зеркал не роняют схему."""
        context = CommandContext()
        assert registry.execute("system.new", context,
                                {"demo": "mirror", "name": "mir"}).ok
        out = str(tmp_path / "layout_mirror.png")
        data = run("plot.layout", {"output": out}, ctx=context)
        assert _png_ok(out)
        assert data["num_ok"] > 0

    def test_layout_empty_system_is_error(self, tmp_path):
        context = CommandContext()
        assert registry.execute("system.new", context,
                                {"demo": "empty", "name": "void"}).ok
        result = registry.execute(
            "plot.layout", context,
            {"output": str(tmp_path / "e.png")})
        assert not result.ok
        assert result.error["code"] == "bad_request"

    def test_caustic_png_and_waist(self, ctx, tmp_path):
        out = str(tmp_path / "caustic.png")
        data = run("plot.caustic", {"output": out, "num_rays": 11},
                   ctx=ctx)
        assert _png_ok(out)
        assert data["num_ok"] == 11
        # Перетяжка — внутри продлённого диапазона, у параксиального фокуса.
        assert data["waist_z_mm"] < data["paraxial_focus_mm"] + 1.0
        assert 0.0 < data["min_rms_mm"] < 1.0

    def test_caustic_bad_range(self, ctx, tmp_path):
        result = registry.execute(
            "plot.caustic", ctx,
            {"output": str(tmp_path / "c.png"), "defocus_range": 0.0})
        assert not result.ok
        assert result.error["code"] == "invalid_param"


# --------------------------------------------------------------------------- #
# Виньетирование / светораспределение / маска зрачка
# --------------------------------------------------------------------------- #

class TestVignetting:
    def test_vignetting_png_rows_match_engines(self, ctx, demo_files,
                                               tmp_path):
        from fileio.json_io import load_json
        from analysis.vignetting import (
            compute_light_distribution,
            compute_vignetting,
        )
        out = str(tmp_path / "vign.png")
        data = run("plot.vignetting", {"output": out,
                                       "fields": [0.0, 5.0]}, ctx=ctx)
        assert _png_ok(out)
        system = load_json(demo_files)
        direct = {f: compute_vignetting(system, f, wl=WL)
                  for f in (0.0, 5.0)}
        light = {row["field_y"]: row for row in
                 compute_light_distribution(system, [0.0, 5.0], wl=WL)}
        for row in data["rows"]:
            f = row["field_y"]
            assert row["vignet_up"] == pytest.approx(
                direct[f]["vignet_up"], rel=1e-9)
            assert row["light_total"] == pytest.approx(
                light[f]["light_total"], rel=1e-9)
        # Демо-ахромат не винетируется: 0 % среза, полный проход.
        assert data["max_vignet_percent"] == pytest.approx(0.0)
        assert all(r["light_total"] == pytest.approx(1.0)
                   for r in data["rows"])

    def test_vignetting_fields_from_system(self, ctx, tmp_path):
        """Без fields — поля системы (демо .json: 0/3/5)."""
        out = str(tmp_path / "vign2.png")
        data = run("plot.vignetting", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert [r["field_y"] for r in data["rows"]] == \
            pytest.approx([0.0, 3.0, 5.0])

    def test_pupil_vign_passes_all_on_demo(self, ctx, tmp_path):
        out = str(tmp_path / "pupil.png")
        data = run("plot.pupil.vign", {"output": out, "field_y": 0.0,
                                       "num_rings": 4,
                                       "num_azimuths": 12}, ctx=ctx)
        assert _png_ok(out)
        # Ахромат без виньетирования: все узлы прошли (1 + 3 кольца × 12).
        assert data["num_passed"] == 1 + 3 * 12
        assert data["num_blocked"] == 0
        assert data["pass_fraction"] == pytest.approx(1.0)

    def test_pupil_vign_matches_grid3d(self, ctx, tmp_path):
        """Маска согласована с прямой трассировкой trace.grid3d."""
        out = str(tmp_path / "pupil2.png")
        data = run("plot.pupil.vign", {"output": out, "field_y": 5.0},
                   ctx=ctx)
        assert _png_ok(out)
        direct = run("trace.grid3d", {"system": "demo", "field_y": 5.0,
                                      "num_rings": 5,
                                      "num_azimuths": 24}, ctx=ctx)
        total = sum(len(ring) for ring in direct["rings"])
        passed = sum(1 for ring in direct["rings"] for ray in ring
                     if ray["success"])
        assert data["num_passed"] + data["num_blocked"] == total
        assert data["num_passed"] == passed

    def test_pupil_vign_bad_grid(self, ctx, tmp_path):
        result = registry.execute(
            "plot.pupil.vign", ctx,
            {"output": str(tmp_path / "p.png"), "num_rings": 1})
        assert not result.ok
        assert result.error["code"] == "invalid_param"


# --------------------------------------------------------------------------- #
# Карта волнового фронта
# --------------------------------------------------------------------------- #

class TestWavefront:
    def test_wavefront_rms_parity(self, ctx, demo_files, tmp_path):
        import numpy as np
        from fileio.json_io import load_json
        from analysis.zernike import compute_wavefront_map_2d
        out = str(tmp_path / "wf.png")
        data = run("plot.wavefront", {"output": out, "field_y": 3.0,
                                      "grid_size": 32}, ctx=ctx)
        assert _png_ok(out)
        wavefront, _, mask = compute_wavefront_map_2d(
            load_json(demo_files), wl=WL, field_y=3.0, grid_size=32)
        inside = mask > 0.5
        rms_direct = float(np.sqrt(np.mean(wavefront[inside] ** 2)))
        assert data["rms_wl"] == pytest.approx(rms_direct, rel=1e-9)
        assert data["pv_wl"] >= data["rms_wl"]
        assert 0.0 < data["fill"] <= 1.0

    def test_wavefront_bad_grid(self, ctx, tmp_path):
        result = registry.execute(
            "plot.wavefront", ctx,
            {"output": str(tmp_path / "w.png"), "grid_size": 4})
        assert not result.ok
        assert result.error["code"] == "invalid_param"


# --------------------------------------------------------------------------- #
# Хроматизм / стёкла / Зейдель / поля
# --------------------------------------------------------------------------- #

class TestChromatismGlasses:
    def test_chromatism_matches_paraxial(self, ctx, demo_files, tmp_path):
        from fileio.json_io import load_json
        from domain.calculations import paraxial_trace
        out = str(tmp_path / "chrom.png")
        data = run("plot.chromatism", {"output": out, "steps": 11},
                   ctx=ctx)
        assert _png_ok(out)
        system = load_json(demo_files)
        f_primary = paraxial_trace(system, wl=WL)["focal_length"]
        assert data["fprime_primary_mm"] == pytest.approx(f_primary,
                                                          rel=1e-12)
        for wl_sys, df in data["dfprime_at_system_wl"].items():
            direct = (paraxial_trace(system, wl=float(wl_sys))
                      ["focal_length"] - f_primary)
            assert df == pytest.approx(direct, rel=1e-12)
        # Вторичный спектр ахромата: Δf′ на краях λ разного знака.
        dfs = list(data["dfprime_at_system_wl"].values())
        assert min(dfs) < 0.0 < max(dfs)

    def test_chromatism_bad_steps(self, ctx, tmp_path):
        result = registry.execute(
            "plot.chromatism", ctx,
            {"output": str(tmp_path / "c.png"), "steps": 1})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_glassmap_path_through_system_glasses(self, ctx, tmp_path):
        out = str(tmp_path / "gmap.png")
        data = run("plot.glassmap", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert data["glasses"] == ["К8", "ТФ1"]
        assert data["skipped"] == []
        assert data["num_catalog"] >= 25

    def test_glassmap_mirror_is_error(self, tmp_path):
        context = CommandContext()
        assert registry.execute("system.new", context,
                                {"demo": "mirror", "name": "mir"}).ok
        result = registry.execute(
            "plot.glassmap", context, {"output": str(tmp_path / "g.png")})
        assert not result.ok
        assert result.error["code"] == "bad_request"

    def test_seidel_bars_match_sums(self, ctx, demo_files, tmp_path):
        from fileio.json_io import load_json
        from analysis.seidel_check import seidel_sums
        out = str(tmp_path / "seidel.png")
        data = run("plot.seidel", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        direct = seidel_sums(load_json(demo_files), wl=WL)
        for key in ("SI", "SII", "SIII", "SIV", "SV"):
            assert data["sums"][key] == pytest.approx(direct[key],
                                                      rel=1e-12)
        assert data["chromatic"] == direct["chromatic"]

    def test_fields_map(self, ctx, tmp_path):
        out = str(tmp_path / "fields.png")
        data = run("plot.fields", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert data["num_fields"] == 3
        assert data["max_field"] == pytest.approx(5.0)
        assert [f["y"] for f in data["fields"]] == \
            pytest.approx([0.0, 3.0, 5.0])

    def test_fields_empty_system_is_error(self, tmp_path):
        context = CommandContext()
        assert registry.execute("system.new", context,
                                {"demo": "empty", "name": "void"}).ok
        result = registry.execute(
            "plot.fields", context, {"output": str(tmp_path / "f.png")})
        assert not result.ok
        assert result.error["code"] == "bad_request"


# --------------------------------------------------------------------------- #
# Семейства по полям: MTF / ФКЭ / пятна / веера
# --------------------------------------------------------------------------- #

class TestFieldFamilies:
    def test_mtf_family_png_and_freqs(self, ctx, tmp_path):
        out = str(tmp_path / "mtf_fam.png")
        data = run("plot.mtf.family", {"output": out,
                                       "fields": [0.0, 3.0, 5.0]},
                   ctx=ctx)
        assert _png_ok(out)
        assert data["fields"] == [0.0, 3.0, 5.0]
        assert data["cutoff_lpmm"] > 0.0
        assert data["nyquist_lpmm"] > 0.0

    def test_mtf_family_max_freq(self, ctx, tmp_path):
        out = str(tmp_path / "mtf_fam2.png")
        data = run("plot.mtf.family", {"output": out, "fields": [0.0],
                                       "max_freq": 100.0}, ctx=ctx)
        assert _png_ok(out)
        assert data["nyquist_lpmm"] > 0.0

    def test_ee_family_r80(self, ctx, tmp_path):
        out = str(tmp_path / "ee_fam.png")
        data = run("plot.ee.family", {"output": out,
                                      "fields": [0.0, 5.0]}, ctx=ctx)
        assert _png_ok(out)
        assert [r["field_y"] for r in data["rows"]] == [0.0, 5.0]
        for row in data["rows"]:
            assert 0.0 < row["r80_um"] < 500.0

    def test_spot_grid_rms_parity(self, ctx, demo_files, tmp_path):
        from fileio.json_io import load_json
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        out = str(tmp_path / "spot_grid.png")
        data = run("plot.spot.grid", {"output": out, "num_rays": 20,
                                      "fields": [0.0, 5.0]}, ctx=ctx)
        assert _png_ok(out)
        system = load_json(demo_files)
        for row in data["rows"]:
            spots = compute_spot_diagram(system, wl=WL, num_rays=20,
                                         field_y=row["field_y"])
            assert row["num_points"] == len(spots)
            assert row["rms"] == pytest.approx(compute_rms_spot(spots),
                                               rel=1e-9)

    def test_fan_fields_counts(self, ctx, tmp_path):
        out = str(tmp_path / "fan_fields.png")
        data = run("plot.fan.fields", {"output": out, "num_fan_rays": 11,
                                       "fields": [0.0, 5.0]}, ctx=ctx)
        assert _png_ok(out)
        assert data["num_fan_rays"] == 11
        assert data["num_ok"] == 22        # оба поля проходят целиком

    def test_families_no_fields_is_error(self, tmp_path):
        """Система без полей + без fields — осмысленный отказ.

        Код invalid_param — канонический поведенческий хелпер полей
        (_r500_common.fields_arg; раньше у plot.* был bad_request —
        унифицировано с sweep/quality/aberrx при дедупликации).
        """
        context = CommandContext()
        assert registry.execute("system.new", context,
                                {"demo": "empty", "name": "void"}).ok
        for name in ("plot.mtf.family", "plot.ee.family",
                     "plot.spot.grid", "plot.fan.fields"):
            result = registry.execute(name, context,
                                      {"output": str(tmp_path / "x.png")})
            assert not result.ok, name
            assert result.error["code"] == "invalid_param", name


# --------------------------------------------------------------------------- #
# Глубина фокуса и срезы ФРТ
# --------------------------------------------------------------------------- #

class TestDofPsfSlice:
    def test_dof_depth_with_loose_coc(self, ctx, tmp_path):
        out = str(tmp_path / "dof.png")
        data = run("plot.dof", {"output": out, "coc_um": 300.0,
                                "defocus_range": 1.0, "num_points": 21,
                                "num_rays": 15}, ctx=ctx)
        assert _png_ok(out)
        assert 0.0 < data["depth_mm"] < 2.0
        assert data["near_mm"] < data["far_mm"]
        assert abs(data["best_defocus_mm"]) <= 1.0

    def test_dof_zero_depth_with_tight_coc(self, ctx, tmp_path):
        """Пятно ахромата всегда больше допуска 5 мкм — зона пустая."""
        out = str(tmp_path / "dof2.png")
        data = run("plot.dof", {"output": out, "coc_um": 5.0,
                                "defocus_range": 0.5, "num_points": 11,
                                "num_rays": 12}, ctx=ctx)
        assert _png_ok(out)
        assert data["depth_mm"] == 0.0
        assert data["near_mm"] is None and data["far_mm"] is None

    def test_dof_bad_coc(self, ctx, tmp_path):
        result = registry.execute(
            "plot.dof", ctx,
            {"output": str(tmp_path / "d.png"), "coc_um": 0.0})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_psf_slice_fwhm_symmetric(self, ctx, tmp_path):
        out = str(tmp_path / "psf_slice.png")
        data = run("plot.psf.slice", {"output": out}, ctx=ctx)
        assert _png_ok(out)
        assert data["strehl"] is not None
        # Осевое поле: срезы x/y совпадают (вращательная симметрия).
        assert data["fwhm_x_um"] == pytest.approx(data["fwhm_y_um"],
                                                  rel=1e-6)
        assert data["fwhm_x_um"] > 0.0

    def test_psf_slice_defocus_widens(self, ctx, tmp_path):
        base = run("plot.psf.slice", {"output": str(tmp_path / "s0.png")},
                   ctx=ctx)
        defoc = run("plot.psf.slice",
                    {"output": str(tmp_path / "s1.png"),
                     "defocus": 2.0}, ctx=ctx)
        assert _png_ok(str(tmp_path / "s1.png"))
        assert defoc["fwhm_x_um"] > base["fwhm_x_um"]

    def test_output_required(self, ctx):
        result = registry.execute("plot.layout", ctx, {})
        assert not result.ok
        assert result.error["code"] == "missing_param"
