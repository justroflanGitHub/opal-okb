# -*- coding: utf-8 -*-
"""TASK_LAP: сборка merged-образа OPALLAP_full.bin + seeds для Ghidra.

Модель оверлеев OPALLAP (подтверждена дизассемблом, см. REVERSE_LAP.md §2):
- DGROUP = 0x5273; собственное имя 'opallap.exe' @ ds:0x46F7;
- пул юнитов 0x30BA:0000..0x3C630 (нули в руте, ридер 0x24942 пишет туда
  порциями 16К, загрузчик-цепочка 0x249E7: mini-MZ, [si+0x1A]=ovno,
  релокации 0x24980);
- вызов юнитов через INT 3Fh (обработчик 0x1ECB:0x5EA5): байт-селектор за
  INT → word[sel] @ ds:0x4554 = сегмент входа, byte[sel] @ ds:0x465E = юнит;
  селекторов 133 (0 — пустышка), юниты 1..6: 13/34/13/16/40/16 входов.
"""
import struct
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import opalo_ovl

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"

# рантайм-база пула + фиктивные базы юнитов 2..6 (за пределами рута 0x5FA10)
OV_BASE = 0x30BA
FAKE = {2: 0x6000, 3: 0x6C00, 4: 0x7100, 5: 0x7800, 6: 0x8400}

# таблицы селекторов (линейные адреса в _unp-образе, DGROUP=0x5273)
T_WORD = 0x56C84   # ds:0x4554
T_BYTE = 0x56D8E   # ds:0x465E
NSEL = 133


def merged_base(unit):
    return OV_BASE if unit == 1 else FAKE[unit]


def main():
    opalo_ovl.CFG["OPALLAP"] = dict(ov_base=OV_BASE, fake=FAKE)
    units, imgs = opalo_ovl.build("OPALLAP")

    unp = open(RD + r"\OPALLAP_unp.bin", "rb").read()
    segs, unit_of = [], []
    for s in range(NSEL):
        segs.append(struct.unpack("<H", unp[T_WORD + 2 * s:T_WORD + 2 * s + 2])[0])
        unit_of.append(unp[T_BYTE + s])
    live = [(s, segs[s], unit_of[s]) for s in range(1, NSEL) if unit_of[s] and segs[s]]
    print("селекторов живых: %d, юниты: %s" % (
        len(live), sorted(Counter(u for _, _, u in live).items())))

    with open(RD + r"\_opallap_seeds.txt", "w") as f:
        for s, seg, u in live:
            m = merged_base(u) + (seg - OV_BASE)
            f.write("%04x 0000\n" % m)
    print("seeds -> _opallap_seeds.txt")


if __name__ == "__main__":
    main()
