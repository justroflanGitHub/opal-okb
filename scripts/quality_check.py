# -*- coding: utf-8 -*-
"""Численный аналог визуальной проверки report.md по ray-путям.

Критерии OK (как у визуальных проверяющих):
- трассировка вообще работает (есть успешные лучи);
- лучи преломляются (наклон меняется между сегментами);
- пучок доходит до плоскости изображения;
- пучок сжимается к фокусу (высоты на выходе < высоты на входе).
"""
import sys, os, math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.render_catalog import build_all_entries
from catalog.library import create_system_from_entry
from ray_tracing import trace_fan
from optics_utils import get_effective_aperture


def quality(sys_obj):
    if sys_obj is None or not sys_obj.surfaces:
        return 'empty', {}
    ap = get_effective_aperture(sys_obj, default=20.0)
    wl = sys_obj.wavelengths[0].value if sys_obj.wavelengths else 0.58756
    fan = trace_fan(sys_obj, num_rays=11, pupil_range=1.0, wl=wl, field_y=0.0)
    ok = [r for r in fan if r.success and len(r.path) >= 3]
    if not ok:
        return 'no_rays', {}
    # 1) преломление: наклон меняется вдоль пути
    refracts = 0
    for r in ok:
        slopes = []
        for i in range(len(r.path) - 1):
            p1, p2 = r.path[i], r.path[i + 1]
            if abs(p2[2] - p1[2]) > 1e-12:
                slopes.append((p2[1] - p1[1]) / (p2[2] - p1[2]))
        for a, b in zip(slopes, slopes[1:]):
            if abs(b - a) > 1e-5:
                refracts += 1
                break
    # 2) вход/выход: сжатие пучка
    y_in = [abs(r.path[0][1]) for r in ok]
    y_out = [abs(r.path[-1][1]) for r in ok]
    w_in = (max(y_in) - min(y_in)) if len(y_in) > 1 else abs(y_in[0])
    w_out = (max(y_out) - min(y_out)) if len(y_out) > 1 else abs(y_out[0])
    # 3) доведение: последний сегмент доходит до image plane (последняя точка = z_img)
    z_last = max(r.path[-1][2] for r in ok)
    z_img = sum(s.thickness for s in sys_obj.surfaces)
    reaches = z_last >= z_img - 1e-6
    info = {'refract_frac': refracts / len(ok), 'w_in': w_in, 'w_out': w_out,
            'reaches_img': reaches, 'n_ok': len(ok)}
    if refracts / len(ok) < 0.3:
        return 'no_refraction', info      # лучи прямые — главный дефект отчёта
    if not reaches:
        return 'truncated', info
    if w_out > w_in * 1.05:
        # афокальные системы (окуляры, трубы, репро с 1:1) дают параллельный/
        # расходящийся пучок по построению — это не дефект
        from optics_engine import ObjectType
        if sys_obj.image_type == ObjectType.INFINITE or w_in < 1e-9:
            return 'ok_afocal', info
        return 'diverging', info
    return 'ok', info


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    entries = build_all_entries()
    stats = {}
    for idx, e in enumerate(entries):
        try:
            s = create_system_from_entry(e['entry'])
            verdict, info = quality(s)
        except Exception as ex:
            verdict, info = 'exc:' + type(ex).__name__, {}
        cat = e['category']
        stats.setdefault(cat, {})
        stats[cat][verdict] = stats[cat].get(verdict, 0) + 1
    tot = {}
    for cat, d in stats.items():
        print(f"\n{cat}:")
        for v, n in sorted(d.items(), key=lambda kv: -kv[1]):
            print(f"   {v:<15} {n}")
            tot[v] = tot.get(v, 0) + n
    print("\n=== ИТОГО ===")
    for v, n in sorted(tot.items(), key=lambda kv: -kv[1]):
        print(f"   {v:<15} {n}")
    ok = tot.get('ok', 0)
    print(f"\nOK-рейтинг: {ok}/{sum(tot.values())} = {ok/sum(tot.values())*100:.0f}%")


if __name__ == '__main__':
    main()
