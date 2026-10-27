# Категория quality

19 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`quality.check.all`](#qualitycheckall) | Агрегат пороговых проверок (MTF/Штрель/RMS/ФКЭ) с общим вердиктом; пороги опциональны — заданный порог включает проверку | `file`, `system`, `lbo_index`, `lbo_name`, `mtf_min`, `strehl_min`, `rms_max_um`, `ee_max_um`, `freq_lpmm`, `fields`, `num_rays` | {checks: [{check, pass, detail}], pass, num_checks} |
| [`quality.check.ee`](#qualitycheckee) | Пороговая проверка ФКЭ: диаметр зоны заданной доли энергии не больше порога (мкм) во всех полях | `file`, `system`, `lbo_index`, `lbo_name`, `threshold_um`, `fraction`, `fields`, `num_rays`, `wl` | {wl, fraction, threshold_um, rows: [{field_y, diameter_um, pass}], pass, worst} |
| [`quality.check.mtf`](#qualitycheckmtf) | Пороговая проверка MTF: контраст на частоте не ниже порога во всех полях (сечения мер/саг) | `file`, `system`, `lbo_index`, `lbo_name`, `threshold`, `freq_lpmm`, `fields`, `wl` | {wl, freq_lpmm, threshold, rows: [{field_y, mtf_t, mtf_s, pass_t, pass_s}], pass} |
| [`quality.check.spot`](#qualitycheckspot) | Пороговая проверка пятна: полихроматический RMS не больше порога (мкм) во всех полях | `file`, `system`, `lbo_index`, `lbo_name`, `threshold_um`, `fields`, `num_rays` | {threshold_um, rows: [{field_y, rms_um, pass}], pass, worst} |
| [`quality.check.strehl`](#qualitycheckstrehl) | Пороговая проверка Штреля: полихроматический Штрель не ниже порога во всех полях | `file`, `system`, `lbo_index`, `lbo_name`, `threshold`, `fields` | {threshold, rows: [{field_y, strehl_exact, pass}], pass, worst} |
| [`quality.compare`](#qualitycompare) | Сравнение двух систем по сводным метрикам (efl, F/#, апертура, RMS, Штрель, MTF, срез ЧКХ) | `file_a`, `file_b`, `freq_lpmm`, `num_rays` | {freq_lpmm, rows: [{metric, a, b, delta}]} |
| [`quality.ee.diameters`](#qualityeediameters) | Диаметры зон задержанной энергии (50/80/90 %) по полям — геометрически, по точечной диаграмме | `file`, `system`, `lbo_index`, `lbo_name`, `fractions`, `fields`, `num_rays`, `wl` | {wl, rows: [{field_y, diameters: [{fraction, diameter_um}]}]} |
| [`quality.ee.diameters.psf`](#qualityeediameterspsf) | Диаметры зон задержанной энергии по дифракционной ФРТ (§9.3): Fraction → D = 2r, с пятном Эйри | `file`, `system`, `lbo_index`, `lbo_name`, `fractions`, `field_y`, `wl` | {wl, field_y, diameters: [{fraction, diameter_um}], airy_um, pitch_um} |
| [`quality.fields.summary`](#qualityfieldssummary) | Сводная таблица качества по полям: полихроматич. RMS, Штрель, MTF на частоте (мер/саг), диаметр зоны 90 % энергии | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `freq_lpmm`, `num_rays` | {freq_lpmm, rows: [{field_y, rms_poly, strehl_exact, mtf_t, mtf_s, d90_um}]} |
| [`quality.mtf.area`](#qualitymtfarea) | Интегральная ЧКХ: площадь под сечениями мер/саг (нормирована на срез) и доля от дифракционного предела | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {wl, field_y, area_t, area_s, ideal_area, ratio_t, ratio_s, cutoff_lpmm} |
| [`quality.mtf.geo_vs_diff`](#qualitymtfgeo_vs_diff) | Геометрическая vs дифракционная ЧКХ на частоте: насколько аберрации снижают контраст от предела | `file`, `system`, `lbo_index`, `lbo_name`, `freq_lpmm`, `field_y`, `num_rays`, `wl` | {wl, field_y, freq_lpmm, diff_t, diff_s, geo_t, geo_s, ratio_t, ratio_s} |
| [`quality.mtf.limit_freq`](#qualitymtflimit_freq) | Предельная частота ЧКХ: где MTF впервые падает ниже порога (сечения мер/саг по полям) | `file`, `system`, `lbo_index`, `lbo_name`, `threshold`, `fields`, `wl` | {wl, threshold, rows: [{field_y, limit_t, limit_s}], min_limit_lpmm} |
| [`quality.mtf.matrix`](#qualitymtfmatrix) | Матрица дифракционной ЧКХ: заданные частоты × поля (сечения мер/саг; выше среза — 0) | `file`, `system`, `lbo_index`, `lbo_name`, `freqs`, `fields`, `wl` | {wl, freqs, rows: [{field_y, mtf: [{freq_lpmm, mtf_t, mtf_s}]}], cutoff_lpmm} |
| [`quality.mtf.poly`](#qualitymtfpoly) | Полихроматическая дифракционная ЧКХ на заданных частотах (взвешенное среднее по рабочим λ системы) | `file`, `system`, `lbo_index`, `lbo_name`, `freqs`, `field_y` | {field_y, wls: [{wl, weight}], rows: [{freq_lpmm, mtf_t, mtf_s}]} |
| [`quality.passport`](#qualitypassport) | Паспорт системы: параксиальные величины (efl, F/#, апертура), RMS по полям, полихроматический Штрель, MTF на частоте, дифракционный предел | `file`, `system`, `lbo_index`, `lbo_name`, `freq_lpmm`, `num_rays` | {name, wavelengths, fields, paraxial: {...}, quality: {...}} |
| [`quality.regime`](#qualityregime) | Чем ограничено пятно: сравнение полихроматического RMS с радиусом диска Эйри (дифракция/аберрации) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `num_rays` | {f_number, wl, airy_radius_um, rms_um, ratio, regime} |
| [`quality.spot.summary`](#qualityspotsummary) | RMS кружка рассеяния по полям и рабочим λ + полихроматический RMS и худшее поле | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays` | {rows: [{field_y, by_wl: [{wl, rms}], rms_poly}], summary: {max_rms, max_field}} |
| [`quality.strehl.summary`](#qualitystrehlsummary) | Полихроматический Штрель по полям (Марешаль + точный) с худшим полем и средним | `file`, `system`, `lbo_index`, `lbo_name`, `fields` | {rows: [{field_y, strehl_exact, strehl_marechal, sigma_w, validity}], worst: {field_y, strehl_exact}, mean_exact} |
| [`quality.wavefront.summary`](#qualitywavefrontsummary) | СКВ волнового фронта по полю + Штрель Марешаля в худшей точке поля | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {wl, rows: [{field_y, rms_wl}], max_rms_wl, max_field, strehl_marechal_max} |

## Параметры и результаты

### quality.check.all

Агрегат пороговых проверок (MTF/Штрель/RMS/ФКЭ) с общим вердиктом; пороги опциональны — заданный порог включает проверку

**Returns:** {checks: [{check, pass, detail}], pass, num_checks}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `mtf_min` | `float` | — | `null` | — | порог MTF на частоте (0; 1) |
| `strehl_min` | `float` | — | `null` | — | порог Штреля (0; 1) |
| `rms_max_um` | `float` | — | `null` | — | порог RMS пятна, мкм |
| `ee_max_um` | `float` | — | `null` | — | порог диаметра зоны 90 % энергии, мкм |
| `freq_lpmm` | `float` | — | `50.0` | — | частота ЧКХ, лин/мм |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |

### quality.check.ee

Пороговая проверка ФКЭ: диаметр зоны заданной доли энергии не больше порога (мкм) во всех полях

**Returns:** {wl, fraction, threshold_um, rows: [{field_y, diameter_um, pass}], pass, worst}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `threshold_um` | `float` | да | `null` | — | порог диаметра зоны, мкм |
| `fraction` | `float` | — | `0.9` | — | доля энергии в зоне (по умолчанию 0.9) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `100` | — | лучей точечной диаграммы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.check.mtf

Пороговая проверка MTF: контраст на частоте не ниже порога во всех полях (сечения мер/саг)

**Returns:** {wl, freq_lpmm, threshold, rows: [{field_y, mtf_t, mtf_s, pass_t, pass_s}], pass}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `threshold` | `float` | да | `null` | — | порог MTF, доли единицы (0; 1) |
| `freq_lpmm` | `float` | — | `50.0` | — | частота ЧКХ, лин/мм |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.check.spot

Пороговая проверка пятна: полихроматический RMS не больше порога (мкм) во всех полях

**Returns:** {threshold_um, rows: [{field_y, rms_um, pass}], pass, worst}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `threshold_um` | `float` | да | `null` | — | порог RMS пятна, мкм |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |

### quality.check.strehl

Пороговая проверка Штреля: полихроматический Штрель не ниже порога во всех полях

**Returns:** {threshold, rows: [{field_y, strehl_exact, pass}], pass, worst}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `threshold` | `float` | да | `null` | — | порог Штреля, доли единицы (0; 1) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |

### quality.compare

Сравнение двух систем по сводным метрикам (efl, F/#, апертура, RMS, Штрель, MTF, срез ЧКХ)

**Returns:** {freq_lpmm, rows: [{metric, a, b, delta}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file_a` | `str` | да | `null` | — | файл первой системы |
| `file_b` | `str` | да | `null` | — | файл второй системы |
| `freq_lpmm` | `float` | — | `50.0` | — | частота ЧКХ, лин/мм |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |

### quality.ee.diameters

Диаметры зон задержанной энергии (50/80/90 %) по полям — геометрически, по точечной диаграмме

**Returns:** {wl, rows: [{field_y, diameters: [{fraction, diameter_um}]}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fractions` | `list` | — | `null` | — | доли энергии; по умолчанию [0.5, 0.8, 0.9] |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `100` | — | лучей точечной диаграммы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.ee.diameters.psf

Диаметры зон задержанной энергии по дифракционной ФРТ (§9.3): Fraction → D = 2r, с пятном Эйри

**Returns:** {wl, field_y, diameters: [{fraction, diameter_um}], airy_um, pitch_um}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fractions` | `list` | — | `null` | — | доли энергии; по умолчанию [0.5, 0.8, 0.9] |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.fields.summary

Сводная таблица качества по полям: полихроматич. RMS, Штрель, MTF на частоте (мер/саг), диаметр зоны 90 % энергии

**Returns:** {freq_lpmm, rows: [{field_y, rms_poly, strehl_exact, mtf_t, mtf_s, d90_um}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `freq_lpmm` | `float` | — | `50.0` | — | частота ЧКХ, лин/мм |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |

### quality.mtf.area

Интегральная ЧКХ: площадь под сечениями мер/саг (нормирована на срез) и доля от дифракционного предела

**Returns:** {wl, field_y, area_t, area_s, ideal_area, ratio_t, ratio_s, cutoff_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.mtf.geo_vs_diff

Геометрическая vs дифракционная ЧКХ на частоте: насколько аберрации снижают контраст от предела

**Returns:** {wl, field_y, freq_lpmm, diff_t, diff_s, geo_t, geo_s, ratio_t, ratio_s}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freq_lpmm` | `float` | — | `50.0` | — | частота, лин/мм |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `40` | — | лучей точечной диаграммы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.mtf.limit_freq

Предельная частота ЧКХ: где MTF впервые падает ниже порога (сечения мер/саг по полям)

**Returns:** {wl, threshold, rows: [{field_y, limit_t, limit_s}], min_limit_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `threshold` | `float` | да | `null` | — | порог MTF, доли единицы (0; 1) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.mtf.matrix

Матрица дифракционной ЧКХ: заданные частоты × поля (сечения мер/саг; выше среза — 0)

**Returns:** {wl, freqs, rows: [{field_y, mtf: [{freq_lpmm, mtf_t, mtf_s}]}], cutoff_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freqs` | `list` | — | `null` | — | частоты, лин/мм; по умолчанию [20, 50, 100] |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### quality.mtf.poly

Полихроматическая дифракционная ЧКХ на заданных частотах (взвешенное среднее по рабочим λ системы)

**Returns:** {field_y, wls: [{wl, weight}], rows: [{freq_lpmm, mtf_t, mtf_s}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freqs` | `list` | — | `null` | — | частоты, лин/мм; по умолчанию [20, 50, 100] |
| `field_y` | `float` | — | `0.0` | — | поле |

### quality.passport

Паспорт системы: параксиальные величины (efl, F/#, апертура), RMS по полям, полихроматический Штрель, MTF на частоте, дифракционный предел

**Returns:** {name, wavelengths, fields, paraxial: {...}, quality: {...}}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freq_lpmm` | `float` | — | `50.0` | — | частота ЧКХ паспорта, лин/мм |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |

### quality.regime

Чем ограничено пятно: сравнение полихроматического RMS с радиусом диска Эйри (дифракция/аберрации)

**Returns:** {f_number, wl, airy_radius_um, rms_um, ratio, regime}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |

### quality.spot.summary

RMS кружка рассеяния по полям и рабочим λ + полихроматический RMS и худшее поле

**Returns:** {rows: [{field_y, by_wl: [{wl, rms}], rms_poly}], summary: {max_rms, max_field}}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |

### quality.strehl.summary

Полихроматический Штрель по полям (Марешаль + точный) с худшим полем и средним

**Returns:** {rows: [{field_y, strehl_exact, strehl_marechal, sigma_w, validity}], worst: {field_y, strehl_exact}, mean_exact}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |

### quality.wavefront.summary

СКВ волнового фронта по полю + Штрель Марешаля в худшей точке поля

**Returns:** {wl, rows: [{field_y, rms_wl}], max_rms_wl, max_field, strehl_marechal_max}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

