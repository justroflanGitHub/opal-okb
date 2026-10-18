# -*- coding: utf-8 -*-
"""TASK_EDGE2: скан остатков прод/попер/Tg' по всем системам банка."""
import io
import os
import sys
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis.golden_verify import compare_system

KEYS = ('прод (дптр)', 'прод (мм)', 'попер (гр.мнсек)', "Tg'*100 (H`ЗР)")

for nm in sys.argv[1:] or ['HELIOS8', 'OPAL3', 'PLIOPT', 'S_KOND1',
                           'US00KI02', '121', 'KURSOVIK']:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            r = compare_system(nm)
        except Exception as e:
            print('==', nm, 'ERR', repr(e))
            continue
    print('==', nm, r['counts'])
    for row in r['rows']:
        if row[1] in KEYS and row[4] is not None and row[2] != 0.0:
            print('   %-18s z%-5s банк=%-10s порт=%-10s d=%.2e %s'
                  % (row[1], row[2], row[3], row[4], row[5], row[7]))
