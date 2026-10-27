# Категория registry

8 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`registry.categories`](#registrycategories) | Категории реестра с числом команд и описанием (описание — карта модуля, для неизвестных категорий null) | — | {count, categories: [{name, commands, description}]} |
| [`registry.category.info`](#registrycategoryinfo) | Команды одной категории: описание, сигнатура параметров и returns каждой команды | `category` | {category, description, count, commands: [{name, description, signature, params, returns}]} |
| [`registry.export`](#registryexport) | Снимок реестра целиком в JSON-файл (для агентов): счётчики, категории и схемы всех команд; запись — exportio (.json) | `out` | {out, format, size_bytes, preview, total, num_categories} |
| [`registry.list`](#registrylist) | Перечень команд реестра (по имени, с категорией и описанием); фильтры — одна категория и/или префикс имени, без фильтров — все команды | `category`, `prefix` | {total, shown, rows: [{name, category, description}]} |
| [`registry.params`](#registryparams) | Команды, принимающие параметр с данным именем (например 'file' или 'num_rays'); опциональный фильтр по типу параметра | `param`, `type` | {param, type, count, rows: [{name, category, type, required, default, help}]} |
| [`registry.schema`](#registryschema) | Схема команды: имя, категория, описание, параметры (имя/тип/обязательность/умолчание/choices/подсказка) и описание результата | `name` | {name, category, description, params: [{name, type, required, default, choices, help}], returns} |
| [`registry.search`](#registrysearch) | Поиск команд по подстроке без регистра: имя, описание или категория; в каждой находке — где совпало | `query`, `limit` | {query, total, shown, rows: [{name, category, description, matched_in}]} |
| [`registry.stats`](#registrystats) | Статистика реестра: всего команд, число категорий, счётчик команд по каждой категории | — | {total, num_categories, categories: {имя: число}} |

## Параметры и результаты

### registry.categories

Категории реестра с числом команд и описанием (описание — карта модуля, для неизвестных категорий null)

**Returns:** {count, categories: [{name, commands, description}]}

### registry.category.info

Команды одной категории: описание, сигнатура параметров и returns каждой команды

**Returns:** {category, description, count, commands: [{name, description, signature, params, returns}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `category` | `str` | да | `null` | — | имя категории (например 'plot') |

### registry.export

Снимок реестра целиком в JSON-файл (для агентов): счётчики, категории и схемы всех команд; запись — exportio (.json)

**Returns:** {out, format, size_bytes, preview, total, num_categories}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `out` | `str` | да | `null` | — | путь к .json-файлу снимка |

### registry.list

Перечень команд реестра (по имени, с категорией и описанием); фильтры — одна категория и/или префикс имени, без фильтров — все команды

**Returns:** {total, shown, rows: [{name, category, description}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `category` | `str` | — | `null` | — | категория (например 'calc'; см. registry.categories) |
| `prefix` | `str` | — | `null` | — | префикс имени (например 'file.lbo.') |

### registry.params

Команды, принимающие параметр с данным именем (например 'file' или 'num_rays'); опциональный фильтр по типу параметра

**Returns:** {param, type, count, rows: [{name, category, type, required, default, help}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `param` | `str` | да | `null` | — | имя параметра (например 'wl') |
| `type` | `str` | — | `null` | `["str", "float", "int", "bool", "list", "dict"]` | только параметры этого типа (str/float/int/bool/list/dict) |

### registry.schema

Схема команды: имя, категория, описание, параметры (имя/тип/обязательность/умолчание/choices/подсказка) и описание результата

**Returns:** {name, category, description, params: [{name, type, required, default, choices, help}], returns}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | имя команды (например 'calc.paraxial') |

### registry.search

Поиск команд по подстроке без регистра: имя, описание или категория; в каждой находке — где совпало

**Returns:** {query, total, shown, rows: [{name, category, description, matched_in}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `query` | `str` | да | `null` | — | подстрока поиска (непустая) |
| `limit` | `int` | — | `null` | — | максимум находок в ответе (по умолчанию — все) |

### registry.stats

Статистика реестра: всего команд, число категорий, счётчик команд по каждой категории

**Returns:** {total, num_categories, categories: {имя: число}}

