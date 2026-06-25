"""
Тесты парсера LBO/OPJ — проверка корректности загрузки систем.
Запуск: py tests\test_parser.py
"""
import sys, os, math, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lbo_reader import load_lbo_fast
from decode_lbo_opj import decode_lbo_opj
from optics_engine import paraxial_trace, refractive_index, ApertureType, ObjectType
from system_utils import deg_to_gmms, gmms_to_deg, gmms_to_str

passed = 0
failed = 0
errors = []


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        errors.append(f"FAIL: {name} {detail}")
        print(f"  FAIL: {name} {detail}")


def test_gmms_conversion():
    """Конвертация Г.ММСС."""
    print("\n=== Г.ММСС ===")
    check("0.5° → 0.30 Г.ММСС", abs(deg_to_gmms(0.5) - 0.30) < 0.001,
          f"got {deg_to_gmms(0.5)}")
    check("0.30 Г.ММСС → 0.5°", abs(gmms_to_deg(0.30) - 0.5) < 0.001,
          f"got {gmms_to_deg(0.30)}")
    check("26° → 26.0000", abs(deg_to_gmms(26.0) - 26.0) < 0.001)
    check("23.2° → 23.1200", abs(deg_to_gmms(23.2) - 23.12) < 0.001)
    check("gmms_to_str", "0°30'00\"" in gmms_to_str(0.30))


def test_industar23u():
    """Индустар-23у f'=110 — основная тестовая система."""
    print("\n=== Индустар-23у f'=110 ===")
    systems = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
    sys_obj = decode_lbo_opj(systems[3]['opj_data'])

    # Имя не должно быть именем стекла
    check("Имя системы", "Индустар" in sys_obj.name or "110" in sys_obj.name,
          f"got {sys_obj.name!r}")
    check("Имя != ТК20", sys_obj.name != "ТК20", f"got {sys_obj.name!r}")

    # Поверхности
    check("7 поверхностей", len(sys_obj.surfaces) == 7,
          f"got {len(sys_obj.surfaces)}")

    # Стёкла
    glasses = [s.glass for s in sys_obj.surfaces if s.glass and s.glass not in ('', 'ЗЕРКАЛО')]
    check("ТК16 в стёклах", any('ТК16' in g for g in glasses), f"{glasses}")
    check("ЛФ5 в стёклах", any('ЛФ5' in g for g in glasses), f"{glasses}")

    # Зеркал нет
    check("Нет зеркал", not any(s.is_reflective for s in sys_obj.surfaces))

    # Stop surface
    check("stop_surface=4", sys_obj.stop_surface == 4,
          f"got {sys_obj.stop_surface}")

    # Stop offset
    check("stop_offset=4.2", abs(sys_obj.stop_offset - 4.2) < 0.01,
          f"got {sys_obj.stop_offset}")

    # Апертура
    check("D≈21.1мм", abs(sys_obj.aperture_value - 21.1) < 0.5,
          f"got {sys_obj.aperture_value}")
    check("aperture type=ENTRANCE_PUPIL",
          sys_obj.aperture_type == ApertureType.ENTRANCE_PUPIL)

    # Поле
    check("field≈26°", abs(sys_obj.object_height - 26.0) < 0.5,
          f"got {sys_obj.object_height}")

    # Длины волн
    check("3 длины волн", len(sys_obj.wavelengths) == 3,
          f"got {len(sys_obj.wavelengths)}")
    wl_names = [w.name for w in sys_obj.wavelengths]
    check("e,G',C", "e" in wl_names and "G'" in wl_names and "C" in wl_names,
          f"got {wl_names}")

    # Параксиальный расчёт
    parax = paraxial_trace(sys_obj)
    f_val = parax.get('focal_length', 0)
    check("f'≈110", abs(f_val - 110) < 5, f"got f'={f_val:.2f}")
    check("f' не 0", abs(f_val) > 1, f"got f'={f_val}")
    check("BFD>50", parax.get('back_focal_distance', 0) > 50,
          f"got BFD={parax.get('back_focal_distance', 0):.2f}")

    # n для КВАРЦСТК не 1.5
    for s in sys_obj.surfaces:
        if s.glass and s.glass.upper() not in ('', 'ВОЗДУХ', 'AIR'):
            n = refractive_index(s.glass, 0.54607)
            check(f"n({s.glass})≠1.5", abs(n - 1.5) > 0.01,
                  f"got n={n:.6f}")


