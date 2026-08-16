"""Регрессионные тесты пункта 7 GAP v2 — таблицы хода габаритных лучей.

Проверяются: 5 габаритных лучей (верхний/нижний меридиональные, главный,
±1 сагиттальные), координаты на поверхностях, направления и длины
сегментов, согласованность с compute_ray_coordinates (API сохранён).
"""
import math

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength
from aberrations import GAUGE_RAYS, compute_gauge_rays, compute_ray_coordinates
from ray_tracing import trace_ray_through_system, Ray


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 — базовая тестовая система."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=70),
    ]
    return s


class TestGaugeRays:
    def test_five_gauge_rays_defined(self):
        keys = [k for k, _, _, _ in GAUGE_RAYS]
        assert keys == ['upper', 'lower', 'chief', 'sag_plus', 'sag_minus']
        # короткие подписи уникальны (заголовки таблиц)
        shorts = [sh for _, _, sh, _ in GAUGE_RAYS]
        assert len(set(shorts)) == len(shorts)

    def test_returns_five_rays_with_points(self):
        rays = compute_gauge_rays(build_doublet())
        assert len(rays) == 5
        for r in rays:
            assert r['success'], f"луч {r['key']} не прошёл: {r['error']}"
            # минимум: старт + 3 поверхности + плоскость изображения
            assert len(r['points']) >= 5
            assert len(r['directions']) == len(r['points']) - 1
            assert len(r['segment_lengths']) == len(r['points']) - 1
        # наклонные лучи получают и точку в плоскости диафрагмы
        rays_by_key = {r['key']: r for r in rays}
        assert len(rays_by_key['upper']['points']) == 6
        # главный идёт через вершины — точки диафрагмы нет
        assert len(rays_by_key['chief']['points']) == 5

    def test_directions_are_unit_vectors(self):
        for r in compute_gauge_rays(build_doublet()):
            for k, l, m in r['directions']:
                assert math.sqrt(k * k + l * l + m * m) == pytest.approx(1.0,
                                                                         abs=1e-9)

    def test_path_length_is_sum_of_segments(self):
        for r in compute_gauge_rays(build_doublet()):
            assert r['path_length'] == pytest.approx(sum(r['segment_lengths']),
                                                     rel=1e-12)

    def test_points_are_connected_by_directions(self):
        """Конечная точка сегмента совпадает со стартом следующего."""
        for r in compute_gauge_rays(build_doublet()):
            for i, ((k, l, m), d) in enumerate(zip(r['directions'],
                                                   r['segment_lengths'])):
                p0, p1 = r['points'][i], r['points'][i + 1]
                assert p1[0] - p0[0] == pytest.approx(k * d, abs=1e-9)
                assert p1[1] - p0[1] == pytest.approx(l * d, abs=1e-9)
                assert p1[2] - p0[2] == pytest.approx(m * d, abs=1e-9)

    def test_meridional_symmetry(self):
        """Осесимметричная система: верхний и нижний симметричны по Y,
        стартуют с ±D/2 входного зрачка."""
        rays = {r['key']: r for r in compute_gauge_rays(build_doublet())}
        up, low = rays['upper'], rays['lower']
        assert up['points'][0][1] == pytest.approx(-low['points'][0][1],
                                                   abs=1e-12)
        assert up['points'][0][0] == pytest.approx(0.0, abs=1e-12)
        assert low['points'][0][0] == pytest.approx(0.0, abs=1e-12)

    def test_sagittal_rays_symmetric(self):
        """Сагиттальные лучи стартуют с (±D/2, 0), симметричны по X."""
        rays = {r['key']: r for r in compute_gauge_rays(build_doublet())}
        sp, sm = rays['sag_plus'], rays['sag_minus']
        assert sp['points'][0][0] == pytest.approx(-sm['points'][0][0],
                                                   abs=1e-12)
        assert sp['points'][0][1] == pytest.approx(0.0, abs=1e-12)
        assert sm['points'][0][1] == pytest.approx(0.0, abs=1e-12)
        # на оси их путь совпадает (равные длины хода)
        assert sp['path_length'] == pytest.approx(sm['path_length'], abs=1e-9)
        assert sp['opl'] == pytest.approx(sm['opl'], abs=1e-9)

    def test_chief_starts_at_pupil_center(self):
        rays = {r['key']: r for r in compute_gauge_rays(build_doublet())}
        chief = rays['chief']
        assert chief['points'][0][0] == pytest.approx(0.0, abs=1e-12)
        assert chief['points'][0][1] == pytest.approx(0.0, abs=1e-12)
        # главный луч на оси идёт вдоль оси: все точки на оси
        for x, y, z in chief['points']:
            assert x == pytest.approx(0.0, abs=1e-9)
            assert y == pytest.approx(0.0, abs=1e-9)

    def test_opl_matches_direct_trace(self):
        """OPL луча совпадает с прямой трассировкой того же луча."""
        from utils.optics_utils import get_effective_aperture
        s = build_doublet()
        r = compute_gauge_rays(s)[0]  # верхний
        aperture = get_effective_aperture(s, default=10.0)
        from optics_utils import make_field_ray
        from aberrations import _compute_ray_start
        from optics_engine import paraxial_trace
        parax = paraxial_trace(s)
        z_start, z_pupil = _compute_ray_start(s, parax)
        ray = make_field_ray(s, 0.0, aperture / 2, 0.0, z_start, z_pupil)
        res = trace_ray_through_system(s, ray, 0.58756)
        assert res.success
        assert r['opl'] == pytest.approx(res.opl, rel=1e-9)
        assert r['points'] == [tuple(p) for p in res.path]


