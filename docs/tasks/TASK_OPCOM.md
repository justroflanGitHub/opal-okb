# TASK_OPCOM: G1-доводка — реверс OPAL.COM (резидент-командир пакета)

## Цель
§20 REVERSE_G1.md: OPAL.COM (6775 б, «(C) Paul McHacker») — резидент;
OPALA/MENUOPAL проверяют его наличие («must be run under OPAL-PC»).
Разобрать: int-перехваты, сигнатура детекта, заставка (какую клавишу ждёт),
OPAL.PSP (что это), OPAL.ARH (архив? формат).

## Материалы
- extracted/opal_okb/OPAL.COM (6775), OPAL.PSP (найти: Get-ChildItem), OPAL.ARH (11990)
- DOSBox-стенд (scripts/dosbox_*.py, win_shot/win_ocr) — ФУНКЦИОНИРУЕТ:
  C:\GOLDEN_DOS собран, конфиг $env:TEMP\dosbox_golden.conf с цепочкой
  KEYRUS.COM→OPAL.COM→OPALA.EXE (застревает на заставке OPAL.COM)
- MS-DOS COM: загрузка по 0x100, без заголовка — Ghidra «DOS Executable (com)»

## Задача → analysis/REVERSE_OPCOM.md
1. Ghidra headless (JAVA_HOME=C:\tools\jdk21x\jdk-21.0.12.1+1) по OPAL.COM →
   decomp_opalcom\; карта: int-таблица (какие вектора ставит: 21h? 28h? 2Fh?),
   сигнатура-детект (что читает OPALA: env «OPAL...»? int-вызов? память-маркер?)
2. Заставка: цикл ожидания — какая клавиша/условие выхода (ENTER/SPACE/ESC
   НЕ подошли — см. §20)
3. OPAL.PSP — hex-просмотр: формат (PSP = Borland Profile?)
4. OPAL.ARH — формат архива (LZ? ranpacked?): заголовок, оглавление
5. ЭКСПЕРИМЕНТ (стенд жив): применить найденную клавишу через
   scripts/dosbox_send.py → dosbox_page.py — поймать текст-меню OPAL;
   пройти до запуска OPALA → если текстовый экран OPALA (CP866) — ВЫПОЛНИТЬ
   пробный расчёт и ВЫГРУЗИТЬ .PRN (сравнить с RT__2236.PRN!)
6. Итог: рецепт золотого запуска (bash-последовательность autoexec + клавиши)

## Правила
- REVERSE_TRACE.md/порт не трогать; коммит:
  docs(reverse): волна 8/G1+ — OPAL.COM резидент + рецепт запуска (REVERSE_OPCOM.md)
- DOSBox-процессы прибивать за собой (Stop-Process DOSBox)
