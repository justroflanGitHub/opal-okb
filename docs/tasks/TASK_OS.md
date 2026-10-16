# TASK_OS: C3 — реверс OPALOS.EXE + GENIZE.EXE

## Цель
OPALOS.EXE (389556) — гипотеза: оптимизационный синтез (OS = Optimization
Synthesis?) — стартовые конфигурации/автодизайн. GENIZE.EXE (196390) —
генератор исходных структур. Реверс-разведка обоих: карты, назначение,
алгоритмы (чем отличаются от OPALLAP?).

## Материалы
- extracted/opal_okb/OPALOS.EXE, GENIZE.EXE; методика REVERSE_UNP.md;
  exepack.py; JAVA_HOME=C:\tools\jdk21x\jdk-21.0.12.1+1
- DOC/OPALOPT.DOC, OPAL.DOC — упоминания синтеза/генерации

## Задача → analysis/REVERSE_OS.md (ОТДЕЛЬНЫЙ, реверс-ONLY)
1. EXEPACK? → _full.bin обоих; Ghidra headless → decomp_opalos/, decomp_genize/
2. Строки/меню cp866 → назначение модулей
3. OPALOS: карта; если оптимизация — сравнить с OPALLAP (волнa 9/C2 параллельно
   работает — просто зафиксировать отличия по строкам/структуре)
4. GENIZE: таблицы шаблонов (дублет/триплет/руссар?), правила масштабирования
5. Вердикты + что переносить в порт (списком, БЕЗ реализации)

## Правила
- Код порта НЕ трогать; коммит:
  docs(reverse): волна 9/C3 — OPALOS + GENIZE разведка (REVERSE_OS.md)
