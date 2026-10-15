# -*- coding: utf-8 -*-
"""TASK_OPAVA: карта распакованного OPAVA_unp.bin (аналог unp_map.py).

1. Трейлер EXEPACK -> пересчитанный MZ (CS/IP/SS/SP оригинала).
2. Верификация: сколько байт образа совпадает с файлом дословно (plain-зона).
3. Скан far-вызовов/переходов (9A/EA) -> гистограмма целевых сегментов.
4. Нулевые диапазоны (BSS) / данные / код (плотность 55 8B EC).
Результат — в REVERSE_OPAVA.md; far-цели -> reverse_data/_opava_fartargets.txt.
"""
import struct
import sys

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import tsr_lib as T

IMG = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPAVA_unp.bin"

img = open(IMG, "rb").read()
exe = T.load("OPAVA.EXE")
inf = T.mz_info(exe)
img_bytes = (inf["pages"] - 1) * 512 + (inf["bytes_last"] or 512)

print("== образ ==")
print("unp size: %#x paragraphs=%#x" % (len(img), len(img) // 16))
print("file: %#x, MZ image: %#x, хвост файла за образом: %#x" % (
    len(exe), img_bytes, len(exe) - img_bytes))

# ---- 1. трейлер EXEPACK ----
tr_off = 0x3A540  # найден поиском 'RB' + стаб 8B E8 8C C0
tw = struct.unpack("<8H", exe[tr_off:tr_off + 16])
names = ["IP0", "CS0", "skip", "stub_para", "SP0", "SS0", "mem_end_para", "magic"]
print("\n== трейлер EXEPACK (file %#x) ==" % tr_off)
for n, v in zip(names, tw):
    print("  %-12s %#06x" % (n, v))

# ---- 2. верификация plain-зоны ----
print("\n== plain-зона (образ == файл дословно) ==")
limit = min(len(img), img_bytes - inf["hdr_para"] * 16, len(exe) - 0x200)
run = 0
first_mism = None
for i in range(limit):
    if img[i] == exe[0x200 + i]:
        run += 1
    else:
        first_mism = i
        break
print("дословно совпадают первые %#x байт; первое расхождение: %s" % (
    run, hex(first_mism) if first_mism is not None else "нет"))
mism_total = sum(1 for i in range(limit) if img[i] != exe[0x200 + i])
print("всего несовпадений в [0..%#x): %d" % (limit, mism_total))

# ---- 3. far-скан ----
print("\n== far-цели (9A call / EA jmp) ==")
from collections import defaultdict

seg_hist = defaultdict(int)
seg_offs = defaultdict(set)
n_call = n_jmp = 0
sites = []
for i in range(0, len(img) - 5):
    b = img[i]
    if b == 0x9A:
        off, seg = struct.unpack("<HH", img[i + 1:i + 5])
        n_call += 1
    elif b == 0xEA:
        off, seg = struct.unpack("<HH", img[i + 1:i + 5])
        n_jmp += 1
    else:
        continue
    lin = (seg << 4) + off
    if lin >= len(img):
        continue
    seg_hist[seg] += 1
    seg_offs[seg].add(off)
    sites.append((i, b, seg, off))
print("call far: %d, jmp far: %d, целей в образе: %d" % (n_call, n_jmp, sum(seg_hist.values())))
print("\n  сегмент  ссылок  целей  диапазон целей      линейный диапазон")
for seg in sorted(seg_hist):
    offs = sorted(seg_offs[seg])
    print("  %04x      %5d  %5d   %04x..%04x       %#07x..%#07x" % (
        seg, seg_hist[seg], len(offs), offs[0], offs[-1], seg * 16, seg * 16 + max(offs)))

with open(r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\_opava_fartargets.txt", "w") as f:
    for site, b, seg, off in sites:
        f.write("%06x %s %04x:%04x\n" % (site, "call" if b == 0x9A else "jmp ", seg, off))

# ---- 4. нулевые диапазоны (BSS) ----
print("\n== нулевые диапазоны >=0x400 в образе ==")
runs = []
i = 0
while i < len(img):
    if img[i] == 0:
        j = i
        while j < len(img) and img[j] == 0:
            j += 1
        if j - i >= 0x400:
            runs.append((i, j))
        i = j
    else:
        i += 1
for a, b in runs:
    print("  %#07x..%#07x  (%#x байт нулей)" % (a, b, b - a))

# ---- 5. плотность прологов ----
print("\n== плотность прологов push bp;mov bp,sp (55 8B EC) по 64K ==")
for base in range(0, len(img), 0x10000):
    chunk = img[base:base + 0x10000]
    n = chunk.count(b"\x55\x8b\xec")
    if n:
        print("  %#07x..%#07x: %d" % (base, base + len(chunk), n))
