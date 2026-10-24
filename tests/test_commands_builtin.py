"""Builtin-команды реестра: smoke КАЖДОЙ команды (Волна 1 + Волна 3 psf).

Демо-данные генерируются самим реестром (system.new + save) — как в
TASK_COMMANDS_W1 §5. Дополнительно — сверка calc.* с прямыми вызовами
domain (обёртка не должна менять числа). Инвариант: у каждой команды
реестра есть smoke-набор здесь (волны добавляют свои записи в карту).
"""
import os

import pytest

from tests.conftest import requires_fil
from commands import CommandContext, default_registry
from commands.base import CommandError
from domain.calculations import (
    compute_beam_geometry,
    paraxial_trace,
    seidel_aberrations,
)
from domain.models import create_demo_system
from fileio.json_io import load_json

# Волна 4 (src=main): команды регистрируются лениво (gui.cmdbridge при
# импорте main) — здесь регистрируем явно, чтобы smoke-инвариант был
# детерминирован и в изолированном прогоне модуля (guard-правило 5 ТЗ).
from commands.builtin import w4_main_cmds
if not default_registry.has("system.append"):
    w4_main_cmds.register(default_registry)


# --------------------------------------------------------------------------- #
# Фикстуры: демо-система, сгенерированная самим реестром (system.new+save)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    """(.opj, .json) демо-ахромат, созданный командами system.new/save."""
    tmp = tmp_path_factory.mktemp("commands_w1")
    opj = str(tmp / "demo_achromat.opj")
    jsn = str(tmp / "demo_achromat.json")
    ctx = CommandContext()
    res = default_registry.execute(
        "system.new", ctx,
        {"demo": "achromat", "save": jsn})
    assert res.ok, res.error
    res = default_registry.execute(
        "file.save", ctx, {"src": jsn, "file": opj})
    assert res.ok, res.error
    return opj, jsn


@pytest.fixture
def ctx(demo_files):
    """Контекст с загруженной демо-системой (REPL-сценарий)."""
    opj, _ = demo_files
    context = CommandContext()
    res = default_registry.execute(
        "system.load", context, {"file": opj, "name": "demo"})
    assert res.ok, res.error
    return context


def run(name, args=None, ctx=None):
    """Выполнить команду; fail-тест если команда не ok."""
    result = default_registry.execute(name, ctx or CommandContext(),
                                      args or {})
    assert result.ok, f"{name}: {result.error}"
    return result.data


# --------------------------------------------------------------------------- #
# Полное покрытие: каждая команда реестра имеет smoke
# --------------------------------------------------------------------------- #

#: Категории Волны 1 — этот smoke-набор покрывает только их; команды
#: более поздних волн (trace/beam/vign/tables, psf/..., ...) держат
#: собственные исчерпывающие наборы в своих тест-модулях.
W1_CATEGORIES = {"file", "system", "calc", "catalog", "analyze"}

#: Синтетические точки зрачка (px, py, W) для команд разложения Цернике:
#: 16 точек ≥ 15 членов классического базиса n≤4,
#: 28 точек ≥ 28 членов базиса OPAL (zern.fit_points).
_SMOKE_POINTS_16 = [
    [0.0, 0.0, 0.10], [0.5, 0.0, 0.20], [0.0, 0.5, -0.10],
    [0.7, 0.7, 0.05], [-0.3, 0.6, 0.02], [0.9, -0.2, -0.30],
    [0.1, -0.8, 0.15], [-0.5, -0.5, 0.0], [0.3, 0.3, 0.01],
    [-0.9, 0.1, 0.20], [0.2, 0.9, -0.05], [-0.1, -0.9, 0.30],
    [0.6, -0.6, -0.02], [-0.7, 0.4, 0.04], [0.8, 0.5, 0.03],
    [0.0, 0.3, 0.0],
]
_SMOKE_POINTS_28 = _SMOKE_POINTS_16 + [
    [0.4, -0.4, 0.0], [-0.2, 0.8, 0.10], [0.55, 0.55, 0.20],
    [0.95, 0.0, -0.10], [0.0, 0.95, 0.25], [-0.95, -0.05, 0.0],
    [0.25, -0.95, -0.20], [0.33, 0.66, 0.05], [-0.66, 0.33, -0.05],
    [0.66, -0.33, 0.10], [0.1, 0.1, 0.0], [-0.1, 0.1, 0.05],
    [0.2, -0.2, -0.05],
]


