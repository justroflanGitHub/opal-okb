# G2BANK — банк эталонных .PRN (волна 2026-10-17)

**Цель:** 10–15 систем разных типов из каталога `C:\GOLDEN_DOS` (*.OPJ, 82 имён —
тот самый «каталог архива» файлового диалога Чтения) → эталонные .PRN.

## Откалиброванный рецепт (sanity US00KI02 = OK, значения эталона совпали)

Отличия от карточки задачи, найдены калибровкой 10:12–10:27:

```
boot (~30 c, title сразу = авто-восстановленный OPALA)
→ F10 → MENUOPAL (бар УЖЕ активен) → ENTER («Формиров.»→METAPRN)
→ F2 → ENTER (Чтение) → BS×12 → <ИМЯ> → (2 c) → ENTER   # загрузка .OPJ
→ F5   ← ВЫХОД ИЗ РЕДАКТОРА = F5 «Меню работ», F10 из таблицы НЕ выходит!
→ RIGHT (ОДИН, курсор после F5 на «Формиров.») → ENTER («Анализ»)
→ ENTER (п.1 Работа-RT; оракул свежести: PROTOCOL.PRN 0 б)
→ F6   ← ОБЯЗАТЕЛЬНО: текст-таблицы (иначе GR-флаг RT.REG → F9 пишет .PCX)
→ '4' (габариты) → '6' (осевой пучок; закрытие вида '4' пишет секцию в протокол)
→ ENTER (закрыть вид '6' → секция осевого пучка в протоколе)
→ '6' (снова открыть вид — F4/F9 работают ТОЛЬКО из вида)
→ F4 → F9 → ENTER → RT__HHMM.PRN → bank/<ИМЯ>.PRN
```

Нюансы:
- `PROTOCOL.PRN` на диске обновляется только при F9-сохранении — live-оракул
  роста НЕ работает; свежесть проверяется только «0 б на старте RT».
- RT-файл из вида = дамп протоколa (все накопленные секции); из меню F9 пишет
  мусор «Задание режимов» (195 б, RT___052) — не использовать.
- Оракулы драйвера: title (`Program: …`), пиксель-диф скринов, контент .PRN
  (заголовок «Cистема-…», «Аберрации осевого пучка», размер).
- Sanity-эталон: `bank/US00KI02.PRN` 1689 б = заголовок IR + Габариты пучков +
  Аберрации осевого пучка **-.09008/.062432** (= RT__2236.PRN 1997). ✓

Драйвер: `scripts/g2bank.py` (`py scripts/g2bank.py ИМЯ [ИМЯ…]`, ребут на систему).
Артефакты: `analysis/reverse_data/golden/bank/`, скрины `capture/gb_*.bmp`.

## Выбор систем (15 + sanity)

| # | Имя | Тип (заголовок OPJ, offset 12) |
|---|---|---|
| 0 | US00KI02 | IR -.2X D=10 2W=72 10L 2USP (зеркальный ИК, sanity-эталон) |
| 1 | 121 | Руссар-1 f'=97 1:5.7 2w=110 3лин. (широкоугольный объектив) |
| 2 | ST | Таир f'=300 1:3.5 2w=5 4 линзы |
| 3 | ST4 | Таир-12 f'=150 1:4 2w=11 3 линзы |
| 4 | OPAL3 | телемар-11 f'=300 1:5 2л |
| 5 | HELIOS8 | гелиос-81 |
| 6 | OKULAR | окуляр (6 поверхностей) |
| 7 | OBEKTIV | объектив |
| 8 | PLIOPT | ОБЪЕКТИВ |
| 9 | LAB6_GAS | Триплет f'=45 1:3.9 2w=50 3линзы |
| 10 | OPTICS#1 | Триплет f'=200 1:4 2w=12 3линзы |
| 11 | GTIN05 | сферич. дифр. решётка |
| 12 | GTIE00 | ЭКРАН - ГОЭ |
| 13 | YBBS77_ | Тор (зеркальный тор, 1756 б) |
| 14 | S_KOND1 | конденсор |
| 15 | KURSOVIK | без заголовка, 17 поверхностей (курсовой) |

