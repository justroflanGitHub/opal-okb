"""
OPAL-OKB — Пакет R500-2: расширенные команды system.*.

Источник — ТЗ TASK_REGISTRY_500 §2 (UI-инвентарь/справочник/сервис):

- менеджмент контекста REPL: ``system.list/select/drop/clone/rename``;
- скалярные поля системы (``*.set``): имя, комментарий, объект/изображение,
  диафрагма, экранирование, режим пучка, апертура;
- пересчёты апертуры (``domain/aperture.py`` — все 7 способов задания);
- поверхности: get/duplicate/move, асферика, переопределение n;
- поля и длины волн: remove/clear/weight/auto/primary;
- стёкла системы: список/замена марки;
- ``system.validate`` — санити-проверки (ТЗ §2.4).

Мутации используют хелперы system_cmds (``_get_surface`` /
``_mutated_result``) — общее не дублируется.
"""
import copy

from commands.base import ERR_INVALID_PARAM, Param, CommandError
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
    system_to_dict,
)

from commands.builtin.system_cmds import (
    _get_surface,
    _mutated_result,
)

from domain.models import ApertureType, ObjectType

#: Выборы enum-параметров.
OBJECT_TYPE_CHOICES = tuple(t.name for t in ObjectType)
APERTURE_TYPE_CHOICES = tuple(t.name for t in ApertureType)
STOP_TYPE_CHOICES = ("d", "z", "p")
BEAM_MODE_CHOICES = ("real", "given")

#: Диапазон длин волн, мкм (санити system.validate).
WL_MIN_UM = 0.1
WL_MAX_UM = 30.0

#: Параметр «сохранить результат» (общий хвост мутаций).
OUT_SAVE_PARAM = Param("out", help="сохранить результат по расширению пути")


def _invalid(name: str, value) -> CommandError:
    """invalid_param для одного параметра."""
    return CommandError(
        ERR_INVALID_PARAM,
        f"параметр {name!r}: недопустимое значение {value!r}")


def _range_error(index: int, length: int, what: str) -> CommandError:
    """invalid_param: индекс вне диапазона."""
    return CommandError(
        ERR_INVALID_PARAM,
        f"index={index} вне диапазона 0..{length - 1} ({what})")


def _get_index(items: list, index: int, what: str):
    """Элемент по индексу с валидацией (поля/λ)."""
    if not (0 <= index < len(items)):
        raise _range_error(index, len(items), what)
    return items[index]


def _pop_index(items: list, index: int, what: str):
    """Удалить элемент по индексу с валидацией; вернуть удалённый."""
    _get_index(items, index, what)
    return items.pop(index)


