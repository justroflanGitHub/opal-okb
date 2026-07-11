# OPAL-OKB Domain Logic & Algorithm Correctness Analysis

**Focus:** Optical engineering physics/math correctness  
**Date:** 2026-07-10  
**Files analyzed:** `optics_engine.py`, `ray_tracing.py`, `aberrations.py`, `diffraction_mtf.py`, `zernike.py`, `advanced_analysis.py`, `glass_catalog.py`, `glass_agf.py`, `optics_utils.py`

---

## Executive Summary

The codebase implements a competent paraxial + real ray tracer with Seidel aberrations, wavefront analysis, and diffraction MTF. However, the analysis reveals **1 Critical bug** (aspheric derivative), **6 Major issues** (coordinate inconsistency, Seidel invariant, OPL/reference sphere, ray launching, vignetting approximation, missing surface types), and **8 Minor issues**.

For purely spherical systems with on-axis or small fields, results will be reasonable. For aspheric lenses or wide-field analysis, significant errors are expected.

---

## 1. Coordinate System Consistency

### ISSUE 1.1 — Field direction axis inconsistency (MAJOR)

**Severity:** Major  
**Files:** `aberrations.py`, `ray_tracing.py`, `diffraction_mtf.py`, `zernike.py`, `advanced_analysis.py`

Two incompatible conventions coexist for the field direction:

| Convention | Used in | Field tilt |
|---|---|---|
| **Field in Y** (l=sin θ) | `trace_fan()`, `trace_grid_3d()`, `compute_field_aberrations()`, `compute_oblique_fan()` | `l = sin(angle)` |
| **Field in X** (k=sin θ) | `trace_aberration_fan()`, `compute_spot_diagram()`, `compute_chief_ray_characteristics()`, `compute_focus_curve()`, `compute_spot_diagram_at_defocus()`, `compute_wavefront_map()`, `compute_zernike_coefficients()`, `compute_psf()` | `k = sin(angle)` |

**Example — `aberrations.py:trace_aberration_fan()` (line ~48):**
```python
ray = Ray(x=0, y=y_start, z=-50, k=math.sin(angle), l=0, m=math.cos(angle))
```
Pupil coordinate is Y (`y_start`), but field tilt is X (`k`). The ray is offset in Y but tilted in X — for a meridional fan, both should be in the same plane.

**Example — `aberrations.py:compute_field_aberrations()` (line ~230):**
```python
ray = Ray(x=0, y=y_start, z=z_start, k=0, l=sin_a, m=cos_a)  # ✓ correct
```

**Impact:** For rotationally symmetric systems, this merely swaps tangential/sagittal labels (errors cancel). For non-symmetric systems or when comparing results across functions (e.g., Zernike coma from `zernike.py` vs. field coma from `aberrations.py`), tangential and sagittal quantities are **swapped**. All wavefront maps, PSFs, and MTFs for off-axis fields use the wrong orientation.

**Recommendation:** Standardize on field-in-Y (l-direction) everywhere. Fix all `k=sin(angle)` to `l=sin(angle)` and adjust the meaning of `l=0` to `k=0` in approximately 12 functions across 4 files.

---

### ISSUE 1.2 — Meridional/sagittal label swap in compute_chief_ray_characteristics() (MAJOR)

**Severity:** Major  
**File:** `aberrations.py`, function `compute_chief_ray_characteristics()`, lines ~390-460

This function uses the X-Z plane as meridional (field in X: `k=sin_a`), while `compute_field_aberrations()` uses Y-Z (field in Y: `l=sin_a`). The labels `Zm` and `Zs` are swapped between the two functions:

```python
# compute_chief_ray_characteristics():
# Meridional fan uses x_start with k=sin_a  → X-Z is "meridional"
# Sagittal fan uses y_start                → Y-Z is "sagittal"

# compute_field_aberrations():
# Meridional fan uses y_start with l=sin_a  → Y-Z is "meridional"  
# Sagittal fan uses x_start                → X-Z is "sagittal"
```

