# -*- coding: utf-8 -*-
"""TASK_OPALO §2: карта сегментов OPALO_unp.bin / OPALOW_unp.bin.

1. far-скан 9A/EA -> гистограмма целевых сегментов (как unp_map.py для OPALA).
2. Нулевые диапазоны (BSS/оверлей-пул) и границы инициализированных данных.
3. Оверлеи в файле за пределами MZ-образа: границы и сигнатуры.
"""
import struct
import sys
from collections import defaultdict

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import tsr_lib as T

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"


def far_scan(img):
    seg_hist = defaultdict(int)
    seg_offs = defaultdict(set)
    sites = []
    for i in range(len(img) - 5):
        b = img[i]
        if b in (0x9A, 0xEA):
            off, seg = struct.unpack("<HH", img[i + 1:i + 5])
        else:
            continue
        if (seg << 4) + off >= len(img):
            continue
        seg_hist[seg] += 1
        seg_offs[seg].add(off)
        sites.append((i, b, seg, off))
    return seg_hist, seg_offs, sites


def zero_runs(img, minlen=0x400):
    runs, i = [], 0
    while i < len(img):
        if img[i] == 0:
            j = i
            while j < len(img) and img[j] == 0:
                j += 1
            if j - i >= minlen:
                runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def map_exe(name):
    img = open(RD + "\\" + name + "_unp.bin", "rb").read()
    exe = T.load(name + ".EXE")
    inf = T.mz_info(exe)
    img_bytes = (inf["pages"] - 1) * 512 + (inf["bytes_last"] or 512)

    print("=" * 72)
    print("%s: unp=%#x, MZ-образ=%#x, файл=%#x (за образом %#x = оверлеи/хвост)" %
          (name, len(img), img_bytes, len(exe), len(exe) - img_bytes))

    # верификация plain-зоны
    plain = img_bytes - inf["hdr_para"] * 16
    mism = sum(1 for i in range(0, min(plain, len(img))) if img[i] != exe[0x200 + i])
    print("plain-зона: %s (%d несовпадений из %#x)" % ("OK" if not mism else "MISMATCH", mism, plain))

    seg_hist, seg_offs, sites = far_scan(img)
    with open(RD + "\\_%s_fartargets.txt" % name, "w") as f:
        for site, b, seg, off in sites:
            f.write("%06x %s %04x:%04x\n" % (site, "call" if b == 0x9A else "jmp ", seg, off))
    print("far-целей: %d   (топ-сегменты)" % len(sites))
    for seg, cnt in sorted(seg_hist.items(), key=lambda kv: -kv[1])[:20]:
        offs = sorted(seg_offs[seg])
        print("  %04x  ссылок %5d  целей %4d  цели %04x..%04x  лин %#x..%#x" % (
            seg, cnt, len(offs), offs[0], offs[-1], seg * 16 + offs[0], seg * 16 + offs[-1]))

    print("  нулевые диапазоны >=0x400:")
    for a, b in zero_runs(img):
        print("    %#07x..%#07x  (%#x)" % (a, b, b - a))

    # прологи по 16K-окнам
    print("  прологи 55 8B EC по 16K-окнам:")
    for base in range(0, len(img), 0x4000):
        n = img[base:base + 0x4000].count(b"\x55\x8b\xec")
        if n:
            print("    %#07x: %d" % (base, n))

    # оверлейная зона файла: структура
    ov = exe[img_bytes:]
    if len(ov) > 16:
        print("  файл-хвост %#x..%#x, первые 32 б: %s" % (img_bytes, len(exe), ov[:32].hex()))
        runs = zero_runs(ov, 0x40)
        nz = len(ov) - sum(b - a for a, b in runs)
        print("  хвост: нулевых %#x, ненулевых %#x; нулевые диапазоны:" % (len(ov) - nz, nz))
        for a, b in runs[:20]:
            print("    %#x..%#x (%#x)" % (img_bytes + a, img_bytes + b, b - a))


if __name__ == "__main__":
    for nm in (sys.argv[1:] or ["OPALO", "OPALOW"]):
        map_exe(nm)
