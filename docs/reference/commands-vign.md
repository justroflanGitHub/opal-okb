# Категория vign

5 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`vign.compute`](#vigncompute) | Виньетирование верх/низ пучка + ограничивающий элемент (бисекция по точному трейсеру) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {vignet_up, vignet_down, limit_up, limit_down, obscured} |
| [`vign.light`](#vignlight) | Светораспределение по полям: доля площади зрачка + центроид (сетка по единичному кругу) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl`, `grid_n` | строки {field_y, light_up, light_down, light_total, centroid_y, n_samples, n_passed} |
| [`vign.passage_zones`](#vignpassage_zones) | Зоны прохождения пучка по ВСЕМ поверхностям («реальное экранирование», веер по диаметру зрачка) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `grid_n` | {passage_fraction, vignetted, surfaces: [{n, crossed, passed, outer, inner, center, blocked_here, limit}]} |
| [`vign.real_obscuration`](#vignreal_obscuration) | «Габариты экранов»: эллипс экранирования на входном зрачке, бисекция по 4 полуосям (TABEAP) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {full_diameter_y/x, screen_diameter_y/x, obscuration_fraction, screen_shift, minimal_obscuration, cutters} |
| [`vign.tabbea`](#vigntabbea) | Апертурные характеристики пучков: апертуры, зрачки, виньетирование, светораспределение (таблица TABBEA) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl` | строки таблицы + текстовый формат OPAL |

## Параметры и результаты

### vign.compute

Виньетирование верх/низ пучка + ограничивающий элемент (бисекция по точному трейсеру)

**Returns:** {vignet_up, vignet_down, limit_up, limit_down, obscured}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### vign.light

Светораспределение по полям: доля площади зрачка + центроид (сетка по единичному кругу)

**Returns:** строки {field_y, light_up, light_down, light_total, centroid_y, n_samples, n_passed}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей (град/мм); по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `grid_n` | `int` | — | `15` | — | узлов сетки зрачка по оси (нечётное) |

### vign.passage_zones

Зоны прохождения пучка по ВСЕМ поверхностям («реальное экранирование», веер по диаметру зрачка)

**Returns:** {passage_fraction, vignetted, surfaces: [{n, crossed, passed, outer, inner, center, blocked_here, limit}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `grid_n` | `int` | — | `15` | — | узлов веера по диаметру зрачка (нечётное) |

### vign.real_obscuration

«Габариты экранов»: эллипс экранирования на входном зрачке, бисекция по 4 полуосям (TABEAP)

**Returns:** {full_diameter_y/x, screen_diameter_y/x, obscuration_fraction, screen_shift, minimal_obscuration, cutters}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### vign.tabbea

Апертурные характеристики пучков: апертуры, зрачки, виньетирование, светораспределение (таблица TABBEA)

**Returns:** строки таблицы + текстовый формат OPAL

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей (град/мм); по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

