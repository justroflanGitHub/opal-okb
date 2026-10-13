# -*- coding: utf-8 -*-
"""Микробенчмарк: Python-референс против нативного C++ ядра (TASK_NATIVE).

Запуск:
    py scripts/bench_native.py            # все системы
    py scripts/bench_native.py achromat   # одна система

Таблица «до/после»: те же сценарии, что в scripts/bench_trace.py (веера,
сетка зрачка), плюс чистое ядро без Python-обёртки и fan 4096 из ТЗ.
Строки «facade» включают генерацию лучей/подготовку поверхностей и
оборачивание результатов в namedtuple (честный end-to-end).
"""
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
