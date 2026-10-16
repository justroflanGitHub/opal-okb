# TASK_FOCUS: B4 — критерии оптимального фокуса (OPAL) + EQF

## Цель
REVERSE_OPALO.md: критерий EQF (не разобран до конца — гипотеза: Equal
Quality Focus / наименьших квадратов W) + OPALOPT.DOC: «оптимальный фокус
по волновым и геометрическим критериям». Реализовать полный набор
критериев OPAL в find_best_focus / analysis.

## Материалы
- analysis/REVERSE_OPALO.md (EQF), analysis/REVERSE_OPTDOC.md (критерии словами)
- Существующее: analysis/strehl.py (find_best_focus?), psf_mtf.py
  (defocus-параметр), beam_heights.py, domain/calculations.py

## Реализация — расширение analysis/ (focus_criteria.py НОВЫЙ или в psf_mtf)
```python
def focus_min_rms_wavefront(system, field, wl) -> float   # min RMS(W)
def focus_max_strehl(system, field, wl) -> float          # max Штрель
def focus_min_spot_rms(system, field, wl) -> float        # min RMS пятна (геом.)
def focus_zone_best(system, field, wl) -> float           # зонный (0.7 зоны) баланс
def eqf(system, field, wl) -> dict                        # EQF: iterative паритет
    # зон W: равенство |W| по краям зоны (правило из OPALO — см. досье §EQF;
    # если не определено — реализовать зонный баланс 0.3/0.7 и задокументировать гипотезу)
def all_focus_criteria(...) -> dict  # сводка + лучшая плоскость по OPAL
```

## Тесты (tests/test_focus_criteria.py)
1. Дублет с сферической: min_RMS_W и max_Strehl дают близкие плоскости (±5%)
2. min_spot_rms ≠ min_rms_W (разные критерии — разные плоскости, физика)
3. Дефокус-симметрия: критерии зеркальны по знаку дефокуса
4. EQF на дублете: конечен, между min_rms и зонным
5. pytest -q зелёный (1009+)

## Правила
- Коммит: feat(analysis): критерии оптимального фокуса OPAL (focus_criteria)
