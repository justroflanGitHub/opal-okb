# W4_INVENTORY_panel.md — инвентаризация `gui/analysis_panel.py` (Волна 4, src=panel)

Источник: `gui/analysis_panel.py` (68 методов). Живой расчёт всех таблиц
переведён на команды реестра через `gui/cmdbridge.py`
(`panel._run_cmd(name, sys, **kwargs)` кладёт живую систему GUI в
`CommandContext` под именем `'gui'` и вызывает `cmdbridge.execute`).

Классы по ТЗ (`docs/tasks/TASK_COMMANDS_W4.md`, п. 1):

* **bound** — логика покрыта командой реестра, обработчик вызывает её через bridge;
* **gap** — команды не было, создана в `commands/builtin/w4_panel_cmds.py`;
* **ui-only** — чистый UI/рендер/данные пайплайна, командой не становится;
* **direct-keep** — живой Qt-интерактив, остался прямым.

## Сводка

| Класс | Методов | Примечание |
|---|---|---|
| bound | 26 | 33 вызова `_run_cmd`, 18 разных команд Волн 1+3 + 2 новых |
| gap (новые команды) | 2 | `panel.spot.summary`, `panel.psf.stats` |
| ui-only | 39 | рендер/тумблеры/настройки/данные пайплайна |
| direct-keep | 1 | `_export_zernike_global` (QFileDialog) |
| инфраструктура | 2 | `__init__` (контекст+регистрация), `_run_cmd` (bridge-обёртка) |

## bound — перевязано на команды (26 методов)

| Метод | Команда(ы) | Параметры из GUI |
|---|---|---|
| `analyze` | `calc.paraxial` + `calc.seidel` | живая система; ошибка → `report_error` + пустые dict (раньше — необработанное исключение) |
| `_update_parax_table` | `calc.paraxial.multi_wl` | — (живой путь; иначе рендер `_parax_data` пайплайна) |
| `_efl_mm` | `calc.paraxial` | — (fallback при пустом `_parax_data`) |
| `_update_spot_table` | **`panel.spot.summary`** (gap) | `num_rays=40`, `field_y=0` |
| `_update_axial_table` | `aber.fan` + `aber.isoplanatism` | `wl` первичная, `num_rays=30` |
| `_update_transverse_table` | `aber.fan` | `wl`, `num_rays=30` |
| `_update_longitudinal_table` | `aber.fan` | `wl`, `num_rays=30` |
| `_update_wavefront_table` | `aber.fan` | `wl`, `num_rays=30` |
| `_update_mtf_table` | `aber.mtf_geo` + `diffr.mtf.quick` + `diffr.mtf.limited` | `max_freq=100`, `num_freqs=20`, `num_rays=40` (у mtf_geo — как в живом расчёте, не дефолт 50) |
| `_update_distortion_table` | `analyze.field_aberrations` | `wl`, поле |
| `_update_astigmatism_table` | `analyze.field_aberrations` | `wl`, поле |
| `_update_coma_table` | `analyze.field_aberrations` | `wl`, поле |
| `_update_focus_table` | `aber.focus_curve` | `num_points=40`, `defocus_range=2.0`, `freq_lpmm=50.0`, `num_rays=25`, `field_y=0` |
| `_update_psf_table` | **`panel.psf.stats`** (gap) | `wl`, `num_rays=64` |
| `_update_lsf_table` | `adv.lsf` ×2 (мер + саг) | `wl`, `num_rays=64`, `direction` |
| `_update_enc_table` | `adv.enc` | `wl`, `num_rays=100` |
| `_update_ptf_table` | `adv.ptf` | `wl`, `num_rays=64` |
| `_update_beam_table` | `calc.beam_geometry` | `semi_mode`/`sharp_edge` из настроек панели |
| `_update_chief_table` | `aber.chief` | — (живой путь; иначе данные пайплайна) |
| `_update_gauge_rays_table` | `aber.gauge_rays` | — |
| `_update_zernike_table` | `zern.coeffs` + `zern.chromatic` | `wl`, `num_rays=32`, `max_order=4`, `defocus_offset` из GUI |
| `_update_zernike_global` | `zern.global` | — (живой путь; готовый текст в ответе; precomputed-путь — форматтер, см. ui-only) |
| `_update_wfmap_table` | `zern.wavefront` | `wl`, `grid_size=48`, `defocus_offset`, `include_grid=True` (fallback, сначала кэш виджета) |
| `_update_esf_table` | `adv.esf` | `wl` |
| `_update_bar_target_table` | `adv.bar_mtf` | `wl` (fallback, сначала кэш mtf_table) |
| `_build_tables_precomputed` | `aber.gauge_rays` | `wl` (только fallback-ветка габаритных лучей; остальное — рендер готовых данных пайплайна) |

## gap — новые команды (2)

