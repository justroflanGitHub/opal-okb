# Категория report

16 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`report.aberrations`](#reportaberrations) | Внеосевые аберрации по полям текстом (analyze.field_aberrations): дисторсия, Z'm/Z's, астигматизм, кома | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl`, `num_fan_rays`, `out` | {wl, text, out?} |
| [`report.chromatism`](#reportchromatism) | Хроматизм положения по рабочим λ текстом (calc.paraxial.multi_wl): f'/sF'/F/#/BFD по λ + разброс f' | `file`, `system`, `lbo_index`, `lbo_name`, `out` | {num_wavelengths, text, out?} |
| [`report.ee`](#reportee) | Диаметры зон задержанной энергии по полям текстом (quality.ee.diameters): 50/80/90 % геометрически | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `fractions`, `num_rays`, `wl`, `out` | {wl, text, out?} |
| [`report.fields`](#reportfields) | Перечень точек поля текстом: №, Y, X, вес + максимальное поле | `file`, `system`, `lbo_index`, `lbo_name`, `out` | {count, text, out?} |
| [`report.full`](#reportfull) | Полный свод текстом: паспорт, поверхности, поля, стёкла, параксиал, Зейдель, хроматизм, аберрации, RMS пятна, зоны энергии, ЧКХ, Штрель, волновой фронт, качество, таблицы порта | `file`, `system`, `lbo_index`, `lbo_name`, `freq_lpmm`, `num_rays`, `out` | {sections, failed?, text, out?} |
| [`report.glasses`](#reportglasses) | Перечень стёкол системы текстом: марки, поверхности использования, n(λ) и nd из каталога | `file`, `system`, `lbo_index`, `lbo_name`, `out` | {count, wl, text, out?} |
| [`report.mtf`](#reportmtf) | Матрица дифракционной ЧКХ текстом (quality.mtf.matrix): частоты × поля, сечения мер/саг, частота среза | `file`, `system`, `lbo_index`, `lbo_name`, `freqs`, `fields`, `wl`, `out` | {wl, text, out?} |
| [`report.paraxial`](#reportparaxial) | Параксиальные характеристики текстом (calc.paraxial): фокусы, кардинальные отрезки, зрачки, F/#, увеличение | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | {wl, text, out?} |
| [`report.quality`](#reportquality) | Свод качества текстом: паспорт системы (quality.passport: f', F/#, RMS, Штрель, ЧКХ, Эйри) + режим ограничения пятна (quality.regime) | `file`, `system`, `lbo_index`, `lbo_name`, `freq_lpmm`, `num_rays`, `out` | {freq_lpmm, text, out?} |
| [`report.seidel`](#reportseidel) | Суммы Зейделя текстом (seidel.sums): SI..SV + хроматические SIхр/SIIхр и пара λ | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | {wl, text, out?} |
| [`report.spot`](#reportspot) | RMS кружка рассеяния по полям и λ текстом (quality.spot.summary) + худшее поле | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `num_rays`, `out` | {text, out?} |
| [`report.strehl`](#reportstrehl) | Число Штреля по полям текстом (quality.strehl.summary): точный/Марешаль/σ + худшее поле и средний | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `out` | {text, out?} |
| [`report.surfaces`](#reportsurfaces) | Таблица поверхностей текстом: №, R, d, стекло, полудиаметр, тип (+ коника/асферика/наклоны) | `file`, `system`, `lbo_index`, `lbo_name`, `out` | {num_surfaces, text, out?} |
| [`report.system`](#reportsystem) | Паспорт системы текстом: предмет/изображение, апертура, диафрагма, экранирование, рабочие λ, точки поля, габарит | `file`, `system`, `lbo_index`, `lbo_name`, `out` | {name, num_surfaces, text, out?} |
| [`report.tables`](#reporttables) | Стандартные таблицы порта текстом: TABOC1/TABOC2/TABGL/TABPR2/TABAX3/TABBEA/TABESB/TABEAP (селектор; сбой секции не роняет отчёт) | `file`, `system`, `lbo_index`, `lbo_name`, `tables`, `wl`, `n_zones`, `out` | {tables, included, failed?, text, out?} |
| [`report.wavefront`](#reportwavefront) | СКВ волнового фронта по полям текстом (quality.wavefront.summary) + Марешаль в максимуме | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `out` | {wl, text, out?} |

## Параметры и результаты

### report.aberrations

Внеосевые аберрации по полям текстом (analyze.field_aberrations): дисторсия, Z'm/Z's, астигматизм, кома

**Returns:** {wl, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная λ системы) |
| `num_fan_rays` | `int` | — | `15` | — | лучей веера на поле |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.chromatism

Хроматизм положения по рабочим λ текстом (calc.paraxial.multi_wl): f'/sF'/F/#/BFD по λ + разброс f'

**Returns:** {num_wavelengths, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.ee

Диаметры зон задержанной энергии по полям текстом (quality.ee.diameters): 50/80/90 % геометрически

**Returns:** {wl, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `fractions` | `list` | — | `null` | — | доли энергии; по умолчанию [0.5, 0.8, 0.9] |
| `num_rays` | `int` | — | `100` | — | лучей точечной диаграммы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная λ системы) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.fields

Перечень точек поля текстом: №, Y, X, вес + максимальное поле

**Returns:** {count, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.full

Полный свод текстом: паспорт, поверхности, поля, стёкла, параксиал, Зейдель, хроматизм, аберрации, RMS пятна, зоны энергии, ЧКХ, Штрель, волновой фронт, качество, таблицы порта

**Returns:** {sections, failed?, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freq_lpmm` | `float` | — | `50.0` | — | частота ЧКХ свода, лин/мм |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка (своды пятна/качества) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.glasses

Перечень стёкол системы текстом: марки, поверхности использования, n(λ) и nd из каталога

**Returns:** {count, wl, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.mtf

Матрица дифракционной ЧКХ текстом (quality.mtf.matrix): частоты × поля, сечения мер/саг, частота среза

**Returns:** {wl, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freqs` | `list` | — | `null` | — | частоты, лин/мм; по умолчанию [20, 50, 100] |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная λ системы) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.paraxial

Параксиальные характеристики текстом (calc.paraxial): фокусы, кардинальные отрезки, зрачки, F/#, увеличение

**Returns:** {wl, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная λ системы) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.quality

Свод качества текстом: паспорт системы (quality.passport: f', F/#, RMS, Штрель, ЧКХ, Эйри) + режим ограничения пятна (quality.regime)

**Returns:** {freq_lpmm, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freq_lpmm` | `float` | — | `50.0` | — | частота ЧКХ свода, лин/мм |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.seidel

Суммы Зейделя текстом (seidel.sums): SI..SV + хроматические SIхр/SIIхр и пара λ

**Returns:** {wl, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная λ системы) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.spot

RMS кружка рассеяния по полям и λ текстом (quality.spot.summary) + худшее поле

**Returns:** {text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `num_rays` | `int` | — | `20` | — | лучей сетки зрачка |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.strehl

Число Штреля по полям текстом (quality.strehl.summary): точный/Марешаль/σ + худшее поле и средний

**Returns:** {text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | список полей; по умолчанию — поля системы |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.surfaces

Таблица поверхностей текстом: №, R, d, стекло, полудиаметр, тип (+ коника/асферика/наклоны)

**Returns:** {num_surfaces, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.system

Паспорт системы текстом: предмет/изображение, апертура, диафрагма, экранирование, рабочие λ, точки поля, габарит

**Returns:** {name, num_surfaces, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.tables

Стандартные таблицы порта текстом: TABOC1/TABOC2/TABGL/TABPR2/TABAX3/TABBEA/TABESB/TABEAP (селектор; сбой секции не роняет отчёт)

**Returns:** {tables, included, failed?, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `tables` | `list` | — | `null` | — | селектор таблиц; по умолчанию ['taboc1', 'taboc2', 'tabgl', 'tabpr2']; допустимо ['taboc1', 'taboc2', 'tabgl', 'tabpr2', 'tabax3', 'tabbea', 'tabesb', 'tabeap'] |
| `wl` | `float` | — | `null` | — | λ, мкм для всех таблиц (по умолчанию — каждая берёт свою основную λ) |
| `n_zones` | `int` | — | `null` | — | число зон зрачка/поля (TABOC1/2, TABGL, TABPR2) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

### report.wavefront

СКВ волнового фронта по полям текстом (quality.wavefront.summary) + Марешаль в максимуме

**Returns:** {wl, text, out?}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная λ системы) |
| `out` | `str` | — | `null` | — | файл .txt для записи отчёта (опционально) |

