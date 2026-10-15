# -*- coding: utf-8 -*-
"""TASK_OPAVA: дизассемблер оверлей-входов int 3Fh + гистограммы релокаций модулей.

Пул = 4 MZ-модуля (file 1..4), каждый грузится контигерно от 0x35FC0.
Таблицы: селектор->сегмент DGROUP:0x3204, селектор->файл DGROUP:0x3266.
Вход (sel, entry_off) -> линейный seg*16+entry_off -> файловый адрес модуля.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"analysis\_tools")
import dis16

exe = open(r"extracted\opal_okb\OPAVA.EXE", "rb").read()
img = open(r"analysis\reverse_data\OPAVA_unp.bin", "rb").read()
dg = 0x58DF0

MODS = {1: (0x3C200, 0x5DF3), 2: (0x42400, 0x431F), 3: (0x47C00, 0x6D7E), 4: (0x4F200, 0x4415)}
BASE = 0x35FC0

def w(lin):
    return struct.unpack("<H", img[lin:lin + 2])[0]

def seg_of(sel):
    return w(dg + 0x3204 + 2 * sel)

def file_of(sel):
    return img[dg + 0x3266 + sel]

SITES = [  # (lin сайта, sel, entry)
    (0x013D, 0x01, 0x0), (0x0678, 0x26, 0xA), (0x07F0, 0x09, 0x5),
    (0x086D, 0x06, 0x3), (0x0B31, 0x07, 0x3), (0x0B83, 0x05, 0x5),
    (0x0BDC, 0x08, 0x4), (0x0C3F, 0x03, 0xA), (0x0CA8, 0x04, 0x4),
    (0x2580, 0x1A, 0x6), (0x2768, 0x0A, 0x0),
]

print("== релокации модулей: внешние сегменты (вне 0x35FC..0x3DB0 и DGROUP) ==")
for f, (st, sz) in MODS.items():
    hdr = {1:0x3BA00,2:0x42000,3:0x46800,4:0x4EA00}[f]
    crlc = struct.unpack("<H", exe[hdr + 6:hdr + 8])[0]
    lfa = struct.unpack("<H", exe[hdr + 0x18:hdr + 0x1A])[0]
    segs = {}
    for r in range(crlc):
        off, s = struct.unpack("<HH", exe[hdr + lfa + r * 4:hdr + lfa + r * 4 + 4])
        segs[s] = segs.get(s, 0) + 1
    ext = {s: c for s, c in segs.items() if not (0x35FC <= s <= 0x3DB0)}
    print("file %d: crlc=%d внешние: %s" % (f, crlc, sorted(ext.items())))

print("\n== входы оверлеев ==")
for site, sel, ent in SITES:
    f = file_of(sel)
    st, sz = MODS[f]
    mod = exe[st:st + sz]
    lin = seg_of(sel) * 16 + ent
    # виртуальный буфер: BASE..BASE+sz
    buf = bytearray(0x40000)
    buf[BASE:BASE + sz] = mod
    # релокации применяем: +0 (значения уже финальные)
    print("\n--- site %#06x sel=%#x (file %d, seg %04x, load %#x) entry=%#x ---"
          % (site, sel, f, seg_of(sel), seg_of(sel) * 16, ent))
    for _ln in dis16.disasm(bytes(buf), 0, lin - 0x30, 0x80):
        print(_ln)
