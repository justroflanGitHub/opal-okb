# Категория system

53 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`system.achromat`](#systemachromat) | Рассчитать ахроматический дублет (f', пара стёкол, апертура) — проектор новой системы | `focal_length`, `crown`, `flint`, `aperture`, `name`, `out` | сериализованная система ахромата (+saved при out) |
| [`system.aperture.convert`](#systemapertureconvert) | Апертуру из любого способа — во все представления (канон: диаметр входного зрачка) | `file`, `system`, `lbo_index`, `lbo_name`, `value`, `from_type` | {epd, entrance_pupil, f_number, ...} (мм / безразмерные) |
| [`system.aperture.epd`](#systemapertureepd) | Диаметр входного зрачка для текущей апертуры системы | `file`, `system`, `lbo_index`, `lbo_name` | {epd, aperture_type, aperture_value} (мм) |
| [`system.aperture.from_epd`](#systemaperturefrom_epd) | Все представления осевого пучка по диаметру входного зрачка | `file`, `system`, `lbo_index`, `lbo_name`, `epd` | {entrance_pupil, f_number, numerical_aperture, ...} |
| [`system.aperture.pupil_distance`](#systemaperturepupil_distance) | Путь осевого луча от предмета до входного зрачка (только FINITE-предмет) | `file`, `system`, `lbo_index`, `lbo_name` | {distance: float\|None, object_type} (мм) |
| [`system.aperture.set`](#systemapertureset) | Задать апертуру: способ (7 типов) + значение | `file`, `system`, `lbo_index`, `lbo_name`, `aperture_type`, `aperture_value`, `out` | система после правки (+saved при out) |
| [`system.append`](#systemappend) | Присоединить систему из файла: поверхности добавляются в конец, параметры — от основной (имя «A + B») | `file`, `system`, `lbo_index`, `lbo_name`, `append`, `append_index`, `append_name`, `name`, `out` | сериализованная объединённая система (+saved при out) |
| [`system.beam.set`](#systembeamset) | Задать режим габаритов пучка: real/given + острая кромка | `file`, `system`, `lbo_index`, `lbo_name`, `beam_mode`, `sharp_edge`, `out` | система после правки (+saved при out) |
| [`system.clone`](#systemclone) | Копия системы под новым именем в контексте (глубокая) | `file`, `system`, `lbo_index`, `lbo_name`, `name`, `out` | сериализованная копия (+saved при out) |
| [`system.comment.set`](#systemcommentset) | Задать комментарий системы | `file`, `system`, `lbo_index`, `lbo_name`, `comment`, `out` | система после правки (+saved при out) |
| [`system.current`](#systemcurrent) | REPL: текущая система контекста | — | имя + сводка текущей системы |
| [`system.drop`](#systemdrop) | REPL: удалить систему из контекста (текущая — сброс current); идемпотентно | `name` | {dropped, current} |
| [`system.fields.add`](#systemfieldsadd) | Добавить точку поля (y — градусы для INFINITE / мм) | `file`, `system`, `lbo_index`, `lbo_name`, `y`, `x`, `weight`, `out` | система после добавления (+saved при out) |
| [`system.fields.auto`](#systemfieldsauto) | Задать точки поля автоматически: зоны поля системы (0, ..., max) | `file`, `system`, `lbo_index`, `lbo_name`, `num_fields`, `out` | система после установки (+saved при out) |
| [`system.fields.clear`](#systemfieldsclear) | Удалить все точки поля | `file`, `system`, `lbo_index`, `lbo_name`, `out` | система после очистки (+saved при out) |
| [`system.fields.list`](#systemfieldslist) | Список точек поля системы | `file`, `system`, `lbo_index`, `lbo_name` | список {y, x, weight} |
| [`system.fields.remove`](#systemfieldsremove) | Удалить точку поля по индексу | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `out` | система после удаления (+saved при out) |
| [`system.fields.set`](#systemfieldsset) | Заменить весь набор точек поля системы | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `name`, `out` | система после замены (+saved при out) |
| [`system.fields.weight.set`](#systemfieldsweightset) | Задать вес точки поля по индексу | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `weight`, `out` | система после правки (+saved при out) |
| [`system.glasses.list`](#systemglasseslist) | Уникальные стёкла системы + где используются | `file`, `system`, `lbo_index`, `lbo_name` | список {glass, surfaces: [индексы]} |
| [`system.glasses.replace`](#systemglassesreplace) | Заменить марку стекла во всех поверхностях (стекло-источник удаляется полностью) | `file`, `system`, `lbo_index`, `lbo_name`, `old`, `new`, `out` | система после замены (+saved при out) |
| [`system.image.set`](#systemimageset) | Задать положение изображения (FINITE/INFINITE) | `file`, `system`, `lbo_index`, `lbo_name`, `image_type`, `out` | система после правки (+saved при out) |
| [`system.info`](#systeminfo) | Сводка о системе: апертура, счётчики, стёкла, длины волн | `file`, `system`, `lbo_index`, `lbo_name` | сводка системы |
| [`system.list`](#systemlist) | REPL: системы в контексте (имена + счётчики, текущая) | — | {current, systems: [{name, num_surfaces, num_wavelengths}]} |
| [`system.load`](#systemload) | REPL: загрузить систему из файла в контекст (сделать текущей) | `file`, `name`, `lbo_index`, `lbo_name` | имя в контексте + сериализованная система |
| [`system.name.set`](#systemnameset) | Задать имя системы | `file`, `system`, `lbo_index`, `lbo_name`, `name`, `out` | система после правки (+saved при out) |
| [`system.new`](#systemnew) | Создать новую систему: пустую или демо-генератором | `demo`, `name`, `save` | сериализованная новая система |
| [`system.object.set`](#systemobjectset) | Задать положение предмета: тип (FINITE/INFINITE), высоту и расстояние | `file`, `system`, `lbo_index`, `lbo_name`, `object_type`, `object_height`, `object_distance`, `out` | система после правки (+saved при out) |
| [`system.obscuration.set`](#systemobscurationset) | Задать центральное экранирование (доля 0..1) | `file`, `system`, `lbo_index`, `lbo_name`, `obscuration_ratio`, `out` | система после правки (+saved при out) |
| [`system.radii.changes`](#systemradiichanges) | Предпросмотр приведения радиусов к ГОСТ 1807-75: таблица замен (поверхность, старый R, новый R, Δ%) | `file`, `system`, `lbo_index`, `lbo_name` | список замен (пустой — всё уже стандартно) |
| [`system.radii.standardize`](#systemradiistandardize) | Заменить нестандартные радиусы ближайшими по ГОСТ 1807-75 (плоские R=0 не трогаются) | `file`, `system`, `lbo_index`, `lbo_name`, `name`, `out` | сериализованная система со стандартными радиусами (+saved при out) |
| [`system.rename`](#systemrename) | Переименовать систему (атрибут name + ключ контекста) | `file`, `system`, `lbo_index`, `lbo_name`, `name`, `out` | {name, old_name} (+saved при out) |
| [`system.reverse`](#systemreverse) | Обернуть систему: поверхности в обратном порядке, знаки радиусов — на противоположные, толщины перепривязываются, стоп пересчитывается | `file`, `system`, `lbo_index`, `lbo_name`, `name`, `out` | сериализованная обращённая система (+saved при out) |
| [`system.scale`](#systemscale) | Масштабировать линейные размеры системы (R, d, полудиаметры, апертура; углы поля не меняются) | `file`, `system`, `lbo_index`, `lbo_name`, `factor`, `name`, `out` | сериализованная масштабированная система (+saved при out) |
| [`system.select`](#systemselect) | REPL: сделать систему текущей по имени контекста | `name` | {current, num_surfaces} |
| [`system.stop.set`](#systemstopset) | Задать апертурную диафрагму: поверхность, отступ, тип | `file`, `system`, `lbo_index`, `lbo_name`, `stop_surface`, `stop_offset`, `stop_type`, `out` | система после правки (+saved при out) |
| [`system.surface.add`](#systemsurfaceadd) | Добавить поверхность (в конец или по индексу вставки) | `file`, `system`, `lbo_index`, `lbo_name`, `radius`, `thickness`, `glass`, `semi_diameter`, `surface_type`, `conic_constant`, `is_reflective`, `tilt_x`, `tilt_y`, `tilt_z`, `decenter_x`, `decenter_y`, `index`, `out` | система после добавления (+saved при out) |
| [`system.surface.aspheric.set`](#systemsurfaceasphericset) | Задать коэффициенты асферики поверхности (A4, A6, ...; тип — ASPHERIC) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `coeffs`, `set_type`, `out` | система после правки (+saved при out) |
| [`system.surface.duplicate`](#systemsurfaceduplicate) | Дублировать поверхность count раз (вставка после) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `count`, `out` | система после вставки (+saved при out) |
| [`system.surface.get`](#systemsurfaceget) | Полные атрибуты поверхности по индексу (0-based) | `file`, `system`, `lbo_index`, `lbo_name`, `index` | словарь поверхности |
| [`system.surface.move`](#systemsurfacemove) | Переставить поверхность на новую позицию (0-based) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `to`, `out` | система после перестановки (+saved при out) |
| [`system.surface.n.set`](#systemsurfacenset) | Переопределить показатели преломления поверхности: {λ мкм: n} вместо каталога стёкол | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `n_override`, `out` | система после правки (+saved при out) |
| [`system.surface.remove`](#systemsurfaceremove) | Удалить поверхность по индексу (0-based) | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `out` | система после удаления (+saved при out) |
| [`system.surface.set`](#systemsurfaceset) | Изменить атрибуты поверхности по индексу (0-based) | `file`, `system`, `lbo_index`, `lbo_name`, `radius`, `thickness`, `glass`, `semi_diameter`, `surface_type`, `conic_constant`, `is_reflective`, `tilt_x`, `tilt_y`, `tilt_z`, `decenter_x`, `decenter_y`, `index`, `out` | система после правки (+saved при out) |
| [`system.surfaces.list`](#systemsurfaceslist) | Список поверхностей системы (полные атрибуты) | `file`, `system`, `lbo_index`, `lbo_name` | список словарей поверхностей |
| [`system.validate`](#systemvalidate) | Санити-проверки системы: структура, апертура, поля, λ, стёкла (в каталогах), параксиальный расчёт | `file`, `system`, `lbo_index`, `lbo_name` | {valid, errors: [...], warnings: [...], checks} |
| [`system.wavelengths.add`](#systemwavelengthsadd) | Добавить рабочую длину волны (мкм) | `file`, `system`, `lbo_index`, `lbo_name`, `value`, `weight`, `name`, `out` | система после добавления (+saved при out) |
| [`system.wavelengths.clear`](#systemwavelengthsclear) | Удалить все рабочие длины волн | `file`, `system`, `lbo_index`, `lbo_name`, `out` | система после очистки (+saved при out) |
| [`system.wavelengths.list`](#systemwavelengthslist) | Список рабочих длин волн системы | `file`, `system`, `lbo_index`, `lbo_name` | список {value, weight, name} |
| [`system.wavelengths.primary`](#systemwavelengthsprimary) | Основная длина волны системы (расчёты по умолчанию) | `file`, `system`, `lbo_index`, `lbo_name` | {value, name} (мкм) |
| [`system.wavelengths.remove`](#systemwavelengthsremove) | Удалить рабочую длину волны по индексу | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `out` | система после удаления (+saved при out) |
| [`system.wavelengths.set`](#systemwavelengthsset) | Заменить весь набор рабочих длин волн системы | `file`, `system`, `lbo_index`, `lbo_name`, `wavelengths`, `name`, `out` | система после замены (+saved при out) |
| [`system.wavelengths.weight.set`](#systemwavelengthsweightset) | Задать вес длины волны по индексу | `file`, `system`, `lbo_index`, `lbo_name`, `index`, `weight`, `out` | система после правки (+saved при out) |

## Параметры и результаты

### system.achromat

Рассчитать ахроматический дублет (f', пара стёкол, апертура) — проектор новой системы

**Returns:** сериализованная система ахромата (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `focal_length` | `float` | да | `null` | — | фокусное расстояние, мм |
| `crown` | `str` | — | `"К8"` | — | крон (например К8, БК10) |
| `flint` | `str` | — | `"ТФ5"` | — | флинт (например ТФ5, ТФ3, Ф4) |
| `aperture` | `float` | — | `0.0` | — | апертура (входной зрачок, мм); 0 — не задавать |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.aperture.convert

Апертуру из любого способа — во все представления (канон: диаметр входного зрачка)

**Returns:** {epd, entrance_pupil, f_number, ...} (мм / безразмерные)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `value` | `float` | да | `null` | — | значение апертуры |
| `from_type` | `str` | — | `"ENTRANCE_PUPIL"` | `["ENTRANCE_PUPIL", "NUMERICAL_APERTURE", "F_NUMBER", "FRONT_ANGLE", "REAR_ANGLE", "REAR_NA", "STOP_HEIGHT"]` | исходный способ задания |

### system.aperture.epd

Диаметр входного зрачка для текущей апертуры системы

**Returns:** {epd, aperture_type, aperture_value} (мм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.aperture.from_epd

Все представления осевого пучка по диаметру входного зрачка

**Returns:** {entrance_pupil, f_number, numerical_aperture, ...}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `epd` | `float` | да | `null` | — | диаметр входного зрачка, мм |

### system.aperture.pupil_distance

Путь осевого луча от предмета до входного зрачка (только FINITE-предмет)

**Returns:** {distance: float\|None, object_type} (мм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.aperture.set

Задать апертуру: способ (7 типов) + значение

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `aperture_type` | `str` | — | `null` | `["ENTRANCE_PUPIL", "NUMERICAL_APERTURE", "F_NUMBER", "FRONT_ANGLE", "REAR_ANGLE", "REAR_NA", "STOP_HEIGHT"]` | способ задания апертуры |
| `aperture_value` | `float` | да | `null` | — | значение в единицах способа |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.append

Присоединить систему из файла: поверхности добавляются в конец, параметры — от основной (имя «A + B»)

**Returns:** сериализованная объединённая система (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `append` | `str` | да | `null` | — | путь к присоединяемой системе (.opj/.lbo/.json) |
| `append_index` | `int` | — | `0` | — | индекс записи .lbo присоединяемой системы |
| `append_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее индекса) |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.beam.set

Задать режим габаритов пучка: real/given + острая кромка

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `beam_mode` | `str` | — | `null` | `["real", "given"]` | real — реальная трассировка, given — заданные полудиаметры |
| `sharp_edge` | `bool` | — | `null` | — | острая кромка ( виньетирование по краю) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.clone

Копия системы под новым именем в контексте (глубокая)

**Returns:** сериализованная копия (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `name` | `str` | да | `null` | — | имя копии в контексте |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.comment.set

Задать комментарий системы

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `comment` | `str` | да | `null` | — | текст комментария |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.current

REPL: текущая система контекста

**Returns:** имя + сводка текущей системы

### system.drop

REPL: удалить систему из контекста (текущая — сброс current); идемпотентно

**Returns:** {dropped, current}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | имя в контексте |

### system.fields.add

Добавить точку поля (y — градусы для INFINITE / мм)

**Returns:** система после добавления (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `y` | `float` | да | `null` | — | координата поля (град/мм) |
| `x` | `float` | — | `0.0` | — | 2D-координата X |
| `weight` | `float` | — | `1.0` | — | вес |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.fields.auto

Задать точки поля автоматически: зоны поля системы (0, ..., max)

**Returns:** система после установки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_fields` | `int` | — | `5` | — | число точек поля (включая осевую) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.fields.clear

Удалить все точки поля

**Returns:** система после очистки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.fields.list

Список точек поля системы

**Returns:** список {y, x, weight}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.fields.remove

Удалить точку поля по индексу

**Returns:** система после удаления (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс точки поля (0-based) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.fields.set

Заменить весь набор точек поля системы

**Returns:** система после замены (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | да | `null` | — | [{y, x, weight}, …] — y обязательно |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.fields.weight.set

Задать вес точки поля по индексу

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс точки поля (0-based) |
| `weight` | `float` | да | `null` | — | вес |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.glasses.list

Уникальные стёкла системы + где используются

**Returns:** список {glass, surfaces: [индексы]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.glasses.replace

Заменить марку стекла во всех поверхностях (стекло-источник удаляется полностью)

**Returns:** система после замены (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `old` | `str` | да | `null` | — | заменяемая марка |
| `new` | `str` | да | `null` | — | новая марка |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.image.set

Задать положение изображения (FINITE/INFINITE)

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `image_type` | `str` | да | `null` | `["FINITE", "INFINITE"]` | FINITE / INFINITE |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.info

Сводка о системе: апертура, счётчики, стёкла, длины волн

**Returns:** сводка системы

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.list

REPL: системы в контексте (имена + счётчики, текущая)

**Returns:** {current, systems: [{name, num_surfaces, num_wavelengths}]}

### system.load

REPL: загрузить систему из файла в контекст (сделать текущей)

**Returns:** имя в контексте + сериализованная система

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | да | `null` | — | путь к файлу системы |
| `name` | `str` | — | `null` | — | имя в контексте (по умолчанию — имя файла) |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo |

### system.name.set

Задать имя системы

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `name` | `str` | да | `null` | — | новое имя |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.new

Создать новую систему: пустую или демо-генератором

**Returns:** сериализованная новая система

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `demo` | `str` | — | `"default"` | `["default", "empty", "achromat", "cook_doublet", "telephoto", "petzval", "mirror", "meniscus", "plano_convex"]` | демо-система: default, empty, achromat, cook_doublet, telephoto, petzval, mirror, meniscus, plano_convex |
| `name` | `str` | — | `null` | — | имя системы (и ключ в контексте REPL) |
| `save` | `str` | — | `null` | — | сохранить сразу по расширению пути |

### system.object.set

Задать положение предмета: тип (FINITE/INFINITE), высоту и расстояние

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `object_type` | `str` | — | `null` | `["FINITE", "INFINITE"]` | FINITE — конечное расстояние, INFINITE — ∞ |
| `object_height` | `float` | — | `null` | — | высота предмета, мм |
| `object_distance` | `float` | — | `null` | — | расстояние до 1-й поверхности, мм |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.obscuration.set

Задать центральное экранирование (доля 0..1)

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `obscuration_ratio` | `float` | да | `null` | — | отношение диаметров экранирования/зрачка, 0..1 |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.radii.changes

Предпросмотр приведения радиусов к ГОСТ 1807-75: таблица замен (поверхность, старый R, новый R, Δ%)

**Returns:** список замен (пустой — всё уже стандартно)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.radii.standardize

Заменить нестандартные радиусы ближайшими по ГОСТ 1807-75 (плоские R=0 не трогаются)

**Returns:** сериализованная система со стандартными радиусами (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.rename

Переименовать систему (атрибут name + ключ контекста)

**Returns:** {name, old_name} (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `name` | `str` | да | `null` | — | новое имя системы |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.reverse

Обернуть систему: поверхности в обратном порядке, знаки радиусов — на противоположные, толщины перепривязываются, стоп пересчитывается

**Returns:** сериализованная обращённая система (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.scale

Масштабировать линейные размеры системы (R, d, полудиаметры, апертура; углы поля не меняются)

**Returns:** сериализованная масштабированная система (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `factor` | `float` | да | `null` | — | коэффициент масштабирования (≠ 0) |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.select

REPL: сделать систему текущей по имени контекста

**Returns:** {current, num_surfaces}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | имя в контексте |

### system.stop.set

Задать апертурную диафрагму: поверхность, отступ, тип

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `stop_surface` | `int` | — | `null` | — | номер поверхности диафрагмы (0-based) |
| `stop_offset` | `float` | — | `null` | — | отступ диафрагмы от поверхности, мм |
| `stop_type` | `str` | — | `null` | `["d", "z", "p"]` | d — диафрагма, z/p — зрачок |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surface.add

Добавить поверхность (в конец или по индексу вставки)

**Returns:** система после добавления (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `radius` | `float` | — | `null` | — | атрибут Surface.radius |
| `thickness` | `float` | — | `null` | — | атрибут Surface.thickness |
| `glass` | `str` | — | `null` | — | атрибут Surface.glass |
| `semi_diameter` | `float` | — | `null` | — | атрибут Surface.semi_diameter |
| `surface_type` | `str` | — | `null` | `["SPHERE", "CONIC", "ASPHERIC", "HOLOGRAM", "GRATING", "TOROIDAL"]` | атрибут Surface.surface_type |
| `conic_constant` | `float` | — | `null` | — | атрибут Surface.conic_constant |
| `is_reflective` | `bool` | — | `null` | — | атрибут Surface.is_reflective |
| `tilt_x` | `float` | — | `null` | — | атрибут Surface.tilt_x |
| `tilt_y` | `float` | — | `null` | — | атрибут Surface.tilt_y |
| `tilt_z` | `float` | — | `null` | — | атрибут Surface.tilt_z |
| `decenter_x` | `float` | — | `null` | — | атрибут Surface.decenter_x |
| `decenter_y` | `float` | — | `null` | — | атрибут Surface.decenter_y |
| `index` | `int` | — | `null` | — | индекс вставки (0-based); по умолчанию — в конец |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surface.aspheric.set

Задать коэффициенты асферики поверхности (A4, A6, ...; тип — ASPHERIC)

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс поверхности (0-based) |
| `coeffs` | `list` | да | `null` | — | коэффициенты [A4, A6, ...] |
| `set_type` | `bool` | — | `true` | — | установить surface_type=ASPHERIC |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surface.duplicate

Дублировать поверхность count раз (вставка после)

**Returns:** система после вставки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс поверхности (0-based) |
| `count` | `int` | — | `1` | — | число копий |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surface.get

Полные атрибуты поверхности по индексу (0-based)

**Returns:** словарь поверхности

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс поверхности (0-based) |

### system.surface.move

Переставить поверхность на новую позицию (0-based)

**Returns:** система после перестановки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | откуда (0-based) |
| `to` | `int` | да | `null` | — | куда (0-based) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surface.n.set

Переопределить показатели преломления поверхности: {λ мкм: n} вместо каталога стёкол

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс поверхности (0-based) |
| `n_override` | `dict` | да | `null` | — | словарь {длина волны мкм: показатель n} |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surface.remove

Удалить поверхность по индексу (0-based)

**Returns:** система после удаления (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс поверхности (0-based) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surface.set

Изменить атрибуты поверхности по индексу (0-based)

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `radius` | `float` | — | `null` | — | атрибут Surface.radius |
| `thickness` | `float` | — | `null` | — | атрибут Surface.thickness |
| `glass` | `str` | — | `null` | — | атрибут Surface.glass |
| `semi_diameter` | `float` | — | `null` | — | атрибут Surface.semi_diameter |
| `surface_type` | `str` | — | `null` | `["SPHERE", "CONIC", "ASPHERIC", "HOLOGRAM", "GRATING", "TOROIDAL"]` | атрибут Surface.surface_type |
| `conic_constant` | `float` | — | `null` | — | атрибут Surface.conic_constant |
| `is_reflective` | `bool` | — | `null` | — | атрибут Surface.is_reflective |
| `tilt_x` | `float` | — | `null` | — | атрибут Surface.tilt_x |
| `tilt_y` | `float` | — | `null` | — | атрибут Surface.tilt_y |
| `tilt_z` | `float` | — | `null` | — | атрибут Surface.tilt_z |
| `decenter_x` | `float` | — | `null` | — | атрибут Surface.decenter_x |
| `decenter_y` | `float` | — | `null` | — | атрибут Surface.decenter_y |
| `index` | `int` | да | `null` | — | индекс поверхности (0-based) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.surfaces.list

Список поверхностей системы (полные атрибуты)

**Returns:** список словарей поверхностей

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.validate

Санити-проверки системы: структура, апертура, поля, λ, стёкла (в каталогах), параксиальный расчёт

**Returns:** {valid, errors: [...], warnings: [...], checks}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.wavelengths.add

Добавить рабочую длину волны (мкм)

**Returns:** система после добавления (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `value` | `float` | да | `null` | — | длина волны, мкм |
| `weight` | `float` | — | `1.0` | — | вес |
| `name` | `str` | — | `""` | — | имя спектральной линии |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.wavelengths.clear

Удалить все рабочие длины волн

**Returns:** система после очистки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.wavelengths.list

Список рабочих длин волн системы

**Returns:** список {value, weight, name}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.wavelengths.primary

Основная длина волны системы (расчёты по умолчанию)

**Returns:** {value, name} (мкм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### system.wavelengths.remove

Удалить рабочую длину волны по индексу

**Returns:** система после удаления (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс λ (0-based) |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.wavelengths.set

Заменить весь набор рабочих длин волн системы

**Returns:** система после замены (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wavelengths` | `list` | да | `null` | — | [{value, weight, name}, …] — value обязательно, name — имя спектральной линии |
| `name` | `str` | — | `null` | — | результат — в контекст REPL под именем |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

### system.wavelengths.weight.set

Задать вес длины волны по индексу

**Returns:** система после правки (+saved при out)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `index` | `int` | да | `null` | — | индекс λ (0-based) |
| `weight` | `float` | да | `null` | — | вес |
| `out` | `str` | — | `null` | — | сохранить результат по расширению пути |

