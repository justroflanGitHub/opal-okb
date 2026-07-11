"""Compatibility shim. Real code in catalog/library.py.

Re-exports everything so that
``from library import build_library`` continues to work.
"""
from catalog.library import *  # noqa: F401, F403
from catalog.library import (
    BASE_DIR, OPJ_DIR, LBO_DIR,
    _scan_opj_files, _scan_lbo_files,
    build_library, create_system_from_entry,
    expand_lbo,
)
