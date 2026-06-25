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
| 0x36   | 2    | uint16 | flags (3 = standard centered system) |
| 0x38   | 2    | uint16 | num_wl (wavelength count) |
| 0x3A   | 2    | uint16 | **ND** (stop surface number) |
| 0x3C   | 2    | uint16 | **Тип предмета**: 0=дальний (∞), 1=ближний (конечный) |
| 0x3E   | 2    | uint16 | Reserved (always 1) |
| 0x46   | 2    | uint16 | **Тип изображения**: 0=ближний, 65535=дальний (∞) |

### System Parameters

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x40   | 24   | bytes | Config/reserved |
| 0x58   | 4    | bytes | Reserved/padding |
| 0x5C   | 8    | float64 | **Апертура**: Y/2 (мм) если ≥1, NA (sin) если <1 |
| 0x64   | 8    | float64 | Апертура (duplicate) |
| 0x6C   | 8    | float64 | **SD** (смещение диафрагмы от ND, мм) |
| 0x70   | 8    | float64 | Флаг виньетирования/светораспределения: +2.0, -2.0, или 0 (25+5 из 612 систем) |
| 0x74   | 8    | float64 | **Поле** (радианы если |v|<1, градусы если |v|≥1) |
| 0x7C   | 8    | float64 | Поле (duplicate) |
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
- Index **65535** (0xFFFF) = **Зеркало** (mirror surface)

**Mapping rule**: glass AFTER surface `i` = `glass_names[glass_indices[i+1] - 1]`

**Mirror detection**: if `glass_indices[i]` or `glass_indices[i+1]` = 65535,
surface `i` is reflective (`is_reflective = True`).

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

Glass names can be **concatenated** within 8-byte slots when names exceed
8 characters (e.g. ВОЗДУХ + КВ | АРЦСТК = two names ВОЗДУХ and КВАРЦСТК
in 16 bytes). The decoder splits them using a database of known glass names.

Format: `[ВОЗДУХ] [glass_1] [glass_2] ... [glass_N]`

Only **unique** glass names stored (repeating glasses not duplicated).

Known long names: КВАРЦ, КВАРЦСТК, ФЛЮОРИТ.

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

## Example: Об.зеркально-линз. f'=450 1:5.5 2w=1

```
num_surf = 6, num_wl = 2
Aperture: 0x3A=0 (NA), 0x5C=0.089
Field: 0x74=-0.008727 rad = -0.5° (= -0.3 гр.мнск)

Surfaces:
  S1: R=382.80, d=10.30, glass=КВАРЦСТК, sd=40.35
  S2: R=-361.40, d=6.40, glass=ВОЗДУХ, sd=40.35
  S3: R=-105.20, d=6.40, glass=КВАРЦСТК, sd=40.00
  S4: R=-223.40, d=54.10, glass=ВОЗДУХ, sd=41.00
  S5: R=-155.96, d=-61.20, glass=ЗЕРКАЛО, sd=42.00, is_reflective=True
  S6: R=-37.41, d=0, glass=ЗЕРКАЛО, sd=9.00, is_reflective=True

Result: f' = 428.62 mm (target: 450, error: 4.8%)
```

## Wavelength Fallback

If wavelength indices in LBO are all zero (no wavelength data stored),
the decoder falls back to standard set: **e (0.54607), G' (0.43405),
C (0.65627)**. Standard line names are auto-assigned when values match
known spectral lines.

## Angle Format: Г.ММСС

OPAL-PC uses **Г.ММСС** (градусы.минутысекунды) format for angular fields:
- 0.30 гр.мнск = 0°30'00" = 0.5°
- 23.1200 гр.мнск = 23°12'00" = 23.2°

Conversion functions: `deg_to_gmms()`, `gmms_to_deg()`, `gmms_to_str()` in `system_utils.py`.

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