**Impact:** Astigmatism values (Zm, Zs) from these two functions cannot be directly compared — they refer to different planes.

---

## 2. Paraxial vs Real Ray Tracing

### ISSUE 2.1 — Seidel sums use wrong invariant (MAJOR)

**Severity:** Major  
**File:** `optics_engine.py`, function `seidel_aberrations()`, lines ~370-410

The code uses `A = nu[i+1] - nu[i]` as the Seidel surface invariant. This equals `-h·Δn/R` (the change in reduced angle). The correct Seidel refraction invariant is:

```
A_correct = n·(u + h/R) = nu + n·h/R
```

which is conserved across refraction (A_before = A_after). The code's `A` is proportional to the surface power times height, not the angle of incidence.

**Numerical example** (surface R=50mm, n=1→1.5, ray height h=1, u=0):
- Code's A = -1×(1.5−1)/50 = **−0.01**
- Correct A = 1×(0 + 1/50) = **0.02**
- Ratio: code gives SI contribution 4× too small for this surface

The ratio differs between surfaces with different glasses, so **relative aberration contributions between surfaces are also wrong**.

**Recommendation:** Replace the invariant computation:
```python
# Replace:
A = nu[i + 1] - nu[i]
A_bar = nub[i + 1] - nub[i]

# With:
A = n_vals[i] * (nu[i]/n_vals[i] + y[i]/R)  # = nu[i] + n_vals[i]*y[i]/R
A_bar = nub[i] + n_vals[i] * yb[i] / R
```

---

### ISSUE 2.2 — Paraxial transfer notation ambiguity (MINOR)

**Severity:** Minor  
**File:** `optics_engine.py`, `paraxial_trace()`

The code uses `nu` as the reduced angle `n·u`, and transfers as:
```python
y[i + 1] = y[i] + nu1[i] * d / n_cur
```

This is correct for the reduced-angle formulation `y' = y + (nu)·d/n`. However, the refraction equation writes:
```python
nu1[i] = nu1[i] - y1[i] * phi_i
```

where `phi_i = (n_a - n_b) / R`. This is `nu' = nu - y·φ`, which is the standard paraxial refraction for reduced angles. This is **correct**. Noted for documentation clarity.

---

### ISSUE 2.3 — No cross-validation between paraxial and real ray EFL (MINOR)

**Severity:** Minor  
**File:** global

There is no automated check that the paraxial effective focal length matches the real ray trace (marginal ray crossing point). A simple sanity check — trace a marginal ray at small height and verify it crosses the axis at the paraxial focus — would catch bugs in either engine.

---

## 3. Edge Cases in Physics

### ISSUE 3.1 — Aspheric polynomial derivative is wrong (CRITICAL)

**Severity:** Critical  
**File:** `ray_tracing.py`, functions `intersect_aspheric()` (line ~75) and `surface_normal_aspheric()` (line ~165)

The derivative of the polynomial sag terms is computed incorrectly:

```python
# Current code (WRONG):
for j, coeff in enumerate(aspheric_coeffs):
    power = 2 * (j + 2) - 1  # gives 3, 5, 7, 9
    dz_dr += coeff * power * (r ** (power - 1))  # gives A4*3*r², A6*5*r⁴, ...
```

The sag polynomial terms are `A₄·r⁴ + A₆·r⁶ + A₈·r⁸ + ...`  
Their derivative w.r.t. r should be `4·A₄·r³ + 6·A₆·r⁵ + 8·A₈·r⁷ + ...`

The code computes:
- j=0 (A₄ term): `3·A₄·r²` instead of `4·A₄·r³`
- j=1 (A₆ term): `5·A₆·r⁴` instead of `6·A₆·r⁵`

Both the **coefficient** AND the **power of r** are wrong.

