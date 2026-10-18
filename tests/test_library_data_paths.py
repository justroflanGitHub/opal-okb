"""Регресс-тест бага библиотеки в exe (2026-10-18, v1.24.5).

В PyInstaller-бандле extracted/opal_okb не было в datas, а BASE_DIR
резолвился по __file__ в _MEIPASS — категории «OPAL системы» и
«LBO библиотеки» оставались пустыми, развернуть было нечего.

Фикс: _resolve_base_dir() (frozen → рядом с exe → _MEIPASS → dev) +
datas в spec.
"""
import os
import sys

from catalog.library import LBO_DIR, OPJ_DIR, _resolve_base_dir, build_library


def test_base_dir_resolves_to_repo_with_data():
    base = _resolve_base_dir()
    assert os.path.isdir(os.path.join(base, 'extracted', 'opal_okb'))


def test_frozen_prefers_exe_dir(tmp_path, monkeypatch):
    fake_exe_dir = str(tmp_path)
    (tmp_path / 'extracted' / 'opal_okb').mkdir(parents=True)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'OPAL-PC.exe'), raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path / '_mei'), raising=False)
    assert _resolve_base_dir() == fake_exe_dir


def test_frozen_falls_back_to_meipass(tmp_path, monkeypatch):
    (tmp_path / '_mei' / 'extracted' / 'opal_okb').mkdir(parents=True)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'OPAL-PC.exe'), raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path / '_mei'), raising=False)
    assert _resolve_base_dir() == str(tmp_path / '_mei')


def test_library_categories_nonempty():
    lib = build_library()
    assert len(lib['OPAL системы (.OPJ)']) > 50
    assert len(lib['LBO библиотеки']) >= 10
    assert os.path.isdir(LBO_DIR) and os.path.isdir(OPJ_DIR)
