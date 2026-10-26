"""R500-1: команды export.* / *.export (commands/builtin/export_cmds.py).

Smoke всех команд пакета на демо-ахромате (system.new+save, как Волна 1)
+ контракты форматов: CSV парсится и колонки совпадают, JSON читается,
.txt непуст; ошибки — unknown_format/unsupported.
"""
import csv
import json
import os

import pytest

from commands import CommandContext, default_registry
from commands.exportio import EXPORT_FORMATS

#: Команды пакета: имя → аргументы сверх file/out (t — tmp-каталог).
EXPORT_CASES = {
    "export.rows": {
        "rows": [{"a": 1, "b": 2.5}, {"a": 3, "b": None}],
        "out": "{t}/rows.csv"},
    "export.data": {"data": {"k": [1, 2]}, "out": "{t}/data.json"},
    "export.text": {"text": "протокол", "out": "{t}/text.txt"},
    "export.command": {"cmd": "catalog.info", "out": "{t}/cmd.json"},
    "tables.taboc1.export": {"out": "{t}/taboc1.csv"},
    "tables.taboc2.export": {"out": "{t}/taboc2.csv"},
    "tables.tabgl.export": {"out": "{t}/tabgl.csv"},
    "tables.tabpr2.export": {"out": "{t}/tabpr2.csv"},
    "tables.tabax3.export": {"out": "{t}/tabax3.csv"},
    "tables.tabbea.export": {"out": "{t}/tabbea.csv"},
    "tables.tabeap.export": {"out": "{t}/tabeap.csv"},
    "tables.tabesb.export": {"out": "{t}/tabesb.csv"},
    "tables.field_zones.export": {"out": "{t}/zones.csv"},
    "analyze.spot.export": {"out": "{t}/spot.csv", "num_rays": 8},
    "analyze.ray_fan.export": {"out": "{t}/rayfan.csv", "num_rays": 5},
    "analyze.field_aberrations.export": {"out": "{t}/fieldab.csv"},
    "aber.fan.export": {"out": "{t}/fan.csv", "num_rays": 10},
    "aber.mtf_geo.export": {"out": "{t}/mtfgeo.csv", "num_rays": 20},
    "export.zern.coeffs": {"out": "{t}/zern.csv", "num_rays": 16},
    "export.psf.encircled": {"out": "{t}/ee.csv"},
    "export.diffr.mtf": {"out": "{t}/mtf.csv", "grid_size": 32},
    "adv.lsf.export": {"out": "{t}/lsf.csv"},
    "adv.enc.export": {"out": "{t}/enc.csv", "num_rays": 50},
    "seidel.sums.export": {"out": "{t}/sums.csv"},
    "trace.ray_bundle.export": {"out": "{t}/bundle.csv"},
    "calc.paraxial.export": {"out": "{t}/parax.json"},
    "calc.seidel.export": {"out": "{t}/seidel.json"},
}


