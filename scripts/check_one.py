# -*- coding: utf-8 -*-
"""Проверка загрузки одной системы каталога по индексу (для субагентов-проверяющих).

Использование:
    py scripts/check_one.py 220          # только загрузка системы
Печатает: OK <surfaces> поверхностей | ERROR <текст ошибки>
Загрузка без трассировки — безопасна для зависающих систем.
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def main():
    idx = int(sys.argv[1])
    from scripts.render_catalog import build_all_entries
    entries = build_all_entries()
    e = entries[idx]
    idx_cat, idx_name, entry = e["category"], e["name"], e["entry"]
    try:
        from catalog.library import create_system_from_entry
        sys_obj = create_system_from_entry(entry)
        n = len(getattr(sys_obj, "surfaces", []) or [])
        if n == 0:
            print(f"ERROR: system '{idx_name}' loads but has 0 surfaces (empty system)")
        else:
            print(f"OK: '{idx_name}' ({idx_cat}) loaded, {n} surfaces")
    except Exception as e:
        print(f"ERROR: '{idx_name}' ({idx_cat}): {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
