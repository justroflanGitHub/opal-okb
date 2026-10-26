# Категория plot

23 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`plot.caustic`](#plotcaustic) | Каустика (PNG): выходящие участки лучей веера за последней поверхностью до z(изображение)+range и ширина пучка RMS(z) — перетяжка/положение фокуса | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `field_y`, `num_rays`, `defocus_range`, `num_points` | {output, size_bytes, wl, field_y, num_rays, num_ok, paraxial_focus_mm, waist_z_mm, min_rms_mm} |
| [`plot.chromatism`](#plotchromatism) | Хроматизм (PNG): f′(λ) по сетке длин волн и осевой хроматизм Δf′(λ) относительно основной λ; рабочие λ системы — метками | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `steps` | {output, size_bytes, primary_wl, fprime_primary_mm, wl_grid, fprimes_mm, dfprime_at_system_wl} |
| [`plot.dof`](#plotdof) | Глубина фокуса (PNG): RMS и геометрический радиус пятна против смещения плоскости изображения; зона, где радиус ≤ круга нерезкости, — глубина резкости | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `field_y`, `coc_um`, `defocus_range`, `num_points`, `num_rays` | {output, size_bytes, wl, field_y, coc_um, best_defocus_mm, best_rms_mm, near_mm, far_mm, depth_mm} |
| [`plot.ee`](#plotee) | Функция концентрации энергии (PNG): доля энергии ФРТ в круге радиуса r | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `field_y`, `wl` | {output, size_bytes, r80_um} |
| [`plot.ee.family`](#ploteefamily) | Семейство функций концентрации энергии по полям (PNG) с метрикой r₈₀ | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `fields`, `wl` | {output, size_bytes, wl, rows: [{field_y, r80_um}]} |
| [`plot.fan`](#plotfan) | Веер лучей (PNG): поперечная dy и продольная ds аберрации против зрачковой координаты | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `field_y`, `num_rays` | {output, size_bytes, num_rays, num_ok} |
| [`plot.fan.fields`](#plotfanfields) | Веера поперечных аберраций dy по полям (PNG): кривые dy(зрачковая координата) всех полей на одном поле графика | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `fields`, `wl`, `num_fan_rays` | {output, size_bytes, wl, num_fan_rays, fields, num_ok} |
| [`plot.field`](#plotfield) | Внеосевые аберрации по полю (PNG): астигматизм Z'm/Z's и дисторсия | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `fields`, `num_fan_rays` | {output, size_bytes, fields} |
| [`plot.fields`](#plotfields) | Карта точек поля системы (PNG): (x, y) с весами и окружностью максимального поля | `file`, `system`, `lbo_index`, `lbo_name`, `output` | {output, size_bytes, num_fields, max_field, fields} |
| [`plot.focus`](#plotfocus) | Фокусировочная кривая (PNG): MTF на заданной частоте против смещения плоскости изображения | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `field_y`, `defocus_range`, `freq_lpmm`, `num_points`, `num_rays` | {output, size_bytes, best_defocus_mm, num_points} |
| [`plot.glassmap`](#plotglassmap) | Стёкла системы на карте стёкол nd–vd (PNG): каталог ГОСТ фоном, стёкла системы — ломаной «траектории коррекции» по ходу поверхностей (данные — diagram.glasses) | `file`, `system`, `lbo_index`, `lbo_name`, `output` | {output, size_bytes, glasses, skipped, num_catalog} |
| [`plot.heatmap`](#plotheatmap) | Топограмма плотности пятна рассеяния (PNG): гистограмма точек в плоскости изображения | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `field_y`, `num_rays`, `grid_size` | {output, size_bytes, x_range, y_range} |
| [`plot.layout`](#plotlayout) | Схема оптической системы с трассировкой лучей (PNG, 2D-разрез): поверхности-дуги, стёкла, стоп, ось, F′ и веера лучей по полям (ANALIZE §4.8) | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `fields`, `num_rays` | {output, size_bytes, num_surfaces, fields, num_rays, num_ok, focal_z_mm} |
| [`plot.mtf`](#plotmtf) | Оптическая передаточная функция (PNG): сечения тангенциальное/сагиттальное из ФРТ | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `field_y`, `wl` | {output, size_bytes, cutoff_lpmm, nyquist_lpmm} |
| [`plot.mtf.family`](#plotmtffamily) | Семейство ЧКХ по полям (PNG): тангенциальное (сплошная) и сагиттальное (пунктир) сечения из ФРТ на одном поле графика | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `fields`, `wl`, `max_freq` | {output, size_bytes, wl, fields, cutoff_lpmm, nyquist_lpmm} |
| [`plot.psf`](#plotpsf) | Функция рассеяния точки (PNG): карта интенсивности в плоскости изображения | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `field_y`, `wl`, `defocus` | {output, size_bytes, strehl, pitch_um} |
| [`plot.psf.slice`](#plotpsfslice) | Срезы ФРТ через центр (PNG): горизонтальный I(x) и вертикальный I(y) профили с шириной FWHM | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `field_y`, `wl`, `defocus` | {output, size_bytes, wl, field_y, defocus, strehl, fwhm_x_um, fwhm_y_um} |
| [`plot.pupil.vign`](#plotpupilvign) | Маска зрачка на поле (PNG): узлы гексаполярной сетки зрачка «прошёл/срезан» (данные — trace.grid3d), границы зрачка и экранирования | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `field_y`, `num_rings`, `num_azimuths`, `wl` | {output, size_bytes, wl, field_y, num_passed, num_blocked, pass_fraction, obscuration_ratio} |
| [`plot.seidel`](#plotseidel) | Суммы Зейделя 3-го порядка — бар-чарт (PNG): SI..SV, при наличии хроматизма — SIхр/SIIхр (данные — seidel.sums) | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl` | {output, size_bytes, wl, sums, chromatic} |
| [`plot.spot`](#plotspot) | Точечная диаграмма пятна рассеяния (PNG): точки + окружность RMS | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `field_y`, `num_rays`, `sampling` | {output, size_bytes, num_points, rms} |
| [`plot.spot.grid`](#plotspotgrid) | Сетка пятен рассеяния по полям (PNG): подпанель на поле, точки и окружность RMS | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `fields`, `wl`, `num_rays` | {output, size_bytes, wl, rows: [{field_y, rms, num_points}]} |
| [`plot.vignetting`](#plotvignetting) | Виньетирование по полям (PNG): срезание верх/низ пучка, % (TABBEA §14.1) и светораспределение (доли площади зрачка верх/низ/всего) | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `fields`, `wl` | {output, size_bytes, wl, rows: [{field_y, vignet_up, vignet_down, light_up, light_down, light_total}], max_vignet_percent} |
| [`plot.wavefront`](#plotwavefront) | Карта волнового фронта W(x, y) на зрачке (PNG, λ), с СКВ и размахом PV | `file`, `system`, `lbo_index`, `lbo_name`, `output`, `wl`, `field_y`, `grid_size` | {output, size_bytes, wl, field_y, grid_size, rms_wl, pv_wl, fill} |

## Параметры и результаты

### plot.caustic

Каустика (PNG): выходящие участки лучей веера за последней поверхностью до z(изображение)+range и ширина пучка RMS(z) — перетяжка/положение фокуса

**Returns:** {output, size_bytes, wl, field_y, num_rays, num_ok, paraxial_focus_mm, waist_z_mm, min_rms_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `num_rays` | `int` | — | `15` | — | лучей в меридиональном веере |
| `defocus_range` | `float` | — | `2.0` | — | продление за плоскость изображения, мм (> 0) |
| `num_points` | `int` | — | `60` | — | точек сетки z кривой ширины |

### plot.chromatism

Хроматизм (PNG): f′(λ) по сетке длин волн и осевой хроматизм Δf′(λ) относительно основной λ; рабочие λ системы — метками

**Returns:** {output, size_bytes, primary_wl, fprime_primary_mm, wl_grid, fprimes_mm, dfprime_at_system_wl}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `steps` | `int` | — | `21` | — | точек сетки λ (≥ 2) |

### plot.dof

Глубина фокуса (PNG): RMS и геометрический радиус пятна против смещения плоскости изображения; зона, где радиус ≤ круга нерезкости, — глубина резкости

**Returns:** {output, size_bytes, wl, field_y, coc_um, best_defocus_mm, best_rms_mm, near_mm, far_mm, depth_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `coc_um` | `float` | — | `20.0` | — | круг нерезкости, мкм (> 0) |
| `defocus_range` | `float` | — | `1.0` | — | ±мм развёртки дефокуса (> 0) |
| `num_points` | `int` | — | `21` | — | точек кривой (≥ 3) |
| `num_rays` | `int` | — | `20` | — | лучей по стороне сетки зрачка |

### plot.ee

Функция концентрации энергии (PNG): доля энергии ФРТ в круге радиуса r

**Returns:** {output, size_bytes, r80_um}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### plot.ee.family

Семейство функций концентрации энергии по полям (PNG) с метрикой r₈₀

**Returns:** {output, size_bytes, wl, rows: [{field_y, r80_um}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### plot.fan

Веер лучей (PNG): поперечная dy и продольная ds аберрации против зрачковой координаты

**Returns:** {output, size_bytes, num_rays, num_ok}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `num_rays` | `int` | — | `21` | — | лучей в веере |

### plot.fan.fields

Веера поперечных аберраций dy по полям (PNG): кривые dy(зрачковая координата) всех полей на одном поле графика

**Returns:** {output, size_bytes, wl, num_fan_rays, fields, num_ok}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `num_fan_rays` | `int` | — | `15` | — | лучей в веере на поле |

### plot.field

Внеосевые аберрации по полю (PNG): астигматизм Z'm/Z's и дисторсия

**Returns:** {output, size_bytes, fields}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `fields` | `list` | — | `null` | — | список полей (град); по умолчанию — поля системы |
| `num_fan_rays` | `int` | — | `15` | — | лучей в веере на поле |

### plot.fields

Карта точек поля системы (PNG): (x, y) с весами и окружностью максимального поля

**Returns:** {output, size_bytes, num_fields, max_field, fields}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |

### plot.focus

Фокусировочная кривая (PNG): MTF на заданной частоте против смещения плоскости изображения

**Returns:** {output, size_bytes, best_defocus_mm, num_points}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `defocus_range` | `float` | — | `2.0` | — | ±мм от лучшей фокальной плоскости |
| `freq_lpmm` | `float` | — | `50.0` | — | частота оценки MTF, лин/мм |
| `num_points` | `int` | — | `40` | — | точек кривой |
| `num_rays` | `int` | — | `30` | — | лучей сетки для оценки пятна |

### plot.glassmap

Стёкла системы на карте стёкол nd–vd (PNG): каталог ГОСТ фоном, стёкла системы — ломаной «траектории коррекции» по ходу поверхностей (данные — diagram.glasses)

**Returns:** {output, size_bytes, glasses, skipped, num_catalog}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |

### plot.heatmap

Топограмма плотности пятна рассеяния (PNG): гистограмма точек в плоскости изображения

**Returns:** {output, size_bytes, x_range, y_range}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `num_rays` | `int` | — | `500` | — | лучей для гистограммы |
| `grid_size` | `int` | — | `100` | — | сетка гистограммы (N×N) |

### plot.layout

Схема оптической системы с трассировкой лучей (PNG, 2D-разрез): поверхности-дуги, стёкла, стоп, ось, F′ и веера лучей по полям (ANALIZE §4.8)

**Returns:** {output, size_bytes, num_surfaces, fields, num_rays, num_ok, focal_z_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `fields` | `list` | — | `null` | — | поля вееров, град; по умолчанию — 0 и максимальное поле системы |
| `num_rays` | `int` | — | `7` | — | лучей в веере на поле |

### plot.mtf

Оптическая передаточная функция (PNG): сечения тангенциальное/сагиттальное из ФРТ

**Returns:** {output, size_bytes, cutoff_lpmm, nyquist_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### plot.mtf.family

Семейство ЧКХ по полям (PNG): тангенциальное (сплошная) и сагиттальное (пунктир) сечения из ФРТ на одном поле графика

**Returns:** {output, size_bytes, wl, fields, cutoff_lpmm, nyquist_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `max_freq` | `float` | — | `null` | — | правая граница частоты, лин/мм (по умолчанию — Найквист ФРТ) |

### plot.psf

Функция рассеяния точки (PNG): карта интенсивности в плоскости изображения

**Returns:** {output, size_bytes, strehl, pitch_um}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |

### plot.psf.slice

Срезы ФРТ через центр (PNG): горизонтальный I(x) и вертикальный I(y) профили с шириной FWHM

**Returns:** {output, size_bytes, wl, field_y, defocus, strehl, fwhm_x_um, fwhm_y_um}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |

### plot.pupil.vign

Маска зрачка на поле (PNG): узлы гексаполярной сетки зрачка «прошёл/срезан» (данные — trace.grid3d), границы зрачка и экранирования

**Returns:** {output, size_bytes, wl, field_y, num_passed, num_blocked, pass_fraction, obscuration_ratio}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `num_rings` | `int` | — | `5` | — | колец зрачка (≥ 2) |
| `num_azimuths` | `int` | — | `24` | — | азимутов на кольцо (≥ 4) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### plot.seidel

Суммы Зейделя 3-го порядка — бар-чарт (PNG): SI..SV, при наличии хроматизма — SIхр/SIIхр (данные — seidel.sums)

**Returns:** {output, size_bytes, wl, sums, chromatic}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### plot.spot

Точечная диаграмма пятна рассеяния (PNG): точки + окружность RMS

**Returns:** {output, size_bytes, num_points, rms}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `num_rays` | `int` | — | `50` | — | лучей по стороне сетки / колец гексаполярной сетки |
| `sampling` | `str` | — | `"grid"` | `["grid", "hexapolar"]` | способ выборки зрачка |

### plot.spot.grid

Сетка пятен рассеяния по полям (PNG): подпанель на поле, точки и окружность RMS

**Returns:** {output, size_bytes, wl, rows: [{field_y, rms, num_points}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `num_rays` | `int` | — | `40` | — | лучей по стороне сетки зрачка |

### plot.vignetting

Виньетирование по полям (PNG): срезание верх/низ пучка, % (TABBEA §14.1) и светораспределение (доли площади зрачка верх/низ/всего)

**Returns:** {output, size_bytes, wl, rows: [{field_y, vignet_up, vignet_down, light_up, light_down, light_total}], max_vignet_percent}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### plot.wavefront

Карта волнового фронта W(x, y) на зрачке (PNG, λ), с СКВ и размахом PV

**Returns:** {output, size_bytes, wl, field_y, grid_size, rms_wl, pv_wl, fill}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `grid_size` | `int` | — | `64` | — | решётка карты N×N (≥ 8) |

