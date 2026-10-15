# -*- coding: utf-8 -*-
"""TASK_OS: дизассемблер контекстов int 3Fh в OPALOS_unp (capstone)."""
import sys

import capstone

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
from os_map import int_sites

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"


def dis(img, lin, before=48, after=24):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    md.detail = False
    lo = max(0, lin - before)
    # выравнивание: дизассемблируем подряд от lo; рваные старты дают мусор,
    # поэтому пробуем несколько стартов и берём самый длинный непрерывный поток
    best = []
    for st in range(lo, min(lo + 16, lin)):
        ins = list(md.disasm(img[st:lin + after], st))
        # обрезаем на int 3Fh + 2
        out = []
        for i in ins:
            out.append(i)
            if i.address + i.size >= lin + 2:
                break
        if len(out) > len(best):
            best = out
    return best


if __name__ == "__main__":
    img = open(RD + r"\OPALOS_unp.bin", "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    for s in int_sites(img):
        if s == 4:
            print("=== %06x (вход 0000:0000)" % s)
            for i in md.disasm(img[0:0x60], 0):
                print("  %04x  %-22s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
            continue
        print("=== site %#x" % s)
        for i in dis(img, s):
            mark = " <<INT3F" if i.address == s else ""
            print("  %04x  %-20s %s %s%s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str, mark))
