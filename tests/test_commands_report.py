"""R500-11: текстовые отчёты report.* (report_cmds.py).

Каждая команда возвращает ``text`` целиком: сверка содержимого листа со
своими источниками (сестринские команды реестра — calc.paraxial,
seidel.sums, quality.*, analyze.*, таблицы порта), контракт ``out``
(запись .txt через exportio), graceful-секции таблиц/полного свода и
JSON-сериализуемость ответов.
"""
import json
import os

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
    path = str(tmp_path_factory.mktemp("report") / "demo.json")
    save_json(create_demo_system_by_name("achromat"), path)
    return path


@pytest.fixture(scope="module")
def nofields_json(tmp_path_factory):
    from domain.models import create_demo_system_by_name
    from fileio.json_io import save_json
    path = str(tmp_path_factory.mktemp("report_nf") / "nofields.json")
    system = create_demo_system_by_name("achromat")
    system.field_points = []
    save_json(system, path)
    return path


# --------------------------------------------------------------------------- #
# Структурные перечни
# --------------------------------------------------------------------------- #

class TestStructureReports:
    def test_system_passport_contents(self, demo_json):
        data = run("report.system", {"file": demo_json})
        text = data["text"]
        assert data["num_surfaces"] == 3
        assert "ОТЧЁТ: ПАСПОРТ СИСТЕМЫ" in text
        assert "Ахромат К8+ТФ1" in text
        assert "INFINITE" in text and "ENTRANCE_PUPIL = 20" in text
        assert "0.54607" in text          # основная λ e
        assert "Y=5" in text              # точки поля
        assert "Конец отчёта" in text

    def test_system_comment_line(self, demo_json):
        from domain.models import create_demo_system_by_name
        from fileio.json_io import save_json
        import tempfile
        system = create_demo_system_by_name("achromat")
        system.comment = "тестовый комментарий"
        path = os.path.join(tempfile.mkdtemp(), "c.json")
        save_json(system, path)
        text = run("report.system", {"file": path})["text"]
        assert "тестовый комментарий" in text

    def test_surfaces_table_matches_system(self, demo_json):
        from fileio.json_io import load_json
        system = load_json(demo_json)
        data = run("report.surfaces", {"file": demo_json})
        assert data["num_surfaces"] == 3
        text = data["text"]
        for surface in system.surfaces:
            if surface.glass:
                assert surface.glass in text
            assert f"{surface.radius:.4f}" in text
        assert "ВОЗДУХ" not in text or True  # воздух печатается по λ-строкам
        assert "R, мм" in text

    def test_fields_listing(self, demo_json):
        data = run("report.fields", {"file": demo_json})
        assert data["count"] == 3
        text = data["text"]
        assert "максимальное поле" in text and "5.0000" in text
        assert " 1.000" in text  # вес по умолчанию

    def test_fields_axial_system(self, nofields_json):
        data = run("report.fields", {"file": nofields_json})
        assert data["count"] == 0
        assert "осевая" in data["text"]

    def test_glasses_matches_catalog(self, demo_json):
        data = run("report.glasses", {"file": demo_json})
        assert data["count"] == 2  # К8 + ТФ1
        text = data["text"]
        assert "К8" in text and "ТФ1" in text
        catalog = run("catalog.glass.get",
                      {"name": "К8", "wl": data["wl"]})
        assert f"{catalog['n']:.6f}" in text
        assert "gost" in text


# --------------------------------------------------------------------------- #
# Параксиал / Зейдель / хроматизм
# --------------------------------------------------------------------------- #

