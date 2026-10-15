# -*- coding: utf-8 -*-
"""TASK_LAP: патч INT 3Fh → call far в OPALLAP_full.bin (для Ghidra-потока).

Протокол OPALLAP (обработчик 0x1ECB:0x5EA5, см. REVERSE_LAP.md §3):
`CD 3F <sel:byte> <off:word>` — 3 байта payload; селектор → word[sel] @
DGROUP:0x4554 = сегмент входа в пуле, byte[sel] @ DGROUP:0x465E = № юнита.
Каждый сайт заменяется на `9A <off> <mseg>` (call far) на перелинкованный
в merged-образе вход — автоанализ получает настоящее far-ребро root→unit.
"""
import struct

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"

OV_BASE = 0x30BA
FAKE = {2: 0x6000, 3: 0x6C00, 4: 0x7100, 5: 0x7800, 6: 0x8400}
UNIT_SIZE = {1: 0x39EF, 2: 0xB460, 3: 0x41AE, 4: 0x6109, 5: 0xB99D, 6: 0x6A84}
ROOT_END = 0x5FA10

T_WORD = 0x56C84   # DGROUP(0x5273)+0x4554
T_BYTE = 0x56D8E   # DGROUP+0x465E
NSEL = 133


def merged_base(u):
    return OV_BASE if u == 1 else FAKE[u]


def regions():
    rs = [("root", 0, ROOT_END)]
    for u in range(2, 7):
        rs.append(("unit%d" % u, merged_base(u) << 4, (merged_base(u) << 4) + UNIT_SIZE[u]))
    return rs


def main():
    buf = bytearray(open(RD + r"\OPALLAP_full.bin", "rb").read())
    segs = [struct.unpack("<H", buf[T_WORD + 2 * s:T_WORD + 2 * s + 2])[0] for s in range(NSEL)]
    unit = bytes(buf[T_BYTE:T_BYTE + NSEL])

    rows, bad = [], []
    for lo_name, lo, hi in regions():
        i = lo
        while True:
            i = bytes(buf).find(b"\xcd\x3f", i + 1, hi)
            if i < 0:
                break
            sel = buf[i + 2]
            off = struct.unpack("<H", bytes(buf[i + 3:i + 5]))[0]
            if not (1 <= sel < NSEL) or not unit[sel] or not segs[sel]:
                bad.append((lo_name, i, sel))
                continue
            u = unit[sel]
            mseg = merged_base(u) + (segs[sel] - OV_BASE)
            if not (merged_base(u) <= mseg < merged_base(u) + (UNIT_SIZE[u] >> 4) + 1):
                bad.append((lo_name, i, sel))
                continue
            rows.append((lo_name, i, sel, u, segs[sel], off, mseg))
            buf[i] = 0x9A                      # call far mseg:off
            buf[i + 1:i + 5] = struct.pack("<HH", off, mseg)

    open(RD + r"\OPALLAP_full.bin", "wb").write(bytes(buf))
    with open(RD + r"\_opallap_int3f.txt", "w") as f:
        f.write("# region lin sel unit pool_seg entry_off merged_seg merged_entry\n")
        for r in rows:
            f.write("%s %06x %02x %d %04x %04x %04x %06x\n" % (
                r[0], r[1], r[2], r[3], r[4], r[5], r[6], (r[6] << 4) + r[5]))
    print("патчей: %d (root: %d), плохих сайтов: %d" % (
        len(rows), sum(1 for r in rows if r[0] == "root"), len(bad)))
    for b in bad:
        print("  ?? %s @%#x sel=%02x" % b)


if __name__ == "__main__":
    main()