## Сводная таблица (строки добавляет g2bank.py)

| Система | RT-файл | Размер | Статус | Примечание |
|---|---|---|---|---|

## Лог циклов (авто)

| US00KI02 | - | - | NOOPALA2 | Анализ не запустил RT |
- `US00KI02 NOOPALA2`
| US00KI02 | RT__1022.PRN | 768 | OK-NOAXIAL | секций~1, габариты=да; Cистема-IR    -.2X D=10  2W=72 10L  2USP  Работа |
- `US00KI02: RT__1022.PRN 768б axial=False seps~1 PROTOCOL 0->729; head='Cистема-IR    -.2X D=10  2W=72 10L  2USP  Работа-RT                   '`
| US00KI02 | - | - | SAVEFAIL | F9 не создал файл; PROTOCOL=0 б |
- `US00KI02 SAVEFAIL PROTOCOL=0`
| US00KI02 | RT__1026.PRN | 1689 | OK | эталонные значения осевого пучка СОВПАЛИ; Cистема-IR    -.2X D=10  2W=72 10L  2USP  Работа |
- `US00KI02: RT__1026.PRN 1689б axial=True seps~3 PROTOCOL 0->1693; head='Cистема-IR    -.2X D=10  2W=72 10L  2USP  Работа-RT                   '`
| 121 | RT__1028.PRN | 2870 | OK | секций~3, габариты=да; Cистема-Руссар-1   f'=97   1:5.7  2w=110  Работа |
- `121: RT__1028.PRN 2870б axial=True seps~3 PROTOCOL 0->2887; head="Cистема-Руссар-1   f'=97   1:5.7  2w=110  Работа-RT                   "`
| ST | - | - | SAVEFAIL | F9 не создал файл; PROTOCOL=0 б |
- `ST SAVEFAIL PROTOCOL=0`
| ST4 | RT__1031.PRN | 2326 | OK | секций~3, габариты=да; Cистема-Таир-12  f'=150  1:4    2w=11  3  Работа |
- `ST4: RT__1031.PRN 2326б axial=True seps~3 PROTOCOL 0->2337; head="Cистема-Таир-12  f'=150  1:4    2w=11  3  Работа-RT                   "`
| OPAL3 | - | - | NOOPALA2 | Анализ не запустил RT |
- `OPAL3 NOOPALA2`
| OPAL3 | - | - | BOOTFAIL | окно не появилось |
- `OPAL3 BOOTFAIL`

## Инцидент 10:32–11:07 (починено)

1. Реальный флейк: ~2 из 8 бутов уходят в DOS shell (`Program: DOSBOX`, «холостой
   EXEC» §21.5) — лечится повторным ребутом (попытка 2 в boot()).
2. БАГ ДРАЙВЕРА (главный): проверка `'DOSBOX' not in title.upper()` всегда False —
   «DOSBox 0.74-3» присутствует в ЛЮБОМ title. Исправлено: сравнивать модуль после
   `Program:`. Из-за бага все буты 10:36–11:04 «зависали» в ожидании.
3. RT.REG переписан извне GR→TX (+ бэкап .bak_g2bank) — граф-сохᴘанения .PCX более
   не угрожают; в драйвере остался fallback «F9 дал .PCX → F6 + повтор».
4. Boot быстрый: авто-восстановленный OPALA стабилен уже ~3–6 с (не 35 с).

