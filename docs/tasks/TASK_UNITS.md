# TASK_UNITS: система единиц OPAL + TABOC1/OC2-таблицы + H ЗР (реверс §11+§19)

## Цель
1. **Система единиц OPAL «ближний/дальний тип»** (пробел из REVERSE_NZR.md §19.2):
   мм↔дптр, мм↔гр.мин.сек, tg×100/tg'×100, H ЗР/H' ЗР в мм
2. **TABOC1/TABOC2-таблицы** (§11): форматтеры остаточных/волновых аберраций
   осевого пучка, включая колонку H ЗР (расшифрована в §19.1: H×Ax)

## Материалы
- analysis/REVERSE_NZR.md — ВЕСЬ (§19.1 H ЗР=зрачковая координата, §19.2 система
  единиц ближний/дальний: mm↔дптр, tg×100 для дальнего, H'/tg' пространство
  изображений; §19.3 словарь)
- analysis/REVERSE_TRACE.md §11.1-11.4: TABOC1 (f6.3,f12.5,2f11.5) — «Отн.зр /
  Продольные (мм) / Поперечные пара»; TABOC2 (F7.3,3F10.4) — «Tg'*100 │ Волновые
  (дл. волн) │ Неизопл. (%) │ H ЗР (мм) │ Z'm │ C's» (первая колонка зоны/выбор)
- Существующее: analysis/tables.py (tabgl_rows/format_tabgl — ОБРАЗЕЦ стиля!),
  analysis/chromatism.py, compute_isoplanatism, trace_wavefront_hexapolar,
  coddington_trace, caustic_radii, paraxial_trace (Ax = entrance_pupil_diameter/2)
- Эталон: RT__2236.PRN (реальный TABOC2: «Н ЗР = зона × 5.0000», Ax=5.0)

## Реализация
### A) analysis/units.py (НОВЫЙ)
```python
"""Система единиц OPAL-PC: ближний (мм) / дальний (дптр, гр.мнсек) тип."""
MM_PER_DIOPTRE = ...
def mm_to_dioptres(mm) -> float           # 1000/mm (дптр), None при 0
def deg_to_gms(deg) -> str                # град.мин.сек «-36.000000» стиль OPAL f12.6 гр.мнсек:
                                          # ОСТОРОЖНО: OPAL печатает ГРАДУСЫ*3600? нет —
                                          # эталон «-36.000000» при 2w=72 → гр.мнсек = град*3600
                                          # НО колонка f12.6 вмещает 131071.999999 → до 36.4° —
                                          # сверить по RT__2250.PRN (1.000 → -36.000000 = поле в гр.мнсек?)
                                          # → ВЕРДИКТ: эталон говорит поле -36 ГРАДУСОВ записано как -36.000000 →
                                          # гр.мнсек = десятичные градусы с 6 знаками. Проверить и задокументировать!
def tg100(angle_deg) -> float             # tan×100
def pupil_h_mm(rel, Ax_mm) -> float       # H ЗР = отн.зр × Ax (§19.1)
def pupil_h_out_mm(rel, Ax_out_mm) -> float  # H' ЗР
```
### B) расширение analysis/tables.py (ОСТОРОЖНО: файл живой, добавлять в КОНЕЦ)
```python
def taboc2_rows(system, wl=None) -> list[dict]:
    """TABOC2: зона(Tg'*100 или отн.зр — по типу предмета), W (дл. волн),
    неизопл. %, H ЗР (мм), Z'm (мм), C's (мм)."""
def format_taboc2(rows) -> str   # (F7.3,3F10.4) — 4 числа из 6 величин по селектору
def taboc1_rows(system, wl=None) -> list[dict]:
    """TABOC1: отн.зр, продольная (мм), поперечные (мм) пара."""
def format_taboc1(rows) -> str   # (f6.3,f12.5,2f11.5)
```
Интеграция в fileio/protocol.py: секции TABOC1/OC2 для осевого пучка.

## Тесты (tests/test_units.py)
1. mm_to_dioptres: 100мм → 10 дптр; 0 → None/inf-защита
2. deg_to_gms: сверка с эталоном RT__2250.PRN (поле 1.000 → -36.000000)
3. pupil_h_mm: зона 0.7, Ax=5 → 3.5 (и эталон RT__2236: зона×5.0)
4. taboc2_rows на дублете: W монотонен по зоне, H ЗР = зона×Ax, Z'm/C's конечны
5. format_taboc1/2: ширины полей
6. pytest -q tests/ зелёный (872+)

## Правила
- tables.py — только добавление в конец, существующее не трогать
- analysis/vignetting.py, beam_heights.py — НЕ трогать (другие агенты)
- CHANGELOG + README + коммит:
  feat(analysis): система единиц OPAL (units.py) + TABOC1/OC2-таблицы с H ЗР (§11+§19)