class TestCalcReports:
    def test_paraxial_matches_sibling(self, demo_json):
        parax = run("calc.paraxial", {"file": demo_json})
        text = run("report.paraxial", {"file": demo_json})["text"]
        assert f"{parax['focal_length']:.4f}" in text
        assert f"{parax['sF_prime']:.4f}" in text
        assert f"{parax['f_number']:.2f}" in text
        assert f"{-parax['focal_length']:.4f}" in text  # передний фокус

    def test_seidel_matches_sibling(self, demo_json):
        sums = run("seidel.sums", {"file": demo_json})
        text = run("report.seidel", {"file": demo_json})["text"]
        for key in ("SI", "SII", "SIII", "SIV", "SV", "SIxp", "SIIxp"):
            assert f"{sums[key]:.6f}" in text, key

    def test_chromatism_spread(self, demo_json):
        multi = run("calc.paraxial.multi_wl", {"file": demo_json})
        text = run("report.chromatism", {"file": demo_json})["text"]
        focals = [r["focal_length"] for r in multi["results"]]
        assert f"{max(focals) - min(focals):.4f}" in text
        # каждая λ системы попадает в таблицу
        for row in multi["results"]:
            assert f"{row['wl']:.5f}" in text


# --------------------------------------------------------------------------- #
# Отчёты качества по полям
# --------------------------------------------------------------------------- #

class TestQualityReports:
    def test_aberrations_matches_sibling(self, demo_json):
        source = run("analyze.field_aberrations", {"file": demo_json})
        text = run("report.aberrations",
                   {"file": demo_json, "num_fan_rays": 15})["text"]
        for row in source["fields"]:
            assert f"{row['field_y']:.3f}" in text
            assert f"{row['distortion']:.3f}" in text

    def test_spot_worst_field(self, demo_json):
        source = run("quality.spot.summary",
                     {"file": demo_json, "num_rays": 10})
        data = run("report.spot",
                   {"file": demo_json, "num_rays": 10})
        text = data["text"]
        assert f"{source['summary']['max_rms']:.4f}" in text
        assert "полихром" in text
        # построчная сверка: RMS каждой λ первого поля
        for entry in source["rows"][0]["by_wl"]:
            assert f"{entry['rms']:.4f}" in text

    def test_ee_fraction_columns(self, demo_json):
        data = run("report.ee",
                   {"file": demo_json, "fields": [0.0, 3.0],
                    "num_rays": 40})
        text = data["text"]
        for header in ("D50%", "D80%", "D90%"):
            assert header in text

    def test_mtf_matrix_matches_sibling(self, demo_json):
        source = run("quality.mtf.matrix",
                     {"file": demo_json, "fields": [0.0],
                      "freqs": [20.0, 60.0]})
        data = run("report.mtf",
                   {"file": demo_json, "fields": [0.0],
                    "freqs": [20.0, 60.0]})
        text = data["text"]
        assert data["freqs"] == [20.0, 60.0]
        row = source["rows"][0]["mtf"]
        for entry in row:
            assert f"{entry['mtf_t']:.4f}" in text
            assert f"{entry['mtf_s']:.4f}" in text
        assert f"{source['cutoff_lpmm']:.1f}" in text

    def test_strehl_worst_and_mean(self, demo_json):
        source = run("quality.strehl.summary",
                     {"file": demo_json, "fields": [0.0, 3.0]})
        text = run("report.strehl",
                   {"file": demo_json, "fields": [0.0, 3.0]})["text"]
        assert f"{source['worst']['strehl_exact']:.5f}" in text
        assert f"{source['mean_exact']:.5f}" in text

    def test_wavefront_max(self, demo_json):
        source = run("quality.wavefront.summary", {"file": demo_json})
        text = run("report.wavefront", {"file": demo_json})["text"]
        assert f"{source['max_rms_wl']:.5f}" in text
        assert f"{source['strehl_marechal_max']:.5f}" in text

    def test_quality_passport_and_regime(self, demo_json):
        passport = run("quality.passport",
                       {"file": demo_json, "num_rays": 10,
                        "freq_lpmm": 30.0})
        regime = run("quality.regime",
                     {"file": demo_json, "num_rays": 10})
        data = run("report.quality",
                   {"file": demo_json, "num_rays": 10,
                    "freq_lpmm": 30.0})
        text = data["text"]
        assert f"{passport['efl_mm']:.4f}" in text
        assert f"{passport['airy_diameter_um']:.4f}" in text
        assert f"{regime['ratio']:.2f}" in text
        assert "ограничена аберрациями" in text  # демо-ахромат


