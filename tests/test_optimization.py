"""TASK_OPTIM — тесты analysis/optimization.py (ЛАП-метод, волна 9)
и подключения fit_dialog → optimize.

1. Дублет: R2+толщина сводят продольную сферическую — мерит монотонно,
   istop корректен.
2. Границы pmin/pmax соблюдаются (штрафы/лимитеры).
3. Связь двух переменных коэф−1 — синхронное движение Δведомый=k·Δведущий.
4. Якобиан центральных разностей против оценки мелким шагом (порядок).
5. parse_opt_file на синтетическом файле формата OPAL.
6. fit_dialog: диалог создаётся, optimize вызывается через mock (main.py).
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, \
    create_demo_system, paraxial_trace

from analysis.optimization import (
    ISTOP_MESSAGES, OptGoal, OptResult, OptVariable,
    build_jacobian, merit_vector, optimize, parse_opt_file,
    parse_opt_task, solve_single,
)


@pytest.fixture(scope='module')
def app():
    """Single QApplication instance for all GUI tests in this module."""
    import sys
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    yield a


def make_dublet():
    """Симметричный биконвекс R=±60, d=5, К8 — как create_optimization_demo."""
    return OpticalSystem(name='dublet', surfaces=[
        Surface(radius=60.0, thickness=5.0, glass='К8', semi_diameter=10.0),
        Surface(radius=-60.0, thickness=95.0, glass='', semi_diameter=10.0)],
        wavelengths=[Wavelength(value=0.5876)])


# --------------------------------------------------------------------------- #
# 1. Дублет: продольная сферическая — мерит падает монотонно
# --------------------------------------------------------------------------- #

class TestLongitudinalMerit:

    def test_merit_monotone_and_istop(self):
        """R2+d → продольная сферическая (зона 0.7): F падает монотонно,
        istop из множества ЛАП (0/1/2) с корректным сообщением."""
        vs = [OptVariable(param='radius', surface=1, dp0=1.0),
              OptVariable(param='thickness', surface=0, dp0=0.25)]
        gs = [OptGoal(kind='longitudinal', target=0.0, weight=1.0,
                      tol=1e-3, refs={'zone': 0.7})]
        res = optimize(make_dublet(), vs, gs, max_iter=60)

        hist = [h['fmin'] for h in res.history]
        assert len(hist) >= 5
        assert all(hist[i + 1] <= hist[i] + 1e-12 for i in range(len(hist) - 1))
        assert hist[-1] < 0.5 * hist[0]        # существенно сведена
        assert res.istop in (0, 1, 2)
        assert ISTOP_MESSAGES[res.istop] in res.message
        # исходная система не тронута
        src = make_dublet()
        assert res.system is not src
        assert src.surfaces[1].radius == -60.0
        assert src.surfaces[0].thickness == 5.0

    def test_multi_goal_efl_bfd(self):
        """Обе цели {f′, BFD} +5% — в допусках за ≤20 итераций (§9.5-3)."""
        sys0 = create_demo_system()
        pt = paraxial_trace(sys0)
        vs = [OptVariable(param='radius', surface=0),
              OptVariable(param='radius', surface=1),
              OptVariable(param='thickness', surface=0)]
        gs = [OptGoal(kind='efl', target=pt['focal_length'] * 1.05, tol=1e-5),
              OptGoal(kind='bfd', target=pt['back_focal_distance'] * 1.05,
                      tol=1e-5)]
        res = optimize(sys0, vs, gs, max_iter=20)
        assert res.istop == 0
        assert res.nstep <= 20
        hist = [h['fmin'] for h in res.history]
        assert all(hist[i + 1] <= hist[i] + 1e-12 for i in range(len(hist) - 1))
        new = paraxial_trace(res.system)
        assert new['focal_length'] == pytest.approx(
            pt['focal_length'] * 1.05, rel=1e-4)
        assert new['back_focal_distance'] == pytest.approx(
            pt['back_focal_distance'] * 1.05, rel=1e-4)

    def test_degenerate_parameter(self):
        """Параметр не влияет на цель — вырождение, istop=−1 (не молчание)."""
        vs = [OptVariable(param='thickness', surface=1)]  # зазор до изображения
        gs = [OptGoal(kind='efl', target=50.0)]
        res = optimize(create_demo_system(), vs, gs, max_iter=5)
        assert res.istop == -1
        assert not res.converged


# --------------------------------------------------------------------------- #
# 2. Границы pmin/pmax
# --------------------------------------------------------------------------- #

class TestBounds:

    def test_bounds_respected(self):
        """Цель вне достижимости — переменная остаётся в [pmin, pmax]."""
        sys0 = create_demo_system()
        pt = paraxial_trace(sys0)
        vs = [OptVariable(param='radius', surface=0, pmin=40.0, pmax=55.0)]
        gs = [OptGoal(kind='efl', target=pt['focal_length'] * 1.5, tol=1e-6)]
        res = optimize(sys0, vs, gs, max_iter=40)
        r1 = res.system.surfaces[0].radius
        assert 40.0 <= r1 <= 55.0
        # прижалась к границе (штрафы/лимитеры) и остановилась по стагнации
        assert r1 == pytest.approx(55.0, abs=1e-6)
        assert res.istop == 2

    def test_solve_single_bounds_unreachable(self):
        """solve_single: недостижимая в границах цель — явная ошибка."""
        with pytest.raises(ValueError, match="недостижима"):
            solve_single(create_demo_system(), 'efl', 1e6, 0, 'radius',
                         pmin=40.0, pmax=55.0)

    def test_solve_single_exact(self):
        """solve_single: f′=80 радиусом — точно и быстро."""
        res = solve_single(make_dublet(), 'efl', 80.0, 0, 'radius')
        assert res.istop == 0
        assert paraxial_trace(res.system)['focal_length'] == \
            pytest.approx(80.0, abs=1e-6)

    def test_solve_single_insensitive(self):
        """solve_single: не влияющий параметр — явная ошибка «не влияет»."""
        with pytest.raises(ValueError, match="не влияет"):
            solve_single(make_dublet(), 'efl', 80.0, 1, 'thickness')


# --------------------------------------------------------------------------- #
# 3. Связь переменных (PGL/CC)
# --------------------------------------------------------------------------- #

class TestLink:

    def test_synchronous_movement(self):
        """ΔR2 = −ΔR1 на каждом шаге; цель достигается (istop 0)."""
        vs = [OptVariable(param='radius', surface=0),
              OptVariable(param='radius', surface=1, link=(0, 'radius', -1.0))]
        gs = [OptGoal(kind='efl', target=69.0, tol=1e-8)]
        res = optimize(make_dublet(), vs, gs, max_iter=30)

        # синхронность относительно стартовых значений (60, −60)
        dr1 = res.system.surfaces[0].radius - 60.0
        dr2 = res.system.surfaces[1].radius - (-60.0)
        assert dr2 == pytest.approx(-dr1, abs=1e-9)
        # история содержит только свободные переменные (ведущая)
        xs = [h['x'] for h in res.history]
        assert all(len(x) == 1 for x in xs)
        assert res.istop == 0
        assert paraxial_trace(res.system)['focal_length'] == \
            pytest.approx(69.0, abs=1e-6)


# --------------------------------------------------------------------------- #
# 4. Якобиан центральных разностей
# --------------------------------------------------------------------------- #

class TestJacobian:

    def test_central_vs_fine_step(self):
        """Центральные разности (DP0) против мелкого шага (DP0/10) —
        согласуются с точностью O(h²) (относительно < 1e-4)."""
        sys0 = create_demo_system()
        vs = [OptVariable(param='radius', surface=0),
              OptVariable(param='thickness', surface=0)]
        gs = [OptGoal(kind='efl', target=50.0),
              OptGoal(kind='longitudinal', refs={'zone': 0.7})]
        j_coarse = build_jacobian(sys0, vs, gs, central=True)
        j_fine = build_jacobian(sys0, [OptVariable(param=v.param,
                                                   surface=v.surface,
                                                   dp0=(v.dp0 or 1e-3) / 10.0)
                                       for v in vs], gs, central=True)
        assert j_coarse.shape == (2, 2)
        assert j_fine.shape == (2, 2)
        scale = max(abs(j_fine).max(), 1e-12)
        assert abs(j_coarse - j_fine).max() / scale < 1e-4

    def test_merit_vector_matches_goals(self):
        """merit_vector согласован с evaluate_goal: длина = числу целей."""
        gs = [OptGoal(kind='efl', target=50.0),
              OptGoal(kind='bfd', target=40.0)]
        r = merit_vector(create_demo_system(), gs)
        assert len(r) == 2
        pt = paraxial_trace(create_demo_system())
        # невязка = (текущее − цель)/норма·вес; норма efl = max(1, 1%·|50|)
        assert r[0] == pytest.approx(
            (pt['focal_length'] - 50.0) / 1.0 * 1.0, rel=1e-6)


# --------------------------------------------------------------------------- #
# 5. Парсер формата OPAL (PAR/EQF/MF)
# --------------------------------------------------------------------------- #

class TestParseOptFile:

    SYNTHETIC = """
