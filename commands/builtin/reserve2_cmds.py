"""
OPAL-OKB — Пакет R500-19 «reserve ч.2»: финальная добивка до 500+.

Четыре семейства (категории выбраны по пинам tests/: tracex/aberx
запинены счётчиком 22 своими тест-модулями, поэтому экспорт-обёртки
живут в категории ``export`` — прецедент П1 «<домен>.*.export»;
``spectral``/``units`` — категории без пинов состава, их smoke —
в тест-модуле пакета):

- ``export.tracex.*`` / ``export.aberx.*`` / ``export.diagram.*`` —
  выгрузка таблиц П16/П17/П18 (лучевые, аберрационные, карта стёкол)
  в CSV/JSON: команда-источник выполняется через ``registry.execute``
  и пишется хелперами :mod:`commands.exportio` (как в П1 — экспортная
  обёртка не пересчитывает движок, а композирует его);
- ``catalog.spectral.band/stats`` — классификация λ по спектральным
  диапазонам (УФ/цветные поддиапазоны видимого/ИК; границы сверены с
  цветами стандартных линий ``utils/spectral_lines.py`` — единственный
  источник справочника) и свод справочника (по элементам/цветам/зонам);
- ``units.arcsec.ddmmss`` — разбор числа «гр.мнсек» DD.MMSS печати
  OPAL в секунды дуги/градусы (движок golden-сверок
  ``analysis.golden_verify.arcsec_of_ddmmss``; обратное кодирование
  ``ddmmss_value`` НЕ обёрнуто — его формула расходится с эталонами
  собственного docstring);
- ``file.stat`` / ``file.bench`` — метаданные файла БЕЗ загрузки
  (os.stat + детект формата по расширению) и замер времени
  загрузки/параксиального прогона (движки ``commands.systemio`` /
  ``domain.calculations`` — без новых ядер).

Физика не выдумывается: границы диапазонов согласованы с данными
репо (у каждой линии справочника полоса совпадает с её цветом —
инвариант теста), фотопические веса V(λ) НЕ добавлялись — таблицы
V(λ) в исходниках порта нет.
"""
import math
import os
import time

from commands.base import (
    ERR_INVALID_PARAM,
    ERR_NOT_FOUND,
    ERR_UNSUPPORTED,
    Param,
    CommandError,
    sanitize_json,
)
from commands.exportio import (
    FORMAT_JSON,
    FORMAT_TXT,
    detect_export_format,
    write_data,
    write_rows,
    write_text,
)
from commands.registry import Registry
from commands.systemio import system_source_params

#: Хелперы композиции П1 (единая точка запуска источника и записи).
from commands.builtin.export_cmds import (
    OUT_PARAM,
    _export_data,
    _run,
    _source_args,
)

# TINY/finite — общие хелперы пакетов R500 (правило №1).
from commands.builtin._r500_common import TINY
from commands.builtin._r500_common import finite as _finite

# ============================================================
# Именованные константы пакета
# ============================================================

#: Границы спектральных зон, нм (УФ/видимый/ИК — стандартные рамки,
#: внутренние поддиапазоны видимого сверены с цветами линий
#: utils/spectral_lines.py: синяя G' 434.05 → граница фиолет/синий
#: 430; жёлтая D 589.30 → жёлтый до 590; красная A' 768.19 → ИК
#: от 780; инвариант — тест пакета).
UV_MAX_NM = 380.0
VIS_MAX_NM = 780.0

#: (ключ, цвет справочника, от нм, до нм) — до None = без верхней.
SPECTRAL_BANDS = (
    ("uv", "УФ", 0.0, UV_MAX_NM),
    ("violet", "фиолетовая", UV_MAX_NM, 430.0),
    ("blue", "синяя", 430.0, 490.0),
    ("green", "зелёная", 490.0, 565.0),
    ("yellow", "жёлтая", 565.0, 590.0),
    ("orange", "оранжевая", 590.0, 625.0),
    ("red", "красная", 625.0, VIS_MAX_NM),
    ("ir", "ИК", VIS_MAX_NM, None),
)

#: Ключи зон для сводов (УФ/видимый/ИК).
ZONE_KEYS = ("uv", "visible", "ir")
ZONE_LABELS = {"uv": "УФ", "visible": "видимый", "ir": "ИК"}