@pytest.fixture(scope="module")
def demo_json(tmp_path_factory):
    """Демо-ахромат .json, созданный командами (system.new+save)."""
    tmp = tmp_path_factory.mktemp("export_cmds")
    jsn = str(tmp / "demo.opal.json")
    res = default_registry.execute(
        "system.new", CommandContext(),
        {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    return jsn


def run(name, args):
    result = default_registry.execute(name, CommandContext(), args)
    assert result.ok, f"{name}: {result.error}"
    return result.data


def _read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class TestExportFormats:
    """exportio: детект формата и контракты записи."""

    def test_formats_registry(self):
        assert set(EXPORT_FORMATS) == {"csv", "json", "txt"}
        assert EXPORT_FORMATS["csv"]["extensions"] == [".csv"]

    def test_rows_columns_order_and_cells(self, tmp_path):
        out = str(tmp_path / "r.csv")
        data = run("export.rows", {
            "rows": [{"a": 1, "b": [1, 2]}, {"a": None, "b": {"k": 3}}],
            "columns": ["b", "a"], "out": out})
        assert data["columns"] == ["b", "a"]
        rows = _read_csv(out)
        assert rows[0]["b"] == "[1, 2]" and rows[0]["a"] == "1"
        assert rows[1]["a"] == ""  # None → пустая ячейка

    def test_rows_json_variant(self, tmp_path):
        out = str(tmp_path / "r.json")
        run("export.rows", {"rows": [{"x": 0.5}], "out": out})
        assert json.load(open(out, encoding="utf-8")) == [{"x": 0.5}]

    def test_data_requires_json(self, tmp_path):
        result = default_registry.execute(
            "export.data", CommandContext(),
            {"data": {"a": 1}, "out": str(tmp_path / "d.csv")})
        assert not result.ok
        assert result.error["code"] == "unsupported"

    def test_rows_txt_unsupported(self, tmp_path):
        """write_rows не пишет CSV-контент в .txt молча (r500-fix)."""
        out = str(tmp_path / "r.txt")
        result = default_registry.execute(
            "export.rows", CommandContext(),
            {"rows": [{"a": 1}], "out": out})
        assert not result.ok
        assert result.error["code"] == "unsupported"
        assert not os.path.exists(out)

    def test_unknown_extension(self, tmp_path):
        result = default_registry.execute(
            "export.rows", CommandContext(),
            {"rows": [], "out": str(tmp_path / "r.xlsx")})
        assert not result.ok
        assert result.error["code"] == "unknown_format"

    def test_non_dict_rows_rejected(self, tmp_path):
        result = default_registry.execute(
            "export.rows", CommandContext(),
            {"rows": [1, 2], "out": str(tmp_path / "r.csv")})
        assert not result.ok
        assert result.error["code"] == "unsupported"

    def test_command_export_meta(self, tmp_path):
        out = str(tmp_path / "c.json")
        data = run("export.command",
                   {"cmd": "catalog.info", "out": out})
        assert data["source"] == "catalog.info"
        assert json.load(open(out, encoding="utf-8"))["glasses"]

    def test_command_export_failure_propagates(self, tmp_path):
        result = default_registry.execute(
            "export.command", CommandContext(),
            {"cmd": "nosuch.command", "out": str(tmp_path / "c.json")})
        assert not result.ok
        assert result.error["code"] == "unknown_command"


class TestTableExports:
    """Табличные экспорты: CSV читается, .txt — формат OPAL, .json — rows."""

    def test_taboc1_three_formats(self, demo_json, tmp_path):
        for ext, check in (("csv", "rows"), ("json", "rows"),
                           ("txt", "size_bytes")):
            out = str(tmp_path / f"taboc1.{ext}")
            data = run("tables.taboc1.export", {"file": demo_json,
                                                "out": out})
            assert data["format"] == ext
            if ext == "csv":
                rows = _read_csv(out)
                assert len(rows) == data["rows"] >= 4  # зоны + осевая
            elif ext == "txt":
                assert open(out, encoding="utf-8").read().strip()

    def test_all_table_commands_smoke(self, demo_json, tmp_path):
        names = [n for n in EXPORT_CASES if n.startswith("tables.")]
        assert len(names) == 9
        for name in names:
            args = {k: (v.format(t=tmp_path) if k == "out" else v)
                    for k, v in EXPORT_CASES[name].items()}
            if "file" in EXPORT_CASES[name] or name != "tables.field_zones.export":
                args.setdefault("file", demo_json)
            data = run(name, args)
            assert data["rows"] >= 1, name
            rows = _read_csv(args["out"])
            assert len(rows) == data["rows"], name

    def test_tabgl_txt_is_opal_format(self, demo_json, tmp_path):
        out = str(tmp_path / "tabgl.txt")
        run("tables.tabgl.export", {"file": demo_json, "out": out})
        text = open(out, encoding="utf-8").read()
        assert "TABGL" in text.upper() or text.strip()


class TestDataExports:
    """Экспорты расчётных данных: длина строк = длине осей кривых."""

    @pytest.mark.parametrize("name", sorted(
        n for n in EXPORT_CASES if not n.startswith(("tables.", "export."))))
    def test_smoke(self, demo_json, tmp_path, name):
        args = {k: (v.format(t=tmp_path) if k == "out" else v)
                for k, v in EXPORT_CASES[name].items()}
        args.setdefault("file", demo_json)
        data = run(name, args)
        out = args["out"]
        if out.endswith(".json"):
            assert json.load(open(out, encoding="utf-8"))
        else:
            rows = _read_csv(out)
            assert len(rows) >= 1
            if name == "analyze.ray_fan.export":
                # веер 5 лучей × (поверхности+1) точек ≥ 2 строк на луч
                assert len(rows) >= 2 * 5
            if name == "trace.ray_bundle.export":
                assert {c for c in rows[0]} >= {"rho", "phi_deg", "success"}
            if name == "export.psf.encircled":
                assert data["r50_um"] > 0 and data["r80_um"] > data["r50_um"]

    def test_curves_txt_unsupported(self, demo_json, tmp_path):
        result = default_registry.execute(
            "export.psf.encircled", CommandContext(),
            {"file": demo_json, "out": str(tmp_path / "ee.txt")})
        assert not result.ok
        assert result.error["code"] == "unsupported"

    def test_json_export_keeps_meta(self, demo_json, tmp_path):
        out = str(tmp_path / "ee.json")
        run("export.psf.encircled", {"file": demo_json, "out": out})
        data = json.load(open(out, encoding="utf-8"))
        assert {"r_um", "ee", "r50_um", "r80_um"} <= set(data)

    def test_ray_fan_rows_have_coords(self, demo_json, tmp_path):
        out = str(tmp_path / "rf.csv")
        run("analyze.ray_fan.export",
            {"file": demo_json, "num_rays": 5, "out": out})
        rows = _read_csv(out)
        assert {"pupil_y", "surface", "x", "y", "z"} <= set(rows[0])


class TestPackageContract:
    """Инварианты пакета: все команды зарегистрированы, категория одна."""

    def test_package_commands_registered(self):
        names = set(default_registry.names())
        missing = set(EXPORT_CASES) - names
        assert not missing, sorted(missing)

    def test_all_export_category(self):
        for name in EXPORT_CASES:
            assert default_registry.get(name).category == "export", name
