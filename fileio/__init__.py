"""I/O layer — import/export for optical system files.

Modules:
    json_io:    Save/load OpticalSystem as .opal.json
    opj_io:     Read/write binary .OPJ files (OPAL-PC native format).
    lbo_io:     Read .LBO library files (collections of .OPJ entries).
    decode_lbo: Advanced LBO decoder with glass-index mapping.
    protocol:   Export analysis results to text protocol (.txt).

Note: Named ``fileio`` to avoid conflict with Python's built-in ``io`` module.
"""
