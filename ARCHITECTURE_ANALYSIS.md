# OPAL-OKB Architecture & Structure Analysis Report

## Overview

| File | Lines | Role |
|------|-------|------|
| `main.py` | 2,078 | Main GUI window, surface table, system params, menu/toolbar |
| `analysis_gui.py` | 4,022 | Analysis panel: 24 plot widgets + 24 table builders + compute orchestrator |
| `optics_engine.py` | 847 | Domain model (OpticalSystem), paraxial trace, Seidel, beam geometry |
| `io_utils.py` | ~240 | JSON save/load, protocol export |
| `library.py` | ~175 | Library scanning (OPJ/LBO files), system factory |
| `worker.py` | 38 | Generic QThread worker wrapper |

Total analyzed: ~7,400 lines across 6 files (plus ~15+ external modules: `aberrations`, `advanced_analysis`, `zernike`, `diffraction_mtf`, `visualization`, `visualization3d`, `system_utils`, `glass_catalog`, `optics_utils`, `achromat`, `opj_reader`, `opj_writer`, `lbo_reader`, `decode_lbo_opj`, `glass_diagram`, `optimizer`).

---

## 1. Module Coupling

### 1.1 Dependency Graph

```
main.py
  ├── optics_engine (domain model + calculations)
  ├── visualization (2D ray tracing view)
  ├── visualization3d (3D view)
  ├── analysis_gui (MASSIVE — entire analysis subsystem)
  ├── system_utils (reverse, scale, standardize)
  ├── io_utils (JSON I/O, protocol export)
  ├── library (OPJ/LBO library)
  ├── achromat (lens design)
  └── optics_utils (helpers)

analysis_gui.py
  ├── optics_engine
  ├── aberrations (ray tracing, spot diagrams, fans)
  ├── advanced_analysis (PSF, LSF, ESF, ENC, PTF, bar target)
  ├── zernike (Zernike coefficients, wavefront maps)
  ├── diffraction_mtf (diffraction MTF)
  └── optics_utils
```

### 1.2 Issues Found

#### **Critical: `analysis_gui.py` is a coupling hub (4,022 lines)**

`analysis_gui.py` directly imports from **6 different modules** (`optics_engine`, `aberrations`, `advanced_analysis`, `zernike`, `diffraction_mtf`, `optics_utils`) and contains **24 widget classes** plus a 700-line `AnalysisPanel` orchestrator. Any change in any of those 6 modules can break `analysis_gui.py`.

**Recommendation:** Split into a `widgets/` package (one file per widget group) and an `analysis_controller.py` for orchestration.

#### **Major: Circular-ish dependency via deferred imports**

`main.py` → `analysis_gui.py` → `main.py`'s classes

While there's no literal circular import, `analysis_gui.py`'s `compute_all_analysis()` function (line ~15) duplicates logic from `MainWindow._do_calc_phase2()` (main.py ~1340). Both code paths call the same set of analysis functions, creating a maintenance burden where changes to analysis logic must be applied in two places.

**Evidence:** `analysis_gui.py` lines 15–140 (`compute_all_analysis`) vs `main.py` lines ~1340–1550 (`_do_calc_phase2`).

#### **Major: `optics_engine.py` pollutes `sys.path`**

