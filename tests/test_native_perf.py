# -*- coding: utf-8 -*-
"""Перф-тесты нативного ядра (маркер ``perf``; НЕ входят в обычный прогон).

Запуск: ``OPAL_NATIVE_PERF=1 py -3 -m pytest tests/test_native_perf.py -m perf``

Почему env-флаг, а не правка pytest.ini: конфиг существующий, TASK_NATIVE
запрещает менять существующие файлы; без флага тест молча скипается при
обычном ``py -3 -m pytest``.
"""
import os
import time

import pytest

ray_native = pytest.importorskip('ray_native')

pytestmark = [
    pytest.mark.perf,
    pytest.mark.skipif(os.environ.get('OPAL_NATIVE_PERF') != '1',
                       reason='перф-тесты: OPAL_NATIVE_PERF=1'),
    pytest.mark.skipif(not ray_native.HAS_NATIVE,
                       reason='_opal_native не собран (native/build.bat)'),
]

from domain.models import create_demo_system_by_name   # noqa: E402
from analysis.ray_tracing import trace_fan             # noqa: E402

#: Порог из TASK_NATIVE.md: ускорение C++ против Python ≥ 10×.
SPEEDUP_MIN = 10.0

#: Размер веера из TASK_NATIVE.md.
FAN_RAYS = 4096


def _median(fn, repeats: int = 3):
    """Медиана времени выполнения ``fn`` (сек)."""
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return sorted(times)[len(times) // 2]


def test_fan_4096_speedup():
    """Веер 4096 лучей: нативное ядро ≥ 10× быстрее Python-референса."""
    system = create_demo_system_by_name('achromat')

    t_py = _median(lambda: trace_fan(system, num_rays=FAN_RAYS,
                                      wl=0.54607, field_y=0.0))
    t_nat = _median(lambda: ray_native.trace_fan_native(
        system, num_rays=FAN_RAYS, wl=0.54607, field_y=0.0))

    speedup = t_py / t_nat
    print(f"\nfan {FAN_RAYS}: python={t_py*1000:.1f} ms, "
          f"native={t_nat*1000:.1f} ms, speedup={speedup:.1f}x")
    assert speedup >= SPEEDUP_MIN, (
        f"ускорение {speedup:.1f}x < {SPEEDUP_MIN}x "
        f"(py={t_py*1000:.1f} ms, native={t_nat*1000:.1f} ms)")


def test_batch_core_speedup():
    """Чистое C++-ядро: ``_opal_native.trace_batch`` (сырые numpy-массивы,
    подготовки и обёртки Python вне замера) против построчного Python.
    """
    import numpy as np
    import _opal_native
    from analysis.ray_tracing import Ray, trace_ray_through_system

    system = create_demo_system_by_name('achromat')
    ys = np.linspace(-8.0, 8.0, FAN_RAYS)
    rays = np.ascontiguousarray(
        np.column_stack([np.zeros(FAN_RAYS), ys, np.full(FAN_RAYS, -50.0),
                         np.zeros(FAN_RAYS), np.zeros(FAN_RAYS),
                         np.ones(FAN_RAYS)]))
    surfaces = ray_native.prepare_surfaces(system, 0.54607)
    params = ray_native._system_params(system, 0.54607)
    ray_list = [tuple(r) for r in rays.tolist()]

    def _py():
        for r6 in ray_list:
            trace_ray_through_system(system, Ray(*r6), 0.54607)

    def _nat():
        _opal_native.trace_batch(surfaces, rays, **params)

    t_py = _median(_py, repeats=3)
    t_nat = _median(_nat, repeats=3)
    speedup = t_py / t_nat
    print(f"\ncore {FAN_RAYS}: python={t_py*1000:.1f} ms, "
          f"native={t_nat*1000:.1f} ms, speedup={speedup:.1f}x")
    assert speedup >= SPEEDUP_MIN