| OPAL3 | RT__11_8.PRN | 1122 | OK | секций~2, габариты=нет; Cистема-телемар-11 f'=300 1:5 2л          Работа |
- `OPAL3: RT__11_8.PRN 1122б axial=True seps~2 PROTOCOL 0->1083; head="Cистема-телемар-11 f'=300 1:5 2л          Работа-RT                   "`
| HELIOS8 | RT__11_9.PRN | 99 | OK-NOAXIAL | секций~0, габариты=нет; Cистема-ОП-04/40   v=-1   2y'=20  A'=.4   Работа |
- `HELIOS8: RT__11_9.PRN 99б axial=False seps~0 PROTOCOL 0->0; head="Cистема-ОП-04/40   v=-1   2y'=20  A'=.4   Работа-RT                   "`
| OKULAR | - | - | SAVEFAIL | F9 не создал файл; PROTOCOL=0 б |
- `OKULAR SAVEFAIL PROTOCOL=0`
| OKULAR | - | - | NOOPALA2 | Анализ не запустил RT |
- `OKULAR NOOPALA2`
| OBEKTIV | - | - | LOADFAIL | диалог Чтения не реагирует |
- `OBEKTIV LOADFAIL diff=0.0013`
| OBEKTIV | RT__1114.PRN | 1005 | OK | секций~2, габариты=нет; Cистема-                                  Работа |
- `OBEKTIV: RT__1114.PRN 1005б axial=True seps~2 PROTOCOL 0->966; head='Cистема-                                  Работа-RT                   '`
| HELIOS8 | - | - | SAVEFAIL | F9 не создал файл; PROTOCOL=-1 б |
- `HELIOS8 SAVEFAIL PROTOCOL=-1`
| HELIOS8 | RT__1117.PRN | 2318 | OK | секций~3, габариты=да; Cистема-гелиос-81                         Работа |
- `HELIOS8: RT__1117.PRN 2318б axial=True seps~3 PROTOCOL 0->2329; head='Cистема-гелиос-81                         Работа-RT                   '`
| OKULAR | RT__1118.PRN | 1777 | OK | секций~3, габариты=да; Cистема-ОП-04/40   v=-1   2y'=20  A'=.4   Работа |
- `OKULAR: RT__1118.PRN 1777б axial=True seps~3 PROTOCOL 0->1782; head="Cистема-ОП-04/40   v=-1   2y'=20  A'=.4   Работа-RT                   "`
| OBEKTIV | RT__1119.PRN | 2009 | OK | секций~4, габариты=да; Cистема-                                  Работа |
- `OBEKTIV: RT__1119.PRN 2009б axial=True seps~4 PROTOCOL 0->2052; head='Cистема-                                  Работа-RT                   '`
| PLIOPT | RT__1120.PRN | 2596 | OK | секций~3, габариты=да; Cистема-ОБЪЕКТИВ                          Работа |
- `PLIOPT: RT__1120.PRN 2596б axial=True seps~3 PROTOCOL 0->2610; head='Cистема-ОБЪЕКТИВ                          Работа-RT                   '`
| LAB6_GAS | - | - | NOOPALA2 | Анализ не запустил RT |
- `LAB6_GAS NOOPALA2`
| LAB6_GAS | - | - | NOOPALA2 | Анализ не запустил RT |
- `LAB6_GAS NOOPALA2`
| OPTICS#1 | - | - | NOOPALA2 | Анализ не запустил RT |
- `OPTICS#1 NOOPALA2`
## Статус 11:25 (батч bncopbwfh в работе)

В банке 8/16: US00KI02✓ 121✓ ST4✓ OPAL3✓ HELIOS8✓ OKULAR✓ OBEKTIV✓ PLIOPT✓
(✓ = axial-секция есть, заголовок системы свой; OKULAR проверен побайтово против
OBEKTIV — данные другие, «ОП-04/40» в заголовке = поле параметров самого файла).
Едут: OPTICS#1 GTIN05 GTIE00 YBBS77_ S_KOND1 KURSOVIK ST. LAB6_GAS — 2× незагрузка
(diff 0.047), взять в ручной добор. F6 из основного пути УБРАН (это toggle:
под TX включает график → F9 пишет .PCX).

