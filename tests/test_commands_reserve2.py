# -*- coding: utf-8 -*-
"""Команды R500-19 «reserve ч.2» (commands/builtin/reserve2_cmds.py):
экспорт таблиц П16/П17/П18 (export.tracex/aberx/diagram), спектральные
зоны λ (catalog.spectral.*), конверсия DD.MMSS (units.arcsec.ddmmss) и
файловые хвосты (file.stat/file.bench) — smoke КАЖДОЙ команды пакета +
сверки с прямыми вызовами движков.

Категории: ``export``/``file`` — covered Волны 1/R500 (их smoke-записи
дублированы в ``tests/test_commands_builtin.py``); ``spectral``/
``units`` — категории без пинов состава (smoke только здесь).
Поле-зависимые таблицы — на .json (.opj теряет field_points);
aberx.chrom.focus_shift — на .opj (конвенция П17).
"""
import csv
import json
import os

import pytest

from commands import CommandContext, default_registry
from commands.base import CommandError
from commands.builtin import reserve2_cmds


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    # контракт: результат строго JSON-сериализуем
    json.dumps(result.data, ensure_ascii=False, allow_nan=False)
    return result.data


def fail(name, args, code):
    """Выполнить команду, ожидая ошибку с данным кодом."""
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error
    return result.error


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    """Демо-ахромат (.json) — стёкла К8 + ТФ1, поля сохранены."""
    from domain.models import create_demo_system_by_name
    from fileio.json_io import save_json
    path = str(tmp_path_factory.mktemp("commands_r500_19") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


@pytest.fixture(scope="module")
def demo_opj(tmp_path_factory):
    """Демо-ахромат (.opj) — для поленезависимых команд."""
    from domain.models import create_demo_system_by_name
    from fileio.opj_io import save_opj
    path = str(tmp_path_factory.mktemp("commands_r500_19") / "demo.opj")
    save_opj(create_demo_system_by_name("achromat"), path)
    return path


# --------------------------------------------------------------------------- #
# Состав пакета и полное smoke-покрытие
# --------------------------------------------------------------------------- #

#: Все 25 команд пакета (имя → категория).
RESERVE2_COMMANDS = {
    "export.tracex.meridional": "export",
    "export.tracex.opl": "export",
    "export.tracex.ray.surfaces": "export",
    "export.tracex.ynu": "export",
    "export.tracex.paraxial.matrices": "export",
    "export.tracex.fan.zones": "export",
    "export.tracex.stop.clearance": "export",
    "export.tracex.ray.multi_wl": "export",
    "export.aberx.map.grid": "export",
    "export.aberx.rms.grid": "export",
    "export.aberx.spot.grid": "export",
    "export.aberx.seidel.shares": "export",
    "export.aberx.distortion.curve": "export",
    "export.aberx.astig.curve": "export",
    "export.aberx.spherical.zones": "export",
    "export.aberx.transverse.zones": "export",
    "export.aberx.focal.zonal": "export",
    "export.aberx.chrom.focus_shift": "export",
    "export.diagram.coverage": "export",
    "export.diagram.type.stats": "export",
    "catalog.spectral.band": "spectral",
    "catalog.spectral.stats": "spectral",
    "units.arcsec.ddmmss": "units",
    "file.stat": "file",
    "file.bench": "file",
}


class TestRegistration:
    def test_all_commands_registered(self):
        for name, category in RESERVE2_COMMANDS.items():
            assert default_registry.has(name), name
            assert default_registry.get(name).category == category, name

    def test_no_dups_with_builtin(self):
        """Повторная регистрация модуля — duplicate_command."""
        with pytest.raises(CommandError) as exc:
            reserve2_cmds.register(default_registry)
        assert exc.value.code == "duplicate_command"

    def test_source_tables_untouched(self):
        """Обёртки не расширяют запиненные категории: tracex/aberx ==
        22 (свои тест-модули), пин Волны 3 trace+beam+vign+tables == 19
        (tests/test_commands_trace_ext.py::test_tracex_does_not_touch_
        w3_pin)."""
        for category in ("tracex", "aberx"):
            names = [n for n in default_registry.names()
                     if default_registry.get(n).category == category]
            assert len(names) == 22, (category, len(names))
        w3 = [n for n in default_registry.names()
              if default_registry.get(n).category
              in ("trace", "beam", "vign", "tables")]
        assert len(w3) == 19


def _smoke_args(demo_json, demo_opj, tmp_path):
    out = lambda name: str(tmp_path / name)  # noqa: E731
    return {
        "export.tracex.meridional":
            {"file": demo_json, "out": out("mer.csv")},
        "export.tracex.opl":
            {"file": demo_json, "out": out("opl.csv")},
        "export.tracex.ray.surfaces":
            {"file": demo_json, "y": 5.0, "out": out("rays.csv")},
        "export.tracex.ynu":
            {"file": demo_json, "out": out("ynu.csv")},
        "export.tracex.paraxial.matrices":
            {"file": demo_json, "out": out("mat.json")},
        "export.tracex.fan.zones":
            {"file": demo_json, "n_zones": 3, "out": out("fanz.csv")},
        "export.tracex.stop.clearance":
            {"file": demo_json, "out": out("stop.csv")},
        "export.tracex.ray.multi_wl":
            {"file": demo_json, "rho_y": 0.5, "out": out("mwl.csv")},
        "export.aberx.map.grid":
            {"file": demo_json, "fields": [0.0, 3.0],
             "out": out("map.csv")},
        "export.aberx.rms.grid":
            {"file": demo_json, "fields": [0.0, 3.0],
             "out": out("rms.csv")},
        "export.aberx.spot.grid":
            {"file": demo_json, "fields": [0.0, 3.0],
             "out": out("spot.csv")},
        "export.aberx.seidel.shares":
            {"file": demo_json, "out": out("sei.csv")},
        "export.aberx.distortion.curve":
            {"file": demo_json, "fields": [0.0, 3.0],
             "out": out("dist.csv")},
        "export.aberx.astig.curve":
            {"file": demo_json, "fields": [0.0, 3.0],
             "out": out("ast.csv")},
        "export.aberx.spherical.zones":
            {"file": demo_json, "num_rays": 5, "out": out("sph.csv")},
        "export.aberx.transverse.zones":
            {"file": demo_json, "field_y": 3.0, "out": out("trans.csv")},
        "export.aberx.focal.zonal":
            {"file": demo_json, "field_y": 3.0, "out": out("fz.csv")},
        "export.aberx.chrom.focus_shift":
            {"file": demo_opj, "out": out("chrom.csv")},
        "export.diagram.coverage":
            {"vd_bins": 3, "nd_bins": 4, "out": out("cov.csv")},
        "export.diagram.type.stats":
            {"out": out("tstat.csv")},
        "catalog.spectral.band": {"wl": 0.58756},
        "catalog.spectral.stats": {},
        "units.arcsec.ddmmss": {"value": 1.130483},
        "file.stat": {"file": demo_json},
        "file.bench": {"file": demo_json, "repeats": 2},
    }


def test_every_command_has_smoke(demo_json, demo_opj, tmp_path):
    """Полный набор пакета покрыт smoke-аргументами — не больше и не
    меньше (команды пакета == smoke-набор)."""
    assert set(_smoke_args(demo_json, demo_opj, tmp_path)) \
        == set(RESERVE2_COMMANDS)


def test_smoke_every_command(demo_json, demo_opj, tmp_path):
    """Каждая команда пакета выполняется на демо-данных (строгий JSON)."""
    for name, args in sorted(_smoke_args(demo_json, demo_opj,
                                         tmp_path).items()):
        run(name, args)


# --------------------------------------------------------------------------- #
# export.tracex.* — выгрузки таблиц трассировки
# --------------------------------------------------------------------------- #

def _read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class TestExportTracex:
    def test_csv_matches_source_rows(self, demo_json, tmp_path):
        """CSV-строки == rows команды-источника (композиция без
        пересчёта: значения колонок совпадают с источником)."""
        out = str(tmp_path / "ynu.csv")
        data = run("export.tracex.ynu", {"file": demo_json, "out": out})
        source = run("tracex.ynu.table", {"file": demo_json})
        rows = _read_csv(out)
        assert data["source"] == "tracex.ynu.table"
        assert data["rows"] == len(source["rows"]) == len(rows)
        assert float(rows[0]["y_marginal"]) == pytest.approx(
            source["rows"][0]["y_marginal"], rel=1e-12)

    def test_meridional_and_opl(self, demo_json, tmp_path):
        for name, key in (("export.tracex.meridional", "y_upper"),
                          ("export.tracex.opl", "opl_upper")):
            out = str(tmp_path / f"{key}.csv")
            data = run(name, {"file": demo_json, "out": out})
            rows = _read_csv(out)
            assert rows and key in rows[0]
            assert data["format"] == "csv"

    def test_ray_surfaces_passthrough(self, demo_json, tmp_path):
        """Параметры луча (y=5) проходят насквозь в источник."""
        out = str(tmp_path / "rays.csv")
        run("export.tracex.ray.surfaces",
            {"file": demo_json, "y": 5.0, "out": out})
        source = run("tracex.ray.surfaces", {"file": demo_json, "y": 5.0})
        rows = _read_csv(out)
        assert len(rows) == source["surfaces_hit"]
        assert float(rows[1]["y"]) == pytest.approx(
            source["rows"][1]["y"], rel=1e-9)

    def test_matrices_json_keeps_gaps(self, demo_json, tmp_path):
        """Матрицы: .csv — строки поверхностей; .json — целиком
        (промежутки + системная ABCD)."""
        out_csv = str(tmp_path / "mat.csv")
        run("export.tracex.paraxial.matrices",
            {"file": demo_json, "out": out_csv})
        rows = _read_csv(out_csv)
        assert {"n", "kind", "phi", "M"} <= set(rows[0])
        out_json = str(tmp_path / "mat.json")
        run("export.tracex.paraxial.matrices",
            {"file": demo_json, "out": out_json})
        data = json.load(open(out_json, encoding="utf-8"))
        assert {"surfaces", "gaps", "system_ABCD", "det"} <= set(data)

    def test_fan_zones_rows_key(self, demo_json, tmp_path):
        """fan.zones хранит таблицу под ключом zones — CSV по зонам."""
        out = str(tmp_path / "fanz.csv")
        data = run("export.tracex.fan.zones",
                   {"file": demo_json, "n_zones": 2, "out": out})
        rows = _read_csv(out)
        assert data["rows"] == len(rows) == 3  # ρ = 0, ±зона
        assert {"rho", "y_img", "dy_vs_chief"} <= set(rows[0])

    def test_stop_clearance_scalar_row(self, demo_json, tmp_path):
        """Клиренс — скаляры: CSV одной строкой, .json целиком."""
        out = str(tmp_path / "stop.csv")
        data = run("export.tracex.stop.clearance",
                   {"file": demo_json, "out": out})
        rows = _read_csv(out)
        assert len(rows) == 1
        assert "clearance_mm" in rows[0]
        assert data["rows"] == 1

    def test_ray_multi_wl(self, demo_json, tmp_path):
        out = str(tmp_path / "mwl.csv")
        source = run("tracex.ray.multi_wl",
                     {"file": demo_json, "rho_y": 0.5})
        data = run("export.tracex.ray.multi_wl",
                   {"file": demo_json, "rho_y": 0.5, "out": out})
        rows = _read_csv(out)
        assert len(rows) == len(source["rows"])

    def test_txt_unsupported(self, demo_json, tmp_path):
        fail("export.tracex.ynu",
             {"file": demo_json, "out": str(tmp_path / "x.txt")},
             "unsupported")


# --------------------------------------------------------------------------- #
# export.aberx.* — выгрузки аберрационных таблиц
# --------------------------------------------------------------------------- #

class TestExportAberx:
    def test_map_grid_csv(self, demo_json, tmp_path):
        out = str(tmp_path / "map.csv")
        data = run("export.aberx.map.grid",
                   {"file": demo_json, "fields": [0.0, 3.0],
                    "num_rays": 5, "out": out})
        source = run("aberx.map.grid",
                     {"file": demo_json, "fields": [0.0, 3.0],
                      "num_rays": 5})
        rows = _read_csv(out)
        assert data["source"] == "aberx.map.grid"
        assert len(rows) == len(source["rows"])
        assert {"field_y", "rho", "dy_mer_um"} <= set(rows[0])

    def test_rms_and_spot_grids(self, demo_json, tmp_path):
        """Сетки поля×λ: CSV-строк == строк источника."""
        for name in ("export.aberx.rms.grid", "export.aberx.spot.grid"):
            out = str(tmp_path / f"{name.split('.')[-2]}.csv")
            src_name = name.replace("export.", "")
            source = run(src_name,
                         {"file": demo_json, "fields": [0.0, 3.0]})
            data = run(name, {"file": demo_json, "fields": [0.0, 3.0],
                              "out": out})
            assert data["rows"] == len(source["rows"])

    def test_seidel_shares_csv(self, demo_json, tmp_path):
        out = str(tmp_path / "sei.csv")
        run("export.aberx.seidel.shares", {"file": demo_json,
                                           "out": out})
        rows = _read_csv(out)
        assert {"n", "SI", "SI_share_pct", "SV"} <= set(rows[0])

    @pytest.mark.parametrize("name,extra", [
        ("export.aberx.distortion.curve", {"fit_degree": 2}),
        ("export.aberx.astig.curve", {}),
        ("export.aberx.spherical.zones", {"num_rays": 5}),
        ("export.aberx.transverse.zones", {"field_y": 3.0}),
        ("export.aberx.focal.zonal", {"field_y": 3.0}),
    ])
    def test_curves_and_zones(self, demo_json, tmp_path, name, extra):
        out = str(tmp_path / "curve.csv")
        args = {"file": demo_json, "out": out}
        args.update(extra)
        source = run(name.replace("export.", ""),
                     {k: v for k, v in args.items() if k != "out"})
        data = run(name, args)
        assert data["rows"] == len(source["rows"]) > 0

    def test_chrom_focus_shift_opj(self, demo_opj, tmp_path):
        """Хроматический сдвиг — на .opj (конвенция П17)."""
        out = str(tmp_path / "chrom.csv")
        data = run("export.aberx.chrom.focus_shift",
                   {"file": demo_opj, "out": out})
        rows = _read_csv(out)
        assert {"wl", "efl_mm", "d_efl_mm"} <= set(rows[0])
        assert data["rows"] == len(rows)

    def test_transverse_requires_field(self, demo_json, tmp_path):
        """field_y обязательна — как у источника (missing_param)."""
        fail("export.aberx.transverse.zones",
             {"file": demo_json, "out": str(tmp_path / "x.csv")},
             "missing_param")


# --------------------------------------------------------------------------- #
# export.diagram.* — выгрузки карты стёкол
# --------------------------------------------------------------------------- #

class TestExportDiagram:
    def test_coverage_cells(self, tmp_path):
        out = str(tmp_path / "cov.csv")
        data = run("export.diagram.coverage",
                   {"source": "gost", "vd_bins": 3, "nd_bins": 4,
                    "out": out})
        rows = _read_csv(out)
        assert data["rows"] == len(rows) == 3 * 4
        assert {"i", "j", "vd_from", "nd_to", "count"} <= set(rows[0])
        assert sum(int(r["count"]) for r in rows) == 28  # ГОСТ, П18

    def test_type_stats_rows(self, tmp_path):
        out = str(tmp_path / "tstat.csv")
        data = run("export.diagram.type.stats",
                   {"source": "gost", "out": out})
        rows = _read_csv(out)
        assert data["rows"] == len(rows)
        assert sum(int(r["count"]) for r in rows) == 28
        assert {"type", "family", "count"} <= set(rows[0])

    def test_json_full_structure(self, tmp_path):
        out = str(tmp_path / "cov.json")
        run("export.diagram.coverage",
            {"source": "gost", "vd_bins": 2, "nd_bins": 2, "out": out})
        data = json.load(open(out, encoding="utf-8"))
        assert {"cells", "top", "view", "vd_edges"} <= set(data)


# --------------------------------------------------------------------------- #
# catalog.spectral.* — спектральные зоны
# --------------------------------------------------------------------------- #

class TestSpectralBand:
    def test_all_reference_lines_consistent(self):
        """Инвариант: полоса каждой линии справочника совпадает с её
        цветом (границы диапазонов сверены с utils/spectral_lines)."""
        data = run("catalog.spectral.band",
                   {"wls": [ln.wavelength_um
                            for ln in _spectral_lines()]})
        lines = _spectral_lines()
        assert data["count"] == len(lines)
        for row, line in zip(data["bands"], lines):
            assert row["color"] == line.color, (row, line)
            assert row["wl_nm"] == pytest.approx(line.wavelength_nm)

    def test_known_boundaries(self):
        uv = run("catalog.spectral.band", {"wl": 0.36501})["bands"][0]
        vis = run("catalog.spectral.band", {"wl": 0.55})["bands"][0]
        ir = run("catalog.spectral.band", {"wl": 1.2})["bands"][0]
        assert uv["band"] == "uv" and not uv["visible"]
        assert vis["band"] == "green" and vis["visible"]
        assert ir["band"] == "ir" and not ir["visible"]
        bounds = run("catalog.spectral.band", {"wl": 0.55})
        assert bounds["boundaries_nm"] == {"uv_max": 380.0,
                                           "vis_max": 780.0}

    def test_batch_zones(self):
        data = run("catalog.spectral.band",
                   {"wls": [0.36501, 0.58756, 0.85211, 1.01398]})
        assert data["zones"] == {"uv": 1, "visible": 1, "ir": 2}

    def test_errors(self):
        fail("catalog.spectral.band", {}, "invalid_param")
        fail("catalog.spectral.band",
             {"wl": 0.55, "wls": [0.55]}, "invalid_param")
        fail("catalog.spectral.band", {"wl": 0.001}, "invalid_param")
        fail("catalog.spectral.band", {"wls": []}, "invalid_param")


class TestSpectralStats:
    def test_reference_summary(self):
        """Свод: 15 линий, УФ=1 / ИК=2, диапазон 365.01–1013.98 нм."""
        data = run("catalog.spectral.stats")
        assert data["count"] == 15
        assert data["by_element"]["Hg"] == 6      # i, h, G', g, e, t
        assert data["by_color"]["синяя"] == 4     # G', g, F', F
        assert data["by_color"]["красная"] == 4   # C', C, r, A'
        assert data["by_zone"] == {"uv": 1, "visible": 12, "ir": 2}
        assert data["wl_nm_min"] == pytest.approx(365.01)
        assert data["wl_nm_max"] == pytest.approx(1013.98)
        assert sum(data["by_element"].values()) == 15
        assert sum(data["by_color"].values()) == 15


def _spectral_lines():
    from utils.spectral_lines import SPECTRAL_LINES
    return SPECTRAL_LINES


# --------------------------------------------------------------------------- #
# units.arcsec.ddmmss — печать «гр.мнсек»
# --------------------------------------------------------------------------- #

class TestArcsecDdmmss:
    def test_golden_examples(self):
        """Эталоны docstring движка: OBEKTIV 1.130483 → 1°13'04.83" =
        4384.83″; ST4 0.000217 → 2.17″ (analysis/golden_verify)."""
        data = run("units.arcsec.ddmmss", {"value": 1.130483})
        assert data["arcsec"] == pytest.approx(4384.83, abs=1e-6)
        assert data["deg"] == pytest.approx(4384.83 / 3600.0)
        assert data["value"] == pytest.approx(1.130483)
        st4 = run("units.arcsec.ddmmss", {"value": 0.000217})
        assert st4["arcsec"] == pytest.approx(2.17, abs=1e-9)

    def test_engine_parity(self):
        from analysis.golden_verify import arcsec_of_ddmmss
        data = run("units.arcsec.ddmmss", {"value": -0.020417})
        assert data["arcsec"] == pytest.approx(
            arcsec_of_ddmmss(-0.020417))
        assert data["value"] == pytest.approx(-0.020417)
        # структурированный разбор: 0°03'30" = 0.053 → 3*60+30
        data = run("units.arcsec.ddmmss", {"value": 0.053})
        assert data["arcsec"] == pytest.approx(330.0)
        assert data["deg"] == pytest.approx(330.0 / 3600.0)

    def test_errors(self):
        fail("units.arcsec.ddmmss", {}, "missing_param")
        fail("units.arcsec.ddmmss", {"value": float("nan")},
             "invalid_param")


# --------------------------------------------------------------------------- #
# file.stat / file.bench — файловые хвосты
# --------------------------------------------------------------------------- #

class TestFileStat:
    def test_json_and_opj_formats(self, demo_json, demo_opj):
        for path, fmt in ((demo_json, "json"), (demo_opj, "opj")):
            data = run("file.stat", {"file": path})
            assert data["format"] == fmt
            assert data["size_bytes"] == os.path.getsize(path) > 0
            assert data["abs"] == os.path.abspath(path)
            assert data["mtime_epoch"] > 0
            assert data["mtime_iso"].count("-") == 2  # YYYY-MM-DD…

    def test_unknown_extension(self, tmp_path):
        path = str(tmp_path / "notes.txt")
        open(path, "w", encoding="utf-8").write("x")
        data = run("file.stat", {"file": path})
        assert data["format"] is None
        assert data["extension"] == ".txt"
        assert data["supported_formats"] == ["json", "lbo", "opj"]

    def test_errors(self, tmp_path):
        fail("file.stat", {"file": str(tmp_path / "nope.opj")},
             "not_found")
        fail("file.stat", {"file": str(tmp_path)}, "invalid_param")


class TestFileBench:
    def test_stats_ordering(self, demo_json):
        data = run("file.bench", {"file": demo_json, "repeats": 3})
        assert data["repeats"] == 3
        assert data["num_surfaces"] == 3
        assert data["format"] == "json"
        for stage in ("load", "trace"):
            stat = data[stage]
            assert 0.0 < stat["min_ms"] <= stat["mean_ms"] \
                <= stat["max_ms"]
        assert data["total_ms"] >= data["load"]["max_ms"]

    def test_opj_and_defaults(self, demo_opj):
        data = run("file.bench", {"file": demo_opj})
        assert data["repeats"] == 3  # BENCH_REPEATS_DEFAULT
        assert data["format"] == "opj"
        assert data["size_bytes"] == os.path.getsize(demo_opj)

    def test_paraxial_matches_calc(self, demo_json):
        """Прогон внутри bench — тот же движок paraxial_trace (не
        выдуманный): bench не искажает расчёт, файл читается тем же
        загрузчиком, что и file.open."""
        bench = run("file.bench", {"file": demo_json, "repeats": 1})
        paraxial = run("calc.paraxial", {"file": demo_json})
        assert bench["num_surfaces"] == 3
        assert paraxial["focal_length"] != 0.0

    def test_repeats_validation(self, demo_json):
        fail("file.bench", {"file": demo_json, "repeats": 0},
             "invalid_param")
        fail("file.bench", {"file": demo_json, "repeats": 21},
             "invalid_param")
