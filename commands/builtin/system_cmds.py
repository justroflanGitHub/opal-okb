"""
OPAL-OKB — Команды system.*: создание, просмотр и правка систем.

CLI — stateless: источник системы задаётся параметром ``file``/``system``
(или ``save``/``out`` для записи результата). REPL держит контекст:
``system.load`` загружает систему по имени, команды без явного источника
работают с текущей; мутации применяются к объекту в контексте на месте.
"""
import os

from domain.models import (
    FieldPoint,
    OpticalSystem,
    Surface,
    SurfaceType,
    create_demo_system,
    create_demo_system_by_name,
)

from commands.base import (
    ERR_INVALID_PARAM,
    ERR_NOT_FOUND,
    Param,
    CommandError,
)
from commands.registry import Registry
from commands.systemio import (
    detect_format,
    load_system,
    resolve_system,
    save_system,
    surface_to_dict,
    system_summary,
    system_to_dict,
    system_source_params,
)

#: Демо-системы для system.new (фабрики domain/models.py).
DEMO_CHOICES = ("default", "empty", "achromat", "cook_doublet",
                "telephoto", "petzval", "mirror", "meniscus",
                "plano_convex")

#: Типы поверхностей (для параметров surface_type).
SURFACE_TYPE_CHOICES = tuple(t.name for t in SurfaceType)

#: Поля поверхности, доступные командам правки:
#: параметр → (атрибут Surface, тип параметра).
SURFACE_FIELDS = (
    ("radius", "radius", "float"),
    ("thickness", "thickness", "float"),
    ("glass", "glass", "str"),
    ("semi_diameter", "semi_diameter", "float"),
    ("surface_type", "surface_type", "str"),
    ("conic_constant", "conic_constant", "float"),
    ("is_reflective", "is_reflective", "bool"),
    ("tilt_x", "tilt_x", "float"),
    ("tilt_y", "tilt_y", "float"),
    ("tilt_z", "tilt_z", "float"),
    ("decenter_x", "decenter_x", "float"),
    ("decenter_y", "decenter_y", "float"),
)


def _surface_field_params(include_glass: bool = True) -> list:
    """Параметры-поля поверхности для схем команд правки."""
    params = []
    for pname, attr, ptype in SURFACE_FIELDS:
        if attr == "glass" and not include_glass:
            continue
        choices = SURFACE_TYPE_CHOICES if attr == "surface_type" else None
        params.append(Param(pname, type=ptype, choices=choices,
                            help=f"атрибут Surface.{attr}"))
    return params


def _get_surface(system: OpticalSystem, index: int) -> Surface:
    """Поверхность по индексу (0-based, как в system_to_dict)."""
    if not (0 <= index < system.num_surfaces):
        raise CommandError(
            ERR_INVALID_PARAM,
            f"index={index} вне диапазона 0..{system.num_surfaces - 1} "
            f"(система {system.name!r}, {system.num_surfaces} поверхностей)")
    return system.surfaces[index]


def _apply_surface_fields(surface: Surface, kwargs: dict) -> list:
    """Применить переданные поля к поверхности; вернуть список изменённых."""
    changed = []
    for pname, attr, _ptype in SURFACE_FIELDS:
        value = kwargs.get(pname)
        if value is None:
            continue
        if attr == "surface_type":
            value = SurfaceType[value]
        setattr(surface, attr, value)
        changed.append(pname)
    return changed


def _mutated_result(ctx, system: OpticalSystem, out) -> dict:
    """Общий хвост мутаций: опциональное сохранение + сериализация."""
    result = system_to_dict(system)
    if out:
        save_system(system, out)
        result["saved"] = out
        result["format"] = detect_format(out)
    return result