class TestRayCoordinatesCompat:
    def test_api_preserved(self):
        """compute_ray_coordinates сохраняет формат (3 меридиональных луча)."""
        coords = compute_ray_coordinates(build_doublet(), wl=0.58756)
        assert coords, "нет данных"
        keys = {'x_upper', 'y_upper', 'z_upper', 'x_lower', 'y_lower',
                'z_lower', 'x_chief', 'y_chief', 'z_chief', 'surface'}
        for entry in coords:
            assert keys <= set(entry.keys())
        # максимум: старт + 3 поверхности + диафрагма + изображение
        assert len(coords) == 6
        assert coords[0]['surface'] == 0

    def test_matches_gauge_rays(self):
        """Координаты из compute_ray_coordinates = точки габаритных лучей."""
        s = build_doublet()
        coords = compute_ray_coordinates(s, wl=0.58756)
        rays = {r['key']: r for r in compute_gauge_rays(s, wl=0.58756)}
        for i, entry in enumerate(coords):
            assert entry['y_upper'] == pytest.approx(rays['upper']['points'][i][1],
                                                     abs=1e-12)
            assert entry['y_lower'] == pytest.approx(rays['lower']['points'][i][1],
                                                     abs=1e-12)
            chief_z = (rays['chief']['points'][i][2]
                       if i < len(rays['chief']['points']) else None)
            assert entry['z_chief'] == chief_z


class TestGaugeRaysGui:
    """GUI: вкладка «Лучи (ход)» с тремя таблицами."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def test_tab_present(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        titles = [panel.tabText(i) for i in range(panel.count())]
        assert 'Лучи (ход)' in titles

    def test_tables_built(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel._update_gauge_rays_table(build_doublet())
        container = panel._table_containers['rays']
        stack = container.layout().itemAt(0).widget()
        lay = stack.layout()
        tables = [lay.itemAt(i).widget() for i in range(lay.count())]
        assert len(tables) == 3
        coords, params, summary = tables
        # 1 колонка-метка + 5 лучей × 3 координаты
        assert coords.columnCount() == 16
        # строки: старт + 3 поверхности + диафрагма + изображение
        assert coords.rowCount() == 6
        # сводка: по строке на луч
        assert summary.rowCount() == 5
        assert summary.columnCount() == 5

    def test_summary_contains_totals(self):
        from gui.analysis_panel import AnalysisPanel
        from PyQt5.QtWidgets import QTableWidget
        panel = AnalysisPanel()
        s = build_doublet()
        rays = compute_gauge_rays(s)
        tables = panel._build_gauge_rays_tables(s, rays)
        summary = tables[2]
        # полная длина хода луча = сумме сегментов (первый луч)
        cell = summary.item(0, 2).text()
        assert float(cell) == pytest.approx(rays[0]['path_length'], abs=1e-4)

    def test_point_labels(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        rays = compute_gauge_rays(build_doublet())
        upper = next(r for r in rays if r['key'] == 'upper')
        labels = panel._gauge_point_labels(build_doublet(), upper['points'])
        assert labels == ['Старт', 'Пов 1', 'Пов 2', 'Диафр.', 'Пов 3',
                          'Изобр.']

    def test_precomputed_path(self):
        """apply_precomputed строит таблицы из данных пайплайна."""
        from gui.analysis_panel import AnalysisPanel
        from gui.analysis_pipeline import compute_all_analysis
        panel = AnalysisPanel()
        s = build_doublet()
        d = compute_all_analysis(s)
        assert d.get('gauge_rays'), "пайплайн не вернул gauge_rays"
        panel.apply_precomputed(s, d)
        container = panel._table_containers['rays']
        assert container.layout().count() == 1
