# Категория sweep

14 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`sweep.aperture.spot_rms`](#sweepaperturespot_rms) | RMS кружка по диаметрам зрачка (апертуре) | `file`, `system`, `lbo_index`, `lbo_name`, `apertures`, `num_rays`, `field_y`, `wl` | {wl, rows: [{epd_mm, rms}]} |
| [`sweep.azimuth.aberrations`](#sweepazimuthaberrations) | Поперечная аберрация веера по азимутам сечений (0° — мер., 90° — саг.) | `file`, `system`, `lbo_index`, `lbo_name`, `azimuths`, `field_y`, `num_rays`, `wl` | {wl, rows: [{azimuth_deg, rms_dy, max_dy}]} |
| [`sweep.defocus.spot_rms`](#sweepdefocusspot_rms) | RMS кружка по дефокусу (плоскость наилучшей установки геометрически) | `file`, `system`, `lbo_index`, `lbo_name`, `defocus_min`, `defocus_max`, `steps`, `num_rays`, `field_y`, `wl` | {wl, rows: [{defocus_mm, rms}], best} |
| [`sweep.defocus.wavefront_rms`](#sweepdefocuswavefront_rms) | RMS волнового фронта по дефокусу (λ на краю зрачка) | `file`, `system`, `lbo_index`, `lbo_name`, `defocus_min`, `defocus_max`, `steps`, `grid_size`, `field_y`, `wl` | {wl, rows: [{defocus_wl, rms_wl, pv_wl}], best} |
| [`sweep.fields.chrom_shift`](#sweepfieldschrom_shift) | Смещение центроида пятна между крайними λ по полям (хроматизм увеличения, мм) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays` | {wl_lo, wl_hi, rows: [{field_y, shift_mm, dy}]} |
| [`sweep.fields.enc`](#sweepfieldsenc) | Доля энергии в кружке радиуса r по полям (ФКЭ) | `file`, `system`, `lbo_index`, `lbo_name`, `radius_um`, `fields`, `num_rays`, `wl` | {wl, radius_um, rows: [{field_y, enc}]} |
| [`sweep.fields.lsf_width`](#sweepfieldslsf_width) | Ширина ФРЛ на половине максимума (FWHM, мкм) по полям | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `direction`, `wl` | {wl, rows: [{field_y, fwhm_um}]} |
| [`sweep.fields.mtf`](#sweepfieldsmtf) | Геометрическая ЧКХ на частоте по полям (танг./саг.) | `file`, `system`, `lbo_index`, `lbo_name`, `freq_lpmm`, `fields`, `num_rays`, `wl` | {wl, freq_lpmm, rows: [{field_y, mtf_t, mtf_s}]} |
| [`sweep.fields.spot_rms`](#sweepfieldsspot_rms) | RMS кружка рассеяния по полям (мм): полный и по осям | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `wl` | {wl, rows: [{field_y, rms, rms_x, rms_y, num_points}]} |
| [`sweep.fields.strehl`](#sweepfieldsstrehl) | Число Штреля по полям (точное по волновому фронту) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl` | {wl, rows: [{field_y, strehl_exact, sigma_w, validity}]} |
| [`sweep.stop.seidel`](#sweepstopseidel) | Суммы Зейделя SI..SV по положениям апертурной диафрагмы (теория переноса диафрагмы) | `file`, `system`, `lbo_index`, `lbo_name`, `stop_surfaces`, `wl` | {wl, rows: [{stop_surface, SI, SII, SIII, SIV, SV}]} |
| [`sweep.wl.spot_rms`](#sweepwlspot_rms) | RMS кружка по рабочим λ системы (на поле) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `num_rays` | {rows: [{wl, rms, num_points}]} |
| [`sweep.wl.strehl`](#sweepwlstrehl) | Число Штреля по рабочим λ (на поле) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y` | {rows: [{wl, strehl_exact, sigma_w}]} |
| [`sweep.zones.spot`](#sweepzonesspot) | RMS пятна по кольцам зрачка (зональная декомпозиция) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rings`, `num_azimuths`, `field_y`, `wl` | {wl, rows: [{ring, rho, rms, num_points}]} |

## Параметры и результаты

### sweep.aperture.spot_rms

RMS кружка по диаметрам зрачка (апертуре)

**Returns:** {wl, rows: [{epd_mm, rms}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `apertures` | `list` | да | `null` | — | диаметры входного зрачка, мм |
| `num_rays` | `int` | — | `30` | — | лучей сетки |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.azimuth.aberrations

Поперечная аберрация веера по азимутам сечений (0° — мер., 90° — саг.)

**Returns:** {wl, rows: [{azimuth_deg, rms_dy, max_dy}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `azimuths` | `list` | — | `null` | — | список азимутов, град; по умолчанию 0/45/90 |
| `field_y` | `float` | да | `null` | — | поле |
| `num_rays` | `int` | — | `15` | — | лучей веера |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.defocus.spot_rms

RMS кружка по дефокусу (плоскость наилучшей установки геометрически)

**Returns:** {wl, rows: [{defocus_mm, rms}], best}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `defocus_min` | `float` | — | `-1.0` | — | начало, мм |
| `defocus_max` | `float` | — | `1.0` | — | конец, мм |
| `steps` | `int` | — | `9` | — | точек развёртки |
| `num_rays` | `int` | — | `30` | — | лучей сетки |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.defocus.wavefront_rms

RMS волнового фронта по дефокусу (λ на краю зрачка)

**Returns:** {wl, rows: [{defocus_wl, rms_wl, pv_wl}], best}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `defocus_min` | `float` | — | `-2.0` | — | начало, длины волн |
| `defocus_max` | `float` | — | `2.0` | — | конец, длины волн |
| `steps` | `int` | — | `9` | — | точек развёртки |
| `grid_size` | `int` | — | `32` | — | решётка зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.fields.chrom_shift

Смещение центроида пятна между крайними λ по полям (хроматизм увеличения, мм)

**Returns:** {wl_lo, wl_hi, rows: [{field_y, shift_mm, dy}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `30` | — | лучей сетки |

### sweep.fields.enc

Доля энергии в кружке радиуса r по полям (ФКЭ)

**Returns:** {wl, radius_um, rows: [{field_y, enc}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `radius_um` | `float` | — | `20.0` | — | радиус кружка, мкм |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `100` | — | лучей |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.fields.lsf_width

Ширина ФРЛ на половине максимума (FWHM, мкм) по полям

**Returns:** {wl, rows: [{field_y, fwhm_um}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `64` | — | сетка зрачка |
| `direction` | `str` | — | `"tangential"` | `["tangential", "sagittal"]` | направление щели |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.fields.mtf

Геометрическая ЧКХ на частоте по полям (танг./саг.)

**Returns:** {wl, freq_lpmm, rows: [{field_y, mtf_t, mtf_s}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freq_lpmm` | `float` | — | `50.0` | — | частота, лин/мм |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `40` | — | лучей точечной диаграммы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.fields.spot_rms

RMS кружка рассеяния по полям (мм): полный и по осям

**Returns:** {wl, rows: [{field_y, rms, rms_x, rms_y, num_points}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `30` | — | лучей сетки |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.fields.strehl

Число Штреля по полям (точное по волновому фронту)

**Returns:** {wl, rows: [{field_y, strehl_exact, sigma_w, validity}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.stop.seidel

Суммы Зейделя SI..SV по положениям апертурной диафрагмы (теория переноса диафрагмы)

**Returns:** {wl, rows: [{stop_surface, SI, SII, SIII, SIV, SV}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `stop_surfaces` | `list` | — | `null` | — | позиции диафрагмы (0-based); по умолчанию — все |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### sweep.wl.spot_rms

RMS кружка по рабочим λ системы (на поле)

**Returns:** {rows: [{wl, rms, num_points}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `30` | — | лучей сетки |

### sweep.wl.strehl

Число Штреля по рабочим λ (на поле)

**Returns:** {rows: [{wl, strehl_exact, sigma_w}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |

### sweep.zones.spot

RMS пятна по кольцам зрачка (зональная декомпозиция)

**Returns:** {wl, rows: [{ring, rho, rms, num_points}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rings` | `int` | — | `4` | — | колец зрачка |
| `num_azimuths` | `int` | — | `8` | — | азимутов на кольцо |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