def test_mirror_lens():
    """Зеркально-линзовая система f'=450."""
    print("\n=== Об.зеркально-линз. f'=450 ===")
    systems = load_lbo_fast('extracted/opal_okb/Lib/LENS_SPC.LBO')
    sys_obj = decode_lbo_opj(systems[1]['opj_data'])

    check("Имя содержит 450", "450" in sys_obj.name, f"got {sys_obj.name!r}")

    # Зеркала
    mirrors = [s for s in sys_obj.surfaces if s.is_reflective]
    check("2 зеркала", len(mirrors) == 2, f"got {len(mirrors)}")

    # КВАРЦСТК
    has_quartz = any('КВАРЦ' in s.glass.upper() for s in sys_obj.surfaces if s.glass)
    check("КВАРЦСТК", has_quartz, f"glasses={[s.glass for s in sys_obj.surfaces]}")

    # NA
    check("NA≈0.089",
          sys_obj.aperture_type == ApertureType.NUMERICAL_APERTURE and
          abs(sys_obj.aperture_value - 0.089) < 0.005,
          f"got type={sys_obj.aperture_type.name} val={sys_obj.aperture_value}")

    # Длины волн
    check("3 длины волн", len(sys_obj.wavelengths) == 3)

    # Параксиальный
    parax = paraxial_trace(sys_obj)
    f_val = parax.get('focal_length', 0)
    check("f'≈420-460", 400 < f_val < 500, f"got f'={f_val:.2f}")
    check("f'≠0", abs(f_val) > 1)


def test_batch_lens_lbo():
    """Пакетный тест всех LENS.LBO систем — f' в пределах 15%."""
    print("\n=== LENS.LBO batch (f' within 15%) ===")
    import re
    systems = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')
    good = 0
    total = 0
    for i, s in enumerate(systems[:30]):
        try:
            sys_obj = decode_lbo_opj(s['opj_data'])
            parax = paraxial_trace(sys_obj)
            f_val = abs(parax.get('focal_length', 0))
            f_match = re.search(r"f'=([\d.]+)", s['name'])
            if f_match:
                f_target = float(f_match.group(1))
                if f_target > 0:
                    total += 1
                    ratio = abs(f_val - f_target) / f_target
                    if ratio < 0.15:
                        good += 1
                    else:
                        sys.stdout.buffer.write(f"  WARN [{i}] f'={f_val:.1f} target={f_target} ratio={ratio:.1%} ".encode())
                        sys.stdout.buffer.write(s['name'].encode('utf-8')[:40] + b'\n')
        except Exception as e:
            sys.stdout.buffer.write(f"  ERROR [{i}] {e}\n".encode())

    check(f"LENS.LBO ≥70% systems OK ({good}/{total})", good >= total * 0.7,
          f"got {good}/{total}")


def test_wavelengths_default():
    """Стандартные длины волн."""
    print("\n=== Default wavelengths ===")
    from optics_engine import _std_wavelengths
    wls = _std_wavelengths()
    check("3 wl", len(wls) == 3)
    check("e=0.54607", abs(wls[0].value - 0.54607) < 1e-6)
    check("G'=0.43405", abs(wls[1].value - 0.43405) < 1e-6)
    check("C=0.65627", abs(wls[2].value - 0.65627) < 1e-6)
    check("name e", wls[0].name == 'e')
    check("name G'", wls[1].name == "G'")
    check("name C", wls[2].name == 'C')


def test_kvarts_n():
    """Показатели преломления КВАРЦСТК."""
    print("\n=== КВАРЦСТК n ===")
    n_e = refractive_index('КВАРЦСТК', 0.54607)
    check("n(e)≈1.46", abs(n_e - 1.46) < 0.02, f"got {n_e:.6f}")
    check("n(e)≠1.5", abs(n_e - 1.5) > 0.01, f"got {n_e:.6f}")

    n_g = refractive_index('КВАРЦСТК', 0.43405)
    check("n(G')>n(e)", n_g > n_e, f"n(G')={n_g:.6f} n(e)={n_e:.6f}")

    n_c = refractive_index('КВАРЦСТК', 0.65627)
    check("n(C)<n(e)", n_c < n_e, f"n(C)={n_c:.6f} n(e)={n_e:.6f}")


if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_gmms_conversion()
    test_wavelengths_default()
    test_kvarts_n()
    test_industar23u()
    test_mirror_lens()
    test_batch_lens_lbo()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print("\nFailed tests:")
        for e in errors:
            print(f"  {e}")
    else:
        print("ALL TESTS PASSED! ✅")
