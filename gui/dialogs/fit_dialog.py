"""Dialogs for fitting / optimizing optical system parameters.

Two режима (вкладки):

- «Подгонка» — solve 1×1: цель (f′ или BFD), целевое значение, поверхность
  и параметр; решение — Ньютон через :func:`analysis.optimization.solve_single`
  (замена бисекции ``optimizer.fit_*``);
- «Оптимизация (ЛАП)» — многоцелевой режим волны 9: чекбоксы переменных
  по поверхностям/параметрам, границы по типам, список целей с весами,
  max_iter/damping; решение — :func:`analysis.optimization.optimize`
  (GTISL: (JᵀJ+λ·diag)ΔP = −Jᵀ·оф, REVERSE_LAP §9).

Стиль — как у остальных диалогов порта (QFormLayout, QDialogButtonBox).
"""
from __future__ import annotations

import math
from typing import Iterable, List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from analysis.optimization import OptGoal, OptVariable

#: Колонки таблицы переменных: (param, заголовок).
_PARAM_COLUMNS: List[Tuple[str, str]] = [
    ('radius', 'R'), ('thickness', 'd'),
    ('conic', 'e²'), ('semi_diameter', 'SD'),
]

#: Выбор характеристик целей: (метка, kind, refs-умолчания).
_GOAL_CHOICES: List[Tuple[str, str, dict]] = [
    ("Фокусное расстояние f′", 'efl', {}),
    ("Задний фок. отрезок BFD", 'bfd', {}),
    ("Увеличение V", 'magnification', {}),
    ("Продольная сферич. (зона)", 'longitudinal', {'zone': 0.7}),
    ("Поперечная аберр. (зона)", 'transverse', {'zone': 0.7, 'field': 0.0}),
    ("RMS пятна рассеяния", 'rms_spot', {'field': 0.0}),
    ("Сумма Зейделя SI", 'seidel', {'term': 'SI'}),
    ("Сумма Зейделя SII", 'seidel', {'term': 'SII'}),
    ("Сумма Зейделя SIII", 'seidel', {'term': 'SIII'}),
    ("Сумма Зейделя SIV", 'seidel', {'term': 'SIV'}),
    ("Сумма Зейделя SV", 'seidel', {'term': 'SV'}),
    ("Астигматизм zм−zс", 'field', {'metric': 'astigmatism'}),
    ("Кома (поле)", 'field', {'metric': 'coma'}),
    ("Дисторсия", 'field', {'metric': 'distortion'}),
]


