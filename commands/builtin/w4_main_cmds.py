"""
OPAL-OKB — Команды Волны 4 (src=main): gap-команды главного окна.

Инвентаризация экшенов main.py — docs/tasks/W4_INVENTORY_main.md.
Обёртки по правилам Волны 1: без Qt, JSON-контракт, источники системы —
``system_source_params`` (file/system/REPL-текущая).

Общий хвост мутаций (REPL-семантика): если источник — текущая система
контекста, результат-система заменяет её на месте
(``system.load`` → ``system.reverse`` → ``calc.paraxial``); параметры
``name``/``save`` — как в ``opt.*`` (положить под именем в контекст /
записать в файл по расширению).

Регистрация — лениво через ``gui.cmdbridge.ensure_w4_registered``
(builtin/__init__ не трогается до мержа, правило 5 ТЗ Волны 4).
"""
from typing import Any, List, Optional

from domain.models import FieldPoint, OpticalSystem, Wavelength

from commands.base import (
    ERR_BAD_REQUEST,
    ERR_INVALID_PARAM,
    CommandError,
    Param,
)
from commands.registry import Registry
from commands.systemio import (
    detect_format,
    load_system,
    resolve_system,
    save_system,
    system_source_params,
    system_to_dict,
)

#: Минимальный значимый коэффициент масштабирования (как в UI).
_MIN_SCALE_FACTOR = 1e-15


def _replace_current(ctx, source: OpticalSystem,
                     result_system: OpticalSystem) -> bool:
    """REPL-семантика мутаций: текущая система контекста → замена на месте.

    Источник из ``file=`` (CLI-режим) не заменяется — команда остаётся
    stateless; замена только когда считают систему, живущую в контексте.
    """
    if ctx.current is not None and ctx.current is source \
            and ctx.current_name:
        ctx.put_system(ctx.current_name, result_system)
        return True
    return False


def _mutated(ctx, source: OpticalSystem, result_system: OpticalSystem,
             out: Optional[str], name: Optional[str]) -> dict:
    """Общий хвост мутаций: замена текущей + name/save + сериализация."""
    result = system_to_dict(result_system)
    result["replaced_current"] = _replace_current(ctx, source, result_system)
    if name:
        ctx.put_system(name, result_system)
        result["system"] = name
    if out:
        save_system(result_system, out)
        result["saved"] = out
        result["format"] = detect_format(out)
    return result


def _require_entries(items: Any, param: str, required_field: str,
                     optional: tuple) -> List[dict]:
    """Разобрать список записей вида {required_field, *optional}.

    Raises:
        CommandError: ``invalid_param`` — не список / не объекты /
            отсутствует или нечисловое обязательное поле.
    """
    if not isinstance(items, list):
        raise CommandError(
            ERR_INVALID_PARAM,
            f"{param} — список объектов {{{required_field}, "
            f"{', '.join(optional)}}}")
    out = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise CommandError(
                ERR_INVALID_PARAM,
                f"{param}[{i}]: ожидается объект, получен "
                f"{type(item).__name__}")
        try:
            base = {required_field: float(item[required_field])}
        except (KeyError, TypeError, ValueError) as exc:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"{param}[{i}].{required_field}: обязательное число "
                f"(получено {item.get(required_field)!r})") from exc
        for key in optional:
            value = item.get(key)
            if value is not None:
                try:
                    value = float(value)
                except (TypeError, ValueError) as exc:
                    raise CommandError(
                        ERR_INVALID_PARAM,
                        f"{param}[{i}].{key}: ожидается число "
                        f"(получено {value!r})") from exc
            base[key] = value
        out.append(base)
    return out


def _string_fields(items: Any, param: str, field: str) -> List[str]:
    """Строковые поля записей-объектов (например имя линии λ).

    Дополняет :func:`_require_entries` (числовая валидация) — вызывается
    после неё, когда список уже проверен на «список объектов».
    """
    if not isinstance(items, list):
        return []  # непустой список уже проверен _require_entries
    out = []
    for i, item in enumerate(items):
        value = item.get(field) if isinstance(item, dict) else None
        if value is None:
            out.append("")
        elif isinstance(value, str):
            out.append(value)
        else:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"{param}[{i}].{field}: ожидается строка "
                f"(получено {value!r})")
    return out


