# TODO: convert to pytest — uses custom runner
# -*- coding: utf-8 -*-
"""
Тесты для LBO reader.
Запуск: py tests\test_lbo.py
"""
import os
import sys
import tempfile
import struct
import io

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from lbo_reader import load_lbo, load_lbo_fast, get_lbo_info, scan_lbo_directory, _find_records
from opj_reader import load_opj

LBO_DIR = os.path.join(BASE_DIR, "extracted", "opal_okb", "Lib")
LENS_LBO = os.path.join(LBO_DIR, "LENS.LBO")


def test_lbo_file_exists():
    """LENS.LBO существует."""
    assert os.path.isfile(LENS_LBO), f"LENS.LBO not found at {LENS_LBO}"
    print("[PASS] test_lbo_file_exists")


def test_lens_lbo_size():
    """LENS.LBO имеет ожидаемый размер."""
    size = os.path.getsize(LENS_LBO)
    assert size == 80804, f"Expected 80804 bytes, got {size}"
    print("[PASS] test_lens_lbo_size")


def test_lens_lbo_record_count():
    """LENS.LBO содержит 116 записей."""
    with open(LENS_LBO, 'rb') as f:
        data = f.read()
    records = _find_records(data)
    assert len(records) == 116, f"Expected 116 records, got {len(records)}"
    print("[PASS] test_lens_lbo_record_count")


def test_load_lbo_returns_systems():
    """load_lbo возвращает список систем."""
    systems = load_lbo(LENS_LBO)
    assert len(systems) > 50, f"Expected >50 systems, got {len(systems)}"
    print(f"[PASS] test_load_lbo_returns_systems ({len(systems)} systems)")


def test_each_system_has_name():
    """Каждая система имеет имя."""
    systems = load_lbo(LENS_LBO)
    for i, s in enumerate(systems):
        assert 'name' in s, f"System {i} missing 'name'"
        assert s['name'], f"System {i} has empty name"
    print(f"[PASS] test_each_system_has_name ({len(systems)} systems checked)")


def test_each_system_has_description():
    """Каждая система имеет описание."""
    systems = load_lbo(LENS_LBO)
    for i, s in enumerate(systems):
        assert 'description' in s, f"System {i} missing 'description'"
    print(f"[PASS] test_each_system_has_description ({len(systems)} systems checked)")


def test_system_has_opj_data():
    """Каждая система содержит OPJ данные."""
    systems = load_lbo(LENS_LBO)
    for i, s in enumerate(systems):
        assert 'opj_data' in s, f"System {i} missing 'opj_data'"
        assert isinstance(s['opj_data'], bytes), f"System {i} opj_data not bytes"
        assert len(s['opj_data']) > 50, f"System {i} opj_data too small: {len(s['opj_data'])}"
    print(f"[PASS] test_system_has_opj_data ({len(systems)} systems checked)")


def test_system_has_optical_system():
    """Каждая система парсится в OpticalSystem."""
    systems = load_lbo(LENS_LBO)
    ok = 0
    for i, s in enumerate(systems):
        assert s['system'] is not None, f"System {i} has None OpticalSystem"
        sys_obj = s['system']
        assert hasattr(sys_obj, 'surfaces'), f"System {i} has no surfaces attr"
        assert len(sys_obj.surfaces) > 0, f"System {i} has 0 surfaces"
        ok += 1
    print(f"[PASS] test_system_has_optical_system ({ok}/{len(systems)} parsed OK)")


def test_first_system_name():
    """Первая система — Индустар-7."""
    systems = load_lbo(LENS_LBO)
    assert 'Индустар' in systems[0]['name'] or 'Industar' in systems[0]['name'], \
        f"First system name unexpected: {systems[0]['name']}"
    print(f"[PASS] test_first_system_name ({systems[0]['name'][:40]})")


def test_opj_data_valid_structure():
    """OPJ данные из LBO имеют валидную структуру."""
    systems = load_lbo(LENS_LBO)
    s = systems[0]
    opj = s['opj_data']
    
    # OPJ offset 0x0C-0x33 = name (40 bytes)
    name = opj[0x0C:0x34].decode('cp866', errors='replace').strip()
    assert len(name) > 0, "Name in OPJ data is empty"
    
    # OPJ offset 0x34 = num_surf
    num_surf = struct.unpack_from('<h', opj, 0x34)[0]
    assert 0 < num_surf <= 160, f"num_surf out of range: {num_surf}"
    
    print(f"[PASS] test_opj_data_valid_structure (name={name[:30]}, num_surf={num_surf})")


def test_load_lbo_fast():
    """load_lbo_fast возвращает системы без парсинга OpticalSystem."""
    systems = load_lbo_fast(LENS_LBO)
    assert len(systems) == 116, f"Expected 116, got {len(systems)}"
    for i, s in enumerate(systems):
        assert 'name' in s
        assert 'opj_data' in s
        assert 'system' not in s  # fast mode doesn't parse
    print(f"[PASS] test_load_lbo_fast ({len(systems)} systems)")


def test_get_lbo_info():
    """get_lbo_info возвращает корректную информацию."""
    info = get_lbo_info(LENS_LBO)
    assert info['name'] == 'LENS'
    assert info['num_systems'] == 116
    assert info['size'] == 80804
    print(f"[PASS] test_get_lbo_info")