Файл `commands/builtin/w4_panel_cmds.py`, категория `panel`, регистрация —
`register(registry)` / `ensure_registered()` (идемпотентно; GUI вызывает сам,
т.к. `commands/builtin/__init__.py` не трогается до мержа — п. 5 ТЗ).

| Команда | Что закрывает | Контракт |
|---|---|---|
| `panel.spot.summary` | таблица «Точечная диагр.»: сводка по каждой λ + полихроматическая строка | `{field_y, num_rays, num_wavelengths, rows: [{kind: mono\|poly, wl, num_points, rms, rms_x, rms_y, centroid_y, max_r}]}` — объединяет `analyze.spot`/`aber.spot_poly`/`aber.rms_poly` точно по колонкам таблицы |
| `panel.psf.stats` | таблица «PSF»: скалярные метрики ФРТ | `{wl, num_rays, pixel_um, max_intensity, center_x_um, center_y_um, width_mer_um, width_sag_um}`; решётки ФРТ в UI не передаются; формулы перенесены из панели без изменений |

## ui-only — не тронуты (39)

Рендер готовых данных / состояние GUI / настройки — командами не становятся
(п. 1 ТЗ: «переключить вкладку, zoom, показать окно»):

* каркас/тумблеры: `__init__`*¹, `_on_mode_toggle`, `_set_table`,
  `_refresh_zernike_tables`, `_on_zernike_chromatic_toggle`;
* приёмники данных пайплайна: `update_parax`, `update_seidel`,
  `apply_precomputed`, `_build_tables_precomputed` (кроме gauge-fallback),
  `_build_wf_rms_table_precomputed`, `apply_phase1`, `apply_phase2`,
  `apply_results`, `_build_zernike_chromatic_table`,
  `_update_zernike_global` (precomputed-ветка: форматтер
  `format_global_zernike_text` готового результата — рендер, не расчёт);
* таблицы из кэша виджетов (без живого расчёта): `_update_heatmap_table`,
  `_update_focus_diag_table`, `_update_psf3d_table`,
  `_update_wf_rms_field_table`, `_update_seidel_table`;
* настройки/геттеры: `get_defocus_offset`, `get_azimuth`
  (нормализация угла — inline `% 360`, был импорт утилиты analysis),
  `get_focus_step`, `get_beam_semi_mode`, `get_beam_sharp_edge`,
  `get_pupil_unit`, `_on_pupil_unit_changed`, `_on_pupil_unit_state_changed`,
  `_push_field_context`, `_refresh_field_tables`, `_field_cell`,
  `_field_unit_label`, `_wl_names`, `set_wavefront_3d`,
  `wavefront_3d_enabled`;
* рендер-строители: `_gauge_point_labels` (подписи точек;
  `compute_z_positions` из `optics_utils` — утилита, не analysis),
  `_build_gauge_rays_tables` (работает и с JSON-данными команды, и с
  нативными кортежами — существующие pytest-qt тесты инжектят данные
  напрямую).

*¹ `__init__` дополнительно создаёт `CommandContext` и вызывает
`w4_panel_cmds.ensure_registered()` — инфраструктура перевязки, не логика.
`_run_cmd` — bridge-обёртка (контекст + `cmdbridge.execute`).

## direct-keep — осталось прямым (1)

| Метод | Почему прямой |
|---|---|
| `_export_zernike_global` | живой Qt-интерактив: `QFileDialog.getSaveFileName` + запись текстового файла; текст берётся из уже построенного виджета (`QPlainTextEdit.toPlainText`), расчёта нет — командой не становится (п. 1 ТЗ) |

## Адаптеры (п. 4 ТЗ — контракты команд не менялись)

* `aber.fan` возвращает `rays` списком dict — таблицы пучков читают ключи
  `pupil_y/dy/ds/wave/success` напрямую (формат совместим);
* `_update_axial_table`: сшивка `aber.isoplanatism` с веером —
  `dict(zip(pupil, eta))` в обработчике (адаптер на стороне виджета);
* `_update_zernike_table`: `[(row['coeff'], row['name']) for row in …]`
  из `zern.coeffs` (адаптер на стороне виджета);
* `_update_wfmap_table`: `np.array(res.data['wavefront'])` /
  `np.array(res.data['pupil_mask'])` из JSON-списков `zern.wavefront`;
* `_update_zernike_global`: живой путь берёт готовый `text` из `zern.global`
  (безымянные λ в тексте команды помечаются «0.588» вместо «0.5876 0.588»
  живого форматтера — контракт Волны 3 заморожен; precomputed-путь
  сохраняет исходное форматирование).

## Тесты

`tests/test_commands_w4_panel.py` (21 тест): smoke+паритет обеих gap-команд
(сверка с прямыми вызовами analysis), идемпотентность регистрации, bridge
`execute`/`report_error`, перевязка живых таблиц offscreen, деградация при
ошибке команды («Нет данных», не исключение), guard исходника панели
(запрещённые compute-вызовы + whitelist импортов шимов).