! синтетическое задание волны 9 !
PAR(1-3)=C,D,SD;
MF(1-4)=DSA,DYM,DYA,DXS;
MF#(1-2)=0.05,0.0;
MFW(1-4)=1,2,1,1;
EQF(1)=VG0; EQF#(1)=-50;
D<(2)=0.5; D>(2)=15; DE<(1-3)=0.1;
AS>(1-3)=12;
RayA=3; RAYM=2;
"""

    def test_parse_task_structure(self):
        vs, gs, warn = parse_opt_task(self.SYNTHETIC, num_surfaces=3)
        assert not warn
        assert len(vs) == 9                   # 3 поверхности × (C,D,SD)
        kinds = [g.kind for g in gs]
        assert kinds == ['longitudinal', 'transverse', 'transverse',
                         'transverse', 'magnification']
        # MF# заданные: первая цель 0.05
        assert gs[0].target == pytest.approx(0.05)
        # MFW веса: вторая цель вес 2
        assert gs[1].weight == pytest.approx(2.0)
        # EQF# цель
        assert gs[4].target == pytest.approx(-50.0)
        # лучевая конфигурация дошла до целей
        assert gs[0].refs['ray']['RAYA'] == 3

    def test_bounds_merged(self):
        """Границы по типам сливаются (толщина 2: D<0.5/D>15 + DE<0.1)."""
        vs, _gs, _w = parse_opt_task(self.SYNTHETIC, num_surfaces=3)
        th = [v for v in vs if v.param == 'thickness']
        assert [v.pmin for v in th] == [0.1, 0.5, 0.1]   # max(0.1, D<)
        assert [v.pmax for v in th] == [None, 15.0, None]
        sd = [v for v in vs if v.param == 'semi_diameter']
        assert all(v.pmax == 12.0 for v in sd)

    def test_parse_file_roundtrip(self, tmp_path):
        path = tmp_path / "task.opt"
        path.write_text(self.SYNTHETIC, encoding='utf-8')
        vs, gs = parse_opt_file(str(path), num_surfaces=3)
        assert len(vs) == 9
        assert len(gs) == 5


# --------------------------------------------------------------------------- #
# 6. fit_dialog: диалог + вызов optimize через mock
# --------------------------------------------------------------------------- #

class _StubOptDialog:
    """Заглушка FitDialog с активной вкладкой «Оптимизация (ЛАП)»."""

    mode = 1

    def __init__(self, num_surfaces, parent=None, current_efl=None,
                 current_bfd=None, mirror_surfaces=None):
        type(self).ctor_kwargs = dict(
            num_surfaces=num_surfaces, current_efl=current_efl,
            current_bfd=current_bfd, mirror_surfaces=mirror_surfaces)

    def exec_(self):
        from PyQt5.QtWidgets import QDialog
        return QDialog.Accepted

    def get_opt_parameters(self):
        return ([OptVariable(param='radius', surface=0)],
                [OptGoal(kind='efl', target=80.0)],
                {'max_iter': 7, 'damping': 0.5})


class TestFitDialogOptimize:

    def test_dialog_created_and_task_collected(self, app):
        """Диалог создаётся; get_opt_parameters возвращает переменные/цели."""
        from PyQt5.QtCore import Qt
        from gui.dialogs.fit_dialog import FitDialog

        d = FitDialog(4, None, current_efl=100.0, current_bfd=95.0,
                      mirror_surfaces=())
        assert d.mode == FitDialog.MODE_SOLVE
        d.tabs.setCurrentIndex(1)
        assert d.mode == FitDialog.MODE_OPTIMIZE

        d.vars_table.item(0, 0).setCheckState(Qt.Checked)   # R пов.1
        d.vars_table.item(1, 1).setCheckState(Qt.Checked)   # d пов.2
        vs, gs, opt = d.get_opt_parameters()
        assert [(v.surface, v.param) for v in vs] == [(0, 'radius'),
                                                      (1, 'thickness')]
        assert len(gs) == 1 and gs[0].kind == 'efl'
        assert gs[0].target == pytest.approx(100.0)
        assert opt['max_iter'] > 0 and opt['damping'] > 0

    def test_main_calls_optimize_through_module(self, app, monkeypatch,
                                                tmp_path):
        """main.py: вкладка ЛАП → analysis.optimization.optimize (mock),
        подтверждение Apply → система заменена, статусбар обновлён."""
        import main
        from PyQt5.QtWidgets import QMessageBox

        calls = {}

        def fake_optimize(system, variables, goals, **kw):
            calls['nvars'] = len(variables)
            calls['ngoals'] = len(goals)
            calls['max_iter'] = kw.get('max_iter')
            calls['damping'] = kw.get('damping')
            calls['progress'] = kw.get('callback') is not None
            new = create_demo_system()
            new.surfaces[0].radius = 77.0
            return OptResult(system=new, converged=True, istop=0, nstep=3,
                             fmin=1e-9, residuals=[1e-5],
                             history=[{'nstep': i, 'fmin': 1.0}
                                      for i in range(4)],
                             protocol=['GTISL: старт', 'GTISL ВЫХОД: ISTOP= 0'],
                             message='допуски целей')

        import analysis
        monkeypatch.setattr(main, 'FitDialog', _StubOptDialog)
        monkeypatch.setattr(main.QMessageBox, 'question',
                            lambda *a, **k: QMessageBox.Apply)
        monkeypatch.setattr(analysis.optimization, 'optimize', fake_optimize)

        from main import MainWindow
        w = MainWindow()
        w._init_new_system()
        w.current_system = create_demo_system()
        w._refresh_ui()
        try:
            w._fit_dialog()
            assert calls == {'nvars': 1, 'ngoals': 1, 'max_iter': 7,
                             'damping': 0.5, 'progress': True}
            assert w.current_system.surfaces[0].radius == 77.0
            msg = w.statusBar().currentMessage()
            assert 'Оптимизация ЛАП' in msg
            assert 'ISTOP = 0' in msg
        finally:
            w.close()

    def test_main_optimize_cancel_keeps_system(self, app, monkeypatch):
        """Отмена подтверждения — система не меняется."""
        import main
        import analysis
        from PyQt5.QtWidgets import QMessageBox

        def fake_optimize(system, variables, goals, **kw):
            new = create_demo_system()
            new.surfaces[0].radius = 77.0
            return OptResult(system=new, istop=0, nstep=1, fmin=1.0,
                             message='допуски целей',
                             protocol=['GTISL ВЫХОД: ISTOP= 0'])

        monkeypatch.setattr(main, 'FitDialog', _StubOptDialog)
        monkeypatch.setattr(main.QMessageBox, 'question',
                            lambda *a, **k: QMessageBox.Cancel)
        monkeypatch.setattr(analysis.optimization, 'optimize', fake_optimize)

        from main import MainWindow
        w = MainWindow()
        w._init_new_system()
        before = create_demo_system()
        w.current_system = before
        w._refresh_ui()
        try:
            w._fit_dialog()
            assert w.current_system is before
            assert w.current_system.surfaces[0].radius == before.surfaces[0].radius
        finally:
            w.close()
