"""GUI-тесты окна «3D-ход лучей» (TASK_3D_VIZ, пакет C).

Пункт меню «Вид» → «3D-ход лучей» и кнопка тулбара «🌐 3D-ход» открывают
НЕмодальное окно (show(), не exec_()) с Visualization3D; текущая система
подаётся ``set_system()`` — виджет сам трассирует веера лучей по полям
(_trace_rays). Зафиксированные поведения:

  * повторный вызов при живом окне — окно поднимается и система
    обновляется (то же окно, не новое);
  * без PyOpenGL (visualization3d.HAS_OPENGL == False, monkeypatch до
    создания MainWindow) оба действия disabled + tooltip
    «… pip install PyOpenGL», вызов ``_show_ray_trace_3d()`` — тихий
    no-op (окно не открывается, никаких QMessageBox — модальный диалог
    блокировал бы offscreen-тест);
  * пустая система (без поверхностей): окно открывается нормально,
    веера не трассируются (ray_data_3d == [], «Rays: 0/0 passed») —
    готовое поведение Visualization3D.set_system.

«Сцена не пуста» на уровне примитивов проверяется прогоном настоящего
paintGL через записывающий GL-стаб (прецедент test_viz3d_mirrors; в
offscreen-платформе нет GL-контекста). Smoke MainWindow — прецедент
tests/qa_v6_full.py::TestGUI, tests/test_gui_strehl.py::TestMainWindowStrehl.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from tests.conftest import requires_pyopengl

from domain.models import create_demo_system_by_name

W, H = 900, 600
#: GL_LINE_STRIP — режим отрисовки луча в _GLWidget._draw_rays
GL_LINE_STRIP = 0x0003


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture
def mw(app):
    """Свежий MainWindow (offscreen). Функциональная область — тесты
    подменяют current_system и (в fallback-классе) HAS_OPENGL."""
    from main import MainWindow
    w = MainWindow()
    yield w
    # Немодальное окно «3D-ход лучей» закрываем явно: MainWindow в
    # offscreen-тестах никогда не показывается, и close() родителя НЕ
    # каскадно скрывает дочерний QDialog (проверено: isVisible()==True
    # после mw.close()); иначе окно висит видимым на QApplication до GC.
    dlg = getattr(w, '_ray_trace_3d_window', None)
    if dlg is not None:
        try:
            dlg.close()
        except RuntimeError:
            pass  # C++-объект уже удалён вместе с родителем
    w.close()


class TestRayTrace3DWindow:
    """Окно «3D-ход лучей»: открытие, подача системы, закрытие/повтор."""

    def test_window_opens_with_achromat(self, mw, app):
        """_show_ray_trace_3d(): немодальное окно с Visualization3D,
        система прокинута set_system, веера протрассированы (сцена не
        пуста: ray_data_3d, total > 0 в get_scene_info)."""
        from visualization3d import Visualization3D
        achromat = create_demo_system_by_name('achromat')
        mw.current_system = achromat

        mw._show_ray_trace_3d()
        app.processEvents()

        win = mw._ray_trace_3d_window
        assert win is not None
        assert win.isVisible()
        assert win.windowTitle() == '3D-ход лучей'
        assert not win.isModal(), 'окно обязано быть немодальным'
        # виджет живёт в окне (и по ссылке, и по дереву детей)
        w3d = mw._ray_trace_3d_widget
        assert win.findChild(Visualization3D) is w3d
        # система подана, веера по полям протрассированы
        assert w3d.system is achromat
        assert w3d.ray_data_3d, 'веера лучей не протрассированы'
        assert w3d.gl_widget is not None
        info = w3d.get_scene_info()
        # формат «Rays: ok/total passed»
        total = int(info.split('/')[1].split()[0])
        assert total > 0
        # веера по полям: осевое поле + крайнее (0 и max|fp.y|)
        fields = {fa for _, fa, _ in w3d.ray_data_3d}
        assert 0.0 in fields
        assert len(fields) >= 2, 'веера трассируются только по оси'

    def test_close_and_reopen(self, mw, app):
        """close() прячет окно; повторный вызов — окно живо (поднято),
        система обновлена текущей."""
        mw.current_system = create_demo_system_by_name('achromat')
        mw._show_ray_trace_3d()
        app.processEvents()
        win = mw._ray_trace_3d_window
        assert win.isVisible()

        win.close()
        app.processEvents()
        assert not win.isVisible(), 'после close() окно видимо'

        mirror = create_demo_system_by_name('mirror')
        mw.current_system = mirror
        mw._show_ray_trace_3d()
        app.processEvents()
        assert mw._ray_trace_3d_window is win, 'живое окно пересоздано'
        assert win.isVisible(), 'повторное открытие не подняло окно'
        assert mw._ray_trace_3d_widget.system is mirror, \
            'система при повторном открытии не обновлена'

    @requires_pyopengl
    def test_scene_primitives_not_empty(self, mw, app):
        """Настоящий paintGL внутреннего gl_widget через GL-стаб
        отправляет примитивы (сцена не пуста на уровне GL-вызовов)."""
        from tests._viz3d_glstub import gl_stubbed
        mw.current_system = create_demo_system_by_name('achromat')
        mw._show_ray_trace_3d()
        app.processEvents()
        w3d = mw._ray_trace_3d_widget
        assert w3d.gl_widget is not None
        with gl_stubbed(W, H) as stub:
            w3d.gl_widget.resizeGL(W, H)
            w3d.gl_widget.paintGL()
        assert stub.primitives, 'сцена пуста: paintGL не отправил примитивов'

    @requires_pyopengl
    def test_scene_contains_rays(self, mw, app):
        """В потоке примитивов paintGL есть лучи (GL_LINE_STRIP)."""
        from tests._viz3d_glstub import gl_stubbed
        mw.current_system = create_demo_system_by_name('achromat')
        mw._show_ray_trace_3d()
        app.processEvents()
        w3d = mw._ray_trace_3d_widget
        with gl_stubbed(W, H) as stub:
            w3d.gl_widget.resizeGL(W, H)
            w3d.gl_widget.paintGL()
        strips = [p for p in stub.primitives if p[0] == GL_LINE_STRIP]
        assert strips, 'в сцене нет лучей (GL_LINE_STRIP)'


class TestNoPyOpenGLFallback:
    """Без PyOpenGL (HAS_OPENGL monkeypatch'ен в False до создания
    MainWindow): действия disabled + tooltip, окно не открывается."""

    def test_actions_disabled_with_tooltip(self, app, monkeypatch):
        import visualization3d
        monkeypatch.setattr(visualization3d, 'HAS_OPENGL', False)
        from main import MainWindow
        mw = MainWindow()
        try:
            for act in (mw.act_viz3d_menu, mw.act_viz3d_toolbar):
                assert not act.isEnabled(), 'действие активно без PyOpenGL'
                assert 'pip install PyOpenGL' in act.toolTip(), \
                    f'tooltip без команды установки: {act.toolTip()!r}'
        finally:
            mw.close()

    def test_show_ray_trace_3d_is_noop(self, app, monkeypatch):
        """Вызов _show_ray_trace_3d() без PyOpenGL — тихий no-op:
        окно не создаётся и не открывается (зафиксированное поведение)."""
        import visualization3d
        monkeypatch.setattr(visualization3d, 'HAS_OPENGL', False)
        from main import MainWindow
        mw = MainWindow()
        try:
            mw.current_system = create_demo_system_by_name('achromat')
            mw._show_ray_trace_3d()
            app.processEvents()
            assert getattr(mw, '_ray_trace_3d_window', None) is None, \
                'окно 3D-хода открылось без PyOpenGL'
            # fallback-виджет MainWindow (viz_3d) без gl_widget не мешает
            assert mw.viz_3d.gl_widget is None
        finally:
            mw.close()

    def test_widget_fallback_label(self, app, monkeypatch):
        """Visualization3D при HAS_OPENGL=False живёт с fallback-QLabel
        (gl_widget=None); set_system при этом не падает — трассировка
        (_trace_rays) не завязана на OpenGL, данные лучей пригодны,
        рендера просто нет. Поэтому окно в этом режиме не открывается,
        а не «падает на отсутствующем gl_widget»."""
        import visualization3d
        monkeypatch.setattr(visualization3d, 'HAS_OPENGL', False)
        from visualization3d import Visualization3D
        w = Visualization3D()
        assert w.gl_widget is None
        achromat = create_demo_system_by_name('achromat')
        w.set_system(achromat)          # не падает на fallback-виджете
        assert w.system is achromat
        assert w.ray_data_3d, 'трассировка на fallback-виджете сломалась'
        info = w.get_scene_info()
        assert int(info.split('/')[1].split()[0]) > 0
        w.set_system(None)              # тоже не падает
        assert w.get_scene_info() == 'No system loaded'


class TestEmptySystemSmoke:
    """Smoke: MainWindow + _show_ray_trace_3d на пустой системе."""

    def test_empty_system_window_opens(self, mw, app):
        """Пустая система (без поверхностей): окно открывается нормально,
        веера не трассируются (ray_data_3d == [], «Rays: 0/0 passed») —
        готовое поведение Visualization3D.set_system, зафиксировано."""
        from optics_engine import OpticalSystem
        empty = OpticalSystem()
        assert not empty.surfaces
        mw.current_system = empty

        mw._show_ray_trace_3d()
        app.processEvents()

        win = mw._ray_trace_3d_window
        assert win is not None and win.isVisible()
        w3d = mw._ray_trace_3d_widget
        assert w3d.system is empty
        assert w3d.ray_data_3d == [], 'на пустой системе протрассированы лучи'
        assert w3d.get_scene_info() == 'Rays: 0/0 passed'
