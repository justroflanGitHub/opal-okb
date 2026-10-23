"""
OPAL-OKB — Пакет R500-1: экспорт результатов в файлы (CSV/JSON/TXT).

Три семейства (источник — ТЗ TASK_REGISTRY_500 §2.3):

- ``export.*`` —generic-выгрузки (строки/структура/текст/результат
  любой команды реестра);
- ``tables.*.export`` — OPAL-таблицы (TABOC1/TABOC2/TABGL/TABPR2/
  TABAX3/TABBEA/TABEAP/TABESB/зоны поля): расчёт соседней командой
  реестра + запись (``.csv`` — строки, ``.json`` — целиком, ``.txt`` —
  текстовый формат OPAL);
- ``<домен>.*.export`` — расчётные данные (пятно, веера, ЧКХ, ФКЭ,
  ФРЛ, Цернике, параксиал, Зейдель, пучок 3D).

Композиция без дублирования: экспортная команда выполняет команду-
источник через тот же реестр (``registry.execute``) и пишет результат
хелперами :mod:`commands.exportio` — единственным местом записи.
"""
from commands.base import (
    ERR_INVALID_PARAM,
    ERR_UNSUPPORTED,
    Param,
    CommandError,
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

#: Параметр «куда писать» — общий хвост всех экспортных команд.
OUT_PARAM = Param("out", required=True,
                  help="файл выгрузки: .csv (строки), .json (структура), "
                       ".txt (текстовый формат, где есть)")


# ============================================================
# Хелперы композиции
# ============================================================

def _run(registry: Registry, ctx, name: str, args: dict) -> dict:
    """Выполнить команду-источник; ошибка → CommandError (как своя)."""
    result = registry.execute(name, ctx, args)
    if not result.ok:
        raise CommandError(result.error["code"], result.error["message"])
    return result.data


def _source_args(locals_dict: dict, skip=("ctx",)) -> dict:
    """Аргументы обработчика → dict для execute (без None и служебных)."""
    return {k: v for k, v in locals_dict.items()
            if k not in skip and v is not None}


def _export_table(registry: Registry, ctx, cmd: str, args: dict,
                  out: str) -> dict:
    """Табличная команда → файл: .txt (text) / .csv+.json (rows)."""
    data = _run(registry, ctx, cmd, args)
    fmt = detect_export_format(out)
    if fmt == FORMAT_TXT:
        text = data.get("text")
        if text is None:
            raise CommandError(
                ERR_UNSUPPORTED,
                f"{cmd} не имеет текстового формата — выгружайте .csv/.json")
        result = write_text(text, out)
        result["source"] = cmd
        return result
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise CommandError(
            ERR_UNSUPPORTED,
            f"{cmd} не возвращает таблицу строк — выгружайте .json")
    result = write_rows(rows, out)
    result["source"] = cmd
    return result


def _export_data(data: dict, out: str, cmd: str = "") -> dict:
    """Полная структура результата → .json (или .csv-строка скаляров)."""
    fmt = detect_export_format(out)
    if fmt == FORMAT_JSON:
        result = write_data(data, out)
    else:
        scalars = {k: v for k, v in data.items()
                   if not isinstance(v, (list, dict))}
        result = write_rows([scalars], out)
    if cmd:
        result["source"] = cmd
    return result


def _export_curves(data: dict, out: str, curves: dict, cmd: str) -> dict:
    """Параллельные массивы одинаковой длины → CSV/JSON.

    ``curves`` — имя колонки → ключ в ``data`` (все списки равной длины).
    Скалярные поля ``data`` попадают в ответ (не в файл).
    """
    fmt = detect_export_format(out)
    if fmt == FORMAT_JSON:
        result = write_data(data, out)
        result["source"] = cmd
        return result
    if fmt == FORMAT_TXT:
        raise CommandError(
            ERR_UNSUPPORTED,
            f"{cmd}: кривые выгружаются в .csv (точки) или .json (целиком)")
    arrays = {col: data[key] for col, key in curves.items()}
    lengths = {len(v) for v in arrays.values()}
    if len(lengths) > 1:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"{cmd}: оси кривых разной длины {sorted(lengths)}; выгружайте .json")
    rows = [dict(zip(arrays, point)) for point in zip(*arrays.values())]
    result = write_rows(rows, out)
    result["source"] = cmd
    return result


