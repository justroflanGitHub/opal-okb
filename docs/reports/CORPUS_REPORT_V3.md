# Корпус волна 3 — классификация 216 отказов и честные unscannable

- **Дата:** 2026-10-27, ветка `feature/corpus-v3` (TASK_CORPUS_V3, пакет E).
- **Источник:** тот же корпус волн 1–2 — `extracted/opal_okb/Lib/*.LBO`, 13 библиотек, **612 систем**
  (данные вне git, read-only).
- **Воспроизведение:**
  `py scripts/corpus_scan.py --lib C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib --out docs/reports/corpus_v3.json`
  → `py scripts/corpus_stats.py --json docs/reports/corpus_v3.json --out "%TEMP%\stats_v3.md"`
- **Артефакты:** `corpus_v3.json` (schema 2, все 10 ops), `corpus_v3_diff.md` (свод v2→v3),
  `corpus_v3_failures.json` / `corpus_v3_failures.md` (реестр 216 отказов с классами),
  `CORPUS_REPORT_V2.md` (волна 2), тесты `tests/test_corpus_scan.py`.

Новое в волне 3: все 216 отказов spot/mtf_geo волны 2 получили **честный вердикт-класс
первопричины** (7 классов, `FAIL_CLASSES` в `scripts/corpus_scan.py` — единый источник для
сканера, stats и реестра); всё, что чинится на стороне сканера, починено — skip-правила
unscannable (efl=0/L=0), запас полудиаметров ×1.4 в spot/mtf_geo, ZeroDivision-бэкстоп
vignette. Движковые причины задокументированы и **не** обходятся в сканере (раздел
«Движковые находки»). ТЗ — `docs/tasks/TASK_CORPUS_V3.md`.

## Итоги прогона

- **total 612, ok 407 (66.5%), fail 205 (33.5%)** (v2: 396/216), JSON schema 2; время ~805 с
  (~13.5 мин; v2 был ~709 с). **unsupported = 0**, безполевых систем = 0 (min поле 0.267°).
- Базовый конвейер по-прежнему **612/612**; все изменения сосредоточены в полевых ops.

| Операция | ok v2 | ok v3 | fail v3 | % успеха v3 | Δ ok |
|---|---:|---:|---:|---:|---:|
| load | 612 | 612 | 0 | 100.0 | 0 |
| parse | 612 | 612 | 0 | 100.0 | 0 |
| paraxial | 612 | 612 | 0 | 100.0 | 0 |
| seidel | 612 | 612 | 0 | 100.0 | 0 |
| taboc1 | 612 | 612 | 0 | 100.0 | 0 |
| pupils | 612 | 612 | 0 | 100.0 | 0 |
| vignette | 605 | 595 | 17 | 97.2 | −10 |
| chief | 609 | 595 | 17 | 97.2 | −14 |
| spot | 402 | 409 | 203 | 66.8 | +7 |
| mtf_geo | 399 | 407 | 205 | 66.5 | +8 |

Снижение vignette/chief на 10/14 — l0-skip-системы (layout сломан, полевые ops скипаются как
unscannable; в v2 у 10/14 из них значения были) — осознанная потеря покрытия на сломанном
layout. Рост spot/mtf_geo — эффект ×1.4 минус уход 15 ok-flips и 4/3 fail-систем v2 в skip.

## Классификация 216 отказов v2

Методика: first-fail op/error из `corpus_v2.json` + триггеры из метрик и диагностики (efl, L,
тип предмета, виньетирование, причины главного луча, RMS оси/поля при полудиаметрах ×1.0/×1.4);
класс — детерминированные правила по приоритету (`efl0 → l0 → chief_degenerate →
field_edge_inflate → axis_beam_blocked → field_fully_vignetted → spot_few_spots`). Полная
методика и таблицы — `corpus_v3_failures.md`.

### Матрица «семейство × класс» (11 библиотек с отказами)

