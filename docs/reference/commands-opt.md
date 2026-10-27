# Категория opt

7 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`opt.goals`](#optgoals) | Справочник критериев оптимизации ЛАП: виды целей, нормы, типы параметров, коды останова | — | kinds/param_types/istop — константы решателя |
| [`opt.merit`](#optmerit) | Оценить цели на системе без оптимизации: значения характеристик и остатки оф(I) = (офт−офз)/офн×офв | `file`, `system`, `lbo_index`, `lbo_name`, `goals` | values/residuals по целям + критерий F |
| [`opt.parse`](#optparse) | Разобрать задание оптимизации во входном языке OPAL (PAR/MF/EQF + pmin/pmax, формат OPALANG §3) | `file`, `system`, `lbo_index`, `lbo_name`, `task`, `task_file` | variables/goals/warnings — готовые spec для opt.run |
| [`opt.rms`](#optrms) | Legacy-оптимизация по RMS пятна рассеяния: DLS (демпфированные НК) или Nelder-Mead Simplex | `file`, `system`, `lbo_index`, `lbo_name`, `variables`, `method`, `max_iter`, `num_rays`, `name`, `save` | мерит RMS до/после + новые значения переменных (+system/saved при name/save) |
| [`opt.run`](#optrun) | Многоцелевая оптимизация ЛАП (аналог OPALLAP): N целей × M переменных, шаг Марквардта, границы-штрафы | `file`, `system`, `lbo_index`, `lbo_name`, `variables`, `goals`, `mode`, `max_iter`, `num_rays`, `include_history`, `name`, `save` | istop/fmin/остатки + новые значения переменных (+system/saved при name/save) |
| [`opt.solve`](#optsolve) | Подогнать один параметр под одну цель (Ньютон по чувствительности; цели — efl/bfd/аберрации/RMS) | `file`, `system`, `lbo_index`, `lbo_name`, `kind`, `target`, `surface`, `param`, `pmin`, `pmax`, `tol`, `max_iter`, `name`, `save` | значение параметра + достигнутое значение характеристики |
| [`opt.variables`](#optvariables) | Варьируемые параметры системы: текущие значения radius/thickness/conic/semi_diameter/glass_index | `file`, `system`, `lbo_index`, `lbo_name` | список {surface, param, value} по всем поверхностям |

## Параметры и результаты

### opt.goals

Справочник критериев оптимизации ЛАП: виды целей, нормы, типы параметров, коды останова

**Returns:** kinds/param_types/istop — константы решателя

### opt.merit

Оценить цели на системе без оптимизации: значения характеристик и остатки оф(I) = (офт−офз)/офн×офв

**Returns:** values/residuals по целям + критерий F

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `goals` | `list` | да | `null` | — | список целей {kind, target, weight, norm, refs} (формат — opt.goals) |

### opt.parse

Разобрать задание оптимизации во входном языке OPAL (PAR/MF/EQF + pmin/pmax, формат OPALANG §3)

**Returns:** variables/goals/warnings — готовые spec для opt.run

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `task` | `str` | — | `null` | — | текст задания (например 'PAR(1)=C/1,D/1; MF(1)=DSA;') |
| `task_file` | `str` | — | `null` | — | путь к файлу задания (.OPT) |

### opt.rms

Legacy-оптимизация по RMS пятна рассеяния: DLS (демпфированные НК) или Nelder-Mead Simplex

**Returns:** мерит RMS до/после + новые значения переменных (+system/saved при name/save)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `variables` | `list` | да | `null` | — | [{surface, param, min, max}, ...] — param только radius/thickness |
| `method` | `str` | — | `"dls"` | `["dls", "simplex"]` | метод оптимизации |
| `max_iter` | `int` | — | `50` | — | максимум итераций |
| `num_rays` | `int` | — | `30` | — | лучей на сторону для spot diagram |
| `name` | `str` | — | `null` | — | сохранить результат в контекст REPL под именем |
| `save` | `str` | — | `null` | — | записать результат в файл (.opj/.json) |

### opt.run

Многоцелевая оптимизация ЛАП (аналог OPALLAP): N целей × M переменных, шаг Марквардта, границы-штрафы

**Returns:** istop/fmin/остатки + новые значения переменных (+system/saved при name/save)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `variables` | `list` | да | `null` | — | [{surface, param, pmin, pmax, dp0, link}, ...] |
| `goals` | `list` | да | `null` | — | [{kind, target, weight, norm, tol, refs}, ...] |
| `mode` | `str` | — | `"linear"` | `["linear", "gradient"]` | linear — нормальные уравнения Марквардта, gradient — наискорейший спуск |
| `max_iter` | `int` | — | `50` | — | максимум итераций NSTEP |
| `num_rays` | `int` | — | `20` | — | лучей веера для трассируемых целей |
| `include_history` | `bool` | — | `false` | — | полная история итераций (nstep/fmin/x/λ) |
| `name` | `str` | — | `null` | — | сохранить результат в контекст REPL под именем |
| `save` | `str` | — | `null` | — | записать результат в файл (.opj/.json) |

### opt.solve

Подогнать один параметр под одну цель (Ньютон по чувствительности; цели — efl/bfd/аберрации/RMS)

**Returns:** значение параметра + достигнутое значение характеристики

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `kind` | `str` | да | `null` | — | вид цели (opt.goals), например efl/bfd/rms_spot |
| `target` | `float` | да | `null` | — | целевое значение характеристики |
| `surface` | `int` | да | `null` | — | индекс поверхности (0-based) |
| `param` | `str` | — | `"radius"` | — | тип параметра (radius/thickness/conic/...) |
| `pmin` | `float` | — | `null` | — | нижняя граница поиска |
| `pmax` | `float` | — | `null` | — | верхняя граница поиска |
| `tol` | `float` | — | `1e-06` | — | допуск на характеристику |
| `max_iter` | `int` | — | `60` | — | максимум итераций |
| `name` | `str` | — | `null` | — | сохранить результат в контекст REPL под именем |
| `save` | `str` | — | `null` | — | записать результат в файл (.opj/.json) |

### opt.variables

Варьируемые параметры системы: текущие значения radius/thickness/conic/semi_diameter/glass_index

**Returns:** список {surface, param, value} по всем поверхностям

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

