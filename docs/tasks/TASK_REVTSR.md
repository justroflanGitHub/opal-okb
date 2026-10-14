# TASK_REVTSR: §18 — TSR-рантайм OPAL (печать/формы за пределами OPALA.EXE)

## Цель
Из §14.0 REVERSE_TRACE.md: вывод таблиц идёт через TSR-движок — lcall 0xFF95
(рантайм-помощь), far-вызовы 0x2e73:0x2042, TSR-сегменты 0x2e73/0x506e/0x52a6/0x52d4,
строковые реквизиты в 0x52d4. Содержимое — [НЕИЗВЕСТНО], «вне EXE».
Гипотеза: TSR-код резидентен из друпих EXE поставки (OPALTRAC.EXE 43KB /
OPALCALC.EXE 91KB / METAPRN.EXE 336KB — принтер-метакод?) — НАЙТИ его.

## Материалы
- extracted/opal_okb/: OPALA.EXE 339800, OPALTRAC.EXE 43310, OPALCALC.EXE 91296,
  METAPRN.EXE 336712, METAPRNO.EXE 355144, OPALOW/OPALLAP/OPALO/OPALOS/OPAVA/OPALVP
- Декомпилы: C:\tools\rea-out\decomp_opaltrac\ (1 файл!), decomp_opalcalc\ (317)
- Ghidra-проекты готовы: C:\tools\rea-out\{OPAL,OPALTRAC,OPALCALC}.gpr
- lcall 0xFF95 = far call через ВЕКТОР int-таблицы (0xFF95:0xxxx) — TSR перехват
  вектора? В реальном DOS far call на сегмент 0xFF95 невозможно напрямую — это
  ВЫЗОВ ПО ВЕКТОРУ. Проверить семантику в 0746/e920 (как записан вызов).

## Задача → analysis/REVERSE_TSR.md (ОТДЕЛЬНЫЙ файл, НЕ трогать REVERSE_TRACE.md)
1. Найти в OPALTRAC/OPALCALC/METAPRN: код, устанавливающий резидентные вектора
   (int 0x95/0x35? — в hex-дампах 4000:5bxx видны int 0x35/0x39/0x3a/0x3d/0xe0 —
   ШИНА TSR-сервисов!). Разобрать int 0x35 (виден чаще всего) — что делает.
2. Сегменты 0x2e73 (движок печати 0x2042), 0x506e/0x52a6 (литералы), 0x52d4
   (строки-реквизиты) — искать их установку: TSR грузится, выделяет сегменты,
   far-указатели возвращаются вызывателю OPALA.
3. Интерфейс: как OPALA узнаёт адреса TSR (поиск сигнатуры в памяти? адрес в PSP?
   фикс. сегмент?). Проверить INIT-код OPALA (стартовые функции сегмента 1000/2000).
4. Состав TSR-сервиса: печать строк (0x2e73:0x2042), λ→n (e7db→0xFF95), что ещё.
5. Вывод: карта памяти после загрузки TSR + OPALA (сегменты, кто где живёт).

## Инструменты
- Ghidra headless (образцы команд в tools/ghidra_scripts/*.java + история:
  analyzeHeadless.bat C:\tools\rea-out OPALTRAC -process OPALTRAC.EXE -noanalysis
  -scriptPath C:\tools\ghidra_scripts -postScript DecompileAll.java)
  ⚠️ JAVA_HOME=C:\tools\jdk21x\jdk-21.0.12.1+1 обязателен в PATH
- Проще: строки/байты grep'ать py-скриптами по EXE-файлам (hex-поиск)
- Коммит: docs(reverse): §18 TSR-рантайм (REVERSE_TSR.md)

## Правила
- НЕ трогать REVERSE_TRACE.md и код порта
- Если Ghidra-запуск нужен, но не выходит — ручной hex-анализ легитимен
