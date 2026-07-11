"""
OPAL-OKB — JSON import/export for OpticalSystem
Формат: .opal.json

Extracted from io_utils.py during package restructuring.
"""
import json
from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    ObjectType, ApertureType, SurfaceType,
)


# Стандартные длины волн — справочник
STANDARD_WAVELENGTHS = {
    'i': 0.36501, 'h': 0.40466, 'g': 0.43584, "G'": 0.43405,
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
