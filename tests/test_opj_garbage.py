# TODO: convert to pytest — uses sys.stdout hack and custom runner
"""Регрессионный тест: OPJ файлы с мусорными поверхностями не вызывают зависание."""
import sys, os, io, math
if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opj_reader import load_opj
from optics_engine import paraxial_trace
from ray_tracing import trace_fan


class TestOPJGarbage:
    def test_andrew_2_no_garbage(self):
        """ANDREW_2.OPJ не содержит мусорные поверхности."""
        path = os.path.join(os.path.dirname(__file__), '..', 'extracted', 'opal_okb', 'ANDREW_2.OPJ')
        if not os.path.exists(path):
            print('  ⏭ Skip (file not found)')
            return
        sys_obj, _ = load_opj(path)
        for s in sys_obj.surfaces:
            assert not math.isnan(s.radius), f"NaN radius in surface"
            assert not math.isinf(s.thickness), f"Inf thickness"
            assert abs(s.thickness) < 1e6, f"Garbage thickness {s.thickness}"
        print(f'  ✅ test_andrew_2_no_garbage ({len(sys_obj.surfaces)} surfaces)')

    def test_helios8_no_garbage(self):
        """HELIOS8.OPJ не содержит мусорные поверхности."""
        path = os.path.join(os.path.dirname(__file__), '..', 'extracted', 'opal_okb', 'HELIOS8.OPJ')
        if not os.path.exists(path):
            print('  ⏭ Skip (file not found)')
            return
        sys_obj, _ = load_opj(path)
        for s in sys_obj.surfaces:
            assert not math.isnan(s.radius), f"NaN radius"
            assert abs(s.thickness) < 1e6, f"Garbage thickness"
        print(f'  ✅ test_helios8_no_garbage ({len(sys_obj.surfaces)} surfaces)')

    def test_opj_no_hang(self):
        """Загрузка + расчёт OPJ не зависает (timeout test)."""
        import time
        path = os.path.join(os.path.dirname(__file__), '..', 'extracted', 'opal_okb', 'HELIOS8.OPJ')
        if not os.path.exists(path):
            print('  ⏭ Skip (file not found)')
            return
        t0 = time.time()
        sys_obj, _ = load_opj(path)
        paraxial_trace(sys_obj)
        trace_fan(sys_obj, num_rays=5, wl=0.58756, field_y=0.0)
        t1 = time.time()
        assert t1 - t0 < 5.0, f"Took {t1-t0:.1f}s — possible hang"
        print(f'  ✅ test_opj_no_hang ({t1-t0:.2f}s)')


if __name__ == '__main__':
    test = TestOPJGarbage()
    methods = [m for m in dir(test) if m.startswith('test_')]
    passed = 0
    failed = 0
    for m in methods:
        try:
            getattr(test, m)()
            passed += 1
        except Exception as e:
            print(f'  ❌ {m}: {e}')
            failed += 1
    print(f'\n{"="*60}')
    print(f'ИТОГО: {passed}/{passed+failed} пройдено, {failed} не пройдено')
    print(f'{"="*60}')
