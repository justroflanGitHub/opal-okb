"""Compatibility shim. Real code in fileio/opj_io.py.

Re-exports everything so that existing imports like
``from opj_reader import load_opj`` continue to work.
"""
from fileio.opj_io import *  # noqa: F401, F403
from fileio.opj_io import (
    _read_glass_name, _find_glass_block, _find_surface_block,
    load_opj, load_all_opj, save_opj,
)