**Impact:** Every aspheric surface produces incorrect surface normals → incorrect refraction directions → all downstream ray trace results (spot diagrams, aberrations, MTF, Zernike) are wrong for any system containing aspheric surfaces with non-zero polynomial coefficients. Purely spherical and conic surfaces are unaffected.

**Fix:**
```python
for j, coeff in enumerate(aspheric_coeffs):
    exp = 2 * (j + 2)       # 4, 6, 8, 10
    dz_dr += coeff * exp * (r ** (exp - 1))  # 4*A4*r³, 6*A6*r⁵, ...
```

---

### ISSUE 3.2 — NA to diameter conversion uses paraxial approximation (MINOR)

**Severity:** Minor  
**File:** `optics_engine.py`, `paraxial_trace()`, line ~195

```python
results['entrance_pupil_diameter'] = 2.0 * abs(efl) * epd  # D = 2*f'*NA
```

The linear relation `D = 2f'·NA` is only valid for small NA. For NA > 0.3 (microscope objectives), the exact formula should be:
```python
D = 2 * abs(efl) * math.tan(math.asin(epd))  # epd = NA (in air)
```

For NA = 0.5: linear gives D = f', exact gives D = 1.155f' — a 15% error.

---

### ISSUE 3.3 — Mirror sign convention in OPL (MINOR)

**Severity:** Minor  
**File:** `ray_tracing.py`, `trace_ray_through_system()`

After reflection, `current_n = n1` (unchanged). For mirrors in air, this is correct (n=1.0 both sides). For mirrors embedded in glass, the OPL should use `n` for the forward path and `n` for the reflected path (same medium). The code does this correctly for simple cases.

However, for a system like: lens → mirror → lens → image, the refractive index after the mirror should remain as the glass index (not flip sign). The real ray tracer handles this correctly via `current_n = n1`. The paraxial tracer flips sign (`n_medium.append(-n_medium[-1])`), which is the standard convention for paraxial matrices but creates a discrepancy if both engines' results are compared directly.

---

### ISSUE 3.4 — HOLOGRAM, GRATING, TOROIDAL surfaces defined but not implemented (MAJOR)

**Severity:** Major  
**File:** `ray_tracing.py`, `optics_engine.py`

`SurfaceType` enum defines HOLOGRAM (3), GRATING (4), TOROIDAL (5), but `trace_ray_through_system()` only handles SPHERE and ASPHERIC (conic + polynomial). If a system file specifies a hologram or grating surface, it will be traced as if spherical, silently producing wrong results.

**Recommendation:** Add explicit dispatch and warning for unsupported surface types, or implement basic diffraction grating and hologram ray tracing.

---

## 4. Numerical Stability

### ISSUE 4.1 — `_find_focal_z()` extrapolation is loosely bounded (MINOR)

**Severity:** Minor  
**File:** `aberrations.py`, `_find_focal_z()`, line ~195

The sanity check accepts any z within `3×|efl|` of the nominal image plane:
```python
if abs(z_int - img_z) < abs(efl) * 3:  # sanity
```

For a 100mm lens, this accepts z anywhere within ±300mm. Combined with the weighting scheme `w = max(0.1, 1.0 - |pupil₁+pupil₂|/2)`, outlier intersections can significantly shift the weighted average.

**Recommendation:** Use median instead of weighted mean, or tighten the bound to `0.5×|efl|`.

---

### ISSUE 4.2 — Herzberger formula has unguarded pole at λ₀ = 0.167 μm (MINOR)

**Severity:** Minor  
**File:** `glass_catalog.py`, `compute_refractive_index()`

```python
denom = lam**2 - lam0**2
if abs(denom) < 1e-12:
    denom = 1e-12
```

The clamping prevents division by zero but produces a huge index spike. No wavelength range validation is performed — wavelengths near 0.167 μm or outside [lam_min, lam_max] silently extrapolate.