def register(registry: Registry) -> None:
    """Зарегистрировать все команды system.*."""

    @registry.command(
        "system.new", category="system",
        description="Создать новую систему: пустую или демо-генератором",
        returns="сериализованная новая система",
        params=[
            Param("demo", choices=list(DEMO_CHOICES), default="default",
                  help="демо-система: " + ", ".join(DEMO_CHOICES)),
            Param("name", help="имя системы (и ключ в контексте REPL)"),
            Param("save", help="сохранить сразу по расширению пути"),
        ])
    def system_new(ctx, demo, name, save):
        system = _create_new(demo)
        if name:
            system.name = name
            ctx.put_system(name, system)
        result = system_to_dict(system)
        if save:
            save_system(system, save)
            result["saved"] = save
            result["format"] = detect_format(save)
        return result

    @registry.command(
        "system.load", category="system",
        description="REPL: загрузить систему из файла в контекст (сделать текущей)",
        returns="имя в контексте + сериализованная система",
        params=[
            Param("file", required=True, help="путь к файлу системы"),
            Param("name", help="имя в контексте (по умолчанию — имя файла)"),
            Param("lbo_index", type="int", default=0, help="индекс записи в .lbo"),
            Param("lbo_name", help="имя .OPJ-записи в .lbo"),
        ])
    def system_load(ctx, file, name, lbo_index, lbo_name):
        system = load_system(file, lbo_index=lbo_index, lbo_name=lbo_name)
        key = name or os.path.splitext(os.path.basename(file))[0]
        ctx.put_system(key, system)
        return {"name": key, "file": file,
                "system": system_to_dict(system)}

    @registry.command(
        "system.current", category="system",
        description="REPL: текущая система контекста",
        returns="имя + сводка текущей системы",
        params=[])
    def system_current(ctx):
        system = ctx.current
        if system is None:
            raise CommandError(
                ERR_NOT_FOUND,
                "в контексте нет текущей системы; загрузите: system.load")
        info = system_summary(system)
        info["name_in_context"] = ctx.current_name
        info["context_names"] = sorted(ctx.systems)
        return info

    @registry.command(
        "system.info", category="system",
        description="Сводка о системе: апертура, счётчики, стёкла, длины волн",
        returns="сводка системы",
        params=system_source_params())
    def system_info(ctx, file, system, lbo_index, lbo_name):
        return system_summary(
            resolve_system(ctx, file, system, lbo_index, lbo_name))

    @registry.command(
        "system.surfaces.list", category="system",
        description="Список поверхностей системы (полные атрибуты)",
        returns="список словарей поверхностей",
        params=system_source_params())
    def system_surfaces_list(ctx, file, system, lbo_index, lbo_name):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"surfaces": [surface_to_dict(i, s) for i, s
                             in enumerate(sys_obj.surfaces)],
                "num_surfaces": sys_obj.num_surfaces}

    @registry.command(
        "system.surface.add", category="system",
        description="Добавить поверхность (в конец или по индексу вставки)",
        returns="система после добавления (+saved при out)",
        params=system_source_params() + _surface_field_params() + [
            Param("index", type="int",
                  help="индекс вставки (0-based); по умолчанию — в конец"),
            Param("out", help="сохранить результат по расширению пути"),
        ])
    def system_surface_add(ctx, file, system, lbo_index, lbo_name,
                           radius, thickness, glass, semi_diameter,
                           surface_type, conic_constant, is_reflective,
                           tilt_x, tilt_y, tilt_z, decenter_x, decenter_y,
                           index, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        kwargs = dict(radius=radius, thickness=thickness, glass=glass,
                      semi_diameter=semi_diameter,
                      surface_type=surface_type,
                      conic_constant=conic_constant,
                      is_reflective=is_reflective,
                      tilt_x=tilt_x, tilt_y=tilt_y, tilt_z=tilt_z,
                      decenter_x=decenter_x, decenter_y=decenter_y)
        surface = Surface()
        _apply_surface_fields(surface, kwargs)
        if index is None:
            sys_obj.surfaces.append(surface)
        else:
            if not (0 <= index <= sys_obj.num_surfaces):
                raise CommandError(
                    ERR_INVALID_PARAM,
                    f"index={index} вне диапазона вставки "
                    f"0..{sys_obj.num_surfaces}")
            sys_obj.surfaces.insert(index, surface)
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.surface.set", category="system",
        description="Изменить атрибуты поверхности по индексу (0-based)",
        returns="система после правки (+saved при out)",
        params=system_source_params() + _surface_field_params() + [
            Param("index", type="int", required=True,
                  help="индекс поверхности (0-based)"),
            Param("out", help="сохранить результат по расширению пути"),
        ])
    def system_surface_set(ctx, file, system, lbo_index, lbo_name,
                           radius, thickness, glass, semi_diameter,
                           surface_type, conic_constant, is_reflective,
                           tilt_x, tilt_y, tilt_z, decenter_x, decenter_y,
                           index, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        surface = _get_surface(sys_obj, index)
        kwargs = dict(radius=radius, thickness=thickness, glass=glass,
                      semi_diameter=semi_diameter,
                      surface_type=surface_type,
                      conic_constant=conic_constant,
                      is_reflective=is_reflective,
                      tilt_x=tilt_x, tilt_y=tilt_y, tilt_z=tilt_z,
                      decenter_x=decenter_x, decenter_y=decenter_y)
        changed = _apply_surface_fields(surface, kwargs)
        if not changed:
            raise CommandError(
                ERR_INVALID_PARAM,
                "не задано ни одного изменяемого поля поверхности")
        result = _mutated_result(ctx, sys_obj, out)
        result["changed"] = changed
        return result

    @registry.command(
        "system.surface.remove", category="system",
        description="Удалить поверхность по индексу (0-based)",
        returns="система после удаления (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс поверхности (0-based)"),
            Param("out", help="сохранить результат по расширению пути"),
        ])
    def system_surface_remove(ctx, file, system, lbo_index, lbo_name,
                              index, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        _get_surface(sys_obj, index)  # валидация индекса
        del sys_obj.surfaces[index]
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.fields.list", category="system",
        description="Список точек поля системы",
        returns="список {y, x, weight}",
        params=system_source_params())
    def system_fields_list(ctx, file, system, lbo_index, lbo_name):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"fields": [{"y": fp.y, "x": fp.x, "weight": fp.weight}
                           for fp in sys_obj.field_points],
                "num_fields": len(sys_obj.field_points)}

    @registry.command(
        "system.fields.add", category="system",
        description="Добавить точку поля (y — градусы для INFINITE / мм)",
        returns="система после добавления (+saved при out)",
        params=system_source_params() + [
            Param("y", type="float", required=True,
                  help="координата поля (град/мм)"),
            Param("x", type="float", default=0.0, help="2D-координата X"),
            Param("weight", type="float", default=1.0, help="вес"),
            Param("out", help="сохранить результат по расширению пути"),
        ])
    def system_fields_add(ctx, file, system, lbo_index, lbo_name,
                          y, x, weight, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.field_points.append(FieldPoint(y=y, x=x, weight=weight))
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.wavelengths.list", category="system",
        description="Список рабочих длин волн системы",
        returns="список {value, weight, name}",
        params=system_source_params())
    def system_wavelengths_list(ctx, file, system, lbo_index, lbo_name):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"wavelengths": [{"value": wl.value, "weight": wl.weight,
                                 "name": wl.name}
                                for wl in sys_obj.wavelengths],
                "num_wavelengths": len(sys_obj.wavelengths)}

    @registry.command(
        "system.wavelengths.add", category="system",
        description="Добавить рабочую длину волны (мкм)",
        returns="система после добавления (+saved при out)",
        params=system_source_params() + [
            Param("value", type="float", required=True,
                  help="длина волны, мкм"),
            Param("weight", type="float", default=1.0, help="вес"),
            Param("name", default="", help="имя спектральной линии"),
            Param("out", help="сохранить результат по расширению пути"),
        ])
    def system_wavelengths_add(ctx, file, system, lbo_index, lbo_name,
                               value, weight, name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        from domain.models import Wavelength
        sys_obj.wavelengths.append(
            Wavelength(value=value, weight=weight, name=name))
        return _mutated_result(ctx, sys_obj, out)


def _create_new(demo: str) -> OpticalSystem:
    """Фабрика новых систем по имени демо (валидация choices — в реестре)."""
    if demo == "empty":
        return OpticalSystem()
    if demo == "default":
        return create_demo_system()
    return create_demo_system_by_name(demo)
