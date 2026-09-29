"""System CRUD controller for OPAL-OKB.

Handles reading the surface table into an :class:`OpticalSystem` and
vice-versa, plus add/delete surface operations. Encapsulates logic that
was previously inline in ``MainWindow``.
"""
from __future__ import annotations

from typing import List

from optics_engine import (
    ApertureType, FieldPoint, ObjectType, OpticalSystem,
    Surface, SurfaceType, Wavelength,
)
from optics_utils import (
    parse_coord_cell, COORD_CELL_TILT_COUNT, COORD_CELL_DECENTER_COUNT,
)


def read_surface_table(table, surfaces: List[Surface]) -> None:
    """Прочитать ячейки таблицы поверхностей в ``surfaces`` — единственная
    реализация (переиспользуется контроллерами системы и расчёта).

    Читает радиус R, осевое расстояние d, марку стекла, высоту D/2,
    коническую постоянную k, наклон X,Y,Z (°) и децентр X,Y (мм).
    Индексы колонок — :meth:`SurfaceTable._col_indices` (single source
    of truth раскладки таблицы).  Нечисловые значения k/наклона/децентра
    молча оставляют прежние (как в OPAL-PC поле EDIT).
    """
    cols = table._col_indices()
    for i in range(min(table.rowCount(), len(surfaces))):
        surf = surfaces[i]
        r_item = table.item(i, cols['r'])
        d_item = table.item(i, cols['d'])
        g_item = table.item(i, cols['glass'])
        sd_item = table.item(i, cols['sd'])
        if r_item:
            txt = r_item.text().strip()
            surf.radius = float(txt) if txt not in ("∞", "inf", "") else 0.0
        if d_item:
            txt = d_item.text().strip()
            surf.thickness = float(txt) if txt else 0.0
        if g_item:
            glass = g_item.text().strip()
            surf.glass = glass
            surf.is_reflective = glass.upper() in ("ЗЕРКАЛО", "MIRROR")
        if sd_item:
            txt = sd_item.text().strip()
            surf.semi_diameter = float(txt) if txt else 0.0
        k_item = table.item(i, cols['k'])
        if k_item:
            txt = k_item.text().strip()
            try:
                k_val = float(txt)
                surf.conic_constant = k_val
                if abs(k_val) > 1e-10:
                    surf.surface_type = SurfaceType.CONIC
                elif surf.surface_type == SurfaceType.CONIC:
                    surf.surface_type = SurfaceType.SPHERE
            except ValueError:
                pass
        # Наклон X,Y,Z (°) и децентр X,Y (мм) — п. 17; формат ячеек и
        # разбор — utils/optics_utils.py (единая реализация)
        tilt_item = table.item(i, cols['tilt'])
        if tilt_item:
            try:
                surf.tilt_x, surf.tilt_y, surf.tilt_z = parse_coord_cell(
                    tilt_item.text(), COORD_CELL_TILT_COUNT)
            except ValueError:
                pass  # нечисловое значение — оставляем прежнее
        dec_item = table.item(i, cols['dec'])
        if dec_item:
            try:
                surf.decenter_x, surf.decenter_y = parse_coord_cell(
                    dec_item.text(), COORD_CELL_DECENTER_COUNT)
            except ValueError:
                pass


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
        conic constant, tilt/decenter — :func:`read_surface_table`) and the
        system parameter widgets (aperture, field points, wavelengths, etc.).
        """
        sys = self.mw.current_system

        # Surfaces
        read_surface_table(self.mw.surface_table, sys.surfaces)

        # System-level parameters
        sp = self.mw.sys_params
        sys.stop_surface = int(sp.stop_nd_spin.value())
        sys.stop_offset = sp.stop_sd_spin.value()
        sys.name = sp.name_edit.text()
        sys.object_type = ObjectType.INFINITE if sp.obj_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.image_type = ObjectType.INFINITE if sp.img_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.object_height = sp.obj_height_spin.value()

        # Апертура: способ задания + значение из UI (п. 12 GAP v2)
        sys.aperture_type, sys.aperture_value = sp.aperture_from_ui()

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