| OPTICS#1 | - | - | NOOPALA2 | Анализ не запустил RT |
- `OPTICS#1 NOOPALA2`
| GTIN05 | - | - | NOOPALA2 | Анализ не запустил RT |
- `GTIN05 NOOPALA2`
| GTIN05 | - | - | NOOPALA2 | Анализ не запустил RT |
- `GTIN05 NOOPALA2`
| GTIE00 | RT__1127.PRN | 2732 | OK | секций~3, габариты=да; Cистема-ЭКРАН - ГОЭ                       Работа |
- `GTIE00: RT__1127.PRN 2732б axial=True seps~3 PROTOCOL 0->2748; head='Cистема-ЭКРАН - ГОЭ                       Работа-RT                   '`
| YBBS77_ | - | - | NOOPALA2 | Анализ не запустил RT |
- `YBBS77_ NOOPALA2`
| YBBS77_ | RT__1130.PRN | 1213 | MISLOAD | НЕДАГРУЗ: в файле «ЭКРАН - ГОЭ» (остаток GTIE00 в редакторе), все нули; Тор не загрузился; файл удалён из банка |
- `YBBS77_: RT__1130.PRN 1213б axial=True seps~2 PROTOCOL 0->0; head='Cистема-ЭКРАН - ГОЭ                       Работа-RT                   '`
| S_KOND1 | - | - | NOOPALA2 | Анализ не запустил RT |
- `S_KOND1 NOOPALA2`
| S_KOND1 | - | - | NOOPALA2 | Анализ не запустил RT |
- `S_KOND1 NOOPALA2`
| KURSOVIK | RT__1134.PRN | 2007 | OK | секций~4, габариты=да; Cистема-                                  Работа |
- `KURSOVIK: RT__1134.PRN 2007б axial=True seps~4 PROTOCOL 0->2050; head='Cистема-                                  Работа-RT                   '`
| ST | RT__1135.PRN | 2318 | OK | секций~3, габариты=да; Cистема-Tаир     f'=300  1:3.5  2w=5   4  Работа |
- `ST: RT__1135.PRN 2318б axial=True seps~3 PROTOCOL 0->2329; head="Cистема-Tаир     f'=300  1:3.5  2w=5   4  Работа-RT                   "`

## Раунд добора 11:42 (сессия B: стенд свободен, батч завершился)

QC банка: 11 валидных; YBBS77_.PRN удалён (MISLOAD). Ретрай пяти отставших:
LAB6_GAS OPTICS#1 GTIN05 S_KOND1 YBBS77_ (для # в имени — контроль диалога по скрину).
| SKOND1 | - | - | NOOPALA2 | Анализ не запустил RT |
- `SKOND1 NOOPALA2`
| LAB6_GAS | - | - | NOOPALA2 | Анализ не запустил RT |
- `LAB6_GAS NOOPALA2`
| SKOND1 | - | - | LOADFAIL | диалог Чтения не реагирует |
- `SKOND1 LOADFAIL diff=0.0000`
| LAB6_GAS | - | - | LOADFAIL | диалог Чтения не реагирует |
- `LAB6_GAS LOADFAIL diff=0.0000`
| LAB6GAS | - | - | LOADFAIL | диалог Чтения не реагирует |
- `LAB6GAS LOADFAIL diff=0.0000`
| OPTICS#1 | - | - | LOADFAIL | диалог Чтения не реагирует |
- `OPTICS#1 LOADFAIL diff=0.0000`
| LAB6GAS | - | - | LOADFAIL | диалог Чтения не реагирует |
- `LAB6GAS LOADFAIL diff=0.0000`
| OPTICS#1 | - | - | LOADFAIL | диалог Чтения не реагирует |
- `OPTICS#1 LOADFAIL diff=0.0000`
| GTIN05 | - | - | LOADFAIL | диалог Чтения не реагирует |
- `GTIN05 LOADFAIL diff=0.0000`
| OPTICS1 | - | - | NOOPALA2 | Анализ не запустил RT |
- `OPTICS1 NOOPALA2`
| GTIN05 | RT__1144.PRN | 1323 | OK-NOAXIAL | секций~1, габариты=да; Cистема-                                  Работа |
- `GTIN05: RT__1144.PRN 1323б axial=False seps~1 PROTOCOL 0->2492; head='Cистема-                                  Работа-RT                   '`
| OPTICS1 | RT__1145.PRN | 2474 | OK-NOAXIAL | секций~2, габариты=да; Cистема-                                  Работа |
- `OPTICS1: RT__1145.PRN 2474б axial=False seps~2 PROTOCOL 2492->2492; head='Cистема-                                  Работа-RT                   '`
