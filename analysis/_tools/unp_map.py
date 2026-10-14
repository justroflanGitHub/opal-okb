# -*- coding: utf-8 -*-
"""TASK_UNP §1: карта распакованного OPALA_unp.bin.

1. Пересчёт MZ-заголовка для _unp (CS/IP/SS/SP из трейлера EXEPACK, rel-таблица).
2. Верификация plain-зоны против исходного EXE.
3. Скан far-вызовов/переходов (9A/EA) -> гистограмма целевых сегментов.
4. Классификация диапазонов: нули (BSS) / данные / код.
Результат печатается в markdown-подобном виде для REVERSE_UNP.md.
"""
import struct
import sys

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import tsr_lib as T

IMG = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPALA_unp.bin"

img = open(IMG, "rb").read()
exe = T.load("OPALA.EXE")
inf = T.mz_info(exe)
img_bytes = (inf["pages"] - 1) * 512 + (inf["bytes_last"] or 512)

print("== образ ==")
print("unp size: %#x paragraphs=%#x" % (len(img), len(img) // 16))

# ---- 1. трейлер EXEPACK -> пересчитанный вход ----
tr_off = 0x44840  # найден поиском 97 93 73 2E + 'RB'
tw = struct.unpack("<8H", exe[tr_off:tr_off + 16])
names = ["IP0", "CS0", "skip", "stub_para", "SP0", "SS0", "mem_end_para", "magic"]
print("\n== трейлер EXEPACK (file %#x) ==" % tr_off)
for n, v in zip(names, tw):
    print("  %-12s %#06x %s" % (n, v, repr(exe[tr_off + 2 * names.index(n): tr_off + 2 * names.index(n) + 2]) if n == "magic" else ""))

# ---- 2. верификация plain-зоны ----
print("\n== plain-зона ==")
plain = min(len(img), img_bytes - inf["hdr_para"] * 16)
mism = [i for i in range(0, 0x3F600) if img[i] != exe[0x200 + i]]
print("bytes[0..0x3F600) vs file[0x200..): %s (не совпало %d)" % (
    "OK" if not mism else "MISMATCH", len(mism)))

# ---- 3. far-скан ----
print("\n== far-цели (9A call / EA jmp) ==")
from collections import defaultdict

seg_hist = defaultdict(int)          # сегмент -> число ссылок
seg_offs = defaultdict(set)          # сегмент -> смещения целей
far_sites = defaultdict(int)         # сегмент-цель -> число мест вызова
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
        continue  # за образом (например, xxxx:FFFF адресация)
    seg_hist[seg] += 1
    seg_offs[seg].add(off)
    sites.append((i, b, seg, off))
print("call far: %d, jmp far: %d, целей в образе: %d" % (n_call, n_jmp, sum(seg_hist.values())))
print("\n  сегмент  ссылок  целей  диапазон целей      линейный диапазон")
for seg in sorted(seg_hist):
    offs = sorted(seg_offs[seg])
    lin_lo, lin_hi = seg * 16, seg * 16 + max(offs)
    print("  %04x      %5d  %5d   %04x..%04x       %#07x..%#07x" % (
        seg, seg_hist[seg], len(offs), offs[0], offs[-1], lin_lo, lin_hi))

# сохраняем список целей для дальнейшей работы
with open(r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\_unp_fartargets.txt", "w") as f:
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

# ---- 5. известные данные-сегменты: где кончаются нули ----
print("\n== данные-сегменты: первый/последний ненулевой байт ==")
for seg, end in ((0x506E, 0x52A6), (0x52A6, 0x52D4), (0x52D4, 0x552F), (0x552F, 0x5B82), (0x5B82, len(img) // 16)):
    lo, hi = seg * 16, end * 16
    chunk = img[lo:hi]
    nz = [k for k, v in enumerate(chunk) if v]
    if nz:
        print("  %04x: данные %#x..%#x, ненулевые %#x..%#x (%d/%d)" % (
            seg, lo, hi, lo + nz[0], lo + nz[-1], len(nz), len(chunk)))
    else:
        print("  %04x: данные %#x..%#x, ВСЕ НУЛИ (BSS)" % (seg, lo, hi))

# ---- 6. код-зоны: плотность 9A/E8/55 8B EC ----
print("\n== плотность прологов push bp;mov bp,sp (55 8B EC) по 64K ==")
for base in range(0, len(img), 0x10000):
    chunk = img[base:base + 0x10000]
    n = chunk.count(b"\x55\x8b\xec")
    if n:
        print("  %#07x..%#07x: %d" % (base, base + len(chunk), n))
