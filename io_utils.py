"""
OPAL-OKB — JSON import/export for OpticalSystem
Формат: .opal.json
"""
import json
from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    ObjectType, ApertureType, SurfaceType,
)


# Стандартные длины волн — справочник
STANDARD_WAVELENGTHS = {
    'i': 0.36501, 'h': 0.40466, 'g': 0.43584,
    "F'": 0.47999, 'F': 0.48613, 'e': 0.54607,
    'd': 0.58756, "D": 0.58929, "C'": 0.64385,
    'C': 0.65627, 'r': 0.70652, 's': 0.85211,
    't': 1.01398,
}


def save_json(system: OpticalSystem, path: str):
    """Сохранить OpticalSystem в JSON файл."""
    data = {
        "name": system.name,
        "object_type": system.object_type.name,
        "object_height": system.object_height,
        "aperture_type": system.aperture_type.name,
        "aperture_value": system.aperture_value,
        "stop_surface": system.stop_surface,
        "comment": system.comment,
        "wavelengths": [
            {"value": wl.value, "weight": wl.weight, "name": wl.name}
            for wl in system.wavelengths
        ],
        "field_points": [
            {"y": fp.y, "x": fp.x, "weight": fp.weight}
            for fp in system.field_points
        ],
        "obscuration_ratio": system.obscuration_ratio,
        "beam_mode": system.beam_mode,
        "sharp_edge": system.sharp_edge,
        "surfaces": [
            {
                "radius": s.radius,
                "thickness": s.thickness,
                "glass": s.glass,
                "semi_diameter": s.semi_diameter,
                "surface_type": s.surface_type.name,
            }
            for s in system.surfaces
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: str) -> OpticalSystem:
    """Загрузить OpticalSystem из JSON файла."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sys = OpticalSystem()
    sys.name = data.get("name", "")
    sys.object_type = ObjectType[data.get("object_type", "INFINITE")]
    sys.object_height = data.get("object_height", 0.0)
    sys.aperture_type = ApertureType[data.get("aperture_type", "ENTRANCE_PUPIL")]
    sys.aperture_value = data.get("aperture_value", 0.0)
    sys.stop_surface = data.get("stop_surface", 1)
    sys.comment = data.get("comment", "")

    sys.wavelengths = [
        Wavelength(
            value=wl["value"],
            weight=wl.get("weight", 1.0),
            name=wl.get("name", ""),
        )
        for wl in data.get("wavelengths", [])
    ]

    sys.field_points = [
        FieldPoint(
            y=fp["y"],
            x=fp.get("x", 0.0),
            weight=fp.get("weight", 1.0),
        )
        for fp in data.get("field_points", [])
    ]

    sys.obscuration_ratio = data.get("obscuration_ratio", 0.0)
    sys.beam_mode = data.get("beam_mode", "real")
    sys.sharp_edge = data.get("sharp_edge", True)

    sys.surfaces = []
    for sd in data.get("surfaces", []):
        stype = SurfaceType[sd.get("surface_type", "SPHERE")]
        glass_name = sd.get("glass", "")
        surf = Surface(
            radius=sd["radius"],
            thickness=sd["thickness"],
            glass=glass_name,
            semi_diameter=sd.get("semi_diameter", 0.0),
            surface_type=stype,
        )
        # Поддержка зеркал
        if glass_name.upper() in ("ЗЕРКАЛО", "MIRROR"):
            surf.is_reflective = True
        sys.surfaces.append(surf)

    return sys


def append_system(main_system: OpticalSystem, filepath: str) -> OpticalSystem:
    """
    Присоединить систему из файла к текущей.
    Все поверхности добавляются в конец.
    Толщина последней поверхности текущей системы = расстояние до первой поверхности присоединяемой.
    """
    appended = load_json(filepath)
    if not appended.surfaces:
        return main_system

    # Сохраняем текущие поверхности
    existing = list(main_system.surfaces)

    # Добавляем все поверхности из присоединяемой системы
    new_surfaces = list(appended.surfaces)

    # Объединяем
    all_surfaces = existing + new_surfaces

    # Создаём новую систему на основе текущей
    result = OpticalSystem(
        name=main_system.name + " + " + appended.name if appended.name else main_system.name,
        object_type=main_system.object_type,
        object_height=main_system.object_height,
        aperture_type=main_system.aperture_type,
        aperture_value=main_system.aperture_value,
        wavelengths=list(main_system.wavelengths),
        field_points=list(main_system.field_points),
        stop_surface=main_system.stop_surface,
        obscuration_ratio=main_system.obscuration_ratio,
        comment=main_system.comment,
    )
    result.surfaces = all_surfaces
    return result


def export_protocol(system: OpticalSystem, paraxial: dict, seidel: dict, filepath: str):
    """
    Экспортировать результаты анализа в текстовый файл (.txt).
    Формат: таблицы с параксиальными характеристиками, суммами Зейделя,
    таблица поверхностей.
    """
    lines = []
    lines.append("=" * 72)
    lines.append(f"  ПРОТОКОЛ РАСЧЁТА ОПТИЧЕСКОЙ СИСТЕМЫ")
    lines.append(f"  {system.name}")
    lines.append("=" * 72)
    lines.append("")

    # Параксиальные характеристики
    lines.append("─" * 40)
    lines.append("  ПАРАКСИАЛЬНЫЕ ХАРАКТЕРИСТИКИ")
    lines.append("─" * 40)
    lines.append(f"  Фокусное расстояние f'          = {paraxial.get('focal_length', 0):>12.4f} мм")
    lines.append(f"  Задний фокальный отрезок sF'     = {paraxial.get('back_focal_distance', 0):>12.4f} мм")
    lines.append(f"  Передний фокальный отрезок FFD   = {paraxial.get('front_focal_distance', 0):>12.4f} мм")
    lines.append(f"  sF (передний фокус)              = {paraxial.get('sF', 0):>12.4f} мм")
    lines.append(f"  sF' (задний фокус)               = {paraxial.get('sF_prime', 0):>12.4f} мм")
    lines.append(f"  sH (перед. главная плоскость)    = {paraxial.get('sH', 0):>12.4f} мм")
    lines.append(f"  sH' (задн. главная плоскость)    = {paraxial.get('sH_prime', 0):>12.4f} мм")
    lines.append(f"  L (длина системы)                = {paraxial.get('L', 0):>12.4f} мм")
    lines.append(f"  sP (входной зрачок)              = {paraxial.get('sP', 0):>12.4f} мм")
    lines.append(f"  sP' (выходной зрачок)            = {paraxial.get('sP_prime', 0):>12.4f} мм")
    lines.append(f"  Увеличение V                     = {paraxial.get('V', 0):>12.4f}")
    lines.append(f"  f'/# (диафрагменное число)        = {paraxial.get('f_number', 0):>12.2f}")
    lines.append(f"  D входного зрачка                = {paraxial.get('entrance_pupil_diameter', 0):>12.2f} мм")
    lines.append("")

    # Суммы Зейделя
    lines.append("─" * 40)
    lines.append("  СУММЫ ЗЕЙДЕЛЯ (3-й порядок)")
    lines.append("─" * 40)
    lines.append(f"  SI   — сферическая аберрация    = {seidel.get('SI', 0):>14.6f}")
    lines.append(f"  SII  — кома                     = {seidel.get('SII', 0):>14.6f}")
    lines.append(f"  SIII — астигматизм              = {seidel.get('SIII', 0):>14.6f}")
    lines.append(f"  SIV  — кривизна поля (Петцваль) = {seidel.get('SIV', 0):>14.6f}")
    lines.append(f"  SV   — дисторсия                = {seidel.get('SV', 0):>14.6f}")
    lines.append("")

    # Таблица поверхностей
    lines.append("─" * 72)
    lines.append("  ТАБЛИЦА ПОВЕРХНОСТЕЙ")
    lines.append("─" * 72)
    header = f"  {'№':>3}  {'R (мм)':>12}  {'d (мм)':>10}  {'Стекло':>10}  {'D/2 (мм)':>9}  {'Тип':>8}"
    lines.append(header)
    lines.append("  " + "-" * 66)

    for i, s in enumerate(system.surfaces):
        r_str = f"{s.radius:.4f}" if s.radius != 0 else "∞"
        glass_str = s.glass if s.glass else "ВОЗДУХ"
        lines.append(
            f"  {i+1:>3}  {r_str:>12}  {s.thickness:>10.4f}  {glass_str:>10}  {s.semi_diameter:>9.2f}  {s.surface_type.name:>8}"
        )

    # Экранирование
    if system.obscuration_ratio > 0:
        lines.append("")
        lines.append(f"  Экранирование: {system.obscuration_ratio*100:.1f}%")

    lines.append("")
    lines.append("=" * 72)
    lines.append("  Конец протокола")
    lines.append("=" * 72)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
