# Категория batch

20 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`batch.apply`](#batchapply) | Применить команду-модификацию (system.scale, system.reverse, ...) к копиям всех систем пакета: команда выполняется с file=<путь> и out=<копия> в out_dir | `files`, `cmd`, `args`, `out_dir`, `suffix`, `ext` | {command, out_dir, suffix, ext, count, ok, applied: [{file, out}], errors: [...]} |
| [`batch.changes`](#batchchanges) | Как каждая система изменилась после команды-модификации: метрики до → после → Δ (модификация — во временном файле, исходники не трогаются) | `files`, `cmd`, `args`, `metrics`, `num_rays`, `field_y` | {command, metrics, count, rows: [{file, name, before, after, delta}], errors: [...]} |
| [`batch.check`](#batchcheck) | Пороговая проверка метрики по всем системам пакета: min — «не ниже порога», max — «не выше» (auto — по полярности метрики) | `files`, `metric`, `threshold`, `mode`, `num_rays`, `field_y` | {metric, mode, comparison, threshold, pass, count, rows: [{file, name, <метрика>, pass}], worst, errors: [...]} |
| [`batch.compare`](#batchcompare) | Сравнение каждой системы пакета с эталонным файлом по метрикам (Δ и Δ%) | `files`, `ref`, `metrics`, `num_rays`, `field_y` | {ref, metrics, count, rows: [{file, name, deltas: {метрика: {ref, value, delta, delta_percent}}}], errors} |
| [`batch.convert`](#batchconvert) | Пакетная конвертация систем в другой формат (.opj ↔ .json; .json сохраняет точки поля, .opj-раундтрип их теряет) | `files`, `out_dir`, `ext` | {ext, out_dir, count, ok, converted: [{src, dst}], errors: [...]} |
| [`batch.dedupe`](#batchdedupe) | Одинаковые файлы пакета по контрольной сумме (md5/sha1/sha256; бит-в-бит), группы дубликатов | `files`, `algo` | {algo, total, unique, num_duplicate_files, groups: [{hex, count, files}], errors: [...]} |
| [`batch.dir`](#batchdir) | Собрать список файлов систем в каталоге по расширениям (для параметра files остальных batch.*) | `path`, `extensions`, `recursive` | {dir, extensions, recursive, count, files: [...], skipped} |
| [`batch.export`](#batchexport) | Выгрузить сводные метрики пакета в файл .csv/.json (exportio: строки-системы × колонки-метрики) | `files`, `out`, `metrics`, `num_rays`, `field_y` | {out, format, rows, columns, preview, ok, errors: [...]} |
| [`batch.filter`](#batchfilter) | Отобрать системы пакета по условию на метрику (gt/ge/lt/le/eq/ne/range) | `files`, `metric`, `op`, `value`, `value_min`, `value_max`, `num_rays`, `field_y` | {metric, op, count, total, kept: [{file, name, <метрика>}], errors: [...]} |
| [`batch.info`](#batchinfo) | Обзор пакета: по каждому файлу формат, размер, поверхности, λ, поля, стёкла, длина хода | `files` | {count, ok, rows: [{file, format, size_bytes, num_surfaces, ...}], errors: [...]} |
| [`batch.load`](#batchload) | Загрузить все системы пакета в контекст REPL под именами-базами файлов (текущая система не меняется; коллизии имён — суффиксы _2, _3, ...) | `files` | {count, loaded: [{file, name, num_surfaces}], errors} |
| [`batch.metric`](#batchmetric) | Одна метрика качества по всем системам пакета (efl, F/#, RMS пятна, Штрель, Зейдель, ФКЭ, ...; справочник — batch.metrics) | `files`, `metric`, `num_rays`, `field_y` | {metric, description, unit, better, count, ok, rows: [{file, name, <метрика>}], errors: [...]} |
| [`batch.metrics`](#batchmetrics) | Справочник метрик пакета: имя, описание, единица, полярность («лучше больше/меньше» — для batch.rank/check auto-режимов) | — | {count, metrics: [{name, description, unit, better}]} |
| [`batch.names`](#batchnames) | Имена систем пакета: файл → имя системы из файла (fallback — база имени файла) | `files` | {count, ok, names: [{file, stem, name, num_surfaces}], errors: [...]} |
| [`batch.rank`](#batchrank) | Ранжирование систем по метрике (auto — лучшая система первой: RMS растёт, Штрель падает) + best/worst | `files`, `metric`, `order`, `top`, `num_rays`, `field_y` | {metric, order, count, rows: [{rank, file, name, <метрика>}], best, worst, errors: [...]} |
| [`batch.report`](#batchreport) | Текстовый свод по пакету: таблица метрик по системам + итоги min/max/mean (опция записи .txt) | `files`, `metrics`, `num_rays`, `field_y`, `out` | {text, count, ok, errors: [...], out?} |
| [`batch.run`](#batchrun) | Выполнить команду реестра над каждым файлом пакета (команда получает file=<путь>; данные ответа — параметром include_data) | `files`, `cmd`, `args`, `include_data` | {command, count, ok, rows: [{file, ok, error?, data?}], errors: [...]} |
| [`batch.stats`](#batchstats) | Статистика метрики по пакету: count/min/max/mean/median/СКО + файлы-экстремумы | `files`, `metric`, `num_rays`, `field_y` | {metric, unit, count, min, max, mean, median, stdev, min_file, max_file, errors: [...]} |
| [`batch.summary`](#batchsummary) | Сводная таблица по нескольким метрикам сразу + итоги min/max/mean по каждой метрике | `files`, `metrics`, `num_rays`, `field_y` | {metrics, count, ok, rows: [{file, name, <метрики>...}], summary: {метрика: {min, max, mean, min_file, max_file}}, errors: [...]} |
| [`batch.validate`](#batchvalidate) | Санити-проверки system.validate по всем файлам пакета (структура/апертура/λ/стёкла) с общим вердиктом | `files` | {count, pass, rows: [{file, valid, errors, warnings}], errors: [...]} |

## Параметры и результаты

### batch.apply

Применить команду-модификацию (system.scale, system.reverse, ...) к копиям всех систем пакета: команда выполняется с file=<путь> и out=<копия> в out_dir

**Returns:** {command, out_dir, suffix, ext, count, ok, applied: [{file, out}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `cmd` | `str` | да | `null` | — | команда-модификация (должна принимать out) |
| `args` | `dict` | — | `null` | — | доп. параметры команды (кроме file/out) |
| `out_dir` | `str` | да | `null` | — | каталог для модифицированных копий |
| `suffix` | `str` | — | `"_applied"` | — | суффикс имён копий (по умолчанию '_applied') |
| `ext` | `str` | — | `"json"` | `["opj", "json"]` | формат копий (по умолчанию json — .opj-раундтрип теряет точки поля) |

### batch.changes

Как каждая система изменилась после команды-модификации: метрики до → после → Δ (модификация — во временном файле, исходники не трогаются)

**Returns:** {command, metrics, count, rows: [{file, name, before, after, delta}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `cmd` | `str` | да | `null` | — | команда-модификация (должна принимать out) |
| `args` | `dict` | — | `null` | — | доп. параметры команды (кроме file/out) |
| `metrics` | `list` | — | `null` | — | метрики (по умолчанию ['efl', 'f_number', 'spot_rms']) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.check

Пороговая проверка метрики по всем системам пакета: min — «не ниже порога», max — «не выше» (auto — по полярности метрики)

**Returns:** {metric, mode, comparison, threshold, pass, count, rows: [{file, name, <метрика>, pass}], worst, errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `metric` | `str` | да | `null` | `["SI", "SII", "SIII", "SIV", "SV", "airy_um", "bfd", "cutoff_lpmm", "d90_um", "efl", "epd", "f_number", "magnification", "num_fields", "num_surfaces", "num_wavelengths", "sigma_w", "spot_rms", "spot_rms_poly", "strehl", "track_length"]` | имя метрики (см. batch.metrics) |
| `threshold` | `float` | да | `null` | — | порог метрики |
| `mode` | `str` | — | `null` | `["auto", "min", "max"]` | min/max/auto (по умолчанию auto — по полярности) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.compare

Сравнение каждой системы пакета с эталонным файлом по метрикам (Δ и Δ%)

**Returns:** {ref, metrics, count, rows: [{file, name, deltas: {метрика: {ref, value, delta, delta_percent}}}], errors}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей для сравнения |
| `ref` | `str` | да | `null` | — | эталонный файл системы (.opj/.json/.lbo) |
| `metrics` | `list` | — | `null` | — | метрики (по умолчанию ['efl', 'f_number', 'num_surfaces', 'track_length', 'spot_rms']) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.convert

Пакетная конвертация систем в другой формат (.opj ↔ .json; .json сохраняет точки поля, .opj-раундтрип их теряет)

**Returns:** {ext, out_dir, count, ok, converted: [{src, dst}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `out_dir` | `str` | да | `null` | — | каталог назначения |
| `ext` | `str` | — | `"json"` | `["opj", "json"]` | целевой формат (по умолчанию json) |

### batch.dedupe

Одинаковые файлы пакета по контрольной сумме (md5/sha1/sha256; бит-в-бит), группы дубликатов

**Returns:** {algo, total, unique, num_duplicate_files, groups: [{hex, count, files}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (любые файлы) |
| `algo` | `str` | — | `"md5"` | `["md5", "sha1", "sha256"]` | алгоритм хеша |

### batch.dir

Собрать список файлов систем в каталоге по расширениям (для параметра files остальных batch.*)

**Returns:** {dir, extensions, recursive, count, files: [...], skipped}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `path` | `str` | да | `null` | — | каталог для скана (путь задаётся явно) |
| `extensions` | `list` | — | `null` | — | расширения; по умолчанию ['.opj', '.json'] |
| `recursive` | `bool` | — | `null` | — | обход подкаталогов (по умолчанию false) |

### batch.export

Выгрузить сводные метрики пакета в файл .csv/.json (exportio: строки-системы × колонки-метрики)

**Returns:** {out, format, rows, columns, preview, ok, errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `out` | `str` | да | `null` | — | путь выгрузки (.csv или .json) |
| `metrics` | `list` | — | `null` | — | метрики (по умолчанию ['efl', 'f_number', 'num_surfaces', 'track_length', 'spot_rms']) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.filter

Отобрать системы пакета по условию на метрику (gt/ge/lt/le/eq/ne/range)

**Returns:** {metric, op, count, total, kept: [{file, name, <метрика>}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `metric` | `str` | да | `null` | `["SI", "SII", "SIII", "SIV", "SV", "airy_um", "bfd", "cutoff_lpmm", "d90_um", "efl", "epd", "f_number", "magnification", "num_fields", "num_surfaces", "num_wavelengths", "sigma_w", "spot_rms", "spot_rms_poly", "strehl", "track_length"]` | имя метрики (см. batch.metrics) |
| `op` | `str` | да | `null` | `["gt", "ge", "lt", "le", "eq", "ne", "range"]` | операция сравнения |
| `value` | `float` | — | `null` | — | порог (для gt/ge/lt/le/eq/ne) |
| `value_min` | `float` | — | `null` | — | нижняя граница (для op=range) |
| `value_max` | `float` | — | `null` | — | верхняя граница (для op=range) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.info

Обзор пакета: по каждому файлу формат, размер, поверхности, λ, поля, стёкла, длина хода

**Returns:** {count, ok, rows: [{file, format, size_bytes, num_surfaces, ...}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |

### batch.load

Загрузить все системы пакета в контекст REPL под именами-базами файлов (текущая система не меняется; коллизии имён — суффиксы _2, _3, ...)

**Returns:** {count, loaded: [{file, name, num_surfaces}], errors}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |

### batch.metric

Одна метрика качества по всем системам пакета (efl, F/#, RMS пятна, Штрель, Зейдель, ФКЭ, ...; справочник — batch.metrics)

**Returns:** {metric, description, unit, better, count, ok, rows: [{file, name, <метрика>}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `metric` | `str` | да | `null` | `["SI", "SII", "SIII", "SIV", "SV", "airy_um", "bfd", "cutoff_lpmm", "d90_um", "efl", "epd", "f_number", "magnification", "num_fields", "num_surfaces", "num_wavelengths", "sigma_w", "spot_rms", "spot_rms_poly", "strehl", "track_length"]` | имя метрики (см. batch.metrics) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка (по умолчанию 20 — лёгкий вариант) |
| `field_y` | `float` | — | `null` | — | поле, градусы (по умолчанию 0.0) |

### batch.metrics

Справочник метрик пакета: имя, описание, единица, полярность («лучше больше/меньше» — для batch.rank/check auto-режимов)

**Returns:** {count, metrics: [{name, description, unit, better}]}

### batch.names

Имена систем пакета: файл → имя системы из файла (fallback — база имени файла)

**Returns:** {count, ok, names: [{file, stem, name, num_surfaces}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |

### batch.rank

Ранжирование систем по метрике (auto — лучшая система первой: RMS растёт, Штрель падает) + best/worst

**Returns:** {metric, order, count, rows: [{rank, file, name, <метрика>}], best, worst, errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `metric` | `str` | да | `null` | `["SI", "SII", "SIII", "SIV", "SV", "airy_um", "bfd", "cutoff_lpmm", "d90_um", "efl", "epd", "f_number", "magnification", "num_fields", "num_surfaces", "num_wavelengths", "sigma_w", "spot_rms", "spot_rms_poly", "strehl", "track_length"]` | имя метрики (см. batch.metrics) |
| `order` | `str` | — | `null` | `["auto", "asc", "desc"]` | asc/desc/auto (по умолчанию auto — по полярности) |
| `top` | `int` | — | `null` | — | показать первые N строк (по умолчанию все) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.report

Текстовый свод по пакету: таблица метрик по системам + итоги min/max/mean (опция записи .txt)

**Returns:** {text, count, ok, errors: [...], out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `metrics` | `list` | — | `null` | — | метрики (по умолчанию ['efl', 'f_number', 'num_surfaces', 'track_length', 'spot_rms']) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |
| `out` | `str` | — | `null` | — | записать отчёт в .txt (exportio) |

### batch.run

Выполнить команду реестра над каждым файлом пакета (команда получает file=<путь>; данные ответа — параметром include_data)

**Returns:** {command, count, ok, rows: [{file, ok, error?, data?}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `cmd` | `str` | да | `null` | — | имя команды (например 'calc.paraxial') |
| `args` | `dict` | — | `null` | — | доп. параметры команды (кроме file) |
| `include_data` | `bool` | — | `null` | — | включить данные ответа каждой команды (по умолчанию false) |

### batch.stats

Статистика метрики по пакету: count/min/max/mean/median/СКО + файлы-экстремумы

**Returns:** {metric, unit, count, min, max, mean, median, stdev, min_file, max_file, errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `metric` | `str` | да | `null` | `["SI", "SII", "SIII", "SIV", "SV", "airy_um", "bfd", "cutoff_lpmm", "d90_um", "efl", "epd", "f_number", "magnification", "num_fields", "num_surfaces", "num_wavelengths", "sigma_w", "spot_rms", "spot_rms_poly", "strehl", "track_length"]` | имя метрики (см. batch.metrics) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.summary

Сводная таблица по нескольким метрикам сразу + итоги min/max/mean по каждой метрике

**Returns:** {metrics, count, ok, rows: [{file, name, <метрики>...}], summary: {метрика: {min, max, mean, min_file, max_file}}, errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |
| `metrics` | `list` | — | `null` | — | метрики (по умолчанию ['efl', 'f_number', 'num_surfaces', 'track_length', 'spot_rms']) |
| `num_rays` | `int` | — | `null` | — | лучей сетки зрачка (по умолчанию 20) |
| `field_y` | `float` | — | `null` | — | поле, градусы |

### batch.validate

Санити-проверки system.validate по всем файлам пакета (структура/апертура/λ/стёкла) с общим вердиктом

**Returns:** {count, pass, rows: [{file, valid, errors, warnings}], errors: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `files` | `list` | да | `null` | — | список путей (.opj/.json/.lbo) |