| Библиотека | unscannable_efl0 | unscannable_l0 | chief_degenerate_axis | field_fully_vignetted | field_edge_inflate | axis_beam_blocked | spot_few_spots | Сумма |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RUSSAR | 0 | 2 | 7 | 36 | 5 | 1 | 0 | 51 |
| OCULAR | 0 | 0 | 0 | 37 | 7 | 0 | 0 | 44 |
| USLENS | 12 | 0 | 3 | 13 | 2 | 0 | 2 | 32 |
| LENS | 0 | 0 | 0 | 17 | 6 | 0 | 0 | 23 |
| MICROLEN | 0 | 7 | 1 | 5 | 0 | 3 | 0 | 16 |
| REPROD | 0 | 0 | 0 | 9 | 0 | 2 | 0 | 11 |
| USREPROD | 2 | 0 | 0 | 6 | 0 | 3 | 0 | 11 |
| BINOCUL | 0 | 0 | 1 | 5 | 4 | 0 | 0 | 10 |
| USBINOCL | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| USMICRO | 1 | 0 | 0 | 4 | 0 | 0 | 0 | 5 |
| ZOOM | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 4 |
| **Итого** | **24** | **9** | **12** | **134** | **26** | **9** | **2** | **216** |

### Описание классов

**1. `unscannable_efl0` — 24 (+7 ok-систем v2 → flips).** efl ровно 0.0 при конечном L: блок
стёкол US-библиотек не декодирован (`glass=''` → n≡1, рефракции нет), лучи идут прямиком.
Список: `USBINOCL[1..9]` (9), `USLENS[10,30,34,35,39,40,48,49,50,56,62,73]` (12), `USREPROD[3,14]`,
`USMICRO[0]`. Spot-значения таких систем — мусор прямых лучей: осевой RMS **3501.6096850617296
мкм** совпадает до последнего знака у 6 систем v2 (5 ok — `USLENS[67]`, `USLENS[97]`,
`USREPROD[1]`, `LENS[113]`, `RUSSAR[73]`; 1 fail — `USBINOCL[1]`): «поддельный ok». Пакет C:
skip spot/mtf_geo — op false + error `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)`;
vignette/chief остаются (геометрия декодирована, их числа бит-в-бит v2).

**2. `unscannable_l0` — 9 (+8 ok-систем v2 → flips).** L ровно 0.0: layout сломан (толщины
обнулены), efl ~1e-270. Список: `MICROLEN[3,4,5,6,7,8,9]` (7), `RUSSAR[71,72]`. У `MICROLEN[3..9]`
вдобавок vignette падал `ZeroDivisionError` (см. движковую находку 3). Всего L==0 в корпусе у 18
систем (кластер A1 волны 1 — 17 + `LENS_SPC[5]` Цуканова; её класс — по efl0). Пакет C: skip всех
полевых ops — `vignette: unscannable: L=0 (layout сломан, толщины обнулены)`.

**3. `chief_degenerate_axis` — 12.** `BINOCUL[3]`, `MICROLEN[13]`, `RUSSAR[1,54,61,63,66,70,83]`,
`USLENS[130,132,146]`. Осевой главный луч (field_y=0) MISS на поверхности с нулевым зазором
(предыдущая thickness==0 → старт сегмента точно на вершине сферы); механизм — движковая находка 1.
Запас полудиаметров ×1.4 не помогает (diag: осевой RMS при ×1.4 = inf у всех 12).

**4. `field_fully_vignetted` — 134.** chief на макс. поле падает (EDGE 107 / MISS 16 / TIR 9 /
STOP 2) даже при ×1.4; у всех 134 виньетирование на макс. поле = 100% хотя бы с одной стороны.
Край поля каталога за пределами полезного поля зрения: пучок срезан полностью, пятно не
существует — честный отказ. Пример: `RUSSAR[0]` Руссар-1 2w=110 (поле 55°): при ×1.4 — EDGE 74 +
STOP 14 из 88 лучей. Полные списки — `corpus_v3_failures.md`.

**5. `field_edge_inflate` — 26.** Полевой RMS = inf при штатных полудиаметрах, но конечен при
×1.4: полудиаметры LBO часто чуть занижены (у всех 26 chief поля — EDGE). Прецедент проекта —
`CODDINGTON_SD_INFLATE=1.4` в `analysis/aberrations.py`. Примеры: `OCULAR[0]` f'=5 2w=42 — на
поле 21° 26/88 лучей EDGE при ×1.0 → 0 при ×1.4; `BINOCUL[0]` Галилея Г=2.5 — 96/124 EDGE →
полевой RMS 1.447 мм при ×1.4. Единственный класс, полностью починенный сканером (26/26 → ok).

