# -*- coding: utf-8 -*-
"""DOC (cp866) -> UTF-8 plain text for analysis reading."""
import sys, os

SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'extracted', 'opal_okb', 'DOC')
DST = r'C:\tmp_optdoc'
os.makedirs(DST, exist_ok=True)

for name in sys.argv[1:] or ['OPALOPT', 'OPAL', 'OPALANG', 'MANUAL']:
    data = open(os.path.join(SRC, name + '.DOC'), 'rb').read()
    txt = data.decode('cp866', errors='replace')
    out = os.path.join(DST, name + '.txt')
    open(out, 'w', encoding='utf-8').write(txt)
    print(name, len(data), 'bytes ->', txt.count('\n') + 1, 'lines ->', out)
