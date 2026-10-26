# OPAL-OKB — корпус волна 3, пакет A: реестр отказов (216 систем)

- Инструмент: `task_corpus_v3.package_A`; сгенерировано: 2026-10-26T23:41:13+03:00
- Основной источник: `docs/reports/corpus_v2.json` (прогон волны 2, schema 2: 612 систем, 13 библиотек, ok=396, fail=216).
- Диагностика отказов: `corpus_v3_diag.json` (снаружи репозитория; поля efl, L, object_type, field_max, status виньетирования, причины хода главного луча).
- Данные .LBO: `C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib` (read-only), чтение через `fileio.lbo_io.load_lbo` — только для триггера «нулевой зазор».

## Методика

- **first_fail_op / error_msg** — разрез поля `error` из corpus_v2.json по первому двоеточию (`spot: max field RMS not finite` → op `spot`, сообщение `max field RMS not finite`).
- Триггеры — признаки, объясняющие отказ, из metrics corpus_v2.json и diag:
  - `efl` — эффективное фокусное расстояние (мм); `efl_zero` — efl ровно 0.0; `efl_degenerate` — |efl| < 1e-6; `afocal` — |efl| > 1e5 (афокальная система).
  - `L` — расстояние предмет–изображение (мм); `L_zero` — L == 0.0.
  - `has_mirror` — есть зеркальная поверхность; `object_type` — INFINITE/FINITE; `field_max` — максимальное поле (°).
  - `vignette_up_pct` / `vignette_down_pct` — виньетирование вверх/вниз (%); `vignette_fully_clipped` — up ≥ 100 или down ≥ 100; `vignette_status` — статус op vignette из diag (`ok` / `ZeroDivision` / …).
  - `zero_thickness_gaps` — 0-индексация списка поверхностей (0 — первая поверхность; последняя, поверхность изображения, исключена), у которых thickness == 0.0 («вырожденный зазор» между поверхностями).
  - `chief_axis_reason` / `chief_field_reason` — исход трассировки главного луча на оси/поле из diag: `OK` / `EDGE` (ушёл с апертуры — «кромка») / `TIR` (полное внутреннее отражение) / `MISS` (мимо поверхности) / `STOP` (мимо диафрагмы).

Компактные метки триггеров в таблицах: `efl=0`, `efl~0` (вырожденный efl, не ровно 0), `afoc`, `L=0`, `zerogap@i[,j…]`, `mirror`, `vign=100%`, `vign:…`, `предмет` (конечный предмет), `кромка`/`ПВО`/`луч-мимо`/`стоп-луч` (главный луч, поле), `ос-miss` (главный луч, ось), `field=W°`.

## Отказы по библиотекам

| Библиотека | Систем в lib | Отказы | Доля |
|---|---:|---:|---:|
| RUSSAR | 84 | 51 | 61% |
| OCULAR | 76 | 44 | 58% |
| USLENS | 234 | 32 | 14% |
| LENS | 116 | 23 | 20% |
| MICROLEN | 16 | 16 | 100% |
| REPROD | 13 | 11 | 85% |
| USREPROD | 15 | 11 | 73% |
| BINOCUL | 22 | 10 | 45% |
| USBINOCL | 10 | 9 | 90% |
| USMICRO | 6 | 5 | 83% |
| ZOOM | 6 | 4 | 67% |
| **Итого** | **612** | **216** | **35%** |

## First-fail операции

| Операция | Систем |
|---|---:|
| spot | 206 |
| vignette | 7 |
| mtf_geo | 3 |
| **Итого** | **216** |

## Сообщения об ошибках

| Операция | Сообщение | Систем |
|---|---|---:|
| spot | `max field RMS not finite` | 165 |
| spot | `axis RMS not finite` | 41 |
| vignette | `ZeroDivisionError: float division by zero` | 7 |
| mtf_geo | `no max field MTF (empty spot?)` | 2 |
| mtf_geo | `no axial MTF (empty spot?)` | 1 |
| **Итого** | | **216** |

## Триггеры

| Триггер | Систем |
|---|---:|
| efl = 0.0 (`efl=0`) | 24 |
| \|efl\| < 1e-6, всего (`efl=0` + `efl~0`) | 33 |
| \|efl\| > 1e5 — афокальные (`afoc`) | 7 |
| L = 0.0 (`L=0`) | 9 |
| зеркальная поверхность (`mirror`) | 0 |
| виньетирование 100% (`vign=100%`) | 198 |
| системы с нулевым зазором (`zerogap@…`) | 26 (поверхностей: 158) |
| конечный предмет (`предмет`) | 40 |
| главный луч, поле: кромка (`EDGE`) | 153 |
| главный луч, поле: мимо (`MISS`) | 38 |
| главный луч, поле: ПВО (`TIR`) | 10 |
| главный луч, поле: мимо диафрагмы (`STOP`) | 2 |
| главный луч, ось: мимо (`MISS`) | 24 |

### Пересечение триггеров (топ-25 комбинаций из 131)

