# TASK_OPALO: B1a — декомпил и карта OPALO.EXE + OPALOW.EXE (уровень-2 анализ)

## Цель
Гипотеза (ANALIZE.DOC п.5+): OPALO/OPALOW — дифракционный анализ уровня 2:
Цернике, оптимальный фокус, ФРТ/ФРЛ/ОПФ/ФКЭ, изображения мир. Декомпилировать,
построить карту функций, привязать к пунктам ANALIZE.DOC, найти FFT-алгоритмы.

## Материалы
- extracted/opal_okb/OPALO.EXE (406717), OPALOW.EXE (438461)
- §18-инструментарий: analysis/_tools/exepack.py (проверить EXEPACK-упаковку!),
  analyzeHeadless + JAVA_HOME=C:\tools\jdk21x\jdk-21.0.12.1+1
- Образец реверса: analysis/REVERSE_UNP.md (волна 7/A1 — там методика)
- DOC/ANALIZE.DOC (cp866) — пункты уровня 2
- OPALO запускается ТОЛЬКО под резидентом OPAL.COM (§20 REVERSE_G1.md)

## Задача → analysis/REVERSE_OPALO.md
1. EXEPACK? → распаковать (exepack.py) в analysis/reverse_data/OPALO_unp.bin
2. Ghidra headless → C:\tools\rea-out\decomp_opalo\
3. Карта функций + строки (cp866): привязка к пунктам ANALIZE.DOC
4. Найти: таблицы sin/cos (DFT), размеры решёток (64/128/256?), окна,
   нормировки, интегрирование зрачка, Цернике-базис (степени, число членов),
   критерии опт. фокуса
5. Сверка с портом: analysis/strehl.py (что есть), пробелы — списком
6. Итог: ТЗ на psf_mtf.py (входы/выходы/параметры для точного соответствия OPAL)

## Правила
- REVERSE_TRACE.md/порт не трогать; коммит:
  docs(reverse): волна 8/B1a — OPALO/OPALOW карта (REVERSE_OPALO.md)