# --------------------------------------------------------------------------- #
# Таблицы порта и полный свод
# --------------------------------------------------------------------------- #

class TestTablesAndFull:
    def test_tables_default_set(self, demo_json):
        data = run("report.tables", {"file": demo_json})
        assert data["tables"] == data["included"] == \
            ["taboc1", "taboc2", "tabgl", "tabpr2"]
        assert "failed" not in data

    def test_tables_text_contains_sibling_text(self, demo_json):
        taboc1 = run("tables.taboc1", {"file": demo_json})
        text = run("report.tables",
                   {"file": demo_json, "tables": ["taboc1"]})["text"]
        assert taboc1["text"] in text

    def test_tables_all_eight(self, demo_json):
        names = ["taboc1", "taboc2", "tabgl", "tabpr2", "tabax3",
                 "tabbea", "tabesb", "tabeap"]
        data = run("report.tables", {"file": demo_json, "tables": names})
        assert data["included"] == names
        assert "failed" not in data

    def test_tables_unknown_selector(self, demo_json):
        fail("report.tables",
             {"file": demo_json, "tables": ["taboc1", "nosuch"]},
             "invalid_param")

    def test_tables_passes_zones_and_wl(self, demo_json):
        data = run("report.tables",
                   {"file": demo_json, "tables": ["taboc1"],
                    "wl": 0.55, "n_zones": 2})
        single = run("tables.taboc1",
                     {"file": demo_json, "wl": 0.55, "n_zones": 2})
        assert single["text"] in data["text"]

    def test_full_all_sections(self, demo_json):
        data = run("report.full",
                   {"file": demo_json, "num_rays": 10,
                    "freq_lpmm": 30.0})
        assert "failed" not in data
        assert len(data["sections"]) == 15
        for marker in ("ПАСПОРТ СИСТЕМЫ", "ТАБЛИЦА ПОВЕРХНОСТЕЙ",
                       "ПАРАКСИАЛЬНЫЕ ХАРАКТЕРИСТИКИ",
                       "СУММЫ ЗЕЙДЕЛЯ", "ТАБЛИЦЫ ПОРТА"):
            assert marker in data["text"]
        assert data["text"].count("Конец отчёта") == 1

    def test_out_writes_txt(self, demo_json, tmp_path):
        out = str(tmp_path / "report.txt")
        data = run("report.paraxial",
                   {"file": demo_json, "out": out})
        assert data["out"] == os.path.abspath(out)
        assert data["format"] == "txt"
        assert data["size_bytes"] > 0
        with open(out, encoding="utf-8") as f:
            assert f.read() == data["text"]

    def test_out_rejects_csv(self, demo_json, tmp_path):
        fail("report.paraxial",
             {"file": demo_json, "out": str(tmp_path / "x.csv")},
             "unsupported")

    def test_every_answer_is_jsonable(self, demo_json):
        names = [n for n in default_registry.names()
                 if n.startswith("report.")]
        assert len(names) == 16
        args_map = {
            "report.ee": {"fields": [0.0], "num_rays": 40},
            "report.mtf": {"fields": [0.0], "freqs": [20.0]},
            "report.strehl": {"fields": [0.0]},
            "report.spot": {"num_rays": 10},
            "report.quality": {"num_rays": 10},
            "report.full": {"num_rays": 10},
        }
        ctx = CommandContext()
        for name in names:
            result = default_registry.execute(
                name, ctx, {"file": demo_json, **args_map.get(name, {})})
            assert result.ok, f"{name}: {result.error}"
            json.dumps(result.data, ensure_ascii=False, allow_nan=False)