**Recommendation:** Add range check and warning for wavelengths outside [0.3, 2.5] μm.

---

### ISSUE 4.3 — Dead code in aspheric intersection (MINOR)

**Severity:** Minor  
**File:** `ray_tracing.py`, `intersect_aspheric()`, lines ~64-67

```python
dz_dr = c * r / (sqrt_disc * (1.0 + sqrt_disc) / (c * r ...))  # immediately overwritten
# Более аккуратно:
dz_dr = c * r / sqrt_disc
```

The first computation is dead code. Not a correctness bug but confusing and suggests the derivative formula was uncertain during development.

---

### ISSUE 4.5 — Ray-sphere intersection selection for rays inside the sphere (MINOR)

**Severity:** Minor  
**File:** `ray_tracing.py`, `intersect_sphere()`, line ~150

```python
if c < 0:
    # Внутри сферы - берём t2 (выход)
    t = t2
```

The condition `c < 0` means the ray origin is inside the sphere. Taking `t2` (the farther root) selects the exit point. This is correct for a ray starting inside a glass sphere. However, for a ray that has just refracted into a surface and is starting near the surface vertex, `c ≈ -R² + δ² ≈ -R²` (inside), so `t2` is chosen. This should give the next intersection with the same sphere — but we want the intersection with the **next** surface, not the same one.

Actually, for a standard singlet lens: surface 1 refracts the ray into the glass. The ray then travels to surface 2 (different sphere). The intersection with surface 2 uses different `R` and `z_surf`, so there's no ambiguity. The `c < 0` case applies when the ray is inside the sphere defined by **this** surface's curvature. For the target surface, this is fine — the ray approaches from outside.

On closer analysis, this logic is correct for the standard case. The comment is misleading ("exit from sphere") but the math works.

---

## 5. Data Model Completeness

### ISSUE 5.1 — No surface tilt/decenter (coordinate breaks) (MAJOR)

**Severity:** Major  
**File:** `optics_engine.py`, `Surface` dataclass

No fields for surface tilt (α, β) or decenter (dx, dy). Real optical systems often have tilted elements (scanning mirrors, prisms, decentred lenses). OPAL-PC likely supported some form of surface decentration.

**Recommendation:** Add `tilt_x: float = 0.0`, `tilt_y: float = 0.0`, `decenter_x: float = 0.0`, `decenter_y: float = 0.0` to `Surface`. Implement coordinate break handling in `trace_ray_through_system()`.

---

### ISSUE 5.2 — `image_type` field is unused (MINOR)

**Severity:** Minor  
**File:** `optics_engine.py`, `OpticalSystem.image_type`

`image_type` is defined but never referenced in any computation. Should either be used (for finite/infinite image conjugate calculations) or removed.

---

### ISSUE 5.3 — No per-surface transmission/aperture data (MINOR)

**Severity:** Minor  
**File:** `optics_engine.py`, `Surface` dataclass

No field for coating transmission, surface absorption, or custom aperture shapes (spider, annular, rectangular). For stray-light analysis and accurate energy calculations, these matter.

---

## 6. Approximations vs OPAL-PC Reference

### ISSUE 6.1 — Vignetting check uses paraxial refraction inside real ray loop (MAJOR)

**Severity:** Major  
**File:** `optics_engine.py`, `apply_vignetting()`, lines ~100-120

```python
# Приближённое преломление для продолжения трассировки
phi = (n_after - n_before) / R
l_new = (l * n_before - y_new * phi) / n_after
```

The function traces a ray through surfaces to check semi-diameter clearance, but uses **paraxial refraction** at each surface instead of vector Snell's law. For strong surfaces or large field angles, this gives incorrect ray positions at subsequent surfaces, leading to wrong vignetting predictions.

**Recommendation:** Use `trace_ray_through_system()` from `ray_tracing.py` instead of reimplementing an approximate tracer.

---

