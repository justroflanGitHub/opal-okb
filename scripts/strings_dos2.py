# -*- coding: utf-8 -*-
"""Извлечение строк из DOS EXE: ASCII + CP866 (кириллица)."""
import sys, re

CP866_HI = re.compile(rb'(?:[\x80-\xAF\xE0-\xEF][\x20-\xEF]{%d,})' % 4)

def extract(path, minlen=6):
    data = open(path, 'rb').read()
    res = []
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, data):
        res.append((m.start(), 'A', m.group().decode('ascii')))
    for m in CP866_HI.finditer(data):
        try:
            t = m.group().decode('cp866')
            if sum(1 for c in t if '\u0410' <= c <= '\u044f') >= 4:
                res.append((m.start(), 'R', t))
        except Exception:
            pass
    res.sort()
    return res

if __name__ == '__main__':
    path = sys.argv[1]
    minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    for off, kind, s in extract(path, minlen):
        print(f"{off:08x} [{kind}] {s}")
