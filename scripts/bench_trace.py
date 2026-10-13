# -*- coding: utf-8 -*-
"""Микробенчмарк трассировки лучей (baseline до C++ порта)."""
import sys, time, statistics
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from optics_engine import OpticalSystem
from analysis.ray_tracing import Ray, trace_ray_through_system, trace_fan, trace_grid_3d
from domain.models import create_demo_system_by_name

def bench(name, fn, n=5):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = fn()
        times.append(time.perf_counter() - t0)
    print(f"{name:40s} {statistics.median(times)*1000:10.2f} ms  (min {min(times)*1000:.2f})  result={r}")

# Демо-система (ахромат)
system = create_demo_system_by_name("achromat")

if system:
    # 1. Одиночный луч
    bench("single ray x1", lambda: len(trace_ray_through_system(system, Ray(y=0.5, m=1.0), 0.55).path), n=3)
    # 2. Веер 64 лучей
    bench("trace_fan 64 rays", lambda: sum(len(t.path) for t in trace_fan(system, num_rays=64)))
    # 3. Веер 256
    bench("trace_fan 256 rays", lambda: sum(len(t.path) for t in trace_fan(system, num_rays=256)))
    # 4. Сетка 3D 3 кольца x 16 = 40+ лучей
    try:
        bench("trace_grid_3d 3x16", lambda: trace_grid_3d(system, num_rings=3, num_azimuths=16), n=3)
    except Exception as e:
        print("grid3d failed:", e)
print("PY_BENCH_DONE")
