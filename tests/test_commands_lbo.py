"""R500-3: команды LBO/библиотеки/сравнения (commands/builtin/lbo_cmds.py).

Не-LBO часть (file.diff/compare/checksum, library.* без LBO-путей)
выполняется всегда; команды .lbo-данных маркируются ``requires_lbo``
(extracted/ — локальные данные, в git не входят).
"""
import pytest

from commands import CommandContext, default_registry
from tests.conftest import requires_lbo, requires_lbo_of

from domain.models import create_demo_system_by_name
from fileio.json_io import save_json


@pytest.fixture(scope="module")
def two_systems(tmp_path_factory):
    """(.json ахромат, .json петцваль) — разные системы для сравнения."""
    tmp = tmp_path_factory.mktemp("lbo_cmds")
    paths = []
    for demo in ("achromat", "petzval"):
        path = str(tmp / f"{demo}.json")
        save_json(create_demo_system_by_name(demo), path)
        paths.append(path)
    return tuple(paths)


@pytest.fixture(scope="session")
def lens_lbo():
    """Путь к LENS.LBO (локальные extracted-данные)."""
    from catalog.library import LBO_DIR
    import os
    return os.path.join(LBO_DIR, "LENS.LBO")


def run(name, args=None, ctx=None):
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


def fail(name, args, code):
    result = default_registry.execute(name, CommandContext(), args)
    assert not result.ok, f"{name}: ожидалась ошибка {code}"
    assert result.error["code"] == code, result.error


# --------------------------------------------------------------------------- #
# file.diff / file.compare.* / file.checksum — всегда доступны
# --------------------------------------------------------------------------- #

class TestFileDiff:
    def test_different_systems(self, two_systems):
        a, b = two_systems
        data = run("file.diff", {"file_a": a, "file_b": b})
        assert data["identical"] is False
        assert data["count"] > 0
        kinds = {d["field"] for d in data["differences"]}
        assert "radius" in kinds  # геометрия разная

    def test_identical_systems(self, two_systems, tmp_path):
        a, _ = two_systems
        copy = str(tmp_path / "copy.json")
        save_json(create_demo_system_by_name("achromat"), copy)
        data = run("file.diff", {"file_a": a, "file_b": copy})
        assert data["identical"] is True and data["count"] == 0

    def test_diff_missing_file(self, two_systems):
        a, _ = two_systems
        fail("file.diff", {"file_a": a, "file_b": "nope.json"},
             "io_error")


class TestFileCompare:
    def test_paraxial_rows(self, two_systems):
        a, b = two_systems
        data = run("file.compare.paraxial", {"file_a": a, "file_b": b})
        by_metric = {r["metric"]: r for r in data["rows"]}
        assert "focal_length" in by_metric
        row = by_metric["focal_length"]
        assert row["delta"] == pytest.approx(row["b"] - row["a"])

    def test_seidel_rows(self, two_systems):
        a, b = two_systems
        data = run("file.compare.seidel", {"file_a": a, "file_b": b})
        sums = {r["sum"] for r in data["rows"]}
        assert {"SI", "SII", "SIII", "SIV", "SV"} <= sums

    def test_spot_delta(self, two_systems):
        a, b = two_systems
        data = run("file.compare.spot",
                   {"file_a": a, "file_b": b, "num_rays": 20})
        assert data["a"]["rms"] >= 0 and data["b"]["rms"] >= 0
        assert data["delta_rms"] == pytest.approx(
            data["b"]["rms"] - data["a"]["rms"])


class TestChecksum:
    def test_sha256_stable(self, two_systems):
        a, _ = two_systems
        first = run("file.checksum", {"file": a})
        second = run("file.checksum", {"file": a})
        assert first["hex"] == second["hex"] and len(first["hex"]) == 64
        assert first["size_bytes"] > 0

    def test_algo_variants_length(self, two_systems):
        a, _ = two_systems
        for algo, size in (("md5", 32), ("sha1", 40), ("sha256", 64)):
            data = run("file.checksum", {"file": a, "algo": algo})
            assert len(data["hex"]) == size

    def test_missing_file(self):
        fail("file.checksum", {"file": "no-such-file.opj"}, "io_error")


# --------------------------------------------------------------------------- #
# library.* — без LBO-данных (генераторы всегда есть)
# --------------------------------------------------------------------------- #

