# -*- coding: utf-8 -*-
"""TASK_UNP §5: полная инвентаризация данных-сегментов OPALA_unp.bin.

Сегменты 0x506E / 0x52A6 / 0x52D4 (+ островки 0x46CA0, 0x4E772, 0x505E0, 0x52420):
CP866-строки с адресами seg:off, таблицы word, форматы FORTRAN. Выход в UTF-8.
"""
import re
import struct
import sys

IMG = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPALA_unp.bin"
OUT = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\_unp_data.txt"

img = open(IMG, "rb").read()

RANGES = [
    ("DATA_4617", 0x4617, 0x46170, 0x506E0),
    ("DATA_506E", 0x506E, 0x506E0, 0x52A60),
    ("DATA_52A6", 0x52A6, 0x52A60, 0x52D40),
    ("DATA_52D4", 0x52D4, 0x52D40, 0x552F0),
    ("DGROUP", 0x552F, 0x552F0, 0x5B820),
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
    # печатные прогоны: ASCII + CP866 рус
    for m in re.finditer(rb"(?:[\x20-\x7e\x80-\xff\xa1\xa2\xa5\xaa\xaf\xb2\xb3\xb5\xbc-\xbe\xc0-\xff][\x20-\x7e\x80-\xff]{3,})", chunk):
        s = m.group()
        try:
            txt = s.decode("cp866")
        except Exception:
            continue
        out.write("%s  %r\n" % (segaddr(seg, lo + m.start()), txt))

    out.write("\n--- таблицы word (прогоны >=6 ненулевых LE-word < 0x6000) ---\n")
    i = 0
    n = len(chunk) // 2
    words = list(struct.unpack("<%dH" % n, chunk[: n * 2]))
    while i < n:
        if words[i] and words[i] < 0x6000:
            j = i
            while j < n and words[j] < 0x6000 and (words[j] or words[j + 1] if j + 1 < n else True):
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

    # фрагменты вокруг форматных строк FORTRAN (скобки)
    out.write("\n--- FORTRAN-форматы (строки с '(' и букво-цифровыми полями) ---\n")
    for m in re.finditer(rb"[\x20-\x7e]{6,}", chunk):
        s = m.group().decode("ascii", "replace")
        if "(" in s and re.search(r"[iIfFeEgG aA]\d|'", s):
            out.write("%s  %s\n" % (segaddr(seg, lo + m.start()), s))

out.close()
print("written", OUT)

# отдельно: сводка по всем строкам трёх сегментов для отчёта
for name, seg, lo, hi in RANGES[1:4]:
    chunk = img[lo:hi]
    cnt = sum(1 for m in re.finditer(rb"(?:[\x20-\x7e\x80-\xff]{4,})", chunk))
    print(name, "строк-прогонов >=4:", cnt)
