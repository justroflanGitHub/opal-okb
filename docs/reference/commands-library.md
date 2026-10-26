# Категория library

8 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`library.batch`](#librarybatch) | Пакетный прогон по записям .LBO с фильтром: метрика поверх существующих движков (ТЗ §2.4) | `file`, `metric`, `filter`, `limit` | {metric, count, rows: [{name, ok, <метрики>}]} |
| [`library.categories`](#librarycategories) | Категории библиотеки с числом записей | — | список {name, count} |
| [`library.dirs`](#librarydirs) | Каталоги данных библиотеки (OPJ/LBO): пути и наличие | — | {base_dir, opj_dir, lbo_dir, opj_count, lbo_count} |
| [`library.entries`](#libraryentries) | Записи категории библиотеки (генераторы/OPJ/LBO) | `category` | {category, entries: [{name, file\|generator\|lbo_path}]} |
| [`library.generators`](#librarygenerators) | Генераторы систем в библиотеке (параметрические) | — | список {name, generator} |
| [`library.load`](#libraryload) | Загрузить систему из библиотеки в контекст REPL (по имени записи: генератор/.OPJ/LBO) | `name`, `category`, `as_name` | {name, system} — система в контексте |
| [`library.search`](#librarysearch) | Поиск по всем категориям библиотеки (подстрока имени) | `query`, `limit` | {total, matches: [{category, name, file?, generator?}]} |
| [`library.summary`](#librarysummary) | Библиотека систем: категории, счётчики, итог | — | {categories: [{name, count}], total} |

## Параметры и результаты

### library.batch

Пакетный прогон по записям .LBO с фильтром: метрика поверх существующих движков (ТЗ §2.4)

**Returns:** {metric, count, rows: [{name, ok, <метрики>}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к .lbo |
| `metric` | `str` | — | `"paraxial"` | `["surfaces", "paraxial", "seidel", "spot_rms"]` | surfaces\|paraxial\|seidel\|spot_rms |
| `filter` | `str` | — | `null` | — | подстрока имени записи |
| `limit` | `int` | — | `50` | — | максимум записей |

### library.categories

Категории библиотеки с числом записей

**Returns:** список {name, count}

### library.dirs

Каталоги данных библиотеки (OPJ/LBO): пути и наличие

**Returns:** {base_dir, opj_dir, lbo_dir, opj_count, lbo_count}

### library.entries

Записи категории библиотеки (генераторы/OPJ/LBO)

**Returns:** {category, entries: [{name, file\|generator\|lbo_path}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `category` | `str` | да | `null` | — | имя категории (см. library.categories) |

### library.generators

Генераторы систем в библиотеке (параметрические)

**Returns:** список {name, generator}

### library.load

Загрузить систему из библиотеки в контекст REPL (по имени записи: генератор/.OPJ/LBO)

**Returns:** {name, system} — система в контексте

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | имя записи (подстрока; см. library.search) |
| `category` | `str` | — | `null` | — | ограничить категорию |
| `as_name` | `str` | — | `null` | — | ключ в контексте (по умолчанию — имя записи) |

### library.search

Поиск по всем категориям библиотеки (подстрока имени)

**Returns:** {total, matches: [{category, name, file?, generator?}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `query` | `str` | да | `null` | — | подстрока имени |
| `limit` | `int` | — | `50` | — | максимум строк |

### library.summary

Библиотека систем: категории, счётчики, итог

**Returns:** {categories: [{name, count}], total}

