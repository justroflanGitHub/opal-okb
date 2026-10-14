# §20. G1-разведка: DOSBox-стенд + архитектура запуска пакета ОПАЛ-ПК (ночь 2026-10-15)

**Инструменты-стенд (scripts/):**
- `dosbox_send.py` — клавиши в окно DOSBox (keybd_event, foreground)
- `dosbox_page.py` / `dosbox_cyr.py` — чтение текстовых страниц VRAM из памяти DOSBox (ReadProcessMemory; x64-Layout MEMORY_BASIC_INFORMATION: Base+0, RegionSize+24, State+32, Protect+36)
- `win_shot.ps1` — PrintWindow-скриншот окна (работает из неинтерактивного контекста; CopyFromScreen — НЕТ)
- `win_ocr.ps1` — Windows.Media.Ocr (WinRT) — читает и кириллицу
- DOSBox 0.74-3 portable: `C:\tools\dosbox\DOSBox.exe` (7z-распаковка инсталлятора; winget зависает)

**Установленная архитектура запуска пакета:**
```
START.BAT / OPAL.BAT:
  set opal_work=C:\opal_okb\   (аналогично opal_temp, opal_save)
  keyrus.com                  ← резидентный русификатор клавиатуры
                              (KEYRUS beta16 (c) 1991-1994 Gurtjak)
  opal.com                    ← РЕЗИДЕНТНЫЙ КОМАНДИР ПАКЕТА
                                «(C) Paul McHacker»; строки: OPAL5x5.EXE,
                                OPAL.PSP, \OPAL.ARH, OPAL_WORK/TEMP/SAVE
```
- `OPAL.COM` (6775 б) — ставит графическую заставку ОПАЛ-ПК (BGI-подобная
  графика в VRAM A000) и, вероятно, перехватывает int (резидент-сервис)
- `OPALA.EXE` при старте проверяет резидент: без него — «This program must be
  run under OPAL-PC» (строка file 0x444C; проверка в EXEPACK-зоне, xref
  релокационные). Рядом (file 0x4274A) — «OPALPCX.EXE» + «.pcx»
- `MENUOPAL.EXE` — тоже требует резидент OPAL (то же сообщение)
- `OPALPCX.EXE` (58758 б) — НЕ лаунчер: PCX-viewer выводов печати
  (BGI EGAVGA 2.00 embedded + «PCX Programmer's Toolkit 3.53» Genus)
- С OPAL.COM резидентом OPALA стартует (заголовок Program: OPAL, заставка),
  но интерактивное меню ещё не пройдено (заставка ждёт ввода — какой клавиши,
  не установлено; ENTER/SPACE/ESC не подошли)
- .REG-файлы — настройки режимов работ (GAB=4;WING=0;WINT=0;GR), НЕ макросы —
  поправка к §16 (AVTO-проигрыватель — интерпретатор этих конфигов)

**Следующие шаги G1 (волна 7-продолжение):**
1. Реверс OPAL.COM (6.7KB — мал!): что перехватывает (int?), какую клавишу/условие
   ждёт заставка, формат OPAL.PSP; как OPALA детектит резидент (env? int-сигнатура?)
2. Пройти заставку → текстовое меню OPAL → работа RT → вывод .PRN на эталонной системе
3. Автоматизация: dosbox_send + dosbox_page в цикле (карта меню) → golden-.PRN
