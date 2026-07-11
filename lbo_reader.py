"""Compatibility shim. Real code in fileio/lbo_io.py.

Re-exports everything so that existing imports like
``from lbo_reader import load_lbo`` continue to work.
"""
from fileio.lbo_io import *  # noqa: F401, F403
from fileio.lbo_io import (
    RECORD_MARKER,
    _find_records, load_lbo, load_lbo_fast,
    get_lbo_info, scan_lbo_directory,
)
