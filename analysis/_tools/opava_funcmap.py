# -*- coding: utf-8 -*-
"""TASK_OPAVA: карта функций OPAVA (линейные адреса, размеры, x87-плотность).

_index.txt (seg:off name) -> линейный адрес, размер по соседней функции,
счётчики FPU-опкодов (9b/d8-df), int 21h/3Fh/16h/10h. Выход: _opava_funcs.txt.
"""
import re

IDX = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\..\..\..\..\..\tools\rea-out\decomp_opava\_index.txt"
IDX = r"C:\tools\rea-out\decomp_opava\_index.txt"
IMG = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPAVA_unp.bin"

img = open(IMG, "rb").read()

def zone(lin):
    if lin < 0x1C510:
        return "MAIN"
    if 0x1C510 <= lin < 0x1C7C0:
        return "ALLOC"
    if 0x1C7C0 <= lin < 0x28E90:
        return "RTL2"
    if 0x28E90 <= lin < 0x303E0:
        return "RTL1"
    if 0x303E0 <= lin < 0x35FB0:
        return "TAIL"
    return "DATA?"

funcs = []
for line in open(IDX):
    m = re.match(r"([0-9a-f]{4}):([0-9a-f]{4}) (\S+)", line.strip())
    if not m:
        continue
    seg, off, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
    funcs.append(((seg << 4) + off, name))

funcs.sort()
# дедупликация по linear
dedup = {}
for lin, name in funcs:
    if lin not in dedup:
        dedup[lin] = name
funcs = sorted(dedup.items())

FPU_NEXT = False  # d8-df: опкод + modrm; грубая оценка — считаем байты d8..df с весом
out = open(r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\_opava_funcs.txt", "w", encoding="utf-8")
out.write("# lin size zone fpu int21 int3f int16 int10 name\n")
rows = []
for i, (lin, name) in enumerate(funcs):
    end = funcs[i + 1][0] if i + 1 < len(funcs) else min(lin + 0x400, len(img))
    size = end - lin
    b = img[lin:end]
    fpu = sum(b.count(bytes([op])) for op in range(0xD8, 0xE0))
    rows.append((lin, size, zone(lin), fpu,
                 b.count(b"\xcd\x21"), b.count(b"\xcd\x3f"), b.count(b"\xcd\x16"), b.count(b"\xcd\x10"), name))
    out.write("%06x %5x %-5s %4d %3d %3d %3d %3d %s\n" % rows[-1])
out.close()

print("функций:", len(funcs))
big = sorted(rows, key=lambda r: -r[3])[:30]
print("\n== топ-30 по FPU-опкодам ==")
for r in big:
    print("%06x %5x %-5s fpu=%4d i21=%2d i3f=%2d %s" % (r[0], r[1], r[2], r[3], r[4], r[5], r[8]))
print("\n== топ-15 по размеру (код MAIN) ==")
for r in sorted([r for r in rows if r[2] == "MAIN"], key=lambda r: -r[1])[:15]:
    print("%06x %5x fpu=%4d i3f=%2d %s" % (r[0], r[1], r[3], r[5], r[8]))
