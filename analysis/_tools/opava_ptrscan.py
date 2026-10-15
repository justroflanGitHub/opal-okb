# -*- coding: utf-8 -*-
"""TASK_OPAVA: поиск far-указателей (seg:off) на данные-зоны OPAVA в образе.

Цели: 437b (меню WZON..), 3cee (баннер), 58b4 (вьюер), 48a1 (форматы EAACVA/WNB*),
58df (DGROUP строки). Ищем 4-байтные LE (off, seg) в коде/данных.
"""
import struct

img = open(r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPAVA_unp.bin", "rb").read()

ZONES = {
    0x437B: "DATA_MENU",
    0x3CEE: "DATA_BANR",
    0x58B4: "DATA_VIEW",
    0x48A1: "DATA_FMT",
    0x58DF: "DGROUP",
    0x3CF3: "BSS_3CF3",
    0x438A: "BSS_438A(common)",
    0x49F1: "BSS_49F1",
}

for seg, name in sorted(ZONES.items()):
    hits = []
    for i in range(0, len(img) - 4):
        off, s = struct.unpack("<HH", img[i:i + 4])
        if s == seg and off < 0x10000:
            # правдоподобие: указатель в коде/данных (не внутри самой зоны данных)
            lin = i
            if seg * 16 <= lin < seg * 16 + 0x20000:
                continue
            hits.append((lin, off))
    print("== %s (seg %04x): %d указателей" % (name, seg, len(hits)))
    # группировка по зоне, где лежит указатель
    zones = {
        "CODE_MAIN(0..1C510)": (0, 0x1C510),
        "CODE_RTL2(1C7C0)": (0x1C7C0, 0x28E90),
        "CODE_RTL1(28E90)": (0x28E90, 0x303E0),
        "CODE_TAIL(303E0)": (0x303E0, 0x35FB0),
        "DATA_FMT(48A10)": (0x48A10, 0x49F05),
        "DGROUP(58DF0)": (0x58DF0, 0x5E560),
    }
    for zn, (lo, hi) in zones.items():
        zh = [(lin, off) for lin, off in hits if lo <= lin < hi]
        if zh:
            print("   %-22s %d: %s" % (zn, len(zh),
                  " ".join("%06x->%04x" % h for h in zh[:24]) + (" ..." if len(zh) > 24 else "")))
