# -*- coding: utf-8 -*-
"""Микробенчмарк: Python-референс против нативного C++ ядра (TASK_NATIVE).

Запуск:
    py scripts/bench_native.py            # все системы
    py scripts/bench_native.py achromat   # одна система

Таблица «до/после»: те же сценарии, что в scripts/bench_trace.py (веера,
сетка зрачка), плюс чистое ядро без Python-обёртки и fan 4096 из ТЗ.
Строки «facade» включают генерацию лучей/подготовку поверхностей и
оборачивание результатов в namedtuple (честный end-to-end).

Секция «integration spots» (TASK_INTEGRATE): реальные массовые вызовы
приложения — analysis/aberrations.py (таблицы аберраций GUI, оценочная
функция оптимизатора), visualization.py (ход лучей). «До» получается
подменой ``ray_native.native_supports`` → ``trace_batch`` уходит на
Python-референс с тем же интерфейсом: измерается именно эффект
интеграции, без дублирования логики в бенче.

visualization3d._trace_rays = wl(≤3) × поле(≤2) вызовов «trace_grid_3d
3×8» из таблицы выше (замер вручную: кнопка «Trace 3D Rays» в GUI;
инстанцирование QOpenGLWidget в headless-бенче ненадёжно).
"""
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                   # noqa: E402

import ray_native                                    # noqa: E402
from domain.models import create_demo_system_by_name  # noqa: E402
from analysis.ray_tracing import (                   # noqa: E402
    Ray,
    trace_fan,
    trace_grid_3d,
    trace_ray_through_system,
)


def bench(fn, repeats: int = 5) -> float:
    """Медианное время выполнения, мс."""
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return statistics.median(times) * 1000.0


def fmt_row(label: str, t_py: float, t_nat: float) -> str:
    """Строка таблицы: scenario | Python | C++ | speedup."""
    return f"{label:36s} {t_py:10.2f} {t_nat:10.2f} {t_py / t_nat:9.1f}x"


def _with_python_core(fn):
    """Выполнить ``fn()`` с выключенным нативным ядром (fallback).

    ``ray_native.trace_batch`` при ``native_supports() == False`` идёт по
    Python-референсу с тем же интерфейсом результатов — это честный
    «до» для интеграционных точек (тот же код приложения, другое ядро).
    """
    saved = ray_native.native_supports
    ray_native.native_supports = lambda system: False
    try:
        return fn()
    finally:
        ray_native.native_supports = saved


def run_system(name: str) -> None:
    """Прогнать все сценарии на одной системе."""
    system = create_demo_system_by_name(name)
    field_y = 0.0
    wl = 0.54607

    print(f"\n=== {name} (wl={wl}, field={field_y}) ===")
    print(f"{'scenario':36s} {'Python ms':>10s} {'C++ ms':>10s} {'speedup':>9s}")
    print("-" * 70)

    # Один и те же лучи для обоих ядер: 4096 лучей по зрачку
    rays_arr = np.ascontiguousarray(np.column_stack([
        np.zeros(4096),
        np.linspace(-8.0, 8.0, 4096),
        np.full(4096, -50.0),
        np.zeros(4096), np.zeros(4096), np.ones(4096)]))
    ray_list = [tuple(r) for r in rays_arr.tolist()]

    # Чистое ядро C++: подготовки/обёртки вне замера
    import _opal_native
    surfaces = ray_native.prepare_surfaces(system, wl)
    params = ray_native._system_params(system, wl)

    t_py = bench(lambda: [trace_ray_through_system(system, Ray(*r), wl)
                          for r in ray_list])
    t_nat = bench(lambda: _opal_native.trace_batch(surfaces, rays_arr,
                                                   **params))
    print(fmt_row("core 4096 raw (no wrapping)", t_py, t_nat))

    # Facade: prepare_surfaces + трассировка + namedtuple-обёртка
    t_nat = bench(lambda: ray_native.trace_batch(system, ray_list, wl))
    print(fmt_row("core 4096 facade (end-to-end)", t_py, t_nat))

    # Одиночный луч (facade): подготовка поверхностей доминирует
    t_py = bench(lambda: trace_ray_through_system(
        system, Ray(y=0.5, m=1.0), wl), repeats=3)
    t_nat = bench(lambda: ray_native.trace_one(
        system, (0.0, 0.5, -50.0, 0.0, 0.0, 1.0), wl), repeats=3)
    print(fmt_row("single ray (facade)", t_py, t_nat))

    # Веера (генерация + трассировка)
    for n in (64, 256, 4096):
        t_py = bench(lambda n=n: trace_fan(system, num_rays=n, wl=wl,
                                           field_y=field_y))
        t_nat = bench(lambda n=n: ray_native.trace_fan_native(
            system, num_rays=n, wl=wl, field_y=field_y))
        print(fmt_row(f"trace_fan {n} rays", t_py, t_nat))

    # Сетка зрачка
    try:
        t_py = bench(lambda: trace_grid_3d(system, num_rings=3,
                                           num_azimuths=16), repeats=3)
        t_nat = bench(lambda: ray_native.trace_grid_3d_native(
            system, num_rings=3, num_azimuths=16), repeats=3)
        print(fmt_row("trace_grid_3d 3x16", t_py, t_nat))
    except Exception as exc:  # pragma: no cover — зависит от системы
        print(f"trace_grid_3d 3x16: skipped ({exc})")

    run_integration_spots(system, wl)


