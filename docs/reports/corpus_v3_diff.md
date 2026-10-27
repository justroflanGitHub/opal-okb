# Corpus v3 — дифф-свод v2 vs v3 (612 систем)

- **Дата:** 2026-10-27, ветка `feature/corpus-v3` (TASK_CORPUS_V3, пакет D).
- **Вход:** `corpus_v2.json` (волна 2) против `corpus_v3.json` (волна 3 — scanner-side: skip
  unscannable efl=0/L=0, полудиаметры ×1.4 в spot/mtf_geo, бэкстоп ZeroDivision vignette).
- **Прогон v3:** `py scripts/corpus_scan.py --lib …\opal_okb\Lib --out docs/reports/corpus_v3.json` —
  код возврата 0, **612 систем**, ~805 с (~13.5 мин; v2 был ~709 с), 13 путей .LBO — идентичны v2,
  наборы `(lib, index)` совпадают 612/612.
- **Сверка:** одноразовый скрипт (в репо не входит), сопоставление по паре `(lib, index)`;
  float-сравнение точное (конвейер детерминирован); NaN на обеих сторонах считался равным.
- Классы отказов — join с реестром `corpus_v3_failures.json` (7 классов, 216 отказов v2 +
  15 ok-flips) по `(lib, index)`.

## Итог v3

- **total 612, ok 407, fail 205** (v2: 396/216) — **+11 ok**; база сравнения не изменилась.
- **unsupported (ops[op] = null): 0** — все 10 операций поддержаны движком на всём корпусе.
- **Безполевых систем: 0** — min `vignette_max_field` = 0.267 (как в v2; n=595 не-skip систем).

## Регресс-проверка (v2 → v3): регрессий НЕТ

