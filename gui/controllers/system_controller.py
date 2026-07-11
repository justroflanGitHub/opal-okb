"""System CRUD controller for OPAL-OKB.

Handles reading the surface table into an :class:`OpticalSystem` and
vice-versa, plus add/delete surface operations. Encapsulates logic that
was previously inline in ``MainWindow``.
"""
from __future__ import annotations

from typing import List

from PyQt5.QtWidgets import QTableWidgetItem

from optics_engine import (
    ApertureType, FieldPoint, ObjectType, OpticalSystem,
    Surface, SurfaceType, Wavelength,
)


class SystemController:
    """Controller for optical system CRUD operations.

    Reads from and writes to the UI widgets (surface table, parameter
    panel) owned by the main window.

    Attributes:
        mw: Reference to the main window providing access to UI widgets.
    """

    def __init__(self, main_window) -> None:
        """Initialize the system controller.

        Args:
            main_window: The :class:`MainWindow` instance that owns
                the surface table and parameter widgets.
        """
        self.mw = main_window

    # ------------------------------------------------------------------
    # Surface table ↔ OpticalSystem
    # ------------------------------------------------------------------

    def collect_system_from_ui(self) -> None:
        """Read all UI fields into ``main_window.current_system``.

        Parses the surface table (radius, thickness, glass, semi-diameter,
        conic constant) and the system parameter widgets (aperture, field
        points, wavelengths, etc.).
        """
        sys = self.mw.current_system
        n_wl = max(1, len(sys.wavelengths))
        sd_col = 4 + n_wl     # D/2
        k_col = 4 + n_wl + 2  # k

        # Surfaces
        for i in range(min(self.mw.surface_table.rowCount(), len(sys.surfaces))):
            r_item = self.mw.surface_table.item(i, 1)
            d_item = self.mw.surface_table.item(i, 2)
            g_item = self.mw.surface_table.item(i, 3)
            sd_item = self.mw.surface_table.item(i, sd_col)
            if r_item:
                txt = r_item.text().strip()
                sys.surfaces[i].radius = float(txt) if txt not in ("∞", "inf", "") else 0.0
            if d_item:
                txt = d_item.text().strip()
                sys.surfaces[i].thickness = float(txt) if txt else 0.0
            if g_item:
                glass = g_item.text().strip()
                sys.surfaces[i].glass = glass
                if glass.upper() in ("ЗЕРКАЛО", "MIRROR"):
                    sys.surfaces[i].is_reflective = True
                else:
                    sys.surfaces[i].is_reflective = False
            if sd_item:
                txt = sd_item.text().strip()
                sys.surfaces[i].semi_diameter = float(txt) if txt else 0.0
            k_item = self.mw.surface_table.item(i, k_col)
            if k_item:
                txt = k_item.text().strip()
                try:
                    k_val = float(txt)
                    sys.surfaces[i].conic_constant = k_val
                    if abs(k_val) > 1e-10:
                        sys.surfaces[i].surface_type = SurfaceType.CONIC
                    elif sys.surfaces[i].surface_type == SurfaceType.CONIC:
                        sys.surfaces[i].surface_type = SurfaceType.SPHERE
                except ValueError:
                    pass

        # System-level parameters
        sp = self.mw.sys_params
        sys.stop_surface = int(sp.stop_nd_spin.value())
        sys.stop_offset = sp.stop_sd_spin.value()
        sys.name = sp.name_edit.text()
        sys.object_type = ObjectType.INFINITE if sp.obj_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.image_type = ObjectType.INFINITE if sp.img_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.object_height = sp.obj_height_spin.value()

        ap_idx = sp.front_ap_combo.currentIndex()
        ap_val = sp.front_ap_spin.value()
        if ap_idx == 0:  # Y height (D/2)
            sys.aperture_type = ApertureType.ENTRANCE_PUPIL
            sys.aperture_value = ap_val * 2
        elif ap_idx == 1:  # NA
            sys.aperture_type = ApertureType.NUMERICAL_APERTURE
            sys.aperture_value = ap_val
        else:  # F/#
            sys.aperture_type = ApertureType.F_NUMBER
            sys.aperture_value = ap_val

        sys.obscuration_ratio = sp.obscuration_spin.value() / 100.0
        sys.beam_mode = "real" if sp.beam_mode_combo.currentIndex() == 0 else "given"
        sys.sharp_edge = sp.sharp_edge_check.isChecked()

        fp_data = sp.field_points_widget.get_field_points()
        sys.field_points = [FieldPoint(y=y, x=x, weight=w) for y, x, w in fp_data]

        sys.wavelengths = []
        for i in range(sp.wl_table.rowCount()):
            wl_val = float(sp.wl_table.item(i, 0).text())
            wl_w = float(sp.wl_table.item(i, 1).text())
            wl_n = sp.wl_table.item(i, 2).text() if sp.wl_table.item(i, 2) else ""
            sys.wavelengths.append(Wavelength(wl_val, wl_w, wl_n))

    # ------------------------------------------------------------------
    # Surface add / delete
    # ------------------------------------------------------------------

    def add_surface(self) -> None:
        """Insert a blank surface before the selected row (or at end)."""
        rows = self.mw.surface_table.selectionModel().selectedRows()
        if rows:
            idx = rows[0].row()
        else:
            idx = len(self.mw.current_system.surfaces)
        idx = max(0, min(idx, len(self.mw.current_system.surfaces)))
        s = Surface()
        self.mw.current_system.surfaces.insert(idx, s)
        self.mw._refresh_ui()
        self.mw.statusBar().showMessage(f"Поверхность вставлена перед S{idx + 1}")

    def del_surface(self) -> None:
        """Delete the selected surface row(s) from the system."""
        rows = sorted(
            set(i.row() for i in self.mw.surface_table.selectedItems()),
            reverse=True,
        )
        if not rows:
            self.mw.statusBar().showMessage("Выберите поверхность для удаления")
            return
        for r in rows:
            if r < len(self.mw.current_system.surfaces):
                del self.mw.current_system.surfaces[r]
        self.mw._refresh_ui()
        self.mw.statusBar().showMessage(f"Удалено поверхностей: {len(rows)}")