def register(registry: Registry) -> None:
    """Зарегистрировать расширенные команды system.* (R500-2)."""

    # ============================================================
    # Контекст REPL
    # ============================================================

    @registry.command(
        "system.list", category="system",
        description="REPL: системы в контексте (имена + счётчики, текущая)",
        returns="{current, systems: [{name, num_surfaces, num_wavelengths}]}",
        params=[])
    def system_list(ctx):
        systems = []
        for name in sorted(ctx.systems):
            s = ctx.systems[name]
            systems.append({"name": name,
                            "num_surfaces": s.num_surfaces,
                            "num_wavelengths": len(s.wavelengths),
                            "num_fields": len(s.field_points)})
        return {"current": ctx.current_name, "systems": systems,
                "count": len(systems)}

    @registry.command(
        "system.select", category="system",
        description="REPL: сделать систему текущей по имени контекста",
        returns="{current, num_surfaces}",
        params=[Param("name", required=True, help="имя в контексте")])
    def system_select(ctx, name):
        system = ctx.get_system(name)  # not_found если нет
        ctx.put_system(name, system, make_current=True)
        return {"current": name, "num_surfaces": system.num_surfaces}

    @registry.command(
        "system.drop", category="system",
        description="REPL: удалить систему из контекста (текущая — сброс "
                    "current); идемпотентно",
        returns="{dropped, current}",
        params=[Param("name", required=True, help="имя в контексте")])
    def system_drop(ctx, name):
        dropped = name in ctx.systems
        ctx.drop_system(name)
        return {"dropped": dropped, "current": ctx.current_name}

    @registry.command(
        "system.clone", category="system",
        description="Копия системы под новым именем в контексте (глубокая)",
        returns="сериализованная копия (+saved при out)",
        params=system_source_params() + [
            Param("name", required=True, help="имя копии в контексте"),
            OUT_SAVE_PARAM,
        ])
    def system_clone(ctx, file, system, lbo_index, lbo_name, name, out):
        src = resolve_system(ctx, file, system, lbo_index, lbo_name)
        clone = copy.deepcopy(src)
        clone.name = name
        ctx.put_system(name, clone)
        result = _mutated_result(ctx, clone, out)
        result["cloned_from"] = src.name
        return result

    @registry.command(
        "system.rename", category="system",
        description="Переименовать систему (атрибут name + ключ контекста)",
        returns="{name, old_name} (+saved при out)",
        params=system_source_params() + [
            Param("name", required=True, help="новое имя системы"),
            OUT_SAVE_PARAM,
        ])
    def system_rename(ctx, file, system, lbo_index, lbo_name, name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        old = sys_obj.name
        sys_obj.name = name
        for key, obj in list(ctx.systems.items()):
            if obj is sys_obj:
                ctx.drop_system(key)
                ctx.put_system(name, sys_obj)
        result = _mutated_result(ctx, sys_obj, out)
        result["old_name"] = old
        return result

    # ============================================================
    # Скалярные поля системы
    # ============================================================

    @registry.command(
        "system.name.set", category="system",
        description="Задать имя системы",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("name", required=True, help="новое имя"),
            OUT_SAVE_PARAM,
        ])
    def system_name_set(ctx, file, system, lbo_index, lbo_name, name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.name = name
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.comment.set", category="system",
        description="Задать комментарий системы",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("comment", required=True, help="текст комментария"),
            OUT_SAVE_PARAM,
        ])
    def system_comment_set(ctx, file, system, lbo_index, lbo_name,
                           comment, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.comment = comment
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.object.set", category="system",
        description="Задать положение предмета: тип (FINITE/INFINITE), "
                    "высоту и расстояние",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("object_type", choices=list(OBJECT_TYPE_CHOICES),
                  help="FINITE — конечное расстояние, INFINITE — ∞"),
            Param("object_height", type="float", help="высота предмета, мм"),
            Param("object_distance", type="float",
                  help="расстояние до 1-й поверхности, мм"),
            OUT_SAVE_PARAM,
        ])
    def system_object_set(ctx, file, system, lbo_index, lbo_name,
                          object_type, object_height, object_distance, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        changed = []
        if object_type is not None:
            sys_obj.object_type = ObjectType[object_type]
            changed.append("object_type")
        if object_height is not None:
            sys_obj.object_height = object_height
            changed.append("object_height")
        if object_distance is not None:
            sys_obj.object_distance = object_distance
            changed.append("object_distance")
        if not changed:
            raise _invalid("object", "не задано ни одного поля")
        result = _mutated_result(ctx, sys_obj, out)
        result["changed"] = changed
        return result

    @registry.command(
        "system.image.set", category="system",
        description="Задать положение изображения (FINITE/INFINITE)",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("image_type", choices=list(OBJECT_TYPE_CHOICES),
                  required=True, help="FINITE / INFINITE"),
            OUT_SAVE_PARAM,
        ])
    def system_image_set(ctx, file, system, lbo_index, lbo_name,
                         image_type, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.image_type = ObjectType[image_type]
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.stop.set", category="system",
        description="Задать апертурную диафрагму: поверхность, отступ, тип",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("stop_surface", type="int",
                  help="номер поверхности диафрагмы (0-based)"),
            Param("stop_offset", type="float",
                  help="отступ диафрагмы от поверхности, мм"),
            Param("stop_type", choices=list(STOP_TYPE_CHOICES),
                  help="d — диафрагма, z/p — зрачок"),
            OUT_SAVE_PARAM,
        ])
    def system_stop_set(ctx, file, system, lbo_index, lbo_name,
                        stop_surface, stop_offset, stop_type, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        changed = []
        if stop_surface is not None:
            if not (0 <= stop_surface < sys_obj.num_surfaces):
                raise _range_error(stop_surface,
                                         sys_obj.num_surfaces,
                                         "stop_surface")
            sys_obj.stop_surface = stop_surface
            changed.append("stop_surface")
        if stop_offset is not None:
            sys_obj.stop_offset = stop_offset
            changed.append("stop_offset")
        if stop_type is not None:
            sys_obj.stop_type = stop_type
            changed.append("stop_type")
        if not changed:
            raise _invalid("stop", "не задано ни одного поля")
        result = _mutated_result(ctx, sys_obj, out)
        result["changed"] = changed
        return result

    @registry.command(
        "system.obscuration.set", category="system",
        description="Задать центральное экранирование (доля 0..1)",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("obscuration_ratio", type="float", required=True,
                  help="отношение диаметров экранирования/зрачка, 0..1"),
            OUT_SAVE_PARAM,
        ])
    def system_obscuration_set(ctx, file, system, lbo_index, lbo_name,
                               obscuration_ratio, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if not (0.0 <= obscuration_ratio < 1.0):
            raise _invalid("obscuration_ratio",
                                       obscuration_ratio)
        sys_obj.obscuration_ratio = obscuration_ratio
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.beam.set", category="system",
        description="Задать режим габаритов пучка: real/given + острая "
                    "кромка",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("beam_mode", choices=list(BEAM_MODE_CHOICES),
                  help="real — реальная трассировка, given — заданные "
                       "полудиаметры"),
            Param("sharp_edge", type="bool",
                  help="острая кромка ( виньетирование по краю)"),
            OUT_SAVE_PARAM,
        ])
    def system_beam_set(ctx, file, system, lbo_index, lbo_name,
                        beam_mode, sharp_edge, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        changed = []
        if beam_mode is not None:
            sys_obj.beam_mode = beam_mode
            changed.append("beam_mode")
        if sharp_edge is not None:
            sys_obj.sharp_edge = sharp_edge
            changed.append("sharp_edge")
        if not changed:
            raise _invalid("beam", "не задано ни одного поля")
        result = _mutated_result(ctx, sys_obj, out)
        result["changed"] = changed
        return result

    @registry.command(
        "system.aperture.set", category="system",
        description="Задать апертуру: способ (7 типов) + значение",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("aperture_type", choices=list(APERTURE_TYPE_CHOICES),
                  help="способ задания апертуры"),
            Param("aperture_value", type="float", required=True,
                  help="значение в единицах способа"),
            OUT_SAVE_PARAM,
        ])
    def system_aperture_set(ctx, file, system, lbo_index, lbo_name,
                            aperture_type, aperture_value, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if aperture_value <= 0:
            raise _invalid("aperture_value", aperture_value)
        if aperture_type is not None:
            sys_obj.aperture_type = ApertureType[aperture_type]
        sys_obj.aperture_value = aperture_value
        return _mutated_result(ctx, sys_obj, out)

    # ============================================================
    # Пересчёты апертуры (domain/aperture.py)
    # ============================================================

    @registry.command(
        "system.aperture.convert", category="system",
        description="Апертуру из любого способа — во все представления "
                    "(канон: диаметр входного зрачка)",
        returns="{epd, entrance_pupil, f_number, ...} (мм / безразмерные)",
        params=system_source_params() + [
            Param("value", type="float", required=True,
                  help="значение апертуры"),
            Param("from_type", choices=list(APERTURE_TYPE_CHOICES),
                  default="ENTRANCE_PUPIL", help="исходный способ задания"),
        ])
    def system_aperture_convert(ctx, file, system, lbo_index, lbo_name,
                                value, from_type):
        from domain.aperture import convert_aperture
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        result = convert_aperture(sys_obj, value, ApertureType[from_type])
        result["from_type"] = from_type
        result["value"] = value
        return result

    @registry.command(
        "system.aperture.epd", category="system",
        description="Диаметр входного зрачка для текущей апертуры системы",
        returns="{epd, aperture_type, aperture_value} (мм)",
        params=system_source_params())
    def system_aperture_epd(ctx, file, system, lbo_index, lbo_name):
        from domain.aperture import aperture_to_epd
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        epd = aperture_to_epd(sys_obj, sys_obj.aperture_value,
                              sys_obj.aperture_type)
        return {"epd": epd, "aperture_type": sys_obj.aperture_type.name,
                "aperture_value": sys_obj.aperture_value}

    @registry.command(
        "system.aperture.from_epd", category="system",
        description="Все представления осевого пучка по диаметру входного "
                    "зрачка",
        returns="{entrance_pupil, f_number, numerical_aperture, ...}",
        params=system_source_params() + [
            Param("epd", type="float", required=True,
                  help="диаметр входного зрачка, мм"),
        ])
    def system_aperture_from_epd(ctx, file, system, lbo_index, lbo_name,
                                 epd):
        from domain.aperture import epd_to_apertures
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        by_type = epd_to_apertures(sys_obj, epd)
        return {"epd": epd,
                **{t.name.lower(): v for t, v in by_type.items()}}

    @registry.command(
        "system.aperture.pupil_distance", category="system",
        description="Путь осевого луча от предмета до входного зрачка "
                    "(только FINITE-предмет)",
        returns="{distance: float|None, object_type} (мм)",
        params=system_source_params())
    def system_aperture_pupil_distance(ctx, file, system, lbo_index,
                                       lbo_name):
        from domain.aperture import object_to_pupil_distance
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"distance": object_to_pupil_distance(sys_obj),
                "object_type": sys_obj.object_type.name}

    # ============================================================
    # Поверхности: точечные операции
    # ============================================================

    @registry.command(
        "system.surface.get", category="system",
        description="Полные атрибуты поверхности по индексу (0-based)",
        returns="словарь поверхности",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс поверхности (0-based)"),
        ])
    def system_surface_get(ctx, file, system, lbo_index, lbo_name, index):
        from commands.systemio import surface_to_dict
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        surface = _get_surface(sys_obj, index)
        return surface_to_dict(index, surface)

    @registry.command(
        "system.surface.duplicate", category="system",
        description="Дублировать поверхность count раз (вставка после)",
        returns="система после вставки (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс поверхности (0-based)"),
            Param("count", type="int", default=1, help="число копий"),
            OUT_SAVE_PARAM,
        ])
    def system_surface_duplicate(ctx, file, system, lbo_index, lbo_name,
                                 index, count, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        surface = _get_surface(sys_obj, index)
        if count < 1:
            raise _invalid("count", count)
        for _ in range(count):
            sys_obj.surfaces.insert(index + 1, copy.deepcopy(surface))
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.surface.move", category="system",
        description="Переставить поверхность на новую позицию (0-based)",
        returns="система после перестановки (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="откуда (0-based)"),
            Param("to", type="int", required=True, help="куда (0-based)"),
            OUT_SAVE_PARAM,
        ])
    def system_surface_move(ctx, file, system, lbo_index, lbo_name,
                            index, to, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        surface = _get_surface(sys_obj, index)
        if not (0 <= to < sys_obj.num_surfaces):
            raise _range_error(to, sys_obj.num_surfaces, "to")
        sys_obj.surfaces.insert(to, sys_obj.surfaces.pop(index))
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.surface.aspheric.set", category="system",
        description="Задать коэффициенты асферики поверхности "
                    "(A4, A6, ...; тип — ASPHERIC)",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс поверхности (0-based)"),
            Param("coeffs", type="list", required=True,
                  help="коэффициенты [A4, A6, ...]"),
            Param("set_type", type="bool", default=True,
                  help="установить surface_type=ASPHERIC"),
            OUT_SAVE_PARAM,
        ])
    def system_surface_aspheric_set(ctx, file, system, lbo_index, lbo_name,
                                    index, coeffs, set_type, out):
        from domain.models import SurfaceType
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        surface = _get_surface(sys_obj, index)
        surface.aspheric_coeffs = [float(c) for c in coeffs]
        if set_type:
            surface.surface_type = SurfaceType.ASPHERIC
        result = _mutated_result(ctx, sys_obj, out)
        result["changed"] = ["aspheric_coeffs"]
        return result

    @registry.command(
        "system.surface.n.set", category="system",
        description="Переопределить показатели преломления поверхности: "
                    "{λ мкм: n} вместо каталога стёкол",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс поверхности (0-based)"),
            Param("n_override", type="dict", required=True,
                  help="словарь {длина волны мкм: показатель n}"),
            OUT_SAVE_PARAM,
        ])
    def system_surface_n_set(ctx, file, system, lbo_index, lbo_name, index,
                             n_override, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        surface = _get_surface(sys_obj, index)
        surface.n_override = {float(k): float(v)
                              for k, v in n_override.items()}
        result = _mutated_result(ctx, sys_obj, out)
        result["changed"] = ["n_override"]
        return result

    # ============================================================
    # Поля и длины волн
    # ============================================================

    @registry.command(
        "system.fields.remove", category="system",
        description="Удалить точку поля по индексу",
        returns="система после удаления (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс точки поля (0-based)"),
            OUT_SAVE_PARAM,
        ])
    def system_fields_remove(ctx, file, system, lbo_index, lbo_name,
                             index, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        removed = _pop_index(sys_obj.field_points, index, "точки поля")
        result = _mutated_result(ctx, sys_obj, out)
        result["removed"] = {"y": removed.y, "x": removed.x}
        return result

    @registry.command(
        "system.fields.clear", category="system",
        description="Удалить все точки поля",
        returns="система после очистки (+saved при out)",
        params=system_source_params() + [OUT_SAVE_PARAM])
    def system_fields_clear(ctx, file, system, lbo_index, lbo_name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.field_points.clear()
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.fields.auto", category="system",
        description="Задать точки поля автоматически: зоны поля системы "
                    "(0, ..., max)",
        returns="система после установки (+saved при out)",
        params=system_source_params() + [
            Param("num_fields", type="int", default=5,
                  help="число точек поля (включая осевую)"),
            OUT_SAVE_PARAM,
        ])
    def system_fields_auto(ctx, file, system, lbo_index, lbo_name,
                           num_fields, out):
        from analysis.aberrations import analysis_field_points
        from domain.models import FieldPoint
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        values = analysis_field_points(sys_obj, num_fields=num_fields)
        sys_obj.field_points = [FieldPoint(y=v) for v in values]
        result = _mutated_result(ctx, sys_obj, out)
        result["field_values"] = values
        return result

    @registry.command(
        "system.fields.weight.set", category="system",
        description="Задать вес точки поля по индексу",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс точки поля (0-based)"),
            Param("weight", type="float", required=True, help="вес"),
            OUT_SAVE_PARAM,
        ])
    def system_fields_weight_set(ctx, file, system, lbo_index, lbo_name,
                                 index, weight, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        _get_index(sys_obj.field_points, index, "точки поля").weight = weight
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.wavelengths.remove", category="system",
        description="Удалить рабочую длину волны по индексу",
        returns="система после удаления (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True,
                  help="индекс λ (0-based)"),
            OUT_SAVE_PARAM,
        ])
    def system_wavelengths_remove(ctx, file, system, lbo_index, lbo_name,
                                  index, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        removed = _pop_index(sys_obj.wavelengths, index, "длины волн")
        result = _mutated_result(ctx, sys_obj, out)
        result["removed"] = {"value": removed.value, "name": removed.name}
        return result

    @registry.command(
        "system.wavelengths.clear", category="system",
        description="Удалить все рабочие длины волн",
        returns="система после очистки (+saved при out)",
        params=system_source_params() + [OUT_SAVE_PARAM])
    def system_wavelengths_clear(ctx, file, system, lbo_index, lbo_name,
                                 out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        sys_obj.wavelengths.clear()
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.wavelengths.weight.set", category="system",
        description="Задать вес длины волны по индексу",
        returns="система после правки (+saved при out)",
        params=system_source_params() + [
            Param("index", type="int", required=True, help="индекс λ (0-based)"),
            Param("weight", type="float", required=True, help="вес"),
            OUT_SAVE_PARAM,
        ])
    def system_wavelengths_weight_set(ctx, file, system, lbo_index,
                                      lbo_name, index, weight, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        _get_index(sys_obj.wavelengths, index,
                   "длины волн").weight = weight
        return _mutated_result(ctx, sys_obj, out)

    @registry.command(
        "system.wavelengths.primary", category="system",
        description="Основная длина волны системы (расчёты по умолчанию)",
        returns="{value, name} (мкм)",
        params=system_source_params())
    def system_wavelengths_primary(ctx, file, system, lbo_index, lbo_name):
        from optics_utils import get_primary_wl
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if not sys_obj.wavelengths:
            raise _invalid("wavelengths", "список длин волн пуст")
        value = get_primary_wl(sys_obj)
        name = next((w.name for w in sys_obj.wavelengths
                     if abs(w.value - value) < 1e-12), "")
        return {"value": value, "name": name}

    # ============================================================
    # Стёкла системы
    # ============================================================

    @registry.command(
        "system.glasses.list", category="system",
        description="Уникальные стёкла системы + где используются",
        returns="список {glass, surfaces: [индексы]}",
        params=system_source_params())
    def system_glasses_list(ctx, file, system, lbo_index, lbo_name):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        where = {}
        for i, s in enumerate(sys_obj.surfaces):
            if s.glass:
                where.setdefault(s.glass, []).append(i)
        return {"glasses": [{"glass": g, "surfaces": idxs}
                            for g, idxs in sorted(where.items())],
                "count": len(where)}

    @registry.command(
        "system.glasses.replace", category="system",
        description="Заменить марку стекла во всех поверхностях "
                    "(стекло-источник удаляется полностью)",
        returns="система после замены (+saved при out)",
        params=system_source_params() + [
            Param("old", required=True, help="заменяемая марка"),
            Param("new", required=True, help="новая марка"),
            OUT_SAVE_PARAM,
        ])
    def system_glasses_replace(ctx, file, system, lbo_index, lbo_name,
                               old, new, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        changed = 0
        for s in sys_obj.surfaces:
            if s.glass == old:
                s.glass = new
                changed += 1
        result = _mutated_result(ctx, sys_obj, out)
        result["changed_surfaces"] = changed
        return result

    # ============================================================
    # Санити
    # ============================================================

    @registry.command(
        "system.validate", category="system",
        description="Санити-проверки системы: структура, апертура, поля, "
                    "λ, стёкла (в каталогах), параксиальный расчёт",
        returns="{valid, errors: [...], warnings: [...], checks}",
        params=system_source_params())
    def system_validate(ctx, file, system, lbo_index, lbo_name):
        from commands.builtin.catalog_cmds import lookup_glass
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        errors, warnings = [], []

        if sys_obj.num_surfaces == 0:
            errors.append("система без поверхностей")
        if not sys_obj.wavelengths:
            errors.append("нет рабочих длин волн")
        else:
            bad = [w.value for w in sys_obj.wavelengths
                   if not (WL_MIN_UM <= w.value <= WL_MAX_UM)]
            if bad:
                errors.append(f"λ вне {WL_MIN_UM}..{WL_MAX_UM} мкм: {bad}")
        if not sys_obj.field_points:
            warnings.append("нет точек поля (расчёты по полю невозможны)")
        elif not any(abs(fp.y) < 1e-12 for fp in sys_obj.field_points):
            warnings.append("нет осевой точки поля (y=0)")

        for i, s in enumerate(sys_obj.surfaces):
            if s.semi_diameter <= 0:
                warnings.append(f"поверхность {i}: semi_diameter<=0")
            if s.thickness < 0 and i < sys_obj.num_surfaces - 1:
                warnings.append(f"поверхность {i}: thickness<0")
            if s.glass and lookup_glass(s.glass) is None:
                warnings.append(
                    f"поверхность {i}: стекло {s.glass!r} вне каталогов "
                    f"(ГОСТ/.FIL/AGF)")

        if sys_obj.num_surfaces:
            if not (0 <= sys_obj.stop_surface < sys_obj.num_surfaces):
                errors.append(
                    f"stop_surface={sys_obj.stop_surface} вне 0.."
                    f"{sys_obj.num_surfaces - 1}")
        if sys_obj.aperture_value <= 0:
            errors.append(f"aperture_value={sys_obj.aperture_value} <= 0")

        try:
            from domain.calculations import paraxial_trace
            parax = paraxial_trace(sys_obj)
            if not parax or not parax.get("focal_length"):
                errors.append("параксиальный расчёт: f' вырождено")
        except Exception as exc:  # движок упал — это ошибка системы
            errors.append(f"параксиальный расчёт не выполняется: {exc}")

        return {"valid": not errors,
                "errors": errors, "warnings": warnings,
                "checks": {"surfaces": sys_obj.num_surfaces,
                           "wavelengths": len(sys_obj.wavelengths),
                           "fields": len(sys_obj.field_points)}}