| Комбинация триггеров | Систем |
|---|---:|
| vign=100%, кромка, field=52° | 11 |
| vign=100%, кромка, field=30° | 10 |
| vign=100%, кромка, field=35° | 9 |
| vign=100%, кромка, field=20° | 6 |
| vign=100%, кромка, field=40° | 6 |
| vign=100%, кромка, field=45° | 6 |
| vign=100%, кромка, field=50° | 5 |
| vign=100%, кромка, field=31° | 4 |
| vign=100%, кромка, field=43° | 4 |
| efl=0, vign=100%, луч-мимо, field=20° | 4 |
| vign=100%, кромка, field=25° | 3 |
| vign=100%, кромка, field=38° | 3 |
| vign=100%, кромка, field=33° | 3 |
| vign=100%, кромка, field=14° | 3 |
| vign=100%, кромка, field=17° | 3 |
| vign=100%, кромка, field=47° | 3 |
| afoc, vign=100%, кромка, field=13° | 2 |
| afoc, vign=100%, кромка, field=3° | 2 |
| vign=100%, предмет, луч-мимо, field=90° | 2 |
| vign=100%, предмет, луч-мимо, field=50° | 2 |
| vign=100%, кромка, field=18° | 2 |
| vign=100%, предмет, ПВО, field=22° | 2 |
| vign=100%, предмет, ПВО, field=53° | 2 |
| vign=100%, предмет, ПВО, field=40° | 2 |
| vign=100%, предмет, кромка, field=22° | 2 |

## Полная таблица отказов (216)