### ISSUE 6.2 — Ray launching from z=-50 for finite conjugates (MAJOR)

**Severity:** Major  
**File:** `aberrations.py`, multiple functions

For finite conjugate systems (object at finite distance), rays are launched from z=-50:

```python
# trace_aberration_fan(), line ~58:
ray = Ray(x=0, y=field_y, z=-50, k=0, l=(y_start - field_y) / 50, m=1)
```

The `/ 50` denominator assumes the pupil is 50mm away. For a finite object at, say, 200mm, the ray direction is wrong by a factor of 4. This affects all finite-conjugate aberration, spot, and MTF calculations.

Similarly in `compute_spot_diagram()`, `compute_focus_curve()`, `compute_spot_diagram_at_defocus()`:
```python
ray = Ray(x=x_start, y=field_y, z=-50,
         k=x_start/50, l=(y_start-field_y)/50, m=1)
```

**Recommendation:** Use the actual object distance from `system.object_distance` or `system.surfaces[0].thickness`, and compute proper direction cosines to the entrance pupil.

---

### ISSUE 6.3 — cos⁴θ relative illumination (MINOR)

**Severity:** Minor  
**File:** `optics_engine.py`, `compute_beam_geometry()`

```python
rel_illum = math.cos(angle) ** 4
```

This is the standard Smith-Holguin approximation. It ignores pupil distortion (pupil vignetting), which OPAL-PC may have included. For accurate relative illumination, the entrance pupil area should be computed as a function of field angle.

---

### ISSUE 6.4 — OPL computation in wavefront functions is inconsistent with trace engine (MAJOR)

**Severity:** Major  
**Files:** `diffraction_mtf.py:compute_wavefront_map()`, `zernike.py:_compute_opl_for_ray()`

Both functions re-compute OPL from the ray path instead of using `result.opl` from the trace engine:

```python
# zernike.py:_compute_opl_for_ray():
for k in range(len(result.path) - 1):
    p1 = result.path[k]
    p2 = result.path[k + 1]
    if k == 0:
        n = 1.0
    else:
        n = compute_refractive_index(system.surfaces[min(k-1, ...)].glass, wl)
    dist = math.sqrt(...)
    opl += n * dist
```

Problems:
1. **Mirror sign not handled** — uses glass of previous surface; for mirrors, the medium doesn't change but the glass field is `""`, giving n=1.0 even inside glass
2. **Doesn't use `result.opl`** — the trace engine already accumulates OPL correctly including mirror handling
3. **Reference sphere not implemented** — for wavefront aberration, OPL should be computed to a point on the reference sphere centered at the ideal image point, not to a flat z-plane:

```python
# diffraction_mtf.py:compute_wavefront_map():
dz_to_focus = parax_focus_z - last[2]
opl_full = result.opl + 1.0 * dz_to_focus  # flat plane, not reference sphere
```

For off-axis fields, the reference sphere is tilted by the field angle. Using a flat z-plane introduces errors proportional to `field_angle² × pupil_radius² / (2×f')`.

**Recommendation:**
1. Use `result.opl` directly from the trace engine
2. For wavefront aberration, compute OPL to the reference sphere: for each ray, project onto the sphere of radius `R_ref` centered at the paraxial image point, where `R_ref = distance from exit pupil to image point`

---

## 7. Ray Launching Strategy

### ISSUE 7.1 — Rays not aimed at entrance pupil in most functions (MAJOR)

**Severity:** Major  
**Files:** `aberrations.py` (multiple functions), `diffraction_mtf.py`, `zernike.py`

Only `trace_fan()` and `trace_grid_3d()` correctly project pupil coordinates back to the start plane:

```python
# trace_fan() — CORRECT:
dz = z_pupil - z_start
y_at_start = y_start - dz * math.sin(angle) / math.cos(angle)
```

