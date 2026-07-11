"""Compatibility shim. Real code in fileio/opj_io.py.

The writer has been merged with the reader into fileio/opj_io.py.
Re-exports save_opj so that ``from opj_writer import save_opj`` continues to work.
"""
from fileio.opj_io import save_opj
