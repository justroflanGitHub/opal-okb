# -*- coding: utf-8 -*-
"""Тесты для LBO reader."""
import os
import struct
import tempfile
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
LBO_DIR = BASE_DIR / "extracted" / "opal_okb" / "Lib"
LENS_LBO = LBO_DIR / "LENS.LBO"


class TestLBOReader:
    def test_lbo_file_exists(self):
        """LENS.LBO существует."""
        assert LENS_LBO.is_file(), f"LENS.LBO not found at {LENS_LBO}"

    def test_lens_lbo_size(self):
        """LENS.LBO имеет ожидаемый размер."""
        size = LENS_LBO.stat().st_size
        assert size == 80804, f"Expected 80804 bytes, got {size}"

    def test_lens_lbo_record_count(self):
        """LENS.LBO содержит 116 записей."""
        from lbo_reader import _find_records
        with open(LENS_LBO, 'rb') as f:
            data = f.read()
        records = _find_records(data)
        assert len(records) == 116, f"Expected 116 records, got {len(records)}"

    def test_load_lbo_returns_systems(self):
        """load_lbo возвращает список систем."""
        from lbo_reader import load_lbo
        systems = load_lbo(str(LENS_LBO))
        assert len(systems) > 50, f"Expected >50 systems, got {len(systems)}"

    def test_each_system_has_name(self):
        """Каждая система имеет имя."""
        from lbo_reader import load_lbo
        systems = load_lbo(str(LENS_LBO))
        for i, s in enumerate(systems):
            assert 'name' in s, f"System {i} missing 'name'"
            assert s['name'], f"System {i} has empty name"

    def test_each_system_has_description(self):
        """Каждая система имеет описание."""
        from lbo_reader import load_lbo
        systems = load_lbo(str(LENS_LBO))
        for i, s in enumerate(systems):
            assert 'description' in s, f"System {i} missing 'description'"

    def test_system_has_opj_data(self):
        """Каждая система содержит OPJ данные."""
        from lbo_reader import load_lbo
        systems = load_lbo(str(LENS_LBO))
        for i, s in enumerate(systems):
            assert 'opj_data' in s, f"System {i} missing 'opj_data'"
            assert isinstance(s['opj_data'], bytes), f"System {i} opj_data not bytes"
            assert len(s['opj_data']) > 50, f"System {i} opj_data too small: {len(s['opj_data'])}"

    def test_system_has_optical_system(self):
        """Каждая система парсится в OpticalSystem."""
        from lbo_reader import load_lbo
        systems = load_lbo(str(LENS_LBO))
        for i, s in enumerate(systems):
            assert s['system'] is not None, f"System {i} has None OpticalSystem"
            sys_obj = s['system']
            assert hasattr(sys_obj, 'surfaces'), f"System {i} has no surfaces attr"
            assert len(sys_obj.surfaces) > 0, f"System {i} has 0 surfaces"

    def test_first_system_name(self):
        """Первая система — Индустар."""
        from lbo_reader import load_lbo
        systems = load_lbo(str(LENS_LBO))
        assert 'Индустар' in systems[0]['name'] or 'Industar' in systems[0]['name'], \
            f"First system name unexpected: {systems[0]['name']}"

    def test_opj_data_valid_structure(self):
        """OPJ данные из LBO имеют валидную структуру."""
        from lbo_reader import load_lbo
        systems = load_lbo(str(LENS_LBO))
        s = systems[0]
        opj = s['opj_data']
        name = opj[0x0C:0x34].decode('cp866', errors='replace').strip()
        assert len(name) > 0, "Name in OPJ data is empty"
        num_surf = struct.unpack_from('<h', opj, 0x34)[0]
        assert 0 < num_surf <= 160, f"num_surf out of range: {num_surf}"

    def test_load_lbo_fast(self):
        """load_lbo_fast возвращает системы без парсинга OpticalSystem."""
        from lbo_reader import load_lbo_fast
        systems = load_lbo_fast(str(LENS_LBO))
        assert len(systems) == 116, f"Expected 116, got {len(systems)}"
        for i, s in enumerate(systems):
            assert 'name' in s
            assert 'opj_data' in s
            assert 'system' not in s  # fast mode doesn't parse

    def test_get_lbo_info(self):
        """get_lbo_info возвращает корректную информацию."""
        from lbo_reader import get_lbo_info
        info = get_lbo_info(str(LENS_LBO))
        assert info['name'] == 'LENS'
        assert info['num_systems'] == 116
        assert info['size'] == 80804

    def test_scan_lbo_directory(self):
        """scan_lbo_directory находит все .LBO файлы."""
        from lbo_reader import scan_lbo_directory
        lbo_files = scan_lbo_directory(str(LBO_DIR))
        assert len(lbo_files) >= 10, f"Expected >=10 LBO files, got {len(lbo_files)}"
        names = [f['name'] for f in lbo_files]
        assert 'LENS' in names, "LENS not found"
        assert 'OCULAR' in names, "OCULAR not found"
        assert 'RUSSAR' in names, "RUSSAR not found"
        total = sum(f['num_systems'] for f in lbo_files)
        assert total > 500, f"Expected >500 total systems, got {total}"

    def test_all_lbo_files_load(self):
        """Все .LBO файлы загружаются без ошибок."""
        from lbo_reader import scan_lbo_directory, load_lbo_fast
        lbo_files = scan_lbo_directory(str(LBO_DIR))
        for info in lbo_files:
            systems = load_lbo_fast(info['path'])
            assert len(systems) == info['num_systems'], \
                f"{info['name']}: expected {info['num_systems']}, got {len(systems)}"

    def test_opj_from_lbo_parses_as_standalone(self):
        """OPJ данные из LBO парсятся так же как standalone OPJ."""
        from lbo_reader import load_lbo
        from opj_reader import load_opj
        systems = load_lbo(str(LENS_LBO))
        s = systems[0]
        tmpfd, tmppath = tempfile.mkstemp(suffix='.OPJ')
        try:
            os.write(tmpfd, s['opj_data'])
            os.close(tmpfd)
            sys_obj, info = load_opj(tmppath)
            assert sys_obj is not None
            assert len(sys_obj.surfaces) > 0
            assert len(sys_obj.surfaces) == len(s['system'].surfaces)
        finally:
            os.unlink(tmppath)

    def test_library_integration(self):
        """Интеграция с library.py — LBO в build_library()."""
        from library import build_library, expand_lbo, create_system_from_entry
        lib = build_library()
        assert "LBO библиотеки" in lib
        lbo_entries = lib["LBO библиотеки"]
        assert len(lbo_entries) >= 10, f"Expected >=10 LBO entries, got {len(lbo_entries)}"
        lens_entry = None
        for e in lbo_entries:
            if e.get("lbo_name") == "LENS":
                lens_entry = e
                break
        assert lens_entry is not None, "LENS library not found in build_library()"
        expanded = expand_lbo(lens_entry["lbo_path"])
        assert len(expanded) == 116, f"Expected 116 systems, got {len(expanded)}"
        sys_obj = create_system_from_entry(expanded[0])
        assert sys_obj is not None
        assert len(sys_obj.surfaces) > 0

    def test_record_header_structure(self):
        """Структура заголовка записи."""
        from lbo_reader import _find_records
        with open(LENS_LBO, 'rb') as f:
            data = f.read()
        records = _find_records(data)
        assert len(records) > 0
        for i, rec in enumerate(records[:5]):
            marker = struct.unpack_from('<H', data, rec['record_offset'])[0]
            assert marker == 0x000C, f"Record {i}: bad marker 0x{marker:04x}"
            fname = data[rec['record_offset'] + 2:rec['record_offset'] + 14].decode('ascii', errors='replace').strip()
            assert '.OPJ' in fname.upper(), f"Record {i}: filename missing .OPJ: {fname}"
            opj_size = struct.unpack_from('<I', data, rec['record_offset'] + 18)[0]
            assert opj_size == rec['opj_size'], f"Record {i}: opj_size mismatch"
            if i + 1 < len(records):
                expected_next = rec['opj_offset'] + rec['opj_size']
                actual_next = records[i + 1]['record_offset']
                assert expected_next == actual_next, \
                    f"Record {i}: expected next at {expected_next}, got {actual_next}"