**6. `axis_beam_blocked` — 9.** `MICROLEN[0,1,2]`, `REPROD[2,11]`, `RUSSAR[65]`, `USREPROD[4,6,7]`.
Все FINITE-предмет (микрообъективы v=−10, репродукционные v=−1, гидроруссар в воде): chief оси OK,
но ВСЕ зрачковые лучи оси отсекаются даже при ×3.0 (`MICROLEN[0]`/`RUSSAR[65]` — EDGE 88/88 при
×1.4/2.0/3.0; `USREPROD[4]` TELECENTR — MISS 88/88; `REPROD[2]` — MISS 48 + TIR 40, декод
подозрителен — аномалия №19 волны 1, err 61%). Движковая находка 2.

**7. `spot_few_spots` — 2.** `USLENS[36,47]`: осевой/полевой RMS конечен, но полихроматическое
пятно < 10 точек (`USLENS[47]`: 4 точки на оси → «no axial MTF»; `USLENS[36]`: ось 12 точек с
mtf=0.0 — частота за Найквистом, поле 8 < 10 → «no max field MTF»). Большинство лучей пучка
срезано/ПВО — честный отказ; mtf_geo невозможен.

## Что исправлено в сканере (пакет C)

1. **Skip-правила unscannable** (`detect_unscannable` + `SKIP_OPS_BY_CLASS` в
   `scripts/corpus_scan.py`): efl == 0.0 → skip `spot, mtf_geo`; L == 0.0 → skip
   `vignette, chief, spot, mtf_geo`. Честный контракт: **op = false + error
   `op: unscannable: efl=0 (стёкла не декодированы, n≡1)` / `op: unscannable: L=0 (layout
   сломан, толщины обнулены)`** вместо трассировки бессмысленной геометрии с фейковыми
   значениями. Метрики пропущенных ops — null. Токен `unscannable: …` — стабильный префикс
   для маркировки групп в `corpus_stats.py`.
2. **Запас полудиаметров ×1.4 в spot/mtf_geo** (`_inflated_sds`, константа
   `CODDINGTON_SD_INFLATE=1.4` — тот же прецедент, что в полевых аберрациях движка):
   заниженные полудиаметры LBO срезали лучи поля кромкой. vignette/chief НЕ раздуты —
   их числа бит-в-бит v2.
3. **ZeroDivision-бэкстоп vignette** (`scripts/corpus_scan.py:551–556`): не-L0 система с
   вырожденным отступом предмета (d=0 в `_pupil_field_ray` при FINITE-предмете) даёт
   человекочитаемый why вместо сырого падения. В прогоне v3 не сработал ни разу
   (не-L0 систем с ZeroDivision — 0: все L=0 скипаются раньше).

### 15 ok-flips: v2 ok → v3 fail (unscannable)

| lib[index] | имя | класс | v3 error |
|---|---|---|---|
| LENS_SPC[5] | Об.з.-л.Цуканова f'=-351 1:1.75 2w=5 | efl0 | `spot: unscannable: efl=0 …` |
| USLENS[55] | LAS F'=4 1:2.3 2W=30 3L USP4753524 | efl0 | `spot: unscannable: efl=0 …` |
| USLENS[67] | LENS F'=38 1:2.8 2W=60 5L USP4456345 | efl0 | `spot: unscannable: efl=0 …` |
| USLENS[68] | LENS F'=25 1:3 2W=61 5L USP4457596 | efl0 | `spot: unscannable: efl=0 …` |
| USLENS[69] | LENS F'=25 1:2.8 2W=62 4L USP4281908 | efl0 | `spot: unscannable: efl=0 …` |
| USLENS[97] | TRIPL F'=100 1:4 2W=40 5L HELIAR | efl0 | `spot: unscannable: efl=0 …` |
| USREPROD[1] | 1/2 REP 1:10 2W=17 F'=192 USP4753523 | efl0 | `spot: unscannable: efl=0 …` |
| LENS[25] | Гелиос-32 f'=15 2w=48 1:2 6 линз | l0 | `vignette: unscannable: L=0 …` |
| LENS[78] | Триплет f'=45 1:3.9 2w=50 3линзы | l0 | `vignette: unscannable: L=0 …` |
| LENS[113] | Подводный(ГОИ) f=-23 2w=90 1:2.5 11л. | l0 | `vignette: unscannable: L=0 …` |
| RUSSAR[28] | Руссар-37 f'=22.6 1:5.6 2w=101 8линз | l0 | `vignette: unscannable: L=0 …` |
| RUSSAR[46] | Киноруссар-4а f'=50 1:2.2 2w=33 11л | l0 | `vignette: unscannable: L=0 …` |
| RUSSAR[48] | Киноруссар-6 f'=12 1:3.5 2w=130 9л | l0 | `vignette: unscannable: L=0 …` |
| RUSSAR[55] | Киноруссар-35 f'=29 1:2.9 2w=90 10л | l0 | `vignette: unscannable: L=0 …` |
| RUSSAR[73] | Гидроруссар-10a f=-15.4 1:2 2w=60 7л | l0 | `vignette: unscannable: L=0 …` |

