# Testing, CI/CD & Development Workflow Analysis — OPAL-OKB

**Date:** 2026-07-10  
**Project:** OPAL-OKB (PyQt5 optical CAD, ported from MS-DOS OPAL-PC)  
**Path:** `C:\Users\mikhail\.openclaw\workspace\opal_okb`

---

## Executive Summary

The project has **~150+ test assertions across 17 test files**, covering core optics well but leaving **most modules significantly under-tested or untested**. Tests are **not pytest-compatible** (custom runners), have **hard external dependencies** (LBO files, GUI/DLLs), and would **fail in any CI environment** without major rework. The `scripts/` directory contains **46 one-off debug scripts** that pollute the repo. Documentation is strong on architecture but weak on contribution/development workflow.

---

## 1. Test Coverage Analysis

### 1.1 Module-by-Module Coverage Matrix

| Module | Lines | Has Direct Tests? | Test Files | Coverage Quality |
|--------|-------|-------------------|------------|-----------------|
| `optics_engine.py` | 847 | ✅ Yes | test_all, test_opal, test_opal_v2, test_lazy_calc, qa_v6 | **Good** — paraxial, Seidel, edge cases, 160 surfaces |
| `glass_catalog.py` | 136 | ✅ Yes | test_all, test_opal, test_opal_v2, qa_v6 | **Good** — n(λ), dispersion, fallback, UV/IR |
| `glass_catalog_full.py` | 129 | ✅ Partial | test_bugs, qa_v6 | **Fair** — import + count only, no dispersion validation |
| `ray_tracing.py` | 636 | ✅ Yes | test_ray_tracing, test_all, qa_v6 | **Good** — Snell, TIR, OPL, batch all libraries |
| `aberrations.py` | 1111 | ✅ Partial | test_all, qa_v6, qa_critical, test_lazy_calc | **Fair** — spot/MTF tested, but ~60% of functions untested |
| `diffraction_mtf.py` | 328 | ✅ Minimal | test_mtf (23 lines), qa_v6 | **Poor** — single smoke test, no cutoff/accuracy validation |
| `advanced_analysis.py` | 368 | ✅ Minimal | qa_v6, qa_critical | **Poor** — import + "not None" checks only |
| `zernike.py` | 328 | ❌ No | — (mentioned in qa_critical for PSF_3d) | **None** — zero direct tests |
| `optimizer.py` | 694 | ✅ Partial | test_all, qa_v6, test_lazy_calc | **Fair** — DLS smoke test, fit_focal_length, fit_bfd tested |
| `achromat.py` | 246 | ✅ Minimal | test_achromat (6 lines!), qa_v6 | **Poor** — single `design_achromat(100)` call |
| `analysis_gui.py` | 4022 | ✅ Minimal | test_lazy_calc (phase1/2), qa_critical (tab count) | **Poor** — 4022 lines, only ~5 assertions |
| `visualization.py` | 684 | ✅ Minimal | test_lazy_calc (set_system_fast) | **Poor** — 1 structural test |
| `visualization3d.py` | 501 | ❌ No | — | **None** |
| `main.py` | 2078 | ✅ Partial | test_opal, test_opal_v2, test_lazy_calc, qa_v6 | **Fair** — GUI smoke tests (create, demo, calculate) |
| `opj_reader.py` | 299 | ✅ Yes | test_all, test_opal, test_lbo, test_opj_garbage | **Good** — parse, roundtrip, garbage detection |
| `opj_writer.py` | 93 | ❌ No | — | **None** — writer completely untested |
| `decode_lbo_opj.py` | 361 | ✅ Yes | test_parser, test_ray_tracing | **Good** — batch tests across all libraries |
| `lbo_reader.py` | 246 | ✅ Yes | test_lbo (17 tests) | **Excellent** — record structure, counts, integration |
| `fil_reader_v2.py` | 181 | ✅ Partial | test_all, qa_v6 | **Fair** — parse_gctg tested, edge cases not |
| `library.py` | 155 | ✅ Minimal | test_lbo (1 integration test) | **Poor** |
| `io_utils.py` | 191 | ✅ Minimal | qa_v6 (JSON roundtrip) | **Fair** — basic roundtrip only |
| `system_utils.py` | 241 | ✅ Yes | test_lazy_calc, qa_v6, test_parser | **Good** — reverse, scale, GOST radii, gmms conversion |
| `worker.py` | 31 | ❌ No | — | **None** (trivial module, low risk) |
| `glass_diagram.py` | 167 | ✅ Minimal | qa_v6 (callable check) | **None** — only checks function exists |
| `glass_agf.py` | 196 | ❌ No | — | **None** |
| `optics_utils.py` | 106 | ❌ No | — (tested indirectly) | **None** — shared utils, no direct tests |
| `map_images.py` | 48 | ❌ No | — | **None** |

