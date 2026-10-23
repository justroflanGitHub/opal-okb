"""
OPAL-OKB — Пакет R500-5: единицы измерения и пространственные
преобразования.

- ``units.*`` — конвертеры оптических единиц: Г.ММСС (углы OPAL),
  диоптрии↔мм, высоты зрачков, Tg·100 (analysis/units.py — все функции
  ещё не были обёрнуты), универсальные λ и углы;
- ``spatial.*`` — матрицы поворотов и координатные изломы поверхностей
  (domain/spatial.py: rotation_matrix/mat_vec/mat_tvec/CoordBreak),
  вершины и СК поверхностей системы (utils/optics_utils.compute_z_positions).
"""
import math

from commands.base import ERR_INVALID_PARAM, Param, CommandError
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
)

#: Единицы длины волны (units.wl.convert).
WL_UNITS = ("um", "nm", "mm", "A")
#: Переводы в мкм (множители).
WL_TO_UM = {"um": 1.0, "nm": 1e-3, "mm": 1e3, "A": 1e-4}

#: Единицы плоского угла (units.angle.convert).
ANGLE_UNITS = ("deg", "rad", "grad", "arcmin", "arcsec")
#: Переводы в градусы (множители).
ANGLE_TO_DEG = {"deg": 1.0, "rad": math.degrees(1.0), "grad": 0.9,
                "arcmin": 1.0 / 60.0, "arcsec": 1.0 / 3600.0}

#: Число элементов 3-вектора и матрицы 3×3 (валидация spatial.*).
VEC_LEN = 3
MAT_LEN = 9


def _vec3(value, param_name: str):
    """3-вектор из списка; валидация длины."""
    if not isinstance(value, (list, tuple)) or len(value) != VEC_LEN:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: нужен список из {VEC_LEN} чисел")
    return tuple(float(x) for x in value)


def _mat3(value, param_name: str):
    """Матрица 3×3 (строка за строкой) из списка 9 чисел."""
    if not isinstance(value, (list, tuple)) or len(value) != MAT_LEN:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"параметр {param_name!r}: нужен список из {MAT_LEN} чисел "
            f"(3×3, строка за строкой)")
    return tuple(float(x) for x in value)


def _unit_vec(v, param_name: str):
    """Направление, нормированное на 1 (трассировка считает t длиной)."""
    norm = math.sqrt(sum(x * x for x in v))
    if norm < 1e-12:
        raise CommandError(
            ERR_INVALID_PARAM,
            f"{param_name}: нулевой вектор направления")
    return tuple(x / norm for x in v)


