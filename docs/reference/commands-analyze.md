# Категория analyze

6 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`analyze.field_aberrations`](#analyzefield_aberrations) | Внеосевые аберрации по полям: дисторсия, астигматизм, кома | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `fields`, `num_fan_rays` | список {field_y, distortion, astigmatism, z_m, z_s, coma} |
| [`analyze.psf`](#analyzepsf) | ФРТ (psf_grid): Штрель, срез ОПФ, решётки — по запросу | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `defocus`, `include_grid` | скалярные метрики ФРТ (+psf/wavefront при include_grid) |
| [`analyze.ray_fan`](#analyzeray_fan) | Меридиональный веер лучей: трассировка через систему | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `pupil_range`, `wl`, `field_y` | список лучей {pupil_y, success, error, opl, path} |
| [`analyze.spot`](#analyzespot) | Точечная диаграмма: пятно + RMS по осям и центроид | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `num_rays`, `field_y`, `sampling` | точки пятна (мм) + RMS-метрики |
| [`analyze.tables.tabgl`](#analyzetablestabgl) | Таблица TABGL: главные лучи по зонам поля (§15.1) | `file`, `system`, `lbo_index`, `lbo_name`, `n_zones`, `wl` | строки таблицы + текстовый формат OPAL |
| [`analyze.tables.tabpr2`](#analyzetablestabpr2) | Таблица TABPR2: хроматизм по зонам поля (§15.2) | `file`, `system`, `lbo_index`, `lbo_name`, `wl_main`, `wl_alt`, `n_zones` | строки таблицы + текстовый формат OPAL |

## Параметры и результаты

### analyze.field_aberrations

Внеосевые аберрации по полям: дисторсия, астигматизм, кома

**Returns:** список {field_y, distortion, astigmatism, z_m, z_s, coma}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `fields` | `list` | — | `null` | — | список полей (град); по умолчанию — поля системы |
| `num_fan_rays` | `int` | — | `15` | — | лучей в веере на поле |

### analyze.psf

ФРТ (psf_grid): Штрель, срез ОПФ, решётки — по запросу

**Returns:** скалярные метрики ФРТ (+psf/wavefront при include_grid)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |
| `include_grid` | `bool` | — | `false` | — | включить решётки psf/wavefront/оси (большой объём) |

### analyze.ray_fan

Меридиональный веер лучей: трассировка через систему

**Returns:** список лучей {pupil_y, success, error, opl, path}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `9` | — | число лучей веера |
| `pupil_range` | `float` | — | `1.0` | — | диапазон зрачка (0..1) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |

### analyze.spot

Точечная диаграмма: пятно + RMS по осям и центроид

**Returns:** точки пятна (мм) + RMS-метрики

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `num_rays` | `int` | — | `50` | — | лучей по стороне сетки / колец гексаполярной сетки |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `sampling` | `str` | — | `"grid"` | `["grid", "hexapolar"]` | способ выборки зрачка |

### analyze.tables.tabgl

Таблица TABGL: главные лучи по зонам поля (§15.1)

**Returns:** строки таблицы + текстовый формат OPAL

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `n_zones` | `int` | — | `3` | — | число зон поля (осевая строка — сверх) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### analyze.tables.tabpr2

Таблица TABPR2: хроматизм по зонам поля (§15.2)

**Returns:** строки таблицы + текстовый формат OPAL

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl_main` | `float` | — | `null` | — | основная λ, мкм (по умолчанию — основная λ системы) |
| `wl_alt` | `float` | — | `null` | — | вторая λ пары (по умолчанию — вторая λ системы) |
| `n_zones` | `int` | — | `3` | — | число зон поля |