But most other functions launch rays from the pupil coordinate directly:
```python
# compute_spot_diagram() — WRONG for off-axis:
ray = Ray(x=x_start, y=y_start, z=-50, k=math.sin(angle), l=0, m=math.cos(angle))
```

At z=0 (first surface), this ray is at `(x_start + 50·tan θ, y_start, 0)` instead of `(x_start, y_start, 0)`. For a 5° field, the displacement is 50·tan(5°) ≈ 4.4mm — comparable to a typical entrance pupil radius.

**Impact:** For off-axis fields, the ray bundle samples the wrong region of the pupil. The chief ray doesn't pass through the center of the stop. All spot diagrams, PSFs, MTF curves, and Zernike coefficients for field ≠ 0 are computed with incorrectly positioned rays.

**Recommendation:** Standardize the ray launching from `trace_fan()` / `trace_grid_3d()`:
1. Compute entrance pupil z from `paraxial_trace()['sP']`
2. For each pupil coordinate (px, py), compute the start position at z_start such that the ray passes through (px·D/2, py·D/2) at z_pupil with the field angle direction

---

### ISSUE 7.2 — Entrance pupil position approximated by stop surface z (MAJOR)

**Severity:** Major  
**Files:** `ray_tracing.py:trace_fan()`, `trace_grid_3d()`, `aberrations.py:compute_field_aberrations()`

```python
# trace_fan():
z_pupil = 0.0
for j in range(min(stop_idx, len(sys.surfaces))):
    z_pupil += sys.surfaces[j].thickness
z_pupil += stop_off
```

This uses the **physical stop surface position** as the entrance pupil position. The actual entrance pupil is the **image of the stop through all preceding optics**. For systems with lenses between the first surface and the stop, the entrance pupil can be significantly displaced.

In `compute_field_aberrations()`, `sP` from paraxial trace IS retrieved but not actually used in ray aiming:
```python
sP = parax.get('sP', z_pupil)  # retrieved but not used in ray launch
# Rays launched from z=-1 with field angle, ignoring sP
```

**Impact:** For telephoto or retrofocus systems where the entrance pupil is far from the stop, rays are aimed at the wrong plane. Pupil aberration is ignored.

**Recommendation:** Use `paraxial_trace()['sP']` (entrance pupil distance from first surface) as the pupil z-position for ray aiming in all functions.

---

### ISSUE 7.3 — No entrance pupil diameter check for ray grid (MINOR)

**Severity:** Minor  
**File:** `ray_tracing.py:trace_grid_3d()`

The grid samples a circle of radius `pupil_radius = aperture / 2`. For systems with central obscuration (`obscuration_ratio > 0`), the center rays are blocked in `trace_fan()` but NOT in `trace_grid_3d()`. This affects reflecting telescopes (Cassegrain, Gregorian).

**Recommendation:** Add obscuration check in `trace_grid_3d()`:
```python
if obscuration > 0 and r < obscuration * pupil_radius:
    continue
```

---

## Additional Findings

### ISSUE A.1 — Geometric MTF uses pure Python FFT (MINOR)

**Severity:** Minor  
**File:** `aberrations.py:_fft1d()`, `_fft2d()`

Recursive Cooley-Tukey FFT is implemented in pure Python. For N=256, this is ~40× slower than numpy FFT. Since numpy is already a dependency, use `np.fft.fft2()` directly.

### ISSUE A.2 — `compute_diffraction_mtf` OTF formula (MINOR)

**Severity:** Minor  
**File:** `diffraction_mtf.py:compute_diffraction_mtf()`

The OTF computation uses:
```python
ft = np.fft.fft2(pupil_complex)
power = np.abs(ft_shifted)**2
otf = np.fft.ifft2(np.fft.ifftshift(power))
```

This computes `OTF = IFFT(|FFT(P)|²)` which is the autocorrelation of the pupil function via the Wiener-Khinchin theorem. This is **correct** — the OTF is the autocorrelation of the pupil function. ✓

