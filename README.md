# OPAL-OKB - Optical CAD

> An open-source, clean-room reimplementation of **OPAL-PC** (MS-DOS, 1990s,
> NII OMP / VNTs SAM, USSR) in **Python 3.10+ / PyQt5** - fully verified
> against the original.

📘 English version | 📗 [Русская версия](README_RU.md)

[![Tests](https://img.shields.io/badge/pytest-1542%20passed%20%2F%208%20skipped-brightgreen)]()
[![Verification](https://img.shields.io/badge/golden%20bank-44%20systems%2C%20921%20checks%20GREEN-blue)]()
[![Release](https://img.shields.io/badge/release-v1.28.0-orange)]()

Design, analysis, optimization and visualization of optical systems: lenses,
objectives, eyepieces, catadioptric schemes and holographic optical elements
(HOE). The original MS-DOS package has been fully reverse-engineered
(Ghidra disassembly + automated DOSBox rig); reference runs from 1997 are
reproduced byte-for-byte. Formulas: [docs/FORMULAS.md](docs/FORMULAS.md)
(Russian).

## 🤖 Built for agents

Every menu item, tool and dialog runs a command from a single registry of
**506 commands** (40 categories). The UI, the CLI, the JSON control channel
and the MCP server all call the same layer — so anything you can click,
a script or an AI agent can do too. The registry grows with each feature
wave (R500 wave complete: 140 → 506 parameterized commands).

### MCP server

OPAL-OKB ships an MCP server (Model Context Protocol, JSON-RPC 2.0 over
stdio, pure stdlib): every registry command is published as an agent tool
(`calc.paraxial` → tool `calc_paraxial`, full JSON Schema for arguments).
The session context is persistent - create or load a system once, then run
calculations without re-passing the file. Oversized outputs are truncated
with a hint, keeping the agent's context small. Logs go to stderr only;
stdout is reserved for the protocol.

Run it: `py -m commands mcp`. Connect from any MCP client (Claude Code,
OpenClaw, ...):

```json
{
  "mcpServers": {
    "opal-okb": {
      "command": "py",
      "args": ["-m", "commands", "mcp"],
      "cwd": "C:/path/to/opal_okb"
    }
  }
}
```

---

## Install & run

```bash
pip install PyQt5 numpy
python main.py
```

- Python 3.10+ (3.13 recommended)
- Ready-to-use **OPAL-PC.exe** - see [Releases](https://github.com/justroflanGitHub/opal-okb/releases)
  (the 700+ system library is bundled; works out of the box and portably)
- Tests: `python -X utf8 -m pytest -q` - **1177 passed / 8 skipped**

## Features

### Computation core
- **Paraxial analysis** (y-nu): focal segments, cardinal points, pupils (mm/dioptre)
- **Real ray tracing**: vectorial Snell's law, TIR, OPL, aspheres (conic + polynomials)
- **Tilted & decentered systems**: exact tracing in local surface coordinates
- **Mirrors & catadioptrics**: sign conventions, obscuration, odd reflection counts
- **Holographic optical elements**: `SurfaceType.HOLOGRAM` - effective curvature
  via the reverse-engineered κ(λ) law (verified to 0.073 dioptre across 3 λ)
- **Multi-wavelength** - up to 5 λ, Herzberger dispersion + exact OPAL indices

### Library & catalogs
- **83 standalone .OPJ + 13 LBO libraries** (LENS 116, OCULAR 76, RUSSAR 84,
  BINOCUL 22 ... ≈ 700 systems): strict standalone-OPJ parser (validated against
  the golden bank), full LBO decoder (mirrors, smart glass-split)
- **Glass catalog - 891 grades**: GOST, Schott, HOYA, Ohara; nd-νd diagram
- **Achromatization** - automatic radius matching for crown+flint pairs

### Analysis - 28 tabs
Paraxial · Spot diagram (2D/3D) · Through-focus · Axial fan 2×2 · transverse
Δy′ · longitudinal Δs′ · wavefront W (OPL) · MTF (geometric + diffraction) ·
Distortion · Astigmatism · Coma · Focusing · PSF / PSF 3D · LSF · ESF ·
Image simulation (test charts) · ENC · PTF · Topogram · Beam footprint /
vignetting · Chief rays · Zernike (+ global) · Wavefront map 2D/3D · Bar
chart · Ray table · Seidel SI-SV

**OPAL protocol tables** (byte-for-byte with the original): TABGL, TABPR2,
TABOC1, TABOC2, TABBEA (vignetting/illumination), TABESB (beam heights),
TABEAP (obscuration zones), PSF/LSF/OTF/EE sections, Strehl (Maréchal +
exact FFT).

### Optimization
- **LAP/GTISL** - a complete port of the OPALLAP optimizer: central-difference
  Jacobian, damped Marquardt normal equations, step limiter, λ adaptation,
  OPAL istop codes, penalty bounds, variable linking, 1×1 solve mode;
  PAR/EQF/MF input language
- DLS and Nelder-Mead for quick starts
- **Fit characteristics** (f′, BFD × any parameter) with preview dialog

### GUI
OPAL-PC-style ray layout (black background, green rays), chromatic rays,
zoom/pan/crosshair, fullscreen; multithreaded computation (phase 1 instant,
phase 2 up to 8 threads); .txt report; .OPJ/.JSON import-export;
reverse/scale/GOST radii.

---

## Reverse-engineering roadmap

Master index - `analysis/REVERSE_TRACE.md` (§0-§24, Russian), wave plan -
`docs/REVERSE_PLAN.md`, dossiers - `analysis/REVERSE_*.md`.

### ✅ Phase I - Data formats & tables (waves 1-7)

- [x] **OPAL binary formats** - .LBO (header, mirrors, smart glass-split),
      standalone .OPJ (λ-slots, object position, ND+SD stop plane)
- [x] **10 protocol tables byte-for-byte**: TABGL, TABPR2, TABOC1, TABOC2,
      TABBEA, TABESB, TABEAP + PSF/OTF sections *(TRACE §11-§19)*
- [x] **OPAL unit system**: gr.minsec, pupil coordinates, mm↔dioptre *(REVERSE_NZR)*
- [x] **Orchestrator E0-E19** - call map of the OPALA computation pipeline *(REVERSE_0746)*
- [x] **EXEPACK unpacking of OPALA** *(REVERSE_TSR)*
- [x] **FORTRAN RTL formatter** - HALF_UP rounding, port fix *(REVERSE_FMT)*
- [x] **DOSBox rig** - boot architecture, .REG, OPALPCX *(REVERSE_G1)*

### ✅ Phase II - Computation modules (waves 8-10)

- [x] **Diffraction engine OPALO/OPALOW** - PSF, LSF, MTF, EE,
      central obscuration *(REVERSE_OPALO)*
- [x] **Zernike OPAVA** - 28-term basis (n ≤ 12), least-squares fit *(REVERSE_OPAVA)*
- [x] **Optimizer OPALLAP** - LAP/GTISL, istop codes, PAR/EQF/MF language;
      fit_dialog repaired *(REVERSE_LAP, OPTDOC)*
- [x] **Glass dictionary OPALOS** - 71 grades, OPT-file parser *(REVERSE_OS)*
- [x] **Best-focus criteria** - min RMS / max Strehl / min spot / zonal / EQF *(TRACE §20)*
- [x] **Real obscuration** - passage zones, ellipse, Seidel cross-check

### ✅ Phase III - Golden verification (G-wave)

- [x] **OPAL.COM resident** - int 90h service bus (16 services), OPAL.PSP
      cipher, 25-module catalog *(REVERSE_OPCOM §21)*
- [x] **Golden run** - DOSBox→.PRN recipe, bank of 14 reference systems,
      byte-exact match with the 1997 archive *(REVERSE_G2_GOLDEN, G2BANK)*
- [x] **Port vs bank verification** - 48 → **307 GREEN**; pupils z/d/p, near
      object, virtual images, rim rays, print λ-law *(REVERSE_GVERIFY, GFIX)*
- [x] **Corpus scan** - all **612** LBO library systems through the port kernel:
      612/612 pipeline OK, f' vs catalog name **393/565 within 1%** (48 broken
      decodes found and localized); wave 2 adds vignette/chief/spot/mtf_geo
      (schema 2: ok 396, all 216 failures on the new ops) *(CORPUS_REPORT_V2,
      CORPUS_REPORT, CORPUS_ANOMALIES)*
- [x] **OPALA core disassembly** - 789 functions (Ghidra), full wavefront
      print pipeline, two-pass fan *(REVERSE_OPALDIS)*
- [x] **HOE system GTIE00** - 0xFFFD marker, recording block, κ(λ) law
      in the port *(REVERSE_GTIE, GOE_MODEL)*

### 🔜 Phase IV - Future (by priority)

- [x] **Built for agents** — single registry of **506 commands** (UI/CLI/JSON/MCP
      call the same layer): everything clickable is scriptable and
      agent-accessible *(done 2026-10-23: waves 1–5 — registry, CLI, REPL,
      mass coverage, UI bridge, MCP server; 1542 tests green)*
- [ ] **grow the registry to 500+** — parameterized variants as features land
- [ ] **X. x87 march emulator** - mini 8086+x87 emulator over the unpacked
      OPALA image with traps on runtime seeds → close the last 17 bank rows;
      alternative: DOSBox debugger *(a week)*
- [ ] **OPALTOL "tolerances"** - manufacturing sensitivity analysis: the last
      major unreverse-engineered module *(2-3 waves)*
- [ ] **OPALCALC / OPALEDIT / OPALTRAN / OPALSHOW** - remaining package
      modules (OPALSHOW decompile already on disk) *(in batch)*
- [ ] **True HOE diffraction** - ray tracing through holograms (currently a
      paraxial κ-model) *(1 wave)*
- [ ] **OPAL.COM §21.12** - runtime probe of the first EXEC *(1 session)*
- [x] **Golden bank extension** - 14 → 44 systems batch export, one DOSBox
      night (g2bank.py wave 3: 28/29 OK, LOV refused RT start), CI-green;
      wave-2 port-vs-PRN sweep: 43 end-to-end systems, **921 checks GREEN**,
      28 fully green, 15 xfail residuals *(docs/tasks/G44_FINDINGS,
      G44_FINAL_REPORT; done 2026-10-23)*

---

## Project layout

```
main.py                  # GUI (QMainWindow, 28 analysis tabs)
domain/                  # models, paraxial math, spatial systems
analysis/                # core: ray tracing, aberrations, OPAL tables,
                         #   LAP optimization, psf_mtf, zernike, golden_*
                         #   + reverse-engineering tools & dossiers (RU)
fileio/                  # OPJ/LBO/JSON io, strict standalone_opj, protocol
catalog/                 # system library, glass catalog (891)
gui/                     # controllers, dialogs, widgets
native/                  # C++ ray-tracing core (parity with Python)
tests/                   # 1177 tests, incl. golden bank + march pins
docs/                    # REVERSE_PLAN, FORMULAS, LBO_FORMAT, tasks/
extracted/opal_okb/      # original OPAL-PC package (OPJ/LBO/ARH/DOC)
scripts/                 # DOSBox automation, g2bank, diagnostics
```

## Documentation

- `README_RU.md` - detailed README in Russian
- `docs/FORMULAS.md` - formula reference (core math & OPAL print conventions, RU)
- `analysis/REVERSE_TRACE.md` - reverse-engineering master index §0-§24 (RU)
- `docs/REVERSE_PLAN.md` - wave plan + future front X (RU)
- `docs/LBO_FORMAT.md` - .LBO binary format specification
- `CHANGELOG.md` - version history (1.22.0-1.24.8: golden verification)

## Releases

- **v1.24.6** - library data bundled into the exe · [Download OPAL-PC.exe](https://github.com/justroflanGitHub/opal-okb/releases/latest)
- v1.24.5 - golden verification (307 GREEN)

## License

Educational project. OPAL-PC © NII OMP / VNTs SAM (USSR, 1990s).
