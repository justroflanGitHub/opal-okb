# Категория aber

18 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`aber.caustic`](#abercaustic) | Радиусы кривизны каустик 2-го порядка (меридиональная/сагиттальная) у фокусов Коддингтона | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `ray_halfheight`, `wl` | {r_m, r_s, r_m_rel, r_s_rel, method, ...} (мм / % от f') |
| [`aber.chief`](#aberchief) | Аберрации главных лучей по полям: дисторсия, отрезки Z'm/Z's, хроматизм увеличения | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | строки {field_y, distortion_abs, distortion_rel, Zm, Zs, lateral_color, lateral_color_pct} |
| [`aber.coddington`](#abercoddington) | След Коддингтона вдоль главного луча: отрезки Z'm/Z's, астигматизм (дифференциальный реверс §7) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {z_m, z_s, delta_zm, delta_zs, astigmatism, u_m, u_s, t_m, t_s} |
| [`aber.fan`](#aberfan) | Веер аберраций: поперечные dy, продольные ds, волновые W (OPL до опорной сферы) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y`, `wl` | строки веера {pupil_y, dy, ds, wave, y_img, z_img, success} |
| [`aber.fields`](#aberfields) | Точки поля для анализа по полю: все точки системы (0 добавляется) или равномерная сетка | `file`, `system`, `lbo_index`, `lbo_name`, `num_fields` | список полей (град/мм) |
| [`aber.focus_curve`](#aberfocus_curve) | Фокусировочная кривая: MTF vs смещение плоскости изображения (RMS пятна по трассировке) | `file`, `system`, `lbo_index`, `lbo_name`, `num_points`, `defocus_range`, `freq_lpmm`, `num_rays`, `field_y`, `wl` | кривая [(defocus_мм, mtf), ...] от найденного фокуса |
| [`aber.focus_diagrams`](#aberfocus_diagrams) | Фокусировочные диаграммы: 5 точечных диаграмм при defocus = 0, ±ΔS', ±2ΔS' | `file`, `system`, `lbo_index`, `lbo_name`, `focus_step_mm`, `num_rays`, `field_y`, `wl`, `include_spots` | по метке позиции {defocus_mm, rms} (+spots при include_spots) и общий max_range |
| [`aber.gauge_rays`](#abergauge_rays) | Габаритные лучи пучка (верх/низ/главный/саг±1): координаты на поверхностях, направления, OPL | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | 5 лучей {key, label, points, directions, segment_lengths, path_length, opl} |
| [`aber.isoplanatism`](#aberisoplanatism) | Неизопланатизм осевого пучка: η(h) — изменение поперечной аберрации при малом смещении предмета | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_eps`, `wl` | высоты зрачка + безразмерные η (0 = изопланатизм) |
| [`aber.mtf_geo`](#abermtf_geo) | Геометрическая ЧКХ: FFT гистограммы точечной диаграммы (танг./саг. срезы) | `file`, `system`, `lbo_index`, `lbo_name`, `max_freq`, `num_freqs`, `num_rays`, `field_y`, `wl` | строки [freq_лин/мм, MTF_tangential, MTF_sagittal] |
| [`aber.oblique_fan`](#aberoblique_fan) | Аберрации в косом сечении: веер под азимутальным углом (0° — меридиональное, 90° — сагиттальное) | `file`, `system`, `lbo_index`, `lbo_name`, `azimuth_deg`, `num_rays`, `field_y`, `wl` | высоты зрачка + dy меридиональное/сагиттальное (мкм) |
| [`aber.ray_coordinates`](#aberray_coordinates) | Координаты габаритных лучей (верхний/нижний/главный) на каждой поверхности и плоскости изображения | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | строки {surface, x/y/z_upper, x/y/z_lower, x/y/z_chief} |
| [`aber.rms_poly`](#aberrms_poly) | Взвешенный RMS пятна по всем полям и длинам волн | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y` | скаляр RMS (мм); null — если ни один луч не дошёл |
| [`aber.spot_defocus`](#aberspot_defocus) | Точечная диаграмма при смещении плоскости изображения | `file`, `system`, `lbo_index`, `lbo_name`, `defocus_mm`, `num_rays`, `field_y`, `wl` | точки относительно центроида (мм) + RMS |
| [`aber.spot_heatmap`](#aberspot_heatmap) | Топограмма плотности пятна рассеяния (гистограмма точек, нормированная на максимум) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `grid_size`, `field_y`, `wl`, `include_grid` | диапазоны + заполнение (+ решётка heatmap при include_grid) |
| [`aber.spot_poly`](#aberspot_poly) | Полихроматическая точечная диаграмма: все рабочие λ системы, точки с индексом волны | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y` | точки [[dx, dy, wl_index], ...] (мм) |
| [`aber.wavefront`](#aberwavefront) | Волновая аберрация W на гексаполярной сетке зрачка (OPL до опорной сферы, в длинах волн) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `num_rings`, `wl` | точки [px, py, W] |
| [`aber.wavefront_rms`](#aberwavefront_rms) | СКВ волновой аберрации W по полю (гексаполярная сетка зрачка в каждой точке поля) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rings`, `num_fields`, `wl` | поля + СКВ (длины волн; null — лучей мало) |

## Параметры и результаты

### aber.caustic

Радиусы кривизны каустик 2-го порядка (меридиональная/сагиттальная) у фокусов Коддингтона

**Returns:** {r_m, r_s, r_m_rel, r_s_rel, method, ...} (мм / % от f')

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `ray_halfheight` | `float` | — | `null` | — | высота δ крайних лучей (мм); по умолчанию — 1% радиуса зрачка |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.chief

Аберрации главных лучей по полям: дисторсия, отрезки Z'm/Z's, хроматизм увеличения

**Returns:** строки {field_y, distortion_abs, distortion_rel, Zm, Zs, lateral_color, lateral_color_pct}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.coddington

След Коддингтона вдоль главного луча: отрезки Z'm/Z's, астигматизм (дифференциальный реверс §7)

**Returns:** {z_m, z_s, delta_zm, delta_zs, astigmatism, u_m, u_s, t_m, t_s}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.fan

Веер аберраций: поперечные dy, продольные ds, волновые W (OPL до опорной сферы)

**Returns:** строки веера {pupil_y, dy, ds, wave, y_img, z_img, success}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `20` | — | лучей веера (сетка зрачка −1..1) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.fields

Точки поля для анализа по полю: все точки системы (0 добавляется) или равномерная сетка

**Returns:** список полей (град/мм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_fields` | `int` | — | `5` | — | число точек, если поле системы не задано |

### aber.focus_curve

Фокусировочная кривая: MTF vs смещение плоскости изображения (RMS пятна по трассировке)

**Returns:** кривая [(defocus_мм, mtf), ...] от найденного фокуса

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_points` | `int` | — | `40` | — | точек кривой |
| `defocus_range` | `float` | — | `2.0` | — | ±мм отклонения плоскости |
| `freq_lpmm` | `float` | — | `50.0` | — | частота оценки MTF (лин/мм) |
| `num_rays` | `int` | — | `30` | — | лучей по стороне сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.focus_diagrams

Фокусировочные диаграммы: 5 точечных диаграмм при defocus = 0, ±ΔS', ±2ΔS'

**Returns:** по метке позиции {defocus_mm, rms} (+spots при include_spots) и общий max_range

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `focus_step_mm` | `float` | — | `0.1` | — | шаг фокусировки ΔS' (мм, настройка анализа) |
| `num_rays` | `int` | — | `60` | — | лучей сетки зрачка на позицию |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `include_spots` | `bool` | — | `false` | — | включить точки пятен (большой объём) |

### aber.gauge_rays

Габаритные лучи пучка (верх/низ/главный/саг±1): координаты на поверхностях, направления, OPL

**Returns:** 5 лучей {key, label, points, directions, segment_lengths, path_length, opl}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.isoplanatism

Неизопланатизм осевого пучка: η(h) — изменение поперечной аберрации при малом смещении предмета

**Returns:** высоты зрачка + безразмерные η (0 = изопланатизм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `20` | — | лучей веера на каждую пробу поля |
| `field_eps` | `float` | — | `null` | — | малое смещение поля ε; по умолчанию — авто (5% макс. поля / типовое по типу предмета) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.mtf_geo

Геометрическая ЧКХ: FFT гистограммы точечной диаграммы (танг./саг. срезы)

**Returns:** строки [freq_лин/мм, MTF_tangential, MTF_sagittal]

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `max_freq` | `float` | — | `100.0` | — | максимальная частота (лин/мм) |
| `num_freqs` | `int` | — | `20` | — | число частот (плюс нулевая) |
| `num_rays` | `int` | — | `50` | — | лучей по стороне сетки зрачка пятна |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.oblique_fan

Аберрации в косом сечении: веер под азимутальным углом (0° — меридиональное, 90° — сагиттальное)

**Returns:** высоты зрачка + dy меридиональное/сагиттальное (мкм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `azimuth_deg` | `float` | — | `45.0` | — | азимут сечения (град, нормализуется к [0, 360)) |
| `num_rays` | `int` | — | `20` | — | лучей веера |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.ray_coordinates

Координаты габаритных лучей (верхний/нижний/главный) на каждой поверхности и плоскости изображения

**Returns:** строки {surface, x/y/z_upper, x/y/z_lower, x/y/z_chief}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.rms_poly

Взвешенный RMS пятна по всем полям и длинам волн

**Returns:** скаляр RMS (мм); null — если ни один луч не дошёл

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `30` | — | лучей по стороне сетки зрачка |
| `field_y` | `float` | — | `null` | — | одно поле вместо точек поля системы |

### aber.spot_defocus

Точечная диаграмма при смещении плоскости изображения

**Returns:** точки относительно центроида (мм) + RMS

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `defocus_mm` | `float` | — | `0.0` | — | смещение плоскости (+ дальше от системы) |
| `num_rays` | `int` | — | `100` | — | лучей по стороне сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.spot_heatmap

Топограмма плотности пятна рассеяния (гистограмма точек, нормированная на максимум)

**Returns:** диапазоны + заполнение (+ решётка heatmap при include_grid)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `500` | — | число лучей пятна (сетка √N × √N) |
| `grid_size` | `int` | — | `100` | — | размер гистограммы grid_size × grid_size |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `include_grid` | `bool` | — | `false` | — | включить решётку heatmap (большой объём) |

### aber.spot_poly

Полихроматическая точечная диаграмма: все рабочие λ системы, точки с индексом волны

**Returns:** точки [[dx, dy, wl_index], ...] (мм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `40` | — | лучей по стороне сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |

### aber.wavefront

Волновая аберрация W на гексаполярной сетке зрачка (OPL до опорной сферы, в длинах волн)

**Returns:** точки [px, py, W]

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rings` | `int` | — | `4` | — | колец гексаполярной сетки (4 → 61 точка) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### aber.wavefront_rms

СКВ волновой аберрации W по полю (гексаполярная сетка зрачка в каждой точке поля)

**Returns:** поля + СКВ (длины волн; null — лучей мало)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rings` | `int` | — | `4` | — | колец гексаполярной сетки зрачка |
| `num_fields` | `int` | — | `5` | — | точек поля, если поле системы не задано |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