def register(registry: Registry) -> None:
    """Зарегистрировать все экспортные команды (R500-1)."""

    # ============================================================
    # export.* — generic-выгрузки
    # ============================================================

    @registry.command(
        "export.rows", category="export",
        description="Записать строки-словари в CSV/JSON (таблица)",
        returns="{out, format, rows, columns, preview}",
        params=[
            Param("rows", type="list", required=True,
                  help="список словарей — строки таблицы"),
            Param("columns", type="list",
                  help="порядок колонок CSV (по умолчанию — все ключи)"),
            Param("out", required=True, help="файл .csv/.json"),
        ])
    def export_rows(ctx, rows, columns, out):
        return write_rows(rows, out, columns)

    @registry.command(
        "export.data", category="export",
        description="Записать структуру (dict/list) в JSON-файл",
        returns="{out, format, size_bytes, preview}",
        params=[
            Param("data", type="dict", required=True,
                  help="JSON-сериализуемая структура"),
            Param("out", required=True, help="файл .json"),
        ])
    def export_data(ctx, data, out):
        return write_data(data, out)

    @registry.command(
        "export.text", category="export",
        description="Записать текст в .txt (протоколы/отчёты)",
        returns="{out, format, size_bytes, preview}",
        params=[
            Param("text", required=True, help="текст для записи"),
            Param("out", required=True, help="файл .txt"),
        ])
    def export_text(ctx, text, out):
        return write_text(text, out)

    @registry.command(
        "export.command", category="export",
        description="Выполнить любую команду реестра и выгрузить её "
                    "результат (.json — целиком; .csv — rows/скаляры; "
                    ".txt — поле text, если есть)",
        returns="результат записи + source-команда",
        params=[
            Param("cmd", required=True, help="имя команды реестра"),
            Param("args", type="dict",
                  help="аргументы команды (по её схеме)"),
            Param("out", required=True, help="файл выгрузки"),
        ])
    def export_command(ctx, cmd, args, out):
        data = _run(registry, ctx, cmd, args or {})
        fmt = detect_export_format(out)
        if fmt == FORMAT_TXT:
            if not isinstance(data, dict) or data.get("text") is None:
                raise CommandError(
                    ERR_UNSUPPORTED,
                    f"{cmd} не возвращает текст — выгружайте .csv/.json")
            result = write_text(data["text"], out)
        elif isinstance(data, dict) and isinstance(data.get("rows"), list):
            result = write_rows(data["rows"], out)
        elif isinstance(data, dict):
            result = _export_data(data, out)
        else:
            result = write_data(data, out)
        result["source"] = cmd
        return result

    # ============================================================
    # tables.*.export — OPAL-таблицы
    # ============================================================

    @registry.command(
        "tables.taboc1.export", category="export",
        description="TABOC1 (остаточные аберрации осевого пучка) → CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("n_zones", type="int", default=4, help="зон зрачка"),
            OUT_PARAM,
        ])
    def tables_taboc1_export(ctx, file, system, lbo_index, lbo_name,
                             wl, n_zones, out):
        return _export_table(registry, ctx, "tables.taboc1",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name, wl=wl,
                                               n_zones=n_zones)), out)

    @registry.command(
        "tables.taboc2.export", category="export",
        description="TABOC2 (волновые аберрации осевого пучка) → CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("n_zones", type="int", default=4, help="зон зрачка"),
            Param("num_rays", type="int", default=20,
                  help="лучей веера неизопланатизма"),
            Param("columns", type="list", help="селектор колонок TABOC2"),
            OUT_PARAM,
        ])
    def tables_taboc2_export(ctx, file, system, lbo_index, lbo_name,
                             wl, n_zones, num_rays, columns, out):
        return _export_table(registry, ctx, "tables.taboc2",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name, wl=wl,
                                               n_zones=n_zones,
                                               num_rays=num_rays,
                                               columns=columns)), out)

    @registry.command(
        "tables.tabgl.export", category="export",
        description="TABGL (характеристики главных лучей) → CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("n_zones", type="int", default=3, help="зон поля"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def tables_tabgl_export(ctx, file, system, lbo_index, lbo_name,
                            n_zones, wl, out):
        return _export_table(registry, ctx, "analyze.tables.tabgl",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name,
                                               n_zones=n_zones, wl=wl)), out)

    @registry.command(
        "tables.tabpr2.export", category="export",
        description="TABPR2 (хроматизм увеличения/положения по полю) → "
                    "CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl_main", type="float", help="основная λ пары, мкм"),
            Param("wl_alt", type="float", help="альтернативная λ, мкм"),
            Param("n_zones", type="int", default=3, help="зон поля"),
            OUT_PARAM,
        ])
    def tables_tabpr2_export(ctx, file, system, lbo_index, lbo_name,
                             wl_main, wl_alt, n_zones, out):
        return _export_table(registry, ctx, "analyze.tables.tabpr2",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name,
                                               wl_main=wl_main,
                                               wl_alt=wl_alt,
                                               n_zones=n_zones)), out)

    @registry.command(
        "tables.tabax3.export", category="export",
        description="TABAX3 (OPAL-хроматизм) → CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl_main", type="float", help="основная λ пары, мкм"),
            Param("wl_flags", type="list",
                  help="флаги волн по поверхностям (как chrom.opal)"),
            Param("field_y", type="float", help="поле главного луча"),
            OUT_PARAM,
        ])
    def tables_tabax3_export(ctx, file, system, lbo_index, lbo_name,
                             wl_main, wl_flags, field_y, out):
        return _export_table(registry, ctx, "chrom.opal",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name,
                                               wl_main=wl_main,
                                               wl_flags=wl_flags,
                                               field_y=field_y)), out)

    @registry.command(
        "tables.tabbea.export", category="export",
        description="TABBEA (виньетирование/освещённость по полю) → "
                    "CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей (град); по умолчанию — поля системы"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def tables_tabbea_export(ctx, file, system, lbo_index, lbo_name,
                             fields, wl, out):
        return _export_table(registry, ctx, "vign.tabbea",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name,
                                               fields=fields, wl=wl)), out)

    @registry.command(
        "tables.tabeap.export", category="export",
        description="TABEAP (зоны экранов/прохождения по поверхностям) → "
                    "CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def tables_tabeap_export(ctx, file, system, lbo_index, lbo_name,
                             wl, out):
        return _export_table(registry, ctx, "beam.screen_zones",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name, wl=wl)),
                             out)

    @registry.command(
        "tables.tabesb.export", category="export",
        description="TABESB (высоты пучков по поверхностям) → CSV/JSON/TXT",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def tables_tabesb_export(ctx, file, system, lbo_index, lbo_name,
                             field_y, wl, out):
        return _export_table(registry, ctx, "beam.heights",
                             _source_args(dict(file=file, system=system,
                                               lbo_index=lbo_index,
                                               lbo_name=lbo_name,
                                               field_y=field_y, wl=wl)), out)

    @registry.command(
        "tables.field_zones.export", category="export",
        description="Зоны поля OPAL (относительные высоты) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=[
            Param("n_zones", type="int", default=3, help="число зон"),
            OUT_PARAM,
        ])
    def tables_field_zones_export(ctx, n_zones, out):
        data = _run(registry, ctx, "tables.field_zones",
                    {"n_zones": n_zones})
        zones = data.get("zones")
        if not isinstance(zones, list):
            raise CommandError(
                ERR_UNSUPPORTED,
                "tables.field_zones не возвращает список зон — выгружайте .json")
        rows = [{"zone": i + 1, "relative_height": z}
                for i, z in enumerate(zones)]
        result = write_rows(rows, out)
        result["source"] = "tables.field_zones"
        return result

    # ============================================================
    # Данные расчётов → CSV/JSON
    # ============================================================

    @registry.command(
        "analyze.spot.export", category="export",
        description="Точки точечной диаграммы (мм) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("num_rays", type="int", default=50,
                  help="лучей по стороне сетки / колец"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("sampling", choices=["grid", "hexapolar"],
                  default="grid", help="способ выборки зрачка"),
            OUT_PARAM,
        ])
    def analyze_spot_export(ctx, file, system, lbo_index, lbo_name,
                            wl, num_rays, field_y, sampling, out):
        data = _run(registry, ctx, "analyze.spot",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      wl=wl, num_rays=num_rays,
                                      field_y=field_y, sampling=sampling)))
        rows = [{"x_mm": dx, "y_mm": dy} for dx, dy in data["spots"]]
        result = write_rows(rows, out)
        result["source"] = "analyze.spot"
        result["rms"] = data.get("rms")
        return result

    @registry.command(
        "analyze.ray_fan.export", category="export",
        description="Координаты лучей веера по поверхностям → CSV/JSON "
                    "(§4.7 «Просмотр координат лучей»)",
        returns="файл выгрузки: строка = точка луча на поверхности",
        params=system_source_params() + [
            Param("num_rays", type="int", default=9, help="лучей веера"),
            Param("pupil_range", type="float", default=1.0,
                  help="доля радиуса зрачка"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            OUT_PARAM,
        ])
    def analyze_ray_fan_export(ctx, file, system, lbo_index, lbo_name,
                               num_rays, pupil_range, wl, field_y, out):
        data = _run(registry, ctx, "analyze.ray_fan",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      num_rays=num_rays,
                                      pupil_range=pupil_range, wl=wl,
                                      field_y=field_y)))
        rows = []
        for ray in data["rays"]:
            for i, (x, y, z) in enumerate(ray["path"]):
                rows.append({"pupil_y": ray["pupil_y"], "surface": i,
                             "x": x, "y": y, "z": z,
                             "success": ray["success"]})
        result = write_rows(rows, out)
        result["source"] = "analyze.ray_fan"
        return result

    @registry.command(
        "analyze.field_aberrations.export", category="export",
        description="Внеосевые аберрации по полям → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("fields", type="list",
                  help="список полей (град); по умолчанию — поля системы"),
            Param("num_fan_rays", type="int", default=15,
                  help="лучей в веере на поле"),
            OUT_PARAM,
        ])
    def analyze_field_aberrations_export(ctx, file, system, lbo_index,
                                         lbo_name, wl, fields, num_fan_rays,
                                         out):
        data = _run(registry, ctx, "analyze.field_aberrations",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      wl=wl, fields=fields,
                                      num_fan_rays=num_fan_rays)))
        result = write_rows(data["fields"], out)
        result["source"] = "analyze.field_aberrations"
        return result

    @registry.command(
        "aber.fan.export", category="export",
        description="Веер аберраций (поперечные/волновые по зрачку) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("num_rays", type="int", default=30, help="лучей веера"),
            Param("field_y", type="float", default=0.0, help="поле"),
            OUT_PARAM,
        ])
    def aber_fan_export(ctx, file, system, lbo_index, lbo_name,
                        wl, num_rays, field_y, out):
        data = _run(registry, ctx, "aber.fan",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      wl=wl, num_rays=num_rays,
                                      field_y=field_y)))
        rays = data.get("rays", data.get("rows"))
        if rays is None:
            raise CommandError(
                ERR_UNSUPPORTED,
                "aber.fan не вернул таблицу лучей — выгружайте .json")
        result = write_rows(rays, out)
        result["source"] = "aber.fan"
        return result

    @registry.command(
        "aber.mtf_geo.export", category="export",
        description="Геометрическая ЧКХ [freq, T, S] → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("max_freq", type="float", default=100.0,
                  help="максимальная частота, лин/мм"),
            Param("num_freqs", type="int", default=20, help="число частот"),
            Param("num_rays", type="int", default=100,
                  help="лучей точечной диаграммы"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def aber_mtf_geo_export(ctx, file, system, lbo_index, lbo_name,
                            max_freq, num_freqs, num_rays, field_y, wl, out):
        data = _run(registry, ctx, "aber.mtf_geo",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      max_freq=max_freq,
                                      num_freqs=num_freqs,
                                      num_rays=num_rays, field_y=field_y,
                                      wl=wl)))
        rows = [{"freq_lpmm": f, "mtf_tangential": t, "mtf_sagittal": s}
                for f, t, s in data["mtf"]]
        result = write_rows(rows, out)
        result["source"] = "aber.mtf_geo"
        return result

    @registry.command(
        "zern.coeffs.export", category="export",
        description="Коэффициенты Цернике {n, m, name, coeff} → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("num_rays", type="int", default=64,
                  help="лучей по стороне сетки зрачка"),
            Param("max_order", type="int", default=4,
                  help="максимальный порядок n"),
            Param("defocus_offset", type="float", default=0.0,
                  help="дефокус, длины волн"),
            OUT_PARAM,
        ])
    def zern_coeffs_export(ctx, file, system, lbo_index, lbo_name, wl,
                           field_y, num_rays, max_order, defocus_offset, out):
        data = _run(registry, ctx, "zern.coeffs",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      wl=wl, field_y=field_y,
                                      num_rays=num_rays,
                                      max_order=max_order,
                                      defocus_offset=defocus_offset)))
        result = write_rows(data["coeffs"], out)
        result["source"] = "zern.coeffs"
        return result

    @registry.command(
        "psf.encircled.export", category="export",
        description="ФКЭ ФРТ (r_um, EE) → CSV/JSON",
        returns="файл выгрузки + r50/r80 из команды-источника",
        params=system_source_params() + [
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка, длины волн"),
            OUT_PARAM,
        ])
    def psf_encircled_export(ctx, file, system, lbo_index, lbo_name,
                             field_y, wl, defocus, out):
        data = _run(registry, ctx, "psf.encircled",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      field_y=field_y, wl=wl,
                                      defocus=defocus)))
        result = _export_curves(data, out,
                                {"r_um": "r_um", "ee": "ee"},
                                "psf.encircled")
        result["r50_um"] = data.get("r50_um")
        result["r80_um"] = data.get("r80_um")
        return result

    @registry.command(
        "diffr.mtf.export", category="export",
        description="Дифракционная ЧКХ (частоты + мер/саг срезы) → CSV/JSON",
        returns="файл выгрузки + cutoff из команды-источника",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("grid_size", type="int", default=64,
                  help="решётка зрачка (N×N)"),
            Param("max_freq_lpmm", type="float",
                  help="верхняя частота, лин/мм"),
            OUT_PARAM,
        ])
    def diffr_mtf_export(ctx, file, system, lbo_index, lbo_name, wl,
                         grid_size, max_freq_lpmm, out):
        data = _run(registry, ctx, "diffr.mtf",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      wl=wl, grid_size=grid_size,
                                      max_freq_lpmm=max_freq_lpmm)))
        curves = {"freq_lpmm": "freqs"}
        for col, key in (("mtf_tangential", "mtf_tangential"),
                         ("mtf_sagittal", "mtf_sagittal")):
            if isinstance(data.get(key), list):
                curves[col] = key
        result = _export_curves(data, out, curves, "diffr.mtf")
        if data.get("cutoff_lpmm") is not None:
            result["cutoff_lpmm"] = data["cutoff_lpmm"]
        return result

    @registry.command(
        "adv.lsf.export", category="export",
        description="ФРЛ (профиль по оси, мкм) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("direction", choices=["tangential", "sagittal"],
                  default="tangential", help="направление щели"),
            Param("num_rays", type="int", default=128,
                  help="размер сетки зрачка"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def adv_lsf_export(ctx, file, system, lbo_index, lbo_name, direction,
                       num_rays, field_y, wl, out):
        data = _run(registry, ctx, "adv.lsf",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      direction=direction,
                                      num_rays=num_rays, field_y=field_y,
                                      wl=wl)))
        return _export_curves(data, out, {"x_um": "x_um", "lsf": "lsf"},
                              "adv.lsf")

    @registry.command(
        "adv.enc.export", category="export",
        description="Геометрическая ФКЭ (r_um, доля) → CSV/JSON",
        returns="файл выгрузки + счётчики строк",
        params=system_source_params() + [
            Param("num_rays", type="int", default=200,
                  help="лучей точечной диаграммы"),
            Param("field_y", type="float", default=0.0, help="поле"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def adv_enc_export(ctx, file, system, lbo_index, lbo_name, num_rays,
                       field_y, wl, out):
        data = _run(registry, ctx, "adv.enc",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      num_rays=num_rays, field_y=field_y,
                                      wl=wl)))
        return _export_curves(data, out, {"r_um": "r_um", "enc": "enc"},
                              "adv.enc")

    @registry.command(
        "seidel.sums.export", category="export",
        description="Суммы Зейделя (SI..SV + хроматические) → CSV/JSON",
        returns="файл выгрузки (CSV — одна строка сумм)",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def seidel_sums_export(ctx, file, system, lbo_index, lbo_name, wl, out):
        data = _run(registry, ctx, "seidel.sums",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      wl=wl)))
        return _export_data(data, out, "seidel.sums")

    @registry.command(
        "trace.ray_bundle.export", category="export",
        description="Пучок лучей 3D-сетки зрачка (кольца × азимуты) → "
                    "CSV/JSON (ТЗ §2.4)",
        returns="файл: строка = луч (rho, phi, OPL, точка на образце)",
        params=system_source_params() + [
            Param("num_rings", type="int", default=3, help="колец зрачка"),
            Param("num_azimuths", type="int", default=8,
                  help="азимутов на кольцо"),
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            Param("field_y", type="float", default=0.0, help="поле"),
            OUT_PARAM,
        ])
    def trace_ray_bundle_export(ctx, file, system, lbo_index, lbo_name,
                                num_rings, num_azimuths, wl, field_y, out):
        data = _run(registry, ctx, "trace.grid3d",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      num_rings=num_rings,
                                      num_azimuths=num_azimuths, wl=wl,
                                      field_y=field_y)))
        rows = []
        for ring in data["rings"]:
            for ray in ring:
                last = ray.get("last_point")
                row = {"rho": ray["rho"], "phi_deg": ray["phi_deg"],
                       "success": ray["success"], "opl": ray["opl"]}
                if isinstance(last, (list, tuple)) and len(last) >= 3:
                    row["x"], row["y"], row["z"] = last[0], last[1], last[2]
                rows.append(row)
        result = write_rows(rows, out)
        result["source"] = "trace.grid3d"
        return result

    @registry.command(
        "calc.paraxial.export", category="export",
        description="Параксиальные характеристики → JSON (CSV — строка скаляров)",
        returns="файл выгрузки",
        params=system_source_params() + [
            Param("wl", type="float", help="λ, мкм (по умолчанию — основная)"),
            OUT_PARAM,
        ])
    def calc_paraxial_export(ctx, file, system, lbo_index, lbo_name, wl, out):
        data = _run(registry, ctx, "calc.paraxial",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name,
                                      wl=wl)))
        return _export_data(data, out, "calc.paraxial")

    @registry.command(
        "calc.seidel.export", category="export",
        description="Суммы Зейделя (domain) → JSON (CSV — строка скаляров)",
        returns="файл выгрузки",
        params=system_source_params() + [OUT_PARAM])
    def calc_seidel_export(ctx, file, system, lbo_index, lbo_name, out):
        data = _run(registry, ctx, "calc.seidel",
                    _source_args(dict(file=file, system=system,
                                      lbo_index=lbo_index, lbo_name=lbo_name)))
        return _export_data(data, out, "calc.seidel")