#: Грани λ (мкм) для проверки параметров спектральных команд.
WL_UM_MIN = 0.01
WL_UM_MAX = 100.0

#: Повторов замера file.bench по умолчанию/максимум.
BENCH_REPEATS_DEFAULT = 3
BENCH_REPEATS_MAX = 20

#: Милисекунды в секунде (масштаб отчёта file.bench).
MS_PER_SECOND = 1000.0


# ============================================================
# Общие хелперы пакета
# ============================================================

def _spectral_band(wl_nm: float) -> dict:
    """Полоса спектральной зоны для λ (нм): ключ/цвет/границы.

    Полузакрытые интервалы [от, до): граница 430.0 нм — уже «синяя».
    """
    for key, color, lo, hi in SPECTRAL_BANDS:
        if wl_nm >= lo and (hi is None or wl_nm < hi):
            return {"band": key, "color": color,
                    "from_nm": lo, "to_nm": hi,
                    "visible": UV_MAX_NM <= wl_nm < VIS_MAX_NM}
    return {"band": "ir", "color": "ИК", "from_nm": VIS_MAX_NM,
            "to_nm": None, "visible": False}


def _wls_arg(wl, wls) -> list:
    """Список λ (мкм) из wl/wls: ровно один способ задания."""
    if wl is None and wls is None:
        raise CommandError(ERR_INVALID_PARAM,
                           "задайте wl (одна λ, мкм) или wls (список)")
    if wl is not None and wls is not None:
        raise CommandError(ERR_INVALID_PARAM,
                           "задайте что-то одно: wl или wls")
    values = [wl] if wl is not None else list(wls)
    if not values:
        raise CommandError(ERR_INVALID_PARAM, "wls: непустой список")
    try:
        values = [_finite(v, "wls") for v in values]
    except TypeError as exc:
        raise CommandError(ERR_INVALID_PARAM,
                           "wls: все элементы — числа") from exc
    for v in values:
        if not (WL_UM_MIN <= v <= WL_UM_MAX):
            raise CommandError(
                ERR_INVALID_PARAM,
                f"λ={v} мкм вне разумного диапазона "
                f"{WL_UM_MIN}–{WL_UM_MAX} мкм")
    return values


def _export_rows_of(registry: Registry, ctx, cmd: str, args: dict,
                    out: str, rows_keys=("rows",)) -> dict:
    """Табличная команда с нестандартным ключом строк → файл.

    Как ``_export_table`` П1, но список строк ищется по очереди в
    ``rows_keys`` (у таблиц П16/П18 бывают ``zones``/``cells``/``types``).
    ``.json`` всегда выгружает структуру целиком.
    """
    data = _run(registry, ctx, cmd, args)
    fmt = detect_export_format(out)
    if fmt == FORMAT_JSON:
        result = write_data(data, out)
        result["source"] = cmd
        return result
    if fmt == FORMAT_TXT:
        text = data.get("text") if isinstance(data, dict) else None
        if text is None:
            raise CommandError(
                ERR_UNSUPPORTED,
                f"{cmd} не имеет текстового формата — выгружайте "
                f".csv/.json")
        result = write_text(text, out)
        result["source"] = cmd
        return result
    rows = None
    for key in rows_keys:
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list) and all(isinstance(r, dict)
                                           for r in value):
            rows = value
            break
    if rows is None:
        raise CommandError(
            ERR_UNSUPPORTED,
            f"{cmd} не возвращает таблицу строк по ключам "
            f"{list(rows_keys)} — выгружайте .json")
    result = write_rows(rows, out)
    result["source"] = cmd
    return result


def _export_scalars(registry: Registry, ctx, cmd: str, args: dict,
                    out: str) -> dict:
    """Скалярная команда → файл: .json целиком / .csv строкой."""
    return _export_data(_run(registry, ctx, cmd, args), out, cmd)


