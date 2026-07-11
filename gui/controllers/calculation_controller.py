"""Calculation pipeline controller for OPAL-OKB.

Encapsulates the two-phase calculation pipeline (fast paraxial/Seidel +
heavy aberration analysis) that was previously inline in ``MainWindow``.

The controller holds a reference to the main window and accesses its
widgets directly, keeping the calculation logic out of the UI class.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

from PyQt5.QtCore import QThread

from optics_engine import (
    OpticalSystem, SurfaceType, paraxial_trace, seidel_aberrations,
)
from optics_utils import get_primary_wl


class CalculationController:
    """Orchestrates the optical calculation pipeline.

    The controller is created once by :class:`MainWindow` and reused
    for every calculation request. It manages Phase 1 (fast sync),
    Phase 2 (heavy async via worker thread), and GUI updates.

    Attributes:
        mw: Reference to the main window providing access to UI widgets.
        _calc_thread: Currently running calculation thread (if any).
        _calc_worker: Worker object inside the thread.
    """

    def __init__(self, main_window) -> None:
        """Initialize the calculation controller.

        Args:
            main_window: The :class:`MainWindow` instance that owns
                the UI widgets accessed during calculation.
        """
        self.mw = main_window
        self._calc_thread: Optional[QThread] = None
        self._calc_worker = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(self) -> None:
        """Gather UI data into ``current_system`` and launch calculation.

        Reads surface table and system parameter widgets, populates the
        :class:`~optics_engine.OpticalSystem`, then starts the two-phase
        calculation pipeline.
        """
        sys = self.mw.current_system

        if not sys.surfaces:
            self.mw.statusBar().showMessage("Нет поверхностей")
            return

        # Update surfaces from table
        n_wl = max(1, len(sys.wavelengths))
        sd_col = 4 + n_wl     # D/2
        k_col = 4 + n_wl + 2  # k
        for i in range(min(self.mw.surface_table.rowCount(), len(sys.surfaces))):
            r_item = self.mw.surface_table.item(i, 1)
            d_item = self.mw.surface_table.item(i, 2)
            g_item = self.mw.surface_table.item(i, 3)
            sd_item = self.mw.surface_table.item(i, sd_col)

            if r_item:
                txt = r_item.text().strip()
                sys.surfaces[i].radius = float(txt) if txt not in ("∞", "inf", "") else 0.0
            if d_item:
                txt = d_item.text().strip()
                sys.surfaces[i].thickness = float(txt) if txt else 0.0
            if g_item:
                glass = g_item.text().strip()
                sys.surfaces[i].glass = glass
                if glass.upper() in ("ЗЕРКАЛО", "MIRROR"):
                    sys.surfaces[i].is_reflective = True
                else:
                    sys.surfaces[i].is_reflective = False
            if sd_item:
                txt = sd_item.text().strip()
                sys.surfaces[i].semi_diameter = float(txt) if txt else 0.0
            k_item = self.mw.surface_table.item(i, k_col)
            if k_item:
                txt = k_item.text().strip()
                try:
                    k_val = float(txt)
                    sys.surfaces[i].conic_constant = k_val
                    if abs(k_val) > 1e-10:
                        sys.surfaces[i].surface_type = SurfaceType.CONIC
                    elif sys.surfaces[i].surface_type == SurfaceType.CONIC:
                        sys.surfaces[i].surface_type = SurfaceType.SPHERE
                except ValueError:
                    pass

        # System-level parameters from UI
        self._collect_system_params(sys)

        # Launch calculation
        self.run_calc(sys)

    def run_calc(self, sys: OpticalSystem, sync: bool = False) -> None:
        """Run the two-phase calculation pipeline.

        Phase 1 runs synchronously (paraxial, Seidel, spot diagram).
        Phase 2 runs asynchronously in a worker thread (fans, MTF, PSF,
        Zernike, etc.) unless ``sync=True``.

        Args:
            sys: The optical system to calculate.
            sync: If ``True``, run Phase 2 synchronously (used by tests).
        """
        # Phase 1: fast synchronous
        phase1_data = self.do_calc_phase1(sys)

        # Immediate GUI update
        self._update_parax_and_seidel(sys, phase1_data)
        self.mw.surface_table.load_system(sys)
        self.mw.viz.set_system(sys, trace_rays=True)

        if sync:
            defocus = self.mw.analysis.get_defocus_offset() if hasattr(self.mw.analysis, 'defocus_spin') else 0.0
            azimuth = self.mw.analysis.get_azimuth() if hasattr(self.mw.analysis, 'azimuth_spin') else 0.0
            phase2_data = self.do_calc_phase2(sys, defocus, azimuth)
            self.update_after_calc(sys, phase1_data, phase2_data)
            return

        # Show intermediate result
        f_text = self.mw.results.parax_table.item(1, 1).text() if self.mw.results.parax_table.rowCount() > 1 else "—"
        self.mw.statusBar().showMessage(f"Расчёт анализа... f'={f_text}")

        # Phase 2: async worker thread
        self.mw.btn_calc.setEnabled(False)
        self.mw.btn_calc.setText("⏳ Анализ...")

        from worker import Worker

        # Cleanup previous thread
        if self._calc_thread is not None and self._calc_thread.isRunning():
            self._calc_thread.quit()
            self._calc_thread.wait(1000)

        defocus = self.mw.analysis.get_defocus_offset() if hasattr(self.mw.analysis, 'defocus_spin') else 0.0
        azimuth = self.mw.analysis.get_azimuth() if hasattr(self.mw.analysis, 'azimuth_spin') else 0.0

        self._calc_thread = QThread()
        self._calc_worker = Worker(self.do_calc_phase2, sys, defocus, azimuth)
        self._calc_worker.moveToThread(self._calc_thread)
        self._calc_thread.started.connect(self._calc_worker.run)
        self._calc_worker.finished.connect(
            lambda r: self.update_after_calc(sys, phase1_data, r)
        )
        self._calc_worker.error.connect(lambda e: self._on_calc_error(e))
        self._calc_worker.finished.connect(self._calc_thread.quit)
        self._calc_thread.start()

    def do_calc_phase1(self, sys: OpticalSystem) -> Dict[str, Any]:
        """Phase 1: Fast synchronous computations (< 0.5 s).

        Computes paraxial trace, Seidel aberrations, and a spot diagram.

        Args:
            sys: The optical system to analyse.

        Returns:
            Dictionary with keys ``'parax'``, ``'seidel'``, ``'spots'``.
        """
        from aberrations import compute_spot_diagram

        wl = get_primary_wl(sys)
        return {
            'parax': paraxial_trace(sys),
            'seidel': seidel_aberrations(sys),
            'spots': compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=0.0),
        }

    def do_calc_phase2(
        self,
        sys: OpticalSystem,
        defocus: float,
        azimuth: float,
    ) -> Dict[str, Any]:
        """Phase 2: Heavy computations run in a worker thread.

        Performs aberration fans, MTF, PSF, Zernike, focus diagrams,
        and other analyses in parallel using a thread pool.

        Args:
            sys: The optical system to analyse.
            defocus: Defocus offset in mm (from analysis panel).
            azimuth: Azimuth angle in degrees (from analysis panel).

        Returns:
            Dictionary of analysis results.
        """
        import os
        import numpy as np
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from optics_engine import paraxial_trace, compute_beam_geometry
        from aberrations import (
            compute_spot_diagram, compute_rms_spot,
            compute_spot_diagram_polychromatic, compute_polychromatic_rms,
            trace_aberration_fan, compute_field_aberrations,
            compute_focus_curve, compute_spot_diagram_at_defocus,
            compute_rms_spot_xy, compute_geometric_mtf,
            compute_chief_ray_characteristics, compute_isoplanatism,
        )
        from diffraction_mtf import (
            compute_diffraction_mtf, compute_diffraction_limited_mtf,
        )
        from advanced_analysis import (
            compute_psf, compute_lsf, compute_esf, compute_enc,
            compute_ptf, compute_bar_target_mtf_table,
            compute_bar_target_image,
        )
        from zernike import (
            compute_zernike_coefficients, compute_zernike_chromatic,
            compute_wavefront_map_2d,
        )

        wl = get_primary_wl(sys)
        wl_list = [w.value for w in sys.wavelengths] if sys.wavelengths else [0.58756]
        n_workers = min(8, max(2, os.cpu_count() or 4))

        results: Dict[str, Any] = {}
        parax = paraxial_trace(sys)

        spots_mono = compute_spot_diagram(sys, wl=wl, num_rays=40, field_y=0.0)
        results['spots_mono'] = spots_mono
        results['rms'] = compute_rms_spot(spots_mono)

        # Polychromatic
        if len(sys.wavelengths) > 1:
            results['spots_poly'] = compute_spot_diagram_polychromatic(sys, num_rays=40, field_y=0.0)
            results['poly_rms'] = compute_polychromatic_rms(sys, num_rays=40, field_y=0.0)
            results['poly_rms_xy'] = compute_rms_spot_xy([(dx, dy) for dx, dy, _ in results['spots_poly']])
            results['poly_max'] = max(
                (math.sqrt(dx**2 + dy**2) for dx, dy, _ in results['spots_poly']),
                default=0,
            )
        else:
            results['spots_poly'] = [(dx, dy, 0) for dx, dy in spots_mono]
            results['poly_rms'] = results['rms']
            results['poly_rms_xy'] = {}
            results['poly_max'] = 0

        # -- Parallel tasks --
        def _task_fan():
            fans = {w: trace_aberration_fan(sys, w, num_rays=30) for w in wl_list}
            iso: Dict[float, Any] = {}
            try:
                for w in wl_list:
                    iso[w] = compute_isoplanatism(sys, wl=w, num_rays=30)
            except Exception:
                pass
            return (fans, iso)

        def _task_field():
            return compute_field_aberrations(sys, wl=wl)

        def _task_geo_mtf():
            return compute_geometric_mtf(spots_mono)

        def _task_diff_mtf():
            return compute_diffraction_mtf(sys, wl=wl)

        def _task_diff_ltd():
            return compute_diffraction_limited_mtf(sys, wl=wl)

        def _task_focus():
            return compute_focus_curve(
                sys, wl=wl, num_points=40,
                defocus_range=2.0, freq_lpmm=50.0, num_rays=25, field_y=0.0,
            )

        def _task_psf():
            try:
                return compute_psf(sys, wl=wl, num_rays=64)
            except Exception:
                return None

        def _task_lsf():
            try:
                t, ax1 = compute_lsf(sys, wl=wl, num_rays=64, direction='tangential')
                s, ax2 = compute_lsf(sys, wl=wl, num_rays=64, direction='sagittal')
                return (t, ax1, s, ax2)
            except Exception:
                return None

        def _task_esf():
            try:
                return compute_esf(sys, wl=wl)
            except Exception:
                return None

        def _task_enc():
            try:
                return compute_enc(sys, wl=wl, num_rays=100)
            except Exception:
                return None

        def _task_ptf():
            try:
                return compute_ptf(sys, wl=wl, num_rays=64)
            except Exception:
                return None

        def _task_beam():
            return compute_beam_geometry(sys)

        def _task_chief():
            return compute_chief_ray_characteristics(sys)

        def _task_zernike():
            try:
                c = compute_zernike_coefficients(sys, wl=wl, num_rays=32, max_order=4, defocus_offset=defocus)
                ch = compute_zernike_chromatic(sys, num_rays=32, max_order=4) if len(sys.wavelengths) > 1 else None
                return (c, ch)
            except Exception:
                return ([], None)

        def _task_wfmap():
            try:
                wf, coords, mask = compute_wavefront_map_2d(sys, wl=wl, grid_size=48, defocus_offset=defocus)
                return (wf, coords, mask)
            except Exception:
                return None

        def _task_bar():
            try:
                x, ideal, blurred = compute_bar_target_image(
                    sys, wl=wl, field_y=0.0, num_bars=5, bar_freq_lp_mm=10,
                )
                mtf = compute_bar_target_mtf_table(sys, wl=wl, field_y=0.0, num_bars=5)
                return {'bar_x': x, 'bar_ideal': ideal, 'bar_blurred': blurred, 'bar_mtf_table': mtf}
            except Exception:
                return None

        task_map = {
            'fan_data': _task_fan, 'field_aberr': _task_field,
            'geo_mtf': _task_geo_mtf, 'diff_mtf': _task_diff_mtf,
            'diff_ltd': _task_diff_ltd, 'focus_curve': _task_focus,
            'psf_data': _task_psf, 'lsf': _task_lsf,
            'esf': _task_esf, 'enc': _task_enc, 'ptf_data': _task_ptf,
            'beam_data': _task_beam, 'chief_data': _task_chief,
            'zernike': _task_zernike, 'wfmap': _task_wfmap,
            'bar_mtf': _task_bar,
        }

        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(fn): key for key, fn in task_map.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    result = future.result()
                    if key == 'lsf' and result:
                        results['lsf_t'], results['lsf_ax1'], results['lsf_s'], results['lsf_ax2'] = result
                    elif key == 'zernike':
                        results['zernike_coeffs'], results['zernike_chromatic'] = result
                    elif key == 'enc' and result:
                        results['enc_r'], results['enc_e'] = result
                    elif key == 'fan_data' and isinstance(result, tuple):
                        fans, iso = result
                        results['fan_data'] = fans
                        results['isoplanatism'] = iso
                    elif key == 'esf' and result:
                        results['esf_x'], results['esf_y'] = result
                    elif key == 'bar_mtf' and isinstance(result, dict):
                        results.update(result)
                    else:
                        results[key] = result
                except Exception:
                    results[key] = None

        # Focus diagrams
        ds = abs(parax.get('longitudinal_spherical', 0)) if parax.get('longitudinal_spherical') else 0.1
        results['focus_diagrams'] = {}
        all_spots = []
        for label, df in [("номинал", 0), ("+DS'", ds), ("-DS'", -ds), ("+2DS'", 2 * ds), ("-2DS'", -2 * ds)]:
            try:
                spots = compute_spot_diagram_at_defocus(
                    sys, wl=wl, num_rays=60, field_y=0.0, defocus_mm=df,
                )
                rms_info = compute_rms_spot_xy(spots)
                results['focus_diagrams'][label] = (spots, rms_info, df)
                all_spots.extend(spots)
            except Exception:
                pass
        results['focus_diag_max'] = (
            max((math.sqrt(dx**2 + dy**2) for dx, dy in all_spots), default=1e-6)
            if all_spots else 1e-6
        )

        return results

    def update_after_calc(
        self,
        sys: OpticalSystem,
        phase1_data: Optional[Dict[str, Any]] = None,
        phase2_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update the GUI after calculation completes.

        Can be called with just ``sys`` (backward-compat path for tests)
        or with full phase data for the async pipeline.

        Args:
            sys: The optical system that was calculated.
            phase1_data: Results from :meth:`do_calc_phase1`, or ``None``.
            phase2_data: Results from :meth:`do_calc_phase2`, or ``None``.
        """
        if sys is None:
            return
        self.mw.current_system = sys
        self.mw.btn_calc.setEnabled(True)
        self.mw.btn_calc.setText("⚙ Рассчитать")

        if phase1_data is None and phase2_data is None:
            # Backward compat: compute fresh
            self._update_parax_and_seidel(sys, None)
            self.mw.surface_table.load_system(sys)
            self.mw.viz.set_system(sys, trace_rays=True)
            if self.mw._viz_mode == '3d':
                self.mw.viz_3d.set_system(sys)
            self.mw.analysis.analyze(sys)
            f_text = self.mw.results.parax_table.item(1, 1).text() if self.mw.results.parax_table.rowCount() > 1 else "—"
            self.mw.statusBar().showMessage(f"Расчёт выполнен: f'={f_text}")
            return

        # Merge phase data
        data: Dict[str, Any] = {}
        if phase1_data:
            data['parax'] = phase1_data['parax']
            data['seidel'] = phase1_data['seidel']
            data['spots_mono'] = phase1_data['spots']
        if phase2_data:
            data.update(phase2_data)

        self._update_parax_and_seidel(sys, data)
        self.mw.surface_table.load_system(sys)
        self.mw.viz.set_system(sys, trace_rays=True)
        if self.mw._viz_mode == '3d':
            self.mw.viz_3d.set_system(sys)
        if data:
            self.mw.analysis.apply_results(sys, data)
        else:
            self.mw.analysis.analyze(sys)
        f_text = self.mw.results.parax_table.item(1, 1).text() if self.mw.results.parax_table.rowCount() > 1 else "—"
        self.mw.statusBar().showMessage(f"Расчёт выполнен: f'={f_text}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_system_params(self, sys: OpticalSystem) -> None:
        """Read system-level parameters from UI widgets into ``sys``.

        This is the shared logic used by both :meth:`calculate` and
        :meth:`SystemController.collect_system_from_ui`.

        Args:
            sys: The optical system to populate.
        """
        from optics_engine import (
            ObjectType, ApertureType, FieldPoint, Wavelength,
        )

        sp = self.mw.sys_params
        sys.stop_surface = int(sp.stop_nd_spin.value())
        sys.stop_offset = sp.stop_sd_spin.value()
        sys.name = sp.name_edit.text()
        sys.object_type = ObjectType.INFINITE if sp.obj_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.image_type = ObjectType.INFINITE if sp.img_type_combo.currentIndex() == 0 else ObjectType.FINITE
        sys.object_height = sp.obj_height_spin.value()

        ap_idx = sp.front_ap_combo.currentIndex()
        ap_val = sp.front_ap_spin.value()
        if ap_idx == 0:  # Y height (D/2)
            sys.aperture_type = ApertureType.ENTRANCE_PUPIL
            sys.aperture_value = ap_val * 2
        elif ap_idx == 1:  # NA
            sys.aperture_type = ApertureType.NUMERICAL_APERTURE
            sys.aperture_value = ap_val
        else:  # F/#
            sys.aperture_type = ApertureType.F_NUMBER
            sys.aperture_value = ap_val

        sys.obscuration_ratio = sp.obscuration_spin.value() / 100.0
        sys.beam_mode = "real" if sp.beam_mode_combo.currentIndex() == 0 else "given"
        sys.sharp_edge = sp.sharp_edge_check.isChecked()

        fp_data = sp.field_points_widget.get_field_points()
        sys.field_points = [FieldPoint(y=y, x=x, weight=w) for y, x, w in fp_data]

        sys.wavelengths = []
        for i in range(sp.wl_table.rowCount()):
            wl_val = float(sp.wl_table.item(i, 0).text())
            wl_w = float(sp.wl_table.item(i, 1).text())
            wl_n = sp.wl_table.item(i, 2).text() if sp.wl_table.item(i, 2) else ""
            sys.wavelengths.append(Wavelength(wl_val, wl_w, wl_n))

    def _update_parax_and_seidel(
        self,
        sys: OpticalSystem,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update paraxial and Seidel tables in results and analysis panels.

        Args:
            sys: The optical system.
            data: Optional pre-computed results dict. If ``None`` or
                missing keys, values are computed on the fly.
        """
        if data and 'parax' in data:
            parax = data['parax']
        else:
            parax = paraxial_trace(sys)

        # ResultsPanel backward compat
        self.mw.results._parax_result = parax
        self.mw.results._current_system_ref = sys

        fno = parax.get('f_number', 0)
        epd = parax.get('entrance_pupil_diameter', 0)
        if fno == 0:
            efl = parax.get('focal_length', 0)
            epd = sys.aperture_value if sys.aperture_value > 0 else efl / 4.0
            fno = efl / epd if epd > 0 else 0
        self.mw.results._fno = fno
        self.mw.results._epd = epd
        self.mw.results._update_parax_display()

        if data and 'seidel' in data:
            seidel = data['seidel']
        else:
            seidel = seidel_aberrations(sys)

        self.mw.analysis.update_parax(parax, fno, epd, sys=sys)
        self.mw.analysis.update_seidel(seidel)
        self.mw.results._update_paraxial_all_wl(sys)

    def _on_calc_error(self, err: str) -> None:
        """Handle calculation errors from the worker thread.

        Args:
            err: Error message string.
        """
        self.mw.btn_calc.setEnabled(True)
        self.mw.btn_calc.setText("⚙ Рассчитать")
        self.mw.statusBar().showMessage(f"Ошибка расчёта: {err[:80]}")