def register(registry: Registry) -> None:
    """Зарегистрировать все команды Волны 4 (src=main)."""

    # ----------------------------------------------------------
    # Трансформации системы (меню «Система»)
    # ----------------------------------------------------------

    @registry.command(
        "system.reverse", category="system",
        description="Обернуть систему: поверхности в обратном порядке, "
                    "знаки радиусов — на противоположные, толщины "
                    "перепривязываются, стоп пересчитывается",
        returns="сериализованная обращённая система (+saved при out)",
        params=system_source_params([
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ]))
    def system_reverse(ctx, file, system, lbo_index, lbo_name, name, out):
        from utils.system_utils import reverse_system
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return _mutated(ctx, sys_obj, reverse_system(sys_obj), out, name)

    @registry.command(
        "system.scale", category="system",
        description="Масштабировать линейные размеры системы (R, d, "
                    "полудиаметры, апертура; углы поля не меняются)",
        returns="сериализованная масштабированная система (+saved при out)",
        params=system_source_params([
            Param("factor", type="float", required=True,
                  help="коэффициент масштабирования (≠ 0)"),
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ]))
    def system_scale(ctx, file, system, lbo_index, lbo_name, factor,
                     name, out):
        from utils.system_utils import scale_system
        if abs(factor) < _MIN_SCALE_FACTOR:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"factor={factor!r}: коэффициент масштабирования "
                "не может быть нулевым")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return _mutated(ctx, sys_obj, scale_system(sys_obj, factor),
                        out, name)

    @registry.command(
        "system.radii.changes", category="system",
        description="Предпросмотр приведения радиусов к ГОСТ 1807-75: "
                    "таблица замен (поверхность, старый R, новый R, Δ%)",
        returns="список замен (пустой — всё уже стандартно)",
        params=system_source_params())
    def system_radii_changes(ctx, file, system, lbo_index, lbo_name):
        from utils.system_utils import get_radii_changes
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        changes = get_radii_changes(sys_obj)
        return {"changes": [
            {"index": idx, "old_radius": old_r,
             "new_radius": new_r, "delta_percent": d_pct}
            for idx, old_r, new_r, d_pct in changes],
            "num_changes": len(changes)}

    @registry.command(
        "system.radii.standardize", category="system",
        description="Заменить нестандартные радиусы ближайшими по "
                    "ГОСТ 1807-75 (плоские R=0 не трогаются)",
        returns="сериализованная система со стандартными радиусами "
                "(+saved при out)",
        params=system_source_params([
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ]))
    def system_radii_standardize(ctx, file, system, lbo_index, lbo_name,
                                 name, out):
        from utils.system_utils import standardize_radii
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return _mutated(ctx, sys_obj, standardize_radii(sys_obj), out, name)

    @registry.command(
        "system.append", category="system",
        description="Присоединить систему из файла: поверхности "
                    "добавляются в конец, параметры — от основной "
                    "(имя «A + B»)",
        returns="сериализованная объединённая система (+saved при out)",
        params=system_source_params([
            Param("append", required=True,
                  help="путь к присоединяемой системе (.opj/.lbo/.json)"),
            Param("append_index", type="int", default=0,
                  help="индекс записи .lbo присоединяемой системы"),
            Param("append_name",
                  help="имя .OPJ-записи в .lbo (приоритетнее индекса)"),
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ]))
    def system_append(ctx, file, system, lbo_index, lbo_name, append,
                      append_index, append_name, name, out):
        main = resolve_system(ctx, file, system, lbo_index, lbo_name)
        appended = load_system(append, lbo_index=append_index,
                               lbo_name=append_name)
        # Набор полей — как io_utils/fileio.json_io.append_system (набор
        # полей основной системы + конкатенация поверхностей).
        result = OpticalSystem(
            name=(main.name + " + " + appended.name)
                 if appended.name else main.name,
            object_type=main.object_type,
            object_height=main.object_height,
            aperture_type=main.aperture_type,
            aperture_value=main.aperture_value,
            wavelengths=list(main.wavelengths),
            field_points=list(main.field_points),
            stop_surface=main.stop_surface,
            obscuration_ratio=main.obscuration_ratio,
            comment=main.comment,
        )
        result.surfaces = list(main.surfaces) + list(appended.surfaces)
        return _mutated(ctx, main, result, out, name)

    # ----------------------------------------------------------
    # Генераторы систем
    # ----------------------------------------------------------

    @registry.command(
        "system.achromat", category="system",
        description="Рассчитать ахроматический дублет (f', пара стёкол, "
                    "апертура) — проектор новой системы",
        returns="сериализованная система ахромата (+saved при out)",
        params=[
            Param("focal_length", type="float", required=True,
                  help="фокусное расстояние, мм"),
            Param("crown", default="К8",
                  help="крон (например К8, БК10)"),
            Param("flint", default="ТФ5",
                  help="флинт (например ТФ5, ТФ3, Ф4)"),
            Param("aperture", type="float", default=0.0,
                  help="апертура (входной зрачок, мм); 0 — не задавать"),
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ])
    def system_achromat(ctx, focal_length, crown, flint, aperture, name,
                        out):
        from achromat import design_achromat
        system = design_achromat(focal_length, crown, flint, aperture)
        result = system_to_dict(system)
        if name:
            ctx.put_system(name, system)
            result["system"] = name
        if out:
            save_system(system, out)
            result["saved"] = out
            result["format"] = detect_format(out)
        return result

    @registry.command(
        "catalog.library.create", category="catalog",
        description="Система из записи библиотеки (catalog/library): "
                    "генератор, standalone .OPJ или запись .LBO",
        returns="сериализованная система (+saved при out)",
        params=[
            Param("generator",
                  help="имя генератора библиотеки (achromat_100, …)"),
            Param("file", help="путь к standalone .OPJ файлу"),
            Param("lbo_path", help="путь к .LBO библиотеке"),
            Param("lbo_filename", help="имя .OPJ-записи внутри .LBO"),
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ])
    def catalog_library_create(ctx, generator, file, lbo_path,
                               lbo_filename, name, out):
        if not (generator or file or (lbo_path and lbo_filename)):
            raise CommandError(
                ERR_BAD_REQUEST,
                "задайте generator, file или пару lbo_path+lbo_filename")
        from catalog.library import create_system_from_entry
        entry = {"generator": generator, "file": file,
                 "lbo_path": lbo_path, "lbo_filename": lbo_filename}
        system = create_system_from_entry(entry)
        result = system_to_dict(system)
        if name:
            ctx.put_system(name, system)
            result["system"] = name
        if out:
            save_system(system, out)
            result["saved"] = out
            result["format"] = detect_format(out)
        return result

    # ----------------------------------------------------------
    # Замена наборов характеристик (меню «Характеристики»)
    # ----------------------------------------------------------

    @registry.command(
        "system.fields.set", category="system",
        description="Заменить весь набор точек поля системы",
        returns="система после замены (+saved при out)",
        params=system_source_params([
            Param("fields", type="list", required=True,
                  help="[{y, x, weight}, …] — y обязательно"),
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ]))
    def system_fields_set(ctx, file, system, lbo_index, lbo_name, fields,
                          name, out):
        entries = _require_entries(fields, "fields", "y",
                                   ("x", "weight"))
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.field_points = [
            FieldPoint(y=e["y"],
                       x=e["x"] if e["x"] is not None else 0.0,
                       weight=e["weight"] if e["weight"] is not None else 1.0)
            for e in entries]
        return _mutated(ctx, sys_obj, sys_obj, out, name)

    @registry.command(
        "system.wavelengths.set", category="system",
        description="Заменить весь набор рабочих длин волн системы",
        returns="система после замены (+saved при out)",
        params=system_source_params([
            Param("wavelengths", type="list", required=True,
                  help="[{value, weight, name}, …] — value обязательно, "
                       "name — имя спектральной линии"),
            Param("name", help="результат — в контекст REPL под именем"),
            Param("out", help="сохранить результат по расширению пути"),
        ]))
    def system_wavelengths_set(ctx, file, system, lbo_index, lbo_name,
                               wavelengths, name, out):
        entries = _require_entries(wavelengths, "wavelengths", "value",
                                   ("weight",))
        line_names = _string_fields(wavelengths, "wavelengths", "name")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.wavelengths = [
            Wavelength(value=e["value"],
                       weight=e["weight"] if e["weight"] is not None else 1.0,
                       name=nm)
            for e, nm in zip(entries, line_names)]
        return _mutated(ctx, sys_obj, sys_obj, out, name)

    # ----------------------------------------------------------
    # Экспорт протокола (меню «Файл»)
    # ----------------------------------------------------------

    @registry.command(
        "file.export.protocol", category="file",
        description="Экспорт протокола расчёта в .txt: параксиальные "
                    "характеристики, суммы Зейделя, таблица поверхностей",
        returns="путь сохранённого протокола + сводка",
        params=system_source_params([
            Param("out", required=True,
                  help="целевой путь протокола (.txt)"),
        ]))
    def file_export_protocol(ctx, file, system, lbo_index, lbo_name, out):
        from domain.calculations import (
            paraxial_trace,
            seidel_aberrations,
        )
        from fileio.protocol import export_protocol
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        parax = paraxial_trace(sys_obj)
        seidel = seidel_aberrations(sys_obj)
        try:
            export_protocol(sys_obj, parax, seidel, out)
        except OSError as exc:
            from commands.base import ERR_IO_ERROR
            raise CommandError(ERR_IO_ERROR, f"{out}: {exc}") from exc
        return {"saved": out, "name": sys_obj.name,
                "focal_length": parax.get("focal_length"),
                "num_surfaces": sys_obj.num_surfaces}
