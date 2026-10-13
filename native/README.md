# Нативное C++ ядро трассировки лучей (`_opal_native`)

pybind11-расширение, побайтово повторяющее формулы Python-референса
`analysis/ray_tracing.py`. Паритет важнее скорости: точки пути и OPL
совпадают до `atol=1e-9` (фактически **побитово**, diff == 0.0), флаги
ошибок (`TIR/MISS/EDGE/STOP/OBSCURED`) — точно.

Два неочевидных условия побитового паритета на Windows/MSVC:

1. `x ** 2` в референсе — это C `pow(x, 2.0)` (CPython `float_pow`), а
   ucrt `pow(x,2)` отличается от `x*x` на 1 ulp. Все квадраты там, где
   референс пишет `**2`, идут через `pow2()` — НЕ через умножение.
2. `pow` зовётся из системной `ucrtbase.dll` (`GetProcAddress` при
   импорте модуля): статический libucrt `/MT` округляет `pow(x,2)` иначе,
   чем динамическая версия, которую вызывает интерпретатор. Диагностика в
   тестах — `_opal_native.ref_pow(x, 2.0)` должен быть равен `x ** 2`
   побитово.

## Сборка одной командой

```bat
native\build.bat
```

Результат — `_opal_native.pyd` в корне репозитория. Зависимости сборки
ставятся сами: `py -3 -m pip install cmake ninja pybind11`.

Каскад тулчейнов (первый найденный побеждает):

1. **MSVC BuildTools** (`vcvars64.bat`: VS 18/2022/2019) + Ninja;
2. **портативный MinGW-w64** в `%LOCALAPPDATA%\opal-native-toolchain\mingw64`
   (без прав администратора; bootstrap — см. ниже);
3. `g++` из `PATH`.

### Bootstrap портативного MinGW-w64 (когда нет MSVC)

Без прав администратора — распаковать WinLibs в пользовательский каталог:

```bat
mkdir "%LOCALAPPDATA%\opal-native-toolchain"
curl -L -o "%LOCALAPPDATA%\opal-native-toolchain\winlibs.zip" ^
  https://github.com/brechtsanders/winlibs_mingw/releases/download/15.2.0posix-13.0.0-msvcrt-r2/winlibs-x86_64-posix-seh-gcc-15.2.0-llvm-19.1.0-mingw-w64msvcrt-13.0.0-r2.zip
powershell -NoProfile -Command "Expand-Archive -Force '%LOCALAPPDATA%\opal-native-toolchain\winlibs.zip' '%LOCALAPPDATA%\opal-native-toolchain'"
```

После этого `native\build.bat` подхватит компилятор сам (шаг 2 каскада).

## Флаги компиляции (почему именно такие)

| Тулчейн | Флаги | Причина |
|---|---|---|
| MSVC | `/O2 /fp:precise /permissive-` + **статический CRT `/MT`** | `/fp:fast` даёт расхождение с Python; статический CRT — чтобы не биндиться к чужим старым `VCRUNTIME140.dll`/`MSVCP140.dll` в процессе (например, из `PyQt5\Qt5\bin` через pytest-qt — access violation при LoadLibrary) |
| gcc/clang | `-O2 -ffp-contract=off` (+ `-static-libgcc -static-libstdc++` на Windows) | запрет FMA-сжатия `a*b+c` — иначе порядок округлений отличается от Python и паритет 1e-9 ломается |

MSVC `/fp:precise` НЕ сворачивает `pow(x, 2.0)` в `x*x` (проверено на
19.50) — честный вызов pow сохраняется, что и требуется для паритета.

## Интерфейс

- `surface_dtype()` — спецификация numpy structured dtype для `SurfaceData`
  (единственный источник раскладки; `offsetof`-ы отдаёт C++-сторона);
- `trace_one(surfaces, ray, wl=..., has_stop=..., z_stop=..., stop_radius=..., n_start=..., propagate_to_image=..., img_z=...)` — одиночный луч;
- `trace_batch(surfaces, rays, ...)` — батч `(N, 6)`; возвращает CSR-массивы
  `path_flat (M,3)`, `path_offsets (N+1)`, `end_ray (N,6)`, `opl`, `error_code`
  (0=OK, 1=TIR, 2=MISS, 3=EDGE, 4=STOP), `surfaces_hit`, `success`;
- `ref_pow(x, y)` — pow, побитово совпадающий с CPython `x ** y`
  (самопроверка окружения в тестах паритета).

Показатели преломления C++ НЕ считает: их готовит Python-фасад
`ray_native.prepare_surfaces` через `glass_catalog.compute_refractive_index`
(включая `n_override`) — дисперсия не дублируется. Матрицы координатных
изломов тоже готовит Python (`domain.spatial.CoordBreak`) — в C++ нет
тригонометрии.

## Тесты и бенчмарк

```bat
py -3 -m pytest tests/test_native_parity.py -q            :: паритет (22 теста)
set OPAL_NATIVE_PERF=1
py -3 -m pytest tests/test_native_perf.py -m perf -q      :: ускорение ≥10×
py scripts/bench_native.py                                :: таблица до/после
```
