# Категория tol

15 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`tol.apply.perturbation`](#tolapplyperturbation) | Применить возмущения к копии системы и вернуть отклик f′/RMS (песочница без правки исходника) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `dr`, `dd`, `field_y`, `num_rays`, `wl` | {efl_base, efl_perturbed, d_efl, rms_base, rms_perturbed} |
| [`tol.budget.split`](#tolbudgetsplit) | RSS-распределение бюджета \|Δf′\| по параметрам: равные доли, tᵢ = budget/(gᵢ·√N) | `file`, `system`, `lbo_index`, `lbo_name`, `budget`, `delta`, `wl` | {budget_mm, rows: [{surface, param, grad, tolerance_mm}]} |
| [`tol.contributions`](#tolcontributions) | Сводная таблица чувствительностей f′: радиусы + толщины + стёкла, ранжирование поверхностей | `file`, `system`, `lbo_index`, `lbo_name`, `delta`, `wl` | {rows: [{index, d_efl_d_r, d_efl_d_d, d_efl_d_n, max_g}]} |
| [`tol.inverse.radius`](#tolinverseradius) | Допуск на радиус каждой поверхности под бюджет \|Δf′\| ≤ budget (линейная оценка) | `file`, `system`, `lbo_index`, `lbo_name`, `budget`, `delta`, `wl` | {budget_mm, rows: [{index, grad, tolerance_mm}]} |
| [`tol.inverse.thickness`](#tolinversethickness) | Допуск на толщину каждой поверхности под бюджет \|Δf′\| ≤ budget | `file`, `system`, `lbo_index`, `lbo_name`, `budget`, `delta`, `wl` | {budget_mm, rows: [{index, grad, tolerance_mm}]} |
| [`tol.monte_carlo`](#tolmonte_carlo) | Монте-Карло разброс f′ при равномерных ошибках радиусов/толщин (детерминирован seed) | `file`, `system`, `lbo_index`, `lbo_name`, `trials`, `radius_tol`, `thickness_tol`, `seed`, `wl` | {trials, radius_tol, thickness_tol, stats, samples} |
| [`tol.rss.combine`](#tolrsscombine) | СКО-комбинация вкладов (RSS): √Σ(Δfᵢ)² | `contributions` | {contributions, rss} |
| [`tol.sensitivity.decenter`](#tolsensitivitydecenter) | Чувствительность Y-центроида пятна (boresight) к децентрировкам поверхностей (decenter_x, мм) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `delta`, `field_y`, `num_rays`, `wl` | {wl, delta_mm, rows: [{index, d_centroid_d_dec}]} |
| [`tol.sensitivity.glass`](#tolsensitivityglass) | Чувствительность f′ к показателю преломления стёкол (Δn через n_override) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `delta`, `wl` | {wl, delta_n, rows: [{index, glass, d_efl_d_n}]} |
| [`tol.sensitivity.radius`](#tolsensitivityradius) | Чувствительность f′ к радиусам поверхностей (центральная разность, мм⁻¹) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `delta`, `wl` | {wl, delta_mm, rows: [{index, d_efl_d_r}]} |
| [`tol.sensitivity.seidel.radius`](#tolsensitivityseidelradius) | Чувствительность сумм Зейделя к радиусам (какая поверхность управляет какой аберрацией) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `delta`, `wl` | {wl, delta_mm, rows: [{index, dS.._d_r: {...}}]} |
| [`tol.sensitivity.spot.radius`](#tolsensitivityspotradius) | Чувствительность RMS кружка к радиусам поверхностей | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `delta`, `field_y`, `num_rays`, `wl` | {wl, delta_mm, rows: [{index, d_rms_d_r}]} |
| [`tol.sensitivity.thickness`](#tolsensitivitythickness) | Чувствительность f′ к толщинам поверхностей | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `delta`, `wl` | {wl, delta_mm, rows: [{index, d_efl_d_d}]} |
| [`tol.sensitivity.tilt`](#tolsensitivitytilt) | Чувствительность Y-центроида пятна (boresight) к наклонам поверхностей (tilt_x, град): мм смещения на градус | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `delta`, `field_y`, `num_rays`, `wl` | {wl, delta_deg, rows: [{index, d_centroid_d_tilt}]} |
| [`tol.worst`](#tolworst) | Топ параметров по чувствительности f′ (радиусы/толщины/стёкла) | `file`, `system`, `lbo_index`, `lbo_name`, `limit`, `delta`, `wl` | {worst: [{surface, param, grad}]} |

## Параметры и результаты

### tol.apply.perturbation

Применить возмущения к копии системы и вернуть отклик f′/RMS (песочница без правки исходника)

**Returns:** {efl_base, efl_perturbed, d_efl, rms_base, rms_perturbed}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | поверхность (0-based) |
| `dr` | `float` | — | `0.0` | — | приращение радиуса, мм |
| `dd` | `float` | — | `0.0` | — | приращение толщины, мм |
| `field_y` | `float` | — | `0.0` | — | поле RMS |
| `num_rays` | `int` | — | `15` | — | лучей сетки |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.budget.split

RSS-распределение бюджета \|Δf′\| по параметрам: равные доли, tᵢ = budget/(gᵢ·√N)

**Returns:** {budget_mm, rows: [{surface, param, grad, tolerance_mm}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `budget` | `float` | да | `null` | — | бюджет \|Δf′\|, мм (RSS) |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.contributions

Сводная таблица чувствительностей f′: радиусы + толщины + стёкла, ранжирование поверхностей

**Returns:** {rows: [{index, d_efl_d_r, d_efl_d_d, d_efl_d_n, max_g}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.inverse.radius

Допуск на радиус каждой поверхности под бюджет \|Δf′\| ≤ budget (линейная оценка)

**Returns:** {budget_mm, rows: [{index, grad, tolerance_mm}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `budget` | `float` | да | `null` | — | бюджет \|Δf′\|, мм |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.inverse.thickness

Допуск на толщину каждой поверхности под бюджет \|Δf′\| ≤ budget

**Returns:** {budget_mm, rows: [{index, grad, tolerance_mm}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `budget` | `float` | да | `null` | — | бюджет \|Δf′\|, мм |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.monte_carlo

Монте-Карло разброс f′ при равномерных ошибках радиусов/толщин (детерминирован seed)

**Returns:** {trials, radius_tol, thickness_tol, stats, samples}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `trials` | `int` | — | `64` | — | число испытаний |
| `radius_tol` | `float` | — | `0.01` | — | ±допуск радиуса, мм |
| `thickness_tol` | `float` | — | `0.01` | — | ±допуск толщины, мм |
| `seed` | `int` | — | `20261023` | — | seed генератора (воспроизводимость) |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.rss.combine

СКО-комбинация вкладов (RSS): √Σ(Δfᵢ)²

**Returns:** {contributions, rss}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `contributions` | `list` | да | `null` | — | список вкладов Δfᵢ (числа) |

### tol.sensitivity.decenter

Чувствительность Y-центроида пятна (boresight) к децентрировкам поверхностей (decenter_x, мм)

**Returns:** {wl, delta_mm, rows: [{index, d_centroid_d_dec}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | — | `null` | — | одна поверхность (0-based) |
| `delta` | `float` | — | `0.05` | — | шаг разности, мм |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `15` | — | лучей сетки |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.sensitivity.glass

Чувствительность f′ к показателю преломления стёкол (Δn через n_override)

**Returns:** {wl, delta_n, rows: [{index, glass, d_efl_d_n}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | — | `null` | — | одна поверхность (0-based) |
| `delta` | `float` | — | `0.001` | — | шаг разности по n |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.sensitivity.radius

Чувствительность f′ к радиусам поверхностей (центральная разность, мм⁻¹)

**Returns:** {wl, delta_mm, rows: [{index, d_efl_d_r}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | — | `null` | — | одна поверхность (0-based) |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.sensitivity.seidel.radius

Чувствительность сумм Зейделя к радиусам (какая поверхность управляет какой аберрацией)

**Returns:** {wl, delta_mm, rows: [{index, dS.._d_r: {...}}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | — | `null` | — | одна поверхность (0-based) |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.sensitivity.spot.radius

Чувствительность RMS кружка к радиусам поверхностей

**Returns:** {wl, delta_mm, rows: [{index, d_rms_d_r}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | — | `null` | — | одна поверхность (0-based) |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `15` | — | лучей сетки |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.sensitivity.thickness

Чувствительность f′ к толщинам поверхностей

**Returns:** {wl, delta_mm, rows: [{index, d_efl_d_d}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | — | `null` | — | одна поверхность (0-based) |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.sensitivity.tilt

Чувствительность Y-центроида пятна (boresight) к наклонам поверхностей (tilt_x, град): мм смещения на градус

**Returns:** {wl, delta_deg, rows: [{index, d_centroid_d_tilt}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | — | `null` | — | одна поверхность (0-based) |
| `delta` | `float` | — | `0.1` | — | шаг разности, град |
| `field_y` | `float` | — | `0.0` | — | поле |
| `num_rays` | `int` | — | `15` | — | лучей сетки |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

### tol.worst

Топ параметров по чувствительности f′ (радиусы/толщины/стёкла)

**Returns:** {worst: [{surface, param, grad}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `limit` | `int` | — | `10` | — | максимум строк |
| `delta` | `float` | — | `0.01` | — | шаг разности, мм |
| `wl` | `float` | — | `null` | — | λ, мкм (по умолчанию — основная) |

