# Категория seidel

4 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`seidel.check_tracing`](#seidelcheck_tracing) | Численная сверка сумм Зейделя с трассировкой: коэффициенты 3-го порядка (МНК по веерам), знаки | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {sums, axial, field, chromatic, signs, orders} |
| [`seidel.parse_prn`](#seidelparse_prn) | Строки секции сумм Зейделя из .PRN OPAL (sumsed, cp866) — без системы | `prn` | строки {n, S1..S5, S1xp, S2xp} (может быть пусто) |
| [`seidel.sums`](#seidelsums) | Суммы Зейделя SI..SV + хроматические SIхр/SIIхр (независимая реализация для контроля паритета) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {SI..SV, SIxp, SIIxp, wl, wl_lo, wl_hi, chromatic} |
| [`seidel.vs_golden`](#seidelvs_golden) | Сверка сумм Зейделя с секцией golden .PRN OPAL (sumsed): знаки + отношения Sₖ/S1 | `file`, `system`, `lbo_index`, `lbo_name`, `prn`, `tol` | {status: matched\|mismatch\|skipped, signs, ratios, ...} |

## Параметры и результаты

### seidel.check_tracing

Численная сверка сумм Зейделя с трассировкой: коэффициенты 3-го порядка (МНК по веерам), знаки

**Returns:** {sums, axial, field, chromatic, signs, orders}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | да | `null` | — | поле полевого веера (град/мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### seidel.parse_prn

Строки секции сумм Зейделя из .PRN OPAL (sumsed, cp866) — без системы

**Returns:** строки {n, S1..S5, S1xp, S2xp} (может быть пусто)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `prn` | `str` | да | `null` | — | путь к .PRN OPAL (cp866) |

### seidel.sums

Суммы Зейделя SI..SV + хроматические SIхр/SIIхр (независимая реализация для контроля паритета)

**Returns:** {SI..SV, SIxp, SIIxp, wl, wl_lo, wl_hi, chromatic}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### seidel.vs_golden

Сверка сумм Зейделя с секцией golden .PRN OPAL (sumsed): знаки + отношения Sₖ/S1

**Returns:** {status: matched\|mismatch\|skipped, signs, ratios, ...}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `prn` | `str` | да | `null` | — | путь к .PRN OPAL (cp866) |
| `tol` | `float` | — | `0.05` | — | допуск относительного расхождения отношений |