def _bench_stats(seconds: list) -> dict:
    """min/mean/max по списку секунд (мс)."""
    ms = [s * MS_PER_SECOND for s in seconds]
    return {"min_ms": min(ms), "mean_ms": sum(ms) / len(ms),
            "max_ms": max(ms)}


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать команды пакета R500-19 (reserve ч.2)."""

    # ----------------------------------------------------------
    # export.tracex.* — таблицы трассировки П16
    # ----------------------------------------------------------

    @registry.command(
        "export.tracex.meridional", category="export",
        description="Меридиональная таблица лучей по поверхностям "
                    "(tracex.meridional.table) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — "
                                           "основная)"),
            OUT_PARAM,
        ])
    def export_tracex_meridional(ctx, file, system, lbo_index, lbo_name,
                                 field_y, wl, out):
        return _export_rows_of(registry, ctx, "tracex.meridional.table",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, field_y=field_y,
                                   wl=wl)), out)

    @registry.command(
        "export.tracex.opl", category="export",
        description="Таблица ОПД лучей веера по поверхностям "
                    "(tracex.opl.table) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — "
                                           "основная)"),
            OUT_PARAM,
        ])
    def export_tracex_opl(ctx, file, system, lbo_index, lbo_name,
                          field_y, wl, out):
        return _export_rows_of(registry, ctx, "tracex.opl.table",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, field_y=field_y,
                                   wl=wl)), out)

    @registry.command(
        "export.tracex.ray.surfaces", category="export",
        description="Трасса луча по поверхностям с ОПД (tracex.ray."
                    "surfaces) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("x", type="float", default=0.0,
                  help="координата x точки запуска, мм"),
            Param("y", type="float", default=0.0,
                  help="координата y точки запуска, мм"),
            Param("z", type="float", default=0.0,
                  help="координата z точки запуска, мм"),
            Param("k", type="float", default=0.0,
                  help="направляющий косинус k"),
            Param("l", type="float", default=0.0,
                  help="направляющий косинус l"),
            Param("m", type="float", default=1.0,
                  help="направляющий косинус m"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_tracex_ray_surfaces(ctx, file, system, lbo_index,
                                   lbo_name, x, y, z, k, l, m, wl, out):
        return _export_rows_of(registry, ctx, "tracex.ray.surfaces",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, x=x, y=y, z=z,
                                   k=k, l=l, m=m, wl=wl)), out)

    @registry.command(
        "export.tracex.ynu", category="export",
        description="Параксиальная таблица y/n·u (tracex.ynu.table) → "
                    "CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_tracex_ynu(ctx, file, system, lbo_index, lbo_name,
                          wl, out):
        return _export_rows_of(registry, ctx, "tracex.ynu.table",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, wl=wl)), out)

    @registry.command(
        "export.tracex.paraxial.matrices", category="export",
        description="Матрицы ABCD по поверхностям (tracex.paraxial."
                    "matrices; строки — поверхности) → CSV/JSON "
                    "(в .json — и промежутки, и системная матрица)",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_tracex_matrices(ctx, file, system, lbo_index, lbo_name,
                               wl, out):
        return _export_rows_of(
            registry, ctx, "tracex.paraxial.matrices",
            _source_args(dict(file=file, system=system,
                              lbo_index=lbo_index, lbo_name=lbo_name,
                              wl=wl)), out,
            rows_keys=("surfaces",))

    @registry.command(
        "export.tracex.fan.zones", category="export",
        description="Осевой веер по зонам зрачка (tracex.fan.zones; "
                    "строки — зоны) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("n_zones", type="int", default=3,
                  help="зон (если zones не заданы)"),
            Param("zones", type="list", help="явные зоны зрачка"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_tracex_fan_zones(ctx, file, system, lbo_index, lbo_name,
                                field_y, n_zones, zones, wl, out):
        return _export_rows_of(
            registry, ctx, "tracex.fan.zones",
            _source_args(dict(file=file, system=system,
                              lbo_index=lbo_index, lbo_name=lbo_name,
                              field_y=field_y, n_zones=n_zones,
                              zones=zones, wl=wl)), out,
            rows_keys=("zones",))

    @registry.command(
        "export.tracex.stop.clearance", category="export",
        description="Клиренс луча на апертурной диафрагме (tracex.stop."
                    "clearance; скаляры) → CSV (строка)/JSON (целиком)",
        returns="файл выгрузки",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("rho_x", type="float", default=0.0,
                  help="зрачковая координата ρx"),
            Param("rho_y", type="float", default=0.0,
                  help="зрачковая координата ρy"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_tracex_stop_clearance(ctx, file, system, lbo_index,
                                     lbo_name, field_y, rho_x, rho_y,
                                     wl, out):
        return _export_scalars(
            registry, ctx, "tracex.stop.clearance",
            _source_args(dict(file=file, system=system,
                              lbo_index=lbo_index, lbo_name=lbo_name,
                              field_y=field_y, rho_x=rho_x,
                              rho_y=rho_y, wl=wl)), out)

    @registry.command(
        "export.tracex.ray.multi_wl", category="export",
        description="Луч на всех λ системы (tracex.ray.multi_wl) → "
                    "CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("rho_x", type="float", default=0.0,
                  help="зрачковая координата ρx"),
            Param("rho_y", type="float", default=0.0,
                  help="зрачковая координата ρy"),
            OUT_PARAM,
        ])
    def export_tracex_ray_multi_wl(ctx, file, system, lbo_index,
                                   lbo_name, field_y, rho_x, rho_y,
                                   out):
        return _export_rows_of(registry, ctx, "tracex.ray.multi_wl",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, field_y=field_y,
                                   rho_x=rho_x, rho_y=rho_y)), out)

    # ----------------------------------------------------------
    # export.aberx.* — аберрационные таблицы П17
    # ----------------------------------------------------------

    @registry.command(
        "export.aberx.map.grid", category="export",
        description="Карта поперечных аберраций по полям×зонам "
                    "(aberx.map.grid) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="поля (по умолчанию — поля системы)"),
            Param("num_rays", type="int", default=9,
                  help="лучей веера на поле"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_aberx_map_grid(ctx, file, system, lbo_index, lbo_name,
                              fields, num_rays, wl, out):
        return _export_rows_of(registry, ctx, "aberx.map.grid",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, fields=fields,
                                   num_rays=num_rays, wl=wl)), out)

    @registry.command(
        "export.aberx.rms.grid", category="export",
        description="СКВ волновой аберрации по полям×λ (aberx.rms.grid)"
                    " → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="поля (по умолчанию — поля системы)"),
            Param("wls", type="list",
                  help="λ, мкм (по умолчанию — λ системы)"),
            Param("num_rings", type="int", default=3,
                  help="кольца гексаполярной сетки зрачка"),
            OUT_PARAM,
        ])
    def export_aberx_rms_grid(ctx, file, system, lbo_index, lbo_name,
                              fields, wls, num_rings, out):
        return _export_rows_of(registry, ctx, "aberx.rms.grid",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, fields=fields,
                                   wls=wls, num_rings=num_rings)), out)

    @registry.command(
        "export.aberx.spot.grid", category="export",
        description="Пятно RMS/центроид по полям×λ (aberx.spot.grid) → "
                    "CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="поля (по умолчанию — поля системы)"),
            Param("wls", type="list",
                  help="λ, мкм (по умолчанию — λ системы)"),
            Param("num_rays", type="int", default=15,
                  help="лучей пятна"),
            OUT_PARAM,
        ])
    def export_aberx_spot_grid(ctx, file, system, lbo_index, lbo_name,
                               fields, wls, num_rays, out):
        return _export_rows_of(registry, ctx, "aberx.spot.grid",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, fields=fields,
                                   wls=wls, num_rays=num_rays)), out)

    @registry.command(
        "export.aberx.seidel.shares", category="export",
        description="Вклады поверхностей в суммы Зейделя, % "
                    "(aberx.seidel.shares) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_aberx_seidel_shares(ctx, file, system, lbo_index,
                                   lbo_name, wl, out):
        return _export_rows_of(registry, ctx, "aberx.seidel.shares",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, wl=wl)), out)

    @registry.command(
        "export.aberx.distortion.curve", category="export",
        description="Кривая дисторсии по полям (aberx.distortion."
                    "curve) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="поля (по умолчанию — поля системы)"),
            Param("fit_degree", type="int", default=3,
                  help="степень полинома подгонки"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_aberx_distortion(ctx, file, system, lbo_index, lbo_name,
                                fields, fit_degree, wl, out):
        return _export_rows_of(registry, ctx, "aberx.distortion.curve",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, fields=fields,
                                   fit_degree=fit_degree, wl=wl)), out)

    @registry.command(
        "export.aberx.astig.curve", category="export",
        description="Кривая астигматизма t′m/t′s по полям (aberx.astig."
                    "curve) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="поля (по умолчанию — поля системы)"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_aberx_astig(ctx, file, system, lbo_index, lbo_name,
                           fields, wl, out):
        return _export_rows_of(registry, ctx, "aberx.astig.curve",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, fields=fields,
                                   wl=wl)), out)

    @registry.command(
        "export.aberx.spherical.zones", category="export",
        description="Сферическая аберрация по зонам зрачка "
                    "(aberx.spherical.zones) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=9,
                  help="лучей веера"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_aberx_spherical(ctx, file, system, lbo_index, lbo_name,
                               field_y, num_rays, wl, out):
        return _export_rows_of(registry, ctx, "aberx.spherical.zones",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, field_y=field_y,
                                   num_rays=num_rays, wl=wl)), out)

    @registry.command(
        "export.aberx.transverse.zones", category="export",
        description="Поперечные аберрации мер./саг. по зонам "
                    "(aberx.transverse.zones) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", required=True, help="поле"),
            Param("n_zones", type="int", default=3,
                  help="зон (если zones не заданы)"),
            Param("zones", type="list", help="явные зоны зрачка"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_aberx_transverse(ctx, file, system, lbo_index, lbo_name,
                                field_y, n_zones, zones, wl, out):
        return _export_rows_of(registry, ctx, "aberx.transverse.zones",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, field_y=field_y,
                                   n_zones=n_zones, zones=zones,
                                   wl=wl)), out)

    @registry.command(
        "export.aberx.focal.zonal", category="export",
        description="Зональные фокусы мер./саг. (aberx.focal.zonal) → "
                    "CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", required=True, help="поле"),
            Param("zones", type="list", help="явные зоны зрачка"),
            Param("wl", type="float", help="λ, мкм"),
            OUT_PARAM,
        ])
    def export_aberx_focal_zonal(ctx, file, system, lbo_index, lbo_name,
                                 field_y, zones, wl, out):
        return _export_rows_of(registry, ctx, "aberx.focal.zonal",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, field_y=field_y,
                                   zones=zones, wl=wl)), out)

    @registry.command(
        "export.aberx.chrom.focus_shift", category="export",
        description="Хроматический сдвиг EFL/BFD по λ "
                    "(aberx.chrom.focus_shift) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wls", type="list",
                  help="λ, мкм (по умолчанию — λ системы)"),
            OUT_PARAM,
        ])
    def export_aberx_chrom_shift(ctx, file, system, lbo_index, lbo_name,
                                 wls, out):
        return _export_rows_of(registry, ctx, "aberx.chrom.focus_shift",
                               _source_args(dict(
                                   file=file, system=system,
                                   lbo_index=lbo_index,
                                   lbo_name=lbo_name, wls=wls)), out)

    # ----------------------------------------------------------
    # export.diagram.* — таблицы карты стёкол П18
    # ----------------------------------------------------------

    @registry.command(
        "export.diagram.coverage", category="export",
        description="Покрытие каталога на карте n–Vd сеткой "
                    "(diagram.coverage; строки — ячейки) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=[
            Param("source", choices=["gost", "fil", "agf"],
                  help="каталог (по умолчанию — все)"),
            Param("vd_bins", type="int", default=6,
                  help="ячеек по Vd"),
            Param("nd_bins", type="int", default=8,
                  help="ячеек по nd"),
            Param("top_cells", type="int", default=5,
                  help="топ-ячеек (в .json)"),
            OUT_PARAM,
        ])
    def export_diagram_coverage(ctx, source, vd_bins, nd_bins,
                                top_cells, out):
        return _export_rows_of(
            registry, ctx, "diagram.coverage",
            _source_args(dict(source=source, vd_bins=vd_bins,
                              nd_bins=nd_bins, top_cells=top_cells)),
            out, rows_keys=("cells",))

    @registry.command(
        "export.diagram.type.stats", category="export",
        description="Диаграмма Аббе по типам марок (diagram.type.stats; "
                    "строки — типы) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=[
            Param("source", choices=["gost", "fil", "agf"],
                  help="каталог (по умолчанию — все)"),
            OUT_PARAM,
        ])
    def export_diagram_type_stats(ctx, source, out):
        return _export_rows_of(
            registry, ctx, "diagram.type.stats",
            _source_args(dict(source=source)), out,
            rows_keys=("types",))

    # ----------------------------------------------------------
    # catalog.spectral.* — спектральные зоны λ
    # ----------------------------------------------------------

    @registry.command(
        "catalog.spectral.band", category="spectral",
        description="Классификация длины волны по спектральным зонам: "
                    "УФ / цветные поддиапазоны видимого / ИК (границы "
                    "согласованы с цветами стандартных линий справочника "
                    "utils/spectral_lines.py — у каждой линии полоса "
                    "совпадает с её цветом)",
        returns="{count, bands: [{wl_um, wl_nm, band, color, from_nm, "
                "to_nm, visible}], zones}",
        params=[
            Param("wl", type="float", help="λ, мкм (одиночная)"),
            Param("wls", type="list",
                  help="список λ, мкм (пакетная классификация)"),
        ])
    def catalog_spectral_band(ctx, wl, wls):
        values = _wls_arg(wl, wls)
        rows = []
        zones = {key: 0 for key in ZONE_KEYS}
        for value in values:
            wl_nm = value * 1000.0
            band = _spectral_band(wl_nm)
            zone = ("visible" if band["visible"]
                    else "uv" if wl_nm < UV_MAX_NM else "ir")
            zones[zone] += 1
            rows.append({"wl_um": value, "wl_nm": wl_nm,
                         "band": band["band"], "color": band["color"],
                         "from_nm": band["from_nm"],
                         "to_nm": band["to_nm"],
                         "visible": band["visible"]})
        return {"count": len(rows), "bands": sanitize_json(rows),
                "zones": zones,
                "boundaries_nm": {"uv_max": UV_MAX_NM,
                                  "vis_max": VIS_MAX_NM}}

    @registry.command(
        "catalog.spectral.stats", category="spectral",
        description="Свод справочника спектральных линий: счётчики по "
                    "элементам и цветам, диапазон λ, разбивка по зонам "
                    "УФ/видимый/ИК (движок классификации — тот же, что "
                    "catalog.spectral.band)",
        returns="{count, by_element, by_color, by_zone, wl_nm_min, "
                "wl_nm_max, wl_um_min, wl_um_max}",
        params=[])
    def catalog_spectral_stats(ctx):
        from utils.spectral_lines import SPECTRAL_LINES
        by_element, by_color = {}, {}
        zones = {key: 0 for key in ZONE_KEYS}
        nm_values = []
        for line in SPECTRAL_LINES:
            by_element[line.element] = \
                by_element.get(line.element, 0) + 1
            by_color[line.color] = by_color.get(line.color, 0) + 1
            band = _spectral_band(line.wavelength_nm)
            zone = ("visible" if band["visible"]
                    else "uv" if line.wavelength_nm < UV_MAX_NM
                    else "ir")
            zones[zone] += 1
            nm_values.append(line.wavelength_nm)
        return {"count": len(SPECTRAL_LINES),
                "by_element": by_element, "by_color": by_color,
                "by_zone": zones,
                "wl_nm_min": min(nm_values), "wl_nm_max": max(nm_values),
                "wl_um_min": min(nm_values) / 1000.0,
                "wl_um_max": max(nm_values) / 1000.0,
                "source": "utils/spectral_lines.SPECTRAL_LINES"}

    # ----------------------------------------------------------
    # units.arcsec.ddmmss — печать OPAL «гр.мнсек»
    # ----------------------------------------------------------

    @registry.command(
        "units.arcsec.ddmmss", category="units",
        description="Разбор числа «гр.мнсек» DD.MMSS печати OPAL в "
                    "секунды дуги и градусы (движок golden-сверок "
                    "analysis.golden_verify.arcsec_of_ddmmss — им "
                    "сверяются поперечные golden-прогонов; OBEKTIV "
                    "1.130483 → 1°13'04.83\" = 4384.83″, ST4 0.000217 "
                    "→ 2.17″)",
        returns="{value, arcsec, deg}",
        params=[
            Param("value", type="float", required=True,
                  help="число «гр.мнсек» DD.MMSS (например 1.130483)"),
        ])
    def units_arcsec_ddmmss(ctx, value):
        from analysis.golden_verify import arcsec_of_ddmmss
        number = _finite(value, "value")
        seconds = arcsec_of_ddmmss(number)
        return {"value": number, "arcsec": seconds,
                "deg": seconds / 3600.0}

    # ----------------------------------------------------------
    # file.stat / file.bench — файловые хвосты
    # ----------------------------------------------------------

    @registry.command(
        "file.stat", category="file",
        description="Метаданные файла БЕЗ загрузки системы: размер, "
                    "время модификации, расширение и формат по "
                    "расширению (os.stat + детект commands.systemio; "
                    "содержимое не читается — в отличие от file.info/"
                    "file.checksum)",
        returns="{file, abs, size_bytes, mtime_epoch, mtime_iso, "
                "extension, format}",
        params=[
            Param("file", required=True, help="путь к файлу"),
        ])
    def file_stat(ctx, file):
        from commands.systemio import FORMATS, detect_format
        if not os.path.exists(file):
            raise CommandError(ERR_NOT_FOUND,
                               f"файл не найден: {file}")
        if not os.path.isfile(file):
            raise CommandError(ERR_INVALID_PARAM,
                               f"не обычный файл: {file}")
        stat = os.stat(file)
        fmt = None
        try:
            fmt = detect_format(file)
        except CommandError:
            fmt = None
        return {
            "file": file, "abs": os.path.abspath(file),
            "size_bytes": stat.st_size,
            "mtime_epoch": stat.st_mtime,
            "mtime_iso": time.strftime("%Y-%m-%dT%H:%M:%S",
                                       time.localtime(stat.st_mtime)),
            "extension": os.path.splitext(str(file))[1].lower(),
            "format": fmt,
            "supported_formats": sorted(FORMATS),
        }

    @registry.command(
        "file.bench", category="file",
        description="Замер времени работы с файлом системы: повторные "
                    "загрузка (commands.systemio.load_system) и "
                    "параксиальный прогон (domain.calculations."
                    "paraxial_trace) — min/mean/max, мс",
        returns="{file, format, repeats, size_bytes, num_surfaces, "
                "load: {min_ms, mean_ms, max_ms}, trace: {…}, total_ms}",
        params=[
            Param("file", required=True, help="путь к файлу системы"),
            Param("repeats", type="int", default=BENCH_REPEATS_DEFAULT,
                  help=f"повторов замера 1–{BENCH_REPEATS_MAX} "
                       f"(по умолчанию {BENCH_REPEATS_DEFAULT})"),
            Param("lbo_index", type="int", default=0,
                  help="индекс записи в .lbo"),
            Param("lbo_name", help="имя .OPJ-записи в .lbo"),
        ])
    def file_bench(ctx, file, repeats, lbo_index, lbo_name):
        from commands.systemio import detect_format, load_system
        from domain.calculations import paraxial_trace
        if not (1 <= repeats <= BENCH_REPEATS_MAX):
            raise CommandError(
                ERR_INVALID_PARAM,
                f"repeats: 1–{BENCH_REPEATS_MAX} (получено {repeats})")
        started = time.perf_counter()
        load_seconds, trace_seconds = [], []
        system = None
        for _ in range(repeats):
            mark = time.perf_counter()
            system = load_system(file, lbo_index=lbo_index,
                                 lbo_name=lbo_name)
            load_seconds.append(time.perf_counter() - mark)
            mark = time.perf_counter()
            paraxial_trace(system)
            trace_seconds.append(time.perf_counter() - mark)
        return {
            "file": file, "format": detect_format(file),
            "repeats": repeats,
            "size_bytes": os.path.getsize(file),
            "num_surfaces": system.num_surfaces,
            "load": _bench_stats(load_seconds),
            "trace": _bench_stats(trace_seconds),
            "total_ms": (time.perf_counter() - started)
            * MS_PER_SECOND,
        }
