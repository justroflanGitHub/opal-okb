# W4_INVENTORY_main.md — инвентаризация экшенов main.py (агент src=main)

Источник: `main.py` (главное окно PyQt5: меню, тулбар, кнопки, виджеты).
Реестр на входе: 128 команд Волн 1+3. Классификация по TASK_COMMANDS_W4.md:
`bound` (готовая команда), `gap` (новая команда `w4_main_cmds.py`),
`ui-only` (чистый UI), `direct-keep` (живой Qt-интерактив / делегирование).

Мост: `gui/cmdbridge.py` (создан этим агентом). Перевязанные обработчики
начинаются с `bridge.set_current(self.current_system)` — синхронизация
состояния GUI → контекст команд; команды без параметра-источника работают
с текущей системой контекста (REPL-семантика).

## Меню «Файл»

| # | Экшен | Обработчик | Класс | Команда |
|---|-------|-----------|-------|---------|
| 1 | Новая система (Ctrl+N; тулбар «📄 Новый») | `_new_system` | bound | `system.new` (demo=empty, name) + `system.fields.add` (y=0) |
| 2 | Открыть… (Ctrl+O) | `_open_file` | bound | `system.load` (кладёт систему в контекст моста) |
| 3 | Сохранить (Ctrl+S) | `_save_file` | bound | `file.save` |
| 4 | Сохранить как… (Ctrl+Shift+S) | `_save_file_as` | bound | `file.save` |
| 5 | Присоединить… | `_append_system` | **gap** | `system.append` |
| 6 | Библиотека… | `_show_library` | **gap** | `catalog.library.create` (выбор записи — диалог, ui) |
| 7 | Экспорт протокола… | `_export_protocol` | **gap** | `file.export.protocol` (.txt) / `file.save` (.opj) |
| 8 | Демо: Линза (Ctrl+D; тулбар «🔧 Демо») | `_load_demo` | bound | `system.new` (demo=default) |
| 9 | Демо: Тонкая линза (f'=77) | `_load_demo` | bound | `system.new` (demo=default) |
| 10 | Демо: Ахромат (2 линзы) | `_load_demo_by_name('achromat')` | bound | `system.new` |
| 11 | Демо: Дублет Кука f/5 | `…('cook_doublet')` | bound | `system.new` |
| 12 | Демо: Телеобъектив | `…('telephoto')` | bound | `system.new` |
| 13 | Демо: Объектив Петцваля | `…('petzval')` | bound | `system.new` |
| 14 | Демо: Зеркало (вогнутое) | `…('mirror')` | bound | `system.new` |
| 15 | Демо: Мениск (Росс) | `…('meniscus')` | bound | `system.new` |
| 16 | Демо: Плоско-выпуклая линза | `…('plano_convex')` | bound | `system.new` |
| 17 | Выход (Ctrl+Q) | `close` | ui-only | — |

## Меню «Система»

| # | Экшен | Обработчик | Класс | Команда |
|---|-------|-----------|-------|---------|
| 18 | Обернуть | `_reverse_system` | **gap** | `system.reverse` |
| 19 | Масштаб… | `_scale_system` | **gap** | `system.scale` |
| 20 | Стандартные радиусы (ГОСТ)… | `_standardize_radii` | **gap** | `system.radii.changes` (предпросмотр) + `system.radii.standardize` (применение) |
| 21 | Ахромат… | `_design_achromat` | **gap** | `system.achromat` (параметры — диалог, ui) |
| 22 | Подгонка… | `_fit_dialog` | bound | `calc.paraxial` (умные дефолты) + `opt.solve` (1×1); ветка ЛАП `_run_lap_optimization` — direct-keep (см. итог) |

## Меню «Характеристики»

| # | Экшен | Обработчик | Класс | Команда |
|---|-------|-----------|-------|---------|
| 23 | Точки поля… | `_show_field_points_dialog` | **gap** | `system.fields.set` (диалог редактирования — ui) |
| 24 | Спектральные линии… | `_show_spectral_dialog` | **gap** | `system.wavelengths.set` (диалог — ui) |

## Меню «Вид» / «Расчёт» / «Помощь»

| # | Экшен | Обработчик | Класс | Команда |
|---|-------|-----------|-------|---------|
| 25 | Диаграмма стёкол | `_show_glass_diagram` | ui-only | показ интерактивного matplotlib-окна (GlassDiagramWindow, zoom/pan); обработчик только собирает имена стёкол для подсветки — рендер-параметр окна |
| 26 | Параксиальный расчёт | `_calculate` | direct-keep | делегирует `CalculationController` (gui/controllers — зона агента panel) |
| 27 | Суммы Зейделя | `_calculate` | direct-keep | тот же контроллер |
| 28 | О программе | `_about` | ui-only | — |

## Кнопки главного окна

| # | Кнопка | Обработчик | Класс | Команда |
|---|-------|-----------|-------|---------|
| 29 | + Поверхность | `_add_surface` | direct-keep | делегирует `SystemController` (gui/controllers — зона panel) |
| 30 | − Удалить | `_del_surface` | direct-keep | там же |
| 31 | ⚙ Рассчитать (+ тулбар «▶ Рассчитать») | `_calculate` | direct-keep | `CalculationController` |
| 32 | Сброс (вид) | `viz.reset_view` | ui-only | — |
| 33 | Z+ / Z− | `viz.zoom_in/out` | ui-only | — |
| 34 | Таблица | `_show_ray_table` | bound | `aber.gauge_rays` (адаптер данных → `_build_gauge_rays_tables`) |
| 35 | 2D/3D (волн. фронт) | `_toggle_wavefront_3d` | ui-only | вкладка + режим панели |
| 36 | Хром.Ц | `_toggle_chromatic_rays` | ui-only | рендер лучей в viz |
| 37 | 3D | `_toggle_viz_3d` | ui-only | QStackedWidget |

## Сигналы виджетов (без бизнес-логики)

| # | Виджет/сигнал | Класс | Примечание |
|---|---------------|-------|------------|
| 38 | ResultsPanel: Ctrl+C (parax/seidel) | ui-only | копирование выделения в буфер |
| 39 | ResultsPanel: комбобокс единиц зрачков | ui-only | общее состояние utils (п. 16) |
| 40 | FieldPointsWidget: +/−/Авто | ui-only | редактирование таблицы диалога |
| 41 | SystemParamsWidget: тип/мера/величина | ui-only | автонастройка полей, подпись Г.ММСС |
| 42 | SurfaceTable.load_system (колонки n) | ui-only | рендер: `refractive_index` для ячейки |

## Методы с прямой логикой (перевязаны, не экшены)

| Метод | Класс | Команды |
|-------|-------|---------|
| `ResultsPanel.update_results` | bound | `calc.paraxial`, `calc.seidel`, `strehl.calc`, `calc.paraxial.multi_wl` |
| `MainWindow._refresh_ui` (Штрель) | bound | `strehl.calc` |
| `MainWindow._init_new_system` | bound | `system.new` + `system.fields.add` (тот же путь, что `_new_system`, без диалога) |

## Итог

- **bound**: 23 экшена (№1–4, 8–16, 22 — solve-часть, 29–31 тулбар-дубли
  в №1/8/31, 34) + 3 метода с логикой (`update_results`, `_refresh_ui`,
  `_init_new_system`)
- **gap**: 8 экшенов → 10 новых команд (`system.append`, `system.reverse`,
  `system.scale`, `system.radii.changes`, `system.radii.standardize`,
  `system.achromat`, `system.fields.set`, `system.wavelengths.set`,
  `catalog.library.create`, `file.export.protocol`)
- **ui-only**: 18 (№17, 25, 28, 32, 33, 35–37, 38–42)
- **direct-keep**: 6 (№26, 27, 29, 30, 31 + ветка ЛАП №22):
  - №26–31 — делегирование в `gui/controllers/*` (зона агента panel;
    перевязка самих контроллеров — в волне panel);
  - `_run_lap_optimization` (ветка ЛАП №22) — контракт `opt.run` (Волна 3)
    не имеет параметров damping/callback, без которых невозможен пошаговый
    прогресс статусбара и настройка решателя; `tests/test_optimization.py`
    пинит прямой вызов `analysis.optimization.optimize` с этими
    параметрами. Контракты Волн 1+3 заморожены (правило 4 ТЗ) →
    осознанный direct-keep, поведение не меняется вовсе.

### Отступления от «поведение не меняется» (осознанные, в пользу корректности)

1. `_save_file` для `_current_file` с расширением `.opj`: старый код писал
   JSON-текст в `.opj` (`save_json`); `file.save` выбирает формат по
   расширению → корректный бинарный `.opj` (через `save_opj`).
