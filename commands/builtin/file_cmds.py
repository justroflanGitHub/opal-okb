"""
OPAL-OKB — Команды file.*: открытие/сохранение/конвертация файлов систем.

Форматы и диспетчеризация — commands/systemio.py (единственное место).
"""
from commands.base import Param
from commands.registry import Registry
from commands.systemio import (
    FORMATS,
    FORMAT_LBO,
    detect_format,
    lbo_entry_info,
    load_system,
    save_system,
    system_summary,
    system_to_dict,
)


def register(registry: Registry) -> None:
    """Зарегистрировать все команды file.*."""

    @registry.command(
        "file.formats", category="file",
        description="Поддерживаемые форматы файлов оптических систем",
        returns="словарь форматов: расширения, чтение/запись, описание")
    def file_formats(ctx):
        return {"formats": list(FORMATS.values())}

    @registry.command(
        "file.open", category="file",
        description="Загрузить систему из файла (.opj/.lbo/.json) по расширению",
        returns="сериализованная система (+ entries для .lbo)",
        params=[
            Param("file", required=True,
                  help="путь к файлу системы"),
            Param("lbo_index", type="int", default=0,
                  help="индекс записи в .lbo"),
            Param("lbo_name",
                  help="имя .OPJ-записи в .lbo (приоритетнее lbo_index)"),
        ])
    def file_open(ctx, file, lbo_index, lbo_name):
        fmt = detect_format(file)
        if fmt == FORMAT_LBO:
            from commands.systemio import _load_lbo_entries, _pick_lbo_entry
            entries = _load_lbo_entries(file)
            picked = _pick_lbo_entry(entries, lbo_name, lbo_index, file)
            return {
                "format": fmt,
                "file": file,
                "total": len(entries),
                "entries": [lbo_entry_info(e) for e in entries],
                "system": system_to_dict(picked["system"]),
            }
        system = load_system(file, lbo_index=lbo_index, lbo_name=lbo_name)
        return {"format": fmt, "file": file,
                "system": system_to_dict(system)}

    @registry.command(
        "file.save", category="file",
        description="Сохранить систему в файл (формат по расширению цели)",
        returns="путь сохранённого файла и формат",
        params=[
            Param("file", required=True, help="целевой путь (.opj/.json)"),
            Param("src", help="исходный файл системы (.opj/.lbo/.json)"),
            Param("system", help="имя системы в контексте REPL"),
            Param("lbo_index", type="int", default=0, help="индекс записи в .lbo"),
            Param("lbo_name", help="имя .OPJ-записи в .lbo"),
        ])
    def file_save(ctx, file, src, system, lbo_index, lbo_name):
        from commands.systemio import resolve_system
        sys_obj = resolve_system(ctx, file=src, system=system,
                                 lbo_index=lbo_index, lbo_name=lbo_name)
        save_system(sys_obj, file)
        return {"saved": file, "format": detect_format(file),
                "num_surfaces": sys_obj.num_surfaces}

    @registry.command(
        "file.info", category="file",
        description="Информация о файле системы: формат, поверхности, стёкла",
        returns="сводка: формат, имя, счётчики, стёкла",
        params=[
            Param("file", required=True, help="путь к файлу системы"),
            Param("lbo_index", type="int", default=0, help="индекс записи в .lbo"),
            Param("lbo_name", help="имя .OPJ-записи в .lbo"),
        ])
    def file_info(ctx, file, lbo_index, lbo_name):
        fmt = detect_format(file)
        system = load_system(file, lbo_index=lbo_index, lbo_name=lbo_name)
        info = system_summary(system)
        info["format"] = fmt
        info["file"] = file
        return info

    @registry.command(
        "file.convert", category="file",
        description="Конвертировать файл системы (.opj↔.json, .lbo→.json/.opj)",
        returns="пути и форматы конвертации",
        params=[
            Param("src", required=True, help="исходный файл"),
            Param("dst", required=True, help="целевой файл (.opj/.json)"),
            Param("lbo_index", type="int", default=0, help="индекс записи в .lbo"),
            Param("lbo_name", help="имя .OPJ-записи в .lbo"),
        ])
    def file_convert(ctx, src, dst, lbo_index, lbo_name):
        system = load_system(src, lbo_index=lbo_index, lbo_name=lbo_name)
        save_system(system, dst)
        return {
            "src": src, "dst": dst,
            "src_format": detect_format(src),
            "dst_format": detect_format(dst),
            "num_surfaces": system.num_surfaces,
        }
