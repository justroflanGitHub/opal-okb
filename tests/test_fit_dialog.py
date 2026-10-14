"""TASK_FIT — тесты диалога подгонки и интеграции с оптимизатором.

1. Диалог: параметр (R/d) разблокирован для обеих целей, умные дефолты
   (current_efl/current_bfd автозаполняют цель), ограничение диапазона
   поверхностей для толщины (1..n-1), предупреждение о зеркале.
2. Интеграция: fit_focal_length через радиус и через толщину на золотой
   фикстуре Индустар-23у (conftest), target 115 ± 0.01, исходная система
   не изменяется; граничные случаи — понятные ошибки, не молчание.
3. Подтверждение в main.py::_fit_dialog: Отмена — система не меняется,
   Применить — меняется, статусбар показывает старое→новое значение
   поверхности (диалог замокан заглушкой без модального exec_).
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import create_demo_system, paraxial_trace
from optimizer import fit_focal_length, fit_bfd


@pytest.fixture(scope='module')
def app():
    """Single QApplication instance for all GUI tests in this module."""
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


def make_dialog(num_surfaces=7, current_efl=109.6976, current_bfd=96.8032,
                mirror_surfaces=()):
    from gui.dialogs.fit_dialog import FitDialog
    return FitDialog(num_surfaces, None, current_efl=current_efl,
                     current_bfd=current_bfd,
                     mirror_surfaces=mirror_surfaces)


# --------------------------------------------------------------------------- #
# 1. Диалог
# --------------------------------------------------------------------------- #

class TestFitDialog:

    def test_param_combo_not_locked(self, app):
        """Параметр R/d выбирается вручную для любой цели (не setEnabled(False))."""
        d = make_dialog()
        assert d.param_combo.isEnabled()
        # f' + толщина d вручную — разрешено
        d.param_combo.setCurrentIndex(1)
        assert d.param_combo.currentIndex() == 1
        assert d.target_combo.currentIndex() == d.TARGET_FOCAL
        # BFD + радиус R вручную — разрешено
        d.target_combo.setCurrentIndex(d.TARGET_BFD)
        d.param_combo.setCurrentIndex(0)
        assert d.param_combo.isEnabled()
        assert d.param_combo.currentIndex() == 0

    def test_target_switch_sets_default_param(self, app):
        """Смена цели автоставит дефолтный параметр: f'→R, BFD→d."""
        d = make_dialog()
        assert d.param_combo.currentIndex() == 0
        d.target_combo.setCurrentIndex(d.TARGET_BFD)
        assert d.param_combo.currentIndex() == 1
        d.target_combo.setCurrentIndex(d.TARGET_FOCAL)
        assert d.param_combo.currentIndex() == 0

    def test_smart_defaults_fill_target_value(self, app):
        """Целевое значение автозаполняется текущим значением выбранной цели."""
        d = make_dialog(current_efl=109.6976, current_bfd=96.8032)
        assert d.target_spin.value() == pytest.approx(109.6976, abs=1e-3)
        assert "f'" in d.current_label.text()
        assert "109.6976" in d.current_label.text()
        d.target_combo.setCurrentIndex(d.TARGET_BFD)
        assert d.target_spin.value() == pytest.approx(96.8032, abs=1e-3)
        assert "BFD" in d.current_label.text()
        assert "96.8032" in d.current_label.text()

    def test_unknown_current_value_shows_dash(self, app):
        """Без текущих значений — «—», дефолт спина не перетирается."""
        d = make_dialog(current_efl=None, current_bfd=None)
        assert d.current_label.text() == "—"
        assert d.target_spin.value() == pytest.approx(100.0)

    def test_thickness_limits_surface_range(self, app):
        """Толщина d: поверхности 1..n-1 (последняя — до плоскости изображения)."""
        d = make_dialog(num_surfaces=7)
        d.param_combo.setCurrentIndex(0)  # Радиус — все поверхности
        assert d.surf_spin.maximum() == 7
        d.surf_spin.setValue(7)
        d.param_combo.setCurrentIndex(1)  # Толщина — без последней
        assert d.surf_spin.maximum() == 6
        assert d.surf_spin.value() == 6  # QSpinBox сам клампит значение

    def test_mirror_thickness_warning(self, app):
        """Зеркало + толщина: разрешено, но tooltip-предупреждение."""
        d = make_dialog(num_surfaces=7, mirror_surfaces={2})
        d.param_combo.setCurrentIndex(1)
        d.surf_spin.setValue(3)  # 1-based → индекс 2 — зеркало
        assert d.surf_spin.toolTip() != ""
        # радиус на зеркале — без предупреждения
        d.param_combo.setCurrentIndex(0)
        assert d.surf_spin.toolTip() == ""
        # толщина не на зеркале — без предупреждения
        d.param_combo.setCurrentIndex(1)
        d.surf_spin.setValue(1)
        assert d.surf_spin.toolTip() == ""

    def test_get_parameters(self, app):
        d = make_dialog(num_surfaces=7)
        d.target_combo.setCurrentIndex(d.TARGET_BFD)
        d.target_spin.setValue(90.0)
        d.surf_spin.setValue(4)
        d.param_combo.setCurrentIndex(0)
        target_type, target_val, surf_idx, param_type = d.get_parameters()
        assert target_type == d.TARGET_BFD
        assert target_val == pytest.approx(90.0)
        assert surf_idx == 3  # 0-based
        assert param_type == 'radius'


# --------------------------------------------------------------------------- #
# 2. Интеграция с оптимизатором (золотая фикстура Индустар-23у из conftest)
# --------------------------------------------------------------------------- #

