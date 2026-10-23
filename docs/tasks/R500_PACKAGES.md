# R500_PACKAGES — таблица прогресса: реестр 140 → 500+

Мастер-ТЗ: `docs/tasks/TASK_REGISTRY_500.md`. Ветка `feature/registry-500`.
Каждый пакет: эскиз → модуль `commands/builtin/<домен>_<тема>.py` → smoke
(в `tests/test_commands_builtin.py` или свой тест-модуль с маркерами
`requires_*` для локальных данных) → коммит → полный `py -m pytest -q`.

Правила счёта: только реальные команды (считают/делают); `not_implemented`
в счёт не идут. Обратная совместимость 140 существующих обязательна.

## Таблица пакетов

| # | Пакет (модуль) | Домены/категории | Команд | Статус |
|---|----------------|------------------|-------:|--------|
| 1 | `export_cmds.py` | `export.*`, `tables.*.export`, `*.export` — CSV/JSON/TXT выгрузки таблиц и данных | 27 | done (+27 → 167) |
| 2 | `system_ext_cmds.py` | `system.*` — апертура/стоп/объект/поля/λ/поверхности-расширения, ctx-менеджмент, validate | 33 | done (+33 → 200) |
| 3 | `lbo_cmds.py` | `file.lbo.*`, `library.*`, `file.diff/compare` — LBO-библиотеки, пакетные прогоны, сравнение систем | 21 | done (+21 → 221) |
| 4 | `glass_ext_cmds.py` | `catalog.glass.*` расширенный, `catalog.spectral.*` — дисперсия, пары, соседние стёкла, спектральные линии | 19 | done (+19 → 240) |
| 5 | `units_cmds.py` | `units.*`, `spatial.*` — Г.ММСС, диоптрии, зрачки; матрицы поворотов | ~18 | planned |
| 6 | `calc_ext_cmds.py` | `calc.*` — показатели преломления, силы/сагитты, тонкие линзы, параксиал-производные | ~22 | planned |
| 7 | `seidel_ext_cmds.py` | `seidel3.*` — поперечные/продольные/волновые аберрации 3-го порядка из сумм Зейделя | ~14 | planned |
| 8 | `tol_cmds.py` | `tol.*` — чувствительность EFL/аберраций к радиусам/толщинам/наклонам, обратные допуски, отчёт | ~18 | planned |
| 9 | `sweep_cmds.py` | `sweep.*` — развёртки по полям/λ/дефокусу/зонам поверх существующих движков | ~24 | planned |
| 10 | `quality_cmds.py` | `quality.*` — сводные метрики качества (MTF@freq, EE-диаметры, strehl по полям, паспорт) | ~20 | planned |
| 11 | `report_cmds.py` | `report.*` — текстовые отчёты для печати (паспорт, параксиал, зейдель, таблицы, качество) | ~16 | planned |
| 12 | `plot_ext_cmds.py` | `plot.*` новые headless-графики: схема системы с лучами, каустика, виньетирование, хроматизм, волн. фронт | ~16 | planned |
| 13 | `meta_cmds.py` | `registry.*`, `app.*` — интроспекция реестра/категорий/схем для агентов | ~12 | planned |
| 14 | `adv_ext_cmds.py` | `adv.*` остатки (psf3d, свёртка, миры), `zern.*` расширения, `focus.*` расширения | ~22 | planned |
| 15 | `diffraction_ext_cmds.py` | `diffr.*`/`psf.*` расширения: сечения MTF, полихром-ЧКХ по полям, ЧКХ@freq, LSF-сечения | ~20 | planned |
| 16 | `batch_cmds.py` | `batch.*` — пакетные прогоны команд по списку систем/файлов, batch-отчёты | ~18 | planned |
| 17 | `reserve_cmds.py` + добивка | резерв: недостающие до 500+ из заблокированных/отложенных тем (diagram.*, trace.*, aber.* хвосты) | ~40 | planned |

## Заметки по пакетам (эскизы уточняются при реализации)

- **П1 export**: общий хелпер записи rows/dict/text по расширению (.csv/.json/.txt)
  в одном месте; команды-обёртки «движок таблицы + запись». Источник: ТЗ §2.3.
- **П2 system**: движки domain/aperture.py (конвертация апертур) — ещё не обёрнуты;
  ctx-менеджмент (select/list/drop/clone) — REPL-семантика W1; validate — санити
  системы (ТЗ §2.4).
- **П3 lbo**: fileio/lbo_io.load_lbo + lbo_reader.scan_lbo_directory; library.batch —
  по ТЗ §2.4; тесты с requires_lbo (extracted/ локальна, в CI нет).
- **П4 glass**: движки catalog/glass_catalog*.py + domain.calculations.refractive_index;
  пары для ахромата — через существующий конструктор system.achromat (двойка К8+ТФ).
- **П5 units**: analysis/units.py (все 7 функций ещё не обёрнуты) + domain/spatial.py.
- **П6 calc**: domain/calculations.py хвосты (refractive_index, goe_effective_radius,
  effective_semi_diameter); геометрия (сагитта, сила поверхности, тонкая линза) —
  формулы FORMULAS.md, без дублирования движков.
- **П7 seidel3**: FORMULAS.md §Зейдель — поперечные/продольные/волновые из сумм
  (Si → Δy′, Δz′, W); движок domain.calculations.seidel_aberrations.
- **П8 tol**: конечноразностная чувствительность поверх paraxial_trace /
  seidel_aberrations / spot RMS (движки есть; нового ядра не пишем — композиция).
- **П9 sweep**: циклы по полям/λ/дефокусу поверх существующих вычислителей
  (compute_spot_diagram, wavefront maps, MTF); знаменитые дубликаты
  (multi_wl, field_aberrations) не повторять.
- **П10 quality**: композиция скаляров из psf/mtf/strehl/spot для паспорта системы.
- **П11 report**: форматтеры analysis/* (format_*) + fileio/protocol.py — печать по
  ANALIZE.txt §2.9; текст целиком в ответе + опция записи.
- **П12 plot**: matplotlib Agg (образец opt_cmds.py); схема системы с лучами —
  ANALIZE.txt §4.8 «Рисунок оптической системы с трассировкой лучей».
- **П13 meta**: registry.search/list/schema как команды (единая точка для агентов).
- **П17 reserve**: добивка — именованные варианты зон/полей, недостающие
  обёртки analysis-хвостов, документирующие команды каталога/библиотеки.

## Заблокированное / отложенное

(заполняется по ходу; статус `blocked: причина`)

- Ничего пока.