def register(registry: Registry) -> None:
    """Зарегистрировать команды units/spatial (R500-5)."""

    # ============================================================
    # units.* — analysis/units.py + универсальные конвертеры
    # ============================================================

    @registry.command(
        "units.deg_to_gms", category="units",
        description="Угол (град) → формат OPAL «Г.ММСС» (как в таблицах "
                    "точек поля)",
        returns="{angle_deg, gms}",
        params=[
            Param("angle_deg", type="float", required=True,
                  help="угол, градусы"),
            Param("width", type="int", help="ширина поля вывода"),
            Param("decimals", type="int", help="знаков после точки"),
        ])
    def units_deg_to_gms(ctx, angle_deg, width, decimals):
        from analysis.units import deg_to_gms
        kwargs = {}
        if width is not None:
            kwargs["width"] = width
        if decimals is not None:
            kwargs["decimals"] = decimals
        return {"angle_deg": angle_deg,
                "gms": deg_to_gms(angle_deg, **kwargs)}

    @registry.command(
        "units.grminsec", category="units",
        description="Угол (град) → градусы.минутысекунды числом "
                    "(12.3456° → 12.2045…)",
        returns="{angle_deg, gms_value}",
        params=[
            Param("angle_deg", type="float", required=True,
                  help="угол, градусы"),
        ])
    def units_grminsec(ctx, angle_deg):
        from analysis.units import grminsec
        return {"angle_deg": angle_deg,
                "gms_value": grminsec(angle_deg)}

    @registry.command(
        "units.gms_to_deg", category="units",
        description="«Г.ММСС» числом → угол в градусах",
        returns="{gms_value, angle_deg}",
        params=[
            Param("value", type="float", required=True,
                  help="значение Г.ММСС (например 12.2045)"),
        ])
    def units_gms_to_deg(ctx, value):
        from analysis.units import from_grminsec
        return {"gms_value": value, "angle_deg": from_grminsec(value)}

    @registry.command(
        "units.mm_to_dioptres", category="units",
        description="Отрезок (мм) → оптическая сила (диоптрии): "
                    "Φ = 1000/f",
        returns="{mm, dioptres}",
        params=[
            Param("mm", type="float", required=True,
                  help="отрезок, мм (не 0)"),
        ])
    def units_mm_to_dioptres(ctx, mm):
        from analysis.units import mm_to_dioptres
        dpt = mm_to_dioptres(mm)
        if dpt is None:
            raise CommandError(ERR_INVALID_PARAM,
                               f"mm={mm}: отрезок должен быть не 0")
        return {"mm": mm, "dioptres": dpt}

    @registry.command(
        "units.dioptres_to_mm", category="units",
        description="Оптическая сила (диоптрии) → отрезок (мм)",
        returns="{dioptres, mm}",
        params=[
            Param("dioptres", type="float", required=True,
                  help="сила, дптр (не 0)"),
        ])
    def units_dioptres_to_mm(ctx, dioptres):
        from analysis.units import MM_PER_DIOPTRE
        if dioptres == 0:
            raise CommandError(ERR_INVALID_PARAM,
                               "dioptres=0: вырожденная сила")
        return {"dioptres": dioptres,
                "mm": MM_PER_DIOPTRE / dioptres}

    @registry.command(
        "units.pupil_h_mm", category="units",
        description="Высота луча в зрачке: доля зрачка × осевой отрезок",
        returns="{rel, ax_mm, h_mm}",
        params=[
            Param("rel", type="float", required=True,
                  help="доля высоты зрачка (−1..1)"),
            Param("ax_mm", type="float", required=True,
                  help="осевой отрезок, мм"),
        ])
    def units_pupil_h_mm(ctx, rel, ax_mm):
        from analysis.units import pupil_h_mm
        return {"rel": rel, "ax_mm": ax_mm,
                "h_mm": pupil_h_mm(rel, ax_mm)}

    @registry.command(
        "units.pupil_h_out_mm", category="units",
        description="Высота луча на выходе: доля × осевой отрезок "
                    "в пространстве изображений",
        returns="{rel, ax_out_mm, h_mm}",
        params=[
            Param("rel", type="float", required=True, help="доля зрачка"),
            Param("ax_out_mm", type="float", required=True,
                  help="осевой отрезок изображения, мм"),
        ])
    def units_pupil_h_out_mm(ctx, rel, ax_out_mm):
        from analysis.units import pupil_h_out_mm
        return {"rel": rel, "ax_out_mm": ax_out_mm,
                "h_mm": pupil_h_out_mm(rel, ax_out_mm)}

    @registry.command(
        "units.tg100", category="units",
        description="Tg·100 — тангенс угла ×100 (единица OPAL для "
                    "виньетирования/полей)",
        returns="{angle_deg, tg100}",
        params=[
            Param("angle_deg", type="float", required=True,
                  help="угол, градусы"),
        ])
    def units_tg100(ctx, angle_deg):
        from analysis.units import tg100
        return {"angle_deg": angle_deg, "tg100": tg100(angle_deg)}

    @registry.command(
        "units.wl.convert", category="units",
        description="Длину волны между единицами (мкм/нм/мм/Å)",
        returns="{value, from_unit, to_unit, result}",
        params=[
            Param("value", type="float", required=True,
                  help="значение длины волны"),
            Param("from_unit", choices=list(WL_UNITS), default="um",
                  help="единица источника"),
            Param("to_unit", choices=list(WL_UNITS), default="nm",
                  help="единица результата"),
        ])
    def units_wl_convert(ctx, value, from_unit, to_unit):
        um = value * WL_TO_UM[from_unit]
        return {"value": value, "from_unit": from_unit,
                "to_unit": to_unit,
                "result": um / WL_TO_UM[to_unit],
                "value_um": um}

    @registry.command(
        "units.angle.convert", category="units",
        description="Плоский угол между единицами (град/рад/град/"
                    "угл.мин/угл.сек)",
        returns="{value, from_unit, to_unit, result}",
        params=[
            Param("value", type="float", required=True, help="значение"),
            Param("from_unit", choices=list(ANGLE_UNITS), default="deg",
                  help="единица источника"),
            Param("to_unit", choices=list(ANGLE_UNITS), default="rad",
                  help="единица результата"),
        ])
    def units_angle_convert(ctx, value, from_unit, to_unit):
        deg = value * ANGLE_TO_DEG[from_unit]
        return {"value": value, "from_unit": from_unit,
                "to_unit": to_unit,
                "result": deg / ANGLE_TO_DEG[to_unit],
                "value_deg": deg}

    # ============================================================
    # spatial.* — domain/spatial.py + вершины поверхностей
    # ============================================================

    @registry.command(
        "spatial.rotation_matrix", category="spatial",
        description="Матрица поворота R = Rz·Ry·Rx (наклоны поверхностей, "
                    "порядок X→Y→Z)",
        returns="{matrix: [9 чисел строкой за строкой], identity}",
        params=[
            Param("tilt_x", type="float", default=0.0,
                  help="наклон вокруг X, град"),
            Param("tilt_y", type="float", default=0.0,
                  help="наклон вокруг Y, град"),
            Param("tilt_z", type="float", default=0.0,
                  help="наклон вокруг Z, град"),
        ])
    def spatial_rotation_matrix(ctx, tilt_x, tilt_y, tilt_z):
        from domain.spatial import rotation_matrix
        matrix = rotation_matrix(tilt_x, tilt_y, tilt_z)
        return {"tilts": [tilt_x, tilt_y, tilt_z],
                "matrix": list(matrix) if matrix else None,
                "identity": matrix is None}

    @registry.command(
        "spatial.rotate_vector", category="spatial",
        description="Повернуть вектор матрицей наклонов (R или Rᵀ)",
        returns="{v, result}",
        params=[
            Param("tilt_x", type="float", default=0.0, help="наклон X, град"),
            Param("tilt_y", type="float", default=0.0, help="наклон Y, град"),
            Param("tilt_z", type="float", default=0.0, help="наклон Z, град"),
            Param("v", type="list", required=True,
                  help="вектор [x, y, z]"),
            Param("transpose", type="bool", default=False,
                  help="применить Rᵀ (глобальная → локальная СК)"),
        ])
    def spatial_rotate_vector(ctx, tilt_x, tilt_y, tilt_z, v, transpose):
        from domain.spatial import mat_tvec, mat_vec, rotation_matrix
        vec = _vec3(v, "v")
        matrix = rotation_matrix(tilt_x, tilt_y, tilt_z)
        if matrix is None:
            result = vec
        else:
            result = (mat_tvec(matrix, vec) if transpose
                      else mat_vec(matrix, vec))
        return {"v": list(vec), "result": list(result)}

    @registry.command(
        "spatial.mat_vec", category="spatial",
        description="Умножить матрицу 3×3 на вектор (M·v)",
        returns="{result: [x, y, z]}",
        params=[
            Param("matrix", type="list", required=True,
                  help="матрица 3×3 строкой за строкой (9 чисел)"),
            Param("v", type="list", required=True, help="вектор [x, y, z]"),
        ])
    def spatial_mat_vec(ctx, matrix, v):
        from domain.spatial import mat_vec
        return {"result": list(mat_vec(_mat3(matrix, "matrix"),
                                       _vec3(v, "v")))}

    @registry.command(
        "spatial.mat_tvec", category="spatial",
        description="Умножить транспонированную матрицу 3×3 на вектор "
                    "(Mᵀ·v)",
        returns="{result: [x, y, z]}",
        params=[
            Param("matrix", type="list", required=True,
                  help="матрица 3×3 строкой за строкой (9 чисел)"),
            Param("v", type="list", required=True, help="вектор [x, y, z]"),
        ])
    def spatial_mat_tvec(ctx, matrix, v):
        from domain.spatial import mat_tvec
        return {"result": list(mat_tvec(_mat3(matrix, "matrix"),
                                        _vec3(v, "v")))}

    @registry.command(
        "spatial.ray_rotate", category="spatial",
        description="Повернуть направление луча (k,l,m) наклонами "
                    "поверхности (нормирует вектор)",
        returns="{k, l, m}",
        params=[
            Param("tilt_x", type="float", default=0.0, help="наклон X, град"),
            Param("tilt_y", type="float", default=0.0, help="наклон Y, град"),
            Param("tilt_z", type="float", default=0.0, help="наклон Z, град"),
            Param("k", type="float", required=True,
                  help="компонента X направления"),
            Param("l", type="float", required=True,
                  help="компонента Y направления"),
            Param("m", type="float", required=True,
                  help="компонента Z направления"),
            Param("transpose", type="bool", default=False,
                  help="применить Rᵀ (в локальную СК)"),
        ])
    def spatial_ray_rotate(ctx, tilt_x, tilt_y, tilt_z, k, l, m,
                           transpose):
        from domain.spatial import mat_tvec, mat_vec, rotation_matrix
        vec = _unit_vec((k, l, m), "(k,l,m)")
        matrix = rotation_matrix(tilt_x, tilt_y, tilt_z)
        if matrix is not None:
            vec = (mat_tvec(matrix, vec) if transpose
                   else mat_vec(matrix, vec))
        return {"k": vec[0], "l": vec[1], "m": vec[2]}

    @registry.command(
        "spatial.coord_breaks", category="spatial",
        description="Изломы СК по поверхностям: где есть наклон/"
                    "децентрировка",
        returns="{surfaces: [{index, has_break, tilts, decenters}]}",
        params=system_source_params())
    def spatial_coord_breaks(ctx, file, system, lbo_index, lbo_name):
        from domain.spatial import surface_has_coord_break
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        rows = []
        for i, s in enumerate(sys_obj.surfaces):
            rows.append({
                "index": i,
                "has_break": surface_has_coord_break(s),
                "tilts": [s.tilt_x, s.tilt_y, s.tilt_z],
                "decenters": [s.decenter_x, s.decenter_y],
            })
        return {"surfaces": rows,
                "count": len(rows),
                "with_break": sum(1 for r in rows if r["has_break"])}

    @registry.command(
        "spatial.vertices", category="spatial",
        description="Вершины поверхностей в глобальной СК (z по "
                    "толщинам + децентрировки)",
        returns="{vertices: [{index, x, y, z, semi_diameter}]}",
        params=system_source_params())
    def spatial_vertices(ctx, file, system, lbo_index, lbo_name):
        from utils.optics_utils import compute_z_positions
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        z_pos = compute_z_positions(sys_obj)
        vertices = []
        for i, s in enumerate(sys_obj.surfaces):
            vertices.append({
                "index": i,
                "x": s.decenter_x, "y": s.decenter_y,
                "z": z_pos[i],
                "semi_diameter": s.semi_diameter,
            })
        return {"vertices": vertices, "count": len(vertices),
                "z_image": z_pos[-1] if z_pos else 0.0}

    @registry.command(
        "spatial.surface_frames", category="spatial",
        description="Системы координат поверхностей: вершина + матрица "
                    "поворота (CoordBreak)",
        returns="{frames: [{index, vertex, matrix, identity}]}",
        params=system_source_params())
    def spatial_surface_frames(ctx, file, system, lbo_index, lbo_name):
        from domain.spatial import CoordBreak
        from utils.optics_utils import compute_z_positions
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        z_pos = compute_z_positions(sys_obj)
        frames = []
        for i, s in enumerate(sys_obj.surfaces):
            break_obj = CoordBreak.from_surface(s, z_pos[i])
            frames.append({
                "index": i,
                "vertex": [break_obj.decenter_x, break_obj.decenter_y,
                           break_obj.z_vertex],
                "matrix": (list(break_obj.matrix)
                           if break_obj.matrix is not None else None),
                "identity": break_obj.is_identity,
            })
        return {"frames": frames, "count": len(frames)}