class TestFitIntegration:

    def test_fit_focal_via_radius(self, industar23u):
        """f'=115 подгоняется радиусом поверхности 6 (индекс 5)."""
        result = fit_focal_length(industar23u, 115.0, 5, 'radius')
        f_new = paraxial_trace(result)['focal_length']
        assert f_new == pytest.approx(115.0, abs=0.01)
        assert result.surfaces[5].radius != pytest.approx(industar23u.surfaces[5].radius)
        # исходная система не тронута (fit работает с копией)
        assert paraxial_trace(industar23u)['focal_length'] == pytest.approx(109.6976, abs=0.01)

    def test_fit_focal_via_thickness(self, industar23u):
        """f'=115 подгоняется толщиной (воздушный зазор поверхности 2)."""
        result = fit_focal_length(industar23u, 115.0, 1, 'thickness')
        f_new = paraxial_trace(result)['focal_length']
        assert f_new == pytest.approx(115.0, abs=0.01)
        assert result.surfaces[1].thickness != pytest.approx(industar23u.surfaces[1].thickness)
        assert industar23u.surfaces[1].thickness == pytest.approx(4.9)

    def test_unreachable_target_clear_error(self, industar23u):
        """Недостижимая цель — ValueError с достижимым диапазоном, не молчание."""
        with pytest.raises(ValueError, match="Невозможно достичь"):
            fit_focal_length(industar23u, 115.0, 0, 'radius')

    def test_nan_target_clear_error(self, industar23u):
        with pytest.raises(ValueError, match="некорректно"):
            fit_focal_length(industar23u, float('nan'), 5, 'radius')

    def test_nan_bfd_target_clear_error(self, industar23u):
        with pytest.raises(ValueError, match="некорректен"):
            fit_bfd(industar23u, float('inf'), 0, 'radius')


# --------------------------------------------------------------------------- #
# 3. Подтверждение в main.py::_fit_dialog (диалог замокан заглушкой)
# --------------------------------------------------------------------------- #

class _StubFitDialog:
    """Замена FitDialog для main.py::_fit_dialog: без модального exec_."""

    TARGET_FOCAL = 0
    TARGET_BFD = 1

    result = (0, 80.7463, 0, 'radius')
    ctor_kwargs = None

    def __init__(self, num_surfaces, parent=None, current_efl=None,
                 current_bfd=None, mirror_surfaces=None):
        type(self).ctor_kwargs = dict(
            num_surfaces=num_surfaces, current_efl=current_efl,
            current_bfd=current_bfd, mirror_surfaces=mirror_surfaces)

    def exec_(self):
        from PyQt5.QtWidgets import QDialog
        return QDialog.Accepted

    def get_parameters(self):
        return type(self).result


@pytest.fixture
def main_window(app):
    from main import MainWindow
    w = MainWindow()
    w._init_new_system()
    w.current_system = create_demo_system()
    w._refresh_ui()
    yield w
    w.close()


class TestFitDialogConfirm:

    def test_cancel_keeps_system(self, main_window, monkeypatch):
        """Отмена в подтверждении — система не изменилась."""
        import main
        from PyQt5.QtWidgets import QMessageBox

        w = main_window
        before = w.current_system
        radii_before = [s.radius for s in before.surfaces]
        target = round(paraxial_trace(before)['focal_length'] * 1.05, 4)
        _StubFitDialog.result = (0, target, 0, 'radius')

        monkeypatch.setattr(main, 'FitDialog', _StubFitDialog)
        monkeypatch.setattr(main.QMessageBox, 'question',
                            lambda *a, **k: QMessageBox.Cancel)

        w._fit_dialog()

        assert w.current_system is before
        assert [s.radius for s in w.current_system.surfaces] == radii_before
        assert 'Подгонка' not in w.statusBar().currentMessage()

    def test_apply_updates_system_and_statusbar(self, main_window, monkeypatch):
        """Применить — система заменена, статусбар: f' и старое→новое R."""
        import main
        from PyQt5.QtWidgets import QMessageBox

        w = main_window
        before = w.current_system
        old_r = before.surfaces[0].radius
        target = round(paraxial_trace(before)['focal_length'] * 1.05, 4)
        _StubFitDialog.result = (0, target, 0, 'radius')

        monkeypatch.setattr(main, 'FitDialog', _StubFitDialog)
        monkeypatch.setattr(main.QMessageBox, 'question',
                            lambda *a, **k: QMessageBox.Apply)

        w._fit_dialog()

        assert w.current_system is not before
        assert paraxial_trace(w.current_system)['focal_length'] == pytest.approx(target, abs=0.01)
        new_r = w.current_system.surfaces[0].radius
        assert new_r != pytest.approx(old_r)
        msg = w.statusBar().currentMessage()
        assert 'f\'' in msg
        assert f'R1: {old_r:.4f} → {new_r:.4f}' in msg

    def test_dialog_receives_current_values(self, main_window, monkeypatch):
        """main.py передаёт в диалог текущие parax значения (умные дефолты)."""
        import main
        from PyQt5.QtWidgets import QMessageBox

        w = main_window
        parax = paraxial_trace(w.current_system)
        _StubFitDialog.result = (0, 80.0, 0, 'radius')

        monkeypatch.setattr(main, 'FitDialog', _StubFitDialog)
        monkeypatch.setattr(main.QMessageBox, 'question',
                            lambda *a, **k: QMessageBox.Cancel)

        w._fit_dialog()

        kw = _StubFitDialog.ctor_kwargs
        assert kw['current_efl'] == pytest.approx(parax['focal_length'])
        assert kw['current_bfd'] == pytest.approx(parax['back_focal_distance'])
        assert kw['num_surfaces'] == len(w.current_system.surfaces)