def _smoke_args(demo_files):
    opj, jsn = demo_files
    return {
        "file.convert": {"src": opj, "dst": opj + ".converted.json"},
        "file.export.protocol": {"file": opj, "out": opj + ".protocol.txt"},
        "file.info": {"file": opj},
        "file.open": {"file": opj},
        "file.save": {"src": opj, "file": opj + ".saved.opj"},
        "file.formats": {},
        # R500-3: сравнение файлов + контрольная сумма
        "file.diff": {"file_a": opj, "file_b": jsn},
        "file.compare.paraxial": {"file_a": opj, "file_b": jsn},
        "file.compare.seidel": {"file_a": opj, "file_b": jsn},
        "file.compare.spot": {"file_a": opj, "file_b": jsn,
                              "num_rays": 10},
        "file.checksum": {"file": opj},
        "system.current": {"__ctx__": True},
        "system.achromat": {"focal_length": 100.0},
        "system.append": {"file": opj, "append": jsn},
        "system.fields.add": {"file": opj, "y": 7.0},
        "system.fields.list": {"file": opj},
        "system.fields.set": {"file": opj,
                              "fields": [{"y": 0.0}, {"y": 5.0, "x": 1.0,
                                                      "weight": 0.5}]},
        "system.info": {"file": opj},
        "system.load": {"file": opj},
        "system.new": {},
        "system.radii.changes": {"file": opj},
        "system.radii.standardize": {"file": opj},
        "system.reverse": {"file": opj},
        "system.scale": {"file": opj, "factor": 2.0},
        "system.surface.add": {"file": opj, "radius": -60.0},
        "system.surface.remove": {"file": opj, "index": 2},
        "system.surface.set": {"file": opj, "index": 0, "radius": 55.0},
        "system.surfaces.list": {"file": opj},
        "system.wavelengths.add": {"file": opj, "value": 0.48613},
        "system.wavelengths.list": {"file": opj},
        "system.wavelengths.set": {"file": opj,
                                   "wavelengths": [{"value": 0.58756,
                                                    "name": "d"}]},
        # R500-2: расширенные system.* (мутации — на свежей копии file)
        "system.list": {},
        "system.select": {"name": "demo_achromat"},
        "system.drop": {"name": "ghost"},
        "system.clone": {"file": opj, "name": "copy1"},
        "system.rename": {"file": opj, "name": "renamed"},
        "system.name.set": {"file": opj, "name": "n2"},
        "system.comment.set": {"file": opj, "comment": "smoke"},
        "system.object.set": {"file": opj, "object_type": "FINITE",
                              "object_distance": 1000.0},
        "system.image.set": {"file": opj, "image_type": "INFINITE"},
        "system.stop.set": {"file": opj, "stop_surface": 1,
                            "stop_type": "z"},
        "system.obscuration.set": {"file": opj, "obscuration_ratio": 0.25},
        "system.beam.set": {"file": opj, "beam_mode": "given"},
        "system.aperture.set": {"file": opj, "aperture_type": "F_NUMBER",
                                "aperture_value": 5.0},
        "system.aperture.convert": {"file": opj, "value": 5.0,
                                    "from_type": "F_NUMBER"},
        "system.aperture.epd": {"file": opj},
        "system.aperture.from_epd": {"file": opj, "epd": 20.0},
        "system.aperture.pupil_distance": {"file": opj},
        "system.surface.get": {"file": opj, "index": 0},
        "system.surface.duplicate": {"file": opj, "index": 0, "count": 1},
        "system.surface.move": {"file": opj, "index": 2, "to": 0},
        "system.surface.aspheric.set": {"file": opj, "index": 0,
                                        "coeffs": [1e-6]},
        "system.surface.n.set": {"file": opj, "index": 0,
                                 "n_override": {"0.58756": 1.7}},
        "system.fields.remove": {"file": jsn, "index": 1},
        "system.fields.clear": {"file": jsn},
        "system.fields.auto": {"file": jsn, "num_fields": 3},
        "system.fields.weight.set": {"file": jsn, "index": 0,
                                     "weight": 2.0},
        "system.wavelengths.remove": {"file": opj, "index": 2},
        "system.wavelengths.clear": {"file": opj},
        "system.wavelengths.weight.set": {"file": opj, "index": 0,
                                          "weight": 0.5},
        "system.wavelengths.primary": {"file": opj},
        "system.glasses.list": {"file": opj},
        "system.glasses.replace": {"file": opj, "old": "К8", "new": "К8"},
        "system.validate": {"file": opj},
        "calc.aperture.real": {"file": opj},
        "calc.beam_geometry": {"file": opj},
        "calc.paraxial": {"file": opj},
        "calc.paraxial.multi_wl": {"file": opj},
        "calc.seidel": {"file": opj},
        # R500-6: расширенные calc.*
        "calc.n": {"glass": "К8", "wl": 0.58756},
        "calc.goe.radius": {"file": opj, "index": 0},
        "calc.goe.table": {"file": opj},
        "calc.semi_effective": {"semi_diameter": 10.0},
        "calc.vignetting.apply": {"file": opj, "field_y": 0.0,
                                  "ray_y": 0.5},
        "calc.cardinals": {"file": opj},
        "calc.pupils": {"file": opj},
        "calc.magnification": {"file": opj},
        "calc.lagrange": {"file": jsn},
        "calc.aperture.na": {"file": opj},
        "calc.sagitta": {"radius": 100.0, "height": 10.0},
        "calc.sagitta.table": {"file": opj, "heights": [5.0]},
        "calc.power.surface": {"n1": 1.0, "n2": 1.5163,
                               "radius": 100.0},
        "calc.power.thin_lens": {"n": 1.5163, "r1": 100.0,
                                 "r2": -100.0},
        "calc.power.table": {"file": opj},
        "calc.airy": {"f_number": 4.87},
        "calc.diffraction.cutoff": {"f_number": 4.87},
        "calc.depth_of_field": {"f_number": 4.87, "coc_um": 20.0},
        "calc.opl": {"segments": [{"n": 1.5, "length": 5.0}]},
        "calc.conjugate.solve": {"file": opj, "s": -200.0},
        "catalog.glass.get": {"name": "К8", "wl": 0.54607},
        "catalog.glass.search": {"query": "ТФ"},
        "catalog.info": {},
        # R500-4: расширенный каталог стёкол
        "catalog.glass.list": {"limit": 3},
        "catalog.glass.filter": {"vd_min": 50.0, "vd_max": 65.0,
                                 "limit": 5},
        "catalog.sources": {},
        "catalog.agf.status": {},
        "catalog.glass.dispersion": {"name": "К8",
                                     "wavelengths": [0.48613, 0.58756]},
        "catalog.glass.range": {"name": "К8", "steps": 4},
        "catalog.glass.abbe": {"name": "К8"},
        "catalog.glass.compare": {"a": "К8", "b": "ТФ1"},
        "catalog.glass.similar": {"name": "К8", "limit": 5},
        "catalog.glass.valid": {"name": "К8", "wl": 0.55},
        "catalog.glass.pairs": {"name": "К8", "limit": 5},
        "catalog.achromat.options": {"focal_length": 100.0},
        "catalog.library.create": {"generator": "achromat_100"},
        "catalog.library.list": {},
        "analyze.field_aberrations": {"file": opj},
        "analyze.psf": {"file": opj},
        "analyze.ray_fan": {"file": opj, "num_rays": 5},
        "analyze.spot": {"file": opj, "num_rays": 10},
        "analyze.tables.tabgl": {"file": opj},
        "analyze.tables.tabpr2": {"file": opj},
        # Волна 3, домен «Дифракция и волновой фронт» (psf_cmds.py);
        # тяжёлые решётки уменьшены, покрываем контракт, не точность.
        "diffr.mtf": {"file": opj, "grid_size": 32},
        "diffr.mtf.limited": {"file": opj},
        "diffr.mtf.poly": {"file": opj, "grid_size": 32},
        "diffr.mtf.quick": {"file": opj},
        "diffr.wavefront": {"file": opj, "grid_size": 32},
        "focus.all": {"file": opj},
        "focus.eqf": {"file": opj},
        "focus.max_strehl": {"file": opj},
        "focus.min_rms": {"file": opj},
        "focus.min_spot": {"file": opj},
        "focus.zone_best": {"file": opj},
        "mtf.curve": {"file": opj},
        "psf.encircled": {"file": opj},
        "psf.lsf": {"file": opj},
        "psf.section": {"file": opj},
        "psf.target": {"file": opj, "freq_lpmm": 50.0},
        "strehl.calc": {"file": opj, "wl": 0.58756},
        "strehl.marechal": {"sigma_w": 0.05},
        "zern.chromatic": {"file": opj, "num_rays": 16},
        "zern.coeffs": {"file": opj, "num_rays": 16},
        "zern.coeffs.fit": {"points": _SMOKE_POINTS_16},
        "zern.decompose": {"file": opj},
        "zern.fit_points": {"points": _SMOKE_POINTS_28},
        "zern.global": {"file": opj, "num_rings": 3, "num_fields": 3},
        "zern.protocol": {"file": opj},
        "zern.reconstruct": {"coeffs": [0.1, 0.0, -0.2, 0.05],
                             "grid": 16},
        "zern.strehl": {"coeffs": [0.1, 0.02, -0.05]},
        "zern.terms": {},
        "zern.wavefront": {"file": opj, "grid_size": 32},
        # R500-1: экспорт таблиц/данных (категория export; выгрузки пишутся
        # рядом с демо-системой в tmp-каталог модуля).
        "export.rows": {"rows": [{"a": 1}], "out": opj + ".rows.csv"},
        "export.data": {"data": {"a": [1]}, "out": opj + ".data.json"},
        "export.text": {"text": "ok", "out": opj + ".text.txt"},
        "export.command": {"cmd": "catalog.info", "out": opj + ".cmd.json"},
        "tables.taboc1.export": {"file": opj, "out": opj + ".taboc1.csv"},
        "tables.taboc2.export": {"file": opj, "out": opj + ".taboc2.csv"},
        "tables.tabgl.export": {"file": opj, "out": opj + ".tabgl.csv"},
        "tables.tabpr2.export": {"file": opj, "out": opj + ".tabpr2.csv"},
        "tables.tabax3.export": {"file": opj, "out": opj + ".tabax3.csv"},
        "tables.tabbea.export": {"file": opj, "out": opj + ".tabbea.csv"},
        "tables.tabeap.export": {"file": opj, "out": opj + ".tabeap.csv"},
        "tables.tabesb.export": {"file": opj, "out": opj + ".tabesb.csv"},
        "tables.field_zones.export": {"out": opj + ".zones.csv"},
        "analyze.spot.export": {"file": opj, "num_rays": 8,
                                "out": opj + ".spot.csv"},
        "analyze.ray_fan.export": {"file": opj, "num_rays": 5,
                                   "out": opj + ".rayfan.csv"},
        "analyze.field_aberrations.export": {"file": opj,
                                             "out": opj + ".fieldab.csv"},
        "aber.fan.export": {"file": opj, "num_rays": 10,
                            "out": opj + ".fan.csv"},
        "aber.mtf_geo.export": {"file": opj, "num_rays": 20,
                                "out": opj + ".mtfgeo.csv"},
        "export.zern.coeffs": {"file": opj, "num_rays": 16,
                               "out": opj + ".zern.csv"},
        "export.psf.encircled": {"file": opj, "out": opj + ".ee.csv"},
        "export.diffr.mtf": {"file": opj, "grid_size": 32,
                             "out": opj + ".mtf.csv"},
        "adv.lsf.export": {"file": opj, "out": opj + ".lsf.csv"},
        "adv.enc.export": {"file": opj, "num_rays": 50,
                           "out": opj + ".enc.csv"},
        "seidel.sums.export": {"file": opj, "out": opj + ".sums.csv"},
        "trace.ray_bundle.export": {"file": opj, "out": opj + ".bundle.csv"},
        "calc.paraxial.export": {"file": opj, "out": opj + ".parax.json"},
        "calc.seidel.export": {"file": opj, "out": opj + ".seidel.json"},
        # R500-10: сводные метрики качества (категория quality;
        # команды с полями системы — на .json: .opj теряет field_points)
        "quality.ee.diameters": {"file": jsn, "fields": [0.0, 3.0],
                                 "num_rays": 40},
        "quality.ee.diameters.psf": {"file": opj},
        "quality.spot.summary": {"file": jsn, "num_rays": 10},
        "quality.fields.summary": {"file": jsn, "num_rays": 10,
                                   "freq_lpmm": 30.0},
        "quality.mtf.matrix": {"file": opj, "fields": [0.0],
                               "freqs": [20.0]},
        "quality.mtf.poly": {"file": opj, "freqs": [20.0]},
        "quality.mtf.limit_freq": {"file": opj, "threshold": 0.3,
                                   "fields": [0.0]},
        "quality.mtf.area": {"file": opj},
        "quality.mtf.geo_vs_diff": {"file": opj, "num_rays": 20},
        "quality.strehl.summary": {"file": jsn},
        "quality.wavefront.summary": {"file": opj},
        "quality.passport": {"file": opj, "num_rays": 10},
        "quality.compare": {"file_a": opj, "file_b": jsn,
                            "num_rays": 10},
        "quality.check.mtf": {"file": opj, "threshold": 0.05,
                              "freq_lpmm": 30.0, "fields": [0.0]},
        "quality.check.strehl": {"file": opj, "fields": [0.0],
                                 "threshold": 0.01},
        "quality.check.spot": {"file": opj, "fields": [0.0],
                               "threshold_um": 500.0, "num_rays": 10},
        "quality.check.ee": {"file": opj, "fields": [0.0],
                             "threshold_um": 1000.0, "num_rays": 40},
        "quality.check.all": {"file": opj, "strehl_min": 0.01,
                              "fields": [0.0]},
        "quality.regime": {"file": opj, "num_rays": 10},
        # R500-11: текстовые отчёты (категория report; команды с полями
        # системы — на .json: .opj теряет field_points)
        "report.system": {"file": opj},
        "report.surfaces": {"file": opj},
        "report.fields": {"file": jsn},
        "report.glasses": {"file": opj},
        "report.paraxial": {"file": opj},
        "report.seidel": {"file": opj},
        "report.chromatism": {"file": opj},
        "report.aberrations": {"file": jsn},
        "report.spot": {"file": jsn, "num_rays": 10},
        "report.ee": {"file": jsn, "fields": [0.0, 3.0],
                      "num_rays": 40},
        "report.mtf": {"file": jsn, "fields": [0.0], "freqs": [20.0]},
        "report.strehl": {"file": jsn, "fields": [0.0]},
        "report.wavefront": {"file": opj},
        "report.quality": {"file": opj, "num_rays": 10},
        "report.tables": {"file": opj},
        "report.full": {"file": jsn, "num_rays": 10, "freq_lpmm": 30.0},
        # Волна 3, домен «Оптимизация и визуализация»: plot.* opt_cmds
        # (категория plot добавлена в covered пакетом R500-12 вместе с
        # plot_ext_cmds; out-файлы — рядом с демо-системой в tmp).
        "plot.spot": {"file": jsn, "output": opj + ".plot_spot.png",
                      "num_rays": 15},
        "plot.fan": {"file": jsn, "output": opj + ".plot_fan.png",
                     "num_rays": 9},
        "plot.field": {"file": jsn, "output": opj + ".plot_field.png"},
        "plot.psf": {"file": opj, "output": opj + ".plot_psf.png"},
        "plot.mtf": {"file": opj, "output": opj + ".plot_mtf.png"},
        "plot.ee": {"file": opj, "output": opj + ".plot_ee.png"},
        "plot.focus": {"file": opj, "output": opj + ".plot_focus.png",
                       "num_points": 10, "num_rays": 10},
        "plot.heatmap": {"file": opj, "output": opj + ".plot_heat.png",
                         "num_rays": 150},
        # R500-12: расширенные plot.* (plot_ext_cmds.py); команды с
        # полями системы — на .json (.opj теряет field_points).
        "plot.layout": {"file": jsn, "output": opj + ".plot_layout.png",
                        "num_rays": 5},
        "plot.caustic": {"file": opj, "output": opj + ".plot_caustic.png",
                         "num_rays": 9, "num_points": 30},
        "plot.vignetting": {"file": jsn,
                            "output": opj + ".plot_vign.png"},
        "plot.chromatism": {"file": opj,
                            "output": opj + ".plot_chrom.png",
                            "steps": 11},
        "plot.wavefront": {"file": opj, "output": opj + ".plot_wf.png",
                           "grid_size": 32},
        "plot.glassmap": {"file": opj, "output": opj + ".plot_gmap.png"},
        "plot.seidel": {"file": opj, "output": opj + ".plot_seidel.png"},
        "plot.fields": {"file": jsn, "output": opj + ".plot_fields.png"},
        "plot.mtf.family": {"file": jsn, "fields": [0.0, 5.0],
                            "output": opj + ".plot_mtf_fam.png"},
        "plot.ee.family": {"file": jsn, "fields": [0.0, 5.0],
                           "output": opj + ".plot_ee_fam.png"},
        "plot.spot.grid": {"file": jsn, "fields": [0.0, 3.0, 5.0],
                           "num_rays": 15,
                           "output": opj + ".plot_spot_grid.png"},
        "plot.fan.fields": {"file": jsn, "num_fan_rays": 9,
                            "output": opj + ".plot_fan_fields.png"},
        "plot.dof": {"file": opj, "coc_um": 300.0,
                     "defocus_range": 0.8, "num_points": 11,
                     "num_rays": 12, "output": opj + ".plot_dof.png"},
        "plot.pupil.vign": {"file": opj, "num_rings": 3,
                            "num_azimuths": 8,
                            "output": opj + ".plot_pupil.png"},
        "plot.psf.slice": {"file": opj,
                           "output": opj + ".plot_psf_slice.png"},
        # R500-13: интроспекция реестра/окружения (категории registry/
        # app/help; локальных данных не требуют — реестр сам источник).
        "registry.stats": {},
        "registry.categories": {},
        "registry.list": {"category": "calc"},
        "registry.search": {"query": "фокус", "limit": 5},
        "registry.schema": {"name": "calc.paraxial"},
        "registry.category.info": {"category": "plot"},
        "registry.params": {"param": "file"},
        "registry.export": {"out": opj + ".registry.json"},
        "app.info": {},
        "app.env": {},
        "app.paths": {},
        "help.command": {"name": "system.new"},
        # R500-14: расширения adv.* (adv_ext_cmds; категория adv добавлена
        # в covered этим пакетом — сюда же smoke 8 adv.* Волны 1 из
        # aber_cmds; команды с полями системы — на .json: .opj теряет
        # field_points).
        "adv.psf": {"file": opj, "num_rays": 64},
        "adv.lsf": {"file": opj, "num_rays": 64},
        "adv.enc": {"file": opj, "num_rays": 60},
        "adv.ptf": {"file": opj, "num_rays": 64},
        "adv.bar_image": {"file": opj},
        "adv.bar_mtf": {"file": opj, "freq_list": [10, 30]},
        "adv.esf": {"file": opj},
        "adv.object_image": {"file": opj, "num_rays": 64},
        "adv.psf.focus_stack": {"file": opj, "num_points": 5,
                                "defocus_range_mm": 0.03},
        "adv.psf.waist": {"file": opj, "num_points": 9,
                          "defocus_range_mm": 0.3},
        "adv.psf.fwhm": {"file": opj},
        "adv.psf.centroid": {"file": jsn, "fields": [0.0, 3.0]},
        "adv.psf.poly": {"file": opj},
        "adv.lsf.poly": {"file": opj},
        "adv.slit_image": {"file": opj, "width_um": 20.0},
        "adv.convolve.profile": {"file": opj,
                                 "profile": [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
                                 "pitch_um": 3.0},
        "adv.usaf.table": {"group_from": 0, "group_to": 2},
        "adv.usaf.resolve": {"file": opj, "group_to": 4},
        "adv.usaf.object": {"file": opj, "group": 2, "element": 3},
        "adv.dof.diffraction": {"file": opj},
        "adv.dof.compare": {"file": jsn, "fields": [0.0, 3.0],
                            "num_rays": 20},
        "adv.snr.bars": {"file": opj, "freq_lpmm": 30.0},
        "adv.noise.spot": {"file": opj, "pixel_um": 8.0, "size": 5,
                           "seed": 42},
        "adv.pixel.matrix": {"file": opj, "pixel_um": 8.0},
        "adv.pixel.energy": {"file": opj, "pixel_um": 8.0,
                             "offset_x_um": 4.0, "block": 3},
        "adv.energy.ring": {"file": opj, "r_inner_um": 5.0,
                            "r_outer_um": 15.0},
        "adv.resolve.thornber": {"file": jsn, "fields": [0.0, 3.0]},
        "adv.otf.complex": {"file": opj},
        "adv.airy.encircled": {"file": opj},
        # R500-15: пакетные прогоны (категория batch; локальных данных не
        # требуют — пакеты собираются из демо-файлов; выгрузки/копии — в
        # tmp-каталог демо-системы модуля).
        "batch.metrics": {},
        "batch.dir": {"path": os.path.dirname(opj)},
        "batch.names": {"files": [opj, jsn]},
        "batch.info": {"files": [opj, jsn]},
        "batch.load": {"files": [opj, jsn]},
        "batch.run": {"files": [jsn], "cmd": "calc.paraxial",
                      "include_data": True},
        "batch.validate": {"files": [opj, jsn]},
        "batch.metric": {"files": [opj, jsn], "metric": "efl"},
        "batch.summary": {"files": [opj, jsn]},
        "batch.rank": {"files": [opj, jsn], "metric": "f_number"},
        "batch.stats": {"files": [jsn], "metric": "spot_rms"},
        "batch.filter": {"files": [opj, jsn], "metric": "num_surfaces",
                         "op": "ge", "value": 1},
        "batch.check": {"files": [jsn], "metric": "spot_rms",
                        "threshold": 1000.0},
        "batch.compare": {"ref": jsn, "files": [opj]},
        "batch.apply": {"files": [jsn], "cmd": "system.scale",
                        "args": {"factor": 2.0},
                        "out_dir": os.path.dirname(opj)},
        "batch.changes": {"files": [jsn], "cmd": "system.scale",
                          "args": {"factor": 2.0}},
        "batch.convert": {"files": [opj],
                          "out_dir": os.path.dirname(opj)},
        "batch.dedupe": {"files": [opj, jsn]},
        "batch.export": {"files": [opj, jsn],
                         "out": opj + ".batch.csv"},
        "batch.report": {"files": [opj, jsn]},
    }


def test_every_registered_command_has_smoke(demo_files):
    """Реестр Волн 1+3(psf) покрыт smoke-набором; trace/aber/opt держат
    свои исчерпывающие наборы в собственных тест-модулях."""
    covered = W1_CATEGORIES | {"psf", "mtf", "diffr", "strehl", "zern",
                               "focus", "export", "quality", "report",
                               "plot", "registry", "app", "help",
                               "adv", "batch"}
    names = {n for n in default_registry.names()
             if default_registry.get(n).category in covered}
    smoke = _smoke_args(demo_files)
    missing = names - set(smoke)
    extra = set(smoke) - names
    assert not missing, f"команды без smoke: {sorted(missing)}"
    assert not extra, f"smoke для несуществующих команд: {sorted(extra)}"
    assert len(names) >= 30


#: R500: инвариант общего числа команд реестра (обновляется каждым пакетом;
#: 140 (Волны 1-5) + 27 (R500-1 export) + 33 (R500-2 system_ext) + 21 (R500-3 lbo) + 19 (R500-4 glass/spectral) + 18 (R500-5 units/spatial) + 20 (R500-6 calc_ext) + 19 (R500-7 sweep/seidel3) + 15 (R500-8 tol) + 19 (R500-10 quality) + 16 (R500-11 report) + 15 (R500-12 plot_ext) + 12 (R500-13 meta) + 21 (R500-14 adv_ext) + 20 (R500-15 batch) = 415).
REGISTRY_TOTAL_COMMANDS = 415


def test_registry_total_count():
    """R500: счётчик реестра == ожидаемому (обновлять в пакетах)."""
    import commands
    commands.register_all()
    assert len(commands.default_registry.names()) == REGISTRY_TOTAL_COMMANDS


def test_smoke_every_command(demo_files, tmp_path):
    """Каждая команда реестра выполняется без ошибки на демо-данных."""
    smoke = _smoke_args(demo_files)
    loaded_ctx = CommandContext()
    assert default_registry.execute(
        "system.load", loaded_ctx, {"file": demo_files[0]}).ok
    for name, args in sorted(smoke.items()):
        call_args = {k: v for k, v in args.items() if k != "__ctx__"}
        result = default_registry.execute(name, loaded_ctx, call_args)
        assert result.ok, f"{name}: {result.error}"
        # контракт: результат строго JSON-сериализуем
        import json
        json.dumps(result.data, ensure_ascii=False, allow_nan=False)


# --------------------------------------------------------------------------- #
# file.*
# --------------------------------------------------------------------------- #

class TestFileCommands:
    def test_formats_shape(self):
        data = run("file.formats")
        fmts = {f["format"]: f for f in data["formats"]}
        assert set(fmts) == {"opj", "lbo", "json"}
        assert fmts["opj"]["write"] and fmts["lbo"]["read"]
        assert not fmts["lbo"]["write"]

    def test_open_json_and_opj_give_same_optics(self, demo_files):
        opj, jsn = demo_files
        from_opj = run("calc.paraxial", {"file": opj})
        from_json = run("calc.paraxial", {"file": jsn})
        assert from_opj["focal_length"] == pytest.approx(
            from_json["focal_length"], abs=1e-6)

    def test_open_unknown_extension(self):
        result = default_registry.execute(
            "file.open", CommandContext(), {"file": "system.txt"})
        assert not result.ok
        assert result.error["code"] == "unknown_format"

    def test_info_counts(self, demo_files):
        data = run("file.info", {"file": demo_files[0]})
        assert data["format"] == "opj"
        assert data["num_surfaces"] == 3
        assert "К8" in data["glasses"] and "ТФ1" in data["glasses"]
        assert data["num_wavelengths"] == 3

    def test_convert_opj_to_json_roundtrip(self, demo_files, tmp_path):
        opj, _ = demo_files
        dst = str(tmp_path / "converted.json")
        data = run("file.convert", {"src": opj, "dst": dst})
        assert data["src_format"] == "opj" and data["dst_format"] == "json"
        system = load_json(dst)
        assert system.num_surfaces == 3
        assert any(s.glass == "К8" for s in system.surfaces)

    def test_save_unsupported_lbo(self, demo_files):
        result = default_registry.execute(
            "file.save", CommandContext(),
            {"src": demo_files[0], "file": "out.lbo"})
        assert not result.ok
        assert result.error["code"] == "unsupported"


# --------------------------------------------------------------------------- #
# system.*
# --------------------------------------------------------------------------- #

class TestSystemCommands:
    def test_new_empty_and_demos(self):
        empty = run("system.new", {"demo": "empty"})
        assert empty["num_surfaces"] == 0
        for demo in ("default", "achromat", "petzval", "mirror"):
            data = run("system.new", {"demo": demo})
            assert data["num_surfaces"] >= 2, demo

    def test_new_bad_demo_choice(self):
        result = default_registry.execute(
            "system.new", CommandContext(), {"demo": "nosuch"})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_load_sets_current(self, demo_files, ctx):
        assert ctx.current is not None
        data = run("system.current", ctx=ctx)
        assert data["name_in_context"] == "demo"
        assert "demo" in data["context_names"]

    def test_current_without_load_is_error(self):
        result = default_registry.execute(
            "system.current", CommandContext(), {})
        assert not result.ok
        assert result.error["code"] == "not_found"

    def test_mutations_visible_in_ctx(self, demo_files, ctx):
        """REPL-сценарий: правка текущей системы меняет её параксиал."""
        before = run("calc.paraxial", ctx=ctx)["focal_length"]
        changed = run("system.surface.set",
                      {"index": 0, "radius": 40.0}, ctx=ctx)
        assert changed["changed"] == ["radius"]
        assert changed["surfaces"][0]["radius"] == 40.0
        after = run("calc.paraxial", ctx=ctx)["focal_length"]
        assert after != pytest.approx(before)

    def test_surface_add_index_and_append(self, ctx):
        inserted = run("system.surface.add",
                       {"radius": -33.0, "index": 0}, ctx=ctx)
        assert inserted["surfaces"][0]["radius"] == -33.0
        appended = run("system.surface.add",
                       {"radius": -44.0}, ctx=ctx)
        assert appended["surfaces"][-1]["radius"] == -44.0

    def test_surface_remove_bad_index(self, ctx):
        result = default_registry.execute(
            "system.surface.remove", ctx, {"index": 99})
        assert not result.ok
        assert result.error["code"] == "invalid_param"

    def test_surface_set_requires_fields(self, ctx):
        result = default_registry.execute(
            "system.surface.set", ctx, {"index": 0})
        assert not result.ok

    def test_wavelengths_and_fields_add(self, ctx):
        wls = run("system.wavelengths.add",
                  {"value": 0.48613, "name": "F"}, ctx=ctx)
        assert wls["wavelengths"][-1] == {"value": 0.48613, "weight": 1.0,
                                          "name": "F"}
        flds = run("system.fields.add", {"y": 7.0}, ctx=ctx)
        assert flds["field_points"][-1]["y"] == 7.0

    def test_no_system_source_error(self):
        result = default_registry.execute(
            "calc.paraxial", CommandContext(), {})
        assert not result.ok
        assert result.error["code"] == "no_system"


# --------------------------------------------------------------------------- #
# calc.* — числа совпадают с прямыми вызовами domain
# --------------------------------------------------------------------------- #

class TestCalcCommands:
    def test_paraxial_matches_domain(self, demo_files):
        opj, _ = demo_files
        direct = paraxial_trace(load_json(demo_files[1]))
        data = run("calc.paraxial", {"file": opj})
        assert data["focal_length"] == pytest.approx(
            direct["focal_length"], rel=1e-12)
        assert data["f_number"] == pytest.approx(direct["f_number"],
                                                 rel=1e-12)
        assert 90.0 < abs(data["focal_length"]) < 110.0  # ахромат f'≈100

    def test_paraxial_wl_override(self, demo_files):
        _, jsn = demo_files
        blue = run("calc.paraxial", {"file": jsn, "wl": 0.43405})
        red = run("calc.paraxial", {"file": jsn, "wl": 0.65627})
        assert blue["wl"] == 0.43405 and red["wl"] == 0.65627
        assert blue["focal_length"] != pytest.approx(red["focal_length"])

    def test_multi_wl_covers_system_wavelengths(self, demo_files):
        _, jsn = demo_files
        system = load_json(jsn)
        data = run("calc.paraxial.multi_wl", {"file": jsn})
        assert data["num_wavelengths"] == len(system.wavelengths)
        wls = [r["wl"] for r in data["results"]]
        assert wls == pytest.approx([w.value for w in system.wavelengths])

    def test_seidel_matches_domain(self, demo_files):
        _, jsn = demo_files
        direct = seidel_aberrations(load_json(jsn))
        data = run("calc.seidel", {"file": jsn})
        assert data == pytest.approx(direct)

    def test_beam_geometry_matches_domain(self, demo_files):
        _, jsn = demo_files
        direct = compute_beam_geometry(load_json(jsn))
        data = run("calc.beam_geometry", {"file": jsn})
        assert len(data["fields"]) == len(direct)
        assert data["fields"][0]["Ax"] == pytest.approx(direct[0]["Ax"])

    def test_aperture_real_returns_diameter(self, demo_files):
        _, jsn = demo_files
        data = run("calc.aperture.real", {"file": jsn})
        assert data["diameter"] > 0


# --------------------------------------------------------------------------- #
# catalog.*
# --------------------------------------------------------------------------- #

class TestCatalogCommands:
    @requires_fil
    def test_info_counts(self):
        data = run("catalog.info")
        assert data["glasses"]["gost"] >= 25
        assert data["glasses"]["fil"] > 100
        assert "library" in data

    def test_glass_get_known_and_unknown(self):
        data = run("catalog.glass.get", {"name": "К8", "wl": 0.54607})
        assert data["source"] == "gost"
        assert data["nd"] == pytest.approx(1.5163, abs=1e-4)
        assert 1.5 < data["n"] < 1.6
        result = default_registry.execute(
            "catalog.glass.get", CommandContext(),
            {"name": "NO_SUCH_GLASS_XYZ"})
        assert not result.ok
        assert result.error["code"] == "not_found"

    def test_glass_search_finds_and_limits(self):
        data = run("catalog.glass.search", {"query": "ТФ", "limit": 5})
        assert 0 < len(data["matches"]) <= 5
        assert data["total"] >= len(data["matches"])
        sources = {m["source"] for m in data["matches"]}
        assert "gost" in sources

    def test_library_list_categories(self):
        data = run("catalog.library.list")
        names = [c["name"] for c in data["categories"]]
        assert any("OPAL" in n or "LBO" in n for n in names)


# --------------------------------------------------------------------------- #
# analyze.*
# --------------------------------------------------------------------------- #

class TestAnalyzeCommands:
    def test_ray_fan_shape(self, demo_files):
        data = run("analyze.ray_fan",
                   {"file": demo_files[1], "num_rays": 5})
        assert len(data["rays"]) == 5
        assert data["rays"][0]["pupil_y"] == pytest.approx(-1.0)
        assert data["rays"][2]["pupil_y"] == pytest.approx(0.0)
        ok_rays = [r for r in data["rays"] if r["success"]]
        assert ok_rays, "все лучи веера упали"
        assert all(len(r["path"]) >= 2 for r in ok_rays)

    def test_field_aberrations_rows(self, demo_files):
        data = run("analyze.field_aberrations",
                   {"file": demo_files[1], "fields": [0.0, 3.0]})
        assert [f["field_y"] for f in data["fields"]] == [0.0, 3.0]

    def test_spot_metrics(self, demo_files):
        data = run("analyze.spot",
                   {"file": demo_files[1], "num_rays": 10})
        assert data["num_points"] > 0
        assert data["rms"] >= 0.0
        assert data["rms_xy"]["rms_total"] >= 0.0

    def test_psf_scalars_and_grid(self, demo_files):
        scalars = run("analyze.psf", {"file": demo_files[1]})
        assert "strehl" in scalars and "cutoff_lpmm" in scalars
        assert "psf" not in scalars  # решётки по умолчанию выключены
        grid = run("analyze.psf",
                   {"file": demo_files[1], "include_grid": True})
        assert len(grid["psf"]) == len(grid["y_um"])
        assert abs(sum(sum(row) for row in grid["psf"]) - 1.0) < 1e-3

    def test_tables_tabgl_and_tabpr2(self, demo_files):
        tabgl = run("analyze.tables.tabgl", {"file": demo_files[1]})
        assert tabgl["rows"][-1]["n"] == 0  # осевая строка-эталон (замыкает)
        assert "TABGL" in tabgl["text"].upper() or tabgl["text"].strip()
        tabpr2 = run("analyze.tables.tabpr2", {"file": demo_files[1]})
        assert len(tabpr2["rows"]) == len(tabgl["rows"])
        assert tabpr2["text"].strip()


# --------------------------------------------------------------------------- #
# Источники системы: файл vs контекст vs текущая
# --------------------------------------------------------------------------- #

class TestSystemResolution:
    def test_ctx_name_beats_current(self, demo_files):
        _, jsn = demo_files
        ctx = CommandContext()
        assert default_registry.execute(
            "system.load", ctx, {"file": jsn, "name": "a"}).ok
        # подменим текущую: первая загруженная остаётся доступной по имени
        assert default_registry.execute(
            "system.new", ctx, {"demo": "mirror", "name": "b"}).ok
        via_name = run("system.surfaces.list", {"system": "a"}, ctx=ctx)
        via_current = run("system.surfaces.list", {}, ctx=ctx)
        assert via_name["num_surfaces"] == 3      # ахромат 'a'
        assert via_current["num_surfaces"] == 2   # зеркало 'b' текущее

    def test_file_beats_ctx(self, demo_files):
        opj, jsn = demo_files
        ctx = CommandContext()
        assert default_registry.execute(
            "system.load", ctx, {"file": jsn}).ok
        data = run("system.info", {"file": opj}, ctx=ctx)
        assert data["num_surfaces"] == 3

    def test_unknown_ctx_name(self, demo_files):
        result = default_registry.execute(
            "system.info", CommandContext(), {"system": "ghost"})
        assert not result.ok
        assert result.error["code"] == "not_found"
