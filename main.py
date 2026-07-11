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
    QFormLayout, QGridLayout, QSpinBox, QTextEdit, QFrame, QInputDialog,
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
from visualization3d import Visualization3D
from analysis_gui import AnalysisPanel
from system_utils import reverse_system, scale_system, nearest_standard_radius, standardize_radii, get_radii_changes
from io_utils import save_json, load_json, append_system, export_protocol, STANDARD_WAVELENGTHS
from library import build_library, create_system_from_entry
from achromat import design_achromat, GLASS_PAIRS
from optics_utils import get_primary_wl, copy_table_selection

from gui.controllers.calculation_controller import CalculationController
from gui.controllers.system_controller import SystemController
from gui.dialogs.library_dialog import LibraryDialog
from gui.dialogs.spectral_dialog import SpectralDialog
from gui.dialogs.field_dialog import FieldPointsDialog
from gui.dialogs.fit_dialog import FitDialog
from gui.dialogs.achromat_dialog import AchromatDialog


class SurfaceTable(QTableWidget):
    """Таблица поверхностей оптической системы."""

    # Базовые заголовки (до n-колонок и после)
    BASE_BEFORE = ["No", "Радиусы\nR (мм)", "Осевые\nрасст. d (мм)", "Марка\nстекла"]
    BASE_AFTER = ["Высоты\nD/2 (мм)", "Тип", "k (конич.)", "Стоп"]

    def __init__(self, parent=None):
        super().__init__(0, len(self.BASE_BEFORE) + 1 + len(self.BASE_AFTER), parent)
        self._n_wl_cols = 1  # обновляется в load_system
        self._update_headers(1)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setFont(QFont("Consolas", 10))
        self.setMinimumHeight(200)
        self._stop_surface = 1

    def _update_headers(self, n_wl):
        """Обновить заголовки таблицы под заданное число длин волн."""
        self._n_wl_cols = n_wl
        headers = list(self.BASE_BEFORE)
        for j in range(n_wl):
            headers.append(f"n{j+1}")
        headers.extend(self.BASE_AFTER)
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

    def _col_indices(self):
        """Вернуть словарь индексов колонок в зависимости от числа длин волн."""
        n = self._n_wl_cols
        return {
            'no': 0, 'r': 1, 'd': 2, 'glass': 3,
            'n_start': 4,
            'sd': 4 + n,
            'type': 4 + n + 1,
            'k': 4 + n + 2,
            'stop': 4 + n + 3,
        }

    def load_system(self, sys: OpticalSystem):
        """Загрузить оптическую систему в таблицу."""
        self._stop_surface = sys.stop_surface
        n_wl = max(1, len(sys.wavelengths))
        self._n_wl_cols = n_wl
        # Формируем заголовки с учётом длин волн
        headers = list(self.BASE_BEFORE)
        for j, wl in enumerate(sys.wavelengths if sys.wavelengths else [Wavelength(0.54607, 1.0, "e")]):
            wl_name = wl.name if wl.name else f"{wl.value:.5f}"
            headers.append(f"n{j+1}\n({wl_name}={wl.value:.5f})")
        headers.extend(self.BASE_AFTER)
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setRowCount(len(sys.surfaces) + 1)

        cols = self._col_indices()
        wl_values = [w.value for w in sys.wavelengths] if sys.wavelengths else [0.54607]

        from optics_engine import refractive_index

        for i, s in enumerate(sys.surfaces):
            self.setItem(i, cols['no'], QTableWidgetItem(str(i + 1)))
            self.setItem(i, cols['r'], QTableWidgetItem(f"{s.radius:.4f}" if s.radius != 0 else "∞"))
            self.setItem(i, cols['d'], QTableWidgetItem(f"{s.thickness:.4f}"))
            self.setItem(i, cols['glass'], QTableWidgetItem(s.glass if s.glass else "ВОЗДУХ"))

            # Колонки n для каждой длины волны
            for j, wl_val in enumerate(wl_values):
                if s.glass and s.glass.upper().strip() not in ('', 'ВОЗДУХ', 'AIR'):
                    n_val = refractive_index(s.glass, wl_val, None, getattr(s, 'n_override', None))
                    n_text = f"{n_val:.6f}"
                else:
                    n_text = "1.000000"
                n_item = QTableWidgetItem(n_text)
                n_item.setFlags(Qt.ItemIsEnabled)  # read-only
                n_item.setTextAlignment(Qt.AlignCenter)
                n_item.setForeground(QColor(80, 80, 80))
                self.setItem(i, cols['n_start'] + j, n_item)

            self.setItem(i, cols['sd'], QTableWidgetItem(f"{s.semi_diameter:.2f}"))
            self.setItem(i, cols['type'], QTableWidgetItem(s.surface_type.name))

            # Коническая постоянная k
            k_text = f"{s.conic_constant:.4f}" if abs(s.conic_constant) > 1e-10 else "0"
            self.setItem(i, cols['k'], QTableWidgetItem(k_text))

            # Стоп-чекбокс
            stop_item = QTableWidgetItem()
            stop_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if i + 1 == sys.stop_surface:
                stop_item.setCheckState(Qt.Checked)
            else:
                stop_item.setCheckState(Qt.Unchecked)
            stop_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(i, cols['stop'], stop_item)

            # Выравнивание
            for key in ['no', 'r', 'd', 'sd', 'k']:
                item = self.item(i, cols[key])
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        # Строка плоскости изображения
        last = len(sys.surfaces)
        self.setItem(last, cols['no'], QTableWidgetItem("Изобр."))
        self.setItem(last, cols['r'], QTableWidgetItem("∞"))
        for col in range(2, self.columnCount()):
            self.setItem(last, col, QTableWidgetItem(""))

        # Подсветка стоп-поверхности
        if 0 < sys.stop_surface <= self.rowCount():
            for col in range(self.columnCount()):
                item = self.item(sys.stop_surface - 1, col)
                if item:
                    item.setBackground(QColor(255, 200, 200))

    def get_stop_surface(self) -> int:
        """Получить номер стоп-поверхности из таблицы."""
        cols = self._col_indices()
        for i in range(self.rowCount()):
            item = self.item(i, cols['stop'])
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
        copy_action_parax.triggered.connect(lambda: copy_table_selection(self.parax_table))
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
        copy_action_seidel.triggered.connect(lambda: copy_table_selection(self.seidel_table))
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

    def _on_pupil_unit_changed(self, index):
        """Переключение единиц зрачков мм/дптр."""
        self._update_parax_display()

    def _update_parax_display(self):
        """Заполнить таблицу параксиальных параметров."""
        if not self._parax_result:
            return
        parax = self._parax_result
        f_val = parax.get('focal_length', 0)
        rows = [
            ("F", f"{-f_val:.4f} мм"),
            ("F'", f"{f_val:.4f} мм"),
            ("sF", f"{parax.get('sF', 0):.4f} мм"),
            ("sF'", f"{parax.get('sF_prime', 0):.4f} мм"),
            ("sH", f"{parax.get('sH', 0):.4f} мм"),
            ("sH'", f"{parax.get('sH_prime', 0):.4f} мм"),
            ("L", f"{parax.get('L', 0):.2f} мм"),
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
    """Формирование оптической системы."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # === Наименование ===
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Наименование:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit, 1)
        layout.addLayout(name_layout)

        # === Двухколоночная схема: Предмет | Изображение ===
        grid = QGridLayout()
        grid.setSpacing(4)
        col_obj = 0   # колонка предмета
        col_img = 2   # колонка изображения
        row = 0

        # Заголовки
        lbl_obj = QLabel("Предмет")
        lbl_obj.setStyleSheet("font-weight: bold; color: #3a6ea5;")
        lbl_img = QLabel("Изображение")
        lbl_img.setStyleSheet("font-weight: bold; color: #3a6ea5;")
        grid.addWidget(lbl_obj, row, col_obj)
        grid.addWidget(lbl_img, row, col_img)
        row += 1

        # Тип: дальнего/ближнего
        self.obj_type_combo = QComboBox()
        self.obj_type_combo.addItems(["Дальнего типа (∞)", "Ближнего типа"])
        self.img_type_combo = QComboBox()
        self.img_type_combo.addItems(["Дальнего типа (∞)", "Ближнего типа"])
        grid.addWidget(self.obj_type_combo, row, col_obj)
        grid.addWidget(self.img_type_combo, row, col_img)
        row += 1

        # Передний отрезок / Смещение
        grid.addWidget(QLabel("Передний отрезок:"), row, col_obj)
        grid.addWidget(QLabel("Смещ. от пл.Гаусса:"), row, col_img)
        row += 1
        self.front_section_spin = QDoubleSpinBox()
        self.front_section_spin.setRange(-100000, 100000)
        self.front_section_spin.setDecimals(4)
        self.front_section_spin.setSuffix(" мм")
        self.back_shift_spin = QDoubleSpinBox()
        self.back_shift_spin.setRange(-100000, 100000)
        self.back_shift_spin.setDecimals(4)
        self.back_shift_spin.setSuffix(" мм")
        self.front_section_combo = QComboBox()
        self.front_section_combo.addItems(["мм", "дптр"])
        self.back_shift_combo = QComboBox()
        self.back_shift_combo.addItems(["мм", "дптр"])
        fs_layout = QHBoxLayout()
        fs_layout.addWidget(self.front_section_spin)
        fs_layout.addWidget(self.front_section_combo)
        bs_layout = QHBoxLayout()
        bs_layout.addWidget(self.back_shift_spin)
        bs_layout.addWidget(self.back_shift_combo)
        grid.addLayout(fs_layout, row, col_obj)
        grid.addLayout(bs_layout, row, col_img)
        row += 1

        # Радиус предмета / изображения
        grid.addWidget(QLabel("Радиус предмета:"), row, col_obj)
        grid.addWidget(QLabel("Радиус изображения:"), row, col_img)
        row += 1
        self.obj_radius_spin = QDoubleSpinBox()
        self.obj_radius_spin.setRange(-1e6, 1e6)
        self.obj_radius_spin.setDecimals(4)
        self.obj_radius_spin.setSuffix(" мм")
        self.img_radius_spin = QDoubleSpinBox()
        self.img_radius_spin.setRange(-1e6, 1e6)
        self.img_radius_spin.setDecimals(4)
        self.img_radius_spin.setSuffix(" мм")
        grid.addWidget(self.obj_radius_spin, row, col_obj)
        grid.addWidget(self.img_radius_spin, row, col_img)
        row += 1

        # Мера величины
        grid.addWidget(QLabel("Мера величины:"), row, col_obj)
        grid.addWidget(QLabel("Мера величины:"), row, col_img)
        row += 1
        self.obj_measure_combo = QComboBox()
        self.obj_measure_combo.addItems(["tg", "мм"])
        self.img_measure_combo = QComboBox()
        self.img_measure_combo.addItems(["tg", "мм"])
        grid.addWidget(self.obj_measure_combo, row, col_obj)
        grid.addWidget(self.img_measure_combo, row, col_img)
        row += 1

        # Величина предмета / изображения
        grid.addWidget(QLabel("Величина предмета:"), row, col_obj)
        grid.addWidget(QLabel("Величина изображения:"), row, col_img)
        row += 1
        self.obj_height_spin = QDoubleSpinBox()
        self.obj_height_spin.setRange(-1000, 1000)
        self.obj_height_spin.setDecimals(6)
        self.obj_height_spin.setValue(0.0)
        self.obj_height_gmms_label = QLabel("")
        self.obj_height_gmms_label.setStyleSheet("color: #666; font-size: 9px;")
        self.img_height_spin = QDoubleSpinBox()
        self.img_height_spin.setRange(-1000, 1000)
        self.img_height_spin.setDecimals(6)
        self.img_height_spin.setValue(0.0)
        self.img_height_gmms_label = QLabel("")
        self.img_height_gmms_label.setStyleSheet("color: #666; font-size: 9px;")
        obj_h_layout = QVBoxLayout()
        oh_h = QHBoxLayout()
        oh_h.addWidget(self.obj_height_spin)
        obj_h_layout.addLayout(oh_h)
        obj_h_layout.addWidget(self.obj_height_gmms_label)
        img_h_layout = QVBoxLayout()
        ih_h = QHBoxLayout()
        ih_h.addWidget(self.img_height_spin)
        img_h_layout.addLayout(ih_h)
        img_h_layout.addWidget(self.img_height_gmms_label)
        grid.addLayout(obj_h_layout, row, col_obj)
        grid.addLayout(img_h_layout, row, col_img)
        row += 1

        # Колонка-разделитель
        grid.setColumnMinimumWidth(1, 10)
        layout.addLayout(grid)

        # === Диафрагма / Вх.зрачок ===
        stop_group = QGroupBox("Диафрагма / Вх. зрачок")
        stop_layout = QHBoxLayout(stop_group)
        stop_layout.addWidget(QLabel("ND:"))
        self.stop_nd_spin = QDoubleSpinBox()
        self.stop_nd_spin.setRange(0, 50)
        self.stop_nd_spin.setDecimals(0)
        self.stop_nd_spin.setValue(1)
        self.stop_nd_spin.setToolTip("Номер поверхности диафрагмы")
        stop_layout.addWidget(self.stop_nd_spin)
        stop_layout.addWidget(QLabel("SD:"))
        self.stop_sd_spin = QDoubleSpinBox()
        self.stop_sd_spin.setRange(-1000, 1000)
        self.stop_sd_spin.setDecimals(4)
        self.stop_sd_spin.setSuffix(" мм")
        self.stop_sd_spin.setToolTip("Смещение диафрагмы от поверхности ND")
        stop_layout.addWidget(self.stop_sd_spin)
        stop_layout.addStretch()
        layout.addWidget(stop_group)

        # === Апертуры ===
        ap_group = QGroupBox("Апертуры")
        ap_grid = QGridLayout(ap_group)
        ap_grid.addWidget(QLabel("Передняя апертура:"), 0, 0)
        self.front_ap_spin = QDoubleSpinBox()
        self.front_ap_spin.setRange(0, 1000)
        self.front_ap_spin.setDecimals(6)
        self.front_ap_combo = QComboBox()
        self.front_ap_combo.addItems(["Высота по Y (мм)", "NA (sin)", "F/#"])
        ap_grid.addWidget(self.front_ap_spin, 0, 1)
        ap_grid.addWidget(self.front_ap_combo, 0, 2)

        ap_grid.addWidget(QLabel("Задняя апертура:"), 1, 0)
        self.rear_ap_spin = QDoubleSpinBox()
        self.rear_ap_spin.setRange(0, 1000)
        self.rear_ap_spin.setDecimals(6)
        self.rear_ap_combo = QComboBox()
        self.rear_ap_combo.addItems(["Высота по Y (мм)", "NA (sin)", "F/#"])
        ap_grid.addWidget(self.rear_ap_spin, 1, 1)
        ap_grid.addWidget(self.rear_ap_combo, 1, 2)
        layout.addWidget(ap_group)

        # === Скрытые виджеты для совместимости ===
        self.aperture_type_combo = QComboBox()  # legacy compat
        self.aperture_type_combo.addItems(["Входной зрачок D (мм)", "Числовая апертура NA", "F/#"])
        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(0, 10000)
        self.aperture_spin.setDecimals(4)
        self.aperture_spin.setValue(20.0)
        self.obscuration_spin = QDoubleSpinBox()
        self.obscuration_spin.setRange(0, 50)
        self.obscuration_spin.setDecimals(1)
        self.obscuration_spin.setValue(0.0)
        self.beam_mode_combo = QComboBox()
        self.beam_mode_combo.addItems(["Реальные", "Заданные"])
        self.sharp_edge_check = QCheckBox()
        self.sharp_edge_check.setChecked(True)
        self.vignetting_check = QCheckBox()

        # Точки поля и спектральные линии
        self.field_points_widget = FieldPointsWidget()
        self.field_points_widget.setVisible(False)
        self.wl_table = QTableWidget(0, 3)
        self.wl_table.setHorizontalHeaderLabels(["λ (мкм)", "Вес", "Имя"])
        self.wl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Сигналы
        self.obj_type_combo.currentIndexChanged.connect(lambda idx: self._on_type_changed('obj', idx))
        self.img_type_combo.currentIndexChanged.connect(lambda idx: self._on_type_changed('img', idx))
        self.obj_measure_combo.currentIndexChanged.connect(lambda: self._update_gmms_label())
        self.obj_height_spin.valueChanged.connect(self._update_gmms_label)
        self.img_measure_combo.currentIndexChanged.connect(lambda: self._update_gmms_label())
        self.img_height_spin.valueChanged.connect(self._update_gmms_label)
        # Связь передней апертуры с aperture_type_combo/aperture_spin для совместимости
        self.front_ap_spin.valueChanged.connect(self._sync_aperture)
        self.front_ap_combo.currentIndexChanged.connect(self._sync_aperture)

    def _on_type_changed(self, side: str, idx: int):
        """Auto-set мера/отрезок при смене типа предмета/изображения.
        
        Дальнего типа (∞): мера=tg, отрезок=дптр, величина=гр.ММСС
        Ближнего типа:    мера=мм, отрезок=мм, величина=мм
        """
        is_far = (idx == 0)
        if side == 'obj':
            self.obj_measure_combo.setCurrentIndex(0 if is_far else 1)  # tg / мм
            self.front_section_combo.setCurrentIndex(1 if is_far else 0)  # дптр / мм
            self.obj_height_spin.setSuffix('' if is_far else ' мм')
        else:
            self.img_measure_combo.setCurrentIndex(0 if is_far else 1)
            self.back_shift_combo.setCurrentIndex(1 if is_far else 0)
            self.img_height_spin.setSuffix('' if is_far else ' мм')
        self._update_gmms_label()

    def _sync_aperture(self):
        """Синхронизировать переднюю апертуру с legacy aperture_spin/aperture_type_combo."""
        idx = self.front_ap_combo.currentIndex()
        val = self.front_ap_spin.value()
        # 0=Y height (D/2), 1=NA, 2=F/#
        self.aperture_type_combo.setCurrentIndex(idx)
        if idx == 0:  # Y → D
            self.aperture_spin.setValue(val * 2 if val > 0 else 20.0)
        else:
            self.aperture_spin.setValue(val)

    def _update_gmms_label(self, val=None):
        """Обновить отображение поля в формате Г.ММСС."""
        from system_utils import deg_to_gmms, gmms_to_str
        # Предмет
        if self.obj_type_combo.currentIndex() == 0 and abs(self.obj_height_spin.value()) > 0.001:
            deg = self.obj_height_spin.value()
            gmms = deg_to_gmms(deg)
            self.obj_height_gmms_label.setText(f"= {gmms:.4f} гр.мнск ({gmms_to_str(gmms)})")
        else:
            self.obj_height_gmms_label.setText("")
        # Изображение
        if self.img_type_combo.currentIndex() == 0 and abs(self.img_height_spin.value()) > 0.001:
            deg = self.img_height_spin.value()
            gmms = deg_to_gmms(deg)
            self.img_height_gmms_label.setText(f"= {gmms:.4f} гр.мнск ({gmms_to_str(gmms)})")
        else:
            self.img_height_gmms_label.setText("")
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
        # Тип предмета: 0=INFINITE(∞), 1=FINITE(ближний)
        self.obj_type_combo.setCurrentIndex(0 if sys.object_type == ObjectType.INFINITE else 1)
        # Тип изображения: 0=INFINITE(∞), 1=FINITE(ближний)
        self.img_type_combo.setCurrentIndex(0 if sys.image_type == ObjectType.INFINITE else 1)
        self.obj_height_spin.setValue(sys.object_height)
        # Auto-set мера/отрезок по типу
        self._on_type_changed('obj', self.obj_type_combo.currentIndex())
        self._on_type_changed('img', self.img_type_combo.currentIndex())

        # Апертура: автоматически выбрать тип и значение
        if sys.aperture_type == ApertureType.ENTRANCE_PUPIL:
            self.front_ap_combo.setCurrentIndex(0)  # Y height
            self.front_ap_spin.setValue(sys.aperture_value / 2.0)  # D → D/2
        elif sys.aperture_type == ApertureType.NUMERICAL_APERTURE:
            self.front_ap_combo.setCurrentIndex(1)  # NA
            self.front_ap_spin.setValue(sys.aperture_value)
        elif sys.aperture_type == ApertureType.F_NUMBER:
            self.front_ap_combo.setCurrentIndex(2)  # F/#
            self.front_ap_spin.setValue(sys.aperture_value)
        # Legacy sync
        self.aperture_type_combo.setCurrentIndex(sys.aperture_type.value)
        self.aperture_spin.setValue(sys.aperture_value)

        # Диафрагма
        self.stop_nd_spin.setValue(sys.stop_surface)
        self.stop_sd_spin.setValue(getattr(sys, 'stop_offset', 0.0))

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

        self._update_gmms_label()


class MainWindow(QMainWindow):
    """Главное окно OPAL-OKB."""

    def __init__(self):
        super().__init__()
        self.current_system = OpticalSystem()
        self._current_file = None
        self._init_ui()
        self._init_new_system()  # Silent init, no dialog
        # Controllers
        self._calc_controller = CalculationController(self)
        self._system_controller = SystemController(self)

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

        sys_params_group = QGroupBox("Формирование оптической системы")
        sp_layout = QVBoxLayout(sys_params_group)
        sp_layout.setContentsMargins(2, 2, 2, 2)
        sp_layout.addWidget(self.sys_params)

        left_splitter.addWidget(surf_group)
        left_splitter.addWidget(sys_params_group)
        left_splitter.setSizes([350, 350])

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
        self.viz_3d = Visualization3D()
        self._viz_mode = '2d'

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

        # 2D/3D toggle
        self.btn_3d_toggle = QPushButton("3D")
        self.btn_3d_toggle.setMaximumWidth(50)
        self.btn_3d_toggle.setCheckable(True)
        self.btn_3d_toggle.setToolTip("Switch 2D / 3D view")
        self.btn_3d_toggle.clicked.connect(self._toggle_viz_3d)

        viz_ctrl.addWidget(self.btn_viz_fit)
        viz_ctrl.addWidget(self.btn_viz_zoomin)
        viz_ctrl.addWidget(self.btn_viz_zoomout)
        viz_ctrl.addWidget(self.lbl_zoom)
        viz_ctrl.addWidget(self.btn_ray_table)
        viz_ctrl.addWidget(self.btn_wf_3d)
        viz_ctrl.addWidget(self.btn_zernike_chrom)
        viz_ctrl.addWidget(self.btn_3d_toggle)
        viz_ctrl.addStretch()
        viz_layout.addLayout(viz_ctrl)

        # Stacked container for 2D and 3D views
        from PyQt5.QtWidgets import QStackedWidget
        self.viz_stack = QStackedWidget()
        self.viz_stack.addWidget(self.viz)       # index 0 = 2D
        self.viz_stack.addWidget(self.viz_3d)    # index 1 = 3D
        viz_layout.addWidget(self.viz_stack)
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
        # Если в системе нет длин волн — подставить стандартные e, G', C
        if not self.current_system.wavelengths:
            from optics_engine import _std_wavelengths
            self.current_system.wavelengths = _std_wavelengths()
        self.surface_table.load_system(self.current_system)
        self.sys_params.load_system(self.current_system)
        self.results.log_text.clear()
        self.viz.set_system(self.current_system, trace_rays=False)

    def _add_surface(self):
        """Insert a blank surface before the selected row."""
        self._system_controller.add_surface()

    def _del_surface(self):
        """Delete selected surface row(s)."""
        self._system_controller.del_surface()

    def _calculate(self):
        """Gather UI data and run the calculation pipeline."""
        self._calc_controller.calculate()

    def _run_calc(self, sys, sync=False):
        """Run two-phase calculation (Phase 1 sync, Phase 2 async)."""
        self._calc_controller.run_calc(sys, sync=sync)

    def _do_calc_phase1(self, sys):
        """Phase 1: Fast synchronous computations (< 0.5 s)."""
        return self._calc_controller.do_calc_phase1(sys)

    def _do_calc_phase2(self, sys, defocus, azimuth):
        """Phase 2: Heavy computations (fans, MTF, PSF, Zernike, etc.)."""
        return self._calc_controller.do_calc_phase2(sys, defocus, azimuth)

    def _on_calc_error(self, err):
        """Handle calculation error from worker thread."""
        self._calc_controller._on_calc_error(err)

    def _update_after_calc(self, sys, phase1_data=None, phase2_data=None):
        """Update GUI after calculation (backward-compat for tests)."""
        self._calc_controller.update_after_calc(sys, phase1_data, phase2_data)

    def _update_parax_and_seidel(self, sys, data=None):
        """Update paraxial + Seidel tables in results and analysis panels."""
        self._calc_controller._update_parax_and_seidel(sys, data)

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
        """Collect current UI data into ``current_system`` (without calculation)."""
        self._system_controller.collect_system_from_ui()

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
        """Open the field points editing dialog."""
        dlg = FieldPointsDialog(self.current_system, FieldPointsWidget, self)
        if dlg.exec_():
            self.current_system.field_points = dlg.get_field_points()
            self.sys_params.field_points_widget.load_system(self.current_system)
            self._calculate()

    def _show_spectral_dialog(self):
        """Open the spectral lines editing dialog."""
        dlg = SpectralDialog(self.current_system, self)
        if dlg.exec_():
            new_wls = dlg.get_wavelengths()
            if new_wls:
                self.current_system.wavelengths = new_wls
                self.sys_params.load_system(self.current_system)
                self._calculate()

    def _design_achromat(self):
        """Open the achromatic doublet design dialog."""
        dlg = AchromatDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return

        f_val, ap_val, crown, flint = dlg.get_parameters()
        try:
            system = design_achromat(f_val, crown, flint, ap_val)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка расчёта ахромата:\n{e}")
            return

        self.current_system = system
        self._refresh_ui()
        self.statusBar().showMessage(
            f"Ахромат: {system.name},  f'={self.results.parax_table.item(1, 1).text() if self.results.parax_table.rowCount() > 1 else '-'}"
        )

    def _show_library(self):
        """Open the optical system library browser dialog."""
        dlg = LibraryDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return

        entry = dlg.get_selected_entry()
        if entry is None:
            return

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
        """Open the parameter fitting dialog."""
        from optimizer import fit_focal_length, fit_bfd

        dlg = FitDialog(len(self.current_system.surfaces), self)
        if dlg.exec_() != QDialog.Accepted:
            return

        self._collect_system_from_ui()
        target_type, target_val, surf_idx, param_type = dlg.get_parameters()

        try:
            if target_type == FitDialog.TARGET_FOCAL:
                result_sys = fit_focal_length(
                    self.current_system, target_val, surf_idx, param_type)
            else:
                result_sys = fit_bfd(
                    self.current_system, target_val, surf_idx, param_type)

            self.current_system = result_sys
            self._refresh_ui()

            parax = paraxial_trace(self.current_system)
            if target_type == FitDialog.TARGET_FOCAL:
                ach_f = parax.get('focal_length', 0)
                self.statusBar().showMessage(
                    f"Подгонка: f' = {ach_f:.4f} мм (цель: {target_val:.4f})")
            else:
                ach_bfd = parax.get('back_focal_distance', 0)
                self.statusBar().showMessage(
                    f"Подгонка: BFD = {ach_bfd:.4f} мм (цель: {target_val:.4f})")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка подгонки:\n{e}")


    def _show_ray_table(self):
        """Показать таблицу координат габаритных лучей (#7)."""
        from aberrations import compute_ray_coordinates
        sys = self.current_system
        wl = get_primary_wl(sys)
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

    def _toggle_viz_3d(self):
        """Switch between 2D and 3D visualization."""
        if self.btn_3d_toggle.isChecked():
            self.viz_stack.setCurrentIndex(1)
            self._viz_mode = '3d'
            self.btn_3d_toggle.setText("2D")
            # Update 3D view with current system
            if self.current_system and self.current_system.surfaces:
                self.viz_3d.set_system(self.current_system)
            self.statusBar().showMessage("3D view")
        else:
            self.viz_stack.setCurrentIndex(0)
            self._viz_mode = '2d'
            self.btn_3d_toggle.setText("3D")
            self.statusBar().showMessage("2D view")


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
