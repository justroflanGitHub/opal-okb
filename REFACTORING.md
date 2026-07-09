# Refactoring Plan — Duplicate Functions Analysis

## Status: ✅ COMPLETE

All identical duplicates moved to `optics_utils.py`. 
Differing variants kept separate (documented below).

---

## Summary

| # | Pattern | Count | Action | Status |
|---|---|---|---|---|
| 1 | `z_pos = [0.0]` loop | 12 | → `compute_z_positions()` | ✅ DONE |
| 2 | `wl default 0.58756` | 49 | → `get_primary_wl()` | ✅ DONE |
| 3 | `aperture default` | 27 | → `get_effective_aperture(default=X)` | ✅ DONE |
| 4 | `_sag()` method | 2 | KEPT SEPARATE (differs) | 📌 DOCUMENTED |
| 5 | `_wl_color()` method | 2 | KEPT SEPARATE (differs) | 📌 DOCUMENTED |
| 6 | `_wl_names` dict | 2 | → `wl_name()` | ✅ DONE |
| 7 | `_copy_parax/seidel_table` | 2 | → `copy_table_selection()` | ✅ DONE |
| 8 | `_fmt(v)` inline | 2 | → `fmt_val()` | ✅ DONE |
| 9 | `compute_refractive_index` | 2 | KEPT SEPARATE (different modules) | 📌 DOCUMENTED |

---

## Details: What Was Moved

### 1. `compute_z_positions(system)` ✅
**Before (12 copies):**
```python
z_pos = [0.0]
for s in system.surfaces:
    z_pos.append(z_pos[-1] + s.thickness)
```
**After:** `z_pos = compute_z_positions(system)`

**Files modified:** aberrations.py (×6), diffraction_mtf.py, optics_engine.py (×2), visualization.py, visualization3d.py, zernike.py

### 2. `get_primary_wl(system)` ✅
**Before (49 copies):** `sys.wavelengths[0].value if sys.wavelengths else 0.58756`
**After:** `get_primary_wl(sys)`

**Files modified:** aberrations.py, analysis_gui.py (×38), diffraction_mtf.py, main.py (×3), optics_engine.py (×4), visualization.py, zernike.py

### 3. `get_effective_aperture(system, default=X)` ✅
**Before (27 copies):** `sys.aperture_value if sys.aperture_value > 0 else X`
**After:** `get_effective_aperture(sys, default=X)` — preserves original fallback per file:
- `default=10.0`: aberrations.py, advanced_analysis.py, diffraction_mtf.py, zernike.py
- `default=20.0`: visualization.py, visualization3d.py, ray_tracing.py
- **NOT replaced** (unique efl/4.0 fallback): optics_engine.py:376, analysis_gui.py:3710/3905, main.py:468/1679

### 4. `_sag()` — KEPT SEPARATE ⚠️
**visualization.py:** `if abs(y) > abs(R): return 0.0` (hard cutoff)
**visualization3d.py:** `if abs(r) > abs(R): r = abs(R) * 0.999` (clamp for smooth 3D rendering)

These are **intentionally different**. Do NOT unify.

### 5. `_wl_color()` — KEPT SEPARATE ⚠️
**visualization.py:** Range-based lookup `(lo, hi)` → QColor
**visualization3d.py:** Nearest-match lookup `wl → (r,g,b)`

Different data structures, different lookup logic.

### 6. `wl_name(wl)` ✅
**Before (2 copies):** `_wl_names = {0.54607: 'e', ...}` + manual lookup loop
**After:** `from optics_utils import wl_name`

**Files modified:** decode_lbo_opj.py, opj_reader.py

### 7. `copy_table_selection(table)` ✅
**Before (2 copies in main.py + 1 in analysis_gui.py):** Inline methods with identical logic
**After:** `copy_table_selection(self.parax_table)` / `copy_table_selection(self.seidel_table)`

### 8. `fmt_val(v)` ✅
**Before (2 copies):** `def _fmt(v): return f"{v:.5f}" if v == v else "—"`
**After:** `from optics_utils import fmt_val`

### 9. `compute_refractive_index()` — KEPT SEPARATE ⚠️
- `glass_catalog.py` — basic lookup
- `glass_catalog_full.py` — extended lookup with more glass data

Different implementations, different data sources.

---

## Verification

- ✅ All 17 modules import successfully
- ✅ 53/53 parser tests pass
- ✅ 12/12 ray tracing tests pass
- ✅ Russian text intact in all files
- ✅ Manually verified each function produces identical results
