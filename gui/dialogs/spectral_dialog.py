"""Dialog for editing spectral lines (wavelengths) of an optical system.

Provides a table editor where the user can add, remove, pick standard
wavelengths, or reset to the default set (e, G', C). Standard lines come
from the shared catalog (utils/spectral_lines.py, п. 11 GAP v2).
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from optics_engine import OpticalSystem, Wavelength
from utils.spectral_lines import SPECTRAL_LINES, format_spectral_line


class StandardLineDialog(QDialog):
    """Выбор стандартной спектральной линии из справочника (п. 11 GAP v2).

    Список линий (обозначение, λ, элемент, цвет) с двойным щелчком для
    выбора; используется и главным окном, и :class:`SpectralDialog`.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Стандартные длины волн")
        self.setMinimumWidth(300)
        self.setMinimumHeight(350)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выберите спектральную линию:"))
        self.line_list = QListWidget()
        for line in SPECTRAL_LINES:
            item = QListWidgetItem(format_spectral_line(line))
            item.setData(Qt.UserRole, (line.name, line.wavelength_um))
            self.line_list.addItem(item)
        layout.addWidget(self.line_list)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.line_list.itemDoubleClicked.connect(lambda _item: self.accept())

    def selected_line(self) -> Optional[Tuple[str, float]]:
        """Выбранная линия: ``(обозначение, λ в мкм)`` или ``None``."""
        item = self.line_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)


def pick_standard_line(parent: Optional[QWidget] = None) -> Optional[Tuple[str, float]]:
    """Модальный выбор стандартной линии из справочника.

    Args:
        parent: родительское окно.

    Returns:
        ``(обозначение, λ в мкм)`` или ``None``, если выбор отменён.
    """
    dlg = StandardLineDialog(parent)
    if dlg.exec_() != QDialog.Accepted:
        return None
    return dlg.selected_line()


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
        """Open a sub-dialog to pick a standard spectral line (справочник)."""
        picked = pick_standard_line(self)
        if picked is None:
            return
        name, val = picked
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