| № | Система | Имя | Op | Сообщение | Триггеры |
|---|---|---|---|---|---|
| 1 | BINOCUL[0] | Бинокль Галилея Г=2.5 2w=9.30 d'=5 3л. | spot | max field RMS not finite | vign=100%, кромка, field=5° |
| 2 | BINOCUL[1] | Бинокль Галилея Г=2.6 2w=25 d'=5 5л. | spot | max field RMS not finite | afoc, vign=100%, кромка, field=13° |
| 3 | BINOCUL[2] | Бинокль Галилея Г=2.5 2w=26 d'=4 4л. | spot | max field RMS not finite | afoc, vign=100%, кромка, field=13° |
| 4 | BINOCUL[3] | Бинокль Галилея Г=4 2w=8 d'=5 4л. | spot | axis RMS not finite | zerogap@1, vign=100%, кромка, ос-miss, field=4° |
| 5 | BINOCUL[5] | Бинокль Г=8 2w=13 d'=5 10л. | spot | max field RMS not finite | afoc, vign=100%, кромка, field=7° |
| 6 | BINOCUL[9] | Бинокль Г=8 2w=11 d'=4 9л. | spot | max field RMS not finite | afoc, vign=100%, кромка, field=6° |
| 7 | BINOCUL[12] | Бинокль Г=12 2w=6 d'=6 10л. | spot | max field RMS not finite | afoc, vign=100%, кромка, field=3° |
| 8 | BINOCUL[13] | Бинокль Г=10 2w=5 d'=4 12л.Репински | spot | max field RMS not finite | afoc, vign=100%, кромка, field=3° |
| 9 | BINOCUL[16] | Бинокль Г=10 2w=7 d'=7 9л. | spot | max field RMS not finite | vign=100%, кромка, field=4° |
| 10 | BINOCUL[17] | Зр.труба Г=10 2w=5 d'=3 9л. | spot | max field RMS not finite | afoc, vign=100%, кромка, field=2° |
| 11 | LENS[20] | Индустар-90 f'=74.3 2w=59 1:4 4линзы | spot | max field RMS not finite | vign=100%, ПВО, field=42° |
| 12 | LENS[22] | Индустар-95 f'=38 2w=60 1:2.8 4линзы | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 13 | LENS[36] | Гелиос-109 f'=300 2w=14 1:3.2 7 линз | spot | max field RMS not finite | vign=100%, кромка, field=37° |
| 14 | LENS[39] | Гелиос-42 f'=27 2w=47 1:2.8 v=-.13 | spot | max field RMS not finite | vign=100%, предмет, луч-мимо, field=90° |
| 15 | LENS[40] | Планар f'=55 y'=50 1:2.5 v=-1 6л | spot | max field RMS not finite | vign=100%, предмет, луч-мимо, field=50° |
| 16 | LENS[44] | Юпитер-9 f'=83 2w=25 1:2 8 линз | spot | max field RMS not finite | vign=100%, кромка, field=18° |
| 17 | LENS[48] | Юпитер-24 f'=1 2w=40 1:1.7 5 линз | spot | max field RMS not finite | vign=100%, кромка, field=20° |
| 18 | LENS[54] | Таир-19 f'=500 1:3 2w=5 4 линзы | spot | max field RMS not finite | vign=100%, луч-мимо, field=22° |
| 19 | LENS[57] | Таир-33 f'=302 1:4.5 2w=15 4 линзы | spot | max field RMS not finite | vign=100%, луч-мимо, field=42° |
| 20 | LENS[73] | Вега-11У f'=54 1:2.8 2y=44 v=-5 5л. | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=22° |
| 21 | LENS[74] | Вега-5 f'=105 1:4 2y=106 v=-4 5л. | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=53° |
| 22 | LENS[75] | Вега-6 f'=76 1:4 2y=81 v=-4 5л. | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=40° |
| 23 | LENS[81] | Триплет-У f'=52 1:3.5 2y=43 v=-2.5 | spot | max field RMS not finite | vign=100%, предмет, кромка, field=22° |
| 24 | LENS[82] | Мир-1 f'=37 2w=50 1:2.9 7 линз | spot | max field RMS not finite | vign=100%, кромка, field=25° |
| 25 | LENS[84] | Мир-4 f'=29.4 2w=75 1:3.5 8 линз | spot | max field RMS not finite | vign=100%, кромка, field=38° |
| 26 | LENS[86] | Mир-11 f'=12.5 2w=54 1:2 7 линз | spot | max field RMS not finite | vign=100%, кромка, field=27° |
| 27 | LENS[87] | Мир-47 f'=20 2w=94 1:3 10линз | spot | max field RMS not finite | vign=100%, луч-мимо, field=47° |
| 28 | LENS[94] | Кинообъектив f'=30 1:2.1 2w=50 7линз | spot | max field RMS not finite | vign=100%, кромка, field=25° |
| 29 | LENS[95] | Фотообъектив f'=36 1:2.5 2w=60 7линз | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 30 | LENS[96] | Кинообъектив f'=35 1:2.6 2w=45 6линз | spot | max field RMS not finite | vign=100%, кромка, field=23° |
| 31 | LENS[99] | Мезон-2a f'=3000 1:6 2w=8 10лин | spot | max field RMS not finite | vign=100%, луч-мимо, field=210° |
| 32 | LENS[102] | Фотооб(LiF) f'=540 1:6.7 2w=20 6линз | spot | max field RMS not finite | vign=100%, кромка, field=10° |
| 33 | LENS[115] | Кинообъектив f'=18 2w=70 1:2.5 10л. | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 34 | MICROLEN[0] | Об.микр.ОМ-2 v=-10 A=0.2 2y=2 5л. | spot | axis RMS not finite | vign=100%, предмет, кромка, field=1° |
| 35 | MICROLEN[1] | Об.микр.ОМ-3 v=-3.5 A=0.1 2y=5.1 3л. | spot | axis RMS not finite | vign=100%, предмет, луч-мимо, field=3° |
| 36 | MICROLEN[2] | Об.микр.ОМ-31 v=-20 A=0.4 2y=0.9 5л. | spot | axis RMS not finite | vign=100%, предмет, кромка, field=26° |
| 37 | MICROLEN[3] | Ахромат v=-40 A=1.35 2y=0.5 9л. | vignette | ZeroDivisionError: float division by zero | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11,12,13,14, vign:ZeroDivision, предмет, кромка, field=14° |
| 38 | MICROLEN[4] | Апохромат v=-6.3 A=0.2 2y=4 5л. | vignette | ZeroDivisionError: float division by zero | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8, vign:ZeroDivision, предмет, field=2° |
| 39 | MICROLEN[5] | Апохромат v=-10 A=0.4 2y=2 7л. | vignette | ZeroDivisionError: float division by zero | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11, vign:ZeroDivision, предмет, field=1° |
| 40 | MICROLEN[6] | Апохромат v=-61 A=1.2 2y=.32 12л | vignette | ZeroDivisionError: float division by zero | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16, vign:ZeroDivision, предмет, кромка, field=9° |
| 41 | MICROLEN[7] | Апохромат ОА63 v=-63 A=1 2y=.32 11л | vignette | ZeroDivisionError: float division by zero | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17, vign:ZeroDivision, предмет, кромка, field=9° |
| 42 | MICROLEN[8] | Планахромат v=-40 A=0.75 2y=.62 9л. | vignette | ZeroDivisionError: float division by zero | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11,12,13,14, vign:ZeroDivision, предмет, field=18° |
| 43 | MICROLEN[9] | Планахромат v=-100 A=1.25 2y=0.2 13л | vignette | ZeroDivisionError: float division by zero | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19, vign:ZeroDivision, предмет, кромка, field=6° |
| 44 | MICROLEN[10] | Об.микр.панкр. v=-(1-5) d3,6,9=7,38,6.6 | spot | max field RMS not finite | vign=100%, предмет, кромка, field=10° |
| 45 | MICROLEN[11] | Об.микр.тубус0 f'=23 A=.17 2y=1.8 4л | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 46 | MICROLEN[12] | Об.микр.тубус0 f'=14 A=.3 2y=1.1 5л | spot | max field RMS not finite | vign=100%, луч-мимо, field=32° |
| 47 | MICROLEN[13] | Коллектор ОИ-19 f'=17 1:0.75 2w=30 2л | spot | axis RMS not finite | zerogap@1, ос-miss, field=15° |
| 48 | MICROLEN[14] | Конденсор f'=7 A'=1.2 2y'=1 2л | spot | max field RMS not finite | vign=100%, луч-мимо, field=29° |
| 49 | MICROLEN[15] | Конденсор f'=17 A'=1.2 2y'=1 2л | spot | max field RMS not finite | vign=100%, луч-мимо, field=29° |
| 50 | OCULAR[2] | Окуляр f'=15 2w=60 d=4 7л. | spot | max field RMS not finite | vign=100%, кромка, field=31° |
| 51 | OCULAR[3] | Окуляр f'=18 2w=65 d=5 4л. | spot | max field RMS not finite | vign=100%, кромка, field=33° |
| 52 | OCULAR[4] | Окуляр f'=15 2w=62 d=4 7л. | spot | max field RMS not finite | vign=100%, кромка, field=31° |
| 53 | OCULAR[5] | Окуляр f'=15 2w=42 d=4 4л. | spot | max field RMS not finite | vign=100%, кромка, field=21° |
| 54 | OCULAR[7] | Окуляр f'=20 2w=69 d=4 6л. | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 55 | OCULAR[9] | Окуляр f'=20 2w=76 d=4 6л. | spot | max field RMS not finite | vign=100%, кромка, field=38° |
| 56 | OCULAR[10] | Окуляр f'=22 2w=60 d=2.5 4л. | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 57 | OCULAR[12] | Окуляр f'=24 2w=71 d=6 4л. | spot | max field RMS not finite | vign=100%, предмет, луч-мимо, field=35° |
| 58 | OCULAR[15] | Окуляр f'=25 2w=70 d=7 4л. | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 59 | OCULAR[19] | Окуляр f'=20 2w=69 d=4 6л. | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 60 | OCULAR[20] | Окуляр f'=25 2w=60 d=6 4л. | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 61 | OCULAR[21] | Окуляр f'=25 2w=65 d=5 6л. | spot | max field RMS not finite | vign=100%, кромка, field=32° |
| 62 | OCULAR[22] | Окуляр f'=20 2w=69 d=4 6л. | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 63 | OCULAR[23] | Окуляр f'=25 2w=56 d=3 6л. | spot | max field RMS not finite | vign=100%, кромка, field=28° |
| 64 | OCULAR[26] | Окуляр f'=30 2w=62 d=5 6л. | spot | max field RMS not finite | vign=100%, кромка, field=31° |
| 65 | OCULAR[32] | Окуляр f'=51 2w=60 d=6 6л. | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 66 | OCULAR[33] | Окуляр Гюйгенса Г=7 2w=28 d=4 2л. | spot | max field RMS not finite | vign=100%, кромка, field=14° |
| 67 | OCULAR[34] | Окуляр Гюйгенса Г=10 2w=31 d=4 2л. | spot | max field RMS not finite | vign=100%, кромка, field=16° |
| 68 | OCULAR[40] | Окуляр симметр. f'=33 2w=50 d=7 4л. | spot | max field RMS not finite | vign=100%, луч-мимо, field=25° |
| 69 | OCULAR[43] | Окуляр симметр. f'=25 2w=48 d=5.6 4л. | spot | max field RMS not finite | vign=100%, кромка, field=24° |
| 70 | OCULAR[47] | Окуляр Эрфле f'=25 2w=40 d=3 5л. | spot | max field RMS not finite | vign=100%, кромка, field=20° |
| 71 | OCULAR[48] | Окуляр Эрфле f'=35 2w=35 d=6 5л. | spot | max field RMS not finite | vign=100%, кромка, field=17° |
| 72 | OCULAR[49] | Окуляр Эрфле f'=25 2w=60 d=5.6 5л. | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 73 | OCULAR[50] | Окуляр Эрфле f'=40 2w=70 d=5 5л. | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 74 | OCULAR[52] | Окуляр Эрфле+колf'=35 2w=62 d=7 6л. | spot | max field RMS not finite | vign=100%, кромка, field=31° |
| 75 | OCULAR[54] | Окуляр широкоуг.f'=15 2w=78 d=4 8л. | spot | max field RMS not finite | vign=100%, кромка, field=39° |
| 76 | OCULAR[55] | Окуляр широкоуг.f'=28 2w=80 d=6 5л. | spot | max field RMS not finite | vign=100%, кромка, field=40° |
| 77 | OCULAR[56] | Окуляр широкоуг.f'=28 2w=80 d=7 5л. | spot | max field RMS not finite | vign=100%, кромка, field=40° |
| 78 | OCULAR[57] | Окуляр широкоуг.f'=16 2w=85 d=4 8л. | spot | max field RMS not finite | vign=100%, кромка, field=43° |
| 79 | OCULAR[58] | Окуляр широкоуг.f'=32 2w=80 d=7 8л. | spot | max field RMS not finite | vign=100%, кромка, field=40° |
| 80 | OCULAR[59] | Окуляр широкоуг.f'=25 2w=94 d=6 6л. | spot | max field RMS not finite | vign=100%, кромка, field=47° |
| 81 | OCULAR[60] | Окуляр широкоуг.f'=20 2w=70 d=5 7л. | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 82 | OCULAR[61] | Окуляр широкоуг.f'=25 2w=70 d=4 7л. | spot | max field RMS not finite | vign=100%, кромка, field=36° |
| 83 | OCULAR[62] | Окуляр широкоуг.f'=16 2w=84 d=4 8л. | spot | max field RMS not finite | vign=100%, кромка, field=42° |
| 84 | OCULAR[63] | Окуляр широкоуг.f'=25 2w=82 d=7 6л. | spot | max field RMS not finite | vign=100%, кромка, field=41° |
| 85 | OCULAR[64] | Окуляр широкоуг.f'=24 2w=85 d=5 6л. | spot | max field RMS not finite | vign=100%, кромка, field=43° |
| 86 | OCULAR[65] | Окуляр широкоуг.f'=26 2w=90 d=6 7л. | spot | max field RMS not finite | vign=100%, кромка, field=45° |
| 87 | OCULAR[66] | Окуляр широкоуг.f'=18 2w=80 d=5 4л. | spot | max field RMS not finite | vign=100%, кромка, field=40° |
| 88 | OCULAR[67] | Окуляр широкоуг.f'=16 2w=85 d=4 8л. | spot | max field RMS not finite | vign=100%, кромка, field=43° |
| 89 | OCULAR[68] | Окуляр широкоуг.f'=18 2w=87 d=3.5 9л. | spot | max field RMS not finite | vign=100%, кромка, field=44° |
| 90 | OCULAR[69] | Окуляр широкоуг.f'=25 2w=100 d=6 7л. | spot | max field RMS not finite | vign=100%, кромка, field=50° |
| 91 | OCULAR[70] | Окуляр шир.+кол.f'=30 2w=82 d=6 9л. | spot | max field RMS not finite | vign=100%, кромка, field=46° |
| 92 | OCULAR[73] | Ок.панкр.f'=12-24 2w=48 d3=2.13 d6=37.7 | spot | max field RMS not finite | vign=100%, кромка, field=24° |
| 93 | OCULAR[74] | Окуляр компенс. f'=17 2w=38 d=4 4л. | spot | max field RMS not finite | vign=100%, кромка, field=19° |
| 94 | REPROD[1] | Репрод.об. v=-1 2y'=185 A'=.05 f'=210 | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=93° |
| 95 | REPROD[2] | ОП-04/40 v=-1 2y'=20 A'=.4 f'=76 | spot | axis RMS not finite | vign=100%, предмет, ПВО, field=10° |
| 96 | REPROD[3] | Триплет-У v=-2.5 2y'=108 A'=.1 f'=52 | spot | max field RMS not finite | vign=100%, предмет, кромка, field=22° |
| 97 | REPROD[4] | Гелиос-42 v=-.13 2y'=24 A'=.18 f'=27 | spot | max field RMS not finite | vign=100%, предмет, луч-мимо, field=90° |
| 98 | REPROD[5] | Планар v=-1 2y'=100 A'=.1 f'=55 | spot | max field RMS not finite | vign=100%, предмет, луч-мимо, field=50° |
| 99 | REPROD[7] | Вега-5 v=-4 2y'=430 A'=.1 f'=105 | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=53° |
| 100 | REPROD[8] | Вега-6 v=-4 2y'=324 A'=.1 f'=76 | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=40° |
| 101 | REPROD[9] | Вега-11У v=-5 2y'=220 A'=.03 f'=54 | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=22° |
| 102 | REPROD[10] | Юпитер-16 v=-.01 2y'=40 A'=.25 f'=51 | spot | max field RMS not finite | vign=100%, предмет, ПВО, field=20° |
| 103 | REPROD[11] | Аврора-1 v=-1 2y'=50 A'=.12 f'=80 | spot | axis RMS not finite | vign=100%, предмет, луч-мимо, field=25° |
| 104 | REPROD[12] | Аврора-7 v=-1 2y'=170 A'=.1 f'=253 | spot | max field RMS not finite | vign=100%, предмет, луч-мимо, field=85° |
| 105 | RUSSAR[0] | Руссар-1 f'=97 1:5.7 2w=110 3лин. | spot | max field RMS not finite | zerogap@5, vign=100%, кромка, field=55° |
| 106 | RUSSAR[1] | Руссар-3 f'=135 1:3.4 2w=90 4лин. | spot | axis RMS not finite | zerogap@1,5, vign=100%, кромка, ос-miss, field=45° |
| 107 | RUSSAR[2] | Руссар-4 f'=100 1:6.7 2w=110 3лин. | spot | max field RMS not finite | vign=100%, кромка, field=55° |
| 108 | RUSSAR[3] | Руссар-5 f'=135 1:4.5 2w=90 4лин. | spot | max field RMS not finite | vign=100%, кромка, field=45° |
| 109 | RUSSAR[4] | Руссар-6 f'=125 1:4.4 2w=92 4лин. | spot | max field RMS not finite | vign=100%, кромка, field=46° |
| 110 | RUSSAR[5] | Руссар-9 f'=210 1:5.2 2w=65 4лин. | spot | max field RMS not finite | vign=100%, кромка, field=33° |
| 111 | RUSSAR[7] | Руссар-13 f'=100 1:5 2w=103 4лин. | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 112 | RUSSAR[8] | Руссар-15 f'=100 1:3.7 2w=100 5линз | spot | max field RMS not finite | vign=100%, кромка, field=50° |
| 113 | RUSSAR[9] | Руссар-17 f'=100 1:5.6 2w=104 4лин. | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 114 | RUSSAR[10] | Руссар-18 f'=210 1:5.5 2w=93 4лин. | spot | max field RMS not finite | vign=100%, кромка, field=47° |
| 115 | RUSSAR[11] | Руссар-19 f'=100 1:6.3 2w=103 3лин. | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 116 | RUSSAR[16] | Руссар-25 f'=97 1:6.3 2w=110 6линз | spot | max field RMS not finite | vign=100%, кромка, field=55° |
| 117 | RUSSAR[24] | Руссар-34 f'=200 1:6.8 2w=93 8линз | spot | max field RMS not finite | vign=100%, кромка, field=47° |
| 118 | RUSSAR[25] | Руссар-35 f'=200 1:6.8 2w=65 8линз | spot | max field RMS not finite | vign=100%, кромка, field=33° |
| 119 | RUSSAR[26] | Руссар-36 f'=100 1:9 2w=103 8линз | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 120 | RUSSAR[31] | Руссар-40 f'=62 1:6.8 2w=104 8линз | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 121 | RUSSAR[32] | Руссар-42 f'=100 1:8.8 2w=103 8линз | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 122 | RUSSAR[33] | Руссар-43 f'=140 1:6.8 2w=85 8линз | spot | max field RMS not finite | vign=100%, кромка, field=43° |
| 123 | RUSSAR[34] | Руссар-44б f'=98 1:6.8 2w=103 6линз | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 124 | RUSSAR[35] | Руссар-44 f'=100 1:6.8 2w=103 8линз | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 125 | RUSSAR[36] | Руссар-49 f'=100 1:6.8 2w=104 8линз | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 126 | RUSSAR[37] | Руссар-49а f'=100 1:6.8 2w=103 8линз | spot | max field RMS not finite | vign=100%, кромка, field=52° |
| 127 | RUSSAR[39] | Руссар-68 f'=350 1:7 2w=40 6линз | spot | max field RMS not finite | vign=100%, кромка, field=20° |
| 128 | RUSSAR[43] | Киноруссар-2 f'=28 1:2.8 2w=52 7л | spot | max field RMS not finite | vign=100%, кромка, field=26° |
| 129 | RUSSAR[44] | Киноруссар-3 f'=32 1:2.5 2w=46 7л | spot | max field RMS not finite | vign=100%, кромка, field=23° |
| 130 | RUSSAR[45] | Киноруссар-4 f'=50 1:2.2 2w=34 8л | spot | max field RMS not finite | vign=100%, кромка, field=17° |
| 131 | RUSSAR[49] | Киноруссар-7 f'=23 1:3.5 2w=108 9л | spot | max field RMS not finite | vign=100%, кромка, field=54° |
| 132 | RUSSAR[53] | Киноруссар-12 f'=29 1:3 2w=90 11л | spot | max field RMS not finite | vign=100%, кромка, field=54° |
| 133 | RUSSAR[54] | Киноруссар-13 f'=21 1:1.9 2w=107 7л | spot | axis RMS not finite | zerogap@6, vign=100%, кромка, ос-miss, field=54° |
| 134 | RUSSAR[56] | Киноруссар-44 f'=23 1:5.6 2w=101 8л | spot | max field RMS not finite | vign=100%, кромка, field=51° |
| 135 | RUSSAR[59] | Видеоруссар-1 f'=7 1:1.8 2w=97 9л | spot | max field RMS not finite | vign=100%, кромка, field=48° |
| 136 | RUSSAR[60] | Видеоруссар-2 f'=10 1:2.5 2w=98 9л | spot | max field RMS not finite | vign=100%, кромка, field=49° |
| 137 | RUSSAR[61] | Видеоруссар-3м f'=11 1:3.5 2w=96 10л | spot | axis RMS not finite | zerogap@10, vign=100%, кромка, ос-miss, field=48° |
| 138 | RUSSAR[63] | Гидроруссар-2 f=-63 1:10 2w=82 8л | spot | axis RMS not finite | zerogap@0, ос-miss, field=41° |
| 139 | RUSSAR[64] | Гидроруссар-3 f=-14 1:4.8 2w=70 4л | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 140 | RUSSAR[65] | Гидроруссар-4 f=-118 1:10 2w=68 8л | spot | axis RMS not finite | vign=100%, предмет, кромка, field=645° |
| 141 | RUSSAR[66] | Гидроруссар-5 f=-34 1:3.6 2w=69 5л | spot | axis RMS not finite | zerogap@0, ос-miss, field=35° |
| 142 | RUSSAR[67] | Гидроруссар6исх.f=-28 1:4 2w=90 3л | spot | max field RMS not finite | vign=100%, кромка, field=45° |
| 143 | RUSSAR[68] | Гидроруссар-6 f=-20 1:2.8 2w=90 6л | spot | max field RMS not finite | vign=100%, кромка, field=45° |
| 144 | RUSSAR[69] | Гидроруссар-7 f=-21 1:2 2w=90 11л | spot | max field RMS not finite | vign=100%, кромка, field=45° |
| 145 | RUSSAR[70] | Гидроруссар-8 f=-28.8 1:3.5 2w=72 6л | spot | axis RMS not finite | zerogap@1, vign=100%, кромка, ос-miss, field=36° |
| 146 | RUSSAR[71] | Гидроруссар-9 f=-21 1:1.5 2w=90 5л | spot | axis RMS not finite | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18, кромка, ос-miss, field=45° |
| 147 | RUSSAR[72] | Гидроруссар-10 f=-12.3 1:2 2w=60 7л | spot | axis RMS not finite | efl~0, L=0, zerogap@0,1,2,3,4,5,6,7,8,9,10,11,12,13,14, vign=100%, луч-мимо, ос-miss, field=30° |
| 148 | RUSSAR[76] | Гидроруссар-14 f=-12.7 1:1.6 2w=80 12л | spot | max field RMS not finite | vign=100%, кромка, field=40° |
| 149 | RUSSAR[77] | Гидроруссар-15 f=-12.7 1:1.6 2w=80 15л | spot | max field RMS not finite | vign=100%, кромка, field=40° |
| 150 | RUSSAR[78] | Гидроруссар-16 f=-9.9 1:3.2 2w=90 12л | spot | max field RMS not finite | vign=100%, кромка, field=45° |
| 151 | RUSSAR[79] | Гидроруссар-18 f=-33.2 1:2 2w=60 9л | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 152 | RUSSAR[80] | Гидроруссар-19 f=22.4 1:2.3 2w=60 10л | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 153 | RUSSAR[81] | Гидроруссар-20 f=37.6 1:4 2w=60 12л | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 154 | RUSSAR[82] | Гидроруссар-21 f=-28 1:3 2w=60 5л | spot | max field RMS not finite | vign=100%, кромка, field=30° |
| 155 | RUSSAR[83] | Гидроруссар-4a f=-104 1:10 2w=87 8л | spot | axis RMS not finite | zerogap@0, ос-miss, field=44° |
| 156 | USBINOCL[1] | IR -.2X D=10 2W=72 10L 2USP4632498 | spot | max field RMS not finite | efl=0, vign=100%, кромка, field=36° |
| 157 | USBINOCL[2] | IR -20X D=200 2W=3.3 7L+2M GB2177812 | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, ос-miss, field=2° |
| 158 | USBINOCL[3] | IR -1X D=14 2W=46 9L 1USP4632498 | spot | max field RMS not finite | efl=0, vign=100%, кромка, field=23° |
| 159 | USBINOCL[4] | IR -.05X D=15 2W=60 6L USP3947084 | spot | max field RMS not finite | efl=0, vign=100%, кромка, field=30° |
| 160 | USBINOCL[5] | LAS .66X D=12 2W=80 3L SEMI-GAUSS | spot | axis RMS not finite | efl=0, vign=100%, кромка, ос-miss, field=40° |
| 161 | USBINOCL[6] | LAS .25X D=5 2W=2 2L LASER EXP. | spot | axis RMS not finite | efl=0, zerogap@2, vign=100%, луч-мимо, ос-miss, field=1° |
| 162 | USBINOCL[7] | LAS .25X D=5 2W=2 2L LASER EXP. | spot | axis RMS not finite | efl=0, zerogap@2, vign=100%, луч-мимо, ос-miss, field=1° |
| 163 | USBINOCL[8] | LAS .25X D=5 2W=2 3L LASER EXP. | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, ос-miss, field=1° |
| 164 | USBINOCL[9] | LAS .25X D=5 2W=2 3L LAZER EXP | spot | axis RMS not finite | efl=0, zerogap@4, vign=100%, луч-мимо, ос-miss, field=1° |
| 165 | USLENS[0] | ACHRO F'=100 1:6 2W=36 6L USP46814076 | spot | max field RMS not finite | vign=100%, кромка, field=18° |
| 166 | USLENS[10] | SPEED F'=40 1:0.6 2W=2 7L 800nm | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, field=1° |
| 167 | USLENS[30] | GAUSS F'=100 1:1.1 2W=40 9L USP2828671 | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, field=20° |
| 168 | USLENS[34] | GAUSS F'=100 1:1.8 2W=40 5L USP4376571 | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, field=20° |
| 169 | USLENS[35] | GAUSS F'=100 1:2 2W=40 6L LEE | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, field=20° |
| 170 | USLENS[36] | GAUSS F'=100 1:2 2W=40 6L LEE | mtf_geo | no max field MTF (empty spot?) | field=20° |
| 171 | USLENS[39] | MIRR F'=500 1:6.7 2W=5 2M+6L IIZUKA | spot | axis RMS not finite | efl=0, zerogap@12, vign=100%, луч-мимо, ос-miss, field=3° |
| 172 | USLENS[40] | MIRR F'=100 1:1.2 2W=13 2M+3L WILDERM. | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, ос-miss, field=7° |
| 173 | USLENS[45] | LAS F'=100 1:50 2W=106 2 USP4707085 | spot | max field RMS not finite | vign=100%, кромка, field=53° |
| 174 | USLENS[47] | LAS F'=25 1:25 2W=57 5L USP4755030 | mtf_geo | no axial MTF (empty spot?) | field=29° |
| 175 | USLENS[48] | LAS F'=4.3 1:1 2W=70 1L USP4449792 | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, ос-miss, field=35° |
| 176 | USLENS[49] | LAS F'=10 1:2 2W=34 1L USP4729645 | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, field=17° |
| 177 | USLENS[50] | LAS F'=4.5 1:1 2W=5 5L USP4447138 | spot | axis RMS not finite | efl=0, ос-miss, field=3° |
| 178 | USLENS[53] | LAS F'=25 1:50 2W=58 3L USP4401362 | spot | max field RMS not finite | vign=100%, кромка, field=29° |
| 179 | USLENS[54] | LAS F'=100 1:16 2W=100 4 SCANNER | spot | max field RMS not finite | vign=100%, кромка, field=50° |
| 180 | USLENS[56] | LAS F'=6.5 1:0.8 2W=2 4L LAS DIODE | mtf_geo | no max field MTF (empty spot?) | efl=0, field=1° |
| 181 | USLENS[58] | MONO F'=77 1:2.3 2W=18 5L | spot | max field RMS not finite | vign=100%, кромка, field=9° |
| 182 | USLENS[62] | LENS F'=100 1:2.5 2W=46 4L | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, field=23° |
| 183 | USLENS[73] | LENS F'=25 1:5.6 2W=60 4L USP3951523 | spot | max field RMS not finite | efl=0, vign=100%, луч-мимо, field=30° |
| 184 | USLENS[108] | WIDE F'=1 1:5 2W=80 8L USP2878724 | spot | max field RMS not finite | vign=100%, стоп-луч, field=40° |
| 185 | USLENS[110] | WIDE F'=118 1:3.5 2W=100 11L USP3841736 | spot | max field RMS not finite | vign=100%, кромка, field=50° |
| 186 | USLENS[111] | WIDE F'=100 1:3.5 2W=70 7L USP4645312 | spot | max field RMS not finite | vign=100%, кромка, field=35° |
| 187 | USLENS[112] | WIDE F'=102 1:3.5 2W=100 13L DE2507368 | spot | max field RMS not finite | vign=100%, кромка, field=50° |
| 188 | USLENS[114] | WIDE F'=100 1:12 2W=71 6L | spot | max field RMS not finite | vign=100%, кромка, field=36° |
| 189 | USLENS[130] | LENS F'=1 1:3.7 2W=36 6L 1USP2452909 | spot | axis RMS not finite | zerogap@1, vign=100%, кромка, ос-miss, field=18° |
| 190 | USLENS[131] | LENS F'=1 1:5.5 2W=28 6L 2USP2452909 | spot | max field RMS not finite | vign=100%, кромка, field=14° |
| 191 | USLENS[132] | LENS F'=1 1:3.3 2W=28 6L USP2458836 | spot | axis RMS not finite | zerogap@3, vign=100%, кромка, ос-miss, field=14° |
| 192 | USLENS[138] | LENS F'=1 1:4.5 2W=30 6L USP2576436 | spot | max field RMS not finite | vign=100%, кромка, field=15° |
| 193 | USLENS[144] | LENS F'=43 1:2.8 2W=54 11L USP2628532 | spot | max field RMS not finite | vign=100%, луч-мимо, field=27° |
| 194 | USLENS[146] | LENS F'=1 1:2.2 2W=46 5L USP2363712 | spot | axis RMS not finite | zerogap@1, ос-miss, field=23° |
| 195 | USLENS[180] | LENS F'=1 1:3.3 2W=34 7L USP2872845 | spot | max field RMS not finite | vign=100%, кромка, field=17° |
| 196 | USLENS[197] | SPEED F'=1 1:1.6 2W=40 4L USP2336300 | spot | max field RMS not finite | vign=100%, кромка, field=20° |
| 197 | USMICRO[0] | ENDOUSP4721372 F'=1 A=.36 2Y=.18 11L | spot | axis RMS not finite | efl=0, vign=100%, предмет, кромка, field=5° |
| 198 | USMICRO[1] | MIC USP3925910 F'=11 A=.4 2Y=0.7 8L | spot | max field RMS not finite | vign=100%, кромка, field=20° |
| 199 | USMICRO[2] | MIC USP3925910 F'=11 A=.4 2Y=0.7 8L | spot | max field RMS not finite | vign=100%, кромка, field=20° |
| 200 | USMICRO[3] | MICROLENS F'=4.7 A=.65 2Y=0.5 5L | spot | max field RMS not finite | vign=100%, кромка, field=14° |
| 201 | USMICRO[4] | MICROLENS F'=16 A=.25 2Y=1.8 4L | spot | max field RMS not finite | vign=100%, луч-мимо, field=52° |
| 202 | USREPROD[3] | 1/2 REP 1:8 2W=40 F'=100 USP 540122 | spot | axis RMS not finite | efl=0, vign=100%, луч-мимо, field=20° |
| 203 | USREPROD[4] | REP V=-1 A=.11 Y=.3 F'=602 TELECENTR. | spot | axis RMS not finite | vign=100%, предмет, луч-мимо, field=17° |
| 204 | USREPROD[6] | REP V=-1 A=.1 Y=2 F'=4125 | spot | axis RMS not finite | предмет, field=2° |
| 205 | USREPROD[7] | REP V=-1 A=.1 Y=2 F'=455 | spot | axis RMS not finite | vign=100%, предмет, луч-мимо, field=2° |
| 206 | USREPROD[8] | REP V=-1 A=.05 Y=50 F'=147 USP3418038 | spot | max field RMS not finite | vign=100%, предмет, кромка, field=50° |
| 207 | USREPROD[9] | REP V=-2 A=.05 Y=150 F'=190 USP3436145 | spot | max field RMS not finite | vign=100%, предмет, кромка, field=150° |
| 208 | USREPROD[10] | REP V=-1 A=.04 Y=58 F'=100 USP3482902 | spot | max field RMS not finite | vign=100%, предмет, кромка, field=58° |
| 209 | USREPROD[11] | REP V=-1 A=.05 Y=53 F'=99 | spot | max field RMS not finite | vign=100%, предмет, кромка, field=53° |
| 210 | USREPROD[12] | REP V=-1 A=.05 Y=74 F'=110 JP | spot | max field RMS not finite | vign=100%, предмет, кромка, field=74° |
| 211 | USREPROD[13] | REP V=-1 A=.03 Y=59 F'=100 JP | spot | max field RMS not finite | vign=100%, предмет, кромка, field=59° |
| 212 | USREPROD[14] | 1/2 REP 1:5.5 2W=50 F'=100 USP 721240 | spot | max field RMS not finite | efl=0, vign=100%, луч-мимо, field=25° |
| 213 | ZOOM[0] | Мир-1 f'=37 2w=50 1:2.9 7 линз | spot | max field RMS not finite | vign=100%, кромка, field=25° |
| 214 | ZOOM[2] | Мир-4 f'=29.4 2w=75 1:3.5 8 линз | spot | max field RMS not finite | vign=100%, кромка, field=38° |
| 215 | ZOOM[4] | Mир-11 f'=12.5 2w=54 1:2 7 линз | spot | max field RMS not finite | vign=100%, кромка, field=27° |
| 216 | ZOOM[5] | Мир-47 f'=20 2w=94 1:3 10линз | spot | max field RMS not finite | vign=100%, стоп-луч, field=47° |

