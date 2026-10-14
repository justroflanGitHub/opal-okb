"""Dialog for fitting optical system parameters.

Allows the user to select a target characteristic (focal length or back
focal distance), a target value, and which surface parameter to vary.
Both parameters (radius and thickness) are available for either target;
switching the target only pre-selects the default parameter. The actual
optimisation is performed by the caller after the dialog returns
accepted parameters.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional, Tuple

from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QSpinBox, QWidget,
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
        current_efl: Optional[float] = None,
        current_bfd: Optional[float] = None,
        mirror_surfaces: Optional[Iterable[int]] = None,
    ) -> None:
        """Initialize the fit dialog.

        Args:
            num_surfaces: Number of surfaces in the system (for spin box range).
            parent: Optional parent widget.
            current_efl: Current paraxial focal length (mm), if known —
                used for the "current value" display and as the initial
                target value for the focal-length goal.
            current_bfd: Current paraxial back focal distance (mm), if known.
            mirror_surfaces: 0-based indices of reflective surfaces, for the
                thickness-on-mirror warning (fit stays allowed).
        """
        super().__init__(parent)
        self.setWindowTitle("Подгонка характеристик")
        self.setMinimumWidth(350)

        self._num_surfaces = num_surfaces
        self._current_efl = current_efl
        self._current_bfd = current_bfd
        self._mirror_surfaces = set(mirror_surfaces or ())

        layout = QFormLayout(self)

        # Target type
        self.target_combo = QComboBox()
        self.target_combo.addItems(["Фокусное расстояние f'", "Задний фок. отрезок BFD"])
        layout.addRow("Цель:", self.target_combo)

        # Current value of the selected characteristic
        self.current_label = QLabel()
        layout.addRow("Текущее:", self.current_label)

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

        # Parameter type — both radius and thickness are allowed for
        # either target; the target only sets the default choice.
        self.param_combo = QComboBox()
        self.param_combo.addItems(["Радиус R", "Толщина d"])
        layout.addRow("Параметр:", self.param_combo)

        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        self.param_combo.currentIndexChanged.connect(self._on_param_changed)
        self.surf_spin.valueChanged.connect(self._on_surface_changed)
        self._on_target_changed(0)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    # ------------------------------------------------------------------ #
    # Internal slots
    # ------------------------------------------------------------------ #

    def _current_target_value(self) -> Optional[float]:
        """Current value of the selected characteristic (None if unknown)."""
        if self.target_combo.currentIndex() == self.TARGET_BFD:
            return self._current_bfd
        return self._current_efl

    def _on_target_changed(self, idx: int) -> None:
        """Pre-select the default parameter for the chosen target and
        refresh the current-value display and the target-value default.

        The parameter combo stays enabled: the user may override the
        default (e.g. fit f' with a thickness).

        Args:
            idx: Current index of :attr:`target_combo`.
        """
        self.param_combo.setCurrentIndex(
            0 if idx == self.TARGET_FOCAL else 1)
        self._refresh_current_value()

    def _refresh_current_value(self) -> None:
        """Show the current value of the target characteristic and use it
        as the default target value."""
        name = "BFD" if self.target_combo.currentIndex() == self.TARGET_BFD else "f'"
        value = self._current_target_value()
        if value is None or not math.isfinite(value):
            self.current_label.setText("—")
        else:
            self.current_label.setText(f"{name} = {value:.4f} мм")
            self.target_spin.setValue(value)

    def _on_param_changed(self, idx: int) -> None:
        """Restrict the surface range for thickness fits.

        The thickness of the last surface is the gap to the image plane —
        varying it cannot change paraxial properties, so it is excluded.
        For radius fits every surface is allowed.

        Args:
            idx: Current index of :attr:`param_combo`.
        """
        if idx == 1:  # Толщина d
            self.surf_spin.setMaximum(max(1, self._num_surfaces - 1))
        else:
            self.surf_spin.setMaximum(max(1, self._num_surfaces))
        self._update_mirror_warning()

    def _on_surface_changed(self, _value: int) -> None:
        """Mirror warning depends on the selected surface."""
        self._update_mirror_warning()

    def _update_mirror_warning(self) -> None:
        """Warn (tooltip only) when varying thickness on a mirror surface.

        Fit is still allowed: for mirrors the thickness shifts the
        following surfaces along the folded path, which may or may not be
        what the user intends.
        """
        is_thickness = self.param_combo.currentIndex() == 1
        on_mirror = (self.surf_spin.value() - 1) in self._mirror_surfaces
        if is_thickness and on_mirror:
            self.surf_spin.setToolTip(
                "Поверхность — зеркало: изменение толщины сдвигает все\n"
                "последующие поверхности вдоль сложенного хода лучей.\n"
                "Подгонка возможна, но проверьте результат.")
        else:
            self.surf_spin.setToolTip("")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

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
