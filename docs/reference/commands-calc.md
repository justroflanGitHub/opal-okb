# Категория calc

36 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`calc.aber.dioptre`](#calcaberdioptre) | Продольная аберрация в диоптриях от плоскости ВЫХОДНОГО ЗРАЧКА: дптр = 1000/L′_зоны − 1000/L′_паракс (FORMULAS.md §3, GVERIFY §2.2; L′=0 → пустая ячейка печати OPAL — null) | `L_zone_mm`, `L_parax_mm` | {L_zone_mm, L_parax_mm, zone_dpt, parax_dpt, dioptres} |
| [`calc.aber.grminsec`](#calcabergrminsec) | Поперечная аберрация в мере «гр.мнсек»: угол atan2(Δy, L′) из ЦЕНТРА выходного зрачка на точку луча в плоскости Гаусса + печать DD.MMSS (FORMULAS.md §3, OPALDIS OD3) | `dy_mm`, `L_mm` | {dy_mm, L_mm, angle_deg, grminsec, print} |
| [`calc.airy`](#calcairy) | Дифракционный диск Эйри: d = 2·1.22·λ·F/# | `f_number`, `wl` | {f_number, wl, radius_um, diameter_um} |
| [`calc.aperture.na`](#calcaperturena) | Числовые апертуры: в пространстве изображений NA′ = D/(2f′) и предмета NA = NA′·\|V\| | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {na_image, na_object, f_number} |
| [`calc.aperture.real`](#calcaperturereal) | Реальный диаметр осевого пучка по полудиаметрам поверхностей | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `sharp_edge` | диаметр (мм) или null — если полудиаметры не заданы |
| [`calc.beam_geometry`](#calcbeam_geometry) | Габариты пучков по полям: апертуры, виньетирование, светораспределение | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `semi_mode`, `sharp_edge` | список результатов по точкам поля |
| [`calc.cardinals`](#calccardinals) | Кардинальные точки: фокусы F/F′, главные плоскости H/H′, фокусные расстояния | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {f, f_prime, sF, sF_prime, sH, sH_prime, back_focal_distance, front_focal_distance} |
| [`calc.conjugate.solve`](#calcconjugatesolve) | Сопряжённые отрезки (формула отрезков, 1/s′ − 1/s = 1/f′): по s → s′, V; или по V → s | `file`, `system`, `lbo_index`, `lbo_name`, `f_override`, `s`, `V_target` | {f_prime, s, s_prime, V} |
| [`calc.defocus.convert`](#calcdefocusconvert) | Конверсия дефокуса мм ↔ волны на краю зрачка: W = PARAXIAL_DEFOCUS_FACTOR·Δz·NA′²/λ (формула analysis/advanced.compute_psf; хелпер П14 — adv_ext_cmds._defocus_waves_per_mm) | `file`, `system`, `lbo_index`, `lbo_name`, `defocus_mm`, `waves`, `wl` | {wl, na_image, waves_per_mm, defocus_mm, waves} |
| [`calc.depth.criteria`](#calcdepthcriteria) | Границы глубины резко изображаемого пространства по допускам критериев (ANALIZE §5.3: «положения индивидуальных границ глубины резкости из условия, чтобы не превышать максимально допустимых значений СКW (СКR)»): скан дефокуса, интервал где критерий ≤ допуска | `file`, `system`, `lbo_index`, `lbo_name`, `criterion`, `max_value`, `defocus_range`, `steps`, `field_y`, `wl`, `num_rays`, `grid_size` | {criterion, max_value, unit, wl, field_y, defocus_range, steps, waves_per_mm, best_focus_mm, min_value, near_mm, far_mm, depth_mm, satisfied, clipped_near, clipped_far, rows: [{defocus_mm, value}]} |
| [`calc.depth_of_field`](#calcdepth_of_field) | ГРИП (геометрическая): ±Δ = c·F/#·(1+m), полная глубина 2Δ | `f_number`, `coc_um`, `magnification` | {f_number, coc_um, magnification, plus_minus_mm, total_mm} |
| [`calc.diffraction.cutoff`](#calcdiffractioncutoff) | Дифракционный срез ЧКХ: ν_c = 1/(λ·F/#), лин/мм | `f_number`, `wl` | {f_number, wl, cutoff_lpmm} |
| [`calc.edge2.lambda`](#calcedge2lambda) | Множитель печати λ(z) = 1 − (q0 + q1·z²)·z² ближнего предмета E2 (FORMULAS.md §3, REVERSE_OPALDIS §4.3(vii); q-пары банка — analysis.aberrations.EDGE2_PRINT_LAMBDA, верифицировано золотыми прогонами) | `system`, `kind`, `zones` | {system, kind, q0, q1, rows: [{zone, lambda}]} |
| [`calc.fan.launch`](#calcfanlaunch) | Запуск лучей осевого веера (FORMULAS.md §3, GFIX P6): дальний предмет — по высоте зона·Ax параллельно оси; ближний — по углу arcsin(зона·NA) от точки предмета (Ax = sin NA) | `zones`, `ax_mm`, `na` | {ax_mm, na, rows: [{zone, far_y_mm, near_u_deg}]} |
| [`calc.goe.kappa`](#calcgoekappa) | Закон эффективной кривизны ГОЭ (FORMULAS.md §5, REVERSE_GOE_MODEL §3): κ(λ) = κ0 + κ1·(λ − λ0) и C_eff(λ) = κ(λ)·C (по умолчанию — пин GTIE00, domain.calculations.GOE_KAPPA_LAW) | `wl`, `k0`, `k1`, `wl0`, `curvature_c` | {wl, k0, k1, wl0, kappa, curvature_c, c_eff, r_eff_mm} |
| [`calc.goe.radius`](#calcgoeradius) | ГЮЭ-радиус поверхности (годная область установки лучей) на длине волны | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `wl` | {index, glass, radius} |
| [`calc.goe.replay`](#calcgoereplay) | Replay-условие ГОЭ (FORMULAS.md §5): фаза решётки на длине волны расчёта δ = rec₀·λ₀/λ — дифракционная добавка ∝ λ0/λ (REVERSE_GOE_MODEL: отклонение ±0.1342 = rec[0]·λ0/λ у GTIE00) | `rec0`, `wl`, `lambda0` | {rec0, lambda0, wl, delta} |
| [`calc.goe.table`](#calcgoetable) | ГЮЭ-радиусы всех поверхностей системы | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {wl, rows: [{index, glass, radius, semi_diameter}]} |
| [`calc.lagrange`](#calclagrange) | Инвариант Лагранжа-Гельмгольца H = n·(D/2)·tg ω_max (n=1, воздух) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {H, epd_mm, max_field, wl} |
| [`calc.magnification`](#calcmagnification) | Увеличение системы V и продольный масштаб L (параксиальный расчёт) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {V, L} |
| [`calc.n`](#calcn) | Показатель преломления стекла на длине волны (все каталоги: ГОСТ/.FIL/AGF) | `glass`, `wl` | {name, source, wl, n} |
| [`calc.opl`](#calcopl) | Оптическая длина пути Σ nᵢ·Lᵢ по участкам | `segments` | {segments, total_opl_mm} |
| [`calc.paraxial`](#calcparaxial) | Параксиальный расчёт: кардинальные отрезки, зрачки, f/# | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | словарь paraxial_trace (focal_length, sF/sF', sP/sP', ...) |
| [`calc.paraxial.multi_wl`](#calcparaxialmulti_wl) | Параксиальный расчёт для каждой рабочей λ системы | `file`, `system`, `lbo_index`, `lbo_name` | список результатов paraxial_trace (ключ 'wl' в каждом) |
| [`calc.power.surface`](#calcpowersurface) | Сила сферической поверхности Φ = (n₂−n₁)/R, дптр | `n1`, `n2`, `radius` | {n1, n2, radius, power_dpt} |
| [`calc.power.table`](#calcpowertable) | Силы поверхностей системы Φᵢ = (nᵢ₊₁−nᵢ)/Rᵢ по стёклам (n воздуха = 1) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {wl, rows: [{index, n_before, n_after, radius, power_dpt}]} |
| [`calc.power.thin_lens`](#calcpowerthin_lens) | Тонкая линза: 1/f′ = (n−1)(1/r₁ − 1/r₂) | `n`, `r1`, `r2` | {n, r1, r2, f_prime, power_dpt} |
| [`calc.pupil.zone`](#calcpupilzone) | Зрачковые координаты зоны (FORMULAS.md §3, REVERSE_NZR): дальний предмет H ЗР = зона·Ax (мм); ближний предмет H = 100·tg(arcsin(зона·NA)) в единицах tg×100 | `zones`, `ax_mm`, `na` | {ax_mm, na, rows: [{zone, h_far_mm, h_near_tg100}]} |
| [`calc.pupils`](#calcpupils) | Зрачки системы: входной/выходной (положения от первой/последней поверхности, диаметры, увеличения) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {sP, sP_prime, entrance_diameter, magnifications} |
| [`calc.sagitta`](#calcsagitta) | Сагитта поверхности на высоте (сфера/коника) | `radius`, `height`, `conic_constant` | {radius, height, conic_constant, sag} |
| [`calc.sagitta.table`](#calcsagittatable) | Сагитты поверхностей системы на заданных высотах | `file`, `system`, `lbo_index`, `lbo_name`, `heights` | {rows: [{index, radius, height, sag}], heights} |
| [`calc.seidel`](#calcseidel) | Суммы Зейделя 3-го порядка: SI..SV | `file`, `system`, `lbo_index`, `lbo_name` | словарь {SI, SII, SIII, SIV, SV} |
| [`calc.semi_effective`](#calcsemi_effective) | Эффективный полудиаметр (острая кромка срезает 2% запас на фаску) | `semi_diameter`, `sharp_edge` | {semi_diameter, sharp_edge, effective} |
| [`calc.tgprime.label`](#calctgprimelabel) | Метка Tg′×100 таблицы TABOC2 (FORMULAS.md §3): дальнее изображение — \|H′ ЗР\| в мм; ближнее — −100·tg u′ (единицы tg′×100) | `h_out_mm`, `u_prime_deg` | {h_out_mm, u_prime_deg, far_label_mm, near_label_tg100} |
| [`calc.vignetting.apply`](#calcvignettingapply) | Виньетируется ли луч (высоты ray_y/ray_x, мм, на первой поверхности) на поле field_y | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `ray_y`, `ray_x`, `sharp_edge` | {field_y, ray_y, ray_x, vignetted, passes} |
| [`calc.virtual.kappa`](#calcvirtualkappa) | Кривизна опорной сферы волновых мнимого изображения (FORMULAS.md §2, GFIX R1): (κ0, κ2) для λ из банка VIRTUAL_WAVE_KAPPA + радиус якоря 1/κ0 | `wl` | {wl, system, kappa0, kappa2, r_ref_mm, available_wls} |

## Параметры и результаты

### calc.aber.dioptre

Продольная аберрация в диоптриях от плоскости ВЫХОДНОГО ЗРАЧКА: дптр = 1000/L′_зоны − 1000/L′_паракс (FORMULAS.md §3, GVERIFY §2.2; L′=0 → пустая ячейка печати OPAL — null)

**Returns:** {L_zone_mm, L_parax_mm, zone_dpt, parax_dpt, dioptres}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `L_zone_mm` | `float` | да | `null` | — | отрезок зонального луча от выходного зрачка, мм |
| `L_parax_mm` | `float` | да | `null` | — | параксиальный отрезок от выходного зрачка, мм |

### calc.aber.grminsec

Поперечная аберрация в мере «гр.мнсек»: угол atan2(Δy, L′) из ЦЕНТРА выходного зрачка на точку луча в плоскости Гаусса + печать DD.MMSS (FORMULAS.md §3, OPALDIS OD3)

**Returns:** {dy_mm, L_mm, angle_deg, grminsec, print}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `dy_mm` | `float` | да | `null` | — | поперечная аберрация Δy, мм |
| `L_mm` | `float` | да | `null` | — | отрезок от центра выходного зрачка, мм |

### calc.airy

Дифракционный диск Эйри: d = 2·1.22·λ·F/#

**Returns:** {f_number, wl, radius_um, diameter_um}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `f_number` | `float` | да | `null` | — | диафрагменное число |
| `wl` | `float` | — | `0.54607` | — | длина волны, мкм |

### calc.aperture.na

Числовые апертуры: в пространстве изображений NA′ = D/(2f′) и предмета NA = NA′·\|V\|

**Returns:** {na_image, na_object, f_number}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.aperture.real

Реальный диаметр осевого пучка по полудиаметрам поверхностей

**Returns:** диаметр (мм) или null — если полудиаметры не заданы

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `sharp_edge` | `bool` | — | `true` | — | виньетирование по острому краю (без скругления) |

### calc.beam_geometry

Габариты пучков по полям: апертуры, виньетирование, светораспределение

**Returns:** список результатов по точкам поля

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `semi_mode` | `str` | — | `"given"` | `["given", "real"]` | режим: given — по заданной апертуре, real — по полудиаметрам поверхностей |
| `sharp_edge` | `bool` | — | `true` | — | виньетирование по острому краю |

### calc.cardinals

Кардинальные точки: фокусы F/F′, главные плоскости H/H′, фокусные расстояния

**Returns:** {f, f_prime, sF, sF_prime, sH, sH_prime, back_focal_distance, front_focal_distance}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.conjugate.solve

Сопряжённые отрезки (формула отрезков, 1/s′ − 1/s = 1/f′): по s → s′, V; или по V → s

**Returns:** {f_prime, s, s_prime, V}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `f_override` | `float` | — | `null` | — | f′ явно, мм (по умолчанию — параксиал системы) |
| `s` | `float` | — | `null` | — | отрезок предмета от H, мм (s<0 — реальный предмет) |
| `V_target` | `float` | — | `null` | — | искомое увеличение (знак — инверсия изображения) |

### calc.defocus.convert

Конверсия дефокуса мм ↔ волны на краю зрачка: W = PARAXIAL_DEFOCUS_FACTOR·Δz·NA′²/λ (формула analysis/advanced.compute_psf; хелпер П14 — adv_ext_cmds._defocus_waves_per_mm)

**Returns:** {wl, na_image, waves_per_mm, defocus_mm, waves}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `defocus_mm` | `float` | — | `null` | — | осевой сдвиг плоскости, мм |
| `waves` | `float` | — | `null` | — | дефокус на краю зрачка, волны |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.depth.criteria

Границы глубины резко изображаемого пространства по допускам критериев (ANALIZE §5.3: «положения индивидуальных границ глубины резкости из условия, чтобы не превышать максимально допустимых значений СКW (СКR)»): скан дефокуса, интервал где критерий ≤ допуска

**Returns:** {criterion, max_value, unit, wl, field_y, defocus_range, steps, waves_per_mm, best_focus_mm, min_value, near_mm, far_mm, depth_mm, satisfied, clipped_near, clipped_far, rows: [{defocus_mm, value}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `criterion` | `str` | да | `null` | `["wave_rms", "spot_rms"]` | СКW (wave_rms, допуск в λ) или СКR (spot_rms, допуск в мм) |
| `max_value` | `float` | да | `null` | — | максимально допустимое значение критерия |
| `defocus_range` | `float` | — | `null` | — | полудиапазон скана, мм (по умолчанию 1.0 для пятна, 0.3 для волнового) |
| `steps` | `int` | — | `21` | — | точек скана ≥ 3 (нечётное) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `num_rays` | `int` | — | `64` | — | лучей пятна (СКR) |
| `grid_size` | `int` | — | `32` | — | решётка зрачка (СКW) |

### calc.depth_of_field

ГРИП (геометрическая): ±Δ = c·F/#·(1+m), полная глубина 2Δ

**Returns:** {f_number, coc_um, magnification, plus_minus_mm, total_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `f_number` | `float` | да | `null` | — | диафрагменное число |
| `coc_um` | `float` | да | `null` | — | круг нерезкости, мкм |
| `magnification` | `float` | — | `0.0` | — | увеличение (макро-режим) |

### calc.diffraction.cutoff

Дифракционный срез ЧКХ: ν_c = 1/(λ·F/#), лин/мм

**Returns:** {f_number, wl, cutoff_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `f_number` | `float` | да | `null` | — | диафрагменное число |
| `wl` | `float` | — | `0.54607` | — | длина волны, мкм |

### calc.edge2.lambda

Множитель печати λ(z) = 1 − (q0 + q1·z²)·z² ближнего предмета E2 (FORMULAS.md §3, REVERSE_OPALDIS §4.3(vii); q-пары банка — analysis.aberrations.EDGE2_PRINT_LAMBDA, верифицировано золотыми прогонами)

**Returns:** {system, kind, q0, q1, rows: [{zone, lambda}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `system` | `str` | да | `null` | `["OBEKTIV", "OKULAR", "OPTICS#1"]` | система банка E2 |
| `kind` | `str` | да | `null` | `["прод", "попер", "Tg"]` | семейство печати (прод/попер/Tg) |
| `zones` | `list` | да | `null` | — | зоны зрачка z (доли полуапертуры) |

### calc.fan.launch

Запуск лучей осевого веера (FORMULAS.md §3, GFIX P6): дальний предмет — по высоте зона·Ax параллельно оси; ближний — по углу arcsin(зона·NA) от точки предмета (Ax = sin NA)

**Returns:** {ax_mm, na, rows: [{zone, far_y_mm, near_u_deg}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `zones` | `list` | да | `null` | — | зоны зрачка (доли полуапертуры) |
| `ax_mm` | `float` | — | `null` | — | полувысота зрачка Ax, мм (дальний предмет) |
| `na` | `float` | — | `null` | — | числовая апертура предмета (ближний предмет) |

### calc.goe.kappa

Закон эффективной кривизны ГОЭ (FORMULAS.md §5, REVERSE_GOE_MODEL §3): κ(λ) = κ0 + κ1·(λ − λ0) и C_eff(λ) = κ(λ)·C (по умолчанию — пин GTIE00, domain.calculations.GOE_KAPPA_LAW)

**Returns:** {wl, k0, k1, wl0, kappa, curvature_c, c_eff, r_eff_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `wl` | `float` | да | `null` | — | длина волны расчёта, мкм |
| `k0` | `float` | — | `null` | — | κ_design (по умолчанию — пин GTIE00) |
| `k1` | `float` | — | `null` | — | dκ/dλ, 1/мкм (по умолчанию — пин GTIE00) |
| `wl0` | `float` | — | `null` | — | λ записи, мкм (по умолчанию — пин GTIE00) |
| `curvature_c` | `float` | — | `null` | — | кривизна поверхности C, 1/мм (для C_eff и R_eff) |

### calc.goe.radius

ГЮЭ-радиус поверхности (годная область установки лучей) на длине волны

**Returns:** {index, glass, radius}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс поверхности (0-based) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.goe.replay

Replay-условие ГОЭ (FORMULAS.md §5): фаза решётки на длине волны расчёта δ = rec₀·λ₀/λ — дифракционная добавка ∝ λ0/λ (REVERSE_GOE_MODEL: отклонение ±0.1342 = rec[0]·λ0/λ у GTIE00)

**Returns:** {rec0, lambda0, wl, delta}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `rec0` | `float` | да | `null` | — | записанная фаза решётки rec₀ (на λ0) |
| `wl` | `float` | да | `null` | — | длина волны расчёта, мкм |
| `lambda0` | `float` | — | `0.6328` | — | λ записи, мкм (по умолчанию HeNe 0.6328) |

### calc.goe.table

ГЮЭ-радиусы всех поверхностей системы

**Returns:** {wl, rows: [{index, glass, radius, semi_diameter}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.lagrange

Инвариант Лагранжа-Гельмгольца H = n·(D/2)·tg ω_max (n=1, воздух)

**Returns:** {H, epd_mm, max_field, wl}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.magnification

Увеличение системы V и продольный масштаб L (параксиальный расчёт)

**Returns:** {V, L}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.n

Показатель преломления стекла на длине волны (все каталоги: ГОСТ/.FIL/AGF)

**Returns:** {name, source, wl, n}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `glass` | `str` | да | `null` | — | марка стекла |
| `wl` | `float` | — | `0.58756` | — | длина волны, мкм |

### calc.opl

Оптическая длина пути Σ nᵢ·Lᵢ по участкам

**Returns:** {segments, total_opl_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `segments` | `list` | да | `null` | — | список [{n, length}] (длина, мм) |

### calc.paraxial

Параксиальный расчёт: кардинальные отрезки, зрачки, f/#

**Returns:** словарь paraxial_trace (focal_length, sF/sF', sP/sP', ...)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ системы) |

### calc.paraxial.multi_wl

Параксиальный расчёт для каждой рабочей λ системы

**Returns:** список результатов paraxial_trace (ключ 'wl' в каждом)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### calc.power.surface

Сила сферической поверхности Φ = (n₂−n₁)/R, дптр

**Returns:** {n1, n2, radius, power_dpt}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `n1` | `float` | да | `null` | — | n среды до поверхности |
| `n2` | `float` | да | `null` | — | n среды после поверхности |
| `radius` | `float` | да | `null` | — | радиус, мм (0 — плоскость, Φ=0) |

### calc.power.table

Силы поверхностей системы Φᵢ = (nᵢ₊₁−nᵢ)/Rᵢ по стёклам (n воздуха = 1)

**Returns:** {wl, rows: [{index, n_before, n_after, radius, power_dpt}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.power.thin_lens

Тонкая линза: 1/f′ = (n−1)(1/r₁ − 1/r₂)

**Returns:** {n, r1, r2, f_prime, power_dpt}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `n` | `float` | да | `null` | — | n материала |
| `r1` | `float` | да | `null` | — | первый радиус, мм (0 — плоскость) |
| `r2` | `float` | да | `null` | — | второй радиус, мм (0 — плоскость) |

### calc.pupil.zone

Зрачковые координаты зоны (FORMULAS.md §3, REVERSE_NZR): дальний предмет H ЗР = зона·Ax (мм); ближний предмет H = 100·tg(arcsin(зона·NA)) в единицах tg×100

**Returns:** {ax_mm, na, rows: [{zone, h_far_mm, h_near_tg100}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `zones` | `list` | да | `null` | — | зоны зрачка (доли полуапертуры) |
| `ax_mm` | `float` | — | `null` | — | полувысота зрачка Ax, мм (дальний предмет) |
| `na` | `float` | — | `null` | — | числовая апертура предмета (ближний предмет) |

### calc.pupils

Зрачки системы: входной/выходной (положения от первой/последней поверхности, диаметры, увеличения)

**Returns:** {sP, sP_prime, entrance_diameter, magnifications}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### calc.sagitta

Сагитта поверхности на высоте (сфера/коника)

**Returns:** {radius, height, conic_constant, sag}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `radius` | `float` | да | `null` | — | радиус, мм (0 — плоскость) |
| `height` | `float` | да | `null` | — | высота от оси, мм |
| `conic_constant` | `float` | — | `0.0` | — | коническая постоянная k |

### calc.sagitta.table

Сагитты поверхностей системы на заданных высотах

**Returns:** {rows: [{index, radius, height, sag}], heights}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `heights` | `list` | да | `null` | — | высоты от оси, мм |

### calc.seidel

Суммы Зейделя 3-го порядка: SI..SV

**Returns:** словарь {SI, SII, SIII, SIV, SV}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### calc.semi_effective

Эффективный полудиаметр (острая кромка срезает 2% запас на фаску)

**Returns:** {semi_diameter, sharp_edge, effective}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `semi_diameter` | `float` | да | `null` | — | полудиаметр, мм |
| `sharp_edge` | `bool` | — | `true` | — | острая кромка (влияет на эффективный размер) |

### calc.tgprime.label

Метка Tg′×100 таблицы TABOC2 (FORMULAS.md §3): дальнее изображение — \|H′ ЗР\| в мм; ближнее — −100·tg u′ (единицы tg′×100)

**Returns:** {h_out_mm, u_prime_deg, far_label_mm, near_label_tg100}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `h_out_mm` | `float` | — | `null` | — | высота зонального луча в выходном зрачке, мм (дальний тип изображения) |
| `u_prime_deg` | `float` | — | `null` | — | выходной наклон зонального луча u′, град (ближний тип изображения) |

### calc.vignetting.apply

Виньетируется ли луч (высоты ray_y/ray_x, мм, на первой поверхности) на поле field_y

**Returns:** {field_y, ray_y, ray_x, vignetted, passes}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле |
| `ray_y` | `float` | да | `null` | — | высота луча, мм |
| `ray_x` | `float` | — | `0.0` | — | саг. высота луча, мм |
| `sharp_edge` | `bool` | — | `true` | — | острая кромка |

### calc.virtual.kappa

Кривизна опорной сферы волновых мнимого изображения (FORMULAS.md §2, GFIX R1): (κ0, κ2) для λ из банка VIRTUAL_WAVE_KAPPA + радиус якоря 1/κ0

**Returns:** {wl, system, kappa0, kappa2, r_ref_mm, available_wls}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `wl` | `float` | да | `null` | — | длина волны, мкм (допуск банка 2e-3) |

