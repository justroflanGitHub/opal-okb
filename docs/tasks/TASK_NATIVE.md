# TASK: Нативное C++ ядро трассировки лучей (native core)

Проект: OPAL-OKB (порт OPAL-PC MS-DOS → Python/PyQt5). Репозиторий: текущая папка.
Цель: перенести горячий путь трассировки лучей из Python в C++ (pybind11), получить ×30+ ускорение с точным паритетом результатов.

## Контекст
- `analysis/ray_tracing.py` — референс-реализация (Python, per-ray, классы Ray/TraceResult).
  Функции: `intersect_sphere`, `intersect_aspheric` (Ньютон), `surface_normal`, `refract`,
  `trace_ray_through_system`, `trace_fan`, `trace_grid_3d`. Также coord-break из `domain/spatial.py`
  (`CoordBreak`, `surface_has_coord_break`, `_apply_coord_break`, `_undo_coord_break` — прочитай их сигнатуры).
- Baseline (scripts/bench_trace.py): ~80 мкс/луч (fan 256 = 20.5 мс) на demo-системе achromat.
- МСВС BuildTools 18 установлен: `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools`
  (vcvars64.bat в `VC\Auxiliary\Build\`). Python 3.13 (`py -3`).

## Что сделать

### 1. `native/` — C++ расширение
- `native/CMakeLists.txt`: pybind11 + C++20; MSVC флаги `/O2 /fp:precise` (НЕ fast — точность паритета важнее скорости!).
- `native/src/raytrace.cpp`:
  - Компактный struct `SurfaceData` (POD, SoA-friendly): R, z_surf, conic_k, k2..k10 (aspheric coeffs до 8), n_before, n_after (уже вычисленные показатели для данной wl —折射 считает Python), semi_diameter, aperture_type/limits, coord-break параметры (alpha/beta/gamma, x/y/z decenter), is_stop, is_mirror, is_coord_break.
  - `trace_one(surfaces[], ray[6], wl)` → одиночный луч (для паритета и отладки).
  - `trace_batch(surfaces[], rays[][6], wl)` → батч: результаты в numpy arrays (N×[x,y,z,k,l,m], флаги success/error-code, opl, surfaces_hit). Ошибка как int enum (0=OK,1=TIR,2=MISS,3=EDGE) — коды согласуй с Python (там строки).
  - Формулы ПО БАЙТОВО паритетны Python-реализации (порядок операций не менять! иначе паритет 1e-12 не получится).
- `native/pyproject.toml` или build-скрипт `native/build.bat`:
  vcvars64 → cmake -S native -B native/build → cmake --build → установить `_opal_native.pyd` рядом с корнем проекта (копия в `opal_okb/_opal_native.pyd` не нужна — просто в корень репо).
  pip install cmake pybind11 numpy — разреши.

### 2. Python-фасад `ray_native.py` (корень репо)
- `prepare_surfaces(system, wl) -> np.ndarray` (struct dtype) — сборка SurfaceData из OpticalSystem
  (показатели преломления через существующий `glass_catalog.compute_refractive_index` — НЕ дублируй формулу дисперсии в C++, только вызов из Python при подготовке).
- `trace_batch(system, rays, wl)` → использует `_opal_native` если импорт удался, иначе fallback на Python `trace_ray_through_system` (тот же интерфейс результатов — конвертация в TraceResult-подобные объекты: namedtuple со всеми полями path/opl/success/error).
- `trace_fan_native(system, num_rays, ...)` / `trace_grid_3d_native(...)` — аналоги trace_fan/trace_grid_3d, но генерируют лучи в numpy и зовут батч. Используй существующие helpers из `optics_utils.get_effective_aperture`/`make_field_ray` для ГЕНЕРАЦИИ лучей (не дублируй логику поля).
- НЕТ дублирования формул: физика (пересечения/Снеллиус) — ТОЛЬКО в C++; Python-версия остаётся как референс для тестов (не трогай analysis/ray_tracing.py!).

### 3. Тесты паритета `tests/test_native_parity.py`
- Системы: `create_demo_system_by_name` для achromat, telephoto, petzval, mirror (см. domain/models.py).
- Для каждой: сетка лучей (fan 33 лучей × 3 поля × 2 wl), сравнить C++ vs Python:
  path точки и opl до atol=1e-9, флаги ошибок точно совпадают.
- pytest маркировка: `@pytest.mark.skipif(not HAS_NATIVE, ...)` — тесты живут в tests/, pytest.ini уже есть.
- Тест производительности `tests/test_native_perf.py` (не в общем прогоне, маркер perf): fan 4096 лучей — C++ vs Python, assert ускорение ≥ 10×.

### 4. Сборка и прогон
- Собери (`native/build.bat`), прогони `pytest tests/test_native_parity.py -x` и `py scripts/bench_trace.py` + новый `scripts/bench_native.py` (выведи таблицу до/после).
- Если MSVC генератор cmake не найдётся — попробуй `-G "NMake Makefiles"` после vcvars64, или `-G "Ninja"` (pip install ninja).

## Правила (жёсткие)
1. Никаких дублей функций/формул между Python и C++ (C++ — реализация, analysis/ray_tracing.py — референс-legacy для паритета).
2. Магических чисел нет: EPSILON/TINY взять из optics_utils.py (передать в C++ константами с именем-комментарием источника).
3. Type hints + docstrings на Python-фасаде.
4. Существующие файлы НЕ менять (analysis/, domain/, main.py, и т.д.) — только добавлять: native/, ray_native.py, tests/test_native_parity.py, tests/test_native_perf.py, scripts/bench_native.py, TASK_NATIVE.md не трогать.
5. Работай в текущей ветке (feature/native-core уже создана). Коммиты: `feat: native core — C++ трассировка (pybind11)` и т.п.
6. CHANGELOG.md — добавь запись (секция Unreleased или новая дата).
7. Когда полностью закончено (сборка + тесты зелёные + бенчмарк снят), выполни:
   `openclaw system event --text "Done: native C++ core built, parity tests green, speedup reported" --mode now`

## Критерий готовности
- `_opal_native.pyd` собирается одной командой native/build.bat
- pytest tests/test_native_parity.py зелёный
- scripts/bench_native.py показывает ускорение ≥10× на fan 4096
- git-коммиты атомарные, CHANGELOG обновлён
