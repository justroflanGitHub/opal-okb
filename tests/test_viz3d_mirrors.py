"""Тесты 3D-визуализации зеркальных поверхностей (TASK_3DMIRRORS).

Аудит фиксов visualization3d.py:
  * подложка зеркала — заполненный диск (TRIANGLE_FAN с прогибом),
    лучи/ось больше не просвечивают сквозь зеркало насквозь;
  * золотое кольцо + штрихи (hash marks) сохранены;
  * объём «стекла» (_draw_glass_volume) не рисуется для зеркал —
    после отражения среды за поверхностью нет;
  * масштаб сцены учитывает |z|-протяжённость (зеркальные системы
    сворачивают путь: thickness < 0);
  * лучи после зеркала идут в −z (отражение) — трассировка корректна.

GPU в тестовом окружении нет: offscreen-платформа Qt не создаёт
GL-контекст (QOpenGLWidget.grabFramebuffer → 0×0), поэтому отрисовка
проверяется через записывающий GL-стаб (tests/_viz3d_glstub.py) —
настоящий paintGL() прогоняется по примитивам и растеризуется
программно. Smoke-тест grab() использует обычный QWidget.grab().
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from domain.models import create_demo_system_by_name

W, H = 900, 600
#: внутренность диска зеркала на экране (без ободка), см. _dbg_mirrors_prims
DISC_X0, DISC_X1, DISC_Y0, DISC_Y1 = 418, 483, 272, 331

#: цвет подложки зеркала из _draw_surface_ring (is_mirror=True)
SUBSTRATE_RGBA = (0.32, 0.26, 0.10, 0.92)
#: цвет золотого кольца зеркала из _draw_surface
GOLD_RGBA = (0.85, 0.70, 0.20, 0.80)


@pytest.fixture(scope='module')
def app():
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


@pytest.fixture(scope='module')
def lbo_mirror(app, lens_spc_systems):
    """LENS_SPC.LBO #4 — «Инфракрасный … з-л» (зеркально-линзовый).

    Returns ``(viz, n_mirrors)``.
    """
    pytest.importorskip('decode_lbo_opj')
    from decode_lbo_opj import decode_lbo_opj
    from visualization3d import Visualization3D
    system = decode_lbo_opj(lens_spc_systems[4]['opj_data'])
    n_mirrors = sum(1 for s in system.surfaces if s.is_reflective)
    assert n_mirrors > 0, 'декодер не пометил зеркала'
    viz = Visualization3D()
    viz.set_system(system)
    return viz, n_mirrors


@pytest.fixture(scope='module')
def viz_mirror(app):
    """Visualization3D с _demo_mirror (вогнутое зеркало f'≈200)."""
    from visualization3d import Visualization3D
    viz = Visualization3D()
    viz.set_system(create_demo_system_by_name('mirror'))
    return viz


@pytest.fixture(scope='module')
def painted(viz_mirror):
    """Кадр + поток примитивов настоящего paintGL через GL-стаб."""
    from tests._viz3d_glstub import render_framebuffer
    img, stub = render_framebuffer(viz_mirror.gl_widget, W, H)
    assert not img.isNull()
    return img, stub


# --------------------------------------------------------------------------- #
# 1. Smoke: виджет живёт offscreen, set_system не падает, grab() валиден
# --------------------------------------------------------------------------- #

class TestSmoke:
    def test_widget_offscreen_grab(self, app):
        """Виджет создаётся offscreen, set_system(_demo_mirror) не падает,
        grab() возвращает QImage размером > 0 пикселей."""
        from visualization3d import Visualization3D
        viz = Visualization3D()
        viz.resize(W, H)
        viz.set_system(create_demo_system_by_name('mirror'))
        img = viz.grab()
        assert not img.isNull()
        assert img.width() > 0 and img.height() > 0
        assert viz.gl_widget is not None
        assert viz.ray_data_3d, 'лучи не протрассированы'

    def test_scene_info_rays_passed(self, viz_mirror):
        """Хотя бы часть лучей доходит до плоскости изображения."""
        info = viz_mirror.get_scene_info()
        passed = int(info.split('/')[0].split()[-1])
        total = int(info.split('/')[1].split()[0])
        assert total > 0 and passed > 0


# --------------------------------------------------------------------------- #
# 2. Стекло за зеркалом не рисуется
# --------------------------------------------------------------------------- #

class TestGlassVolume:
    def test_no_glass_volume_for_mirror_system(self, app):
        """Для системы с зеркалом _draw_glass_volume не вызывается вовсе
        (после отражения среды за поверхностью нет)."""
        from visualization3d import Visualization3D
        viz = Visualization3D()
        viz.set_system(create_demo_system_by_name('mirror'))
        calls = []
        orig = viz.gl_widget._draw_glass_volume

        def counting(*a, **k):
            calls.append(a)
            return orig(*a, **k)

        viz.gl_widget._draw_glass_volume = counting
        try:
            from tests._viz3d_glstub import gl_stubbed, GL_QUADS
            with gl_stubbed(W, H) as stub:
                viz.gl_widget.resizeGL(W, H)
                viz.gl_widget.paintGL()
        finally:
            viz.gl_widget._draw_glass_volume = orig
        assert calls == [], f'_draw_glass_volume вызван {len(calls)} раз'
        quads = [p for p in stub.primitives if p[0] == GL_QUADS]
        assert quads == [], 'GL_QUADS (объём стекла) в сцене зеркала'

    def test_glass_volume_still_drawn_for_lenses(self, app):
        """Регресс: у обычной линзы объём стекла рисуется как раньше."""
        from visualization3d import Visualization3D
        from domain.models import create_demo_system_by_name
        viz = Visualization3D()
        viz.set_system(create_demo_system_by_name('achromat'))
        calls = []
        orig = viz.gl_widget._draw_glass_volume

        def counting(*a, **k):
            calls.append(a)
            return orig(*a, **k)

        viz.gl_widget._draw_glass_volume = counting
        try:
            from tests._viz3d_glstub import gl_stubbed
            with gl_stubbed(W, H) as stub:
                viz.gl_widget.resizeGL(W, H)
                viz.gl_widget.paintGL()
        finally:
            viz.gl_widget._draw_glass_volume = orig
        assert calls, 'у линзового дублета объём стекла пропал'


# --------------------------------------------------------------------------- #
# 3. Подложка зеркала + золотое кольцо
# --------------------------------------------------------------------------- #

class TestMirrorSurface:
    def test_substrate_fan_present(self, painted):
        """Зеркало рисуется заполненным диском-подложкой (не просвечивает)."""
        _, stub = painted
        fans = [p for p in stub.primitives
                if p[0] == 0x0006  # GL_TRIANGLE_FAN
                and all(abs(a - b) < 0.02 for a, b in zip(p[1], SUBSTRATE_RGBA))]
        assert len(fans) == 1, 'нет подложки зеркала (TRIANGLE_FAN)'
        # диск с прогибом: вершины не в одной плоскости (sag ≠ 0 при R<0)
        zs = {round(v[2], 6) for v in fans[0][3]}
        assert len(zs) > 1, 'подложка без сагитты (плоский диск)'

    def test_golden_ring_preserved(self, painted):
        """Золотое кольцо (LINE_LOOP) и штрихи зеркала не сломаны."""
        _, stub = painted
        rings = [p for p in stub.primitives
                 if p[0] == 0x0002  # GL_LINE_LOOP
                 and all(abs(a - b) < 0.02 for a, b in zip(p[1], GOLD_RGBA))]
        assert len(rings) == 1, 'золотое кольцо зеркала отсутствует'
        assert len(rings[0][3]) >= 48, 'кольцо не замкнуто по сегментам'
        # штрихи (hash marks) — тёмное золото поверх кольца
        hashes = [p for p in stub.primitives
                  if p[0] == 0x0001  # GL_LINES
                  and abs(p[1][0] - 0.7) < 0.02]
        assert len(hashes) >= 12, 'штрихи зеркала отсутствуют'

    def test_disc_filled_in_raster(self, painted):
        """В растеризованном кадре диск зеркала заполнен подложкой,
        а не фоном/лучами насквозь."""
        img, _ = painted

        def is_substrate(r, g, b):
            return 55 < r < 140 and 40 < g < 110 and b < 70 and r > b + 25

        n = 0
        for y in range(DISC_Y0, DISC_Y1):
            for x in range(DISC_X0, DISC_X1):
                c = img.pixel(x, y)
                if is_substrate((c >> 16) & 255, (c >> 8) & 255, c & 255):
                    n += 1
        assert n > 1000, f'подложка не залита: {n} px в прямоугольнике диска'

    def test_mirror_fits_viewport(self, painted):
        """Масштаб сцены: диск зеркала (и весь кадр) внутри вьюпорта.

        Регресс total_z < 0 у зеркальных систем: раньше max_dim считался
        без |z| и зеркало раздувалось на 3-5 экранов.
        """
        _, stub = painted
        from tests._viz3d_glstub import (GL_PROJECTION, GL_MODELVIEW,
                                         _project)
        mv = stub.matrices[GL_MODELVIEW]
        proj = stub.matrices[GL_PROJECTION]
        fans = [p for p in stub.primitives if p[0] == 0x0006]
        assert fans
        pts = _project(fans[0][3], mv, proj, W, H)
        assert pts is not None
        xs, ys = pts[0], pts[1]
        assert xs.min() >= 0 and xs.max() <= W, 'диск шире вьюпорта'
        assert ys.min() >= 0 and ys.max() <= H, 'диск выше/ниже вьюпорта'


# --------------------------------------------------------------------------- #
# 4. Лучи после зеркала
# --------------------------------------------------------------------------- #

class TestReflectedRays:
    def test_rays_drawn_as_polylines(self, painted):
        """3D-лучи рисуются полилиниями (в т.ч. после отражения)."""
        _, stub = painted
        strips = [p for p in stub.primitives if p[0] == 0x0003]
        assert len(strips) > 10, 'лучи не отрисованы'
        # прошедший отражённый луч: старт → зеркало → фокус (≥3 точек);
        # упавшие (EDGE) лучи могут короче
        assert sum(1 for p in strips if len(p[3]) >= 3) > 10

    def test_ray_z_decreases_after_mirror(self, app):
        """Физика отражения: после зеркала (z=0) луч идёт в −z к фокусу."""
        import ray_native
        system = create_demo_system_by_name('mirror')
        grid = ray_native.trace_grid_3d_native(system, 3, 8,
                                               wl=0.54607, field_y=0.0)
        ok = [tr for ring in grid for tr in ring if tr.success]
        assert ok, 'лучи не прошли трассировку'
        for tr in ok:
            zs = [p[2] for p in tr.path]
            assert zs[0] < 0            # старт слева от вершины
            assert abs(zs[1]) < 1.0     # попадание в зеркало у z≈0
            assert zs[2] < zs[1]        # после отражения — в −z
            assert zs[2] <= -199.0      # фокус у z=−200 (f'=|R|/2)

    def test_rays_occluded_by_substrate(self, painted):
        """Лучи не просвечивают сквозь зеркало: внутри диска пикселей
        лучей исчезающе мало (остаются лишь точки приземления на
        хордовой аппроксимации поверхности)."""
        img, _ = painted

        def is_ray(r, g, b):
            mx, mn = max(r, g, b), min(r, g, b)
            if mx > 140 and 100 < g < 210 and b < 110 and r > b + 60:
                return False  # золото
            if 55 < r < 140 and 40 < g < 110 and b < 70 and r > b + 25:
                return False  # подложка
            return mx > 90 and mx - mn > 40

        n = 0
        for y in range(DISC_Y0, DISC_Y1):
            for x in range(DISC_X0, DISC_X1):
                c = img.pixel(x, y)
                if is_ray((c >> 16) & 255, (c >> 8) & 255, c & 255):
                    n += 1
        assert n < 60, f'{n} px лучей просвечивают сквозь зеркало'


# --------------------------------------------------------------------------- #
# 5. Реальная зеркально-линзовая: LENS_SPC.LBO «Инфракрасный з-л»
# --------------------------------------------------------------------------- #

class TestRealMirrorLens:
    def test_decoder_marks_mirrors(self, lbo_mirror):
        """Декодер LBO помечает зеркала is_reflective.

        Правильная топология «Инфракрасного з-л» — 2 зеркала (S3 и S6):
        серия маркеров 0xFFFE/0xFFFF (гэпы обратного хода) a..b даёт
        зеркала на a-1 и b. Промежуточные поверхности S4/S5 — обычные
        рефрактивные (z-совпадения S2=S4, S5=S7; f' = 44.03 при
        каталогном 44, TASK_RUSSAR / docs/LBO_FORMAT.md «Особые случаи»).
        """
        _, n_mirrors = lbo_mirror
        assert n_mirrors == 2

    def test_paint_mirrors_no_glass_volume(self, lbo_mirror):
        """Сцена «з-л» рисуется: подложек столько же, сколько зеркал;
        объём стекла рисуют только настоящие линзы — ни один вызов
        _draw_glass_volume не принадлежит зеркальной поверхности."""
        from tests._viz3d_glstub import gl_stubbed, GL_QUADS
        viz, n_mirrors = lbo_mirror
        calls = []
        orig = viz.gl_widget._draw_glass_volume

        def counting(*a, **k):
            calls.append(a)
            return orig(*a, **k)

        viz.gl_widget._draw_glass_volume = counting
        try:
            with gl_stubbed(W, H) as stub:
                viz.gl_widget.resizeGL(W, H)
                viz.gl_widget.paintGL()
        finally:
            viz.gl_widget._draw_glass_volume = orig

        # ни один объём не «принадлежит» зеркалу (первый аргумент — surf)
        assert not any(a[0].is_reflective for a in calls), \
            'объём стекла рисуется для зеркальной поверхности'
        fans = [p for p in stub.primitives
                if p[0] == 0x0006
                and all(abs(a - b) < 0.02 for a, b in zip(p[1], SUBSTRATE_RGBA))]
        assert len(fans) == n_mirrors, \
            f'подложек {len(fans)} != зеркал {n_mirrors}'
        # QUADS между НЕзеркальными стеклами допустимы, но их немного
        quads = sum(1 for p in stub.primitives if p[0] == GL_QUADS)
        assert quads <= len(viz.system.surfaces)
