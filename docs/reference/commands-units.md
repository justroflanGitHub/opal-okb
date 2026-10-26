# Категория units

12 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`units.angle.convert`](#unitsangleconvert) | Плоский угол между единицами (град/рад/град/угл.мин/угл.сек) | `value`, `from_unit`, `to_unit` | {value, from_unit, to_unit, result} |
| [`units.arcsec.ddmmss`](#unitsarcsecddmmss) | Разбор числа «гр.мнсек» DD.MMSS печати OPAL в секунды дуги и градусы (движок golden-сверок analysis.golden_verify.arcsec_of_ddmmss — им сверяются поперечные golden-прогонов; OBEKTIV 1.130483 → 1°13'04.83" = 4384.83″, ST4 0.000217 → 2.17″) | `value` | {value, arcsec, deg} |
| [`units.deg_to_gms`](#unitsdeg_to_gms) | Угол (град) → формат OPAL «Г.ММСС» (как в таблицах точек поля) | `angle_deg`, `width`, `decimals` | {angle_deg, gms} |
| [`units.dioptres_to_mm`](#unitsdioptres_to_mm) | Оптическая сила (диоптрии) → отрезок (мм) | `dioptres` | {dioptres, mm} |
| [`units.gms_to_deg`](#unitsgms_to_deg) | «Г.ММСС» числом → угол в градусах | `value` | {gms_value, angle_deg} |
| [`units.grminsec`](#unitsgrminsec) | Угол (град) → градусы.минутысекунды числом (12.3456° → 12.2045…) | `angle_deg` | {angle_deg, gms_value} |
| [`units.mm_to_dioptres`](#unitsmm_to_dioptres) | Отрезок (мм) → оптическая сила (диоптрии): Φ = 1000/f | `mm` | {mm, dioptres} |
| [`units.print.table`](#unitsprinttable) | Таблица единиц печати OPAL «ближний/дальний тип» (REVERSE_NZR §19.2 / ANALIZE.DOC:659–680): какие единицы печатает OPAL для величин анализа | — | {count, rows: [{quantity, near, far}], source} |
| [`units.pupil_h_mm`](#unitspupil_h_mm) | Высота луча в зрачке: доля зрачка × осевой отрезок | `rel`, `ax_mm` | {rel, ax_mm, h_mm} |
| [`units.pupil_h_out_mm`](#unitspupil_h_out_mm) | Высота луча на выходе: доля × осевой отрезок в пространстве изображений | `rel`, `ax_out_mm` | {rel, ax_out_mm, h_mm} |
| [`units.tg100`](#unitstg100) | Tg·100 — тангенс угла ×100 (единица OPAL для виньетирования/полей) | `angle_deg` | {angle_deg, tg100} |
| [`units.wl.convert`](#unitswlconvert) | Длину волны между единицами (мкм/нм/мм/Å) | `value`, `from_unit`, `to_unit` | {value, from_unit, to_unit, result} |

## Параметры и результаты

### units.angle.convert

Плоский угол между единицами (град/рад/град/угл.мин/угл.сек)

**Returns:** {value, from_unit, to_unit, result}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `value` | `float` | да | `null` | — | значение |
| `from_unit` | `str` | — | `"deg"` | `["deg", "rad", "grad", "arcmin", "arcsec"]` | единица источника |
| `to_unit` | `str` | — | `"rad"` | `["deg", "rad", "grad", "arcmin", "arcsec"]` | единица результата |

### units.arcsec.ddmmss

Разбор числа «гр.мнсек» DD.MMSS печати OPAL в секунды дуги и градусы (движок golden-сверок analysis.golden_verify.arcsec_of_ddmmss — им сверяются поперечные golden-прогонов; OBEKTIV 1.130483 → 1°13'04.83" = 4384.83″, ST4 0.000217 → 2.17″)

**Returns:** {value, arcsec, deg}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `value` | `float` | да | `null` | — | число «гр.мнсек» DD.MMSS (например 1.130483) |

### units.deg_to_gms

Угол (град) → формат OPAL «Г.ММСС» (как в таблицах точек поля)

**Returns:** {angle_deg, gms}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `angle_deg` | `float` | да | `null` | — | угол, градусы |
| `width` | `int` | — | `null` | — | ширина поля вывода |
| `decimals` | `int` | — | `null` | — | знаков после точки |

### units.dioptres_to_mm

Оптическая сила (диоптрии) → отрезок (мм)

**Returns:** {dioptres, mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `dioptres` | `float` | да | `null` | — | сила, дптр (не 0) |

### units.gms_to_deg

«Г.ММСС» числом → угол в градусах

**Returns:** {gms_value, angle_deg}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `value` | `float` | да | `null` | — | значение Г.ММСС (например 12.2045) |

### units.grminsec

Угол (град) → градусы.минутысекунды числом (12.3456° → 12.2045…)

**Returns:** {angle_deg, gms_value}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `angle_deg` | `float` | да | `null` | — | угол, градусы |

### units.mm_to_dioptres

Отрезок (мм) → оптическая сила (диоптрии): Φ = 1000/f

**Returns:** {mm, dioptres}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `mm` | `float` | да | `null` | — | отрезок, мм (не 0) |

### units.print.table

Таблица единиц печати OPAL «ближний/дальний тип» (REVERSE_NZR §19.2 / ANALIZE.DOC:659–680): какие единицы печатает OPAL для величин анализа

**Returns:** {count, rows: [{quantity, near, far}], source}

### units.pupil_h_mm

Высота луча в зрачке: доля зрачка × осевой отрезок

**Returns:** {rel, ax_mm, h_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `rel` | `float` | да | `null` | — | доля высоты зрачка (−1..1) |
| `ax_mm` | `float` | да | `null` | — | осевой отрезок, мм |

### units.pupil_h_out_mm

Высота луча на выходе: доля × осевой отрезок в пространстве изображений

**Returns:** {rel, ax_out_mm, h_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `rel` | `float` | да | `null` | — | доля зрачка |
| `ax_out_mm` | `float` | да | `null` | — | осевой отрезок изображения, мм |

### units.tg100

Tg·100 — тангенс угла ×100 (единица OPAL для виньетирования/полей)

**Returns:** {angle_deg, tg100}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `angle_deg` | `float` | да | `null` | — | угол, градусы |

### units.wl.convert

Длину волны между единицами (мкм/нм/мм/Å)

**Returns:** {value, from_unit, to_unit, result}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `value` | `float` | да | `null` | — | значение длины волны |
| `from_unit` | `str` | — | `"um"` | `["um", "nm", "mm", "A"]` | единица источника |
| `to_unit` | `str` | — | `"nm"` | `["um", "nm", "mm", "A"]` | единица результата |

