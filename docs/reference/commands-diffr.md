# Категория diffr

5 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`diffr.mtf`](#diffrmtf) | Дифракционная ЧКХ через FFT автокорреляции зрачка (Л1.7.1): сечения мер/саг + СКВ/PV фронта | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `grid_size`, `max_freq_lpmm` | freqs + mtf_tangential/mtf_sagittal + cutoff_lpmm |
| [`diffr.mtf.limited`](#diffrmtflimited) | Безаберрационная (дифракционно-ограниченная) ЧКХ круглого зрачка: аналитическая формула | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | freqs + mtf + cutoff_lpmm (эталон для сравнения) |
| [`diffr.mtf.poly`](#diffrmtfpoly) | Полихроматическая дифракционная ЧКХ: взвешенная сумма по всем λ системы (веса λ) | `file`, `system`, `lbo_index`, `lbo_name`, `grid_size`, `max_freq_lpmm` | freqs + mtf_tangential/mtf_sagittal + cutoff_lpmm |
| [`diffr.mtf.quick`](#diffrmtfquick) | Быстрая дифракционная ЧКХ (решётка зрачка 32×32) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | как diffr.mtf (freqs + мер/саг + cutoff) |
| [`diffr.wavefront`](#diffrwavefront) | Карта волнового фронта W на зрачке (опорная сфера параксиального изображения) | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `field_y`, `grid_size`, `include_grid` | СКВ/PV фронта по зрачку (+решётки W и маска по запросу) |

## Параметры и результаты

### diffr.mtf

Дифракционная ЧКХ через FFT автокорреляции зрачка (Л1.7.1): сечения мер/саг + СКВ/PV фронта

**Returns:** freqs + mtf_tangential/mtf_sagittal + cutoff_lpmm

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `grid_size` | `int` | — | `64` | — | решётка зрачка (N×N лучей) |
| `max_freq_lpmm` | `float` | — | `null` | — | верхняя частота, лин/мм (по умолчанию — срез) |

### diffr.mtf.limited

Безаберрационная (дифракционно-ограниченная) ЧКХ круглого зрачка: аналитическая формула

**Returns:** freqs + mtf + cutoff_lpmm (эталон для сравнения)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### diffr.mtf.poly

Полихроматическая дифракционная ЧКХ: взвешенная сумма по всем λ системы (веса λ)

**Returns:** freqs + mtf_tangential/mtf_sagittal + cutoff_lpmm

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `grid_size` | `int` | — | `64` | — | решётка зрачка (N×N лучей) |
| `max_freq_lpmm` | `float` | — | `null` | — | верхняя частота, лин/мм (по умолчанию — срез) |

### diffr.mtf.quick

Быстрая дифракционная ЧКХ (решётка зрачка 32×32)

**Returns:** как diffr.mtf (freqs + мер/саг + cutoff)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### diffr.wavefront

Карта волнового фронта W на зрачке (опорная сфера параксиального изображения)

**Returns:** СКВ/PV фронта по зрачку (+решётки W и маска по запросу)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE) |
| `grid_size` | `int` | — | `64` | — | решётка зрачка (N×N лучей) |
| `include_grid` | `bool` | — | `false` | — | включить карту W и маску зрачка (N² значений) |