| Проверка | Объём | Результат |
|---|---|---|
| 6 базовых ops (`load, parse, paraxial, seidel, taboc1, pupils`) — bool побитово | 612 × 6 = 3672 | **все совпали** |
| 15 базовых ключей `metrics` (efl/bfd/f#/L/зрачки/Seidel×5/taboc1×3) | 612 × 15 = 9180 | **все совпали точно** |
| `f_check` (`name_f, calc_f, err_pct, category`) | 612 × 4 = 2448 | **все совпали** |
| vignette-метрики (3 ключа) на 595 не-skip системах | 595 × 3 = 1785 | **все совпали точно** |
| chief-метрики (4 ключа) на 595 не-skip системах | 595 × 4 = 2380 | **все совпали точно** |

Skip-правила не задели чужих операций: база (3672 bool + 9180 метрик + f_check) побитова у **всех**
612, включая 216 бывших fail и 15 ok-flips; ×1.4 действует только вокруг spot/mtf_geo, поэтому
vignette/chief-числа не сдвинулись ни на бит.

Единственные изменения вне spot/mtf_geo — **сами skip-операции** у 17 unscannable_l0-систем
(layout сломан; SKIP_OPS_BY_CLASS = vignette, chief, spot, mtf_geo): в v3 их vignette/chief =
false, метрики null. Из них в v2 значения были: vignette у 10, chief у 14 (осознанная потеря
покрытия на сломанном layout); у 7 (MICROLEN[3..9]) vignette падал ZeroDivision и в v2 — null
остался null (бэкстоп больше не нужен: не-L0 систем с ZeroDivision в v3 — 0).

Изменения ops bool по всем 10 (v2 → v3): `spot` False→True 26 / True→False 19, `mtf_geo`
False→True 26 / True→False 18, `vignette` True→False 10, `chief` True→False 14. True→False у
spot/mtf — это 15 ok-flips плюс 4/3 fail-системы v2, у которых spot/mtf_geo проходил при отказе
vignette/chief/mtf_geo (MICROLEN[4,5,8], USLENS[56]) и теперь честно скипается как unscannable.

## Покрытие по 10 ops: v2 vs v3

| op | v2 ok | v2 % | v3 ok | v3 % | Δ ok |
|---|---:|---:|---:|---:|---:|
| load | 612 | 100.0% | 612 | 100.0% | 0 |
| parse | 612 | 100.0% | 612 | 100.0% | 0 |
| paraxial | 612 | 100.0% | 612 | 100.0% | 0 |
| seidel | 612 | 100.0% | 612 | 100.0% | 0 |
| taboc1 | 612 | 100.0% | 612 | 100.0% | 0 |
| pupils | 612 | 100.0% | 612 | 100.0% | 0 |
| vignette | 605 | 98.9% | 595 | 97.2% | −10 |
| chief | 609 | 99.5% | 595 | 97.2% | −14 |
| spot | 402 | 65.7% | 409 | 66.8% | +7 |
| mtf_geo | 399 | 65.2% | 407 | 66.5% | +8 |

Снижение vignette/chief на 10/14 — те же l0-skip-системы (см. выше); рост spot/mtf_geo — эффект
×1.4 минус уход 15 ok-flips и 4/3 скипнутых в unscannable.

## Смены статуса: 41 система

- **fail → ok: 26** — все 26 класса `field_edge_inflate`, все с v2-ошибкой
  `spot: max field RMS not finite`. Полудиаметров ×1.4 хватило: полевой RMS стал конечен.
  Это весь класс (26/26) — других переходов fail→ok нет.
- **ok → fail: 15** — ровно 15 ok-flips из реестра (`unscannable_ok_flips`): 7 `unscannable_efl0` +
  8 `unscannable_l0`; ни одной внезапной ok→fail вне реестра.
- fail → fail: 190; ok → ok: 381.

Куда ушли 216 отказов v2 (join с реестром):

| класс v2 | систем | v3 исход |
|---|---:|---|
| field_edge_inflate | 26 | **ok** (26) |
| unscannable_efl0 | 24 | fail: `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` (24) |
| unscannable_l0 | 9 | fail: `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` (9) |
| field_fully_vignetted | 134 | fail: `spot: max field RMS not finite` (134) |
| chief_degenerate_axis | 12 | fail: `spot: axis RMS not finite` (12) |
| axis_beam_blocked | 9 | fail: `spot: axis RMS not finite` (9) |
| spot_few_spots | 2 | fail: `mtf_geo: no (max field\|axial) MTF (empty spot?)` (2) |

Итого v3 fail 205 по подписям error: `spot: max field RMS not finite` 134; unscannable efl0 31;
`spot: axis RMS not finite` 21; unscannable l0 17; mtf_geo 2. First-fail: spot 186, vignette 17,
mtf_geo 2. Нюанс: в v2 было 41 «axis RMS not finite», в v3 — 21: ×1.4 починил ось 20 системам,
но их макс. поле осталось срезано полностью (класс `field_fully_vignetted`) — подпись сменилась
на `max field RMS not finite`, статус не изменился.

## Эффект ×1.4 полудиаметров в spot/mtf_geo

- Из 381 системы ok→ok значения spot/mtf изменились у **253**, остались бит-в-бит у **128**
  (базовая сетка без обрезки лучей — ×1.4 ничего не меняет). Всего систем с изменёнными
  spot/mtf-значениями (любые статусы): 359.
- По ключам (ok→ok): `spot_rms_max_field_um` 252, `mtf30_max_field` 215, `mtf50_max_field` 214 —
  изменения концентрируются на макс. поле; ось реже: `spot_rms_axis_um` 31 (RUSSAR 13, LENS 8,
  USLENS 6, OCULAR 4), `mtf30_axis` 27, `mtf50_axis` 25.
- Примеры (ok в обеих волнах):

| lib[index] | имя | ключ | v2 → v3 |
|---|---|---|---|
| OCULAR[25] | Окуляр f'=38 2w=70 d=5 4л. | spot_rms_max_field_um | 148.586 → 146.467 |
| USLENS[205] | SPEED F'=1 1:1.9 2w=36 3L USP2503751 | spot_rms_max_field_um | 7.1678 → 8.4152 |
| LENS[76] | Триплет-5 f'=100 1:2.8 2w=24 3линзы | spot_rms_max_field_um | 102.653 → 111.368 |
| LENS[85] | Мир-10 f'=28 2w=75 1:3.5 8 линз | spot_rms_max_field_um | 36.522 → 45.559 |
| LENS[103] | Восход-1 f'=52 1:1.4 2w=45 7линз | spot_rms_axis_um / …_max_field_um | 26.265 → 27.676 / 48.964 → 271.751 |

- LENS[0..4] (Индустары, все ok в обеих волнах): у кромки поля теперь трассируются лучи, ранее
  срезанные заниженными полудиаметрами (известный факт пакета C: LENS[0] — 1428 → 1944 лучей).
  LENS[0]: `spot_rms_max_field_um` 65.286 → 149.905, `mtf30_max_field` 0.00951 → 0.00079,
  `mtf50_max_field` 0.00135 → 0.01804; LENS[3]: 142.076 → 449.039. Значения честные — при
  раздутых апертурах к полю добавились ранее отсечённые лучи (у части систем контраст на поле
  вырос, у части упал — сетка пятна изменилась, физика трассировки та же).

## 15 ok-flips: v2 ok → v3 fail (unscannable)

Поддельный ok (мусорные spot-значения прямых лучей при n≡1 / L=0) заменён честным skip.

| lib[index] | имя | класс | v3 error |
|---|---|---|---|
| LENS_SPC[5] | Об.з.-л.Цуканова f'=-351 1:1.75 2w=5 | efl0 | `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` |
| USLENS[55] | LAS F'=4 1:2.3 2W=30 3L USP4753524 | efl0 | `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` |
| USLENS[67] | LENS F'=38 1:2.8 2W=60 5L USP4456345 | efl0 | `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` |
| USLENS[68] | LENS F'=25 1:3 2W=61 5L USP4457596 | efl0 | `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` |
| USLENS[69] | LENS F'=25 1:2.8 2W=62 4L USP4281908 | efl0 | `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` |
| USLENS[97] | TRIPL F'=100 1:4 2W=40 5L HELIAR | efl0 | `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` |
| USREPROD[1] | 1/2 REP 1:10 2W=17 F'=192 USP4753523 | efl0 | `spot: unscannable: efl=0 (стёкла не декодированы, n≡1)` |
| LENS[25] | Гелиос-32 f'=15 2w=48 1:2 6 линз | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |
| LENS[78] | Триплет f'=45 1:3.9 2w=50 3линзы | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |
| LENS[113] | Подводный(ГОИ) f=-23 2w=90 1:2.5 11л. | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |
| RUSSAR[28] | Руссар-37 f'=22.6 1:5.6 2w=101 8линз | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |
| RUSSAR[46] | Киноруссар-4а f'=50 1:2.2 2w=33 11л | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |
| RUSSAR[48] | Киноруссар-6 f'=12 1:3.5 2w=130 9л | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |
| RUSSAR[55] | Киноруссар-35 f'=29 1:2.9 2w=90 10л | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |
| RUSSAR[73] | Гидроруссар-10a f=-15.4 1:2 2w=60 7л | l0 | `vignette: unscannable: L=0 (layout сломан, толщины обнулены)` |

У efl0-flips (стёкла не декодированы) геометрия декодирована — vignette/chief остались true,
их числа бит-в-бит v2; у l0-flips (layout сломан) все полевые ops false.

## Контракт волны 3

- Error-строки unscannable — точно эталон: `spot: unscannable: efl=0 (стёкла не декодированы,
  n≡1)` — 31 система (24 fail + 7 flips); `vignette: unscannable: L=0 (layout сломан, толщины
  обнулены)` — 17 (9 fail + 8 flips); других error с токеном `unscannable` — 0.
- unsupported (ops[op] = null): **0**; безполевых систем: **0** (min поле корпуса 0.267).
- STATS (`corpus_stats.py --json corpus_v3.json`) согласована с JSON: total/ok/fail 612/407/205,
  ops-таблица побитово, группы `spot [unscannable_efl0]` 31 и `vignette [unscannable_l0] 17`
  размечены; нарушение контракта «null/не-числовые метрики при true-опе»: 0.

## По библиотекам

| lib | n | ok v2 | ok v3 | fail v2 | fail v3 |
|---|---:|---:|---:|---:|---:|
| BINOCUL | 22 | 12 | 16 | 10 | 6 |
| LENS | 116 | 93 | 96 | 23 | 20 |
| LENS_SPC | 6 | 6 | 5 | 0 | 1 |
| MICROLEN | 16 | 0 | 0 | 16 | 16 |
| OCULAR | 76 | 32 | 39 | 44 | 37 |
| REPROD | 13 | 2 | 2 | 11 | 11 |
| RUSSAR | 84 | 33 | 33 | 51 | 51 |
| USBINOCL | 10 | 1 | 1 | 9 | 9 |
| USEYE | 8 | 8 | 8 | 0 | 0 |
| USLENS | 234 | 202 | 199 | 32 | 35 |
| USMICRO | 6 | 1 | 1 | 5 | 5 |
| USREPROD | 15 | 4 | 3 | 11 | 12 |
| ZOOM | 6 | 2 | 4 | 4 | 2 |

Рост ок — BINOCUL +4, OCULAR +7, LENS +3, ZOOM +2 (эффект ×1.4); снижение — LENS_SPC −1,
USLENS −3, USREPROD −1 (ok-flips). RUSSAR/MICROLEN/USBINOCL/REPROD не изменились: их отказы —
движковые классы (полностью срезанное поле, вырожденный осевой chief, конечный предмет) и
unscannable-скипы, сканеру не чинятся.

---

_Сводка по прогону TASK_CORPUS_V3 (пакет D); числа — docs/reports/corpus_v3.json (schema 2,
generated 2026-10-27T20:08:57+03:00) против docs/reports/corpus_v2.json, классы —
docs/reports/corpus_v3_failures.json, сканер scripts/corpus_scan.py @ 89bd935._
