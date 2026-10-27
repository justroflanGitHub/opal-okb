# Категория panel

2 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`panel.psf.stats`](#panelpsfstats) | Скалярные метрики дифракционной ФРТ для таблицы панели: размер пикселя, максимум, центр пика, ширины меридиональная/сагиттальная по полумаксимуму | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `num_rays`, `field_y`, `defocus_mm` | {wl, num_rays, pixel_um, max_intensity, center_x_um, center_y_um, width_mer_um, width_sag_um} |
| [`panel.spot.summary`](#panelspotsummary) | Сводка точечной диаграммы для таблицы панели: по каждой рабочей λ + полихроматическая строка (RMS по осям, центроид, макс. радиус) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y` | rows [{kind: mono\|poly, wl, num_points, rms, rms_x, rms_y, centroid_y, max_r}] |

## Параметры и результаты

### panel.psf.stats

Скалярные метрики дифракционной ФРТ для таблицы панели: размер пикселя, максимум, центр пика, ширины меридиональная/сагиттальная по полумаксимуму

**Returns:** {wl, num_rays, pixel_um, max_intensity, center_x_um, center_y_um, width_mer_um, width_sag_um}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `num_rays` | `int` | — | `64` | — | размер сетки зрачка ФРТ |
| `field_y` | `float` | — | `0.0` | — | поле |
| `defocus_mm` | `float` | — | `0.0` | — | смещение плоскости установки, мм |

### panel.spot.summary

Сводка точечной диаграммы для таблицы панели: по каждой рабочей λ + полихроматическая строка (RMS по осям, центроид, макс. радиус)

**Returns:** rows [{kind: mono\|poly, wl, num_points, rms, rms_x, rms_y, centroid_y, max_r}]

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `40` | — | лучей по стороне сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |

