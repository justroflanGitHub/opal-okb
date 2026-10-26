# Категория lbo

8 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`file.lbo.count`](#filelbocount) | Число записей .LBO и сколько разобрано в системы | `file` | {count, ok, broken} |
| [`file.lbo.get`](#filelboget) | Система из записи .LBO (по имени записи или индексу) | `file`, `index`, `name` | полная сериализация системы + метаданные записи |
| [`file.lbo.info`](#filelboinfo) | Метаданные .LBO-файла: размер, число записей | `file` | {path, name, size, num_systems} |
| [`file.lbo.list`](#filelbolist) | Записи .LBO-библиотеки: имена файлов, описания, поверхности, предупреждения парсера | `file`, `limit` | {count, ok, entries: [...]} |
| [`file.lbo.save`](#filelbosave) | Извлечь запись .LBO в файл .opj/.json | `file`, `out`, `index`, `name` | {out, format, name} |
| [`file.lbo.save_all`](#filelbosave_all) | Распаковать все записи .LBO в каталог (.opj) | `file`, `dir` | {dir, saved, broken, names: [...]} |
| [`file.lbo.scan`](#filelboscan) | Сканировать каталог с .LBO-библиотеками (без разбора записей) | `dir` | {count, libraries: [{name, num_systems, size, path}]} |
| [`file.lbo.search`](#filelbosearch) | Поиск записей .LBO по подстроке (имя файла/описание) | `file`, `query`, `limit` | {total, entries: [...]} |

## Параметры и результаты

### file.lbo.count

Число записей .LBO и сколько разобрано в системы

**Returns:** {count, ok, broken}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |

### file.lbo.get

Система из записи .LBO (по имени записи или индексу)

**Returns:** полная сериализация системы + метаданные записи

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |
| `index` | `int` | — | `0` | — | индекс записи (0-based) |
| `name` | `str` | — | `null` | — | имя .OPJ-записи (приоритетнее index) |

### file.lbo.info

Метаданные .LBO-файла: размер, число записей

**Returns:** {path, name, size, num_systems}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |

### file.lbo.list

Записи .LBO-библиотеки: имена файлов, описания, поверхности, предупреждения парсера

**Returns:** {count, ok, entries: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |
| `limit` | `int` | — | `null` | — | максимум записей (по умолчанию — все) |

### file.lbo.save

Извлечь запись .LBO в файл .opj/.json

**Returns:** {out, format, name}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |
| `out` | `str` | да | `null` | — | куда сохранить |
| `index` | `int` | — | `0` | — | индекс записи |
| `name` | `str` | — | `null` | — | имя .OPJ-записи (приоритетнее index) |

### file.lbo.save_all

Распаковать все записи .LBO в каталог (.opj)

**Returns:** {dir, saved, broken, names: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |
| `dir` | `str` | да | `null` | — | каталог назначения |

### file.lbo.scan

Сканировать каталог с .LBO-библиотеками (без разбора записей)

**Returns:** {count, libraries: [{name, num_systems, size, path}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `dir` | `str` | да | `null` | — | каталог с .lbo |

### file.lbo.search

Поиск записей .LBO по подстроке (имя файла/описание)

**Returns:** {total, entries: [...]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |
| `query` | `str` | да | `null` | — | подстрока поиска |
| `limit` | `int` | — | `50` | — | максимум записей в ответе |

