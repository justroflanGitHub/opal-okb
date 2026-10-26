# CORPUS_PLAN — чекпойнт оркестратора (TASK_CORPUS_SCAN)

Ветка `feature/corpus-scan`, worktree `C:\Users\mikhail\.openclaw\workspace\opal_okb_corpus`.
Данные (read-only, вне git): `C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\*.LBO` —
**13 библиотек, ровно 612 систем** (BINOCUL 22, LENS 116, LENS_SPC 6, MICROLEN 16, OCULAR 76,
REPROD 13, RUSSAR 84, USBINOCL 10, USEYE 8, USLENS 234, USMICRO 6, USREPROD 15, ZOOM 6).

## Подзадачи / статусы

| # | Субагент | Файлы (только эти!) | Статус |
|---|----------|---------------------|--------|
| SA-1 | сканер | `scripts/corpus_scan.py` | ✅ готов + фикс: f_check IGNORECASE (US `F'=1`, +261 система) |
| SA-2 | метрики | `scripts/corpus_stats.py` | ✅ готов |
| SA-3 | аномалии | `docs/reports/CORPUS_ANOMALIES.md` (вход: corpus.json) | ✅ готов (выполнил оркестратор — субагенты недоступны: 3× сетевые ошибки провайдера) |
| SA-4 | тесты | `tests/test_corpus_scan.py` | ✅ готов (8 тестов; без данных 3 passed/5 skipped) |
| SA-5 | доки | `docs/reports/CORPUS_REPORT.md`, `CHANGELOG.md`, `README.md`, `README_RU.md` | ✅ готов (выполнил оркестратор — та же причина) |
| ORCH | я | план, прогон корпуса, интеграция, коммиты, pytest | ✅ корпус 612/612 ok, всё закоммичено |

Коммиты — атомарно по подзадаче, только оркестратор. Запреты: `commands/`, `gui/`, `main.py`,
`tests/test_commands_*`, `tests/test_golden_*` не трогать; `extracted/` основной папки — только чтение; не пушить.

## Контракт CLI сканера (SA-1 ↔ SA-4)

```
py scripts/corpus_scan.py --lib <путь к .LBO ИЛИ к каталогу Lib> --out <файл.json> [--limit N] [--quiet]
```

- `--lib` файл → одна библиотека; каталог → все `*.LBO` по алфавиту. `--limit N` — первые N систем
  **каждой** библиотеки (для тестов). Выход — всегда один JSON-файл `--out` (каталог создаётся).
