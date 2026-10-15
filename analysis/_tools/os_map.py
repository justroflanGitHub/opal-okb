# -*- coding: utf-8 -*-
"""TASK_OS §1: карта OPALOS_unp / GENIZE_unp — far-скан, int 3Fh, оверлеи.

Дополняет opalo_map.py: поиск ридера оверлеев (int 3Fh / mov di,imm),
разбор мини-MZ цепочки хвоста OPALOS.EXE, вывод OV_BASE.
"""
import re
import struct
import sys

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import tsr_lib as T
from opalo_ovl import parse_chain

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"


def int_sites(img, lo=0, hi=None):
    """Адреса `int 3Fh` (cd 3f) в диапазоне, с контекстом."""
    hi = hi or len(img)
    pat = re.escape(bytes([0xCD, 0x3F]))
    out = []
    for m in re.finditer(pat, img[lo:hi]):
        out.append(lo + m.start())
    return out


def mov_di_imm(img, lo, hi):
    """`mov di, imm16` = bf xx xx внутри окна."""
    return [(lo + m.start(), struct.unpack("<H", img[m.start() + 1:m.start() + 3])[0])
            for m in re.finditer(b"\xbf", img[lo:hi])
            if m.start() + 3 <= hi - lo]


def report(name):
    img = open(RD + "\\" + name + "_unp.bin", "rb").read()
    exe = T.load(name + ".EXE")
    inf = T.mz_info(exe)
    img_bytes = (inf["pages"] - 1) * 512 + (inf["bytes_last"] or 512)
    print("=" * 72)
    print("%s: unp=%#x  MZ-img=%#x  file=%#x  tail=%#x" %
          (name, len(img), img_bytes, len(exe), len(exe) - img_bytes))
    sites = int_sites(img)
    print("int 3Fh: %d sites: %s" % (len(sites), [hex(s) for s in sites]))
    for s in sites:
        print("  ctx@%#x: %s" % (s, img[s - 12:s + 12].hex()))
    if len(exe) > img_bytes + 0x200:
        units = parse_chain(exe, img_bytes)
        for u in units:
            print("unit MZ@%#x ovno=%d size=%#x nrel=%d hdr=%#x img_para=%#x" %
                  (u["mz"], u["ovno"], u["size"], u["nrel"], u["hdr"], u["img_para"]))
    return img, exe, inf


if __name__ == "__main__":
    for nm in (sys.argv[1:] or ["OPALOS", "GENIZE"]):
        report(nm)
