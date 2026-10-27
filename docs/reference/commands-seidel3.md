# Категория seidel3

5 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`seidel3.chromatic.magnitude`](#seidel3chromaticmagnitude) | Хроматизм увеличения: V(λ) по рабочим λ и относительное изменение | `file`, `system`, `lbo_index`, `lbo_name` | {rows: [{wl, V}], delta_V_pct, wl_lo, wl_hi} |
| [`seidel3.chromatic.position`](#seidel3chromaticposition) | Хроматизм положения: f′ и BFD по всем рабочим λ, Δf′ между крайними | `file`, `system`, `lbo_index`, `lbo_name` | {rows: [{wl, f_prime, bfd}], delta_f_mm, wl_lo, wl_hi} |
| [`seidel3.petzval.radius`](#seidel3petzvalradius) | Радиус кривизны поверхности Петцваля из суммы SIV (SIV = Σ(n′−n)/(R·n·n′) = 1/R_p) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {wl, SIV, petzval_radius_mm} |
| [`seidel3.sums.normalized`](#seidel3sumsnormalized) | Суммы Зейделя, нормированные на SI (относительная картина коррекции) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {wl, SI, ratios: {SII: SII/SI, ...}} |
| [`seidel3.sums.ranking`](#seidel3sumsranking) | Ранжирование сумм Зейделя по модулю с метками аберраций и долями | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {wl, ranking: [{sum, label, value, share}]} |

## Параметры и результаты

### seidel3.chromatic.magnitude

Хроматизм увеличения: V(λ) по рабочим λ и относительное изменение

**Returns:** {rows: [{wl, V}], delta_V_pct, wl_lo, wl_hi}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### seidel3.chromatic.position

Хроматизм положения: f′ и BFD по всем рабочим λ, Δf′ между крайними

**Returns:** {rows: [{wl, f_prime, bfd}], delta_f_mm, wl_lo, wl_hi}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### seidel3.petzval.radius

Радиус кривизны поверхности Петцваля из суммы SIV (SIV = Σ(n′−n)/(R·n·n′) = 1/R_p)

**Returns:** {wl, SIV, petzval_radius_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### seidel3.sums.normalized

Суммы Зейделя, нормированные на SI (относительная картина коррекции)

**Returns:** {wl, SI, ratios: {SII: SII/SI, ...}}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### seidel3.sums.ranking

Ранжирование сумм Зейделя по модулю с метками аберраций и долями

**Returns:** {wl, ranking: [{sum, label, value, share}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

