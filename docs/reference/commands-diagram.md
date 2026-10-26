# Категория diagram

10 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`diagram.bbox`](#diagrambbox) | Границы диапазона nd/Vd каталога (bbox реальных стёкол), стандартное окно карты и выбросы за окно | `source` | {total, bbox: {nd_min, nd_max, vd_min, vd_max}, view, outside_view, outliers: [{name, nd, vd, source}]} |
| [`diagram.coverage`](#diagramcoverage) | Покрытие каталога на карте n–Vd: гистограмма плотности по сетке окна просмотра, занятость ячеек и самые населённые зоны | `source`, `vd_bins`, `nd_bins`, `top_cells` | {total, in_view, outside_view, vd_edges, nd_edges, cells: [{i, j, vd_from, vd_to, nd_from, nd_to, count}], occupied, occupancy_pct, top: [{i, j, count, names}]} |
| [`diagram.crown.flint`](#diagramcrownflint) | Кроны против флинтов по зонам Vd: счётчики семейств в полосах Vd, диапазоны семейств и граница смешанных зон (карта n–Vd) | `source`, `vd_step` | {vd_step, bands: [{vd_from, vd_to, crown, flint, other}], family_stats: {crown/flint/other: {count, vd_min, vd_max}}, mixed_bands, vd_overlap, outside} |
| [`diagram.data`](#diagramdata) | Точки карты стёкол n–V: {name, nd, vd, тип, цвет} (данные для построения/подсветки) | `source`, `highlight`, `limit` | {count, glasses: [{name, nd, vd, type, color, highlight}]} |
| [`diagram.glasses`](#diagramglasses) | Данные карты стёкол: марки каталога ГОСТ с nd/vd, типом и цветом диаграммы | `type` | список {name, nd, vd, type, color} |
| [`diagram.pick`](#diagrampick) | Выборка стекла по позиции на карте: ближайшие к заданной точке (nd, Vd) марки — евклидова метрика, нормированная на окно карты | `nd`, `vd`, `source`, `limit` | {nd, vd, count, nearest: {...}, matches: [{name, nd, vd, d_nd, d_vd, dist, type, source}]} |
| [`diagram.render`](#diagramrender) | Диаграмма стёкол n–V (PNG): nd против vd по каталогу ГОСТ, стекла системы — подсветкой | `output`, `highlight`, `file`, `system`, `lbo_index`, `lbo_name` | {output, size_bytes, num_glasses, highlighted} |
| [`diagram.system`](#diagramsystem) | Стёкла системы на карте n–Vd: для каждой марки — nd/Vd, тип, семейство, источники; свод — сколько стёкол системы в каких типах/семействах/зонах Vd | `file`, `system`, `lbo_index`, `lbo_name` | {glasses: [{glass, found, nd, vd, type, family, sources, vd_band}], summary: {total, found, not_found, by_type, by_family, by_vd_band, outside_view}} |
| [`diagram.type.stats`](#diagramtypestats) | Диаграмма Аббе по типам: плотность каждого типа — счётчик, центроид (nd, Vd), разброс и диапазоны | `source` | {total, types: [{type, family, count, nd_mean, nd_std, vd_mean, vd_std, nd_min, nd_max, vd_min, vd_max}], unclassified} |
| [`diagram.types`](#diagramtypes) | Типы стёкол (К/БК/ТК/ТФ/…) и их представительство в каталогах | `source` | {types: [{type, count}]} |

## Параметры и результаты

### diagram.bbox

Границы диапазона nd/Vd каталога (bbox реальных стёкол), стандартное окно карты и выбросы за окно

**Returns:** {total, bbox: {nd_min, nd_max, vd_min, vd_max}, view, outside_view, outliers: [{name, nd, vd, source}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |

### diagram.coverage

Покрытие каталога на карте n–Vd: гистограмма плотности по сетке окна просмотра, занятость ячеек и самые населённые зоны

**Returns:** {total, in_view, outside_view, vd_edges, nd_edges, cells: [{i, j, vd_from, vd_to, nd_from, nd_to, count}], occupied, occupancy_pct, top: [{i, j, count, names}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |
| `vd_bins` | `int` | — | `6` | — | ячеек по Vd (по умолчанию 6) |
| `nd_bins` | `int` | — | `8` | — | ячеек по nd (по умолчанию 8) |
| `top_cells` | `int` | — | `5` | — | сколько ячеек в «топе» (0 — не считать) |

### diagram.crown.flint

Кроны против флинтов по зонам Vd: счётчики семейств в полосах Vd, диапазоны семейств и граница смешанных зон (карта n–Vd)

**Returns:** {vd_step, bands: [{vd_from, vd_to, crown, flint, other}], family_stats: {crown/flint/other: {count, vd_min, vd_max}}, mixed_bands, vd_overlap, outside}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |
| `vd_step` | `float` | — | `10.0` | — | ширина полосы Vd (по умолчанию 10) |

### diagram.data

Точки карты стёкол n–V: {name, nd, vd, тип, цвет} (данные для построения/подсветки)

**Returns:** {count, glasses: [{name, nd, vd, type, color, highlight}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — ГОСТ+.FIL) |
| `highlight` | `list` | — | `null` | — | имена стёкол системы для пометки |
| `limit` | `int` | — | `null` | — | максимум точек (по умолчанию — все) |

### diagram.glasses

Данные карты стёкол: марки каталога ГОСТ с nd/vd, типом и цветом диаграммы

**Returns:** список {name, nd, vd, type, color}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `type` | `str` | — | `null` | — | фильтр по типу (префикс марки: К, ТФ, БК, ...) |

### diagram.pick

Выборка стекла по позиции на карте: ближайшие к заданной точке (nd, Vd) марки — евклидова метрика, нормированная на окно карты

**Returns:** {nd, vd, count, nearest: {...}, matches: [{name, nd, vd, d_nd, d_vd, dist, type, source}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `nd` | `float` | да | `null` | — | показатель преломления nd точки |
| `vd` | `float` | да | `null` | — | число Аббе Vd точки |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |
| `limit` | `int` | — | `10` | — | сколько ближайших вернуть |

### diagram.render

Диаграмма стёкол n–V (PNG): nd против vd по каталогу ГОСТ, стекла системы — подсветкой

**Returns:** {output, size_bytes, num_glasses, highlighted}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `output` | `str` | да | `null` | — | путь к PNG-файлу |
| `highlight` | `list` | — | `null` | — | марки стёкол для подсветки (список имён) |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### diagram.system

Стёкла системы на карте n–Vd: для каждой марки — nd/Vd, тип, семейство, источники; свод — сколько стёкол системы в каких типах/семействах/зонах Vd

**Returns:** {glasses: [{glass, found, nd, vd, type, family, sources, vd_band}], summary: {total, found, not_found, by_type, by_family, by_vd_band, outside_view}}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### diagram.type.stats

Диаграмма Аббе по типам: плотность каждого типа — счётчик, центроид (nd, Vd), разброс и диапазоны

**Returns:** {total, types: [{type, family, count, nd_mean, nd_std, vd_mean, vd_std, nd_min, nd_max, vd_min, vd_max}], unclassified}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |

### diagram.types

Типы стёкол (К/БК/ТК/ТФ/…) и их представительство в каталогах

**Returns:** {types: [{type, count}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |

