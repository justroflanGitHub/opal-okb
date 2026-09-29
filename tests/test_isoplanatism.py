"""Регрессионные тесты пункта 1 GAP v2 — неизопланатизм осевого пучка.

Физика: η(h) = [Δy'(h, ε) − Δy'(h, 0) − y'_ε] / y'_ε, безразмерная;
0 = идеальный изопланатизм. Доминирующий 3-й порядок — кома: η ∝ SII·h².
"""
import math

import numpy as np
import pytest

from optics_engine import OpticalSystem, Surface, Wavelength, seidel_aberrations
from aberrations import compute_isoplanatism


def build_doublet() -> OpticalSystem:
    """Клееный дублет K8/TF5 — базовая тестовая система."""
    s = OpticalSystem()
    s.wavelengths = [Wavelength(value=0.58756)]
    s.surfaces = [
        Surface(radius=80, glass='K8', thickness=5),
        Surface(radius=-60, glass='TF5', thickness=3),
        Surface(radius=-200, glass='', thickness=0),
    ]
    return s


class TestIsoplanatismShape:
    def test_returns_paired_lists(self):
        pupils, etas = compute_isoplanatism(build_doublet(), num_rays=21)
        assert len(pupils) == len(etas)
        assert len(pupils) >= 3
        assert all(math.isfinite(e) for e in etas)

    def test_zero_at_pupil_center(self):
        """Луч через центр зрачка — сам главный луч: η(0) = 0 точно."""
        pupils, etas = compute_isoplanatism(build_doublet(), num_rays=21)
        idx0 = pupils.index(0.0)
        assert etas[idx0] == pytest.approx(0.0, abs=1e-12)

    def test_pupil_grid_symmetric(self):
        pupils, _ = compute_isoplanatism(build_doublet(), num_rays=21)
        assert pupils[0] == pytest.approx(-1.0)
        assert pupils[-1] == pytest.approx(1.0)

    def test_empty_for_zero_eps(self):
        assert compute_isoplanatism(build_doublet(), field_eps=0.0) == ([], [])


class TestIsoplanatismPhysics:
    def test_converges_as_eps_shrinks(self):
        """η → предел при ε→0 (члены ∝ε² и выше исчезают)."""
        sys_obj = build_doublet()
        pupils_a, eta_a = compute_isoplanatism(sys_obj, num_rays=21, field_eps=0.4)
        pupils_b, eta_b = compute_isoplanatism(sys_obj, num_rays=21, field_eps=0.1)
        eta_a = np.abs(np.array(eta_a))
        eta_b = np.abs(np.array(eta_b))
        scale = max(eta_a.max(), 1e-9)
        # Разность кривых (нечётные члены ∝ε) убывает вместе с ε
        assert np.max(np.abs(eta_a - eta_b)) < 0.6 * scale

    def test_grows_towards_rim_like_coma(self):
        """Кома ∝ h²: |η| на краю больше, чем в средней зоне зрачка."""
        pupils, etas = compute_isoplanatism(build_doublet(), num_rays=21,
                                            field_eps=0.1)
        h = np.abs(np.array(pupils))
        eta = np.abs(np.array(etas))
        rim = eta[h > 0.85].max()
        mid = eta[(h > 0.3) & (h < 0.5)].max()
        assert rim > mid

    def test_seidel_sii_cross_check(self, lens_systems):
        """Сверка с суммой Зейделя SII: в режиме 3-го порядка (узкая
        апертура) коэффициент комы η(h) ≈ c·h² пропорционален SII."""
        from decode_lbo_opj import decode_lbo_opj

        coma_coefs, seiels_sii = [], []
        for i in [0, 3, 5, 8, 10, 15, 20, 30]:
            sys_obj = decode_lbo_opj(lens_systems[i]['opj_data'])
            sii = seidel_aberrations(sys_obj)['SII']
            orig_aperture = sys_obj.aperture_value
            sys_obj.aperture_value = 4.0  # узкая апертура → 3-й порядок
            pupils, etas = compute_isoplanatism(sys_obj, num_rays=21,
                                                field_eps=0.1)
            sys_obj.aperture_value = orig_aperture
            h = np.array(pupils)
            eta = np.array(etas)
            m = (np.abs(h) > 0.05) & (np.abs(h) <= 0.9)
            if m.sum() < 4 or not math.isfinite(sii):
                continue
            coma_coefs.append(float(np.sum(eta[m] * h[m] ** 2) / np.sum(h[m] ** 4)))
            seiels_sii.append(float(sii))

        assert len(coma_coefs) >= 5, "слишком много систем без данных"
        corr = float(np.corrcoef(coma_coefs, seiels_sii)[0, 1])
        assert corr > 0.9, f"корреляция η-комы с SII = {corr:.3f} < 0.9"


class TestIsoplanatismGui:
    """GUI: окно «Аберрации осевого пучка» 2×2 с 4-м графиком η."""

    @pytest.fixture(autouse=True)
    def _qt_offscreen(self):
        import os
        import sys
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def test_axial_beam_widget_contains_four_graphs(self):
        from gui.widgets import AxialBeamWidget, IsoplanatismWidget
        w = AxialBeamWidget()
        children = [w.transverse, w.longitudinal, w.wavefront, w.isoplanatism]
        assert all(children)
        assert isinstance(w.isoplanatism, IsoplanatismWidget)
        layout = w.layout()
        assert layout.count() == 4

    def test_axial_beam_widget_set_data(self):
        from gui.widgets import AxialBeamWidget
        w = AxialBeamWidget()
        w.resize(800, 600)
        w.set_data(build_doublet())
        assert w.transverse.fan_data, "веер Δy' пуст"
        assert w.isoplanatism.iso_data, "неизопланатизм пуст"
        wl_first = next(iter(w.isoplanatism.iso_data))
        pupils, etas = w.isoplanatism.iso_data[wl_first]
        assert len(pupils) == len(etas) and len(pupils) >= 3

    def test_apply_data(self):
        from gui.widgets import AxialBeamWidget
        w = AxialBeamWidget()
        pupils, etas = compute_isoplanatism(build_doublet(), num_rays=21)
        w.apply_data({0.58756: []}, {0.58756: (pupils, etas)})
        assert w.isoplanatism.iso_data[0.58756][0] == pupils
