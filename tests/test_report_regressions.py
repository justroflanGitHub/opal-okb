# -*- coding: utf-8 -*-
"""Регрессионные тесты багов из report.md (проверка отображения каталога).

Каждый тест соответствует конкретному классу дефектов:
1. test_us_library_glass_resolved  — US-библиотеки (USLENS/USEYE/USREPROD):
   блок имён 'AIR' + G-разделители не распознавался → все стёкла '' →
   лучи шли прямыми без преломления (массовый FAIL ~250 систем).
2. test_russian_water_glass        — '+' в 'ВОДА+20С' ломал чтение блока имён.
3. test_zoom_no_marker_indices     — запись без маркера 1e20 (ZOOM.LBO Мир-3):
   индексы стёкол не находились → glass=''.
4. test_ri_layout_prefers_air_rows — RI-таблица (окуляры): неверный выбор
   nair/nwl ломал показатели преломления.
5. test_finite_object_no_sf_no_crash — NameError obj_z в paintEvent →
   PyQt5 abort → «зависание» рендера 14 систем.
6. test_grid_loop_bounded          — цикл сетки при гигантском z-диапазоне.
"""
import os
import sys
import math

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

qt = pytest.importorskip("PyQt5.QtWidgets")

from lbo_reader import load_lbo_fast                     # noqa: E402
from decode_lbo_opj import decode_lbo_opj                # noqa: E402
from optics_engine import paraxial_trace                  # noqa: E402

LIB_DIR = os.path.join(BASE_DIR, 'extracted', 'opal_okb', 'Lib')


def _lbo(name):
    path = os.path.join(LIB_DIR, name)
    if not os.path.isfile(path):
        pytest.skip(f"{name} не найден")
    return load_lbo_fast(path)


def test_us_library_glass_resolved():
    """USLENS: 'AIR' + G-разделители → стёкла/RI должны резолвиться."""
    systems = _lbo('USLENS.LBO')
    decoded = [decode_lbo_opj(s['opj_data']) for s in systems]
    with_glass = sum(1 for s in decoded
                     if any(sf.glass or getattr(sf, 'n_override', None)
                            for sf in s.surfaces))
    # до фикса: 0 из 234; после: подавляющее большинство
    assert with_glass > len(decoded) * 0.8, \
        f"стёкла резолвятся только у {with_glass}/{len(decoded)} систем USLENS"


def test_us_lens_refracts():
    """У ACHRO F'=100 1:6 лучи должны преломляться: параксиальное f' конечно."""
    systems = _lbo('USLENS.LBO')
    target = next(s for s in systems if 'ACHRO' in s['name'] and "F'=100" in s['name'])
    sys_obj = decode_lbo_opj(target['opj_data'])
    f = paraxial_trace(sys_obj).get('focal_length', 0)
    assert abs(f) > 10, f"f'={f}: преломления нет (лучи прямые)"
    assert abs(abs(f) - 100.0) / 100.0 < 0.15, f"f'={f} далеко от 100"


def test_russian_water_glass():
    """Гидроруссар: имя среды 'ВОДА+20С' с '+' не должно ломать блок имён."""
    systems = _lbo('RUSSAR.LBO')
    target = next((s for s in systems if 'Гидроруссар-1' in s['name']), None)
    if target is None:
        pytest.skip("Гидроруссар-1 не найден")
    sys_obj = decode_lbo_opj(target['opj_data'])
    has_glass = any(sf.glass for sf in sys_obj.surfaces)
    assert has_glass, "блок имён не прочитан (стёкла пустые)"


def test_zoom_no_marker_indices():
    """ZOOM.LBO Мир-3: запись без маркера 1e20 — индексы после толщин."""
    systems = _lbo('ZOOM.LBO')
    target = next((s for s in systems if 'Мир-3' in s['name']), None)
    if target is None:
        pytest.skip("Мир-3 (ZOOM) не найден")
    sys_obj = decode_lbo_opj(target['opj_data'])
    n_glass = sum(1 for sf in sys_obj.surfaces if sf.glass)
    assert n_glass >= 4, f"стёкла не резолвятся ({n_glass} поверхностей со стеклом)"
    f = abs(paraxial_trace(sys_obj).get('focal_length', 0))
    assert 40 < f < 100, f"f'={f}: Мир-3 f'=66"


@pytest.mark.parametrize("lbo_name,ratio", [
    ('LENS.LBO', 0.8),
    ('OCULAR.LBO', 0.8),
])
def test_russian_libraries_still_ok(lbo_name, ratio):
    """Русские библиотеки не регрессировали: f' совпадает с именами."""
    systems = _lbo(lbo_name)
    import re
    f_re = re.compile(r"[fF]['′]?=\s*(\d+(?:\.\d+)?)")
    good = total = 0
    for s in systems:
        m = f_re.search(s['name'])
        if not m:
            continue
        total += 1
        try:
            sys_obj = decode_lbo_opj(s['opj_data'])
            f = paraxial_trace(sys_obj).get('focal_length', 0)
        except Exception:
            continue
        if f and math.isfinite(f) and abs(abs(f) - float(m.group(1))) / float(m.group(1)) < 0.1:
            good += 1
    assert total > 5
    assert good / total > ratio, \
        f"{lbo_name}: f' точен только у {good}/{total}"


def test_binocul_glasses_resolved():
    """BINOCUL — афокальные трубы (f' не определён): проверяем стёкла."""
    systems = _lbo('BINOCUL.LBO')
    decoded = [decode_lbo_opj(s['opj_data']) for s in systems]
    with_glass = sum(1 for s in decoded if any(sf.glass for sf in s.surfaces))
    assert with_glass > len(decoded) * 0.7, \
        f"стёкла только у {with_glass}/{len(decoded)} систем BINOCUL"


def test_finite_object_no_sf_no_crash():
    """paintEvent конечного предмета без sF не должен падать (obj_z)."""
    from PyQt5.QtWidgets import QApplication
    from optics_engine import OpticalSystem, Surface, ObjectType
    from visualization import OpticalSystemView

    app = QApplication.instance() or QApplication(['test'])
    # вырожденная система: конечный предмет, sF=0 (плоские поверхности)
    sys_obj = OpticalSystem(name="degenerate_finite")
    sys_obj.object_type = ObjectType.FINITE
    for _ in range(3):
        sys_obj.surfaces.append(Surface(radius=0.0, thickness=5.0, glass=''))
    view = OpticalSystemView()
    view.resize(400, 300)
    view.set_system(sys_obj)
    pix = view.grab()          # до фикса: NameError → PyQt5 abort (0xC0000409)
    assert not pix.isNull()


def test_grid_loop_bounded_giant_range():
    """Гигантский z-диапазон (мусорный BFD) не должен зацикливать сетку."""
    from PyQt5.QtWidgets import QApplication
    from optics_engine import OpticalSystem, Surface
    from visualization import OpticalSystemView

    app = QApplication.instance() or QApplication(['test'])
    sys_obj = OpticalSystem(name="giant_range")
    sys_obj.surfaces.append(Surface(radius=50.0, thickness=1e12, glass=''))
    sys_obj.surfaces.append(Surface(radius=-50.0, thickness=10.0, glass=''))
    view = OpticalSystemView()
    view.resize(400, 300)
    view.set_system(sys_obj, trace_rays=True)
    pix = view.grab()
    assert not pix.isNull()