class FitDialog(QDialog):
    """Modal dialog for configuring a fit / optimization run.

    On accept, :attr:`mode` selects the сценарий, :meth:`get_parameters`
    returns the 1×1 solve configuration, :meth:`get_opt_parameters` —
    the ЛАП task (OptVariable/OptGoal lists + options).

    Attributes:
        MODE_SOLVE: Index constant for the 1×1 fit tab.
        MODE_OPTIMIZE: Index constant for the ЛАП optimization tab.
        TARGET_FOCAL: Index constant for focal-length target.
        TARGET_BFD: Index constant for back-focal-distance target.
    """

    MODE_SOLVE: int = 0
    MODE_OPTIMIZE: int = 1

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
        self.setWindowTitle("Подгонка и оптимизация")
        self.setMinimumWidth(430)

        self._num_surfaces = num_surfaces
        self._current_efl = current_efl
        self._current_bfd = current_bfd
        self._mirror_surfaces = set(mirror_surfaces or ())

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.tabs.addTab(self._build_solve_tab(), "Подгонка")
        self.tabs.addTab(self._build_optimize_tab(), "Оптимизация (ЛАП)")

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ #
    # Вкладка 1 — подгонка 1×1 (виджеты прежние, тесты порта не меняются)
    # ------------------------------------------------------------------ #

    def _build_solve_tab(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)

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
        self.surf_spin.setRange(1, max(1, self._num_surfaces))
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
        return page

    # ------------------------------------------------------------------ #
    # Вкладка 2 — оптимизация ЛАП (волна 9)
    # ------------------------------------------------------------------ #

    def _build_optimize_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # --- Переменные: чекбоксы поверхность × параметр
        vars_box = QGroupBox("Переменные (PAR)")
        vars_grid = QGridLayout(vars_box)
        self.vars_table = QTableWidget(self._num_surfaces, len(_PARAM_COLUMNS))
        self.vars_table.setHorizontalHeaderLabels(
            [title for _, title in _PARAM_COLUMNS])
        self.vars_table.setVerticalHeaderLabels(
            [str(i + 1) for i in range(self._num_surfaces)])
        self.vars_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        for row in range(self._num_surfaces):
            for col, (param, _title) in enumerate(_PARAM_COLUMNS):
                item = QTableWidgetItem()
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                # Толщина последней поверхности — зазор до плоскости
                # изображения: на параксиальные свойства не влияет.
                if param == 'thickness' and row == self._num_surfaces - 1:
                    item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                    item.setToolTip("Толщина последней поверхности — зазор\n"
                                    "до плоскости изображения (не варьируется).")
                elif param == 'thickness' and row in self._mirror_surfaces:
                    item.setToolTip("Поверхность — зеркало: изменение толщины "
                                    "сдвигает последующие поверхности вдоль\n"
                                    "сложенного хода лучей — проверьте результат.")
                self.vars_table.setItem(row, col, item)
        vars_grid.addWidget(self.vars_table, 0, 0, 1, 2)

        # Границы по типам параметров (как PAR-буквы D</D> в OPAL)
        self.bounds_spins: dict = {}
        for i, (param, title) in enumerate((_PARAM_COLUMNS[0], _PARAM_COLUMNS[1])):
            row_widget = QWidget()
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(f"Границы {title}:")
            pmin = QDoubleSpinBox(); pmax = QDoubleSpinBox()
            for sp in (pmin, pmax):
                sp.setRange(-100000, 100000)
                sp.setDecimals(3)
                sp.setSpecialValueText("—")
            pmin.setValue(pmin.minimum())   # «—» = нет границы
            pmax.setValue(pmax.maximum())
            row_lay.addWidget(lbl)
            row_lay.addWidget(pmin)
            row_lay.addWidget(QLabel(".."))
            row_lay.addWidget(pmax)
            row_lay.addStretch(1)
            vars_grid.addWidget(row_widget, 1 + i, 0, 1, 2)
            self.bounds_spins[param] = (pmin, pmax)
        layout.addWidget(vars_box)

        # --- Цели (MF/EQF): таблица характеристика/цель/вес/зона/поле
        goals_box = QGroupBox("Цели (MF)")
        goals_lay = QGridLayout(goals_box)
        self.goals_table = QTableWidget(0, 5)
        self.goals_table.setHorizontalHeaderLabels(
            ["Характеристика", "Цель", "Вес", "Зона", "Поле°"])
        self.goals_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        add_btn = QPushButton("+ цель")
        del_btn = QPushButton("− цель")
        add_btn.clicked.connect(lambda: self._add_goal_row())
        del_btn.clicked.connect(self._remove_goal_row)
        goals_lay.addWidget(self.goals_table, 0, 0, 1, 2)
        goals_lay.addWidget(add_btn, 1, 0)
        goals_lay.addWidget(del_btn, 1, 1)
        layout.addWidget(goals_box)

        # --- Управление итерациями (NSTEP / λ)
        ctl_box = QGroupBox("Итерации")
        ctl_form = QFormLayout(ctl_box)
        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 500)
        self.max_iter_spin.setValue(50)
        ctl_form.addRow("Макс. итераций (NSTEP):", self.max_iter_spin)
        self.damping_spin = QDoubleSpinBox()
        self.damping_spin.setRange(1e-6, 1e4)
        self.damping_spin.setDecimals(6)
        self.damping_spin.setValue(1.0)
        self.damping_spin.setSingleStep(0.1)
        ctl_form.addRow("Демпфирование λ₀:", self.damping_spin)
        layout.addWidget(ctl_box)

        # Дефолтная цель: f′ = текущее f′ (как EQF «зафиксировать»)
        self._add_goal_row()
        return page

    def _add_goal_row(self, choice: int = 0, target: Optional[float] = None,
                      weight: float = 1.0, zone: Optional[float] = None,
                      field: Optional[float] = None) -> None:
        """Добавить строку цели (дефолт — f′ = текущее, вес 1)."""
        row = self.goals_table.rowCount()
        self.goals_table.insertRow(row)

        combo = QComboBox()
        combo.addItems([label for label, _k, _r in _GOAL_CHOICES])
        combo.setCurrentIndex(choice)
        self.goals_table.setCellWidget(row, 0, combo)

        tgt = QDoubleSpinBox()
        tgt.setRange(-100000, 100000)
        tgt.setDecimals(4)
        tgt.setValue(self._current_efl if target is None
                     and self._current_efl is not None
                     and math.isfinite(self._current_efl) else 0.0)
        self.goals_table.setCellWidget(row, 1, tgt)

        w = QDoubleSpinBox()
        w.setRange(0.001, 1000)
        w.setDecimals(3)
        w.setValue(weight)
        self.goals_table.setCellWidget(row, 2, w)

        def _ref_spin(value: Optional[float]) -> QDoubleSpinBox:
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 1.0)
            sp.setDecimals(2)
            sp.setSpecialValueText("—")
            sp.setValue(value if value is not None else sp.minimum())
            return sp

        fld = QDoubleSpinBox()
        fld.setRange(0.0, 90.0)
        fld.setDecimals(1)
        fld.setValue(field if field is not None else 0.0)
        self.goals_table.setCellWidget(row, 4, fld)
        self.goals_table.setCellWidget(row, 3, _ref_spin(zone))

    def _remove_goal_row(self) -> None:
        """Удалить последнюю строку целей (минимум одну оставляем)."""
        if self.goals_table.rowCount() > 1:
            self.goals_table.removeRow(self.goals_table.rowCount() - 1)

    # ------------------------------------------------------------------ #
    # Internal slots (вкладка «Подгонка» — прежние)
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

    @property
    def mode(self) -> int:
        """Активный режим: :attr:`MODE_SOLVE` или :attr:`MODE_OPTIMIZE`."""
        return self.tabs.currentIndex()

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

    def get_opt_parameters(self) -> Tuple[List[OptVariable], List[OptGoal], dict]:
        """Собрать задачу ЛАП с вкладки «Оптимизация».

        Returns:
            ``(variables, goals, options)``: отмеченные переменные с
            границами по типам, цели с весами/зонами/полями и параметры
            итерационного процесса ``{'max_iter', 'damping'}``.
        """
        bounds: dict = {}
        for param, (pmin, pmax) in self.bounds_spins.items():
            lo = None if pmin.value() <= pmin.minimum() else pmin.value()
            hi = None if pmax.value() >= pmax.maximum() else pmax.value()
            bounds[param] = (lo, hi)

        variables: List[OptVariable] = []
        for row in range(self._num_surfaces):
            for col, (param, _title) in enumerate(_PARAM_COLUMNS):
                item = self.vars_table.item(row, col)
                if item is None or item.checkState() != Qt.Checked:
                    continue
                lo, hi = bounds.get(param, (None, None))
                variables.append(OptVariable(
                    surface=row, param=param,
                    pmin=lo if param in ('radius', 'thickness') else None,
                    pmax=hi if param in ('radius', 'thickness') else None))

        goals: List[OptGoal] = []
        for row in range(self.goals_table.rowCount()):
            combo = self.goals_table.cellWidget(row, 0)
            if combo is None:
                continue
            _label, kind, ref_defs = _GOAL_CHOICES[combo.currentIndex()]
            refs = dict(ref_defs)
            zone_sp = self.goals_table.cellWidget(row, 3)
            fld_sp = self.goals_table.cellWidget(row, 4)
            if 'zone' in refs and zone_sp is not None and \
                    zone_sp.value() > zone_sp.minimum():
                refs['zone'] = zone_sp.value()
            if 'field' in refs and fld_sp is not None:
                refs['field'] = fld_sp.value()
            goals.append(OptGoal(
                kind=kind,
                target=self.goals_table.cellWidget(row, 1).value(),
                weight=self.goals_table.cellWidget(row, 2).value(),
                refs=refs))

        options = {'max_iter': self.max_iter_spin.value(),
                   'damping': self.damping_spin.value()}
        return variables, goals, options
