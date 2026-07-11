"""Регрессионный тест: OPJ файлы с мусорными поверхностями не вызывают зависание."""
import math
import os
import time
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = BASE_DIR / "extracted" / "opal_okb"


class TestOPJGarbage:
    def test_andrew_2_no_garbage(self):
        """ANDREW_2.OPJ не содержит мусорные поверхность."""
        path = EXTRACTED_DIR / "ANDREW_2.OPJ"
        if not path.exists():
            pytest.skip("file not found")
        from opj_reader import load_opj
        sys_obj, _ = load_opj(str(path))
        for s in sys_obj.surfaces:
            assert not math.isnan(s.radius), "NaN radius in surface"
            assert not math.isinf(s.thickness), "Inf thickness"
            assert abs(s.thickness) < 1e6, f"Garbage thickness {s.thickness}"

    def test_helios8_no_garbage(self):
        """HELIOS8.OPJ не содержит мусорные поверхности."""
        path = EXTRACTED_DIR / "HELIOS8.OPJ"
        if not path.exists():
            pytest.skip("file not found")
        from opj_reader import load_opj
        sys_obj, _ = load_opj(str(path))
        for s in sys_obj.surfaces:
            assert not math.isnan(s.radius), "NaN radius"
            assert abs(s.thickness) < 1e6, f"Garbage thickness {s.thickness}"

    def test_opj_no_hang(self):
        """Загрузка + расчёт OPJ не зависает (timeout test)."""
        path = EXTRACTED_DIR / "HELIOS8.OPJ"
        if not path.exists():
            pytest.skip("file not found")
        from opj_reader import load_opj
        from optics_engine import paraxial_trace
        from ray_tracing import trace_fan
        t0 = time.time()
        sys_obj, _ = load_opj(str(path))
        paraxial_trace(sys_obj)
        trace_fan(sys_obj, num_rays=5, wl=0.58756, field_y=0.0)
        t1 = time.time()
        assert t1 - t0 < 5.0, f"Took {t1 - t0:.1f}s — possible hang"
