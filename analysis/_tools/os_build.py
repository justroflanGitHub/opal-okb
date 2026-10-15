# -*- coding: utf-8 -*-
"""TASK_OS: сборка merged-образа OPALOS_full.bin + seeds для Ghidra.

Модель оверлеев OPALOS (подтверждена дизассемблом, см. REVERSE_OS.md §2):
- DGROUP = 0x63D0; имя 'opalos.exe' @ ds:0x3F35;
- вход (EXEPACK CS0:IP0) = 0x2E62:0x6271: ставит int 3Fh := 0x2E62:0x612D
  (Overlay Manager FORTRAN 5.0), DS := 0x63D0, ljmp 0x2E62:0x43D0 (RTL-startup);
- пул юнитов 0x4AB4:0000..0x599BF (нули в руте): ВСЕ юниты грузятся в один пул;
- вызов юнитов через INT 3Fh с инлайн-payload `CD 3F <sel> <off16>` (3 байта):
  word[sel] @ ds:0x3DA4 = сегмент входа, byte[sel] @ ds:0x3EA2 = № юнита;
  селекторов 127 (1..126 живые), юниты 1..4: 45/48/11/22 входа.
"""
import struct
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import opalo_ovl

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"

# рантайм-база пула + фиктивные базы юнитов 2..4 (за пределами рута 0x6FA60)
OV_BASE = 0x4AB4
FAKE = {2: 0x7000, 3: 0x8000, 4: 0x8600}

# таблицы селекторов (линейные адреса в _unp-образе, DGROUP=0x63D0)
DGROUP = 0x63D00
T_WORD = DGROUP + 0x3DA4   # word[sel] = сегмент входа (0x4AB4..0x5985)
T_BYTE = DGROUP + 0x3EA2   # byte[sel] = № юнита
NSEL = 127


def merged_base(unit):
    return OV_BASE if unit == 1 else FAKE[unit]


def main():
    opalo_ovl.CFG["OPALOS"] = dict(ov_base=OV_BASE, fake=FAKE)
    units, imgs = opalo_ovl.build("OPALOS")

    unp = open(RD + r"\OPALOS_unp.bin", "rb").read()
    segs, unit_of = [], []
    for s in range(NSEL):
        segs.append(struct.unpack("<H", unp[T_WORD + 2 * s:T_WORD + 2 * s + 2])[0])
        unit_of.append(unp[T_BYTE + s])
    live = [(s, segs[s], unit_of[s]) for s in range(1, NSEL) if unit_of[s] and segs[s]]
    print("селекторов живых: %d, юниты: %s" % (
        len(live), sorted(Counter(u for _, _, u in live).items())))

    with open(RD + r"\_oplos_seeds.txt", "w") as f:
        for s, seg, u in live:
            m = merged_base(u) + (seg - OV_BASE)
            f.write("%04x 0000\n" % m)
    print("seeds -> _oplos_seeds.txt")


if __name__ == "__main__":
    main()
