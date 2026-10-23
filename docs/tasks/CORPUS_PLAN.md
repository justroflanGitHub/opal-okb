# CORPUS_PLAN — чекпойнт оркестратора (TASK_CORPUS_SCAN)

Ветка `feature/corpus-scan`, worktree `C:\Users\mikhail\.openclaw\workspace\opal_okb_corpus`.
Данные (read-only, вне git): `C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\*.LBO` —
**13 библиотек, ровно 612 систем** (BINOCUL 22, LENS 116, LENS_SPC 6, MICROLEN 16, OCULAR 76,
REPROD 13, RUSSAR 84, USBINOCL 10, USEYE 8, USLENS 234, USMICRO 6, USREPROD 15, ZOOM 6).

## Подзадачи / статусы

| # | Субагент | Файлы (только эти!) | Статус |
|---|----------|---------------------|--------|
| SA-1 | сканер | `scripts/corpus_scan.py` | 🔲 в работе |
| SA-2 | метрики | `scripts/corpus_stats.py` | 🔲 в работе |
| SA-3 | аномалии | `docs/reports/CORPUS_ANOMALIES.md` (вход: corpus.json) | 🔲 ожидает JSON |
| SA-4 | тесты | `tests/test_corpus_scan.py` | 🔲 в работе |
| SA-5 | доки | `docs/reports/CORPUS_REPORT.md`, `CHANGELOG.md`, `README.md`, `README_RU.md` | 🔲 последняя волна |
| ORCH | я | план, прогон корпуса, интеграция, коммиты, pytest | 🔲 |

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
