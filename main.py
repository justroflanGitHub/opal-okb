"""
OPAL-OKB Windows 10 - PyQt5 GUI
Главное окно приложения для расчёта оптических систем
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenuBar,
    QMenu, QAction, QToolBar, QStatusBar, QTabWidget,
    QGroupBox, QLabel, QLineEdit, QComboBox, QDoubleSpinBox,
    QPushButton, QFileDialog, QMessageBox, QSplitter,
    QFormLayout, QSpinBox, QTextEdit, QFrame, QInputDialog,
    QCheckBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QColor

from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    ObjectType, ApertureType, SurfaceType,
    paraxial_trace, seidel_aberrations, create_demo_system,
    apply_vignetting
)
from visualization import OpticalSystemView
from analysis_gui import AnalysisPanel
from system_utils import reverse_system, scale_system, nearest_standard_radius, standardize_radii, get_radii_changes
from io_utils import save_json, load_json, append_system, export_protocol, STANDARD_WAVELENGTHS
from library import build_library, create_system_from_entry
from achromat import design_achromat, GLASS_PAIRS


class SurfaceTable(QTableWidget):
    """Таблица поверхностей оптической системы."""

    HEADERS = ["No", "Радиусы\nR (мм)", "Осевые\nрасст. d (мм)", "Марка\nстекла", "n (при λ)", "Высоты\nD/2 (мм)", "Тип", "k (конич.)", "Стоп"]

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setFont(QFont("Consolas", 10))
        self.setMinimumHeight(200)
        self._stop_surface = 1

    def load_system(self, sys: OpticalSystem):
        """Загрузить оптическую систему в таблицу."""
        self._stop_surface = sys.stop_surface
        self.setRowCount(len(sys.surfaces) + 1)  # +1 для плоскости изображения

        # Первичная длина волны для расчёта n
        wl_primary = sys.wavelengths[0].value if sys.wavelengths else 0.54607

        for i, s in enumerate(sys.surfaces):
            self.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.setItem(i, 1, QTableWidgetItem(f"{s.radius:.4f}" if s.radius != 0 else "∞"))
            self.setItem(i, 2, QTableWidgetItem(f"{s.thickness:.4f}"))
            self.setItem(i, 3, QTableWidgetItem(s.glass if s.glass else "ВОЗДУХ"))

            # Показатель преломления n (6 знаков)
            from optics_engine import refractive_index
            if s.glass and s.glass.upper().strip() not in ('', 'ВОЗДУХ', 'AIR'):
                n_val = refractive_index(s.glass, wl_primary, None, getattr(s, 'n_override', None))
                n_text = f"{n_val:.6f}"
            else:
                n_text = "1.000000"
            n_item = QTableWidgetItem(n_text)
            n_item.setFlags(Qt.ItemIsEnabled)  # read-only
            n_item.setTextAlignment(Qt.AlignCenter)
            n_item.setForeground(QColor(80, 80, 80))
            self.setItem(i, 4, n_item)

            self.setItem(i, 5, QTableWidgetItem(f"{s.semi_diameter:.2f}"))
            self.setItem(i, 6, QTableWidgetItem(s.surface_type.name))

            # Коническая постоянная k
            k_text = f"{s.conic_constant:.4f}" if abs(s.conic_constant) > 1e-10 else "0"
            self.setItem(i, 7, QTableWidgetItem(k_text))

            # Стоп-чекбокс
            stop_item = QTableWidgetItem()
            stop_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if i + 1 == sys.stop_surface:
                stop_item.setCheckState(Qt.Checked)
            else:
                stop_item.setCheckState(Qt.Unchecked)
            stop_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(i, 8, stop_item)

            # Выравнивание
            for col in [0, 1, 2, 5, 7]:
                item = self.item(i, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        # Строка плоскости изображения
        last = len(sys.surfaces)
        self.setItem(last, 0, QTableWidgetItem("Изобр."))
        self.setItem(last, 1, QTableWidgetItem("∞"))
        for col in range(2, self.columnCount()):
            self.setItem(last, col, QTableWidgetItem(""))

        # Подсветка стоп-поверхности
        if 0 < sys.stop_surface <= self.rowCount():
            for col in range(self.columnCount()):
                item = self.item(sys.stop_surface - 1, col)
                if item:
                    item.setBackground(QColor(255, 200, 200))  # красноватый для стопа

    def get_stop_surface(self) -> int:
        """Получить номер стоп-поверхности из таблицы."""
        for i in range(self.rowCount()):
            item = self.item(i, 8)
            if item and item.checkState() == Qt.Checked:
                return i + 1
        return self._stop_surface


class FieldPointsWidget(QWidget):
    """Виджет для управления точками поля."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        lbl = QLabel("Точки поля (Y, X, Вес)")
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Y (град/мм)", "X (град/мм)", "Вес"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMaximumHeight(120)
        self.table.setFont(QFont("Consolas", 9))
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ Точка")
        btn_add.setMaximumWidth(80)
        btn_add.clicked.connect(self._add_point)
        btn_del = QPushButton("- Удалить")
        btn_del.setMaximumWidth(80)
        btn_del.clicked.connect(self._del_point)
        btn_auto = QPushButton("Авто 3 точки")
        btn_auto.setMaximumWidth(100)
        btn_auto.clicked.connect(self._auto_points)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        btn_layout.addWidget(btn_auto)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _add_point(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem("0.0"))
        self.table.setItem(row, 1, QTableWidgetItem("0.0"))
        self.table.setItem(row, 2, QTableWidgetItem("1.0"))

    def _del_point(self):
        rows = set(i.row() for i in self.table.selectedItems())
        for r in sorted(rows, reverse=True):
            self.table.removeRow(r)

    def _auto_points(self):
        """Автоматически создать 3 точки поля."""
        # Определяем тип предмета и полное поле из родительского окна
        # Будет вызвано с system context из MainWindow
        self.table.setRowCount(3)
        self.table.setItem(0, 0, QTableWidgetItem("0.0"))
        self.table.setItem(0, 1, QTableWidgetItem("0.0"))
        self.table.setItem(0, 2, QTableWidgetItem("1.0"))
        self.table.setItem(1, 0, QTableWidgetItem("0.0"))  # Placeholder - заполнится при _calculate
        self.table.setItem(1, 1, QTableWidgetItem("0.0"))
        self.table.setItem(1, 2, QTableWidgetItem("1.0"))
        self.table.setItem(2, 0, QTableWidgetItem("0.0"))
        self.table.setItem(2, 1, QTableWidgetItem("0.0"))
        self.table.setItem(2, 2, QTableWidgetItem("1.0"))

    def load_system(self, sys: OpticalSystem):
        """Загрузить точки поля из системы."""
        if not sys.field_points:
            self.table.setRowCount(0)
            return
        self.table.setRowCount(len(sys.field_points))
        for i, fp in enumerate(sys.field_points):
            self.table.setItem(i, 0, QTableWidgetItem(f"{fp.y:.4f}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{fp.x:.4f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{fp.weight:.2f}"))

    def get_field_points(self) -> list:
        """Получить список (y, x, weight) из таблицы."""
        points = []
        for i in range(self.table.rowCount()):
            y_item = self.table.item(i, 0)
            x_item = self.table.item(i, 1)
            w_item = self.table.item(i, 2)
            y = float(y_item.text()) if y_item else 0.0
            x = float(x_item.text()) if x_item else 0.0
            w = float(w_item.text()) if w_item else 1.0
            points.append((y, x, w))
        return points


