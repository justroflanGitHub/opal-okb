# -*- coding: utf-8 -*-
"""TASK_OPAVA: полнообразовый скан CP866-строк OPAVA_unp.bin (>=5 симв., seg:off)."""
import re

img = open(r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPAVA_unp.bin", "rb").read()
out = open(r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\_opava_strings.txt", "w", encoding="utf-8")
pat = re.compile(rb"[\x20-\x7e\xa1\xa2\xa5\xaa\xaf\xb2\xb3\xb5\xbc-\xbe\xc0-\xff][\x20-\x7e\xa1\xa2\xa5\xaa\xaf\xb2\xb3\xb5\xbc-\xbe]{4,}")
cnt = 0
for m in pat.finditer(img):
    s = m.group()
    if len(set(s)) < 3:
        continue
    try:
        t = s.decode("cp866")
    except Exception:
        continue
    lin = m.start()
    seg, off = lin >> 4, lin & 15
    out.write("%06x %04x:%04x  %r\n" % (lin, seg, off, t))
    cnt += 1
out.close()
print("strings:", cnt)