- Коды возврата: 0 — скан дошёл до конца (отказы систем ≠ ошибка скана); 2 — неверный путь/аргументы.
- stdout: прогресс по библиотекам и итоговая строка; `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.
- `sys.path` — от корня проекта (родитель `scripts/`), не хардкод основной worktree.
- Импорты: `fileio.lbo_io.load_lbo`, `domain.calculations.paraxial_trace/seidel_aberrations`,
  `analysis.tables.taboc1_rows`. Конвейен на систему: load → parse(получили system) →
  paraxial (efl/bfd/f#) → seidel → taboc1 → зрачки (finite entrance_pupil/exit_pupil).
  Каждый этап в try/except: отказ этапа не валит систему/скан, фиксируется в `ops`/`error`.

## Контракт JSON (authoritative; schema_version 1)

Верхний уровень:
```json
{
  "tool": "corpus_scan.py", "schema_version": 1, "generated": "ISO-дата",
  "source": ["<полные пути .LBO>"], "limit": null,
  "total": 612, "ok": 608, "fail": 4,
  "ops_summary": {"load": {"ok": 612, "fail": 0}, "parse": {...}, "paraxial": {...}, "seidel": {...}, "taboc1": {...}, "pupils": {...}},
  "systems": [ {система, см. ниже} ]
}
```

Система:
```json
{
  "lib": "LENS", "index": 0, "name": "Индустар-7   f'=104  2w=24 1:3.5 4линзы", "filename": "IND7.OPJ",
  "n_surfaces": 8, "n_wavelengths": 3, "glasses": ["К8", "Ф1"], "has_mirror": false,
  "status": "ok",            // ok = все 6 ops true; иначе fail
  "error": null,             // "parse: <msg>" | "paraxial: <msg>" | ... — первый отказ
  "ops": {"load": true, "parse": true, "paraxial": true, "seidel": true, "taboc1": true, "pupils": true},
  "metrics": {
    "efl": 103.84, "bfd": 88.561, "f_number": 4.104, "L": 119.761,
    "entrance_pupil": 21.008, "exit_pupil": -9.235, "entrance_pupil_diameter": 25.3,
    "seidel_SI": -0.0002, "seidel_SII": 0.0067, "seidel_SIII": -0.0997, "seidel_SIV": 0.0033, "seidel_SV": 15.66,
    "taboc1_rows": 5, "taboc1_ok": 5, "taboc1_max_abs_longitudinal_mm": 0.606
  },
  "f_check": {               // null, если в имени нет f= / f'= / ф'=
    "name_f": 104.0, "calc_f": 103.84,
    "err_pct": 0.154,        // |calc-name|/|name|*100; для hydro: |calc*1.331|-|name| .../|name|*100 (по модулю)
    "category": "ok"         // ok (≤5%) | sign_flip | hydro | truncated | diverge (>5%) | no_f
  }
}
```

Категории f_check (правила из docs/LBO_FORMAT.md и scripts/lbo_verify_f.py):
- парс имени: `f'=\s*(-?\d+...)`, `f=\s*(-?\d+...)`, `[фf]'\s*=...`; нет совпадения → `f_check=null`;
- **hydro**: «f=» без апострофа + «Гидро» в имени — каталог даёт фокус в воде: сверять `|calc*1.331|` vs `|name_f|`;
- **truncated**: `|name_f|<10` и `8 ≤ |calc/name_f| ≤ 25` — усечённое имя каталога (Юпитер-24 f'=1 → 12.2);
- **sign_flip**: знаки calc и name различаются при `||calc|-|name||/|name| ≤ 5%` — типично для зеркально-линзовых,
  **находка, не баг** (ТЗ);
- **ok**: err ≤ 5%; **diverge**: остальное. NaN/±inf в calc → category=diverge, err_pct=null.

JSON пишется `ensure_ascii=False`, encoding utf-8. Числа — float или null (не строки).

## Прогресс

- 2026-10-23: план создан; конвейер провалидирован на LENS[0] (Индустар-7: имя f'=104, расчёт 103.84, 0.15%; ~0.04 с/система → полный корпус ≈ полминуты расчёта).
- 2026-10-23/24, волна 1 (3 субагента параллельно): SA-1 сканер (612/612 ok на полном корпусе), SA-2 статистика, SA-4 тесты (8 passed) — коммиты caeb83e/f1b85de/def8aae.
- 2026-10-24: полный прогон → docs/reports/corpus.json (782 КБ) + corpus_stats.md; находка SA-интеграции: US-библиотеки пишут «F'» — regex сканера переведён на IGNORECASE (f_check: 304 → 565 имённых систем).
- 2026-10-24, SA-3 (оркестратор, субагентам мешали сетевые сбои провайдера): CORPUS_ANOMALIES.md — 48 сломанных декодов (31 US efl=0 из-за недекодированных стёкол; 17 L=0 руссары/микролен), 22 афокальных бинокля (норма), 27 честных расхождений f', таблица 150 систем >1%, гидро ×1.331 подтверждена. Коммит a25092a.
- 2026-10-24, SA-5 (оркестратор, та же причина): CORPUS_REPORT.md + CHANGELOG [1.30.0-corpus] + README.md/README_RU.md (строка «Corpus scan» в Фазе III).
- Итог: критерии ТЗ выполнены (сканер на полном корпусе, отчёт с реальными числами, тесты зелёные, план отражает вклад субагентов).

## Контракт v2 (волна 2, TASK_CORPUS_SCAN_V2)

### Операции (OPS)
- OPS = (load, parse, paraxial, seidel, taboc1, pupils, vignette, chief, spot, mtf_geo). Единый источник — кортеж OPS в scripts/corpus_scan.py; corpus_stats.py импортирует его (уже делает).
- CLI сканера: `--ops all|base|v2|<имена через запятую>`, по умолчанию all.
  - `all` — все 10 операций; `base` — 6 базовых v1 (load, parse, paraxial, seidel, taboc1, pupils); `v2` — 4 новые (vignette, chief, spot, mtf_geo); список — любое подмножество имён OPS (неизвестное имя → код возврата 2).
  - load и parse выполняются всегда и всегда присутствуют в JSON (без них нет системы); остальные операции — только выбранные.
  - При `--ops base` поведение и JSON побитово идентичны v1 (по base-ключам).
- schema_version = 2 всегда (независимо от --ops). corpus_stats.py обязан читать оба формата по data['schema_version']: 1 → только v1-секции; 2 → все секции.

### Новые ключи metrics (float | null; null при отказе операции; v1-ключи неизменны)
- **vignette** — апертурные характеристики по образцу TABBEA (analysis.vignetting.compute_vignetting):
  - `vignette_max_field` — макс. поле системы (max |field_points[].y|; град для бесконечного объекта) — поле, на котором мерилось;
  - `vignette_up_pct` / `vignette_down_pct` — виньетирование верх/низ на макс. поле, %;
  - положение выходного зрачка — существующий v1-ключ `exit_pupil` (не дублируется);
  - поля — точки поля системы; нет полей → одна осевая (max_field = 0.0).
- **chief** — аберрации главного луча на макс. поле (analysis.aberrations.compute_chief_ray_characteristics):
  - `chief_max_field` — то же поле, что vignette_max_field;
  - `distortion_pct` — дисторсия, %; `astig_Zm_mm` / `astig_Zs_mm` — астигматические отрезки Z'm/Z's, мм;
  - безполевая система (макс. поле == 0) → эти 4 ключа = null, НО ops['chief'] = true (осевой случай валиден, не ошибка).
- **spot** — RMS пятна, полихроматический (analysis.aberrations.compute_polychromatic_rms):
  - `spot_rms_axis_um` — RMS на оси, мкм; `spot_rms_max_field_um` — RMS на макс. поле, мкм (безполевая → null, op true);
  - параметры фиксированы: сетка 30×30 (круглая маска на зрачке), все длины волн системы с весами (wl.weight); мм → мкм ×1000.
- **mtf_geo** — геометрическая ЧКХ, FFT гистограммы пятна (analysis.aberrations.compute_geometric_mtf):
  - `mtf30_axis` / `mtf50_axis` — тангенциальный контраст (0..1) на 30 и 50 лин/мм на оси;
  - `mtf30_max_field` / `mtf50_max_field` — то же на макс. поле (безполевая → null, op true);
  - пятно полихроматическое (compute_spot_diagram_polychromatic, все λ системы, сетка 30×30).

### status / error / unsupported
- status = ok ⟺ все выбранные операции == true (расширение v1-правила; при --ops base идентично v1: ok ⟺ error = null). error — первый не-true этап в порядке конвейера: `'op: <msg>'`.
- unsupported (операции не хватает настроек в движке): ops[op] = null, error = `'op: unsupported'`; null не считается ok → система fail. Пустышки-заглушки запрещены. Все 4 новые операции поддержаны текущим движком — в корпусе unsupported не ожидается (подтверждается прогоном, см. CORPUS_REPORT_V2.md).
- ops_summary: {op: {'ok': N, 'fail': M}} для всех выбранных операций; в fail попадают false и null.
- f_check и все базовые ключи JSON — семантика v1 без изменений.

## Прогресс волны 2 (2026-10-24)

Пакеты A→финал ТЗ TASK_CORPUS_SCAN_V2, каждый — атомарный коммит, субагенты последовательно:

| Пакет | Что | Коммит |
|---|---|---|
| A | контракт v2 в этом файле (раздел выше) | 7f9073e |
| B | сканер v2: +vignette/chief/spot/mtf_geo, CLI --ops, schema 2 | a4e5a0d |
| C | полный прогон → corpus_v2.json + corpus_v2_diff.md (регресс-сверка v1↔v2) | 6a4de1f |
| D | corpus_stats.py: 7 секций v2, читатель schema 1+2 | 92903d1 |
| E | CORPUS_REPORT_V2.md + CHANGELOG [1.31.0] + README/README_RU | 00d27ee |
| финал | тесты 8 → 16 (smoke v2, schema 2, CLI --ops, читатель v1-JSON) | f0f1ffd |

Итог: полный корпус 612 систем (~12 мин), ok=396 / fail=216 — все отказы на новых ops
(first-fail: spot 206, vignette 7, mtf_geo 3); база 612/612, регрессий декода нет
(базовые ops 3672/3672, метрики 9180/9180, f_check 612×4 — побитово). unsupported = 0,
безполевых систем 0. Полный `py -m pytest -q` зелёный: 1417 passed / 149 skipped.

### Ревью ветки (2026-10-24, код-ревьюер)

- Независимая сверка цифр corpus_v2.json с отчётами (612/396/216, ops-таблицы,
  first-fail, покрытие 13 метрик, fieldless=0) и регресс-заявки v1↔v2
  (base-ops/метрики/f_check — 0 расхождений) — всё сошлось.
- fix: секция «Аномалии v2» stats помечала валидный null полевого ключа
  «нарушением контракта», если поле системы неизвестно (JSON с --ops-подмножеством
  без vignette/chief); теперь такие null не классифицируются (регресс-тест на
  синтетическом subset-JSON; на полном корпусе вывод не изменился — только
  пояснительный текст).
- refactor (правило «логика >1 раза → общий модуль»): V2_KEY_OPS stats выводится
  из V2_METRICS сканера (переименован из _V2_METRICS, публичный); блок таблицы
  «отказы по префиксу» — общий хелпер _error_groups_lines; sec_mtf без повторного
  прохода по системам. Docstring --ops base уточнён: base-ключи как в волне 1,
  но schema_version всегда 2.
- test(corpus): +2 теста (читатель v1 на реальном артефакте corpus.json — 612
  систем, rc 0, без v2-секций/операций; аномалии subset-JSON) + assert schema 2
  при --ops base. 16 → 18 тестов.
