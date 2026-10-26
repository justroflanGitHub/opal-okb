"""Тесты хроматических лучей 3D-вьюера (TASK_3D_VIZ, пакет D).

Тумблер «Лучи по λ» тулбара Visualization3D: моно (основная λ) ↔
полихром (все рабочие λ, w.weight > 0); цвет луча = цвет спектральной
линии. Палитра — единый источник ``gui.widgets.base.wl_to_plot_color``
(значения λ якорей — ``utils/spectral_lines.py``, h/g/F/e/d/C/r);
прежний захардкоженный ``WL_COLORS`` visualization3d.py удалён.

Зафиксированные решения (осознанные):
  * 2D-тумблер «Хром.Ц» УЖЕ есть в главном окне
    (main.py:990-994 → viz.chromatic_rays; visualization.py вне рабочей
    зоны пакета D) — требований «тот же тумблер и там» новых действий
    не порождает, зафиксировано комментарием в visualization3d.py;
  * по умолчанию тумблер ВЫКЛ = моно: прежнее «до первых 3 λ» заменено
    честным моно (счётчики get_scene_info меняются, но smoke-тесты
    test_viz3d_mirrors/test_gui_viz3d_window проверяют только > 0);
  * «рабочая» λ — по весу (weight > 0), как в 2D-полихроме и Strehl.

Проверка «число цветов = числу λ» — через записывающий GL-стаб
(tests/_viz3d_glstub.py): стаб пишет в примитив цвет последнего
glColor4f (RGBA 0..1); лучи — единственные GL_LINE_STRIP-примитивы
сцены, заблокированные лучи рисуются серым (0.5, 0.5, 0.5, α=0.2) —
фильтруются осознанно. GL-тесты — @requires_pyopengl; логические
(наборы λ в ray_data_3d, палитра, fallback) — без маркера: CI без
PyOpenGL обязан быть зелёным.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from tests.conftest import HAS_PYOPENGL, REASON_NO_PYOPENGL, requires_pyopengl

from domain.models import create_demo_system_by_name
from optics_engine import Wavelength
from tests.test_spot_3d import build_doublet

W, H = 900, 600
#: GL_LINE_STRIP — режим отрисовки луча в _GLWidget._draw_rays
GL_LINE_STRIP = 0x0003
#: цвет заблокированного луча в _draw_rays (тусклый серый, alpha 0.2)
GRAY_BLOCKED_RGBA = (0.5, 0.5, 0.5, 0.2)
#: полихром-набор дублета: e, C, F (все с weight=1 — рабочие)
DOUBLET_WLS = [Wavelength(0.54607, 1.0, 'e'),
               Wavelength(0.65627, 1.0, 'C'),
               Wavelength(0.48613, 1.0, 'F')]


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture
def viz_doublet(app):
    """Visualization3D на демо-дублете с 3 рабочими λ (моно по умолчанию)."""
    from visualization3d import Visualization3D
    viz = Visualization3D()
    viz.set_system(build_doublet(wls=[Wavelength(w.value, w.weight, w.name)
                                      for w in DOUBLET_WLS]))
    return viz


def _ray_strip_colors(stub, tol=0.02):
    """Различные цвета GL_LINE_STRIP-примитивов лучей (без серых).

    Цвет примитива стаб берёт из последнего glColor4f перед glEnd;
    успешные лучи яркие (alpha 0.85), заблокированные — серые
    (alpha 0.2), последние в счёт цветов не идут осознанно.
    """
    colors = []
    for mode, rgba, _lw, _verts in stub.primitives:
        if mode != GL_LINE_STRIP:
            continue
        if all(abs(a - b) < tol for a, b in zip(rgba, GRAY_BLOCKED_RGBA)):
            continue
        if not any(all(abs(a - b) < tol for a, b in zip(rgba, c))
                   for c in colors):
            colors.append(tuple(rgba))
    return colors


def _traced_wls(viz):
    """Множество λ в ray_data_3d."""
    return {wl for wl, _, _ in viz.ray_data_3d}


# --------------------------------------------------------------------------- #
# 1. Палитра — единый источник
# --------------------------------------------------------------------------- #

class TestSingleSourcePalette:
    """_wl_color от wl_to_plot_color (якоря utils/spectral_lines.py)."""

    def test_wl_color_matches_wl_to_plot_color(self, app):
        """_wl_color(λ) — RGB якоря wl_to_plot_color (float 0..1, допуск)."""
        from gui.widgets.base import wl_to_plot_color
        from visualization3d import Visualization3D
        viz = Visualization3D()
        for wl in (0.48613, 0.65627, 0.54607, 0.58756, 0.43405, 0.70652):
            expected = wl_to_plot_color(wl).getRgbF()[:3]
            got = viz._wl_color(wl)
            assert len(got) == 3
            assert got == pytest.approx(expected, abs=1e-9), \
                f'λ={wl}: {got} != {expected}'

    def test_wl_color_F_anchor_exact(self, app):
        """Якорь F (0.48613 → (0, 80, 255)/255) — конкретные значения."""
        from visualization3d import Visualization3D
        viz = Visualization3D()
        r, g, b = viz._wl_color(0.48613)
        assert r == pytest.approx(0.0, abs=1e-6)
        assert g == pytest.approx(80.0 / 255.0, abs=1e-6)
        assert b == pytest.approx(1.0, abs=1e-6)

    def test_wl_color_nonstandard_nearest_anchor(self, app):
        """Нестандартная λ — цвет ближайшего якоря, без падения:
        дублирующий fallback в visualization3d удалён, ближайший якорь
        даёт сам wl_to_plot_color (0.550 → e)."""
        from gui.widgets.base import wl_to_plot_color
        from visualization3d import Visualization3D
        viz = Visualization3D()
        assert viz._wl_color(0.550) == pytest.approx(
            wl_to_plot_color(0.550).getRgbF()[:3], abs=1e-9)

    def test_wl_colors_dict_removed(self):
        """Захардкоженный WL_COLORS удалён (значения λ больше не дублируются)."""
        from visualization3d import Visualization3D
        assert not hasattr(Visualization3D, 'WL_COLORS')

    def test_achromat_lambda_colors_distinct(self, app):
        """Три λ демо-ахромата (e, G', C) — три различных цвета линий."""
        from visualization3d import Visualization3D
        viz = Visualization3D()
        sys_ = create_demo_system_by_name('achromat')
        assert len(sys_.wavelengths) == 3
        colors = [viz._wl_color(w.value) for w in sys_.wavelengths]
        for i in range(len(colors)):
            for j in range(i + 1, len(colors)):
                assert any(abs(a - b) > 0.05
                           for a, b in zip(colors[i], colors[j])), \
                    f'цвета λ#{i} и λ#{j} совпадают: {colors[i]}'


# --------------------------------------------------------------------------- #
# 2. Toggle: моно ↔ полихром (логика, без GL)
# --------------------------------------------------------------------------- #

class TestChromaticToggleLogic:
    """Наборы λ в ray_data_3d — работает и без PyOpenGL (fallback)."""

    def test_default_is_mono(self, viz_doublet):
        """По умолчанию ВЫКЛ = моно: только основная λ (первая)."""
        assert viz_doublet.chromatic_enabled is False
        assert _traced_wls(viz_doublet) == {0.54607}

    def test_toggle_switches_ray_set(self, viz_doublet):
        """Toggle переключает набор отрисованных лучей: моно → все
        рабочие λ → обратно моно."""
        assert _traced_wls(viz_doublet) == {0.54607}

        viz_doublet.chromatic_enabled = True
        assert viz_doublet.chromatic_enabled is True
        assert _traced_wls(viz_doublet) == {0.54607, 0.65627, 0.48613}

        viz_doublet.chromatic_enabled = False
        assert viz_doublet.chromatic_enabled is False
        assert _traced_wls(viz_doublet) == {0.54607}

    def test_polychrome_uses_weights(self, viz_doublet):
        """Полихром — все РАБОЧИЕ λ (weight > 0); λ с weight=0 не трассируется."""
        viz_doublet.chromatic_enabled = True
        viz_doublet.system.wavelengths.append(Wavelength(0.58756, 0.0, 'd'))
        try:
            viz_doublet.set_system(viz_doublet.system)  # пере-трассировка
            assert _traced_wls(viz_doublet) == {0.54607, 0.65627, 0.48613}
        finally:
            viz_doublet.system.wavelengths.pop()

    def test_set_system_preserves_toggle_state(self, viz_doublet):
        """set_system сохраняет состояние тумблера: пере-трассировка
        выполняется в текущем режиме (полихром)."""
        viz_doublet.chromatic_enabled = True
        fresh = build_doublet(wls=[Wavelength(w.value, w.weight, w.name)
                                   for w in DOUBLET_WLS])
        viz_doublet.set_system(fresh)
        assert viz_doublet.chromatic_enabled is True
        assert viz_doublet.system is fresh
        assert _traced_wls(viz_doublet) == {0.54607, 0.65627, 0.48613}

    def test_polychrome_ray_count_gt_mono(self, viz_doublet):
        """Sanity: полихром-набор лучей строго больше моно-набора."""
        def total(v):
            info = v.get_scene_info()
            return int(info.split('/')[1].split()[0])

        mono_total = total(viz_doublet)
        assert mono_total > 0
        viz_doublet.chromatic_enabled = True
        poly_total = total(viz_doublet)
        assert poly_total > mono_total, \
            f'полихром {poly_total} ≤ моно {mono_total}'


# --------------------------------------------------------------------------- #
# 3. «Число цветов = числу λ» — настоящий paintGL через GL-стаб
# --------------------------------------------------------------------------- #

class TestChromaticGLColors:
    @requires_pyopengl
    def test_mono_single_color(self, viz_doublet):
        """Моно (по умолчанию): лучи одного цвета — цвет основной λ."""
        from tests._viz3d_glstub import gl_stubbed
        assert viz_doublet.chromatic_enabled is False
        with gl_stubbed(W, H) as stub:
            viz_doublet.gl_widget.resizeGL(W, H)
            viz_doublet.gl_widget.paintGL()
        colors = _ray_strip_colors(stub)
        assert len(colors) == 1, \
            f'моно: ожидался 1 цвет лучей, получено {len(colors)}: {colors}'
        # и это цвет якоря e (основная λ дублета)
        from gui.widgets.base import wl_to_plot_color
        expected = wl_to_plot_color(0.54607).getRgbF()[:3]
        assert colors[0][:3] == pytest.approx(expected, abs=0.02)

    @requires_pyopengl
    def test_polychrome_colors_equal_lambda_count(self, viz_doublet):
        """Тумблер ВКЛ: число РАЗЛИЧНЫХ цветов GL_LINE_STRIP-лучей равно
        числу рабочих λ системы (3 для дублета e/C/F)."""
        from tests._viz3d_glstub import gl_stubbed
        viz_doublet.chromatic_enabled = True
        n_wl = len([w for w in viz_doublet.system.wavelengths if w.weight > 0])
        assert n_wl == 3
        with gl_stubbed(W, H) as stub:
            viz_doublet.gl_widget.resizeGL(W, H)
            viz_doublet.gl_widget.paintGL()
        colors = _ray_strip_colors(stub)
        assert len(colors) == n_wl, \
            f'полихром: цветов {len(colors)} != λ {n_wl}: {colors}'
        # каждый цвет — якорь палитры соответствующей λ
        from gui.widgets.base import wl_to_plot_color
        for wl in (0.54607, 0.65627, 0.48613):
            expected = wl_to_plot_color(wl).getRgbF()[:3]
            assert any(tuple(c[:3]) == pytest.approx(expected, abs=0.02)
                       for c in colors), f'нет цвета λ={wl}: {colors}'

    @requires_pyopengl
    def test_no_gray_rays_for_doublet(self, viz_doublet):
        """Дублет не блокирует лучи: серых GL_LINE_STRIP (заблокированных)
        в сцене нет — фильтр серого в _ray_strip_colors ничего не ест."""
        from tests._viz3d_glstub import gl_stubbed
        viz_doublet.chromatic_enabled = True
        with gl_stubbed(W, H) as stub:
            viz_doublet.gl_widget.resizeGL(W, H)
            viz_doublet.gl_widget.paintGL()
        gray = [p for p in stub.primitives
                if p[0] == GL_LINE_STRIP
                and all(abs(a - b) < 0.02 for a, b in zip(p[1], GRAY_BLOCKED_RGBA))]
        assert gray == [], 'дублет заблокировал лучи (серые полилинии)'


# --------------------------------------------------------------------------- #
# 4. Кнопка тулбара (GL-ветка конструктора)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not HAS_PYOPENGL, reason=REASON_NO_PYOPENGL)
class TestChromaticToolbarButton:
    def test_button_default_state_and_text(self, viz_doublet):
        """Кнопка «Лучи по λ: выкл» — checkable, по умолчанию не нажата."""
        btn = viz_doublet.btn_chromatic
        assert btn.isCheckable()
        assert not btn.isChecked()
        assert btn.text() == 'Лучи по λ: выкл'

    def test_button_click_toggles_and_retraces(self, viz_doublet):
        """Клик по кнопке переключает режим, текст отражает состояние,
        лучи пере-трассируются (3 λ)."""
        btn = viz_doublet.btn_chromatic
        btn.click()
        assert viz_doublet.chromatic_enabled is True
        assert btn.isChecked() and btn.text() == 'Лучи по λ: вкл'
        assert _traced_wls(viz_doublet) == {0.54607, 0.65627, 0.48613}

        btn.click()
        assert viz_doublet.chromatic_enabled is False
        assert not btn.isChecked() and btn.text() == 'Лучи по λ: выкл'
        assert _traced_wls(viz_doublet) == {0.54607}

    def test_toolbar_russian_labels(self, viz_doublet):
        """Тулбар русифицирован: «Сброс вида» / «Лучи: вкл» /
        «Каркас» / «Трассировать» (+ новый тумблер)."""
        assert viz_doublet.btn_reset.text() == 'Сброс вида'
        assert viz_doublet.btn_toggle_rays.text() == 'Лучи: вкл'
        assert viz_doublet.btn_toggle_wire.text() == 'Каркас'
        assert viz_doublet.btn_trace.text() == 'Трассировать'

    def test_toggle_rays_button_text_sync(self, viz_doublet):
        """Кнопка «Лучи» синхронизирует текст вкл/выкл при переключении."""
        viz_doublet.btn_toggle_rays.setChecked(False)
        viz_doublet._toggle_rays()
        assert viz_doublet.btn_toggle_rays.text() == 'Лучи: выкл'
        viz_doublet.btn_toggle_rays.setChecked(True)
        viz_doublet._toggle_rays()
        assert viz_doublet.btn_toggle_rays.text() == 'Лучи: вкл'


# --------------------------------------------------------------------------- #
# 5. Fallback без PyOpenGL
# --------------------------------------------------------------------------- #

class TestFallbackNoPyOpenGL:
    def test_fallback_widget_chromatic_works(self, app, monkeypatch):
        """HAS_OPENGL=False: виджет создаётся (gl_widget=None), свойство
        chromatic_enabled работает, пере-трассировка не падает, набор λ
        переключается (трассировка не завязана на OpenGL)."""
        import visualization3d
        monkeypatch.setattr(visualization3d, 'HAS_OPENGL', False)
        from visualization3d import Visualization3D
        viz = Visualization3D()
        assert viz.gl_widget is None
        assert viz.chromatic_enabled is False
        assert not hasattr(viz, 'btn_chromatic'), \
            'кнопки не должно быть в fallback-ветке (тулбар живёт в GL-ветке)'

        viz.set_system(build_doublet(wls=[Wavelength(w.value, w.weight, w.name)
                                          for w in DOUBLET_WLS]))
        assert viz.ray_data_3d, 'моно-трассировка на fallback сломалась'
        assert _traced_wls(viz) == {0.54607}

        viz.chromatic_enabled = True
        assert viz.chromatic_enabled is True
        assert _traced_wls(viz) == {0.54607, 0.65627, 0.48613}
        assert viz.get_scene_info().split('/')[0].split()[-1] != '0'