У efl0-flips (стёкла не декодированы) геометрия декодирована — vignette/chief остались true,
их числа бит-в-бит v2; у l0-flips (layout сломан) все полевые ops false. Ни одной внезапной
ok→fail вне реестра.

## Переходы статусов v2→v3: 41 система

- **fail → ok: 26** — весь класс `field_edge_inflate` (26/26), все с v2-ошибкой
  `spot: max field RMS not finite`; полудиаметров ×1.4 хватило, полевой RMS стал конечен.
- **ok → fail: 15** — ровно реестровые ok-flips (7 `unscannable_efl0` + 8 `unscannable_l0`).
- fail → fail: 190; ok → ok: 381. **Итог: ok 396 → 407 (+11).**

Куда ушли 216 отказов v2 (join с реестром):

| класс v2 | систем | v3 исход |
|---|---:|---|
| field_edge_inflate | 26 | **ok** (26) |
| unscannable_efl0 | 24 | fail: `spot: unscannable: efl=0 …` (24) |
| unscannable_l0 | 9 | fail: `vignette: unscannable: L=0 …` (9) |
| field_fully_vignetted | 134 | fail: `spot: max field RMS not finite` (134) |
| chief_degenerate_axis | 12 | fail: `spot: axis RMS not finite` (12) |
| axis_beam_blocked | 9 | fail: `spot: axis RMS not finite` (9) |
| spot_few_spots | 2 | fail: `mtf_geo: no (max field\|axial) MTF` (2) |

Остаток 205 fail по подписям error: `spot: max field RMS not finite` 134; unscannable efl0 31
(24 + 7 flips); `spot: axis RMS not finite` 21; unscannable l0 17 (9 + 8 flips); mtf_geo
«empty spot» 2. First-fail: spot 186, vignette 17, mtf_geo 2. Изменения ops bool (v2 → v3):
spot False→True 26 / True→False 19, mtf_geo 26/18, vignette True→False 10, chief True→False 14
(True→False у spot/mtf — 15 flips плюс 4/3 fail-системы v2 — `MICROLEN[4,5,8]`, `USLENS[56]` —
у которых spot/mtf_geo проходил при отказе другой op и теперь честно скипается).

## Движковые находки (в сканере не чинятся)

Сканер не обходит эти причины обходами, меняющими физику расчёта; фикс — только в движке,
в будущих волнах.

1. **`intersect_sphere` возвращает дальний корень для луча из вершины сферы** — класс
   `chief_degenerate_axis`, 12 систем. Проверка на движке:
   `intersect_sphere(Ray(0,0,5.0,0,0,1), 43.0, 5.0)` → `(0.0, 0.0, 91.0, 86.0)` — ближний
   корень t=0 (сама вершина) отбрасывается условием `tc <= EPSILON`
   (`analysis/ray_tracing.py:258–259`), побеждает дальний t=86. Дальше физический кап
   GFIX P6 (`analysis/ray_tracing.py:565–579`) бракует «спину» математической сферы
   (|hz−z| = 86 > sag) → MISS → осевой chief не прошёл → пятно пусто → RMS = inf.
   Пример `BINOCUL[3]`: старт (0,0,5.0), R=43, z_surf=5 → точка (0,0,91.86). ×1.4 не помогает
   (осевой RMS при ×1.4 = inf у всех 12).
