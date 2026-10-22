"""Волна 4 (src=panel): gap-команды panel.*, bridge и перевязка панели.

Правила ТЗ (docs/tasks/TASK_COMMANDS_W4.md):

* реестр — изолированный экземпляр (builtin + w4_panel_cmds), регистрация
  вручную + guard ``has()`` (``commands/builtin/__init__.py`` собирает
  координатор после мержа веток);
* перевязка: живые таблицы панели строятся командами через
  ``gui.cmdbridge``, без прямых вызовов analysis/* (guard на исходник);
* каждая gap-команда — smoke + сверка обёртки с прямым вызовом analysis.
"""
import json
import os
import re
import sys
from pathlib import Path

import pytest

from commands import CommandContext
from commands.registry import Registry, default_registry
from commands.builtin import register_builtin
from commands.builtin import w4_panel_cmds

#: Команды Волны 4 (src=panel): имя → категория.
PANEL_COMMANDS = {
    "panel.spot.summary": "panel",
    "panel.psf.stats": "panel",
}

#: Команда-маркер panel.* (регистрация w4_panel_cmds уже выполнена).
_PANEL_MARK = "panel.spot.summary"

#: Путь к исходнику панели (guard перевязки: нет прямых вызовов analysis).
_PANEL_SRC = Path(__file__).resolve().parent.parent / "gui" / "analysis_panel.py"


# --------------------------------------------------------------------------- #
# Реестр: builtin + w4_panel_cmds (изолированный, без default_registry)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def registry():
    """Изолированный реестр: builtin Волны 1+3 + panel.* (без мержа)."""
    reg = Registry()
    register_builtin(reg)
    if not reg.has(_PANEL_MARK):
        w4_panel_cmds.register(reg)
    return reg


