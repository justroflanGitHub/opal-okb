# Категория file

13 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`file.bench`](#filebench) | Замер времени работы с файлом системы: повторные загрузка (commands.systemio.load_system) и параксиальный прогон (domain.calculations.paraxial_trace) — min/mean/max, мс | `file`, `repeats`, `lbo_index`, `lbo_name` | {file, format, repeats, size_bytes, num_surfaces, load: {min_ms, mean_ms, max_ms}, trace: {…}, total_ms} |
| [`file.checksum`](#filechecksum) | Контрольная сумма файла (md5/sha1/sha256) | `file`, `algo` | {file, algo, hex, size_bytes} |
| [`file.compare.paraxial`](#filecompareparaxial) | Сравнение параксиальных характеристик двух систем | `file_a`, `file_b` | строки {metric, a, b, delta} |
| [`file.compare.seidel`](#filecompareseidel) | Сравнение сумм Зейделя двух систем | `file_a`, `file_b` | строки {sum, a, b, delta} |
| [`file.compare.spot`](#filecomparespot) | Сравнение пятна рассеяния двух систем (RMS, мм) | `file_a`, `file_b`, `num_rays` | {a: {rms, num_points}, b: {rms, num_points}, delta_rms} |
| [`file.convert`](#fileconvert) | Конвертировать файл системы (.opj↔.json, .lbo→.json/.opj) | `src`, `dst`, `lbo_index`, `lbo_name` | пути и форматы конвертации |
| [`file.diff`](#filediff) | Структурное сравнение двух систем: поверхности (R/d/стекло), поля, λ | `file_a`, `file_b` | {identical, differences: [{surface?, field, a, b}], count} |
| [`file.export.protocol`](#fileexportprotocol) | Экспорт протокола расчёта в .txt: параксиальные характеристики, суммы Зейделя, таблица поверхностей | `file`, `system`, `lbo_index`, `lbo_name`, `out` | путь сохранённого протокола + сводка |
| [`file.formats`](#fileformats) | Поддерживаемые форматы файлов оптических систем | — | словарь форматов: расширения, чтение/запись, описание |
| [`file.info`](#fileinfo) | Информация о файле системы: формат, поверхности, стёкла | `file`, `lbo_index`, `lbo_name` | сводка: формат, имя, счётчики, стёкла |
| [`file.open`](#fileopen) | Загрузить систему из файла (.opj/.lbo/.json) по расширению | `file`, `lbo_index`, `lbo_name` | сериализованная система (+ entries для .lbo) |
| [`file.save`](#filesave) | Сохранить систему в файл (формат по расширению цели) | `file`, `src`, `system`, `lbo_index`, `lbo_name` | путь сохранённого файла и формат |
| [`file.stat`](#filestat) | Метаданные файла БЕЗ загрузки системы: размер, время модификации, расширение и формат по расширению (os.stat + детект commands.systemio; содержимое не читается — в отличие от file.info/file.checksum) | `file` | {file, abs, size_bytes, mtime_epoch, mtime_iso, extension, format} |

## Параметры и результаты

### file.bench

Замер времени работы с файлом системы: повторные загрузка (commands.systemio.load_system) и параксиальный прогон (domain.calculations.paraxial_trace) — min/mean/max, мс

**Returns:** {file, format, repeats, size_bytes, num_surfaces, load: {min_ms, mean_ms, max_ms}, trace: {…}, total_ms}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к файлу системы |
| `repeats` | `int` | — | `3` | — | повторов замера 1–20 (по умолчанию 3) |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo |

### file.checksum

Контрольная сумма файла (md5/sha1/sha256)

**Returns:** {file, algo, hex, size_bytes}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к файлу |
| `algo` | `str` | — | `"sha256"` | `["md5", "sha1", "sha256"]` | алгоритм хеша |

### file.compare.paraxial

Сравнение параксиальных характеристик двух систем

**Returns:** строки {metric, a, b, delta}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file_a` | `str` | да | `null` | — | файл первой системы |
| `file_b` | `str` | да | `null` | — | файл второй системы |

### file.compare.seidel

Сравнение сумм Зейделя двух систем

**Returns:** строки {sum, a, b, delta}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file_a` | `str` | да | `null` | — | файл первой системы |
| `file_b` | `str` | да | `null` | — | файл второй системы |

### file.compare.spot

Сравнение пятна рассеяния двух систем (RMS, мм)

**Returns:** {a: {rms, num_points}, b: {rms, num_points}, delta_rms}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file_a` | `str` | да | `null` | — | файл первой системы |
| `file_b` | `str` | да | `null` | — | файл второй системы |
| `num_rays` | `int` | — | `30` | — | лучей точечной диаграммы |

### file.convert

Конвертировать файл системы (.opj↔.json, .lbo→.json/.opj)

**Returns:** пути и форматы конвертации

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `src` | `str` | да | `null` | — | исходный файл |
| `dst` | `str` | да | `null` | — | целевой файл (.opj/.json) |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo |

### file.diff

Структурное сравнение двух систем: поверхности (R/d/стекло), поля, λ

**Returns:** {identical, differences: [{surface?, field, a, b}], count}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file_a` | `str` | да | `null` | — | файл первой системы |
| `file_b` | `str` | да | `null` | — | файл второй системы |

### file.export.protocol

Экспорт протокола расчёта в .txt: параксиальные характеристики, суммы Зейделя, таблица поверхностей

**Returns:** путь сохранённого протокола + сводка

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | да | `null` | — | целевой путь протокола (.txt) |

### file.formats

Поддерживаемые форматы файлов оптических систем

**Returns:** словарь форматов: расширения, чтение/запись, описание

### file.info

Информация о файле системы: формат, поверхности, стёкла

**Returns:** сводка: формат, имя, счётчики, стёкла

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к файлу системы |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo |

### file.open

Загрузить систему из файла (.opj/.lbo/.json) по расширению

**Returns:** сериализованная система (+ entries для .lbo)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к файлу системы |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### file.save

Сохранить систему в файл (формат по расширению цели)

**Returns:** путь сохранённого файла и формат

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | целевой путь (.opj/.json) |
| `src` | `str` | — | `null` | — | исходный файл системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo |

### file.stat

Метаданные файла БЕЗ загрузки системы: размер, время модификации, расширение и формат по расширению (os.stat + детект commands.systemio; содержимое не читается — в отличие от file.info/file.checksum)

**Returns:** {file, abs, size_bytes, mtime_epoch, mtime_iso, extension, format}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к файлу |

