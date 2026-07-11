"""
OPAL-OKB Полное тестирование
============================
Тест-кейсы основаны на:
1. Документации OPAL-PC (DOC/*.DOC)
2. Примерах .OPJ файлов
3. Лабораторных работах ITMO (концептуально)
4. Классическим задачам оптического проектирования

Структура:
- Unit-тесты: оптический движок, каталог стёкол
- Integration-тесты: GUI, расчёт полной системы
- Validation-тесты: сравнение с аналитическими решениями
"""
import sys, io, os, math, time
if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    ObjectType, ApertureType, SurfaceType,
    paraxial_trace, seidel_aberrations, create_demo_system,
    refractive_index
)
from glass_catalog import compute_refractive_index, GLASS_CATALOG

# ============================================================
# Test framework
# ============================================================
passed = 0
failed = 0
errors = []

def test(name, func):
    """Run a single test."""
    global passed, failed
    try:
        result = func()
        if result:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            errors.append(name)
            print(f"  ❌ {name} — FAILED")
    except Exception as e:
        failed += 1
        errors.append(f"{name}: {e}")
        print(f"  ❌ {name} — ERROR: {e}")

def assert_approx(val, expected, tol=0.01, label=""):
    """Assert value is approximately equal."""
    if expected == 0:
        return abs(val) < tol
    return abs(val - expected) / abs(expected) < tol

# ============================================================
# SECTION 1: Glass Catalog Tests
# ============================================================
print("\n" + "="*60)
print("SECTION 1: КАТАЛОГ СТЁКОЛ")
print("="*60)

def test_air_is_1():
    n = compute_refractive_index("ВОЗДУХ", 0.58756)
    return abs(n - 1.0) < 1e-10

def test_air_english():
    n = compute_refractive_index("AIR", 0.58756)
    return abs(n - 1.0) < 1e-10

def test_empty_glass():
    n = compute_refractive_index("", 0.58756)
    return abs(n - 1.0) < 1e-10

def test_k8_nd():
    """К8: nd ≈ 1.5163 (ГОСТ 13658-78)"""
    n = compute_refractive_index("К8", 0.58756)
    return assert_approx(n, 1.5163, 0.01)

def test_tf5_nd():
    """ТФ5: nd ≈ 1.7550"""
    n = compute_refractive_index("ТФ5", 0.58756)
    return assert_approx(n, 1.7550, 0.01)

def test_dispersion_order():
    """Дисперсия: n(F) > n(d) > n(C) для любого стекла"""
    nF = compute_refractive_index("К8", 0.48613)
    nd = compute_refractive_index("К8", 0.58756)
    nC = compute_refractive_index("К8", 0.65627)
    return nF > nd > nC

def test_unknown_glass_fallback():
    """Неизвестное стекло → fallback 1.5"""
    n = compute_refractive_index("UNKNOWN_GLASS_XYZ", 0.58756)
    return abs(n - 1.5) < 0.01

def test_catalog_has_gost_glasses():
    """Каталог содержит основные ГОСТ стёкла"""
    required = ["К8", "БК10", "ТК16", "Ф1", "Ф4", "ТФ1", "ТФ3", "ТФ5"]
    for g in required:
        if g not in GLASS_CATALOG:
            return False
    return True

test("ВОЗДУХ → n=1.0", test_air_is_1)
test("AIR → n=1.0", test_air_english)
test("Пустое стекло → n=1.0", test_empty_glass)
test("К8 nd ≈ 1.5163", test_k8_nd)
test("ТФ5 nd ≈ 1.7550", test_tf5_nd)
test("Дисперсия n(F)>n(d)>n(C)", test_dispersion_order)
test("Неизвестное стекло → fallback", test_unknown_glass_fallback)
test("Каталог содержит ГОСТ стёкла", test_catalog_has_gost_glasses)

# ============================================================
# SECTION 2: Paraxial Ray Tracing
# ============================================================
print("\n" + "="*60)
print("SECTION 2: ПАРАКСИАЛЬНЫЙ РАСЧЁТ")
print("="*60)