2. **`_pupil_field_ray` делит на нулевой отрезок предмета** (`analysis/aberrations.py:1655–1658`):
   для FINITE-предмета `obj_z = −surfaces[0].thickness`, `d = abs(obj_z)`, направления
   `k = x_start / d` — при нулевой первой толщине ZeroDivision. В 9 системах класса
   `axis_beam_blocked` (все FINITE: микрообъективы v=−10, репродукционные v=−1, гидроруссар
   в воде) весь осевой пучок отсекается даже при ×3.0 полудиаметров (детали в классе 6).
3. **ZeroDivision-механизм vignette на `MICROLEN[3..9]`** — то же деление `d = 0`
   (L=0-кластер): 7 отказов vignette в v2. В v3 предупреждено l0-skip (skip раньше расчёта);
   бэкстоп сканера остаётся как защита для не-L0 систем.
4. **Побочный эффект ×1.4 — легитимный пересчёт полевых значений**: у `LENS[0..4]` (Индустары,
   ok в обеих волнах) лучи у кромки поля теперь трассируются — ранее отсекались заниженными
   полудиаметрами (`LENS[0]`: 1428 → 1944 лучей, факт пакета C). `LENS[0]`:
   `spot_rms_max_field_um` 65.286 → 149.905, `mtf30_max_field` 0.0095 → 0.0008; `LENS[3]`:
   142.076 → 449.039. Значения честные — сетка пятна изменилась, физика трассировки та же.

Кандидаты на движковые фиксы будущих волн: выбор корня `intersect_sphere` при старте луча из
вершины (t=0 — валидное пересечение) — снимет класс `chief_degenerate_axis` (12 систем);
построение пучка для FINITE-предмета при нулевом первом отрезке — снимет `axis_beam_blocked`
(9 систем) и ZeroDivision-хвост.

## Регресс-сверка v2→v3: регрессий нет

Методика: `corpus_v2.json` против `corpus_v3.json`, сопоставление по паре `(lib, index)`;
float-сравнение точное (конвейер детерминирован), NaN на обеих сторонах считался равным.
Полная методика — `corpus_v3_diff.md`.