def test_scan_lbo_directory():
    """scan_lbo_directory находит все .LBO файлы."""
    lbo_files = scan_lbo_directory(LBO_DIR)
    assert len(lbo_files) >= 10, f"Expected >=10 LBO files, got {len(lbo_files)}"
    
    names = [f['name'] for f in lbo_files]
    assert 'LENS' in names, "LENS not found"
    assert 'OCULAR' in names, "OCULAR not found"
    assert 'RUSSAR' in names, "RUSSAR not found"
    
    total = sum(f['num_systems'] for f in lbo_files)
    assert total > 500, f"Expected >500 total systems, got {total}"
    print(f"[PASS] test_scan_lbo_directory ({len(lbo_files)} files, {total} total systems)")


def test_all_lbo_files_load():
    """Все .LBO файлы загружаются без ошибок."""
    lbo_files = scan_lbo_directory(LBO_DIR)
    total_systems = 0
    for info in lbo_files:
        systems = load_lbo_fast(info['path'])
        assert len(systems) == info['num_systems'], \
            f"{info['name']}: expected {info['num_systems']}, got {len(systems)}"
        total_systems += len(systems)
    print(f"[PASS] test_all_lbo_files_load ({len(lbo_files)} files, {total_systems} systems)")


def test_opj_from_lbo_parses_as_standalone():
    """OPJ данные из LBO парсятся так же как standalone OPJ."""
    systems = load_lbo(LENS_LBO)
    
    # Take first system, write OPJ to temp file, load it
    s = systems[0]
    tmpfd, tmppath = tempfile.mkstemp(suffix='.OPJ')
    try:
        os.write(tmpfd, s['opj_data'])
        os.close(tmpfd)
        sys_obj, info = load_opj(tmppath)
        assert sys_obj is not None
        assert len(sys_obj.surfaces) > 0
        # Should match the system parsed by load_lbo
        assert len(sys_obj.surfaces) == len(s['system'].surfaces)
    finally:
        os.unlink(tmppath)
    
    print(f"[PASS] test_opj_from_lbo_parses_as_standalone")


def test_library_integration():
    """Интеграция с library.py — LBO в build_library()."""
    from library import build_library, expand_lbo, create_system_from_entry
    
    lib = build_library()
    assert "LBO библиотеки" in lib
    
    lbo_entries = lib["LBO библиотеки"]
    assert len(lbo_entries) >= 10, f"Expected >=10 LBO entries, got {len(lbo_entries)}"
    
    # Find LENS library
    lens_entry = None
    for e in lbo_entries:
        if e.get("lbo_name") == "LENS":
            lens_entry = e
            break
    assert lens_entry is not None, "LENS library not found in build_library()"
    
    # Expand it
    expanded = expand_lbo(lens_entry["lbo_path"])
    assert len(expanded) == 116, f"Expected 116 systems, got {len(expanded)}"
    
    # Load first system
    sys_obj = create_system_from_entry(expanded[0])
    assert sys_obj is not None
    assert len(sys_obj.surfaces) > 0
    
    print(f"[PASS] test_library_integration")


def test_record_header_structure():
    """Структура заголовка записи: marker(2) + filename(12) + meta(4) + opj_size(4) = 22 bytes."""
    with open(LENS_LBO, 'rb') as f:
        data = f.read()
    
    records = _find_records(data)
    assert len(records) > 0
    
    for i, rec in enumerate(records[:5]):
        # Check marker
        marker = struct.unpack_from('<H', data, rec['record_offset'])[0]
        assert marker == 0x000C, f"Record {i}: bad marker 0x{marker:04x}"
        
        # Check filename
        fname = data[rec['record_offset']+2:rec['record_offset']+14].decode('ascii', errors='replace').strip()
        assert '.OPJ' in fname.upper(), f"Record {i}: filename missing .OPJ: {fname}"
        
        # Check opj_size matches
        opj_size = struct.unpack_from('<I', data, rec['record_offset']+18)[0]
        assert opj_size == rec['opj_size'], f"Record {i}: opj_size mismatch"
        
        # Check next record offset
        if i + 1 < len(records):
            expected_next = rec['opj_offset'] + rec['opj_size']
            actual_next = records[i+1]['record_offset']
            assert expected_next == actual_next, \
                f"Record {i}: expected next at {expected_next}, got {actual_next}"
    
    print(f"[PASS] test_record_header_structure (5 records checked)")


def run_all():
    """Run all tests."""
    tests = [
        test_lbo_file_exists,
        test_lens_lbo_size,
        test_lens_lbo_record_count,
        test_load_lbo_returns_systems,
        test_each_system_has_name,
        test_each_system_has_description,
        test_system_has_opj_data,
        test_system_has_optical_system,
        test_first_system_name,
        test_opj_data_valid_structure,
        test_load_lbo_fast,
        test_get_lbo_info,
        test_scan_lbo_directory,
        test_all_lbo_files_load,
        test_opj_from_lbo_parses_as_standalone,
        test_library_integration,
        test_record_header_structure,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"LBO Tests: {passed}/{passed + failed} passed")
    if failed:
        print(f"FAILED: {failed}")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
