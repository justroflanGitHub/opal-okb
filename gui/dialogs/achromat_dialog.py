"""Dialog for designing an achromatic doublet.

Lets the user specify a target focal length, entrance pupil diameter,
and a glass pair (crown + flint). The actual design is performed by
:func:`achromat.design_achromat` after the dialog is accepted.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QWidget,
)

from achromat import GLASS_PAIRS


class AchromatDialog(QDialog):
    """Modal dialog for achromatic doublet design parameters.

    On accept, call :meth:`get_parameters` to obtain the focal length,
    aperture, and glass pair selection.

    Attributes:
        f_spin: Spin box for focal length in mm.
        ap_spin: Spin box for entrance pupil diameter in mm (0 = auto).
        pair_combo: Combo box for selecting a crown+flint glass pair.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the achromat design dialog.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Расчёт ахроматического дублета")
        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        # Focal length
        self.f_spin = QDoubleSpinBox()
        self.f_spin.setRange(1.0, 100000.0)
        self.f_spin.setDecimals(1)
        self.f_spin.setValue(100.0)
        self.f_spin.setSuffix(" мм")
        layout.addRow("Фокусное расстояние f':", self.f_spin)

        # Aperture
        self.ap_spin = QDoubleSpinBox()
        self.ap_spin.setRange(0.0, 10000.0)
        self.ap_spin.setDecimals(1)
        self.ap_spin.setValue(0.0)
        self.ap_spin.setSuffix(" мм (0 = авто)")
        layout.addRow("Входной зрачок D:", self.ap_spin)

        # Glass pair
        self.pair_combo = QComboBox()
        for crown, flint in GLASS_PAIRS:
            self.pair_combo.addItem(f"{crown} + {flint}")
        layout.addRow("Пара стёкол:", self.pair_combo)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_parameters(self) -> Tuple[float, float, str, str]:
        """Return the design parameters chosen by the user.

        Returns:
            A tuple of ``(focal_length, aperture, crown_glass, flint_glass)``.
        """
        crown, flint = GLASS_PAIRS[self.pair_combo.currentIndex()]
        return (self.f_spin.value(), self.ap_spin.value(), crown, flint)
