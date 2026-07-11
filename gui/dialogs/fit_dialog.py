"""Dialog for fitting optical system parameters.

Allows the user to select a target characteristic (focal length or back
focal distance), a target value, and which surface parameter to vary.
The actual optimisation is performed by the caller after the dialog
returns accepted parameters.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QSpinBox, QWidget,
)


class FitDialog(QDialog):
    """Modal dialog for configuring a fit operation.

    On accept, call :meth:`get_parameters` to obtain the target type,
    target value, surface index, and parameter type.

    Attributes:
        TARGET_FOCAL: Index constant for focal-length target.
        TARGET_BFD: Index constant for back-focal-distance target.
    """

    TARGET_FOCAL: int = 0
    TARGET_BFD: int = 1

    def __init__(
        self,
        num_surfaces: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the fit dialog.

        Args:
            num_surfaces: Number of surfaces in the system (for spin box range).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Подгонка характеристик")
        self.setMinimumWidth(350)

        layout = QFormLayout(self)

        # Target type
        self.target_combo = QComboBox()
        self.target_combo.addItems(["Фокусное расстояние f'", "Задний фок. отрезок BFD"])
        layout.addRow("Цель:", self.target_combo)

        # Target value
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(-100000, 100000)
        self.target_spin.setDecimals(4)
        self.target_spin.setSuffix(" мм")
        self.target_spin.setValue(100.0)
        layout.addRow("Целевое значение:", self.target_spin)

        # Surface number
        self.surf_spin = QSpinBox()
        self.surf_spin.setRange(1, max(1, num_surfaces))
        self.surf_spin.setValue(1)
        layout.addRow("Поверхность No:", self.surf_spin)

        # Parameter type
        self.param_combo = QComboBox()
        self.param_combo.addItems(["Радиус R", "Толщина d"])
        layout.addRow("Параметр:", self.param_combo)

        # When target changes, auto-set available parameters
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        self._on_target_changed(0)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_target_changed(self, idx: int) -> None:
        """Auto-select the appropriate parameter for the chosen target.

        Args:
            idx: Current index of :attr:`target_combo`.
        """
        if idx == self.TARGET_FOCAL:
            self.param_combo.setCurrentIndex(0)  # Радиус R
            self.param_combo.setEnabled(False)
        else:
            self.param_combo.setCurrentIndex(1)  # Толщина d
            self.param_combo.setEnabled(False)

    def get_parameters(self) -> Tuple[int, float, int, str]:
        """Return the fit configuration selected by the user.

        Returns:
            A tuple of ``(target_type, target_value, surface_index, param_type)``
            where ``target_type`` is :attr:`TARGET_FOCAL` or :attr:`TARGET_BFD`,
            ``surface_index`` is 0-based, and ``param_type`` is ``'radius'``
            or ``'thickness'``.
        """
        surf_idx = self.surf_spin.value() - 1  # 0-based
        param_type = 'radius' if self.param_combo.currentIndex() == 0 else 'thickness'
        return (
            self.target_combo.currentIndex(),
            self.target_spin.value(),
            surf_idx,
            param_type,
        )
