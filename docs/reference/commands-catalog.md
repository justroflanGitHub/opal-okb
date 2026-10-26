# Категория catalog

21 команда.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`catalog.achromat.options`](#catalogachromatoptions) | Варианты ахроматического дублета по парам стёкол (дизайнер achromat.design_achromat): радиусы/толщины | `focal_length`, `crown`, `flint`, `limit` | {focal_length, options: [{crown, flint, radii, ok}]} |
| [`catalog.agf.status`](#catalogagfstatus) | AGF-каталог Zemax: доступность и число стёкол | — | {available, count} |
| [`catalog.availability`](#catalogavailability) | Доступность марки стекла: в каких источниках есть (ГОСТ/.FIL/AGF), nd/Vd каждого вхождения и синонимы (латиница ↔ русская транслитерация AGF) | `name` | {query, canonical, primary, sources: [{source, name, nd, vd, alias}], synonyms} |
| [`catalog.glass.abbe`](#catalogglassabbe) | Число Аббе Vd расчётом n(λ) по формуле каталога (F 486.1 / d 587.6 / C 656.3 нм) | `name` | {name, nd, nF, nd_line, nC, vd_calc, vd_catalog} |
| [`catalog.glass.compare`](#catalogglasscompare) | Сравнение двух стёкол: Δnd, ΔVd, n(λ) | `a`, `b`, `wl` | {a, b, d_nd, d_vd, n_a, n_b, d_n} |
| [`catalog.glass.dispersion`](#catalogglassdispersion) | n(λ) стекла на списке длин волн | `name`, `wavelengths` | {name, source, rows: [{wl, n}]} |
| [`catalog.glass.filter`](#catalogglassfilter) | Фильтр стёкол по диапазонам nd/Vd (подбор замен) | `nd_min`, `nd_max`, `vd_min`, `vd_max`, `source`, `order_by`, `descending`, `limit` | {total, entries: [{name, nd, vd, source}]} |
| [`catalog.glass.get`](#catalogglassget) | Стекло по марке: nd, vd, коэффициенты дисперсии (+n(λ)) | `name`, `wl` | данные стекла (+n при указании wl) |
| [`catalog.glass.list`](#catalogglasslist) | Постраничный список стёкол (имя, nd, Vd) по источнику | `source`, `limit`, `offset`, `order_by`, `descending` | {total, entries: [{name, nd, vd, source}]} |
| [`catalog.glass.multi`](#catalogglassmulti) | Стёкла, доступные сразу в нескольких источниках (ГОСТ/.FIL/AGF, сопоставление по имени/алиасу): nd/Vd каждого вхождения и разброс nd между источниками | `min_sources`, `limit` | {total, entries: [{name, sources: {источник: {name, nd, vd}}, sources_count, d_nd, d_vd}]} |
| [`catalog.glass.pairs`](#catalogglasspairs) | Пары крон+флинт для ахромата (ΔVd ≥ min_vd_diff) | `name`, `min_vd_diff`, `limit` | {pairs: [{crown, flint, vd_crown, vd_flint, d_vd}]} |
| [`catalog.glass.range`](#catalogglassrange) | Кривая дисперсии n(λ) по диапазону | `name`, `wl_min`, `wl_max`, `steps` | {name, source, points: [{wl, n}], steps} |
| [`catalog.glass.search`](#catalogglasssearch) | Поиск стёкол по подстроке марки во всех каталогах | `query`, `limit` | список совпадений {name, source, nd, vd} |
| [`catalog.glass.similar`](#catalogglasssimilar) | Соседние стёкла по (nd, Vd) — кандидаты на замену | `name`, `nd_tol`, `vd_tol`, `limit` | {name, matches: [{name, d_nd, d_vd, source}]} |
| [`catalog.glass.valid`](#catalogglassvalid) | Применимость стекла на длине волны (диапазон каталога + n) | `name`, `wl` | {name, wl, in_range, lam_min, lam_max, n} |
| [`catalog.info`](#cataloginfo) | Источники данных: число стёкол по каталогам + библиотека | — | счётчики стёкол (gost/fil/agf) и библиотеки систем |
| [`catalog.library.create`](#cataloglibrarycreate) | Система из записи библиотеки (catalog/library): генератор, standalone .OPJ или запись .LBO | `generator`, `file`, `lbo_path`, `lbo_filename`, `name`, `out` | сериализованная система (+saved при out) |
| [`catalog.library.list`](#cataloglibrarylist) | Библиотека систем: генераторы, .OPJ архив, .LBO библиотеки | — | категории библиотеки с записями |
| [`catalog.sources`](#catalogsources) | Источники данных о стёклах: состав и охват | — | по источникам: счётчик, диапазоны nd/Vd |
| [`catalog.sources.compare`](#catalogsourcescompare) | Пересечения имён стёкол между источниками (ГОСТ/.FIL/AGF; AGF — по русским алиасам): пары, общее пересечение, образцы | `limit` | {counts, pairwise: {gost_fil/gost_agf/fil_agf: {count, sample}}, all_three: {count, sample}, union, unique} |
| [`catalog.stats`](#catalogstats) | Свод по всем источникам стёкол: счётчики всего/реальных/отфильтрованных, объединение имён, стёкла в нескольких источниках, уникальные | — | {sources: {gost/fil/agf: {total, real, filtered}}, union, multi_source, unique: {источник: count}} |

## Параметры и результаты

### catalog.achromat.options

Варианты ахроматического дублета по парам стёкол (дизайнер achromat.design_achromat): радиусы/толщины

**Returns:** {focal_length, options: [{crown, flint, radii, ok}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `focal_length` | `float` | да | `null` | — | фокусное расстояние, мм |
| `crown` | `str` | — | `null` | — | крон (по умолчанию — перебор К8/БК10) |
| `flint` | `str` | — | `null` | — | флинт (по умолчанию — ТФ5/ТФ3/Ф4) |
| `limit` | `int` | — | `6` | — | максимум вариантов |

### catalog.agf.status

AGF-каталог Zemax: доступность и число стёкол

**Returns:** {available, count}

### catalog.availability

Доступность марки стекла: в каких источниках есть (ГОСТ/.FIL/AGF), nd/Vd каждого вхождения и синонимы (латиница ↔ русская транслитерация AGF)

**Returns:** {query, canonical, primary, sources: [{source, name, nd, vd, alias}], synonyms}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | марка стекла |

### catalog.glass.abbe

Число Аббе Vd расчётом n(λ) по формуле каталога (F 486.1 / d 587.6 / C 656.3 нм)

**Returns:** {name, nd, nF, nd_line, nC, vd_calc, vd_catalog}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | марка стекла |

### catalog.glass.compare

Сравнение двух стёкол: Δnd, ΔVd, n(λ)

**Returns:** {a, b, d_nd, d_vd, n_a, n_b, d_n}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `a` | `str` | да | `null` | — | марка первого стекла |
| `b` | `str` | да | `null` | — | марка второго стекла |
| `wl` | `float` | — | `0.58756` | — | λ для сравнения n, мкм |

### catalog.glass.dispersion

n(λ) стекла на списке длин волн

**Returns:** {name, source, rows: [{wl, n}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | марка стекла |
| `wavelengths` | `list` | да | `null` | — | список λ, мкм |

### catalog.glass.filter

Фильтр стёкол по диапазонам nd/Vd (подбор замен)

**Returns:** {total, entries: [{name, nd, vd, source}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `nd_min` | `float` | — | `null` | — | нижняя граница nd |
| `nd_max` | `float` | — | `null` | — | верхняя граница nd |
| `vd_min` | `float` | — | `null` | — | нижняя граница Vd |
| `vd_max` | `float` | — | `null` | — | верхняя граница Vd |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |
| `order_by` | `str` | — | `"vd"` | `["name", "nd", "vd"]` | ключ сортировки |
| `descending` | `bool` | — | `false` | — | обратный порядок |
| `limit` | `int` | — | `50` | — | строк в ответе |

### catalog.glass.get

Стекло по марке: nd, vd, коэффициенты дисперсии (+n(λ))

**Returns:** данные стекла (+n при указании wl)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | марка стекла (К8, ТФ1, TK16…) |
| `wl` | `float` | — | `null` | — | длина волны, мкм — добавить n(λ) |

### catalog.glass.list

Постраничный список стёкол (имя, nd, Vd) по источнику

**Returns:** {total, entries: [{name, nd, vd, source}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |
| `limit` | `int` | — | `50` | — | строк в ответе |
| `offset` | `int` | — | `0` | — | смещение страницы |
| `order_by` | `str` | — | `"name"` | `["name", "nd", "vd"]` | ключ сортировки |
| `descending` | `bool` | — | `false` | — | обратный порядок |

### catalog.glass.multi

Стёкла, доступные сразу в нескольких источниках (ГОСТ/.FIL/AGF, сопоставление по имени/алиасу): nd/Vd каждого вхождения и разброс nd между источниками

**Returns:** {total, entries: [{name, sources: {источник: {name, nd, vd}}, sources_count, d_nd, d_vd}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `min_sources` | `int` | — | `2` | — | минимум источников (2 или 3) |
| `limit` | `int` | — | `50` | — | максимум строк |

### catalog.glass.pairs

Пары крон+флинт для ахромата (ΔVd ≥ min_vd_diff)

**Returns:** {pairs: [{crown, flint, vd_crown, vd_flint, d_vd}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | — | `null` | — | марка одного из стёкол пары (фильтр) |
| `min_vd_diff` | `float` | — | `15.0` | — | минимальная разность Vd |
| `limit` | `int` | — | `50` | — | максимум пар |

### catalog.glass.range

Кривая дисперсии n(λ) по диапазону

**Returns:** {name, source, points: [{wl, n}], steps}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | марка стекла |
| `wl_min` | `float` | — | `0.4` | — | начало диапазона, мкм |
| `wl_max` | `float` | — | `0.8` | — | конец диапазона, мкм |
| `steps` | `int` | — | `10` | — | число точек |

### catalog.glass.search

Поиск стёкол по подстроке марки во всех каталогах

**Returns:** список совпадений {name, source, nd, vd}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `query` | `str` | да | `null` | — | подстрока марки (К8, ТФ, BK…) |
| `limit` | `int` | — | `50` | — | максимум записей в ответе |

### catalog.glass.similar

Соседние стёкла по (nd, Vd) — кандидаты на замену

**Returns:** {name, matches: [{name, d_nd, d_vd, source}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | марка стекла-эталона |
| `nd_tol` | `float` | — | `0.01` | — | допуск по nd |
| `vd_tol` | `float` | — | `3.0` | — | допуск по Vd |
| `limit` | `int` | — | `50` | — | максимум строк |

### catalog.glass.valid

Применимость стекла на длине волны (диапазон каталога + n)

**Returns:** {name, wl, in_range, lam_min, lam_max, n}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | марка стекла |
| `wl` | `float` | да | `null` | — | λ, мкм |

### catalog.info

Источники данных: число стёкол по каталогам + библиотека

**Returns:** счётчики стёкол (gost/fil/agf) и библиотеки систем

### catalog.library.create

Система из записи библиотеки (catalog/library): генератор, standalone .OPJ или запись .LBO

**Returns:** сериализованная система (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `generator` | `str` | — | `null` | — | имя генератора библиотеки (achromat_100, …) |
| `file` | `str` | — | `null` | — | путь к standalone .OPJ файлу |
| `lbo_path` | `str` | — | `null` | — | путь к .LBO библиотеке |
| `lbo_filename` | `str` | — | `null` | — | имя .OPJ-записи внутри .LBO |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### catalog.library.list

Библиотека систем: генераторы, .OPJ архив, .LBO библиотеки

**Returns:** категории библиотеки с записями

### catalog.sources

Источники данных о стёклах: состав и охват

**Returns:** по источникам: счётчик, диапазоны nd/Vd

### catalog.sources.compare

Пересечения имён стёкол между источниками (ГОСТ/.FIL/AGF; AGF — по русским алиасам): пары, общее пересечение, образцы

**Returns:** {counts, pairwise: {gost_fil/gost_agf/fil_agf: {count, sample}}, all_three: {count, sample}, union, unique}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `limit` | `int` | — | `10` | — | размер образцов-списков |

### catalog.stats

Свод по всем источникам стёкол: счётчики всего/реальных/отфильтрованных, объединение имён, стёкла в нескольких источниках, уникальные

**Returns:** {sources: {gost/fil/agf: {total, real, filtered}}, union, multi_source, unique: {источник: count}}