class ResultsPanel(QWidget):
    """Панель результатов расчёта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Параксиальные параметры - таблица
        parax_group = QGroupBox("Параксиальные характеристики")
        parax_layout = QVBoxLayout()

        self.parax_table = QTableWidget()
        self.parax_table.setColumnCount(2)
        self.parax_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.parax_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.parax_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.parax_table.setFocusPolicy(Qt.StrongFocus)
        self.parax_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        copy_action_parax = QAction("Копировать (Ctrl+C)", self.parax_table)
        copy_action_parax.setShortcut("Ctrl+C")
        copy_action_parax.triggered.connect(lambda: self._copy_parax_table())
        self.parax_table.addAction(copy_action_parax)
        self.parax_table.verticalHeader().setVisible(False)
        self.parax_table.setAlternatingRowColors(True)
        self.parax_table.setFont(QFont("Courier", 9))
        self.parax_table.horizontalHeader().setFont(QFont("Courier", 9, QFont.Bold))
        self.parax_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.parax_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.parax_table.setMinimumWidth(250)
        # No max width - let it expand

        # Единицы зрачков
        pupil_unit_layout = QHBoxLayout()
        pupil_unit_layout.addWidget(QLabel("Единицы зрачков:"))
        self.pupil_unit_combo = QComboBox()
        self.pupil_unit_combo.addItems(["мм", "дптр"])
        self.pupil_unit_combo.setToolTip("Единицы для sP и sP'")
        self.pupil_unit_combo.currentIndexChanged.connect(self._on_pupil_unit_changed)
        pupil_unit_layout.addWidget(self.pupil_unit_combo)
        pupil_unit_layout.addStretch()
        self._parax_result = {}
        self._current_system_ref = None

        # Мульти-λ параксиальная таблица
        self.parax_wl_table = QTableWidget()
        self.parax_wl_table.setColumnCount(4)
        self.parax_wl_table.setHorizontalHeaderLabels(["λ", "f' (мм)", "sF' (мм)", "Δf' (мм)"])
        self.parax_wl_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.parax_wl_table.verticalHeader().setVisible(False)
        self.parax_wl_table.setAlternatingRowColors(True)
        self.parax_wl_table.setFont(QFont("Courier", 9))
        self.parax_wl_table.horizontalHeader().setFont(QFont("Courier", 9, QFont.Bold))
        self.parax_wl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parax_wl_table.setMinimumWidth(250)
        self.parax_wl_table.setVisible(False)  # скрыта, пока 1 длина волны

        parax_layout.addLayout(pupil_unit_layout)
        parax_layout.addWidget(self.parax_table)
        # Подпись мульти-λ таблицы
        self.parax_wl_label = QLabel("Параксиальные по длинам волн:")
        self.parax_wl_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.parax_wl_label.setVisible(False)
        parax_layout.addWidget(self.parax_wl_label)
        parax_layout.addWidget(self.parax_wl_table)
        parax_group.setLayout(parax_layout)

        # Суммы Зейделя - таблица
        seidel_group = QGroupBox("Суммы Зейделя")
        seidel_layout = QVBoxLayout()
        self.seidel_table = QTableWidget()
        self.seidel_table.setColumnCount(2)
        self.seidel_table.setHorizontalHeaderLabels(["Сумма", "Значение"])
        self.seidel_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.seidel_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.seidel_table.setFocusPolicy(Qt.StrongFocus)
        self.seidel_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        copy_action_seidel = QAction("Копировать (Ctrl+C)", self.seidel_table)
        copy_action_seidel.setShortcut("Ctrl+C")
        copy_action_seidel.triggered.connect(lambda: self._copy_seidel_table())
        self.seidel_table.addAction(copy_action_seidel)
        self.seidel_table.verticalHeader().setVisible(False)
        self.seidel_table.setAlternatingRowColors(True)
        self.seidel_table.setFont(QFont("Courier", 9))
        self.seidel_table.horizontalHeader().setFont(QFont("Courier", 9, QFont.Bold))
        self.seidel_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.seidel_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.seidel_table.setMinimumWidth(250)
        self.seidel_table.setMaximumWidth(400)
        seidel_layout.addWidget(self.seidel_table)
        seidel_group.setLayout(seidel_layout)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 9))

        layout.addWidget(parax_group)
        layout.addWidget(seidel_group)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log_text, 1)  # stretch factor 1 — log takes extra space
        layout.addStretch()

    def _copy_parax_table(self):
        """Копирует выделенные ячейки таблицы параксиальных параметров."""
        selection = self.parax_table.selectedRanges()
        if not selection:
            return
        lines = []
        for rng in selection:
            for row in range(rng.topRow(), rng.bottomRow() + 1):
                cells = []
                for col in range(rng.leftColumn(), rng.rightColumn() + 1):
                    item = self.parax_table.item(row, col)
                    cells.append(item.text() if item else "")
                lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))

    def _copy_seidel_table(self):
        """Копирует выделенные ячейки таблицы сумм Зейделя."""
        selection = self.seidel_table.selectedRanges()
        if not selection:
            return
        lines = []
        for rng in selection:
            for row in range(rng.topRow(), rng.bottomRow() + 1):
                cells = []
                for col in range(rng.leftColumn(), rng.rightColumn() + 1):
                    item = self.seidel_table.item(row, col)
                    cells.append(item.text() if item else "")
                lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))

    def _on_pupil_unit_changed(self, index):
        """Переключение единиц зрачков мм/дптр."""
        self._update_parax_display()

    def _update_parax_display(self):
        """Заполнить таблицу параксиальных параметров."""
        if not self._parax_result:
            return
        parax = self._parax_result
        rows = [
            ("f'", f"{parax.get('focal_length', 0):.4f} мм"),
            ("BFD", f"{parax.get('back_focal_distance', 0):.4f} мм"),
            ("FFD", f"{parax.get('front_focal_distance', 0):.4f} мм"),
            ("sF", f"{parax.get('sF', 0):.4f} мм"),
            ("sF'", f"{parax.get('sF_prime', 0):.4f} мм"),
            ("sH", f"{parax.get('sH', 0):.4f} мм"),
            ("sH'", f"{parax.get('sH_prime', 0):.4f} мм"),
            ("L", f"{parax.get('L', 0):.4f} мм"),
            ("V", f"{parax.get('V', 0):.4f}"),
            ("f/#", f"{self._fno:.2f}"),
            ("D вх.зрачка", f"{self._epd:.2f} мм"),
        ]
        # sP и sP' - с учётом единиц
        sP = parax.get('sP', 0)
        sP_prime = parax.get('sP_prime', 0)
        if self.pupil_unit_combo.currentText() == "дптр":
            n = 1.0
            sP_str = f"{1000.0/n/sP:.4f} дптр" if abs(sP) > 1e-10 else "∞"
            sPp_str = f"{1000.0/n/sP_prime:.4f} дптр" if abs(sP_prime) > 1e-10 else "∞"
        else:
            sP_str = f"{sP:.4f} мм"
            sPp_str = f"{sP_prime:.4f} мм"
        rows.append(("sP (вх. зрачок)", sP_str))
        rows.append(("sP' (вых. зрачок)", sPp_str))

        self.parax_table.setRowCount(len(rows))
        for i, (name, val) in enumerate(rows):
            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            val_item = QTableWidgetItem(val)
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if i % 2 == 1:
                name_item.setBackground(QColor(240, 240, 245))
                val_item.setBackground(QColor(240, 240, 245))
            self.parax_table.setItem(i, 0, name_item)
            self.parax_table.setItem(i, 1, val_item)
        self.parax_table.setFixedHeight(26 + len(rows) * 20)
        self.parax_table.setRowCount(len(rows))  # ensure consistent

    def _update_seidel_display(self, seidel):
        """Заполнить таблицу сумм Зейделя."""
        rows = [
            ("SI - сферическая", f"{seidel.get('SI', 0):.6e}"),
            ("SII - кома", f"{seidel.get('SII', 0):.6e}"),
            ("SIII - астигматизм", f"{seidel.get('SIII', 0):.6e}"),
            ("SIV - кривизна поля", f"{seidel.get('SIV', 0):.6e}"),
            ("SV - дисторсия", f"{seidel.get('SV', 0):.6e}"),
        ]
        self.seidel_table.setRowCount(len(rows))
        for i, (name, val) in enumerate(rows):
            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            val_item = QTableWidgetItem(val)
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if i % 2 == 1:
                name_item.setBackground(QColor(240, 240, 245))
                val_item.setBackground(QColor(240, 240, 245))
            self.seidel_table.setItem(i, 0, name_item)
            self.seidel_table.setItem(i, 1, val_item)
        self.seidel_table.setFixedHeight(30 + len(rows) * 22)

    def update_results(self, sys: OpticalSystem):
        """Обновить результаты."""
        parax = paraxial_trace(sys)
        seidel = seidel_aberrations(sys)

        self._parax_result = parax
        self._current_system_ref = sys

        # f/# и входной зрачок
        fno = parax.get('f_number', 0)
        epd = parax.get('entrance_pupil_diameter', 0)
        if fno == 0:
            efl = parax.get('focal_length', 0)
            epd = sys.aperture_value if sys.aperture_value > 0 else efl / 4.0
            fno = efl / epd if epd > 0 else 0
        self._fno = fno
        self._epd = epd

        self._update_parax_display()
        self._update_seidel_display(seidel)

        # Параксиальные для всех λ
        self._update_paraxial_all_wl(sys)

        self.log_text.append(f"Расчёт: f'={parax.get('focal_length', 0):.2f} мм")
    def _update_paraxial_all_wl(self, sys: OpticalSystem):
        """Показать f', sF' и хроматические разности для каждой длины волны."""
        if len(sys.wavelengths) <= 1:
            self.parax_wl_table.setVisible(False)
            self.parax_wl_label.setVisible(False)
            return

        import copy

        # Базовое фокусное расстояние (первая λ)
        base_f = None
        base_bfd = None
        rows_data = []

        for wl in sys.wavelengths:
            wl_name = wl.name if wl.name else f"{wl.value:.3f}"
            try:
                sys_wl = copy.deepcopy(sys)
                sys_wl.wavelengths = [wl]
                parax_wl = paraxial_trace(sys_wl)
                f_wl = parax_wl.get('focal_length', 0)
                bfd_wl = parax_wl.get('back_focal_distance', 0)

                if base_f is None:
                    base_f = f_wl
                    base_bfd = bfd_wl
                    delta_f = 0.0
                else:
                    delta_f = f_wl - base_f

                rows_data.append((wl_name, f_wl, bfd_wl, delta_f))
            except Exception:
                rows_data.append((wl_name, 0, 0, 0))

        if not rows_data:
            self.parax_wl_table.setVisible(False)
            self.parax_wl_label.setVisible(False)
            return

        # Заполняем таблицу
        self.parax_wl_table.setRowCount(len(rows_data))
        for i, (wl_name, f_val, bfd_val, df_val) in enumerate(rows_data):
            items = [
                QTableWidgetItem(wl_name),
                QTableWidgetItem(f"{f_val:.4f}"),
                QTableWidgetItem(f"{bfd_val:.4f}"),
                QTableWidgetItem(f"{df_val:+.4f}" if i > 0 else "—"),
            ]
            for j, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter if j == 0 else Qt.AlignRight | Qt.AlignVCenter)
                if i % 2 == 1:
                    item.setBackground(QColor(240, 240, 245))
                self.parax_wl_table.setItem(i, j, item)

        self.parax_wl_table.setFixedHeight(28 + len(rows_data) * 20)
        self.parax_wl_table.setVisible(True)
        self.parax_wl_label.setVisible(True)

        # Дополнительно: продольная хроматическая аберрация в лог
        if len(rows_data) >= 2:
            f_min = min(r[1] for r in rows_data)
            f_max = max(r[1] for r in rows_data)
            bfd_min = min(r[2] for r in rows_data)
            bfd_max = max(r[2] for r in rows_data)
            self.log_text.append("\n── Параксиальные по λ ──")
            for wl_name, f_val, bfd_val, df_val in rows_data:
                self.log_text.append(f"  {wl_name}: f'={f_val:.4f} мм, sF'={bfd_val:.4f} мм")
            self.log_text.append(f"  Δf'(хром.) = {f_max - f_min:.4f} мм")
            self.log_text.append(f"  ΔsF'(хром.) = {bfd_max - bfd_min:.4f} мм")


class SystemParamsWidget(QWidget):
    """Параметры оптической системы (длины волн, поле, апертура)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.name_edit = QLineEdit()
        layout.addRow("Название:", self.name_edit)

        self.obj_type_combo = QComboBox()
        self.obj_type_combo.addItems(["Бесконечно удалённый предмет (∞)", "Конечный предмет"])
        layout.addRow("Тип предмета:", self.obj_type_combo)

        self.obj_height_spin = QDoubleSpinBox()
        self.obj_height_spin.setRange(-1000, 1000)
        self.obj_height_spin.setDecimals(4)
        self.obj_height_spin.setValue(5.0)
        self.obj_height_spin.setToolTip("Угловое поле (град) для ∞ или высота предмета (мм) для конечного")
        layout.addRow("Поле/высота предмета:", self.obj_height_spin)

        self.aperture_type_combo = QComboBox()
        self.aperture_type_combo.addItems(["Входной зрачок D (мм)", "Числовая апертура NA", "F/#"])
        layout.addRow("Тип апертуры:", self.aperture_type_combo)

        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(0, 10000)
        self.aperture_spin.setDecimals(4)
        self.aperture_spin.setValue(20.0)
        layout.addRow("Значение апертуры:", self.aperture_spin)

        # Виньетирование
        self.vignetting_check = QCheckBox("Виньетирование")
        self.vignetting_check.setToolTip("Отсекать лучи за пределами полудиаметра поверхностей")
        layout.addRow(self.vignetting_check)

        # Экранирование
        self.obscuration_spin = QDoubleSpinBox()
        self.obscuration_spin.setRange(0, 50)
        self.obscuration_spin.setDecimals(1)
        self.obscuration_spin.setValue(0.0)
        self.obscuration_spin.setSuffix(" %")
        self.obscuration_spin.setToolTip("Центральное экранирование (0% = нет)")
        layout.addRow("Экранирование:", self.obscuration_spin)

        # Режимы расчёта габаритов (#15)
        self.beam_mode_combo = QComboBox()
        self.beam_mode_combo.addItems(["Реальные", "Заданные"])
        self.beam_mode_combo.setToolTip("Режим расчёта габаритов")
        layout.addRow("Габариты:", self.beam_mode_combo)

        self.sharp_edge_check = QCheckBox("Острый край")
        self.sharp_edge_check.setToolTip("Учитывать острый край при расчёте габаритов")
        self.sharp_edge_check.setChecked(True)
        layout.addRow(self.sharp_edge_check)

        # Точки поля и спектральные линии — в меню Характеристики
        self.field_points_widget = FieldPointsWidget()
        self.field_points_widget.setVisible(False)  # скрытый, для загрузки/сохранения
        self.wl_table = QTableWidget(0, 3)
        self.wl_table.setHorizontalHeaderLabels(["λ (мкм)", "Вес", "Имя"])
        self.wl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.wl_table.setVisible(False)  # скрытый

    def _add_wavelength(self):
        row = self.wl_table.rowCount()
        self.wl_table.insertRow(row)
        self.wl_table.setItem(row, 0, QTableWidgetItem("0.54607"))
        self.wl_table.setItem(row, 1, QTableWidgetItem("1.0"))
        self.wl_table.setItem(row, 2, QTableWidgetItem("e"))

    def _standard_wavelengths(self):
        """Диалог выбора стандартной длины волны."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem
        dlg = QDialog(self)
        dlg.setWindowTitle("Стандартные длины волн")
        dlg.setMinimumWidth(300)
        dlg.setMinimumHeight(350)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Выберите длину волны:"))
        lst = QListWidget()
        for name, wl_val in STANDARD_WAVELENGTHS.items():
            item = QListWidgetItem(f"{name} - {wl_val*1000:.2f} нм ({wl_val:.5f} мкм)")
            item.setData(Qt.UserRole, (name, wl_val))
            lst.addItem(item)
        layout.addWidget(lst)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        lst.itemDoubleClicked.connect(lambda: dlg.accept())
        if dlg.exec_() == QDialog.Accepted:
            sel = lst.selectedItems()
            if sel:
                name, wl_val = sel[0].data(Qt.UserRole)
                row = self.wl_table.rowCount()
                self.wl_table.insertRow(row)
                self.wl_table.setItem(row, 0, QTableWidgetItem(str(wl_val)))
                self.wl_table.setItem(row, 1, QTableWidgetItem("1.0"))
                self.wl_table.setItem(row, 2, QTableWidgetItem(name))

    def _del_wavelength(self):
        rows = set(i.row() for i in self.wl_table.selectedItems())
        for r in sorted(rows, reverse=True):
            self.wl_table.removeRow(r)

    def load_system(self, sys: OpticalSystem):
        self.name_edit.setText(sys.name)
        self.obj_type_combo.setCurrentIndex(0 if sys.object_type == ObjectType.INFINITE else 1)
        self.obj_height_spin.setValue(sys.object_height)
        self.aperture_type_combo.setCurrentIndex(sys.aperture_type.value)
        self.aperture_spin.setValue(sys.aperture_value)

        # Экранирование
        self.obscuration_spin.setValue(getattr(sys, 'obscuration_ratio', 0.0) * 100)

        # Режимы габаритов (#15)
        beam_mode = getattr(sys, 'beam_mode', 'real')
        self.beam_mode_combo.setCurrentIndex(0 if beam_mode == 'real' else 1)
        self.sharp_edge_check.setChecked(getattr(sys, 'sharp_edge', True))

        # Точки поля
        self.field_points_widget.load_system(sys)

        self.wl_table.setRowCount(len(sys.wavelengths))
        for i, wl in enumerate(sys.wavelengths):
            self.wl_table.setItem(i, 0, QTableWidgetItem(str(wl.value)))
            self.wl_table.setItem(i, 1, QTableWidgetItem(str(wl.weight)))
            self.wl_table.setItem(i, 2, QTableWidgetItem(wl.name))


class MainWindow(QMainWindow):
    """Главное окно OPAL-OKB."""

    def __init__(self):
        super().__init__()
        self.current_system = OpticalSystem()
        self._current_file = None
        self._init_ui()
        self._init_new_system()  # Silent init, no dialog

    def _init_ui(self):
        self.setWindowTitle("OPAL-OKB - САПР Оптических Систем")
        self.setMinimumSize(1100, 700)
        self.setFont(QFont("Segoe UI", 10))

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Left: Surface table + params
        left_splitter = QSplitter(Qt.Vertical)

        # Surface table
        surf_group = QGroupBox("Конструктивные параметры")
        surf_layout = QVBoxLayout()
        self.surface_table = SurfaceTable()
        surf_layout.addWidget(self.surface_table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_add_surf = QPushButton("+ Поверхность")
        self.btn_add_surf.clicked.connect(self._add_surface)
        self.btn_del_surf = QPushButton("- Удалить")
        self.btn_del_surf.clicked.connect(self._del_surface)
        self.btn_calc = QPushButton("⚙ Рассчитать")
        self.btn_calc.clicked.connect(self._calculate)
        self.btn_calc.setStyleSheet("background-color: #3a6ea5; color: white; font-weight: bold; padding: 5px 15px;")
        btn_layout.addWidget(self.btn_add_surf)
        btn_layout.addWidget(self.btn_del_surf)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_calc)
        surf_layout.addLayout(btn_layout)
        surf_group.setLayout(surf_layout)

        # System params
        self.sys_params = SystemParamsWidget()

        left_splitter.addWidget(surf_group)
        left_splitter.addWidget(self.sys_params)
        left_splitter.setSizes([400, 300])

        # Right: Visualization + Results
        right_splitter = QSplitter(Qt.Vertical)

        # Visualization with controls
        viz_group = QGroupBox("Ход лучей")
        viz_layout = QVBoxLayout()
        viz_layout.setContentsMargins(2, 2, 2, 2)

        # Zoom controls bar
        viz_ctrl = QHBoxLayout()
        viz_ctrl.setContentsMargins(0, 0, 0, 0)

        # Create viz widget FIRST (before connecting signals)
        self.viz = OpticalSystemView()

        self.btn_viz_fit = QPushButton("Сброс")
        self.btn_viz_fit.setMaximumWidth(70)
        self.btn_viz_fit.clicked.connect(lambda: self.viz.reset_view())
        self.btn_viz_zoomin = QPushButton("Z+")
        self.btn_viz_zoomin.setMaximumWidth(45)
        self.btn_viz_zoomin.clicked.connect(lambda: self.viz.zoom_in())
        self.btn_viz_zoomout = QPushButton("Z-")
        self.btn_viz_zoomout.setMaximumWidth(45)
        self.btn_viz_zoomout.clicked.connect(lambda: self.viz.zoom_out())
        self.lbl_zoom = QLabel("1.0x")
        self.lbl_zoom.setMaximumWidth(40)
        self.viz.zoom_changed.connect(lambda z: self.lbl_zoom.setText(f"{z:.1f}x"))

        # Кнопка таблицы координат лучей (#7)
        self.btn_ray_table = QPushButton("Таблица")
        self.btn_ray_table.setMaximumWidth(70)
        self.btn_ray_table.setToolTip("Таблица координат габаритных лучей")
        self.btn_ray_table.clicked.connect(self._show_ray_table)

        # Переключатель 2D/3D для волнового фронта (#10)
        self.btn_wf_3d = QPushButton("2D/3D")
        self.btn_wf_3d.setMaximumWidth(55)
        self.btn_wf_3d.setToolTip("Переключить 2D/3D вид волнового фронта")
        self.btn_wf_3d.clicked.connect(self._toggle_wavefront_3d)

        # Переключатель хроматических лучей (#8)
        self.btn_zernike_chrom = QPushButton("Хром.Ц")
        self.btn_zernike_chrom.setMaximumWidth(60)
        self.btn_zernike_chrom.setCheckable(True)
        self.btn_zernike_chrom.setToolTip("Показывать лучи для всех длин волн")
        self.btn_zernike_chrom.clicked.connect(self._toggle_chromatic_rays)

        viz_ctrl.addWidget(self.btn_viz_fit)
        viz_ctrl.addWidget(self.btn_viz_zoomin)
        viz_ctrl.addWidget(self.btn_viz_zoomout)
        viz_ctrl.addWidget(self.lbl_zoom)
        viz_ctrl.addWidget(self.btn_ray_table)
        viz_ctrl.addWidget(self.btn_wf_3d)
        viz_ctrl.addWidget(self.btn_zernike_chrom)
        viz_ctrl.addStretch()
        viz_layout.addLayout(viz_ctrl)

        viz_layout.addWidget(self.viz)
        viz_group.setLayout(viz_layout)

        self.results = ResultsPanel()  # Kept for compat (tests access w.results.parax_table)
        self.analysis = AnalysisPanel()
        right_splitter.addWidget(viz_group)
        right_splitter.addWidget(self.analysis)
        right_splitter.setSizes([300, 400])

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_splitter)
        splitter.addWidget(right_splitter)
        splitter.setSizes([600, 500])

        main_layout.addWidget(splitter)

        # Menu bar
        self._create_menu()

        # Toolbar
        self._create_toolbar()

        # Status bar
        self.statusBar().showMessage("Готово")

    def _create_menu(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("&Файл")

        new_action = QAction("&Новая система", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_system)
        file_menu.addAction(new_action)

        open_action = QAction("&Открыть...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        save_action = QAction("&Сохранить", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)

        saveas_action = QAction("Сохранить &как...", self)
        saveas_action.setShortcut("Ctrl+Shift+S")
        saveas_action.triggered.connect(self._save_file_as)
        file_menu.addAction(saveas_action)

        file_menu.addSeparator()

        append_action = QAction("Присоединить...", self)
        append_action.triggered.connect(self._append_system)
        file_menu.addAction(append_action)

        library_action = QAction("Библиотека...", self)
        library_action.triggered.connect(self._show_library)
        file_menu.addAction(library_action)

        export_action = QAction("Экспорт протокола...", self)
        export_action.triggered.connect(self._export_protocol)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        demo_action = QAction("Демо: &Линза", self)
        demo_action.setShortcut("Ctrl+D")
        demo_action.triggered.connect(self._load_demo)
        file_menu.addAction(demo_action)

        from PyQt5.QtWidgets import QMenu
        demo_menu = QMenu("Демо примеры", self)
        demos = [
            ("Тонкая линза (f'=77)", self._load_demo),
            ("Ахромат (2 линзы)", lambda: self._load_demo_by_name("achromat")),
            ("Дублет Кука f/5", lambda: self._load_demo_by_name("cook_doublet")),
            ("Телеобъектив", lambda: self._load_demo_by_name("telephoto")),
            ("Объектив Петцваля", lambda: self._load_demo_by_name("petzval")),
            ("Зеркало (вогнутое)", lambda: self._load_demo_by_name("mirror")),
            ("Мениск (Росс)", lambda: self._load_demo_by_name("meniscus")),
            ("Плоско-выпуклая линза", lambda: self._load_demo_by_name("plano_convex")),
        ]
        for title, fn in demos:
            act = demo_menu.addAction(title)
            act.triggered.connect(fn)
        file_menu.addMenu(demo_menu)

        file_menu.addSeparator()

        exit_action = QAction("&Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Система
        sys_menu = menubar.addMenu("&Система")

        reverse_action = QAction("&Обернуть", self)
        reverse_action.triggered.connect(self._reverse_system)
        sys_menu.addAction(reverse_action)

        scale_action = QAction("&Масштаб...", self)
        scale_action.triggered.connect(self._scale_system)
        sys_menu.addAction(scale_action)

        sys_menu.addSeparator()

        gost_action = QAction("Стандартные &радиусы (ГОСТ)...", self)
        gost_action.triggered.connect(self._standardize_radii)
        sys_menu.addAction(gost_action)

        sys_menu.addSeparator()

        achromat_action = QAction("&Ахромат...", self)
        achromat_action.triggered.connect(self._design_achromat)
        sys_menu.addAction(achromat_action)

        sys_menu.addSeparator()

        fit_action = QAction("&Подгонка...", self)
        fit_action.triggered.connect(self._fit_dialog)
        sys_menu.addAction(fit_action)

        # Характеристики
        char_menu = menubar.addMenu("&Характеристики")

        field_action = QAction("&Точки поля...", self)
        field_action.triggered.connect(lambda: self._show_field_points_dialog())
        char_menu.addAction(field_action)

        spectral_action = QAction("&Спектральные линии...", self)
        spectral_action.triggered.connect(lambda: self._show_spectral_dialog())
        char_menu.addAction(spectral_action)

        # Вид
        view_menu = menubar.addMenu("&Вид")

        glass_diag_action = QAction("Диаграмма &стёкол", self)
        glass_diag_action.triggered.connect(self._show_glass_diagram)
        view_menu.addAction(glass_diag_action)

        # Расчёт
        calc_menu = menubar.addMenu("&Расчёт")

        parax_action = QAction("Параксиальный &расчёт", self)
        parax_action.triggered.connect(self._calculate)
        calc_menu.addAction(parax_action)

        seidel_action = QAction("Суммы &Зейделя", self)
        seidel_action.triggered.connect(self._calculate)
        calc_menu.addAction(seidel_action)

        # Помощь
        help_menu = menubar.addMenu("&Помощь")
        about_action = QAction("&О программе", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        toolbar = QToolBar("Основная")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        toolbar.addAction("📄 Новый", self._new_system)
        toolbar.addAction("🔧 Демо", self._load_demo)
        toolbar.addSeparator()
        toolbar.addAction("▶ Рассчитать", self._calculate)

    def _init_new_system(self):
        """Silent init - no dialog, just defaults."""
        from optics_engine import _std_wavelengths
        self.current_system = OpticalSystem(name="Новая система")
        self.current_system.wavelengths = _std_wavelengths()
        self.current_system.field_points = [FieldPoint(0.0)]
        self.current_system.stop_surface = 1
        self._current_file = None

    def _new_system(self):
        # #17: Диалог выбора типа системы
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QRadioButton, QButtonGroup, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Новая система")
        dlg.setMinimumWidth(300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Тип системы:"))

        btn_group = QButtonGroup(dlg)
        rb_centered = QRadioButton("Центрированная")
        rb_centered.setChecked(True)
        rb_spatial = QRadioButton("Пространственная")
        rb_spatial.setEnabled(False)
        rb_spatial.setToolTip("Не реализовано")
        btn_group.addButton(rb_centered)
        btn_group.addButton(rb_spatial)
        layout.addWidget(rb_centered)
        layout.addWidget(rb_spatial)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        self.current_system = OpticalSystem(name="Новая система")
        from optics_engine import _std_wavelengths
        self.current_system.wavelengths = _std_wavelengths()
        self.current_system.field_points = [FieldPoint(0.0)]
        self.current_system.stop_surface = 1
        self._current_file = None
        self._refresh_ui()
        self.statusBar().showMessage("Новая система создана")

    def _load_demo(self):
        self.current_system = create_demo_system()
        self._refresh_ui()
        self.statusBar().showMessage("Демо-система загружена")

    def _load_demo_by_name(self, name):
        from optics_engine import create_demo_system_by_name
        self.current_system = create_demo_system_by_name(name)
        self._refresh_ui()
        self.statusBar().showMessage(f"Демо: {self.current_system.name}")

    def _refresh_ui(self):
        self.surface_table.load_system(self.current_system)
        self.sys_params.load_system(self.current_system)
        self.results.log_text.clear()
        self.viz.set_system(self.current_system, trace_rays=False)

    def _add_surface(self):
        """Вставить пустую поверхность перед текущей строкой."""
        rows = self.surface_table.selectionModel().selectedRows()
        if rows:
            idx = rows[0].row()
        else:
            idx = len(self.current_system.surfaces)
        # Clamp to valid range
        idx = max(0, min(idx, len(self.current_system.surfaces)))
        s = Surface()
        self.current_system.surfaces.insert(idx, s)
        self._refresh_ui()
        self.statusBar().showMessage(f"Поверхность вставлена перед S{idx+1}")

    def _del_surface(self):
        """Удалить выбранные поверхности."""
        rows = sorted(set(i.row() for i in self.surface_table.selectedItems()), reverse=True)
        if not rows:
            self.statusBar().showMessage("Выберите поверхность для удаления")
            return
        for r in rows:
            if r < len(self.current_system.surfaces):
                del self.current_system.surfaces[r]
        self._refresh_ui()
        self.statusBar().showMessage(f"Удалено поверхностей: {len(rows)}")

    def _calculate(self):
        """Собрать данные из таблицы и рассчитать."""
        sys = self.current_system

        # Защита от пустой системы
        if not sys.surfaces:
            self.statusBar().showMessage("Нет поверхностей")
            return

        # Обновить поверхности из таблицы
        for i in range(min(self.surface_table.rowCount(), len(sys.surfaces))):
            r_item = self.surface_table.item(i, 1)
            d_item = self.surface_table.item(i, 2)
            g_item = self.surface_table.item(i, 3)
            sd_item = self.surface_table.item(i, 5)

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
            k_item = self.surface_table.item(i, 7)
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

        sys.stop_surface = self.surface_table.get_stop_surface()
        sys.name = self.sys_params.name_edit.text()
        sys.object_type = ObjectType.INFINITE if self.sys_params.obj_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.object_height = self.sys_params.obj_height_spin.value()
        sys.aperture_type = ApertureType(self.sys_params.aperture_type_combo.currentIndex())
        sys.aperture_value = self.sys_params.aperture_spin.value()
        sys.obscuration_ratio = self.sys_params.obscuration_spin.value() / 100.0
        sys.beam_mode = "real" if self.sys_params.beam_mode_combo.currentIndex() == 0 else "given"
        sys.sharp_edge = self.sys_params.sharp_edge_check.isChecked()
        fp_data = self.sys_params.field_points_widget.get_field_points()
        sys.field_points = [FieldPoint(y=y, x=x, weight=w) for y, x, w in fp_data]
        sys.wavelengths = []
        for i in range(self.sys_params.wl_table.rowCount()):
            wl_val = float(self.sys_params.wl_table.item(i, 0).text())
            wl_w = float(self.sys_params.wl_table.item(i, 1).text())
            wl_n = self.sys_params.wl_table.item(i, 2).text() if self.sys_params.wl_table.item(i, 2) else ""
            sys.wavelengths.append(Wavelength(wl_val, wl_w, wl_n))

        # Запустить расчёт (асинхронный или синхронный для тестов)
        self._run_calc(sys)

    def _run_calc(self, sys, sync=False):
        """Запустить расчёт — Phase 1 sync (быстро), Phase 2 async (тяжёлый)."""
        # Phase 1: быстрые вычисления (синхронно, < 0.5 сек)
        phase1_data = self._do_calc_phase1(sys)

        # Немедленное обновление GUI: ход лучей + parax + seidel
        self._update_parax_and_seidel(sys, phase1_data)
        self.surface_table.load_system(sys)
        self.viz.set_system(sys, trace_rays=True)

        if sync:
            # Sync mode: выполнить Фазу 2 сразу
            defocus = self.analysis.get_defocus_offset() if hasattr(self.analysis, 'defocus_spin') else 0.0
            azimuth = self.analysis.get_azimuth() if hasattr(self.analysis, 'azimuth_spin') else 0.0
            phase2_data = self._do_calc_phase2(sys, defocus, azimuth)
            self._update_after_calc(sys, phase1_data, phase2_data)
            return

        # Показать промежуточный результат
        f_text = self.results.parax_table.item(0, 1).text() if self.results.parax_table.rowCount() > 0 else "—"
        self.statusBar().showMessage(f"Расчёт анализа... f'={f_text}")

        # Phase 2: тяжёлые вычисления (в Worker потоке)
        self.btn_calc.setEnabled(False)
        self.btn_calc.setText("⏳ Анализ...")

        from PyQt5.QtCore import QThread
        from worker import Worker

        # Cleanup previous thread if still running
        if hasattr(self, '_calc_thread') and self._calc_thread.isRunning():
            self._calc_thread.quit()
            self._calc_thread.wait(1000)

        # Capture GUI values BEFORE starting thread
        defocus = self.analysis.get_defocus_offset() if hasattr(self.analysis, 'defocus_spin') else 0.0
        azimuth = self.analysis.get_azimuth() if hasattr(self.analysis, 'azimuth_spin') else 0.0

        self._calc_thread = QThread()
        self._calc_worker = Worker(self._do_calc_phase2, sys, defocus, azimuth)
        self._calc_worker.moveToThread(self._calc_thread)
        self._calc_thread.started.connect(self._calc_worker.run)
        self._calc_worker.finished.connect(lambda r: self._update_after_calc(sys, phase1_data, r))
        self._calc_worker.error.connect(lambda e: self._on_calc_error(e))
        self._calc_worker.finished.connect(self._calc_thread.quit)
        self._calc_thread.start()

    def _do_calc_phase1(self, sys):
        """Фаза 1: Быстрые вычисления — paraxial, Seidel, spot diagram. < 0.5 сек."""
        from optics_engine import paraxial_trace, seidel_aberrations
        from aberrations import compute_spot_diagram

        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        return {
            'parax': paraxial_trace(sys),
            'seidel': seidel_aberrations(sys),
            'spots': compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=0.0),
        }

    def _do_calc_phase2(self, sys, defocus, azimuth):
        """Фаза 2: Тяжёлые вычисления — fans, MTF, PSF, Zernike и т.д.
        Работает в Worker потоке."""
        import math, numpy as np
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from optics_engine import paraxial_trace, compute_beam_geometry
        from aberrations import (
            compute_spot_diagram, compute_rms_spot, compute_spot_diagram_polychromatic,
            compute_polychromatic_rms, trace_aberration_fan, compute_field_aberrations,
            compute_focus_curve, compute_spot_diagram_at_defocus, compute_rms_spot_xy,
            compute_geometric_mtf, compute_chief_ray_characteristics, compute_isoplanatism
        )
        from diffraction_mtf import compute_diffraction_mtf, compute_diffraction_limited_mtf
        from advanced_analysis import compute_psf, compute_lsf, compute_esf, compute_enc, compute_ptf, compute_bar_target_mtf_table, compute_bar_target_image
        from zernike import compute_zernike_coefficients, compute_zernike_chromatic, compute_wavefront_map_2d

        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        wl_list = [w.value for w in sys.wavelengths] if sys.wavelengths else [0.58756]
        n_workers = min(8, max(2, __import__('os').cpu_count() or 4))

        results = {}

        # parax нужен для focus diagrams
        parax = paraxial_trace(sys)

        # spots_mono нужен как вход для нескольких вычислений
        spots_mono = compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=0.0)
        results['spots_mono'] = spots_mono
        results['rms'] = compute_rms_spot(spots_mono)

        # Polychromatic
        if len(sys.wavelengths) > 1:
            results['spots_poly'] = compute_spot_diagram_polychromatic(sys, num_rays=40, field_y=0.0)
            results['poly_rms'] = compute_polychromatic_rms(sys, num_rays=40, field_y=0.0)
            results['poly_rms_xy'] = compute_rms_spot_xy([(dx, dy) for dx, dy, _ in results['spots_poly']])
            results['poly_max'] = max((math.sqrt(dx**2+dy**2) for dx, dy, _ in results['spots_poly']), default=0)
        else:
            results['spots_poly'] = [(dx, dy, 0) for dx, dy in spots_mono]
            results['poly_rms'] = results['rms']
            results['poly_rms_xy'] = {}
            results['poly_max'] = 0

        # Parallel independent heavy computations
        parallel_tasks = {}

        def _task_fan():
            fans = {w: trace_aberration_fan(sys, w, num_rays=30) for w in wl_list}
            iso = {}
            try:
                for w in wl_list:
                    iso[w] = compute_isoplanatism(sys, wl=w, num_rays=30)
            except:
                pass
            return (fans, iso)

        def _task_field():
            return compute_field_aberrations(sys, wl=wl)

        def _task_geo_mtf():
            return compute_geometric_mtf(spots_mono)

        def _task_diff_mtf():
            return compute_diffraction_mtf(sys, wl=wl)

        def _task_diff_ltd():
            return compute_diffraction_limited_mtf(sys, wl=wl)

        def _task_focus():
            return compute_focus_curve(sys, wl=wl, num_points=40,
                defocus_range=2.0, freq_lpmm=50.0, num_rays=25, field_y=0.0)

        def _task_psf():
            try:
                return compute_psf(sys, wl=wl, num_rays=64)
            except:
                return None

        def _task_lsf():
            try:
                t, ax1 = compute_lsf(sys, wl=wl, num_rays=64, direction='tangential')
                s, ax2 = compute_lsf(sys, wl=wl, num_rays=64, direction='sagittal')
                return (t, ax1, s, ax2)
            except:
                return None

        def _task_esf():
            try:
                return compute_esf(sys, wl=wl)
            except:
                return None

        def _task_enc():
            try:
                return compute_enc(sys, wl=wl, num_rays=100)
            except:
                return None

        def _task_ptf():
            try:
                return compute_ptf(sys, wl=wl, num_rays=64)
            except:
                return None

        def _task_beam():
            return compute_beam_geometry(sys)

        def _task_chief():
            return compute_chief_ray_characteristics(sys)

        def _task_zernike():
            try:
                c = compute_zernike_coefficients(sys, wl=wl, num_rays=32, max_order=4, defocus_offset=defocus)
                ch = compute_zernike_chromatic(sys, num_rays=32, max_order=4) if len(sys.wavelengths) > 1 else None
                return (c, ch)
            except:
                return ([], None)

        def _task_wfmap():
            try:
                wf, coords, mask = compute_wavefront_map_2d(sys, wl=wl, grid_size=48, defocus_offset=defocus)
                return (wf, coords, mask)
            except:
                return None

        def _task_bar():
            try:
                x, ideal, blurred = compute_bar_target_image(sys, wl=wl, field_y=0.0, num_bars=5, bar_freq_lp_mm=10)
                mtf = compute_bar_target_mtf_table(sys, wl=wl, field_y=0.0, num_bars=5)
                return {'bar_x': x, 'bar_ideal': ideal, 'bar_blurred': blurred, 'bar_mtf_table': mtf}
            except:
                return None

        task_map = {
            'fan_data': _task_fan, 'field_aberr': _task_field,
            'geo_mtf': _task_geo_mtf, 'diff_mtf': _task_diff_mtf,
            'diff_ltd': _task_diff_ltd, 'focus_curve': _task_focus,
            'psf_data': _task_psf, 'lsf': _task_lsf,
            'esf': _task_esf, 'enc': _task_enc, 'ptf_data': _task_ptf,
            'beam_data': _task_beam, 'chief_data': _task_chief,
            'zernike': _task_zernike, 'wfmap': _task_wfmap,
            'bar_mtf': _task_bar,
        }

        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(fn): key for key, fn in task_map.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    result = future.result()
                    if key == 'lsf' and result:
                        results['lsf_t'], results['lsf_ax1'], results['lsf_s'], results['lsf_ax2'] = result
                    elif key == 'zernike':
                        results['zernike_coeffs'], results['zernike_chromatic'] = result
                    elif key == 'enc' and result:
                        results['enc_r'], results['enc_e'] = result
                    elif key == 'fan_data' and isinstance(result, tuple):
                        fans, iso = result
                        results['fan_data'] = fans
                        results['isoplanatism'] = iso
                    elif key == 'esf' and result:
                        results['esf_x'], results['esf_y'] = result
                    elif key == 'bar_mtf' and isinstance(result, dict):
                        results.update(result)
                    else:
                        results[key] = result
                except Exception:
                    results[key] = None

        # Focus diagrams (depends on parax results)
        ds = abs(parax.get('longitudinal_spherical', 0)) if parax.get('longitudinal_spherical') else 0.1
        results['focus_diagrams'] = {}
        all_spots = []
        for label, df in [("номинал", 0), ("+DS'", ds), ("-DS'", -ds), ("+2DS'", 2*ds), ("-2DS'", -2*ds)]:
            try:
                spots = compute_spot_diagram_at_defocus(sys, wl=wl, num_rays=60, field_y=0.0, defocus_mm=df)
                rms_info = compute_rms_spot_xy(spots)
                results['focus_diagrams'][label] = (spots, rms_info, df)
                all_spots.extend(spots)
            except:
                pass
        results['focus_diag_max'] = max((math.sqrt(dx**2+dy**2) for dx, dy in all_spots), default=1e-6) if all_spots else 1e-6

        return results

    def _on_calc_error(self, err):
        self.btn_calc.setEnabled(True)
        self.btn_calc.setText("⚙ Рассчитать")
        self.statusBar().showMessage(f"Ошибка расчёта: {err[:80]}")

    def _update_after_calc(self, sys, phase1_data=None, phase2_data=None):
        """Обновить GUI после расчёта.

        Совместимость с тестами: если вызван с одним аргументом (sys),
        пересчитывает всё на месте.
        Полный режим: (sys, phase1_data, phase2_data).
        """
        if sys is None:
            return
        self.current_system = sys
        self.btn_calc.setEnabled(True)
        self.btn_calc.setText("⚙ Рассчитать")

        if phase1_data is None and phase2_data is None:
            # Backward compat path (tests): compute everything fresh
            self._update_parax_and_seidel(sys, None)
            self.surface_table.load_system(sys)
            self.viz.set_system(sys, trace_rays=True)
            self.analysis.analyze(sys)
            f_text = self.results.parax_table.item(0, 1).text() if self.results.parax_table.rowCount() > 0 else "—"
            self.statusBar().showMessage(f"Расчёт выполнен: f'={f_text}")
            return

        # Объединить данные обеих фаз
        data = {}
        if phase1_data:
            data['parax'] = phase1_data['parax']
            data['seidel'] = phase1_data['seidel']
            data['spots_mono'] = phase1_data['spots']
        if phase2_data:
            data.update(phase2_data)

        self._update_parax_and_seidel(sys, data)
        self.surface_table.load_system(sys)
        self.viz.set_system(sys, trace_rays=True)
        if data:
            self.analysis.apply_results(sys, data)
        else:
            self.analysis.analyze(sys)
        f_text = self.results.parax_table.item(0, 1).text() if self.results.parax_table.rowCount() > 0 else "—"
        self.statusBar().showMessage(f"Расчёт выполнен: f'={f_text}")

    def _update_parax_and_seidel(self, sys, data=None):
        """Update paraxial + seidel in ResultsPanel (compat) and AnalysisPanel."""
        # Get parax from data or compute
        if data and 'parax' in data:
            parax = data['parax']
        else:
            parax = paraxial_trace(sys)

        # ResultsPanel — backward compat (tests access w.results.parax_table)
        self.results._parax_result = parax
        self.results._current_system_ref = sys

        # f/# and entrance pupil
        fno = parax.get('f_number', 0)
        epd = parax.get('entrance_pupil_diameter', 0)
        if fno == 0:
            efl = parax.get('focal_length', 0)
            epd = sys.aperture_value if sys.aperture_value > 0 else efl / 4.0
            fno = efl / epd if epd > 0 else 0
        self.results._fno = fno
        self.results._epd = epd
        self.results._update_parax_display()

        # Seidel
        if data and 'seidel' in data:
            seidel = data['seidel']
        else:
            seidel = seidel_aberrations(sys)

        self.analysis.update_parax(parax, fno, epd, sys=sys)
        self.analysis.update_seidel(seidel)
        self.results._update_paraxial_all_wl(sys)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть оптическую систему", "",
            "OPJ files (*.opj);;JSON (*.opal.json);;Все файлы (*)")
        if not path:
            return
        try:
            if path.lower().endswith('.opj'):
                from opj_reader import load_opj
                self.current_system, _info = load_opj(path)
            else:
                self.current_system = load_json(path)
            self._current_file = path
            self._refresh_ui()
            self.statusBar().showMessage(f"Загружено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")

    def _save_file(self):
        if self._current_file:
            try:
                self._collect_system_from_ui()
                save_json(self.current_system, self._current_file)
                self.statusBar().showMessage(f"Сохранено: {self._current_file}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")
        else:
            self._save_file_as()

    def _save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить оптическую систему", "",
            "OPAL files (*.opal.json);;JSON (*.json)")
        if not path:
            return
        # Ensure .opal.json extension
        if not path.endswith(".opal.json") and not path.endswith(".json"):
            path += ".opal.json"
        try:
            self._collect_system_from_ui()
            save_json(self.current_system, path)
            self._current_file = path
            self.statusBar().showMessage(f"Сохранено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")

    def _collect_system_from_ui(self):
        """Собрать текущие данные из UI в current_system (без запуска расчёта)."""
        sys = self.current_system
        # Поверхности
        for i in range(min(self.surface_table.rowCount(), len(sys.surfaces))):
            r_item = self.surface_table.item(i, 1)
            d_item = self.surface_table.item(i, 2)
            g_item = self.surface_table.item(i, 3)
            sd_item = self.surface_table.item(i, 5)
            if r_item:
                txt = r_item.text().strip()
                sys.surfaces[i].radius = float(txt) if txt not in ("∞", "inf", "") else 0.0
            if d_item:
                txt = d_item.text().strip()
                sys.surfaces[i].thickness = float(txt) if txt else 0.0
            if g_item:
                glass = g_item.text().strip()
                sys.surfaces[i].glass = glass
                # Поддержка зеркал
                if glass.upper() in ("ЗЕРКАЛО", "MIRROR"):
                    sys.surfaces[i].is_reflective = True
                else:
                    sys.surfaces[i].is_reflective = False
            if sd_item:
                txt = sd_item.text().strip()
                sys.surfaces[i].semi_diameter = float(txt) if txt else 0.0
            # Коническая постоянная k
            k_item = self.surface_table.item(i, 7)
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
        # Стоп-поверхность
        sys.stop_surface = self.surface_table.get_stop_surface()
        # Параметры
        sys.name = self.sys_params.name_edit.text()
        sys.object_type = ObjectType.INFINITE if self.sys_params.obj_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.object_height = self.sys_params.obj_height_spin.value()
        sys.aperture_type = ApertureType(self.sys_params.aperture_type_combo.currentIndex())
        sys.aperture_value = self.sys_params.aperture_spin.value()
        # Экранирование
        sys.obscuration_ratio = self.sys_params.obscuration_spin.value() / 100.0
        # Режимы габаритов (#15)
        sys.beam_mode = "real" if self.sys_params.beam_mode_combo.currentIndex() == 0 else "given"
        sys.sharp_edge = self.sys_params.sharp_edge_check.isChecked()
        # Точки поля
        fp_data = self.sys_params.field_points_widget.get_field_points()
        sys.field_points = [FieldPoint(y=y, x=x, weight=w) for y, x, w in fp_data]
        # Длины волн
        sys.wavelengths = []
        for i in range(self.sys_params.wl_table.rowCount()):
            wl_val = float(self.sys_params.wl_table.item(i, 0).text())
            wl_w = float(self.sys_params.wl_table.item(i, 1).text())
            wl_n = self.sys_params.wl_table.item(i, 2).text() if self.sys_params.wl_table.item(i, 2) else ""
            sys.wavelengths.append(Wavelength(wl_val, wl_w, wl_n))

    def _reverse_system(self):
        """Обернуть оптическую систему."""
        if not self.current_system.surfaces:
            self.statusBar().showMessage("Нет поверхностей для оборачивания")
            return
        self.current_system = reverse_system(self.current_system)
        self._refresh_ui()
        self.statusBar().showMessage("Система обращена. Нажмите «Рассчитать»")

    def _scale_system(self):
        """Масштабировать оптическую систему."""
        factor, ok = QInputDialog.getDouble(
            self, "Масштабирование",
            "Коэффициент масштабирования:",
            1.0, -1e6, 1e6, 6
        )
        if not ok or abs(factor) < 1e-15:
            return
        try:
            self.current_system = scale_system(self.current_system, factor)
            self._refresh_ui()
            self.statusBar().showMessage(f"Система масштабирована (×{factor:.4g})")
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def _standardize_radii(self):
        """Показать диалог приведения радиусов к ГОСТ 1807-75."""
        self._collect_system_from_ui()
        changes = get_radii_changes(self.current_system)

        if not changes:
            QMessageBox.information(self, "Стандартные радиусы",
                "Все радиусы уже соответствуют ГОСТ 1807-75.")
            return

        # Диалог с таблицей изменений
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Стандартные радиусы (ГОСТ 1807-75)")
        dlg.setIcon(QMessageBox.Question)

        # Текст таблицы
        lines = ["<table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;'>"]
        lines.append("<tr><th>Поверхность</th><th>Старый R (мм)</th><th>Новый R (мм)</th><th>Δ%</th></tr>")
        for idx, old_r, new_r, d_pct in changes:
            color = "red" if abs(d_pct) > 1.0 else ("orange" if abs(d_pct) > 0.5 else "green")
            lines.append(f"<tr><td>S{idx+1}</td><td>{old_r:.4f}</td><td>{new_r:.4f}"
                         f"</td><td style='color:{color}'>{d_pct:+.3f}%</td></tr>")
        lines.append("</table>")
        dlg.setInformativeText(f"Заменить {len(changes)} радиусов?")
        dlg.setText("".join(lines))
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.Yes)

        if dlg.exec_() == QMessageBox.Yes:
            self.current_system = standardize_radii(self.current_system)
            self._refresh_ui()
            self.statusBar().showMessage(f"Радиусы приведены к ГОСТ 1807-75 ({len(changes)} замен)")

    def _about(self):
        QMessageBox.about(self, "О программе",
            "OPAL-OKB\n\n"
            "Система автоматизированного проектирования\n"
            "оптических систем\n\n"
            "Портирование с MS-DOS на Windows 10\n"
            "Python + PyQt5")

    def _show_field_points_dialog(self):
        """Диалог точек поля."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Точки поля")
        dlg.setMinimumWidth(350)
        layout = QVBoxLayout(dlg)
        fp_widget = FieldPointsWidget()
        fp_widget.load_system(self.current_system)
        layout.addWidget(fp_widget)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec_():
            self.current_system.field_points = fp_widget.get_field_points()
            self.sys_params.field_points_widget.load_system(self.current_system)
            self._calculate()

    def _show_spectral_dialog(self):
        """Диалог спектральных линий."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView
        dlg = QDialog(self)
        dlg.setWindowTitle("Спектральные линии")
        dlg.setMinimumWidth(350)
        layout = QVBoxLayout(dlg)
        wl_table = QTableWidget(0, 3)
        wl_table.setHorizontalHeaderLabels(["λ (мкм)", "Вес", "Имя"])
        wl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for wl in self.current_system.wavelengths:
            r = wl_table.rowCount()
            wl_table.insertRow(r)
            wl_table.setItem(r, 0, QTableWidgetItem(f"{wl.value:.4f}"))
            wl_table.setItem(r, 1, QTableWidgetItem(f"{wl.weight:.1f}"))
            wl_table.setItem(r, 2, QTableWidgetItem(wl.name or ""))
        layout.addWidget(wl_table)
        # Add/remove buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Добавить")
        del_btn = QPushButton("- Удалить")
        std_btn = QPushButton("Стандартные...")
        add_btn.clicked.connect(lambda: wl_table.insertRow(wl_table.rowCount()))
        del_btn.clicked.connect(lambda: wl_table.removeRow(wl_table.currentRow()) if wl_table.currentRow() >= 0 else None)
        # Standard wavelengths dialog
        from io_utils import STANDARD_WAVELENGTHS
        def _add_std():
            from PyQt5.QtWidgets import QDialog as _D, QDialogButtonBox as _B, QListWidget as _L
            d = _D(dlg)
            d.setWindowTitle("Стандартные длины волн")
            d.setMinimumWidth(250)
            dl = QVBoxLayout(d)
            lst = _L()
            for name, val in sorted(STANDARD_WAVELENGTHS.items(), key=lambda x: x[1]):
                lst.addItem(f"{name} \u2014 {val:.5f} \u043c\u043a\u043c")
            dl.addWidget(lst)
            b = _B(_B.Ok | _B.Cancel)
            b.accepted.connect(d.accept)
            b.rejected.connect(d.reject)
            dl.addWidget(b)
            if d.exec_():
                idx = lst.currentRow()
                if idx >= 0:
                    items = sorted(STANDARD_WAVELENGTHS.items(), key=lambda x: x[1])
                    name, val = items[idx]
                    r = wl_table.rowCount()
                    wl_table.insertRow(r)
                    wl_table.setItem(r, 0, QTableWidgetItem(f"{val:.4f}"))
                    wl_table.setItem(r, 1, QTableWidgetItem("1.0"))
                    wl_table.setItem(r, 2, QTableWidgetItem(name))
        std_btn.clicked.connect(_add_std)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(std_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec_():
            from optics_engine import Wavelength
            new_wls = []
            for r in range(wl_table.rowCount()):
                val_item = wl_table.item(r, 0)
                w_item = wl_table.item(r, 1)
                n_item = wl_table.item(r, 2)
                if val_item:
                    try:
                        val = float(val_item.text())
                        w = float(w_item.text()) if w_item and w_item.text() else 1.0
                        name = n_item.text() if n_item else ""
                        new_wls.append(Wavelength(val, w, name))
                    except ValueError:
                        pass
            if new_wls:
                self.current_system.wavelengths = new_wls
                self.sys_params.load_system(self.current_system)
                self._calculate()

    def _design_achromat(self):
        """Диалог расчёта ахроматического дублета."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout

        dlg = QDialog(self)
        dlg.setWindowTitle("Расчёт ахроматического дублета")
        dlg.setMinimumWidth(300)
        layout = QFormLayout(dlg)

        # f' input
        f_spin = QDoubleSpinBox()
        f_spin.setRange(1.0, 100000.0)
        f_spin.setDecimals(1)
        f_spin.setValue(100.0)
        f_spin.setSuffix(" мм")
        layout.addRow("Фокусное расстояние f':", f_spin)

        # Апертура
        ap_spin = QDoubleSpinBox()
        ap_spin.setRange(0.0, 10000.0)
        ap_spin.setDecimals(1)
        ap_spin.setValue(0.0)
        ap_spin.setSuffix(" мм (0 = авто)")
        layout.addRow("Входной зрачок D:", ap_spin)

        # Пара стёкол
        pair_combo = QComboBox()
        for crown, flint in GLASS_PAIRS:
            pair_combo.addItem(f"{crown} + {flint}")
        layout.addRow("Пара стёкол:", pair_combo)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addRow(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        crown, flint = GLASS_PAIRS[pair_combo.currentIndex()]
        try:
            system = design_achromat(f_spin.value(), crown, flint, ap_spin.value())
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка расчёта ахромата:\n{e}")
            return

        self.current_system = system
        self._refresh_ui()
        self.statusBar().showMessage(
            f"Ахромат: {system.name},  f'={self.results.parax_table.item(0, 1).text() if self.results.parax_table.rowCount() > 0 else '-'}"
        )

    def _show_library(self):
        """Показать диалог библиотеки оптических систем."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTreeWidget, QTreeWidgetItem

        dlg = QDialog(self)
        dlg.setWindowTitle("Библиотека оптических систем")
        dlg.setMinimumSize(500, 400)
        layout = QVBoxLayout(dlg)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Название системы"])
        tree.setHeaderHidden(False)

        lib = build_library()
        entries = {}  # QTreeWidgetItem -> entry dict
        lbo_categories = {}  # QTreeWidgetItem -> lbo_path
        
        # Sort categories: LBO first, then others alphabetically
        sorted_cats = sorted(lib.items(), key=lambda kv: (0 if "LBO" in kv[0] else 1, kv[0]))
        
        for category, items in sorted_cats:
            cat_item = QTreeWidgetItem(tree, [category])
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            for entry in items:
                item = QTreeWidgetItem(cat_item, [entry["name"]])
                if entry.get("lbo_path") and not entry.get("opj_data"):
                    # LBO category — store for expansion
                    lbo_categories[id(item)] = entry
                    # Pre-load children immediately so expand arrow works
                    from library import expand_lbo
                    systems = expand_lbo(entry["lbo_path"])
                    for s in systems:
                        child = QTreeWidgetItem(item, [s["name"]])
                        entries[id(child)] = s
                    item.setExpanded(False)  # collapsed by default, but expandable
                else:
                    entries[id(item)] = entry
            cat_item.setExpanded(True)

        layout.addWidget(tree)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        # Double-click: open system immediately
        def on_double_click(item, col):
            if id(item) in entries:
                dlg.accept()
        tree.itemDoubleClicked.connect(on_double_click)

        if dlg.exec_() != QDialog.Accepted:
            return

        selected = tree.selectedItems()
        if not selected:
            return

        item = selected[0]
        if id(item) not in entries:
            return

        entry = entries[id(item)]
        try:
            self.current_system = create_system_from_entry(entry)
            self._refresh_ui()
            self.statusBar().showMessage(f"Загружено из библиотеки: {entry['name']}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить систему:\n{e}")

    def _append_system(self):
        """Присоединить оптическую систему из файла."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Присоединить оптическую систему", "",
            "OPJ files (*.opj);;JSON (*.opal.json);;Все файлы (*)")
        if not path:
            return
        try:
            self._collect_system_from_ui()
            if path.lower().endswith('.opj'):
                from opj_reader import load_opj
                appended_sys, _info = load_opj(path)
                from system_utils import reverse_system as _rev
                # Use io_utils.append_system logic inline for OPJ
                from optics_engine import OpticalSystem as _OS
                if not appended_sys.surfaces:
                    pass
                else:
                    result = _OS(
                        name=self.current_system.name + " + " + appended_sys.name,
                        object_type=self.current_system.object_type,
                        object_height=self.current_system.object_height,
                        aperture_type=self.current_system.aperture_type,
                        aperture_value=self.current_system.aperture_value,
                        wavelengths=list(self.current_system.wavelengths),
                        field_points=list(self.current_system.field_points),
                        stop_surface=self.current_system.stop_surface,
                        obscuration_ratio=self.current_system.obscuration_ratio,
                        comment=self.current_system.comment,
                    )
                    result.surfaces = list(self.current_system.surfaces) + list(appended_sys.surfaces)
                    self.current_system = result
            else:
                self.current_system = append_system(self.current_system, path)
            self._refresh_ui()
            self.statusBar().showMessage(f"Система присоединена из: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось присоединить систему:\n{e}")

    def _export_protocol(self):
        """Экспорт протокола расчёта в текстовый файл или .OPJ."""
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Экспорт протокола", "",
            "OPJ files (*.opj);;Текстовые файлы (*.txt);;Все файлы (*)")
        if not path:
            return
        try:
            if path.lower().endswith('.opj') or 'OPJ' in selected_filter:
                if not path.lower().endswith('.opj'):
                    path += '.opj'
                from opj_writer import save_opj
                self._collect_system_from_ui()
                save_opj(self.current_system, path)
            else:
                if not path.endswith(".txt"):
                    path += ".txt"
                self._collect_system_from_ui()
                parax = paraxial_trace(self.current_system)
                seidel = seidel_aberrations(self.current_system)
                export_protocol(self.current_system, parax, seidel, path)
            self.statusBar().showMessage(f"Протокол экспортирован: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать протокол:\n{e}")

    def _show_glass_diagram(self):
        """Показать диаграмму стёкол."""
        try:
            from glass_diagram import GlassDiagramWindow
            # Собираем стёкла из системы для подсветки
            highlight = list(set(
                s.glass for s in self.current_system.surfaces
                if s.glass and s.glass not in ('', 'ВОЗДУХ', 'AIR', 'воздух', 'air')
            ))
            dlg = GlassDiagramWindow(parent=self, highlight_glasses=highlight)
            dlg.show()
        except ImportError:
            QMessageBox.warning(self, "Ошибка",
                "matplotlib не установлен.\nУстановите: pip install matplotlib")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при построении диаграммы:\n{e}")

    def _fit_dialog(self):
        """Диалог подгонки характеристик."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox
        from optimizer import fit_focal_length, fit_bfd

        dlg = QDialog(self)
        dlg.setWindowTitle("Подгонка характеристик")
        dlg.setMinimumWidth(350)
        layout = QFormLayout(dlg)

        # Цель
        target_combo = QComboBox()
        target_combo.addItems(["Фокусное расстояние f'", "Задний фок. отрезок BFD"])
        layout.addRow("Цель:", target_combo)

        target_spin = QDoubleSpinBox()
        target_spin.setRange(-100000, 100000)
        target_spin.setDecimals(4)
        target_spin.setSuffix(" мм")
        target_spin.setValue(100.0)
        layout.addRow("Целевое значение:", target_spin)

        # Переменная
        surf_spin = QSpinBox()
        surf_spin.setRange(1, max(1, len(self.current_system.surfaces)))
        surf_spin.setValue(1)
        layout.addRow("Поверхность No:", surf_spin)

        param_combo = QComboBox()
        param_combo.addItems(["Радиус R", "Толщина d"])
        layout.addRow("Параметр:", param_combo)

        # При выборе цели автоматически менять доступные параметры
        def on_target_changed(idx):
            if idx == 0:  # f' — только радиус
                param_combo.setCurrentIndex(0)
                param_combo.setEnabled(False)
            else:  # BFD — толщина
                param_combo.setCurrentIndex(1)
                param_combo.setEnabled(False)
        target_combo.currentIndexChanged.connect(on_target_changed)
        on_target_changed(0)  # initial

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addRow(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        self._collect_system_from_ui()
        surf_idx = surf_spin.value() - 1  # 0-based
        param_type = 'radius' if param_combo.currentIndex() == 0 else 'thickness'

        try:
            if target_combo.currentIndex() == 0:
                result_sys = fit_focal_length(
                    self.current_system, target_spin.value(),
                    surf_idx, param_type)
            else:
                result_sys = fit_bfd(
                    self.current_system, target_spin.value(),
                    surf_idx, param_type)

            self.current_system = result_sys
            self._refresh_ui()

            parax = paraxial_trace(self.current_system)
            if target_combo.currentIndex() == 0:
                ach_f = parax.get('focal_length', 0)
                self.statusBar().showMessage(
                    f"Подгонка: f' = {ach_f:.4f} мм (цель: {target_spin.value():.4f})")
            else:
                ach_bfd = parax.get('back_focal_distance', 0)
                self.statusBar().showMessage(
                    f"Подгонка: BFD = {ach_bfd:.4f} мм (цель: {target_spin.value():.4f})")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка подгонки:\n{e}")


    def _show_ray_table(self):
        """Показать таблицу координат габаритных лучей (#7)."""
        from aberrations import compute_ray_coordinates
        sys = self.current_system
        wl = sys.wavelengths[0].value if sys.wavelengths else 0.58756
        try:
            coords = compute_ray_coordinates(sys, wl=wl, field_y=0.0)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка трассировки: {e}")
            return
        if not coords:
            QMessageBox.information(self, "Таблица", "Нет данных")
            return

        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Координаты габаритных лучей")
        dlg.setMinimumSize(800, 400)
        layout = QVBoxLayout(dlg)

        headers = ["Пов.", "X верх", "Y верх", "Z верх",
                    "X низ", "Y низ", "Z низ",
                    "X гл.", "Y гл.", "Z гл."]
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(coords))
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setFont(QFont("Consolas", 9))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for i, entry in enumerate(coords):
            table.setItem(i, 0, QTableWidgetItem(str(entry['surface'])))
            for j, key in enumerate(['x_upper', 'y_upper', 'z_upper',
                                      'x_lower', 'y_lower', 'z_lower',
                                      'x_chief', 'y_chief', 'z_chief']):
                val = entry.get(key)
                text = f"{val:.4f}" if val is not None else "-"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, j + 1, item)

        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.exec_()

    def _toggle_wavefront_3d(self):
        """Переключить 2D/3D вид волнового фронта."""
        # Switch to Волн. фронт tab
        for i in range(self.analysis.count()):
            if 'Волн' in self.analysis.tabText(i):
                self.analysis.setCurrentIndex(i)
                break
        wf = self.analysis.wavefront_map_w
        wf._mode_3d = not wf._mode_3d
        wf.update()
        mode = "3D" if wf._mode_3d else "2D"
        self.statusBar().showMessage(f"Волновой фронт: {mode}")

    def _toggle_chromatic_rays(self):
        """Переключить хроматические лучи (все длины волн) на графике хода лучей."""
        self.viz.chromatic_rays = self.btn_zernike_chrom.isChecked()
        if self.current_system and self.current_system.surfaces:
            self.viz._trace_all_rays()
            self.viz.update()
        mode = "все длины волн" if self.viz.chromatic_rays else "одна длина волны"
        self.statusBar().showMessage(f"Ход лучей: {mode}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark-ish theme
    palette = app.palette()
    palette.setColor(palette.Window, QColor(245, 245, 250))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