### ISSUE A.3 — Zernike normalization (MINOR)

**Severity:** Minor  
**File:** `zernike.py:_zernike_poly()`

The Zernike polynomials are not normalized to unit RMS (the Noll normalization). For example, `Z²₀ = 2ρ²−1` has RMS = 1/√3, not 1. The standard Noll-normalized form would be `Z²₀ = √3·(2ρ²−1)`. The least-squares fit will still find the best coefficients, but comparing magnitudes between different Zernike terms is misleading.

### ISSUE A.4 — Spot diagram uses square grid, not hexapolar (MINOR)

**Severity:** Minor  
**File:** `aberrations.py:compute_spot_diagram()`

Uses a square grid with circular masking. For the same number of rays, a hexapolar (concentric rings + radial) distribution gives more uniform pupil sampling and avoids aliasing along the axes.

---

## Summary Table

| # | Severity | File | Issue |
|---|---|---|---|
| 3.1 | **CRITICAL** | ray_tracing.py | Aspheric polynomial derivative: wrong power AND coefficient |
| 1.1 | MAJOR | aberrations.py + 4 files | Field direction axis inconsistency (k vs l) |
| 1.2 | MAJOR | aberrations.py | Meridional/sagittal swap in chief_ray_characteristics |
| 2.1 | MAJOR | optics_engine.py | Seidel invariant incorrect (Δnu vs n·(u+h/R)) |
| 3.4 | MAJOR | ray_tracing.py | HOLOGRAM/GRATING/TOROIDAL defined but not traced |
| 5.1 | MAJOR | optics_engine.py | No surface tilt/decenter support |
| 6.1 | MAJOR | optics_engine.py | Vignetting uses paraxial refraction |
| 6.2 | MAJOR | aberrations.py | Finite conjugate rays launched from z=-50 |
| 6.4 | MAJOR | diffraction_mtf.py, zernike.py | OPL re-computed incorrectly; no reference sphere |
| 7.1 | MAJOR | aberrations.py + 3 files | Rays not aimed at entrance pupil |
| 7.2 | MAJOR | ray_tracing.py | Stop z used instead of entrance pupil z |
| 2.2 | Minor | optics_engine.py | Paraxial notation needs documentation |
| 2.3 | Minor | global | No paraxial-real cross-validation |
| 3.2 | Minor | optics_engine.py | NA→D linear approximation |
| 3.3 | Minor | ray_tracing.py | Mirror sign convention discrepancy |
| 4.1 | Minor | aberrations.py | _find_focal_z loose bounds |
| 4.2 | Minor | glass_catalog.py | Herzberger pole unguarded |
| 4.3 | Minor | ray_tracing.py | Dead code in aspheric |
| 5.2 | Minor | optics_engine.py | image_type unused |
| 5.3 | Minor | optics_engine.py | No coating/aperture data |
| 6.3 | Minor | optics_engine.py | cos⁴θ illumination only |
| 7.3 | Minor | ray_tracing.py | No obscuration in grid_3d |
| A.1 | Minor | aberrations.py | Pure Python FFT |
| A.2 | Minor | diffraction_mtf.py | OTF formula correct ✓ |
| A.3 | Minor | zernike.py | No Noll normalization |
| A.4 | Minor | aberrations.py | Square grid, not hexapolar |

---

## Recommended Priority Order

1. **Fix aspheric derivative** (Critical, 2 lines of code)
2. **Standardize field direction** (Major, ~12 functions, straightforward)
3. **Fix ray launching / entrance pupil aiming** (Major, central to all off-axis results)
4. **Fix Seidel invariant** (Major, affects 3rd-order aberration accuracy)
5. **Use result.opl for wavefront** (Major, affects all wavefront/MTF/PSF)
6. **Fix finite-conjugate ray launching** (Major, affects finite object systems)
7. Implement unsupported surface type warnings
8. Add tilt/decenter support (larger scope)
