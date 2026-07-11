"""
optics_utils.py — shared utility functions for OPAL-OKB.

Created by refactoring/dedup-v2.
Each function here was extracted from duplicated inline code.
See REFACTORING.md for details.
"""

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optics_engine import OpticalSystem


# ============================================================
# NUMERICAL CONSTANTS
# ============================================================

EPSILON = 1e-10       # general "near zero" for float comparisons
TINY = 1e-15          # very small, for division guards
UNLIMITED_SD = 1e6    # placeholder for unlimited semi-diameter
DEFAULT_RAY_Z = -50.0  # default ray start z (should be overridden by entrance pupil)


# ============================================================
# Z-POSITIONS: cumulative vertex positions from thicknesses
# ============================================================

def compute_z_positions(system):
    """
    Compute cumulative z-position of each surface vertex.
    Returns list of len(surfaces)+1 values (z[0]=0, z[i]=z[i-1]+thickness[i-1]).
    """
    z_pos = [0.0]
    for s in system.surfaces:
        z_pos.append(z_pos[-1] + s.thickness)
    return z_pos


# ============================================================
# PRIMARY WAVELENGTH
# ============================================================

def get_primary_wl(system):
    """
    Return the primary (first) wavelength value in micrometers.
    Falls back to 0.58756 (d-line) if no wavelengths defined.
    """
    return system.wavelengths[0].value if system.wavelengths else 0.58756


# ============================================================
# EFFECTIVE APERTURE
# ============================================================

def get_effective_aperture(system, default=20.0):
    """
    Return aperture diameter (D in mm).
    Falls back to `default` if aperture_value <= 0.
    
    Callers should pass the same default they used before refactoring:
    - aberrations.py, advanced_analysis.py, diffraction_mtf.py, zernike.py: default=10.0
    - visualization.py, visualization3d.py, ray_tracing.py: default=20.0
    - optics_engine.py: uses its own efl/4.0 logic (not this function)
    """
    ap = system.aperture_value
    if ap and ap > 0:
        return ap
    return default


# ============================================================
# WAVELENGTH NAME LOOKUP
# ============================================================

# Full mapping: wavelength (μm) → spectral line name
# Superset of both decode_lbo_opj.py and opj_reader.py dicts
WL_NAMES = {
    0.54607: 'e',
    0.43405: "G'",
    0.65627: 'C',
    0.58756: 'd',
    0.48613: 'F',
    0.43584: 'g',
    0.40466: 'h',
    0.36501: 'i',
    0.70652: 'r',
    0.85211: 's',
    0.64385: "C'",
    0.47999: "F'",
    0.58930: 'D',
}


def wl_name(wl, tol=0.0002):
    """
    Look up spectral line name for a wavelength (μm).
    Returns name if within `tol` of a known line, else formatted string.
    """
    for wlv, name in WL_NAMES.items():
        if abs(wl - wlv) < tol:
            return name
    return f"{wl:.5f}"


# ============================================================
# TABLE CLIPBOARD COPY
# ============================================================

def copy_table_selection(table_widget):
    """
    Copy selected cells from a QTableWidget to clipboard as TSV.
    Works with any QTableWidget instance.
    """
    from PyQt5.QtWidgets import QApplication
    selection = table_widget.selectedRanges()
    if not selection:
        return
    lines = []
    for rng in selection:
        for row in range(rng.topRow(), rng.bottomRow() + 1):
            cells = []
            for col in range(rng.leftColumn(), rng.rightColumn() + 1):
                item = table_widget.item(row, col)
                cells.append(item.text() if item else '')
            lines.append('\t'.join(cells))
    QApplication.clipboard().setText('\n'.join(lines))


# ============================================================
# VALUE FORMATTING
# ============================================================

def fmt_val(v, ndigits=5):
    """
    Format a numeric value with fixed decimals.
    Returns em-dash for NaN.
    """
    if v != v:  # NaN check
        return '\u2014'
    return f"{v:.{ndigits}f}"


# ============================================================
# RAY FACTORY
# ============================================================

def make_field_ray(system: 'OpticalSystem',
                    pupil_x: float,
                    pupil_y: float,
                    field_angle_deg: float,
                    z_start: float,
                    z_pupil: float = 0.0):
    """
    Create a field ray aimed through entrance pupil coordinates.

    For **INFINITE** objects: the ray starts at *z_start*, tilted by
    *field_angle_deg* (degrees), and passes through *(pupil_x, pupil_y)*
    at *z_pupil*.  Back-projection from the pupil plane to the start
    plane is handled automatically.

    For **FINITE** objects: *field_angle_deg* is interpreted as the
    object-side field height (mm).  The ray originates from
    (pupil_x, field_angle_deg) at the object plane and is aimed at
    *(pupil_x, pupil_y)* near the first surface.

    Parameters
    ----------
    system : OpticalSystem
        The optical system (provides ``object_type`` and ``surfaces``).
    pupil_x, pupil_y : float
        Physical coordinates (mm) at the entrance-pupil / first-surface
        plane that the ray must pass through.
    field_angle_deg : float
        Field angle (degrees) for INFINITE objects, or field height (mm)
        for FINITE objects.
    z_start : float
        Z-position where the ray originates.
    z_pupil : float
        Z-position of the entrance pupil (used for back-projection in
        the INFINITE case).  Default 0.0.

    Returns
    -------
    Ray
        A ready-to-trace ray (see :class:`ray_tracing.Ray`).
    """
    from ray_tracing import Ray          # avoid circular at module level
    from optics_engine import ObjectType

    if system.object_type == ObjectType.INFINITE:
        angle = math.radians(field_angle_deg) if field_angle_deg != 0 else 0.0
        sin_a, cos_a = math.sin(angle), math.cos(angle)

        # Back-project pupil coords to z_start plane
        dz = z_pupil - z_start
        x_start = pupil_x
        if cos_a > EPSILON:
            y_start = pupil_y - dz * sin_a / cos_a
        else:
            y_start = pupil_y

        return Ray(x=x_start, y=y_start, z=z_start, k=0.0, l=sin_a, m=cos_a)
    else:
        # FINITE object — field_angle_deg is field height in mm
        obj_z = -system.surfaces[0].thickness if system.surfaces else DEFAULT_RAY_Z
        d = abs(obj_z)
        if d < EPSILON:
            d = abs(DEFAULT_RAY_Z)
        k = pupil_x / d
        l = (pupil_y - field_angle_deg) / d
        m = 1.0
        norm = math.sqrt(k * k + l * l + m * m)
        return Ray(x=pupil_x, y=field_angle_deg, z=obj_z,
                   k=k / norm, l=l / norm, m=m / norm)
