"""Compatibility shim. Real code in domain/models.py and domain/calculations.py.

This module re-exports everything that was previously in optics_engine.py
so that existing imports (``from optics_engine import OpticalSystem``) continue
to work without modification.

During the package restructuring, the contents were split:
  - Data models (OpticalSystem, Surface, Wavelength, etc.)  → domain/models.py
  - Calculations (paraxial_trace, seidel_aberrations, etc.) → domain/calculations.py
"""
# Models
from domain.models import (
    SurfaceType,
    ObjectType,
    ApertureType,
    Surface,
    Wavelength,
    FieldPoint,
    GlassCatalogEntry,
    OpticalSystem,
    _std_wavelengths,
    _std_fields,
    create_demo_system,
    create_demo_system_by_name,
    _demo_achromat,
    _demo_cook_doublet,
    _demo_telephoto,
    _demo_petzval,
    _demo_mirror,
    _demo_meniscus,
    _demo_plano_convex,
)

# Calculations
from domain.calculations import (
    apply_vignetting,
    refractive_index,
    paraxial_trace,
    compute_beam_geometry,
    seidel_aberrations,
)

__all__ = [
    # Enums
    'SurfaceType', 'ObjectType', 'ApertureType',
    # Dataclasses
    'Surface', 'Wavelength', 'FieldPoint', 'GlassCatalogEntry', 'OpticalSystem',
    # Factories
    '_std_wavelengths', '_std_fields',
    'create_demo_system', 'create_demo_system_by_name',
    '_demo_achromat', '_demo_cook_doublet', '_demo_telephoto', '_demo_petzval',
    '_demo_mirror', '_demo_meniscus', '_demo_plano_convex',
    # Calculations
    'apply_vignetting', 'refractive_index', 'paraxial_trace',
    'compute_beam_geometry', 'seidel_aberrations',
]