```python
# optics_engine.py line 18
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

This is also repeated in `main.py` line 6. Path manipulation should happen once at the entry point.

---

## 2. God Objects / God Classes

### 2.1 **CRITICAL: `MainWindow` (main.py, ~1,070 lines, lines 755–2078)**

The `MainWindow` class handles:
- UI layout and widget creation (`_init_ui`, `_create_menu`, `_create_toolbar`)
- System state management (`current_system`, `_current_file`)
- Surface table CRUD (`_add_surface`, `_del_surface`)
- Full calculation pipeline (`_calculate`, `_run_calc`, `_do_calc_phase1`, `_do_calc_phase2`)
- Result display (`_update_after_calc`, `_update_parax_and_seidel`)
- UI↔model sync (`_collect_system_from_ui` — 80 lines of reading widgets back into the model)
- File I/O (`_open_file`, `_save_file`, `_save_file_as`, `_export_protocol`)
- Library dialog (`_show_library` — 70 lines)
- Achromat designer dialog (`_design_achromat`)
- System transformation (`_reverse_system`, `_scale_system`, `_standardize_radii`)
- 3D/2D view toggling (`_toggle_viz_3d`)
- Glass diagram launch (`_show_glass_diagram`)
- Fitting dialog (`_fit_dialog`)
- Spectral/field points dialogs (`_show_spectral_dialog` — 90 lines, `_show_field_points_dialog`)

**Responsibilities count: ~15+ distinct concerns in one class.**

**Recommendation:** Extract:
- `CalculationController` — `_do_calc_phase1`, `_do_calc_phase2`, `_run_calc`
- `SystemController` — CRUD operations, `_collect_system_from_ui`
- `FileDialogs` — all file open/save/export methods
- `MainMenuBuilder` — `_create_menu` (90+ actions)

### 2.2 **CRITICAL: `AnalysisPanel` (analysis_gui.py, ~1,200 lines, starting ~line 2870)**

This single class:
- Creates and manages **24 plot widgets** as attributes
- Creates and manages **24 corresponding table builders**
- Implements `apply_precomputed()` (~80 lines of setting widget attributes)
- Implements `_build_tables_precomputed()` (~350 lines building QTableWidgets)
- Implements `apply_phase1()`, `apply_phase2()`, `analyze()` (~200 lines each path)
- Has 24+ `_update_*_table()` methods (~600 lines total)
- Manages global settings (defocus, azimuth, chromatic mode)

**Recommendation:** Split into:
- `AnalysisWidgetRegistry` — manages widget lifecycle
- `TableBuilderFactory` — generates tables from data dicts
- `AnalysisOrchestrator` — coordinates phase1/phase2 computation

### 2.3 **MAJOR: `SystemParamsWidget` (main.py, ~300 lines, lines 615–920)**

This widget handles:
- All system parameter UI (object type, aperture, field, wavelengths, beam mode)
- Legacy compatibility widgets (`aperture_type_combo`, `aperture_spin` — hidden, kept for backward compat)
- Wavelength management dialogs (`_add_wavelength`, `_standard_wavelengths`, `_del_wavelength`)
- Unit conversion logic (`_on_type_changed`, `_sync_aperture`, `_update_gmms_label`)
- Field points sub-widget management

### 2.4 **MAJOR: `ResultsPanel` (main.py, ~200 lines, lines 336–550)**

Kept purely for backward compatibility (tests access it). It duplicates paraxial display logic that's also in `AnalysisPanel._update_parax_table()`. Dead code risk.

---

## 3. Separation of Concerns

### 3.1 **CRITICAL: UI logic mixed with business logic in `MainWindow._calculate()` (lines ~1170–1290)**

The `_calculate()` method reads raw table cells (`self.surface_table.item(i, 1).text()`), parses strings to floats, sets OpticalSystem attributes, then triggers computation. This is **presentation-to-domain mapping embedded in the UI class**.

The inverse — `_collect_system_from_ui()` (lines ~1690–1760) — does the same thing again, duplicating ~70 lines of table-parsing logic that's already in `_calculate()`.

**Recommendation:** Extract a `SystemSerializer` that converts between `OpticalSystem` domain objects and UI table state.

### 3.2 **CRITICAL: `analysis_gui.py` mixes computation with presentation**

The `compute_all_analysis()` function (lines 15–140) performs heavy optical calculations (spot diagrams, MTF, PSF, Zernike). This is **business logic in a GUI module**. It's imported and called both from `AnalysisPanel.analyze()` and from `MainWindow._do_calc_phase2()`.

Meanwhile, `MainWindow._do_calc_phase2()` (~lines 1340–1550) implements **the same computation** using `ThreadPoolExecutor`, with slightly different structure and results dict keys. Two implementations of the same logic.

**Recommendation:** Move all computation orchestration to a separate `analysis_pipeline.py` module. GUI should only call `pipeline.run_analysis(sys, defocus, azimuth) -> dict`.

### 3.3 **MAJOR: Domain logic in `io_utils.py`**

`append_system()` (line ~100) implements optical system merging logic (combining surfaces, creating new `OpticalSystem`). This is domain logic, not I/O logic. It belongs in `optics_engine.py` or a `system_operations.py`.

### 3.4 **MAJOR: Presentation in `io_utils.py`**

`export_protocol()` (lines ~120–175) formats optical data into a text protocol with specific column layouts, separators, and Russian labels. This is presentation logic living in an I/O utility.

### 3.5 **MAJOR: Inline UI dialog construction throughout `main.py`**

Methods like `_show_library()` (70 lines), `_show_spectral_dialog()` (90 lines), `_design_achromat()` (50 lines), `_fit_dialog()` (70 lines) build complex QDialogs inline. Each is a mini-application embedded in MainWindow.

---

## 4. Module Organization

### 4.1 Current Structure (Flat)

```
opal_okb/
├── main.py              ← GUI + app entry + half the controller logic
├── analysis_gui.py      ← 24 widgets + orchestrator + computation (4K lines)
├── optics_engine.py     ← Domain model + calculations (OK)
├── io_utils.py          ← JSON I/O + protocol formatting + system merge
├── library.py           ← File scanning + factory (OK, mostly)
├── worker.py            ← Generic QThread wrapper (OK)
├── aberrations.py       ← (not analyzed, external)
├── advanced_analysis.py ← (not analyzed, external)
├── zernike.py           ← (not analyzed, external)
├── diffraction_mtf.py   ← (not analyzed, external)
├── visualization.py     ← (not analyzed, external)
├── visualization3d.py   ← (not analyzed, external)
├── system_utils.py      ← (not analyzed, external)
├── glass_catalog.py     ← (not analyzed, external)
├── optics_utils.py      ← (not analyzed, external)
├── achromat.py          ← (not analyzed, external)
├── opj_reader.py        ← (not analyzed, external)
├── opj_writer.py        ← (not analyzed, external)
├── lbo_reader.py        ← (not analyzed, external)
├── decode_lbo_opj.py    ← (not analyzed, external)
└── glass_diagram.py     ← (not analyzed, external)
```

### 4.2 **CRITICAL: No package structure**

20+ Python files all at the same level. No `__init__.py`, no packages. Every module uses `sys.path.insert(0, ...)` to find siblings.

### 4.3 Recommended Restructure

```
opal_okb/
├── main.py                  ← Entry point only (QApplication + MainWindow)
├── domain/
│   ├── __init__.py
│   ├── models.py            ← OpticalSystem, Surface, Wavelength, etc. (from optics_engine.py)
│   ├── calculations.py      ← paraxial_trace, seidel_aberrations, etc. (from optics_engine.py)
│   └── system_operations.py ← reverse, scale, merge (from system_utils, io_utils)
├── analysis/
│   ├── __init__.py
│   ├── pipeline.py          ← compute_all_analysis, phase1/phase2 orchestration
│   ├── ray_tracing.py       ← (from aberrations.py)
│   ├── advanced.py          ← (from advanced_analysis.py)
│   ├── zernike.py
│   └── diffraction.py       ← (from diffraction_mtf.py)
├── gui/
│   ├── __init__.py
│   ├── main_window.py       ← MainWindow (slimmed down)
│   ├── surface_table.py     ← SurfaceTable widget
│   ├── system_params.py     ← SystemParamsWidget
│   ├── results_panel.py     ← ResultsPanel (or delete if truly dead)
│   ├── dialogs/             ← Library, Achromat, Spectral, Fit dialogs
│   └── widgets/             ← All 24 analysis widgets (split from analysis_gui.py)
│       ├── spot_diagram.py
│       ├── aberration_graphs.py
│       ├── mtf.py
│       ├── psf.py
│       ├── wavefront.py
│       └── ... (one file per 1-2 widget classes)
├── io/
│   ├── json_io.py           ← save/load JSON (from io_utils.py)
│   ├── opj_io.py            ← OPJ read/write
│   ├── lbo_io.py            ← LBO read
│   └── protocol.py          ← export_protocol (from io_utils.py)
├── catalog/
│   ├── glass_catalog.py
│   └── library.py
└── utils/
    ├── worker.py
    └── optics_utils.py
