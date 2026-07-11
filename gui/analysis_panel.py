"""Analysis panel — main orchestrator tab widget.

:class:`AnalysisPanel` owns all analysis widget instances and manages:
* Two-phase result application (parax/seidel → full analysis).
* Graph/table mode toggling per tab.
* Table construction from precomputed or live-computed data.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QFormLayout, QSplitter,
    QDoubleSpinBox, QComboBox,
    QPushButton, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHeaderView

from optics_engine import OpticalSystem, paraxial_trace, seidel_aberrations
from aberrations import (
    trace_aberration_fan,
    compute_spot_diagram,
    compute_spot_diagram_polychromatic,
    compute_polychromatic_rms,
    compute_rms_spot,
    compute_rms_spot_xy,
    compute_geometric_mtf,
    compute_field_aberrations,
    compute_focus_curve,
    compute_chief_ray_characteristics,
)
from advanced_analysis import (
    compute_psf, compute_lsf, compute_enc, compute_ptf, compute_esf,
    compute_bar_target_mtf_table,
)
from zernike import (
    compute_zernike_coefficients,
    compute_wavefront_map_2d,
    compute_zernike_chromatic,
)
from optics_utils import get_primary_wl, fmt_val

from .widgets import (
    # Table helpers
    make_table,
    clear_layout,
    # Widget classes
    SpotDiagramWidget,
    AberrationGraphWidget,
    MTFWidget,
    DistortionWidget,
    AstigmatismWidget,
    ComaWidget,
    FocusCurveWidget,
    PSFWidget,
    LSFWidget,
    ENCWidget,
    PTFWidget,
    HeatmapWidget,
    BeamGeometryWidget,
    ChiefRayWidget,
    ZernikeWidget,
    WavefrontMapWidget,
    ESFWidget,
    WavefrontRmsVsFieldWidget,
    FocusDiagramWidget,
    PSF3DWidget,
    BarTargetWidget,
)
from .analysis_pipeline import compute_all_analysis


class AnalysisPanel(QTabWidget):
    """Main analysis panel — all graphs and tables in tabbed layout."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Global settings bar ──
        self._settings_widget = QWidget()
        settings_layout = QHBoxLayout(self._settings_widget)
        settings_layout.setContentsMargins(4, 2, 4, 2)

        settings_layout.addWidget(QLabel("Смещение плоскости (мм):"))
        self.defocus_spin = QDoubleSpinBox()
        self.defocus_spin.setRange(-100.0, 100.0)
        self.defocus_spin.setSingleStep(0.01)
        self.defocus_spin.setDecimals(4)
        self.defocus_spin.setValue(0.0)
        self.defocus_spin.setToolTip("Смещение плоскости изображения для всех вкладок")
        settings_layout.addWidget(self.defocus_spin)
        settings_layout.addStretch()

        settings_layout.addWidget(QLabel("Азимут (°):"))
        self.azimuth_spin = QDoubleSpinBox()
        self.azimuth_spin.setRange(0.0, 90.0)
        self.azimuth_spin.setSingleStep(5.0)
        self.azimuth_spin.setDecimals(1)
        self.azimuth_spin.setValue(0.0)
        self.azimuth_spin.setToolTip("Азимутальный угол сечения: 0=меридиональное, 90=сагиттальное")
        settings_layout.addWidget(self.azimuth_spin)
        settings_layout.addStretch()

        settings_layout.addWidget(QLabel("Хроматизм:"))
        self.chromatic_combo = QComboBox()
        self.chromatic_combo.addItems(["Абсолютный", "Разностный", "Спектр"])
        self.chromatic_combo.setToolTip("Режим отображения хроматизма в таблицах")
        settings_layout.addWidget(self.chromatic_combo)
        settings_layout.addStretch()

        # Create plot widgets
        self.spot_diagram = SpotDiagramWidget()
        self.transverse = AberrationGraphWidget('transverse')
        self.longitudinal = AberrationGraphWidget('longitudinal')
        self.wavefront = AberrationGraphWidget('wavefront')
        self.mtf = MTFWidget()
        self.distortion = DistortionWidget()
        self.astigmatism = AstigmatismWidget()
        self.coma = ComaWidget()
        self.focus_curve = FocusCurveWidget()
        self.psf_w = PSFWidget()
        self.lsf_w = LSFWidget()
        self.enc_w = ENCWidget()
        self.ptf_w = PTFWidget()
        self.heatmap_w = HeatmapWidget()
        self.beam_geom = BeamGeometryWidget()
        self.chief_ray = ChiefRayWidget()
        self.zernike_w = ZernikeWidget()
        self.wavefront_map_w = WavefrontMapWidget()
        self.esf_w = ESFWidget()
        self.wf_rms_field_w = WavefrontRmsVsFieldWidget()
        self.focus_diagrams = FocusDiagramWidget()
        self.psf_3d_w = PSF3DWidget()
        self.bar_target_w = BarTargetWidget()

        self._table_containers: dict[str, QWidget] = {}
        self._parax_data = {}
        self._seidel_data = {}
        self._fno = 0
        self._epd = 0
        self._calculation_done = False

        parax_placeholder = QWidget()
        seidel_placeholder = QWidget()

        tabs = [
            ("Параксиальные", parax_placeholder, 'parax'),
            ("Точечная диагр.", self.spot_diagram, 'spot'),
            ("Поперечные Δy'", self.transverse, 'transverse'),
            ("Продольные Δs'", self.longitudinal, 'longitudinal'),
            ("Волновые W", self.wavefront, 'wavefront'),
            ("ЧКХ (MTF)", self.mtf, 'mtf'),
            ("Дисторсия", self.distortion, 'distortion'),
            ("Астигматизм", self.astigmatism, 'astigmatism'),
            ("Кома", self.coma, 'coma'),
            ("Фокусировка", self.focus_curve, 'focus'),
            ("PSF", self.psf_w, 'psf'),
            ("PSF 3D", self.psf_3d_w, 'psf3d'),
            ("LSF", self.lsf_w, 'lsf'),
            ("ESF", self.esf_w, 'esf'),
            ("ENC", self.enc_w, 'enc'),
            ("PTF", self.ptf_w, 'ptf'),
            ("Топограмма", self.heatmap_w, 'heatmap'),
            ("Фокус.диагр.", self.focus_diagrams, 'focus_diag'),
            ("Габариты", self.beam_geom, 'beam'),
            ("Гл. лучи", self.chief_ray, 'chief'),
            ("Цернике", self.zernike_w, 'zernike'),
            ("Волн. фронт", self.wavefront_map_w, 'wfmap'),
            ("СКВ по полю", self.wf_rms_field_w, 'wf_rms_field'),
            ("Мира", self.bar_target_w, 'bar_target'),
            ("Зейдель", seidel_placeholder, 'seidel'),
        ]

        self._table_mode = False
        self._toggle_btns = []

        for title, plot_widget, key in tabs:
            if key in ('parax', 'seidel'):
                container = QWidget()
                container.setLayout(QVBoxLayout(container))
                container.layout().setContentsMargins(0, 0, 0, 0)
                self._table_containers[key] = container
                self.addTab(container, title)
                continue

            toggle_btn = QPushButton("📊 График")
            toggle_btn.setCheckable(True)
            toggle_btn.setChecked(False)
            toggle_btn.setFixedWidth(90)
            toggle_btn.setToolTip("Переключить: график / таблица")
            toggle_btn.setStyleSheet(
                "QPushButton { font-size: 10px; padding: 2px 4px; }"
                "QPushButton:checked { background-color: #505080; }"
            )

            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(plot_widget)
            container = QWidget()
            container.setLayout(QVBoxLayout(container))
            container.layout().setContentsMargins(0, 0, 0, 0)
            container.setMinimumWidth(0)
            splitter.addWidget(container)
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 0)
            container.hide()
            self._table_containers[key] = container

            tab_page = QWidget()
            tab_page_layout = QVBoxLayout(tab_page)
            tab_page_layout.setContentsMargins(0, 0, 0, 0)
            tab_page_layout.setSpacing(0)

            top_bar = QHBoxLayout()
            top_bar.setContentsMargins(4, 1, 4, 1)
            top_bar.addWidget(toggle_btn)
            top_bar.addStretch()
            tab_page_layout.addLayout(top_bar)
            tab_page_layout.addWidget(splitter)

            toggle_btn._splitter = splitter
            toggle_btn._plot_widget = plot_widget
            toggle_btn._table_container = container
            self._toggle_btns.append(toggle_btn)
            toggle_btn.toggled.connect(
                lambda checked, btn=toggle_btn: self._on_mode_toggle(btn, checked))

            self.addTab(tab_page, title)

    # ------------------------------------------------------------------
    #  Mode toggle
    # ------------------------------------------------------------------

    def _on_mode_toggle(self, btn, checked: bool) -> None:
        """Toggle graph/table mode globally."""
        self._table_mode = checked
        for b in self._toggle_btns:
            b.blockSignals(True)
            b.setChecked(checked)
            b.blockSignals(False)
            b.setText("📋 Таблица" if checked else "📊 График")
            container = b._table_container
            plot = b._plot_widget
            splitter = b._splitter
            if checked:
                plot.hide()
                container.show()
                splitter.setStretchFactor(0, 0)
                splitter.setStretchFactor(1, 1)
            else:
                plot.show()
                container.hide()
                splitter.setStretchFactor(0, 1)
                splitter.setStretchFactor(1, 0)

    def _set_table(self, key: str, table) -> None:
        """Replace the table widget in a container."""
        container = self._table_containers[key]
        layout = container.layout()
        clear_layout(layout)
        if table:
            layout.addWidget(table)

    # ------------------------------------------------------------------
    #  Parax / Seidel
    # ------------------------------------------------------------------

    def update_parax(self, parax_dict: dict, fno: float, epd: float, sys=None) -> None:
        self._parax_data = parax_dict or {}
        self._fno = fno
        self._epd = epd
        self._parax_sys = sys
        self._update_parax_table()

    def update_seidel(self, seidel_dict: dict) -> None:
        self._seidel_data = seidel_dict or {}
        self._update_seidel_table()

    def _update_parax_table(self) -> None:
        from optics_engine import paraxial_trace as _paraxial_trace
        parax = self._parax_data
        if not parax:
            self._set_table('parax', make_table(
                ["Параметр", "Значение"], [["—", "Нет данных"]], [120, 120]))
            return

        sys = getattr(self, '_parax_sys', None)
        wl_labels = []
        parax_by_wl = {}
        if sys and sys.wavelengths:
            for wl in sys.wavelengths:
                label = wl.name if wl.name else f"{wl.value:.4f}"
                try:
                    sys_wl = copy.deepcopy(sys)
                    sys_wl.wavelengths = [type(wl)(wl.value, 1.0, wl.name)]
                    parax_by_wl[label] = _paraxial_trace(sys_wl)
                    wl_labels.append(label)
                except Exception:
                    pass
        if not wl_labels:
            wl_labels = ['d']
            parax_by_wl['d'] = parax
        n_wl = len(wl_labels)

        f_val = parax.get('focal_length', 0)
        common_rows = [
            ["F", f"{-f_val:.4f}"],
            ["F'", f"{f_val:.4f}"],
            ["sF", f"{parax.get('sF', 0):.4f}"],
            ["sF'", f"{parax.get('sF_prime', 0):.4f}"],
            ["sH", f"{parax.get('sH', 0):.4f}"],
            ["sH'", f"{parax.get('sH_prime', 0):.4f}"],
            ["L", f"{parax.get('L', 0):.2f}"],
            ["f/#", f"{self._fno:.2f}"],
            ["D вх.зрачка", f"{self._epd:.2f}"],
        ]
        table1 = make_table(["Кардинальные", "Значение"], common_rows, [90, 80])
        table1.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        per_wl_keys = [
            ("s' (дптр)", 'back_focal_distance'),
            ("s' (мм)", 'back_focal_distance'),
            ("s'G (мм)", 'back_focal_distance'),
            ("V", 'V'),
            ("sP (мм)", 'sP'),
            ("sP' (мм)", 'sP_prime'),
        ]
        wl_headers = ["Параметр"] + wl_labels
        wl_rows = []
        for name, key in per_wl_keys:
            vals = []
            raw_vals = []
            for wl in wl_labels:
                p = parax_by_wl.get(wl, {})
                v = p.get(key, 0)
                if 'дптр' in name and v:
                    v = 1000.0 / v if abs(v) > 1e-10 else 0
                raw_vals.append(v)
            if name == 'V' and len(raw_vals) > 1:
                base = raw_vals[0]
                for i, v in enumerate(raw_vals):
                    if i == 0:
                        vals.append(f"{v:.5f}" if v is not None else "—")
                    else:
                        vals.append(f"{v - base:+.5f}" if v is not None else "—")
            else:
                for v in raw_vals:
                    vals.append(f"{v:.4f}" if v is not None else "—")
            wl_rows.append([name] + vals)
        table2 = make_table(wl_headers, wl_rows, [60] + [55] * n_wl)
        table2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(table1)
        splitter.addWidget(table2)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self._set_table('parax', splitter)

    def _update_seidel_table(self) -> None:
        seidel = self._seidel_data
        if not seidel:
            self._set_table('seidel', make_table(
                ["Сумма", "Значение"], [["—", "Нет данных"]], [120, 120]))
            return
        rows = [
            ("SI — сферическая", f"{seidel.get('SI', 0):.6e}"),
            ("SII — кома", f"{seidel.get('SII', 0):.6e}"),
            ("SIII — астигматизм", f"{seidel.get('SIII', 0):.6e}"),
            ("SIV — кривизна", f"{seidel.get('SIV', 0):.6e}"),
            ("SV — дисторсия", f"{seidel.get('SV', 0):.6e}"),
        ]
        table = make_table(["Сумма", "Значение"], rows, [130, 100])
        self._set_table('seidel', table)

    # ------------------------------------------------------------------
    #  Settings accessors
    # ------------------------------------------------------------------

    def get_defocus_offset(self) -> float:
        return self.defocus_spin.value() if hasattr(self, 'defocus_spin') else 0.0

    def get_azimuth(self) -> float:
        return self.azimuth_spin.value() if hasattr(self, 'azimuth_spin') else 0.0

    # ------------------------------------------------------------------
    #  Precomputed data application
    # ------------------------------------------------------------------

    def apply_precomputed(self, sys: OpticalSystem, data: dict) -> None:
        """Apply precomputed analysis data to all widgets (GUI thread)."""
        d = data
        self.spot_diagram.spots_mono = d.get('spot_mono', [])
        self.spot_diagram.rms = d.get('spot_rms', 0)
        self.spot_diagram._wl_cache = d.get('wl_list', [0.588])
        self.spot_diagram.spots_poly = d.get('spot_poly', [])
        self.spot_diagram.poly_rms = d.get('poly_rms', 0)
        self.spot_diagram.update()

        for widget in [self.transverse, self.longitudinal, self.wavefront]:
            widget.fan_data = d.get('fan_data', {})
            widget.isoplanatism_data = d.get('isoplanatism_data', {})
            widget.oblique_data = d.get('oblique_data')
            widget.update()

        self.mtf.geo_mtf = d.get('geo_mtf')
        self.mtf.diff_mtf = d.get('diff_mtf')
        self.mtf.poly_mtf = d.get('poly_mtf')
        self.mtf.diff_limited_mtf = d.get('diff_limited_mtf')
        self.mtf.update()

        fd = d.get('field_data')
        self.distortion.field_data = fd; self.distortion.update()
        self.astigmatism.field_data = fd; self.astigmatism.update()
        self.coma.field_data = fd; self.coma.update()

        curve = d.get('focus_curve')
        self.focus_curve.curve_data = curve
        if curve:
            best = max(curve, key=lambda p: p[1])
            self.focus_curve.best_defocus = best[0]
            self.focus_curve.best_mtf = best[1]
        self.focus_curve.update()

        self.psf_w.psf_data = d.get('psf_data'); self.psf_w.dx = d.get('psf_dx'); self.psf_w.dy = d.get('psf_dy'); self.psf_w.update()
        self.lsf_w.lsf_tan = d.get('lsf_tan'); self.lsf_w.lsf_sag = d.get('lsf_sag'); self.lsf_w.axis = d.get('lsf_ax'); self.lsf_w.update()
        self.esf_w.x_um = d.get('esf_x'); self.esf_w.esf = d.get('esf_y'); self.esf_w.update()
        self.enc_w.r_um = d.get('enc_r'); self.enc_w.enc = d.get('enc_e'); self.enc_w.update()
        self.ptf_w.ptf_data = d.get('ptf_data'); self.ptf_w.update()

        self.heatmap_w.heatmap = d.get('heatmap')
        self.heatmap_w.x_range = d.get('heatmap_x_range', (0, 0))
        self.heatmap_w.y_range = d.get('heatmap_y_range', (0, 0))
        self.heatmap_w.centroid_x = d.get('heatmap_centroid_x', 0)
        self.heatmap_w.centroid_y = d.get('heatmap_centroid_y', 0)
        self.heatmap_w.max_density = d.get('heatmap_max_density', 0)
        self.heatmap_w.num_points = d.get('heatmap_num_points', 0)
        self.heatmap_w.update()

        self.beam_geom.beam_data = d.get('beam_data'); self.beam_geom.update()
        self.chief_ray.chief_data = d.get('chief_data'); self.chief_ray.update()
        self.zernike_w.coeffs = d.get('zernike_coeffs', [])
        self.zernike_w.chromatic_data = d.get('zernike_chromatic'); self.zernike_w.update()
        self.wavefront_map_w.wf_data = d.get('wf_data')
        self.wavefront_map_w.coords = d.get('wf_coords')
        self.wavefront_map_w.mask = d.get('wf_mask'); self.wavefront_map_w.update()
        self.wf_rms_field_w.field_data = d.get('wf_rms_field'); self.wf_rms_field_w.update()
        self.focus_diagrams.spots_by_defocus = d.get('focus_diag_data', {})
        self.focus_diagrams.max_range = d.get('focus_diag_max_range', 0.001); self.focus_diagrams.update()
        self.psf_3d_w.x_coords = d.get('psf3d_x'); self.psf_3d_w.y_coords = d.get('psf3d_y')
        self.psf_3d_w.Z = d.get('psf3d_Z'); self.psf_3d_w.update()
        self.bar_target_w.x_um = d.get('bar_x'); self.bar_target_w.ideal = d.get('bar_ideal')
        self.bar_target_w.blurred = d.get('bar_blurred'); self.bar_target_w.mtf_table = d.get('bar_mtf_table')
        self.bar_target_w.update()

        self._build_tables_precomputed(sys, d)

    def _build_tables_precomputed(self, sys: OpticalSystem, d: dict) -> None:
        """Build all tables from precomputed data."""
        wl = d.get('wl', 0.58756)
        wl_list = d.get('wl_list', [0.58756])

        rows = []
        spots_mono = d.get('spot_mono', [])
        rms = d.get('spot_rms', 0)
        rms_xy = d.get('spot_rms_xy', {})
        max_r = max((math.sqrt(dx**2 + dy**2) for dx, dy in spots_mono), default=0)
        rows.append(["0.0", f"{wl:.4f}", str(len(spots_mono)),
                     f"{rms:.4f}", f"{rms_xy.get('rms_x', 0):.4f}",
                     f"{rms_xy.get('rms_y', 0):.4f}",
                     f"{rms_xy.get('centroid_y', 0):.4f}", f"{max_r:.4f}"])
        if len(wl_list) > 1:
            poly_spots = d.get('spot_poly', [])
            poly_rms = d.get('poly_rms', 0)
            poly_rms_xy = d.get('poly_rms_xy', {})
            poly_max = max((math.sqrt(dx**2 + dy**2) for dx, dy, _ in poly_spots), default=0)
            rows.append(["0.0", "\u043f\u043e\u043b\u0438\u0445\u0440.", str(len(poly_spots)),
                         f"{poly_rms:.4f}", f"{poly_rms_xy.get('rms_x', 0):.4f}",
                         f"{poly_rms_xy.get('rms_y', 0):.4f}",
                         f"{poly_rms_xy.get('centroid_y', 0):.4f}", f"{poly_max:.4f}"])
        self._set_table('spot', make_table(
            ["\u041f\u043e\u043b\u0435", "\u03bb, \u043c\u043a\u043c", "\u041b\u0443\u0447\u0435\u0439", "RMS, \u043c\u043c",
             "RMS_X", "RMS_Y", "Y\u0446\u044d", "\u041c\u0430\u043a\u0441 R, \u043c\u043c"],
            rows, [35, 55, 40, 60, 60, 60, 60, 60]))

        fan_primary = d.get('fan_data', {}).get(wl, [])
        for key, val_key in [('transverse', 'dy'), ('longitudinal', 'ds'), ('wavefront', 'wave')]:
            rows_fan = []
            step = max(1, len(fan_primary) // 13)
            for i in range(0, len(fan_primary), step):
                r = fan_primary[i]
                if r['success']:
                    if val_key == 'dy':
                        rows_fan.append([f"{r['pupil_y']:.4f}", f"{r['dy']*1000:.5f}"])
                    elif val_key == 'ds':
                        rows_fan.append([f"{r['pupil_y']:.4f}", f"{r['ds']:.5f}"])
                    else:
                        rows_fan.append([f"{r['pupil_y']:.4f}", f"{r['wave']:.5f}"])
            if val_key == 'dy':
                self._set_table(key, make_table(
                    ["\u0412\u044b\u0441\u043e\u0442\u0430 \u043b\u0443\u0447\u0430", "\u0394y' (\u043c\u043a\u043c)"],
                    rows_fan, [100, 100]))
            elif val_key == 'ds':
                self._set_table(key, make_table(
                    ["\u0412\u044b\u0441\u043e\u0442\u0430 \u043b\u0443\u0447\u0430", "\u0394s' (\u043c\u043c)"],
                    rows_fan, [100, 100]))
            else:
                self._set_table(key, make_table(
                    ["\u0412\u044b\u0441\u043e\u0442\u0430 \u043b\u0443\u0447\u0430", "W (\u03bb)"],
                    rows_fan, [100, 100]))

        geo_mtf = d.get('geo_mtf')
        diff_mtf = d.get('diff_mtf')
        diff_ltd = d.get('diff_limited_mtf')
        rows_mtf = []
        if geo_mtf:
            for i, (freq, mtf_t, mtf_s) in enumerate(geo_mtf):
                dt = ds = dl = ""
                if diff_mtf and i < len(diff_mtf['freqs']):
                    dt = f"{diff_mtf['mtf_tangential'][i]:.4f}"
                    ds = f"{diff_mtf['mtf_sagittal'][i]:.4f}" if i < len(diff_mtf.get('mtf_sagittal', [])) else ""
                if diff_ltd and i < len(diff_ltd['freqs']):
                    dl = f"{diff_ltd['mtf'][i]:.4f}"
                rows_mtf.append([f"{freq:.2f}", f"{mtf_t:.4f}", f"{mtf_s:.4f}", dt, ds, dl, ""])
        self._set_table('mtf', make_table(
            ["\u0427\u0430\u0441\u0442\u043e\u0442\u0430", "\u0413.\u043c\u0435\u0440.", "\u0413.\u0441\u0430\u0433.",
             "\u0414.\u043c\u0435\u0440.", "\u0414.\u0441\u0430\u0433.", "\u0411\u0435\u0437\u0430\u0431.", "\u041f\u043e\u043b\u0438\u0445\u0440."],
            rows_mtf, [45, 48, 48, 48, 48, 48, 45]))

        field_data = d.get('field_data', [])
        rows_dist = []; rows_astig = []; rows_coma = []
        for dd in field_data:
            fy = dd['field_y']
            if dd.get('distortion') is not None:
                dist_pct = dd['distortion']
                dist_mm = fy * dist_pct / 100.0 if abs(fy) > 1e-10 else 0.0
                rows_dist.append([f"{fy:.4f}", f"{dist_pct:.5f}", f"{dist_mm:.5f}"])
            if dd.get('z_m') is not None:
                dz = dd['z_m'] - dd['z_s']
                rows_astig.append([f"{fy:.4f}", f"{dd['z_m']:.5f}", f"{dd['z_s']:.5f}", f"{dz:.5f}"])
            if dd.get('coma') is not None:
                coma_y = dd['coma'] * 1000
                rows_coma.append([f"{fy:.4f}", "0.0000", f"{coma_y:.5f}"])
        self._set_table('distortion', make_table(
            ["\u041f\u043e\u043b\u0435 Y (\u043c\u043c)", "\u0414\u0438\u0441\u0442. %", "\u0414\u0438\u0441\u0442. (\u043c\u043c)"],
            rows_dist, [75, 70, 75]))
        self._set_table('astigmatism', make_table(
            ["\u041f\u043e\u043b\u0435 Y (\u043c\u043c)", "Z'm (\u043c\u043c)", "Z's (\u043c\u043c)", "\u0394Z (\u043c\u043c)"],
            rows_astig, [70, 65, 65, 65]))
        self._set_table('coma', make_table(
            ["\u041f\u043e\u043b\u0435 Y (\u043c\u043c)", "\u041a\u043e\u043c\u0430 X (\u043c\u043a\u043c)", "\u041a\u043e\u043c\u0430 Y (\u043c\u043a\u043c)"],
            rows_coma, [75, 75, 75]))

        curve = d.get('focus_curve')
        if curve:
            best_defocus = max(curve, key=lambda p: p[1])[0]
            rows_fc = []
            step = max(1, len(curve) // 15)
            for i in range(0, len(curve), step):
                dd_f, mt = curve[i][0], curve[i][1]
                ms = curve[i][2] if len(curve[i]) > 2 else 0.0
                rows_fc.append([f"{dd_f:+.4f}", f"{mt:.4f}", f"{ms:.4f}"])
            table = make_table(
                ["\u0394defocus (\u043c\u043c)", "MTF \u043c\u0435\u0440.", "MTF \u0441\u0430\u0433."],
                rows_fc, [80, 70, 70])
            for i, rd in enumerate(rows_fc):
                if abs(float(rd[0]) - best_defocus) < 0.001:
                    font = QFont("Courier", 9); font.setBold(True)
                    for j in range(table.columnCount()):
                        item = table.item(i, j)
                        if item:
                            item.setFont(font)
                    break
            self._set_table('focus', table)
        else:
            self._set_table('focus', None)

        rows_psf = [["\u03bb \u043f\u0435\u0440\u0432.", f"{wl:.4f} \u043c\u043a\u043c"]]
        psf_data = d.get('psf_data'); psf_dx = d.get('psf_dx'); psf_dy = d.get('psf_dy')
        if psf_data is not None and psf_dx is not None:
            pix_size = (psf_dx.max() - psf_dx.min()) / len(psf_dx) if len(psf_dx) > 1 else 0
            max_intens = psf_data.max()
            cy, cx = np.unravel_index(np.argmax(psf_data), psf_data.shape)
            center_x = psf_dx[cx] if cx < len(psf_dx) else 0
            center_y = psf_dy[cy] if cy < len(psf_dy) else 0
            row_c = psf_data[cy, :]; col_c = psf_data[:, cx]
            half_max = max_intens / 2
            try:
                w_mer = (psf_dx.max() - psf_dx.min()) / len(psf_dx) * np.sum(row_c > half_max)
                w_sag = (psf_dy.max() - psf_dy.min()) / len(psf_dy) * np.sum(col_c > half_max)
            except Exception:
                w_mer = w_sag = 0
            rows_psf.append(["\u0420\u0430\u0437\u043c. \u043f\u0438\u043a\u0441.", f"{pix_size:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u041c\u0430\u043a\u0441. \u0438\u043d\u0442\u0435\u043d\u0441.", f"{max_intens:.5f}"])
            rows_psf.append(["\u0426\u0435\u043d\u0442\u0440 X", f"{center_x:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u0426\u0435\u043d\u0442\u0440 Y", f"{center_y:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u0428\u0438\u0440. \u043c\u0435\u0440.", f"{w_mer:.4f} \u043c\u043a\u043c"])
            rows_psf.append(["\u0428\u0438\u0440. \u0441\u0430\u0433.", f"{w_sag:.4f} \u043c\u043a\u043c"])
        else:
            rows_psf.append(["\u041e\u0448\u0438\u0431\u043a\u0430", "\u2014"])
        self._set_table('psf', make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_psf, [100, 120]))

        lsf_tan = d.get('lsf_tan'); lsf_ax = d.get('lsf_ax'); lsf_sag = d.get('lsf_sag')
        if lsf_tan is not None and lsf_ax is not None:
            rows_lsf = []
            n = len(lsf_ax); step = max(1, n // 15)
            for i in range(0, n, step):
                rows_lsf.append([f"{lsf_ax[i]:.4f}", f"{lsf_tan[i]:.5f}", f"{lsf_sag[i]:.5f}"])
            self._set_table('lsf', make_table(
                ["\u041a\u043e\u043e\u0440\u0434. (\u043c\u043a\u043c)", "\u041c\u0435\u0440\u0438\u0434. LSF", "\u0421\u0430\u0433\u0438\u0442. LSF"],
                rows_lsf, [75, 75, 75]))
        else:
            self._set_table('lsf', None)

        esf_x = d.get('esf_x'); esf_y = d.get('esf_y')
        if esf_x is not None:
            rows_esf = []; n = len(esf_x); step = max(1, n // 15)
            for i in range(0, n, step):
                rows_esf.append([f"{esf_x[i]:.4f}", f"{esf_y[i]:.5f}"])
            self._set_table('esf', make_table(
                ["\u041a\u043e\u043e\u0440\u0434. (\u043c\u043a\u043c)", "ESF"], rows_esf, [90, 90]))
        else:
            self._set_table('esf', None)

        enc_r = d.get('enc_r'); enc_e = d.get('enc_e')
        if enc_r is not None:
            rows_enc = []; n = len(enc_r); step = max(1, n // 13)
            for i in range(0, n, step):
                rows_enc.append([f"{enc_r[i]*2:.4f}", f"{enc_e[i]*100:.2f}"])
            for pct in [0.5, 0.8, 0.9]:
                idx = np.searchsorted(enc_e, pct)
                if idx < len(enc_r):
                    dd_enc = enc_r[idx] * 2
                    rows_enc.append([f"D@{int(pct*100)}%={dd_enc:.4f}", f"{pct*100:.2f}%"])
            self._set_table('enc', make_table(
                ["D \u043a\u0440\u0443\u0433\u0430 (\u043c\u043a\u043c)", "\u041f\u043e\u043b\u0438\u0445\u0440. %"],
                rows_enc, [110, 80]))
        else:
            self._set_table('enc', None)

        ptf_data = d.get('ptf_data')
        if ptf_data is not None:
            freqs = ptf_data['freqs']; ptf_t = ptf_data['ptf_tangential']; ptf_s = ptf_data['ptf_sagittal']
            rows_ptf = []; step = max(1, len(freqs) // 15)
            for i in range(0, len(freqs), step):
                rows_ptf.append([f"{freqs[i]:.2f}", f"{ptf_t[i]:.5f}", f"{ptf_s[i]:.5f}"])
            self._set_table('ptf', make_table(
                ["\u0427\u0430\u0441\u0442\u043e\u0442\u0430 (\u043b/\u043c\u043c)", "PTF \u043c\u0435\u0440. (\u0440\u0430\u0434)", "PTF \u0441\u0430\u0433. (\u0440\u0430\u0434)"],
                rows_ptf, [75, 80, 80]))
        else:
            self._set_table('ptf', None)

        rows_hm = [["\u0414\u043b\u0438\u043d\u0430 \u0432\u043e\u043b\u043d\u044b", f"{wl:.4f} \u043c\u043a\u043c"],
                   ["\u0421\u0435\u0442\u043a\u0430", f"100\u00d7100"]]
        if d.get('heatmap') is not None:
            xr = d['heatmap_x_range']; yr = d['heatmap_y_range']
            x_span = (xr[1] - xr[0]) * 1000; y_span = (yr[1] - yr[0]) * 1000
            rows_hm.append(["\u0420\u0430\u0437\u043c\u0435\u0440 \u043f\u043e\u043b\u044f", f"{x_span:.4f}\u00d7{y_span:.4f} \u043c\u043a\u043c"])
            rows_hm.append(["\u041f\u0438\u043a\u0441\u0435\u043b\u0435\u0439 \u0441 \u0434\u0430\u043d\u043d\u044b\u043c\u0438", str(d.get('heatmap_num_points', 0))])
            rows_hm.append(["\u041c\u0430\u043a\u0441. \u043f\u043b\u043e\u0442\u043d\u043e\u0441\u0442\u044c", f"{d.get('heatmap_max_density', 0):.4f}"])
            rows_hm.append(["\u0426\u0435\u043d\u0442\u0440\u043e\u0438\u0434 X", f"{d.get('heatmap_centroid_x', 0)*1000:.4f} \u043c\u043a\u043c"])
            rows_hm.append(["\u0426\u0435\u043d\u0442\u0440\u043e\u0438\u0434 Y", f"{d.get('heatmap_centroid_y', 0)*1000:.4f} \u043c\u043a\u043c"])
        else:
            rows_hm.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        self._set_table('heatmap', make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_hm, [130, 130]))

        beam_data = d.get('beam_data', [])
        rows_beam = []
        for bd in beam_data:
            rows_beam.append([f"{bd['field_y']:.4f}", f"{bd['Ay']:.4f}", f"{bd['Ay_prime']:.4f}",
                              f"{bd['vignetting_upper']:.4f}", f"{bd['vignetting_lower']:.4f}",
                              f"{bd['relative_illumination']:.4f}"])
        self._set_table('beam', make_table(
            ["\u041f\u043e\u043b\u0435", "Ay", "Ay'", "\u0412\u0438\u043d\u044c\u0435\u0442.\u2191",
             "\u0412\u0438\u043d\u044c\u0435\u0442.\u2193", "\u0421\u0432\u0435\u0442\u043e\u0440\u0430\u0441\u043f\u0440."],
            rows_beam, [45, 50, 50, 55, 55, 60]))

        chief_data = d.get('chief_data', [])
        rows_chief = []
        for cd in chief_data:
            rows_chief.append([f"{cd['field_y']:.4f}", f"{cd['distortion_abs']:.6f}",
                               f"{cd['distortion_rel']:.6f}", f"{cd['Zm']:.6f}",
                               f"{cd['Zs']:.6f}", f"{cd['lateral_color']:.6f}"])
        self._set_table('chief', make_table(
            ["\u041f\u043e\u043b\u0435", "\u0414\u0438\u0441\u0442.\u0430\u0431\u0441", "\u0414\u0438\u0441\u0442.%",
             "Z'm", "Z's", "\u0425\u0440.\u0443\u0432\u0435\u043b."],
            rows_chief, [45, 60, 55, 60, 60, 60]))

        zernike_coeffs = d.get('zernike_coeffs', [])
        zernike_chromatic = d.get('zernike_chromatic')
        if zernike_chromatic and self.zernike_w._show_chromatic:
            wl_keys = [k for k in zernike_chromatic if not k.startswith('delta_')]
            if wl_keys:
                headers = ["\u041f\u043e\u043b\u0438\u043d\u043e\u043c"] + wl_keys
                rows_zk = []
                for idx, (val, name) in enumerate(zernike_coeffs):
                    row = [name]
                    for key in wl_keys:
                        if key in zernike_chromatic:
                            for c, n in zernike_chromatic[key]:
                                if n == name:
                                    row.append(f"{c:+.6f}")
                                    break
                            else:
                                row.append("\u2014")
                        else:
                            row.append("\u2014")
                    rows_zk.append(row)
                delta_headers = [k for k in ['delta_F-d', 'delta_C-d'] if k in zernike_chromatic]
                for delta_key in delta_headers:
                    for idx, (val, name) in enumerate(zernike_chromatic[delta_key]):
                        if idx < len(rows_zk):
                            rows_zk[idx].append(f"{val:+.6f}")
                headers.extend(delta_headers)
                self._set_table('zernike', make_table(
                    headers, rows_zk, [80] + [70] * (len(headers) - 1)))
                return
        rows_z = []
        for val, name in zernike_coeffs:
            rows_z.append([name, f"{val:+.6f}"])
        self._set_table('zernike', make_table(
            ["\u041f\u043e\u043b\u0438\u043d\u043e\u043c", "\u041a\u043e\u044d\u0444\u0444. (\u03bb)"],
            rows_z, [120, 90]))

        wf_data = d.get('wf_data'); wf_mask = d.get('wf_mask')
        rows_wf = [["\u03bb \u043f\u0435\u0440\u0432.", f"{wl:.4f} \u043c\u043a\u043c"]]
        if wf_data is not None and wf_mask is not None:
            valid = wf_data[wf_mask > 0]
            if valid.size > 0:
                rows_wf.append(["PV", f"{valid.max()-valid.min():.5f} \u03bb"])
                rows_wf.append(["RMS", f"{np.sqrt(np.mean(valid**2)):.5f} \u03bb"])
                rows_wf.append(["\u041c\u0438\u043d", f"{valid.min():.5f} \u03bb"])
                rows_wf.append(["\u041c\u0430\u043a\u0441", f"{valid.max():.5f} \u03bb"])
                rows_wf.append(["\u0421\u0435\u0442\u043a\u0430", f"{wf_data.shape[0]}\u00d7{wf_data.shape[1]}"])
            else:
                rows_wf.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        else:
            rows_wf.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        self._set_table('wfmap', make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_wf, [100, 120]))

        fd_data = d.get('focus_diag_data', {})
        if fd_data:
            rows_fd = []
            for label in ["\u043d\u043e\u043c\u0438\u043d\u0430\u043b", "+DS'", "-DS'", "+2DS'", "-2DS'"]:
                if label in fd_data:
                    spots, rms_info, df = fd_data[label]
                    rows_fd.append([label, f"{df:+.4f}", str(len(spots)),
                                    f"{rms_info['rms_total']:.5f}",
                                    f"{rms_info['rms_x']:.4f}",
                                    f"{rms_info['rms_y']:.4f}"])
            self._set_table('focus_diag', make_table(
                ["\u041f\u043e\u0437.", "\u0394z (\u043c\u043c)", "\u041b\u0443\u0447\u0435\u0439", "RMS", "RMS_X", "RMS_Y"],
                rows_fd, [55, 65, 40, 65, 65, 65]))
        else:
            self._set_table('focus_diag', None)

        rows_p3 = [["\u03bb \u043f\u0435\u0440\u0432.", f"{wl:.4f} \u043c\u043a\u043c"]]
        psf3d_Z = d.get('psf3d_Z'); psf3d_x = d.get('psf3d_x')
        if psf3d_Z is not None:
            rows_p3.append(["\u041c\u0430\u043a\u0441.", f"{psf3d_Z.max():.5f}"])
            rows_p3.append(["\u0420\u0430\u0437\u043c\u0435\u0440", f"{psf3d_Z.shape[0]}\u00d7{psf3d_Z.shape[1]}"])
            if psf3d_x is not None:
                x_span = psf3d_x.max() - psf3d_x.min()
                rows_p3.append(["\u041f\u043e\u043b\u0435 X", f"{x_span:.4f} \u043c\u043a\u043c"])
        else:
            rows_p3.append(["\u0421\u0442\u0430\u0442\u0443\u0441", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"])
        self._set_table('psf3d', make_table(
            ["\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", "\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435"], rows_p3, [100, 120]))

        wf_rms = d.get('wf_rms_field')
        if wf_rms and wf_rms[0]:
            field_vals, rms_full, rms_no_def, rms_no_tilt = wf_rms
            rows_wr = []
            for f, r_f, r_d, r_t in zip(field_vals, rms_full, rms_no_def, rms_no_tilt):
                rows_wr.append([f"{f:.2f}\u00b0", fmt_val(r_f), fmt_val(r_d), fmt_val(r_t)])
            self._set_table('wf_rms_field', make_table(
                ["\u041f\u043e\u043b\u0435", "\u0421\u041a\u0412 (\u03bb)", "\u0421\u041a\u0412-\u0434\u0435\u0444", "\u0421\u041a\u0412-\u0442\u0438\u043b\u044c\u0442"],
                rows_wr, [55, 75, 75, 75]))
        else:
            self._set_table('wf_rms_field', make_table(
                ["\u041f\u043e\u043b\u0435", "\u0421\u041a\u0412 (\u03bb)"],
                [["\u2014", "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"]], [60, 100]))

        bar_mtf = d.get('bar_mtf_table')
        if bar_mtf:
            rows_bt = []
            for entry in bar_mtf:
                rows_bt.append([f"{entry['freq']}", f"{entry['contrast_ideal']:.4f}",
                                f"{entry['contrast_real']:.4f}", f"{entry['mtf']:.4f}"])
            self._set_table('bar_target', make_table(
                ["\u0427\u0430\u0441\u0442\u043e\u0442\u0430 (\u043b/\u043c\u043c)", "\u041a\u043e\u043d\u0442\u0440. \u0438\u0434\u0435\u0430\u043b",
                 "\u041a\u043e\u043d\u0442\u0440. \u0440\u0435\u0430\u043b.", "MTF"],
                rows_bt, [80, 80, 80, 80]))
        else:
            self._set_table('bar_target', None)

    # ------------------------------------------------------------------
    #  Phase 1 / Phase 2
    # ------------------------------------------------------------------

    _PHASE2_WIDGETS = (
        'spot_diagram', 'transverse', 'longitudinal', 'wavefront',
        'mtf', 'distortion', 'astigmatism', 'coma',
        'focus_curve', 'psf_w', 'lsf_w', 'esf_w',
        'enc_w', 'ptf_w', 'heatmap_w', 'beam_geom',
        'chief_ray', 'zernike_w', 'wavefront_map_w',
        'wf_rms_field_w', 'focus_diagrams', 'psf_3d_w',
        'bar_target_w',
    )
    _PHASE2_TABLES = (
        'spot', 'transverse', 'longitudinal', 'wavefront', 'mtf',
        'distortion', 'astigmatism', 'coma', 'focus', 'psf', 'psf3d',
        'lsf', 'esf', 'enc', 'ptf', 'heatmap', 'focus_diag',
        'beam', 'chief', 'zernike', 'wfmap', 'wf_rms_field', 'bar_target',
    )

    def apply_phase1(self, sys: OpticalSystem, data: dict) -> None:
        """Phase 1: update parax + seidel tabs, mark others as pending."""
        self._calculation_done = False
        if not data:
            data = {}
        if 'parax' in data:
            parax = data['parax']
            fno = parax.get('f_number', 0)
            epd = parax.get('entrance_pupil_diameter', 0)
            if fno == 0:
                efl = parax.get('focal_length', 0)
                epd = sys.aperture_value if sys.aperture_value > 0 else efl / 4.0
                fno = efl / epd if epd > 0 else 0
            self.update_parax(parax, fno, epd, sys=sys)
        if 'seidel' in data:
            self.update_seidel(data['seidel'])
        for name in self._PHASE2_WIDGETS:
            widget = getattr(self, name, None)
            if widget is not None:
                widget._pending = True
                widget.update()
        for key in self._PHASE2_TABLES:
            self._set_table(key, make_table(["Статус"], [["⏳ Расчёт анализа..."]], [200]))

    def apply_phase2(self, sys: OpticalSystem, data: dict) -> None:
        """Phase 2: update all remaining widgets with full analysis data."""
        for name in self._PHASE2_WIDGETS:
            widget = getattr(self, name, None)
            if widget is not None:
                widget._pending = False
        if not data:
            self.analyze(sys)
            return
        wl = get_primary_wl(sys)
        if 'spots_mono' in data:
            self.spot_diagram.spots_mono = data['spots_mono']
            self.spot_diagram.rms = data['rms']
            self.spot_diagram._wl_cache = [w.value for w in sys.wavelengths]
            self.spot_diagram.spots_poly = data.get('spots_poly', [])
            self.spot_diagram.poly_rms = data.get('poly_rms', data['rms'])
            self.spot_diagram.update()
        if 'fan_data' in data:
            all_fans = data['fan_data']
            wl_keys = list(all_fans.keys())
            isoplanatism = data.get('isoplanatism', {})
            for key, widget in [('transverse', self.transverse), ('longitudinal', self.longitudinal), ('wavefront', self.wavefront)]:
                widget.fan_data = all_fans
                widget._wl_cache = wl_keys
                if key == 'transverse' and isoplanatism:
                    widget.isoplanatism_data = isoplanatism
                if key == 'transverse':
                    widget.val_key = 'dy'; widget.scale = 1000
                elif key == 'longitudinal':
                    widget.val_key = 'ds'; widget.scale = 1
                else:
                    widget.val_key = 'wave'; widget.scale = 1
                widget.update()
        if 'geo_mtf' in data:
            self.mtf.geo_mtf = data['geo_mtf']
            self.mtf.diff_mtf = data.get('diff_mtf')
            self.mtf.diff_limited_mtf = data.get('diff_ltd')
            self.mtf.update()
        if 'field_aberr' in data:
            fa = data['field_aberr']
            self.distortion.field_data = fa; self.distortion.update()
            self.astigmatism.field_data = fa; self.astigmatism.update()
            self.coma.field_data = fa; self.coma.update()
        if 'focus_curve' in data:
            self.focus_curve.curve_data = data['focus_curve']; self.focus_curve.update()
        if data.get('psf_data') is not None:
            self.psf_w.psf_data, self.psf_w.dx, self.psf_w.dy = data['psf_data']; self.psf_w.update()
        if data.get('lsf_t') is not None:
            self.lsf_w.lsf_tan = data['lsf_t']; self.lsf_w.axis = data['lsf_ax1']
            self.lsf_w.lsf_sag = data['lsf_s']; self.lsf_w.update()
        if data.get('esf_x') is not None:
            self.esf_w.x_um = data['esf_x']; self.esf_w.esf = data['esf_y']; self.esf_w.update()
        if data.get('enc_r') is not None:
            self.enc_w.r_um = data['enc_r']; self.enc_w.enc = data['enc_e']; self.enc_w.update()
        if data.get('ptf_data') is not None:
            self.ptf_w.ptf_data = data['ptf_data']; self.ptf_w.update()
        if 'beam_data' in data:
            self.beam_geom.beam_data = data['beam_data']; self.beam_geom.update()
        if 'chief_data' in data:
            self.chief_ray.chief_data = data['chief_data']; self.chief_ray.update()
        if 'zernike_coeffs' in data:
            self.zernike_w.coeffs = data['zernike_coeffs']
            self.zernike_w.chromatic = data.get('zernike_chromatic'); self.zernike_w.update()
        if data.get('wfmap') is not None:
            wf, coords, mask = data['wfmap']
            self.wavefront_map_w.wf_data = wf; self.wavefront_map_w.coords = coords
            self.wavefront_map_w.mask = mask; self.wavefront_map_w.update()
        if data.get('focus_diagrams'):
            self.focus_diagrams.spots_by_defocus = data['focus_diagrams']
            self.focus_diagrams.max_range = data.get('focus_diag_max', 1e-6); self.focus_diagrams.update()
        if data.get('bar_x') is not None:
            self.bar_target_w.x_um = data['bar_x']; self.bar_target_w.ideal = data['bar_ideal']
            self.bar_target_w.blurred = data['bar_blurred']; self.bar_target_w.mtf_table = data.get('bar_mtf_table')
            self.bar_target_w.update()
        self.heatmap_w.set_data(sys)
        self.wf_rms_field_w.set_data(sys)
        self.psf_3d_w.set_data(sys)
        self._update_spot_table(sys)
        self._update_transverse_table(sys)
        self._update_longitudinal_table(sys)
        self._update_wavefront_table(sys)
        self._update_mtf_table(sys)
        self._update_distortion_table(sys)
        self._update_astigmatism_table(sys)
        self._update_coma_table(sys)
        self._update_focus_table(sys)
        self._update_psf_table(sys)
        self._update_lsf_table(sys)
        self._update_esf_table(sys)
        self._update_enc_table(sys)
        self._update_ptf_table(sys)
        self._update_heatmap_table(sys)
        self._update_beam_table(sys)
        self._update_chief_table(sys)
        self._update_zernike_table(sys)
        self._update_wfmap_table(sys)
        self._update_wf_rms_field_table(sys)
        self._update_focus_diag_table(sys)
        self._update_psf3d_table(sys)
        self._update_bar_target_table(sys)
        self._calculation_done = True

    def apply_results(self, sys: OpticalSystem, data: dict) -> None:
        """Apply pre-computed results (calls both phases for backward compat)."""
        self.apply_phase1(sys, data)
        self.apply_phase2(sys, data)

    # ------------------------------------------------------------------
    #  Synchronous analysis
    # ------------------------------------------------------------------

    def analyze(self, sys: OpticalSystem) -> None:
        """Compute all analysis data and update all widgets synchronously."""
        defocus = self.get_defocus_offset()
        azimuth = self.get_azimuth()
        from optics_engine import paraxial_trace, seidel_aberrations
        parax = paraxial_trace(sys)
        efl = parax.get('focal_length', 0)
        epd = sys.aperture_value if sys.aperture_value > 0 else efl / 4.0
        fno = efl / epd if epd > 0 else 0
        self.update_parax(parax, fno, epd, sys=sys)
        self.update_seidel(seidel_aberrations(sys))
        self.spot_diagram.set_data(sys)
        self.transverse.set_data(sys, azimuth_deg=azimuth)
        self.longitudinal.set_data(sys, azimuth_deg=azimuth)
        self.wavefront.set_data(sys, azimuth_deg=azimuth)
        self.mtf.set_data(sys)
        self.distortion.set_data(sys)
        self.astigmatism.set_data(sys)
        self.coma.set_data(sys)
        self.focus_curve.set_data(sys)
        self.psf_w.set_data(sys)
        self.lsf_w.set_data(sys)
        self.esf_w.set_data(sys, defocus_offset=defocus)
        self.enc_w.set_data(sys)
        self.ptf_w.set_data(sys)
        self.heatmap_w.set_data(sys)
        self.beam_geom.set_data(sys)
        self.chief_ray.set_data(sys)
        self.zernike_w.set_data(sys, defocus_offset=defocus)
        self.wavefront_map_w.set_data(sys, defocus_offset=defocus)
        self.wf_rms_field_w.set_data(sys)
        self.focus_diagrams.set_data(sys)
        self.psf_3d_w.set_data(sys)
        self.bar_target_w.set_data(sys)
        self._update_spot_table(sys)
        self._update_transverse_table(sys)
        self._update_longitudinal_table(sys)
        self._update_wavefront_table(sys)
        self._update_mtf_table(sys)
        self._update_distortion_table(sys)
        self._update_astigmatism_table(sys)
        self._update_coma_table(sys)
        self._update_focus_table(sys)
        self._update_psf_table(sys)
        self._update_lsf_table(sys)
        self._update_esf_table(sys)
        self._update_enc_table(sys)
        self._update_ptf_table(sys)
        self._update_heatmap_table(sys)
        self._update_beam_table(sys)
        self._update_chief_table(sys)
        self._update_zernike_table(sys)
        self._update_wfmap_table(sys)
        self._update_wf_rms_field_table(sys)
        self._update_focus_diag_table(sys)
        self._update_psf3d_table(sys)
        self._update_bar_target_table(sys)
        self._update_parax_table()
        self._update_seidel_table()

    # ------------------------------------------------------------------
    #  Live table builders (compute on the fly)
    #  -----------------------------------------------------------------

    def _update_spot_table(self, sys: OpticalSystem) -> None:
        wl_list = [w.value for w in sys.wavelengths] if sys.wavelengths else [0.58756]
        rows = []
        for field_y in [0.0]:
            for wl in wl_list:
                spots = compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=field_y)
                rms = compute_rms_spot(spots)
                rms_xy = compute_rms_spot_xy(spots)
                max_r = max((math.sqrt(dx**2+dy**2) for dx,dy in spots), default=0)
                rows.append([f"{field_y:.1f}", f"{wl:.4f}", str(len(spots)),
                             f"{rms:.4f}", f"{rms_xy['rms_x']:.4f}",
                             f"{rms_xy['rms_y']:.4f}", f"{rms_xy['centroid_y']:.4f}",
                             f"{max_r:.4f}"])
        if len(wl_list) > 1:
            poly_spots = compute_spot_diagram_polychromatic(sys, num_rays=40, field_y=0.0)
            poly_rms = compute_polychromatic_rms(sys, num_rays=40, field_y=0.0)
            poly_rms_xy = compute_rms_spot_xy([(dx, dy) for dx, dy, _ in poly_spots])
            poly_max = max((math.sqrt(dx**2+dy**2) for dx,dy,_ in poly_spots), default=0)
            rows.append(["0.0", "полихр.", str(len(poly_spots)),
                         f"{poly_rms:.4f}", f"{poly_rms_xy['rms_x']:.4f}",
                         f"{poly_rms_xy['rms_y']:.4f}", f"{poly_rms_xy['centroid_y']:.4f}",
                         f"{poly_max:.4f}"])
        self._set_table('spot', make_table(
            ["Поле", "λ, мкм", "Лучей", "RMS, мм", "RMS_X", "RMS_Y", "Yцэ", "Макс R, мм"],
            rows, [35, 55, 40, 60, 60, 60, 60, 60]))

    def _update_transverse_table(self, sys: OpticalSystem) -> None:
        rows = []; wl = get_primary_wl(sys)
        fan = trace_aberration_fan(sys, wl, num_rays=30)
        step = max(1, len(fan) // 13)
        for i in range(0, len(fan), step):
            r = fan[i]
            if r['success']:
                rows.append([f"{r['pupil_y']:.4f}", f"{r['dy']*1000:.5f}"])
        self._set_table('transverse', make_table(["Высота луча", "Δy' (мкм)"], rows, [100, 100]))

    def _update_longitudinal_table(self, sys: OpticalSystem) -> None:
        rows = []; wl = get_primary_wl(sys)
        fan = trace_aberration_fan(sys, wl, num_rays=30)
        step = max(1, len(fan) // 13)
        for i in range(0, len(fan), step):
            r = fan[i]
            if r['success']:
                rows.append([f"{r['pupil_y']:.4f}", f"{r['ds']:.5f}"])
        self._set_table('longitudinal', make_table(["Высота луча", "Δs' (мм)"], rows, [100, 100]))

    def _update_wavefront_table(self, sys: OpticalSystem) -> None:
        rows = []; wl = get_primary_wl(sys)
        fan = trace_aberration_fan(sys, wl, num_rays=30)
        step = max(1, len(fan) // 13)
        for i in range(0, len(fan), step):
            r = fan[i]
            if r['success']:
                rows.append([f"{r['pupil_y']:.4f}", f"{r['wave']:.5f}"])
        self._set_table('wavefront', make_table(["Высота луча", "W (λ)"], rows, [100, 100]))

    def _update_mtf_table(self, sys: OpticalSystem) -> None:
        rows = []; wl = get_primary_wl(sys)
        spots = compute_spot_diagram(sys, wl=wl, num_rays=40)
        geo_mtf = compute_geometric_mtf(spots, max_freq=100, num_freqs=20)
        diff_mtf = None
        try:
            from diffraction_mtf import compute_diffraction_mtf_quick
            diff_mtf = compute_diffraction_mtf_quick(sys, wl=wl)
        except Exception:
            pass
        diff_limited_mtf = None
        try:
            from diffraction_mtf import compute_diffraction_limited_mtf
            diff_limited_mtf = compute_diffraction_limited_mtf(sys, wl=wl)
        except Exception:
            pass
        for i, (freq, mtf_t, mtf_s) in enumerate(geo_mtf):
            d_t = ""; d_s = ""; dl = ""; poly = ""
            if diff_mtf and i < len(diff_mtf['freqs']):
                d_t = f"{diff_mtf['mtf_tangential'][i]:.4f}"
                d_s = f"{diff_mtf['mtf_sagittal'][i]:.4f}" if i < len(diff_mtf.get('mtf_sagittal', [])) else ""
            if diff_limited_mtf and i < len(diff_limited_mtf['freqs']):
                dl = f"{diff_limited_mtf['mtf'][i]:.4f}"
            rows.append([f"{freq:.2f}", f"{mtf_t:.4f}", f"{mtf_s:.4f}", d_t, d_s, dl, poly])
        self._set_table('mtf', make_table(
            ["Частота", "Г.мер.", "Г.саг.", "Д.мер.", "Д.саг.", "Безаб.", "Полихр."],
            rows, [45, 48, 48, 48, 48, 48, 45]))

    def _update_distortion_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        data = compute_field_aberrations(sys, wl=wl)
        rows = []
        for d in data:
            if d['distortion'] is not None:
                fy = d['field_y']; dist_pct = d['distortion']
                dist_mm = fy * dist_pct / 100.0 if abs(fy) > 1e-10 else 0.0
                rows.append([f"{fy:.4f}", f"{dist_pct:.5f}", f"{dist_mm:.5f}"])
        self._set_table('distortion', make_table(["Поле Y (мм)", "Дист. %", "Дист. (мм)"], rows, [75, 70, 75]))

    def _update_astigmatism_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        data = compute_field_aberrations(sys, wl=wl)
        rows = []
        for d in data:
            if d['z_m'] is not None:
                dz = d['z_m'] - d['z_s']
                rows.append([f"{d['field_y']:.4f}", f"{d['z_m']:.5f}", f"{d['z_s']:.5f}", f"{dz:.5f}"])
        self._set_table('astigmatism', make_table(["Поле Y (мм)", "Z'm (мм)", "Z's (мм)", "ΔZ (мм)"], rows, [70, 65, 65, 65]))

    def _update_coma_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        data = compute_field_aberrations(sys, wl=wl)
        rows = []
        for d in data:
            if d['coma'] is not None:
                coma_y = d['coma'] * 1000
                rows.append([f"{d['field_y']:.4f}", "0.0000", f"{coma_y:.5f}"])
        self._set_table('coma', make_table(["Поле Y (мм)", "Кома X (мкм)", "Кома Y (мкм)"], rows, [75, 75, 75]))

    def _update_focus_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        curve = compute_focus_curve(sys, wl=wl, num_points=40, defocus_range=2.0, freq_lpmm=50.0, num_rays=25, field_y=0.0)
        if not curve:
            self._set_table('focus', None); return
        best_defocus = max(curve, key=lambda p: p[1])[0]
        rows = []; step = max(1, len(curve) // 15)
        for i in range(0, len(curve), step):
            d, mt = curve[i][0], curve[i][1]
            ms = curve[i][2] if len(curve[i]) > 2 else 0.0
            rows.append([f"{d:+.4f}", f"{mt:.4f}", f"{ms:.4f}"])
        table = make_table(["Δdefocus (мм)", "MTF мер.", "MTF саг."], rows, [80, 70, 70])
        for i, row_data in enumerate(rows):
            if abs(float(row_data[0]) - best_defocus) < 0.001:
                font = QFont("Courier", 9); font.setBold(True)
                for j in range(table.columnCount()):
                    item = table.item(i, j)
                    if item:
                        item.setFont(font)
                break
        self._set_table('focus', table)

    def _update_psf_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        rows = [["λ перв.", f"{wl:.4f} мкм"]]
        try:
            psf_data, dx, dy = compute_psf(sys, wl=wl, num_rays=64)
            if psf_data is not None:
                pix_size = (dx.max() - dx.min()) / len(dx) if len(dx) > 1 else 0
                max_intens = psf_data.max()
                cy, cx = np.unravel_index(np.argmax(psf_data), psf_data.shape)
                center_x = dx[cx] if cx < len(dx) else 0
                center_y = dy[cy] if cy < len(dy) else 0
                row_center = psf_data[cy, :]; col_center = psf_data[:, cx]
                half_max = max_intens / 2
                try:
                    w_mer = (dx.max() - dx.min()) / len(dx) * np.sum(row_center > half_max)
                    w_sag = (dy.max() - dy.min()) / len(dy) * np.sum(col_center > half_max)
                except Exception:
                    w_mer = w_sag = 0
                rows.append(["Разм. пикс.", f"{pix_size:.4f} мкм"])
                rows.append(["Макс. интенс.", f"{max_intens:.5f}"])
                rows.append(["Центр X", f"{center_x:.4f} мкм"])
                rows.append(["Центр Y", f"{center_y:.4f} мкм"])
                rows.append(["Шир. мер.", f"{w_mer:.4f} мкм"])
                rows.append(["Шир. саг.", f"{w_sag:.4f} мкм"])
        except Exception:
            rows.append(["Ошибка", "—"])
        self._set_table('psf', make_table(["Параметр", "Значение"], rows, [100, 120]))

    def _update_lsf_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            lsf_t, ax1 = compute_lsf(sys, wl=wl, num_rays=64, direction='tangential')
            lsf_s, ax2 = compute_lsf(sys, wl=wl, num_rays=64, direction='sagittal')
            rows = []; n = len(ax1); step = max(1, n // 15)
            for i in range(0, n, step):
                rows.append([f"{ax1[i]:.4f}", f"{lsf_t[i]:.5f}", f"{lsf_s[i]:.5f}"])
            self._set_table('lsf', make_table(["Коорд. (мкм)", "Мерид. LSF", "Сагит. LSF"], rows, [75, 75, 75]))
        except Exception:
            self._set_table('lsf', None)

    def _update_enc_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            r_um, enc = compute_enc(sys, wl=wl, num_rays=100)
            rows = []; n = len(r_um); step = max(1, n // 13)
            for i in range(0, n, step):
                rows.append([f"{r_um[i]*2:.4f}", f"{enc[i]*100:.2f}"])
            for pct in [0.5, 0.8, 0.9]:
                idx = np.searchsorted(enc, pct)
                if idx < len(r_um):
                    d = r_um[idx] * 2
                    rows.append([f"D@{int(pct*100)}%={d:.4f}", f"{pct*100:.2f}%"])
            self._set_table('enc', make_table(["D круга (мкм)", "Полихр. %"], rows, [110, 80]))
        except Exception:
            self._set_table('enc', None)

    def _update_ptf_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            ptf = compute_ptf(sys, wl=wl, num_rays=64)
            if ptf is None:
                self._set_table('ptf', None); return
            freqs = ptf['freqs']; ptf_t = ptf['ptf_tangential']; ptf_s = ptf['ptf_sagittal']
            rows = []; n = len(freqs); step = max(1, n // 15)
            for i in range(0, n, step):
                rows.append([f"{freqs[i]:.2f}", f"{ptf_t[i]:.5f}", f"{ptf_s[i]:.5f}"])
            self._set_table('ptf', make_table(["Частота (л/мм)", "PTF мер. (рад)", "PTF саг. (рад)"], rows, [75, 80, 80]))
        except Exception:
            self._set_table('ptf', None)

    def _update_heatmap_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        rows = [["Длина волны", f"{wl:.4f} мкм"],
                ["Сетка", f"{self.heatmap_w.grid_size}×{self.heatmap_w.grid_size}"]]
        if self.heatmap_w.heatmap is not None and self.heatmap_w.heatmap.size > 0:
            x_span = (self.heatmap_w.x_range[1] - self.heatmap_w.x_range[0]) * 1000
            y_span = (self.heatmap_w.y_range[1] - self.heatmap_w.y_range[0]) * 1000
            rows.append(["Размер поля", f"{x_span:.4f}×{y_span:.4f} мкм"])
            rows.append(["Пикселей с данными", str(self.heatmap_w.num_points)])
            rows.append(["Макс. плотность", f"{self.heatmap_w.max_density:.4f}"])
            rows.append(["Центроид X", f"{self.heatmap_w.centroid_x*1000:.4f} мкм"])
            rows.append(["Центроид Y", f"{self.heatmap_w.centroid_y*1000:.4f} мкм"])
        else:
            rows.append(["Статус", "Нет данных"])
        self._set_table('heatmap', make_table(["Параметр", "Значение"], rows, [130, 130]))

    def _update_beam_table(self, sys: OpticalSystem) -> None:
        from optics_engine import compute_beam_geometry
        beam_data = compute_beam_geometry(sys)
        rows = []
        for bd in beam_data:
            rows.append([f"{bd['field_y']:.4f}", f"{bd['Ay']:.4f}", f"{bd['Ay_prime']:.4f}",
                         f"{bd['vignetting_upper']:.4f}", f"{bd['vignetting_lower']:.4f}",
                         f"{bd['relative_illumination']:.4f}"])
        self._set_table('beam', make_table(
            ["Поле", "Ay", "Ay'", "Виньет.↑", "Виньет.↓", "Светораспр."],
            rows, [45, 50, 50, 55, 55, 60]))

    def _update_chief_table(self, sys: OpticalSystem) -> None:
        chief_data = compute_chief_ray_characteristics(sys)
        rows = []
        for cd in chief_data:
            rows.append([f"{cd['field_y']:.4f}", f"{cd['distortion_abs']:.6f}",
                         f"{cd['distortion_rel']:.6f}", f"{cd['Zm']:.6f}",
                         f"{cd['Zs']:.6f}", f"{cd['lateral_color']:.6f}"])
        self._set_table('chief', make_table(
            ["Поле", "Дист.абс", "Дист.%", "Z'm", "Z's", "Хр.увел."],
            rows, [45, 60, 55, 60, 60, 60]))

    def _update_zernike_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys); defocus = self.get_defocus_offset()
        try:
            coeffs = compute_zernike_coefficients(sys, wl=wl, num_rays=32, max_order=4, defocus_offset=defocus)
            chromatic = None
            if len(sys.wavelengths) > 1:
                try:
                    chromatic = compute_zernike_chromatic(sys, num_rays=32, max_order=4)
                except Exception:
                    pass
            if chromatic and self.zernike_w._show_chromatic:
                wl_keys = [k for k in chromatic if not k.startswith('delta_')]
                if wl_keys:
                    headers = ["Полином"] + wl_keys
                    rows = []
                    for idx, (val, name) in enumerate(coeffs):
                        row = [name]
                        for key in wl_keys:
                            if key in chromatic:
                                for c, n in chromatic[key]:
                                    if n == name:
                                        row.append(f"{c:+.6f}"); break
                                else:
                                    row.append("—")
                            else:
                                row.append("—")
                        rows.append(row)
                    for delta_key in ['delta_F-d', 'delta_C-d']:
                        if delta_key in chromatic:
                            for idx, (val, name) in enumerate(chromatic[delta_key]):
                                if idx < len(rows):
                                    rows[idx].append(f"{val:+.6f}")
                    if any(k in chromatic for k in ['delta_F-d', 'delta_C-d']):
                        delta_headers = [k for k in ['delta_F-d', 'delta_C-d'] if k in chromatic]
                        headers.extend(delta_headers)
                    self._set_table('zernike', make_table(headers, rows, [80] + [70] * (len(headers) - 1)))
                    return
            rows = []
            for val, name in coeffs:
                rows.append([name, f"{val:+.6f}"])
            self._set_table('zernike', make_table(["Полином", "Коэфф. (λ)"], rows, [120, 90]))
        except Exception:
            self._set_table('zernike', None)

    def _update_wfmap_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        rows = [["λ перв.", f"{wl:.4f} мкм"]]
        try:
            wf, coords, mask = compute_wavefront_map_2d(sys, wl=wl, grid_size=48, defocus_offset=self.get_defocus_offset())
            if wf is not None and mask is not None:
                valid = wf[mask > 0]; valid = valid[np.isfinite(valid)]
                if valid.size > 0:
                    rows.append(["PV", f"{valid.max()-valid.min():.5f} λ"])
                    rows.append(["RMS", f"{np.sqrt(np.mean(valid**2)):.5f} λ"])
                    rows.append(["Мин", f"{valid.min():.5f} λ"])
                    rows.append(["Макс", f"{valid.max():.5f} λ"])
                    rows.append(["Сетка", f"{wf.shape[0]}×{wf.shape[1]}"])
                else:
                    rows.append(["Статус", "Нет данных"])
            else:
                rows.append(["Статус", "Нет данных"])
        except Exception:
            rows.append(["Ошибка", "—"])
        self._set_table('wfmap', make_table(["Параметр", "Значение"], rows, [100, 120]))

    def _update_esf_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            x_um, esf = compute_esf(sys, wl=wl)
            if x_um is None:
                self._set_table('esf', None); return
            rows = []; n = len(x_um); step = max(1, n // 15)
            for i in range(0, n, step):
                rows.append([f"{x_um[i]:.4f}", f"{esf[i]:.5f}"])
            self._set_table('esf', make_table(["Коорд. (мкм)", "ESF"], rows, [90, 90]))
        except Exception:
            self._set_table('esf', None)

    def _update_focus_diag_table(self, sys: OpticalSystem) -> None:
        if not self.focus_diagrams.spots_by_defocus:
            self._set_table('focus_diag', None); return
        rows = []
        for label in ["номинал", "+DS'", "-DS'", "+2DS'", "-2DS'"]:
            if label not in self.focus_diagrams.spots_by_defocus:
                continue
            spots, rms_info, df = self.focus_diagrams.spots_by_defocus[label]
            rows.append([label, f"{df:+.4f}", str(len(spots)),
                         f"{rms_info['rms_total']:.5f}", f"{rms_info['rms_x']:.5f}", f"{rms_info['rms_y']:.5f}"])
        self._set_table('focus_diag', make_table(
            ["Поз.", "Δz (мм)", "Лучей", "RMS", "RMS_X", "RMS_Y"], rows, [55, 65, 40, 65, 65, 65]))

    def _update_psf3d_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        rows = [["λ перв.", f"{wl:.4f} мкм"]]
        if self.psf_3d_w.Z is not None:
            Z = self.psf_3d_w.Z
            rows.append(["Макс.", f"{Z.max():.5f}"])
            rows.append(["Размер", f"{Z.shape[0]}×{Z.shape[1]}"])
            if self.psf_3d_w.x_coords is not None:
                x_span = self.psf_3d_w.x_coords.max() - self.psf_3d_w.x_coords.min()
                rows.append(["Поле X", f"{x_span:.5f} мкм"])
        else:
            rows.append(["Статус", "Нет данных"])
        self._set_table('psf3d', make_table(["Параметр", "Значение"], rows, [100, 120]))

    def _update_wf_rms_field_table(self, sys: OpticalSystem) -> None:
        data = self.wf_rms_field_w.field_data
        if not data or not data[0]:
            self._set_table('wf_rms_field', make_table(["Поле", "СКВ (λ)"], [["—", "Нет данных"]], [60, 100])); return
        field_vals, rms_full, rms_no_def, rms_no_tilt = data
        rows = []
        for f, r_full, r_def, r_tilt in zip(field_vals, rms_full, rms_no_def, rms_no_tilt):
            rows.append([f"{f:.2f}°", fmt_val(r_full), fmt_val(r_def), fmt_val(r_tilt)])
        self._set_table('wf_rms_field', make_table(["Поле", "СКВ (λ)", "СКВ-деф", "СКВ-тильт"], rows, [55, 75, 75, 75]))

    def _update_bar_target_table(self, sys: OpticalSystem) -> None:
        wl = get_primary_wl(sys)
        try:
            mtf_data = self.bar_target_w.mtf_table
            if not mtf_data:
                mtf_data = compute_bar_target_mtf_table(sys, wl=wl)
            rows = []
            for entry in mtf_data:
                rows.append([f"{entry['freq']}", f"{entry['contrast_ideal']:.4f}",
                             f"{entry['contrast_real']:.4f}", f"{entry['mtf']:.4f}"])
            self._set_table('bar_target', make_table(
                ["Частота (л/мм)", "Контр. идеал", "Контр. реал.", "MTF"], rows, [80, 80, 80, 80]))
        except Exception:
            self._set_table('bar_target', None)
