"""
optics_utils.py — shared utility functions for OPAL-OKB.

Created by refactoring/dedup-v2.
Each function here was extracted from duplicated inline code.
See REFACTORING.md for details.
"""

import math


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