```

---

## 5. Dependency Flow

### 5.1 Calculation Data Flow

```
User clicks "Рассчитать"
    │
    ▼
MainWindow._calculate()
    │ Reads table cells → modifies current_system attributes
    │
    ▼
MainWindow._run_calc(sys)
    │
    ├── Phase 1 (sync): _do_calc_phase1(sys)
    │   ├── paraxial_trace(sys)
    │   ├── seidel_aberrations(sys)
    │   └── compute_spot_diagram(sys)
    │   → Updates: ResultsPanel, AnalysisPanel (parax/seidel tabs), viz widget
    │
    └── Phase 2 (async QThread): _do_calc_phase2(sys, defocus, azimuth)
        ├── ThreadPoolExecutor with 16 parallel tasks
        │   ├── _task_fan → trace_aberration_fan + compute_isoplanatism
        │   ├── _task_field → compute_field_aberrations
        │   ├── _task_geo_mtf → compute_geometric_mtf
        │   ├── _task_diff_mtf → compute_diffraction_mtf
        │   ├── _task_diff_ltd → compute_diffraction_limited_mtf
        │   ├── _task_focus → compute_focus_curve
        │   ├── _task_psf → compute_psf
        │   ├── _task_lsf → compute_lsf
        │   ├── _task_esf → compute_esf
        │   ├── _task_enc → compute_enc
        │   ├── _task_ptf → compute_ptf
        │   ├── _task_beam → compute_beam_geometry
        │   ├── _task_chief → compute_chief_ray_characteristics
        │   ├── _task_zernike → compute_zernike_coefficients
        │   ├── _task_wfmap → compute_wavefront_map_2d
        │   └── _task_bar → compute_bar_target_image
        │
        └── Worker.finished → _update_after_calc(sys, phase1_data, phase2_data)
            → AnalysisPanel.apply_results(sys, data)
                → Sets widget attributes directly (apply_precomputed)
                → OR calls widget.set_data(sys) per widget (apply_phase2)
                → Builds 24 QTableWidgets (_build_tables_precomputed)
