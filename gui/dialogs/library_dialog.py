"""Dialog for browsing the optical system library.

Displays a tree of categorized optical systems (including expandable
LBO archive entries) and lets the user select one to load.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from library import build_library, create_system_from_entry, expand_lbo


class LibraryDialog(QDialog):
    """Modal dialog for browsing and selecting a library system.

    On accept, call :meth:`get_selected_system` to obtain the
    :class:`~optics_engine.OpticalSystem` created from the selected entry.

    Attributes:
        _entries: Mapping from ``id(QTreeWidgetItem)`` to entry dict.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the library browser dialog.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Библиотека оптических систем")
        self.setMinimumSize(500, 400)

        self._entries: Dict[int, Dict[str, Any]] = {}

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Название системы"])
        self.tree.setHeaderHidden(False)
        self._populate_tree()
        layout.addWidget(self.tree)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Double-click opens immediately
        self.tree.itemDoubleClicked.connect(self._on_double_click)

    def _populate_tree(self) -> None:
        """Build the tree from the library data."""
        lib = build_library()

        # Sort: LBO categories first, then alphabetical
        sorted_cats = sorted(
            lib.items(),
            key=lambda kv: (0 if "LBO" in kv[0] else 1, kv[0]),
        )

        for category, items in sorted_cats:
            cat_item = QTreeWidgetItem(self.tree, [category])
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)

            for entry in items:
                item = QTreeWidgetItem(cat_item, [entry["name"]])
                if entry.get("lbo_path") and not entry.get("opj_data"):
                    # Expandable LBO category — pre-load children
                    systems = expand_lbo(entry["lbo_path"])
                    for s in systems:
                        child = QTreeWidgetItem(item, [s["name"]])
                        self._entries[id(child)] = s
                    item.setExpanded(False)
                else:
                    self._entries[id(item)] = entry

            cat_item.setExpanded(True)

    def _on_double_click(self, item: QTreeWidgetItem, col: int) -> None:
        """Accept the dialog on double-click of a leaf entry."""
        if id(item) in self._entries:
            self.accept()

    def get_selected_entry(self) -> Optional[Dict[str, Any]]:
        """Return the selected library entry dict, or ``None``.

        Returns:
            The entry dictionary for the selected tree item, or
            ``None`` if no valid entry is selected.
        """
        selected = self.tree.selectedItems()
        if not selected:
            return None
        item = selected[0]
        return self._entries.get(id(item))
