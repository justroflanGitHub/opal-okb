# -*- coding: utf-8 -*-
"""Паритет нативного C++ ядра (``_opal_native``) с Python-референсом.

Системы — ``create_demo_system_by_name`` (achromat / telephoto / petzval /
mirror); сетка fan 33 луча × 3 поля × 2 длины волны: точки пути и OPL —
до ``atol=1e-9``, флаги ошибок — точно. Дополнительно: сетка
``trace_grid_3d``, координатные изломы (п. 17), увеличенный зрачок
(``pupil_range=1.5`` — ветки EDGE/STOP), экранирование (OBSCURED),
асферика с коникой (итерации Ньютона) и одиночный луч ``trace_one``.
"""
import pytest

ray_native = pytest.importorskip('ray_native')

pytestmark = pytest.mark.skipif(
    not ray_native.HAS_NATIVE,
    reason='_opal_native не собран (native/build.bat)')

from domain.models import create_demo_system_by_name          # noqa: E402
from analysis.ray_tracing import (                             # noqa: E402
    Ray,
    trace_fan,
    trace_grid_3d,
    trace_ray_through_system,
)

#: Допуск сравнения точек пути и OPL (TASK_NATIVE: 1e-9; фактически <3e-14).
ATOL = 1e-9

#: Демо-системы domain/models.py.
SYSTEM_NAMES = ['achromat', 'telephoto', 'petzval', 'mirror']

#: Длины волн: e-линия (зелёная) и g-линия (синяя) — обе в каталоге стёкол.
WAVELENGTHS = [0.54607, 0.43405]


def _fields(system, count: int = 3):
    """Поля системы (до ``count``); при нехватке — убывающие доли последнего."""
    vals = [fp.y for fp in system.field_points][:count]
    while len(vals) < count:
        vals.append(vals[-1] * 0.6 if vals else 0.0)
    return vals


def _assert_parity(ref, nat, ctx: str) -> None:
    """Посравнивать списки результатов референса и нативного ядра.

    Пути и OPL сравниваются и для лучей с ошибками (EDGE/STOP/MISS) —
    ядро воспроизводит те же точки обрыва; фактическая точность
    побайтовая (diff == 0.0), допуск 1e-9 — требование TASK_NATIVE.
    """
    assert len(ref) == len(nat), f'{ctx}: число результатов {len(ref)} != {len(nat)}'
    for i, (r, n) in enumerate(zip(ref, nat)):
        c = f'{ctx}, луч {i}'
        assert r.success == n.success, c
        assert r.error == n.error, f'{c}: ошибка {r.error!r} != {n.error!r}'
        assert r.surfaces_hit == n.surfaces_hit, \
            f'{c}: поверхностей {r.surfaces_hit} != {n.surfaces_hit}'
        assert len(r.path) == len(n.path), f'{c}: точек пути {len(r.path)} != {len(n.path)}'
        for j, (a, b) in enumerate(zip(r.path, n.path)):
            assert a == pytest.approx(b, abs=ATOL), f'{c}: точка пути {j}: {a} != {b}'
        assert r.opl == pytest.approx(n.opl, abs=ATOL), f'{c}: OPL {r.opl} != {n.opl}'


# ============================================================
# Основная сетка: fan 33 × 3 поля × 2 wl на каждой системе
# ============================================================

@pytest.mark.parametrize('name', SYSTEM_NAMES)
def test_fan_parity(name):
    """fan 33 луча × 3 поля × 2 wl: путь/OPL до 1e-9, флаги — точно."""
    system = create_demo_system_by_name(name)
    for field_y in _fields(system):
        for wl in WAVELENGTHS:
            ref = trace_fan(system, 33, wl=wl, field_y=field_y)
            nat = ray_native.trace_fan_native(system, 33, wl=wl, field_y=field_y)
            _assert_parity(ref, nat, f'{name} f={field_y} wl={wl}')


