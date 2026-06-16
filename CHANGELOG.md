# Changelog

All notable changes to OPAL-OKB will be documented in this file.

## [Unreleased]

### Added
- 7 demo systems: achromat, Cook doublet, telephoto, Petzval, mirror, meniscus, plano-convex
- Afocal system support (0,0 / 1,0): parallel ray output without focal point
- Finite object support: object placed at front focal point (sF)
- Object visualization (yellow arrow) for finite object type
- Glass catalog expanded: К2, К5, К9, К13, ТФ2, БФ7, БФ12, ЛФ5, ТК9
- ThreadPoolExecutor parallel computation (up to 8 workers) for all analysis tasks
- Global table/graph toggle mode (applies to all tabs)
- "Демо примеры" submenu with 8 systems

### Fixed
- Ray extension to focal point: uses real ray crossing, not paraxial BFD
- Afocal viewport: z_max adapts for parallel output rays
- `reverse_system()`: glass + thickness now correctly paired (К8 d=5 → К8 d=5)
- `reverse_system()`: adds air surface at start (former image plane)
- TФ2 missing from glass catalog (was returning n=1.5 instead of 1.686)
- `apply_results()`: attribute name mismatches (LSF, ESF, ENC, Wavefront, Bar target)
- Crosshair coordinates match cursor at any zoom level (QPainter save/restore)
- Pan direction: drag right = content moves right
- Font size no longer scales with zoom
- NaN/inf filtering in wavefront map (PV, RMS, min, max)
- `paint_finalize` moved to InteractivePlot (crash on FocusDiagramWidget)
- `_reverse_system()` now calls `_calculate()` automatically
- Multithreading: Worker does heavy computation, GUI thread only updates
- Object distance auto-determined from sF (not manual field)

### Changed
- Terminology: "Поверхности оптической системы" → "Конструктивные параметры"
- Column headers: "Радиус" → "Радиусы", "Толщина" → "Осевые расст.", "Стекло" → "Марка стекла", "Полудиам." → "Высоты"
- "Параксиальные параметры" → "Параксиальные характеристики"
- "Длины волн" → "Спектральные линии"
- Number formatting unified per OPAL-PC: 5 decimals (aberrations), 6 (chief rays, Zernike), 4 (general)
