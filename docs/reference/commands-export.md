# Категория export

47 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`aber.fan.export`](#aberfanexport) | Веер аберраций (поперечные/волновые по зрачку) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `num_rays`, `field_y`, `out` | файл выгрузки + счётчики строк |
| [`aber.mtf_geo.export`](#abermtf_geoexport) | Геометрическая ЧКХ [freq, T, S] → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `max_freq`, `num_freqs`, `num_rays`, `field_y`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`adv.enc.export`](#advencexport) | Геометрическая ФКЭ (r_um, доля) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`adv.lsf.export`](#advlsfexport) | ФРЛ (профиль по оси, мкм) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `direction`, `num_rays`, `field_y`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`analyze.field_aberrations.export`](#analyzefield_aberrationsexport) | Внеосевые аберрации по полям → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `fields`, `num_fan_rays`, `out` | файл выгрузки + счётчики строк |
| [`analyze.ray_fan.export`](#analyzeray_fanexport) | Координаты лучей веера по поверхностям → CSV/JSON (§4.7 «Просмотр координат лучей») | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `pupil_range`, `wl`, `field_y`, `out` | файл выгрузки: строка = точка луча на поверхности |
| [`analyze.spot.export`](#analyzespotexport) | Точки точечной диаграммы (мм) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `num_rays`, `field_y`, `sampling`, `out` | файл выгрузки + счётчики строк |
| [`calc.paraxial.export`](#calcparaxialexport) | Параксиальные характеристики → JSON (CSV — строка скаляров) | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | файл выгрузки |
| [`calc.seidel.export`](#calcseidelexport) | Суммы Зейделя (domain) → JSON (CSV — строка скаляров) | `file`, `system`, `lbo_index`, `lbo_name`, `out` | файл выгрузки |
| [`export.aberx.astig.curve`](#exportaberxastigcurve) | Кривая астигматизма t′m/t′s по полям (aberx.astig.curve) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.chrom.focus_shift`](#exportaberxchromfocus_shift) | Хроматический сдвиг EFL/BFD по λ (aberx.chrom.focus_shift) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wls`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.distortion.curve`](#exportaberxdistortioncurve) | Кривая дисторсии по полям (aberx.distortion.curve) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `fit_degree`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.focal.zonal`](#exportaberxfocalzonal) | Зональные фокусы мер./саг. (aberx.focal.zonal) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `zones`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.map.grid`](#exportaberxmapgrid) | Карта поперечных аберраций по полям×зонам (aberx.map.grid) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.rms.grid`](#exportaberxrmsgrid) | СКВ волновой аберрации по полям×λ (aberx.rms.grid) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wls`, `num_rings`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.seidel.shares`](#exportaberxseidelshares) | Вклады поверхностей в суммы Зейделя, % (aberx.seidel.shares) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.spherical.zones`](#exportaberxsphericalzones) | Сферическая аберрация по зонам зрачка (aberx.spherical.zones) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `num_rays`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.spot.grid`](#exportaberxspotgrid) | Пятно RMS/центроид по полям×λ (aberx.spot.grid) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wls`, `num_rays`, `out` | файл выгрузки + счётчики строк |
| [`export.aberx.transverse.zones`](#exportaberxtransversezones) | Поперечные аберрации мер./саг. по зонам (aberx.transverse.zones) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `n_zones`, `zones`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.command`](#exportcommand) | Выполнить любую команду реестра и выгрузить её результат (.json — целиком; .csv — rows/скаляры; .txt — поле text, если есть) | `cmd`, `args`, `out` | результат записи + source-команда |
| [`export.data`](#exportdata) | Записать структуру (dict/list) в JSON-файл | `data`, `out` | {out, format, size_bytes, preview} |
| [`export.diagram.coverage`](#exportdiagramcoverage) | Покрытие каталога на карте n–Vd сеткой (diagram.coverage; строки — ячейки) → CSV/JSON | `source`, `vd_bins`, `nd_bins`, `top_cells`, `out` | файл выгрузки + счётчики строк |
| [`export.diagram.type.stats`](#exportdiagramtypestats) | Диаграмма Аббе по типам марок (diagram.type.stats; строки — типы) → CSV/JSON | `source`, `out` | файл выгрузки + счётчики строк |
| [`export.diffr.mtf`](#exportdiffrmtf) | Дифракционная ЧКХ (частоты + мер/саг срезы) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `grid_size`, `max_freq_lpmm`, `out` | файл выгрузки + cutoff из команды-источника |
| [`export.psf.encircled`](#exportpsfencircled) | ФКЭ ФРТ (r_um, EE) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `defocus`, `out` | файл выгрузки + r50/r80 из команды-источника |
| [`export.rows`](#exportrows) | Записать строки-словари в CSV/JSON (таблица) | `rows`, `columns`, `out` | {out, format, rows, columns, preview} |
| [`export.text`](#exporttext) | Записать текст в .txt (протоколы/отчёты) | `text`, `out` | {out, format, size_bytes, preview} |
| [`export.tracex.fan.zones`](#exporttracexfanzones) | Осевой веер по зонам зрачка (tracex.fan.zones; строки — зоны) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `n_zones`, `zones`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.tracex.meridional`](#exporttracexmeridional) | Меридиональная таблица лучей по поверхностям (tracex.meridional.table) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.tracex.opl`](#exporttracexopl) | Таблица ОПД лучей веера по поверхностям (tracex.opl.table) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.tracex.paraxial.matrices`](#exporttracexparaxialmatrices) | Матрицы ABCD по поверхностям (tracex.paraxial.matrices; строки — поверхности) → CSV/JSON (в .json — и промежутки, и системная матрица) | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.tracex.ray.multi_wl`](#exporttracexraymulti_wl) | Луч на всех λ системы (tracex.ray.multi_wl) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `rho_x`, `rho_y`, `out` | файл выгрузки + счётчики строк |
| [`export.tracex.ray.surfaces`](#exporttracexraysurfaces) | Трасса луча по поверхностям с ОПД (tracex.ray.surfaces) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `x`, `y`, `z`, `k`, `l`, `m`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.tracex.stop.clearance`](#exporttracexstopclearance) | Клиренс луча на апертурной диафрагме (tracex.stop.clearance; скаляры) → CSV (строка)/JSON (целиком) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `rho_x`, `rho_y`, `wl`, `out` | файл выгрузки |
| [`export.tracex.ynu`](#exporttracexynu) | Параксиальная таблица y/n·u (tracex.ynu.table) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`export.zern.coeffs`](#exportzerncoeffs) | Коэффициенты Цернике {n, m, name, coeff} → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `field_y`, `num_rays`, `max_order`, `defocus_offset`, `out` | файл выгрузки + счётчики строк |
| [`seidel.sums.export`](#seidelsumsexport) | Суммы Зейделя (SI..SV + хроматические) → CSV/JSON | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | файл выгрузки (CSV — одна строка сумм) |
| [`tables.field_zones.export`](#tablesfield_zonesexport) | Зоны поля OPAL (относительные высоты) → CSV/JSON | `n_zones`, `out` | файл выгрузки + счётчики строк |
| [`tables.tabax3.export`](#tablestabax3export) | TABAX3 (OPAL-хроматизм) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `wl_main`, `wl_flags`, `field_y`, `out` | файл выгрузки + счётчики строк |
| [`tables.tabbea.export`](#tablestabbeaexport) | TABBEA (виньетирование/освещённость по полю) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`tables.tabeap.export`](#tablestabeapexport) | TABEAP (зоны экранов/прохождения по поверхностям) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`tables.tabesb.export`](#tablestabesbexport) | TABESB (высоты пучков по поверхностям) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`tables.tabgl.export`](#tablestabglexport) | TABGL (характеристики главных лучей) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `n_zones`, `wl`, `out` | файл выгрузки + счётчики строк |
| [`tables.taboc1.export`](#tablestaboc1export) | TABOC1 (остаточные аберрации осевого пучка) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `n_zones`, `out` | файл выгрузки + счётчики строк |
| [`tables.taboc2.export`](#tablestaboc2export) | TABOC2 (волновые аберрации осевого пучка) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `n_zones`, `num_rays`, `columns`, `out` | файл выгрузки + счётчики строк |
| [`tables.tabpr2.export`](#tablestabpr2export) | TABPR2 (хроматизм увеличения/положения по полю) → CSV/JSON/TXT | `file`, `system`, `lbo_index`, `lbo_name`, `wl_main`, `wl_alt`, `n_zones`, `out` | файл выгрузки + счётчики строк |
| [`trace.ray_bundle.export`](#traceray_bundleexport) | Пучок лучей 3D-сетки зрачка (кольца × азимуты) → CSV/JSON (ТЗ §2.4) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rings`, `num_azimuths`, `wl`, `field_y`, `out` | файл: строка = луч (rho, phi, OPL, точка на образце) |

## Параметры и результаты

### aber.fan.export

Веер аберраций (поперечные/волновые по зрачку) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `num_rays` | `int` | — | `30` | — | лучей веера |
| `field_y` | `float` | — | `0.0` | — | поле |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### aber.mtf_geo.export

Геометрическая ЧКХ [freq, T, S] → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `max_freq` | `float` | — | `100.0` | — | максимальная частота, лин/мм |
| `num_freqs` | `int` | — | `20` | — | число частот |
| `num_rays` | `int` | — | `100` | — | лучей точечной диаграммы |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### adv.enc.export

Геометрическая ФКЭ (r_um, доля) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `200` | — | лучей точечной диаграммы |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### adv.lsf.export

ФРЛ (профиль по оси, мкм) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `direction` | `str` | — | `"tangential"` | `["tangential", "sagittal"]` | направление щели |
| `num_rays` | `int` | — | `128` | — | размер сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### analyze.field_aberrations.export

Внеосевые аберрации по полям → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `fields` | `list` | — | `null` | — | список полей (град); по умолчанию — поля системы |
| `num_fan_rays` | `int` | — | `15` | — | лучей в веере на поле |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### analyze.ray_fan.export

Координаты лучей веера по поверхностям → CSV/JSON (§4.7 «Просмотр координат лучей»)

**Returns:** файл выгрузки: строка = точка луча на поверхности

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `9` | — | лучей веера |
| `pupil_range` | `float` | — | `1.0` | — | доля радиуса зрачка |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### analyze.spot.export

Точки точечной диаграммы (мм) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `num_rays` | `int` | — | `50` | — | лучей по стороне сетки / колец |
| `field_y` | `float` | — | `0.0` | — | поле |
| `sampling` | `str` | — | `"grid"` | `["grid", "hexapolar"]` | способ выборки зрачка |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### calc.paraxial.export

Параксиальные характеристики → JSON (CSV — строка скаляров)

**Returns:** файл выгрузки

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### calc.seidel.export

Суммы Зейделя (domain) → JSON (CSV — строка скаляров)

**Returns:** файл выгрузки

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.astig.curve

Кривая астигматизма t′m/t′s по полям (aberx.astig.curve) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | поля (по умолчанию — поля системы) |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.chrom.focus_shift

Хроматический сдвиг EFL/BFD по λ (aberx.chrom.focus_shift) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wls` | `list` | — | `null` | — | λ, мкм (по умолчанию — λ системы) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.distortion.curve

Кривая дисторсии по полям (aberx.distortion.curve) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | поля (по умолчанию — поля системы) |
| `fit_degree` | `int` | — | `3` | — | степень полинома подгонки |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.focal.zonal

Зональные фокусы мер./саг. (aberx.focal.zonal) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле |
| `zones` | `list` | — | `null` | — | явные зоны зрачка |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.map.grid

Карта поперечных аберраций по полям×зонам (aberx.map.grid) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | поля (по умолчанию — поля системы) |
| `num_rays` | `int` | — | `9` | — | лучей веера на поле |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.rms.grid

СКВ волновой аберрации по полям×λ (aberx.rms.grid) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | поля (по умолчанию — поля системы) |
| `wls` | `list` | — | `null` | — | λ, мкм (по умолчанию — λ системы) |
| `num_rings` | `int` | — | `3` | — | кольца гексаполярной сетки зрачка |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.seidel.shares

Вклады поверхностей в суммы Зейделя, % (aberx.seidel.shares) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.spherical.zones

Сферическая аберрация по зонам зрачка (aberx.spherical.zones) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `9` | — | лучей веера |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.spot.grid

Пятно RMS/центроид по полям×λ (aberx.spot.grid) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | поля (по умолчанию — поля системы) |
| `wls` | `list` | — | `null` | — | λ, мкм (по умолчанию — λ системы) |
| `num_rays` | `int` | — | `15` | — | лучей пятна |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.aberx.transverse.zones

Поперечные аберрации мер./саг. по зонам (aberx.transverse.zones) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле |
| `n_zones` | `int` | — | `3` | — | зон (если zones не заданы) |
| `zones` | `list` | — | `null` | — | явные зоны зрачка |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.command

Выполнить любую команду реестра и выгрузить её результат (.json — целиком; .csv — rows/скаляры; .txt — поле text, если есть)

**Returns:** результат записи + source-команда

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `cmd` | `str` | да | `null` | — | имя команды реестра |
| `args` | `dict` | — | `null` | — | аргументы команды (по её схеме) |
| `out` | `str` | да | `null` | — | файл выгрузки |

### export.data

Записать структуру (dict/list) в JSON-файл

**Returns:** {out, format, size_bytes, preview}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `data` | `dict` | да | `null` | — | JSON-сериализуемая структура |
| `out` | `str` | да | `null` | — | файл .json |

### export.diagram.coverage

Покрытие каталога на карте n–Vd сеткой (diagram.coverage; строки — ячейки) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |
| `vd_bins` | `int` | — | `6` | — | ячеек по Vd |
| `nd_bins` | `int` | — | `8` | — | ячеек по nd |
| `top_cells` | `int` | — | `5` | — | топ-ячеек (в .json) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.diagram.type.stats

Диаграмма Аббе по типам марок (diagram.type.stats; строки — типы) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `source` | `str` | — | `null` | `["gost", "fil", "agf"]` | каталог (по умолчанию — все) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.diffr.mtf

Дифракционная ЧКХ (частоты + мер/саг срезы) → CSV/JSON

**Returns:** файл выгрузки + cutoff из команды-источника

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `grid_size` | `int` | — | `64` | — | решётка зрачка (N×N) |
| `max_freq_lpmm` | `float` | — | `null` | — | верхняя частота, лин/мм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.psf.encircled

ФКЭ ФРТ (r_um, EE) → CSV/JSON

**Returns:** файл выгрузки + r50/r80 из команды-источника

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка, длины волн |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.rows

Записать строки-словари в CSV/JSON (таблица)

**Returns:** {out, format, rows, columns, preview}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `rows` | `list` | да | `null` | — | список словарей — строки таблицы |
| `columns` | `list` | — | `null` | — | порядок колонок CSV (по умолчанию — все ключи) |
| `out` | `str` | да | `null` | — | файл .csv/.json |

### export.text

Записать текст в .txt (протоколы/отчёты)

**Returns:** {out, format, size_bytes, preview}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `text` | `str` | да | `null` | — | текст для записи |
| `out` | `str` | да | `null` | — | файл .txt |

### export.tracex.fan.zones

Осевой веер по зонам зрачка (tracex.fan.zones; строки — зоны) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `n_zones` | `int` | — | `3` | — | зон (если zones не заданы) |
| `zones` | `list` | — | `null` | — | явные зоны зрачка |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.tracex.meridional

Меридиональная таблица лучей по поверхностям (tracex.meridional.table) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.tracex.opl

Таблица ОПД лучей веера по поверхностям (tracex.opl.table) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.tracex.paraxial.matrices

Матрицы ABCD по поверхностям (tracex.paraxial.matrices; строки — поверхности) → CSV/JSON (в .json — и промежутки, и системная матрица)

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.tracex.ray.multi_wl

Луч на всех λ системы (tracex.ray.multi_wl) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `rho_x` | `float` | — | `0.0` | — | зрачковая координата ρx |
| `rho_y` | `float` | — | `0.0` | — | зрачковая координата ρy |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.tracex.ray.surfaces

Трасса луча по поверхностям с ОПД (tracex.ray.surfaces) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `x` | `float` | — | `0.0` | — | координата x точки запуска, мм |
| `y` | `float` | — | `0.0` | — | координата y точки запуска, мм |
| `z` | `float` | — | `0.0` | — | координата z точки запуска, мм |
| `k` | `float` | — | `0.0` | — | направляющий косинус k |
| `l` | `float` | — | `0.0` | — | направляющий косинус l |
| `m` | `float` | — | `1.0` | — | направляющий косинус m |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.tracex.stop.clearance

Клиренс луча на апертурной диафрагме (tracex.stop.clearance; скаляры) → CSV (строка)/JSON (целиком)

**Returns:** файл выгрузки

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `rho_x` | `float` | — | `0.0` | — | зрачковая координата ρx |
| `rho_y` | `float` | — | `0.0` | — | зрачковая координата ρy |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.tracex.ynu

Параксиальная таблица y/n·u (tracex.ynu.table) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### export.zern.coeffs

Коэффициенты Цернике {n, m, name, coeff} → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `64` | — | лучей по стороне сетки зрачка |
| `max_order` | `int` | — | `4` | — | максимальный порядок n |
| `defocus_offset` | `float` | — | `0.0` | — | дефокус, длины волн |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### seidel.sums.export

Суммы Зейделя (SI..SV + хроматические) → CSV/JSON

**Returns:** файл выгрузки (CSV — одна строка сумм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.field_zones.export

Зоны поля OPAL (относительные высоты) → CSV/JSON

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `n_zones` | `int` | — | `3` | — | число зон |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.tabax3.export

TABAX3 (OPAL-хроматизм) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl_main` | `float` | — | `null` | — | основная λ пары, мкм |
| `wl_flags` | `list` | — | `null` | — | флаги волн по поверхностям (как chrom.opal) |
| `field_y` | `float` | — | `null` | — | поле главного луча |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.tabbea.export

TABBEA (виньетирование/освещённость по полю) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей (град); по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.tabeap.export

TABEAP (зоны экранов/прохождения по поверхностям) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.tabesb.export

TABESB (высоты пучков по поверхностям) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.tabgl.export

TABGL (характеристики главных лучей) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `n_zones` | `int` | — | `3` | — | зон поля |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.taboc1.export

TABOC1 (остаточные аберрации осевого пучка) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `n_zones` | `int` | — | `4` | — | зон зрачка |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.taboc2.export

TABOC2 (волновые аберрации осевого пучка) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `n_zones` | `int` | — | `4` | — | зон зрачка |
| `num_rays` | `int` | — | `20` | — | лучей веера неизопланатизма |
| `columns` | `list` | — | `null` | — | селектор колонок TABOC2 |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### tables.tabpr2.export

TABPR2 (хроматизм увеличения/положения по полю) → CSV/JSON/TXT

**Returns:** файл выгрузки + счётчики строк

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl_main` | `float` | — | `null` | — | основная λ пары, мкм |
| `wl_alt` | `float` | — | `null` | — | альтернативная λ, мкм |
| `n_zones` | `int` | — | `3` | — | зон поля |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

### trace.ray_bundle.export

Пучок лучей 3D-сетки зрачка (кольца × азимуты) → CSV/JSON (ТЗ §2.4)

**Returns:** файл: строка = луч (rho, phi, OPL, точка на образце)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rings` | `int` | — | `3` | — | колец зрачка |
| `num_azimuths` | `int` | — | `8` | — | азимутов на кольцо |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `out` | `str` | да | `null` | — | файл выгрузки: .csv (строки), .json (структура), .txt (текстовый формат, где есть) |

