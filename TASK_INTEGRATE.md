# TASK: Интеграция нативного C++ ядра в приложение (hot paths)

Проект OPAL-OKB. Ветка: feature/native-core. Нативное ядро УЖЕ готово:
- `_opal_native.pyd` (собран) + `ray_native.py` фасад: `trace_batch`, `trace_fan_native`, `trace_grid_3d_native` — интерфейс как у Python-версий, результаты ПОБАЙТОВО идентичны (23 паритет-теста зелёные).

## Цель
Приложение (GUI, анализ, оптимизатор) должно реально использовать нативную трассировку на массовых расчётах — БЕЗ изменения результатов. Ускорение ×10-20 на батчах.

## Что сделать
1. Найди все места, где трассировка вызывается В ЦИКЛАХ (горячие пути):
   - `visualization.py` (ход лучей, габаритные лучи, веера)
   - `visualization3d.py`
   - `analysis/aberrations.py` (таблицы аберраций, веера по полям/λ)
   - `optimizer.py` (оценочная функция гоняет сотни трасс)
   - `main.py` (если прямо зовёт trace_*)
   Поиск: `grep -rn "trace_fan\|trace_grid_3d\|trace_ray_through_system" --include=*.py`
2. Замени вызовы на `ray_native`-версии (`trace_fan_native`, `trace_grid_3d_native`). Точечные одиночные лучи НЕ трогать (там overhead). Если модуль зовёт trace_fan много раз по разным полям/λ — это идеальный кандидат.
3. Результаты не должны измениться: существующие тесты (`pytest tests -q`, 759 passed сейчас) обязаны остаться зелёными. Паритет-тесты уже гарантируют одинаковость trace_fan_native vs trace_fan.
4. Если где-то нужна трассировка, которой нет в ray_native (например батч по нестандартной генерации лучей) — используй `ray_native.trace_batch(system, rays_numpy_Nx6, wl)` напрямую: он принимает произвольные массивы лучей.
5. НЕ трогать: analysis/ray_tracing.py (референс), native/, ray_native.py, tests/test_native_*.
6. Измерь эффект: расширь scripts/bench_native.py секцией «integration spots» — реальный вызов из visualization/optimizer (если это функция, которую можно вызвать без GUI-ивента; если нет — просто укажи в комментарии где замерить вручную).
7. Коммиты атомарные (`perf: <место> — нативная трассировка`), CHANGELOG.md обновить (секция 1.10.x).
8. По завершении: `openclaw system event --text "Done: native core integrated into hot paths, all tests green" --mode now`

## Правила
- Никаких дублей: facade уже есть, не оборачивай обёртки.
- Fallback: ray_native сам падает на Python при отсутствии pyd — просто вызывай ray_native-функции.
- Type hints/docstrings для новых лямбд/хелперов.
