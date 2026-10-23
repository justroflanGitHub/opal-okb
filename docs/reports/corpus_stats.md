# Corpus scan — статистика

- Источник: C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\BINOCUL.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\LENS.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\LENS_SPC.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\MICROLEN.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\OCULAR.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\REPROD.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\RUSSAR.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\USBINOCL.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\USEYE.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\USLENS.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\USMICRO.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\USREPROD.LBO, C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\ZOOM.LBO
- Сгенерировано (generated): 2026-10-24T00:20:46+03:00
- Всего систем (total): 612

## Обзор

- Всего систем: 612
- ok: 612 (100.0%)
- fail: 0 (0.0%)

| Операция | ok | fail | % успеха |
|---|---:|---:|---:|
| load | 612 | 0 | 100.0 |
| parse | 612 | 0 | 100.0 |
| paraxial | 612 | 0 | 100.0 |
| seidel | 612 | 0 | 100.0 |
| taboc1 | 612 | 0 | 100.0 |
| pupils | 612 | 0 | 100.0 |

## Распределение f'

По ok-системам с конечным efl≠0: 581 из 612; гистограмма |efl| по лог-диапазонам (мм).

| Диапазон | Кол-во | Гистограмма |
|---|---:|---|
| <3 мм | 146 | ######################################## |
| 3–10 мм | 20 | ##### |
| 10–30 мм | 129 | ################################### |
| 30–100 мм | 147 | ######################################## |
| 100–300 мм | 88 | ######################## |
| 300–1000 мм | 21 | ###### |
| >1000 мм | 30 | ######## |

Мин |efl| = 0.0 мм; медиана = 29.4 мм; макс = 38637754.7 мм.

## Число поверхностей

Систем с известным n_surfaces: 612 из 612.

| n_surfaces | Кол-во | Гистограмма |
|---|---:|---|
| <2 | 1 | # |
| 2–4 | 23 | #### |
| 5–8 | 195 | ################################ |
| 9–12 | 245 | ######################################## |
| 13–20 | 131 | ##################### |
| >20 | 17 | ### |

## Стёкла

Всего уникальных стёкол: 380 (частота — число систем, где стекло встречается).

| # | Стекло | Систем |
|---:|---|---:|
| 1 | ТК16 | 144 |
| 2 | К8 | 123 |
| 3 | Ф1 | 93 |
| 4 | ТФ1 | 88 |
| 5 | ТФ4 | 67 |
| 6 | ТК14 | 46 |
| 7 | БК10 | 35 |
| 8 | ТК21 | 34 |
| 9 | 0 | 33 |
| 10 | ЛФ10 | 29 |
| 11 | СТК9 | 29 |
| 12 | ТК20 | 28 |
| 13 | SK16 | 27 |
| 14 | J   LAK9 | 26 |
| 15 | ТФ2 | 24 |

## Сверка f' (f_check)

f_check заполнен (есть f= / f'= в имени): 565; f_check = null: 47.

| Категория | Систем |
|---|---:|
| ok | 485 |
| hydro | 22 |
| truncated | 1 |
| diverge | 57 |
| f_check = null | 47 |
| **Итого** | **612** |

Внутри ok (485): err ≤ 1% — 393; 1–5% — 92.

Топ-10 наибольших err_pct:

| lib | name | name_f | calc_f | err_pct | category |
|---|---|---:|---:|---:|---|
| USLENS | SPEED F'=1   1:1.1 2W=24  6L USP2158202 | 1.0 | 104.3 | 10326.01 | diverge |
| LENS | Юпитер-24  f'=1    2w=40  1:1.7  5 линз | 1.0 | 11.5 | 1053.09 | truncated |
| USLENS | GAUSS F'=100 1:2    2W=40 6L    LEE | 100.0 | 558.5 | 458.51 | diverge |
| USLENS | IR    F'=100 1:1    2W=3  2L DOUBLET | 100.0 | 380.7 | 280.74 | diverge |
| USLENS | MONO  F'=112 1:3.3  2W=34 8L USP3572904 | 112.0 | -173.6 | 254.98 | diverge |
| USLENS | IR    F'=100 1:1    2W=3  1L DOUBLET | 100.0 | 344.8 | 244.84 | diverge |
| USLENS | IR    F'=100 1:1    2W=3  1L | 100.0 | 318.3 | 218.30 | diverge |
| USLENS | LAS   F'=300 1:100  2W=46 1L USP4695132 | 300.0 | -259.4 | 186.46 | diverge |
| USLENS | LAS   F'=100 1:50   2W=106 2 USP4707085 | 100.0 | -68.9 | 168.91 | diverge |
| USLENS | LAS   F'=25  1:50   2W=58 3L USP4401362 | 25.0 | -8.6 | 134.42 | diverge |

Примечание: `sign_flip` — расхождение только знака при совпадении модуля (в пределах 5%) — норма каталога для зеркально-линзовых систем: находка, а не баг (docs/LBO_FORMAT.md, ТЗ TASK_CORPUS_SCAN).

## Отказы

fail-систем: 0.

_Отказов нет._
