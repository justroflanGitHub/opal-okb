# Категория aberx

22 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`aberx.aperture.aberrations`](#aberxapertureaberrations) | Апертурная зависимость аберраций: краевая поперечная dy(±1) и продольная LA края меридионального веера при разных диаметрах входного зрачка + отношение dy/D³ (сферическая ∝ D³) | `file`, `system`, `lbo_index`, `lbo_name`, `apertures`, `field_y`, `num_rays`, `wl` | {wl, field_y, num_rays, rows: [{epd_mm, dy_plus_edge_um, dy_minus_edge_um, la_edge_mm, dy_over_d3}]} |
| [`aberx.astig.curve`](#aberxastigcurve) | Кривая астигматизма по полям: отрезки Z'm/Z's следа Коддингтона (мм от плоскости Гаусса), разность Z'm−Z's, худшее поле | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl` | {wl, rows: [{field_y, delta_zm, delta_zs, astigmatism, t_m, t_s}], worst: {field_y, astigmatism} \| null} |
| [`aberx.bestfocus.fields`](#aberxbestfocusfields) | Наилучший дефокус (минимум RMS пятна) по полям и λ + хроматический сдвиг лучшего фокуса между крайними λ (полевая кривизна пятна и её хроматизм) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wls`, `num_rays`, `defocus_range`, `num_points` | {defocus_range, num_points, rows: [{field_y, wl, best_defocus_mm, min_rms_mm, rms_at_zero_mm, best_at_boundary}], by_field: [{field_y, chrom_shift_mm}]} |
| [`aberx.centroid.fields`](#aberxcentroidfields) | Boresight по полям: положение центроида пятна против главного луча и параксиальной высоты — смещение энергетического центра, абсолютная дисторсия главного луча | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `wl` | {wl, num_rays, rows: [{field_y, chief_x_mm, chief_y_mm, centroid_x_mm, centroid_y_mm, centroid_shift_um, y_parax_mm, dist_abs_mm, dist_pct}]} |
| [`aberx.chrom.focus_shift`](#aberxchromfocus_shift) | Осевой хроматизм: параксиальные EFL/BFD по каждой рабочей λ, сдвиги относительно основной λ и полный разброс (вторичный спектр, мм) | `file`, `system`, `lbo_index`, `lbo_name`, `wls` | {wl_ref, rows: [{wl, efl_mm, bfd_mm, d_efl_mm, d_bfd_mm}], efl_spread_mm, bfd_spread_mm} |
| [`aberx.chrom.magnification`](#aberxchrommagnification) | Хроматизм увеличения: высота главного луча по λ на каждом поле, сдвиг dy против основной λ, относительное увеличение и поперечный хроматизм по полю | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wls` | {wl_ref, rows: [{field_y, wl, y_chief_mm, dy_vs_ref_mm, magnification_rel}], by_field: [{field_y, lateral_color_mm, lateral_color_pct}]} |
| [`aberx.coma.fan`](#aberxcomafan) | Кома-веер по зонам зрачка на поле: асимметрия меридионального веера dy(+ρ)+dy(−ρ), тангенциальная кома (край) и сагиттальная (из наклонного хода сагиттального веера), отношение T/S (3-й порядок: 3) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `num_rays`, `wl` | {wl, field_y, num_rays, rows: [{rho, dy_plus_um, dy_minus_um, asym_um}], tangential_coma_um, sagittal_coma_um, ratio_t_over_s, ratio_t_over_s_3rd_order} |
| [`aberx.coma.fields`](#aberxcomafields) | Кривая комы по полям: тангенциальная кома (dy(+1)+dy(−1) меридионального веера) и сагиттальная (край сагиттального веера) по полям, мкм | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `wl` | {wl, num_rays, rows: [{field_y, t_coma_um, s_coma_um, ratio_t_over_s}]} |
| [`aberx.distortion.curve`](#aberxdistortioncurve) | Кривая дисторсии по полям: высота главного луча, гауссова высота, абсолютная/относительная дисторсия + полиномиальный фит dist(f) с максимальной невязкой | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `fit_degree`, `wl` | {wl, efl, rows: [{field_y, y_chief_mm, y_parax_mm, dist_abs_mm, dist_pct}], fit: {degree, coeffs, resid_max_pct} \| null} |
| [`aberx.fan.chrom`](#aberxfanchrom) | Веер сечения по ВСЕМ λ системы на поле: dy меридиональная/сагиттальная (мкм, относительно главного луча) по зонам ρ и сводка по λ | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wls`, `num_rays`, `azimuth_deg` | {field_y, azimuth_deg, rows: [{wl, rho, dy_mer_um, dy_sag_um}], by_wl: [{wl, rms_dy_mer_um, max_abs_dy_mer_um}]} |
| [`aberx.focal.zonal`](#aberxfocalzonal) | Зонные фокусы Z(±ρ) тангенциальной и сагиттальной плоскостей на поле: пересечения лучей зон с главным лучом (диагностика каустик) — данные фокальных поверхностей по зонам | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `zones`, `wl` | {wl, field_y, z_m0, z_s0, rows: [{rho, z_m_plus, z_m_minus, z_m_mid, z_s_plus, z_s_minus, z_s_mid}]} |
| [`aberx.longitudinal.fields`](#aberxlongitudinalfields) | Продольные отрезки крайних лучей по полям: Z, где верхний/нижний крайние меридиональные лучи догоняют высоту главного луча, средний сдвиг относительно плоскости изображения и разброс | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl` | {wl, rows: [{field_y, z_upper_mm, z_lower_mm, mean_shift_mm, spread_mm}]} |
| [`aberx.map.grid`](#aberxmapgrid) | Карта поперечных аберраций поле×зона: матрица dy меридионального и сагиттального сечений по зонам зрачка (мкм, относительно главного луча) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `wl` | {wl, num_rays, rows: [{field_y, rho, dy_mer_um, dy_sag_um}], by_field: [{field_y, rms_dy_mer_um, max_dy_mer_um, rms_dy_sag_um, max_dy_sag_um, failed}]} |
| [`aberx.petzval.check`](#aberxpetzvalcheck) | Кривизна поля Петцваля из хода: поверхность Петцваля z_p = (3·Z's − Z'm)/2 по полям (третий порядок: танг. = z_p + 3A/2, саг. = z_p + A/2), эмпирический радиус из фита z_p ≈ z₀ + y²/(2R) против −1/SIV сумм Зейделя | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl` | {wl, rows: [{field_y, y_img_mm, z_petzval}], petzval_radius_empirical_mm, petzval_radius_seidel_mm, SIV, deviation_pct} \| null-поля при нехватке поля |
| [`aberx.rms.grid`](#aberxrmsgrid) | Решётка «поле × λ → СКВ волновой аберрации» (гексаполярная сетка зрачка, СКВ от среднего по зрачку, в длинах волн) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wls`, `num_rings` | {rows: [{field_y, wl, rms_wl, n_points}]} |
| [`aberx.seidel.shares`](#aberxseidelshares) | Вклады отдельных поверхностей в суммы Зейделя SI..SV + хроматические SIхр/SIIхр: абсолютные значения и процентные доли (паритет итогов с seidel.sums проверяется) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {wl, rows: [{n, glass, radius, SI, SI_share_pct, SII, ..., SIIxp_share_pct}], totals, parity_ok} |
| [`aberx.spherical.zones`](#aberxsphericalzones) | Продольная сферическая аберрация по зонам зрачка (осевое поле): поперечная dy и продольная ds (z-пересечение луча зоны с осью — классическая LA) + фит ds ≈ c₂·ρ² + c₄·ρ⁴, отрезки LA края и зоны 0.707 | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `num_rays`, `wl` | {wl, field_y, num_rays, rows: [{rho, dy_um, ds_mm}], fit: {coeffs: [c2, c4], resid_max_mm} \| null, la_edge_mm, la_zonal_mm} |
| [`aberx.spot.grid`](#aberxspotgrid) | Решётка пятен поле×λ: RMS общий и раздельно по меридиональной/сагиттальной осям, отношение осей, центроид (числа, не картинка) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wls`, `num_rays` | {num_rays, rows: [{field_y, wl, n_points, rms_total_mm, rms_x_mm, rms_y_mm, rms_y_over_x, centroid_x_mm, centroid_y_mm}]} |
| [`aberx.transverse.zones`](#aberxtransversezones) | Таблица поперечных аберраций заданного поля по зонам зрачка равной площади (1, √((n−1)/n), ...): dy меридионального и сагиттального сечений, мкм относительно главного луча | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `n_zones`, `zones`, `wl` | {wl, field_y, chief: [x, y], rows: [{rho, dy_mer_um, dy_sag_um, mer_success, sag_success}]} |
| [`aberx.wf.chrom`](#aberxwfchrom) | Хроматическая волновая разность dW(λ): волновой фронт на гексаполярной сетке для каждой λ против основной λ в тех же точках зрачка (длины волн) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wls`, `num_rings` | {wl_ref, num_rings, rows: [{wl, dW_rms, dW_pv, n_points, points: [[px, py, dW], ...]}]} |
| [`aberx.wf.pv`](#aberxwfpv) | Пик-валлей волновой аберрации по полям: min/max/W_pv/среднее/СКВ на гексаполярной сетке зрачка + худшее поле по PV | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rings`, `wl` | {wl, num_rings, rows: [{field_y, w_min, w_max, pv, mean, rms, n_points}], worst_field, worst_pv} |
| [`aberx.wf.rho`](#aberxwfrho) | Меридиональная волновая аберрация W(ρ) по полям: карта поле×зона (W в длинах волн, ноль отсчёта — главный луч, опорная сфера в параксиальном фокусе) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `wl` | {wl, num_rays, rows: [{field_y, rho, wave}], by_field: [{field_y, pv, rms, n_points}]} |

## Параметры и результаты

### aberx.aperture.aberrations

Апертурная зависимость аберраций: краевая поперечная dy(±1) и продольная LA края меридионального веера при разных диаметрах входного зрачка + отношение dy/D³ (сферическая ∝ D³)

**Returns:** {wl, field_y, num_rays, rows: [{epd_mm, dy_plus_edge_um, dy_minus_edge_um, la_edge_mm, dy_over_d3}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `apertures` | `list` | да | `null` | — | диаметры входного зрачка, мм (≥2 значащих) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `num_rays` | `int` | — | `9` | — | лучей веера (≥3; по умолчанию 9) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.astig.curve

Кривая астигматизма по полям: отрезки Z'm/Z's следа Коддингтона (мм от плоскости Гаусса), разность Z'm−Z's, худшее поле

**Returns:** {wl, rows: [{field_y, delta_zm, delta_zs, astigmatism, t_m, t_s}], worst: {field_y, astigmatism} \| null}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.bestfocus.fields

Наилучший дефокус (минимум RMS пятна) по полям и λ + хроматический сдвиг лучшего фокуса между крайними λ (полевая кривизна пятна и её хроматизм)

**Returns:** {defocus_range, num_points, rows: [{field_y, wl, best_defocus_mm, min_rms_mm, rms_at_zero_mm, best_at_boundary}], by_field: [{field_y, chrom_shift_mm}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wls` | `list` | — | `null` | — | список λ, мкм; по умолчанию — только основная |
| `num_rays` | `int` | — | `15` | — | лучей по стороне сетки |
| `defocus_range` | `float` | — | `3.0` | — | ± мм скана (по умолчанию 3.0) |
| `num_points` | `int` | — | `9` | — | точек скана (по умолчанию 9) |

### aberx.centroid.fields

Boresight по полям: положение центроида пятна против главного луча и параксиальной высоты — смещение энергетического центра, абсолютная дисторсия главного луча

**Returns:** {wl, num_rays, rows: [{field_y, chief_x_mm, chief_y_mm, centroid_x_mm, centroid_y_mm, centroid_shift_um, y_parax_mm, dist_abs_mm, dist_pct}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `15` | — | лучей по стороне сетки |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.chrom.focus_shift

Осевой хроматизм: параксиальные EFL/BFD по каждой рабочей λ, сдвиги относительно основной λ и полный разброс (вторичный спектр, мм)

**Returns:** {wl_ref, rows: [{wl, efl_mm, bfd_mm, d_efl_mm, d_bfd_mm}], efl_spread_mm, bfd_spread_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wls` | `list` | — | `null` | — | список λ, мкм; по умолчанию — рабочие λ системы |

### aberx.chrom.magnification

Хроматизм увеличения: высота главного луча по λ на каждом поле, сдвиг dy против основной λ, относительное увеличение и поперечный хроматизм по полю

**Returns:** {wl_ref, rows: [{field_y, wl, y_chief_mm, dy_vs_ref_mm, magnification_rel}], by_field: [{field_y, lateral_color_mm, lateral_color_pct}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wls` | `list` | — | `null` | — | список λ, мкм; по умолчанию — рабочие λ системы |

### aberx.coma.fan

Кома-веер по зонам зрачка на поле: асимметрия меридионального веера dy(+ρ)+dy(−ρ), тангенциальная кома (край) и сагиттальная (из наклонного хода сагиттального веера), отношение T/S (3-й порядок: 3)

**Returns:** {wl, field_y, num_rays, rows: [{rho, dy_plus_um, dy_minus_um, asym_um}], tangential_coma_um, sagittal_coma_um, ratio_t_over_s, ratio_t_over_s_3rd_order}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле (град / мм) |
| `num_rays` | `int` | — | `9` | — | лучей веера (≥3; по умолчанию 9) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.coma.fields

Кривая комы по полям: тангенциальная кома (dy(+1)+dy(−1) меридионального веера) и сагиттальная (край сагиттального веера) по полям, мкм

**Returns:** {wl, num_rays, rows: [{field_y, t_coma_um, s_coma_um, ratio_t_over_s}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `9` | — | лучей веера (≥3; по умолчанию 9) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.distortion.curve

Кривая дисторсии по полям: высота главного луча, гауссова высота, абсолютная/относительная дисторсия + полиномиальный фит dist(f) с максимальной невязкой

**Returns:** {wl, efl, rows: [{field_y, y_chief_mm, y_parax_mm, dist_abs_mm, dist_pct}], fit: {degree, coeffs, resid_max_pct} \| null}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `fit_degree` | `int` | — | `3` | — | степень полинома дисторсии (по умолчанию 3) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.fan.chrom

Веер сечения по ВСЕМ λ системы на поле: dy меридиональная/сагиттальная (мкм, относительно главного луча) по зонам ρ и сводка по λ

**Returns:** {field_y, azimuth_deg, rows: [{wl, rho, dy_mer_um, dy_sag_um}], by_wl: [{wl, rms_dy_mer_um, max_abs_dy_mer_um}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле (град / мм) |
| `wls` | `list` | — | `null` | — | список λ, мкм; по умолчанию — рабочие λ системы |
| `num_rays` | `int` | — | `9` | — | лучей веера (≥3; по умолчанию 9) |
| `azimuth_deg` | `float` | — | `0.0` | — | азимут сечения (0 — меридиональное, 90 — сагиттальное) |

### aberx.focal.zonal

Зонные фокусы Z(±ρ) тангенциальной и сагиттальной плоскостей на поле: пересечения лучей зон с главным лучом (диагностика каустик) — данные фокальных поверхностей по зонам

**Returns:** {wl, field_y, z_m0, z_s0, rows: [{rho, z_m_plus, z_m_minus, z_m_mid, z_s_plus, z_s_minus, z_s_mid}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле (град / мм) |
| `zones` | `list` | — | `null` | — | доли зрачка (по умолчанию [0.25, 0.5, 0.75, 1.0]) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.longitudinal.fields

Продольные отрезки крайних лучей по полям: Z, где верхний/нижний крайние меридиональные лучи догоняют высоту главного луча, средний сдвиг относительно плоскости изображения и разброс

**Returns:** {wl, rows: [{field_y, z_upper_mm, z_lower_mm, mean_shift_mm, spread_mm}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.map.grid

Карта поперечных аберраций поле×зона: матрица dy меридионального и сагиттального сечений по зонам зрачка (мкм, относительно главного луча)

**Returns:** {wl, num_rays, rows: [{field_y, rho, dy_mer_um, dy_sag_um}], by_field: [{field_y, rms_dy_mer_um, max_dy_mer_um, rms_dy_sag_um, max_dy_sag_um, failed}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `9` | — | лучей веера в сечении (≥3; по умолчанию 9) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.petzval.check

Кривизна поля Петцваля из хода: поверхность Петцваля z_p = (3·Z's − Z'm)/2 по полям (третий порядок: танг. = z_p + 3A/2, саг. = z_p + A/2), эмпирический радиус из фита z_p ≈ z₀ + y²/(2R) против −1/SIV сумм Зейделя

**Returns:** {wl, rows: [{field_y, y_img_mm, z_petzval}], petzval_radius_empirical_mm, petzval_radius_seidel_mm, SIV, deviation_pct} \| null-поля при нехватке поля

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей (нужно ≥2 внеосевых); по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.rms.grid

Решётка «поле × λ → СКВ волновой аберрации» (гексаполярная сетка зрачка, СКВ от среднего по зрачку, в длинах волн)

**Returns:** {rows: [{field_y, wl, rms_wl, n_points}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wls` | `list` | — | `null` | — | список λ, мкм; по умолчанию — рабочие λ системы |
| `num_rings` | `int` | — | `3` | — | колец гексаполярной сетки (по умолчанию 3) |

### aberx.seidel.shares

Вклады отдельных поверхностей в суммы Зейделя SI..SV + хроматические SIхр/SIIхр: абсолютные значения и процентные доли (паритет итогов с seidel.sums проверяется)

**Returns:** {wl, rows: [{n, glass, radius, SI, SI_share_pct, SII, ..., SIIxp_share_pct}], totals, parity_ok}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.spherical.zones

Продольная сферическая аберрация по зонам зрачка (осевое поле): поперечная dy и продольная ds (z-пересечение луча зоны с осью — классическая LA) + фит ds ≈ c₂·ρ² + c₄·ρ⁴, отрезки LA края и зоны 0.707

**Returns:** {wl, field_y, num_rays, rows: [{rho, dy_um, ds_mm}], fit: {coeffs: [c2, c4], resid_max_mm} \| null, la_edge_mm, la_zonal_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм); осевое — 0 |
| `num_rays` | `int` | — | `9` | — | лучей веера (≥3; по умолчанию 9) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.spot.grid

Решётка пятен поле×λ: RMS общий и раздельно по меридиональной/сагиттальной осям, отношение осей, центроид (числа, не картинка)

**Returns:** {num_rays, rows: [{field_y, wl, n_points, rms_total_mm, rms_x_mm, rms_y_mm, rms_y_over_x, centroid_x_mm, centroid_y_mm}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wls` | `list` | — | `null` | — | список λ, мкм; по умолчанию — рабочие λ системы |
| `num_rays` | `int` | — | `15` | — | лучей по стороне сетки (по умолчанию 15) |

### aberx.transverse.zones

Таблица поперечных аберраций заданного поля по зонам зрачка равной площади (1, √((n−1)/n), ...): dy меридионального и сагиттального сечений, мкм относительно главного луча

**Returns:** {wl, field_y, chief: [x, y], rows: [{rho, dy_mer_um, dy_sag_um, mer_success, sag_success}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле (град / мм) |
| `n_zones` | `int` | — | `3` | — | зон равной площади (по умолчанию 3) |
| `zones` | `list` | — | `null` | — | явный список зон (доли зрачка, допускаются отрицательные); по умолчанию — зоны равной площади обеих знаков |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.wf.chrom

Хроматическая волновая разность dW(λ): волновой фронт на гексаполярной сетке для каждой λ против основной λ в тех же точках зрачка (длины волн)

**Returns:** {wl_ref, num_rings, rows: [{wl, dW_rms, dW_pv, n_points, points: [[px, py, dW], ...]}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле (град / мм) |
| `wls` | `list` | — | `null` | — | список λ, мкм; по умолчанию — рабочие λ системы |
| `num_rings` | `int` | — | `3` | — | колец гексаполярной сетки зрачка |

### aberx.wf.pv

Пик-валлей волновой аберрации по полям: min/max/W_pv/среднее/СКВ на гексаполярной сетке зрачка + худшее поле по PV

**Returns:** {wl, num_rings, rows: [{field_y, w_min, w_max, pv, mean, rms, n_points}], worst_field, worst_pv}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rings` | `int` | — | `3` | — | колец гексаполярной сетки зрачка |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aberx.wf.rho

Меридиональная волновая аберрация W(ρ) по полям: карта поле×зона (W в длинах волн, ноль отсчёта — главный луч, опорная сфера в параксиальном фокусе)

**Returns:** {wl, num_rays, rows: [{field_y, rho, wave}], by_field: [{field_y, pv, rms, n_points}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `9` | — | лучей веера (≥3; по умолчанию 9) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

