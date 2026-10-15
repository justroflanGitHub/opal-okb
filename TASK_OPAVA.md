# TASK_OPAVA: B1b — декомпил и карта OPAVA.EXE

## Цель
OPAVA.EXE (341525) — гипотеза: волновой анализ (VA = волновая аберрация) или
автотрассировка. Декомпилировать (exepack-распаковка → Ghidra → карта),
строки cp866, привязка к DOC (ANALIZE.DOC/MAN_VP.DOC), реверс ключевых алгоритмов.

## Материалы
- extracted/opal_okb/OPAVA.EXE; §18-методика: analysis/REVERSE_UNP.md;
  tools: analysis/_tools/exepack.py, JAVA_HOME=C:\tools\jdk21x\jdk-21.0.12.1+1
- Данные поставки: OPALOW.DAT (2100), SCMVA.DAT (28434), VAFORUS.DAT (3784) —
  вероятно, ресурсы OPAVA/OPALOW (словари? таблицы?) — заглянуть в hex

## Задача → analysis/REVERSE_OPAVA.md
1. EXEPACK? → _unp.bin; Ghidra headless → decomp_opava/
2. Строки/меню cp866 → назначение модуля
3. Карта функций; ключевые вычислители — реверс (что считает)
4. DAT-файлы: формат, назначение
5. Сверка с портом: что уже есть (analysis/), пробелы

## Правила
- Не трогать REVERSE_TRACE.md/порт; коммит:
  docs(reverse): волна 8/B1b — OPAVA карта (REVERSE_OPAVA.md)
