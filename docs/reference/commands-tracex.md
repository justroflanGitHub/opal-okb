# Категория tracex

22 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`tracex.apertures.fill`](#tracexaperturesfill) | Заполнение полудиаметров поверхностей ходом крайних лучей пучка: высоты, доля заполнения, минимально необходимый полудиаметр | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {rows: [{n, semi_diameter, y_upper, y_lower, y_max_abs, fill_fraction, min_sd_required, violation}]} |
| [`tracex.exit.cone`](#tracexexitcone) | Выходной конус пучка: углы крайних лучей в пространстве изображений, диаметр пучка на изображении, NA' и рабочее F/# (сравнение с параксиальным) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {u_upper_deg, u_lower_deg, half_angle_deg, beam_diameter_mm, na_prime, f_number_real, f_number_paraxial} |
| [`tracex.fan.zones`](#tracexfanzones) | Меридиональный веер по ЗОНАМ зрачка равной площади (1, √((n−1)/n), ...): координаты на изображении и поперечная аберрация относительно главного луча | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `n_zones`, `zones`, `wl` | {zones: [{rho, success, error, y_img, dy_vs_chief, opl}]} |
| [`tracex.grid.stats`](#tracexgridstats) | Сводка сетки 3D по кольцам зрачка: доли успеха, разбивка по ошибкам трассировки, статистика ОПС и разброс точек на изображении | `file`, `system`, `lbo_index`, `lbo_name`, `num_rings`, `num_azimuths`, `field_y`, `wl` | {total, success, failed, by_error, opl_min, opl_max, opl_mean, last_point_rms, max_radius_mm} |
| [`tracex.meridional.table`](#tracexmeridionaltable) | Меридиональная таблица пучка: высоты и углы верхнего/нижнего крайних и главного лучей по поверхностям, полувысота и угол конуса пучка | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {rows: [{n, y_upper, y_lower, y_chief, u_upper_deg, u_lower_deg, u_chief_deg, semi_height, cone_half_deg}], image_row} |
| [`tracex.opl.summary`](#tracexoplsummary) | Сводка длины пути и ОПС габаритных лучей до плоскости изображения + ОПД относительно главного луча (мм и волны) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {rays: [{key, label, success, path_length, opl, d_opl_mm, d_opl_waves}], mean_opl, opd_spread_mm} |
| [`tracex.opl.table`](#tracexopltable) | Ход ОПС по поверхностям для габаритных лучей пучка (верх/низ/главный/саг±1): n·L нарастающим итогом | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {rows: [{n, opl_upper, opl_lower, opl_chief, opl_sag_plus, opl_sag_minus}], keys} |
| [`tracex.paraxial.gaps`](#tracexparaxialgaps) | Параксиальный ход пучка по промежуткам: высота крайевого луча на границах, угол, диаметр пучка, увеличение промежутка (масштаб — реальный зрачок) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {scale_mm, rows: [{gap, after_n, d, n, y_start, y_end, u_deg, beam_diameter, magnification}]} |
| [`tracex.paraxial.invariants`](#tracexparaxialinvariants) | Инвариант Лагранжа-Гельмгольца по промежуткам: H = y_гл·(nu)_кр − y_кр·(nu)_гл в каждом промежутке (проверка постоянства параксиального переноса) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {rows: [{gap, after_n, n_medium, H}], H_min, H_max, drift} |
| [`tracex.paraxial.matrices`](#tracexparaxialmatrices) | ABCD-матрицы параксиального переноса: матрицы преломления/отражения по поверхностям, трансляции по промежуткам и накопленная матрица системы (efl = −1/C, сверка с paraxial_trace) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {surfaces: [{n, kind, phi, M}], gaps: [{after_n, d, n, T}], system_ABCD, det, efl_from_matrix, efl_paraxial} |
| [`tracex.paraxial.ray`](#tracexparaxialray) | Параксиальная трассировка ПРОИЗВОЛЬНОГО луча (y₀, u₀ на первой поверхности) по поверхностям: y, n·u и углы до/после преломления | `file`, `system`, `lbo_index`, `lbo_name`, `y0`, `u0`, `wl` | {y0, u0_rad, rows: [{n, y, u_before_rad, u_after_rad, nu_after, n_after, phi}], image_y, image_u_rad} |
| [`tracex.pupils.surfaces`](#tracexpupilssurfaces) | Проекция зрачков на поверхности: высоты главного луча (центры зрачков) и полувысоты пучка по поверхностям + отрезки входного/выходного зрачка | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl` | {entrance_pupil_z, exit_pupil_z, epd_mm, rows: [{n, z, pupil_center_y, dz_to_entrance, dz_to_exit, semi_height_up, semi_height_low}]} |
| [`tracex.ray.angles`](#tracexrayangles) | Углы падения/преломления ЗАДАННОГО луча на каждой поверхности: cos I, cos I', I, I' (нормали — в локальной СК поверхности) | `file`, `system`, `lbo_index`, `lbo_name`, `x`, `y`, `z`, `k`, `l`, `m`, `wl` | {success, error, rows: [{n, cos_i, cos_t, i_deg, t_deg, n_before, n_after, reflective, tir_margin}]} |
| [`tracex.ray.multi_wl`](#tracexraymulti_wl) | Луч поля через точку зрачка по ВСЕМ λ системы: координаты на изображении и ОПС по длинам волн | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `rho_x`, `rho_y` | {rows: [{wl, success, error, last_point, y_img, opl}]} |
| [`tracex.ray.pupil`](#tracexraypupil) | Трассировка луча ПОЛЯ через заданную точку входного зрачка (доли полуапертуры; построитель габаритных лучей TABESB) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `rho_x`, `rho_y`, `wl` | {wl, field_y, rho_x, rho_y, success, error, surfaces_hit, opl, path} |
| [`tracex.ray.surfaces`](#tracexraysurfaces) | Таблица ЗАДАННОГО луча по поверхностям: координаты, углы сегментов, ОПС нарастающим итогом (Снеллиус, точный трейсер) | `file`, `system`, `lbo_index`, `lbo_name`, `x`, `y`, `z`, `k`, `l`, `m`, `wl` | {success, error, opl_total, rows: [{n, x, y, z, u_y_deg, u_x_deg, opl_cum_mm, clipped?}], image} |
| [`tracex.stop.clearance`](#tracexstopclearance) | Клиренс луча до края апертурной диафрагмы: положение луча в плоскости диафрагмы, запас в мм и долях радиуса (диафрагма НА поверхности — клиренс до её полудиаметра) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `rho_x`, `rho_y`, `wl` | {stop_surface, stop_z, on_surface, stop_radius_mm, r_at_stop, clearance_mm, clearance_frac, reached, passed} |
| [`tracex.surface.glasses`](#tracexsurfaceglasses) | Таблица сред по поверхностям для трассируемой λ: стекло, n до/после, скачок Δn (зеркала — без скачка) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {rows: [{n, glass, n_before, n_after, dn, reflective}]} |
| [`tracex.surface.vertices`](#tracexsurfacevertices) | Таблица вершин поверхностей: Z-координаты, расстояния между вершинами, радиусы, стёкла, полудиаметры, длина хода нарастающим итогом | `file`, `system`, `lbo_index`, `lbo_name` | {rows: [{n, z_vertex, radius, glass, semi_diameter, thickness, dz_to_next, track_cum}], total_track_mm} |
| [`tracex.tir.critical`](#tracextircritical) | Предельные углы полного внутреннего отражения по поверхностям (asin n₂/n₁ для сред с n₁>n₂) | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {rows: [{n, glass, n_before, n_after, critical_deg, tir_possible, reflective}]} |
| [`tracex.vignetted.rays`](#tracexvignettedrays) | Срезанные лучи сетки 3D: какие лучи по кольцам/азимутам не прошли и на какой ошибке (EDGE — кромка, STOP — диафрагма, MISS/TIR) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rings`, `num_azimuths`, `field_y`, `wl` | {total, failed, rays: [{rho, phi_deg, error, surfaces_hit, last_point}]} |
| [`tracex.ynu.table`](#tracexynutable) | ynu-таблица базисных параксиальных лучей по поверхностям: y и n·u крайевого (y=1, u=0) и главного (y=0, u=1) лучей + кардинальные итоги | `file`, `system`, `lbo_index`, `lbo_name`, `wl` | {start, rows: [{n, y_marginal, nu_marginal, y_chief, nu_chief}], image, efl, bfd} |

## Параметры и результаты

### tracex.apertures.fill

Заполнение полудиаметров поверхностей ходом крайних лучей пучка: высоты, доля заполнения, минимально необходимый полудиаметр

**Returns:** {rows: [{n, semi_diameter, y_upper, y_lower, y_max_abs, fill_fraction, min_sd_required, violation}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.exit.cone

Выходной конус пучка: углы крайних лучей в пространстве изображений, диаметр пучка на изображении, NA' и рабочее F/# (сравнение с параксиальным)

**Returns:** {u_upper_deg, u_lower_deg, half_angle_deg, beam_diameter_mm, na_prime, f_number_real, f_number_paraxial}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.fan.zones

Меридиональный веер по ЗОНАМ зрачка равной площади (1, √((n−1)/n), ...): координаты на изображении и поперечная аберрация относительно главного луча

**Returns:** {zones: [{rho, success, error, y_img, dy_vs_chief, opl}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `n_zones` | `int` | — | `3` | — | число зон (по умолчанию 3) |
| `zones` | `list` | — | `null` | — | явный список зон (доли зрачка, допускаются отрицательные; по умолчанию — зоны равной площади + главный) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.grid.stats

Сводка сетки 3D по кольцам зрачка: доли успеха, разбивка по ошибкам трассировки, статистика ОПС и разброс точек на изображении

**Returns:** {total, success, failed, by_error, opl_min, opl_max, opl_mean, last_point_rms, max_radius_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rings` | `int` | — | `3` | — | колец зрачка |
| `num_azimuths` | `int` | — | `8` | — | азимутальных лучей на кольцо |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.meridional.table

Меридиональная таблица пучка: высоты и углы верхнего/нижнего крайних и главного лучей по поверхностям, полувысота и угол конуса пучка

**Returns:** {rows: [{n, y_upper, y_lower, y_chief, u_upper_deg, u_lower_deg, u_chief_deg, semi_height, cone_half_deg}], image_row}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.opl.summary

Сводка длины пути и ОПС габаритных лучей до плоскости изображения + ОПД относительно главного луча (мм и волны)

**Returns:** {rays: [{key, label, success, path_length, opl, d_opl_mm, d_opl_waves}], mean_opl, opd_spread_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.opl.table

Ход ОПС по поверхностям для габаритных лучей пучка (верх/низ/главный/саг±1): n·L нарастающим итогом

**Returns:** {rows: [{n, opl_upper, opl_lower, opl_chief, opl_sag_plus, opl_sag_minus}], keys}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.paraxial.gaps

Параксиальный ход пучка по промежуткам: высота крайевого луча на границах, угол, диаметр пучка, увеличение промежутка (масштаб — реальный зрачок)

**Returns:** {scale_mm, rows: [{gap, after_n, d, n, y_start, y_end, u_deg, beam_diameter, magnification}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.paraxial.invariants

Инвариант Лагранжа-Гельмгольца по промежуткам: H = y_гл·(nu)_кр − y_кр·(nu)_гл в каждом промежутке (проверка постоянства параксиального переноса)

**Returns:** {rows: [{gap, after_n, n_medium, H}], H_min, H_max, drift}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.paraxial.matrices

ABCD-матрицы параксиального переноса: матрицы преломления/отражения по поверхностям, трансляции по промежуткам и накопленная матрица системы (efl = −1/C, сверка с paraxial_trace)

**Returns:** {surfaces: [{n, kind, phi, M}], gaps: [{after_n, d, n, T}], system_ABCD, det, efl_from_matrix, efl_paraxial}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.paraxial.ray

Параксиальная трассировка ПРОИЗВОЛЬНОГО луча (y₀, u₀ на первой поверхности) по поверхностям: y, n·u и углы до/после преломления

**Returns:** {y0, u0_rad, rows: [{n, y, u_before_rad, u_after_rad, nu_after, n_after, phi}], image_y, image_u_rad}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `y0` | `float` | — | `1.0` | — | высота луча на первой поверхности, мм |
| `u0` | `float` | — | `0.0` | — | угол с осью в предметном пространстве, радианы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.pupils.surfaces

Проекция зрачков на поверхности: высоты главного луча (центры зрачков) и полувысоты пучка по поверхностям + отрезки входного/выходного зрачка

**Returns:** {entrance_pupil_z, exit_pupil_z, epd_mm, rows: [{n, z, pupil_center_y, dz_to_entrance, dz_to_exit, semi_height_up, semi_height_low}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.ray.angles

Углы падения/преломления ЗАДАННОГО луча на каждой поверхности: cos I, cos I', I, I' (нормали — в локальной СК поверхности)

**Returns:** {success, error, rows: [{n, cos_i, cos_t, i_deg, t_deg, n_before, n_after, reflective, tir_margin}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `x` | `float` | — | `0.0` | — | старт луча X, мм |
| `y` | `float` | — | `0.0` | — | старт луча Y, мм |
| `z` | `float` | — | `0.0` | — | старт луча Z, мм |
| `k` | `float` | — | `0.0` | — | направление X (нормируется) |
| `l` | `float` | — | `0.0` | — | направление Y (нормируется) |
| `m` | `float` | — | `1.0` | — | направление Z (нормируется) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.ray.multi_wl

Луч поля через точку зрачка по ВСЕМ λ системы: координаты на изображении и ОПС по длинам волн

**Returns:** {rows: [{wl, success, error, last_point, y_img, opl}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `rho_x` | `float` | — | `0.0` | — | точка зрачка X, доли полуапертуры |
| `rho_y` | `float` | — | `0.0` | — | точка зрачка Y, доли полуапертуры |

### tracex.ray.pupil

Трассировка луча ПОЛЯ через заданную точку входного зрачка (доли полуапертуры; построитель габаритных лучей TABESB)

**Returns:** {wl, field_y, rho_x, rho_y, success, error, surfaces_hit, opl, path}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `rho_x` | `float` | — | `0.0` | — | точка зрачка X, доли полуапертуры (−1..1) |
| `rho_y` | `float` | — | `0.0` | — | точка зрачка Y, доли полуапертуры (−1..1) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.ray.surfaces

Таблица ЗАДАННОГО луча по поверхностям: координаты, углы сегментов, ОПС нарастающим итогом (Снеллиус, точный трейсер)

**Returns:** {success, error, opl_total, rows: [{n, x, y, z, u_y_deg, u_x_deg, opl_cum_mm, clipped?}], image}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `x` | `float` | — | `0.0` | — | старт луча X, мм |
| `y` | `float` | — | `0.0` | — | старт луча Y, мм |
| `z` | `float` | — | `0.0` | — | старт луча Z, мм |
| `k` | `float` | — | `0.0` | — | направление X (нормируется) |
| `l` | `float` | — | `0.0` | — | направление Y (нормируется) |
| `m` | `float` | — | `1.0` | — | направление Z (нормируется) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.stop.clearance

Клиренс луча до края апертурной диафрагмы: положение луча в плоскости диафрагмы, запас в мм и долях радиуса (диафрагма НА поверхности — клиренс до её полудиаметра)

**Returns:** {stop_surface, stop_z, on_surface, stop_radius_mm, r_at_stop, clearance_mm, clearance_frac, reached, passed}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `rho_x` | `float` | — | `0.0` | — | точка зрачка X, доли полуапертуры |
| `rho_y` | `float` | — | `0.0` | — | точка зрачка Y, доли полуапертуры |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.surface.glasses

Таблица сред по поверхностям для трассируемой λ: стекло, n до/после, скачок Δn (зеркала — без скачка)

**Returns:** {rows: [{n, glass, n_before, n_after, dn, reflective}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.surface.vertices

Таблица вершин поверхностей: Z-координаты, расстояния между вершинами, радиусы, стёкла, полудиаметры, длина хода нарастающим итогом

**Returns:** {rows: [{n, z_vertex, radius, glass, semi_diameter, thickness, dz_to_next, track_cum}], total_track_mm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### tracex.tir.critical

Предельные углы полного внутреннего отражения по поверхностям (asin n₂/n₁ для сред с n₁>n₂)

**Returns:** {rows: [{n, glass, n_before, n_after, critical_deg, tir_possible, reflective}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.vignetted.rays

Срезанные лучи сетки 3D: какие лучи по кольцам/азимутам не прошли и на какой ошибке (EDGE — кромка, STOP — диафрагма, MISS/TIR)

**Returns:** {total, failed, rays: [{rho, phi_deg, error, surfaces_hit, last_point}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rings` | `int` | — | `3` | — | колец зрачка |
| `num_azimuths` | `int` | — | `8` | — | азимутальных лучей на кольцо |
| `field_y` | `float` | — | `0.0` | — | поле (град / мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### tracex.ynu.table

ynu-таблица базисных параксиальных лучей по поверхностям: y и n·u крайевого (y=1, u=0) и главного (y=0, u=1) лучей + кардинальные итоги

**Returns:** {start, rows: [{n, y_marginal, nu_marginal, y_chief, nu_chief}], image, efl, bfd}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

