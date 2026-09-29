"""Регрессионные тесты пункта 6 GAP v2 — косое сечение (азимут 0..360°).

Физика: осевой пучок осесимметричной системы имеет радиальную поперечную
аберрацию A(ρ)·(px, py), поэтому проекции косого сечения подчиняются
dy_мер(θ) = dy_мер(0°)·cosθ, dy_саг(θ) = dy_мер(0°)·sinθ.
"""
import math

import pytest

from optics_engine import OpticalSystem, Surface, Wavelength
from aberrations import (
    AZIMUTH_FULL_TURN_DEG,
    compute_oblique_fan,
    is_oblique_section,
    normalize_azimuth_deg,
    trace_aberration_fan,
)


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 — осесимметричная тестовая система."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


class TestNormalizeAzimuth:
    """Нормализация и признак косого сечения (общие helpers)."""

    @pytest.mark.parametrize("raw,expected", [
        (0.0, 0.0), (45.0, 45.0), (360.0, 0.0), (370.0, 10.0),
        (720.0, 0.0), (-90.0, 270.0), (-0.5, 359.5), (359.9, 359.9),
    ])
    def test_normalize(self, raw, expected):
        assert normalize_azimuth_deg(raw) == pytest.approx(expected, abs=1e-12)

    @pytest.mark.parametrize("az,expected", [
        (0.0, False),          # меридиональное
        (360.0, False),        # эквивалент 0°
        (0.05, False),         # в допуске от 0°
        (359.99, False),       # в допуске от 360°
        (720.0, False),        # два полных оборота
        (0.5, True),           # косое
        (45.0, True),          # косое
        (90.0, True),          # сагиттальное
        (180.0, True),         # косое
        (359.0, True),         # косое
        (-270.0, True),        # эквивалент 90°
    ])
    def test_is_oblique(self, az, expected):
        assert is_oblique_section(az) is expected

    def test_full_turn_constant(self):
        assert AZIMUTH_FULL_TURN_DEG == 360.0


class TestObliqueFanPhysics:
    def test_zero_azimuth_matches_meridional_fan(self):
        """θ=0 — меридиональное сечение: dy совпадает с веером (мм → мкм)."""
        s = build_doublet()
        pupils, dy_mer, dy_sag = compute_oblique_fan(s, wl=0.58756, num_rays=11,
                                                     azimuth_deg=0.0)
        fan = trace_aberration_fan(s, 0.58756, num_rays=11)
        for h, v, r in zip(pupils, dy_mer, fan):
            assert abs(h - r['pupil_y']) < 1e-9
            assert v == pytest.approx(r['dy'] * 1000.0, abs=5e-3, rel=1e-4)
        # сагиттальная проекция на оси нулевая
        assert all(v == pytest.approx(0.0, abs=1e-6) for v in dy_sag)

    def test_90_is_sagittal(self):
        """θ=90 — сагиттальное сечение: меридиональная проекция ≈ 0."""
        s = build_doublet()
        _, dy_mer, dy_sag = compute_oblique_fan(s, wl=0.58756, num_rays=11,
                                                azimuth_deg=90.0)
        assert all(v == pytest.approx(0.0, abs=1e-6) for v in dy_mer)
        assert max(abs(v) for v in dy_sag) > 0.01  # сферическая аберрация

    def test_projection_invariant_45(self):
        """Осесимметричный пучок: dy_мер(45°)=dy_мер(0°)·cos45°, dy_саг — ·sin45°."""
        s = build_doublet()
        _, mer0, _ = compute_oblique_fan(s, wl=0.58756, num_rays=11,
                                         azimuth_deg=0.0)
        _, mer45, sag45 = compute_oblique_fan(s, wl=0.58756, num_rays=11,
                                              azimuth_deg=45.0)
        c = math.cos(math.radians(45.0))
        sn = math.sin(math.radians(45.0))
        for v0, vm, vs in zip(mer0, mer45, sag45):
            assert vm == pytest.approx(v0 * c, abs=1e-3, rel=1e-5)
            assert vs == pytest.approx(v0 * sn, abs=1e-3, rel=1e-5)

    def test_180_flips_sign(self):
        """θ=180° — обратный ход диаметра: dy_мер(h) = −dy_мер(0°)(h)."""
        s = build_doublet()
        _, mer0, _ = compute_oblique_fan(s, wl=0.58756, num_rays=11,
                                         azimuth_deg=0.0)
        _, mer180, sag180 = compute_oblique_fan(s, wl=0.58756, num_rays=11,
                                                azimuth_deg=180.0)
        for v0, vm, vs in zip(mer0, mer180, sag180):
            assert vm == pytest.approx(-v0, abs=1e-3, rel=1e-5)
            assert vs == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.parametrize("az", [30.0, 200.0, 335.0])
    def test_periodicity_full_turn(self, az):
        """θ и θ+360° — одно и то же сечение (после нормализации)."""
        s = build_doublet()
        a = compute_oblique_fan(s, wl=0.58756, num_rays=11, azimuth_deg=az)
        b = compute_oblique_fan(s, wl=0.58756, num_rays=11,
                                azimuth_deg=az + AZIMUTH_FULL_TURN_DEG)
        for va, vb in zip(a[1], b[1]):
            assert va == pytest.approx(vb, abs=1e-12)
        for va, vb in zip(a[2], b[2]):
            assert va == pytest.approx(vb, abs=1e-12)


class TestObliqueSectionGui:
    """GUI: спиннер азимута 0..360° и переключение режима графика."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def test_azimuth_spin_range(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        assert panel.azimuth_spin.minimum() == 0.0
        assert panel.azimuth_spin.maximum() == 360.0

    def test_get_azimuth_normalizes(self):
        from gui.analysis_panel import AnalysisPanel
        panel = AnalysisPanel()
        panel.azimuth_spin.setValue(360.0)
        assert panel.get_azimuth() == pytest.approx(0.0)
        panel.azimuth_spin.setValue(45.0)
        assert panel.get_azimuth() == pytest.approx(45.0)

    def test_widget_switches_by_shared_helper(self):
        """AberrationGraphWidget использует is_oblique_section:
        360° → меридиональный веер, 45° → косое сечение."""
        from gui.widgets.aberration_graphs import AberrationGraphWidget
        s = build_doublet()
        w = AberrationGraphWidget(mode='transverse')
        w.set_data(s, azimuth_deg=360.0)
        assert w.oblique_data is None
        assert w.fan_data, "меридиональный веер не построен"
        w.set_data(s, azimuth_deg=45.0)
        assert w.oblique_data is not None
        assert len(w.oblique_data) == 3  # (pupils, dy_mer, dy_sag)
        assert len(w.oblique_data[0]) == 20

    def test_widget_azimuth_normalized(self):
        from gui.widgets.aberration_graphs import AberrationGraphWidget
        w = AberrationGraphWidget(mode='transverse')
        w.set_azimuth(-90.0)
        assert w._azimuth_deg == pytest.approx(270.0)
