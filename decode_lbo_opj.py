"""Compatibility shim. Real code in fileio/decode_lbo.py.

Re-exports everything so that existing imports like
``from decode_lbo_opj import decode_lbo_opj`` continue to work.
"""
from fileio.decode_lbo import *  # noqa: F401, F403
from fileio.decode_lbo import (
    OPAL_WL,
    decode_lbo_opj,
)
