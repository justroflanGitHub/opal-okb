# -*- coding: utf-8 -*-
"""TASK_OPAVA §данные: инвентаризация данных-сегментов OPAVA_unp.bin.

Карта сегментов — BuildOpava.java (§2 REVERSE_OPAVA.md): DATA_BANR 3CEE,
DATA_MENU 437B, DATA_FMT 48A1, DATA_VIEW 58B4, DGROUP 58DF + островки кода.
CP866-строки с адресами seg:off, word-таблицы, FORTRAN-форматы. Выход UTF-8.
"""
import re
import struct

IMG = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPAVA_unp.bin"
OUT = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\_opava_data.txt"

img = open(IMG, "rb").read()

RANGES = [
    ("DATA_BANR", 0x3CEE, 0x3CEE0, 0x3CF30),
    ("DATA_MENU", 0x437B, 0x437B0, 0x4389C),
    ("DATA_FMT", 0x48A1, 0x48A10, 0x49F05),
    ("DATA_VIEW", 0x58B4, 0x58B40, 0x58DF0),
    ("DGROUP", 0x58DF, 0x58DF0, 0x5E560),
]

out = open(OUT, "w", encoding="utf-8")

def segaddr(seg, lin):
    return "%04x:%04x" % (seg, lin - seg * 16)

for name, seg, lo, hi in RANGES:
    out.write("\n===== %s [%s..%s] =====\n" % (name, segaddr(seg, lo), segaddr(seg, hi - 1)))
    chunk = img[lo:hi]
    nz = [k for k, v in enumerate(chunk) if v]
    if not nz:
        out.write("(все нули — BSS)\n")
        continue
    out.write("ненулевые: %s..%s (%d из %d)\n\n--- строки CP866 (прогоны >=4) ---\n" % (
        segaddr(seg, lo + nz[0]), segaddr(seg, lo + nz[-1]), len(nz), len(chunk)))
    for m in re.finditer(rb"(?:[\x20-\x7e\x80-\xff\xa1\xa2\xa5\xaa\xaf\xb2\xb3\xb5\xbc-\xbe\xc0-\xff][\x20-\x7e\x80-\xff]{3,})", chunk):
        s = m.group()
        try:
            txt = s.decode("cp866")
        except Exception:
            continue
        out.write("%s  %r\n" % (segaddr(seg, lo + m.start()), txt))

    out.write("\n--- таблицы word (прогоны >=6 ненулевых LE-word < 0x6400) ---\n")
    i = 0
    n = len(chunk) // 2
    words = list(struct.unpack("<%dH" % n, chunk[: n * 2]))
    while i < n:
        if words[i] and words[i] < 0x6400:
            j = i
            while j < n and words[j] < 0x6400:
                if words[j] == 0 and (j - i) > 6:
                    break
                j += 1
            if j - i >= 6:
                vals = words[i:j][:16]
                out.write("%s  %d сл.: %s%s\n" % (
                    segaddr(seg, lo + i * 2), j - i,
                    " ".join("%04x" % v for v in vals), " ..." if j - i > 16 else ""))
            i = j
        else:
            i += 1

    out.write("\n--- FORTRAN-форматы (строки с '(' и полями) ---\n")
    for m in re.finditer(rb"[\x20-\x7e]{6,}", chunk):
        s = m.group().decode("ascii", "replace")
        if "(" in s and re.search(r"[iIfFeEgG aA]\d|'", s):
            out.write("%s  %s\n" % (segaddr(seg, lo + m.start()), s))

out.close()
print("written", OUT)
