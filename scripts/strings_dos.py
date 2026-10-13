# -*- coding: utf-8 -*-
"""Извлечение строк из DOS EXE (Turbo Pascal) — разведка перед Ghidra."""
import sys, re

def strings(path, minlen=5, encoding='cp866'):
    data = open(path, 'rb').read()
    # ASCII runs
    out = []
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, data):
        try:
            out.append((m.start(), m.group().decode('ascii')))
        except Exception:
            pass
    return out

path = sys.argv[1]
minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 6
items = strings(path, minlen)
print(f"TOTAL_ASCII_STRINGS: {len(items)}")
for off, s in items:
    print(f"{off:08x}  {s}")