def run_integration_spots(system, wl: float) -> None:
    """Секция «integration spots»: реальные вызовы приложения, A/B ядро.

    Замеряет функции, которые после TASK_INTEGRATE трассируются нативным
    батчем: точечные диаграммы и фокусировочные диаграммы
    (analysis/aberrations.py, они же — оценочная функция оптимизатора),
    ход лучей 2D-визуализации (visualization.py, offscreen Qt).
    """
    import optimizer
    from analysis import aberrations as ab

    print("-- integration spots (app-level, same code, core A/B) --")

    spot = lambda: ab.compute_spot_diagram(system, wl=wl, num_rays=30)  # noqa: E731
    t_py = bench(lambda: _with_python_core(spot), repeats=3)
    t_nat = bench(spot, repeats=3)
    print(fmt_row("spot_diagram 30 grid", t_py, t_nat))

    merit = lambda: optimizer._merit_function(system, [], num_rays=20)  # noqa: E731
    t_py = bench(lambda: _with_python_core(merit), repeats=3)
    t_nat = bench(merit, repeats=3)
    print(fmt_row("optimizer merit 20 rays", t_py, t_nat))

    focus = lambda: ab.compute_focus_diagrams(system, wl=wl, num_rays=40)  # noqa: E731
    t_py = bench(lambda: _with_python_core(focus), repeats=3)
    t_nat = bench(focus, repeats=3)
    print(fmt_row("focus_diagrams 5x40 grid", t_py, t_nat))

    # visualization.py: реальный вызов виджета без GUI-ивента (offscreen).
    # set_system_fast — мгновенный осевой пучок при правке системы,
    # _trace_all_rays (через set_system) — полный ход лучей по всем λ.
    try:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PyQt5.QtWidgets import QApplication
        import visualization
        app = QApplication.instance() or QApplication([])
        view = visualization.OpticalSystemView()

        t_py = bench(lambda: _with_python_core(
            lambda: view.set_system_fast(system)), repeats=3)
        t_nat = bench(lambda: view.set_system_fast(system), repeats=3)
        print(fmt_row("viz set_system_fast 11 fan", t_py, t_nat))

        def _viz_full():
            view.chromatic_rays = True
            view.set_system(system, trace_rays=True)

        t_py = bench(lambda: _with_python_core(_viz_full), repeats=3)
        t_nat = bench(_viz_full, repeats=3)
        print(fmt_row("viz _trace_all_rays chromatic", t_py, t_nat))
        view.deleteLater()
        app.processEvents()
    except Exception as exc:  # pragma: no cover — зависит от окружения
        print(f"visualization rows: skipped ({exc}); "
              f"замер вручную: открыть систему в GUI → «Рассчитать»")


def main() -> int:
    """Прогнать бенчмарк (все демо-системы или указанная аргументом)."""
    if not ray_native.HAS_NATIVE:
        print("NO _opal_native.pyd — comparison impossible. "
              "Build: native\\build.bat", file=sys.stderr)
        return 1
    print("native core: OK (_opal_native.pyd loaded)")

    names = sys.argv[1:] or ["achromat", "telephoto", "petzval", "mirror"]
    for name in names:
        run_system(name)
    print("\nBENCH_NATIVE_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