@pytest.mark.parametrize('name', SYSTEM_NAMES)
def test_grid_3d_parity(name):
    """Кольцевая сетка зрачка (3×8 и 1×6): путь/OPL до 1e-9."""
    system = create_demo_system_by_name(name)
    for kwargs in (dict(num_rings=3, num_azimuths=8,
                        field_y=system.field_points[-1].y),
                   dict(num_rings=1, num_azimuths=6, field_y=0.0)):
        ref = trace_grid_3d(system, wl=0.54607, **kwargs)
        nat = ray_native.trace_grid_3d_native(system, wl=0.54607, **kwargs)
        assert len(ref) == len(nat)
        for ring_r, ring_n in zip(ref, nat):
            _assert_parity(ring_r, ring_n, f'{name} grid {kwargs}')


# ============================================================
# Ветви ошибок и спецслучаи
# ============================================================

@pytest.mark.parametrize('name', SYSTEM_NAMES)
def test_fan_oversized_pupil(name):
    """pupil_range=1.5: краевые лучи обрезаются — EDGE/STOP совпадают точно."""
    system = create_demo_system_by_name(name)
    field_y = system.field_points[-1].y
    ref = trace_fan(system, 33, pupil_range=1.5, wl=0.54607, field_y=field_y)
    nat = ray_native.trace_fan_native(system, 33, pupil_range=1.5,
                                      wl=0.54607, field_y=field_y)
    _assert_parity(ref, nat, f'{name} pupil_range=1.5')


def test_error_branches_exercised():
    """Санити: увеличенный зрачок ахромата реально даёт EDGE и STOP
    (паритет-тесты не вакуумные — ветки ошибок C++ покрыты)."""
    system = create_demo_system_by_name('achromat')
    ref = trace_fan(system, 33, pupil_range=1.5, wl=0.54607, field_y=3.0)
    errors = {r.error for r in ref}
    assert 'EDGE' in errors, 'ожидались обрезанные краевые лучи (EDGE)'
    assert 'STOP' in errors, 'ожидалась обрезка апертурной диафрагмой (STOP)'


def test_ref_pow_bitparity():
    """Самопроверка окружения: ``ref_pow(x, 2.0)`` побитово равен ``x ** 2``.

    Референс возводит в квадрат через CPython ``float_pow`` → ucrtbase.dll
    ``pow``; модуль собран со статическим CRT, поэтому его pow обязан идти
    через ту же ucrtbase.dll (GetProcAddress при импорте). Если это
    сломалось (другой CRT/платформа), побайтовый паритет невозможен —
    подробности в ``native/README.md``.
    """
    import struct

    import _opal_native

    # 399.99999992968741935 — реальный az нормали зеркала, на нём
    # pow и умножение расходятся ровно на 1 ulp (0x…e2823e против …3f)
    for x in (399.99999992968741935, 0.007500003684924539, -12.3456789,
              1.0000000000001, 1e-7, 123.456, 0.0, 1.0):
        assert (struct.pack('>d', x ** 2)
                == struct.pack('>d', _opal_native.ref_pow(x, 2.0))), repr(x)


def test_coord_break_parity():
    """Наклон/децентрировка поверхностей (п. 17): локальные СК в C++."""
    system = create_demo_system_by_name('achromat')
    system.surfaces[1].tilt_x = 5.0
    system.surfaces[1].decenter_y = 0.5
    system.surfaces[2].tilt_y = -3.0
    system.surfaces[2].tilt_z = 2.0
    for field_y, wl in [(3.0, 0.54607), (0.0, 0.43405)]:
        ref = trace_fan(system, 33, wl=wl, field_y=field_y)
        nat = ray_native.trace_fan_native(system, 33, wl=wl, field_y=field_y)
        _assert_parity(ref, nat, f'coord-break achromat f={field_y} wl={wl}')

    system2 = create_demo_system_by_name('petzval')
    system2.surfaces[2].tilt_x = 2.5
    system2.surfaces[3].decenter_x = 1.0
    ref = trace_fan(system2, 33, wl=0.54607, field_y=3.0)
    nat = ray_native.trace_fan_native(system2, 33, wl=0.54607, field_y=3.0)
    _assert_parity(ref, nat, 'coord-break petzval f=3.0')