```

### 5.2 **MAJOR: Awkward dual-path for results application**

`AnalysisPanel` has **three** code paths for updating widgets:

1. **`apply_precomputed(sys, data)`** — Sets widget attributes directly from dict (used by `compute_all_analysis`)
2. **`apply_phase2(sys, data)`** — Sets attributes from Worker results dict with different key names
3. **`analyze(sys)`** — Calls `widget.set_data(sys)` on each widget (recomputes everything in GUI thread)

The dict keys are **inconsistent** between paths:
- `compute_all_analysis`: `'spot_mono'`, `'spot_rms'`
- `_do_calc_phase2`: `'spots_mono'`, `'rms'`
- `apply_phase2`: reads `'spots_mono'`, `'rms'`

This is a **bug magnet**. Any rename or new field must be kept in sync across 3 locations.

**Recommendation:** Single canonical results schema. One function that converts dict → widgets.

### 5.3 **MAJOR: `compute_all_analysis()` is unused dead code**

The function at `analysis_gui.py:15` duplicates `MainWindow._do_calc_phase2()` but uses a different key naming scheme. `apply_precomputed()` consumes its format, but the main application uses `_do_calc_phase2` instead. This is ~125 lines of dead/duplicate code.

---

## 6. State Management

### 6.1 **MAJOR: `MainWindow.current_system` is mutated in-place**

The `current_system` attribute is a mutable `OpticalSystem` dataclass. It's modified:
- Directly in `_calculate()` (surface attributes set from table)
- In `_collect_system_from_ui()` (another 70 lines of mutation)
- In `_add_surface()` / `_del_surface()` (list mutation)
- In `_reverse_system()`, `_scale_system()`, `_standardize_radii()` (full replacement)
- In `_design_achromat()` (full replacement)
- In `_show_library()` (full replacement)

There's no observer pattern, no dirty flag, no validation. Any code that holds a reference to `current_system` may see stale data.

### 6.2 **MAJOR: Hidden legacy widgets in `SystemParamsWidget`**

```python
# main.py ~lines 820-835
# === Скрытые виджеты для совместимости ===
self.aperture_type_combo = QComboBox()  # legacy compat
self.aperture_type_combo.addItems(["Входной зрачок D (мм)", ...])
self.aperture_spin = QDoubleSpinBox()
...
self.obscuration_spin = QDoubleSpinBox()
self.beam_mode_combo = QComboBox()
self.sharp_edge_check = QCheckBox()
```

These widgets are created, hidden, and kept alive solely for "compatibility". `_calculate()` reads from `front_ap_spin`/`front_ap_combo` but then syncs to `aperture_spin`/`aperture_type_combo`. Code reading the legacy widgets may get stale values if `_sync_aperture()` hasn't been called.

### 6.3 **MINOR: `AnalysisPanel._calculation_done` flag**

Set to `True` at end of `apply_phase2()` but never checked anywhere. Dead state.

### 6.4 **MINOR: `ResultsPanel` kept alive for test compatibility**

```python
# main.py ~line 1038
self.results = ResultsPanel()  # Kept for compat (tests access w.results.parax_table)
```

A ~200-line class exists solely because tests directly access its internal table widget. The production code uses `AnalysisPanel` for paraxial display.

### 6.5 **MINOR: `sys.path.insert` in multiple files**

- `main.py` line 6
- `optics_engine.py` line 18

Both insert the same directory. Redundant and fragile.

---

## Summary: Top 10 Issues by Priority

| # | Severity | Issue | Location | Fix Effort |
|---|----------|-------|----------|------------|
| 1 | 🔴 Critical | `analysis_gui.py` is a 4,022-line monolith with 24 widgets + orchestrator | Whole file | Large (1-2 weeks) |
| 2 | 🔴 Critical | `MainWindow` has ~15 concerns, 1,070 lines | `main.py:755-2078` | Large |
| 3 | 🔴 Critical | Triple code path for analysis results (3 dict key schemes) | `analysis_gui.py:2870+`, `main.py:1340+` | Medium |
| 4 | 🔴 Critical | No package structure — 20+ flat .py files | Project root | Medium |
| 5 | 🟡 Major | UI↔domain mapping embedded in MainWindow (table parsing) | `main.py:1170-1290`, `1690-1760` | Medium |
| 6 | 🟡 Major | `compute_all_analysis()` is dead/duplicate code | `analysis_gui.py:15-140` | Small (delete) |
| 7 | 🟡 Major | `io_utils.append_system()` contains domain logic | `io_utils.py:~100` | Small |
| 8 | 🟡 Major | Legacy hidden widgets create state inconsistency risk | `main.py:820-835` | Small (remove + refactor) |
| 9 | 🟡 Major | `ResultsPanel` exists only for test compatibility | `main.py:336-550` | Small (fix tests, delete) |
| 10 | 🟠 Minor | `sys.path.insert` duplicated, `_calculation_done` dead flag | Multiple | Trivial |

---

## Appendix: Per-File Metrics

### Class Count per File

| File | Classes | Largest Class | Lines |
|------|---------|---------------|-------|
| `main.py` | 5 (`MainWindow`, `SystemParamsWidget`, `ResultsPanel`, `SurfaceTable`, `FieldPointsWidget`) | `MainWindow` (~1,070) | 2,078 |
| `analysis_gui.py` | 25+ (`AnalysisPanel` + 24 widget classes) | `AnalysisPanel` (~1,200) | 4,022 |
| `optics_engine.py` | 5 dataclasses + 0 classes | `OpticalSystem` (dataclass) | 847 |
| `io_utils.py` | 0 (pure functions) | — | ~240 |
| `library.py` | 0 (pure functions) | — | ~175 |
| `worker.py` | 1 (`Worker`) | `Worker` (38) | 38 |