### 1.2 Summary

- **Well-tested (Good+):** 7 modules — `optics_engine`, `glass_catalog`, `ray_tracing`, `opj_reader`, `decode_lbo_opj`, `lbo_reader`, `system_utils`
- **Partially tested (Fair/Poor):** 10 modules
- **Zero tests:** 7 modules — `zernike.py`, `visualization3d.py`, `opj_writer.py`, `glass_agf.py`, `optics_utils.py`, `map_images.py`, `worker.py`

**Estimated line coverage:** ~35-40% (core engine well-covered, GUI/analysis mostly untested).

---

## 2. Test Quality Assessment

### 2.1 Strengths

- **Golden reference values:** `test_ray_tracing.py` uses precise OPAL-PC paraxial values (f'=109.6976, sF=-95.5619, etc.) — excellent for regression detection.
- **Batch testing:** Tests iterate all 612 systems across 13 LBO libraries, catching edge cases.
- **Edge cases:** Empty systems, 160 surfaces, R=0, unknown glasses, UV/IR wavelengths, TIR detection.
- **Analytical validation:** Lensmaker's equation verified to <0.001% error.

### 2.2 Weaknesses

| Issue | Severity | Details |
|-------|----------|---------|
| **No assertions on numerical accuracy for analysis** | Major | `qa_v6_full.py` checks `result is not None` for PSF/LSF/ENC/PTF — never validates actual values |
| **Placeholder tests** | Major | `test_opal_v2.py` has `return True # Structural` for meridional ray, sagittal ray, field aberrations — these test nothing |
| **Missing edge cases in ray tracing** | Major | No tests for aspheric surfaces (conic + polynomial), OPL accumulation accuracy, OPL sign conventions |
| **Zernike completely untested** | Major | 328 lines of Zernike polynomial code with zero tests — coefficients, normalization, chromatic terms |
| **Diffraction MTF barely tested** | Major | `test_mtf.py` is 23 lines — just prints values, no assertions on cutoff frequency accuracy or MTF curve shape |
| **No property-based testing** | Minor | No hypothesis/parameterized tests for invariant checking (e.g., reverse(reverse(s)) == s) |

---

## 3. Test Organization

### 3.1 Current State

| Aspect | Status | Details |
|--------|--------|---------|
| **Framework** | ❌ None | All tests use custom `passed/failed` counters with `assert` — **not pytest-compatible** |
| **Test discovery** | ❌ Poor | Tests run via `py tests\test_X.py` (manual), not `pytest tests/` |
| **Fixtures** | ❌ None | No pytest fixtures, no setup/teardown. Each test creates its own `MainWindow()`, `OpticalSystem()` |
| **`__init__.py`** | ✅ Present | Empty, but exists |
| **Test naming** | ⚠️ Mixed | `test_*.py` (good), but `qa_*.py` breaks pytest convention |
| **Test classes** | ⚠️ Inconsistent | Some use classes (`TestLazyCalc`, `TestOPJGarbage`), most use functions |
| **Shared state** | ❌ Problematic | `test_all.py` uses module-level mutable `passed/failed` counters — can't run in parallel |
| **Stdout replacement** | ❌ Critical | Multiple tests replace `sys.stdout` at module level — corrupts pytest capture |

### 3.2 Test Runner Compatibility

```python
# Current pattern (EVERY test file):
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    ...

if __name__ == '__main__':
    test_this()
    test_that()
    print(f"Results: {passed} passed, {failed} failed")
```

**This pattern is fundamentally incompatible with pytest.** Running `pytest tests/` would:
1. Import each module (triggering `sys.stdout` replacement)
2. Find 0 test functions (they're not prefixed correctly or are in `__main__` blocks)
3. Not collect any of the custom `check()` assertions

---

## 4. Dead/Skipped Tests

| File | Issue | Severity |
|------|-------|----------|
| `test_opal_v2.py` | 3 tests return `True # Structural` — effectively skipped | Major |
| `test_opal_v2.py` | `test_mirror_focus` — `return True # Placeholder` | Major |
| `test_mtf.py` | Not a test at all — just prints MTF values, no assertions | Major |
| `test_opt_bug.py` | 13 lines — debug script, not a test | Minor |
| `test_achromat.py` | 6 lines — prints report, no assertions | Major |
| `test_gui.py` | 16 lines — debug script masquerading as test | Minor |
| `test_bugs.py` | 13 lines — verifies 3 imports, trivially passes | Minor |
| `qa_v5_check.py` | References non-existent API (`calculate_seidel_sums`, `cardinal_points`, `OPJReader`, `IOUtils`, `AchromatDesigner`) — permanently failing | **Critical** |

**`qa_v5_check.py`** is completely broken — it tests against an API that was never implemented (or was renamed). It imports `from optics_engine import calculate_seidel_sums, cardinal_points` which don't exist. This file is dead code.

---

## 5. Script Pollution

### 5.1 Analysis

The `scripts/` directory contains **46 Python files** totaling ~3,500 lines. These are one-off debug/reverse-engineering scripts from the development process:

**Categories:**
- **Hex dump / binary analysis:** `hex_dump.py`, `hex4.py`, `hex_analysis.py`, `hex_analysis2.py`, `hex_analysis3.py`, `hex_deep.py`, `hex_demo.py` (7 files)
- **LBO/OPJ reverse engineering:** `analyze_lbo.py`, `analyze_opj.py`, `analyze2.py`, `analyze2_opj.py`, `compare_opj.py`, `parse_opj.py`, `diag.py` (7 files)
- **Glass catalog debugging:** `analyze_gcon.py`, `analyze_gcon2.py`, `analyze_gcon3.py`, `analyze_gcon4.py`, `debug_glass.py`, `debug_glass2.py`, `match_glasses.py`, `match_by_nd.py`, `match_final.py`, `map_glasses.py`, `generate_gost.py`, `verify_gost.py` (12 files)
- **FIL file parsing:** `analyze_gctg.py`, `debug_gctg.py`, `debug_gctg2.py`, `extract_gctg.py`, `debug_fil_headers.py`, `fil_reader.py` (6 files)
- **GCNG parsing:** `parse_gcng.py`, `parse_gcng2.py`, `debug_gcng.py`, `debug_gcng2.py`, `debug_gdat.py` (5 files)
- **Other:** `convert_docs.py`, `fetch_all_labs.py`, `fetch_itmo.py`, `deep_analysis.py`, `find_values.py`, `analyze_gfiles.py`, `debug_catalog.py`, `debug_cat2.py`, `debug_names.py` (9 files)

### 5.2 Root-Level Pollution

Additionally, 3 debug files exist at the **project root**:
- `_dump_exports.py` (37 lines)
- `_try_api.py` (93 lines)
- `_try_converter.py` (56 lines)

### 5.3 Recommendation

**Severity: Major** (repo hygiene, confusing for contributors)

1. Move all 46 scripts + 3 root debug files to `scripts/legacy/` or delete them
2. Keep only `scripts/convert_docs.py` if still needed for documentation regeneration
3. Add `scripts/legacy/` to `.gitignore` or document as archived

---

## 6. CI/CD Readiness

### 6.1 Current State: ❌ NOT CI-READY

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| pytest-compatible tests | ❌ | Custom runners, stdout replacement, `__main__` blocks |
| No hardcoded paths | ❌ | `test_opal.py` has `r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'` hardcoded |
| No GUI dependency for unit tests | ❌ | `test_lazy_calc.py`, `test_opal.py` require PyQt5 + display server |
| No external file dependencies | ❌ | All parser tests require `extracted/opal_okb/Lib/*.LBO` (binary files not in .gitignore but large) |
| Deterministic results | ✅ | Optical calculations are deterministic |
| Fast execution | ✅ | Tests complete in seconds |
| Isolated test environment | ❌ | Tests mutate `sys.stdout`, share global state |
| conftest.py / fixtures | ❌ | None exists |
| requirements-test.txt | ❌ | None exists |
| GitHub Actions / CI config | ❌ | None exists |

### 6.2 Blocking Issues for CI

1. **stdout corruption** (Critical): Multiple modules replace `sys.stdout` at import time:
   - `opj_reader.py` line 8: `sys.stdout = io.TextIOWrapper(...)`
   - `fil_reader_v2.py` line 5: same
   - Every test file does the same
   - **Fix:** Remove all `sys.stdout` replacements from source modules. Use `encoding='utf-8'` in print statements instead.

2. **Hardcoded Windows paths** (Critical): Multiple test files contain absolute paths like `C:\Users\mikhail\...`

3. **PyQt5 display requirement** (Major): GUI tests need `QT_QPA_PLATFORM=offscreen` — only `test_lazy_calc.py` sets this.

4. **Binary file dependencies** (Major): Tests require `extracted/opal_okb/Lib/*.LBO` files. These are binary blobs excluded from `.gitignore` via `extracted/` — but tests depend on them.

5. **No pytest collection** (Major): Running `pytest tests/` would collect 0 tests due to the custom runner pattern.

### 6.3 CI/CD Roadmap

**Phase 1 (to make tests collectible):**
- Convert all test files to pytest format (remove `if __name__ == '__main__'` runners, use `assert` directly)
- Remove `sys.stdout` replacements
- Replace hardcoded paths with `os.path.join(BASE_DIR, ...)`
- Add `conftest.py` with fixtures for `OpticalSystem`, `MainWindow`

**Phase 2 (to make tests pass in CI):**
- Mark GUI tests with `@pytest.mark.gui` and `pytest.importorskip('PyQt5')`
- Create test fixtures that generate synthetic LBO data (don't depend on external files)
- Add `requirements-test.txt`
- Add `.github/workflows/test.yml` (or equivalent)

**Phase 3 (coverage):**
- Add `pytest-cov`, set minimum coverage threshold
- Parameterize tests for multiple glass types, wavelengths, field angles
- Add property-based tests with `hypothesis`

---

## 7. Documentation Quality

### 7.1 Documentation Inventory

| Document | Quality | Notes |
|----------|---------|-------|
| `README.md` | **Good** | Comprehensive feature list, installation, structure table. Test section understates actual count. |
| `docs/ARCHITECTURE.md` | **Excellent** | ASCII diagrams, data flow, class model, formulas, dependencies. Best document in the project. |
| `docs/LBO_FORMAT.md` | Not checked (referenced) | Binary format specification |
| `docs/MANUAL.txt` | Present | Original OPAL-PC manual, converted |
| `docs/USER_GUIDE.md` | Present | Not reviewed in detail |
| `REFACTORING.md` | **Good** | Clear tracking of duplicate code consolidation. Status: Complete. |
| `GAP_ANALYSIS.md` | **Good** | Thorough feature gap analysis vs OPAL-PC (20 items prioritized) |
| `GAP_ANALYSIS_V2.md` | **Good** | Screenshot-based gap analysis (83 images mapped to features) |
| `docs/itmo_labs/` | Present | ITMO lab work materials |

### 7.2 Issues

| Issue | Severity | Details |
|-------|----------|---------|
| **No CONTRIBUTING.md** | Major | No guide for contributors on testing standards, code style, PR process |
| **No CHANGELOG** | Major | No version history or release notes |
| **ARCHITECTURE.md is outdated** | Minor | Says "13 вкладок графиков" but README says 23 tabs. Diagram doesn't show `optics_utils.py`, `zernike.py`, `worker.py` |
| **README test count is stale** | Minor | Claims "44/44 parser tests" but actual count differs. No mention of `qa_*` files. |
| **No inline docstrings in many modules** | Minor | `zernike.py`, `advanced_analysis.py`, `diffraction_mtf.py` have minimal function-level docstrings |

---

## 8. Git Workflow

### 8.1 Observations

- **Git is not installed** in the current environment, so commit history analysis was limited.
- **`.git` directory exists** — repo is version controlled.
- **`.gitignore`** is present and reasonably configured (excludes `__pycache__`, `*.pyc`, `extracted/`, binary files, screenshots).
- **No branches visible** (single branch work, no feature branches detected from file structure).
- **No tags/releases** evident.
- **No PR template** or `.github/` directory.

### 8.2 Assessment

| Aspect | Status | Severity |
|--------|--------|----------|
| Version control | ✅ In use | — |
| `.gitignore` quality | ✅ Good | Covers binaries, caches, extracted data |
| Branching strategy | ❌ Unknown | No evidence of feature branches |
| Release process | ❌ None | No tags, no CHANGELOG, no version numbers |
| PR/Review workflow | ❌ None | No CONTRIBUTING.md, no PR template |
| Commit conventions | ❌ Unknown | Can't verify without git log |

### 8.3 Recommendation

Adopt a simple workflow:
1. Use `main` for stable code
2. Feature branches for new work (`feature/achromat-v2`, `fix/mirror-trace`)
3. Tag releases (`v0.1`, `v0.2`)
4. Add `CHANGELOG.md`
5. Squash debug commits

---

## 9. Prioritized Action Items

### Critical (blocks CI/CD and professional development)

1. **Remove `sys.stdout` replacement from source modules** (`opj_reader.py:8`, `fil_reader_v2.py:5`)
2. **Delete `qa_v5_check.py`** — permanently broken, tests non-existent API
3. **Convert test files to pytest format** — remove custom runners, use `assert` + fixtures
4. **Remove hardcoded paths** — use `pathlib.Path(__file__).parent.parent` everywhere

### Major (significant quality improvement)

5. **Write tests for `zernike.py`** (328 lines, zero tests)
6. **Write tests for `opj_writer.py`** (93 lines, zero tests — writer can corrupt files!)
7. **Add real assertions to `test_mtf.py`, `test_achromat.py`, `test_opt_bug.py`** — currently just print
8. **Clean up `scripts/` directory** — move 46 scripts to `scripts/legacy/` or delete
9. **Remove placeholder tests** in `test_opal_v2.py` (`return True # Structural`)
10. **Add `conftest.py`** with shared fixtures (OpticalSystem, MainWindow, LBO path)
11. **Create `CONTRIBUTING.md`** with testing standards
12. **Add numerical accuracy tests for diffraction MTF** (cutoff frequency vs theoretical)

### Minor (polish)

13. **Update README test counts** to reflect actual numbers
14. **Update ARCHITECTURE.md** — add missing modules, fix "13 tabs" → "23 tabs"
15. **Add `CHANGELOG.md`**
16. **Move `_dump_exports.py`, `_try_api.py`, `_try_converter.py`** from root to scripts/ or delete
17. **Add `requirements-test.txt`** (pytest, pytest-qt, pytest-cov)
18. **Add `pytest.ini` or `[tool.pytest.ini_options]` in pyproject.toml**

---

## 10. Test File Summary Table

| File | Lines | Type | Quality | pytest-ready? |
|------|-------|------|---------|---------------|
| `test_parser.py` | 200 | Custom runner | Good | ❌ |
| `test_ray_tracing.py` | 325 | Custom runner with asserts | Good | ⚠️ (partial) |
| `test_all.py` | 889 | Custom runner | Good (breadth) | ❌ |
| `test_opal.py` | 639 | Custom runner | Fair (some placeholders) | ❌ |
| `test_opal_v2.py` | 538 | Custom runner | Fair (3 placeholders) | ❌ |
| `test_lazy_calc.py` | 215 | Class-based + asserts | Good | ⚠️ (partial) |
| `test_lbo.py` | 249 | Custom `run_all()` | Excellent | ❌ |
| `test_opj_garbage.py` | 60 | Class-based + asserts | Good | ⚠️ (partial) |
| `test_mtf.py` | 23 | Print-only (no asserts) | **Dead** | ❌ |
| `test_achromat.py` | 6 | Print-only (no asserts) | **Dead** | ❌ |
| `test_opt_bug.py` | 13 | Print-only (no asserts) | **Dead** | ❌ |
| `test_gui.py` | 16 | Print-only (no asserts) | **Dead** | ❌ |
| `test_bugs.py` | 13 | Print-only (trivial) | **Dead** | ❌ |
| `qa_critical.py` | 101 | Custom runner | Good | ❌ |
| `qa_v5_check.py` | 272 | Custom runner | **Broken** (dead) | ❌ |
| `qa_v6_full.py` | 474 | Custom `check()` | Fair (smoke tests) | ❌ |
| `test_results.txt` | — | Output artifact | Should not be in repo | N/A |

**Total test code:** ~4,200 lines across 17 files (excluding `test_results.txt`)  
**Effective test code:** ~2,500 lines (excluding dead/broken files)  
**Tests that would be collected by pytest today:** ~0
