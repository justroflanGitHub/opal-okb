# -*- coding: utf-8 -*-
"""TASK_OS §1b: релоки юнитов OPALOS → OV_BASE; извлечение + мерж OPALOS_full.bin.

Модель та же, что opalo_ovl.py для OPALO/OPALOW: хвост = цепочка мини-MZ;
юнит грузится целиком на OV_BASE:0000; релоки хранят финальный сегмент.
"""
import struct
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import tsr_lib as T
from opalo_ovl import parse_chain

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"


def unit_relocs(exe, u):
    p = u["mz"] + (u["reloc_off"] or 0x20)
    out = []
    for i in range(u["nrel"]):
        off, seg = struct.unpack("<HH", exe[p + 4 * i:p + 4 * i + 4])
        out.append((off, seg))
    return out


def analyze():
    exe = T.load("OPALOS.EXE")
    inf = T.mz_info(exe)
    img_bytes = (inf["pages"] - 1) * 512 + (inf["bytes_last"] or 512)
    units = parse_chain(exe, img_bytes)
    for u in units:
        rels = unit_relocs(exe, u)
        segs = Counter(s for _, s in rels)
        lo = min(segs)
        hi = max(segs)
        print("unit%d MZ@%#x nrel=%d reloc-seg min=%04x max=%04x  топ: %s" %
              (u["ovno"], u["mz"], u["nrel"], lo, hi,
               " ".join("%04x*%d" % kv for kv in segs.most_common(8))))
    return exe, units


if __name__ == "__main__":
    analyze()