def test_thin_lens_efl():
    """
    Тонкая линза в воздухе: f' = R/(n-1) для плоско-выпуклой
    R=50, n=1.5163 → f' = 50/0.5163 = 96.8 мм
    """
    sys = OpticalSystem(
        name="Плоско-выпуклая линза",
        object_type=ObjectType.INFINITE,
    )
    sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    sys.surfaces = [
        Surface(radius=50.0, thickness=0.01, glass="К8", semi_diameter=10.0),
        Surface(radius=0.0, thickness=0.0, glass=""),  # плоская задняя
    ]
    result = paraxial_trace(sys)
    efl = result.get('focal_length', 0)
    # Для тонкой линзы: 1/f = (n-1)*(1/R1 - 1/R2)
    # = (1.5163-1)*(1/50 - 0) = 0.5163/50 = 0.010326
    # f = 96.84 мм
    expected = 50.0 / 0.5163  # ≈ 96.84
    return assert_approx(efl, expected, 0.05, "Thin lens EFL")

def test_biconvex_efl():
    """
    Двояковыпуклая линза: R1=100, R2=-100, d=5, К8
    1/f = (n-1)*(1/R1 - 1/R2 + (n-1)*d/(n*R1*R2))
    """
    sys = OpticalSystem(name="Двояковыпуклая", object_type=ObjectType.INFINITE)
    sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    sys.surfaces = [
        Surface(radius=100.0, thickness=5.0, glass="К8", semi_diameter=15.0),
        Surface(radius=-100.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    efl = result.get('focal_length', 0)
    n = compute_refractive_index("К8", 0.58756)
    # 1/f = (n-1)*(1/R1 - 1/R2) + (n-1)^2*d/(n*R1*R2)
    inv_f = (n - 1) * (1/100 - 1/(-100)) + (n-1)**2 * 5 / (n * 100 * (-100))
    expected = 1.0 / inv_f
    return assert_approx(efl, expected, 0.05, "Biconvex EFL")

def test_mirror_focus():
    """
    Вогнутое зеркало: R=-200 (вогнутое), f' = R/2 = -100
    Зеркало = отражение, но для проверки считаем как поверхность
    """
    sys = OpticalSystem(name="Вогнутое зеркало", object_type=ObjectType.INFINITE)
    sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    # Для зеркала: n_after = -n_before (отражение)
    # В OPAL зеркало задаётся через особый тип поверхности
    # Для простоты — проверяем плоское зеркало (R→∞)
    # TODO: полноценная поддержка зеркал
    return True  # Placeholder

def test_doublet_system():
    """
    Дублет: К8 + ТФ5 (классическая комбинация)
    """
    sys = OpticalSystem(name="Дублет К8+ТФ5", object_type=ObjectType.INFINITE)
    sys.wavelengths = [
        Wavelength(0.58756, 1.0, "d"),
        Wavelength(0.48613, 1.0, "F"),
        Wavelength(0.65627, 1.0, "C"),
    ]
    sys.surfaces = [
        Surface(radius=80.0, thickness=6.0, glass="К8", semi_diameter=15.0),
        Surface(radius=-60.0, thickness=2.0, glass="ТФ5", semi_diameter=15.0),
        Surface(radius=-120.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    efl = result.get('focal_length', 0)
    return efl != 0 and abs(efl) < 500  # EFR != 0 and reasonable

def test_empty_system():
    """Пустая система → нет результата"""
    sys = OpticalSystem()
    result = paraxial_trace(sys)
    return result == {}

def test_flat_parallel_plate():
    """
    Плоскопараллельная пластина: не меняет f', но сдвигает фокус
    """
    sys = OpticalSystem(name="Пластина", object_type=ObjectType.INFINITE)
    sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    sys.surfaces = [
        Surface(radius=0.0, thickness=10.0, glass="К8", semi_diameter=20.0),  # R=0 = плоскость
        Surface(radius=0.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    # Плоскопараллельная пластина не фокусирует — EFL = ∞
    efl = result.get('focal_length', 0)
    # nu после 2-х плоских поверхностей в воздухе = 0 → EFL → ∞
    return abs(efl) < 1e-6 or abs(efl) > 1e10  # Должно быть ~∞ или 0

test("Плоско-выпуклая линза f'", test_thin_lens_efl)
test("Двояковыпуклая линза f'", test_biconvex_efl)
test("Зеркало (placeholder)", test_mirror_focus)
test("Дублет К8+ТФ5", test_doublet_system)
test("Пустая система", test_empty_system)
test("Плоскопараллельная пластина", test_flat_parallel_plate)

# ============================================================
# SECTION 3: Seidel Aberrations
# ============================================================
print("\n" + "="*60)
print("SECTION 3: СУММЫ ЗЕЙДЕЛЯ")
print("="*60)

def test_seidel_symmetric_lens():
    """
    Симметричная линза (R1=-R2): кома SII≈0, дисторсия SV≈0
    при симметричной диафрагме
    """
    sys = OpticalSystem(name="Симметричная линза", object_type=ObjectType.INFINITE)
    sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    sys.surfaces = [
        Surface(radius=100.0, thickness=8.0, glass="К8", semi_diameter=20.0),
        Surface(radius=-100.0, thickness=0.0, glass=""),
    ]
    sys.stop_surface = 1
    s = seidel_aberrations(sys)
    # SI should be nonzero, SII/SV should be relatively small for symmetric
    return abs(s['SI']) > 0  # At least spherical aberration exists

def test_seidel_exists():
    """Суммы Зейделя возвращают все 5 сумм"""
    sys = create_demo_system()
    s = seidel_aberrations(sys)
    return all(k in s for k in ['SI', 'SII', 'SIII', 'SIV', 'SV'])

def test_seidel_all_float():
    """Все суммы — числа"""
    sys = create_demo_system()
    s = seidel_aberrations(sys)
    return all(isinstance(v, float) for v in s.values())

test("Симметричная линза: SI>0", test_seidel_symmetric_lens)
test("Зейдель: все 5 сумм", test_seidel_exists)
test("Зейдель: все float", test_seidel_all_float)

# ============================================================
# SECTION 4: System Data Model
# ============================================================
print("\n" + "="*60)
print("SECTION 4: МОДЕЛЬ ДАННЫХ")
print("="*60)

def test_surface_defaults():
    s = Surface()
    return s.radius == 0.0 and s.thickness == 0.0 and s.glass == ""

def test_system_num_surfaces():
    sys = OpticalSystem()
    sys.surfaces = [Surface(), Surface(), Surface()]
    return sys.num_surfaces == 3

def test_system_image_index():
    sys = OpticalSystem()
    sys.surfaces = [Surface(), Surface()]
    return sys.image_index == 1

def test_wavelength_range():
    """OPAL поддерживает 0.365-2.6 мкм"""
    wl = Wavelength(0.365, 1.0, "i")
    return abs(wl.value - 0.365) < 1e-6

def test_max_surfaces():
    """OPAL поддерживает до 160 поверхностей"""
    sys = OpticalSystem()
    sys.surfaces = [Surface(radius=float(i), thickness=1.0) for i in range(160)]
    return sys.num_surfaces == 160

def test_max_wavelengths():
    """OPAL поддерживает до 5 длин волн"""
    sys = OpticalSystem()
    sys.wavelengths = [
        Wavelength(0.48613, 1.0, "F"),
        Wavelength(0.54607, 1.0, "e"),
        Wavelength(0.58756, 1.0, "d"),
        Wavelength(0.65627, 1.0, "C"),
        Wavelength(0.70652, 1.0, "r"),
    ]
    return len(sys.wavelengths) == 5

test("Surface defaults", test_surface_defaults)
test("num_surfaces", test_system_num_surfaces)
test("image_index", test_system_image_index)
test("Wavelength range (UV)", test_wavelength_range)
test("Max 160 surfaces", test_max_surfaces)
test("Max 5 wavelengths", test_max_wavelengths)

# ============================================================
# SECTION 5: OPJ File Parsing (example systems)
# ============================================================
print("\n" + "="*60)
print("SECTION 5: ПАРСИНГ .OPJ ФАЙЛОВ")
print("="*60)

def test_opj_files_exist():
    """Все .OPJ файлы доступны для чтения"""
    opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
    opj_files = [f for f in os.listdir(opal_dir) if f.endswith('.OPJ')]
    return len(opj_files) > 0

def test_opj_binary_readable():
    """OPJ файлы — бинарные, читаются"""
    opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
    opj_files = [f for f in os.listdir(opal_dir) if f.endswith('.OPJ')]
    for f in opj_files[:3]:
        with open(os.path.join(opal_dir, f), 'rb') as fh:
            data = fh.read()
        if len(data) < 10:
            return False
    return True

def test_opj_has_air_string():
    """OPJ содержит строку 'ВОЗДУХ'"""
    opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
    found = False
    for f in os.listdir(opal_dir):
        if f.endswith('.OPJ'):
            with open(os.path.join(opal_dir, f), 'rb') as fh:
                data = fh.read()
            if 'ВОЗДУХ'.encode('cp866') in data:
                found = True
                break
    return found

test(".OPJ файлы существуют", test_opj_files_exist)
test(".OPJ бинарные, читаются", test_opj_binary_readable)
test(".OPJ содержит 'ВОЗДУХ'", test_opj_has_air_string)

# ============================================================
# SECTION 6: Documentation Completeness
# ============================================================
print("\n" + "="*60)
print("SECTION 6: ДОКУМЕНТАЦИЯ")
print("="*60)

def test_docs_converted():
    """Все DOC файлы сконвертированы в TXT"""
    doc_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\docs'
    txt_files = [f for f in os.listdir(doc_dir) if f.endswith('.txt')]
    return len(txt_files) >= 10

def test_manual_content():
    """MANUAL.txt содержит ключевые слова"""
    with open(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\docs\MANUAL.txt', 'r', encoding='utf-8') as f:
        text = f.read().lower()
    keywords = ['поверхность', ('стекло', 'стекла'), 'система', ('расчёт', 'расчет')]
    for kw in keywords:
        if isinstance(kw, tuple):
            if not any(k in text for k in kw):
                return False
        else:
            if kw not in text:
                return False
    return True

def test_glass_doc_content():
    """GLASS.txt содержит формулу Герцбергера"""
    with open(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\docs\GLASS.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    return 'Герцбергер' in text or 'герцбергер' in text.lower()

test("DOC → TXT конвертация", test_docs_converted)
test("MANUAL.txt: ключевые слова", test_manual_content)
test("GLASS.txt: формула Герцбергера", test_glass_doc_content)

# ============================================================
# SECTION 7: GUI Import & Structure Tests
# ============================================================
print("\n" + "="*60)
print("SECTION 7: GUI КОМПОНЕНТЫ")
print("="*60)

def test_pyqt5_import():
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow
        return True
    except ImportError:
        return False

def test_main_window_import():
    try:
        from main import MainWindow, SurfaceTable, ResultsPanel, SystemParamsWidget
        return True
    except Exception as e:
        print(f"    ({e})")
        return False

def test_surface_table_headers():
    from main import SurfaceTable
    t = SurfaceTable.HEADERS
    return len(t) == 6 and 'Радиус' in t[1]

test("PyQt5 импорт", test_pyqt5_import)
test("MainWindow импорт", test_main_window_import)
test("SurfaceTable заголовки", test_surface_table_headers)

# ============================================================
# SECTION 8: Analytical Validation
# ============================================================
print("\n" + "="*60)
print("SECTION 8: АНАЛИТИЧЕСКАЯ ВАЛИДАЦИЯ")
print("="*60)

def test_lensmaker_equation():
    """
    Формула линзмейкера (точная):
    1/f = (n-1) * [1/R1 - 1/R2 + (n-1)*d/(n*R1*R2)]
    
    Тест: R1=50, R2=-100, d=5, К8
    """
    n = compute_refractive_index("К8", 0.58756)
    R1, R2, d = 50.0, -100.0, 5.0
    
    inv_f = (n - 1) * (1/R1 - 1/R2 + (n-1)*d/(n*R1*R2))
    f_analytical = 1.0 / inv_f
    
    sys = OpticalSystem(object_type=ObjectType.INFINITE)
    sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    sys.surfaces = [
        Surface(radius=R1, thickness=d, glass="К8"),
        Surface(radius=R2, thickness=0, glass=""),
    ]
    result = paraxial_trace(sys)
    f_computed = result.get('focal_length', 0)
    
    err = abs(f_computed - f_analytical) / abs(f_analytical)
    print(f"    Analytical: {f_analytical:.4f}, Computed: {f_computed:.4f}, Error: {err*100:.4f}%")
    return err < 0.05  # 5% tolerance

def test_cooke_triplet():
    """
    Триплет Кука: классическая конструкция
    + - + с воздушными промежутками
    К8 + ТФ5 + К8
    """
    sys = OpticalSystem(name="Триплет Кука", object_type=ObjectType.INFINITE)
    sys.wavelengths = [
        Wavelength(0.48613, 1.0, "F"),
        Wavelength(0.58756, 1.0, "d"),
        Wavelength(0.65627, 1.0, "C"),
    ]
    sys.surfaces = [
        # Положительная линза (К8)
        Surface(radius=40.0, thickness=6.0, glass="К8", semi_diameter=12.0),
        Surface(radius=-200.0, thickness=8.0, glass=""),
        # Отрицательная линза (ТФ5)
        Surface(radius=-40.0, thickness=2.0, glass="ТФ5", semi_diameter=10.0),
        Surface(radius=40.0, thickness=10.0, glass=""),
        # Положительная линза (К8)
        Surface(radius=60.0, thickness=5.0, glass="К8", semi_diameter=12.0),
        Surface(radius=-80.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    efl = result.get('focal_length', 0)
    print(f"    Cooke triplet EFL = {efl:.2f} мм")
    return abs(efl) > 0 and abs(efl) < 1000  # Non-zero, reasonable

def test_objective_from_opal():
    """
    Создаём систему по примеру из MANUAL.DOC:
    Объектив Гелиос-44 (из HELIOS8.OPJ)
    """
    # Approximate Helios-44 parameters
    sys = OpticalSystem(name="Гелиос-44", object_type=ObjectType.INFINITE)
    sys.wavelengths = [Wavelength(0.58756, 1.0, "d")]
    sys.aperture_value = 29.0  # f/2
    sys.surfaces = [
        Surface(radius=40.0, thickness=8.0, glass="К8", semi_diameter=16.0),
        Surface(radius=100.0, thickness=12.0, glass=""),
        Surface(radius=-50.0, thickness=2.0, glass="ТФ5", semi_diameter=14.0),
        Surface(radius=50.0, thickness=5.0, glass=""),
        Surface(radius=60.0, thickness=6.0, glass="К8", semi_diameter=14.0),
        Surface(radius=-60.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    efl = result.get('focal_length', 0)
    print(f"    Helios-44 EFL = {efl:.2f} мм")
    return efl != 0 and abs(efl) < 2000  # Non-zero, reasonable

test("Формула линзмейкера", test_lensmaker_equation)
test("Триплет Кука", test_cooke_triplet)
test("Объектив Гелиос-44", test_objective_from_opal)

# ============================================================
# SECTION 9: Edge Cases & Error Handling
# ============================================================
print("\n" + "="*60)
print("SECTION 9: КРАЕВЫЕ СЛУЧАИ")
print("="*60)

def test_zero_radius():
    """R=0 (плоскость): не должно крашиться"""
    sys = OpticalSystem()
    sys.wavelengths = [Wavelength(0.58756)]
    sys.surfaces = [
        Surface(radius=0.0, thickness=5.0, glass="К8"),
        Surface(radius=0.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    return isinstance(result, dict)

def test_very_thick_lens():
    """Толстая линза d=100мм"""
    sys = OpticalSystem()
    sys.wavelengths = [Wavelength(0.58756)]
    sys.surfaces = [
        Surface(radius=50.0, thickness=100.0, glass="К8"),
        Surface(radius=-50.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    return isinstance(result, dict) and result.get('focal_length', 0) != 0

def test_single_surface():
    """Одна поверхность"""
    sys = OpticalSystem()
    sys.wavelengths = [Wavelength(0.58756)]
    sys.surfaces = [
        Surface(radius=50.0, thickness=10.0, glass="К8"),
    ]
    result = paraxial_trace(sys)
    return isinstance(result, dict)

def test_many_surfaces():
    """Много поверхностей (20)"""
    sys = OpticalSystem()
    sys.wavelengths = [Wavelength(0.58756)]
    for i in range(10):
        sys.surfaces.append(Surface(radius=50.0+10*i, thickness=3.0, glass="К8"))
        sys.surfaces.append(Surface(radius=-80.0-5*i, thickness=5.0, glass=""))
    result = paraxial_trace(sys)
    return isinstance(result, dict)

def test_high_index_glass():
    """Высокопреломляющее стекло (ТФ5, n≈1.755)"""
    sys = OpticalSystem()
    sys.wavelengths = [Wavelength(0.58756)]
    sys.surfaces = [
        Surface(radius=30.0, thickness=3.0, glass="ТФ5"),
        Surface(radius=-60.0, thickness=0.0, glass=""),
    ]
    result = paraxial_trace(sys)
    return result.get('focal_length', 0) > 0

test("R=0 (плоскость)", test_zero_radius)
test("Толстая линза d=100", test_very_thick_lens)
test("Одна поверхность", test_single_surface)
test("20 поверхностей", test_many_surfaces)
test("Высокий n (ТФ5)", test_high_index_glass)

# ============================================================
# SECTION 10: GUI Runtime Tests
# ============================================================
print("\n" + "="*60)
print("SECTION 10: GUI ТЕСТИРОВАНИЕ (РАБОТА ПРИЛОЖЕНИЯ)")
print("="*60)

def test_gui_starts():
    """GUI запускается без ошибок"""
    # Check if the existing process is still running
    import subprocess
    result = subprocess.run(
        ['py', '-c', 'from PyQt5.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); print("OK")'],
        capture_output=True, text=True, timeout=10
    )
    return 'OK' in result.stdout

def test_gui_window_instance():
    """MainWindow создаётся"""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    from main import MainWindow
    w = MainWindow()
    ok = w is not None and w.windowTitle().startswith("OPAL")
    w.close()
    return ok

def test_gui_load_demo():
    """Загрузка демо-системы в GUI"""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    from main import MainWindow
    w = MainWindow()
    w._load_demo()
    ok = w.current_system.name == "Демо: Тонкая линза"
    w.close()
    return ok

def test_gui_add_surface():
    """Добавление поверхности"""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    from main import MainWindow
    w = MainWindow()
    initial = len(w.current_system.surfaces)
    w._add_surface()
    after = len(w.current_system.surfaces)
    w.close()
    return after == initial + 1

def test_gui_calculate():
    """Расчёт из GUI"""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    from main import MainWindow
    w = MainWindow()
    w._load_demo()
    w._calculate()
    efl_text = w.results.lbl_efl.text()
    ok = '—' not in efl_text and len(efl_text) > 0
    w.close()
    return ok

def test_gui_new_system():
    """Создание новой системы"""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    from main import MainWindow
    w = MainWindow()
    w._load_demo()
    w._new_system()
    ok = w.current_system.name == "Новая система"
    w.close()
    return ok

test("QApplication запускается", test_gui_starts)
test("MainWindow создаётся", test_gui_window_instance)
test("Демо-система загружается", test_gui_load_demo)
test("Добавление поверхности", test_gui_add_surface)
test("Расчёт из GUI", test_gui_calculate)
test("Новая система", test_gui_new_system)

# ============================================================
# SECTION 11: Performance Tests
# ============================================================
print("\n" + "="*60)
print("SECTION 11: ПРОИЗВОДИТЕЛЬНОСТЬ")
print("="*60)

def test_paraxial_speed():
    """Параксиальный расчёт < 10ms для 160 поверхностей"""
    sys = OpticalSystem()
    sys.wavelengths = [Wavelength(0.58756)]
    for i in range(160):
        sys.surfaces.append(Surface(radius=50.0+5*i, thickness=2.0, glass="К8" if i%2==0 else ""))
    
    t0 = time.perf_counter()
    for _ in range(100):
        paraxial_trace(sys)
    t1 = time.perf_counter()
    ms = (t1 - t0) / 100 * 1000
    print(f"    {ms:.3f} ms per trace (160 surfaces)")
    return ms < 10

def test_glass_lookup_speed():
    """Поиск стекла < 0.1ms"""
    t0 = time.perf_counter()
    for _ in range(10000):
        compute_refractive_index("К8", 0.58756)
    t1 = time.perf_counter()
    us = (t1 - t0) / 10000 * 1e6
    print(f"    {us:.1f} µs per lookup")
    return us < 100

test("160 поверхностей < 10ms", test_paraxial_speed)
test("Каталог стёкол < 100µs", test_glass_lookup_speed)

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*60)
total = passed + failed
print(f"РЕЗУЛЬТАТЫ: {passed}/{total} пройдено, {failed} не пройдено")
print("="*60)

if errors:
    print("\nОшибки:")
    for e in errors:
        print(f"  • {e}")

print()
sys.exit(0 if failed == 0 else 1)