| Проверка | Объём | Результат |
|---|---|---|
| 6 базовых ops (`load, parse, paraxial, seidel, taboc1, pupils`) — bool побитово | 612 × 6 = 3672 | **все совпали** |
| 15 базовых ключей `metrics` (efl/bfd/f#/L/зрачки/Seidel×5/taboc1×3) | 612 × 15 = 9180 | **все совпали точно** |
| `f_check` (`name_f, calc_f, err_pct, category`) | 612 × 4 = 2448 | **все совпали** |
| vignette-метрики (3 ключа) на 595 не-skip системах | 595 × 3 = 1785 | **все совпали точно** |
| chief-метрики (4 ключа) на 595 не-skip системах | 595 × 4 = 2380 | **все совпали точно** |

Skip-правила не задели чужих операций: база побитова у всех 612, включая 216 бывших fail и
15 ok-flips; ×1.4 действует только вокруг spot/mtf_geo.

**Эффект ×1.4 на значения:** из 381 ok→ok систем spot/mtf-значения изменились у **253**,
остались бит-в-бит у 128 (базовая сетка без обрезки — ×1.4 ничего не меняет). Изменения
концентрируются на макс. поле: `spot_rms_max_field_um` 252, `mtf30_max_field` 215,
`mtf50_max_field` 214; ось реже: `spot_rms_axis_um` 31, `mtf30_axis` 27, `mtf50_axis` 25.
Всего систем с изменёнными spot/mtf-значениями (любые статусы): 359. Примеры (ok в обеих):

| lib[index] | имя | ключ | v2 → v3 |
|---|---|---|---|
| OCULAR[25] | Окуляр f'=38 2w=70 d=5 4л. | spot_rms_max_field_um | 148.586 → 146.467 |
| USLENS[205] | SPEED F'=1 1:1.9 2w=36 3L USP2503751 | spot_rms_max_field_um | 7.1678 → 8.4152 |
| LENS[76] | Триплет-5 f'=100 1:2.8 2w=24 3линзы | spot_rms_max_field_um | 102.653 → 111.368 |
| LENS[85] | Мир-10 f'=28 2w=75 1:3.5 8 линз | spot_rms_max_field_um | 36.522 → 45.559 |
| LENS[103] | Восход-1 f'=52 1:1.4 2w=45 7линз | spot_rms_axis_um / …_max_field_um | 26.265 → 27.676 / 48.964 → 271.751 |

**Нюанс подписей ошибок (уточнено пакетом E по JSON):** в v2 было 41 система с
`spot: axis RMS not finite`, в v3 — 21 (12 `chief_degenerate_axis` + 9 `axis_beam_blocked`).
Расхождение 20 — **не** эффект ×1.4: это 18 efl0- и 2 l0-системы, переведённые skip-правилами
в `unscannable`. У всех 134 `field_fully_vignetted` подпись `spot: max field RMS not finite`
идентична в v2 и v3 (0 смен подписи; ось у них конечна уже при штатных полудиаметрах —
diag реестра), статус не менялся. Эффект ×1.4 виден только там, где полевой RMS стал конечен
(26 полей → ok) и в значениях ok-систем (253 системы).

## Выводы о готовности порта

- **Сканер больше не выдаёт фейковых чисел.** Поддельный ok волны 2 (мусор прямых лучей при
  n≡1/L=0: идентичный RMS 3501.6096850617296 мкм у 6 систем) заменён честным unscannable-
  контрактом; каждая из 216 систем v2 имеет вердикт-класс, остаток 205 fail полностью
  разложен по классам:
  **134** `field_fully_vignetted` (край поля каталога за пределами полезного поля — честный
  отказ, чинится только слоем данных каталога) + **12** `chief_degenerate_axis` и **9**
  `axis_beam_blocked` (движковые, см. находки) + **31** unscannable efl0 и **17** unscannable
  l0 (сломанные декоды, ждут US-стёкол/layout-кодов) + **2** `spot_few_spots` = 205.
- **Покрытие:** полные v2-метрики (все 10 ops) у **407/612 (66.5%)**; spot 409 (66.8%),
  mtf_geo 407 (66.5%), vignette/chief 595 (97.2%), база 612/612. Сканерные резервы исчерпаны:
  рост v3 дал ровно тот класс, что чинится на стороне сканера (26 field_edge_inflate).
- **Рекомендации следующих волн** (по убыванию эффекта):
  1. US-блок стёкол (декод `glass=''` → n≡1) — **−31** отказ (24 fail + 7 flips) и возврат
     15 полевых значений из ok-flips;
  2. layout-коды руссаров/микролен (обнуленные толщины) — **−17**;
  3. движковые фиксы `intersect_sphere` (корень из вершины) и `_pupil_field_ray`
     (нулевой отрезок FINITE-предмета) — **−21** (12 + 9);
  4. afocal-режим биноклей BINOCUL/USBINOCL — снимет остаток их отказов и хвост экстремумов
     метрик (астигматизм ~4.9·10⁶ мм, RMS ~311 мм волны 2).
  Хвост после этого — честные `field_fully_vignetted` (134): данные каталога за пределами
  полезного поля.

## Ссылки

- `docs/reports/corpus_v3.json` — прогон v3 (schema 2, все 10 ops, 612 систем,
  generated 2026-10-27T20:08:57+03:00).
- `docs/reports/corpus_v3_diff.md` — дифф-свод v2→v3 (пакет D: покрытие, переходы, регресс,
  эффект ×1.4, ok-flips, по библиотекам).
- `docs/reports/corpus_v3_failures.json` / `corpus_v3_failures.md` — реестр 216 отказов с
  классами (пакеты A–B: методика, триггеры, матрица).
- Статистика v3 (в git не входит, генерируется):
  `py scripts/corpus_stats.py --json docs/reports/corpus_v3.json --out "%TEMP%\stats_v3.md"`.
- `docs/reports/CORPUS_REPORT_V2.md` — отчёт волны 2 (методика ops, распределения метрик);
  `corpus_v2.json` / `corpus_v2_diff.md` — база сравнения.
- `docs/tasks/TASK_CORPUS_V3.md` — ТЗ волны 3; `docs/tasks/CORPUS_PLAN.md` — «Контракт v2».

---

_Отчёт собран в пакете E TASK_CORPUS_V3; числа — docs/reports/corpus_v3.json (schema 2,
generated 2026-10-27T20:08:57+03:00) против docs/reports/corpus_v2.json, классы —
docs/reports/corpus_v3_failures.json, сканер scripts/corpus_scan.py @ 89bd935._
