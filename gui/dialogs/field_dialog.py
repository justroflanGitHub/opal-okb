"""Dialog for editing field points of an optical system.

Provides a table-based editor where the user can add, remove, and edit
field points (Y, X, Weight) that define the field configuration.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QWidget,
)

from optics_engine import OpticalSystem, FieldPoint


class FieldPointsDialog(QDialog):
    """Modal dialog for managing field points.

    Loads field points from an :class:`OpticalSystem`, lets the user
    edit them, and on accept writes them back to the system.

    Attributes:
        _fp_widget: The embedded :class:`FieldPointsWidget` used for editing.
    """

    def __init__(
        self,
        system: OpticalSystem,
        field_points_widget_class: type,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the field points dialog.

        Args:
            system: The optical system whose field points to edit.
            field_points_widget_class: The :class:`FieldPointsWidget` class
                (imported from ``main`` to avoid circular imports).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Точки поля")
        self.setMinimumWidth(350)

        self._system = system

        layout = QVBoxLayout(self)
        self._fp_widget = field_points_widget_class()
        self._fp_widget.load_system(system)
        layout.addWidget(self._fp_widget)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_field_points(self) -> List[FieldPoint]:
        """Return the edited field points as a list of :class:`FieldPoint`.

        Returns:
            List of field points configured in the embedded widget.
        """
        fp_data = self._fp_widget.get_field_points()
        return [FieldPoint(y=y, x=x, weight=w) for y, x, w in fp_data]