def test_obscuration_parity():
    """Центральное экранирование: блокированные лучи — 'OBSCURED'."""
    system = create_demo_system_by_name('mirror')
    system.obscuration_ratio = 0.3
    ref = trace_fan(system, 33, wl=0.54607, field_y=0.5)
    nat = ray_native.trace_fan_native(system, 33, wl=0.54607, field_y=0.5)
    _assert_parity(ref, nat, 'obscured mirror')
    assert any(r.error == 'OBSCURED' for r in ref), 'экранирование не сработало'


def test_aspheric_parity():
    """Асферика (коника + A4/A6): итерации Ньютона в C++."""
    system = create_demo_system_by_name('achromat')
    system.surfaces[1].conic_constant = -0.5
    system.surfaces[1].aspheric_coeffs = [1e-6, -2e-9]
    ref = trace_fan(system, 33, wl=0.54607, field_y=3.0)
    nat = ray_native.trace_fan_native(system, 33, wl=0.54607, field_y=3.0)
    _assert_parity(ref, nat, 'aspheric achromat f=3.0')


# ============================================================
# Одиночный луч и согласованность батча
# ============================================================

@pytest.mark.parametrize('name', SYSTEM_NAMES)
def test_trace_one_parity(name):
    """trace_one против референса на характерных лучах (вне/внутри зрачка)."""
    system = create_demo_system_by_name(name)
    rays = [
        Ray(x=0, y=0.0, z=-50.0, k=0, l=0.0, m=1.0),
        Ray(x=0, y=2.0, z=-50.0, k=0, l=0.02, m=0.9998),
        Ray(x=0, y=-3.5, z=-50.0, k=0, l=-0.03, m=0.99955),
    ]
    for ray in rays:
        ref = trace_ray_through_system(system, ray, 0.54607)
        nat = ray_native.trace_one(
            system, (ray.x, ray.y, ray.z, ray.k, ray.l, ray.m), 0.54607)
        _assert_parity([ref], [nat], f'{name} trace_one y={ray.y}')


def test_batch_consistency():
    """trace_batch поэлементно равен trace_one (один и тот же C++ вход)."""
    system = create_demo_system_by_name('telephoto')
    rays = [(0.0, py * 4.0, -60.0, 0.0, 0.01 * py, 1.0) for py in range(-3, 4)]
    batch = ray_native.trace_batch(system, rays, 0.54607)
    for ray6, res in zip(rays, batch):
        one = ray_native.trace_one(system, ray6, 0.54607)
        assert res.error == one.error
        assert res.opl == pytest.approx(one.opl, abs=1e-12)
        assert len(res.path) == len(one.path)


def test_fallback_matches_reference():
    """Fallback без C++ (native_supports=False) даёт те же результаты,
    что и прямая трассировка референсом (механизм деградации не искажает)."""
    system = create_demo_system_by_name('achromat')
    system.surfaces[1].aspheric_coeffs = [0.0] * 9  # > MAX_ASPHERIC_TERMS → fallback
    assert not ray_native.native_supports(system)
    rays = [(0.0, py * 3.0, -60.0, 0.0, 0.01 * py, 1.0) for py in range(-3, 4)]
    res = ray_native.trace_batch(system, rays, 0.54607)
    for ray6, r in zip(rays, res):
        ref = trace_ray_through_system(system, Ray(*ray6), 0.54607)
        assert r.error == ref.error
        assert r.opl == pytest.approx(ref.opl, abs=1e-12)
        assert r.surfaces_hit == ref.surfaces_hit
