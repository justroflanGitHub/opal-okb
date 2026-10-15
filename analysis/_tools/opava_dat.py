# -*- coding: utf-8 -*-
"""TASK_OPAVA §4: hex/структурный разбор OPALOW.DAT, SCMVA.DAT, VAFORUS.DAT."""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def dump(name, maxw=40):
    d = open(r"extracted\opal_okb" + "\\" + name, "rb").read()
    print("=" * 70)
    print("%s: %d байт" % (name, len(d)))
    # заголовок: первые 0x40 байт hex
    for j in range(0, min(0x60, len(d)), 16):
        row = d[j:j + 16]
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
        print("  %04x  %-47s  %s" % (j, " ".join("%02x" % c for c in row), asc))
    # интерпретация: как слова / как float
    n = len(d) // 2
    words = struct.unpack("<%dH" % n, d[:n * 2])
    nz = [i for i, v in enumerate(words) if v]
    print("  word-интерпретация: первый ненулевой @word %d (байт %#x), ненулевых %d/%d"
          % (nz[0], nz[0] * 2, len(nz), n) if nz else "  все нули")
    # ведущие нули = размер int-заголовка?
    m8 = len(d) // 4
    fl = struct.unpack("<%df" % m8, d[:m8 * 4])
    plausible = sum(1 for v in fl[:0x400] if abs(v) < 1e6 and (v == 0 or abs(v) > 1e-9))
    print("  float32 (первые 0x400): правдоподобных %d/%d; примеры: %s"
          % (plausible, min(m8, 0x400), ["%.4g" % v for v in fl[:8]]))
    d8 = len(d) // 8
    db = struct.unpack("<%dd" % d8, d[:d8 * 8])
    pb = sum(1 for v in db[:0x200] if abs(v) < 1e8 and (v == 0 or abs(v) > 1e-12))
    print("  float64 (первые 0x200): правдоподобных %d/%d; примеры: %s"
          % (pb, min(d8, 0x200), ["%.5g" % v for v in db[:6]]))
    return d

for nm in ("OPALOW.DAT", "SCMVA.DAT", "VAFORUS.DAT"):
    dump(nm)