class TestLibrary:
    def test_summary_and_categories(self):
        summary = run("library.summary")
        cats = {c["name"] for c in summary["categories"]}
        assert "Ахроматические дублеты" in cats
        assert summary["total"] == sum(c["count"]
                                       for c in summary["categories"])
        data = run("library.categories")
        assert {c["name"] for c in data["categories"]} == cats

    def test_entries_known_category(self):
        data = run("library.entries", {"category": "Ахроматические дублеты"})
        assert data["count"] == 2
        assert all(e.get("generator") for e in data["entries"])

    def test_entries_unknown_category(self):
        fail("library.entries", {"category": "нет такой"}, "not_found")

    def test_search_and_generators(self):
        data = run("library.search", {"query": "Дублет"})
        assert data["total"] >= 2
        gens = run("library.generators")
        assert gens["count"] >= 2
        assert all("generator" in g for g in gens["generators"])

    def test_dirs_reports_counts(self):
        data = run("library.dirs")
        assert data["lbo_count"] >= 0 and data["opj_count"] >= 0
        assert isinstance(data["lbo_exists"], bool)

    def test_load_generator_into_ctx(self):
        ctx = CommandContext()
        data = run("library.load",
                   {"name": "achromat_100", "as_name": "lib"}, ctx=ctx)
        assert data["name"] == "lib"
        assert data["system"]["num_surfaces"] >= 2
        assert ctx.get_system("lib") is not None

    def test_load_unknown(self):
        fail("library.load", {"name": "нет-такой-записи"}, "not_found")


# --------------------------------------------------------------------------- #
# file.lbo.* + library.batch — только при локальных extracted-данных
# --------------------------------------------------------------------------- #

@requires_lbo_of("LENS", "LENS_SPC")
class TestLboFiles:
    def test_info(self, lens_lbo):
        data = run("file.lbo.info", {"file": lens_lbo})
        assert data["num_systems"] == 116 and data["size"] > 0

    def test_list_and_count(self, lens_lbo):
        listed = run("file.lbo.list", {"file": lens_lbo, "limit": 5})
        assert listed["count"] == 116 and len(listed["entries"]) == 5
        assert listed["entries"][0]["index"] == 0
        counted = run("file.lbo.count", {"file": lens_lbo})
        assert counted["count"] == 116 and counted["ok"] == counted["count"]

    def test_get_first_entry(self, lens_lbo):
        data = run("file.lbo.get", {"file": lens_lbo, "index": 0})
        assert data["system"]["num_surfaces"] > 0
        assert data["entry"]["filename"].upper().endswith(".OPJ")

    def test_search(self, lens_lbo):
        data = run("file.lbo.search", {"file": lens_lbo, "query": "ST01"})
        assert data["total"] >= 1

    def test_save_entry_roundtrip(self, lens_lbo, tmp_path):
        out = str(tmp_path / "entry.json")
        data = run("file.lbo.save",
                   {"file": lens_lbo, "index": 0, "out": out})
        assert data["format"] == "json"
        from fileio.json_io import load_json
        assert load_json(out).num_surfaces > 0

    def test_save_all(self, lens_lbo, tmp_path):
        lib_dir = str(tmp_path / "lib")
        data = run("file.lbo.save_all",
                   {"file": lens_lbo.replace("LENS", "LENS_SPC"),
                    "dir": lib_dir})
        assert data["saved"] + data["broken"] >= 5

    def test_scan_dir(self, lens_lbo):
        import os
        data = run("file.lbo.scan", {"dir": os.path.dirname(lens_lbo)})
        assert data["count"] >= 10
        assert all("num_systems" in lib for lib in data["libraries"])

    def test_scan_missing_dir(self):
        fail("file.lbo.scan", {"dir": "Z:/no-such-dir"}, "io_error")

    def test_get_bad_index(self, lens_lbo):
        fail("file.lbo.get", {"file": lens_lbo, "index": 999},
             "not_found")


@requires_lbo
class TestLibraryBatch:
    def test_paraxial_metric(self, lens_lbo):
        data = run("library.batch",
                   {"file": lens_lbo, "metric": "paraxial", "limit": 5})
        assert 1 <= data["count"] <= 5
        for row in data["rows"]:
            if row["ok"]:
                assert row["efl"] != 0

    def test_surfaces_and_filter(self, lens_lbo):
        data = run("library.batch",
                   {"file": lens_lbo, "metric": "surfaces",
                    "filter": "ST01FA0", "limit": 10})
        assert data["count"] >= 1
        assert all("ST01FA0" in r["name"] for r in data["rows"])
        assert all(r["num_surfaces"] >= 1 for r in data["rows"] if r["ok"])

    def test_seidel_and_spot(self, lens_lbo):
        seidel = run("library.batch",
                     {"file": lens_lbo, "metric": "seidel", "limit": 3})
        assert all("SI" in r for r in seidel["rows"] if r["ok"])
        spot = run("library.batch",
                   {"file": lens_lbo, "metric": "spot_rms", "limit": 2})
        assert all(r["rms"] >= 0 for r in spot["rows"] if r["ok"])

    def test_no_matches(self, lens_lbo):
        fail("library.batch",
             {"file": lens_lbo, "filter": "НЕТ_ТАКОЙ_ЗАПИСИ"},
             "not_found")
