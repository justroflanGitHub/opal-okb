# LBO Binary Format — Reverse Engineering Documentation

## Overview

`.LBO` files are optical system libraries used by OPAL-PC (MS-DOS CAD).
Each `.LBO` file contains multiple optical systems in a compact binary format.

## LBO File Structure

```
[Record 1: 22-byte header + OPJ data]
[Record 2: 22-byte header + OPJ data]
...
[Record N]
```

### Record Header (22 bytes)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00   | 2    | uint16 | Marker (0x000C) |
| 0x02   | 12   | char[12] | OPJ filename (ASCII, e.g. "ST01FA01.OPJ") |
| 0x0E   | 4    | bytes | Metadata/hash |
| 0x12   | 4    | uint32 | OPJ data size (N) |
| 0x16   | N    | bytes | OPJ binary data |

## OPJ Data Structure (inside LBO)

### Header

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00   | 4    | bytes | Magic/version |
| 0x04   | 4    | uint32 | Total size |
| 0x08   | 4    | bytes | Reserved |
| 0x0C   | 40   | char[40] | System name (cp866, Russian) |
| 0x34   | 2    | uint16 | num_surf (surface count, NOT including trailing air) |
| 0x36   | 2    | uint16 | Unknown |
| 0x38   | 2    | uint16 | num_wl (wavelength count) |
| 0x3A   | 6    | bytes | Config flags |

### System Parameters

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x40   | 16   | bytes | Config/aperture data |
| 0x58   | 8    | float64 | Y height (semi-aperture, mm) |
| 0x60   | 8    | float64 | Duplicate or field data |
| 0x68   | 8    | float64 | SD (stop diameter or f/number) |
| 0x70   | 8    | float64 | Field angle 1 (radians) |
| 0x78   | 8    | float64 | Field angle 2 (radians) |
| 0x80   | 24   | bytes | Zeros / reserved |

### Surface Data

#### Curvatures (at offset 0xA8)

`num_surf` values of `float64`, each = **curvature C = 1/R** (not radius!).

To get radius: `R = 1.0 / C` (or `R = 0.0` if `C ≈ 0` for flat surface).

#### Thicknesses (immediately after curvatures)

`num_surf` values of `float64`, representing axial distance to next surface.

Last thickness is followed by **end marker**: `float64` value of `1.0e+20`.

### Glass Index Array (after end marker)

`num_surf + 1` values of `uint16`, 1-based indices into glass name block:

- Index **1** = ВОЗДУХ (air)
- Index **2** = first glass in block
- Index **3** = second glass
- etc.

**Mapping rule**: glass AFTER surface `i` = `glass_names[glass_indices[i+1] - 1]`

(Glass at position `i` in the index array represents the medium **to the left** of surface `i`, which equals the medium **after** surface `i-1`.)

### Wavelength Indices (after glass indices)

`num_wl` values of `uint16`, indices into OPAL-PC standard wavelength table:

| Index | λ (μm) | Spectral line |
|-------|---------|---------------|
| 1     | 0.58930 | d (Na)       |
| 2     | 0.48613 | F (H)        |
| 3     | 0.65627 | C (H)        |
| 4     | 0.43584 | g (Hg)       |
| 5     | 0.58756 | d (He)       |
| 6     | 0.70652 | r (He)       |
| 7     | 0.66782 | B (He)       |
| 8     | 0.50858 | e (Hg)       |

### Glass Name Block

Located by searching for cp866 bytes of `"ВОЗДУХ"`.

Each entry: 8 bytes, cp866 encoded, null-padded.

Format: `[ВОЗДУХ] [glass_1] [glass_2] ... [glass_N]`

Only **unique** glass names stored (repeating glasses not duplicated).

### Semi-Diameters (after glass block)

Located at: `glass_offset + num_glass_text_entries * 8 + 4` (4-byte gap).

`num_surf` values of `float32`, representing D/2 (semi-diameter in mm).

### Refractive Index Matrix (before glass block)

Compact storage: `[air_count × 1.0] + [glass_count × ri_per_wl]`

- Air entries: `float64` values of `1.0` (typically 3)
- Glass entries: `ri_per_wl` values per glass (typically 3 wavelengths: d, F, C)

Total: `air_count + glass_count × ri_per_wl` float64 values.

## Example: Индустар-23у f'=110

```
num_surf = 7, num_wl = 5

Curvatures (0xA8):
  C₀=0.032808 → R₀=30.48
  C₁=0.000000 → R₁=0.00 (flat)
  C₂=-0.014656 → R₂=-68.23
  C₃=0.035651 → R₃=28.05
  C₄=-0.004655 → R₄=-214.80
  C₅=0.034990 → R₅=28.58
  C₆=-0.022696 → R₆=-44.06

Thicknesses: 4.5, 4.9, 1.9, 8.4, 1.6, 6.0

Glass indices: [1, 2, 1, 3, 1, 4, 5, 1]
  → [ВОЗДУХ, ТК16, ВОЗДУХ, ЛФ5, ВОЗДУХ, ОФ1, ТК20, ВОЗДУХ]

Glass names: [ВОЗДУХ, ТК16, ЛФ5, ОФ1, ТК20]

Semi-diameters: 12.35, 12.10, 11.00, 10.50, 10.75, 11.00, 11.10

Result: f' = 109.83 mm (target: 110 mm, error: 0.2%)
```

## Library Statistics

| LBO File | Systems | Description |
|----------|---------|-------------|
| LENS.LBO | 116 | Camera lenses (Индустар, Юпитер, etc.) |
| USLENS.LBO | 234 | US-format lenses |
| OCULAR.LBO | 76 | Oculars (eyepieces) |
| RUSSAR.LBO | 84 | Wide-angle lenses (Руссар) |
| BINOCUL.LBO | 22 | Binoculars |
| REPROD.LBO | 13 | Reproduction lenses |
| USREPROD.LBO | 15 | US reproduction lenses |
| MICROLEN.LBO | 16 | Microscope objectives |
| USBINOCL.LBO | 10 | US binoculars |
| USEYE.LBO | 8 | Eyepieces (US format) |
| LENS_SPC.LBO | 6 | Special lenses |
| USMICRO.LBO | 6 | US microscope objectives |
| ZOOM.LBO | 6 | Zoom lenses |
| **Total** | **612** | |

## Validation Results

20/20 LENS.LBO systems loaded within 1% of target focal length:

| System | f' (calculated) | f' (target) | Error |
|--------|-----------------|-------------|-------|
| Индустар-7 | 104.0 | 104 | 0.0% |
| Индустар-21 | 80.5 | 80 | 0.6% |
| Индустар-23у | 109.8 | 110 | 0.2% |
| Индустар-37 | 302.7 | 300 | 0.9% |
| Индустар-51 | 211.5 | 211 | 0.2% |
| Индустар-58 | 75.0 | 75 | 0.0% |
| Индустар-61 | 53.1 | 53 | 0.2% |
| Индустар-71 | 46.4 | 46 | 0.9% |
