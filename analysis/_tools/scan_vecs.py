# -*- coding: utf-8 -*-
"""Скан: установка int-векторов, TSR-маркеры, иммедиаты 0xFF9/0x1000, EXEC, resize."""
import tsr_lib as T, re, struct, sys

FILES = ["OPALA.EXE", "OPALTRAC.EXE", "OPALCALC.EXE", "METAPRN.EXE", "METAPRNO.EXE",
         "OPAL.COM", "KEYRUS.COM", "OPAL5X5.EXE", "OPALOW.EXE", "OPALVP.EXE",
         "OPALO.EXE", "OPALOS.EXE", "OPAVA.EXE", "OPALLAP.EXE"]

def scans(name):
    d = T.load(name)
    print("=" * 70)
    print(name, "size=%#x" % len(d), "MZ" if d[:2] == b"MZ" else ("COM" if d[:1] == b"\xe9" or True else ""))
    if d[:2] == b"MZ":
        inf = T.mz_info(d)
        print("  hdr:", {k: hex(v) for k, v in inf.items()}, "relocs:", len(T.relocations(d)))
    # mov ax,25xx ; int 21  →  b8 xx 25 cd 21
    for m in re.finditer(rb"\xb8(.{1})\x25\xcd\x21", d, re.S):
        vec = m.group(1)[0]
        print("  DOS-set-vector int %02xh @ file %#06x" % (vec, m.start()))
    # int 21h ah=31h (tsr keep)  →  b4 31 cd 21
    for m in re.finditer(rb"\xb4\x31\xcd\x21", d):
        print("  TSR-KEEP (int21 ah=31) @ %#06x" % m.start())
    # exec: b8 00 4b / b4 4b cd 21
    for m in re.finditer(rb"(?:\xb8\x00\x4b|\xb4\x4b)\xcd\x21", d):
        print("  EXEC (int21 ah=4b) @ %#06x" % m.start())
    # resize ah=4a
    for m in re.finditer(rb"\xb4\x4a\xcd\x21", d):
        print("  RESIZE (int21 ah=4a) @ %#06x" % m.start())
    # xor ax,ax; mov es,ax → 31 c0 8e c0 (или 33 c0 8e c0)
    for m in re.finditer(rb"(?:\x31\xc0|\x33\xc0)\x8e\xc0", d):
        off = m.start()
        tail = d[off+4: off+64]
        # после этого пишут в es:[0xD0..0xF8] — int 34..3E вектора
        m2 = re.match(rb"(?:\x26|\x06)?[\x00-\xff]{0,12}?\x26\xc7\x06(....)", d[off+4:off+48], re.S)
        print("  IVT-base (xor ax,ax; mov es,ax) @ %#06x  next=%s" % (off, d[off+4:off+24].hex(" ")))
    # иммедиат 0x0ff9 в коде: b8/b9/ba/bb/bf f9 0f  и push 0ff9 (68 f9 0f)
    for m in re.finditer(rb"[\xb8\xb9\xba\xbb\xbe\xbf\x68\xf9\x0f]", d):
        pass  # слишком шумно — отдельно ниже
    for m in re.finditer(rb"[\xb8\xb9\xba\xbb\xbe\xbf]\xf9\x0f", d):
        print("  imm 0x0FF9 reg-load @ %#06x  ctx=%s" % (m.start(), d[m.start()-6:m.start()+16].hex(" ")))

for n in FILES:
    try:
        scans(n)
    except FileNotFoundError:
        print("=" * 70, "\n", n, "MISSING")
