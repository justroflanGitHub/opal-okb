"""Dialog for editing spectral lines (wavelengths) of an optical system.

Provides a table editor where the user can add, remove, pick standard
wavelengths, or reset to the default set (e, G', C).
"""
from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from optics_engine import OpticalSystem, Wavelength
from io_utils import STANDARD_WAVELENGTHS


class SpectralDialog(QDialog):
    """Modal dialog for configuring spectral lines.

    Allows adding arbitrary wavelengths, picking from standard spectral
    lines, or resetting to the default triplet (e, G', C).

    Attributes:
        wl_table: The table widget holding wavelength data.
    """

    def __init__(
        self,
        system: OpticalSystem,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the spectral lines dialog.

        Args:
            system: The optical system whose wavelengths to edit.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Спектральные линии")
        self.setMinimumWidth(350)

        self._system = system

        layout = QVBoxLayout(self)

        self.wl_table = QTableWidget(0, 3)
        self.wl_table.setHorizontalHeaderLabels(["λ (мкм)", "Вес", "Имя"])
        self.wl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        current_wls = system.wavelengths
        if not current_wls:
            from optics_engine import _std_wavelengths
            current_wls = _std_wavelengths()

        for wl in current_wls:
            self._add_wavelength_row(wl)

        layout.addWidget(self.wl_table)

        # Add / remove / standard buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Добавить")
        del_btn = QPushButton("- Удалить")
        std_btn = QPushButton("Стандартные...")
        default_btn = QPushButton("По умолчанию (e, G', C)")

        add_btn.clicked.connect(self._on_add)
        del_btn.clicked.connect(self._on_delete)
        std_btn.clicked.connect(self._on_standard)
        default_btn.clicked.connect(self._on_default)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(std_btn)
        btn_layout.addWidget(default_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _add_wavelength_row(self, wl: Wavelength) -> None:
        """Append a single wavelength to the table."""
        r = self.wl_table.rowCount()
        self.wl_table.insertRow(r)
        self.wl_table.setItem(r, 0, QTableWidgetItem(f"{wl.value:.5f}"))
        self.wl_table.setItem(r, 1, QTableWidgetItem(f"{wl.weight:.1f}"))
        self.wl_table.setItem(r, 2, QTableWidgetItem(wl.name or ""))

    def _on_add(self) -> None:
        """Add an empty wavelength row."""
        self.wl_table.insertRow(self.wl_table.rowCount())

    def _on_delete(self) -> None:
        """Delete the currently selected wavelength row."""
        if self.wl_table.currentRow() >= 0:
            self.wl_table.removeRow(self.wl_table.currentRow())

    def _on_standard(self) -> None:
        """Open a sub-dialog to pick a standard spectral line."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Стандартные длины волн")
        dlg.setMinimumWidth(250)
        dl = QVBoxLayout(dlg)
        from PyQt5.QtWidgets import QListWidget
        lst = QListWidget()
        for name, val in sorted(STANDARD_WAVELENGTHS.items(), key=lambda x: x[1]):
            lst.addItem(f"{name} — {val:.5f} мкм")
        dl.addWidget(lst)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(dlg.accept)
        b.rejected.connect(dlg.reject)
        dl.addWidget(b)
        if dlg.exec_():
            idx = lst.currentRow()
            if idx >= 0:
                items = sorted(STANDARD_WAVELENGTHS.items(), key=lambda x: x[1])
                name, val = items[idx]
                r = self.wl_table.rowCount()
                self.wl_table.insertRow(r)
                self.wl_table.setItem(r, 0, QTableWidgetItem(f"{val:.4f}"))
                self.wl_table.setItem(r, 1, QTableWidgetItem("1.0"))
                self.wl_table.setItem(r, 2, QTableWidgetItem(name))

    def _on_default(self) -> None:
        """Reset to the default triplet (e, G', C)."""
        from optics_engine import _std_wavelengths
        std = _std_wavelengths()
        self.wl_table.setRowCount(0)
        for wl in std:
            self._add_wavelength_row(wl)

    def get_wavelengths(self) -> List[Wavelength]:
        """Return the configured wavelengths.

        Returns:
            List of :class:`Wavelength` objects parsed from the table.
            Rows with invalid float values are silently skipped.
        """
        new_wls: List[Wavelength] = []
        for r in range(self.wl_table.rowCount()):
            val_item = self.wl_table.item(r, 0)
            w_item = self.wl_table.item(r, 1)
            n_item = self.wl_table.item(r, 2)
            if val_item:
                try:
                    val = float(val_item.text())
                    w = float(w_item.text()) if w_item and w_item.text() else 1.0
                    name = n_item.text() if n_item else ""
                    new_wls.append(Wavelength(val, w, name))
                except ValueError:
                    pass
        return new_wls