@pytest.fixture(scope="module")
def demo_json(registry, tmp_path_factory):
    """Демо-ахромат (.json), созданный командой system.new."""
    tmp = tmp_path_factory.mktemp("commands_w4_panel")
    jsn = str(tmp / "demo_achromat.json")
    ctx = CommandContext()
    res = registry.execute("system.new", ctx,
                           {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    return jsn


def run(registry, name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = registry.execute(name, ctx or CommandContext(), args or {})
    assert result.ok, f"{name}: {result.error}"
    # контракт: результат строго JSON-сериализуем
    json.dumps(result.data, ensure_ascii=False, allow_nan=False)
    return result.data


# --------------------------------------------------------------------------- #
# Регистрация
# --------------------------------------------------------------------------- #

def test_panel_commands_registered(registry):
    for name, category in PANEL_COMMANDS.items():
        assert registry.has(name), name
        cmd = registry.get(name)
        assert cmd.category == category
        assert cmd.description


def test_ensure_registered_idempotent():
    """ensure_registered не падает при повторном вызове (guard has)."""
    w4_panel_cmds.ensure_registered(default_registry)
    w4_panel_cmds.ensure_registered(default_registry)
    assert default_registry.has(_PANEL_MARK)
    assert default_registry.get("panel.psf.stats").category == "panel"


def test_ensure_registered_fresh_registry():
    reg = Registry()
    w4_panel_cmds.ensure_registered(reg)
    assert reg.has(_PANEL_MARK)
    w4_panel_cmds.ensure_registered(reg)  # повтор — no-op
    assert reg.has(_PANEL_MARK)


# --------------------------------------------------------------------------- #
# panel.spot.summary
# --------------------------------------------------------------------------- #

def test_spot_summary_smoke(registry, demo_json):
    data = run(registry, "panel.spot.summary", {"file": demo_json})
    n_wl = data["num_wavelengths"]
    assert n_wl >= 1
    rows = data["rows"]
    # по строке на каждую λ + полихроматическая (λ у демо несколько)
    assert len(rows) == n_wl + (1 if n_wl > 1 else 0)
    mono = [r for r in rows if r["kind"] == "mono"]
    poly = [r for r in rows if r["kind"] == "poly"]
    assert len(mono) == n_wl
    assert all(r["wl"] > 0 for r in mono)
    if n_wl > 1:
        assert len(poly) == 1 and poly[0]["wl"] is None
    for r in rows:
        assert r["num_points"] > 0
        assert r["rms"] >= 0.0
        assert 0.0 <= r["max_r"]  # RMS ≤ максимального радиуса
        assert r["max_r"] >= r["rms"]
        for key in ("rms_x", "rms_y", "centroid_y"):
            assert key in r


def test_spot_summary_matches_direct(registry, demo_json):
    """Обёртка не меняет числа: сверка с прямыми вызовами analysis."""
    from fileio.json_io import load_json
    from analysis.aberrations import (
        compute_polychromatic_rms,
        compute_rms_spot,
        compute_rms_spot_xy,
        compute_spot_diagram,
    )
    sys_obj = load_json(demo_json)
    data = run(registry, "panel.spot.summary",
               {"file": demo_json, "num_rays": 20})
    wl = sys_obj.wavelengths[0].value
    spots = compute_spot_diagram(sys_obj, wl=wl, num_rays=20, field_y=0.0)
    row = next(r for r in data["rows"]
               if r["kind"] == "mono" and abs(r["wl"] - wl) < 1e-12)
    assert row["num_points"] == len(spots)
    assert row["rms"] == pytest.approx(compute_rms_spot(spots))
    xy = compute_rms_spot_xy(list(spots))
    assert row["rms_x"] == pytest.approx(xy["rms_x"])
    assert row["centroid_y"] == pytest.approx(xy["centroid_y"])
    if data["num_wavelengths"] > 1:
        poly_row = next(r for r in data["rows"] if r["kind"] == "poly")
        assert poly_row["rms"] == pytest.approx(
            compute_polychromatic_rms(sys_obj, num_rays=20, field_y=0.0))


def test_spot_summary_requires_system(registry):
    result = registry.execute("panel.spot.summary", CommandContext(), {})
    assert not result.ok
    assert result.error["code"] in ("no_system", "not_found")


# --------------------------------------------------------------------------- #
# panel.psf.stats
# --------------------------------------------------------------------------- #

def test_psf_stats_smoke(registry, demo_json):
    data = run(registry, "panel.psf.stats", {"file": demo_json})
    assert data["wl"] > 0
    assert data["num_rays"] > 0
    assert data["pixel_um"] > 0.0
    assert data["max_intensity"] > 0.0
    assert data["width_mer_um"] >= 0.0
    assert data["width_sag_um"] >= 0.0
    # ширина по полумаксимуму не меньше пикселя решётки
    assert data["width_mer_um"] >= data["pixel_um"] - 1e-9


def test_psf_stats_matches_direct(registry, demo_json):
    """Метрики совпадают с формулами живой таблицы панели (до Волны 4)."""
    from fileio.json_io import load_json
    from analysis.advanced import compute_psf
    sys_obj = load_json(demo_json)
    wl = run(registry, "panel.psf.stats", {"file": demo_json})["wl"]
    psf, dx, dy = compute_psf(sys_obj, wl=wl, num_rays=64)
    data = run(registry, "panel.psf.stats",
               {"file": demo_json, "wl": wl, "num_rays": 64})
    assert data["pixel_um"] == pytest.approx(
        (dx.max() - dx.min()) / len(dx))
    assert data["max_intensity"] == pytest.approx(float(psf.max()))


# --------------------------------------------------------------------------- #
# gui.cmdbridge
# --------------------------------------------------------------------------- #

class TestBridge:
    def test_execute_is_registry_wrapper(self):
        from gui import cmdbridge
        # без системы в контексте — CommandResult с ошибкой, не исключение
        result = cmdbridge.execute("calc.seidel", CommandContext())
        assert isinstance(result.ok, bool)
        assert not result.ok
        assert result.error["code"] == "no_system"

    def test_execute_with_system(self, demo_json):
        from gui import cmdbridge
        ctx = CommandContext()
        res = cmdbridge.execute("system.load", ctx, file=demo_json)
        assert res.ok, res.error
        res = cmdbridge.execute("calc.seidel", ctx)
        assert res.ok, res.error
        assert "SI" in res.data

    def test_report_error_shows_message_box(self, monkeypatch):
        from gui import cmdbridge
        _qapp()  # живая ссылка в _APP_HOLDER (см. комментарий у _qapp)
        calls = []
        monkeypatch.setattr(
            "gui.cmdbridge.QMessageBox.warning",
            staticmethod(lambda *a, **k: calls.append(a)))
        ok_result = cmdbridge.execute("system.new", CommandContext(),
                                      demo="achromat")
        assert cmdbridge.report_error(None, ok_result) is False
        assert not calls
        bad_result = cmdbridge.execute("calc.seidel", CommandContext())
        assert cmdbridge.report_error(None, bad_result) is True
        assert len(calls) == 1
        assert "no_system" in calls[0][2]  # код команды в тексте


# --------------------------------------------------------------------------- #
# Перевязка панели: живые таблицы строятся командами
# --------------------------------------------------------------------------- #

#: Держатель QApplication: без живой ссылки sip удаляет C++-объект сразу
#: после выражения ``instance() or QApplication(...)``, и построение
#: виджетов панели падает fail-fast (0xC0000409) без приложения.
_APP_HOLDER: list = []


def _qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    if not _APP_HOLDER:
        _APP_HOLDER.append(app)
    return _APP_HOLDER[0]


@pytest.fixture(scope="module")
def demo_system(demo_json):
    """Живая система (OpticalSystem) из демо-файла."""
    from fileio.json_io import load_json
    return load_json(demo_json)


@pytest.fixture
def panel(demo_system):
    """Панель анализа с зарегистрированными panel.* (как в GUI)."""
    _qapp()
    from gui.analysis_panel import AnalysisPanel
    return AnalysisPanel()


def _first_table(panel, key):
    """Первый виджет-таблица контейнера вкладки."""
    item = panel._table_containers[key].layout().itemAt(0)
    return item.widget()


class TestPanelRewired:
    def test_chief_table_via_registry(self, panel, demo_system):
        panel._update_chief_table(demo_system)
        table = _first_table(panel, 'chief')
        assert table is not None and table.rowCount() > 0

    def test_spot_table_via_registry(self, panel, demo_system):
        panel._update_spot_table(demo_system)
        table = _first_table(panel, 'spot')
        # по строке на λ + полихроматическая
        assert table.rowCount() == len(demo_system.wavelengths) + 1
        # числовые ячейки RMS (столбец 3)
        assert float(table.item(0, 3).text()) >= 0.0

    def test_psf_table_via_registry(self, panel, demo_system):
        panel._update_psf_table(demo_system)
        table = _first_table(panel, 'psf')
        assert table.rowCount() >= 7  # λ + 6 метрик

    def test_axial_table_via_registry(self, panel, demo_system):
        panel._update_axial_table(demo_system)
        assert _first_table(panel, 'axial').rowCount() > 0

    def test_gauge_rays_table_via_registry(self, panel, demo_system):
        panel._update_gauge_rays_table(demo_system)
        container = panel._table_containers['rays']
        assert container.layout().count() == 1

    def test_zernike_global_via_registry(self, panel, demo_system):
        panel._update_zernike_global(demo_system)
        text = panel.zernike_global_text.toPlainText()
        assert 'Глобальное разложение Цернике' in text

    def test_analyze_via_registry(self, panel, demo_system):
        panel.analyze(demo_system)
        # параксиальные характеристики от calc.paraxial + Зейдель
        assert panel._parax_data.get('focal_length')
        assert panel._seidel_data.get('SI') is not None

    def test_command_failure_degrades_to_no_data(self, panel, demo_system,
                                                 monkeypatch):
        """Ошибка команды = пустые данные, не исключение (как try/except
        живого расчёта до Волны 4)."""
        from gui import cmdbridge

        def _fail(name, ctx, **kwargs):
            from commands.base import CommandError
            from commands.registry import CommandResult
            return CommandResult.failure(
                CommandError("internal_error", "тестовый сбой"))

        monkeypatch.setattr(cmdbridge, "execute", _fail)
        panel._update_chief_table(demo_system)
        assert _first_table(panel, 'chief') is not None
        panel._update_spot_table(demo_system)
        assert _first_table(panel, 'spot').rowCount() == 0


class TestPanelSourceGuard:
    """Перевязка: в панели нет прямых вызовов расчётных функций
    analysis/domain (кроме форматтера готового результата и констант)."""

    def test_no_direct_analysis_calls(self):
        src = _PANEL_SRC.read_text(encoding="utf-8")
        banned = [
            "trace_aberration_fan", "compute_spot_diagram",
            "compute_polychromatic_rms", "compute_rms_spot",
            "compute_geometric_mtf", "compute_field_aberrations",
            "compute_focus_curve", "compute_chief_ray_characteristics",
            "compute_isoplanatism", "compute_gauge_rays",
            "compute_zernike_coefficients", "compute_wavefront_map_2d",
            "compute_zernike_chromatic", "compute_global_zernike",
            "compute_psf", "compute_lsf", "compute_enc", "compute_ptf",
            "compute_esf", "compute_bar_target_mtf_table",
            "paraxial_trace", "seidel_aberrations", "compute_beam_geometry",
        ]
        for name in banned:
            assert name not in src, f"прямой вызов {name} в analysis_panel"

    def test_shim_imports_whitelisted(self):
        """Из модулей-шимов analysis — только константа и форматтер
        (рендер готового результата, не расчёт)."""
        src = _PANEL_SRC.read_text(encoding="utf-8")
        # склеить многострочные ``from X import (\\n A,\\n B)`` в одну строку
        src = re.sub(r"\([^()]*\)", lambda m: m.group(0).replace("\n", " "),
                     src)
        whitelist = {
            "aberrations": {"DEFAULT_FOCUS_STEP_MM"},
            "zernike": {"format_global_zernike_text"},
            # optics_engine (шим domain): тип системы для сигнатур/проверок
            # + константы раскладки таблиц (не расчёт)
            "optics_engine": {"OpticalSystem", "PARAXIAL_WL_ROWS",
                              "PUPIL_POSITION_KEYS", "BEAM_SEMI_MODES"},
        }
        # from <shim> import X, Y  /  from <shim> import (X, Y)
        pattern = re.compile(
            r"^\s*from\s+(aberrations|advanced_analysis|zernike|"
            r"optics_engine)\s+import\s+([^\n#]+)",
            re.MULTILINE)
        for match in pattern.finditer(src):
            shim, names = match.group(1), match.group(2)
            # убрать скобки/переносы многострочного импорта
            names = re.sub(r"[\s()]+", "", names)
            imported = {n for n in names.split(",") if n}
            allowed = whitelist.get(shim, set())
            extra = imported - allowed
            assert not extra, (
                f"из шима {shim!r} импортированы расчётные имена "
                f"{sorted(extra)} (допустимо только {sorted(allowed)})")
