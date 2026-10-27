# Категория spectral

7 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`catalog.spectral.band`](#catalogspectralband) | Классификация длины волны по спектральным зонам: УФ / цветные поддиапазоны видимого / ИК (границы согласованы с цветами стандартных линий справочника utils/spectral_lines.py — у каждой линии полоса совпадает с её цветом) | `wl`, `wls` | {count, bands: [{wl_um, wl_nm, band, color, from_nm, to_nm, visible}], zones} |
| [`catalog.spectral.element`](#catalogspectralelement) | Линии по элементу-источнику (Hg, H, He, Na, Cd, K, Cs) | `element` | {element, lines: [...]} |
| [`catalog.spectral.get`](#catalogspectralget) | Спектральная линия по обозначению (F, d, C', t…) | `name` | {name, wavelength_nm, element, color, text} |
| [`catalog.spectral.lines`](#catalogspectrallines) | Справочник стандартных спектральных линий (λ, элемент, цвет) | — | {count, lines: [{name, wavelength_nm, element, color}]} |
| [`catalog.spectral.match`](#catalogspectralmatch) | Рабочие λ системы ↔ стандартные линии (ближайшие, допуск справочника) | `file`, `system`, `lbo_index`, `lbo_name` | {rows: [{wl, line, distance_nm, matched}]} |
| [`catalog.spectral.nearest`](#catalogspectralnearest) | Ближайшая стандартная линия к длине волны | `wl` | {wl, line: {...}, distance_nm} |
| [`catalog.spectral.stats`](#catalogspectralstats) | Свод справочника спектральных линий: счётчики по элементам и цветам, диапазон λ, разбивка по зонам УФ/видимый/ИК (движок классификации — тот же, что catalog.spectral.band) | — | {count, by_element, by_color, by_zone, wl_nm_min, wl_nm_max, wl_um_min, wl_um_max} |

## Параметры и результаты

### catalog.spectral.band

Классификация длины волны по спектральным зонам: УФ / цветные поддиапазоны видимого / ИК (границы согласованы с цветами стандартных линий справочника utils/spectral_lines.py — у каждой линии полоса совпадает с её цветом)

**Returns:** {count, bands: [{wl_um, wl_nm, band, color, from_nm, to_nm, visible}], zones}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `wl` | `float` | — | `null` | — | λ, мкм (одиночная) |
| `wls` | `list` | — | `null` | — | список λ, мкм (пакетная классификация) |

### catalog.spectral.element

Линии по элементу-источнику (Hg, H, He, Na, Cd, K, Cs)

**Returns:** {element, lines: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `element` | `str` | да | `null` | — | символ элемента |

### catalog.spectral.get

Спектральная линия по обозначению (F, d, C', t…)

**Returns:** {name, wavelength_nm, element, color, text}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | обозначение линии |

### catalog.spectral.lines

Справочник стандартных спектральных линий (λ, элемент, цвет)

**Returns:** {count, lines: [{name, wavelength_nm, element, color}]}

### catalog.spectral.match

Рабочие λ системы ↔ стандартные линии (ближайшие, допуск справочника)

**Returns:** {rows: [{wl, line, distance_nm, matched}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### catalog.spectral.nearest

Ближайшая стандартная линия к длине волны

**Returns:** {wl, line: {...}, distance_nm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `wl` | `float` | да | `null` | — | длина волны, мкм |

### catalog.spectral.stats

Свод справочника спектральных линий: счётчики по элементам и цветам, диапазон λ, разбивка по зонам УФ/видимый/ИК (движок классификации — тот же, что catalog.spectral.band)

**Returns:** {count, by_element, by_color, by_zone, wl_nm_min, wl_nm_max, wl_um_min, wl_um_max}

